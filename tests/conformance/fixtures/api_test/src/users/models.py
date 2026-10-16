"""SQLAlchemy ORM model for users."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import DeclarativeBase

if TYPE_CHECKING:
    pass


class User(DeclarativeBase):
    """User model representing the users table in the database.

    Attributes:
        id: UUID primary key with server-default uuid4
        email: Unique, indexed string (not nullable)
        full_name: Optional string
        is_active: Boolean, default True
        created_at: Timestamp with timezone, server-default now()
        updated_at: Timestamp with timezone, server-default now(), onupdate now()
    """

    __tablename__ = "users"

    # Override the inherited id column to use Python-side UUID generation
    # This works with both SQLite and PostgreSQL
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps - DeclarativeBase provides these, but we override to add timezone
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email!r})"
