import axios from 'axios';

// Use relative path for API calls - works with Vite proxy and ngrok
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Market API
export const marketApi = {
  getOverview: () => apiClient.get('/market/overview'),
  getFlow: (limit = 30) => apiClient.get('/market/flow', { params: { limit } }),
  getLatestFlow: () => apiClient.get('/market/flow/latest'),
  getRegime: () => apiClient.get('/market/regime'),
  getActiveStocksTrend: (limit = 30) => apiClient.get('/market/active-stocks-trend', { params: { limit } }),
};

// Stocks API
export const stocksApi = {
  getGainers: (limit = 20) => apiClient.get('/stocks/gainers', { params: { limit } }),
  getLosers: (limit = 20) => apiClient.get('/stocks/losers', { params: { limit } }),
  getPercentMovers: (direction, marketCapCategory) => 
    apiClient.get('/stocks/percent-movers', { 
      params: { direction, market_cap_category: marketCapCategory } 
    }),
  getConcentration: (limit = 20) => apiClient.get('/stocks/concentration', { params: { limit } }),
  getConcentrationByCategory: (topN = 10) => 
    apiClient.get('/stocks/concentration-by-category', { params: { top_n: topN } }),
  getContinuousMovers: (minDays = 3, direction, marketCapCategory) =>
    apiClient.get('/stocks/continuous-movers', {
      params: { min_days: minDays, direction, market_cap_category: marketCapCategory }
    }),
};

// Shockers API
export const shockersApi = {
  getVolumeShockers: (minZScore = 2.0, marketCapCategory) =>
    apiClient.get('/shockers/volume', {
      params: { min_z_score: minZScore, market_cap_category: marketCapCategory }
    }),
  getValueShockers: (minZScore = 2.0, marketCapCategory) =>
    apiClient.get('/shockers/value', {
      params: { min_z_score: minZScore, market_cap_category: marketCapCategory }
    }),
};

// Indices API
export const indicesApi = {
  getTopMTFByIndex: () => apiClient.get('/indices/top-mtf'),
  getTopMTFForIndex: (indexName) => apiClient.get(`/indices/top-mtf/${indexName}`),
  getConstituents: (indexName) => apiClient.get(`/indices/constituents/${indexName}`),
  getAvailableIndices: () => apiClient.get('/indices/available'),
};

export default apiClient;
