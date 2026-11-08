"""Load an official NSE Indices historical-data CSV into PostgreSQL.

Export NIFTY Total Market daily index OHLC data from the NSE Indices Historical
Data page, save the CSV locally, then run:
    python -m etl.load_index_history path/to/nifty_total_market.csv
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from config import DB_CONFIG


ALIASES = {
    "date": ("date", "index date", "trade date", "trading date"),
    "open": ("open", "open index", "open value"),
    "high": ("high", "high index", "high value"),
    "low": ("low", "low index", "low value"),
    "close": ("close", "close index", "close value", "closing index value"),
}


def parse_decimal(value):
    if value is None or str(value).strip() in ("", "-", "NA", "N/A"):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None


def parse_date(value):
    value = str(value or "").strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported index date: {value!r}")


def load_csv(path: Path, index_name: str = "NIFTY_TOTAL_MARKET") -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV does not have a header row")
        fields = {name.strip().lower(): name for name in reader.fieldnames}
        columns = {}
        for key, aliases in ALIASES.items():
            source = next((fields[a] for a in aliases if a in fields), None)
            if source is None:
                raise ValueError(
                    f"Could not identify {key!r} column. CSV headers: {reader.fieldnames}"
                )
            columns[key] = source

        rows = []
        for record in reader:
            close_value = parse_decimal(record.get(columns["close"]))
            if close_value is None:
                continue
            rows.append((
                index_name.upper(),
                parse_date(record.get(columns["date"])),
                parse_decimal(record.get(columns["open"])),
                parse_decimal(record.get(columns["high"])),
                parse_decimal(record.get(columns["low"])),
                close_value,
                path.name,
            ))

    if not rows:
        raise ValueError("CSV contains no valid index observations")

    sql = """
        INSERT INTO nifty_index_daily
        (index_name, trade_date, open_value, high_value, low_value, close_value, source_file)
        VALUES %s
        ON CONFLICT (index_name, trade_date) DO UPDATE SET
            open_value=EXCLUDED.open_value,
            high_value=EXCLUDED.high_value,
            low_value=EXCLUDED.low_value,
            close_value=EXCLUDED.close_value,
            source_file=EXCLUDED.source_file,
            loaded_at=now()
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn, conn.cursor() as cursor:
            execute_values(cursor, sql, rows, page_size=1000)
    finally:
        conn.close()
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--index-name", default="NIFTY_TOTAL_MARKET")
    args = parser.parse_args()
    print(f"Loaded {load_csv(args.csv_file, args.index_name)} index sessions")
