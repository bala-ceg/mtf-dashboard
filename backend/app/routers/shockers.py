from fastapi import APIRouter, Query
from typing import List, Optional
from ..database import execute_query
from ..models import VolumeShocker, ValueShocker
from ..sql_loader import load_sql_query

router = APIRouter(prefix="/shockers", tags=["Anomaly Detection"])


@router.get("/volume", response_model=List[VolumeShocker])
async def get_volume_shockers(
    min_z_score: float = Query(2.0, ge=1.5),
    market_cap_category: Optional[str] = Query(None)
):
    """
    Get volume shockers (Z-score based anomalies on MTF quantity)
    
    Filters:
    - min_z_score: Minimum Z-score threshold (default: 2.0)
    - market_cap_category: Filter by market cap segment
    
    Uses 10-day rolling window for Z-score calculation
    """
    query = load_sql_query("volume_shockers")
    results = await execute_query(query)
    
    # Filter by Z-score and category
    filtered = [r for r in results if abs(r.get("z_score", 0)) >= min_z_score]
    
    if market_cap_category:
        filtered = [r for r in filtered if r.get("market_cap_category") == market_cap_category]
    
    # Sort by Z-score magnitude
    filtered.sort(key=lambda x: abs(x.get("z_score", 0)), reverse=True)
    
    return filtered


@router.get("/value", response_model=List[ValueShocker])
async def get_value_shockers(
    min_z_score: float = Query(2.0, ge=1.5),
    market_cap_category: Optional[str] = Query(None)
):
    """
    Get value shockers (Z-score based anomalies on MTF amount)
    
    Filters:
    - min_z_score: Minimum Z-score threshold (default: 2.0)
    - market_cap_category: Filter by market cap segment
    
    Uses 10-day rolling window for Z-score calculation
    """
    query = load_sql_query("value_shockers")
    results = await execute_query(query)
    
    # Filter by Z-score and category
    filtered = [r for r in results if abs(r.get("z_score", 0)) >= min_z_score]
    
    if market_cap_category:
        filtered = [r for r in filtered if r.get("market_cap_category") == market_cap_category]
    
    # Sort by Z-score magnitude
    filtered.sort(key=lambda x: abs(x.get("z_score", 0)), reverse=True)
    
    return filtered
