"""
Turns smart-money analysis into one-off alerts:

  SWEEP    a candle took liquidity above a swing high / below a swing low
  CHOCH    market structure changed character
  OB_TAP   price moved back into an unmitigated order block
  FVG_TAP  price moved back into an unfilled fair value gap

The analysis is recomputed on every tick, so the same sweep or CHoCH shows up
many times in a row. The tracker remembers what it has already reported and
only emits each event once. Zone taps fire on entry only: the zone must have
existed on the previous tick with price outside it. A zone that is born with
price already inside it hasn't been revisited, so it doesn't count. Price often
flickers across the edge of a thin zone, so each zone can only fire once per
TAP_COOLDOWN.

The first update for a pair primes this memory without emitting anything, so
history restored at startup doesn't replay old signals.
"""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.schemas import SmartMoneyZones, StructureAlert

MAX_SEEN = 200
TAP_COOLDOWN = timedelta(minutes=15)


def _fmt(pair: str, price: float) -> str:
    return f"{price:.3f}" if "JPY" in pair else f"{price:.5f}"


class StructureAlertTracker:
    def __init__(self, max_seen: int = MAX_SEEN):
        self._max_seen = max_seen
        self._seen: dict[str, OrderedDict] = {}
        # zone key -> was price inside it on the previous update
        self._zones: dict[str, dict[tuple, bool]] = {}
        # zone key -> when it last fired
        self._last_tap: dict[str, dict[tuple, datetime]] = {}

    def reset(self) -> None:
        self._seen.clear()
        self._zones.clear()
        self._last_tap.clear()

    def _first_time(self, pair: str, key: tuple) -> bool:
        seen = self._seen[pair]
        if key in seen:
            return False
        seen[key] = True
        while len(seen) > self._max_seen:
            seen.popitem(last=False)
        return True

    def update(
        self, pair: str, zones: SmartMoneyZones, price: float, now: Optional[datetime] = None,
    ) -> list[StructureAlert]:
        now = now or datetime.now(timezone.utc)
        priming = pair not in self._seen
        if priming:
            self._seen[pair] = OrderedDict()
        alerts: list[StructureAlert] = []

        sweep = zones.liquidity_sweep
        if sweep is not None:
            key = ("SWEEP", sweep.type, sweep.level, sweep.timestamp.isoformat() if sweep.timestamp else None)
            if self._first_time(pair, key) and not priming:
                above = sweep.type == "HIGH_SWEEP"
                alerts.append(StructureAlert(
                    kind="SWEEP",
                    direction="BEARISH" if above else "BULLISH",
                    level=sweep.level,
                    message=f"{pair} swept liquidity {'above' if above else 'below'} {_fmt(pair, sweep.level)}",
                ))

        structure = zones.structure
        if structure is not None and structure.type == "CHoCH":
            # No timestamp in the key: the analysis restamps the same CHoCH every candle
            key = ("CHOCH", structure.direction, structure.level)
            if self._first_time(pair, key) and not priming:
                alerts.append(StructureAlert(
                    kind="CHOCH",
                    direction=structure.direction,
                    level=structure.level,
                    message=f"{pair} CHoCH {structure.direction.lower()} at {_fmt(pair, structure.level)}",
                ))

        previous = self._zones.get(pair, {})
        last_tap = self._last_tap.setdefault(pair, {})
        current: dict[tuple, bool] = {}
        for kind, label, items in (
            ("OB_TAP", "order block", zones.order_blocks),
            ("FVG_TAP", "FVG", zones.fair_value_gaps),
        ):
            for zone in items:
                key = (kind, zone.type, zone.top, zone.bottom)
                inside = zone.bottom <= price <= zone.top
                current[key] = inside
                cooling = key in last_tap and now - last_tap[key] < TAP_COOLDOWN
                if inside and previous.get(key) is False and not priming and not cooling:
                    last_tap[key] = now
                    alerts.append(StructureAlert(
                        kind=kind,
                        direction=zone.type,
                        top=zone.top,
                        bottom=zone.bottom,
                        message=f"{pair} tapped {zone.type.lower()} {label} "
                                f"{_fmt(pair, zone.bottom)}–{_fmt(pair, zone.top)}",
                    ))
        self._zones[pair] = current
        # Forget cooldowns for zones that no longer exist
        for key in [k for k in last_tap if k not in current]:
            del last_tap[key]
        return alerts
