import { useState } from 'react';
import { formatCurrency } from '../utils/formatters';

const IndexMTFHoldings = ({ data }) => {
  const [selectedIndex, setSelectedIndex] = useState('NIFTY50');

  if (!data || data.length === 0) {
    return (
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Top MTF Holdings by Index</h2>
        </div>
        <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
          No index MTF data available. Please run the index data loader.
        </div>
      </div>
    );
  }

  // Group data by index
  const groupedData = data.reduce((acc, row) => {
    if (!acc[row.index_name]) {
      acc[row.index_name] = [];
    }
    acc[row.index_name].push(row);
    return acc;
  }, {});

  // Define index order (excluding Nifty 500)
  const indexOrder = ['NIFTY50', 'NIFTY_NEXT50', 'NIFTY_MIDCAP50', 'NIFTY_SMALLCAP50'];
  const indexNames = indexOrder.filter(name => groupedData[name]);

  // Get display name for index
  const getIndexDisplayName = (indexName) => {
    const nameMap = {
      'NIFTY50': 'Nifty 50',
      'NIFTY_NEXT50': 'Nifty Next 50',
      'NIFTY_SMALLCAP50': 'Nifty Smallcap 50',
      'NIFTY_MIDCAP50': 'Nifty Midcap 50'
    };
    return nameMap[indexName] || indexName;
  };

  // Get current stocks to display
  const currentStocks = groupedData[selectedIndex] || [];

  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">Top MTF Holdings by Index</h2>
      </div>

      {/* Index Tabs */}
      <div className="tabs">
        {indexNames.map(indexName => (
          <button
            key={indexName}
            className={`tab ${selectedIndex === indexName ? 'active' : ''}`}
            onClick={() => setSelectedIndex(indexName)}
          >
            {getIndexDisplayName(indexName)}
          </button>
        ))}
      </div>

      {/* Table */}
      <IndexTable stocks={currentStocks} />
    </div>
  );
};

const IndexTable = ({ stocks }) => {
  if (!stocks || stocks.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
        No data available for this index.
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: '60px' }}>Rank</th>
            <th>Symbol</th>
            <th>Company</th>
            <th>Industry</th>
            <th style={{ textAlign: 'right' }}>MTF Quantity</th>
            <th style={{ textAlign: 'right' }}>MTF Value (₹ Cr)</th>
            <th style={{ textAlign: 'right' }}>Market Cap (₹ Cr)</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock, idx) => (
            <tr key={`${stock.symbol}-${idx}`}>
              <td>
                <span style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  backgroundColor: stock.rank <= 3 ? 'rgba(251, 191, 36, 0.2)' : 'var(--color-surface-light)',
                  color: stock.rank <= 3 ? 'var(--color-warning)' : 'var(--color-text-secondary)',
                  fontWeight: '600',
                  fontSize: '13px',
                  border: stock.rank <= 3 ? '1px solid var(--color-warning)' : '1px solid var(--color-border)'
                }}>
                  {stock.rank}
                </span>
              </td>
              <td className="symbol">{stock.symbol}</td>
              <td>{stock.company_name}</td>
              <td style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                {stock.industry || 'N/A'}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>
                {(stock.client_mtf_qty || 0).toLocaleString('en-IN')}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: '600' }}>
                {formatCurrency(stock.client_mtf_val || 0)}
              </td>
              <td style={{ textAlign: 'right', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
                {stock.market_cap_cr ? formatCurrency(stock.market_cap_cr) : 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default IndexMTFHoldings;
