from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ..database import execute_query
from ..sql_loader import load_sql_query

router = APIRouter(prefix="/indices", tags=["Index Analytics"])


@router.get("/top-mtf", response_model=List[Dict[str, Any]])
async def get_top_mtf_by_index():
    """
    Get top 10 stocks by MTF holdings for each Nifty index category.
    
    Returns stocks with highest MTF exposure in:
    - NIFTY50
    - NIFTY_NEXT50
    - NIFTY_MIDCAP50
    - NIFTY_SMALLCAP50
    """
    query = load_sql_query("top_mtf_by_index")
    results = await execute_query(query)
    
    if not results:
        raise HTTPException(
            status_code=404, 
            detail="No index MTF data available. Please ensure index constituents are loaded."
        )
    
    return results


@router.get("/top-mtf/{index_name}", response_model=List[Dict[str, Any]])
async def get_top_mtf_for_specific_index(index_name: str):
    """
    Get top 10 stocks by MTF holdings for a specific index.
    
    Parameters:
    - index_name: One of NIFTY50, NIFTY_NEXT50, NIFTY_MIDCAP50, NIFTY_SMALLCAP50
    """
    query = load_sql_query("top_mtf_by_index")
    
    # Add filter for specific index
    query = query.replace(
        "WHERE rank <= 10",
        f"WHERE rank <= 10 AND index_name = '{index_name.upper()}'"
    )
    
    results = await execute_query(query)
    
    if not results:
        raise HTTPException(
            status_code=404, 
            detail=f"No MTF data available for index: {index_name}"
        )
    
    return results


@router.get("/constituents/{index_name}", response_model=List[Dict[str, Any]])
async def get_index_constituents(index_name: str):
    """
    Get all constituents for a specific index.
    
    Parameters:
    - index_name: One of NIFTY50, NIFTY_NEXT50, NIFTY_SMALLCAP50, NIFTY_MIDCAP50, NIFTY500
    """
    query = """
        SELECT 
            symbol,
            company_name,
            industry,
            series,
            isin_code,
            last_updated
        FROM nifty_index_constituents
        WHERE index_name = %s
        ORDER BY symbol
    """
    
    results = await execute_query(query, (index_name.upper(),))
    
    if not results:
        raise HTTPException(
            status_code=404, 
            detail=f"No constituents found for index: {index_name}"
        )
    
    return results


@router.get("/available", response_model=List[str])
async def get_available_indices():
    """Get list of available index names in the database."""
    query = "SELECT DISTINCT index_name FROM nifty_index_constituents ORDER BY index_name"
    results = await execute_query(query)
    
    return [row["index_name"] for row in results] if results else []
