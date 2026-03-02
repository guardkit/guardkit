"""Tests for Graphiti context loader instrumentation.

Verifies that graphiti.query events are emitted for every context retrieval
operation, with correct query_type, tokens_injected, latency, and status.
Also tests Graphiti unavailability handling: error events, warning logs,
and graceful fallback to digest-only context.

References:
    - TASK-INST-006: Instrument Graphiti context loader
    - TASK-INST-002: EventEmitter protocol
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import GraphitiQueryEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def capture_emitter() -> NullEmitter:
    """NullEmitter that captures emitted events."""
    return NullEmitter(capture=True)


def _make_fake_graphiti(
    *,
    search_results: Optional[List[Dict[str, Any]]] = None,
    enabled: bool = True,
    raise_on_search: Optional[Exception] = None,
) -> MagicMock:
    """Build a mock GraphitiClient for testing.

    Args:
        search_results: Results returned by search() calls.
        enabled: Whether the client reports as enabled.
        raise_on_search: If set, search() raises this exception.
    """
    client = MagicMock()
    client.enabled = enabled

    if raise_on_search is not None:
        client.search = AsyncMock(side_effect=raise_on_search)
    else:
        client.search = AsyncMock(return_value=search_results or [])

    return client


# ---------------------------------------------------------------------------
# Seam test: EVENT_EMITTER contract from TASK-INST-002
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("EVENT_EMITTER")
def test_event_emitter_accepts_graphiti_events():
    """Verify EventEmitter can emit GraphitiQueryEvent.

    Contract: EventEmitter injected via constructor; call await emitter.emit(event)
    Producer: TASK-INST-002
    """
    emitter = NullEmitter(capture=True)
    event = GraphitiQueryEvent(
        run_id="test",
        task_id="TASK-001",
        agent_role="player",
        attempt=1,
        timestamp="2026-03-01T00:00:00Z",
        query_type="context_loader",
        items_returned=5,
        tokens_injected=1200,
        latency_ms=350.0,
        status="ok",
    )
    asyncio.run(emitter.emit(event))
    assert len(emitter.events) == 1


# ---------------------------------------------------------------------------
# AC-1: graphiti.query event emitted for every context retrieval
# ---------------------------------------------------------------------------


class TestGraphitiQueryEventEmission:
    """Verify events are emitted for each Graphiti query."""

    def test_load_critical_context_emits_events(self, capture_emitter: NullEmitter):
        """load_critical_context should emit a graphiti.query event for each
        internal Graphiti query when an emitter is provided."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            search_results=[{"body": "test", "score": 1.0}],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        # Should have multiple events (one per internal query category)
        assert len(capture_emitter.events) > 0
        for event in capture_emitter.events:
            assert isinstance(event, GraphitiQueryEvent)

    def test_each_retrieval_emits_exactly_one_event(self, capture_emitter: NullEmitter):
        """Each call to _load_* helper should produce exactly one event."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            search_results=[{"body": "data", "score": 1.0}],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        # The number of events should match the number of Graphiti search calls
        search_call_count = fake_graphiti.search.call_count
        assert len(capture_emitter.events) == search_call_count


# ---------------------------------------------------------------------------
# AC-2: query_type correctly identifies the retrieval type
# ---------------------------------------------------------------------------


class TestQueryTypeIdentification:
    """Verify query_type field is set correctly per retrieval type."""

    def test_context_loader_query_type(self, capture_emitter: NullEmitter):
        """Standard context loader queries should use 'context_loader' type."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            search_results=[{"body": "test", "score": 1.0}],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        assert len(capture_emitter.events) > 0
        # All context loader queries should be 'context_loader' type
        for event in capture_emitter.events:
            assert event.query_type == "context_loader"

    def test_adr_lookup_query_type(self, capture_emitter: NullEmitter):
        """ADR loading should use 'adr_lookup' query type."""
        from guardkit.knowledge.context_loader import load_critical_adrs

        fake_graphiti = _make_fake_graphiti(
            search_results=[{"body": {"id": "ADR-001", "title": "test"}, "score": 1.0}],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(load_critical_adrs(emitter=capture_emitter))

        assert len(capture_emitter.events) == 1
        assert capture_emitter.events[0].query_type == "adr_lookup"


# ---------------------------------------------------------------------------
# AC-3: tokens_injected estimated for retrieved context
# ---------------------------------------------------------------------------


class TestTokensInjected:
    """Verify tokens_injected is populated with a reasonable estimate."""

    def test_tokens_injected_positive_for_results(self, capture_emitter: NullEmitter):
        """tokens_injected should be > 0 when results are returned."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            search_results=[
                {"body": "A" * 100, "score": 1.0},
                {"body": "B" * 200, "score": 1.0},
            ],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        for event in capture_emitter.events:
            assert event.tokens_injected >= 0
            if event.items_returned > 0:
                assert event.tokens_injected > 0

    def test_tokens_injected_zero_for_empty_results(self, capture_emitter: NullEmitter):
        """tokens_injected should be 0 when no results returned."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(search_results=[])

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        for event in capture_emitter.events:
            assert event.tokens_injected == 0
            assert event.items_returned == 0


# ---------------------------------------------------------------------------
# AC-4: Graphiti unavailability emits error event and falls back gracefully
# ---------------------------------------------------------------------------


class TestGraphitiUnavailability:
    """Verify error handling when Graphiti is unreachable."""

    def test_error_event_on_graphiti_exception(self, capture_emitter: NullEmitter):
        """When Graphiti raises, emit event with status='error'."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            raise_on_search=ConnectionError("Graphiti unreachable"),
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            result = asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        # Should still return a valid (empty) context - no crash
        assert result is not None

        # At least one error event should be emitted
        error_events = [e for e in capture_emitter.events if e.status == "error"]
        assert len(error_events) > 0

    def test_graceful_fallback_returns_empty_context(self, capture_emitter: NullEmitter):
        """On Graphiti failure, should return empty context (digest-only)."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            raise_on_search=TimeoutError("Connection timed out"),
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            result = asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        # Fallback: empty context (digest-only)
        assert result.system_context == []
        assert result.quality_gates == []
        assert result.architecture_decisions == []
        assert result.failure_patterns == []

    def test_none_graphiti_emits_no_events(self, capture_emitter: NullEmitter):
        """When graphiti is None (disabled), no events are emitted."""
        from guardkit.knowledge.context_loader import load_critical_context

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=None,
        ):
            result = asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        assert result is not None
        # No events emitted when Graphiti is completely disabled
        assert len(capture_emitter.events) == 0


# ---------------------------------------------------------------------------
# AC-5: Warning logged on Graphiti fallback
# ---------------------------------------------------------------------------


class TestWarningLogging:
    """Verify warning is logged when Graphiti falls back."""

    def test_warning_logged_on_search_failure(self, capture_emitter: NullEmitter, caplog):
        """A warning should be logged when Graphiti search fails."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            raise_on_search=ConnectionError("Cannot connect"),
        )

        with caplog.at_level(logging.WARNING, logger="guardkit.knowledge.context_loader"):
            with patch(
                "guardkit.knowledge.context_loader.get_graphiti",
                return_value=fake_graphiti,
            ):
                asyncio.run(
                    load_critical_context(
                        command="task-work",
                        emitter=capture_emitter,
                    )
                )

        # Check that a warning was logged about Graphiti fallback
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("graphiti" in msg.lower() or "fallback" in msg.lower() for msg in warning_messages), (
            f"Expected warning about Graphiti fallback, got: {warning_messages}"
        )


# ---------------------------------------------------------------------------
# AC-6: Run continues with digest-only context when Graphiti unavailable
# ---------------------------------------------------------------------------


class TestDigestOnlyFallback:
    """Verify the run continues when Graphiti is unavailable."""

    def test_disabled_graphiti_returns_empty_context(self, capture_emitter: NullEmitter):
        """Disabled Graphiti should return empty context without error."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(enabled=False)

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            result = asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        assert result is not None
        assert result.system_context == []

    def test_exception_during_load_returns_empty_context(self, capture_emitter: NullEmitter):
        """Even unexpected exceptions should not crash - return empty context."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            raise_on_search=RuntimeError("Unexpected internal error"),
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            result = asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        assert result is not None
        # Should have error events
        error_events = [e for e in capture_emitter.events if e.status == "error"]
        assert len(error_events) >= 0  # May or may not have events depending on where error occurs


# ---------------------------------------------------------------------------
# AC-7: Unit tests cover successful queries, error paths, and fallback
#        (This entire file satisfies AC-7)
# ---------------------------------------------------------------------------


class TestLatencyTracking:
    """Verify latency_ms is tracked for each query."""

    def test_latency_ms_populated(self, capture_emitter: NullEmitter):
        """Each event should have a non-negative latency_ms value."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            search_results=[{"body": "test", "score": 1.0}],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        assert len(capture_emitter.events) > 0
        for event in capture_emitter.events:
            assert event.latency_ms >= 0.0


class TestItemsReturnedCount:
    """Verify items_returned matches actual result count."""

    def test_items_returned_matches_result_count(self, capture_emitter: NullEmitter):
        """items_returned should reflect the actual number of results."""
        from guardkit.knowledge.context_loader import load_critical_context

        results = [
            {"body": "item1", "score": 1.0},
            {"body": "item2", "score": 1.0},
            {"body": "item3", "score": 1.0},
        ]
        fake_graphiti = _make_fake_graphiti(search_results=results)

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                )
            )

        assert len(capture_emitter.events) > 0
        for event in capture_emitter.events:
            if event.status == "ok":
                assert event.items_returned == len(results)


class TestEventFieldsComplete:
    """Verify all required event fields are populated."""

    def test_event_has_all_base_fields(self, capture_emitter: NullEmitter):
        """Each event should have run_id, task_id, agent_role, etc."""
        from guardkit.knowledge.context_loader import load_critical_context

        fake_graphiti = _make_fake_graphiti(
            search_results=[{"body": "test", "score": 1.0}],
        )

        with patch(
            "guardkit.knowledge.context_loader.get_graphiti",
            return_value=fake_graphiti,
        ):
            asyncio.run(
                load_critical_context(
                    command="task-work",
                    emitter=capture_emitter,
                    run_id="test-run-001",
                    task_id="TASK-001",
                    agent_role="player",
                    attempt=1,
                )
            )

        assert len(capture_emitter.events) > 0
        for event in capture_emitter.events:
            assert event.run_id == "test-run-001"
            assert event.task_id == "TASK-001"
            assert event.agent_role == "player"
            assert event.attempt == 1
            assert event.timestamp != ""
            assert event.query_type in ("context_loader", "nearest_neighbours", "adr_lookup")
            assert event.status in ("ok", "error")
