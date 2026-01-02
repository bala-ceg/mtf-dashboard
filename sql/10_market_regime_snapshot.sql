-- =====================================================
-- 08_market_regime_snapshot.sql
-- Market-level leverage regime (latest day)
-- =====================================================

WITH latest_day AS (
    SELECT MAX(trade_date) AS trade_date
    FROM mtf_market_daily
)
SELECT
    m.trade_date,

    ROUND(NULLIF(m.opening_outstanding_cr, 'NaN'::numeric), 2)
        AS opening_outstanding_cr,

    ROUND(NULLIF(m.closing_outstanding_cr, 'NaN'::numeric), 2)
        AS closing_outstanding_cr,

    ROUND(NULLIF(m.fresh_exposure_cr, 'NaN'::numeric), 2)
        AS fresh_exposure_cr,

    ROUND(NULLIF(m.liquidated_exposure_cr, 'NaN'::numeric), 2)
        AS liquidated_exposure_cr,

    ROUND(
        COALESCE(NULLIF(m.fresh_exposure_cr, 'NaN'::numeric), 0)
        -
        COALESCE(NULLIF(m.liquidated_exposure_cr, 'NaN'::numeric), 0),
        2
    ) AS net_flow_cr

FROM mtf_market_daily m
JOIN latest_day l
  ON m.trade_date = l.trade_date;