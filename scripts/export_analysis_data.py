#!/usr/bin/env python3
"""
Export MTF Dashboard Data for Deep Analysis
Exports all key metrics and datasets in JSON format for AI analysis
"""

import json
import psycopg2
import datetime
from pathlib import Path
import sys
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_CONFIG


def execute_query(conn, query, description):
    """Execute query and return results as list of dicts"""
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    
    # Convert any date/datetime objects to strings
    for row in results:
        for key, value in row.items():
            if isinstance(value, (datetime.date, datetime.datetime)):
                row[key] = value.isoformat()
    
    print(f"✓ Exported {len(results)} rows: {description}")
    return results


def export_all_data():
    """Export all dashboard data for analysis"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    export_data = {
        "export_timestamp": datetime.datetime.now().isoformat(),
        "export_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "data": {}
    }
    
    print("\n" + "="*60)
    print("MTF Dashboard Data Export for Deep Analysis")
    print("="*60 + "\n")
    
    # 1. Market Overview
    print("Exporting Market Overview...")
    query = Path(__file__).parent.parent / "sql" / "02_market_overview_stats.sql"
    export_data["data"]["market_overview"] = execute_query(
        conn, query.read_text(), "Market Overview"
    )
    
    # 2. Market Flow (Last 90 days)
    print("\nExporting Market Flow...")
    query = Path(__file__).parent.parent / "sql" / "03_market_flow_stats.sql"
    query_text = query.read_text().rstrip().rstrip(';')
    export_data["data"]["market_flow"] = execute_query(
        conn, query_text + "\nLIMIT 90", "Market Flow (90 days)"
    )
    
    # 3. Market Regime
    print("\nExporting Market Regime...")
    query = Path(__file__).parent.parent / "sql" / "10_market_regime_snapshot.sql"
    export_data["data"]["market_regime"] = execute_query(
        conn, query.read_text(), "Market Regime"
    )
    
    # 4. Risk Regime
    print("\nExporting Risk Regime...")
    query = Path(__file__).parent.parent / "sql" / "11_market_risk_regime.sql"
    export_data["data"]["risk_regime"] = execute_query(
        conn, query.read_text(), "Risk Regime"
    )
    
    # 5. Top Gainers (All categories)
    print("\nExporting Top Gainers...")
    query = Path(__file__).parent.parent / "sql" / "05_top_mtf_gainers_latest.sql"
    export_data["data"]["top_gainers"] = execute_query(
        conn, query.read_text().replace("LIMIT 20", "LIMIT 100"), "Top Gainers (100)"
    )
    
    # 6. Top Losers (All categories)
    print("\nExporting Top Losers...")
    query = Path(__file__).parent.parent / "sql" / "06_top_mtf_losers_latest.sql"
    export_data["data"]["top_losers"] = execute_query(
        conn, query.read_text().replace("LIMIT 20", "LIMIT 100"), "Top Losers (100)"
    )
    
    # 7. Concentration
    print("\nExporting Concentration...")
    query = Path(__file__).parent.parent / "sql" / "08_mtf_concentration.sql"
    export_data["data"]["concentration"] = execute_query(
        conn, query.read_text().replace("LIMIT 20", "LIMIT 50"), "Concentration (50)"
    )
    
    # 8. Concentration by Market Cap
    print("\nExporting Concentration by Market Cap...")
    query = Path(__file__).parent.parent / "sql" / "14_mtf_concentration_by_market_cap.sql"
    export_data["data"]["concentration_by_market_cap"] = execute_query(
        conn, query.read_text(), "Concentration by Market Cap"
    )
    
    # 9. Continuous Movers (3+ days)
    print("\nExporting Continuous Movers...")
    query = Path(__file__).parent.parent / "sql" / "12_continuous_mtf_movers.sql"
    export_data["data"]["continuous_movers"] = execute_query(
        conn, query.read_text(), "Continuous Movers"
    )
    
    # 10. Volume Shockers
    print("\nExporting Volume Shockers...")
    query = Path(__file__).parent.parent / "sql" / "13a_mtf_volume_shockers.sql"
    export_data["data"]["volume_shockers"] = execute_query(
        conn, query.read_text(), "Volume Shockers"
    )
    
    # 11. Active Stock Trend (90 days)
    print("\nExporting Active Stock Trend...")
    query = Path(__file__).parent.parent / "sql" / "09_active_mtf_stock_trend.sql"
    query_text = query.read_text().rstrip().rstrip(';')
    export_data["data"]["active_stock_trend"] = execute_query(
        conn, query_text + "\nLIMIT 90", "Active Stock Trend (90 days)"
    )
    
    # 12. Top MTF by Index
    print("\nExporting Top MTF by Index...")
    query = Path(__file__).parent.parent / "sql" / "16_top_mtf_by_index.sql"
    export_data["data"]["top_mtf_by_index"] = execute_query(
        conn, query.read_text(), "Top MTF by Index"
    )
    
    # 13. Recent MTF Daily Data (Last 30 days, top stocks)
    print("\nExporting Recent MTF Daily Data...")
    recent_query = """
    WITH latest_date AS (
        SELECT MAX(trade_date) as max_date FROM mtf_daily
    ),
    top_stocks AS (
        SELECT symbol, mtf_amount_cr
        FROM mtf_daily 
        WHERE trade_date = (SELECT max_date FROM latest_date)
        ORDER BY mtf_amount_cr DESC 
        LIMIT 200
    )
    SELECT 
        md.trade_date,
        md.symbol,
        sm.company_name,
        sm.market_cap_cr,
        cat.market_cap_category,
        md.mtf_amount_cr,
        md.mtf_quantity
    FROM mtf_daily md
    INNER JOIN top_stocks ts ON md.symbol = ts.symbol
    LEFT JOIN stocks_master sm ON md.symbol = sm.symbol
    LEFT JOIN (
        SELECT symbol, market_cap_category FROM (
            SELECT symbol, 
                CASE
                    WHEN market_cap_cr >= 100000 THEN 'Large-High'
                    WHEN market_cap_cr BETWEEN 70000 AND 99999 THEN 'Large-Low'
                    WHEN market_cap_cr BETWEEN 50000 AND 69999 THEN 'Mid-High'
                    WHEN market_cap_cr BETWEEN 30000 AND 49999 THEN 'Mid-Low'
                    WHEN market_cap_cr BETWEEN 10000 AND 29999 THEN 'Small-High'
                    WHEN market_cap_cr BETWEEN 5000 AND 9999 THEN 'Small-Low'
                    WHEN market_cap_cr BETWEEN 1000 AND 4999 THEN 'Micro-High'
                    ELSE 'Micro-Low'
                END as market_cap_category
            FROM stocks_master
        ) x
    ) cat ON md.symbol = cat.symbol
    WHERE md.trade_date >= (SELECT max_date FROM latest_date) - INTERVAL '30 days'
    ORDER BY md.trade_date DESC, md.mtf_amount_cr DESC
    """
    export_data["data"]["recent_daily_data"] = execute_query(
        conn, recent_query, "Recent Daily Data (30 days, top 200 stocks)"
    )
    
    # 14. Stock Master Data
    print("\nExporting Stock Master Data...")
    master_query = """
    SELECT 
        symbol,
        company_name,
        market_cap_cr,
        CASE
            WHEN market_cap_cr >= 100000 THEN 'Large-High'
            WHEN market_cap_cr BETWEEN 70000 AND 99999 THEN 'Large-Low'
            WHEN market_cap_cr BETWEEN 50000 AND 69999 THEN 'Mid-High'
            WHEN market_cap_cr BETWEEN 30000 AND 49999 THEN 'Mid-Low'
            WHEN market_cap_cr BETWEEN 10000 AND 29999 THEN 'Small-High'
            WHEN market_cap_cr BETWEEN 5000 AND 9999 THEN 'Small-Low'
            WHEN market_cap_cr BETWEEN 1000 AND 4999 THEN 'Micro-High'
            ELSE 'Micro-Low'
        END as market_cap_category
    FROM stocks_master
    ORDER BY market_cap_cr DESC NULLS LAST
    """
    export_data["data"]["stock_master"] = execute_query(
        conn, master_query, "Stock Master Data"
    )
    
    conn.close()
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "data" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"mtf_analysis_data_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    print("\n" + "="*60)
    print(f"✓ Export Complete!")
    print(f"✓ File saved to: {output_file}")
    print(f"✓ File size: {output_file.stat().st_size / 1024:.2f} KB")
    print("="*60 + "\n")
    
    return output_file


if __name__ == "__main__":
    export_all_data()
