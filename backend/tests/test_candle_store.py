from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.db import database
from app.models.schemas import Candle
from app.services import candle_store
from app.services.twelve_data import CandleAggregator, TwelveDataStream

T0 = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)


def c(minute: int, close: float = 1.12) -> Candle:
    return Candle(open=close - 0.0001, high=close + 0.0002, low=close - 0.0002, close=close,
                  volume=5, timestamp=T0 + timedelta(minutes=minute))


@pytest_asyncio.fixture
async def db(tmp_path):
    assert await database.init_db(f"sqlite+aiosqlite:///{tmp_path / 'candles.db'}")
    yield
    await database.close_db()


@pytest.mark.asyncio
async def test_save_and_load_round_trip(db):
    for m in (2, 0, 1):
        assert await candle_store.save_candle("EUR/USD", c(m, 1.12 + m / 1000))
    loaded = await candle_store.load_recent("EUR/USD", limit=10)
    assert [x.timestamp for x in loaded] == [T0, T0 + timedelta(minutes=1), T0 + timedelta(minutes=2)]
    assert loaded[-1].close == pytest.approx(1.122)
    assert all(x.timestamp.tzinfo is not None for x in loaded)


@pytest.mark.asyncio
async def test_duplicate_minute_is_ignored(db):
    assert await candle_store.save_candle("EUR/USD", c(0))
    assert not await candle_store.save_candle("EUR/USD", c(0))
    assert len(await candle_store.load_recent("EUR/USD")) == 1


@pytest.mark.asyncio
async def test_load_recent_respects_limit_and_pair(db):
    for m in range(5):
        await candle_store.save_candle("EUR/USD", c(m))
    await candle_store.save_candle("USD/JPY", c(0, 149.8))
    recent = await candle_store.load_recent("EUR/USD", limit=2)
    assert [x.timestamp for x in recent] == [T0 + timedelta(minutes=3), T0 + timedelta(minutes=4)]
    assert len(await candle_store.load_recent("USD/JPY")) == 1


@pytest.mark.asyncio
async def test_prune_removes_old_candles(db):
    old = Candle(open=1, high=1, low=1, close=1, timestamp=datetime.now(timezone.utc) - timedelta(days=40))
    new = Candle(open=1, high=1, low=1, close=1, timestamp=datetime.now(timezone.utc))
    await candle_store.save_candle("EUR/USD", old)
    await candle_store.save_candle("EUR/USD", new)
    assert await candle_store.prune(older_than_days=30) == 1
    assert len(await candle_store.load_recent("EUR/USD")) == 1


@pytest.mark.asyncio
async def test_no_database_is_a_no_op():
    await database.close_db()
    assert not await candle_store.save_candle("EUR/USD", c(0))
    assert await candle_store.load_recent("EUR/USD") == []
    assert await candle_store.prune() == 0


@pytest.mark.asyncio
async def test_unreachable_database_disables_persistence():
    ok = await database.init_db("postgresql+asyncpg://nobody:nothing@127.0.0.1:1/none")
    assert ok is False
    assert database.get_sessionmaker() is None


def test_aggregator_seed_keeps_last_100():
    agg = CandleAggregator()
    agg.seed("EUR/USD", [c(m) for m in range(150)])
    candles = agg.get_candles("EUR/USD")
    assert len(candles) == 100
    assert candles[0].timestamp == T0 + timedelta(minutes=50)


@pytest.mark.asyncio
async def test_stream_fires_candle_closed_on_minute_rollover():
    stream = TwelveDataStream()
    closed = []

    async def on_closed(pair, candle):
        closed.append((pair, candle))

    stream.on_candle_closed(on_closed)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.twelve_data.datetime", _FakeClock([T0, T0 + timedelta(seconds=30), T0 + timedelta(minutes=1, seconds=5)]))
        for price in (1.1200, 1.1210, 1.1205):
            await stream._handle_message({"event": "price", "symbol": "EUR/USD", "price": str(price)})
    assert len(closed) == 1
    pair, candle = closed[0]
    assert pair == "EUR/USD"
    assert (candle.open, candle.high, candle.close) == (1.12, 1.121, 1.121)


class _FakeClock:
    """Stands in for the datetime class inside twelve_data so ticks get chosen times."""

    def __init__(self, times):
        self._times = list(times)

    def now(self, tz=None):
        return self._times.pop(0)
