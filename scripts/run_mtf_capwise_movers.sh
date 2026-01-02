#!/usr/bin/env bash
set -e

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
DB_URL="postgresql://bseetharaman@localhost:5432/mtf_db?gssencmode=disable"
OUT_BASE="./data/subcap_partitions"

# Create directory structure
for cap in large_low large_high mid_low mid_high small_low small_high micro_low micro_high; do
  mkdir -p "$OUT_BASE/$cap"
done

echo "Running MTF sub-cap partition analysis..."
echo "Output directory: $OUT_BASE"
echo "-----------------------------------------"

# =================================================
# FUNCTION TEMPLATE (inline expansion pattern)
# =================================================

run_query () {
  local outfile=$1
  local cap_filter=$2
  local direction=$3
  local order=$4

psql "$DB_URL" <<SQL > "$outfile"
WITH ranked AS (
    SELECT
        d.trade_date,
        d.symbol,
        NULLIF(d.mtf_amount_cr, 'NaN'::numeric) AS mtf_amount_cr,
        LAG(NULLIF(d.mtf_amount_cr, 'NaN'::numeric))
            OVER (PARTITION BY d.symbol ORDER BY d.trade_date) AS prev_mtf_amount_cr
    FROM mtf_daily d
    WHERE d.symbol ~ '^[A-Z0-9]+$'
),
deltas AS (
    SELECT
        trade_date,
        symbol,
        (mtf_amount_cr - prev_mtf_amount_cr) AS mtf_change_cr
    FROM ranked
    WHERE prev_mtf_amount_cr IS NOT NULL
),
latest_day AS (
    SELECT MAX(trade_date) AS trade_date FROM deltas
)
SELECT
    d.trade_date,
    d.symbol,
    ROUND(d.mtf_change_cr, 2) AS mtf_change_cr
FROM deltas d
JOIN latest_day l ON d.trade_date = l.trade_date
JOIN stocks_master s ON d.symbol = s.symbol
WHERE d.mtf_change_cr $direction 0
  AND $cap_filter
ORDER BY d.mtf_change_cr $order
LIMIT 10;
SQL
}

# =================================================
# LARGE CAP
# =================================================

# Large-Low: 70,000 – 100,000
run_query "$OUT_BASE/large_low/positive.csv"  "s.market_cap_cr BETWEEN 70000 AND 99999" ">" "DESC"
run_query "$OUT_BASE/large_low/negative.csv"  "s.market_cap_cr BETWEEN 70000 AND 99999" "<" "ASC"

# Large-High: ≥ 100,000
run_query "$OUT_BASE/large_high/positive.csv" "s.market_cap_cr >= 100000" ">" "DESC"
run_query "$OUT_BASE/large_high/negative.csv" "s.market_cap_cr >= 100000" "<" "ASC"

# =================================================
# MID CAP
# =================================================

# Mid-Low: 30,000 – 50,000
run_query "$OUT_BASE/mid_low/positive.csv"    "s.market_cap_cr BETWEEN 30000 AND 49999" ">" "DESC"
run_query "$OUT_BASE/mid_low/negative.csv"    "s.market_cap_cr BETWEEN 30000 AND 49999" "<" "ASC"

# Mid-High: 50,000 – 70,000
run_query "$OUT_BASE/mid_high/positive.csv"   "s.market_cap_cr BETWEEN 50000 AND 69999" ">" "DESC"
run_query "$OUT_BASE/mid_high/negative.csv"   "s.market_cap_cr BETWEEN 50000 AND 69999" "<" "ASC"

# =================================================
# SMALL CAP
# =================================================

# Small-Low: 5,000 – 10,000
run_query "$OUT_BASE/small_low/positive.csv"  "s.market_cap_cr BETWEEN 5000 AND 9999" ">" "DESC"
run_query "$OUT_BASE/small_low/negative.csv"  "s.market_cap_cr BETWEEN 5000 AND 9999" "<" "ASC"

# Small-High: 10,000 – 30,000
run_query "$OUT_BASE/small_high/positive.csv" "s.market_cap_cr BETWEEN 10000 AND 29999" ">" "DESC"
run_query "$OUT_BASE/small_high/negative.csv" "s.market_cap_cr BETWEEN 10000 AND 29999" "<" "ASC"

# =================================================
# MICRO CAP
# =================================================

# Micro-Low: < 5,000
run_query "$OUT_BASE/micro_low/positive.csv"  "s.market_cap_cr < 5000" ">" "DESC"
run_query "$OUT_BASE/micro_low/negative.csv"  "s.market_cap_cr < 5000" "<" "ASC"

# Micro-High: 5,000 – 10,000
run_query "$OUT_BASE/micro_high/positive.csv" "s.market_cap_cr BETWEEN 5000 AND 9999" ">" "DESC"
run_query "$OUT_BASE/micro_high/negative.csv" "s.market_cap_cr BETWEEN 5000 AND 9999" "<" "ASC"

echo "✅ Sub-cap partition analysis completed successfully."
