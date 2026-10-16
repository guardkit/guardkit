"""Time endpoint API router."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from src.time.schemas import TimeResponse

router = APIRouter()


@router.get(
    "/time",
    response_model=TimeResponse,
    tags=["time"],
    summary="Get current server time",
    description="Returns the current UTC time in ISO-8601 format with second precision and the service name.",
    responses={
        200: {"description": "Current time retrieved successfully"},
        405: {"description": "Method not allowed"},
    },
)
async def get_time() -> TimeResponse:
    """Get current server time endpoint.

    Returns the current UTC time computed at request time,
    never a cached or module-level constant.
    """
    now = datetime.now(timezone.utc)
    # Second precision: truncate microseconds, render +00:00 as Z
    time_str = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return TimeResponse(time=time_str, service="api_test")
