WITH latest_day AS (
    SELECT MAX(trade_date) AS trade_date
    FROM mtf_daily
)
SELECT
    d.trade_date,
    ROUND(
        SUM(
            NULLIF(d.mtf_amount_cr, 'NaN'::numeric)
        ),
        2
    ) AS total_mtf_cr,
    COUNT(DISTINCT d.symbol) AS active_mtf_stocks
FROM mtf_daily d
JOIN latest_day l
  ON d.trade_date = l.trade_date
GROUP BY d.trade_date;