import { useCallback, useEffect, useState } from 'react';
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { swingApi } from '../api/client';

const number = (value, digits = 1) =>
  value === null || value === undefined ? '—' : Number(value).toFixed(digits);
const pct = (value) => value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`;
const scoreClass = (value) => Number(value) >= 65 ? 'strong' : Number(value) >= 45 ? 'watch' : 'neutral';
const parseJson = (value, fallback) => {
  if (value === null || value === undefined) return fallback;
  if (typeof value !== 'string') return value;
  try { return JSON.parse(value); } catch { return fallback; }
};
const labelize = (value) => String(value).replaceAll('_', ' ').toLowerCase();

export default function SwingOrderFlow() {
  const [signal, setSignal] = useState('');
  const [minScore, setMinScore] = useState(40);
  const [includeIlliquid, setIncludeIlliquid] = useState(false);
  const [results, setResults] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [performance, setPerformance] = useState({ accumulation: null, distribution: null });
  const [status, setStatus] = useState(null);
  const [tradeDate, setTradeDate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [stockHistory, setStockHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [scannerRes, sectorsRes, statusRes, accumulationPerfRes, distributionPerfRes] = await Promise.all([
        swingApi.getScanner({ signal: signal || undefined, minScore, limit: 750, includeIlliquid }),
        swingApi.getSectors(),
        swingApi.getStatus(),
        swingApi.getPerformance('ACCUMULATION'),
        swingApi.getPerformance('DISTRIBUTION'),
      ]);
      setResults(scannerRes.data.results || []);
      setTradeDate(scannerRes.data.trade_date);
      setSectors(sectorsRes.data.results || []);
      setStatus(statusRes.data);
      setPerformance({ accumulation: accumulationPerfRes.data, distribution: distributionPerfRes.data });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Unable to load swing scanner');
    } finally {
      setLoading(false);
    }
  }, [signal, minScore, includeIlliquid]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!selectedSymbol) {
      setStockHistory([]);
      setHistoryError(null);
      return undefined;
    }
    let cancelled = false;
    setHistoryLoading(true);
    setHistoryError(null);
    swingApi.getStockHistory(selectedSymbol, 60)
      .then(response => {
        if (!cancelled) setStockHistory(response.data || []);
      })
      .catch(err => {
        if (!cancelled) setHistoryError(err.response?.data?.detail || err.message || 'Unable to load stock history');
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => { cancelled = true; };
  }, [selectedSymbol]);

  const accumulation = results.filter(x => String(x.signal).startsWith('ACCUMULATION')).length;
  const distribution = results.filter(x => String(x.signal).startsWith('DISTRIBUTION')).length;
  const strongAccumulation = results.filter(x => x.signal === 'ACCUMULATION').length;
  const strongDistribution = results.filter(x => x.signal === 'DISTRIBUTION').length;

  return (
    <section className="swing-panel">
      <div className="swing-heading">
        <div>
          <div className="swing-eyebrow">NIFTY TOTAL MARKET · CASH EQUITIES</div>
          <h2>Swing Order Flow Scanner</h2>
          <p>Multi-session accumulation and distribution candidates from price, volume and delivery data.</p>
        </div>
        <div className="swing-actions">
          <span className="swing-date">
            {tradeDate ? `Session: ${tradeDate}` : 'No computed session'}
            <small>Benchmark: {status?.latest_benchmark_date || 'not loaded'} · Membership snapshot: {status?.latest_membership_snapshot_date || 'not captured'}</small>
          </span>
          <button type="button" className="swing-refresh" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="swing-metrics">
        <div className="swing-metric"><span>Universe</span><strong>{status?.universe_count ?? '—'}</strong><small>Current constituents</small></div>
        <div className="swing-metric positive"><span>Accumulation</span><strong>{accumulation}</strong><small>{strongAccumulation} strong · {accumulation - strongAccumulation} watch</small></div>
        <div className="swing-metric negative"><span>Distribution</span><strong>{distribution}</strong><small>{strongDistribution} strong · {distribution - strongDistribution} watch</small></div>
        <div className="swing-metric"><span>Latest Bhavcopy</span><strong className="swing-date-value">{status?.latest_bhavcopy_date || '—'}</strong><small>Features: {status?.latest_feature_date || 'not computed'}</small></div>
      </div>

      <div className="swing-toolbar">
        <label>
          Signal
          <select value={signal} onChange={e => setSignal(e.target.value)}>
            <option value="">All directions</option>
            <option value="ACCUMULATION">Strong accumulation</option>
            <option value="ACCUMULATION_WATCH">Accumulation watch</option>
            <option value="DISTRIBUTION">Strong distribution</option>
            <option value="DISTRIBUTION_WATCH">Distribution watch</option>
            <option value="NEUTRAL">Neutral</option>
          </select>
        </label>
        <label>
          Minimum score: <b>{minScore}</b>
          <input type="range" min="0" max="80" step="5" value={minScore}
            onChange={e => setMinScore(Number(e.target.value))} />
        </label>
        <label className="swing-checkbox-label">
          <input type="checkbox" checked={includeIlliquid} onChange={e => setIncludeIlliquid(e.target.checked)} />
          Include illiquid stocks
        </label>
        <span className="swing-result-count">{results.length} stocks</span>
      </div>

      {error && <div className="swing-error">{error}</div>}
      {!error && !loading && !tradeDate && (
        <div className="swing-empty">
          No scanner results yet. Apply the SQL migration, refresh the NIFTY Total Market universe,
          load cash Bhavcopy history and run the daily scanner ETL.
        </div>
      )}

      <div className="swing-table-wrap">
        <table className="swing-table">
          <thead><tr>
            <th>Stock</th><th>Signal</th><th>Acc. score</th><th>Dist. score</th>
            <th>RVOL</th><th>Delivery %</th><th>20D return</th><th>RS vs NIFTY TM</th><th>CMF 20</th><th>MFI 14</th><th>Close vs VWAP</th>
          </tr></thead>
          <tbody>
            {results.map(row => (
              <tr key={row.symbol}>
                <td>
                  <button type="button" className="swing-stock-select" onClick={() => setSelectedSymbol(row.symbol)}>
                    {row.symbol}
                  </button>
                  <small>{row.company_name || row.sector || ''}</small>
                </td>
                <td><span className={`swing-signal ${String(row.signal).toLowerCase()}`}>{String(row.signal).replaceAll('_', ' ')}</span></td>
                <td><span className={`swing-score ${scoreClass(row.accumulation_score)}`}>{number(row.accumulation_score, 0)}</span></td>
                <td><span className={`swing-score ${scoreClass(row.distribution_score)}`}>{number(row.distribution_score, 0)}</span></td>
                <td>{number(row.relative_volume, 2)}×</td>
                <td>{pct(row.delivery_pct)} <small>({row.delivery_pct_delta == null ? '—' : `${number(row.delivery_pct_delta)} pp vs 20D`})</small></td>
                <td className={Number(row.return_20d_pct) >= 0 ? 'positive' : 'negative'}>{pct(row.return_20d_pct)}</td>
                <td className={row.relative_strength_20d_pct == null ? '' : Number(row.relative_strength_20d_pct) >= 0 ? 'positive' : 'negative'}>{pct(row.relative_strength_20d_pct)}</td>
                <td>{number(row.cmf_20, 2)}</td>
                <td>{number(row.mfi_14, 1)}</td>
                <td>{pct(row.vwap_deviation_pct)}</td>
              </tr>
            ))}
            {!loading && results.length === 0 && tradeDate && (
              <tr><td colSpan="11" className="swing-no-results">No stocks match the current filters.</td></tr>
            )}
          </tbody>
        </table>
        {loading && <div className="swing-loading">Loading scanner…</div>}
      </div>

      {selectedSymbol && (
        <div className="swing-subpanel swing-stock-detail">
          <div className="swing-detail-heading">
            <div>
              <h3>{selectedSymbol} · recent signal history</h3>
              <p>Daily accumulation and distribution scores over the last 60 sessions.</p>
            </div>
            <button type="button" className="swing-refresh" onClick={() => setSelectedSymbol('')}>Close</button>
          </div>
          {historyError && <div className="swing-error">{historyError}</div>}
          {historyLoading && <div className="swing-loading">Loading {selectedSymbol} history…</div>}
          {!historyLoading && !historyError && stockHistory.length > 0 && (() => {
            const chronological = [...stockHistory].reverse();
            const latest = stockHistory[0];
            const parsedReasons = parseJson(latest.reason_codes, []);
            const parsedBreakdown = parseJson(latest.score_breakdown, {});
            const latestSignal = String(latest.signal || '');
            const direction = latestSignal.startsWith('DISTRIBUTION')
              || (!latestSignal.startsWith('ACCUMULATION')
                && Number(latest.distribution_score) > Number(latest.accumulation_score))
              ? 'distribution' : 'accumulation';
            const components = parsedBreakdown[direction] || {};
            const weights = parsedBreakdown.weights || {};
            return (
              <>
                <div className="swing-detail-chart">
                  <ResponsiveContainer width="100%" height={260}>
                    <LineChart data={chronological} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="trade_date" tickFormatter={value => String(value).slice(5)} minTickGap={24} />
                      <YAxis domain={[0, 100]} />
                      <Tooltip labelFormatter={value => `Session: ${value}`} />
                      <Legend />
                      <Line type="monotone" dataKey="accumulation_score" name="Accumulation" stroke="#16a34a" dot={false} />
                      <Line type="monotone" dataKey="distribution_score" name="Distribution" stroke="#dc2626" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="swing-detail-summary">
                  <span>Latest close: <b>{number(latest.close_price, 2)}</b></span>
                  <span>Signal: <b>{String(latest.signal).replaceAll('_', ' ')}</b></span>
                  <span>Accumulation: <b>{number(latest.accumulation_score, 0)}</b></span>
                  <span>Distribution: <b>{number(latest.distribution_score, 0)}</b></span>
                  <span>Relative strength: <b>{pct(latest.relative_strength_20d_pct)}</b></span>
                </div>
                <div className="swing-detail-breakdown">
                  <div>
                    <h4>Why this signal?</h4>
                    {parsedReasons.length ? (
                      <div className="swing-reason-list">
                        {parsedReasons.map(reason => <span key={reason}>{labelize(reason)}</span>)}
                      </div>
                    ) : <p>No explicit reason flags for the latest session.</p>}
                  </div>
                  <div>
                    <h4>{direction === 'distribution' ? 'Distribution' : 'Accumulation'} score breakdown</h4>
                    <div className="swing-breakdown-list">
                      {Object.entries(components).filter(([key]) => key !== 'total').map(([key, value]) => (
                        <div key={key}>
                          <span>{labelize(key)}</span>
                          <b>{number(value, 0)} / {number(weights[key], 0)}</b>
                        </div>
                      ))}
                      <div className="swing-breakdown-total">
                        <span>Total</span><b>{number(components.total ?? latest[direction + '_score'], 0)} / 100</b>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            );
          })()}
        </div>
      )}

      <div className="swing-performance-grid">
        {[
          ['Accumulation signals', performance.accumulation],
          ['Distribution signals', performance.distribution],
        ].map(([label, item]) => (
          <div className="swing-subpanel" key={label}>
            <h3>{label} · forward close returns</h3>
            {item ? (
              <>
                <div className="swing-performance-meta">{item.signal_count ?? 0} historical signals · {item.observations_20d ?? 0} complete 20-session outcomes</div>
                <table className="swing-table compact">
                  <thead><tr><th>Horizon</th><th>Average return</th><th>Median return</th><th>Directional hit rate</th></tr></thead>
                  <tbody>
                    {[5, 10, 20].map(days => (
                      <tr key={days}>
                        <td>{days} sessions</td>
                        <td className={Number(item['avg_return_' + days + 'd_pct']) >= 0 ? 'positive' : 'negative'}>{pct(item['avg_return_' + days + 'd_pct'])}</td>
                        <td>{pct(item['median_return_' + days + 'd_pct'])}</td>
                        <td>{pct(item['win_rate_' + days + 'd_pct'])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : <div className="swing-loading">Performance history not available yet.</div>}
          </div>
        ))}
      </div>

      <div className="swing-sector-grid">
        <div className="swing-subpanel">
          <h3>Sector participation</h3>
          <div className="swing-table-wrap">
            <table className="swing-table compact">
              <thead><tr><th>Sector</th><th>Stocks</th><th>Accum.</th><th>Distrib.</th><th>Avg score</th></tr></thead>
              <tbody>{sectors.slice(0, 10).map(row => (
                <tr key={row.sector}>
                  <td>{row.sector}</td><td>{row.stocks}</td>
                  <td className="positive">{row.accumulation_stocks}</td>
                  <td className="negative">{row.distribution_stocks}</td>
                  <td>{number(row.avg_accumulation_score)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </div>
        <div className="swing-subpanel swing-method">
          <h3>How to read this scanner</h3>
          <p><b>Accumulation / distribution scores</b> combine relative volume and turnover, close location, price trend, delivery participation, OBV change and Chaikin Money Flow.</p>
          <p><b>Delivery delta</b> is the percentage-point difference versus the stock’s preceding 20-session average.</p>
          <p><b>RVOL</b> compares today’s traded quantity with the preceding 20 sessions. Signals are screening hypotheses, not confirmed institutional activity or trade-side delta.</p>
          <p className="swing-footnote">Forward-return panels are descriptive, overlap across signal dates, exclude fees and slippage, and are not an out-of-sample backtest. Point-in-time index membership and adjusted prices are required to reduce survivorship and corporate-action bias.</p>
        </div>
      </div>
    </section>
  );
}
