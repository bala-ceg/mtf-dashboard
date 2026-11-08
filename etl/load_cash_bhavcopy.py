"""Load full NSE cash Bhavcopy for NIFTY Total Market EQ constituents.

Unlike load_bhavcopy_mtf.py this loader is not restricted to MTF-active stocks.
It uses the existing data/clean/bhavcopy archive and existing PostgreSQL config.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from config import DB_CONFIG

ROOT = Path(__file__).resolve().parent.parent
CANDIDATE_DIRS = [
    ROOT / "data" / "data" / "clean" / "bhavcopy",
    ROOT / "data" / "clean" / "bhavcopy",
]
DATA_DIR = next((p for p in CANDIDATE_DIRS if p.exists()), CANDIDATE_DIRS[0])
LOG_DIR = ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "swing_bhavcopy_load.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
TABLE = "cash_market_daily"


def _trade_date(path: Path, frame: pd.DataFrame):
    suffix = path.stem.split("_")[-1]
    try:
        return datetime.strptime(suffix, "%d%m%Y").date()
    except ValueError:
        if "DATE1" not in frame.columns:
            raise ValueError(f"Cannot infer trade date from {path.name}")
        return pd.to_datetime(frame["DATE1"].iloc[0], dayfirst=True).date()


def load_file(path: Path, conn) -> int:
    frame = pd.read_csv(path)
    frame.columns = frame.columns.str.strip().str.upper()
    required = {"SYMBOL", "SERIES", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE",
                "CLOSE_PRICE", "TTL_TRD_QNTY"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path.name} missing columns: {sorted(missing)}")

    frame["SYMBOL"] = frame["SYMBOL"].astype(str).str.strip().str.upper()
    frame["SERIES"] = frame["SERIES"].astype(str).str.strip().str.upper()
    frame = frame[frame["SERIES"] == "EQ"].copy()
    frame = frame.drop_duplicates(subset=["SYMBOL", "SERIES"], keep="last")
    trade_date = _trade_date(path, frame)

    numeric = [
        "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "AVG_PRICE",
        "LAST_PRICE", "PREV_CLOSE", "TTL_TRD_QNTY", "TURNOVER_LACS",
        "NO_OF_TRADES", "DELIV_QTY", "DELIV_PER"
    ]
    for column in numeric:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT upper(symbol)
            FROM nifty_index_constituents
            WHERE upper(replace(index_name, ' ', '_')) IN
                  ('NIFTY_TOTAL_MARKET','NIFTY_TOTALMARKET')
        """)
        universe = {row[0] for row in cur.fetchall()}

    if not universe:
        raise RuntimeError(
            "NIFTY_TOTAL_MARKET constituents are missing. Run download_nifty_indices.py "
            "and load_nifty_indices.py before loading Bhavcopy."
        )

    frame = frame[frame["SYMBOL"].isin(universe)]
    if frame.empty:
        logging.warning("No NIFTY Total Market EQ rows in %s (%s)", path.name, trade_date)
        return 0

    def val(row, col):
        value = row.get(col)
        if pd.isna(value):
            return None
        if col in {"TTL_TRD_QNTY", "NO_OF_TRADES", "DELIV_QTY"}:
            return int(value)
        return float(value)

    records = []
    for row in frame.to_dict("records"):
        records.append((
            trade_date, row["SYMBOL"], row["SERIES"],
            val(row, "OPEN_PRICE"), val(row, "HIGH_PRICE"),
            val(row, "LOW_PRICE"), val(row, "CLOSE_PRICE"),
            val(row, "AVG_PRICE"), val(row, "LAST_PRICE"),
            val(row, "PREV_CLOSE"), val(row, "TTL_TRD_QNTY"),
            val(row, "TURNOVER_LACS"), val(row, "NO_OF_TRADES"),
            val(row, "DELIV_QTY"), val(row, "DELIV_PER"), path.name
        ))

    sql = """
        INSERT INTO cash_market_daily (
            trade_date, symbol, series, open_price, high_price, low_price,
            close_price, avg_price, last_price, prev_close, total_traded_qty,
            turnover_lacs, no_of_trades, deliv_qty, deliv_per, source_file
        ) VALUES %s
        ON CONFLICT (trade_date, symbol, series) DO UPDATE SET
            open_price=EXCLUDED.open_price, high_price=EXCLUDED.high_price,
            low_price=EXCLUDED.low_price, close_price=EXCLUDED.close_price,
            avg_price=EXCLUDED.avg_price, last_price=EXCLUDED.last_price,
            prev_close=EXCLUDED.prev_close, total_traded_qty=EXCLUDED.total_traded_qty,
            turnover_lacs=EXCLUDED.turnover_lacs, no_of_trades=EXCLUDED.no_of_trades,
            deliv_qty=EXCLUDED.deliv_qty, deliv_per=EXCLUDED.deliv_per,
            source_file=EXCLUDED.source_file, ingested_at=now()
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, records, page_size=1000)
    conn.commit()
    logging.info("Loaded %s rows for %s from %s", len(records), trade_date, path.name)
    return len(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Load one date in YYYY-MM-DD format")
    parser.add_argument("--directory", default=str(DATA_DIR))
    args = parser.parse_args()
    directory = Path(args.directory)
    if args.date:
        day = datetime.strptime(args.date, "%Y-%m-%d")
        path = directory / f"sec_bhavdata_full_{day:%d%m%Y}.csv"
        files = [path] if path.exists() else []
    else:
        files = sorted(directory.glob("sec_bhavdata_full_*.csv"))
    if not files:
        raise SystemExit(f"No sec_bhavdata_full_*.csv files found under {directory}")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        total = 0
        for path in files:
            try:
                count = load_file(path, conn)
                total += count
                print(f"{path.name}: {count} rows")
            except Exception:
                conn.rollback()
                logging.exception("Failed to load %s", path)
                raise
        print(f"Loaded {total} NIFTY Total Market EQ rows from {len(files)} files")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
