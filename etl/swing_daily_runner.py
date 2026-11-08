"""End-of-day NIFTY Total Market swing scanner pipeline.

Downloads/uses the latest NSE full security Bhavcopy, refreshes current index
membership, loads EQ rows into the dedicated cash table, then computes signals.
Run from the repository root after the NSE cash market close.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2

from config import DB_CONFIG
from etl.download_bhavcopy import get_nse_session, download_and_process_bhavcopy
from etl.download_nifty_indices import download_nifty_indices
from etl.load_nifty_indices import load_index_constituents
from etl.load_cash_bhavcopy import load_file, DATA_DIR
from backend.app.database import init_db_pool, close_db_pool, get_db
from backend.app.services.swing_scanner import compute_for_date, STRATEGY_VERSION

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "sql" / "20_swing_scanner_schema.sql"


def apply_migration() -> None:
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(MIGRATION.read_text(encoding="utf-8"))


def refresh_universe() -> int:
    files = download_nifty_indices()
    target = ROOT / "data" / "nifty_indices" / "nifty_total_market.csv"
    if not target.exists():
        raise RuntimeError(
            "Could not obtain NIFTY Total Market constituent CSV. "
            "Confirm NSE Indices availability and retry."
        )
    load_index_constituents()
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(DISTINCT upper(symbol))
                FROM nifty_index_constituents
                WHERE upper(replace(index_name, ' ', '_')) IN
                      ('NIFTY_TOTAL_MARKET','NIFTY_TOTALMARKET')
            """)
            count = cur.fetchone()[0]
    if count < 500:
        raise RuntimeError(f"NIFTY Total Market universe unexpectedly small: {count}")
    print(f"Loaded {count} current NIFTY Total Market constituents from {len(files)} index files")
    return count


def fetch_latest_bhavcopy():
    ist_today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    session = get_nse_session()
    for offset in range(0, 11):
        candidate = ist_today - timedelta(days=offset)
        path = DATA_DIR / f"sec_bhavdata_full_{candidate:%d%m%Y}.csv"
        if path.exists():
            return candidate, path
        if candidate.weekday() >= 5:
            continue
        if download_and_process_bhavcopy(session, datetime.combine(candidate, datetime.min.time())):
            if path.exists():
                return candidate, path
    raise RuntimeError("No recent NSE full security Bhavcopy found in the last 10 calendar days")


async def compute(trade_date):
    await init_db_pool()
    try:
        async with get_db() as conn:
            result = await compute_for_date(conn, trade_date)
            return result
    finally:
        await close_db_pool()


def main():
    apply_migration()
    universe_count = refresh_universe()
    trade_date, bhavcopy_path = fetch_latest_bhavcopy()

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO swing_scanner_runs (trade_date, status, universe_count, strategy_version)
                VALUES (%s, 'running', %s, %s) RETURNING id
            """, (trade_date, universe_count, STRATEGY_VERSION))
            run_id = cur.fetchone()[0]
            conn.commit()
        try:
            loaded = load_file(bhavcopy_path, conn)
            result = asyncio.run(compute(trade_date))
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE swing_scanner_runs
                    SET status='completed', completed_at=now(), processed_count=%s,
                        feature_count=%s
                    WHERE id=%s
                """, (loaded, result["feature_count"], run_id))
                conn.commit()
            print(
                f"Swing scanner completed for {trade_date}: "
                f"{result['feature_count']} features, "
                f"{result['accumulation_count']} accumulation candidates, "
                f"{result['distribution_count']} distribution candidates."
            )
        except Exception as exc:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE swing_scanner_runs
                    SET status='failed', completed_at=now(), error_message=%s
                    WHERE id=%s
                """, (str(exc)[:2000], run_id))
                conn.commit()
            raise


if __name__ == "__main__":
    main()
