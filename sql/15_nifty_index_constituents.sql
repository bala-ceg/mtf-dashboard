-- Table to store Nifty index constituents
CREATE TABLE IF NOT EXISTS nifty_index_constituents (
    id SERIAL PRIMARY KEY,
    index_name VARCHAR(50) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(255),
    symbol VARCHAR(50) NOT NULL,
    series VARCHAR(10),
    isin_code VARCHAR(20),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(index_name, symbol)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_nifty_constituents_symbol ON nifty_index_constituents(symbol);
CREATE INDEX IF NOT EXISTS idx_nifty_constituents_index_name ON nifty_index_constituents(index_name);

-- Add comment
COMMENT ON TABLE nifty_index_constituents IS 'Stores constituent stocks for various Nifty indices (Nifty 50, Next 50, Smallcap 50, etc.)';
