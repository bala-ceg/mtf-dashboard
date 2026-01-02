-- =========================
-- STOCK MASTER
-- =========================
CREATE TABLE IF NOT EXISTS stocks_master (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    sector TEXT,
    market_cap_cr NUMERIC,
    created_at TIMESTAMP DEFAULT now()
);

-- =========================
-- SCRIP-WISE DAILY MTF
-- =========================
CREATE TABLE IF NOT EXISTS mtf_daily (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL REFERENCES stocks_master(symbol),
    mtf_amount_cr NUMERIC,
    mtf_quantity BIGINT,
    PRIMARY KEY (trade_date, symbol)
);

-- =========================
-- MARKET-LEVEL DAILY MTF SUMMARY
-- =========================
CREATE TABLE IF NOT EXISTS mtf_market_daily (
    trade_date DATE PRIMARY KEY,
    opening_outstanding_cr NUMERIC,
    fresh_exposure_cr NUMERIC,
    liquidated_exposure_cr NUMERIC,
    closing_outstanding_cr NUMERIC,
    created_at TIMESTAMP DEFAULT now()
);
