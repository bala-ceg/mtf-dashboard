import { formatCurrency, formatNumber, formatDate } from '../utils/formatters';

export default function MarketOverviewCards({ overview, regime, flow }) {
  return (
    <>
      {/* Regime Badge */}
      {regime && (
        <div className={`regime-badge regime-${regime.regime?.toLowerCase().replace('_', '-')}`}>
          <span>Market Regime: {regime.regime}</span>
          <span>
            {regime.regime === 'RISK_ON' && '🟢'}
            {regime.regime === 'NEUTRAL' && '🟡'}
            {regime.regime === 'RISK_OFF' && '🔴'}
          </span>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="metrics-grid">
        {/* Total MTF */}
        {overview && (
          <div className="metric-card">
            <div className="metric-label">Total MTF Outstanding</div>
            <div className="metric-value">
              ₹{formatCurrency(overview.total_mtf_cr)}
              <span className="metric-unit">Cr</span>
            </div>
          </div>
        )}

        {/* Net Flow */}
        {flow && (
          <div className="metric-card">
            <div className="metric-label">Net Flow (Today)</div>
            <div className="metric-value">
              ₹{formatCurrency(Math.abs(flow.net_flow_cr || 0))}
              <span className="metric-unit">Cr</span>
            </div>
            <div className={`metric-change ${flow.net_flow_cr >= 0 ? 'positive' : 'negative'}`}>
              {flow.net_flow_cr >= 0 ? '↑' : '↓'} {flow.net_flow_cr >= 0 ? 'Inflow' : 'Outflow'}
            </div>
          </div>
        )}

        {/* Active Stocks */}
        {overview && (
          <div className="metric-card">
            <div className="metric-label">Active MTF Stocks</div>
            <div className="metric-value">{formatNumber(overview.active_mtf_stocks)}</div>
          </div>
        )}

        {/* Fresh Exposure */}
        {flow && (
          <div className="metric-card">
            <div className="metric-label">Fresh Exposure</div>
            <div className="metric-value">
              ₹{formatCurrency(flow.fresh_exposure_cr)}
              <span className="metric-unit">Cr</span>
            </div>
          </div>
        )}

        {/* Liquidated Exposure */}
        {flow && (
          <div className="metric-card">
            <div className="metric-label">Liquidated Exposure</div>
            <div className="metric-value">
              ₹{formatCurrency(flow.liquidated_exposure_cr)}
              <span className="metric-unit">Cr</span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
