"""Users API router."""

from __future__ import annotations

import json
import logging

import redis.asyncio
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.dependencies import get_db
from src.users import crud
from src.users.calculations import calculate_days_since_created
from src.users.exceptions import UserNotFoundError
from src.users.schemas import (
    DomainCountResponse,
    RecentUsersResponse,
    UserCountResponse,
    UserCreate,
    UserList,
    UserPublic,
    UserSummaryResponse,
    UserUpdate,
)
from src.users.validators import (
    get_validated_min_count,
    get_validated_user_id,
    validate_limit,
)

logger = logging.getLogger(__name__)

# Authorization token expected in the X-Auth-Token header.
# In production this would be validated against a real auth provider.
AUTH_TOKEN = "dev-token"

CACHE_TTL = 300  # 5 minutes
REDIS_URL = "redis://localhost:6379/0"


def _cache_key(user_id: str) -> str:
    """Generate a cache key for a user summary.

    Args:
        user_id: The user UUID string.

    Returns:
        A cache key string following the pattern user:summary:{user_id}.
    """
    return f"user:summary:{user_id}"


async def _get_cached_summary(user_id: str) -> dict | None:
    """Retrieve a cached user summary from Redis.

    Args:
        user_id: The user UUID string.

    Returns:
        The cached summary dict, or None if not found or on error.
    """
    try:
        client = redis.asyncio.from_url(REDIS_URL, decode_responses=True)
        data = await client.get(_cache_key(user_id))
        await client.close()
        if data is not None:
            return json.loads(data)
    except Exception:
        logger.debug("Cache read failed for user %s", user_id)
    return None


async def _set_cached_summary(user_id: str, summary: dict) -> None:
    """Store a user summary in Redis cache.

    Args:
        user_id: The user UUID string.
        summary: The summary dict to cache.
    """
    try:
        client = redis.asyncio.from_url(REDIS_URL, decode_responses=True)
        await client.set(
            _cache_key(user_id),
            json.dumps(summary),
            ex=CACHE_TTL,
        )
        await client.close()
    except Exception:
        logger.debug("Cache write failed for user %s", user_id)


def require_auth(request: Request) -> None:
    """FastAPI dependency that enforces authentication on protected endpoints.

    Checks for the ``X-Auth-Token`` header and validates it against the
    configured auth token.  Returns a 403 response when the header is
    missing or incorrect.

    Args:
        request: The incoming FastAPI request.

    Raises:
        HTTPException: 403 Forbidden if the request is unauthorized.
    """
    token = request.headers.get("X-Auth-Token")
    if not token or token != AUTH_TOKEN:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: valid authentication token required",
        )


router = APIRouter(prefix="/users", redirect_slashes=False)


@router.post(
    "",
    response_model=UserPublic,
    status_code=201,
    tags=["users"],
    summary="Create a new user",
    description="Creates a new user with the provided email and optional full name.",
    responses={
        201: {"description": "User created successfully"},
        409: {"description": "User with this email already exists"},
    },
)
async def create_user(
    user_in: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserPublic:
    """Create a new user."""
    user = await crud.create_user(db, user_in)
    return UserPublic.model_validate(user)


@router.get(
    "",
    response_model=UserList,
    tags=["users"],
    summary="List users with pagination",
    description="Returns a paginated list of users.",
)
async def list_users(
    skip: int = 0, limit: str = "100", db: AsyncSession = Depends(get_db)
) -> UserList:
    """List users with optional pagination."""
    try:
        limit = validate_limit(limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    users = await crud.get_users(db, skip=skip, limit=limit)
    total = await crud.count_users(db)
    return UserList(items=[UserPublic.model_validate(u) for u in users], total=total)


@router.get(
    "/count",
    response_model=UserCountResponse,
    tags=["users"],
    summary="Get total user count",
    description="Returns the total number of users stored in the database.",
    responses={
        503: {"description": "Database unavailable"},
    },
)
async def get_user_count(db: AsyncSession = Depends(get_db)) -> UserCountResponse:
    """Get total user count.

    Returns the total number of users in the database.
    Returns 503 if the database is unavailable.
    """
    try:
        total = await crud.count_users(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    return UserCountResponse(count=total)


@router.get(
    "/count-today",
    response_model=UserCountResponse,
    tags=["users"],
    summary="Get today's user count",
    description="Returns the number of users created on the current calendar day.",
    responses={
        503: {"description": "Database unavailable"},
    },
)
async def get_users_count_today(
    db: AsyncSession = Depends(get_db),
) -> UserCountResponse:
    """Get today's user count.

    Returns the number of users created on the current calendar day.
    Returns 503 if the database is unavailable.
    """
    try:
        total = await crud.count_users_today(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    return UserCountResponse(count=total)


@router.get(
    "/count-by-domain",
    response_model=list[DomainCountResponse],
    tags=["users"],
    summary="Get user count by email domain",
    description=(
        "Returns a JSON array of {domain, count} objects showing how many "
        "users are registered per email domain, ordered by count descending. "
        "An optional ``min_count`` query parameter filters results to only "
        "include domains with at least that many users."
    ),
    responses={
        503: {"description": "Database unavailable"},
    },
)
async def get_domain_count(
    min_count: int | None = Depends(get_validated_min_count),
    db: AsyncSession = Depends(get_db),
) -> list[DomainCountResponse]:
    """Get user count grouped by email domain.

    Extracts the domain portion from each user's email address, groups by domain,
    and returns counts ordered by count descending.

    When ``min_count`` is provided, only domains with a count greater than or
    equal to the given value are returned.

    Returns 400 if ``min_count`` is invalid (empty, non-integer, negative, or
    exceeds the maximum allowed value of 10,000).

    Returns 503 if the database is unavailable.
    """
    try:
        rows = await crud.count_users_by_domain(db, min_count=min_count)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    return [DomainCountResponse(**row) for row in rows]


@router.get(
    "/{user_id}/summary",
    response_model=UserSummaryResponse,
    tags=["users"],
    summary="Get user summary",
    description=(
        "Returns a summary of user profile information "
        "including account metadata. Falls back to cache when the database "
        "is unavailable."
    ),
    responses={
        400: {"description": "Invalid user ID format"},
        404: {"description": "User not found"},
        503: {"description": "Database unavailable"},
    },
)
async def get_user_summary(
    validated_user_id: str = Depends(get_validated_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserSummaryResponse:
    """Get a user summary with profile metadata.

    Attempts to fetch user data from the database. If the database is
    unavailable, falls back to the Redis cache. If the cache contains
    the record for the requested user, returns cached data. If the
    cache does not contain the record, returns 404 (user not found).

    Args:
        user_id: The UUID of the user to retrieve.
        db: The async database session.

    Returns:
        UserSummaryResponse with user profile summary data.

    Raises:
        UserNotFoundError: If the user does not exist in the database
            or cache.
    """
    user_id_str = validated_user_id
    try:
        user = await crud.get_user(db, user_id_str)
        if user is None:
            raise UserNotFoundError(user_id=user_id_str)

        days_since_created = calculate_days_since_created(user.created_at)

        profile_metadata: dict[str, str] = {
            "email": user.email,
            "status": "active" if user.is_active else "inactive",
        }

        display_name = user.full_name or user.email.split("@")[0]

        summary = UserSummaryResponse(
            username=user.email,
            display_name=display_name,
            profile_metadata=profile_metadata,
            days_since_created=days_since_created,
            is_active=user.is_active,
        )
        # Cache the result for future requests
        await _set_cached_summary(user_id_str, summary.model_dump())
        return summary
    except SQLAlchemyError as exc:
        logger.warning("Database unavailable for user summary: %s", exc)
        # Fall back to cache
        cached = await _get_cached_summary(user_id_str)
        if cached is not None:
            return UserSummaryResponse(**cached)
        # Cache miss means the user is unknown (never queried before)
        raise UserNotFoundError(user_id=user_id_str) from exc


@router.get(
    "/by-email",
    response_model=UserPublic,
    tags=["users"],
    summary="Get user by email",
    description="Retrieves a user by their exact email address.",
    responses={
        404: {"description": "User not found"},
        503: {"description": "Database unavailable"},
    },
)
async def get_user_by_email(
    email: EmailStr, db: AsyncSession = Depends(get_db)
) -> UserPublic:
    """Get user by email.

    Returns the user with the exact matching email address.
    Returns 404 if no user has that email.
    Returns 503 if the database is unavailable.
    """
    try:
        user = await crud.get_user_by_email(db, email)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"User with email '{email}' not found",
        )
    return UserPublic.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    tags=["users"],
    summary="Get user by ID",
    description="Retrieves a specific user by their UUID.",
    responses={
        400: {"description": "Invalid user ID format"},
        404: {"description": "User not found"},
        503: {"description": "Database unavailable"},
    },
)
async def get_user(
    validated_user_id: str = Depends(get_validated_user_id),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """Get user by ID.

    Returns the user with the matching ID.
    Returns 400 if the user ID format is invalid.
    Returns 404 if no user has that ID.
    Returns 503 if the database is unavailable.
    """
    try:
        user = await crud.get_user(db, validated_user_id)
    except SQLAlchemyError as exc:
        logger.error(
            "Database error while fetching user %s: %s", validated_user_id, exc
        )
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    if user is None:
        raise UserNotFoundError(user_id=validated_user_id)
    return UserPublic.model_validate(user)


recent_router = APIRouter(prefix="/recent-users", redirect_slashes=False)


@recent_router.get(
    "",
    response_model=RecentUsersResponse,
    tags=["users"],
    summary="Get recent users",
    description=(
        "Returns the most recently created users in descending order "
        "of creation timestamp."
    ),
    responses={
        503: {"description": "Database unavailable"},
    },
)
async def get_recent_users(
    limit: str = "10", db: AsyncSession = Depends(get_db)
) -> RecentUsersResponse:
    """Get recent users in descending order of creation timestamp.

    Args:
        limit: Maximum number of users to return (default 10, max 100).
        db: The async database session.

    Returns:
        RecentUsersResponse with users ordered by created_at descending.

    Raises:
        HTTPException: 400 if limit is not a valid positive integer.
    """
    try:
        limit = validate_limit(limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    try:
        users = await crud.get_recent_users(db, limit=limit)
        total = await crud.count_users(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc
    return RecentUsersResponse(
        users=[UserPublic.model_validate(u) for u in users],
        total=total,
    )


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    tags=["users"],
    summary="Update user",
    description="Updates an existing user with the provided data.",
    responses={
        400: {"description": "Invalid user ID format"},
        404: {"description": "User not found"},
    },
)
async def update_user(
    validated_user_id: str = Depends(get_validated_user_id),
    user_in: UserUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    """Update user.

    Returns 400 if the user ID format is invalid.
    Returns 404 if no user has that ID.
    """
    user = await crud.update_user(db, validated_user_id, user_in)
    if user is None:
        raise UserNotFoundError(user_id=validated_user_id)
    return UserPublic.model_validate(user)


@router.delete(
    "/by-email",
    status_code=204,
    tags=["users"],
    summary="Delete user by email",
    description=(
        "Deletes a user by their exact email address. "
        "Returns 204 No Content on success."
    ),
    responses={
        204: {"description": "User deleted successfully"},
        404: {"description": "User not found"},
        422: {"description": "Malformed email address"},
        503: {"description": "Database unavailable"},
    },
)
async def delete_user_by_email(
    email: EmailStr, db: AsyncSession = Depends(get_db)
) -> Response:
    """Delete user by email.

    Finds the user with the exact matching email address and deletes them.
    Returns 204 on success, 404 if no user has that email,
    503 if the database is unavailable.
    """
    try:
        user = await crud.get_user_by_email(db, email)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"User with email '{email}' not found",
        )

    try:
        deleted = await crud.delete_user(db, str(user.id))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"User with email '{email}' not found",
        )
    return Response(status_code=204)


@router.delete(
    "/{user_id}",
    status_code=204,
    tags=["users"],
    summary="Delete user",
    description="Deletes a user by ID. Returns 204 No Content on success.",
    responses={
        204: {"description": "User deleted successfully"},
        400: {"description": "Invalid user ID format"},
        403: {"description": "Unauthorized: valid authentication token required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    request: Request,
    validated_user_id: str = Depends(get_validated_user_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete user.

    Requires authentication via the ``X-Auth-Token`` header.
    Returns 400 if the user ID format is invalid.
    Returns 403 if the request is unauthorized.
    Returns 404 if no user has that ID.
    """
    require_auth(request)
    deleted = await crud.delete_user(db, validated_user_id)
    if not deleted:
        raise UserNotFoundError(user_id=validated_user_id)
    return Response(status_code=204)
