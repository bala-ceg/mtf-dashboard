import { useState, useEffect } from 'react';
import { formatCurrency } from '../utils/formatters';

const IndexMTFHoldings = ({ data }) => {
  const [selectedIndex, setSelectedIndex] = useState('NIFTY50');
  const [selectedStock, setSelectedStock] = useState(null);
  const [historicalData, setHistoricalData] = useState({});
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, data: null });

  // Fetch historical data when index changes
  useEffect(() => {
    fetchHistoricalData(selectedIndex);
  }, [selectedIndex]);

  const fetchHistoricalData = async (indexName) => {
    if (historicalData[indexName]) return; // Already loaded
    
    setLoadingHistory(true);
    try {
      const response = await fetch(`/api/indices/stock-history/${indexName}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Group by symbol
      const grouped = data.reduce((acc, row) => {
        if (!acc[row.symbol]) {
          acc[row.symbol] = {
            company_name: row.company_name,
            daily_data: []
          };
        }
        acc[row.symbol].daily_data.push(row);
        return acc;
      }, {});
      
      setHistoricalData(prev => ({
        ...prev,
        [indexName]: grouped
      }));
    } catch (error) {
      console.error('Error fetching historical data:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

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
  const currentHistoricalData = historicalData[selectedIndex] || {};

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
      <IndexTable 
        stocks={currentStocks} 
        historicalData={currentHistoricalData}
        selectedStock={selectedStock}
        setSelectedStock={setSelectedStock}
        loadingHistory={loadingHistory}
      />

      {/* Detailed Chart */}
      {selectedStock && currentHistoricalData[selectedStock] && (
        <DetailedChart 
          stock={currentHistoricalData[selectedStock]}
          symbol={selectedStock}
          onClose={() => setSelectedStock(null)}
          tooltip={tooltip}
          setTooltip={setTooltip}
        />
      )}
    </div>
  );
};

// Calculate correlation coefficient between MTF change % and price change %
const calculateCorrelation = (data) => {
  if (!data || data.length < 2) return null;
  
  const sortedData = data.slice().sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
  
  // Calculate percentage changes
  const changes = [];
  for (let i = 1; i < sortedData.length; i++) {
    const prevMtf = Number(sortedData[i-1].mtf_amount_cr);
    const currMtf = Number(sortedData[i].mtf_amount_cr);
    const prevPrice = Number(sortedData[i-1].close_price);
    const currPrice = Number(sortedData[i].close_price);
    
    if (prevMtf && currMtf && prevPrice && currPrice) {
      const mtfChangePct = ((currMtf - prevMtf) / prevMtf) * 100;
      const priceChangePct = ((currPrice - prevPrice) / prevPrice) * 100;
      changes.push({ mtfChangePct, priceChangePct });
    }
  }
  
  if (changes.length < 2) return null;
  
  // Calculate correlation coefficient
  const n = changes.length;
  const meanMtf = changes.reduce((sum, c) => sum + c.mtfChangePct, 0) / n;
  const meanPrice = changes.reduce((sum, c) => sum + c.priceChangePct, 0) / n;
  
  let numerator = 0;
  let sumSqMtf = 0;
  let sumSqPrice = 0;
  
  for (const c of changes) {
    const mtfDiff = c.mtfChangePct - meanMtf;
    const priceDiff = c.priceChangePct - meanPrice;
    numerator += mtfDiff * priceDiff;
    sumSqMtf += mtfDiff * mtfDiff;
    sumSqPrice += priceDiff * priceDiff;
  }
  
  const denominator = Math.sqrt(sumSqMtf * sumSqPrice);
  if (denominator === 0) return null;
  
  return numerator / denominator;
};

const IndexTable = ({ stocks, historicalData, selectedStock, setSelectedStock, loadingHistory }) => {
  if (!stocks || stocks.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
        No data available for this index.
      </div>
    );
  }

  const renderCorrelation = (symbol) => {
    const stockData = historicalData[symbol];
    if (!stockData || !stockData.daily_data || stockData.daily_data.length === 0) {
      return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: 'var(--color-text-muted)' }}>Loading...</div>;
    }

    const correlation = calculateCorrelation(stockData.daily_data);
    
    if (correlation === null) {
      return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', color: 'var(--color-text-muted)' }}>N/A</div>;
    }

    // Color based on correlation strength and direction
    let color, bgColor, label;
    if (correlation >= 0.7) {
      color = '#10b981'; // Strong positive
      bgColor = 'rgba(16, 185, 129, 0.1)';
      label = 'Strong +';
    } else if (correlation >= 0.3) {
      color = '#22c55e'; // Moderate positive
      bgColor = 'rgba(34, 197, 94, 0.1)';
      label = 'Moderate +';
    } else if (correlation >= -0.3) {
      color = '#6b7280'; // Weak
      bgColor = 'rgba(107, 114, 128, 0.1)';
      label = 'Weak';
    } else if (correlation >= -0.7) {
      color = '#f59e0b'; // Moderate negative
      bgColor = 'rgba(245, 158, 11, 0.1)';
      label = 'Moderate -';
    } else {
      color = '#ef4444'; // Strong negative
      bgColor = 'rgba(239, 68, 68, 0.1)';
      label = 'Strong -';
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
        <div style={{
          fontSize: '16px',
          fontWeight: '700',
          fontFamily: 'monospace',
          color: color
        }}>
          {correlation.toFixed(3)}
        </div>
        <div style={{
          fontSize: '10px',
          fontWeight: '600',
          padding: '2px 8px',
          borderRadius: '10px',
          backgroundColor: bgColor,
          color: color
        }}>
          {label}
        </div>
      </div>
    );
  };

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
            <th style={{ textAlign: 'center' }}>Correlation<br/><span style={{ fontSize: '10px', fontWeight: '400', color: 'var(--color-text-muted)' }}>(MTF % vs Price %)</span></th>
            <th>Action</th>
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
              <td style={{ textAlign: 'center' }}>
                {renderCorrelation(stock.symbol)}
              </td>
              <td>
                <button
                  onClick={() => setSelectedStock(selectedStock === stock.symbol ? null : stock.symbol)}
                  disabled={loadingHistory}
                  style={{
                    padding: '6px 12px',
                    fontSize: '12px',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: selectedStock === stock.symbol ? 'var(--color-primary)' : 'var(--color-bg-secondary)',
                    color: selectedStock === stock.symbol ? 'white' : 'var(--color-text-primary)',
                    cursor: loadingHistory ? 'not-allowed' : 'pointer',
                    opacity: loadingHistory ? 0.6 : 1,
                    transition: 'all 0.2s'
                  }}
                >
                  {selectedStock === stock.symbol ? 'Hide' : 'View Chart'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const DetailedChart = ({ stock, symbol, onClose, tooltip, setTooltip }) => {
  if (!stock || !stock.daily_data || stock.daily_data.length === 0) return null;

  // Sort by date and take only the last 30 trading days
  const data = stock.daily_data
    .slice()
    .sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date))
    .slice(-30);
  const width = 900;
  const height = 350;
  const padding = 50;

  const maxMtf = Math.max(...data.map(d => Number(d.mtf_amount_cr) || 0));
  const minMtf = Math.min(...data.map(d => Number(d.mtf_amount_cr) || 0));
  const maxPrice = Math.max(...data.map(d => Number(d.close_price) || 0));
  const minPrice = Math.min(...data.map(d => Number(d.close_price) || 0));

  const mtfPoints = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
    const y = padding + (1 - (Number(d.mtf_amount_cr) - minMtf) / (maxMtf - minMtf || 1)) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(' ');

  const pricePoints = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
    const y = padding + (1 - (Number(d.close_price) - minPrice) / (maxPrice - minPrice || 1)) * (height - 2 * padding);
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

  // Calculate summary stats
  const totalMtfChange = Number(data[data.length - 1].mtf_amount_cr) - Number(data[0].mtf_amount_cr);
  const totalPriceChange = Number(data[data.length - 1].close_price) - Number(data[0].close_price);
  const avgMtfChange = data.reduce((sum, d) => sum + (Number(d.mtf_change_cr) || 0), 0) / data.length;
  const avgPriceChangePct = data.reduce((sum, d) => sum + (Number(d.price_change_pct) || 0), 0) / data.length;

  return (
    <div style={{ 
      marginTop: '30px', 
      padding: '25px', 
      backgroundColor: 'var(--color-bg-secondary)', 
      borderRadius: '12px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ marginBottom: '5px', fontSize: '20px', fontWeight: '600' }}>
            {symbol} - {stock.company_name}
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--color-text-muted)' }}>
            30-Day MTF & Price Movement Analysis
          </p>
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '8px 16px',
            fontSize: '14px',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: 'var(--color-bg)',
            color: 'var(--color-text-primary)',
            cursor: 'pointer',
            transition: 'all 0.2s',
            fontWeight: '500'
          }}
        >
          ✕ Close
        </button>
      </div>

      {/* Current Values */}
      <div style={{ display: 'flex', gap: '30px', marginBottom: '20px', fontSize: '14px', flexWrap: 'wrap' }}>
        <div style={{ 
          padding: '12px 20px', 
          backgroundColor: 'var(--color-bg)', 
          borderRadius: '8px',
          border: '2px solid var(--color-primary)',
          flex: '1',
          minWidth: '200px'
        }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '4px' }}>Current MTF</div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--color-primary)' }}>
            {formatCurrency(data[data.length - 1].mtf_amount_cr)} Cr
          </div>
        </div>
        <div style={{ 
          padding: '12px 20px', 
          backgroundColor: 'var(--color-bg)', 
          borderRadius: '8px',
          border: '2px solid #10b981',
          flex: '1',
          minWidth: '200px'
        }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '4px' }}>Current Price</div>
          <div style={{ fontSize: '18px', fontWeight: '700', color: '#10b981' }}>
            ₹{Number(data[data.length - 1].close_price)?.toFixed(2)}
          </div>
        </div>
        <div style={{ 
          padding: '12px 20px', 
          backgroundColor: 'var(--color-bg)', 
          borderRadius: '8px',
          flex: '1',
          minWidth: '200px'
        }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '4px' }}>MTF Change (30d)</div>
          <div style={{ 
            fontSize: '18px', 
            fontWeight: '700', 
            color: totalMtfChange >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' 
          }}>
            {totalMtfChange >= 0 ? '+' : ''}{formatCurrency(totalMtfChange)} Cr
          </div>
        </div>
        <div style={{ 
          padding: '12px 20px', 
          backgroundColor: 'var(--color-bg)', 
          borderRadius: '8px',
          flex: '1',
          minWidth: '200px'
        }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '4px' }}>Price Change (30d)</div>
          <div style={{ 
            fontSize: '18px', 
            fontWeight: '700', 
            color: totalPriceChange >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' 
          }}>
            {totalPriceChange >= 0 ? '+' : ''}₹{totalPriceChange?.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ position: 'relative', backgroundColor: 'var(--color-bg)', padding: '20px', borderRadius: '8px' }}>
        <svg 
          width={width} 
          height={height + 40} 
          style={{ display: 'block', margin: '0 auto' }}
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

          {/* Area fills for visual appeal */}
          <defs>
            <linearGradient id="mtfGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.3" />
              <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.05" />
            </linearGradient>
            <linearGradient id="priceGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.05" />
            </linearGradient>
          </defs>

          {/* MTF area */}
          <path
            d={`M ${mtfPoints.split(' ')[0]} L ${mtfPoints} L ${width - padding},${height - padding} L ${padding},${height - padding} Z`}
            fill="url(#mtfGradient)"
          />

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
            const yMtf = padding + (1 - (Number(d.mtf_amount_cr) - minMtf) / (maxMtf - minMtf || 1)) * (height - 2 * padding);
            const yPrice = padding + (1 - (Number(d.close_price) - minPrice) / (maxPrice - minPrice || 1)) * (height - 2 * padding);
            
            return (
              <g key={i}>
                <circle
                  cx={x}
                  cy={yMtf}
                  r="6"
                  fill="var(--color-primary)"
                  opacity="0.8"
                  style={{ cursor: 'pointer' }}
                  onMouseMove={(e) => handleMouseMove(e, i)}
                />
                <circle
                  cx={x}
                  cy={yPrice}
                  r="6"
                  fill="#10b981"
                  opacity="0.8"
                  style={{ cursor: 'pointer' }}
                  onMouseMove={(e) => handleMouseMove(e, i)}
                />
              </g>
            );
          })}

          {/* Legend */}
          <g transform={`translate(${padding}, 20)`}>
            <circle cx="0" cy="0" r="5" fill="var(--color-primary)" />
            <text x="12" y="4" fill="var(--color-text-primary)" fontSize="13" fontWeight="600">MTF Amount (Cr)</text>
            
            <circle cx="140" cy="0" r="5" fill="#10b981" />
            <text x="152" y="4" fill="var(--color-text-primary)" fontSize="13" fontWeight="600">Stock Price (₹)</text>
          </g>

          {/* X-axis labels */}
          {data.map((d, i) => {
            if (i % Math.floor(data.length / 6) === 0 || i === data.length - 1) {
              const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
              return (
                <text
                  key={i}
                  x={x}
                  y={height + 25}
                  fill="var(--color-text-muted)"
                  fontSize="11"
                  textAnchor="middle"
                  fontWeight="500"
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
            border: '2px solid var(--color-border)',
            borderRadius: '8px',
            padding: '14px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.2)',
            pointerEvents: 'none',
            zIndex: 1000,
            minWidth: '240px',
            fontSize: '13px'
          }}>
            <div style={{ 
              fontWeight: '700', 
              marginBottom: '10px', 
              borderBottom: '2px solid var(--color-border)', 
              paddingBottom: '8px',
              fontSize: '14px',
              color: 'var(--color-text-primary)'
            }}>
              {new Date(tooltip.data.trade_date).toLocaleDateString('en-GB', { 
                weekday: 'short',
                day: '2-digit', 
                month: 'short', 
                year: 'numeric' 
              })}
            </div>
            <div style={{ display: 'grid', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--color-primary)', fontWeight: '600' }}>MTF Amount:</span>
                <span style={{ fontWeight: '700', fontSize: '14px' }}>{formatCurrency(tooltip.data.mtf_amount_cr)} Cr</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--color-primary)', fontWeight: '600' }}>MTF Change:</span>
                <span style={{ 
                  fontWeight: '700', 
                  fontSize: '14px',
                  color: tooltip.data.mtf_change_cr >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' 
                }}>
                  {tooltip.data.mtf_change_cr >= 0 ? '+' : ''}{formatCurrency(tooltip.data.mtf_change_cr)} Cr
                </span>
              </div>
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ color: '#10b981', fontWeight: '600' }}>Close Price:</span>
                  <span style={{ fontWeight: '700', fontSize: '14px' }}>₹{Number(tooltip.data.close_price)?.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--color-text-muted)' }}>
                  <span>O: ₹{Number(tooltip.data.open_price)?.toFixed(2)}</span>
                  <span>H: ₹{Number(tooltip.data.high_price)?.toFixed(2)}</span>
                  <span>L: ₹{Number(tooltip.data.low_price)?.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                  <span style={{ color: '#10b981', fontWeight: '600' }}>Change:</span>
                  <span style={{ 
                    fontWeight: '700',
                    fontSize: '14px',
                    color: tooltip.data.price_change >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' 
                  }}>
                    {tooltip.data.price_change >= 0 ? '+' : ''}₹{Number(tooltip.data.price_change)?.toFixed(2)} ({Number(tooltip.data.price_change_pct)?.toFixed(2)}%)
                  </span>
                </div>
              </div>
              <div style={{ 
                borderTop: '1px solid var(--color-border)', 
                marginTop: '6px', 
                paddingTop: '8px', 
                fontSize: '12px', 
                color: 'var(--color-text-muted)',
                display: 'grid',
                gap: '4px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Volume:</span>
                  <span style={{ fontWeight: '600' }}>{Number(tooltip.data.volume)?.toLocaleString('en-IN')}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Delivery:</span>
                  <span style={{ fontWeight: '600' }}>{Number(tooltip.data.delivery_pct)?.toFixed(2)}%</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Summary Statistics */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
        gap: '15px', 
        marginTop: '25px' 
      }}>
        <div style={{ padding: '15px', backgroundColor: 'var(--color-bg)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '6px' }}>Avg Daily MTF Change</div>
          <div style={{ 
            fontSize: '16px', 
            fontWeight: '700',
            color: avgMtfChange >= 0 ? 'var(--color-positive)' : 'var(--color-negative)'
          }}>
            {avgMtfChange >= 0 ? '+' : ''}{formatCurrency(avgMtfChange)} Cr
          </div>
        </div>
        <div style={{ padding: '15px', backgroundColor: 'var(--color-bg)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '6px' }}>Avg Daily Price Change</div>
          <div style={{ 
            fontSize: '16px', 
            fontWeight: '700',
            color: avgPriceChangePct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)'
          }}>
            {avgPriceChangePct >= 0 ? '+' : ''}{avgPriceChangePct.toFixed(2)}%
          </div>
        </div>
        <div style={{ padding: '15px', backgroundColor: 'var(--color-bg)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '6px' }}>Data Points</div>
          <div style={{ fontSize: '16px', fontWeight: '700' }}>
            {data.length} days
          </div>
        </div>
        <div style={{ padding: '15px', backgroundColor: 'var(--color-bg)', borderRadius: '8px' }}>
          <div style={{ color: 'var(--color-text-muted)', fontSize: '12px', marginBottom: '6px' }}>MTF Quantity</div>
          <div style={{ fontSize: '16px', fontWeight: '700' }}>
            {data[data.length - 1].mtf_quantity?.toLocaleString('en-IN')}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IndexMTFHoldings;
