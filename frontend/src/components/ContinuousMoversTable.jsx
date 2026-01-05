import { useState } from 'react';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function ContinuousMoversTable({ movers }) {
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
  
  // Group by market cap category and sort by total_change_cr descending
  const groupedMovers = categories.reduce((acc, category) => {
    const filtered = movers?.filter(m => m.market_cap_category === category) || [];
    // Sort by total_change_cr in descending order (highest first)
    acc[category] = filtered.sort((a, b) => b.total_change_cr - a.total_change_cr);
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

  const categoryMovers = groupedMovers[activeCategory] || [];

  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">Continuous MTF Movers (≥3 Days) - Buy Direction</h2>
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
        <div>
          <div style={{ fontSize: '14px', color: 'var(--color-text-muted)', marginBottom: '4px' }}>
            Active Streaks
          </div>
          <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--color-primary)' }}>
            {categoryMovers.length}
          </div>
        </div>
      </div>
      
      {/* Data Table */}
      {categoryMovers.length === 0 ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px 20px',
          color: 'var(--color-text-muted)',
          backgroundColor: 'var(--color-bg-secondary)',
          borderRadius: '6px'
        }}>
          No continuous movers found in {activeCategory} category
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Direction</th>
                <th style={{ textAlign: 'center' }}>Days</th>
                <th style={{ textAlign: 'right' }}>Total Change (₹ Cr)</th>
                <th style={{ textAlign: 'right' }}>Avg Daily (₹ Cr)</th>
                <th>Period</th>
              </tr>
            </thead>
            <tbody>
              {categoryMovers.map((mover) => (
                <tr key={`${mover.symbol}-${mover.streak_start_date}`}>
                  <td className="symbol">{mover.symbol}</td>
                  <td>
                    <span className={mover.direction === 'positive' ? 'positive' : 'negative'}>
                      {mover.direction === 'positive' ? '📈 Buy' : '📉 Sell'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center', fontWeight: '600' }}>
                    {mover.consecutive_days}
                  </td>
                  <td 
                    className={mover.direction === 'positive' ? 'positive' : 'negative'}
                    style={{ textAlign: 'right' }}
                  >
                    {mover.direction === 'positive' ? '+' : ''}{formatCurrency(mover.total_change_cr)}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {formatCurrency(Math.abs(mover.avg_daily_change_cr))}
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                    {formatDate(mover.streak_start_date)} → {formatDate(mover.streak_end_date)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
