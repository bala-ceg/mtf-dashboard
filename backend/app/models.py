from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


# ==================== Market Overview ====================

class MarketOverview(BaseModel):
    trade_date: date
    total_mtf_cr: float = Field(..., description="Total MTF Outstanding in ₹ Crores")
    active_mtf_stocks: int = Field(..., description="Number of active MTF stocks")


class MarketFlow(BaseModel):
    trade_date: date
    fresh_exposure_cr: Optional[float] = Field(None, description="Fresh MTF exposure in ₹ Cr")
    liquidated_exposure_cr: Optional[float] = Field(None, description="Liquidated MTF exposure in ₹ Cr")
    net_flow_cr: Optional[float] = Field(None, description="Net flow (Fresh - Liquidated)")


class MarketRegime(BaseModel):
    trade_date: date
    opening_outstanding_cr: Optional[float]
    closing_outstanding_cr: Optional[float]
    fresh_exposure_cr: Optional[float]
    liquidated_exposure_cr: Optional[float]
    net_flow_cr: Optional[float]
    regime: str = Field(..., description="RISK_ON, NEUTRAL, or RISK_OFF")


# ==================== Top Movers ====================

class TopMover(BaseModel):
    trade_date: date
    symbol: str
    mtf_change_cr: float = Field(..., description="MTF change in ₹ Crores")
    market_cap_category: str


class PercentMover(BaseModel):
    symbol: str
    base_mtf_cr: float
    mtf_change_cr: float
    mtf_change_pct: float
    market_cap_category: Optional[str] = None


# ==================== Concentration ====================

class Concentration(BaseModel):
    trade_date: date
    symbol: str
    stock_mtf_cr: float
    mtf_share_pct: float = Field(..., description="% of total market MTF")


class ConcentrationByCategory(BaseModel):
    trade_date: date
    symbol: str
    market_cap_category: str
    stock_mtf_cr: float
    market_cap_cr: float
    category_share_pct: float = Field(..., description="% of category MTF")


# ==================== Continuous Movers ====================

class ContinuousMover(BaseModel):
    symbol: str
    market_cap_category: str
    direction: str
    streak_start_date: date
    streak_end_date: date
    consecutive_days: int
    avg_daily_change_cr: float
    total_change_cr: float


# ==================== Volume/Value Shockers ====================

class VolumeShocker(BaseModel):
    trade_date: date
    symbol: str
    mtf_quantity: int
    avg_qty_10d: float
    stddev_qty_10d: float
    mtf_amount_cr: float
    avg_amount_10d: float
    stddev_amount_10d: float
    z_score: float
    market_cap_category: Optional[str] = None


class ValueShocker(BaseModel):
    trade_date: date
    symbol: str
    mtf_amount_cr: float
    avg_amount_10d: float
    stddev_amount_10d: float
    z_score: float
    market_cap_category: Optional[str] = None


# ==================== Active Stock Trend ====================

class ActiveStockTrend(BaseModel):
    trade_date: date
    active_mtf_stocks: int
