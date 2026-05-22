from app.models.schemas import Candle, ConsolidationZone

CONSOLIDATION_THRESHOLD = 0.0015  # 0.15% — tuned for G30 behaviour


def is_consolidating(candles: list[Candle], threshold: float = CONSOLIDATION_THRESHOLD) -> bool:
    """
    Returns True if price is consolidating.
    Consolidation = high-low range of last 20 candles is within threshold % of price.
    """
    if len(candles) < 20:
        return False
    recent = candles[-20:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    range_pct = (max(highs) - min(lows)) / min(lows)
    return range_pct < threshold


def get_consolidation_zone(candles: list[Candle]) -> ConsolidationZone:
    if not is_consolidating(candles):
        return ConsolidationZone(active=False)
    recent = candles[-20:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    upper = max(highs)
    lower = min(lows)
    return ConsolidationZone(
        active=True,
        upper=upper,
        lower=lower,
        midpoint=(upper + lower) / 2,
    )
