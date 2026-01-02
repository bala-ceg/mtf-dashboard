import { useState } from 'react';
import { formatCurrency } from '../utils/formatters';

export default function ShockersTable({ shockers, type }) {
  const title = type === 'volume' ? 'MTF Volume Shockers' : 'MTF Value Shockers';
  const subtitle = type === 'volume' 
    ? 'Anomalies in MTF share quantity (number of shares) using Z-score analysis (10-day window)'
    : 'Anomalies in MTF rupee value (amount in crores) using Z-score analysis (10-day window)';

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

  // Group by market cap category
  const groupedShockers = categories.reduce((acc, category) => {
    acc[category] = shockers?.filter(s => s.market_cap_category === category) || [];
    return acc;
  }, {});

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

  const categoryShockers = groupedShockers[activeCategory] || [];
  
  // Separate positive and negative shockers for selected category
  const positiveShockers = categoryShockers.filter(s => s.z_score > 0);
  const negativeShockers = categoryShockers.filter(s => s.z_score < 0);

  const renderShockersList = (shockerData, title, colorClass) => (
    <div className="section">
      <div className="section-header">
        <h3 className="section-title" style={{ fontSize: '16px' }}>{title}</h3>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Date</th>
              <th>Symbol</th>
              <th>Category</th>
              <th style={{ textAlign: 'right' }}>MTF Quantity</th>
              <th style={{ textAlign: 'right' }}>Qty Avg (10d)</th>
              <th style={{ textAlign: 'right' }}>MTF Amount (₹ Cr)</th>
              <th style={{ textAlign: 'right' }}>Amt Avg (10d)</th>
              <th style={{ textAlign: 'right' }}>Z-Score</th>
            </tr>
          </thead>
          <tbody>
            {shockerData.length > 0 ? (
              shockerData.map((shocker, idx) => (
                <tr key={`${shocker.symbol}-${idx}`}>
                  <td>{idx + 1}</td>
                  <td style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                    {new Date(shocker.trade_date).toLocaleDateString('en-IN', { 
                      day: '2-digit', 
                      month: 'short',
                      year: 'numeric'
                    })}
                  </td>
                  <td className="symbol">{shocker.symbol}</td>
                  <td style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                    {shocker.market_cap_category}
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: '500' }}>
                    {(shocker.mtf_quantity || 0).toLocaleString('en-IN')}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--color-text-muted)' }}>
                    {(shocker.avg_qty_10d || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: '500' }}>
                    {formatCurrency(shocker.mtf_amount_cr)}
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--color-text-muted)' }}>
                    {formatCurrency(shocker.avg_amount_10d)}
                  </td>
                  <td 
                    className={colorClass}
                    style={{ 
                      textAlign: 'right',
                      fontWeight: '700',
                      fontSize: '15px'
                    }}
                  >
                    {parseFloat(shocker.z_score).toFixed(2)}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>
                  No {title.toLowerCase()} detected
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div>
      <div className="section" style={{ marginBottom: '12px' }}>
        <div className="section-header">
          <h2 className="section-title">{title}</h2>
        </div>
        <p style={{ 
          color: 'var(--color-text-muted)', 
          fontSize: '14px',
          marginTop: '-8px',
          marginBottom: '8px'
        }}>
          {subtitle}
        </p>
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
          <div style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
            Market Cap Range
          </div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--color-text-primary)' }}>
            {categoryDescriptions[activeCategory]}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '24px' }}>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
              Positive Shockers
            </div>
            <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--color-positive)' }}>
              {positiveShockers.length}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
              Negative Shockers
            </div>
            <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--color-negative)' }}>
              {negativeShockers.length}
            </div>
          </div>
        </div>
      </div>

      <div className="grid-2">{renderShockersList(
          positiveShockers.slice(0, 10),
          '📈 Top 10 Positive Shockers',
          'positive'
        )}
        {renderShockersList(
          negativeShockers.slice(0, 10),
          '📉 Top 10 Negative Shockers',
          'negative'
        )}
      </div>

      {/* Legend */}
      <div style={{
        marginTop: '16px',
        padding: '12px',
        backgroundColor: 'var(--color-bg-secondary)',
        borderRadius: '6px',
        fontSize: '13px',
        color: 'var(--color-text-muted)'
      }}>
      </div>
    </div>
  );
}
