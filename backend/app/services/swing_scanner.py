"""Daily swing accumulation/distribution feature calculation.

Uses daily OHLCV and delivery participation. This is an accumulation proxy,
not true trade-side order flow and not evidence of institutional identity.
"""
from datetime import date
import asyncpg

STRATEGY_VERSION = "swing-v1"


async def compute_for_date(conn: asyncpg.Connection, trade_date: date) -> dict:
    # Current constituents are used until point-in-time membership snapshots are
    # populated. Do not treat historic results as survivorship-bias-free.
    await conn.execute("""
        WITH universe AS (
            SELECT DISTINCT upper(symbol) AS symbol
            FROM nifty_index_constituents
            WHERE upper(replace(index_name, ' ', '_')) IN
                  ('NIFTY_TOTAL_MARKET', 'NIFTY_TOTALMARKET')
        ),
        history AS (
            SELECT c.*,
                lag(c.close_price, 5) OVER (PARTITION BY c.symbol ORDER BY c.trade_date) AS close_5,
                lag(c.close_price, 20) OVER (PARTITION BY c.symbol ORDER BY c.trade_date) AS close_20,
                CASE WHEN count(c.total_traded_qty) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) = 20
                     THEN avg(c.total_traded_qty) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) END AS avg_volume_20,
                CASE WHEN count(c.turnover_lacs) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) = 20
                     THEN avg(c.turnover_lacs) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) END AS avg_turnover_20,
                CASE WHEN count(c.deliv_per) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) = 20
                     THEN avg(c.deliv_per) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) END AS avg_delivery_20,
                sum(CASE WHEN c.close_price > c.prev_close THEN c.total_traded_qty
                         WHEN c.close_price < c.prev_close THEN -c.total_traded_qty
                         ELSE 0 END) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS obv,
                sum(CASE WHEN c.high_price > c.low_price
                         THEN (((2*c.close_price-c.high_price-c.low_price)
                                 / NULLIF(c.high_price-c.low_price,0)) * c.total_traded_qty)
                         ELSE 0 END) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS ad_line,
                sum(CASE WHEN c.high_price > c.low_price
                         THEN (((2*c.close_price-c.high_price-c.low_price)
                                 / NULLIF(c.high_price-c.low_price,0)) * c.total_traded_qty)
                         ELSE 0 END)
                    OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS mfv_20,
                sum(c.total_traded_qty) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS volume_20,
                count(c.total_traded_qty) OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS bars_20,
                avg(greatest(c.high_price-c.low_price,
                             abs(c.high_price-c.prev_close),
                             abs(c.low_price-c.prev_close)))
                    OVER (PARTITION BY c.symbol ORDER BY c.trade_date
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS atr_14
            FROM cash_market_daily c
            JOIN universe u ON u.symbol = upper(c.symbol)
            WHERE c.series = 'EQ' AND c.trade_date <= $1
        ),
        price_flow AS (
            SELECT h.*,
                (h.high_price + h.low_price + h.close_price) / 3 AS typical_price,
                lag((h.high_price + h.low_price + h.close_price) / 3)
                    OVER (PARTITION BY h.symbol ORDER BY h.trade_date) AS prev_typical_price
            FROM history h
        ),
        money_flow AS (
            SELECT p.*,
                sum(CASE WHEN typical_price > prev_typical_price
                         THEN typical_price * total_traded_qty ELSE 0 END)
                    OVER (PARTITION BY symbol ORDER BY trade_date
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS positive_mf_14,
                sum(CASE WHEN typical_price < prev_typical_price
                         THEN typical_price * total_traded_qty ELSE 0 END)
                    OVER (PARTITION BY symbol ORDER BY trade_date
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS negative_mf_14,
                count(prev_typical_price) OVER (PARTITION BY symbol ORDER BY trade_date
                    ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) AS mfi_obs_14
            FROM price_flow p
        ),
        latest AS (
            SELECT h.*,
                row_number() OVER (PARTITION BY symbol ORDER BY trade_date DESC) AS rn,
                obv - lag(obv, 5) OVER (PARTITION BY symbol ORDER BY trade_date) AS obv_change_5
            FROM money_flow h
        ),
        features AS (
            SELECT *,
                CASE WHEN high_price > low_price
                    THEN ((close_price-low_price)-(high_price-close_price))
                         / NULLIF(high_price-low_price,0) ELSE 0 END AS clv,
                CASE WHEN avg_volume_20 > 0
                    THEN total_traded_qty::numeric / avg_volume_20 END AS rvol,
                CASE WHEN avg_turnover_20 > 0
                    THEN turnover_lacs / avg_turnover_20 END AS rvalue,
                CASE WHEN close_5 > 0 THEN (close_price/close_5-1)*100 END AS ret5,
                CASE WHEN close_20 > 0 THEN (close_price/close_20-1)*100 END AS ret20,
                CASE WHEN avg_delivery_20 IS NOT NULL
                    THEN deliv_per-avg_delivery_20 END AS delivery_delta,
                CASE WHEN bars_20 = 20 AND volume_20 > 0 THEN mfv_20/volume_20 END AS cmf20,
                CASE WHEN avg_price > 0 THEN (close_price/avg_price-1)*100 END AS vwap_deviation,
                CASE WHEN mfi_obs_14 = 14 AND coalesce(negative_mf_14,0) = 0 THEN 100
                     WHEN mfi_obs_14 = 14 AND coalesce(positive_mf_14,0) = 0 THEN 0
                     WHEN mfi_obs_14 = 14
                     THEN 100 - (100 / (1 + positive_mf_14 / NULLIF(negative_mf_14,0)))
                END AS mfi14
            FROM latest
            WHERE rn = 1
        ),
        scored AS (
            SELECT *,
                (CASE WHEN rvol >= 1.5 THEN 15 WHEN rvol >= 1.2 THEN 8 ELSE 0 END +
                 CASE WHEN rvalue >= 1.5 THEN 10 WHEN rvalue >= 1.2 THEN 5 ELSE 0 END +
                 CASE WHEN clv >= 0.7 THEN 15 WHEN clv >= 0.4 THEN 8 ELSE 0 END +
                 CASE WHEN close_price > prev_close THEN 10 ELSE 0 END +
                 CASE WHEN close_20 IS NOT NULL AND close_price > close_20 THEN 10 ELSE 0 END +
                 CASE WHEN delivery_delta >= 10 THEN 15 WHEN delivery_delta >= 5 THEN 8 ELSE 0 END +
                 CASE WHEN ret20 > 0 THEN 10 ELSE 0 END +
                 CASE WHEN obv_change_5 > 0 THEN 10 ELSE 0 END +
                 CASE WHEN cmf20 > 0 THEN 5 ELSE 0 END) AS acc_score,
                (CASE WHEN rvol >= 1.5 THEN 15 WHEN rvol >= 1.2 THEN 8 ELSE 0 END +
                 CASE WHEN rvalue >= 1.5 THEN 10 WHEN rvalue >= 1.2 THEN 5 ELSE 0 END +
                 CASE WHEN clv <= -0.7 THEN 15 WHEN clv <= -0.4 THEN 8 ELSE 0 END +
                 CASE WHEN close_price < prev_close THEN 10 ELSE 0 END +
                 CASE WHEN close_20 IS NOT NULL AND close_price < close_20 THEN 10 ELSE 0 END +
                 CASE WHEN delivery_delta <= -10 THEN 15 WHEN delivery_delta <= -5 THEN 8 ELSE 0 END +
                 CASE WHEN ret20 < 0 THEN 10 ELSE 0 END +
                 CASE WHEN obv_change_5 < 0 THEN 10 ELSE 0 END +
                 CASE WHEN cmf20 < 0 THEN 5 ELSE 0 END) AS dist_score
            FROM features
        )
        INSERT INTO swing_scanner_features (
            trade_date, symbol, close_price, volume, turnover_lacs, delivery_qty,
            delivery_pct, avg_volume_20, relative_volume, avg_turnover_20,
            relative_turnover, close_location_value, obv, obv_change_5, ad_line, cmf_20,
            atr_14, mfi_14, vwap_deviation_pct, return_5d_pct, return_20d_pct,
            delivery_pct_avg_20, delivery_pct_delta, accumulation_score,
            distribution_score, signal, reason_codes, data_quality, strategy_version
        )
        SELECT $1, symbol, close_price, total_traded_qty, turnover_lacs, deliv_qty,
            deliv_per, avg_volume_20, rvol, avg_turnover_20, rvalue, clv, obv, obv_change_5, ad_line,
            cmf20, atr_14, mfi14, vwap_deviation, ret5, ret20,
            avg_delivery_20, delivery_delta, least(100, acc_score),
            least(100, dist_score),
            CASE WHEN acc_score >= 65 AND acc_score > dist_score THEN 'ACCUMULATION'
                 WHEN dist_score >= 65 AND dist_score > acc_score THEN 'DISTRIBUTION'
                 WHEN acc_score >= 45 AND acc_score > dist_score THEN 'ACCUMULATION_WATCH'
                 WHEN dist_score >= 45 AND dist_score > acc_score THEN 'DISTRIBUTION_WATCH'
                 ELSE 'NEUTRAL' END,
            to_jsonb(array_remove(ARRAY[
                CASE WHEN rvol >= 1.5 THEN 'RELATIVE_VOLUME_SPIKE' END,
                CASE WHEN rvalue >= 1.5 THEN 'TRADED_VALUE_SPIKE' END,
                CASE WHEN clv >= 0.7 THEN 'CLOSE_NEAR_HIGH' END,
                CASE WHEN clv <= -0.7 THEN 'CLOSE_NEAR_LOW' END,
                CASE WHEN delivery_delta >= 5 THEN 'DELIVERY_ABOVE_20D_AVERAGE' END,
                CASE WHEN obv_change_5 > 0 THEN 'OBV_RISING' END,
                CASE WHEN cmf20 > 0 THEN 'POSITIVE_CHAIKIN_MONEY_FLOW' END,
                CASE WHEN ret20 > 0 THEN 'POSITIVE_20D_RETURN' END
            ]::text[], NULL)),
            jsonb_build_object(
                'has_20d_volume_baseline', avg_volume_20 IS NOT NULL,
                'has_20d_delivery_baseline', avg_delivery_20 IS NOT NULL,
                'has_20d_price_history', close_20 IS NOT NULL,
                'has_vwap_proxy', avg_price IS NOT NULL,
                'low_liquidity', coalesce(turnover_lacs,0) < 25
            ),
            $2
        FROM scored
        WHERE close_price IS NOT NULL AND total_traded_qty IS NOT NULL
        ON CONFLICT (trade_date, symbol) DO UPDATE SET
            close_price=EXCLUDED.close_price, volume=EXCLUDED.volume,
            turnover_lacs=EXCLUDED.turnover_lacs, delivery_qty=EXCLUDED.delivery_qty,
            delivery_pct=EXCLUDED.delivery_pct, avg_volume_20=EXCLUDED.avg_volume_20,
            relative_volume=EXCLUDED.relative_volume, avg_turnover_20=EXCLUDED.avg_turnover_20,
            relative_turnover=EXCLUDED.relative_turnover,
            close_location_value=EXCLUDED.close_location_value, obv=EXCLUDED.obv,
            obv_change_5=EXCLUDED.obv_change_5, ad_line=EXCLUDED.ad_line,
            cmf_20=EXCLUDED.cmf_20,
            atr_14=EXCLUDED.atr_14, mfi_14=EXCLUDED.mfi_14,
            vwap_deviation_pct=EXCLUDED.vwap_deviation_pct,
            return_5d_pct=EXCLUDED.return_5d_pct, return_20d_pct=EXCLUDED.return_20d_pct,
            delivery_pct_avg_20=EXCLUDED.delivery_pct_avg_20,
            delivery_pct_delta=EXCLUDED.delivery_pct_delta,
            accumulation_score=EXCLUDED.accumulation_score,
            distribution_score=EXCLUDED.distribution_score, signal=EXCLUDED.signal,
            reason_codes=EXCLUDED.reason_codes, data_quality=EXCLUDED.data_quality,
            strategy_version=EXCLUDED.strategy_version, computed_at=now()
    """, trade_date, STRATEGY_VERSION)

    summary = await conn.fetchrow("""
        SELECT count(*) AS feature_count,
               count(*) FILTER (WHERE signal IN ('ACCUMULATION','ACCUMULATION_WATCH')) AS accumulation_count,
               count(*) FILTER (WHERE signal IN ('DISTRIBUTION','DISTRIBUTION_WATCH')) AS distribution_count
        FROM swing_scanner_features WHERE trade_date=$1
    """, trade_date)
    return dict(summary)
