"""CRUD operations for User model."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.exceptions import UserAlreadyExistsError
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a new user.

    Args:
        db: The async database session.
        user_in: User creation data.

    Returns:
        The created User object.

    Raises:
        UserAlreadyExistsError: If a user with the same email already exists.
    """
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        is_active=True,
    )

    db.add(user)
    try:
        await db.flush()
        await db.refresh(user)
        await db.commit()
        return user
    except IntegrityError:
        await db.rollback()
        raise UserAlreadyExistsError(email=user_in.email) from None


async def get_user(db: AsyncSession, user_id: str) -> User | None:
    """Get a user by ID.

    Args:
        db: The async database session.
        user_id: The UUID of the user.

    Returns:
        The User object if found, None otherwise.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> Sequence[User]:
    """Get a list of users with optional pagination.

    Args:
        db: The async database session.
        skip: Number of records to skip (default 0).
        limit: Maximum number of records to return (default 100).

    Returns:
        Sequence of User objects.
    """
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by email.

    Args:
        db: The async database session.
        email: The email address to search for.

    Returns:
        The User object if found, None otherwise.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession, user_id: str, user_in: UserUpdate
) -> User | None:
    """Update an existing user with partial data.

    Args:
        db: The async database session.
        user_id: The UUID of the user to update.
        user_in: User update data (only provided fields will be updated).

    Returns:
        The updated User object if found, None if user not found.
    """
    user = await get_user(db, user_id)
    if user is None:
        return None

    # Update only the fields that were explicitly set
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """Soft-delete a user by ID.

    Sets the ``deleted_at`` timestamp instead of removing the row,
    so that count endpoints can exclude deleted users while preserving
    audit history.

    Returns False if the user is already soft-deleted (prevents double-delete).

    Args:
        db: The async database session.
        user_id: The UUID of the user to delete.

    Returns:
        True if the user was deleted, False if not found or already deleted.
    """
    user = await get_user(db, user_id)
    if user is None:
        return False

    # Prevent double-delete: if already soft-deleted, return False
    if user.deleted_at is not None:
        return False

    from datetime import UTC, datetime

    user.deleted_at = datetime.now(UTC)
    db.add(user)
    await db.flush()
    await db.commit()
    return True


async def count_users(db: AsyncSession) -> int:
    """Count total number of non-deleted users.

    Args:
        db: The async database session.

    Returns:
        Total number of non-deleted users in the database.
    """
    stmt = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    result = await db.execute(stmt)
    return result.scalar_one() or 0


async def count_users_today(db: AsyncSession) -> int:
    """Count users created on the current day.

    Uses date-only comparison so that users created at any time
    during the current calendar day are included.

    Args:
        db: The async database session.

    Returns:
        Number of users created today.
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Build start-of-today and start-of-tomorrow as timezone-aware datetimes
    start_today = datetime(today.year, today.month, today.day, tzinfo=UTC)
    start_tomorrow = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=UTC)

    stmt = (
        select(func.count())
        .select_from(User)
        .where(User.created_at >= start_today)
        .where(User.created_at < start_tomorrow)
        .where(User.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one() or 0


async def count_users_by_domain(
    db: AsyncSession, min_count: int | None = None
) -> list[dict[str, int | str]]:
    """Count users grouped by email domain.

    Extracts the domain portion from each user's email address, groups by domain,
    and returns counts ordered by count descending.

    Uses a SQL expression that works across both SQLite and PostgreSQL:
    - SQLite: INSTR(email, '@') to find the @ position
    - PostgreSQL: POSITION('@' IN email) via SQLAlchemy's func.position

    Malformed emails (those without '@') are excluded from the count.

    When ``min_count`` is provided, only domains with a count >= min_count
    are included in the result.

    Args:
        db: The async database session.
        min_count: Optional minimum count threshold for filtering domains.

    Returns:
        List of dicts with 'domain' (str) and 'count' (int) keys,
        ordered by count descending.
    """
    # Postgres has no instr(); SQLite has no strpos(). The sandbox gate
    # caught this live on 2026-08-25: green on the SQLite test database,
    # 503 on the real Postgres. Pick the position function by dialect —
    # what the old comment claimed and never did.
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "postgresql":
        at_position = func.strpos(User.email, "@")
    else:
        at_position = func.instr(User.email, "@")

    domain_expr = func.substr(
        User.email,
        at_position + 1,
    )

    count_expr = func.count().label("count")
    stmt = (
        select(domain_expr.label("domain"), count_expr)
        .select_from(User)
        .where(at_position > 0)
        .where(User.deleted_at.is_(None))
        .group_by(domain_expr)
        .order_by(func.count().desc())
    )

    if min_count is not None:
        stmt = stmt.having(func.count() >= min_count)

    result = await db.execute(stmt)
    rows = result.fetchall()
    return [{"domain": row.domain, "count": row.count} for row in rows]


async def get_recent_users(db: AsyncSession, limit: int = 10) -> Sequence[User]:
    """Get the most recently created users in descending order.

    Args:
        db: The async database session.
        limit: Maximum number of users to return (default 10).

    Returns:
        Sequence of User objects ordered by created_at descending.
    """
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
