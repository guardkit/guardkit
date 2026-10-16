"""FastAPI dependencies for database integration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_async_session

# Type alias for dependency injection
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Provides an async database session that is automatically closed
    after the request is processed.

    Yields:
        AsyncSession: A database session for the current request.

    Example:
        @router.get("/users")
        async def read_users(db: AsyncSessionDep):
            users = await db.execute(select(User))
            return users.scalars().all()
    """
    async with get_async_session() as session:
        yield session


__all__ = ["AsyncSessionDep", "get_db"]
