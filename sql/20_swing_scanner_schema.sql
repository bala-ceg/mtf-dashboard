-- NIFTY Total Market swing scanner (additive migration).
-- Cash-market universe is deliberately independent of MTF participation.
CREATE TABLE IF NOT EXISTS cash_market_daily (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    series TEXT NOT NULL DEFAULT 'EQ',
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
    source_file TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trade_date, symbol, series)
);
CREATE INDEX IF NOT EXISTS idx_cash_market_daily_symbol_date
    ON cash_market_daily (symbol, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_cash_market_daily_date
    ON cash_market_daily (trade_date DESC);

CREATE TABLE IF NOT EXISTS swing_scanner_features (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    close_price NUMERIC,
    volume BIGINT,
    turnover_lacs NUMERIC,
    delivery_qty BIGINT,
    delivery_pct NUMERIC,
    avg_volume_20 NUMERIC,
    relative_volume NUMERIC,
    avg_turnover_20 NUMERIC,
    relative_turnover NUMERIC,
    close_location_value NUMERIC,
    obv NUMERIC,
    obv_change_5 NUMERIC,
    ad_line NUMERIC,
    cmf_20 NUMERIC,
    mfi_14 NUMERIC,
    atr_14 NUMERIC,
    vwap_deviation_pct NUMERIC,
    return_5d_pct NUMERIC,
    return_20d_pct NUMERIC,
    relative_strength_20d_pct NUMERIC,
    delivery_pct_avg_20 NUMERIC,
    delivery_pct_delta NUMERIC,
    accumulation_score NUMERIC,
    distribution_score NUMERIC,
    signal TEXT NOT NULL DEFAULT 'NEUTRAL',
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    data_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    strategy_version TEXT NOT NULL DEFAULT 'swing-v1',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (trade_date, symbol)
);
CREATE INDEX IF NOT EXISTS idx_swing_features_date_signal_score
    ON swing_scanner_features (trade_date DESC, signal, accumulation_score DESC);
CREATE INDEX IF NOT EXISTS idx_swing_features_symbol_date
    ON swing_scanner_features (symbol, trade_date DESC);

CREATE TABLE IF NOT EXISTS swing_scanner_runs (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    universe_count INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    feature_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    strategy_version TEXT NOT NULL DEFAULT 'swing-v1'
);
CREATE INDEX IF NOT EXISTS idx_swing_scanner_runs_date
    ON swing_scanner_runs (trade_date DESC, started_at DESC);

COMMENT ON TABLE cash_market_daily IS
    'Full NSE cash-market bhavcopy universe. Not restricted to MTF stocks.';
COMMENT ON TABLE swing_scanner_features IS
    'Daily swing accumulation/distribution features derived from cash_market_daily.';
