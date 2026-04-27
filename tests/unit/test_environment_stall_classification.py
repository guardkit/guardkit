"""Unit tests for TASK-ABSR-C3D4 environment_stall classification.

Covers the new ``environment_stall`` sub-type added to ``classify_stall`` and
the env-aware diagnostic emitted by ``_build_summary_details`` /
``_build_environment_stall_diagnostic``:

1. ``classify_stall`` detects ``environment_stall`` when N recent turns all
   carry an ``all_gates_passed=True`` + ``independent_tests.tests_passed=False``
   + ``test_verification`` issue with ``failure_classification ==
   "infrastructure"`` and identical ``failure_confidence``.
2. The env-stall diagnostic includes the bootstrap state (success/failure,
   installs_attempted, installs_failed) when ``bootstrap_state.json`` exists.
3. The diagnostic names the active Python interpreter and the manifest's
   ``requires-python`` constraint.
4. The classifier does not fire when only one turn matches the pattern.
5. Pre-existing sub-types (agent_invocations, context_pollution,
   coach_feedback_stall) are unchanged for non-env-stall cases.
6. ``environment_stall`` takes precedence over the generic
   ``coach_feedback_stall`` fallback when the pattern matches.

Coverage Target: >=85%
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    STALL_COACH_AGENT_INVOCATIONS,
    STALL_CONTEXT_POLLUTION,
    STALL_ENVIRONMENT,
    STALL_FEEDBACK_GENERIC,
    TurnRecord,
    _extract_environment_stall_signal,
    classify_stall,
)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


def _real_player_result(
    turn: int, task_id: str = "TASK-TEST-ABSR"
) -> AgentInvocationResult:
    """A real Player report used for env-stall fixtures (Player gates pass)."""
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


def _coach_result_with_env_signal(
    turn: int,
    failure_confidence: str = "high",
    task_id: str = "TASK-TEST-ABSR",
    extra_issues: Optional[List[Dict[str, Any]]] = None,
) -> AgentInvocationResult:
    """Build a coach result that carries the environment_stall pattern.

    Player gates passed, independent tests failed, and the
    test_verification issue is classified as infrastructure.
    """
    issues: List[Dict[str, Any]] = list(extra_issues or [])
    issues.append(
        {
            "severity": "must_fix",
            "category": "test_verification",
            "description": "Tests failed due to infrastructure/environment issues",
            "failure_classification": "infrastructure",
            "failure_confidence": failure_confidence,
        }
    )
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": "Independent tests failed (infrastructure).",
            "validation_results": {
                "quality_gates": {
                    "tests_passed": True,
                    "coverage_met": True,
                    "arch_review_passed": True,
                    "plan_audit_passed": True,
                    "all_gates_passed": True,
                },
                "independent_tests": {
                    "tests_passed": False,
                    "test_command": "pytest",
                    "test_output_summary": "ImportError: ...",
                    "duration_seconds": 1.2,
                },
            },
            "issues": issues,
        },
        duration_seconds=0.5,
        error=None,
    )


def _env_stall_turn(
    turn: int,
    failure_confidence: str = "high",
    task_id: str = "TASK-TEST-ABSR",
) -> TurnRecord:
    coach_result = _coach_result_with_env_signal(
        turn, failure_confidence=failure_confidence, task_id=task_id
    )
    return TurnRecord(
        turn=turn,
        player_result=_real_player_result(turn, task_id),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_result.report["feedback"],
        timestamp=f"2026-04-27T11:0{turn}:00Z",
    )


def _generic_coach_feedback_turn(turn: int) -> TurnRecord:
    """Generic coach rejection on AC grounds (no env signal, no agent inv)."""
    feedback = "0/5 acceptance criteria passing."
    coach_result = AgentInvocationResult(
        task_id="TASK-TEST-ABSR",
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": feedback,
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "acceptance_criteria",
                    "description": "0/5 criteria passing",
                }
            ],
        },
        duration_seconds=0.5,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_real_player_result(turn),
        coach_result=coach_result,
        decision="feedback",
        feedback=feedback,
        timestamp=f"2026-04-27T11:0{turn}:00Z",
    )


def _agent_invocations_turn(turn: int) -> TurnRecord:
    """Coach rejection that fires the agent_invocations_violation sub-type."""
    coach_result = AgentInvocationResult(
        task_id="TASK-TEST-ABSR",
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": "Agent-invocations protocol violation: missing phases 4, 5",
            "issues": [
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
            ],
        },
        duration_seconds=0.5,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_real_player_result(turn),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_result.report["feedback"],
        timestamp=f"2026-04-27T11:0{turn}:00Z",
    )


# ---------------------------------------------------------------------------
# AC tests
# ---------------------------------------------------------------------------


class TestExtractEnvironmentStallSignal:
    """Predicate: ``_extract_environment_stall_signal``."""

    def test_returns_issue_when_pattern_matches(self):
        turn = _env_stall_turn(1)
        signal = _extract_environment_stall_signal(turn)
        assert signal is not None
        assert signal["category"] == "test_verification"
        assert signal["failure_classification"] == "infrastructure"

    def test_returns_none_when_quality_gates_failed(self):
        turn = _env_stall_turn(1)
        turn.coach_result.report["validation_results"]["quality_gates"][
            "all_gates_passed"
        ] = False
        assert _extract_environment_stall_signal(turn) is None

    def test_returns_none_when_independent_tests_passed(self):
        turn = _env_stall_turn(1)
        turn.coach_result.report["validation_results"]["independent_tests"][
            "tests_passed"
        ] = True
        assert _extract_environment_stall_signal(turn) is None

    def test_returns_none_when_failure_classification_not_infrastructure(self):
        turn = _env_stall_turn(1)
        turn.coach_result.report["issues"][-1][
            "failure_classification"
        ] = "code_defect"
        assert _extract_environment_stall_signal(turn) is None


class TestClassifyEnvironmentStall:
    """AC: classify_stall fires environment_stall when pattern matches."""

    def test_environment_stall_classification_when_infrastructure_repeated(self):
        history = [
            _env_stall_turn(1, failure_confidence="high"),
            _env_stall_turn(2, failure_confidence="high"),
            _env_stall_turn(3, failure_confidence="high"),
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert STALL_ENVIRONMENT in result.co_fires
        assert result.decision_label == STALL_ENVIRONMENT
        assert result.decision_subtype == STALL_ENVIRONMENT

    def test_environment_stall_does_not_fire_when_only_one_turn_matches(self):
        history = [
            _generic_coach_feedback_turn(1),
            _generic_coach_feedback_turn(2),
            _env_stall_turn(3),
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert STALL_ENVIRONMENT not in result.co_fires
        # Falls through to the generic feedback stall.
        assert STALL_FEEDBACK_GENERIC in result.co_fires

    def test_environment_stall_does_not_fire_when_confidence_varies(self):
        history = [
            _env_stall_turn(1, failure_confidence="high"),
            _env_stall_turn(2, failure_confidence="medium"),
            _env_stall_turn(3, failure_confidence="high"),
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert STALL_ENVIRONMENT not in result.co_fires

    def test_environment_stall_takes_precedence_over_generic_coach_feedback_stall_when_pattern_matches(
        self,
    ):
        history = [
            _env_stall_turn(1, failure_confidence="medium"),
            _env_stall_turn(2, failure_confidence="medium"),
            _env_stall_turn(3, failure_confidence="medium"),
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        # env_stall must beat the default fallback.
        assert STALL_FEEDBACK_GENERIC not in result.co_fires
        assert result.decision_label == STALL_ENVIRONMENT


class TestExistingSubtypesUnchangedForNonEnvStalls:
    """AC: existing sub-types still fire for their own patterns."""

    def test_agent_invocations_stall_takes_precedence_over_env_pattern(self):
        # All three turns carry BOTH an agent_invocations_violation and the
        # env-stall pattern. Per AC, agent_invocations wins.
        coach_with_both = []
        for turn in (1, 2, 3):
            extra = [
                {
                    "severity": "must_fix",
                    "category": "agent_invocations_violation",
                    "description": "Missing phases",
                    "details": {
                        "missing_phases": ["4", "5"],
                        "expected_phases": 3,
                        "actual_invocations": 1,
                    },
                }
            ]
            coach = _coach_result_with_env_signal(turn, extra_issues=extra)
            coach_with_both.append(
                TurnRecord(
                    turn=turn,
                    player_result=_real_player_result(turn),
                    coach_result=coach,
                    decision="feedback",
                    feedback="agent inv + env signal",
                    timestamp=f"2026-04-27T11:0{turn}:00Z",
                )
            )

        result = classify_stall(coach_with_both, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert STALL_COACH_AGENT_INVOCATIONS in result.co_fires
        # env_stall must NOT co-fire when agent_invocations took precedence.
        assert STALL_ENVIRONMENT not in result.co_fires

    def test_context_pollution_takes_precedence_over_env_pattern(self):
        history = [
            _env_stall_turn(1),
            _env_stall_turn(2),
            _env_stall_turn(3),
        ]
        result = classify_stall(
            history,
            "unrecoverable_stall",
            threshold=3,
            context_pollution_fired=True,
        )
        assert result is not None
        assert STALL_CONTEXT_POLLUTION in result.co_fires
        # env_stall must NOT co-fire when context_pollution took precedence.
        assert STALL_ENVIRONMENT not in result.co_fires

    def test_coach_feedback_stall_still_fires_when_no_env_pattern(self):
        history = [
            _generic_coach_feedback_turn(1),
            _generic_coach_feedback_turn(2),
            _generic_coach_feedback_turn(3),
        ]
        result = classify_stall(history, "unrecoverable_stall", threshold=3)
        assert result is not None
        assert result.decision_label == STALL_FEEDBACK_GENERIC

    def test_classify_stall_returns_none_for_non_stall_decisions(self):
        history = [_env_stall_turn(1), _env_stall_turn(2), _env_stall_turn(3)]
        assert classify_stall(history, "approved") is None
        assert classify_stall(history, "max_turns_exceeded") is None


# ---------------------------------------------------------------------------
# Diagnostic renderer tests
# ---------------------------------------------------------------------------


class _FakeWorktreeManager:
    """Minimal stand-in for WorktreeManager used by the diagnostic renderer."""

    def __init__(self, worktrees_dir: Path) -> None:
        self.worktrees_dir = worktrees_dir


def _orchestrator_with_worktree(tmp_path: Path) -> AutoBuildOrchestrator:
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    orchestrator = AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=10,
        worktree_manager=_FakeWorktreeManager(worktrees_dir),
        enable_context=False,
    )
    return orchestrator


def _make_python_worktree(
    worktrees_dir: Path,
    task_id: str,
    requires_python: Optional[str] = ">=3.13",
    bootstrap_state: Optional[Dict[str, Any]] = None,
) -> Path:
    worktree = worktrees_dir / task_id
    worktree.mkdir(parents=True, exist_ok=True)
    pyproject_text = '[project]\nname = "demo"\nversion = "0.1.0"\n'
    if requires_python is not None:
        pyproject_text += f'requires-python = "{requires_python}"\n'
    (worktree / "pyproject.toml").write_text(pyproject_text, encoding="utf-8")
    if bootstrap_state is not None:
        gk_dir = worktree / ".guardkit"
        gk_dir.mkdir(parents=True, exist_ok=True)
        (gk_dir / "bootstrap_state.json").write_text(
            json.dumps(bootstrap_state), encoding="utf-8"
        )
    return worktree


class TestEnvironmentStallDiagnostic:
    """AC: env-aware diagnostic includes bootstrap state, interpreter, and constraint."""

    def test_environment_stall_diagnostic_includes_bootstrap_state(self, tmp_path):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        _make_python_worktree(
            orchestrator._worktree_manager.worktrees_dir,
            task_id,
            requires_python=">=3.13",
            bootstrap_state={
                "success": False,
                "installs_attempted": 1,
                "installs_failed": 1,
                "content_hash": "abc",
                "timestamp": "2026-04-27T00:00:00",
            },
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        message = orchestrator._build_environment_stall_diagnostic(history)
        assert message is not None
        assert "Bootstrap state:" in message
        assert "success=False" in message
        assert "installs_attempted=1" in message
        assert "installs_failed=1" in message
        # The misleading hint must not appear in the env-stall message.
        assert "Review task_type classification" not in message

    def test_environment_stall_diagnostic_names_interpreter_and_constraint(
        self, tmp_path
    ):
        import platform as _platform

        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        _make_python_worktree(
            orchestrator._worktree_manager.worktrees_dir,
            task_id,
            requires_python="<3.13,>=3.12",
            bootstrap_state=None,
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        message = orchestrator._build_environment_stall_diagnostic(history)
        assert message is not None
        assert _platform.python_version() in message
        assert "<3.13,>=3.12" in message
        assert "uv python install" in message
        assert "pyenv install" in message
        assert "conda create" in message
        assert "bootstrap_failure_mode" in message

    def test_environment_stall_diagnostic_falls_through_for_non_python_worktree(
        self, tmp_path
    ):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        # Worktree exists but has no pyproject.toml.
        (orchestrator._worktree_manager.worktrees_dir / task_id).mkdir(
            parents=True, exist_ok=True
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        assert orchestrator._build_environment_stall_diagnostic(history) is None

    def test_environment_stall_diagnostic_handles_missing_bootstrap_state(
        self, tmp_path
    ):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        _make_python_worktree(
            orchestrator._worktree_manager.worktrees_dir,
            task_id,
            requires_python=">=3.13",
            bootstrap_state=None,
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        message = orchestrator._build_environment_stall_diagnostic(history)
        assert message is not None
        # No bootstrap line should appear when the file is absent.
        assert "Bootstrap state:" not in message
        # But the rest of the diagnostic still renders.
        assert ">=3.13" in message

    def test_environment_stall_diagnostic_handles_corrupt_bootstrap_state(
        self, tmp_path
    ):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        worktree = _make_python_worktree(
            orchestrator._worktree_manager.worktrees_dir,
            task_id,
            requires_python=">=3.13",
            bootstrap_state=None,
        )
        gk_dir = worktree / ".guardkit"
        gk_dir.mkdir(parents=True, exist_ok=True)
        (gk_dir / "bootstrap_state.json").write_text(
            "not valid json {{{", encoding="utf-8"
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        message = orchestrator._build_environment_stall_diagnostic(history)
        # Should not raise; diagnostic still produced minus the bootstrap line.
        assert message is not None
        assert "Bootstrap state:" not in message


class TestEnvironmentStallSummaryRouting:
    """AC: _build_summary_details routes env_stall pattern to the env diagnostic."""

    def test_build_summary_details_emits_environment_stall_message(self, tmp_path):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        _make_python_worktree(
            orchestrator._worktree_manager.worktrees_dir,
            task_id,
            requires_python=">=3.13",
            bootstrap_state={
                "success": False,
                "installs_attempted": 1,
                "installs_failed": 1,
            },
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        assert f"[{STALL_ENVIRONMENT}]" in message
        assert "infrastructure-class failures" in message
        assert "Review task_type classification" not in message

    def test_build_summary_details_falls_through_when_env_diagnostic_unavailable(
        self, tmp_path
    ):
        orchestrator = _orchestrator_with_worktree(tmp_path)
        task_id = "TASK-TEST-ABSR"
        # Worktree has no pyproject.toml, so env diagnostic returns None.
        (orchestrator._worktree_manager.worktrees_dir / task_id).mkdir(
            parents=True, exist_ok=True
        )
        history = [
            _env_stall_turn(1, task_id=task_id),
            _env_stall_turn(2, task_id=task_id),
            _env_stall_turn(3, task_id=task_id),
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        # Falls through to the generic stall message.
        assert "Unrecoverable stall detected" in message
        assert f"[{STALL_ENVIRONMENT}]" not in message
