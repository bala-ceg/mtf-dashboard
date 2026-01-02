import psycopg2
from datetime import datetime
from config import DB_CONFIG
from etl.utils import read_scripwise_table

def load_scripwise(csv_path):
    trade_date = datetime.strptime(
        csv_path.stem.split("_")[-1], "%d%m%y"
    ).date()

    df = read_scripwise_table(csv_path)

    df = df.rename(columns={
        "symbol": "symbol",
        "name": "company_name",
        "amt_fin_by_all_the_membersrs_in_lakhs": "mtf_amount_lakhs",
        "qty_fin_by_all_the_membersnoof_shares": "mtf_quantity",
    })

    df["mtf_amount_cr"] = df["mtf_amount_lakhs"] / 100

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for _, r in df.iterrows():
        cur.execute("""
            INSERT INTO stocks_master (symbol, company_name)
            VALUES (%s, %s)
            ON CONFLICT (symbol) DO NOTHING
        """, (r["symbol"], r["company_name"]))

        cur.execute("""
            INSERT INTO mtf_daily (
                trade_date, symbol, mtf_amount_cr, mtf_quantity
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (trade_date, symbol)
            DO UPDATE SET
                mtf_amount_cr = EXCLUDED.mtf_amount_cr,
                mtf_quantity = EXCLUDED.mtf_quantity
        """, (
            trade_date,
            r["symbol"],
            r["mtf_amount_cr"],
            r["mtf_quantity"]
        ))

    conn.commit()
    cur.close()
    conn.close()