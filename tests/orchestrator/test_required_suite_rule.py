"""Reliability repair 1 (12 October 2026): a red required suite blocks on every path.

B463's first task — declarative, built in direct mode — was approved with
1 failed / 871 passed in the Coach's own independent run. The deterministic
backstop acted only for ``testing`` tasks; direct-mode tasks and turns whose
Phase 4 was skipped for budget had nothing else to catch them, and the legacy
``validate()`` path approved a code failure in a parallel wave.

These tests drive the REAL caller, ``AutoBuildOrchestrator._invoke_coach_primary``
— real ``CoachValidator.gather_evidence`` over a real worktree, real
``AgentInvoker.invoke_coach`` with only the model call replaced by an
``approve`` verdict, real guards, real ``coach_turn_N.json``. (The legacy
``validate()`` path was deleted in the cull, 27 October 2026, with its tests.)

The independent test run is the seam (no suite is executed), and so is the
failure classifier, so each path can be run with ``code``,
``infrastructure``, ``parallel_contention`` and a missing classification. Each
asserts the returned decision AND the persisted one.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.harness import AssistantMessageEvent, ResultMessageEvent
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_evidence import (
    IndependentTestClassification,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.quality_gates.required_suite import (
    REQUIRED_SUITE_FAILURE_CATEGORY,
)


TASK_ID = "TASK-B463-001"

# B463's shape: one real failure among hundreds of passes.
_RED_OUTPUT = (
    "FAILED tests/test_conftest_database_url.py::test_database_url - "
    "AssertionError\n"
    "1 failed, 871 passed in 41.20s\n"
)
_GREEN_OUTPUT = "872 passed in 40.10s\n"

CLASSES = ["code", "infrastructure", "parallel_contention", None]


@pytest.fixture(autouse=True)
def _pin_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")


# ---------------------------------------------------------------------------
# A real worktree with the task's own results
# ---------------------------------------------------------------------------


def _git_worktree(path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    for key, value in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(
            ["git", "-C", str(path), "config", key, value],
            check=True,
            capture_output=True,
        )
    return path


def _write_results(worktree: Path, *, mode: str) -> None:
    """task_work_results.json for a turn whose own gates all passed.

    ``mode="direct"``: the direct-mode writer's shape (relaxed gates, no
    Phase 4). ``mode="task-work"``: a task-work turn whose orchestrator Phase 4
    was skipped for budget (the record ``autobuild.py`` writes in that case).
    """
    quality_gates: Dict[str, Any] = {
        "all_passed": True,
        "tests_passing": True,
        "tests_passed": 871,
        "tests_failed": 0,
        "coverage_met": True,
    }
    results: Dict[str, Any] = {
        "task_id": TASK_ID,
        "implementation_mode": mode,
        "completed": True,
        "success": True,
        "quality_gates": quality_gates,
        "files_created": [],
        "files_modified": ["src/settings.py"],
        "tests_written": [],
        "completion_promises": [{"criterion_id": "AC-001", "status": "complete"}],
        "requirements_met": ["AC-001"],
        "requirements_addressed": ["AC-001"],
        "plan_audit": {"violations": 0, "severity": "low"},
        "code_review": {"score": 90},
    }
    if mode == "direct":
        quality_gates["quality_gates_relaxed"] = True
    else:
        results["agent_invocations"] = [
            {
                "phase": "4",
                "agent": "test-orchestrator",
                "status": "skipped",
                "error": "specialist_skipped: budget exhausted "
                "(post_player_remaining=12.0s)",
                "source": "orchestrator",
            }
        ]
    # The file the turn says it changed exists.
    (worktree / "src").mkdir(exist_ok=True)
    (worktree / "src" / "settings.py").write_text("DATABASE_URL = 'x'\n")
    path = TaskArtifactPaths.task_work_results_path(TASK_ID, worktree)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results))


def _independent(output: str, *, passed: bool) -> IndependentTestResult:
    return IndependentTestResult.from_run(
        tests_passed=passed,
        test_command="bash qa/run-suite.sh",
        test_output_summary="1 failed, 871 passed" if not passed else "872 passed",
        duration_seconds=41.2,
        output=output,
        resolved_interpreter=None,
    )


def _persisted(worktree: Path, turn: int = 1) -> Dict[str, Any]:
    path = TaskArtifactPaths.private_artifact_path(
        TASK_ID, f"coach_turn_{turn}.json", worktree
    )
    return json.loads(path.read_text())


def _blocked_by_rule(report: Dict[str, Any]) -> bool:
    return any(
        issue.get("category") == REQUIRED_SUITE_FAILURE_CATEGORY
        for issue in report.get("issues", [])
    )


class _Worktree:
    def __init__(self, path: Path) -> None:
        self.path = path


# ---------------------------------------------------------------------------
# The primary path
# ---------------------------------------------------------------------------


def _approving_invoker(worktree: Path) -> AgentInvoker:
    """A real AgentInvoker whose only fake is the model: it always approves."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = lambda *a, **k: 600  # type: ignore[method-assign]
    invoker._venv_python = None
    verdict = {
        "task_id": TASK_ID,
        "turn": 1,
        "decision": "approve",
        "rationale": "The failure looks environmental; approving.",
        "criteria_verification": [],
    }
    events = [
        AssistantMessageEvent(text="```json\n" + json.dumps(verdict) + "\n```"),
        ResultMessageEvent(session_id=None),
    ]
    invoker._invoke_with_role = AsyncMock(return_value=(None, events))  # type: ignore[method-assign]
    return invoker


def _run_primary(
    worktree: Path,
    *,
    task_type: str,
    independent: Optional[IndependentTestResult],
    failure_class: Optional[str] = "code",
    wave_size: int = 1,
    requires_infrastructure: Optional[list] = None,
    docker_available: bool = True,
):
    """Drive ``_invoke_coach_primary`` with the test run and classifier as seams."""
    original_gather = CoachValidator.gather_evidence

    def _gather(self, *args, **kwargs):
        bundle = original_gather(self, *args, **kwargs)
        it = bundle.independent_tests
        if it is not None and it.tests_passed is False and not it.signal_absent:
            bundle.independent_test_classification = (
                IndependentTestClassification(
                    failure_class=failure_class,
                    confidence="high",
                    raw_output_excerpt=(it.raw_output or "")[-500:],
                )
                if failure_class is not None
                else None
            )
        return bundle

    orch = AutoBuildOrchestrator(
        repo_root=worktree,
        enable_pre_loop=False,
        agent_invoker=_approving_invoker(worktree),
    )
    with patch.object(
        CoachValidator, "run_independent_tests", return_value=independent
    ), patch.object(CoachValidator, "gather_evidence", _gather), patch.object(
        CoachValidator, "_is_docker_available", return_value=docker_available
    ):
        return orch._invoke_coach_primary(
            task_id=TASK_ID,
            turn=1,
            requirements="Read the database URL from settings.",
            player_report={"task_id": TASK_ID, "files_modified": ["src/settings.py"]},
            worktree=_Worktree(worktree),
            acceptance_criteria=["AC-001: read the database URL from settings"],
            task_type=task_type,
            skip_arch_review=True,
            requires_infrastructure=requires_infrastructure,
            consumer_context=None,
            remaining_budget=None,
            wave_size=wave_size,
            context_prompt="",
            start_time=0.0,
        )


class TestPrimaryDeclarativeDirectMode:
    """B463's shape: declarative task, direct mode, no deterministic Phase 4."""

    @pytest.mark.parametrize("failure_class", CLASSES)
    def test_red_required_suite_is_not_approved(
        self, tmp_path: Path, failure_class: Optional[str]
    ) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")

        result = _run_primary(
            wt,
            task_type="declarative",
            independent=_independent(_RED_OUTPUT, passed=False),
            failure_class=failure_class,
        )

        assert result.report["decision"] == "feedback"
        assert _blocked_by_rule(result.report)
        persisted = _persisted(wt)
        assert persisted["decision"] == "feedback"
        assert _blocked_by_rule(persisted)
        issue = persisted["issues"][0]
        assert issue["details"]["failure_class"] == failure_class
        if failure_class in ("infrastructure", "parallel_contention"):
            assert "do not change code for it" in issue["description"]

    def test_passing_run_is_approved(self, tmp_path: Path) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")

        result = _run_primary(
            wt,
            task_type="declarative",
            independent=_independent(_GREEN_OUTPUT, passed=True),
        )

        assert result.report["decision"] == "approve"
        assert _persisted(wt)["decision"] == "approve"


class TestPrimaryTaskWorkPhase4SkippedForBudget:
    """A task-work turn whose Phase 4 was skipped for budget (7010 turn 4)."""

    @pytest.mark.parametrize("failure_class", CLASSES)
    def test_red_required_suite_is_not_approved(
        self, tmp_path: Path, failure_class: Optional[str]
    ) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")

        result = _run_primary(
            wt,
            task_type="feature",
            independent=_independent(_RED_OUTPUT, passed=False),
            failure_class=failure_class,
            wave_size=3,
        )

        assert result.report["decision"] == "feedback"
        assert _blocked_by_rule(result.report)
        persisted = _persisted(wt)
        assert persisted["decision"] == "feedback"
        assert _blocked_by_rule(persisted)


class TestPrimaryPositiveControls:
    def test_signal_absent_is_not_sent_back_it_stops(self, tmp_path: Path) -> None:
        """A run that said nothing (here a timeout) is not a red suite, so
        nothing goes back to the builder; it is not a pass either, so the task
        stops with the reason (31 October 2026)."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")
        absent = IndependentTestResult.absent(
            test_command="bash qa/run-suite.sh",
            test_output_summary="timed out after 300s",
            duration_seconds=300.0,
        )

        result = _run_primary(wt, task_type="declarative", independent=absent)

        assert result.success is False
        assert "timed out after 300s" in result.error
        assert not _blocked_by_rule(result.report)

    def test_check_could_not_run_stops_the_task_without_a_builder_turn(
        self, tmp_path: Path
    ) -> None:
        """31 October 2026: a check that could not run is neither approved nor
        sent back; the Coach turn fails with the reason, which ends the task
        before the reviewer runs."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")
        could_not = IndependentTestResult.could_not_run(
            test_command="bash qa/run-suite.sh",
            detail="bash qa/run-suite.sh could not start in /w: no such file",
            duration_seconds=0.1,
        )

        result = _run_primary(wt, task_type="declarative", independent=could_not)

        assert result.success is False
        assert result.error.startswith("The check could not run")
        assert "bash qa/run-suite.sh" in result.error
        assert result.report == {}

    def test_a_scaffolding_task_whose_part_failed_is_sent_back(
        self, tmp_path: Path
    ) -> None:
        """No task-type exemption: the tests that run are the changed parts'
        (31 October 2026)."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")

        result = _run_primary(
            wt,
            task_type="scaffolding",
            independent=_independent(_RED_OUTPUT, passed=False),
        )

        assert _blocked_by_rule(result.report)
        assert result.report["decision"] == "feedback"

    def test_collection_error_gets_neutral_words(self, tmp_path: Path) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")

        result = _run_primary(
            wt,
            task_type="declarative",
            independent=_independent(_RED_OUTPUT, passed=False),
            failure_class="collection_error",
        )

        assert result.report["decision"] == "feedback"
        rationale = _persisted(wt)["rationale"]
        assert "could not import or collect" in rationale
        assert "do not change code for it" not in rationale
