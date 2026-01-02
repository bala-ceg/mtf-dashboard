from datetime import datetime, timedelta
from config import CLEAN_DIR

from etl.extract_market_summary import extract_market_summary
from etl.db_writer import upsert_market_summary
from etl.load_scripwise_mtf import load_scripwise
from etl.download_mtf import download_date_range, get_nse_session, download_and_process_date

def main(start_date=None, end_date=None, skip_download=False):
    """
    Backfill MTF data from a date range.
    
    Args:
        start_date: datetime object (default: 30 days ago)
        end_date: datetime object (default: today)
        skip_download: bool (default: False - will attempt to download missing files)
    """
    
    if start_date is None:
        start_date = datetime.now() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now()
    
    # Download missing files
    if not skip_download:
        print(f"📥 Downloading MTF data from {start_date.date()} to {end_date.date()}...")
        download_date_range(start_date, end_date)
    
    print(f"\n📊 Processing MTF files...")
    
    for csv_file in sorted(CLEAN_DIR.glob("mrg_trading_*.csv")):
        print(f"Processing {csv_file.name}")

        trade_date = datetime.strptime(
            csv_file.stem.split("_")[-1], "%d%m%y"
        ).date()

        summary = extract_market_summary(csv_file)
        if summary:
            upsert_market_summary(trade_date, summary)
        else:
            print("  ↳ Market summary missing (skipped)")

        load_scripwise(csv_file)
    
    print("\n✅ Backfill completed")

if __name__ == "__main__":
    main()