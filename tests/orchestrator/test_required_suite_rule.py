"""Reliability repair 1 (12 October 2026): a red required suite blocks on every path.

B463's first task — declarative, built in direct mode — was approved with
1 failed / 871 passed in the Coach's own independent run. The deterministic
backstop acted only for ``testing`` tasks; direct-mode tasks and turns whose
Phase 4 was skipped for budget had nothing else to catch them, and the legacy
``validate()`` path approved a code failure in a parallel wave.

These tests drive the REAL callers:

* the primary path, ``AutoBuildOrchestrator._invoke_coach_primary`` — real
  ``CoachValidator.gather_evidence`` over a real worktree, real
  ``AgentInvoker.invoke_coach`` with only the model call replaced by an
  ``approve`` verdict, real guards, real ``coach_turn_N.json``;
* the legacy path, ``AutoBuildOrchestrator._invoke_coach_legacy`` — real
  ``CoachValidator.validate`` and ``save_decision``.

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
from guardkit.orchestrator.baseline import (
    BaselineResult,
    feature_baseline_path,
    write_baseline,
)
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
    monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
    monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
    monkeypatch.delenv("GUARDKIT_AUTOBUILD_BASELINE_DIFF", raising=False)


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
    # The file the turn says it changed exists, so the honesty check passes
    # and gathering reaches the independent run.
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


def _measured_red_base(worktree: Path) -> None:
    """A measured baseline naming exactly the one failure the run reports."""
    write_baseline(
        feature_baseline_path(worktree, "FEAT-B463"),
        BaselineResult(
            command="bash qa/run-suite.sh",
            expected_exit=0,
            passed=False,
            exit_code=1,
            failing_node_ids=[
                "tests/test_conftest_database_url.py::test_database_url"
            ],
            failing_count=1,
            timestamp="2026-10-12T00:00:00",
        ),
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
            peer_changed_files=None,
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
    def test_signal_absent_keeps_todays_handling(self, tmp_path: Path) -> None:
        """Unavailable evidence is owned by the absent guard, not this rule."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")
        absent = IndependentTestResult.absent(
            test_command="bash qa/run-suite.sh",
            test_output_summary="timed out after 300s",
            duration_seconds=300.0,
        )

        result = _run_primary(wt, task_type="declarative", independent=absent)

        assert result.report["decision"] == "feedback"
        assert not _blocked_by_rule(result.report)
        assert any(
            i.get("category") == "absence_of_failure"
            for i in result.report["issues"]
        )

    def test_check_could_not_run_keeps_todays_handling(self, tmp_path: Path) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")
        could_not = IndependentTestResult.could_not_run(
            test_command="bash qa/run-suite.sh",
            detail="bash qa/run-suite.sh could not start in /w: no such file",
            duration_seconds=0.1,
        )

        result = _run_primary(wt, task_type="declarative", independent=could_not)

        assert not _blocked_by_rule(result.report)
        assert not _blocked_by_rule(_persisted(wt))

    def test_type_not_requiring_tests_is_skipped_as_today(
        self, tmp_path: Path
    ) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")

        result = _run_primary(
            wt,
            task_type="scaffolding",
            independent=_independent(_RED_OUTPUT, passed=False),
        )

        assert not _blocked_by_rule(result.report)
        assert result.report["decision"] == "approve"

    def test_every_failure_on_a_measured_baseline_is_approved(
        self, tmp_path: Path
    ) -> None:
        """The baseline exception: every failure verified as pre-existing."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")
        write_baseline(
            feature_baseline_path(wt, "FEAT-B463"),
            BaselineResult(
                command="bash qa/run-suite.sh",
                expected_exit=0,
                passed=False,
                exit_code=1,
                failing_node_ids=[
                    "tests/test_conftest_database_url.py::test_database_url"
                ],
                failing_count=1,
                timestamp="2026-10-12T00:00:00",
            ),
        )

        result = _run_primary(
            wt,
            task_type="declarative",
            independent=_independent(_RED_OUTPUT, passed=False),
        )

        assert result.report["decision"] == "approve"
        assert _persisted(wt)["decision"] == "approve"

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

    def test_an_unmeasured_baseline_excuses_nothing(self, tmp_path: Path) -> None:
        """Repair 2: a base that failed at import named nothing, so it cannot
        stand as the baseline exception."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="direct")
        write_baseline(
            feature_baseline_path(wt, "FEAT-B463"),
            BaselineResult(
                command="bash qa/run-suite.sh",
                expected_exit=0,
                passed=False,
                exit_code=4,
                failing_node_ids=[],
                failing_count=0,
                timestamp="2026-10-12T00:00:00",
            ),
        )

        result = _run_primary(
            wt,
            task_type="declarative",
            independent=_independent(_RED_OUTPUT, passed=False),
        )

        assert result.report["decision"] == "feedback"
        assert _blocked_by_rule(_persisted(wt))


# ---------------------------------------------------------------------------
# The legacy path (GUARDKIT_COACH_LEGACY=1)
# ---------------------------------------------------------------------------


# Each legacy case is a shape validate() APPROVES today, so the override is
# what the test exercises: (wave size, what validate()'s classifier returns,
# what the wording step's classifier returns, bootstrap broken?).
LEGACY_HOLES = {
    # A code failure in a parallel wave (TASK-ABFIX-005 conditional approval).
    "code": (3, ("code", "high"), ("code", "high"), False),
    # Parallel contention with no source-file overlap.
    "parallel_contention": (
        3, ("parallel_contention", "high"), ("parallel_contention", "high"), False,
    ),
    # The broken-bootstrap environment amnesty (TASK-ABSR-2468).
    "infrastructure": (
        1, ("infrastructure", "ambiguous"), ("infrastructure", "ambiguous"), True,
    ),
    # validate() approves on contention; the wording step gets no class.
    None: (3, ("parallel_contention", "high"), (None, None), False),
}


def _legacy_patches(
    independent: IndependentTestResult,
    classifications: list,
    *,
    docker_available: bool = True,
    bootstrap_broken: bool = False,
):
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(
        patch.object(CoachValidator, "run_independent_tests", return_value=independent)
    )
    stack.enter_context(
        patch.object(
            CoachValidator,
            "_classify_test_failure",
            side_effect=list(classifications) + [classifications[-1]] * 4,
        )
    )
    stack.enter_context(
        patch.object(
            CoachValidator, "_is_docker_available", return_value=docker_available
        )
    )
    stack.enter_context(
        patch.object(
            CoachValidator, "_bootstrap_likely_broken", return_value=bootstrap_broken
        )
    )
    return stack


def _validate_today(
    worktree: Path,
    independent: IndependentTestResult,
    classification: tuple,
    *,
    wave_size: int,
    bootstrap_broken: bool = False,
    requires_infrastructure: Optional[list] = None,
    docker_available: bool = True,
):
    """What validate() alone decides — the precondition proving the hole."""
    with _legacy_patches(
        independent,
        [classification],
        docker_available=docker_available,
        bootstrap_broken=bootstrap_broken,
    ):
        return CoachValidator(str(worktree), task_id=TASK_ID, wave_size=wave_size).validate(
            task_id=TASK_ID,
            turn=1,
            task={
                "acceptance_criteria": ["AC-001: read the database URL from settings"],
                "task_type": "declarative",
                "requires_infrastructure": requires_infrastructure or [],
                "_docker_available": docker_available,
            },
            skip_arch_review=True,
        )


def _run_legacy(
    worktree: Path,
    *,
    task_type: str,
    independent: IndependentTestResult,
    classifications: Optional[list] = None,
    wave_size: int = 1,
    requires_infrastructure: Optional[list] = None,
    docker_available: bool = True,
    bootstrap_broken: bool = False,
):
    orch = AutoBuildOrchestrator(repo_root=worktree, enable_pre_loop=False)
    with _legacy_patches(
        independent,
        classifications or [("code", "high")],
        docker_available=docker_available,
        bootstrap_broken=bootstrap_broken,
    ):
        return orch._invoke_coach_legacy(
            task_id=TASK_ID,
            turn=1,
            requirements="Read the database URL from settings.",
            player_report={"task_id": TASK_ID},
            worktree=_Worktree(worktree),
            acceptance_criteria=["AC-001: read the database URL from settings"],
            task_type=task_type,
            skip_arch_review=True,
            requires_infrastructure=requires_infrastructure,
            consumer_context=None,
            remaining_budget=None,
            wave_size=wave_size,
            peer_changed_files=None,
            context_prompt="",
            start_time=0.0,
        )


class TestLegacyPath:
    @pytest.mark.parametrize("failure_class", CLASSES)
    def test_a_red_suite_validate_approves_is_not_approved(
        self, tmp_path: Path, failure_class: Optional[str]
    ) -> None:
        """Every class, in a shape validate() itself approves today: the rule
        applied in _invoke_coach_legacy turns it to feedback, persisted."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")
        wave, judged, worded, broken = LEGACY_HOLES[failure_class]
        red = _independent(_RED_OUTPUT, passed=False)

        today = _validate_today(
            wt, red, judged, wave_size=wave, bootstrap_broken=broken
        )
        assert today.decision == "approve"  # the hole

        result = _run_legacy(
            wt,
            task_type="declarative",
            independent=red,
            classifications=[judged, worded],
            wave_size=wave,
            bootstrap_broken=broken,
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"
        assert _blocked_by_rule(result.report)
        persisted = _persisted(wt)
        assert persisted["decision"] == "feedback"
        assert _blocked_by_rule(persisted)
        assert persisted["approved_without_independent_tests"] is False
        assert persisted["environment_conditional_approval"] is False
        assert persisted["issues"][0]["details"]["failure_class"] == failure_class

    def test_collection_error_approval_is_closed_with_neutral_words(
        self, tmp_path: Path
    ) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")
        red = _independent(_RED_OUTPUT, passed=False)
        judged = ("collection_error", "high")

        assert _validate_today(wt, red, judged, wave_size=1).decision == "approve"

        result = _run_legacy(
            wt, task_type="declarative", independent=red,
            classifications=[judged, judged],
        )

        assert result.report["decision"] == "feedback"
        persisted = _persisted(wt)
        assert persisted["decision"] == "feedback"
        assert "could not import or collect" in persisted["rationale"]
        assert "do not change code for it" not in persisted["rationale"]

    def test_every_failure_on_a_measured_baseline_is_approved(
        self, tmp_path: Path
    ) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")
        _measured_red_base(wt)

        result = _run_legacy(
            wt,
            task_type="declarative",
            independent=_independent(_RED_OUTPUT, passed=False),
        )

        assert result.report["decision"] == "approve"
        assert _persisted(wt)["decision"] == "approve"

    def test_declared_infrastructure_without_docker_is_not_approved(
        self, tmp_path: Path
    ) -> None:
        """validate() conditionally approves a red suite whose declared
        infrastructure has no Docker; the shared rule makes it ordinary
        feedback (unavailable evidence keeps today's handling; this run
        actually ran and failed)."""
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")
        red = _independent(_RED_OUTPUT, passed=False)
        judged = ("infrastructure", "high")

        assert _validate_today(
            wt, red, judged, wave_size=1,
            requires_infrastructure=["postgresql"], docker_available=False,
        ).decision == "approve"

        result = _run_legacy(
            wt,
            task_type="declarative",
            independent=red,
            classifications=[judged, judged],
            requires_infrastructure=["postgresql"],
            docker_available=False,
        )

        persisted = _persisted(wt)
        for report in (result.report, persisted):
            assert report["decision"] == "feedback"
            assert _blocked_by_rule(report)
            assert report["is_configuration_error"] is False
            assert report["approved_without_independent_tests"] is False

    def test_passing_run_is_approved(self, tmp_path: Path) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")

        result = _run_legacy(
            wt,
            task_type="declarative",
            independent=_independent(_GREEN_OUTPUT, passed=True),
        )

        assert result.report["decision"] == "approve"
        assert _persisted(wt)["decision"] == "approve"

    def test_signal_absent_is_not_this_rule(self, tmp_path: Path) -> None:
        wt = _git_worktree(tmp_path)
        _write_results(wt, mode="task-work")
        absent = IndependentTestResult.absent(
            test_command="bash qa/run-suite.sh",
            test_output_summary="timed out after 300s",
            duration_seconds=300.0,
        )

        result = _run_legacy(wt, task_type="declarative", independent=absent)

        assert not _blocked_by_rule(result.report)
        assert not _blocked_by_rule(_persisted(wt))
