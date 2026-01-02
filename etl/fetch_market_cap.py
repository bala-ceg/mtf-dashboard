import time
import requests
import psycopg2
from datetime import datetime

# -----------------------
# NSE helpers
# -----------------------
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}

def nse_session():
    session = requests.Session()
    session.headers.update(NSE_HEADERS)

    # Prime cookies
    session.get("https://www.nseindia.com", timeout=10)
    time.sleep(1)

    return session

def fetch_market_cap(session, symbol: str):
    url = (
        "https://www.nseindia.com/api/quote-equity"
        f"?symbol={symbol}&section=trade_info"
    )

    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    try:
        mcap = data["marketDeptOrderBook"]["tradeInfo"]["totalMarketCap"]
        return float(mcap) if mcap is not None else None
    except KeyError:
        return None

# -----------------------
# DB logic
# -----------------------
def update_market_caps():
    conn = psycopg2.connect(
        "postgresql://bseetharaman@localhost:5432/mtf_db?gssencmode=disable"
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT symbol
        FROM mtf_daily
        WHERE symbol ~ '^[A-Z0-9]+$'
    """)
    symbols = [r[0] for r in cur.fetchall()]

    session = nse_session()

    for i, symbol in enumerate(symbols, 1):
        try:
            market_cap = fetch_market_cap(session, symbol)

            cur.execute("""
                UPDATE stocks_master
                SET
                    market_cap_cr = %s,
                    market_cap_updated_at = %s
                WHERE symbol = %s
            """, (
                market_cap,
                datetime.utcnow(),
                symbol
            ))

            print(f"[{i}/{len(symbols)}] {symbol} → {market_cap}")

            time.sleep(0.8)  # 🔒 RATE LIMIT

        except Exception as e:
            print(f"[ERROR] {symbol}: {e}")
            time.sleep(2)

    cur.close()
    conn.close()

# -----------------------
# Entry point
# -----------------------
if __name__ == "__main__":
    update_market_caps()
