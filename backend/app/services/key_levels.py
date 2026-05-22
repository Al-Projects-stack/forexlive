"""
Key level alert storage.
Uses in-memory store for local dev (no DB required).
Swap get_db dependency for a real SQLAlchemy session in production.
"""
from datetime import datetime, timezone
from typing import Optional
import logging

from app.models.schemas import AlertRequest, KeyLevelTriggered

logger = logging.getLogger(__name__)

# In-memory store: list of alert dicts
_alerts: list[dict] = []
_next_id: int = 1


def _new_alert(alert: AlertRequest) -> dict:
    global _next_id
    entry = {
        "id": _next_id,
        "pair": alert.pair,
        "level": alert.level,
        "direction": alert.direction,
        "active": True,
        "triggered": False,
        "created_at": datetime.now(timezone.utc),
        "triggered_at": None,
    }
    _next_id += 1
    return entry


async def create_alert(db, alert: AlertRequest) -> dict:
    entry = _new_alert(alert)
    _alerts.append(entry)
    logger.info(f"Alert created: {entry}")
    return entry


async def get_alerts(db, pair: Optional[str] = None) -> list[dict]:
    return [a for a in _alerts if a["active"] and (pair is None or a["pair"] == pair)]


async def delete_alert(db, alert_id: int) -> bool:
    for a in _alerts:
        if a["id"] == alert_id:
            a["active"] = False
            return True
    return False


async def check_key_levels(
    db,
    pair: str,
    current_price: float,
    previous_price: float,
) -> list[KeyLevelTriggered]:
    triggered = []
    for alert in await get_alerts(db, pair=pair):
        level = alert["level"]
        direction = alert["direction"]
        hit = False

        if direction == "ABOVE" and previous_price <= level < current_price:
            hit = True
        elif direction == "BELOW" and previous_price >= level > current_price:
            hit = True
        elif direction == "EITHER" and (
            (previous_price <= level < current_price)
            or (previous_price >= level > current_price)
        ):
            hit = True

        if hit:
            triggered.append(KeyLevelTriggered(level=level, direction=direction))
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now(timezone.utc)
            logger.info(f"Key level triggered: {pair} @ {level} ({direction})")

    return triggered
