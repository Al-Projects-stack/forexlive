"""
Economic calendar. Real events come from ForexFactory's public weekly feed
(no API key), refreshed every 30 minutes and filtered to the currencies we
trade. If the feed has never loaded, a static estimate of the usual weekly
releases is served instead and every event is marked source="fallback" so the
UI can say so.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.models.schemas import ALLOWED_PAIRS

logger = logging.getLogger(__name__)

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
USER_AGENT = "ForexLive/1.0 (+https://github.com/Al-Projects-stack/forexlive)"
REFRESH_SECONDS = 30 * 60
# Keep a released event on the list briefly so "LIVE" is visible around the print
SHOW_PAST_MINUTES = 15

CURRENCIES = {c for pair in ALLOWED_PAIRS for c in pair.split("/")}
IMPACTS = {"High": "HIGH", "Medium": "MEDIUM"}

_cache: list[dict] = []
_fetched_at: Optional[datetime] = None


# Used only until the live feed has loaded once
RECURRING_EVENTS = [
    {"name": "US Non-Farm Payrolls", "currency": "USD", "impact": "HIGH", "day_of_week": 4, "hour": 13, "minute": 30},
    {"name": "US CPI", "currency": "USD", "impact": "HIGH", "day_of_week": 2, "hour": 13, "minute": 30},
    {"name": "FOMC Rate Decision", "currency": "USD", "impact": "HIGH", "day_of_week": 2, "hour": 19, "minute": 0},
    {"name": "ECB Rate Decision", "currency": "EUR", "impact": "HIGH", "day_of_week": 3, "hour": 13, "minute": 15},
    {"name": "BOJ Rate Decision", "currency": "JPY", "impact": "HIGH", "day_of_week": 1, "hour": 3, "minute": 0},
    {"name": "UK GDP", "currency": "GBP", "impact": "HIGH", "day_of_week": 4, "hour": 7, "minute": 0},
    {"name": "US Initial Jobless Claims", "currency": "USD", "impact": "MEDIUM", "day_of_week": 3, "hour": 13, "minute": 30},
    {"name": "US Retail Sales", "currency": "USD", "impact": "HIGH", "day_of_week": 0, "hour": 13, "minute": 30},
    {"name": "UK CPI", "currency": "GBP", "impact": "HIGH", "day_of_week": 2, "hour": 7, "minute": 0},
    {"name": "SARB Rate Decision", "currency": "ZAR", "impact": "HIGH", "day_of_week": 3, "hour": 13, "minute": 0},
]


def _blank_to_none(value) -> Optional[str]:
    value = (value or "").strip() if isinstance(value, str) else value
    return value or None


def parse_ff_events(raw) -> list[dict]:
    """ForexFactory JSON -> our events (UTC, high/medium impact, our currencies only)."""
    events = []
    for item in raw if isinstance(raw, list) else []:
        try:
            impact = IMPACTS.get(item.get("impact"))
            currency = item.get("country")
            if impact is None or currency not in CURRENCIES:
                continue
            when = datetime.fromisoformat(item["date"]).astimezone(timezone.utc)
            events.append({
                "name": item["title"].strip(),
                "currency": currency,
                "impact": impact,
                "scheduled_at": when,
                "forecast": _blank_to_none(item.get("forecast")),
                "previous": _blank_to_none(item.get("previous")),
            })
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    events.sort(key=lambda e: e["scheduled_at"])
    return events


async def refresh(client: Optional[httpx.AsyncClient] = None) -> bool:
    """Fetch the weekly feed. On any failure the previous cache is kept."""
    global _cache, _fetched_at
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=10, headers={"User-Agent": USER_AGENT})
    try:
        resp = await client.get(FF_URL)
        resp.raise_for_status()
        events = parse_ff_events(resp.json())
        if not events:
            logger.warning("Calendar feed returned no usable events; keeping previous data")
            return False
        _cache, _fetched_at = events, datetime.now(timezone.utc)
        logger.info("Calendar refreshed: %d events from ForexFactory", len(events))
        return True
    except Exception as e:
        logger.warning("Calendar refresh failed, keeping previous data: %s", e)
        return False
    finally:
        if owns_client:
            await client.aclose()


async def run_refresher(interval: int = REFRESH_SECONDS) -> None:
    while True:
        await refresh()
        await asyncio.sleep(interval)


def _fallback_events(now: datetime) -> list[dict]:
    events = []
    for event in RECURRING_EVENTS:
        days_ahead = (event["day_of_week"] - now.weekday()) % 7
        when = now.replace(hour=event["hour"], minute=event["minute"], second=0, microsecond=0) + timedelta(days=days_ahead)
        if when < now - timedelta(minutes=SHOW_PAST_MINUTES):
            when += timedelta(days=7)
        events.append({**{k: event[k] for k in ("name", "currency", "impact")},
                       "scheduled_at": when, "forecast": None, "previous": None})
    return sorted(events, key=lambda e: e["scheduled_at"])


def get_upcoming_events(limit: int = 5, now: Optional[datetime] = None, impact: Optional[str] = None) -> list[dict]:
    """Next events with a minutes countdown. Includes ones released in the last 15 minutes."""
    now = now or datetime.now(timezone.utc)
    live = bool(_cache)
    source_events = _cache if live else _fallback_events(now)
    updated_at = _fetched_at.isoformat() if live and _fetched_at else None

    out = []
    for event in source_events:
        if impact and event["impact"] != impact:
            continue
        minutes_away = int((event["scheduled_at"] - now).total_seconds() // 60)
        if minutes_away < -SHOW_PAST_MINUTES:
            continue
        out.append({
            "name": event["name"],
            "currency": event["currency"],
            "impact": event["impact"],
            "scheduled_at": event["scheduled_at"].isoformat(),
            "minutes_away": minutes_away,
            "forecast": event["forecast"],
            "previous": event["previous"],
            "source": "forexfactory" if live else "fallback",
            "updated_at": updated_at,
        })
        if len(out) >= limit:
            break
    return out


def get_imminent_high_impact_event(now: Optional[datetime] = None) -> Optional[dict]:
    """Return a HIGH impact event within 5 minutes, if any."""
    for event in get_upcoming_events(limit=10, now=now, impact="HIGH"):
        if 0 <= event["minutes_away"] <= 5:
            return event
    return None
