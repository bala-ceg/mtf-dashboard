import requests
import zipfile
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import logging

# -----------------------
# Configuration
# -----------------------
BASE_DIR = Path("data")
ZIP_DIR = BASE_DIR / "zips"
RAW_DIR = BASE_DIR / "raw"
CLEAN_DIR = BASE_DIR / "clean"
LOG_DIR = BASE_DIR / "logs"

for d in [ZIP_DIR, RAW_DIR, CLEAN_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "mtf_download.log"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/zip",
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
# NSE Session (important)
# -----------------------
def get_nse_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    session.get("https://www.nseindia.com", timeout=10)
    return session

# -----------------------
# Download ZIP
# -----------------------
def download_zip(session, url: str, output_path: Path) -> bool:
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
# Unzip CSV
# -----------------------
def unzip_csv(zip_path: Path, output_csv: Path) -> None:
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
# Clean CSV
# -----------------------
def clean_margin_trading_csv(input_csv: Path, output_csv: Path) -> None:
    df = pd.read_csv(input_csv)

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )

    df.dropna(how="all", inplace=True)

    for col in df.select_dtypes(include="object"):
        df[col] = df[col].str.strip()

    for col in df.columns:
        if any(k in col for k in ["value", "amount", "qty", "quantity"]):
            df[col] = (
                df[col].astype(str)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)

    df.to_csv(output_csv, index=False)

# -----------------------
# Main Loop
# -----------------------
if __name__ == "__main__":

    session = get_nse_session()

    start_date = datetime(2025, 10, 1)
    end_date = datetime(2025, 12, 18)

    curr = start_date

    while curr <= end_date:
        ddmmyy = curr.strftime("%d%m%y")

        url = f"https://nsearchives.nseindia.com/content/equities/mrg_trading_{ddmmyy}.zip"

        zip_path = ZIP_DIR / f"mrg_trading_{ddmmyy}.zip"
        raw_csv = RAW_DIR / f"mrg_trading_{ddmmyy}.csv"
        clean_csv = CLEAN_DIR / f"mrg_trading_{ddmmyy}.csv"

        logging.info(f"Processing {curr.date()}")

        if download_zip(session, url, zip_path):
            try:
                unzip_csv(zip_path, raw_csv)
                clean_margin_trading_csv(raw_csv, clean_csv)
                logging.info(f"SUCCESS: {curr.date()}")
            except Exception as e:
                logging.error(f"FAILED PROCESSING {curr.date()} | {e}")

        curr += timedelta(days=1)

    logging.info("MTF historical download completed")
