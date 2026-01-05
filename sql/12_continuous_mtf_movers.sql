-- =====================================================
-- 12_continuous_mtf_movers.sql
-- Identify stocks with continuous MTF changes (positive/negative)
-- for the last 10 trading sessions across all market cap categories
-- =====================================================

WITH recent_dates AS (
    -- Get the last 10 trading dates
    SELECT DISTINCT trade_date
    FROM mtf_daily
    ORDER BY trade_date DESC
    LIMIT 10
),

ranked_mtf AS (
    -- Calculate daily MTF changes with market cap categories
    SELECT
        d.trade_date,
        d.symbol,
        s.market_cap_cr,
        NULLIF(d.mtf_amount_cr, 'NaN'::numeric) AS mtf_amount_cr,
        LAG(NULLIF(d.mtf_amount_cr, 'NaN'::numeric))
            OVER (PARTITION BY d.symbol ORDER BY d.trade_date) AS prev_mtf_amount_cr,
        (NULLIF(d.mtf_amount_cr, 'NaN'::numeric) - 
         LAG(NULLIF(d.mtf_amount_cr, 'NaN'::numeric))
            OVER (PARTITION BY d.symbol ORDER BY d.trade_date)) AS mtf_change_cr,
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
),

-- Determine direction (positive/negative) for each trading day
direction_marked AS (
    SELECT
        *,
        CASE
            WHEN mtf_change_cr > 0 THEN 'positive'
            WHEN mtf_change_cr < 0 THEN 'negative'
            ELSE 'neutral'
        END AS direction
    FROM ranked_mtf
    WHERE prev_mtf_amount_cr IS NOT NULL
),

-- Group continuous streaks
streaks AS (
    SELECT
        symbol,
        market_cap_category,
        direction,
        trade_date,
        ROW_NUMBER() OVER (PARTITION BY symbol, market_cap_category ORDER BY trade_date) -
        ROW_NUMBER() OVER (PARTITION BY symbol, market_cap_category, direction ORDER BY trade_date) AS streak_id
    FROM direction_marked
    WHERE direction = 'positive'  -- Only buy direction stocks
),

-- Count continuous occurrences
streak_counts AS (
    SELECT
        symbol,
        market_cap_category,
        direction,
        MIN(trade_date) AS streak_start_date,
        MAX(trade_date) AS streak_end_date,
        COUNT(*) AS consecutive_days,
        ROUND(AVG(ABS(mtf_change_cr)), 2) AS avg_daily_change_cr,
        ROUND(SUM(mtf_change_cr), 2) AS total_change_cr
    FROM streaks
    JOIN direction_marked USING (symbol, market_cap_category, direction, trade_date)
    GROUP BY symbol, market_cap_category, direction, streak_id
    HAVING COUNT(*) >= 3  -- Only streaks of 3+ consecutive days
),

-- Final result with category breakdown - Top 10 per category
ranked_results AS (
    SELECT
        market_cap_category,
        symbol,
        direction,
        consecutive_days,
        streak_start_date,
        streak_end_date,
        avg_daily_change_cr,
        total_change_cr,
        CASE direction
            WHEN 'positive' THEN '📈 Continuous Buying'
            WHEN 'negative' THEN '📉 Continuous Selling'
        END AS trend_label,
        ROW_NUMBER() OVER (
            PARTITION BY market_cap_category 
            ORDER BY consecutive_days DESC, total_change_cr DESC
        ) AS rn
    FROM streak_counts
)

SELECT
    market_cap_category,
    symbol,
    direction,
    consecutive_days,
    streak_start_date,
    streak_end_date,
    avg_daily_change_cr,
    total_change_cr,
    trend_label
FROM ranked_results
WHERE rn <= 10
ORDER BY 
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
    rn;
