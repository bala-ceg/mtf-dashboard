import pandas as pd
import psycopg2
from pathlib import Path
import sys
import os

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG


def load_index_constituents():
    """Load Nifty index constituents from CSV files into database"""
    
    nifty_indices_dir = Path(__file__).parent.parent / "data" / "nifty_indices"
    
    if not nifty_indices_dir.exists():
        print(f"Error: Directory {nifty_indices_dir} does not exist")
        return
    
    # Mapping of file names to index names
    index_mapping = {
        "nifty50.csv": "NIFTY50",
        "nifty_next50.csv": "NIFTY_NEXT50",
        "nifty_smallcap50.csv": "NIFTY_SMALLCAP50",
        "nifty_midcap50.csv": "NIFTY_MIDCAP50"
    }
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Create table if not exists
        sql_file = Path(__file__).parent.parent / "sql" / "15_nifty_index_constituents.sql"
        if sql_file.exists():
            with open(sql_file, 'r') as f:
                cursor.execute(f.read())
            conn.commit()
            print("✓ Table created/verified")
        
        total_loaded = 0
        
        for csv_file, index_name in index_mapping.items():
            file_path = nifty_indices_dir / csv_file
            
            if not file_path.exists():
                print(f"⚠ Skipping {csv_file} - file not found")
                continue
            
            print(f"\nProcessing {index_name}...")
            
            # Read CSV
            df = pd.read_csv(file_path)
            
            # Standardize column names (handle variations)
            df.columns = df.columns.str.strip()
            
            # Map columns (adjust based on actual CSV structure)
            column_mapping = {
                'Company Name': 'company_name',
                'Industry': 'industry',
                'Symbol': 'symbol',
                'Series': 'series',
                'ISIN Code': 'isin_code'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Delete existing records for this index
            delete_query = "DELETE FROM nifty_index_constituents WHERE index_name = %s"
            cursor.execute(delete_query, (index_name,))
            
            # Insert new records
            insert_query = """
                INSERT INTO nifty_index_constituents 
                (index_name, company_name, industry, symbol, series, isin_code)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (index_name, symbol) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    industry = EXCLUDED.industry,
                    series = EXCLUDED.series,
                    isin_code = EXCLUDED.isin_code,
                    last_updated = CURRENT_TIMESTAMP
            """
            
            count = 0
            for _, row in df.iterrows():
                cursor.execute(insert_query, (
                    index_name,
                    row.get('company_name', ''),
                    row.get('industry', ''),
                    row.get('symbol', ''),
                    row.get('series', ''),
                    row.get('isin_code', '')
                ))
                count += 1
            
            conn.commit()
            total_loaded += count
            print(f"✓ Loaded {count} constituents for {index_name}")
        
        print(f"\n✓ Total constituents loaded: {total_loaded}")
        
    except Exception as e:
        print(f"Error loading index constituents: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("Loading Nifty index constituents into database...")
    load_index_constituents()
    print("\nDone!")
