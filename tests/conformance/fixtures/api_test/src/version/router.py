"""Version information API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from src.core.config import settings
from src.version.schemas import VersionResponse
from src.version.utils import get_git_commit_hash

router = APIRouter()


def _accept_json_header(accept: str | None = Header(default=None)) -> None:
    """Dependency to enforce application/json Accept header.

    Returns 406 Not Acceptable when an Accept header IS present but does not
    include application/json. When no Accept header is sent, the request
    proceeds normally (HTTP spec: absence of Accept means any media type is OK).
    Wildcard Accept headers (e.g., */*) are treated as accepting all types.

    Args:
        accept: The Accept header value from the request.

    Raises:
        HTTPException: 406 if Accept header is present but application/json
            is not included.
    """
    if accept is not None:
        # Wildcard accepts everything
        if accept.strip() == "*/*":
            return
        # Check if application/json is explicitly listed
        if "application/json" in accept:
            return
        raise HTTPException(
            status_code=406,
            detail="Not Acceptable: application/json is required",
        )


@router.get(
    "/version",
    response_model=VersionResponse,
    tags=["version"],
    summary="Get version information",
    description="Returns the application version, git commit hash, and service name.",
    responses={
        200: {"description": "Version information retrieved successfully"},
        405: {"description": "Method not allowed"},
        406: {"description": "Not Acceptable: unsupported media type"},
    },
    dependencies=[Depends(_accept_json_header)],
)
async def get_version() -> VersionResponse:
    """Get version information endpoint.

    Returns the current application version, git commit hash, and service name.
    """
    return VersionResponse(
        version=settings.app_version,
        commit=get_git_commit_hash(),
        service=settings.app_name,
    )
