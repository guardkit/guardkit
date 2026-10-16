"""Search API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.dependencies import get_db
from src.search.schemas import SearchResponse
from src.users.models import User

router = APIRouter(tags=["search"], redirect_slashes=False)


async def _validate_name_param(name: str | None = Query(default=None)) -> str:
    """Validate that the `name` query parameter is provided.

    Args:
        name: The name query parameter value, or None if not provided.

    Returns:
        The name value if provided.

    Raises:
        HTTPException: 400 Bad Request if name parameter is missing.
    """
    if name is None:
        raise HTTPException(
            status_code=400,
            detail="The 'name' query parameter is required",
        )
    return name


@router.get(
    "/search",
    response_model=SearchResponse,
    tags=["search"],
    summary="Search for content",
    description=(
        "Searches for content matching the provided query name. "
        "Returns a list of matching results and the total count."
    ),
    responses={
        200: {"description": "Search completed successfully"},
        400: {"description": "Name parameter is missing"},
    },
)
async def search(
    validated_name: str = Depends(_validate_name_param),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search endpoint.

    Accepts a `name` query parameter and returns matching results.
    Uses case-insensitive substring matching on user full names.
    Empty or whitespace-only queries return all users.
    """
    if not validated_name or not validated_name.strip():
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        results = [u.full_name for u in users if u.full_name]
        return SearchResponse(query=validated_name, results=results, total=len(results))

    query_lower = validated_name.lower()
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    results = [
        u.full_name for u in users if u.full_name and query_lower in u.full_name.lower()
    ]
    return SearchResponse(query=validated_name, results=results, total=len(results))
