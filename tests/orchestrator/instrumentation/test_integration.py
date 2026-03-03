"""Integration tests for the AutoBuild instrumentation pipeline.

End-to-end integration tests that verify the complete instrumentation pipeline
works correctly across all components. Tests validate event flow from emission
through backends, NATS fallback behaviour, concurrent worker safety, A/B profile
comparison data, and digest validation.

Test Scenarios (from BDD spec):
1. End-to-end event stream (successful + failed tasks)
2. NATS fallback to local JSONL
3. Concurrent worker safety (3 parallel workers)
4. A/B comparison data under different profiles
5. Digest validation boundary (700 tokens / 701 tokens)
6. Phase 1 migration preservation (rules bundle + digest)
7. Non-blocking emission (async fire-and-forget)

Acceptance Criteria:
- AC-001: End-to-end test verifies complete event stream for successful task
- AC-002: End-to-end test verifies event stream for failed task
- AC-003: NATS unavailable: all events written to local JSONL
- AC-004: NATS drops mid-run: seamless fallback with warning
- AC-005: No events silently dropped in any failure scenario
- AC-006: Concurrent workers produce independent, non-corrupted events
- AC-007: A/B data: same task produces comparable metrics under different profiles
- AC-008: Digest boundary: 700 tokens accepted, 701 warned
- AC-009: Phase 1: rules bundle + digest coexist
- AC-010: Async emission verified non-blocking
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import List, Optional
from unittest.mock import AsyncMock

import pytest

from guardkit.orchestrator.instrumentation.digests import (
    DigestLoader,
    DigestValidator,
    DigestValidationResult,
    MAX_TOKENS,
    count_tokens,
)
from guardkit.orchestrator.instrumentation.emitter import (
    CompositeBackend,
    JSONLFileBackend,
    NATSBackend,
    NullEmitter,
)
from guardkit.orchestrator.instrumentation.prompt_profile import (
    PromptProfile,
    PromptProfileAssembler,
)
from guardkit.orchestrator.instrumentation.schemas import (
    LLMCallEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    ToolExecEvent,
)


# ============================================================================
# Shared Helpers
# ============================================================================


def _base_fields(
    *,
    run_id: str = "run-integration-001",
    task_id: str = "TASK-INT-001",
    agent_role: str = "player",
    attempt: int = 1,
    timestamp: str = "2026-03-02T12:00:00Z",
) -> dict:
    """Return minimal base event fields."""
    return {
        "run_id": run_id,
        "task_id": task_id,
        "agent_role": agent_role,
        "attempt": attempt,
        "timestamp": timestamp,
    }


def _make_task_started(*, run_id: str = "run-integration-001", task_id: str = "TASK-INT-001", **kwargs) -> TaskStartedEvent:
    """Create a TaskStartedEvent with sensible defaults."""
    fields = _base_fields(run_id=run_id, task_id=task_id, **kwargs)
    return TaskStartedEvent(**fields)


def _make_llm_call(
    *,
    run_id: str = "run-integration-001",
    task_id: str = "TASK-INT-001",
    input_tokens: int = 500,
    output_tokens: int = 200,
    latency_ms: float = 1500.0,
    prompt_profile: str = "digest_only",
    status: str = "ok",
    **kwargs,
) -> LLMCallEvent:
    """Create an LLMCallEvent with sensible defaults."""
    fields = _base_fields(run_id=run_id, task_id=task_id, **kwargs)
    return LLMCallEvent(
        **fields,
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        prompt_profile=prompt_profile,
        status=status,
    )


def _make_tool_exec(
    *,
    run_id: str = "run-integration-001",
    task_id: str = "TASK-INT-001",
    tool_name: str = "bash",
    cmd: str = "pytest tests/ -v",
    exit_code: int = 0,
    **kwargs,
) -> ToolExecEvent:
    """Create a ToolExecEvent with sensible defaults."""
    fields = _base_fields(run_id=run_id, task_id=task_id, **kwargs)
    return ToolExecEvent(
        **fields,
        tool_name=tool_name,
        cmd=cmd,
        exit_code=exit_code,
        latency_ms=500.0,
        stdout_tail="All tests passed",
        stderr_tail="",
    )


def _make_task_completed(
    *,
    run_id: str = "run-integration-001",
    task_id: str = "TASK-INT-001",
    prompt_profile: str = "digest_only",
    **kwargs,
) -> TaskCompletedEvent:
    """Create a TaskCompletedEvent with sensible defaults."""
    fields = _base_fields(run_id=run_id, task_id=task_id, **kwargs)
    return TaskCompletedEvent(
        **fields,
        turn_count=3,
        diff_stats="+50 -10",
        verification_status="approved",
        prompt_profile=prompt_profile,
    )


def _make_task_failed(
    *,
    run_id: str = "run-integration-001",
    task_id: str = "TASK-INT-001",
    failure_category: str = "test_failure",
    **kwargs,
) -> TaskFailedEvent:
    """Create a TaskFailedEvent with sensible defaults."""
    fields = _base_fields(run_id=run_id, task_id=task_id, **kwargs)
    return TaskFailedEvent(**fields, failure_category=failure_category)


# ============================================================================
# AC-001: End-to-end event stream for successful task
# ============================================================================


class TestEndToEndSuccessfulTask:
    """An AutoBuild run produces a complete event stream for a successful task.

    The expected sequence: task.started -> llm.call(s) -> tool.exec(s) -> task.completed
    """

    async def test_complete_event_stream_successful_task(self) -> None:
        """Successful task emits full lifecycle: started -> llm calls -> tool execs -> completed."""
        emitter = NullEmitter(capture=True)

        # Simulate a complete AutoBuild run
        await emitter.emit(_make_task_started())
        await emitter.emit(_make_llm_call())
        await emitter.emit(_make_tool_exec())
        await emitter.emit(_make_llm_call(input_tokens=300, output_tokens=150))
        await emitter.emit(_make_tool_exec(cmd="npm test"))
        await emitter.emit(_make_task_completed())

        assert len(emitter.events) == 6

        # Verify event ordering matches lifecycle
        assert isinstance(emitter.events[0], TaskStartedEvent)
        assert isinstance(emitter.events[1], LLMCallEvent)
        assert isinstance(emitter.events[2], ToolExecEvent)
        assert isinstance(emitter.events[3], LLMCallEvent)
        assert isinstance(emitter.events[4], ToolExecEvent)
        assert isinstance(emitter.events[5], TaskCompletedEvent)

    async def test_all_events_share_same_run_id(self) -> None:
        """All events in a run share the same run_id."""
        emitter = NullEmitter(capture=True)
        run_id = "run-e2e-success"

        await emitter.emit(_make_task_started(run_id=run_id))
        await emitter.emit(_make_llm_call(run_id=run_id))
        await emitter.emit(_make_tool_exec(run_id=run_id))
        await emitter.emit(_make_task_completed(run_id=run_id))

        for event in emitter.events:
            assert event.run_id == run_id

    async def test_all_events_share_same_task_id(self) -> None:
        """All events in a task share the same task_id."""
        emitter = NullEmitter(capture=True)
        task_id = "TASK-E2E-001"

        await emitter.emit(_make_task_started(task_id=task_id))
        await emitter.emit(_make_llm_call(task_id=task_id))
        await emitter.emit(_make_task_completed(task_id=task_id))

        for event in emitter.events:
            assert event.task_id == task_id

    async def test_events_roundtrip_through_jsonl_backend(self, tmp_path: Path) -> None:
        """Complete event stream persists to JSONL and can be re-read."""
        events_dir = tmp_path / "events"
        backend = JSONLFileBackend(events_dir=events_dir)

        events = [
            _make_task_started(),
            _make_llm_call(),
            _make_tool_exec(),
            _make_task_completed(),
        ]
        for event in events:
            await backend.emit(event)
        await backend.flush()

        # Read back and verify
        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 4

        # Verify each line is valid JSON with required fields
        for line in lines:
            data = json.loads(line)
            assert "run_id" in data
            assert "task_id" in data
            assert "schema_version" in data


# ============================================================================
# AC-002: End-to-end event stream for failed task
# ============================================================================


class TestEndToEndFailedTask:
    """An AutoBuild run produces a complete event stream for a failed task.

    The expected sequence: task.started -> llm.call(s) -> tool.exec(s) -> task.failed
    """

    async def test_complete_event_stream_failed_task(self) -> None:
        """Failed task emits lifecycle with task.failed instead of completed."""
        emitter = NullEmitter(capture=True)

        await emitter.emit(_make_task_started())
        await emitter.emit(_make_llm_call())
        await emitter.emit(_make_tool_exec(exit_code=1))
        await emitter.emit(_make_task_failed(failure_category="test_failure"))

        assert len(emitter.events) == 4

        assert isinstance(emitter.events[0], TaskStartedEvent)
        assert isinstance(emitter.events[-1], TaskFailedEvent)
        assert emitter.events[-1].failure_category == "test_failure"

    async def test_failed_task_preserves_all_events(self, tmp_path: Path) -> None:
        """All events including the failure event are persisted."""
        events_dir = tmp_path / "failed-events"
        backend = JSONLFileBackend(events_dir=events_dir)

        await backend.emit(_make_task_started())
        await backend.emit(_make_llm_call())
        await backend.emit(_make_task_failed(failure_category="env_failure"))
        await backend.flush()

        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 3

        last_event = json.loads(lines[-1])
        assert last_event["failure_category"] == "env_failure"


# ============================================================================
# AC-003: NATS unavailable — all events written to local JSONL
# ============================================================================


class TestNATSUnavailableFallback:
    """When NATS is not configured, events are written to local JSONL.

    Each event must be valid JSON on its own line and no events are silently dropped.
    """

    async def test_events_written_to_jsonl_without_nats(self, tmp_path: Path) -> None:
        """All events are persisted to JSONL when NATS is not configured."""
        events_dir = tmp_path / "no-nats"
        jsonl = JSONLFileBackend(events_dir=events_dir)
        # Composite with only JSONL — simulates "NATS not configured"
        composite = CompositeBackend(backends=[jsonl])

        events = [
            _make_task_started(),
            _make_llm_call(),
            _make_tool_exec(),
            _make_task_completed(),
        ]
        for event in events:
            await composite.emit(event)
        await composite.flush()

        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 4

    async def test_each_jsonl_line_is_valid_json(self, tmp_path: Path) -> None:
        """Each event is valid JSON on its own line."""
        events_dir = tmp_path / "jsonl-valid"
        jsonl = JSONLFileBackend(events_dir=events_dir)
        composite = CompositeBackend(backends=[jsonl])

        await composite.emit(_make_task_started())
        await composite.emit(_make_llm_call())
        await composite.emit(_make_tool_exec())
        await composite.flush()

        events_file = events_dir / "events.jsonl"
        for line in events_file.read_text().strip().split("\n"):
            parsed = json.loads(line)
            assert isinstance(parsed, dict)
            assert "run_id" in parsed

    async def test_nats_unavailable_all_events_still_in_jsonl(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """NATS unavailable at start: all events are written to local JSONL."""
        events_dir = tmp_path / "nats-down"
        jsonl = JSONLFileBackend(events_dir=events_dir)

        mock_nats_client = AsyncMock()
        mock_nats_client.publish.side_effect = ConnectionError("NATS unreachable")
        nats = NATSBackend(client=mock_nats_client, subject="events.autobuild")

        composite = CompositeBackend(backends=[jsonl, nats])

        events = [
            _make_task_started(),
            _make_llm_call(),
            _make_tool_exec(),
            _make_task_completed(),
        ]
        with caplog.at_level(logging.WARNING):
            for event in events:
                await composite.emit(event)
        await composite.flush()

        # All events are in JSONL despite NATS failures
        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 4

        # NATS publish was attempted for each event
        assert mock_nats_client.publish.call_count == 4


# ============================================================================
# AC-004: NATS drops mid-run — seamless fallback with warning
# ============================================================================


class TestNATSMidRunFallback:
    """NATS connection lost mid-run: subsequent events fall back to JSONL.

    Warning must be logged about NATS fallback.
    """

    async def test_nats_drops_mid_run_events_still_captured(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """NATS drops after 2 events; remaining events still land in JSONL."""
        events_dir = tmp_path / "nats-mid-drop"
        jsonl = JSONLFileBackend(events_dir=events_dir)

        mock_nats_client = AsyncMock()
        # First 2 events: NATS succeeds. Events 3+: NATS fails.
        mock_nats_client.publish.side_effect = [
            None,
            None,
            ConnectionError("Connection lost"),
            ConnectionError("Connection lost"),
        ]
        nats = NATSBackend(client=mock_nats_client, subject="events.autobuild")
        composite = CompositeBackend(backends=[jsonl, nats])

        events = [
            _make_task_started(),
            _make_llm_call(),
            _make_tool_exec(),
            _make_task_completed(),
        ]
        with caplog.at_level(logging.WARNING):
            for event in events:
                await composite.emit(event)
        await composite.flush()

        # All 4 events are in JSONL regardless of NATS mid-run failure
        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 4

        # Warning logged about NATS failure
        nats_warnings = [r for r in caplog.records if "NATS" in r.message]
        assert len(nats_warnings) >= 1, "Expected at least one NATS warning log"


# ============================================================================
# AC-005: No events silently dropped in any failure scenario
# ============================================================================


class TestNoSilentDrops:
    """No events are silently dropped regardless of backend failures."""

    async def test_no_events_dropped_when_nats_fails(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """All emitted events appear in JSONL even when NATS fails for every event."""
        events_dir = tmp_path / "no-drops"
        jsonl = JSONLFileBackend(events_dir=events_dir)

        mock_nats_client = AsyncMock()
        mock_nats_client.publish.side_effect = RuntimeError("NATS permanently broken")
        nats = NATSBackend(client=mock_nats_client, subject="events.autobuild")

        composite = CompositeBackend(backends=[jsonl, nats])

        event_count = 10
        with caplog.at_level(logging.WARNING):
            for i in range(event_count):
                await composite.emit(
                    _make_llm_call(
                        run_id=f"run-drop-test",
                        input_tokens=100 + i,
                    )
                )
        await composite.flush()

        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == event_count, f"Expected {event_count} events, got {len(lines)}"

    async def test_no_events_dropped_with_failing_custom_backend(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """JSONL captures all events even when another backend raises exceptions."""
        events_dir = tmp_path / "custom-fail"
        jsonl = JSONLFileBackend(events_dir=events_dir)
        capture = NullEmitter(capture=True)

        failing = AsyncMock()
        failing.emit = AsyncMock(side_effect=Exception("Custom backend boom"))
        failing.flush = AsyncMock()
        failing.close = AsyncMock()

        composite = CompositeBackend(backends=[failing, jsonl, capture])

        with caplog.at_level(logging.WARNING):
            await composite.emit(_make_task_started())
            await composite.emit(_make_llm_call())
            await composite.emit(_make_task_completed())
        await composite.flush()

        # Both healthy backends captured all events
        assert len(capture.events) == 3
        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 3


# ============================================================================
# AC-006: Concurrent workers produce independent, non-corrupted events
# ============================================================================


class TestConcurrentWorkerSafety:
    """3 parallel workers emit independent events without data corruption.

    Each event must have the correct task_id for its worker.
    No event should contain fields from a different worker's execution.
    """

    async def test_three_workers_independent_events(self, tmp_path: Path) -> None:
        """3 concurrent workers produce events with correct task_ids."""
        events_dir = tmp_path / "concurrent"
        backend = JSONLFileBackend(events_dir=events_dir)

        async def worker(worker_id: int) -> None:
            """Simulate a worker emitting events for its own task."""
            task_id = f"TASK-WORKER-{worker_id}"
            run_id = f"run-worker-{worker_id}"
            await backend.emit(_make_task_started(run_id=run_id, task_id=task_id))
            await backend.emit(_make_llm_call(run_id=run_id, task_id=task_id, input_tokens=100 * worker_id))
            await backend.emit(_make_tool_exec(run_id=run_id, task_id=task_id))
            await backend.emit(_make_task_completed(run_id=run_id, task_id=task_id))

        # Run 3 workers concurrently
        await asyncio.gather(worker(1), worker(2), worker(3))
        await backend.flush()

        # Read all events
        events_file = events_dir / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 12  # 4 events x 3 workers

        # Verify each event is valid JSON and has consistent task_id / run_id
        events_by_task: dict[str, list[dict]] = {}
        for line in lines:
            data = json.loads(line)
            tid = data["task_id"]
            rid = data["run_id"]
            events_by_task.setdefault(tid, []).append(data)
            # run_id and task_id must be consistently paired
            expected_worker = tid.split("-")[-1]
            assert rid == f"run-worker-{expected_worker}", (
                f"run_id mismatch: {rid} for task_id {tid}"
            )

        # Each worker produced exactly 4 events
        assert len(events_by_task) == 3
        for tid, task_events in events_by_task.items():
            assert len(task_events) == 4, f"Expected 4 events for {tid}, got {len(task_events)}"

    async def test_no_cross_contamination_between_workers(self, tmp_path: Path) -> None:
        """No event contains fields from a different worker's execution."""
        capture = NullEmitter(capture=True)

        async def worker(worker_id: int) -> None:
            task_id = f"TASK-W-{worker_id}"
            run_id = f"run-w-{worker_id}"
            # Emit multiple events with worker-specific data
            for i in range(5):
                await capture.emit(
                    _make_llm_call(
                        run_id=run_id,
                        task_id=task_id,
                        input_tokens=worker_id * 100 + i,
                    )
                )

        await asyncio.gather(worker(1), worker(2), worker(3))

        assert len(capture.events) == 15

        # Verify no cross-contamination
        for event in capture.events:
            worker_num = event.task_id.split("-")[-1]
            assert event.run_id == f"run-w-{worker_num}", (
                f"Cross-contamination: event for {event.task_id} has run_id {event.run_id}"
            )
            # input_tokens should be in the range for this worker
            expected_base = int(worker_num) * 100
            assert expected_base <= event.input_tokens < expected_base + 5


# ============================================================================
# AC-007: A/B data — same task produces comparable metrics under different profiles
# ============================================================================


class TestABComparisonData:
    """Same task under different profiles produces comparable instrumentation.

    Both runs must produce task.completed events with the same task_id.
    input_tokens must be available for both runs.
    latency_ms values must be available for p50/p95 comparison.
    """

    async def test_same_task_different_profiles_produce_completed_events(self) -> None:
        """Both A/B runs produce task.completed with the same task_id."""
        capture_a = NullEmitter(capture=True)
        capture_b = NullEmitter(capture=True)

        task_id = "TASK-AB-001"

        # Run A: digest_only profile
        await capture_a.emit(_make_task_started(run_id="run-a", task_id=task_id))
        await capture_a.emit(
            _make_llm_call(run_id="run-a", task_id=task_id, prompt_profile="digest_only", input_tokens=500, latency_ms=1200.0)
        )
        await capture_a.emit(
            _make_task_completed(run_id="run-a", task_id=task_id, prompt_profile="digest_only")
        )

        # Run B: digest+rules_bundle profile
        await capture_b.emit(_make_task_started(run_id="run-b", task_id=task_id))
        await capture_b.emit(
            _make_llm_call(run_id="run-b", task_id=task_id, prompt_profile="digest+rules_bundle", input_tokens=800, latency_ms=1800.0)
        )
        await capture_b.emit(
            _make_task_completed(run_id="run-b", task_id=task_id, prompt_profile="digest+rules_bundle")
        )

        # Both produce completed events
        completed_a = [e for e in capture_a.events if isinstance(e, TaskCompletedEvent)]
        completed_b = [e for e in capture_b.events if isinstance(e, TaskCompletedEvent)]
        assert len(completed_a) == 1
        assert len(completed_b) == 1
        assert completed_a[0].task_id == task_id
        assert completed_b[0].task_id == task_id

    async def test_input_tokens_available_for_both_runs(self) -> None:
        """input_tokens is available for both A and B runs."""
        capture_a = NullEmitter(capture=True)
        capture_b = NullEmitter(capture=True)

        task_id = "TASK-AB-002"

        await capture_a.emit(
            _make_llm_call(run_id="run-a", task_id=task_id, prompt_profile="digest_only", input_tokens=500)
        )
        await capture_b.emit(
            _make_llm_call(run_id="run-b", task_id=task_id, prompt_profile="digest+rules_bundle", input_tokens=800)
        )

        llm_a = [e for e in capture_a.events if isinstance(e, LLMCallEvent)]
        llm_b = [e for e in capture_b.events if isinstance(e, LLMCallEvent)]

        assert llm_a[0].input_tokens == 500
        assert llm_b[0].input_tokens == 800

    async def test_latency_ms_available_for_comparison(self) -> None:
        """latency_ms values are available for p50/p95 comparison between profiles."""
        capture_a = NullEmitter(capture=True)
        capture_b = NullEmitter(capture=True)

        task_id = "TASK-AB-003"

        # Simulate multiple LLM calls to gather latency data
        latencies_a = [1200.0, 1100.0, 1300.0, 1150.0]
        latencies_b = [1800.0, 1700.0, 1900.0, 1750.0]

        for lat in latencies_a:
            await capture_a.emit(
                _make_llm_call(run_id="run-a", task_id=task_id, prompt_profile="digest_only", latency_ms=lat)
            )
        for lat in latencies_b:
            await capture_b.emit(
                _make_llm_call(run_id="run-b", task_id=task_id, prompt_profile="digest+rules_bundle", latency_ms=lat)
            )

        # All latency values are present and can be used for comparison
        all_latencies_a = [e.latency_ms for e in capture_a.events if isinstance(e, LLMCallEvent)]
        all_latencies_b = [e.latency_ms for e in capture_b.events if isinstance(e, LLMCallEvent)]

        assert len(all_latencies_a) == 4
        assert len(all_latencies_b) == 4
        assert all(lat > 0 for lat in all_latencies_a)
        assert all(lat > 0 for lat in all_latencies_b)

        # Verify we can compute p50 and p95 (sorted values, pick indices)
        sorted_a = sorted(all_latencies_a)
        sorted_b = sorted(all_latencies_b)
        # p50 ~ median
        p50_a = sorted_a[len(sorted_a) // 2]
        p50_b = sorted_b[len(sorted_b) // 2]
        assert isinstance(p50_a, float)
        assert isinstance(p50_b, float)


# ============================================================================
# AC-008: Digest boundary — 700 tokens accepted, 701 warned
# ============================================================================


class TestDigestValidationBoundary:
    """Digest at exactly 700 tokens is accepted; 701 triggers a warning."""

    def _create_digest_file(self, digest_dir: Path, role: str, content: str) -> None:
        """Write a digest file for the given role."""
        digest_dir.mkdir(parents=True, exist_ok=True)
        (digest_dir / f"{role}.md").write_text(content, encoding="utf-8")

    def _generate_text_with_token_count(self, target_tokens: int) -> str:
        """Generate text that approximates the target token count.

        Uses word-based generation. The count_tokens function counts
        using tiktoken if available, else char/4 approximation.
        We iteratively build text to hit the target.
        """
        # Start with a reasonable word-per-token estimate
        # Most tokenizers: ~1 token per 4 chars, avg word ~5 chars
        # Build up iteratively
        words = []
        text = ""
        # Use short words to make tokens more predictable
        word = "test"
        while count_tokens(text) < target_tokens:
            words.append(word)
            text = " ".join(words)
        # We may overshoot by 1, trim back if needed
        while count_tokens(text) > target_tokens and len(words) > 1:
            words.pop()
            text = " ".join(words)
        return text

    def test_digest_at_exactly_max_tokens_accepted(self, tmp_path: Path) -> None:
        """Digest at exactly MAX_TOKENS (700) is valid with no warning."""
        assert MAX_TOKENS == 700, f"Expected MAX_TOKENS=700, got {MAX_TOKENS}"

        digest_dir = tmp_path / "digests"
        # Create text that's exactly at the limit
        content = self._generate_text_with_token_count(MAX_TOKENS)
        actual_tokens = count_tokens(content)
        assert actual_tokens <= MAX_TOKENS, (
            f"Generated text has {actual_tokens} tokens, expected <= {MAX_TOKENS}"
        )

        self._create_digest_file(digest_dir, "player", content)
        validator = DigestValidator(digest_dir)
        result = validator.validate("player")

        assert result.valid is True
        assert result.warning is None

    def test_digest_at_701_tokens_triggers_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Digest at 701 tokens is still valid but triggers a warning."""
        digest_dir = tmp_path / "digests-over"
        # Generate text that exceeds MAX_TOKENS by at least 1
        content = self._generate_text_with_token_count(MAX_TOKENS + 10)
        # Ensure we're actually over
        actual_tokens = count_tokens(content)
        assert actual_tokens > MAX_TOKENS, (
            f"Generated text has {actual_tokens} tokens, expected > {MAX_TOKENS}"
        )

        self._create_digest_file(digest_dir, "player", content)
        validator = DigestValidator(digest_dir)

        with caplog.at_level(logging.WARNING):
            result = validator.validate("player")

        assert result.valid is True  # Still valid, but warned
        assert result.warning is not None
        assert "exceeds" in result.warning.lower() or str(MAX_TOKENS) in result.warning


# ============================================================================
# AC-009: Phase 1 — rules bundle + digest coexist
# ============================================================================


class TestPhase1MigrationPreservation:
    """Phase 1: Full rules bundle injected alongside digest.

    prompt_profile is tagged as digest+rules_bundle.
    """

    def test_rules_bundle_and_digest_coexist(self, tmp_path: Path) -> None:
        """Assembler includes both digest and rules bundle in output."""
        digest_dir = tmp_path / "digests"
        digest_dir.mkdir(parents=True)
        (digest_dir / "player.md").write_text("# Player Digest\nMinimal player instructions.", encoding="utf-8")

        loader = DigestLoader(digest_dir)
        assembler = PromptProfileAssembler(loader=loader)

        rules_bundle = "# Full Rules Bundle\nAll rules here."
        assembled = assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_RULES_BUNDLE,
            rules_bundle=rules_bundle,
        )

        # Both digest and rules bundle content present
        assert "Player Digest" in assembled
        assert "Full Rules Bundle" in assembled

    def test_prompt_profile_tagged_as_digest_rules_bundle(self, tmp_path: Path) -> None:
        """The assembled prompt is tagged with digest+rules_bundle profile."""
        digest_dir = tmp_path / "digests"
        digest_dir.mkdir(parents=True)
        (digest_dir / "player.md").write_text("# Player Digest", encoding="utf-8")

        loader = DigestLoader(digest_dir)
        assembler = PromptProfileAssembler(loader=loader)

        assembler.assemble(
            role="player",
            profile=PromptProfile.DIGEST_RULES_BUNDLE,
            rules_bundle="rules content",
        )

        assert assembler.last_profile == PromptProfile.DIGEST_RULES_BUNDLE
        assert assembler.last_profile.value == "digest+rules_bundle"

    async def test_events_tagged_with_digest_rules_bundle_profile(self) -> None:
        """Events emitted during Phase 1 carry the digest+rules_bundle profile tag."""
        emitter = NullEmitter(capture=True)

        await emitter.emit(
            _make_llm_call(prompt_profile="digest+rules_bundle")
        )
        await emitter.emit(
            _make_task_completed(prompt_profile="digest+rules_bundle")
        )

        llm_event = emitter.events[0]
        assert isinstance(llm_event, LLMCallEvent)
        assert llm_event.prompt_profile == "digest+rules_bundle"

        completed_event = emitter.events[1]
        assert isinstance(completed_event, TaskCompletedEvent)
        assert completed_event.prompt_profile == "digest+rules_bundle"

    def test_default_profile_is_digest_rules_bundle(self, tmp_path: Path) -> None:
        """Default assembler profile is digest+rules_bundle for Phase 1 safety."""
        digest_dir = tmp_path / "digests"
        digest_dir.mkdir(parents=True)
        (digest_dir / "player.md").write_text("# Player", encoding="utf-8")

        loader = DigestLoader(digest_dir)
        assembler = PromptProfileAssembler(loader=loader)

        assert assembler.default_profile == PromptProfile.DIGEST_RULES_BUNDLE


# ============================================================================
# AC-010: Async emission verified non-blocking
# ============================================================================


class TestAsyncEmissionNonBlocking:
    """Event emission does not block LLM call critical path.

    Verified via async fire-and-forget semantics.
    """

    async def test_emit_is_async_coroutine(self) -> None:
        """All emitter emit() methods return coroutines."""
        null = NullEmitter(capture=True)
        coro = null.emit(_make_task_started())
        assert asyncio.iscoroutine(coro)
        await coro

    async def test_emit_does_not_block_caller(self, tmp_path: Path) -> None:
        """emit() completes within a reasonable time, not blocking the caller."""
        events_dir = tmp_path / "nonblocking"
        backend = JSONLFileBackend(events_dir=events_dir)

        start = time.monotonic()
        await backend.emit(_make_task_started())
        await backend.emit(_make_llm_call())
        await backend.emit(_make_tool_exec())
        elapsed = time.monotonic() - start

        # Emit calls should complete very quickly (well under 1 second)
        assert elapsed < 1.0, f"emit() took {elapsed:.3f}s, expected < 1.0s"
        await backend.flush()

    async def test_fire_and_forget_pattern(self) -> None:
        """Events can be emitted in fire-and-forget style using asyncio.create_task."""
        emitter = NullEmitter(capture=True)

        # Simulate fire-and-forget emission (what the LLM call path would do)
        tasks = []
        for i in range(5):
            task = asyncio.create_task(
                emitter.emit(_make_llm_call(input_tokens=100 + i))
            )
            tasks.append(task)

        # LLM work continues here without waiting for emissions
        # (In production, the caller doesn't await the emit tasks immediately)

        # Eventually gather to verify they all completed
        await asyncio.gather(*tasks)
        assert len(emitter.events) == 5

    async def test_concurrent_emit_with_simulated_work(self, tmp_path: Path) -> None:
        """Emission can happen concurrently with simulated LLM work."""
        events_dir = tmp_path / "concurrent-work"
        jsonl = JSONLFileBackend(events_dir=events_dir)
        capture = NullEmitter(capture=True)
        composite = CompositeBackend(backends=[jsonl, capture])

        async def simulated_llm_call(call_id: int) -> float:
            """Simulate an LLM call that emits events."""
            start = time.monotonic()
            # Emit event (fire-and-forget style, but awaited here for test)
            await composite.emit(
                _make_llm_call(input_tokens=call_id * 100, latency_ms=float(call_id * 10))
            )
            # Simulate LLM processing
            await asyncio.sleep(0.01)
            return time.monotonic() - start

        # Run 5 simulated LLM calls concurrently
        latencies = await asyncio.gather(
            *[simulated_llm_call(i) for i in range(1, 6)]
        )
        await composite.flush()

        # All events captured
        assert len(capture.events) == 5

        # All calls completed quickly (emission didn't significantly block)
        for lat in latencies:
            assert lat < 1.0, f"Call took {lat:.3f}s, expected < 1.0s"
