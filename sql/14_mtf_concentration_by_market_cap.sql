-- =====================================================
-- 14_mtf_concentration_by_market_cap.sql
-- Stock-level MTF concentration grouped by market cap category
-- =====================================================

WITH latest_day AS (
    SELECT MAX(trade_date) AS trade_date
    FROM mtf_daily
),

sanitized AS (
    SELECT
        d.trade_date,
        d.symbol,
        NULLIF(d.mtf_amount_cr, 'NaN'::numeric) AS mtf_amount_cr,
        s.market_cap_cr
    FROM mtf_daily d
    JOIN stocks_master s ON d.symbol = s.symbol
    WHERE
        d.symbol IS NOT NULL
        AND d.symbol ~ '^[A-Z0-9]+$'          -- 🔒 valid NSE symbols only
),

categorized AS (
    SELECT
        trade_date,
        symbol,
        mtf_amount_cr,
        market_cap_cr,
        CASE
            WHEN market_cap_cr >= 100000 THEN 'Large-High'
            WHEN market_cap_cr BETWEEN 70000 AND 99999 THEN 'Large-Low'
            WHEN market_cap_cr BETWEEN 50000 AND 69999 THEN 'Mid-High'
            WHEN market_cap_cr BETWEEN 30000 AND 49999 THEN 'Mid-Low'
            WHEN market_cap_cr BETWEEN 10000 AND 29999 THEN 'Small-High'
            WHEN market_cap_cr BETWEEN 5000 AND 9999 THEN 'Small-Low'
            WHEN market_cap_cr BETWEEN 1000 AND 4999 THEN 'Micro-High'
            WHEN market_cap_cr < 1000 THEN 'Micro-Low'
            ELSE 'Unknown'
        END AS market_cap_category
    FROM sanitized
),

category_totals AS (
    SELECT
        trade_date,
        market_cap_category,
        SUM(mtf_amount_cr) AS category_total_mtf_cr
    FROM categorized
    WHERE market_cap_category != 'Unknown'
    GROUP BY trade_date, market_cap_category
)

SELECT
    c.trade_date,
    c.symbol,
    c.market_cap_category,
    ROUND(c.mtf_amount_cr, 2) AS stock_mtf_cr,
    ROUND(c.market_cap_cr, 2) AS market_cap_cr,
    ROUND(100 * c.mtf_amount_cr / ct.category_total_mtf_cr, 2) AS category_share_pct
FROM categorized c
JOIN latest_day l ON c.trade_date = l.trade_date
JOIN category_totals ct 
    ON c.trade_date = ct.trade_date 
    AND c.market_cap_category = ct.market_cap_category
WHERE 
    c.mtf_amount_cr IS NOT NULL
    AND c.market_cap_category != 'Unknown'
ORDER BY 
    CASE c.market_cap_category
        WHEN 'Large-High' THEN 1
        WHEN 'Large-Low' THEN 2
        WHEN 'Mid-High' THEN 3
        WHEN 'Mid-Low' THEN 4
        WHEN 'Small-High' THEN 5
        WHEN 'Small-Low' THEN 6
        WHEN 'Micro-High' THEN 7
        WHEN 'Micro-Low' THEN 8
    END,
    category_share_pct DESC;
