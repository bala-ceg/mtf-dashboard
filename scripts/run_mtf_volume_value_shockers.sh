#!/usr/bin/env bash
# =====================================================
# run_mtf_volume_value_shockers.sh
# Generate MTF volume and value shockers report
# Top 10 positive and negative movers (past 10 trading sessions)
# =====================================================

DB_URL="postgresql://bseetharaman@localhost:5432/mtf_db?gssencmode=disable"
OUT_DIR="./data/analysis"

mkdir -p "$OUT_DIR"

echo "📊 Generating MTF Volume & Value Shockers Report..."
echo "======================================================"

# Run the MTF shockers query and save to file
psql "$DB_URL" -f ./sql/13_mtf_volume_value_shockers.sql > "$OUT_DIR/mtf_volume_value_shockers.csv"

echo "✅ Report generated successfully!"
echo "📈 Output saved to: $OUT_DIR/mtf_volume_value_shockers.csv"
echo ""
echo "📊 Summary Statistics:"
echo "---"

# Count by category
echo "Total Shockers Identified:"
tail -n +3 "$OUT_DIR/mtf_volume_value_shockers.csv" | wc -l

echo ""
echo "Top 10 Positive Shockers:"
grep "TOP 10 POSITIVE" "$OUT_DIR/mtf_volume_value_shockers.csv" | head -10

echo ""
echo "Top 10 Negative Shockers:"
grep "TOP 10 NEGATIVE" "$OUT_DIR/mtf_volume_value_shockers.csv" | head -10

echo ""
echo "Shocker Type Breakdown:"
grep -o "High Positive Shocker\|High Negative Shocker\|Moderate Positive Shocker\|Moderate Negative Shocker" "$OUT_DIR/mtf_volume_value_shockers.csv" | sort | uniq -c
