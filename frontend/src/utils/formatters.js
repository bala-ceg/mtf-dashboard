export const formatCurrency = (value) => {
  if (value === null || value === undefined) return 'N/A';
  
  const num = parseFloat(value);
  if (isNaN(num)) return 'N/A';
  
  return new Intl.NumberFormat('en-IN', {
    style: 'decimal',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};

export const formatNumber = (value) => {
  if (value === null || value === undefined) return 'N/A';
  
  const num = parseFloat(value);
  if (isNaN(num)) return 'N/A';
  
  return new Intl.NumberFormat('en-IN').format(num);
};

export const formatPercent = (value) => {
  if (value === null || value === undefined) return 'N/A';
  
  const num = parseFloat(value);
  if (isNaN(num)) return 'N/A';
  
  return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
};

export const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date);
};

export const getRegimeColor = (regime) => {
  switch (regime?.toUpperCase()) {
    case 'RISK_ON':
      return 'danger';
    case 'RISK_OFF':
      return 'success';
    case 'NEUTRAL':
      return 'warning';
    default:
      return 'neutral';
  }
};

export const getRegimeEmoji = (regime) => {
  switch (regime?.toUpperCase()) {
    case 'RISK_ON':
      return '🔴';
    case 'RISK_OFF':
      return '🟢';
    case 'NEUTRAL':
      return '🟡';
    default:
      return '⚪';
  }
};

export const getChangeClass = (value) => {
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return '';
};
