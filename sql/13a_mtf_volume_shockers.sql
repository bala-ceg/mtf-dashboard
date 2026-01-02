-- =====================================================
-- 13a_mtf_volume_shockers.sql
-- Identify MTF volume shockers based on quantity
-- Top 10 positive and negative movers in past 10 trading sessions
-- =====================================================

WITH recent_dates AS (
    -- Get the last 10 trading dates
    SELECT DISTINCT trade_date
    FROM mtf_daily
    ORDER BY trade_date DESC
    LIMIT 10
),

mtf_data AS (
    -- Get MTF volume data with market cap categories
    SELECT
        d.trade_date,
        d.symbol,
        s.market_cap_cr,
        d.mtf_quantity,
        d.mtf_amount_cr,
        CASE
            WHEN s.market_cap_cr BETWEEN 70000 AND 99999 THEN 'Large-Low'
            WHEN s.market_cap_cr >= 100000 THEN 'Large-High'
            WHEN s.market_cap_cr BETWEEN 30000 AND 49999 THEN 'Mid-Low'
            WHEN s.market_cap_cr BETWEEN 50000 AND 69999 THEN 'Mid-High'
            WHEN s.market_cap_cr BETWEEN 5000 AND 9999 THEN 'Small-Low'
            WHEN s.market_cap_cr BETWEEN 10000 AND 29999 THEN 'Small-High'
            WHEN s.market_cap_cr < 5000 THEN 'Micro-Low'
            WHEN s.market_cap_cr BETWEEN 5000 AND 9999 THEN 'Micro-High'
            ELSE 'Unknown'
        END AS market_cap_category
    FROM mtf_daily d
    JOIN stocks_master s ON d.symbol = s.symbol
    JOIN recent_dates rd ON d.trade_date = rd.trade_date
    WHERE d.symbol ~ '^[A-Z0-9]+$'
        AND d.mtf_quantity IS NOT NULL
        AND d.mtf_amount_cr IS NOT NULL
),

-- Calculate statistics for each stock
stock_stats AS (
    SELECT
        symbol,
        market_cap_category,
        COUNT(*) AS trading_days,
        ROUND(AVG(mtf_quantity), 2) AS avg_qty_10d,
        ROUND(STDDEV(mtf_quantity), 2) AS stddev_qty_10d,
        MIN(mtf_quantity) AS min_qty,
        MAX(mtf_quantity) AS max_qty,
        ROUND(AVG(mtf_amount_cr), 2) AS avg_amount_10d,
        ROUND(STDDEV(mtf_amount_cr), 2) AS stddev_amount_10d
    FROM mtf_data
    WHERE mtf_quantity IS NOT NULL
    GROUP BY symbol, market_cap_category
    HAVING COUNT(*) >= 5  -- At least 5 data points
),

-- Calculate daily deviations and identify shockers
daily_analysis AS (
    SELECT
        d.trade_date,
        d.symbol,
        d.market_cap_category,
        d.mtf_quantity,
        d.mtf_amount_cr,
        s.avg_qty_10d,
        s.stddev_qty_10d,
        s.avg_amount_10d,
        s.stddev_amount_10d,
        ROUND((d.mtf_quantity - s.avg_qty_10d) / NULLIF(s.stddev_qty_10d, 0), 2) AS z_score,
        CASE
            WHEN (d.mtf_quantity - s.avg_qty_10d) / NULLIF(s.stddev_qty_10d, 0) > 2 THEN 'High Positive Shocker'
            WHEN (d.mtf_quantity - s.avg_qty_10d) / NULLIF(s.stddev_qty_10d, 0) < -2 THEN 'High Negative Shocker'
            WHEN (d.mtf_quantity - s.avg_qty_10d) / NULLIF(s.stddev_qty_10d, 0) > 1 THEN 'Moderate Positive Shocker'
            WHEN (d.mtf_quantity - s.avg_qty_10d) / NULLIF(s.stddev_qty_10d, 0) < -1 THEN 'Moderate Negative Shocker'
            ELSE 'Normal'
        END AS shocker_type,
        ROUND(d.mtf_quantity - s.avg_qty_10d, 2) AS deviation_from_avg_qty
    FROM mtf_data d
    JOIN stock_stats s ON d.symbol = s.symbol AND d.market_cap_category = s.market_cap_category
),

-- Rank shockers by category and date for past 10 days
ranked_shockers AS (
    SELECT
        da.trade_date,
        da.symbol,
        da.market_cap_category,
        da.mtf_quantity,
        da.mtf_amount_cr,
        da.avg_qty_10d,
        da.stddev_qty_10d,
        da.avg_amount_10d,
        da.stddev_amount_10d,
        da.z_score,
        da.shocker_type,
        da.deviation_from_avg_qty,
        ROW_NUMBER() OVER (
            PARTITION BY da.market_cap_category, da.trade_date
            ORDER BY ABS(da.z_score) DESC, ABS(da.deviation_from_avg_qty) DESC
        ) AS rank_in_category_date
    FROM daily_analysis da
    WHERE da.shocker_type IN ('High Positive Shocker', 'High Negative Shocker', 
                              'Moderate Positive Shocker', 'Moderate Negative Shocker')
)

-- Final result: Top 10 shockers per category per day for past 10 days
SELECT
    trade_date,
    symbol,
    market_cap_category,
    mtf_quantity,
    ROUND(avg_qty_10d, 2) AS avg_qty_10d,
    ROUND(stddev_qty_10d, 2) AS stddev_qty_10d,
    ROUND(mtf_amount_cr, 2) AS mtf_amount_cr,
    ROUND(avg_amount_10d, 2) AS avg_amount_10d,
    ROUND(stddev_amount_10d, 2) AS stddev_amount_10d,
    ROUND(z_score, 2) AS z_score,
    shocker_type,
    ROUND(deviation_from_avg_qty, 2) AS deviation_from_avg_qty
FROM ranked_shockers
WHERE rank_in_category_date <= 10
ORDER BY 
    trade_date DESC,
    CASE market_cap_category
        WHEN 'Large-High' THEN 1
        WHEN 'Large-Low' THEN 2
        WHEN 'Mid-High' THEN 3
        WHEN 'Mid-Low' THEN 4
        WHEN 'Small-High' THEN 5
        WHEN 'Small-Low' THEN 6
        WHEN 'Micro-High' THEN 7
        WHEN 'Micro-Low' THEN 8
        ELSE 9
    END,
    ABS(z_score) DESC;
