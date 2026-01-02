import { useState } from 'react';
import { formatCurrency } from '../utils/formatters';

const ConcentrationByCategoryTable = ({ data }) => {
  const categories = [
    'Large-High',
    'Large-Low',
    'Mid-High',
    'Mid-Low',
    'Small-High',
    'Small-Low',
    'Micro-High',
    'Micro-Low'
  ];

  const [activeCategory, setActiveCategory] = useState('Large-High');

  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="section">
        <div className="section-header">
          <h2 className="section-title">MTF Concentration by Market Cap</h2>
        </div>
        <p style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: '2rem' }}>
          No concentration data available
        </p>
      </div>
    );
  }

  const categoryData = data[activeCategory] || [];
  const categoryDescriptions = {
    'Large-High': '≥100,000 Cr',
    'Large-Low': '70,000-99,999 Cr',
    'Mid-High': '50,000-69,999 Cr',
    'Mid-Low': '30,000-49,999 Cr',
    'Small-High': '10,000-29,999 Cr',
    'Small-Low': '5,000-9,999 Cr',
    'Micro-High': '1,000-4,999 Cr',
    'Micro-Low': '<1,000 Cr'
  };

  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">
          MTF Concentration by Market Cap Category
        </h2>
      </div>

      {/* Category Tabs */}
      <div style={{ 
        display: 'flex', 
        gap: '8px', 
        marginBottom: '20px',
        flexWrap: 'wrap',
        borderBottom: '1px solid var(--color-border)',
        paddingBottom: '12px'
      }}>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: 'none',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              backgroundColor: activeCategory === cat ? 'var(--color-primary)' : 'var(--color-bg-secondary)',
              color: activeCategory === cat ? 'white' : 'var(--color-text-secondary)',
            }}
            onMouseEnter={(e) => {
              if (activeCategory !== cat) {
                e.target.style.backgroundColor = 'var(--color-bg-hover)';
              }
            }}
            onMouseLeave={(e) => {
              if (activeCategory !== cat) {
                e.target.style.backgroundColor = 'var(--color-bg-secondary)';
              }
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Category Info */}
      <div style={{
        backgroundColor: 'var(--color-bg-secondary)',
        padding: '16px',
        borderRadius: '6px',
        marginBottom: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <h3 style={{ 
            fontSize: '18px', 
            fontWeight: '600', 
            color: 'var(--color-text)',
            marginBottom: '4px'
          }}>
            {activeCategory}
          </h3>
          <p style={{ 
            fontSize: '14px', 
            color: 'var(--color-text-muted)' 
          }}>
            Market Cap Range: <span style={{ color: 'var(--color-primary)' }}>{categoryDescriptions[activeCategory]}</span>
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--color-primary)' }}>
            {categoryData.length}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Top Stocks
          </div>
        </div>
      </div>

      {/* Data Table */}
      {categoryData.length > 0 ? (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Symbol</th>
                <th style={{ textAlign: 'right' }}>Market Cap (₹ Cr)</th>
                <th style={{ textAlign: 'right' }}>MTF Amount (₹ Cr)</th>
                <th style={{ textAlign: 'right' }}>Category Share (%)</th>
              </tr>
            </thead>
            <tbody>
              {categoryData.map((row, idx) => (
                <tr key={row.symbol}>
                  <td>{idx + 1}</td>
                  <td className="symbol">{row.symbol}</td>
                  <td style={{ textAlign: 'right' }}>
                    {formatCurrency(row.market_cap_cr)}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--color-primary)', fontWeight: '500' }}>
                    {formatCurrency(row.stock_mtf_cr)}
                  </td>
                  <td style={{ 
                    textAlign: 'right',
                    color: row.category_share_pct > 10 ? 'var(--color-positive)' :
                           row.category_share_pct > 5 ? 'var(--color-warning)' :
                           'var(--color-negative)',
                    fontWeight: '600',
                    fontSize: '15px'
                  }}>
                    {parseFloat(row.category_share_pct).toFixed(2)}%
                    {row.category_share_pct > 10}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
          <p style={{ fontSize: '16px', marginBottom: '8px' }}>
            No data available for {activeCategory} category
          </p>
          <p style={{ fontSize: '14px' }}>
            Try selecting a different category
          </p>
        </div>
      )}

      {/* Legend */}
      <div style={{
        marginTop: '20px',
        paddingTop: '16px',
        borderTop: '1px solid var(--color-border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        fontSize: '13px'
      }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <span style={{ color: 'var(--color-text-muted)' }}>
            <span style={{ color: 'var(--color-positive)' }}>■</span> High (&gt;10%)
          </span>
          <span style={{ color: 'var(--color-text-muted)' }}>
            <span style={{ color: 'var(--color-warning)' }}>■</span> Medium (5-10%)
          </span>
          <span style={{ color: 'var(--color-text-muted)' }}>
            <span style={{ color: 'var(--color-negative)' }}>■</span> Low (&lt;5%)
          </span>
        </div>
        <div style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>
          Category Share % = Stock MTF / Total Category MTF
        </div>
      </div>
    </div>
  );
};

export default ConcentrationByCategoryTable;
