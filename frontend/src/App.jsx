import { useState, useEffect } from 'react';
import { marketApi, stocksApi, shockersApi, indicesApi } from './api/client';
import MarketOverviewCards from './components/MarketOverviewCards';
import TopMoversTable from './components/TopMoversTable';
import ConcentrationByCategoryTable from './components/ConcentrationByCategoryTable';
import ContinuousMoversTable from './components/ContinuousMoversTable';
import ShockersTable from './components/ShockersTable';
import IndexMTFHoldings from './components/IndexMTFHoldings';
import MTFPriceCorrelation from './components/MTFPriceCorrelation';
import { formatDate } from './utils/formatters';
import './App.css';

function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // State for all data
  const [overview, setOverview] = useState(null);
  const [regime, setRegime] = useState(null);
  const [flow, setFlow] = useState(null);
  const [gainers, setGainers] = useState([]);
  const [losers, setLosers] = useState([]);
  const [concentrationByCategory, setConcentrationByCategory] = useState({});
  const [continuousMovers, setContinuousMovers] = useState([]);
  const [volumeShockers, setVolumeShockers] = useState([]);
  const [indexMTFData, setIndexMTFData] = useState([]);

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all data in parallel (with error handling for optional endpoints)
      const [
        overviewRes,
        regimeRes,
        flowRes,
        gainersRes,
        losersRes,
        concentrationByCategoryRes,
        continuousRes,
        volumeShockersRes,
        indexMTFRes,
      ] = await Promise.all([
        marketApi.getOverview(),
        marketApi.getRegime(),
        marketApi.getLatestFlow().catch(err => {
          console.warn('Flow data unavailable:', err.message);
          return { data: null };
        }),
        stocksApi.getGainers(20),
        stocksApi.getLosers(20),
        stocksApi.getConcentrationByCategory(10),
        stocksApi.getContinuousMovers(3),
        shockersApi.getVolumeShockers(1.5).catch(err => {
          console.warn('Volume shockers unavailable:', err.message);
          return { data: [] };
        }),
        indicesApi.getTopMTFByIndex().catch(err => {
          console.warn('Index MTF data unavailable:', err.message);
          return { data: [] };
        }),
      ]);

      setOverview(overviewRes.data);
      setRegime(regimeRes.data);
      setFlow(flowRes.data);
      setGainers(gainersRes.data);
      setLosers(losersRes.data);
      setConcentrationByCategory(concentrationByCategoryRes.data);
      setContinuousMovers(continuousRes.data);
      setVolumeShockers(volumeShockersRes.data);
      setIndexMTFData(indexMTFRes.data);

    } catch (err) {
      console.error('Error fetching data:', err);
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="app">
        <div className="dashboard-container">
          <div className="loading">Loading MTF Dashboard...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
        <div className="dashboard-container">
          <div className="error">
            <h2>Error Loading Dashboard</h2>
            <p>{error}</p>
            <button 
              onClick={fetchAllData}
              style={{
                marginTop: '16px',
                padding: '8px 16px',
                background: 'var(--color-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <div className="dashboard-container">
        {/* Header */}
        <div className="dashboard-header">
          <div className="header-title">
            <h1>MTF Market Intelligence Dashboard</h1>
            <div className="last-updated">
              Last Updated: {overview?.trade_date ? formatDate(overview.trade_date) : 'N/A'}
            </div>
          </div>
          
          <MarketOverviewCards 
            overview={overview}
            regime={regime}
            flow={flow}
          />
        </div>

        {/* Top Movers */}
        <TopMoversTable 
          gainers={gainers}
          losers={losers}
        />

        {/* Concentration by Market Cap Category */}
        <ConcentrationByCategoryTable data={concentrationByCategory} />

        {/* Continuous Movers */}
        <ContinuousMoversTable movers={continuousMovers} />

        {/* MTF vs Price Correlation Analysis */}
        <MTFPriceCorrelation />

        {/* Volume Shockers */}
        <ShockersTable shockers={volumeShockers} type="volume" />

        {/* Index MTF Holdings */}
        <IndexMTFHoldings data={indexMTFData} />
      </div>
    </div>
  );
}

export default App;
