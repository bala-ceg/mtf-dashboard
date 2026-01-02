#!/usr/bin/env bash
# =====================================================
# run_continuous_mtf_movers.sh
# Generate continuous MTF movers report for all market cap categories
# =====================================================

DB_URL="postgresql://bseetharaman@localhost:5432/mtf_db?gssencmode=disable"
OUT_DIR="./data/analysis"

mkdir -p "$OUT_DIR"

echo "🔄 Generating Continuous MTF Movers Report..."
echo "================================================"

# Run the continuous MTF movers query and save to file
psql "$DB_URL" -f ./sql/12_continuous_mtf_movers.sql > "$OUT_DIR/continuous_mtf_movers.csv"

echo "✅ Report generated successfully!"
echo "📊 Output saved to: $OUT_DIR/continuous_mtf_movers.csv"
echo ""
echo "📈 Summary Statistics:"
echo "---"

# Count by direction
echo "Continuous Buying Streaks:"
grep "Continuous Buying" "$OUT_DIR/continuous_mtf_movers.csv" | wc -l

echo "Continuous Selling Streaks:"
grep "Continuous Selling" "$OUT_DIR/continuous_mtf_movers.csv" | wc -l

echo ""
echo "Top 5 Longest Positive Streaks:"
grep "Continuous Buying" "$OUT_DIR/continuous_mtf_movers.csv" | sort -t'|' -k4 -rn | head -5

echo ""
echo "Top 5 Longest Negative Streaks:"
grep "Continuous Selling" "$OUT_DIR/continuous_mtf_movers.csv" | sort -t'|' -k4 -rn | head -5
