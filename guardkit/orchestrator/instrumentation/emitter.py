"""EventEmitter protocol and pluggable backend implementations.

This module provides the core abstraction for event delivery in the AutoBuild
instrumentation pipeline. The EventEmitter protocol is injected into all
AutoBuild components that produce telemetry events.

Architecture:
    EventEmitter (Protocol)
    ├── JSONLFileBackend   (always-on local persistence)
    ├── NATSBackend        (optional async NATS publish)
    ├── CompositeBackend   (fan-out to multiple backends)
    └── NullEmitter        (no-op / in-memory capture for tests)

Design Decisions:
    - All emit() calls are async and non-blocking to avoid blocking the
      LLM call critical path.
    - JSONLFileBackend uses an asyncio.Lock for thread-safe writes from
      concurrent coroutines.
    - NATSBackend degrades gracefully: connection failures are logged as
      warnings, never raised to callers.
    - CompositeBackend tolerates individual backend failures: if one backend
      fails, the others still receive the event.

Example:
    >>> from guardkit.orchestrator.instrumentation.emitter import (
    ...     CompositeBackend, JSONLFileBackend, NullEmitter,
    ... )
    >>> from pathlib import Path
    >>> jsonl = JSONLFileBackend(events_dir=Path(".guardkit/autobuild/TASK-001"))
    >>> composite = CompositeBackend(backends=[jsonl])
    >>> # In async context:
    >>> # await composite.emit(event)
    >>> # await composite.flush()
    >>> # await composite.close()
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, List, Optional, Protocol, runtime_checkable

from guardkit.orchestrator.instrumentation.schemas import BaseEvent

logger = logging.getLogger(__name__)


# ============================================================================
# EventEmitter Protocol
# ============================================================================


@runtime_checkable
class EventEmitter(Protocol):
    """Protocol defining the event emission interface.

    All AutoBuild components that produce telemetry events depend on this
    protocol. Implementations MUST be async and non-blocking.

    Methods:
        emit: Deliver an event to the backend.
        flush: Ensure all buffered events are persisted.
        close: Flush and release any held resources.
    """

    async def emit(self, event: BaseEvent) -> None:
        """Emit an event to the backend.

        This method MUST be async and non-blocking. It should not block
        the LLM call critical path.

        Args:
            event: A BaseEvent subclass instance to emit.
        """
        ...

    async def flush(self) -> None:
        """Flush any buffered events to their destination.

        Ensures all previously emitted events have been persisted or
        transmitted.
        """
        ...

    async def close(self) -> None:
        """Close the emitter, flushing remaining events and releasing resources.

        After close() is called, the emitter should not be used again.
        """
        ...


# ============================================================================
# NullEmitter (Testing)
# ============================================================================


class NullEmitter:
    """No-op emitter for unit tests.

    Optionally captures events in memory for assertion in test code.

    Args:
        capture: If True, store emitted events in the ``events`` list.
            Defaults to False (pure no-op).

    Attributes:
        events: List of captured events (empty if capture=False).

    Example:
        >>> emitter = NullEmitter(capture=True)
        >>> # await emitter.emit(some_event)
        >>> # assert len(emitter.events) == 1
    """

    def __init__(self, capture: bool = False) -> None:
        self._capture = capture
        self.events: List[BaseEvent] = []

    async def emit(self, event: BaseEvent) -> None:
        """Emit an event, optionally capturing it in memory.

        Args:
            event: The event to emit.
        """
        if self._capture:
            self.events.append(event)

    async def flush(self) -> None:
        """No-op flush."""

    async def close(self) -> None:
        """No-op close."""


# ============================================================================
# JSONLFileBackend (Always-On Local Persistence)
# ============================================================================


class JSONLFileBackend:
    """Append-only JSONL file backend for event persistence.

    Writes each event as a valid JSON object on its own line to
    ``{events_dir}/events.jsonl``. Creates parent directories if needed.

    Thread-safety is ensured via an asyncio.Lock so concurrent coroutines
    can safely emit events without corrupting the file.

    Args:
        events_dir: Directory where ``events.jsonl`` will be written.
            Parent directories are created automatically on first write.

    Example:
        >>> backend = JSONLFileBackend(events_dir=Path(".guardkit/autobuild/TASK-001"))
        >>> # await backend.emit(event)
        >>> # await backend.flush()
    """

    def __init__(self, events_dir: Path) -> None:
        self._events_dir = events_dir
        self._events_file = events_dir / "events.jsonl"
        self._lock = asyncio.Lock()
        self._buffer: List[str] = []
        self._dir_created = False

    def _ensure_dir(self) -> None:
        """Create parent directories if they don't exist yet."""
        if not self._dir_created:
            self._events_dir.mkdir(parents=True, exist_ok=True)
            self._dir_created = True

    async def emit(self, event: BaseEvent) -> None:
        """Serialize and buffer an event for writing.

        The event is serialized to a JSON string and added to an internal
        buffer. The buffer is flushed to disk on each emit to ensure
        durability, while the lock ensures thread-safe writes.

        Args:
            event: A BaseEvent subclass to persist.
        """
        line = json.dumps(event.model_dump(), separators=(",", ":"))
        async with self._lock:
            self._ensure_dir()
            with self._events_file.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    async def flush(self) -> None:
        """Ensure all buffered events are written to disk.

        Since emit() writes directly under a lock, flush() is a
        synchronization point that ensures any in-flight write has
        completed.
        """
        async with self._lock:
            # All writes happen in emit() under the lock,
            # so acquiring the lock here ensures completion.
            pass

    async def close(self) -> None:
        """Flush remaining events and release resources."""
        await self.flush()


# ============================================================================
# NATSBackend (Optional Async Publish)
# ============================================================================


class NATSBackend:
    """Optional NATS publish backend for event distribution.

    Publishes each event as a JSON payload to a configurable NATS subject.
    Handles connection failures gracefully: logs a warning and continues
    without raising to the caller.

    Args:
        client: An async NATS client with a ``publish(subject, payload)``
            method. This is intentionally duck-typed to avoid a hard
            dependency on the ``nats-py`` package.
        subject: The NATS subject to publish events to.

    Example:
        >>> # nats_client = await nats.connect("nats://localhost:4222")
        >>> # backend = NATSBackend(client=nats_client, subject="events.autobuild")
        >>> # await backend.emit(event)
    """

    def __init__(self, client: Any, subject: str) -> None:
        self._client = client
        self._subject = subject

    async def emit(self, event: BaseEvent) -> None:
        """Publish an event to NATS.

        If the publish fails for any reason (connection error, timeout, etc.),
        the error is logged as a warning and the method returns normally.
        This ensures NATS failures never block the calling code.

        Args:
            event: A BaseEvent subclass to publish.
        """
        try:
            payload = json.dumps(event.model_dump(), separators=(",", ":")).encode(
                "utf-8"
            )
            await self._client.publish(self._subject, payload)
        except Exception as exc:
            logger.warning(
                "NATS publish failed for subject '%s': %s. "
                "Event will not be delivered via NATS. "
                "Local JSONL persistence (if configured via CompositeBackend) "
                "is unaffected.",
                self._subject,
                exc,
            )

    async def flush(self) -> None:
        """Flush the NATS client (no-op if client doesn't support flush)."""
        try:
            if hasattr(self._client, "flush"):
                await self._client.flush()
        except Exception as exc:
            logger.warning("NATS flush failed: %s", exc)

    async def close(self) -> None:
        """Close the NATS connection gracefully."""
        try:
            if hasattr(self._client, "close"):
                await self._client.close()
        except Exception as exc:
            logger.warning("NATS close failed: %s", exc)


# ============================================================================
# CompositeBackend (Fan-Out)
# ============================================================================


class CompositeBackend:
    """Fan-out backend that emits to ALL registered backends.

    If one backend fails during emit/flush/close, the others continue
    to receive events. This ensures that JSONL (always registered) provides
    guaranteed local persistence even if optional backends (e.g., NATS) fail.

    Args:
        backends: List of backends to fan-out to. JSONL should always be
            included for guaranteed persistence.

    Example:
        >>> jsonl = JSONLFileBackend(events_dir=Path("..."))
        >>> nats = NATSBackend(client=..., subject="events.autobuild")
        >>> composite = CompositeBackend(backends=[jsonl, nats])
        >>> # await composite.emit(event)  # fans out to both
    """

    def __init__(self, backends: List[Any]) -> None:
        self._backends = list(backends)

    async def emit(self, event: BaseEvent) -> None:
        """Emit an event to all registered backends.

        Each backend is called independently. If one backend raises an
        exception, it is logged as a warning and the remaining backends
        still receive the event.

        Args:
            event: A BaseEvent subclass to emit.
        """
        for backend in self._backends:
            try:
                await backend.emit(event)
            except Exception as exc:
                logger.warning(
                    "Backend %s failed during emit: %s. "
                    "Other backends are unaffected.",
                    type(backend).__name__,
                    exc,
                )

    async def flush(self) -> None:
        """Flush all registered backends.

        Each backend is flushed independently; failures in one do not
        prevent flushing of others.
        """
        for backend in self._backends:
            try:
                await backend.flush()
            except Exception as exc:
                logger.warning(
                    "Backend %s failed during flush: %s",
                    type(backend).__name__,
                    exc,
                )

    async def close(self) -> None:
        """Close all registered backends.

        Each backend is closed independently; failures in one do not
        prevent closing of others.
        """
        for backend in self._backends:
            try:
                await backend.close()
            except Exception as exc:
                logger.warning(
                    "Backend %s failed during close: %s",
                    type(backend).__name__,
                    exc,
                )


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "EventEmitter",
    "NullEmitter",
    "JSONLFileBackend",
    "NATSBackend",
    "CompositeBackend",
]
