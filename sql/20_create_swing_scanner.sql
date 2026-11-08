-- Additive migration: leaves the existing MTF tables untouched.
CREATE TABLE IF NOT EXISTS swing_daily_bhavcopy (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    series TEXT NOT NULL DEFAULT 'EQ',
    prev_close NUMERIC(18,4),
    open_price NUMERIC(18,4),
    high_price NUMERIC(18,4),
    low_price NUMERIC(18,4),
    last_price NUMERIC(18,4),
    close_price NUMERIC(18,4),
    avg_price NUMERIC(18,4),
    traded_quantity BIGINT NOT NULL DEFAULT 0,
    turnover_cr NUMERIC(20,4),
    number_of_trades BIGINT,
    delivery_quantity BIGINT,
    delivery_pct NUMERIC(8,4),
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trade_date, symbol, series),
    CHECK (traded_quantity >= 0),
    CHECK (delivery_quantity IS NULL OR delivery_quantity >= 0)
);
CREATE INDEX IF NOT EXISTS idx_swing_bhavcopy_symbol_date
    ON swing_daily_bhavcopy(symbol, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_swing_bhavcopy_date_volume
    ON swing_daily_bhavcopy(trade_date, traded_quantity DESC);

CREATE TABLE IF NOT EXISTS swing_index_constituents (
    index_name TEXT NOT NULL DEFAULT 'NIFTY_TOTAL_MARKET',
    symbol TEXT NOT NULL,
    company_name TEXT,
    isin TEXT,
    sector TEXT,
    weight_pct NUMERIC(10,6),
    effective_from DATE NOT NULL,
    effective_to DATE,
    source_file TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (index_name, symbol, effective_from)
);
CREATE INDEX IF NOT EXISTS idx_swing_constituents_current
    ON swing_index_constituents(index_name, symbol)
    WHERE effective_to IS NULL;

CREATE TABLE IF NOT EXISTS swing_index_daily (
    index_name TEXT NOT NULL,
    trade_date DATE NOT NULL,
    close_value NUMERIC(18,4) NOT NULL,
    source_file TEXT,
    PRIMARY KEY (index_name, trade_date)
);

CREATE TABLE IF NOT EXISTS swing_daily_features (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    close_price NUMERIC(18,4),
    traded_quantity BIGINT,
    turnover_cr NUMERIC(20,4),
    delivery_pct NUMERIC(8,4),
    rvol_20 NUMERIC(12,4),
    turnover_rvol_20 NUMERIC(12,4),
    delivery_pct_avg_20 NUMERIC(8,4),
    delivery_pct_delta_20 NUMERIC(8,4),
    clv NUMERIC(10,6),
    obv NUMERIC(24,4),
    obv_change_20 NUMERIC(12,6),
    cmf_20 NUMERIC(12,6),
    atr_pct_14 NUMERIC(12,6),
    return_5d NUMERIC(12,6),
    return_20d NUMERIC(12,6),
    relative_strength_20d NUMERIC(12,6),
    accumulation_score NUMERIC(8,2),
    distribution_score NUMERIC(8,2),
    data_quality_score NUMERIC(8,2),
    signal TEXT NOT NULL,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    strategy_version TEXT NOT NULL DEFAULT 'swing-v1',
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trade_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_swing_features_date_score
    ON swing_daily_features(trade_date, accumulation_score DESC);
CREATE INDEX IF NOT EXISTS idx_swing_features_symbol_date
    ON swing_daily_features(symbol, trade_date DESC);

CREATE TABLE IF NOT EXISTS swing_ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    dataset TEXT NOT NULL,
    trade_date DATE,
    source_file TEXT,
    rows_loaded INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
