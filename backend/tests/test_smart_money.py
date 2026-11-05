import pytest
from app.models.schemas import Candle
from app.services.smart_money import (
    detect_fair_value_gaps,
    detect_liquidity_sweep,
    detect_market_structure,
    detect_order_blocks,
    find_swing_points,
)


def c(open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(open=open_, high=high, low=low, close=close)


# ---------- Market structure (swing points, BOS, CHoCH) ----------

def _bullish_swing_candles(final: Candle) -> list[Candle]:
    """
    A clean higher-high / higher-low zigzag:
      idx2  swing LOW  @ 1.0000
      idx5  swing HIGH @ 1.0160
      idx8  swing LOW  @ 1.0040  (higher low)
      idx11 swing HIGH @ 1.0200  (higher high)
    `final` is appended as the deciding candle.
    """
    return [
        c(1.0100, 1.0105, 1.0095, 1.0100),
        c(1.0080, 1.0085, 1.0075, 1.0080),
        c(1.0050, 1.0055, 1.0000, 1.0050),  # idx2: swing low 1.0000
        c(1.0080, 1.0085, 1.0075, 1.0080),
        c(1.0095, 1.0100, 1.0090, 1.0095),
        c(1.0150, 1.0160, 1.0140, 1.0150),  # idx5: swing high 1.0160
        c(1.0120, 1.0125, 1.0115, 1.0120),
        c(1.0090, 1.0095, 1.0085, 1.0090),
        c(1.0070, 1.0075, 1.0040, 1.0070),  # idx8: swing low 1.0040 (higher low)
        c(1.0090, 1.0095, 1.0085, 1.0090),
        c(1.0140, 1.0145, 1.0135, 1.0140),
        c(1.0190, 1.0200, 1.0180, 1.0190),  # idx11: swing high 1.0200 (higher high)
        c(1.0170, 1.0175, 1.0165, 1.0170),
        c(1.0150, 1.0155, 1.0145, 1.0150),
        final,
    ]


def test_find_swing_points_detects_highs_and_lows():
    candles = _bullish_swing_candles(c(1.0150, 1.0155, 1.0145, 1.0150))
    swings = find_swing_points(candles)
    highs = [p.price for p in swings if p.kind == "HIGH"]
    lows = [p.price for p in swings if p.kind == "LOW"]
    assert highs == [1.0160, 1.0200]
    assert lows == [1.0000, 1.0040]


def test_market_structure_bos_bullish():
    # Final candle closes above the last swing high (1.0200) -> continuation
    candles = _bullish_swing_candles(c(1.0205, 1.0215, 1.0200, 1.0210))
    event = detect_market_structure(candles)
    assert event is not None
    assert event.type == "BOS"
    assert event.direction == "BULLISH"
    assert event.level == pytest.approx(1.0200)


def test_market_structure_choch_bearish():
    # Prevailing structure is bullish, but final candle closes below the
    # last swing low (1.0040) -> reversal signal
    candles = _bullish_swing_candles(c(1.0030, 1.0035, 1.0015, 1.0020))
    event = detect_market_structure(candles)
    assert event is not None
    assert event.type == "CHoCH"
    assert event.direction == "BEARISH"
    assert event.level == pytest.approx(1.0040)


def test_market_structure_none_when_no_break():
    candles = _bullish_swing_candles(c(1.0150, 1.0155, 1.0145, 1.0150))
    assert detect_market_structure(candles) is None


def test_market_structure_requires_two_swings_each_side():
    candles = [c(1.0, 1.001, 0.999, 1.0) for _ in range(5)]
    assert detect_market_structure(candles) is None


# ---------- Fair Value Gaps ----------

def test_bullish_fvg_detected():
    candles = [
        c(1.0000, 1.0010, 0.9990, 1.0005),
        c(1.0005, 1.0020, 1.0000, 1.0015),
        c(1.0025, 1.0035, 1.0020, 1.0030),  # low (1.0020) > candle1 high (1.0010)
    ]
    gaps = detect_fair_value_gaps(candles)
    assert len(gaps) == 1
    assert gaps[0].type == "BULLISH"
    assert gaps[0].top == pytest.approx(1.0020)
    assert gaps[0].bottom == pytest.approx(1.0010)


def test_bearish_fvg_detected():
    candles = [
        c(1.0030, 1.0035, 1.0020, 1.0025),
        c(1.0015, 1.0020, 1.0005, 1.0010),
        c(1.0005, 1.0010, 0.9995, 1.0000),  # high (1.0010) < candle1 low (1.0020)
    ]
    gaps = detect_fair_value_gaps(candles)
    assert len(gaps) == 1
    assert gaps[0].type == "BEARISH"
    assert gaps[0].top == pytest.approx(1.0020)
    assert gaps[0].bottom == pytest.approx(1.0010)


def test_fvg_mitigated_is_excluded():
    candles = [
        c(1.0000, 1.0010, 0.9990, 1.0005),
        c(1.0005, 1.0020, 1.0000, 1.0015),
        c(1.0025, 1.0035, 1.0020, 1.0030),
        c(1.0025, 1.0030, 1.0015, 1.0020),  # low dips back into the gap -> mitigated
    ]
    assert detect_fair_value_gaps(candles) == []


def test_fvg_requires_no_overlap():
    candles = [
        c(1.0000, 1.0010, 0.9990, 1.0005),
        c(1.0005, 1.0020, 1.0000, 1.0015),
        c(1.0005, 1.0015, 1.0000, 1.0010),  # overlaps candle1 -> no gap
    ]
    assert detect_fair_value_gaps(candles) == []


# ---------- Order Blocks ----------

def _quiet_candle(open_: float) -> Candle:
    return c(open_, open_ + 0.0003, open_ - 0.0001, open_ + 0.0003)  # small bullish body


def test_bullish_order_block_detected():
    candles = [_quiet_candle(1.0000 + i * 0.0001) for i in range(10)]
    candles.append(c(1.0105, 1.0106, 1.0094, 1.0095))  # prev: bearish candle (the OB)
    candles.append(c(1.0100, 1.0115, 1.0099, 1.0110))  # impulse: big bullish candle

    blocks = detect_order_blocks(candles)
    assert len(blocks) == 1
    assert blocks[0].type == "BULLISH"
    assert blocks[0].top == pytest.approx(1.0106)
    assert blocks[0].bottom == pytest.approx(1.0094)


def test_bearish_order_block_detected():
    candles = [_quiet_candle(1.0000 + i * 0.0001) for i in range(10)]
    candles.append(c(1.0094, 1.0106, 1.0093, 1.0105))  # prev: bullish candle (the OB)
    candles.append(c(1.0100, 1.0101, 1.0085, 1.0090))  # impulse: big bearish candle

    blocks = detect_order_blocks(candles)
    assert len(blocks) == 1
    assert blocks[0].type == "BEARISH"
    assert blocks[0].top == pytest.approx(1.0106)
    assert blocks[0].bottom == pytest.approx(1.0093)


def test_order_block_mitigated_is_excluded():
    candles = [_quiet_candle(1.0000 + i * 0.0001) for i in range(10)]
    candles.append(c(1.0105, 1.0106, 1.0094, 1.0095))
    candles.append(c(1.0100, 1.0115, 1.0099, 1.0110))
    candles.append(c(1.0090, 1.0092, 1.0080, 1.0085))  # closes below OB bottom -> invalidated

    assert detect_order_blocks(candles) == []


def test_order_block_requires_impulsive_body():
    candles = [_quiet_candle(1.0000 + i * 0.0001) for i in range(10)]
    candles.append(c(1.0105, 1.0106, 1.0094, 1.0095))
    candles.append(c(1.0100, 1.0103, 1.0099, 1.0102))  # body too small to qualify as impulse

    assert detect_order_blocks(candles) == []


# ---------- Liquidity sweeps ----------

def _ranging_candles() -> list[Candle]:
    return [
        c(1.0040, 1.0050, 1.0020, 1.0045),
        c(1.0050, 1.0060, 1.0030, 1.0055),
        c(1.0060, 1.0070, 1.0040, 1.0065),
        c(1.0070, 1.0080, 1.0050, 1.0075),
        c(1.0080, 1.0090, 1.0060, 1.0085),
        c(1.0090, 1.0100, 1.0070, 1.0095),  # highest high: 1.0100
        c(1.0080, 1.0090, 1.0060, 1.0085),
        c(1.0070, 1.0080, 1.0050, 1.0075),
        c(1.0060, 1.0070, 1.0000, 1.0065),  # lowest low: 1.0000
        c(1.0050, 1.0060, 1.0010, 1.0055),
    ]


def test_high_sweep_detected():
    candles = _ranging_candles() + [c(1.0095, 1.0110, 1.0085, 1.0095)]  # wicks above 1.0100, closes back below
    sweep = detect_liquidity_sweep(candles)
    assert sweep is not None
    assert sweep.type == "HIGH_SWEEP"
    assert sweep.level == pytest.approx(1.0100)


def test_low_sweep_detected():
    candles = _ranging_candles() + [c(1.0010, 1.0020, 0.9990, 1.0005)]  # wicks below 1.0000, closes back above
    sweep = detect_liquidity_sweep(candles)
    assert sweep is not None
    assert sweep.type == "LOW_SWEEP"
    assert sweep.level == pytest.approx(1.0000)


def test_no_sweep_when_price_stays_inside_range():
    candles = _ranging_candles() + [c(1.0050, 1.0060, 1.0040, 1.0055)]
    assert detect_liquidity_sweep(candles) is None


def test_no_sweep_with_insufficient_history():
    candles = _ranging_candles()[:5]
    assert detect_liquidity_sweep(candles) is None
