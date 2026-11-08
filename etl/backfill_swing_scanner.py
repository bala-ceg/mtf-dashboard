"""Backfill cash Bhavcopy and compute historical swing features.

Run after the schema migration and after loading NIFTY_TOTAL_MARKET constituents.
Current constituent membership is used for all dates; results are exploratory
until point-in-time index membership is captured.
"""
import argparse
import asyncio
from pathlib import Path

import psycopg2

from config import DB_CONFIG
from etl.load_cash_bhavcopy import load_file, DATA_DIR
from backend.app.database import init_db_pool, close_db_pool, get_db
from backend.app.services.swing_scanner import compute_for_date, STRATEGY_VERSION

ROOT = Path(__file__).resolve().parent.parent


def apply_migration():
    migration = ROOT / "sql" / "20_swing_scanner_schema.sql"
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(migration.read_text(encoding="utf-8"))


def load_history(directory: Path, start_date=None, end_date=None):
    files = sorted(directory.glob("sec_bhavdata_full_*.csv"))
    if start_date:
        files = [p for p in files if p.stem.endswith(
            __import__("datetime").datetime.strptime(p.stem.split("_")[-1], "%d%m%Y").strftime("%d%m%Y")
        ) and __import__("datetime").datetime.strptime(p.stem.split("_")[-1], "%d%m%Y").date() >= start_date]
    if end_date:
        from datetime import datetime
        files = [p for p in files if datetime.strptime(p.stem.split("_")[-1], "%d%m%Y").date() <= end_date]
    if not files:
        raise RuntimeError(f"No Bhavcopy CSV files available under {directory}")

    with psycopg2.connect(**DB_CONFIG) as conn:
        total = 0
        for path in files:
            total += load_file(path, conn)
    print(f"Loaded {total} NIFTY Total Market rows from {len(files)} files")


async def compute_history(start_date=None, end_date=None):
    await init_db_pool()
    try:
        async with get_db() as conn:
            dates = await conn.fetch("""
                SELECT DISTINCT trade_date
                FROM cash_market_daily
                WHERE ($1::date IS NULL OR trade_date >= $1)
                  AND ($2::date IS NULL OR trade_date <= $2)
                ORDER BY trade_date
            """, start_date, end_date)
            for item in dates:
                trade_date = item["trade_date"]
                result = await compute_for_date(conn, trade_date)
                print(
                    f"{trade_date}: {result['feature_count']} features; "
                    f"accumulation={result['accumulation_count']}; "
                    f"distribution={result['distribution_count']}"
                )
    finally:
        await close_db_pool()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    args = parser.parse_args()
    from datetime import date

    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None
    apply_migration()
    load_history(DATA_DIR, start_date, end_date)
    asyncio.run(compute_history(start_date, end_date))


if __name__ == "__main__":
    main()
