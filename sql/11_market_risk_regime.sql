-- =====================================================
-- 09_market_risk_regime.sql
-- Market Risk Regime Classification using MTF flows
-- =====================================================

SELECT
    trade_date,

    ROUND(NULLIF(opening_outstanding_cr, 'NaN'::numeric), 2)
        AS opening_outstanding_cr,

    ROUND(NULLIF(closing_outstanding_cr, 'NaN'::numeric), 2)
        AS closing_outstanding_cr,

    ROUND(NULLIF(fresh_exposure_cr, 'NaN'::numeric), 2)
        AS fresh_exposure_cr,

    ROUND(NULLIF(liquidated_exposure_cr, 'NaN'::numeric), 2)
        AS liquidated_exposure_cr,

    ROUND(
        COALESCE(NULLIF(fresh_exposure_cr, 'NaN'::numeric), 0)
        -
        COALESCE(NULLIF(liquidated_exposure_cr, 'NaN'::numeric), 0),
        2
    ) AS net_flow_cr,

    CASE
        WHEN (
            COALESCE(NULLIF(fresh_exposure_cr, 'NaN'::numeric), 0)
            -
            COALESCE(NULLIF(liquidated_exposure_cr, 'NaN'::numeric), 0)
        ) > 500
            THEN 'RISK_ON'

        WHEN (
            COALESCE(NULLIF(fresh_exposure_cr, 'NaN'::numeric), 0)
            -
            COALESCE(NULLIF(liquidated_exposure_cr, 'NaN'::numeric), 0)
        ) < -500
            THEN 'RISK_OFF'

        ELSE 'NEUTRAL'
    END AS market_regime

FROM mtf_market_daily
ORDER BY trade_date DESC;
