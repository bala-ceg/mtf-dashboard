WITH ranked AS (
    SELECT
        trade_date,
        symbol,
        NULLIF(mtf_amount_cr, 'NaN'::numeric) AS mtf_amount_cr,
        LAG(NULLIF(mtf_amount_cr, 'NaN'::numeric))
            OVER (PARTITION BY symbol ORDER BY trade_date) AS prev_mtf_amount_cr
    FROM mtf_daily
),
deltas AS (
    SELECT
        trade_date,
        symbol,
        (mtf_amount_cr - prev_mtf_amount_cr) AS mtf_change_cr
    FROM ranked
    WHERE prev_mtf_amount_cr IS NOT NULL
),
latest_day AS (
    SELECT MAX(trade_date) AS trade_date
    FROM deltas
),
categorized AS (
    SELECT
        d.trade_date,
        d.symbol,
        d.mtf_change_cr,
        s.market_cap_cr,
        CASE
            WHEN s.market_cap_cr >= 100000 THEN 'Large-High'
            WHEN s.market_cap_cr BETWEEN 70000 AND 99999 THEN 'Large-Low'
            WHEN s.market_cap_cr BETWEEN 50000 AND 69999 THEN 'Mid-High'
            WHEN s.market_cap_cr BETWEEN 30000 AND 49999 THEN 'Mid-Low'
            WHEN s.market_cap_cr BETWEEN 10000 AND 29999 THEN 'Small-High'
            WHEN s.market_cap_cr BETWEEN 5000 AND 9999 THEN 'Small-Low'
            WHEN s.market_cap_cr BETWEEN 1000 AND 4999 THEN 'Micro-High'
            WHEN s.market_cap_cr < 1000 THEN 'Micro-Low'
            ELSE 'Unknown'
        END AS market_cap_category
    FROM deltas d
    JOIN latest_day l ON d.trade_date = l.trade_date
    JOIN stocks_master s ON d.symbol = s.symbol
    WHERE d.mtf_change_cr > 0
)
SELECT
    trade_date,
    symbol,
    ROUND(mtf_change_cr, 2) AS mtf_change_cr,
    market_cap_category
FROM categorized
WHERE market_cap_category != 'Unknown'
ORDER BY mtf_change_cr DESC;
