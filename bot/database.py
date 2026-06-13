"""Shared async database engine and session factory.

A single engine (and therefore a single connection pool) is created for the
whole process and reused by every cog. This keeps connection usage predictable,
which matters for managed providers like Neon that cap concurrent connections.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import config

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> AsyncEngine:
    """Create the shared engine and session factory if not already created."""
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(config.database_url, **config.engine_options)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the shared session factory, initializing the engine on first use."""
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


async def dispose_engine() -> None:
    """Dispose the shared engine and reset module state."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
