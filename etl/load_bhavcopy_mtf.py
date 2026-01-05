"""
Load bhavcopy data into database for stocks that have MTF activity
Only loads data for symbols present in mtf_daily table
"""
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
import logging
from config import DB_CONFIG, BASE_DIR

# Setup logging
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "load_bhavcopy_mtf.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Check for nested data/data directory structure
if (BASE_DIR / "data" / "data" / "clean" / "bhavcopy").exists():
    BHAVCOPY_CLEAN_DIR = BASE_DIR / "data" / "data" / "clean" / "bhavcopy"
else:
    BHAVCOPY_CLEAN_DIR = BASE_DIR / "data" / "clean" / "bhavcopy"


def get_mtf_symbols():
    """Get list of all symbols that have MTF activity"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT symbol 
            FROM mtf_daily
            WHERE symbol NOT LIKE '%*%'
              AND symbol NOT LIKE '%Figures%'
              AND LENGTH(symbol) <= 20
            ORDER BY symbol
        """)
        
        symbols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        logging.info(f"Found {len(symbols)} unique MTF symbols")
        return set(symbols)
        
    except Exception as e:
        logging.error(f"Error fetching MTF symbols: {e}")
        return set()


def load_bhavcopy_file(file_path: Path, mtf_symbols: set) -> int:
    """
    Load a single bhavcopy CSV file, filtering for MTF stocks only
    
    Returns:
        Number of records inserted
    """
    try:
        # Read the cleaned bhavcopy CSV
        df = pd.read_csv(file_path)
        
        logging.info(f"Read {len(df)} rows from {file_path.name}")
        logging.info(f"Columns: {df.columns.tolist()}")
        
        # Check if SYMBOL column exists
        if 'SYMBOL' not in df.columns:
            logging.error(f"SYMBOL column not found in {file_path.name}")
            return 0
        
        # Filter for MTF symbols only
        before_filter = len(df)
        df = df[df['SYMBOL'].isin(mtf_symbols)]
        after_filter = len(df)
        
        logging.info(f"Filtered from {before_filter} to {after_filter} MTF stocks")
        print(f"  Debug: {before_filter} rows -> {after_filter} MTF stocks")
        
        if len(df) == 0:
            logging.info(f"No MTF stocks found in {file_path.name}")
            print(f"  Debug: First 5 bhav symbols: {list(pd.read_csv(file_path)['SYMBOL'].head())}")
            print(f"  Debug: First 5 mtf symbols: {list(mtf_symbols)[:5]}")
            return 0
        
        # Extract date from filename: sec_bhavdata_full_DDMMYYYY.csv
        date_str = file_path.stem.split('_')[-1]  # Gets DDMMYYYY
        trade_date = datetime.strptime(date_str, "%d%m%Y").date()
        
        # Prepare data for insertion
        records = []
        for idx, row in df.iterrows():
            try:
                # Convert numeric values properly, handling NaN
                total_qty = row.get('TTL_TRD_QNTY')
                deliv_qty = row.get('DELIV_QTY')
                no_trades = row.get('NO_OF_TRADES')
                
                # Convert to int if not NaN, else None
                total_qty = int(total_qty) if pd.notna(total_qty) else None
                deliv_qty = int(deliv_qty) if pd.notna(deliv_qty) else None
                no_trades = int(no_trades) if pd.notna(no_trades) else None
                
                record = (
                    trade_date,
                    row['SYMBOL'],
                    row.get('SERIES', 'EQ'),
                    row.get('OPEN_PRICE') if pd.notna(row.get('OPEN_PRICE')) else None,
                    row.get('HIGH_PRICE') if pd.notna(row.get('HIGH_PRICE')) else None,
                    row.get('LOW_PRICE') if pd.notna(row.get('LOW_PRICE')) else None,
                    row.get('CLOSE_PRICE') if pd.notna(row.get('CLOSE_PRICE')) else None,
                    row.get('LAST_PRICE') if pd.notna(row.get('LAST_PRICE')) else None,
                    row.get('PREV_CLOSE') if pd.notna(row.get('PREV_CLOSE')) else None,
                    total_qty,
                    row.get('TURNOVER_LACS') if pd.notna(row.get('TURNOVER_LACS')) else None,
                    no_trades,
                    deliv_qty,
                    row.get('DELIV_PER') if pd.notna(row.get('DELIV_PER')) else None
                )
                records.append(record)
            except Exception as e:
                print(f"  ⚠️  Error processing row {idx} symbol {row.get('SYMBOL')}: {e}")
                logging.error(f"Error processing row {idx}: {e}")
                continue
        
        print(f"  Debug: Prepared {len(records)} records for insertion")
        
        # Insert into database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO bhavcopy_mtf_stocks (
                trade_date, symbol, series, open_price, high_price, low_price,
                close_price, last_price, prev_close, total_traded_qty,
                turnover_lacs, no_of_trades, deliv_qty, deliv_per
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (trade_date, symbol) 
            DO UPDATE SET
                series = EXCLUDED.series,
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                last_price = EXCLUDED.last_price,
                prev_close = EXCLUDED.prev_close,
                total_traded_qty = EXCLUDED.total_traded_qty,
                turnover_lacs = EXCLUDED.turnover_lacs,
                no_of_trades = EXCLUDED.no_of_trades,
                deliv_qty = EXCLUDED.deliv_qty,
                deliv_per = EXCLUDED.deliv_per,
                created_at = now()
        """
        
        cursor.executemany(insert_query, records)
        conn.commit()
        
        rows_inserted = cursor.rowcount
        cursor.close()
        conn.close()
        
        logging.info(f"Loaded {rows_inserted} MTF stock records from {file_path.name} for {trade_date}")
        print(f"  Debug: Database returned rowcount: {rows_inserted}")
        return rows_inserted
        
    except Exception as e:
        logging.error(f"Error loading {file_path.name}: {e}")
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0


def load_all_bhavcopy_files():
    """Load all bhavcopy files from clean directory"""
    
    if not BHAVCOPY_CLEAN_DIR.exists():
        print(f"❌ Bhavcopy directory not found: {BHAVCOPY_CLEAN_DIR}")
        return
    
    # Get MTF symbols
    print("📊 Fetching MTF symbols...")
    mtf_symbols = get_mtf_symbols()
    
    if not mtf_symbols:
        print("❌ No MTF symbols found in database")
        return
    
    print(f"✅ Found {len(mtf_symbols)} unique MTF symbols")
    
    # Get all cleaned bhavcopy files
    csv_files = sorted(BHAVCOPY_CLEAN_DIR.glob("sec_bhavdata_full_*.csv"))
    
    if not csv_files:
        print(f"❌ No bhavcopy files found in {BHAVCOPY_CLEAN_DIR}")
        return
    
    print(f"📁 Found {len(csv_files)} bhavcopy files")
    print("=" * 70)
    
    total_records = 0
    success_count = 0
    
    for csv_file in csv_files:
        records = load_bhavcopy_file(csv_file, mtf_symbols)
        if records > 0:
            total_records += records
            success_count += 1
            print(f"✅ {csv_file.name}: {records} records")
        else:
            print(f"⚠️  {csv_file.name}: 0 records (skipped)")
    
    print("=" * 70)
    print(f"✅ Loaded {success_count}/{len(csv_files)} files")
    print(f"📊 Total records inserted: {total_records}")
    logging.info(f"Batch load completed: {total_records} total records from {success_count} files")


def load_bhavcopy_date_range(start_date: datetime, end_date: datetime):
    """Load bhavcopy files for a specific date range"""
    
    print("📊 Fetching MTF symbols...")
    mtf_symbols = get_mtf_symbols()
    
    if not mtf_symbols:
        print("❌ No MTF symbols found in database")
        return
    
    print(f"✅ Found {len(mtf_symbols)} unique MTF symbols")
    print(f"📅 Loading bhavcopy from {start_date.date()} to {end_date.date()}")
    print("=" * 70)
    
    total_records = 0
    success_count = 0
    curr = start_date
    
    while curr <= end_date:
        date_str = curr.strftime("%d%m%Y")
        file_path = BHAVCOPY_CLEAN_DIR / f"sec_bhavdata_full_{date_str}.csv"
        
        if file_path.exists():
            records = load_bhavcopy_file(file_path, mtf_symbols)
            if records > 0:
                total_records += records
                success_count += 1
                print(f"✅ {file_path.name}: {records} records")
            else:
                print(f"⚠️  {file_path.name}: 0 records")
        else:
            print(f"⏭️  {curr.date()}: File not found")
        
        curr += timedelta(days=1)
    
    print("=" * 70)
    print(f"✅ Loaded {success_count} files")
    print(f"📊 Total records inserted: {total_records}")


if __name__ == "__main__":
    import sys
    from datetime import timedelta
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "range":
            # Load specific date range
            if len(sys.argv) < 4:
                print("Usage: python load_bhavcopy_mtf.py range YYYY-MM-DD YYYY-MM-DD")
                sys.exit(1)
            start = datetime.strptime(sys.argv[2], "%Y-%m-%d")
            end = datetime.strptime(sys.argv[3], "%Y-%m-%d")
            load_bhavcopy_date_range(start, end)
        else:
            print("Unknown command. Use: range")
    else:
        # Load all files
        load_all_bhavcopy_files()
