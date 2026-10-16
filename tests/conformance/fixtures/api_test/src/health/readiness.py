"""Readiness state management.

Provides a lightweight module-level flag to track whether the service
is ready to accept requests. This is used by the /ready endpoint to
return 200 when ready and 503 when not ready.

This module is intentionally simple and does not depend on databases,
external services, or complex state machines. It is designed for
Kubernetes readiness probes that require a lightweight, synchronous check.
"""

from __future__ import annotations

_ready: bool = True


def is_ready() -> bool:
    """Return whether the service is ready to accept requests."""
    return _ready


def set_ready() -> None:
    """Mark the service as ready."""
    global _ready
    _ready = True


def set_not_ready() -> None:
    """Mark the service as not ready."""
    global _ready
    _ready = False
