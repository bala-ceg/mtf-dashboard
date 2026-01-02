from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from ..database import execute_query
from ..models import TopMover, PercentMover, Concentration, ConcentrationByCategory, ContinuousMover
from ..sql_loader import load_sql_query

router = APIRouter(prefix="/stocks", tags=["Stock Analytics"])


@router.get("/gainers", response_model=List[TopMover])
async def get_top_gainers(limit: int = Query(20, ge=1, le=100)):
    """
    Get top MTF gainers by absolute ₹ Cr change (latest day)
    
    Default: Top 20 stocks
    """
    query = load_sql_query("top_gainers")
    # Query already has LIMIT 20, replace if needed
    if limit != 20:
        query = query.replace("LIMIT 20", f"LIMIT {limit}")
    
    results = await execute_query(query)
    return results


@router.get("/losers", response_model=List[TopMover])
async def get_top_losers(limit: int = Query(20, ge=1, le=100)):
    """
    Get top MTF losers by absolute ₹ Cr change (latest day)
    
    Default: Top 20 stocks
    """
    query = load_sql_query("top_losers")
    # Query already has LIMIT 20, replace if needed
    if limit != 20:
        query = query.replace("LIMIT 20", f"LIMIT {limit}")
    
    results = await execute_query(query)
    return results


@router.get("/percent-movers", response_model=List[PercentMover])
async def get_percent_movers(
    direction: Optional[str] = Query(None, regex="^(positive|negative)$"),
    market_cap_category: Optional[str] = Query(None)
):
    """
    Get percentage movers (minimum base ₹5 Cr)
    
    Optional filters:
    - direction: "positive" or "negative"
    - market_cap_category: e.g., "Large-High", "Mid-Low", etc.
    """
    query = load_sql_query("percent_movers")
    results = await execute_query(query)
    
    # Apply filters in Python (could also modify SQL)
    if direction:
        if direction == "positive":
            results = [r for r in results if r.get("mtf_change_cr", 0) > 0]
        else:
            results = [r for r in results if r.get("mtf_change_cr", 0) < 0]
    
    if market_cap_category:
        results = [r for r in results if r.get("market_cap_category") == market_cap_category]
    
    return results


@router.get("/concentration", response_model=List[Concentration])
async def get_concentration(limit: int = Query(20, ge=1, le=100)):
    """
    Get MTF concentration by stock (latest day)
    
    Shows top stocks by % of total market MTF
    Default: Top 20 stocks
    """
    query = load_sql_query("concentration")
    
    if limit != 20:
        query = query.replace("LIMIT 20", f"LIMIT {limit}")
    
    results = await execute_query(query)
    return results


@router.get("/continuous-movers", response_model=List[ContinuousMover])
async def get_continuous_movers(
    min_days: int = Query(3, ge=3, le=10),
    direction: Optional[str] = Query(None, regex="^(positive|negative)$"),
    market_cap_category: Optional[str] = Query(None)
):
    """
    Get stocks with continuous MTF buying/selling streaks
    
    Filters:
    - min_days: Minimum consecutive days (default: 3)
    - direction: "positive" or "negative"
    - market_cap_category: e.g., "Large-High", "Mid-Low", etc.
    """
    query = load_sql_query("continuous_movers")
    results = await execute_query(query)
    
    # Apply filters
    filtered = [r for r in results if r.get("consecutive_days", 0) >= min_days]
    
    if direction:
        filtered = [r for r in filtered if r.get("direction") == direction]
    
    if market_cap_category:
        filtered = [r for r in filtered if r.get("market_cap_category") == market_cap_category]
    
    return filtered


@router.get("/concentration-by-category", response_model=Dict[str, List[ConcentrationByCategory]])
async def get_concentration_by_category(
    top_n: int = Query(10, ge=5, le=50, description="Top N stocks per category")
):
    """
    Get MTF concentration grouped by market cap category
    
    Returns top stocks by category share % within each segment:
    - Large-High (≥100k Cr)
    - Large-Low (70-99k Cr)
    - Mid-High (50-69k Cr)
    - Mid-Low (30-49k Cr)
    - Small-High (10-29k Cr)
    - Small-Low (5-9k Cr)
    - Micro-High (5-9k Cr)
    - Micro-Low (<5k Cr)
    """
    query = load_sql_query("concentration_by_market_cap")
    results = await execute_query(query)
    
    # Group by category and take top N per category
    grouped = {}
    for row in results:
        category = row.get("market_cap_category")
        if category not in grouped:
            grouped[category] = []
        if len(grouped[category]) < top_n:
            grouped[category].append(row)
    
    return grouped
