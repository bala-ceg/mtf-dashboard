-- =====================================================
-- 05_mtf_percent_movers.sql
-- Top stocks by % change in MTF (latest day)
-- Hardened against NULLs and tiny bases
-- =====================================================

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
        mtf_amount_cr,
        prev_mtf_amount_cr,
        100 * (mtf_amount_cr - prev_mtf_amount_cr)
            / prev_mtf_amount_cr AS mtf_pct_change
    FROM ranked
    WHERE
        prev_mtf_amount_cr IS NOT NULL
        AND prev_mtf_amount_cr >= 5        -- 🔒 minimum base (₹ 5 Cr)
        AND mtf_amount_cr IS NOT NULL
),

latest_day AS (
    SELECT MAX(trade_date) AS trade_date
    FROM deltas
)

SELECT
    d.trade_date,
    d.symbol,
    ROUND(d.mtf_pct_change, 2) AS mtf_pct_change
FROM deltas d
JOIN latest_day l
  ON d.trade_date = l.trade_date
ORDER BY mtf_pct_change DESC
LIMIT 20;
