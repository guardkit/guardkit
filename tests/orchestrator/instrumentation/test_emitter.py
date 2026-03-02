"""Tests for AutoBuild instrumentation EventEmitter protocol and backends.

Covers:
- EventEmitter protocol definition (emit/flush/close)
- JSONLFileBackend (append-only JSONL, thread-safe, directory creation)
- NATSBackend (async publish, connection failure, graceful degradation)
- CompositeBackend (fan-out, individual failure tolerance, guaranteed JSONL)
- NullEmitter (no-op / in-memory capture for test assertions)
- Seam test for EVENT_SCHEMAS contract from TASK-INST-001
- Non-blocking emission
- Thread-safe concurrent writes
"""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.instrumentation.schemas import (
    BaseEvent,
    LLMCallEvent,
    TaskStartedEvent,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def base_event_fields() -> dict:
    """Minimal valid fields for creating a BaseEvent subclass."""
    return {
        "run_id": "run-test-001",
        "task_id": "TASK-001",
        "agent_role": "player",
        "attempt": 1,
        "timestamp": "2026-03-02T12:00:00Z",
    }


@pytest.fixture
def sample_llm_event(base_event_fields: dict) -> LLMCallEvent:
    """Create a sample LLMCallEvent for testing."""
    return LLMCallEvent(
        **base_event_fields,
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=50,
        latency_ms=1500.0,
        prompt_profile="digest_only",
        status="ok",
    )


@pytest.fixture
def sample_task_started(base_event_fields: dict) -> TaskStartedEvent:
    """Create a sample TaskStartedEvent for testing."""
    return TaskStartedEvent(**base_event_fields)


@pytest.fixture
def tmp_events_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for JSONL event files."""
    return tmp_path / ".guardkit" / "autobuild" / "TASK-001"


# ============================================================================
# EventEmitter Protocol Tests
# ============================================================================


class TestEventEmitterProtocol:
    """Tests for the EventEmitter protocol definition."""

    def test_protocol_has_emit_method(self) -> None:
        """EventEmitter protocol defines an async emit() method."""
        from guardkit.orchestrator.instrumentation.emitter import EventEmitter

        assert hasattr(EventEmitter, "emit")

    def test_protocol_has_flush_method(self) -> None:
        """EventEmitter protocol defines an async flush() method."""
        from guardkit.orchestrator.instrumentation.emitter import EventEmitter

        assert hasattr(EventEmitter, "flush")

    def test_protocol_has_close_method(self) -> None:
        """EventEmitter protocol defines an async close() method."""
        from guardkit.orchestrator.instrumentation.emitter import EventEmitter

        assert hasattr(EventEmitter, "close")

    def test_null_emitter_satisfies_protocol(self) -> None:
        """NullEmitter implements the EventEmitter protocol."""
        from guardkit.orchestrator.instrumentation.emitter import (
            EventEmitter,
            NullEmitter,
        )

        emitter = NullEmitter()
        # Structural typing check - NullEmitter has all required methods
        assert hasattr(emitter, "emit")
        assert hasattr(emitter, "flush")
        assert hasattr(emitter, "close")

    def test_jsonl_backend_satisfies_protocol(self, tmp_events_dir: Path) -> None:
        """JSONLFileBackend implements the EventEmitter protocol."""
        from guardkit.orchestrator.instrumentation.emitter import (
            JSONLFileBackend,
        )

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        assert hasattr(backend, "emit")
        assert hasattr(backend, "flush")
        assert hasattr(backend, "close")

    def test_composite_backend_satisfies_protocol(
        self, tmp_events_dir: Path
    ) -> None:
        """CompositeBackend implements the EventEmitter protocol."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
            JSONLFileBackend,
        )

        jsonl = JSONLFileBackend(events_dir=tmp_events_dir)
        composite = CompositeBackend(backends=[jsonl])
        assert hasattr(composite, "emit")
        assert hasattr(composite, "flush")
        assert hasattr(composite, "close")


# ============================================================================
# NullEmitter Tests
# ============================================================================


class TestNullEmitter:
    """Tests for NullEmitter (testing backend)."""

    async def test_emit_no_capture(self, sample_llm_event: LLMCallEvent) -> None:
        """NullEmitter with capture=False does not store events."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter(capture=False)
        await emitter.emit(sample_llm_event)
        assert emitter.events == []

    async def test_emit_with_capture(self, sample_llm_event: LLMCallEvent) -> None:
        """NullEmitter with capture=True stores events in memory."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter(capture=True)
        await emitter.emit(sample_llm_event)
        assert len(emitter.events) == 1
        assert emitter.events[0] is sample_llm_event

    async def test_emit_multiple_events(
        self,
        sample_llm_event: LLMCallEvent,
        sample_task_started: TaskStartedEvent,
    ) -> None:
        """NullEmitter captures multiple events in order."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter(capture=True)
        await emitter.emit(sample_llm_event)
        await emitter.emit(sample_task_started)
        assert len(emitter.events) == 2
        assert isinstance(emitter.events[0], LLMCallEvent)
        assert isinstance(emitter.events[1], TaskStartedEvent)

    async def test_flush_is_noop(self) -> None:
        """NullEmitter.flush() completes without error."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter()
        await emitter.flush()  # Should not raise

    async def test_close_is_noop(self) -> None:
        """NullEmitter.close() completes without error."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter()
        await emitter.close()  # Should not raise

    async def test_default_no_capture(self) -> None:
        """NullEmitter defaults to capture=False."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter()
        assert emitter.events == []


# ============================================================================
# JSONLFileBackend Tests
# ============================================================================


class TestJSONLFileBackend:
    """Tests for JSONLFileBackend (always-on local persistence)."""

    async def test_creates_parent_directories(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """JSONLFileBackend creates parent directories if they don't exist."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        assert not tmp_events_dir.exists()
        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        await backend.emit(sample_llm_event)
        await backend.flush()
        assert tmp_events_dir.exists()

    async def test_writes_valid_jsonl(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """Each emitted event is a valid JSON object on its own line."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        await backend.emit(sample_llm_event)
        await backend.flush()

        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()

        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["run_id"] == "run-test-001"
        assert data["provider"] == "anthropic"
        assert data["schema_version"] == "1.0.0"

    async def test_append_only(
        self,
        tmp_events_dir: Path,
        sample_llm_event: LLMCallEvent,
        sample_task_started: TaskStartedEvent,
    ) -> None:
        """Multiple events are appended, not overwritten."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        await backend.emit(sample_llm_event)
        await backend.emit(sample_task_started)
        await backend.flush()

        events_file = tmp_events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 2
        # First line is LLMCallEvent
        data1 = json.loads(lines[0])
        assert "provider" in data1
        # Second line is TaskStartedEvent
        data2 = json.loads(lines[1])
        assert data2["task_id"] == "TASK-001"

    async def test_each_line_is_valid_json(
        self,
        tmp_events_dir: Path,
        sample_llm_event: LLMCallEvent,
        sample_task_started: TaskStartedEvent,
    ) -> None:
        """Each line in the JSONL file is independently valid JSON."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        await backend.emit(sample_llm_event)
        await backend.emit(sample_task_started)
        await backend.flush()

        events_file = tmp_events_dir / "events.jsonl"
        for line in events_file.read_text().strip().split("\n"):
            parsed = json.loads(line)
            assert isinstance(parsed, dict)

    async def test_flush_writes_buffered_events(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """flush() ensures all buffered events are written to disk."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        await backend.emit(sample_llm_event)
        await backend.flush()

        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()
        content = events_file.read_text().strip()
        assert len(content) > 0

    async def test_close_flushes_and_releases(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """close() flushes remaining events and releases resources."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        await backend.emit(sample_llm_event)
        await backend.close()

        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1

    async def test_thread_safe_concurrent_writes(
        self, tmp_events_dir: Path, base_event_fields: dict
    ) -> None:
        """Concurrent emit() calls from multiple coroutines are thread-safe."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        events = [
            TaskStartedEvent(
                **{**base_event_fields, "run_id": f"run-{i}"}
            )
            for i in range(20)
        ]

        # Fire all emits concurrently
        await asyncio.gather(*(backend.emit(e) for e in events))
        await backend.flush()

        events_file = tmp_events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 20
        # Each line must be valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert "run_id" in parsed


# ============================================================================
# NATSBackend Tests
# ============================================================================


class TestNATSBackend:
    """Tests for NATSBackend (optional async NATS publish)."""

    async def test_publish_event(
        self, sample_llm_event: LLMCallEvent
    ) -> None:
        """NATSBackend publishes event to configured subject."""
        from guardkit.orchestrator.instrumentation.emitter import NATSBackend

        mock_client = AsyncMock()
        backend = NATSBackend(client=mock_client, subject="events.autobuild")
        await backend.emit(sample_llm_event)

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "events.autobuild"
        # Payload should be valid JSON
        payload = call_args[0][1]
        data = json.loads(payload)
        assert data["run_id"] == "run-test-001"

    async def test_connection_failure_logs_warning(
        self, sample_llm_event: LLMCallEvent, caplog: pytest.LogCaptureFixture
    ) -> None:
        """NATSBackend logs warning and continues if NATS is unavailable."""
        from guardkit.orchestrator.instrumentation.emitter import NATSBackend

        mock_client = AsyncMock()
        mock_client.publish.side_effect = ConnectionError("NATS unavailable")
        backend = NATSBackend(client=mock_client, subject="events.autobuild")

        with caplog.at_level(logging.WARNING):
            await backend.emit(sample_llm_event)

        # Should not raise, just log warning
        assert any("NATS" in record.message or "unavailable" in record.message
                    for record in caplog.records)

    async def test_connection_loss_mid_run(
        self,
        sample_llm_event: LLMCallEvent,
        sample_task_started: TaskStartedEvent,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Mid-run NATS connection loss: logs warning, does not drop events."""
        from guardkit.orchestrator.instrumentation.emitter import NATSBackend

        mock_client = AsyncMock()
        # First call succeeds, second fails
        mock_client.publish.side_effect = [
            None,
            ConnectionError("Connection lost"),
        ]
        backend = NATSBackend(client=mock_client, subject="events.autobuild")

        await backend.emit(sample_llm_event)  # Succeeds
        with caplog.at_level(logging.WARNING):
            await backend.emit(sample_task_started)  # Fails gracefully

        assert mock_client.publish.call_count == 2

    async def test_flush_is_safe(self) -> None:
        """NATSBackend.flush() completes without error."""
        from guardkit.orchestrator.instrumentation.emitter import NATSBackend

        mock_client = AsyncMock()
        backend = NATSBackend(client=mock_client, subject="events.autobuild")
        await backend.flush()  # Should not raise

    async def test_close_is_safe(self) -> None:
        """NATSBackend.close() completes without error."""
        from guardkit.orchestrator.instrumentation.emitter import NATSBackend

        mock_client = AsyncMock()
        backend = NATSBackend(client=mock_client, subject="events.autobuild")
        await backend.close()  # Should not raise

    async def test_graceful_degradation_on_exception(
        self, sample_llm_event: LLMCallEvent, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Any exception during publish is handled gracefully."""
        from guardkit.orchestrator.instrumentation.emitter import NATSBackend

        mock_client = AsyncMock()
        mock_client.publish.side_effect = RuntimeError("Unexpected error")
        backend = NATSBackend(client=mock_client, subject="events.autobuild")

        with caplog.at_level(logging.WARNING):
            await backend.emit(sample_llm_event)
        # Should not raise


# ============================================================================
# CompositeBackend Tests
# ============================================================================


class TestCompositeBackend:
    """Tests for CompositeBackend (fan-out to all registered backends)."""

    async def test_fans_out_to_all_backends(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """CompositeBackend emits to ALL registered backends."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
            JSONLFileBackend,
            NullEmitter,
        )

        jsonl = JSONLFileBackend(events_dir=tmp_events_dir)
        null = NullEmitter(capture=True)
        composite = CompositeBackend(backends=[jsonl, null])

        await composite.emit(sample_llm_event)
        await composite.flush()

        # Both backends received the event
        assert len(null.events) == 1
        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()

    async def test_tolerates_individual_backend_failure(
        self,
        tmp_events_dir: Path,
        sample_llm_event: LLMCallEvent,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """If one backend fails, others continue to receive events."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
            JSONLFileBackend,
            NullEmitter,
        )

        jsonl = JSONLFileBackend(events_dir=tmp_events_dir)
        null = NullEmitter(capture=True)

        # Create a failing backend
        failing_backend = AsyncMock()
        failing_backend.emit = AsyncMock(side_effect=RuntimeError("Backend failed"))
        failing_backend.flush = AsyncMock()
        failing_backend.close = AsyncMock()

        composite = CompositeBackend(backends=[failing_backend, jsonl, null])

        with caplog.at_level(logging.WARNING):
            await composite.emit(sample_llm_event)
        await composite.flush()

        # Non-failing backends still received the event
        assert len(null.events) == 1
        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()

    async def test_jsonl_always_registered(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """JSONL backend is guaranteed local persistence."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
            JSONLFileBackend,
        )

        jsonl = JSONLFileBackend(events_dir=tmp_events_dir)
        composite = CompositeBackend(backends=[jsonl])

        await composite.emit(sample_llm_event)
        await composite.flush()

        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1

    async def test_flush_calls_all_backends(
        self, tmp_events_dir: Path
    ) -> None:
        """CompositeBackend.flush() calls flush on all backends."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
            NullEmitter,
        )

        b1 = AsyncMock()
        b1.emit = AsyncMock()
        b1.flush = AsyncMock()
        b1.close = AsyncMock()
        b2 = AsyncMock()
        b2.emit = AsyncMock()
        b2.flush = AsyncMock()
        b2.close = AsyncMock()
        composite = CompositeBackend(backends=[b1, b2])
        await composite.flush()

        b1.flush.assert_called_once()
        b2.flush.assert_called_once()

    async def test_close_calls_all_backends(
        self, tmp_events_dir: Path
    ) -> None:
        """CompositeBackend.close() calls close on all backends."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
        )

        b1 = AsyncMock()
        b1.emit = AsyncMock()
        b1.flush = AsyncMock()
        b1.close = AsyncMock()
        b2 = AsyncMock()
        b2.emit = AsyncMock()
        b2.flush = AsyncMock()
        b2.close = AsyncMock()
        composite = CompositeBackend(backends=[b1, b2])
        await composite.close()

        b1.close.assert_called_once()
        b2.close.assert_called_once()

    async def test_nats_failure_falls_back_to_jsonl(
        self,
        tmp_events_dir: Path,
        sample_llm_event: LLMCallEvent,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """NATS connection loss mid-run: JSONL still receives events."""
        from guardkit.orchestrator.instrumentation.emitter import (
            CompositeBackend,
            JSONLFileBackend,
            NATSBackend,
        )

        jsonl = JSONLFileBackend(events_dir=tmp_events_dir)
        mock_nats_client = AsyncMock()
        mock_nats_client.publish.side_effect = ConnectionError("NATS down")
        nats = NATSBackend(client=mock_nats_client, subject="events.autobuild")

        composite = CompositeBackend(backends=[jsonl, nats])

        with caplog.at_level(logging.WARNING):
            await composite.emit(sample_llm_event)
        await composite.flush()

        # JSONL still has the event despite NATS failure
        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["run_id"] == "run-test-001"


# ============================================================================
# Non-Blocking Emission Tests
# ============================================================================


class TestNonBlockingEmission:
    """Tests that event emission does not block the calling code."""

    async def test_emit_is_async(self, sample_llm_event: LLMCallEvent) -> None:
        """emit() is an async method and does not block."""
        from guardkit.orchestrator.instrumentation.emitter import NullEmitter

        emitter = NullEmitter(capture=True)
        # emit should be a coroutine
        coro = emitter.emit(sample_llm_event)
        assert asyncio.iscoroutine(coro)
        await coro

    async def test_emit_returns_quickly(
        self, tmp_events_dir: Path, sample_llm_event: LLMCallEvent
    ) -> None:
        """emit() returns without waiting for I/O completion."""
        from guardkit.orchestrator.instrumentation.emitter import JSONLFileBackend

        backend = JSONLFileBackend(events_dir=tmp_events_dir)
        # Should not block - just queues or writes quickly
        await backend.emit(sample_llm_event)
        await backend.flush()

        events_file = tmp_events_dir / "events.jsonl"
        assert events_file.exists()


# ============================================================================
# Seam Test: EVENT_SCHEMAS Contract
# ============================================================================


@pytest.mark.seam
class TestEventSchemasSeam:
    """Seam test: verify EVENT_SCHEMAS contract from TASK-INST-001."""

    def test_event_schemas_serialization(self) -> None:
        """Verify event models produce valid JSON for backend consumption.

        Contract: All event objects are Pydantic BaseEvent subclasses with model_dump()
        Producer: TASK-INST-001
        """
        event = LLMCallEvent(
            run_id="test-run",
            task_id="TASK-001",
            agent_role="player",
            attempt=1,
            timestamp="2026-03-01T00:00:00Z",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1500.0,
            prompt_profile="digest_only",
            status="ok",
        )
        data = event.model_dump()
        assert isinstance(data, dict)
        assert "run_id" in data
        assert "schema_version" in data

    def test_event_json_roundtrip_for_jsonl_backend(self) -> None:
        """Event model_dump() output can be serialized to JSON for JSONL files."""
        event = TaskStartedEvent(
            run_id="test-run",
            task_id="TASK-001",
            agent_role="player",
            attempt=1,
            timestamp="2026-03-01T00:00:00Z",
        )
        data = event.model_dump()
        json_str = json.dumps(data)
        roundtripped = json.loads(json_str)
        assert roundtripped["run_id"] == "test-run"
        assert roundtripped["schema_version"] == "1.0.0"
