import { useState } from 'react';
import { formatCurrency } from '../utils/formatters';

export default function TopMoversTable({ gainers, losers }) {
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

  // Filter and get top 10 for active category
  const filteredGainers = (gainers || [])
    .filter(g => g.market_cap_category === activeCategory)
    .slice(0, 10);
  
  const filteredLosers = (losers || [])
    .filter(l => l.market_cap_category === activeCategory)
    .slice(0, 10);

  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">Top Gainers & Losers (₹ Cr)</h2>
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
        gap: '16px'
      }}>
        <div>
          <span style={{ 
            fontSize: '14px', 
            color: 'var(--color-text-muted)',
            marginRight: '8px'
          }}>
            Market Cap Range:
          </span>
          <span style={{ 
            fontSize: '16px', 
            fontWeight: '600',
            color: 'var(--color-text-primary)'
          }}>
            {categoryDescriptions[activeCategory]}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '24px' }}>
          <div>
            <span style={{ 
              fontSize: '14px', 
              color: 'var(--color-text-muted)',
              marginRight: '8px'
            }}>
              Gainers:
            </span>
            <span style={{ 
              fontSize: '16px', 
              fontWeight: '600',
              color: 'var(--color-positive)'
            }}>
              {filteredGainers.length}
            </span>
          </div>
          <div>
            <span style={{ 
              fontSize: '14px', 
              color: 'var(--color-text-muted)',
              marginRight: '8px'
            }}>
              Losers:
            </span>
            <span style={{ 
              fontSize: '16px', 
              fontWeight: '600',
              color: 'var(--color-negative)'
            }}>
              {filteredLosers.length}
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Gainers Table */}
        <div>
          <h3 style={{ 
            marginBottom: '12px',
            color: 'var(--color-positive)',
            fontSize: '18px',
            fontWeight: '600'
          }}>
            Top 10 Gainers
          </h3>
          {filteredGainers.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>#</th>
                    <th>Symbol</th>
                    <th style={{ textAlign: 'right' }}>MTF Change (₹ Cr)</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGainers.map((item, idx) => (
                    <tr key={item.symbol}>
                      <td style={{ textAlign: 'center' }}>{idx + 1}</td>
                      <td className="symbol">{item.symbol}</td>
                      <td className="positive" style={{ textAlign: 'right' }}>
                        +{formatCurrency(item.mtf_change_cr)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ 
              textAlign: 'center', 
              color: 'var(--color-text-muted)', 
              padding: '2rem',
              backgroundColor: 'var(--color-bg-secondary)',
              borderRadius: '6px'
            }}>
              No gainers in this category
            </p>
          )}
        </div>

        {/* Losers Table */}
        <div>
          <h3 style={{ 
            marginBottom: '12px',
            color: 'var(--color-negative)',
            fontSize: '18px',
            fontWeight: '600'
          }}>
            Top 10 Losers
          </h3>
          {filteredLosers.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '60px' }}>#</th>
                    <th>Symbol</th>
                    <th style={{ textAlign: 'right' }}>MTF Change (₹ Cr)</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLosers.map((item, idx) => (
                    <tr key={item.symbol}>
                      <td style={{ textAlign: 'center' }}>{idx + 1}</td>
                      <td className="symbol">{item.symbol}</td>
                      <td className="negative" style={{ textAlign: 'right' }}>
                        {formatCurrency(item.mtf_change_cr)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ 
              textAlign: 'center', 
              color: 'var(--color-text-muted)', 
              padding: '2rem',
              backgroundColor: 'var(--color-bg-secondary)',
              borderRadius: '6px'
            }}>
              No losers in this category
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
