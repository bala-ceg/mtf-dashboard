-- =========================
-- MTF PRICE CORRELATION ANALYSIS
-- =========================
-- This query analyzes the correlation between MTF changes and stock price movements
-- for continuous movers to identify stocks where MTF buying/selling correlates with price

WITH continuous_movers AS (
    -- Get stocks with continuous MTF movement
    SELECT 
        symbol,
        direction,
        consecutive_days,
        streak_start_date,
        streak_end_date,
        total_change_cr
    FROM (
        SELECT 
            symbol,
            direction,
            consecutive_days,
            streak_start_date,
            streak_end_date,
            total_change_cr,
            ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY consecutive_days DESC) as rn
        FROM (
            -- Existing continuous movers logic
            WITH daily_changes AS (
                SELECT 
                    trade_date,
                    symbol,
                    mtf_amount_cr,
                    mtf_amount_cr - LAG(mtf_amount_cr) OVER (PARTITION BY symbol ORDER BY trade_date) AS daily_change
                FROM mtf_daily
                WHERE trade_date >= CURRENT_DATE - INTERVAL '30 days'
            ),
            directional_changes AS (
                SELECT 
                    trade_date,
                    symbol,
                    daily_change,
                    CASE 
                        WHEN daily_change > 0 THEN 'positive'
                        WHEN daily_change < 0 THEN 'negative'
                        ELSE 'neutral'
                    END AS direction
                FROM daily_changes
                WHERE daily_change IS NOT NULL
            ),
            streak_groups AS (
                SELECT 
                    trade_date,
                    symbol,
                    direction,
                    daily_change,
                    SUM(CASE WHEN prev_direction != direction THEN 1 ELSE 0 END) OVER (
                        PARTITION BY symbol ORDER BY trade_date
                    ) AS streak_group
                FROM (
                    SELECT 
                        trade_date,
                        symbol,
                        direction,
                        daily_change,
                        LAG(direction) OVER (PARTITION BY symbol ORDER BY trade_date) AS prev_direction
                    FROM directional_changes
                ) sub
            )
            SELECT 
                symbol,
                direction,
                COUNT(*) AS consecutive_days,
                MIN(trade_date) AS streak_start_date,
                MAX(trade_date) AS streak_end_date,
                SUM(daily_change) AS total_change_cr
            FROM streak_groups
            WHERE direction = 'positive'
            GROUP BY symbol, direction, streak_group
            HAVING COUNT(*) >= 3
        ) streaks
    ) ranked
    WHERE rn = 1
),
daily_data AS (
    -- Get daily MTF and price data for these stocks
    SELECT 
        cm.symbol,
        cm.direction,
        cm.consecutive_days,
        cm.streak_start_date,
        cm.streak_end_date,
        cm.total_change_cr,
        m.trade_date,
        m.mtf_amount_cr,
        m.mtf_quantity,
        b.close_price,
        b.open_price,
        b.high_price,
        b.low_price,
        b.total_traded_qty,
        b.deliv_qty,
        b.deliv_per,
        -- Calculate day-over-day changes
        m.mtf_amount_cr - LAG(m.mtf_amount_cr) OVER (PARTITION BY m.symbol ORDER BY m.trade_date) as mtf_value_change,
        m.mtf_quantity - LAG(m.mtf_quantity) OVER (PARTITION BY m.symbol ORDER BY m.trade_date) as mtf_qty_change,
        b.close_price - LAG(b.close_price) OVER (PARTITION BY b.symbol ORDER BY b.trade_date) as price_change,
        ((b.close_price - LAG(b.close_price) OVER (PARTITION BY b.symbol ORDER BY b.trade_date)) / 
         NULLIF(LAG(b.close_price) OVER (PARTITION BY b.symbol ORDER BY b.trade_date), 0) * 100) as price_change_pct
    FROM continuous_movers cm
    INNER JOIN mtf_daily m ON cm.symbol = m.symbol
    INNER JOIN bhavcopy_mtf_stocks b ON m.symbol = b.symbol AND m.trade_date = b.trade_date
    WHERE m.trade_date BETWEEN cm.streak_start_date - INTERVAL '5 days' AND cm.streak_end_date + INTERVAL '2 days'
),
correlation_metrics AS (
    -- Calculate correlation metrics for each stock
    SELECT 
        symbol,
        direction,
        consecutive_days,
        streak_start_date,
        streak_end_date,
        total_change_cr,
        COUNT(*) as data_points,
        -- MTF statistics
        SUM(mtf_value_change) as total_mtf_change,
        AVG(mtf_value_change) as avg_mtf_change,
        SUM(mtf_qty_change) as total_qty_change,
        -- Price statistics
        SUM(price_change) as total_price_change,
        AVG(price_change) as avg_price_change,
        AVG(price_change_pct) as avg_price_change_pct,
        -- Simple correlation indicator (positive if both move in same direction)
        SUM(CASE 
            WHEN (mtf_value_change > 0 AND price_change > 0) OR 
                 (mtf_value_change < 0 AND price_change < 0) THEN 1 
            ELSE 0 
        END)::FLOAT / NULLIF(COUNT(*), 0) * 100 as correlation_score,
        -- Collect daily data for charting
        json_agg(
            json_build_object(
                'trade_date', trade_date,
                'mtf_amount_cr', mtf_amount_cr,
                'mtf_quantity', mtf_quantity,
                'close_price', close_price,
                'open_price', open_price,
                'high_price', high_price,
                'low_price', low_price,
                'mtf_value_change', mtf_value_change,
                'mtf_qty_change', mtf_qty_change,
                'price_change', price_change,
                'price_change_pct', price_change_pct,
                'volume', total_traded_qty,
                'delivery_pct', deliv_per
            ) ORDER BY trade_date
        ) as daily_data
    FROM daily_data
    WHERE mtf_value_change IS NOT NULL AND price_change IS NOT NULL
    GROUP BY symbol, direction, consecutive_days, streak_start_date, streak_end_date, total_change_cr
)
SELECT 
    cm.symbol,
    sm.company_name,
    sm.market_cap_cr,
    CASE 
        WHEN sm.market_cap_cr >= 100000 THEN 'Large-High'
        WHEN sm.market_cap_cr >= 70000 THEN 'Large-Low'
        WHEN sm.market_cap_cr >= 50000 THEN 'Mid-High'
        WHEN sm.market_cap_cr >= 30000 THEN 'Mid-Low'
        WHEN sm.market_cap_cr >= 10000 THEN 'Small-High'
        WHEN sm.market_cap_cr >= 5000 THEN 'Small-Low'
        WHEN sm.market_cap_cr >= 1000 THEN 'Micro-High'
        ELSE 'Micro-Low'
    END as market_cap_category,
    cm.direction,
    cm.consecutive_days,
    cm.streak_start_date,
    cm.streak_end_date,
    cm.total_change_cr,
    cm.data_points,
    cm.total_mtf_change,
    cm.avg_mtf_change,
    cm.total_qty_change,
    cm.total_price_change,
    cm.avg_price_change,
    cm.avg_price_change_pct,
    cm.correlation_score,
    cm.daily_data
FROM correlation_metrics cm
INNER JOIN stocks_master sm ON cm.symbol = sm.symbol
ORDER BY cm.correlation_score DESC, cm.total_change_cr DESC;
