"""Async SQLAlchemy session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine as _create_async_engine_impl,
)

from src.core.config import settings

# Async engine instance (initialized lazily)
_engine: AsyncEngine | None = None


def create_async_engine() -> AsyncEngine:
    """Create and configure the async SQLAlchemy engine.

    Returns:
        AsyncEngine: Configured async engine with connection pooling.
    """
    global _engine

    if _engine is not None:
        return _engine

    _engine = _create_async_engine_impl(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,  # Validate connections before use
    )

    return _engine


def init_engine() -> AsyncEngine:
    """Initialize the async engine if not already initialized.

    Returns:
        AsyncEngine: The initialized engine.
    """
    global _engine

    if _engine is None:
        _engine = create_async_engine()

    return _engine


async def dispose_engine() -> None:
    """Dispose of the async engine and close all connections.

    This should be called during application shutdown to cleanly
    close all pooled connections.
    """
    global _engine

    if _engine is not None:
        await _engine.dispose()
        _engine = None


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions.

    Yields:
        AsyncSession: A database session.
    """
    engine = init_engine()
    async_session_factory = _create_async_session_factory(engine)
    async with async_session_factory() as session:
        yield session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...

    Yields:
        AsyncSession: A database session that is automatically closed.
    """
    engine = init_engine()
    async_session_factory = _create_async_session_factory(engine)
    async with async_session_factory() as session:
        yield session


def _create_async_session_factory(engine: AsyncEngine) -> Any:
    """Create an async session factory for the given engine.

    This is a private helper function to avoid type inference issues
    with async_sessionmaker.

    Args:
        engine: The async engine to create sessions from.

    Returns:
        A callable that creates AsyncSession instances.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
