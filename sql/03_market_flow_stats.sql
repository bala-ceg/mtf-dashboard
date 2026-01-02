-- =====================================================
-- 02_market_flow_stats.sql
-- Market-level MTF flow statistics (daily)
-- =====================================================

SELECT
    trade_date,

    -- Fresh exposure taken during the day (₹ Cr)
    ROUND(
        NULLIF(fresh_exposure_cr, 'NaN'::numeric),
        2
    ) AS fresh_exposure_cr,

    -- Exposure liquidated during the day (₹ Cr)
    ROUND(
        NULLIF(liquidated_exposure_cr, 'NaN'::numeric),
        2
    ) AS liquidated_exposure_cr,

    -- Net flow = Fresh - Liquidation (₹ Cr)
    ROUND(
        COALESCE(NULLIF(fresh_exposure_cr, 'NaN'::numeric), 0)
        -
        COALESCE(NULLIF(liquidated_exposure_cr, 'NaN'::numeric), 0),
        2
    ) AS net_flow_cr

FROM mtf_market_daily
ORDER BY trade_date DESC;
