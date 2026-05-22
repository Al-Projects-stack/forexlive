"""
Database stub for local dev — no connection required.
In production with Docker/PostgreSQL, replace engine and session with real async SQLAlchemy.
"""
from contextlib import asynccontextmanager


class _FakeSession:
    async def close(self):
        pass


async def get_db():
    yield _FakeSession()


async def init_db():
    pass  # No-op in local dev mode
