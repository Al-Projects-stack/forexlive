from datetime import datetime, timezone, timedelta
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


# Static high-impact recurring events — updated weekly in production via Twelve Data calendar
RECURRING_EVENTS = [
    {"name": "US Non-Farm Payrolls", "currency": "USD", "impact": "HIGH", "day_of_week": 4, "hour": 8, "minute": 30},  # First Friday
    {"name": "US CPI", "currency": "USD", "impact": "HIGH", "day_of_week": 2, "hour": 8, "minute": 30},
    {"name": "FOMC Rate Decision", "currency": "USD", "impact": "HIGH", "day_of_week": 2, "hour": 14, "minute": 0},
    {"name": "ECB Rate Decision", "currency": "EUR", "impact": "HIGH", "day_of_week": 3, "hour": 7, "minute": 45},
    {"name": "BOJ Rate Decision", "currency": "JPY", "impact": "HIGH", "day_of_week": 1, "hour": 3, "minute": 0},
    {"name": "UK GDP", "currency": "GBP", "impact": "HIGH", "day_of_week": 4, "hour": 7, "minute": 0},
    {"name": "US Initial Jobless Claims", "currency": "USD", "impact": "MEDIUM", "day_of_week": 3, "hour": 8, "minute": 30},
    {"name": "US Retail Sales", "currency": "USD", "impact": "HIGH", "day_of_week": 0, "hour": 8, "minute": 30},
    {"name": "UK CPI", "currency": "GBP", "impact": "HIGH", "day_of_week": 2, "hour": 7, "minute": 0},
    {"name": "ZAR SARB Rate Decision", "currency": "ZAR", "impact": "HIGH", "day_of_week": 3, "hour": 13, "minute": 0},
]


def get_upcoming_events(limit: int = 5) -> list[dict]:
    """Return next N high-impact events with countdown in minutes."""
    now = datetime.now(timezone.utc)
    events_with_times = []

    for event in RECURRING_EVENTS:
        # Find the next occurrence this week or next week
        days_ahead = event["day_of_week"] - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and now.hour >= event["hour"]):
            days_ahead += 7

        event_dt = now.replace(
            hour=event["hour"],
            minute=event["minute"],
            second=0,
            microsecond=0,
        ) + timedelta(days=days_ahead)

        minutes_away = int((event_dt - now).total_seconds() / 60)
        events_with_times.append({
            "name": event["name"],
            "currency": event["currency"],
            "impact": event["impact"],
            "scheduled_at": event_dt.isoformat(),
            "minutes_away": minutes_away,
        })

    events_with_times.sort(key=lambda e: e["minutes_away"])
    return events_with_times[:limit]


def get_imminent_high_impact_event() -> Optional[dict]:
    """Return a HIGH impact event within 5 minutes, if any."""
    events = get_upcoming_events(limit=10)
    for event in events:
        if event["impact"] == "HIGH" and 0 <= event["minutes_away"] <= 5:
            return event
    return None
