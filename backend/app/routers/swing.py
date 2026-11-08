from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..database import get_db

router = APIRouter(prefix="/swing", tags=["Swing Order Flow"])


@router.get("/status")
async def scanner_status():
    async with get_db() as conn:
        row = await conn.fetchrow("""
            SELECT
                (SELECT count(DISTINCT upper(symbol))
                 FROM nifty_index_constituents
                 WHERE upper(replace(index_name, ' ', '_')) IN
                       ('NIFTY_TOTAL_MARKET','NIFTY_TOTALMARKET')) AS universe_count,
                (SELECT max(trade_date) FROM cash_market_daily) AS latest_bhavcopy_date,
                (SELECT max(trade_date) FROM swing_scanner_features) AS latest_feature_date,
                (SELECT count(*) FROM cash_market_daily c
                 JOIN nifty_index_constituents i ON upper(i.symbol)=upper(c.symbol)
                 WHERE upper(replace(i.index_name, ' ', '_')) IN
                       ('NIFTY_TOTAL_MARKET','NIFTY_TOTALMARKET')
                   AND c.trade_date=(SELECT max(trade_date) FROM cash_market_daily)
                   AND c.series='EQ') AS latest_universe_rows
        """)
    return dict(row)


@router.get("/scanner")
async def get_scanner(
    trade_date: date | None = None,
    signal: str | None = Query(
        None,
        pattern="^(ACCUMULATION|ACCUMULATION_WATCH|DISTRIBUTION|DISTRIBUTION_WATCH|NEUTRAL)$"
    ),
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(100, ge=1, le=750),
    include_illiquid: bool = False,
):
    async with get_db() as conn:
        effective_date = trade_date or await conn.fetchval(
            "SELECT max(trade_date) FROM swing_scanner_features"
        )
        if not effective_date:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No swing scanner features yet. Apply the migration, load the "
                    "NIFTY Total Market constituents and cash Bhavcopy history, then "
                    "run python -m etl.swing_daily_runner."
                )
            )

        params: list[Any] = [effective_date, min_score]
        signal_filter = ""
        if signal:
            params.append(signal)
            signal_filter = f"AND f.signal = ${len(params)}"
        params.append(include_illiquid)
        liquidity_filter = f"""
            AND (${len(params)}::boolean OR
                 coalesce((f.data_quality->>'low_liquidity')::boolean, false) = false)
        """
        params.append(limit)
        limit_parameter = len(params)

        rows = await conn.fetch(f"""
            SELECT f.*, sm.company_name, sm.sector, sm.market_cap_cr
            FROM swing_scanner_features f
            LEFT JOIN stocks_master sm ON upper(sm.symbol)=upper(f.symbol)
            WHERE f.trade_date=$1
              AND greatest(f.accumulation_score, f.distribution_score) >= $2
              {signal_filter}
              {liquidity_filter}
            ORDER BY greatest(f.accumulation_score, f.distribution_score) DESC,
                     f.relative_volume DESC NULLS LAST
            LIMIT ${limit_parameter}
        """, *params)
        return {
            "trade_date": effective_date,
            "count": len(rows),
            "results": [dict(row) for row in rows]
        }


@router.get("/sectors")
async def get_sector_flow(trade_date: date | None = None):
    async with get_db() as conn:
        effective_date = trade_date or await conn.fetchval(
            "SELECT max(trade_date) FROM swing_scanner_features"
        )
        if not effective_date:
            return {"trade_date": None, "results": []}
        rows = await conn.fetch("""
            SELECT coalesce(sm.sector, 'Unclassified') AS sector,
                   count(*) AS stocks,
                   round(avg(f.accumulation_score),1) AS avg_accumulation_score,
                   round(avg(f.distribution_score),1) AS avg_distribution_score,
                   count(*) FILTER (WHERE f.signal IN
                       ('ACCUMULATION','ACCUMULATION_WATCH')) AS accumulation_stocks,
                   count(*) FILTER (WHERE f.signal IN
                       ('DISTRIBUTION','DISTRIBUTION_WATCH')) AS distribution_stocks
            FROM swing_scanner_features f
            LEFT JOIN stocks_master sm ON upper(sm.symbol)=upper(f.symbol)
            WHERE f.trade_date=$1
              AND coalesce((f.data_quality->>'low_liquidity')::boolean, false) = false
            GROUP BY 1 ORDER BY avg_accumulation_score DESC NULLS LAST
        """, effective_date)
        return {"trade_date": effective_date, "results": [dict(row) for row in rows]}


@router.get("/stock/{symbol}/history")
async def get_stock_signal_history(
    symbol: str,
    limit: int = Query(60, ge=1, le=250)
):
    async with get_db() as conn:
        rows = await conn.fetch("""
            SELECT f.*, sm.company_name, sm.sector
            FROM swing_scanner_features f
            LEFT JOIN stocks_master sm ON upper(sm.symbol)=upper(f.symbol)
            WHERE upper(f.symbol)=upper($1)
            ORDER BY f.trade_date DESC LIMIT $2
        """, symbol, limit)
        if not rows:
            raise HTTPException(status_code=404, detail=f"No swing history found for {symbol}")
        return [dict(row) for row in rows]


@router.get("/performance")
async def get_signal_performance(
    start_date: date | None = None,
    end_date: date | None = None,
    signal: str = Query(
        "ACCUMULATION",
        pattern="^(ACCUMULATION|ACCUMULATION_WATCH|DISTRIBUTION|DISTRIBUTION_WATCH)$"
    ),
):
    """Exploratory forward-close returns; no costs or point-in-time universe yet."""
    async with get_db() as conn:
        rows = await conn.fetch("""
            WITH prices AS (
                SELECT symbol, trade_date, close_price,
                    lead(close_price, 5) OVER (PARTITION BY symbol ORDER BY trade_date) AS close_5d,
                    lead(close_price, 10) OVER (PARTITION BY symbol ORDER BY trade_date) AS close_10d,
                    lead(close_price, 20) OVER (PARTITION BY symbol ORDER BY trade_date) AS close_20d
                FROM cash_market_daily
                WHERE series='EQ'
            ),
            observations AS (
                SELECT f.symbol, f.signal, f.trade_date,
                    CASE WHEN p.close_5d > 0 THEN (p.close_5d/p.close_price-1)*100 END AS ret_5d,
                    CASE WHEN p.close_10d > 0 THEN (p.close_10d/p.close_price-1)*100 END AS ret_10d,
                    CASE WHEN p.close_20d > 0 THEN (p.close_20d/p.close_price-1)*100 END AS ret_20d
                FROM swing_scanner_features f
                JOIN prices p ON p.symbol=f.symbol AND p.trade_date=f.trade_date
                WHERE f.signal=$1
                  AND ($2::date IS NULL OR f.trade_date >= $2)
                  AND ($3::date IS NULL OR f.trade_date <= $3)
                  AND coalesce((f.data_quality->>'low_liquidity')::boolean, false)=false
            )
            SELECT count(*) AS signal_count,
                   count(ret_5d) AS observations_5d,
                   round(avg(ret_5d)::numeric,2) AS avg_return_5d_pct,
                   round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ret_5d)::numeric,2) AS median_return_5d_pct,
                   round(100.0*count(*) FILTER (WHERE ret_5d>0)/NULLIF(count(ret_5d),0),1) AS win_rate_5d_pct,
                   count(ret_10d) AS observations_10d,
                   round(avg(ret_10d)::numeric,2) AS avg_return_10d_pct,
                   round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ret_10d)::numeric,2) AS median_return_10d_pct,
                   round(100.0*count(*) FILTER (WHERE ret_10d>0)/NULLIF(count(ret_10d),0),1) AS win_rate_10d_pct,
                   count(ret_20d) AS observations_20d,
                   round(avg(ret_20d)::numeric,2) AS avg_return_20d_pct,
                   round(percentile_cont(0.5) WITHIN GROUP (ORDER BY ret_20d)::numeric,2) AS median_return_20d_pct,
                   round(100.0*count(*) FILTER (WHERE ret_20d>0)/NULLIF(count(ret_20d),0),1) AS win_rate_20d_pct
            FROM observations
        """, signal, start_date, end_date)
        return {"signal": signal, **dict(rows[0])}
