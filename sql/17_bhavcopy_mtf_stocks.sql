-- =========================
-- BHAVCOPY DATA FOR MTF STOCKS ONLY
-- =========================
-- This table stores daily bhavcopy (market) data only for stocks that have MTF activity
-- It provides trading statistics like open, high, low, close, volume, and delivery data

CREATE TABLE IF NOT EXISTS bhavcopy_mtf_stocks (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    series TEXT,
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    last_price NUMERIC,
    prev_close NUMERIC,
    total_traded_qty BIGINT,
    turnover_lacs NUMERIC,
    no_of_trades INTEGER,
    deliv_qty BIGINT,
    deliv_per NUMERIC,
    created_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (trade_date, symbol),
    FOREIGN KEY (symbol) REFERENCES stocks_master(symbol)
);

-- Index for faster queries by date
CREATE INDEX IF NOT EXISTS idx_bhavcopy_mtf_date ON bhavcopy_mtf_stocks(trade_date DESC);

-- Index for faster queries by symbol
CREATE INDEX IF NOT EXISTS idx_bhavcopy_mtf_symbol ON bhavcopy_mtf_stocks(symbol);

-- Composite index for date + symbol lookups
CREATE INDEX IF NOT EXISTS idx_bhavcopy_mtf_date_symbol ON bhavcopy_mtf_stocks(trade_date, symbol);

COMMENT ON TABLE bhavcopy_mtf_stocks IS 'Daily bhavcopy data for stocks that have MTF activity';
COMMENT ON COLUMN bhavcopy_mtf_stocks.trade_date IS 'Trading date';
COMMENT ON COLUMN bhavcopy_mtf_stocks.symbol IS 'Stock symbol (must exist in stocks_master)';
COMMENT ON COLUMN bhavcopy_mtf_stocks.series IS 'Trading series (EQ, BE, etc.)';
COMMENT ON COLUMN bhavcopy_mtf_stocks.open_price IS 'Opening price';
COMMENT ON COLUMN bhavcopy_mtf_stocks.high_price IS 'Highest price of the day';
COMMENT ON COLUMN bhavcopy_mtf_stocks.low_price IS 'Lowest price of the day';
COMMENT ON COLUMN bhavcopy_mtf_stocks.close_price IS 'Closing price';
COMMENT ON COLUMN bhavcopy_mtf_stocks.last_price IS 'Last traded price';
COMMENT ON COLUMN bhavcopy_mtf_stocks.prev_close IS 'Previous day closing price';
COMMENT ON COLUMN bhavcopy_mtf_stocks.total_traded_qty IS 'Total quantity traded';
COMMENT ON COLUMN bhavcopy_mtf_stocks.turnover_lacs IS 'Turnover in lakhs';
COMMENT ON COLUMN bhavcopy_mtf_stocks.no_of_trades IS 'Number of trades';
COMMENT ON COLUMN bhavcopy_mtf_stocks.deliv_qty IS 'Delivery quantity';
COMMENT ON COLUMN bhavcopy_mtf_stocks.deliv_per IS 'Delivery percentage';
