"""Backfill cash Bhavcopy and compute historical swing features.

Run after the schema migration and after loading NIFTY_TOTAL_MARKET constituents.
Current constituent membership is used for all dates; results are exploratory
until point-in-time index membership is captured.
"""
import argparse
import asyncio
from datetime import datetime, date
from pathlib import Path

import psycopg2

from config import DB_CONFIG
from etl.load_cash_bhavcopy import load_file, DATA_DIR
from backend.app.database import init_db_pool, close_db_pool, get_db
from backend.app.services.swing_scanner import compute_range, STRATEGY_VERSION

ROOT = Path(__file__).resolve().parent.parent


def apply_migration():
    migration = ROOT / "sql" / "20_swing_scanner_schema.sql"
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(migration.read_text(encoding="utf-8"))


def load_history(directory: Path, start_date=None, end_date=None):
    files = sorted(directory.glob("sec_bhavdata_full_*.csv"))
    def file_date(path):
        return datetime.strptime(path.stem.split("_")[-1], "%d%m%Y").date()

    if start_date:
        files = [path for path in files if file_date(path) >= start_date]
    if end_date:
        files = [path for path in files if file_date(path) <= end_date]
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
            first_date = start_date or await conn.fetchval(
                "SELECT min(trade_date) FROM cash_market_daily"
            )
            last_date = end_date or await conn.fetchval(
                "SELECT max(trade_date) FROM cash_market_daily"
            )
            if not first_date or not last_date:
                raise RuntimeError("cash_market_daily contains no data to calculate")
            result = await compute_range(conn, first_date, last_date)
            print(
                f"Computed {result['feature_count']} daily stock features from "
                f"{first_date} through {last_date}; "
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

    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None
    apply_migration()
    load_history(DATA_DIR, start_date, end_date)
    asyncio.run(compute_history(start_date, end_date))


if __name__ == "__main__":
    main()
