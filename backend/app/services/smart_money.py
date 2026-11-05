"""
Smart Money Concepts (SMC) detection.

Computes four price-action structures directly from OHLC candles — no volume
or order-book data required, which is why this works on top of the same
CandleAggregator output used for consolidation detection:

- Order Blocks: the last opposing candle before a strong impulse move.
- Fair Value Gaps: 3-candle imbalances where wick 1 and wick 3 don't overlap.
- Liquidity Sweeps: a wick through a recent high/low that closes back inside.
- Market Structure (BOS/CHoCH): trend continuation vs. reversal, derived from
  the sequence of swing highs/lows.

These are simplified, rule-based heuristics (fractal swing points, a body-size
multiplier for "impulsive" candles) rather than a full institutional-grade
model — tuned to read clearly on 1-minute G30 candles.
"""
from dataclasses import dataclass
from typing import Optional

from app.models.schemas import (
    Candle,
    FairValueGap,
    LiquiditySweep,
    MarketStructureEvent,
    OrderBlock,
    SmartMoneyZones,
)

SWING_LOOKBACK = 2
ORDER_BLOCK_BODY_MULTIPLIER = 1.5
ORDER_BLOCK_AVG_WINDOW = 10
LIQUIDITY_SWEEP_LOOKBACK = 10
MAX_ZONES_RETURNED = 3


@dataclass
class SwingPoint:
    index: int
    kind: str  # HIGH | LOW
    price: float


def _is_swing_high(candles: list[Candle], i: int, lookback: int) -> bool:
    left = candles[i - lookback:i]
    right = candles[i + 1:i + 1 + lookback]
    return all(candles[i].high > c.high for c in left) and all(candles[i].high > c.high for c in right)


def _is_swing_low(candles: list[Candle], i: int, lookback: int) -> bool:
    left = candles[i - lookback:i]
    right = candles[i + 1:i + 1 + lookback]
    return all(candles[i].low < c.low for c in left) and all(candles[i].low < c.low for c in right)


def find_swing_points(candles: list[Candle], lookback: int = SWING_LOOKBACK) -> list[SwingPoint]:
    n = len(candles)
    points: list[SwingPoint] = []
    for i in range(lookback, n - lookback):
        if _is_swing_high(candles, i, lookback):
            points.append(SwingPoint(index=i, kind="HIGH", price=candles[i].high))
        elif _is_swing_low(candles, i, lookback):
            points.append(SwingPoint(index=i, kind="LOW", price=candles[i].low))
    return points


def detect_market_structure(candles: list[Candle], lookback: int = SWING_LOOKBACK) -> Optional[MarketStructureEvent]:
    """
    BOS (Break of Structure) = price closes beyond the last swing point in the
    direction of the prevailing trend (continuation).
    CHoCH (Change of Character) = price closes beyond the last swing point
    against the prevailing trend (potential reversal).
    """
    swings = find_swing_points(candles, lookback)
    highs = [p for p in swings if p.kind == "HIGH"]
    lows = [p for p in swings if p.kind == "LOW"]
    if len(highs) < 2 or len(lows) < 2:
        return None

    bullish_bias = highs[-1].price > highs[-2].price and lows[-1].price > lows[-2].price
    bearish_bias = highs[-1].price < highs[-2].price and lows[-1].price < lows[-2].price
    if not bullish_bias and not bearish_bias:
        return None

    last_close = candles[-1].close
    last_timestamp = candles[-1].timestamp
    reference_high = highs[-1]
    reference_low = lows[-1]

    if bullish_bias and last_close > reference_high.price:
        return MarketStructureEvent(type="BOS", direction="BULLISH", level=reference_high.price, timestamp=last_timestamp)
    if bearish_bias and last_close < reference_low.price:
        return MarketStructureEvent(type="BOS", direction="BEARISH", level=reference_low.price, timestamp=last_timestamp)
    if bullish_bias and last_close < reference_low.price:
        return MarketStructureEvent(type="CHoCH", direction="BEARISH", level=reference_low.price, timestamp=last_timestamp)
    if bearish_bias and last_close > reference_high.price:
        return MarketStructureEvent(type="CHoCH", direction="BULLISH", level=reference_high.price, timestamp=last_timestamp)
    return None


def detect_fair_value_gaps(candles: list[Candle], max_results: int = MAX_ZONES_RETURNED) -> list[FairValueGap]:
    n = len(candles)
    gaps: list[FairValueGap] = []
    for i in range(2, n):
        c1, c2, c3 = candles[i - 2], candles[i - 1], candles[i]
        gap: Optional[FairValueGap] = None
        if c1.high < c3.low:
            gap = FairValueGap(type="BULLISH", top=c3.low, bottom=c1.high, timestamp=c2.timestamp)
        elif c1.low > c3.high:
            gap = FairValueGap(type="BEARISH", top=c1.low, bottom=c3.high, timestamp=c2.timestamp)
        if gap is None:
            continue

        mitigated = False
        for later in candles[i + 1:]:
            if gap.type == "BULLISH" and later.low <= gap.top:
                mitigated = True
                break
            if gap.type == "BEARISH" and later.high >= gap.bottom:
                mitigated = True
                break
        if not mitigated:
            gaps.append(gap)
    return gaps[-max_results:]


def detect_order_blocks(
    candles: list[Candle],
    body_multiplier: float = ORDER_BLOCK_BODY_MULTIPLIER,
    avg_window: int = ORDER_BLOCK_AVG_WINDOW,
    max_results: int = MAX_ZONES_RETURNED,
) -> list[OrderBlock]:
    n = len(candles)
    if n < avg_window + 2:
        return []

    blocks: list[OrderBlock] = []
    for i in range(avg_window + 1, n):
        window = candles[i - avg_window:i]
        avg_body = sum(abs(c.close - c.open) for c in window) / len(window)
        if avg_body == 0:
            continue

        impulse = candles[i]
        body = abs(impulse.close - impulse.open)
        if body < avg_body * body_multiplier:
            continue

        prev = candles[i - 1]
        block: Optional[OrderBlock] = None
        if impulse.close > impulse.open and prev.close < prev.open:
            block = OrderBlock(type="BULLISH", top=prev.high, bottom=prev.low, timestamp=prev.timestamp)
        elif impulse.close < impulse.open and prev.close > prev.open:
            block = OrderBlock(type="BEARISH", top=prev.high, bottom=prev.low, timestamp=prev.timestamp)
        if block is None:
            continue

        mitigated = False
        for later in candles[i + 1:]:
            if block.type == "BULLISH" and later.close < block.bottom:
                mitigated = True
                break
            if block.type == "BEARISH" and later.close > block.top:
                mitigated = True
                break
        if not mitigated:
            blocks.append(block)
    return blocks[-max_results:]


def detect_liquidity_sweep(candles: list[Candle], lookback: int = LIQUIDITY_SWEEP_LOOKBACK) -> Optional[LiquiditySweep]:
    if len(candles) < lookback + 1:
        return None

    last = candles[-1]
    prior = candles[-(lookback + 1):-1]
    prior_high = max(c.high for c in prior)
    prior_low = min(c.low for c in prior)

    if last.high > prior_high and last.close < prior_high:
        return LiquiditySweep(type="HIGH_SWEEP", level=prior_high, timestamp=last.timestamp)
    if last.low < prior_low and last.close > prior_low:
        return LiquiditySweep(type="LOW_SWEEP", level=prior_low, timestamp=last.timestamp)
    return None


def analyze_smart_money(candles: list[Candle]) -> SmartMoneyZones:
    return SmartMoneyZones(
        order_blocks=detect_order_blocks(candles),
        fair_value_gaps=detect_fair_value_gaps(candles),
        liquidity_sweep=detect_liquidity_sweep(candles),
        structure=detect_market_structure(candles),
    )
