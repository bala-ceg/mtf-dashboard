"""Import NSE Full Bhavcopy / Security Deliverable Data CSV into PostgreSQL.

Supports the legacy SEC_BHAVDATA_FULL format and common UDiFF aliases.
Run: python -m etl.import_bhavcopy path/to/sec_bhavdata_full_DDMMYYYY.csv
DB connection: DATABASE_URL or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD.
"""
from __future__ import annotations
import argparse
import csv
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

ALIASES = {
    "symbol": ("symbol", "tckrsymb", "tradingsymbol"),
    "series": ("series", "sctysrs"),
    "date": ("date1", "traddt", "trading_date", "date"),
    "prev_close": ("prev_close", "prvsclsgpric"),
    "open": ("open_price", "opnpric"),
    "high": ("high_price", "hghpric"),
    "low": ("low_price", "lwpric"),
    "last": ("last_price", "lastpric"),
    "close": ("close_price", "clspric"),
    "avg": ("avg_price", "avrgpric", "vwap"),
    "qty": ("ttl_trd_qnty", "ttltxqty", "tottrdqty", "traded_quantity"),
    "turnover": ("turnover_lacs", "turnover", "ttlamnt", "traded_value"),
    "trades": ("no_of_trades", "tnt", "nooftrades"),
    "delivery_qty": ("deliv_qty", "dlyqty", "deliverable_quantity"),
    "delivery_pct": ("deliv_per", "dlyqtto", "delivery_percentage"),
}

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.strip().lower())

def decimal(value):
    if value is None or str(value).strip() in ("", "-", "nan", "None"):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation:
        return None

def parse_date(value, fallback):
    value = str(value or "").strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return fallback

def connect():
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "mtf_db"),
        user=os.getenv("DB_USER", "bseetharaman"),
        password=os.getenv("DB_PASSWORD", ""),
    )

def import_file(path: Path, include_be: bool = True) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        lookup = {norm(k): k for k in reader.fieldnames}
        cols = {}
        for key, aliases in ALIASES.items():
            cols[key] = next((lookup[norm(a)] for a in aliases if norm(a) in lookup), None)
        required = ("symbol", "date", "close", "qty")
        missing = [k for k in required if not cols[k]]
        if missing:
            raise ValueError(f"Unsupported Bhavcopy columns; missing {missing}. Found: {reader.fieldnames}")

        rows = []
        for raw in reader:
            symbol = str(raw.get(cols["symbol"]) or "").strip().upper()
            series = str(raw.get(cols["series"]) or "EQ").strip().upper() if cols["series"] else "EQ"
            if not symbol or series not in (("EQ", "BE") if include_be else ("EQ",)):
                continue
            dt = parse_date(raw.get(cols["date"]), None)
            if not dt:
                continue
            qty = int(decimal(raw.get(cols["qty"])) or 0)
            turnover = decimal(raw.get(cols["turnover"])) if cols["turnover"] else None
            # Legacy NSE SEC_BHAVDATA_FULL turnover is in lakh rupees.
            if turnover is not None and "turnover_lacs" in norm(cols["turnover"]):
                turnover = turnover / Decimal(100)
            delivery_qty = int(decimal(raw.get(cols["delivery_qty"])) or 0) if cols["delivery_qty"] else None
            delivery_pct = decimal(raw.get(cols["delivery_pct"])) if cols["delivery_pct"] else None
            if delivery_pct is None and delivery_qty is not None and qty > 0:
                delivery_pct = Decimal(delivery_qty) * 100 / Decimal(qty)
            rows.append((
                dt, symbol, series,
                decimal(raw.get(cols["prev_close"])) if cols["prev_close"] else None,
                decimal(raw.get(cols["open"])) if cols["open"] else None,
                decimal(raw.get(cols["high"])) if cols["high"] else None,
                decimal(raw.get(cols["low"])) if cols["low"] else None,
                decimal(raw.get(cols["last"])) if cols["last"] else None,
                decimal(raw.get(cols["close"])),
                decimal(raw.get(cols["avg"])) if cols["avg"] else None,
                qty, turnover,
                int(decimal(raw.get(cols["trades"])) or 0) if cols["trades"] else None,
                delivery_qty, delivery_pct, path.name
            ))
    if not rows:
        return 0
    sql = """
      INSERT INTO swing_daily_bhavcopy
      (trade_date,symbol,series,prev_close,open_price,high_price,low_price,last_price,
       close_price,avg_price,traded_quantity,turnover_cr,number_of_trades,
       delivery_quantity,delivery_pct,source_file)
      VALUES %s
      ON CONFLICT (trade_date,symbol,series) DO UPDATE SET
       prev_close=EXCLUDED.prev_close, open_price=EXCLUDED.open_price,
       high_price=EXCLUDED.high_price, low_price=EXCLUDED.low_price,
       last_price=EXCLUDED.last_price, close_price=EXCLUDED.close_price,
       avg_price=EXCLUDED.avg_price, traded_quantity=EXCLUDED.traded_quantity,
       turnover_cr=EXCLUDED.turnover_cr, number_of_trades=EXCLUDED.number_of_trades,
       delivery_quantity=EXCLUDED.delivery_quantity, delivery_pct=EXCLUDED.delivery_pct,
       source_file=EXCLUDED.source_file, ingested_at=now()
    """
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            execute_values(cur, sql, rows, page_size=1000)
            cur.execute("""INSERT INTO swing_ingestion_runs
              (dataset,trade_date,source_file,rows_loaded,status,finished_at)
              VALUES ('bhavcopy',%s,%s,%s,'success',now())""",
              (rows[0][0], path.name, len(rows)))
    finally:
        conn.close()
    return len(rows)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--exclude-be", action="store_true")
    args = p.parse_args()
    print(f"Imported {import_file(args.csv, include_be=not args.exclude_be)} rows")
