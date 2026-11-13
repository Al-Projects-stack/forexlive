from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import (
    FairValueGap, LiquiditySweep, MarketStructureEvent, OrderBlock, SmartMoneyZones,
)
from app.services.structure_alerts import StructureAlertTracker

T0 = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)
OB = OrderBlock(type="BULLISH", top=1.1050, bottom=1.1040, timestamp=T0)
FVG = FairValueGap(type="BEARISH", top=1.1090, bottom=1.1080, timestamp=T0)


def zones(**kw) -> SmartMoneyZones:
    return SmartMoneyZones(**kw)


def primed(pair="EUR/USD", z=None, price=1.1065) -> StructureAlertTracker:
    t = StructureAlertTracker()
    assert t.update(pair, z or zones(), price) == []
    return t


def test_first_update_primes_without_alerting():
    t = StructureAlertTracker()
    z = zones(liquidity_sweep=LiquiditySweep(type="HIGH_SWEEP", level=1.1100, timestamp=T0),
              structure=MarketStructureEvent(type="CHoCH", direction="BULLISH", level=1.1060, timestamp=T0),
              order_blocks=[OB])
    assert t.update("EUR/USD", z, 1.1045) == []
    # Same picture on the next tick is still old news
    assert t.update("EUR/USD", z, 1.1045) == []


def test_new_sweep_fires_once():
    t = primed()
    z = zones(liquidity_sweep=LiquiditySweep(type="HIGH_SWEEP", level=1.10987, timestamp=T0))
    [alert] = t.update("EUR/USD", z, 1.1095)
    assert (alert.kind, alert.direction, alert.level) == ("SWEEP", "BEARISH", 1.10987)
    assert alert.message == "EUR/USD swept liquidity above 1.10987"
    assert t.update("EUR/USD", z, 1.1094) == []
    # A later sweep of the same level is a new event
    z2 = zones(liquidity_sweep=LiquiditySweep(type="HIGH_SWEEP", level=1.10987, timestamp=T0 + timedelta(minutes=5)))
    assert len(t.update("EUR/USD", z2, 1.1095)) == 1


def test_choch_fires_once_despite_restamping_and_bos_is_ignored():
    t = primed()
    bos = zones(structure=MarketStructureEvent(type="BOS", direction="BULLISH", level=1.1070, timestamp=T0))
    assert t.update("EUR/USD", bos, 1.1072) == []
    for minute in range(3):
        z = zones(structure=MarketStructureEvent(type="CHoCH", direction="BEARISH", level=1.1050,
                                                 timestamp=T0 + timedelta(minutes=minute)))
        alerts = t.update("EUR/USD", z, 1.1048)
        assert len(alerts) == (1 if minute == 0 else 0)
    assert alerts == [] and t.update("EUR/USD", z, 1.1048) == []


def test_zone_tap_fires_on_entry_only():
    both = zones(order_blocks=[OB], fair_value_gaps=[FVG])
    t = primed(z=both, price=1.1065)
    [tap] = t.update("EUR/USD", both, 1.1048, T0)
    assert (tap.kind, tap.direction, tap.top, tap.bottom) == ("OB_TAP", "BULLISH", 1.1050, 1.1040)
    assert "tapped bullish order block 1.10400–1.10500" in tap.message
    # Staying inside: no repeat
    assert t.update("EUR/USD", both, 1.1045, T0) == []
    [fvg] = t.update("EUR/USD", both, 1.1085, T0)
    assert fvg.kind == "FVG_TAP" and fvg.direction == "BEARISH"


def test_zone_edge_flicker_is_rate_limited():
    t = primed(z=zones(order_blocks=[OB]), price=1.1065)
    assert len(t.update("EUR/USD", zones(order_blocks=[OB]), 1.1048, T0)) == 1
    for s in range(1, 10):  # in, out, in, out... within the cooldown
        price = 1.1051 if s % 2 else 1.1049
        assert t.update("EUR/USD", zones(order_blocks=[OB]), price, T0 + timedelta(seconds=s)) == []
    t.update("EUR/USD", zones(order_blocks=[OB]), 1.1060, T0 + timedelta(minutes=16))
    assert len(t.update("EUR/USD", zones(order_blocks=[OB]), 1.1045, T0 + timedelta(minutes=16, seconds=1))) == 1


def test_zone_born_around_price_is_not_a_tap():
    t = primed(price=1.1045)
    assert t.update("EUR/USD", zones(order_blocks=[OB]), 1.1045) == []


def test_pairs_are_independent_and_jpy_formatting():
    t = primed("EUR/USD")
    z = zones(liquidity_sweep=LiquiditySweep(type="LOW_SWEEP", level=149.123, timestamp=T0))
    assert t.update("USD/JPY", z, 149.2) == []  # first sight of USD/JPY primes
    z2 = zones(liquidity_sweep=LiquiditySweep(type="LOW_SWEEP", level=149.05, timestamp=T0 + timedelta(minutes=1)))
    [alert] = t.update("USD/JPY", z2, 149.1)
    assert alert.direction == "BULLISH" and alert.message == "USD/JPY swept liquidity below 149.050"


def test_seen_memory_is_capped():
    t = StructureAlertTracker(max_seen=5)
    t.update("EUR/USD", zones(), 1.0)
    for i in range(20):
        t.update("EUR/USD", zones(liquidity_sweep=LiquiditySweep(
            type="HIGH_SWEEP", level=1.1, timestamp=T0 + timedelta(minutes=i))), 1.1)
    assert len(t._seen["EUR/USD"]) == 5


@pytest.mark.asyncio
async def test_on_tick_broadcasts_structure_alert():
    from app import main

    main.structure_alerts.reset()
    calm = zones()
    swept = zones(liquidity_sweep=LiquiditySweep(type="LOW_SWEEP", level=1.1001, timestamp=T0))
    with patch.object(main, "analyze_smart_money", side_effect=[calm, swept]), \
         patch.object(main, "check_key_levels", AsyncMock(return_value=[])), \
         patch.object(main, "get_imminent_high_impact_event", return_value=None), \
         patch.object(main.manager, "broadcast", AsyncMock()) as broadcast:
        await main.on_tick("EUR/USD", 1.1010, T0)
        await main.on_tick("EUR/USD", 1.1012, T0 + timedelta(seconds=2))

    types = [call.args[1]["type"] for call in broadcast.await_args_list]
    assert types == ["CANDLE_UPDATE", "CANDLE_UPDATE", "STRUCTURE_ALERT"]
    message = broadcast.await_args_list[-1].args[1]
    assert message["structure_alert"]["kind"] == "SWEEP"
    assert message["structure_alert"]["direction"] == "BULLISH"
    assert message["smart_money"]["liquidity_sweep"]["level"] == 1.1001
    main.structure_alerts.reset()
