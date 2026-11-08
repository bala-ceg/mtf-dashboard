"""Daily swing accumulation/distribution feature calculation.

Uses daily OHLCV and delivery participation. This is an accumulation proxy,
not true trade-side order flow and not evidence of institutional identity.
"""
from datetime import date
import asyncpg

STRATEGY_VERSION = "swing-v1"


async def compute_range(conn: asyncpg.Connection, start_date: date, end_date: date) -> dict:
    # Use the latest captured constituent snapshot on or before each session.
    # Before the first snapshot exists, fall back to the current legacy list;
    # those earlier backfill dates still have survivorship bias.
    await conn.execute("""
        WITH calendar AS (
            SELECT DISTINCT trade_date
            FROM cash_market_daily
            WHERE trade_date <= $2
        ),
        snapshot_dates AS (
            SELECT d.trade_date,
                   (SELECT max(s.snapshot_date)
                    FROM nifty_index_constituent_snapshots s
                    WHERE upper(replace(s.index_name, ' ', '_')) IN
                          ('NIFTY_TOTAL_MARKET', 'NIFTY_TOTALMARKET')
                      AND s.snapshot_date <= d.trade_date) AS snapshot_date
            FROM calendar d
        ),
        universe AS (
            SELECT d.trade_date, upper(s.symbol) AS symbol
            FROM snapshot_dates d
            JOIN nifty_index_constituent_snapshots s
              ON s.snapshot_date = d.snapshot_date
             AND upper(replace(s.index_name, ' ', '_')) IN
                 ('NIFTY_TOTAL_MARKET', 'NIFTY_TOTALMARKET')
            WHERE d.snapshot_date IS NOT NULL
            UNION ALL
            SELECT d.trade_date, upper(i.symbol) AS symbol
            FROM snapshot_dates d
            JOIN nifty_index_constituents i
              ON upper(replace(i.index_name, ' ', '_')) IN
                 ('NIFTY_TOTAL_MARKET', 'NIFTY_TOTALMARKET')
            WHERE d.snapshot_date IS NULL
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
            JOIN universe u
              ON u.trade_date = c.trade_date
             AND u.symbol = upper(c.symbol)
            WHERE c.series = 'EQ' AND c.trade_date <= $2
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
                obv - lag(obv, 5) OVER (PARTITION BY symbol ORDER BY trade_date) AS obv_change_5
            FROM money_flow h
        ),
        benchmark AS (
            SELECT trade_date,
                   (close_value / NULLIF(lag(close_value, 20) OVER (ORDER BY trade_date), 0) - 1) * 100
                       AS benchmark_return_20d_pct
            FROM nifty_index_daily
            WHERE upper(replace(index_name, ' ', '_')) IN
                  ('NIFTY_TOTAL_MARKET', 'NIFTY_TOTALMARKET')
              AND trade_date <= $2
        ),
        features AS (
            SELECT latest.*, b.benchmark_return_20d_pct,
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
                CASE WHEN close_20 > 0 AND b.benchmark_return_20d_pct IS NOT NULL
                    THEN ((close_price/close_20-1)*100) - b.benchmark_return_20d_pct
                END AS relative_strength_20d_pct,
                CASE WHEN mfi_obs_14 = 14 AND coalesce(negative_mf_14,0) = 0 THEN 100
                     WHEN mfi_obs_14 = 14 AND coalesce(positive_mf_14,0) = 0 THEN 0
                     WHEN mfi_obs_14 = 14
                     THEN 100 - (100 / (1 + positive_mf_14 / NULLIF(negative_mf_14,0)))
                END AS mfi14
            FROM latest
            LEFT JOIN benchmark b ON b.trade_date = latest.trade_date
        ),
        scored AS (
            SELECT *,
                (CASE WHEN rvol >= 1.5 THEN 12 WHEN rvol >= 1.2 THEN 6 ELSE 0 END +
                 CASE WHEN rvalue >= 1.5 THEN 8 WHEN rvalue >= 1.2 THEN 4 ELSE 0 END +
                 CASE WHEN clv >= 0.7 THEN 12 WHEN clv >= 0.4 THEN 6 ELSE 0 END +
                 CASE WHEN close_price > prev_close THEN 8 ELSE 0 END +
                 CASE WHEN close_20 IS NOT NULL AND close_price > close_20 THEN 8 ELSE 0 END +
                 CASE WHEN delivery_delta >= 10 THEN 12 WHEN delivery_delta >= 5 THEN 6 ELSE 0 END +
                 CASE WHEN ret20 > 0 THEN 8 ELSE 0 END +
                 CASE WHEN obv_change_5 > 0 THEN 8 ELSE 0 END +
                 CASE WHEN cmf20 > 0 THEN 4 ELSE 0 END +
                 CASE WHEN relative_strength_20d_pct >= 2 THEN 10
                      WHEN relative_strength_20d_pct > 0 THEN 5 ELSE 0 END +
                 CASE WHEN turnover_lacs >= 100 THEN 10
                      WHEN turnover_lacs >= 25 THEN 5 ELSE 0 END) AS acc_score,
                (CASE WHEN rvol >= 1.5 THEN 12 WHEN rvol >= 1.2 THEN 6 ELSE 0 END +
                 CASE WHEN rvalue >= 1.5 THEN 8 WHEN rvalue >= 1.2 THEN 4 ELSE 0 END +
                 CASE WHEN clv <= -0.7 THEN 12 WHEN clv <= -0.4 THEN 6 ELSE 0 END +
                 CASE WHEN close_price < prev_close THEN 8 ELSE 0 END +
                 CASE WHEN close_20 IS NOT NULL AND close_price < close_20 THEN 8 ELSE 0 END +
                 CASE WHEN delivery_delta <= -10 THEN 12 WHEN delivery_delta <= -5 THEN 6 ELSE 0 END +
                 CASE WHEN ret20 < 0 THEN 8 ELSE 0 END +
                 CASE WHEN obv_change_5 < 0 THEN 8 ELSE 0 END +
                 CASE WHEN cmf20 < 0 THEN 4 ELSE 0 END +
                 CASE WHEN relative_strength_20d_pct <= -2 THEN 10
                      WHEN relative_strength_20d_pct < 0 THEN 5 ELSE 0 END +
                 CASE WHEN turnover_lacs >= 100 THEN 10
                      WHEN turnover_lacs >= 25 THEN 5 ELSE 0 END) AS dist_score
            FROM features
        ),
        scored_detail AS (
            SELECT scored.*,
                jsonb_build_object(
                    'weights', jsonb_build_object(
                        'relative_volume', 12, 'relative_turnover', 8,
                        'close_location', 12, 'daily_price_direction', 8,
                        '20d_price_trend', 8, 'delivery_participation', 12,
                        '20d_momentum', 8, 'obv_5d', 8,
                        'chaikin_money_flow', 4, 'benchmark_relative_strength', 10,
                        'liquidity', 10
                    ),
                    'accumulation', jsonb_build_object(
                        'relative_volume', CASE WHEN rvol >= 1.5 THEN 12 WHEN rvol >= 1.2 THEN 6 ELSE 0 END,
                        'relative_turnover', CASE WHEN rvalue >= 1.5 THEN 8 WHEN rvalue >= 1.2 THEN 4 ELSE 0 END,
                        'close_location', CASE WHEN clv >= 0.7 THEN 12 WHEN clv >= 0.4 THEN 6 ELSE 0 END,
                        'daily_price_direction', CASE WHEN close_price > prev_close THEN 8 ELSE 0 END,
                        '20d_price_trend', CASE WHEN close_20 IS NOT NULL AND close_price > close_20 THEN 8 ELSE 0 END,
                        'delivery_participation', CASE WHEN delivery_delta >= 10 THEN 12 WHEN delivery_delta >= 5 THEN 6 ELSE 0 END,
                        '20d_momentum', CASE WHEN ret20 > 0 THEN 8 ELSE 0 END,
                        'obv_5d', CASE WHEN obv_change_5 > 0 THEN 8 ELSE 0 END,
                        'chaikin_money_flow', CASE WHEN cmf20 > 0 THEN 4 ELSE 0 END,
                        'benchmark_relative_strength', CASE WHEN relative_strength_20d_pct >= 2 THEN 10 WHEN relative_strength_20d_pct > 0 THEN 5 ELSE 0 END,
                        'liquidity', CASE WHEN turnover_lacs >= 100 THEN 10 WHEN turnover_lacs >= 25 THEN 5 ELSE 0 END,
                        'total', least(100, acc_score)
                    ),
                    'distribution', jsonb_build_object(
                        'relative_volume', CASE WHEN rvol >= 1.5 THEN 12 WHEN rvol >= 1.2 THEN 6 ELSE 0 END,
                        'relative_turnover', CASE WHEN rvalue >= 1.5 THEN 8 WHEN rvalue >= 1.2 THEN 4 ELSE 0 END,
                        'close_location', CASE WHEN clv <= -0.7 THEN 12 WHEN clv <= -0.4 THEN 6 ELSE 0 END,
                        'daily_price_direction', CASE WHEN close_price < prev_close THEN 8 ELSE 0 END,
                        '20d_price_trend', CASE WHEN close_20 IS NOT NULL AND close_price < close_20 THEN 8 ELSE 0 END,
                        'delivery_participation', CASE WHEN delivery_delta <= -10 THEN 12 WHEN delivery_delta <= -5 THEN 6 ELSE 0 END,
                        '20d_momentum', CASE WHEN ret20 < 0 THEN 8 ELSE 0 END,
                        'obv_5d', CASE WHEN obv_change_5 < 0 THEN 8 ELSE 0 END,
                        'chaikin_money_flow', CASE WHEN cmf20 < 0 THEN 4 ELSE 0 END,
                        'benchmark_relative_strength', CASE WHEN relative_strength_20d_pct <= -2 THEN 10 WHEN relative_strength_20d_pct < 0 THEN 5 ELSE 0 END,
                        'liquidity', CASE WHEN turnover_lacs >= 100 THEN 10 WHEN turnover_lacs >= 25 THEN 5 ELSE 0 END,
                        'total', least(100, dist_score)
                    )
                ) AS score_breakdown
            FROM scored
        )
        INSERT INTO swing_scanner_features (
            trade_date, symbol, close_price, volume, turnover_lacs, delivery_qty,
            delivery_pct, avg_volume_20, relative_volume, avg_turnover_20,
            relative_turnover, close_location_value, obv, obv_change_5, ad_line, cmf_20,
            atr_14, mfi_14, vwap_deviation_pct, return_5d_pct, return_20d_pct,
            relative_strength_20d_pct, delivery_pct_avg_20, delivery_pct_delta, accumulation_score,
            distribution_score, signal, reason_codes, score_breakdown, data_quality, strategy_version
        )
        SELECT trade_date, symbol, close_price, total_traded_qty, turnover_lacs, deliv_qty,
            deliv_per, avg_volume_20, rvol, avg_turnover_20, rvalue, clv, obv, obv_change_5, ad_line,
            cmf20, atr_14, mfi14, vwap_deviation, ret5, ret20,
            relative_strength_20d_pct, avg_delivery_20, delivery_delta, least(100, acc_score),
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
                CASE WHEN delivery_delta <= -5 THEN 'DELIVERY_BELOW_20D_AVERAGE' END,
                CASE WHEN obv_change_5 > 0 THEN 'OBV_RISING' END,
                CASE WHEN obv_change_5 < 0 THEN 'OBV_FALLING' END,
                CASE WHEN cmf20 > 0 THEN 'POSITIVE_CHAIKIN_MONEY_FLOW' END,
                CASE WHEN ret20 > 0 THEN 'POSITIVE_20D_RETURN' END,
                CASE WHEN relative_strength_20d_pct > 0 THEN 'OUTPERFORMING_NIFTY_TOTAL_MARKET' END,
                CASE WHEN relative_strength_20d_pct < 0 THEN 'UNDERPERFORMING_NIFTY_TOTAL_MARKET' END,
                CASE WHEN turnover_lacs >= 25 THEN 'MINIMUM_LIQUIDITY_MET' END
            ]::text[], NULL)),
            score_breakdown,
            jsonb_build_object(
                'has_20d_volume_baseline', avg_volume_20 IS NOT NULL,
                'has_20d_delivery_baseline', avg_delivery_20 IS NOT NULL,
                'has_20d_price_history', close_20 IS NOT NULL,
                'has_vwap_proxy', avg_price IS NOT NULL,
                'has_benchmark_20d', benchmark_return_20d_pct IS NOT NULL,
                'low_liquidity', coalesce(turnover_lacs,0) < 25
            ),
            $3
        FROM scored_detail
        WHERE close_price IS NOT NULL AND total_traded_qty IS NOT NULL
          AND trade_date BETWEEN $1 AND $2
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
            relative_strength_20d_pct=EXCLUDED.relative_strength_20d_pct,
            delivery_pct_avg_20=EXCLUDED.delivery_pct_avg_20,
            delivery_pct_delta=EXCLUDED.delivery_pct_delta,
            accumulation_score=EXCLUDED.accumulation_score,
            distribution_score=EXCLUDED.distribution_score, signal=EXCLUDED.signal,
            reason_codes=EXCLUDED.reason_codes, data_quality=EXCLUDED.data_quality,
            score_breakdown=EXCLUDED.score_breakdown,
            strategy_version=EXCLUDED.strategy_version, computed_at=now()
    """, start_date, end_date, STRATEGY_VERSION)

    summary = await conn.fetchrow("""
        SELECT count(*) AS feature_count,
               count(*) FILTER (WHERE signal IN ('ACCUMULATION','ACCUMULATION_WATCH')) AS accumulation_count,
               count(*) FILTER (WHERE signal IN ('DISTRIBUTION','DISTRIBUTION_WATCH')) AS distribution_count
        FROM swing_scanner_features WHERE trade_date BETWEEN $1 AND $2
    """, start_date, end_date)
    return dict(summary)


async def compute_for_date(conn: asyncpg.Connection, trade_date: date) -> dict:
    """Compute one session while retaining all preceding history for rolling features."""
    return await compute_range(conn, trade_date, trade_date)
