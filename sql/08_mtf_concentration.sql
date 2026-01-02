-- =====================================================
-- 06_mtf_concentration.sql
-- Stock-level MTF concentration (latest day)
-- Filters NSE footer / note rows
-- =====================================================

WITH latest_day AS (
    SELECT MAX(trade_date) AS trade_date
    FROM mtf_daily
),

sanitized AS (
    SELECT
        trade_date,
        symbol,
        NULLIF(mtf_amount_cr, 'NaN'::numeric) AS mtf_amount_cr
    FROM mtf_daily
    WHERE
        symbol IS NOT NULL
        AND symbol ~ '^[A-Z0-9]+$'          -- 🔒 valid NSE symbols only
),

totals AS (
    SELECT
        trade_date,
        SUM(mtf_amount_cr) AS total_mtf_cr
    FROM sanitized
    GROUP BY trade_date
)

SELECT
    s.trade_date,
    s.symbol,
    ROUND(s.mtf_amount_cr, 2) AS stock_mtf_cr,
    ROUND(100 * s.mtf_amount_cr / t.total_mtf_cr, 2) AS mtf_share_pct
FROM sanitized s
JOIN latest_day l
  ON s.trade_date = l.trade_date
JOIN totals t
  ON s.trade_date = t.trade_date
WHERE s.mtf_amount_cr IS NOT NULL
ORDER BY mtf_share_pct DESC
LIMIT 20;
