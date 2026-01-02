from fastapi import APIRouter, HTTPException
from typing import List
from ..database import execute_query, execute_query_one
from ..models import MarketOverview, MarketFlow, MarketRegime, ActiveStockTrend
from ..sql_loader import load_sql_query

router = APIRouter(prefix="/market", tags=["Market Analytics"])


@router.get("/overview", response_model=MarketOverview)
async def get_market_overview():
    """
    Get latest market overview statistics:
    - Total MTF Outstanding (₹ Cr)
    - Active MTF stocks count
    """
    query = load_sql_query("market_overview")
    result = await execute_query_one(query)
    
    if not result:
        raise HTTPException(status_code=404, detail="No market data available")
    
    return result


@router.get("/flow", response_model=List[MarketFlow])
async def get_market_flow(limit: int = 30):
    """
    Get market flow statistics (daily):
    - Fresh exposure
    - Liquidated exposure
    - Net flow
    
    Default: Last 30 trading days
    """
    query = load_sql_query("market_flow")
    
    if limit:
        query += f"\nLIMIT {limit};"
    
    results = await execute_query(query)
    return results


@router.get("/flow/latest", response_model=MarketFlow)
async def get_latest_market_flow():
    """Get latest day's market flow"""
    query = load_sql_query("market_flow").rstrip().rstrip(';') + "\nLIMIT 1;"
    result = await execute_query_one(query)
    
    if not result:
        raise HTTPException(status_code=404, detail="No flow data available")
    
    return result


@router.get("/regime", response_model=MarketRegime)
async def get_market_regime():
    """
    Get market regime classification:
    - RISK_ON: Net flow > +500 Cr
    - RISK_OFF: Net flow < -500 Cr
    - NEUTRAL: Between -500 and +500 Cr
    """
    query = load_sql_query("market_regime")
    result = await execute_query_one(query)
    
    if not result:
        raise HTTPException(status_code=404, detail="No regime data available")
    
    # Add regime classification
    net_flow = result.get("net_flow_cr", 0) or 0
    
    if net_flow > 500:
        regime = "RISK_ON"
    elif net_flow < -500:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"
    
    result["regime"] = regime
    return result


@router.get("/active-stocks-trend", response_model=List[ActiveStockTrend])
async def get_active_stocks_trend(limit: int = 30):
    """
    Get trend of active MTF stocks over time
    
    Default: Last 30 trading days
    """
    query = load_sql_query("active_stocks_trend")
    
    if limit:
        query += f"\nLIMIT {limit};"
    
    results = await execute_query(query)
    return results
