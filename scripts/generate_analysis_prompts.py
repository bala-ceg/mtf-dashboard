#!/usr/bin/env python3
"""
Generate AI Analysis Prompts for MTF Dashboard Data
Creates comprehensive prompts for deep analysis of margin trading patterns
"""

import json
from pathlib import Path
from datetime import datetime


def load_latest_export():
    """Load the most recent data export"""
    analysis_dir = Path(__file__).parent.parent / "data" / "analysis"
    
    if not analysis_dir.exists():
        print("No analysis data found. Please run export_analysis_data.py first.")
        return None
    
    # Get the most recent export file
    export_files = sorted(analysis_dir.glob("mtf_analysis_data_*.json"), reverse=True)
    
    if not export_files:
        print("No export files found. Please run export_analysis_data.py first.")
        return None
    
    latest_file = export_files[0]
    print(f"Loading data from: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        return json.load(f)


def generate_summary_stats(data):
    """Generate summary statistics from the data"""
    stats = {}
    
    # Market Overview
    if data["data"].get("market_overview"):
        overview = data["data"]["market_overview"][0]
        stats["total_mtf_outstanding"] = overview.get("total_mtf_outstanding_cr", 0)
        stats["active_stocks"] = overview.get("active_mtf_stocks", 0)
        stats["trade_date"] = overview.get("trade_date", "N/A")
    
    # Market Regime
    if data["data"].get("market_regime"):
        regime = data["data"]["market_regime"][0]
        stats["market_regime"] = regime.get("regime", "N/A")
        stats["days_in_regime"] = regime.get("days_in_regime", 0)
    
    # Risk Level
    if data["data"].get("risk_regime"):
        risk = data["data"]["risk_regime"][0]
        stats["risk_level"] = risk.get("risk_level", "N/A")
    
    # Top categories
    stats["top_gainers_count"] = len(data["data"].get("top_gainers", []))
    stats["top_losers_count"] = len(data["data"].get("top_losers", []))
    stats["continuous_movers_count"] = len(data["data"].get("continuous_movers", []))
    stats["volume_shockers_count"] = len(data["data"].get("volume_shockers", []))
    
    return stats


def generate_prompts(data):
    """Generate comprehensive analysis prompts"""
    
    stats = generate_summary_stats(data)
    
    prompts = {
        "overview_analysis": f"""# MTF Market Overview Analysis

Please analyze the following Margin Trading Facility (MTF) market data:

## Market Summary
- **Total MTF Outstanding**: ₹{stats.get('total_mtf_outstanding', 0):,.2f} Cr
- **Active MTF Stocks**: {stats.get('active_stocks', 0):,}
- **Trade Date**: {stats.get('trade_date', 'N/A')}
- **Market Regime**: {stats.get('market_regime', 'N/A')} (for {stats.get('days_in_regime', 0)} days)
- **Risk Level**: {stats.get('risk_level', 'N/A')}

## Data Included
- Market flow trends (90 days)
- Top {stats.get('top_gainers_count', 0)} gainers and {stats.get('top_losers_count', 0)} losers
- MTF concentration across market caps
- {stats.get('continuous_movers_count', 0)} continuous movers (3+ days)
- {stats.get('volume_shockers_count', 0)} volume shockers
- Index-wise top MTF holdings
- Recent 30-day trends for top 200 stocks

## Analysis Required

1. **Market Health Assessment**
   - Overall market sentiment based on MTF flows
   - Risk indicators and warning signs
   - Comparison with historical norms

2. **Sector & Industry Trends**
   - Which sectors are seeing increased margin activity?
   - Are there concerning concentrations in specific industries?
   - Cross-sector correlation patterns

3. **Stock-Level Insights**
   - Identify stocks with unusual MTF activity
   - Momentum patterns in continuous movers
   - Risk assessment for highly leveraged stocks

4. **Market Cap Analysis**
   - MTF distribution across Large/Mid/Small/Micro caps
   - Which category poses the most risk?
   - Liquidity concerns by category

5. **Predictive Indicators**
   - Early warning signals from the data
   - Potential trend reversals
   - Stocks to watch closely

6. **Index Analysis**
   - MTF concentration in major indices
   - Systemic risk from index heavyweights
   - Comparison across Nifty 50/Next 50/Midcap/Smallcap

Please provide:
- Executive summary (3-5 key findings)
- Detailed analysis with data-backed insights
- Risk alerts and recommendations
- Stocks/sectors requiring immediate attention

DATA_FILE: {data.get('export_timestamp', 'N/A')}
""",

        "risk_analysis": f"""# MTF Risk Deep Dive Analysis

## Context
Analyzing {stats.get('total_mtf_outstanding', 0):,.2f} Cr of MTF exposure across {stats.get('active_stocks', 0):,} stocks.
Current Market Regime: {stats.get('market_regime', 'N/A')}
Risk Level: {stats.get('risk_level', 'N/A')}

## Focus Areas

1. **Concentration Risk**
   - Top 10/20/50 stocks holding majority of MTF
   - Single-stock risk exposure
   - Industry concentration concerns

2. **Liquidity Risk**
   - Small/Micro cap stocks with high MTF
   - Volume shockers indicating liquidity stress
   - Stocks where MTF is growing faster than market cap

3. **Momentum Risk**
   - Continuous movers creating momentum bubbles
   - Stocks with rapid MTF expansion
   - Potential cascade effects

4. **Systemic Risk**
   - Interconnected positions across indices
   - Broker concentration (if available)
   - Market-wide leverage indicators

5. **Early Warning Signals**
   - Divergence between price and MTF trends
   - Unusual patterns in flow data
   - Regime change indicators

## Deliverables Needed
- Risk score for top 50 stocks (0-100)
- Red flags list with severity ratings
- Monitoring watchlist with thresholds
- Scenario analysis (if market corrects 5%, 10%, 15%)

Provide actionable intelligence for risk management.

DATA_FILE: {data.get('export_timestamp', 'N/A')}
""",

        "sector_analysis": f"""# Sector-wise MTF Analysis

## Objective
Deep dive into sector and industry trends in margin trading activity.

## Analysis Framework

1. **Sector Distribution**
   - MTF exposure by major sectors
   - Growth rates by sector (recent vs historical)
   - Sector rotation patterns

2. **Industry Hotspots**
   - Which industries show concentrated MTF activity?
   - Emerging vs declining industry trends
   - Correlation with sector performance

3. **Cross-Sector Patterns**
   - Contagion risk between related sectors
   - Defensive vs aggressive sector positioning
   - Sector-wise continuous movers

4. **Comparative Analysis**
   - Sectors overweight vs market cap
   - Unusual sector-level patterns
   - Historical sector comparison

5. **Sector Risk Assessment**
   - High-risk sectors with excessive leverage
   - Stable sectors with healthy MTF
   - Sectors showing stress signals

## Output Format
For each major sector:
- Total MTF exposure (₹ Cr and % of total)
- Top stocks in the sector
- Risk rating and trend direction
- Key observations and recommendations

Focus on actionable sector-level insights.

DATA_FILE: {data.get('export_timestamp', 'N/A')}
""",

        "stock_screening": f"""# Individual Stock Analysis & Screening

## Screening Criteria

Using the MTF data, screen stocks for:

1. **High Risk Stocks**
   - MTF > 20% of market cap
   - Continuous upward movers for 5+ days
   - Small/Micro caps with sudden MTF spikes
   - Declining stocks with increasing MTF

2. **Quality MTF Stocks**
   - Large caps with stable MTF
   - Healthy MTF growth aligned with fundamentals
   - Liquid stocks with reasonable leverage

3. **Momentum Plays**
   - Strong continuous movers (3-7 days)
   - Increasing MTF with price momentum
   - Breakout candidates

4. **Value Traps**
   - Stocks where MTF is declining but price stable
   - High MTF concentration with low volumes
   - Potential liquidation candidates

5. **Index Leaders**
   - Top MTF stocks in Nifty 50
   - Index heavyweights with unusual patterns
   - Systematic importance analysis

## For Each Screened Stock Provide:
- Symbol, Company Name, Industry
- Current MTF metrics and trends
- Risk assessment (Low/Medium/High/Critical)
- Key observations
- Recommendation (Buy/Hold/Avoid/Exit)

Create 5 separate lists for the above categories.

DATA_FILE: {data.get('export_timestamp', 'N/A')}
""",

        "trend_prediction": f"""# MTF Trend Analysis & Predictions

## Objective
Identify emerging trends and predict near-term movements in margin trading activity.

## Analysis Areas

1. **Market Flow Trends**
   - Daily fresh vs liquidated exposure patterns
   - Net flow direction and momentum
   - Acceleration/deceleration signals

2. **Stock-Level Trends**
   - Stocks entering uptrend/downtrend cycles
   - Momentum sustainability analysis
   - Reversal candidates

3. **Category Shifts**
   - Movement between market cap categories
   - Sector rotation patterns
   - Index rebalancing impacts

4. **Volume & Liquidity Trends**
   - Volume shockers becoming normalized
   - Liquidity stress building up
   - Trading pattern changes

5. **Regime Analysis**
   - How long will current regime last?
   - Triggers for regime change
   - Historical regime transition patterns

## Predictions Required

For next 5-10 trading days:
- Market regime (Risk On/Off/Neutral)
- Top 10 stocks likely to see MTF surge
- Top 10 stocks likely to see MTF decline
- Sectors to watch
- Potential black swan events

Provide confidence levels (Low/Medium/High) for each prediction.

DATA_FILE: {data.get('export_timestamp', 'N/A')}
""",

        "comparative_analysis": f"""# Historical & Comparative Analysis

## Data Context
Current Date: {stats.get('trade_date', 'N/A')}
Market Regime: {stats.get('market_regime', 'N/A')} (Day {stats.get('days_in_regime', 0)})

## Comparative Studies

1. **Time-based Comparison**
   - Current vs 30 days ago
   - Current vs 90 days ago
   - Year-over-year patterns (if data available)

2. **Category Comparison**
   - Large vs Mid vs Small vs Micro caps
   - Index constituents vs non-constituents
   - Gainers vs losers patterns

3. **Concentration Trends**
   - Top 10, 20, 50 concentration changes
   - Diversification trends
   - New entrants vs exits

4. **Flow Analysis**
   - Fresh exposure trends
   - Liquidation patterns
   - Net flow volatility

5. **Anomaly Detection**
   - Stocks deviating from historical patterns
   - Unusual sector movements
   - Divergence from market behavior

## Deliverables
- Change matrices (% change across periods)
- Trend charts description
- Anomaly report
- Historical context for current patterns

Highlight significant changes and their implications.

DATA_FILE: {data.get('export_timestamp', 'N/A')}
"""
    }
    
    return prompts


def save_prompts(prompts, data):
    """Save prompts to files"""
    
    output_dir = Path(__file__).parent.parent / "data" / "analysis" / "prompts"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save individual prompts
    for prompt_name, prompt_text in prompts.items():
        prompt_file = output_dir / f"{prompt_name}_{timestamp}.md"
        with open(prompt_file, 'w') as f:
            f.write(prompt_text)
        print(f"✓ Saved: {prompt_file.name}")
    
    # Save combined prompt
    combined_file = output_dir / f"all_prompts_{timestamp}.md"
    with open(combined_file, 'w') as f:
        f.write("# MTF Dashboard - Comprehensive Analysis Prompts\n\n")
        f.write(f"Generated: {timestamp}\n\n")
        f.write("---\n\n")
        for prompt_name, prompt_text in prompts.items():
            f.write(f"\n\n{prompt_text}\n\n")
            f.write("\n---\n\n")
    
    print(f"\n✓ Combined prompts saved to: {combined_file.name}")
    
    # Save data reference
    data_ref_file = output_dir / f"data_reference_{timestamp}.json"
    with open(data_ref_file, 'w') as f:
        json.dump({
            "export_timestamp": data.get("export_timestamp"),
            "export_date": data.get("export_date"),
            "data_summary": generate_summary_stats(data),
            "data_keys": list(data["data"].keys()),
            "record_counts": {k: len(v) for k, v in data["data"].items()}
        }, f, indent=2)
    
    print(f"✓ Data reference saved to: {data_ref_file.name}")


def main():
    """Main execution"""
    print("\n" + "="*60)
    print("MTF Analysis Prompt Generator")
    print("="*60 + "\n")
    
    # Load data
    data = load_latest_export()
    if not data:
        return
    
    print("\nGenerating analysis prompts...\n")
    
    # Generate prompts
    prompts = generate_prompts(data)
    
    # Save prompts
    save_prompts(prompts, data)
    
    print("\n" + "="*60)
    print("✓ Prompt Generation Complete!")
    print("="*60)
    print("\nYou can now use these prompts with the exported data for:")
    print("  • ChatGPT / Claude / other AI assistants")
    print("  • Custom analysis scripts")
    print("  • Research and reporting")
    print("\nPrompts are tailored for different analysis perspectives.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
