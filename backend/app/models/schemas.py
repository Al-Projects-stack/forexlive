from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


ALLOWED_PAIRS = ["USD/JPY", "EUR/USD", "GBP/USD", "USD/ZAR"]


class Candle(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    timestamp: Optional[datetime] = None


class ConsolidationZone(BaseModel):
    active: bool
    upper: Optional[float] = None
    lower: Optional[float] = None
    midpoint: Optional[float] = None


class OrderBlock(BaseModel):
    type: str  # BULLISH | BEARISH
    top: float
    bottom: float
    timestamp: Optional[datetime] = None


class FairValueGap(BaseModel):
    type: str  # BULLISH | BEARISH
    top: float
    bottom: float
    timestamp: Optional[datetime] = None


class LiquiditySweep(BaseModel):
    type: str  # HIGH_SWEEP | LOW_SWEEP
    level: float
    timestamp: Optional[datetime] = None


class MarketStructureEvent(BaseModel):
    type: str  # BOS | CHoCH
    direction: str  # BULLISH | BEARISH
    level: float
    timestamp: Optional[datetime] = None


class SmartMoneyZones(BaseModel):
    order_blocks: list[OrderBlock] = Field(default_factory=list)
    fair_value_gaps: list[FairValueGap] = Field(default_factory=list)
    liquidity_sweep: Optional[LiquiditySweep] = None
    structure: Optional[MarketStructureEvent] = None


class KeyLevelTriggered(BaseModel):
    level: float
    direction: str


class NewsWarning(BaseModel):
    event: str
    minutes_away: int
    impact: str


class WSMessage(BaseModel):
    type: str
    pair: str
    timestamp: str
    candle: Optional[Candle] = None
    consolidation_zone: Optional[ConsolidationZone] = None
    key_level_triggered: Optional[KeyLevelTriggered] = None
    news_warning: Optional[NewsWarning] = None
    smart_money: Optional[SmartMoneyZones] = None


class AlertRequest(BaseModel):
    pair: str = Field(description="Currency pair")
    level: float = Field(gt=0, lt=100000, description="Price level")
    direction: str = Field(description="ABOVE, BELOW, or EITHER")

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, v: str) -> str:
        if v not in ALLOWED_PAIRS:
            raise ValueError(f"Pair must be one of {ALLOWED_PAIRS}")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ["ABOVE", "BELOW", "EITHER"]:
            raise ValueError("Direction must be ABOVE, BELOW, or EITHER")
        return v


class AlertResponse(BaseModel):
    id: int
    pair: str
    level: float
    direction: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TickData(BaseModel):
    pair: str
    price: float
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None


class TradeReviewRequest(BaseModel):
    pair: str = Field(description="Currency pair")
    direction: str = Field(description="LONG or SHORT")
    entry_price: float = Field(gt=0, description="Entry price")
    exit_price: float = Field(gt=0, description="Exit / current price used as exit")
    quantity: float = Field(gt=0, description="Position size")
    pnl: float = Field(description="Realised/floating P&L at exit")
    held_minutes: Optional[int] = Field(default=None, ge=0, description="How long the position was held, if known")

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, v: str) -> str:
        if v not in ALLOWED_PAIRS:
            raise ValueError(f"Pair must be one of {ALLOWED_PAIRS}")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ["LONG", "SHORT"]:
            raise ValueError("Direction must be LONG or SHORT")
        return v


class TradeReviewResponse(BaseModel):
    review: str
    model: str
