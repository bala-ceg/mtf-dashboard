# MTF Market Intelligence Dashboard

A production-grade analytics dashboard for NSE Margin Trading Facility (MTF) data, providing real-time insights into market leverage patterns, concentration risks, and momentum indicators.

## 🎯 Features

### Market Intelligence
- **Market Regime Classification**: Real-time RISK_ON/RISK_OFF/NEUTRAL signals based on MTF flows
- **Leverage Analytics**: Track total MTF outstanding, fresh exposure, and liquidation patterns
- **Top Movers**: Identify stocks with largest absolute and percentage MTF changes
- **Concentration Analysis**: Monitor systemic risk from concentrated positions (>1% market share)
- **Momentum Tracking**: Detect continuous buying/selling streaks (≥3 days)
- **Anomaly Detection**: Z-score based volume/value shockers

### Market Cap Segmentation
Fixed categories for consistent analysis:
- Large-High (≥100,000 Cr), Large-Low (70,000-99,999 Cr)
- Mid-High (50,000-69,999 Cr), Mid-Low (30,000-49,999 Cr)
- Small-High (10,000-29,999 Cr), Small-Low (5,000-9,999 Cr)
- Micro-High (5,000-9,999 Cr), Micro-Low (<5,000 Cr)


## 📈 NIFTY Total Market Swing Order-Flow Scanner

The dashboard now includes a cash-market swing scanner for the NIFTY Total Market universe. It analyses daily NSE full-security Bhavcopy and delivery statistics; it does not depend on MTF participation and therefore includes NIFTY Total Market EQ constituents that have no MTF record.

### Signals and interpretation

The scanner computes daily relative volume, relative traded value, close-location value, OBV and its five-session change, Accumulation/Distribution Line, 20-session Chaikin Money Flow, 14-session ATR and Money Flow Index (MFI), close-vs-average-price deviation, 5/20-session returns, and delivery percentage versus its preceding 20-session average.

- **Accumulation / distribution scores:** transparent 0–100 rule-based screening scores. Scores of 65+ are strong candidates; 45–64 are watch candidates.
- **Liquidity screen:** by default excludes stocks with less than ₹25 lakh turnover on the signal day. The dashboard has an option to include them.
- **Delivery delta:** expressed in percentage points versus the preceding 20-session average.
- **Forward-return diagnostics:** the API reports close-to-close 5/10/20-session returns and direction-adjusted hit rates for historical signals. These are descriptive diagnostics, not a fully costed or out-of-sample backtest.

Bhavcopy is end-of-day data. The scanner cannot calculate intraday bid/ask delta, CVD, footprint charts, queue position or executed aggressor-side flow. It identifies accumulation/distribution *proxies*, not confirmed institutional activity.

### Initial setup

The scanner reuses the project's PostgreSQL database and existing backend environment file. Ensure `backend/.env` has the correct database connection variables (including `DB_SSLMODE`, normally `prefer`).

From the repository root:

```bash
# 1. Download NIFTY index constituent files, including NIFTY_TOTAL_MARKET
python -m etl.download_nifty_indices

# 2. Load the downloaded constituent lists into PostgreSQL
python -m etl.load_nifty_indices

# 3. Create the additive cash-market and scanner tables
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -f sql/20_swing_scanner_schema.sql

# 4. Backfill all local full-security Bhavcopy CSV files and calculate historical features
python -m etl.backfill_swing_scanner
```

The backfill script reads the project's existing `data/data/clean/bhavcopy/sec_bhavdata_full_*.csv` archive (or `data/clean/bhavcopy`). To obtain more history, download the required date range with the existing `etl/download_bhavcopy.py` range command before running the backfill. Keep in mind that reliable 20-session averages require at least 21 trading sessions per stock.

### Daily run

```bash
python -m etl.swing_daily_runner
```

This refreshes the official NIFTY Total Market constituent file, obtains the latest available NSE full-security Bhavcopy, loads EQ constituents into `cash_market_daily`, calculates features and updates `swing_scanner_runs`.

A GitHub Actions schedule is included in `.github/workflows/swing-scanner.yml` for 19:00 IST on weekdays. Add repository Actions secrets `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`; optionally set `DB_SSLMODE` (defaults to `prefer`). The runner requires network access to NSE/Nifty Indices and database access from the GitHub-hosted runner. If your PostgreSQL server is private or IP-restricted, run the command from your own scheduled host instead.

### Swing scanner API

- `GET /api/swing/status` – universe size and latest cash-data / feature dates.
- `GET /api/swing/scanner?min_score=40&limit=750` – ranked stock candidates; supports `signal`, `trade_date` and `include_illiquid`.
- `GET /api/swing/sectors` – sector-level accumulation/distribution participation.
- `GET /api/swing/stock/{symbol}/history` – recent signal and feature history for a stock.
- `GET /api/swing/performance?signal=ACCUMULATION` – exploratory 5/10/20-session forward-return summary. Also accepts `DISTRIBUTION`, `ACCUMULATION_WATCH` and `DISTRIBUTION_WATCH`.

### Research caveats

1. The existing constituent table is refreshed to the current list; it does not yet preserve point-in-time index membership. Historical scans therefore use today's universe and have survivorship bias.
2. Corporate-action adjusted historical prices are not yet applied in the feature engine. Review splits, bonuses, demergers and symbol changes before relying on long-period results.
3. The forward-return panel overlaps observations, does not account for fees/slippage/circuit exits, and is not an out-of-sample strategy backtest.
4. The current rule-based weights and cutoffs are initial hypotheses. Validate them chronologically and separately by market-cap group before using the rankings in live decisions.
5. The schema includes a field for benchmark-relative strength, which is not currently populated because the daily index-level benchmark series has not yet been added.

## 🏗️ Architecture

```
MTF_dashboard/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py       # Application entry point
│   │   ├── config.py     # Configuration management
│   │   ├── database.py   # AsyncPG connection pool
│   │   ├── models.py     # Pydantic response models
│   │   ├── sql_loader.py # SQL query loader
│   │   └── routers/      # API endpoints
│   │       ├── market.py
│   │       ├── stocks.py
│   │       └── shockers.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React + Vite application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── api/          # API client
│   │   ├── utils/        # Formatters & helpers
│   │   ├── App.jsx       # Main dashboard
│   │   └── main.jsx
│   ├── package.json
│   └── Dockerfile
├── sql/                  # Production SQL queries
├── etl/                  # Data ingestion pipelines
├── data/                 # CSV outputs
└── docker-compose.yml
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone and navigate to project
cd MTF_dashboard

# 2. Create environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Start all services
docker-compose up -d

# 4. Access dashboard
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run database migrations (ensure PostgreSQL is running)
psql -U bseetharaman -d mtf_db -f ../sql/01_create_tables.sql

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

## 📊 API Endpoints

### Market Analytics
- `GET /api/market/overview` - Latest market overview (total MTF, active stocks)
- `GET /api/market/flow` - Market flow statistics (fresh/liquidated exposure)
- `GET /api/market/flow/latest` - Latest day's flow
- `GET /api/market/regime` - Market regime classification
- `GET /api/market/active-stocks-trend` - Active stocks trend

### Stock Analytics
- `GET /api/stocks/gainers` - Top MTF gainers (absolute ₹ Cr)
- `GET /api/stocks/losers` - Top MTF losers (absolute ₹ Cr)
- `GET /api/stocks/percent-movers` - Percentage movers (min ₹5 Cr base)
- `GET /api/stocks/concentration` - MTF concentration by stock
- `GET /api/stocks/continuous-movers` - Continuous buying/selling streaks

### Anomaly Detection
- `GET /api/shockers/volume` - Volume shockers (Z-score based)
- `GET /api/shockers/value` - Value shockers (Z-score based)

Full API documentation: http://localhost:8000/docs

## 🗄️ Database Schema

### `stocks_master`
```sql
CREATE TABLE stocks_master (
    symbol TEXT PRIMARY KEY,
    company_name TEXT,
    sector TEXT,
    market_cap_cr NUMERIC,
    created_at TIMESTAMP DEFAULT now()
);
```

### `mtf_daily`
```sql
CREATE TABLE mtf_daily (
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL REFERENCES stocks_master(symbol),
    mtf_amount_cr NUMERIC,
    mtf_quantity BIGINT,
    PRIMARY KEY (trade_date, symbol)
);
```

### `mtf_market_daily`
```sql
CREATE TABLE mtf_market_daily (
    trade_date DATE PRIMARY KEY,
    opening_outstanding_cr NUMERIC,
    fresh_exposure_cr NUMERIC,
    liquidated_exposure_cr NUMERIC,
    closing_outstanding_cr NUMERIC,
    created_at TIMESTAMP DEFAULT now()
);
```

## 🔄 Data Pipeline

### Daily ETL Process

```bash
# 1. Download latest MTF data from NSE
python etl/download_mtf.py

# 2. Load into PostgreSQL
python etl/daily_runner.py

# 3. Generate analytics (optional CSV exports)
bash scripts/run_analysis.sh
```

### Backfill Historical Data

```bash
python etl/backfill_runner.py
```

## 🎨 Dashboard Wireframe

```
+-----------------------------------------------------------+
|  MTF Market Intelligence Dashboard   Last Updated: DD-MMM |
+-----------------------------------------------------------+
| Market Regime: RISK_ON 🔴 / NEUTRAL 🟡 / RISK_OFF 🟢     |
+-----------------------------------------------------------+
| Total MTF    | Net Flow   | Active    | Fresh    | Liquid.|
| ₹112,049 Cr  | -₹493 Cr   | 2,099     | ₹5,234Cr | ₹5,727Cr|
+-----------------------------------------------------------+
|  Top Gainers (₹ Cr)     |  Top Losers (₹ Cr)             |
|  #  Symbol     Change    |  #  Symbol     Change          |
|  1  INFY       +224      |  1  XYZ        -180            |
|  2  VEDL       +168      |  2  ABC        -145            |
+-----------------------------------------------------------+
|  MTF Concentration (%)                                    |
|  HAL 1.47%  |  JIOFIN 1.24%  |  MAZDOCK 1.02%  ⚠️       |
+-----------------------------------------------------------+
|  Continuous Movers (≥3 Days)                              |
|  Symbol | Cap  | Direction | Days | Total Change          |
|  ABC    | Mid  | 📈 Buy    | 7    | +320                 |
|  XYZ    | Sm   | 📉 Sell   | 6    | -210                 |
+-----------------------------------------------------------+
```

## ⚙️ Configuration

### Backend (`backend/.env`)
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mtf_db
DB_USER=bseetharaman
DB_PASSWORD=your_password

API_TITLE=MTF Market Intelligence API
API_VERSION=1.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend (`frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## 📈 Performance Targets

- API Response Time: <300ms per endpoint
- Dashboard Load Time: <2 seconds
- Database Query Optimization: Indexed on (trade_date, symbol)
- Connection Pooling: 2-10 concurrent connections

## 🔒 Security Considerations

- Read-only analytics (no mutations)
- CORS configured for specific origins
- Environment variables for sensitive data
- SQL injection prevention via parameterized queries
- Connection pool timeout: 60 seconds

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

## 📦 Production Deployment

### Using Docker Compose

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Deployment

1. **Backend**: Use Gunicorn/Uvicorn with systemd service
2. **Frontend**: Build and serve with Nginx
3. **Database**: Configure PostgreSQL with proper backups
4. **Monitoring**: Set up logging and health checks

## 🛠️ Maintenance

### Daily Tasks
- Run ETL pipeline: `python etl/daily_runner.py`
- Monitor error logs: `data/logs/mtf_download.log`

### Weekly Tasks
- Database vacuum: `VACUUM ANALYZE mtf_daily;`
- Backup database: `pg_dump mtf_db > backup.sql`

### Monthly Tasks
- Archive old data (>6 months)
- Review and optimize slow queries
- Update market cap data

## 📝 API Response Examples

### Market Overview
```json
{
  "trade_date": "2025-12-18",
  "total_mtf_cr": 112049.23,
  "active_mtf_stocks": 2099
}
```

### Market Regime
```json
{
  "trade_date": "2025-12-18",
  "opening_outstanding_cr": 112542.50,
  "closing_outstanding_cr": 112049.23,
  "fresh_exposure_cr": 5234.12,
  "liquidated_exposure_cr": 5727.39,
  "net_flow_cr": -493.27,
  "regime": "NEUTRAL"
}
```

## 🎯 Success Criteria

✅ Dashboard loads latest MTF day automatically  
✅ Clear Risk-On/Risk-Off signal visible  
✅ Actionable stock-level insights in <5 seconds  
✅ Zero manual SQL execution needed  
✅ Accurate > aesthetics  

## 🤝 Contributing

1. Follow SQL-first design principles
2. Reuse existing SQL files via endpoints
3. No schema changes without approval
4. Keep UI minimal, data-dense, professional
5. No mock data - real database only

## 📄 License

Proprietary - Internal Use Only

## 👥 Target Users

- **Traders**: Short-term momentum and leverage signals
- **Market Strategists**: Risk-on/risk-off regime analysis
- **Risk Managers**: Concentration and unwind risk monitoring

## 🔗 Related Components

- ETL Pipelines: `etl/`
- SQL Analytics: `sql/`
- Shell Scripts: `scripts/`
- Raw Data: `data/`

---

**Built with FastAPI, React, PostgreSQL, and ❤️**
