from datetime import datetime
from config import CLEAN_DIR

from etl.extract_market_summary import extract_market_summary
from etl.db_writer import upsert_market_summary
from etl.load_scripwise_mtf import load_scripwise

def run_daily():
    today = datetime.today().strftime("%d%m%y")
    csv_file = CLEAN_DIR / f"mrg_trading_{today}.csv"

    if not csv_file.exists():
        print(f"No MTF file for {today}, skipping")
        return

    trade_date = datetime.strptime(today, "%d%m%y").date()

    summary = extract_market_summary(csv_file)
    if summary:
        upsert_market_summary(trade_date, summary)

    load_scripwise(csv_file)

if __name__ == "__main__":
    run_daily()