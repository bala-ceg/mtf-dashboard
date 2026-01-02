-- Query to get top 10 stocks by MTF holdings for each Nifty index category
-- This shows which stocks in each index have the highest MTF exposure

WITH latest_mtf AS (
    SELECT 
        symbol,
        mtf_quantity as client_mtf_qty,
        mtf_amount_cr as client_mtf_val,
        trade_date
    FROM mtf_daily
    WHERE trade_date = (SELECT MAX(trade_date) FROM mtf_daily)
),
index_mtf AS (
    SELECT 
        nic.index_name,
        nic.symbol,
        nic.company_name,
        nic.industry,
        lm.client_mtf_qty,
        lm.client_mtf_val,
        lm.trade_date,
        s.market_cap_cr,
        ROW_NUMBER() OVER (PARTITION BY nic.index_name ORDER BY lm.client_mtf_val DESC) as rank
    FROM nifty_index_constituents nic
    INNER JOIN latest_mtf lm ON nic.symbol = lm.symbol
    LEFT JOIN stocks_master s ON nic.symbol = s.symbol
)
SELECT 
    index_name,
    symbol,
    company_name,
    industry,
    client_mtf_qty,
    client_mtf_val,
    market_cap_cr,
    trade_date,
    rank
FROM index_mtf
WHERE rank <= 10
ORDER BY index_name, rank;
