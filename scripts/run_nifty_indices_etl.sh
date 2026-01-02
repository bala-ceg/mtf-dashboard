#!/bin/bash
# Script to download and load Nifty index constituents

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Nifty Index Constituents ETL"
echo "=========================================="
echo ""

# Step 1: Download index constituent CSV files
echo "Step 1: Downloading Nifty index constituent lists..."
python3 -m etl.download_nifty_indices

if [ $? -eq 0 ]; then
    echo "✓ Download completed successfully"
else
    echo "✗ Download failed"
    exit 1
fi

echo ""
echo "Step 2: Loading constituents into database..."
python3 -m etl.load_nifty_indices

if [ $? -eq 0 ]; then
    echo "✓ Load completed successfully"
else
    echo "✗ Load failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Nifty Index Constituents ETL Complete!"
echo "=========================================="
echo ""
echo "You can now view the top MTF holdings by index in the dashboard."
