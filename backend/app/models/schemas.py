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
