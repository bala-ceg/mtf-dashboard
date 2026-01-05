from pathlib import Path

# SQL files directory
SQL_DIR = Path(__file__).parent.parent.parent / "sql"

# SQL Query Registry - Maps each SQL file to its purpose
SQL_QUERIES = {
    "market_overview": SQL_DIR / "02_market_overview_stats.sql",
    "market_flow": SQL_DIR / "03_market_flow_stats.sql",
    "top_gainers": SQL_DIR / "05_top_mtf_gainers_latest.sql",
    "top_losers": SQL_DIR / "06_top_mtf_losers_latest.sql",
    "percent_movers": SQL_DIR / "07_mtf_percent_movers.sql",
    "concentration": SQL_DIR / "08_mtf_concentration.sql",
    "active_stocks_trend": SQL_DIR / "09_active_mtf_stock_trend.sql",
    "market_regime": SQL_DIR / "10_market_regime_snapshot.sql",
    "risk_regime": SQL_DIR / "11_market_risk_regime.sql",
    "continuous_movers": SQL_DIR / "12_continuous_mtf_movers.sql",
    "volume_shockers": SQL_DIR / "13a_mtf_volume_shockers.sql",
    "value_shockers": SQL_DIR / "13_mtf_volume_value_shockers.sql",
    "concentration_by_market_cap": SQL_DIR / "14_mtf_concentration_by_market_cap.sql",
    "top_mtf_by_index": SQL_DIR / "16_top_mtf_by_index.sql",
    "mtf_price_correlation": SQL_DIR / "18_mtf_price_correlation.sql",
    "index_stock_history": SQL_DIR / "19_index_stock_history.sql",
}


def load_sql_query(query_name: str) -> str:
    """Load SQL query from file"""
    sql_path = SQL_QUERIES.get(query_name)
    if not sql_path or not sql_path.exists():
        raise FileNotFoundError(f"SQL query not found: {query_name}")
    
    return sql_path.read_text()
