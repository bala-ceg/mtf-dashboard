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
                (SELECT count(*) FROM cash_market_daily
                 WHERE trade_date=(SELECT max(trade_date) FROM cash_market_daily)
                   AND series='EQ') AS latest_cash_eq_rows
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
):
    async with get_db() as conn:
        effective_date = trade_date or await conn.fetchval(
            "SELECT max(trade_date) FROM swing_scanner_features"
        )
        if not effective_date:
            raise HTTPException(
                status_code=404,
                detail="No swing scanner features yet. Apply migration, load NIFTY Total Market constituents and cash Bhavcopy, then run etl/compute_swing_scanner.py."
            )

        params: list[Any] = [effective_date, min_score]
        signal_filter = ""
        if signal:
            params.append(signal)
            signal_filter = f"AND f.signal = ${len(params)}"
        params.append(limit)
        limit_parameter = len(params)

        rows = await conn.fetch(f"""
            SELECT f.*, sm.company_name, sm.sector, sm.market_cap_cr
            FROM swing_scanner_features f
            LEFT JOIN stocks_master sm ON upper(sm.symbol)=upper(f.symbol)
            WHERE f.trade_date=$1
              AND greatest(f.accumulation_score, f.distribution_score) >= $2
              {signal_filter}
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
