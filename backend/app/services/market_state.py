"""
Tiny indirection so request handlers can read the live CandleAggregator without
importing main.py (which would create a circular import: main imports routers).
main.py calls set_aggregator() at startup; everything else reads through here.
"""
from typing import Optional

from app.models.schemas import Candle

_aggregator = None


def set_aggregator(aggregator) -> None:
    global _aggregator
    _aggregator = aggregator


def get_candles(pair: str) -> list[Candle]:
    if _aggregator is None:
        return []
    try:
        return _aggregator.get_candles(pair)
    except Exception:
        return []


def get_current_candle(pair: str) -> Optional[Candle]:
    if _aggregator is None:
        return None
    try:
        return _aggregator.get_current_candle(pair)
    except Exception:
        return None
