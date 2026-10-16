"""Whoami API router."""

from __future__ import annotations

from fastapi import APIRouter

from src.core.config import settings
from src.whoami.schemas import WhoamiResponse

router = APIRouter()


@router.get(
    "/whoami",
    response_model=WhoamiResponse,
    tags=["whoami"],
    summary="Identify the API service",
    description="Returns the name of the API service currently running.",
    responses={
        200: {"description": "Service identification returned successfully"},
    },
)
async def whoami() -> WhoamiResponse:
    """Whoami endpoint.

    Returns the name of the API service.
    """
    return WhoamiResponse(service=settings.app_name)
