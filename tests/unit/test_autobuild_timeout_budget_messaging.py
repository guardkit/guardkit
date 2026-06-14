"""
Unit tests for the ``timeout_budget_exhausted`` summary/error messaging
(TASK-FIX-TBXMSG01).

A clean, well-classified budget exhaustion must NOT render as the generic
"Unknown error occurred" in either the finalize-phase summary panel
(``_build_summary_details``) or the ``OrchestrationResult.error`` field
(``_build_error_message``). The message must name the cause (time budget
exhausted) and quote the turns-used and remaining-vs-minimum, mirroring the
precise structured log line emitted at exhaustion time
("remaining=<X>s < min=600s").

These tests live in a dedicated module (rather than the shared
``test_autobuild_timeout_budget.py``) so they exercise only the two message
builders in isolation and stay decoupled from the per-turn-budget machinery
tested next door.

Coverage target: the two message builders' ``timeout_budget_exhausted``
branches and the unchanged unknown-error fallbacks.
"""

from pathlib import Path
from typing import Any, List
from unittest.mock import Mock

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    MIN_TURN_BUDGET_SECONDS,
    TurnRecord,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures / helpers
# ============================================================================


@pytest.fixture
def worktree_path(tmp_path) -> Path:
    """Temporary directory used as a worktree root."""
    wt = tmp_path / "worktree"
    wt.mkdir()
    return wt


@pytest.fixture
def mock_worktree() -> Worktree:
    """Mock Worktree instance."""
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-AB-001"
    wt.path = Path("/tmp/worktrees/TASK-AB-001")
    wt.branch_name = "autobuild/TASK-AB-001"
    wt.base_branch = "main"
    return wt


def _bare_orchestrator() -> AutoBuildOrchestrator:
    """An orchestrator built without ``__init__``.

    The two message builders' ``timeout_budget_exhausted`` and unknown-error
    branches read only ``getattr(self, "_timeout_budget_remaining", None)``,
    ``len(turn_history)``, ``MIN_TURN_BUDGET_SECONDS`` and ``turn_history``
    itself — no other instance state — so a bare instance is sufficient and
    keeps these tests insulated from the full constructor.
    """
    return AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)


def _turn_history(n: int) -> List[Any]:
    """A ``turn_history`` of length ``n``.

    Only ``len(turn_history)`` matters for the budget branch; each record's
    ``decision`` is pinned to a non-"error" value so the unknown-error
    branch's ``next(... if t.decision == "error")`` filter reliably finds
    nothing and falls through to the generic message.
    """
    history: List[Any] = []
    for _ in range(n):
        record = Mock(spec=TurnRecord)
        record.decision = "feedback"
        history.append(record)
    return history


# ============================================================================
# Tests: _build_summary_details (the rendered summary panel)
# ============================================================================


class TestSummaryDetailsTimeoutBudget:
    """AC-1/AC-2 for the summary panel."""

    def test_names_budget_cause_with_remaining(self):
        """AC-1: names the cause + turns-used + remaining-vs-minimum."""
        orch = _bare_orchestrator()
        orch._timeout_budget_remaining = 397.4

        details = orch._build_summary_details(
            _turn_history(3), "timeout_budget_exhausted"
        )

        assert "Unknown error occurred" not in details
        assert "Time budget exhausted" in details
        assert "3 turn(s)" in details  # turns-used
        assert "remaining=397.4s" in details  # remaining
        assert f"min={MIN_TURN_BUDGET_SECONDS}s" in details  # minimum

    def test_budget_fallback_when_remaining_unknown(self):
        """The builder degrades gracefully when the remaining value was never
        captured (bare instance → ``getattr`` returns None) instead of
        raising AttributeError."""
        orch = _bare_orchestrator()
        # _timeout_budget_remaining intentionally unset.

        details = orch._build_summary_details(
            _turn_history(1), "timeout_budget_exhausted"
        )

        assert "Unknown error occurred" not in details
        assert "Time budget exhausted" in details
        assert "remaining budget unknown" in details
        assert f"min={MIN_TURN_BUDGET_SECONDS}s" in details

    def test_unknown_error_path_unchanged(self):
        """AC-2: a genuine unknown-error decision still renders the generic
        message (no error turn in history → fallback string)."""
        orch = _bare_orchestrator()

        details = orch._build_summary_details(_turn_history(2), "error")

        assert details == (
            "Unknown error occurred. Worktree preserved for inspection."
        )


# ============================================================================
# Tests: _build_error_message (OrchestrationResult.error field)
# ============================================================================


class TestErrorMessageTimeoutBudget:
    """The error field must be a meaningful budget message, never empty."""

    def test_names_budget_cause(self):
        """timeout_budget_exhausted yields a budget message, neither "" nor
        "Unknown error occurred" — a ``success=False`` result must carry a
        non-empty error string."""
        orch = _bare_orchestrator()
        orch._timeout_budget_remaining = 397.4

        error = orch._build_error_message(
            "timeout_budget_exhausted", _turn_history(3)
        )

        assert error != ""
        assert "Unknown error occurred" not in error
        assert "Time budget exhausted" in error
        assert "3 turn(s)" in error
        assert "remaining=397.4s" in error
        assert f"min={MIN_TURN_BUDGET_SECONDS}s" in error

    def test_budget_fallback_when_remaining_unknown(self):
        """Graceful degradation when the remaining value is absent."""
        orch = _bare_orchestrator()

        error = orch._build_error_message(
            "timeout_budget_exhausted", _turn_history(2)
        )

        assert error != ""
        assert "Unknown error occurred" not in error
        assert "Time budget exhausted" in error
        assert "remaining budget unknown" in error

    def test_unknown_error_path_unchanged(self):
        """AC-2 (error-field side): a genuine error with no error turn still
        yields the unchanged "Unknown error occurred" string."""
        orch = _bare_orchestrator()

        error = orch._build_error_message("error", _turn_history(1))

        assert error == "Unknown error occurred"
