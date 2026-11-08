"""Download official NIFTY index constituent files from NSE archives."""
from pathlib import Path
import csv
import requests

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "nifty_indices"
NSE_HOME = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
}

INDEX_FILES = {
    "nifty50": "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "nifty_next50": "https://nsearchives.nseindia.com/content/indices/ind_niftynext50list.csv",
    "nifty_smallcap50": "https://nsearchives.nseindia.com/content/indices/ind_niftysmallcap50list.csv",
    "nifty_midcap50": "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap50list.csv",
    "nifty_total_market": "https://nsearchives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv",
}


def download_nifty_indices():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(NSE_HOME, timeout=15)
        downloaded = []
        errors = []
        for name, url in INDEX_FILES.items():
            output = OUTPUT_DIR / f"{name}.csv"
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
                content = response.content.decode("utf-8-sig").strip()
                if not content or "<html" in content[:500].lower():
                    raise ValueError("Response was empty or HTML, not a CSV file")
                header = next(csv.reader(content.splitlines()), [])
                if "symbol" not in {item.strip().lower() for item in header}:
                    raise ValueError(f"CSV header has no Symbol column: {header}")
                temp = output.with_suffix(".csv.tmp")
                temp.write_text(content + "\n", encoding="utf-8")
                temp.replace(output)
                downloaded.append(output)
                print(f"Downloaded {name}: {output}")
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                print(f"Failed {name}: {exc}")
        if not any(path.name == "nifty_total_market.csv" for path in downloaded):
            raise RuntimeError(
                "Could not refresh the official NIFTY Total Market constituent file "
                "from NSE. Refusing to mark a stale cached file as today's membership snapshot."
            )
        if errors:
            print("Optional lists not refreshed: " + "; ".join(errors))
        return downloaded
    finally:
        session.close()


if __name__ == "__main__":
    files = download_nifty_indices()
    print(f"Downloaded {len(files)} index constituent file(s).")
