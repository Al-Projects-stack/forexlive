"""
Candle persistence. Closed candles are written as they complete; on startup the
most recent ones are loaded back so a restart doesn't wipe the chart. Every
function is a no-op when the database is unavailable.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.database import get_sessionmaker
from app.db.models import CandleRecord
from app.models.schemas import Candle

logger = logging.getLogger(__name__)


def _utc(dt: datetime) -> datetime:
    # SQLite drops tzinfo on the way back out; everything we store is UTC
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


async def save_candle(pair: str, candle: Candle) -> bool:
    maker = get_sessionmaker()
    if maker is None or candle.timestamp is None:
        return False
    try:
        async with maker() as session:
            session.add(CandleRecord(
                pair=pair, ts=_utc(candle.timestamp),
                open=candle.open, high=candle.high, low=candle.low, close=candle.close,
                volume=candle.volume,
            ))
            await session.commit()
        return True
    except IntegrityError:
        return False  # this minute is already stored
    except Exception as e:
        logger.error("Failed to save %s candle: %s", pair, e)
        return False


async def load_recent(pair: str, limit: int = 100) -> list[Candle]:
    maker = get_sessionmaker()
    if maker is None:
        return []
    try:
        async with maker() as session:
            rows = (await session.execute(
                select(CandleRecord).where(CandleRecord.pair == pair)
                .order_by(CandleRecord.ts.desc()).limit(limit)
            )).scalars().all()
        return [
            Candle(open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume, timestamp=_utc(r.ts))
            for r in reversed(rows)
        ]
    except Exception as e:
        logger.error("Failed to load %s candles: %s", pair, e)
        return []


async def prune(older_than_days: int = 30) -> int:
    maker = get_sessionmaker()
    if maker is None:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    try:
        async with maker() as session:
            result = await session.execute(delete(CandleRecord).where(CandleRecord.ts < cutoff))
            await session.commit()
        return result.rowcount or 0
    except Exception as e:
        logger.error("Failed to prune candles: %s", e)
        return 0
