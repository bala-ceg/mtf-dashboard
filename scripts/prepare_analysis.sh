#!/bin/bash
# Master script to export data and generate analysis prompts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "MTF Data Export & Analysis Prompt Generator"
echo "=========================================="
echo ""

# Step 1: Export data
echo "Step 1: Exporting dashboard data..."
python3 "$SCRIPT_DIR/export_analysis_data.py"

if [ $? -ne 0 ]; then
    echo "✗ Data export failed"
    exit 1
fi

echo ""

# Step 2: Generate prompts
echo "Step 2: Generating analysis prompts..."
python3 "$SCRIPT_DIR/generate_analysis_prompts.py"

if [ $? -ne 0 ]; then
    echo "✗ Prompt generation failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Find exported data in: data/analysis/"
echo "2. Find analysis prompts in: data/analysis/prompts/"
echo "3. Use the prompts with AI assistants for deep analysis"
echo ""
echo "Tips:"
echo "  • Load the JSON data file into your AI analysis tool"
echo "  • Use individual prompts for focused analysis"
echo "  • Use the combined prompt file for comprehensive review"
echo ""
