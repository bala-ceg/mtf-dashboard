"""PostgreSQL smoke test for the NIFTY Total Market swing SQL pipeline.

Uses a disposable CI database. It seeds two constituents and 35 synthetic sessions,
runs the actual feature service SQL, and asserts benchmark-relative strength is present.
"""
import asyncio
from datetime import date, timedelta
import os

import asyncpg

from backend.app.services.swing_scanner import compute_for_date


async def main():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "mtf_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )
    start = date(2026, 1, 1)
    end = start + timedelta(days=34)
    try:
        async with conn.transaction():
            for symbol in ("TESTA", "TESTB"):
                await conn.execute(
                    """
                    INSERT INTO nifty_index_constituents
                    (index_name, company_name, industry, symbol, series, isin_code)
                    VALUES ('NIFTY_TOTAL_MARKET', $1, 'Testing', $2, 'EQ', $3)
                    ON CONFLICT (index_name, symbol) DO NOTHING
                    """,
                    symbol, symbol, f"INE{symbol}00001",
                )
                await conn.execute(
                    """
                    INSERT INTO nifty_index_constituent_snapshots
                    (snapshot_date, index_name, company_name, industry, symbol, series, isin_code)
                    VALUES ($1, 'NIFTY_TOTAL_MARKET', $2, 'Testing', $3, 'EQ', $4)
                    ON CONFLICT (snapshot_date, index_name, symbol) DO NOTHING
                    """,
                    start - timedelta(days=1), symbol, symbol, f"INE{symbol}00001",
                )

            for n in range(35):
                trade_date = start + timedelta(days=n)
                index_close = 1000 + 3 * n
                await conn.execute(
                    """
                    INSERT INTO nifty_index_daily
                    (index_name, trade_date, open_value, high_value, low_value, close_value)
                    VALUES ('NIFTY_TOTAL_MARKET', $1, $2, $3, $4, $5)
                    ON CONFLICT (index_name, trade_date) DO UPDATE SET close_value=EXCLUDED.close_value
                    """,
                    trade_date, index_close - 1, index_close + 2, index_close - 2, index_close,
                )
                for symbol, base in (("TESTA", 100), ("TESTB", 200)):
                    close = base + n * (1.8 if symbol == "TESTA" else 0.8)
                    volume = 30000 + n * 100
                    await conn.execute(
                        """
                        INSERT INTO cash_market_daily
                        (trade_date, symbol, series, open_price, high_price, low_price,
                         close_price, avg_price, last_price, prev_close, total_traded_qty,
                         turnover_lacs, no_of_trades, deliv_qty, deliv_per)
                        VALUES ($1,$2,'EQ',$3,$4,$5,$6,$7,$6,$8,$9,$10,1000,$11,45)
                        ON CONFLICT (trade_date, symbol, series) DO NOTHING
                        """,
                        trade_date, symbol, close - 0.3, close + 2, close - 1,
                        close, close - 0.2, close - 1.2, volume,
                        close * volume / 100000, int(volume * 0.45),
                    )

        summary = await compute_for_date(conn, end)
        assert summary["feature_count"] == 2, summary

        rows = await conn.fetch(
            """
            SELECT symbol, relative_strength_20d_pct, accumulation_score,
                   distribution_score, signal
            FROM swing_scanner_features
            WHERE trade_date=$1
            ORDER BY symbol
            """,
            end,
        )
        assert len(rows) == 2, rows
        assert all(row["relative_strength_20d_pct"] is not None for row in rows), rows
        assert all(0 <= row["accumulation_score"] <= 100 for row in rows), rows
        assert all(0 <= row["distribution_score"] <= 100 for row in rows), rows
        print("Swing scanner PostgreSQL smoke test passed:", [dict(r) for r in rows])
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
