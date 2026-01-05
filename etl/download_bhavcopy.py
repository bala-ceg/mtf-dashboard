import requests
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
import logging
import pandas as pd
from config import BASE_DIR, DB_CONFIG
import psycopg2

# -----------------------
# Configuration
# -----------------------
BHAVCOPY_ZIP_DIR = BASE_DIR / "data" / "zips" / "bhavcopy"
BHAVCOPY_RAW_DIR = BASE_DIR / "data" / "raw" / "bhavcopy"
BHAVCOPY_CLEAN_DIR = BASE_DIR / "data" / "clean" / "bhavcopy"
LOG_DIR = BASE_DIR / "data" / "logs"

for d in [BHAVCOPY_ZIP_DIR, BHAVCOPY_RAW_DIR, BHAVCOPY_CLEAN_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "bhavcopy_download.log"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/zip,application/csv,text/csv,*/*",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

# -----------------------
# Logging
# -----------------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# -----------------------
# NSE Session
# -----------------------
def get_nse_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
    except Exception as e:
        logging.warning(f"Could not initialize NSE session: {e}")
    return session

# -----------------------
# Get Maximum MTF Date
# -----------------------
def get_max_mtf_date() -> datetime:
    """Get the maximum trade date from mtf_daily table"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT MAX(trade_date) 
            FROM mtf_daily
        """)
        
        max_date = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        if max_date:
            logging.info(f"Maximum MTF date found: {max_date}")
            # Convert date to datetime
            if isinstance(max_date, datetime):
                return max_date
            else:
                return datetime.combine(max_date, datetime.min.time())
        else:
            # Default to yesterday if no data
            return datetime.now() - timedelta(days=1)
            
    except Exception as e:
        logging.error(f"Error fetching max MTF date: {e}")
        # Default to yesterday if error
        return datetime.now() - timedelta(days=1)

# -----------------------
# Download CSV or ZIP
# -----------------------
def download_bhavcopy(session, url: str, output_path: Path) -> bool:
    """Download bhavcopy file (CSV or ZIP)"""
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}")

        output_path.write_bytes(resp.content)
        return True

    except Exception as e:
        logging.warning(f"SKIPPED: {url} | Reason: {e}")
        return False

# -----------------------
# Unzip CSV (if needed)
# -----------------------
def unzip_bhavcopy(zip_path: Path, output_csv: Path) -> None:
    """Extract CSV from ZIP file"""
    with zipfile.ZipFile(zip_path) as z:
        csv_name = next(
            (f for f in z.namelist() if f.lower().endswith(".csv")),
            None
        )
        if not csv_name:
            raise RuntimeError("No CSV found in ZIP")

        with z.open(csv_name) as src:
            output_csv.write_bytes(src.read())

# -----------------------
# Clean Bhavcopy CSV
# -----------------------
def clean_bhavcopy_csv(input_csv: Path, output_csv: Path) -> None:
    """Clean and standardize bhavcopy CSV data"""
    df = pd.read_csv(input_csv)

    # Standardize column names
    df.columns = (
        df.columns.str.strip()
        .str.upper()
    )

    # Remove rows with all nulls
    df.dropna(how="all", inplace=True)

    # Strip whitespace from string columns
    for col in df.select_dtypes(include="object"):
        df[col] = df[col].str.strip()

    # Convert numeric columns (remove commas if any)
    numeric_cols = ['OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 'CLOSE_PRICE', 
                    'LAST_PRICE', 'PREV_CLOSE', 'TTL_TRD_QNTY', 'TURNOVER_LACS',
                    'NO_OF_TRADES', 'DELIV_QTY', 'DELIV_PER']
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Remove duplicates
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    df.to_csv(output_csv, index=False)
    logging.info(f"Cleaned bhavcopy saved: {output_csv.name} ({len(df)} rows)")

# -----------------------
# Download and process single date
# -----------------------
def download_and_process_bhavcopy(session, trade_date: datetime, auto_load: bool = False) -> bool:
    """Download, extract, and clean bhavcopy data for a specific date"""
    ddmmyyyy = trade_date.strftime("%d%m%Y")
    
    # NSE bhavcopy URL format: https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv
    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
    
    raw_csv = BHAVCOPY_RAW_DIR / f"sec_bhavdata_full_{ddmmyyyy}.csv"
    clean_csv = BHAVCOPY_CLEAN_DIR / f"sec_bhavdata_full_{ddmmyyyy}.csv"
    
    logging.info(f"Processing bhavcopy for {trade_date.date()}")
    print(f"Downloading bhavcopy for {trade_date.strftime('%Y-%m-%d')}...")
    
    if download_bhavcopy(session, url, raw_csv):
        try:
            clean_bhavcopy_csv(raw_csv, clean_csv)
            logging.info(f"SUCCESS: {trade_date.date()}")
            print(f"✅ {clean_csv.name}")
            
            # Auto-load into database if requested
            if auto_load:
                try:
                    from etl.load_bhavcopy_mtf import load_bhavcopy_file, get_mtf_symbols
                    mtf_symbols = get_mtf_symbols()
                    if mtf_symbols:
                        records = load_bhavcopy_file(clean_csv, mtf_symbols)
                        if records > 0:
                            print(f"  ✅ Loaded {records} records into database")
                except Exception as e:
                    print(f"  ⚠️  Auto-load failed: {e}")
            
            return True
        except Exception as e:
            logging.error(f"FAILED PROCESSING {trade_date.date()} | {e}")
            print(f"❌ Failed: {trade_date.strftime('%Y-%m-%d')} | {e}")
            return False
    else:
        print(f"⚠️  Skipped: {trade_date.strftime('%Y-%m-%d')} (file not available)")
    
    return False

# -----------------------
# Download date range
# -----------------------
def download_bhavcopy_range(start_date: datetime, end_date: datetime, auto_load: bool = False) -> None:
    """Download bhavcopy data for a date range"""
    session = get_nse_session()
    
    curr = start_date
    success_count = 0
    skip_count = 0
    
    print(f"\n📊 Downloading bhavcopy from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("=" * 70)
    
    while curr <= end_date:
        result = download_and_process_bhavcopy(session, curr)
        if result:
            # Check if it was a new download or already existed
            clean_csv = BHAVCOPY_CLEAN_DIR / f"sec_bhavdata_full_{curr.strftime('%d%m%Y')}.csv"
            if clean_csv.exists():
                success_count += 1
        curr += timedelta(days=1)
    
    print("=" * 70)
    logging.info(f"Bhavcopy download completed. Success: {success_count}")
    print(f"\n✅ Total files: {success_count}")
    
    # Auto-load into database if requested
    if auto_load:
        print("\n🔄 Auto-loading data into database...")
        try:
            from etl.load_bhavcopy_mtf import load_bhavcopy_date_range
            load_bhavcopy_date_range(start_date, end_date)
        except Exception as e:
            print(f"❌ Error during auto-load: {e}")
            logging.error(f"Auto-load failed: {e}")

# -----------------------
# Sync with max MTF date
# -----------------------
def sync_bhavcopy_with_mtf(days_back: int = 0, auto_load: bool = True) -> None:
    """
    Download bhavcopy files up to the maximum MTF date in database
    
    Args:
        days_back: Number of days to go back from max MTF date (default: 0)
        auto_load: Automatically load data into database after download (default: True)
    """
    max_mtf_date = get_max_mtf_date()
    end_date = max_mtf_date - timedelta(days=days_back)
    
    # Start from October 1, 2025
    start_date = datetime(2025, 10, 1)
    
    print(f"\n🔄 Syncing bhavcopy with MTF data")
    print(f"Max MTF Date: {max_mtf_date.strftime('%Y-%m-%d')}")
    print(f"Downloading bhavcopy: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    download_bhavcopy_range(start_date, end_date)
    
    # Auto-load into database
    if auto_load:
        print("\n🔄 Auto-loading data into database...")
        try:
            from etl.load_bhavcopy_mtf import load_bhavcopy_date_range
            load_bhavcopy_date_range(start_date, end_date)
        except Exception as e:
            print(f"❌ Error during auto-load: {e}")
            logging.error(f"Auto-load failed: {e}")

# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "sync":
            # Sync with max MTF date
            sync_bhavcopy_with_mtf()
        elif sys.argv[1] == "date":
            # Download specific date
            if len(sys.argv) < 3:
                print("Usage: python download_bhavcopy.py date YYYY-MM-DD")
                sys.exit(1)
            date_str = sys.argv[2]
            trade_date = datetime.strptime(date_str, "%Y-%m-%d")
            session = get_nse_session()
            download_and_process_bhavcopy(session, trade_date)
        elif sys.argv[1] == "range":
            # Download date range
            if len(sys.argv) < 4:
                print("Usage: python download_bhavcopy.py range YYYY-MM-DD YYYY-MM-DD")
                sys.exit(1)
            start = datetime.strptime(sys.argv[2], "%Y-%m-%d")
            end = datetime.strptime(sys.argv[3], "%Y-%m-%d")
            auto_load = len(sys.argv) > 4 and sys.argv[4] == "--load"
            download_bhavcopy_range(start, end, auto_load=auto_load)
        else:
            print("Unknown command. Use: sync, date, or range")
            print("Add --load flag to automatically load data into database")
    else:
        # Default: sync with MTF (auto-loads by default)
        sync_bhavcopy_with_mtf()
