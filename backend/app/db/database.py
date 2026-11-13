"""
Async SQLAlchemy engine, configured from DATABASE_URL (SQLite in dev, Postgres in
Docker). If the database can't be reached at startup the app keeps running on
in-memory state and candle history simply isn't persisted.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker] = None


class _FakeSession:
    """Key-level alerts are still held in memory; routes keep this dependency contract."""

    async def close(self):
        pass


async def get_db():
    yield _FakeSession()


async def init_db(url: Optional[str] = None) -> bool:
    """Create the engine and tables. Returns False (and disables persistence) on failure."""
    global _engine, _sessionmaker
    target = url or settings.database_url
    try:
        from app.db import models  # noqa: F401  (registers tables on Base)

        _engine = create_async_engine(target, pool_pre_ping=True)
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
        logger.info("Database ready (%s)", _engine.dialect.name)
        return True
    except Exception as e:
        logger.warning("Database unavailable, candle history will not persist: %s", e)
        if _engine is not None:
            await _engine.dispose()
        _engine = None
        _sessionmaker = None
        return False


def get_sessionmaker() -> Optional[async_sessionmaker]:
    return _sessionmaker


async def close_db() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
