-- Get 30-day historical MTF and price data for stocks in a specific index
-- This query joins MTF data with bhavcopy price data to show trends

WITH recent_dates AS (
    -- Get the last 30 trading days (not calendar days)
    SELECT DISTINCT trade_date 
    FROM mtf_daily 
    ORDER BY trade_date DESC
    LIMIT 30
),
index_stocks AS (
    SELECT DISTINCT symbol 
    FROM nifty_index_constituents 
    WHERE index_name = $1
),
daily_data AS (
    SELECT 
        m.trade_date,
        m.symbol,
        s.company_name,
        m.mtf_quantity,
        m.mtf_amount_cr,
        b.close_price,
        b.open_price,
        b.high_price,
        b.low_price,
        b.total_traded_qty as volume,
        b.deliv_per as delivery_pct,
        LAG(m.mtf_amount_cr) OVER (PARTITION BY m.symbol ORDER BY m.trade_date) as prev_mtf_cr,
        LAG(b.close_price) OVER (PARTITION BY m.symbol ORDER BY m.trade_date) as prev_close
    FROM mtf_daily m
    INNER JOIN recent_dates rd ON m.trade_date = rd.trade_date
    INNER JOIN index_stocks idx ON m.symbol = idx.symbol
    INNER JOIN stocks_master s ON m.symbol = s.symbol
    LEFT JOIN bhavcopy_mtf_stocks b ON m.symbol = b.symbol AND m.trade_date = b.trade_date
    WHERE m.mtf_amount_cr > 0
)
SELECT 
    symbol,
    company_name,
    trade_date,
    mtf_quantity,
    mtf_amount_cr,
    close_price,
    open_price,
    high_price,
    low_price,
    volume,
    delivery_pct,
    CASE 
        WHEN prev_mtf_cr IS NOT NULL THEN mtf_amount_cr - prev_mtf_cr
        ELSE 0
    END as mtf_change_cr,
    CASE 
        WHEN prev_close IS NOT NULL THEN close_price - prev_close
        ELSE 0
    END as price_change,
    CASE 
        WHEN prev_close IS NOT NULL AND prev_close > 0 THEN ((close_price - prev_close) / prev_close) * 100
        ELSE 0
    END as price_change_pct
FROM daily_data
ORDER BY symbol, trade_date;
