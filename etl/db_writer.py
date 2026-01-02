import psycopg2
from config import DB_CONFIG

def upsert_market_summary(trade_date, metrics):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO mtf_market_daily (
            trade_date,
            opening_outstanding_cr,
            fresh_exposure_cr,
            liquidated_exposure_cr,
            closing_outstanding_cr
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (trade_date)
        DO UPDATE SET
            opening_outstanding_cr = EXCLUDED.opening_outstanding_cr,
            fresh_exposure_cr = EXCLUDED.fresh_exposure_cr,
            liquidated_exposure_cr = EXCLUDED.liquidated_exposure_cr,
            closing_outstanding_cr = EXCLUDED.closing_outstanding_cr
    """, (
        trade_date,
        metrics["opening_outstanding_cr"],
        metrics["fresh_exposure_cr"],
        metrics["liquidated_exposure_cr"],
        metrics["closing_outstanding_cr"]
    ))

    conn.commit()
    cur.close()
    conn.close()
