import { useState, useEffect } from 'react';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function MTFPriceCorrelation() {
  const [correlationData, setCorrelationData] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState('Large-High');
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });

  const categories = ['Large-High', 'Large-Low', 'Mid-High', 'Mid-Low', 'Small-High', 'Small-Low', 'Micro-High', 'Micro-Low'];

  useEffect(() => {
    fetchCorrelationData();
  }, []);

  const fetchCorrelationData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/stocks/mtf-price-correlation?limit=100');
      const data = await response.json();
      // Parse daily_data JSON string
      const parsedData = data.map(stock => ({
        ...stock,
        daily_data: typeof stock.daily_data === 'string' ? JSON.parse(stock.daily_data) : stock.daily_data
      }));
      setCorrelationData(parsedData);
    } catch (error) {
      console.error('Error fetching correlation data:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredData = correlationData.filter(stock => stock.market_cap_category === activeCategory);

  const renderMiniChart = (dailyData) => {
    if (!dailyData || dailyData.length === 0) return null;

    const maxMtf = Math.max(...dailyData.map(d => d.mtf_amount_cr || 0));
    const minMtf = Math.min(...dailyData.map(d => d.mtf_amount_cr || 0));
    const maxPrice = Math.max(...dailyData.map(d => d.close_price || 0));
    const minPrice = Math.min(...dailyData.map(d => d.close_price || 0));

    const width = 200;
    const height = 60;
    const padding = 5;

    // Create MTF line
    const mtfPoints = dailyData.map((d, i) => {
      const x = padding + (i / (dailyData.length - 1)) * (width - 2 * padding);
      const y = padding + (1 - (d.mtf_amount_cr - minMtf) / (maxMtf - minMtf || 1)) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    // Create Price line
    const pricePoints = dailyData.map((d, i) => {
      const x = padding + (i / (dailyData.length - 1)) * (width - 2 * padding);
      const y = padding + (1 - (d.close_price - minPrice) / (maxPrice - minPrice || 1)) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    return (
      <svg width={width} height={height} style={{ border: '1px solid var(--color-border)', borderRadius: '4px', background: 'var(--color-bg)' }}>
        {/* MTF Line (Blue) */}
        <polyline
          points={mtfPoints}
          fill="none"
          stroke="var(--color-primary)"
          strokeWidth="2"
        />
        {/* Price Line (Green) */}
        <polyline
          points={pricePoints}
          fill="none"
          stroke="#10b981"
          strokeWidth="2"
        />
      </svg>
    );
  };

  const renderDetailedChart = (stock) => {
    if (!stock || !stock.daily_data || stock.daily_data.length === 0) return null;

    const data = stock.daily_data;
    const width = 800;
    const height = 300;
    const padding = 40;

    const maxMtf = Math.max(...data.map(d => d.mtf_amount_cr || 0));
    const minMtf = Math.min(...data.map(d => d.mtf_amount_cr || 0));
    const maxPrice = Math.max(...data.map(d => d.close_price || 0));
    const minPrice = Math.min(...data.map(d => d.close_price || 0));

    // MTF line
    const mtfPoints = data.map((d, i) => {
      const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
      const y = padding + (1 - (d.mtf_amount_cr - minMtf) / (maxMtf - minMtf || 1)) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    // Price line
    const pricePoints = data.map((d, i) => {
      const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
      const y = padding + (1 - (d.close_price - minPrice) / (maxPrice - minPrice || 1)) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    const handleMouseMove = (e, index) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      setTooltip({
        visible: true,
        x: x + 10,
        y: y - 10,
        data: data[index]
      });
    };

    const handleMouseLeave = () => {
      setTooltip({ visible: false, x: 0, y: 0, data: null });
    };

    return (
      <div style={{ marginTop: '20px', padding: '20px', backgroundColor: 'var(--color-bg-secondary)', borderRadius: '8px' }}>
        <h3 style={{ marginBottom: '10px', fontSize: '18px' }}>
          {stock.symbol} - {stock.company_name}
        </h3>
        <div style={{ display: 'flex', gap: '20px', marginBottom: '15px', fontSize: '14px' }}>
          <div>
            <span style={{ color: 'var(--color-primary)' }}>● MTF:</span> {formatCurrency(data[data.length - 1].mtf_amount_cr)} Cr
          </div>
          <div>
            <span style={{ color: '#10b981' }}>● Price:</span> ₹{data[data.length - 1].close_price?.toFixed(2)}
          </div>
          <div>
            <span style={{ color: 'var(--color-text-muted)' }}>Correlation:</span> {stock.correlation_score?.toFixed(1)}%
          </div>
        </div>
        <div style={{ position: 'relative' }}>
          <svg 
            width={width} 
            height={height + 20} 
            style={{ backgroundColor: 'var(--color-bg)', borderRadius: '6px' }}
            onMouseLeave={handleMouseLeave}
          >
            {/* Grid lines */}
            {[0, 25, 50, 75, 100].map(pct => {
              const y = padding + (pct / 100) * (height - 2 * padding);
              return (
                <line
                  key={pct}
                  x1={padding}
                  y1={y}
                  x2={width - padding}
                  y2={y}
                  stroke="var(--color-border)"
                  strokeWidth="1"
                  opacity="0.3"
                />
              );
            })}

            {/* MTF Line */}
            <polyline
              points={mtfPoints}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth="3"
            />
            
            {/* Price Line */}
            <polyline
              points={pricePoints}
              fill="none"
              stroke="#10b981"
              strokeWidth="3"
            />

            {/* Interactive data points */}
            {data.map((d, i) => {
              const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
              const yMtf = padding + (1 - (d.mtf_amount_cr - minMtf) / (maxMtf - minMtf || 1)) * (height - 2 * padding);
              const yPrice = padding + (1 - (d.close_price - minPrice) / (maxPrice - minPrice || 1)) * (height - 2 * padding);
              
              return (
                <g key={i}>
                  {/* MTF point */}
                  <circle
                    cx={x}
                    cy={yMtf}
                    r="5"
                    fill="var(--color-primary)"
                    opacity="0.8"
                    style={{ cursor: 'pointer' }}
                    onMouseMove={(e) => handleMouseMove(e, i)}
                  />
                  {/* Price point */}
                  <circle
                    cx={x}
                    cy={yPrice}
                    r="5"
                    fill="#10b981"
                    opacity="0.8"
                    style={{ cursor: 'pointer' }}
                    onMouseMove={(e) => handleMouseMove(e, i)}
                  />
                </g>
              );
            })}

            {/* Labels */}
            <text x="10" y="20" fill="var(--color-primary)" fontSize="12">MTF</text>
            <text x="10" y="35" fill="#10b981" fontSize="12">Price</text>

            {/* X-axis labels (dates) */}
            {data.map((d, i) => {
              if (i % Math.floor(data.length / 5) === 0 || i === data.length - 1) {
                const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
                return (
                  <text
                    key={i}
                    x={x}
                    y={height + 15}
                    fill="var(--color-text-muted)"
                    fontSize="10"
                    textAnchor="middle"
                  >
                    {new Date(d.trade_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                  </text>
                );
              }
              return null;
            })}
          </svg>

          {/* Tooltip */}
          {tooltip.visible && tooltip.data && (
            <div style={{
              position: 'absolute',
              left: tooltip.x,
              top: tooltip.y,
              backgroundColor: 'var(--color-bg-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              padding: '12px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
              pointerEvents: 'none',
              zIndex: 1000,
              minWidth: '220px',
              fontSize: '13px'
            }}>
              <div style={{ fontWeight: '600', marginBottom: '8px', borderBottom: '1px solid var(--color-border)', paddingBottom: '6px' }}>
                {new Date(tooltip.data.trade_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
              </div>
              <div style={{ display: 'grid', gap: '6px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-primary)' }}>MTF:</span>
                  <span style={{ fontWeight: '600' }}>{formatCurrency(tooltip.data.mtf_amount_cr)} Cr</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--color-primary)' }}>MTF Change:</span>
                  <span style={{ fontWeight: '600', color: tooltip.data.mtf_value_change >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>
                    {tooltip.data.mtf_value_change >= 0 ? '+' : ''}{formatCurrency(tooltip.data.mtf_value_change)} Cr
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#10b981' }}>Close:</span>
                  <span style={{ fontWeight: '600' }}>₹{tooltip.data.close_price?.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#10b981' }}>Price Change:</span>
                  <span style={{ fontWeight: '600', color: tooltip.data.price_change >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>
                    {tooltip.data.price_change >= 0 ? '+' : ''}₹{tooltip.data.price_change?.toFixed(2)} ({tooltip.data.price_change_pct?.toFixed(2)}%)
                  </span>
                </div>
                <div style={{ borderTop: '1px solid var(--color-border)', marginTop: '4px', paddingTop: '6px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Volume:</span>
                    <span>{tooltip.data.volume?.toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Delivery:</span>
                    <span>{tooltip.data.delivery_pct?.toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Summary stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginTop: '20px', fontSize: '13px' }}>
          <div>
            <div style={{ color: 'var(--color-text-muted)' }}>MTF Change</div>
            <div style={{ fontSize: '16px', fontWeight: '600', color: stock.total_mtf_change >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>
              {stock.total_mtf_change >= 0 ? '+' : ''}{formatCurrency(stock.total_mtf_change)} Cr
            </div>
          </div>
          <div>
            <div style={{ color: 'var(--color-text-muted)' }}>Price Change</div>
            <div style={{ fontSize: '16px', fontWeight: '600', color: stock.total_price_change >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>
              {stock.total_price_change >= 0 ? '+' : ''}₹{stock.total_price_change?.toFixed(2)}
            </div>
          </div>
          <div>
            <div style={{ color: 'var(--color-text-muted)' }}>Avg Price Change</div>
            <div style={{ fontSize: '16px', fontWeight: '600' }}>
              {stock.avg_price_change_pct?.toFixed(2)}%
            </div>
          </div>
          <div>
            <div style={{ color: 'var(--color-text-muted)' }}>Days</div>
            <div style={{ fontSize: '16px', fontWeight: '600' }}>
              {stock.consecutive_days}
            </div>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>Loading correlation data...</div>;
  }

  return (
    <div className="section">
      <div className="section-header">
        <h2 className="section-title">📊 MTF vs Price Correlation Analysis</h2>
      </div>

      {/* Detailed Chart */}
      {selectedStock && renderDetailedChart(selectedStock)}

      {/* Category Tabs */}
      <div>
        <h3 style={{ fontSize: '18px', marginBottom: '15px', color: 'var(--color-text-primary)' }}>
          📈 Correlation by Market Cap Category
        </h3>
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
            >
              {cat}
            </button>
          ))}
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Company</th>
                <th style={{ textAlign: 'center' }}>Correlation %</th>
                <th style={{ textAlign: 'right' }}>MTF Change</th>
                <th style={{ textAlign: 'right' }}>Price Change %</th>
                <th style={{ textAlign: 'center' }}>Days</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.slice(0, 20).map((stock) => (
                <tr key={stock.symbol}>
                  <td className="symbol">{stock.symbol}</td>
                  <td>{stock.company_name}</td>
                  <td style={{ textAlign: 'center', fontWeight: '600' }}>
                    <span style={{ 
                      color: stock.correlation_score >= 70 ? 'var(--color-positive)' : 
                             stock.correlation_score >= 50 ? 'var(--color-warning)' : 'var(--color-text-muted)'
                    }}>
                      {stock.correlation_score?.toFixed(1)}%
                    </span>
                  </td>
                  <td className={stock.total_mtf_change >= 0 ? 'positive' : 'negative'} style={{ textAlign: 'right' }}>
                    {stock.total_mtf_change >= 0 ? '+' : ''}{formatCurrency(stock.total_mtf_change)}
                  </td>
                  <td className={stock.avg_price_change_pct >= 0 ? 'positive' : 'negative'} style={{ textAlign: 'right' }}>
                    {stock.avg_price_change_pct >= 0 ? '+' : ''}{stock.avg_price_change_pct?.toFixed(2)}%
                  </td>
                  <td style={{ textAlign: 'center' }}>{stock.consecutive_days}</td>
                  <td>
                    <button
                      onClick={() => setSelectedStock(selectedStock?.symbol === stock.symbol ? null : stock)}
                      style={{
                        padding: '6px 12px',
                        fontSize: '12px',
                        borderRadius: '4px',
                        border: 'none',
                        backgroundColor: selectedStock?.symbol === stock.symbol ? 'var(--color-primary)' : 'var(--color-bg-secondary)',
                        color: selectedStock?.symbol === stock.symbol ? 'white' : 'var(--color-text-primary)',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {selectedStock?.symbol === stock.symbol ? 'Hide' : 'Details'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
