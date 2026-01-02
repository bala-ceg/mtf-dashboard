import requests
import pandas as pd
import os
from pathlib import Path

def nsecsvfetch(payload):  
    """Fetch CSV data from NSE/Nifty Indices website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        s = requests.Session()
        s.get("https://nseindia.com", headers=headers)
        response = s.get(payload, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def download_nifty_indices():
    """Download Nifty index constituent lists"""
    
    # Create data/nifty_indices directory if it doesn't exist
    base_dir = Path(__file__).parent.parent / "data" / "nifty_indices"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    indices = {
        "nifty50": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
        "nifty_next50": "https://www.niftyindices.com/IndexConstituent/ind_niftynext50list.csv",
        "nifty_smallcap50": "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap50list.csv",
        "nifty_midcap50": "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap50list.csv"
    }
    
    downloaded_files = []
    
    for index_name, url in indices.items():
        print(f"Downloading {index_name}...")
        response = nsecsvfetch(url)
        
        if response:
            data_text = response.text
            # Replace & with %26 to handle special characters
            data_text = data_text.replace('&', '%26')
            
            output_file = base_dir / f"{index_name}.csv"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(data_text)
            
            print(f"✓ Successfully downloaded {index_name} to {output_file}")
            downloaded_files.append(output_file)
        else:
            print(f"✗ Failed to download {index_name}")
    
    return downloaded_files


if __name__ == "__main__":
    print("Starting Nifty Indices download...")
    files = download_nifty_indices()
    print(f"\nDownloaded {len(files)} index files successfully!")
