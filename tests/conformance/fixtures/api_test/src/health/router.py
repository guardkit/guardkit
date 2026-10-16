"""Health check API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.dependencies import get_db
from src.health.readiness import is_ready
from src.health.schemas import HealthResponse, ReadyResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Check service health",
    description=(
        "Returns the current health status, version, logging configuration, "
        "and database connectivity status of the API service."
    ),
    responses={
        200: {"description": "Service is healthy"},
    },
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Health check endpoint.

    Returns the current service health status including database connectivity.
    When the database is unreachable, returns status "degraded" with database
    "unavailable".
    """
    # Probe database connection
    db_status = "connected"
    try:
        result = await db.execute(text("SELECT 1"))
        result.fetchone()
    except SQLAlchemyError:
        db_status = "unavailable"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.app_version,
        log_level=settings.log_level,
        log_format=settings.log_format,
        database=db_status,
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
    tags=["health"],
    summary="Check service readiness",
    description=(
        "Returns whether the service is ready to accept requests. "
        "This endpoint is intended for Kubernetes readiness probes."
    ),
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready"},
    },
)
async def readiness_check(response: Response) -> ReadyResponse:
    """Readiness check endpoint.

    Returns a simple status indicating the service is ready to accept requests.
    Returns 200 when ready, 503 when not ready. This is a lightweight check
    suitable for Kubernetes readiness probes.
    """
    if is_ready():
        return ReadyResponse(status="ready", service=settings.app_name)
    response.status_code = 503
    return ReadyResponse(status="not_ready", service=settings.app_name)
