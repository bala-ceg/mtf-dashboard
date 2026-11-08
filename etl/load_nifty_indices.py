"""Load NIFTY index members and retain dated membership snapshots."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg2

from config import DB_CONFIG

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "data" / "nifty_indices"
INDEX_MAPPING = {
    "nifty50.csv": "NIFTY50",
    "nifty_next50.csv": "NIFTY_NEXT50",
    "nifty_smallcap50.csv": "NIFTY_SMALLCAP50",
    "nifty_midcap50.csv": "NIFTY_MIDCAP50",
    "nifty_total_market.csv": "NIFTY_TOTAL_MARKET",
}


def _clean(value):
    if pd.isna(value):
        return None
    return str(value).strip()


def _ensure_schema(cursor):
    for relative_path in (
        "sql/15_nifty_index_constituents.sql",
        "sql/20_swing_scanner_schema.sql",
    ):
        sql_path = ROOT / relative_path
        if sql_path.exists():
            cursor.execute(sql_path.read_text(encoding="utf-8"))


def load_index_constituents():
    """Refresh current constituents and record the downloaded membership snapshot.

    Snapshot date is the date the official list was captured in Asia/Kolkata.
    It is not backdated to a review's effective date unless the source provides
    that date; pre-snapshot backfill therefore continues to use current membership.
    """
    if not INDEX_DIR.exists():
        raise FileNotFoundError(
            f"{INDEX_DIR} does not exist. Run python -m etl.download_nifty_indices first."
        )

    snapshot_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    conn = psycopg2.connect(**DB_CONFIG)
    total_loaded = 0
    try:
        with conn:
            with conn.cursor() as cursor:
                _ensure_schema(cursor)

                for csv_name, index_name in INDEX_MAPPING.items():
                    file_path = INDEX_DIR / csv_name
                    if not file_path.exists():
                        print(f"Skipping {csv_name}: file not found")
                        continue

                    frame = pd.read_csv(file_path, encoding="utf-8-sig")
                    frame.columns = [str(c).strip().lower() for c in frame.columns]
                    aliases = {
                        "company name": "company_name",
                        "company_name": "company_name",
                        "industry": "industry",
                        "symbol": "symbol",
                        "series": "series",
                        "isin code": "isin_code",
                        "isin_code": "isin_code",
                    }
                    frame = frame.rename(columns=aliases)
                    if "symbol" not in frame.columns:
                        raise ValueError(
                            f"{csv_name} does not include a Symbol column: {list(frame.columns)}"
                        )

                    frame["symbol"] = frame["symbol"].fillna("").astype(str).str.strip().str.upper()
                    frame = frame[frame["symbol"] != ""].drop_duplicates("symbol", keep="last")

                    # The legacy table remains the latest/current snapshot for existing APIs.
                    cursor.execute(
                        "DELETE FROM nifty_index_constituents WHERE index_name = %s",
                        (index_name,),
                    )

                    current_sql = """
                        INSERT INTO nifty_index_constituents
                        (index_name, company_name, industry, symbol, series, isin_code)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (index_name, symbol) DO UPDATE SET
                            company_name=EXCLUDED.company_name,
                            industry=EXCLUDED.industry,
                            series=EXCLUDED.series,
                            isin_code=EXCLUDED.isin_code,
                            last_updated=CURRENT_TIMESTAMP
                    """
                    snapshot_sql = """
                        INSERT INTO nifty_index_constituent_snapshots
                        (snapshot_date, index_name, company_name, industry, symbol, series, isin_code)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (snapshot_date, index_name, symbol) DO UPDATE SET
                            company_name=EXCLUDED.company_name,
                            industry=EXCLUDED.industry,
                            series=EXCLUDED.series,
                            isin_code=EXCLUDED.isin_code,
                            captured_at=now()
                    """

                    count = 0
                    for row in frame.to_dict("records"):
                        symbol = row["symbol"]
                        company = _clean(row.get("company_name")) or ""
                        industry = _clean(row.get("industry"))
                        series = (_clean(row.get("series")) or "EQ").upper()
                        isin = _clean(row.get("isin_code"))

                        values = (index_name, company, industry, symbol, series, isin)
                        cursor.execute(current_sql, values)
                        cursor.execute(snapshot_sql, (snapshot_date, *values))
                        count += 1

                    total_loaded += count
                    print(f"Loaded {count} {index_name} members for snapshot {snapshot_date}")

        print(f"Total constituents refreshed: {total_loaded}")
        return total_loaded
    finally:
        conn.close()


if __name__ == "__main__":
    print("Loading NIFTY index constituents...")
    load_index_constituents()
