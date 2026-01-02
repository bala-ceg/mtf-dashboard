-- =====================================================
-- 07_active_mtf_stock_trend.sql
-- Daily count of stocks with active MTF
-- =====================================================

SELECT
    trade_date,
    COUNT(DISTINCT symbol) AS active_mtf_stocks
FROM mtf_daily
GROUP BY trade_date
ORDER BY trade_date;
