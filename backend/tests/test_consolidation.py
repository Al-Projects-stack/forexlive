import pytest
from app.models.schemas import Candle
from app.services.consolidation import is_consolidating, get_consolidation_zone


def make_candles(open_: float, high: float, low: float, close: float, n: int = 20) -> list[Candle]:
    return [Candle(open=open_, high=high, low=low, close=close) for _ in range(n)]


def test_consolidation_detected():
    # 20 candles in a tight 0.10% range — should detect consolidation
    candles = make_candles(154.80, 154.95, 154.75, 154.88)
    assert is_consolidating(candles, threshold=0.0015) is True


def test_consolidation_not_detected():
    # Candles with a wide range — should not detect consolidation
    candles = make_candles(154.00, 156.00, 153.00, 155.00)
    assert is_consolidating(candles, threshold=0.0015) is False


def test_consolidation_requires_20_candles():
    candles = make_candles(154.80, 154.95, 154.75, 154.88, n=19)
    assert is_consolidating(candles) is False


def test_consolidation_uses_last_20():
    # First candle has a huge range, last 20 are tight — should consolidate
    wide = Candle(open=140.00, high=170.00, low=140.00, close=155.00)
    tight = Candle(open=154.80, high=154.95, low=154.75, close=154.88)
    candles = [wide] + [tight] * 20
    assert is_consolidating(candles, threshold=0.0015) is True


def test_get_consolidation_zone_active():
    candles = make_candles(154.80, 154.95, 154.75, 154.88)
    zone = get_consolidation_zone(candles)
    assert zone.active is True
    assert zone.upper == pytest.approx(154.95)
    assert zone.lower == pytest.approx(154.75)
    assert zone.midpoint == pytest.approx((154.95 + 154.75) / 2)


def test_get_consolidation_zone_inactive():
    candles = make_candles(154.00, 156.00, 153.00, 155.00)
    zone = get_consolidation_zone(candles)
    assert zone.active is False
    assert zone.upper is None
    assert zone.lower is None


def test_exact_threshold_boundary():
    # Range exactly at threshold — should NOT consolidate (< not <=)
    candles = make_candles(100.00, 100.15, 100.00, 100.10)
    range_pct = (100.15 - 100.00) / 100.00  # = 0.0015
    # is_consolidating uses strict <, so this should be False
    assert is_consolidating(candles, threshold=0.0015) is False
