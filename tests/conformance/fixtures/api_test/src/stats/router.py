"""Service request statistics module.

Provides an in-process request counter via ASGI middleware and a
GET /stats endpoint mirroring the /health module structure.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.core.config import settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp


# ---------------------------------------------------------------------------
# Thread-safe in-process state
# ---------------------------------------------------------------------------


class StatsState:
    """Thread-safe container for in-process request statistics."""

    __slots__ = ("_lock", "_requests_served", "_first_request_at")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests_served = 0
        self._first_request_at: datetime | None = None

    # -- mutation ----------------------------------------------------------

    def increment(self) -> datetime:
        """Increment the request counter.

        Returns the first-request timestamp (setting it on first call).
        """
        with self._lock:
            self._requests_served += 1
            if self._first_request_at is None:
                self._first_request_at = datetime.now(UTC)
            return self._first_request_at

    # -- query -------------------------------------------------------------

    def snapshot(self) -> tuple[str, int, datetime | None]:
        """Return (service, requests_served, first_request_at)."""
        with self._lock:
            return (
                settings.app_name,
                self._requests_served,
                self._first_request_at,
            )


# Module-level shared state instance
_stats_state = StatsState()


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------


class StatsCounterMiddleware(BaseHTTPMiddleware):
    """Middleware that increments an in-process request counter on every request."""

    def __init__(self, app: ASGIApp, state: StatsState | None = None) -> None:
        super().__init__(app)
        self._state = state if state is not None else _stats_state

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Increment the counter for every handled request."""
        self._state.increment()
        return await call_next(request)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):  # type: ignore[name-defined]
    """Statistics response model.

    Provides the service name, total requests served, and the timestamp of
    the first recorded request (UTC ISO-8601 or null).
    """

    service: str = Field(description="The name of the service")
    requests_served: int = Field(description="Total number of requests served")
    first_request_at: str | None = Field(
        description="UTC ISO-8601 timestamp of the first recorded request, or null",
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["stats"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Service request statistics",
)
async def get_stats() -> StatsResponse:
    """Return in-process request statistics."""
    service, requests_served, first_request_at = _stats_state.snapshot()
    return StatsResponse(
        service=service,
        requests_served=requests_served,
        first_request_at=first_request_at.isoformat() if first_request_at else None,
    )
