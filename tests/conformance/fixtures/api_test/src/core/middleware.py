"""ASGI middleware for correlation ID and request logging."""

from __future__ import annotations

import contextvars
import time
import uuid
from typing import TYPE_CHECKING

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from src.core.config import settings

if TYPE_CHECKING:
    from starlette.types import ASGIApp

# ContextVar for correlation ID storage
_correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Get the current request's correlation ID from contextvars.

    Returns:
        The correlation ID string, or None if not set.
    """
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in contextvars.

    Args:
        correlation_id: The correlation ID to set.
    """
    _correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from contextvars."""
    _correlation_id_var.set(None)


class APIVersionHeaderMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that injects X-API-Version header into responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and add version header to response.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to process the request and get the response.

        Returns:
            Response with X-API-Version header added.
        """
        response = await call_next(request)
        response.headers["X-API-Version"] = settings.app_version
        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that generates and manages correlation IDs per request.

    This middleware:
    - Checks for an incoming X-Correlation-ID header and uses it if present
    - Generates a UUID4 correlation ID if none is provided
    - Stores the correlation ID in a ContextVar for access throughout the request
    - Binds the correlation ID to structlog context for logging
    - Adds X-Correlation-ID header to all responses
    - Clears contextvars after request completes
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and manage correlation ID.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to process the request and get the response.

        Returns:
            Response with X-Correlation-ID header added.
        """
        # Check for incoming X-Correlation-ID header
        incoming_correlation_id = request.headers.get("X-Correlation-ID")

        if incoming_correlation_id:
            correlation_id = incoming_correlation_id
        else:
            correlation_id = str(uuid.uuid4())

        # Store in ContextVar
        set_correlation_id(correlation_id)

        # Bind to structlog context for all logs in this request
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Add correlation ID to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        # Clear contextvars after request completes
        structlog.contextvars.unbind_contextvars("correlation_id")
        clear_correlation_id()

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that logs request start and completion.

    This middleware:
    - Logs request start with method, path, and client IP
    - Logs request completion with method, path, status code, and duration
    - Measures duration using time.perf_counter()
    - Supports configurable health endpoint logging skip
    """

    def __init__(
        self,
        app: ASGIApp,
        skip_health_logging: bool = True,
    ) -> None:
        """
        Initialize the RequestLoggingMiddleware.

        Args:
            app: The ASGI application.
            skip_health_logging: Whether to skip logging for health endpoints.
        """
        super().__init__(app)
        self.skip_health_logging = skip_health_logging

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process request and log start/completion.

        Args:
            request: The incoming HTTP request.
            call_next: Callable to process the request and get the response.

        Returns:
            The HTTP response.
        """
        # Check if this is a health endpoint
        path = request.url.path
        is_health_endpoint = path.startswith("/health")

        # Get logger
        logger = structlog.get_logger("request")

        # Log request start
        if not (self.skip_health_logging and is_health_endpoint):
            logger.info(
                "request_started",
                method=request.method,
                path=path,
                client_ip=self._get_client_ip(request),
            )

        # Measure request duration
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Log error if needed
            if not (self.skip_health_logging and is_health_endpoint):
                logger.error(
                    "request_error",
                    method=request.method,
                    path=path,
                    exc_info=True,
                )
            raise

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Log request completion
        if not (self.skip_health_logging and is_health_endpoint):
            logger.info(
                "request_completed",
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

        return response

    def _get_client_ip(self, request: Request) -> str | None:
        """
        Get client IP address from request.

        Args:
            request: The incoming HTTP request.

        Returns:
            The client IP address, or None if not determinable.
        """
        # Check X-Forwarded-For header first (for proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Fall back to client host
        if request.client:
            return request.client.host

        return None
