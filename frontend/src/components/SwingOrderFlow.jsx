import { useCallback, useEffect, useState } from 'react';
import { swingApi } from '../api/client';

const number = (value, digits = 1) =>
  value === null || value === undefined ? '—' : Number(value).toFixed(digits);
const pct = (value) => value === null || value === undefined ? '—' : `${Number(value).toFixed(1)}%`;
const scoreClass = (value) => Number(value) >= 65 ? 'strong' : Number(value) >= 45 ? 'watch' : 'neutral';

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
          <span className="swing-date">{tradeDate ? `Session: ${tradeDate}` : 'No computed session'}</span>
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
            <th>RVOL</th><th>Delivery %</th><th>20D return</th><th>CMF 20</th><th>MFI 14</th><th>Close vs VWAP</th>
          </tr></thead>
          <tbody>
            {results.map(row => (
              <tr key={row.symbol}>
                <td><strong>{row.symbol}</strong><small>{row.company_name || row.sector || ''}</small></td>
                <td><span className={`swing-signal ${String(row.signal).toLowerCase()}`}>{String(row.signal).replaceAll('_', ' ')}</span></td>
                <td><span className={`swing-score ${scoreClass(row.accumulation_score)}`}>{number(row.accumulation_score, 0)}</span></td>
                <td><span className={`swing-score ${scoreClass(row.distribution_score)}`}>{number(row.distribution_score, 0)}</span></td>
                <td>{number(row.relative_volume, 2)}×</td>
                <td>{pct(row.delivery_pct)} <small>({row.delivery_pct_delta == null ? '—' : `${number(row.delivery_pct_delta)} pp vs 20D`})</small></td>
                <td className={Number(row.return_20d_pct) >= 0 ? 'positive' : 'negative'}>{pct(row.return_20d_pct)}</td>
                <td>{number(row.cmf_20, 2)}</td>
                <td>{number(row.mfi_14, 1)}</td>
                <td>{pct(row.vwap_deviation_pct)}</td>
              </tr>
            ))}
            {!loading && results.length === 0 && tradeDate && (
              <tr><td colSpan="10" className="swing-no-results">No stocks match the current filters.</td></tr>
            )}
          </tbody>
        </table>
        {loading && <div className="swing-loading">Loading scanner…</div>}
      </div>

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
