from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.services import news_calendar as nc

RAW = [
    {"title": "CPI m/m", "country": "USD", "date": "2026-11-10T08:30:00-05:00",
     "impact": "High", "forecast": "0.3%", "previous": "0.2%"},
    {"title": "German ZEW Economic Sentiment", "country": "EUR", "date": "2026-11-10T05:00:00-05:00",
     "impact": "Medium", "forecast": "", "previous": "39.3"},
    {"title": "Bank Holiday", "country": "USD", "date": "2026-11-11T00:00:00-05:00",
     "impact": "Holiday", "forecast": "", "previous": ""},
    {"title": "Building Permits", "country": "AUD", "date": "2026-11-10T19:30:00-05:00",
     "impact": "High", "forecast": "", "previous": ""},
    {"title": "Retail Sales y/y", "country": "ZAR", "date": "2026-11-12T06:00:00-05:00",
     "impact": "Low", "forecast": "", "previous": "2.1%"},
    {"title": "broken", "country": "USD", "date": "not a date", "impact": "High"},
]


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(nc, "_cache", [])
    monkeypatch.setattr(nc, "_fetched_at", None)
    monkeypatch.setattr(nc, "CACHE_PATH", tmp_path / "calendar.json")


def test_parse_filters_and_converts_to_utc():
    events = nc.parse_ff_events(RAW)
    assert [e["name"] for e in events] == ["German ZEW Economic Sentiment", "CPI m/m"]
    cpi = events[1]
    assert cpi["scheduled_at"] == datetime(2026, 11, 10, 13, 30, tzinfo=timezone.utc)
    assert (cpi["impact"], cpi["forecast"], cpi["previous"]) == ("HIGH", "0.3%", "0.2%")
    assert events[0]["forecast"] is None


def test_parse_tolerates_garbage():
    assert nc.parse_ff_events({"error": "nope"}) == []
    assert nc.parse_ff_events(None) == []


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_refresh_fills_cache_and_serves_live_events():
    async with _client(lambda req: httpx.Response(200, json=RAW)) as client:
        assert await nc.refresh(client)
    now = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
    events = nc.get_upcoming_events(now=now)
    assert [e["name"] for e in events] == ["German ZEW Economic Sentiment", "CPI m/m"]
    assert events[1]["minutes_away"] == 270
    assert all(e["source"] == "forexfactory" and e["updated_at"] for e in events)


@pytest.mark.asyncio
async def test_failed_refresh_keeps_previous_data():
    async with _client(lambda req: httpx.Response(200, json=RAW)) as client:
        await nc.refresh(client)
    async with _client(lambda req: httpx.Response(503)) as client:
        assert not await nc.refresh(client)
    assert len(nc._cache) == 2


def test_released_events_linger_for_15_minutes_then_drop():
    nc._cache = nc.parse_ff_events(RAW)
    nc._fetched_at = datetime.now(timezone.utc)
    names = lambda t: [e["name"] for e in nc.get_upcoming_events(now=t)]
    assert "CPI m/m" in names(datetime(2026, 11, 10, 13, 40, tzinfo=timezone.utc))
    assert "CPI m/m" not in names(datetime(2026, 11, 10, 13, 50, tzinfo=timezone.utc))


def test_fallback_when_feed_never_loaded():
    events = nc.get_upcoming_events(limit=5, now=datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc))
    assert len(events) == 5
    assert all(e["source"] == "fallback" for e in events)
    assert all(e["minutes_away"] >= -nc.SHOW_PAST_MINUTES for e in events)
    assert events == sorted(events, key=lambda e: e["minutes_away"])


def test_imminent_high_impact_only():
    nc._cache = nc.parse_ff_events(RAW)
    assert nc.get_imminent_high_impact_event(now=datetime(2026, 11, 10, 13, 27, tzinfo=timezone.utc))["name"] == "CPI m/m"
    # ZEW is MEDIUM: never a news warning
    assert nc.get_imminent_high_impact_event(now=datetime(2026, 11, 10, 9, 57, tzinfo=timezone.utc)) is None
    assert nc.get_imminent_high_impact_event(now=datetime(2026, 11, 10, 13, 20, tzinfo=timezone.utc)) is None


@pytest.mark.asyncio
async def test_disk_cache_survives_restart():
    async with _client(lambda req: httpx.Response(200, json=RAW)) as client:
        assert await nc.refresh(client)
    assert nc.CACHE_PATH.exists()
    nc._cache, nc._fetched_at = [], None  # simulate a fresh process
    assert nc.load_disk_cache()
    assert [e["name"] for e in nc._cache] == ["German ZEW Economic Sentiment", "CPI m/m"]


@pytest.mark.asyncio
async def test_stale_or_corrupt_disk_cache_is_ignored():
    async with _client(lambda req: httpx.Response(200, json=RAW)) as client:
        await nc.refresh(client)
    nc._cache, nc._fetched_at = [], None
    assert not nc.load_disk_cache(now=datetime.now(timezone.utc) + nc.DISK_CACHE_MAX_AGE + timedelta(minutes=1))
    nc.CACHE_PATH.write_text("{not json", encoding="utf-8")
    assert not nc.load_disk_cache()
    assert nc._cache == []
