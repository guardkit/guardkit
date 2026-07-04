"""Unit tests for TASK-AB-STALLTAX01 parallel_interference stall classification.

Covers the new ``parallel_interference_stall`` co-fire sub-type added to
``classify_stall``, the extractor it keys on, and the actionability additions
to the context-pollution stall message:

1. ``_extract_parallel_interference_signal`` fires on the schema-stable
   ``failure_classification == "parallel_contention"`` field OR a non-empty
   ``contention_peers`` map on a ``test_verification`` issue — never on
   feedback prose, and never when the classification is absent
   (absent != contention).
2. ``classify_stall`` CO-FIRES ``parallel_interference_stall`` additively
   alongside ``context_pollution_stall_no_checkpoint`` (both appear); plain
   repeated code failures leave context_pollution alone; the existing
   ``environment_stall`` precedence is unchanged.
3. The context-pollution stall message appends (a) the parallel-wave
   isolation hint naming peer tasks/files when interference co-fired, and
   (b) an aggregated, deduped, bounded list of the failing-test lines from
   the stall window's turns.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    FAILURE_CATEGORY_MAP,
    STALL_COACH_AGENT_INVOCATIONS,
    STALL_CONTEXT_POLLUTION,
    STALL_ENVIRONMENT,
    STALL_FEEDBACK_GENERIC,
    STALL_PARALLEL_INTERFERENCE,
    TurnRecord,
    _aggregate_failing_test_lines,
    _collect_contention_peers,
    _extract_parallel_interference_signal,
    classify_stall,
)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


_DEFAULT_TEST_OUTPUT = (
    "Error detail:\n"
    "FAILED tests/test_tutor.py::test_session_flow - AssertionError\n"
    "Result:\n"
    "1 failed, 4 passed in 2.1s"
)


def _real_player_result(
    turn: int, task_id: str = "TASK-SMP-002"
) -> AgentInvocationResult:
    """A real Player report used for interference fixtures."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": ["src/feature.py"],
            "files_created": ["tests/test_feature.py"],
            "tests_passed": True,
            "test_count": 5,
        },
        duration_seconds=12.0,
        error=None,
    )


def _coach_result_with_test_verification(
    turn: int,
    failure_classification: Optional[str] = "parallel_contention",
    contention_peers: Optional[Dict[str, List[str]]] = None,
    test_output: str = _DEFAULT_TEST_OUTPUT,
    task_id: str = "TASK-SMP-002",
    extra_issues: Optional[List[Dict[str, Any]]] = None,
    include_classification_key: bool = True,
) -> AgentInvocationResult:
    """Build a coach result carrying a ``test_verification`` issue.

    ``failure_classification=None`` with ``include_classification_key=True``
    exercises the explicit-``None`` absent case;
    ``include_classification_key=False`` omits the key entirely.
    """
    issue: Dict[str, Any] = {
        "severity": "must_fix",
        "category": "test_verification",
        "description": "Independent test verification failed",
        "test_output": test_output,
        "failure_confidence": "high",
    }
    if include_classification_key:
        issue["failure_classification"] = failure_classification
    if contention_peers is not None:
        issue["contention_peers"] = contention_peers
    issues: List[Dict[str, Any]] = list(extra_issues or [])
    issues.append(issue)
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": "Independent tests failed.",
            "issues": issues,
        },
        duration_seconds=0.5,
        error=None,
    )


def _turn(
    turn: int,
    coach_result: AgentInvocationResult,
) -> TurnRecord:
    return TurnRecord(
        turn=turn,
        player_result=_real_player_result(turn),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_result.report["feedback"],
        timestamp=f"2026-07-03T11:0{turn}:00Z",
    )


def _interference_turn(
    turn: int,
    contention_peers: Optional[Dict[str, List[str]]] = None,
    test_output: str = _DEFAULT_TEST_OUTPUT,
) -> TurnRecord:
    """Trailing-window turn carrying the parallel_contention classification."""
    return _turn(
        turn,
        _coach_result_with_test_verification(
            turn,
            failure_classification="parallel_contention",
            contention_peers=contention_peers,
            test_output=test_output,
        ),
    )


def _code_failure_turn(
    turn: int, test_output: str = _DEFAULT_TEST_OUTPUT
) -> TurnRecord:
    """Plain repeated code failure — no contention marker of either kind."""
    return _turn(
        turn,
        _coach_result_with_test_verification(
            turn,
            failure_classification="code",
            test_output=test_output,
        ),
    )


def _env_stall_turn(turn: int) -> TurnRecord:
    """Turn matching the TASK-ABSR-C3D4 environment_stall pattern."""
    coach_result = AgentInvocationResult(
        task_id="TASK-SMP-002",
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": "Independent tests failed (infrastructure).",
            "validation_results": {
                "quality_gates": {"all_gates_passed": True},
                "independent_tests": {"tests_passed": False},
            },
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "test_verification",
                    "description": "Tests failed due to infrastructure issues",
                    "failure_classification": "infrastructure",
                    "failure_confidence": "high",
                }
            ],
        },
        duration_seconds=0.5,
        error=None,
    )
    return _turn(turn, coach_result)


# ---------------------------------------------------------------------------
# 1. Extractor: _extract_parallel_interference_signal
# ---------------------------------------------------------------------------


class TestExtractParallelInterferenceSignal:
    """Predicate: schema-match only, absent classification stays absent."""

    def test_fires_on_parallel_contention_classification(self):
        turn = _interference_turn(1)
        signal = _extract_parallel_interference_signal(turn)
        assert signal is not None
        assert signal["failure_classification"] == "parallel_contention"

    def test_fires_on_contention_peers_only(self):
        # TASK-FIX-A7B2 overlap branch shape: failure_class recorded as
        # "code" but the peer-overlap map carries the contention marker.
        turn = _turn(
            1,
            _coach_result_with_test_verification(
                1,
                failure_classification="code",
                contention_peers={"TASK-SMP-003": ["src/shared.py"]},
            ),
        )
        signal = _extract_parallel_interference_signal(turn)
        assert signal is not None
        assert signal["contention_peers"] == {"TASK-SMP-003": ["src/shared.py"]}

    def test_fires_on_contention_peers_with_missing_classification(self):
        turn = _turn(
            1,
            _coach_result_with_test_verification(
                1,
                contention_peers={"TASK-SMP-003": ["src/shared.py"]},
                include_classification_key=False,
            ),
        )
        assert _extract_parallel_interference_signal(turn) is not None

    def test_absent_classification_is_absent_signal(self):
        # Key omitted entirely: absent must never default to interference
        # (absence-must-survive-every-reconciliation-layer).
        turn = _turn(
            1,
            _coach_result_with_test_verification(
                1, include_classification_key=False
            ),
        )
        assert _extract_parallel_interference_signal(turn) is None

    def test_none_classification_is_absent_signal(self):
        turn = _turn(
            1,
            _coach_result_with_test_verification(
                1, failure_classification=None
            ),
        )
        assert _extract_parallel_interference_signal(turn) is None

    def test_code_classification_without_peers_does_not_fire(self):
        assert (
            _extract_parallel_interference_signal(_code_failure_turn(1)) is None
        )

    def test_empty_contention_peers_does_not_fire(self):
        turn = _turn(
            1,
            _coach_result_with_test_verification(
                1, failure_classification="code", contention_peers={}
            ),
        )
        assert _extract_parallel_interference_signal(turn) is None

    def test_returns_none_when_coach_result_missing(self):
        turn = TurnRecord(
            turn=1,
            player_result=_real_player_result(1),
            coach_result=None,
            decision="error",
            feedback=None,
            timestamp="2026-07-03T11:01:00Z",
        )
        assert _extract_parallel_interference_signal(turn) is None

    def test_returns_none_for_non_test_verification_category(self):
        coach_result = AgentInvocationResult(
            task_id="TASK-SMP-002",
            turn=1,
            agent_type="coach",
            success=True,
            report={
                "decision": "feedback",
                "feedback": "AC missing",
                "issues": [
                    {
                        "severity": "must_fix",
                        "category": "missing_requirement",
                        "failure_classification": "parallel_contention",
                    }
                ],
            },
            duration_seconds=0.5,
            error=None,
        )
        assert _extract_parallel_interference_signal(_turn(1, coach_result)) is None


# ---------------------------------------------------------------------------
# 2. classify_stall co-fire behaviour
# ---------------------------------------------------------------------------


class TestClassifyParallelInterferenceStall:
    """AC: parallel_interference CO-FIRES additively; label stays additive."""

    def test_co_fires_with_context_pollution(self):
        history = [
            _interference_turn(1),
            _interference_turn(2),
            _interference_turn(3),
        ]
        result = classify_stall(
            history,
            "unrecoverable_stall",
            threshold=3,
            context_pollution_fired=True,
        )
        assert result is not None
        # Both appear: the CONDITION and the CAUSE.
        assert STALL_CONTEXT_POLLUTION in result.co_fires
        assert STALL_PARALLEL_INTERFERENCE in result.co_fires
        # context_pollution stays the primary label; interference is additive.
        assert result.decision_label == STALL_CONTEXT_POLLUTION
        assert result.decision_subtype == (
            f"{STALL_CONTEXT_POLLUTION} + {STALL_PARALLEL_INTERFERENCE}"
        )

    def test_two_of_three_turns_do_not_fire(self):
        history = [
            _code_failure_turn(1),
            _interference_turn(2),
            _interference_turn(3),
        ]
        result = classify_stall(
            history,
            "unrecoverable_stall",
            threshold=3,
            context_pollution_fired=True,
        )
        assert result is not None
        assert STALL_PARALLEL_INTERFERENCE not in result.co_fires
        assert result.co_fires == [STALL_CONTEXT_POLLUTION]

    def test_plain_code_failures_leave_context_pollution_alone(self):
        history = [
            _code_failure_turn(1),
            _code_failure_turn(2),
            _code_failure_turn(3),
        ]
        result = classify_stall(
            history,
            "unrecoverable_stall",
            threshold=3,
            context_pollution_fired=True,
        )
        assert result is not None
        assert result.co_fires == [STALL_CONTEXT_POLLUTION]
        assert result.decision_subtype == STALL_CONTEXT_POLLUTION

    def test_absent_classification_never_fires(self):
        history = [
            _turn(
                n,
                _coach_result_with_test_verification(
                    n, include_classification_key=False
                ),
            )
            for n in (1, 2, 3)
        ]
        result = classify_stall(
            history,
            "unrecoverable_stall",
            threshold=3,
            context_pollution_fired=True,
        )
        assert result is not None
        assert STALL_PARALLEL_INTERFERENCE not in result.co_fires

    def test_interference_only_fires_without_context_pollution(self):
        # The interference co-fire is checked unconditionally: it also names
        # the cause when the loop exited via a non-pollution stall path.
        history = [
            _interference_turn(1),
            _interference_turn(2),
            _interference_turn(3),
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert result.co_fires == [STALL_PARALLEL_INTERFERENCE]
        assert STALL_FEEDBACK_GENERIC not in result.co_fires

    def test_co_fires_additively_with_agent_invocations(self):
        # Precedence decision pinned: unlike environment_stall, interference
        # is NOT suppressed by agent_invocations — it co-fires additively.
        extra = [
            {
                "severity": "must_fix",
                "category": "agent_invocations_violation",
                "description": "Missing phase invocations",
                "details": {
                    "missing_phases": ["4", "5"],
                    "expected_phases": 3,
                    "actual_invocations": 1,
                },
            }
        ]
        history = [
            _turn(
                n,
                _coach_result_with_test_verification(n, extra_issues=extra),
            )
            for n in (1, 2, 3)
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert STALL_COACH_AGENT_INVOCATIONS in result.co_fires
        assert STALL_PARALLEL_INTERFERENCE in result.co_fires
        assert result.decision_label == STALL_COACH_AGENT_INVOCATIONS

    def test_environment_stall_precedence_unchanged(self):
        # Pure env pattern: env fires as before, interference stays absent.
        history = [_env_stall_turn(1), _env_stall_turn(2), _env_stall_turn(3)]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert STALL_ENVIRONMENT in result.co_fires
        assert STALL_PARALLEL_INTERFERENCE not in result.co_fires
        assert result.decision_label == STALL_ENVIRONMENT

    def test_environment_stall_still_suppressed_by_context_pollution(self):
        history = [_env_stall_turn(1), _env_stall_turn(2), _env_stall_turn(3)]
        result = classify_stall(
            history,
            "unrecoverable_stall",
            threshold=3,
            context_pollution_fired=True,
        )
        assert result is not None
        assert STALL_CONTEXT_POLLUTION in result.co_fires
        assert STALL_ENVIRONMENT not in result.co_fires

    def test_returns_none_for_non_stall_decisions(self):
        # Backward-compat: the top-level final_decision is untouched — the
        # classifier only runs for "unrecoverable_stall".
        history = [
            _interference_turn(1),
            _interference_turn(2),
            _interference_turn(3),
        ]
        assert classify_stall(history, "approved") is None
        assert classify_stall(history, "max_turns_exceeded") is None

    def test_failure_category_map_entry(self):
        assert FAILURE_CATEGORY_MAP[STALL_PARALLEL_INTERFERENCE] == "env_failure"


# ---------------------------------------------------------------------------
# 3. Contention-peer collection + failing-test aggregation helpers
# ---------------------------------------------------------------------------


class TestCollectContentionPeers:
    def test_merges_peer_maps_across_window(self):
        history = [
            _interference_turn(
                1, contention_peers={"TASK-SMP-003": ["src/shared.py"]}
            ),
            _interference_turn(
                2,
                contention_peers={
                    "TASK-SMP-003": ["src/other.py"],
                    "TASK-SMP-004": ["features/glue.py"],
                },
            ),
            _interference_turn(3),
        ]
        peers = _collect_contention_peers(history, threshold=3)
        assert peers == {
            "TASK-SMP-003": ["src/other.py", "src/shared.py"],
            "TASK-SMP-004": ["features/glue.py"],
        }

    def test_empty_when_no_turn_carries_the_map(self):
        history = [_interference_turn(1), _interference_turn(2)]
        assert _collect_contention_peers(history, threshold=3) == {}


class TestAggregateFailingTestLines:
    def test_dedupes_across_turns(self):
        history = [
            _interference_turn(1),
            _interference_turn(2),
            _interference_turn(3),
        ]
        lines = _aggregate_failing_test_lines(history, threshold=3)
        failed = [ln for ln in lines if "test_session_flow" in ln]
        assert len(failed) == 1

    def test_bounded_with_overflow_marker(self):
        big_output = "\n".join(
            f"FAILED tests/test_bulk.py::test_case_{i} - AssertionError"
            for i in range(30)
        )
        history = [_interference_turn(1, test_output=big_output)]
        lines = _aggregate_failing_test_lines(history, threshold=3, max_lines=10)
        assert len(lines) == 11
        assert lines[-1].startswith("... (")
        assert "20 more" in lines[-1]

    def test_falls_back_to_description_when_no_marker_lines(self):
        turn = _turn(
            1,
            _coach_result_with_test_verification(
                1, test_output="everything exploded quietly"
            ),
        )
        lines = _aggregate_failing_test_lines([turn], threshold=3)
        assert lines == ["Independent test verification failed"]

    def test_empty_for_turns_without_test_verification_issues(self):
        coach_result = AgentInvocationResult(
            task_id="TASK-SMP-002",
            turn=1,
            agent_type="coach",
            success=True,
            report={"decision": "feedback", "feedback": "x", "issues": []},
            duration_seconds=0.5,
            error=None,
        )
        assert _aggregate_failing_test_lines([_turn(1, coach_result)]) == []

    # -- 2026-07-04 code review (FIX 3): anchored primary extractor ---------

    def test_section_banners_and_traceback_noise_are_excluded(self):
        """pytest section banners and ``E   assert`` traceback lines must not
        pollute the failing-tests list when a real node-id line exists."""
        noisy = (
            "=========================== ERRORS ===========================\n"
            "E   assert 1 == 2\n"
            "FAILED tests/test_x.py::test_a - AssertionError: boom\n"
        )
        history = [_interference_turn(1, test_output=noisy)]
        lines = _aggregate_failing_test_lines(history, threshold=3)
        assert lines == ["FAILED tests/test_x.py::test_a"]

    def test_same_test_different_reason_dedupes_by_node_id(self):
        """Repeated same-test-different-message lines collapse to one node-id
        (the anchored extractor strips the `` - <reason>`` suffix)."""
        t1 = _interference_turn(
            1,
            test_output=(
                "FAILED tests/test_x.py::test_a - AssertionError: expected 1"
            ),
        )
        t2 = _interference_turn(
            2,
            test_output=(
                "FAILED tests/test_x.py::test_a - AssertionError: expected 2"
            ),
        )
        lines = _aggregate_failing_test_lines([t1, t2], threshold=3)
        assert lines == ["FAILED tests/test_x.py::test_a"]

    def test_loose_fallback_fires_only_when_anchored_parse_finds_nothing(self):
        """Non-pytest runner output (no anchored node-id lines) still
        surfaces something via the loose marker scan."""
        non_pytest = "ERROR: build failed at step 3"
        history = [_interference_turn(1, test_output=non_pytest)]
        lines = _aggregate_failing_test_lines(history, threshold=3)
        assert lines == ["ERROR: build failed at step 3"]


# ---------------------------------------------------------------------------
# 4. Stall message actionability
# ---------------------------------------------------------------------------


class _FakeWorktreeManager:
    """Minimal stand-in for WorktreeManager used by the summary renderer."""

    def __init__(self, worktrees_dir: Path) -> None:
        self.worktrees_dir = worktrees_dir


def _orchestrator_with_worktree(tmp_path: Path) -> AutoBuildOrchestrator:
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=10,
        worktree_manager=_FakeWorktreeManager(worktrees_dir),
        enable_context=False,
    )


class TestStallMessageActionability:
    """AC: isolation hint + peer names/files + aggregated failing tests."""

    def test_message_contains_isolation_hint_and_peers_when_co_fired(
        self, tmp_path
    ):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        orchestrator._context_pollution_no_checkpoint_fired = True
        history = [
            _interference_turn(
                n, contention_peers={"TASK-SMP-003": ["src/shared.py"]}
            )
            for n in (1, 2, 3)
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        # The existing context-pollution hint is preserved.
        assert "Context pollution detected but no passing checkpoint" in message
        # (a) the parallel-wave isolation hint.
        assert f"[{STALL_PARALLEL_INTERFERENCE}]" in message
        assert "--max-parallel 1" in message
        assert "GUARDKIT_MAX_PARALLEL_TASKS=1" in message
        assert "parallel_groups" in message
        # Peer task and overlapping file named.
        assert "TASK-SMP-003" in message
        assert "src/shared.py" in message
        # (b) the aggregated failing-test lines.
        assert "Failing tests across the stall window" in message
        assert "FAILED tests/test_tutor.py::test_session_flow" in message

    def test_message_omits_isolation_hint_without_interference(self, tmp_path):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        orchestrator._context_pollution_no_checkpoint_fired = True
        history = [_code_failure_turn(n) for n in (1, 2, 3)]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        assert "Context pollution detected but no passing checkpoint" in message
        assert f"[{STALL_PARALLEL_INTERFERENCE}]" not in message
        assert "--max-parallel 1" not in message
        # (b) fires ALWAYS in the context-pollution message, interference or not.
        assert "Failing tests across the stall window" in message
        assert "FAILED tests/test_tutor.py::test_session_flow" in message

    def test_failing_test_block_is_bounded(self, tmp_path):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        orchestrator._context_pollution_no_checkpoint_fired = True
        big_output = "\n".join(
            f"FAILED tests/test_bulk.py::test_case_{i} - AssertionError"
            for i in range(30)
        )
        history = [
            _interference_turn(n, test_output=big_output) for n in (1, 2, 3)
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        failed_lines = [
            line for line in message.splitlines() if "FAILED tests/" in line
        ]
        assert len(failed_lines) == 10
        assert "more line(s) omitted" in message

    # -- 2026-07-04 code review (FIX 1): interference-only stalls -----------

    def test_interference_only_stall_renders_isolation_hint_not_generic(
        self, tmp_path
    ):
        """An interference-ONLY stall (pollution flag False — e.g. the
        ``_is_feedback_stalled`` exit, which never sets
        ``_context_pollution_no_checkpoint_fired``) must carry the isolation
        hint, the remediation, and the peer names — NOT the generic
        task_type hint the pre-fix nesting fell through to."""
        orchestrator = _orchestrator_with_worktree(tmp_path)
        assert orchestrator._context_pollution_no_checkpoint_fired is False
        history = [
            _interference_turn(
                n, contention_peers={"TASK-SMP-003": ["src/shared.py"]}
            )
            for n in (1, 2, 3)
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        # (a) the isolation hint + remediation.
        assert f"[{STALL_PARALLEL_INTERFERENCE}]" in message
        assert "--max-parallel 1" in message
        assert "GUARDKIT_MAX_PARALLEL_TASKS=1" in message
        assert "parallel_groups" in message
        # Peer task and overlapping file named.
        assert "TASK-SMP-003" in message
        assert "src/shared.py" in message
        # (b) the failing-test aggregation renders for interference too.
        assert "Failing tests across the stall window" in message
        assert "FAILED tests/test_tutor.py::test_session_flow" in message
        # NOT the generic task_type hint, and no pollution framing.
        assert "Review task_type classification" not in message
        assert "Context pollution detected" not in message

    def test_interference_only_without_peer_map_still_renders_hint(
        self, tmp_path
    ):
        """The plain ``parallel_contention`` classification names no peers —
        the hint must still render (peer block simply omitted)."""
        orchestrator = _orchestrator_with_worktree(tmp_path)
        history = [_interference_turn(n) for n in (1, 2, 3)]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        assert f"[{STALL_PARALLEL_INTERFERENCE}]" in message
        assert "--max-parallel 1" in message
        assert "Contending peer task(s)" not in message
        assert "Review task_type classification" not in message

    def test_agent_invocations_branch_appends_interference_block(
        self, tmp_path
    ):
        """FIX 1: the additive block is keyed off co_fires alone — it renders
        even when the agent-invocations branch built the primary message."""
        orchestrator = _orchestrator_with_worktree(tmp_path)
        extra = [
            {
                "severity": "must_fix",
                "category": "agent_invocations_violation",
                "description": "Missing phase invocations",
                "details": {
                    "missing_phases": ["4", "5"],
                    "expected_phases": 3,
                    "actual_invocations": 1,
                },
            }
        ]
        history = [
            _turn(
                n,
                _coach_result_with_test_verification(
                    n,
                    contention_peers={"TASK-SMP-003": ["src/shared.py"]},
                    extra_issues=extra,
                ),
            )
            for n in (1, 2, 3)
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        # Primary branch is agent-invocations...
        assert "agent-invocations gate rejected" in message
        # ...and the interference block still renders additively.
        assert f"[{STALL_PARALLEL_INTERFERENCE}]" in message
        assert "--max-parallel 1" in message
        assert "TASK-SMP-003" in message
