#!/usr/bin/env bash
set -e

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
DB_URL="postgresql://bseetharaman@localhost:5432/mtf_db?gssencmode=disable"
OUT_DIR="./data/analysis"

# Create output directory
mkdir -p "$OUT_DIR"

echo "Running MTF analysis queries..."
echo "Output directory: $OUT_DIR"
echo "-----------------------------------------"

# Run Market Overview Stats
echo "Running: Market Overview Stats"
psql "$DB_URL" -f ./sql/02_market_overview_stats.sql > "$OUT_DIR/market_overview.csv"

# Run Market Flow Stats
echo "Running: Market Flow Stats"
psql "$DB_URL" -f ./sql/03_market_flow_stats.sql > "$OUT_DIR/market_flow.csv"

# Run Top MTF Gainers
echo "Running: Top MTF Gainers (Latest)"
psql "$DB_URL" -f ./sql/05_top_mtf_gainers_latest.sql > "$OUT_DIR/top_gainers.csv"

# Run Top MTF Losers
echo "Running: Top MTF Losers (Latest)"
psql "$DB_URL" -f ./sql/06_top_mtf_losers_latest.sql > "$OUT_DIR/top_losers.csv"

# Run MTF Percent Movers
echo "Running: MTF Percent Movers"
psql "$DB_URL" -f ./sql/07_mtf_percent_movers.sql > "$OUT_DIR/percent_movers.csv"

# Run MTF Concentration
echo "Running: MTF Concentration"
psql "$DB_URL" -f ./sql/08_mtf_concentration.sql > "$OUT_DIR/concentration.csv"

# Run Active MTF Stock Trend
echo "Running: Active MTF Stock Trend"
psql "$DB_URL" -f ./sql/09_active_mtf_stock_trend.sql > "$OUT_DIR/active_stocks_trend.csv"

# Run Market Regime Snapshot
echo "Running: Market Regime Snapshot"
psql "$DB_URL" -f ./sql/10_market_regime_snapshot.sql > "$OUT_DIR/market_regime.csv"

# Run Market Risk Regime
echo "Running: Market Risk Regime"
psql "$DB_URL" -f ./sql/11_market_risk_regime.sql > "$OUT_DIR/risk_regime.csv"

echo ""
echo "✅ Analysis completed successfully."
echo "Results saved to: $OUT_DIR"
