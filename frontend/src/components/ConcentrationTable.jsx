import { formatCurrency } from '../utils/formatters';

export default function ConcentrationTable({ concentration }) {
  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">MTF Concentration (Top Stocks by Market Share)</h2>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Symbol</th>
              <th style={{ textAlign: 'right' }}>MTF Amount (₹ Cr)</th>
              <th style={{ textAlign: 'right' }}>Market Share (%)</th>
            </tr>
          </thead>
          <tbody>
            {concentration?.length > 0 ? (
              concentration.map((stock, idx) => (
                <tr key={stock.symbol}>
                  <td>{idx + 1}</td>
                  <td className="symbol">{stock.symbol}</td>
                  <td style={{ textAlign: 'right' }}>{formatCurrency(stock.stock_mtf_cr)}</td>
                  <td 
                    style={{ 
                      textAlign: 'right',
                      color: stock.mtf_share_pct > 1 ? 'var(--color-warning)' : 'inherit',
                      fontWeight: stock.mtf_share_pct > 1 ? '600' : 'normal'
                    }}
                  >
                    {stock.mtf_share_pct?.toFixed(2)}%
                    {stock.mtf_share_pct > 1 && ' ⚠️'}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
