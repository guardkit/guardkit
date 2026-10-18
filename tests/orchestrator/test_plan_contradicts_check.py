"""The FEAT-15DD replay: a repair round stops early when the plan contradicts
the project's own check (design of 18 October 2026, accepted by review).

What happened in FEAT-15DD (17 October 2026)
--------------------------------------------
The plan's AC-003 asked for the singular "1 note"; the project's committed
whole-feature check reads the same label as "N notes" for every count. The
first round's Coach approved "1 note", the whole-feature check then failed,
and the repair round began. In repair turn 1 the coder wrote "N notes", ran the
check itself (it passed) and marked AC-003 ``incomplete``, explaining that the
two cannot both hold. The direct-mode evidence gate sent that turn back before
any model saw it. Repair turn 2 went back to "1 note", the model Coach approved
it, and attempt 2 of the check failed again: about 18 more minutes for the
same failure, and a reason that never said why.

What this file proves, with no model called
-------------------------------------------
* The replay drives the REAL path for repair turn 1: ``_loop_phase`` ->
  ``_execute_turn`` -> ``_invoke_coach_safely`` -> ``_invoke_coach_primary`` ->
  ``CoachValidator.gather_evidence`` (which runs the check once through the
  repair's runner) -> the evidence-repo gate -> the direct-mode gate ->
  ``_emit_synthetic_coach_feedback`` -> the ``TurnRecord`` -> the stop. The
  saved ``player_turn_1.json`` stands in for the Player (no model), and the
  check runner is the only other stand-in: it returns a passing attempt.
* The report carries ``direct_mode_blockers`` as data, the stop fires with the
  one plain sentence, the task's result carries it, and at the feature level
  the receipt gets ``stopped_because`` and no second attempt runs.
* Every control in the design gives today's behaviour.

Fixtures (``tests/fixtures/feat-15dd-early-stop-2026-10-18``) are the saved
records, copied read-only from the build's receipts with paths scrubbed. The
build's own worktree lived in the sandbox and is gone, so the two changed
source files are short stand-ins showing the wording each turn chose; nothing
on this path reads their contents for a verdict.
"""

from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import (
    STALL_PLAN_CONTRADICTS_CHECK,
    AutoBuildOrchestrator,
    TurnRecord,
    _criteria_only_rejection,
    _extract_direct_mode_blockers,
    classify_stall,
)
from guardkit.orchestrator.feature_check import (
    FeatureCheckAttempt,
    FeatureCheckRepair,
    OUTCOME_FAILED,
    OUTCOME_PASSED,
)
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "feat-15dd-early-stop-2026-10-18"
)
TASK_ID = "TASK-15DD-001"
BRANCH = "autobuild/FEAT-15DD"
CHECK = "bash scripts/check-feature.sh"
REQUEST = (
    "Show how many notes I have, as a count label directly above the notes list."
)


def _load(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _criteria() -> List[str]:
    """The task's six acceptance criteria, in order, from the saved promises."""
    report = _load("repair_player_turn_1.json")
    return [p["criterion_text"] for p in report["completion_promises"]]


def failed_attempt() -> FeatureCheckAttempt:
    """Attempt 1 exactly as recorded: the check failed (exit 1)."""
    data = _load("failed_attempt_1.json")
    return FeatureCheckAttempt(
        attempt=data["attempt"],
        command=data["command"],
        candidate_sha=data["candidate_sha"],
        passed=False,
        outcome=OUTCOME_FAILED,
        exit_code=data["exit_code"],
        timed_out=data["timed_out"],
        duration_seconds=data["duration_seconds"],
        stdout_tail=data["stdout_tail"],
        stderr_tail=data["stderr_tail"],
        failure_reason=data["failure_reason"],
    )


def passing_attempt(attempt: int = 1) -> FeatureCheckAttempt:
    """What GuardKit's own run printed on repair turn 1's code (it passed)."""
    return FeatureCheckAttempt(
        attempt=attempt,
        command=CHECK,
        candidate_sha="0" * 40,
        passed=True,
        outcome=OUTCOME_PASSED,
        exit_code=0,
        stdout_tail="  3 passed (31.0s)\ncheck-feature: PASS run=20261017083551-0bd78c exit=0",
        stderr_tail="",
    )


# ---------------------------------------------------------------------------
# The project: a tiny git repository standing in for the notes fixture
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


APP_BEFORE = (
    "export function App() {\n"
    "  return <ul aria-label=\"Your notes\" />;\n"
    "}\n"
)
APP_PLURAL = (
    "// Stand-in for repair turn 1: the label reads 'N notes' for every count.\n"
    "const noteCountLabel = (count: number) => `${count} notes`;\n"
    "export function App() { return null; }\n"
)
APP_SINGULAR = (
    "// Stand-in for repair turn 2: '1 note' for a count of one.\n"
    "const noteCountLabel = (count: number) =>\n"
    "  `${count} ${count === 1 ? 'note' : 'notes'}`;\n"
    "export function App() { return null; }\n"
)


def make_project(root: Path) -> Path:
    repo = root / "notes"
    (repo / "apps" / "web" / "src").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "apps" / "web" / "src" / "App.tsx").write_text(APP_BEFORE)
    (repo / "apps" / "web" / "src" / "App.test.tsx").write_text("// tests\n")
    # The task's own test command exits 0, as the real check.sh did.
    (repo / "scripts" / "check.sh").write_text("#!/bin/sh\necho 'check: ok'\nexit 0\n")
    # The whole-feature check itself is never run here: its runner is the
    # one stand-in on this path.
    (repo / "scripts" / "check-feature.sh").write_text("#!/bin/sh\nexit 99\n")
    (repo / ".guardkit").mkdir()
    (repo / ".guardkit" / "config.yaml").write_text(
        "toolchain:\n"
        '  test: "bash scripts/check.sh"\n'
        f'  feature_check: "{CHECK}"\n'
    )
    tasks = repo / "tasks" / "backlog"
    tasks.mkdir(parents=True)
    (tasks / f"{TASK_ID}-add-count-label.md").write_text(
        "---\n"
        f"id: {TASK_ID}\n"
        "title: Add the notes count label\n"
        "status: backlog\n"
        "complexity: 3\n"
        "implementation_mode: direct\n"
        "task_type: feature\n"
        "---\n\n# Add the notes count label\n\n## Acceptance Criteria\n\n"
        + "".join(f"- [ ] {c}\n" for c in _criteria())
    )
    _git(repo, "init", "-q", "-b", BRANCH)
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


class _WorktreeManager:
    def __init__(self, worktrees_dir: Path) -> None:
        self.worktrees_dir = worktrees_dir


def make_orchestrator(
    repo: Path,
    *,
    repair: Optional[FeatureCheckRepair],
    model_verdict: Optional[Dict[str, Any]] = None,
    wave_size: int = 1,
) -> AutoBuildOrchestrator:
    """A real task orchestrator; only the model is absent.

    ``model_verdict`` is what the model Coach would have answered, for the
    turns that reach it (repair turn 1 must never reach it).
    """
    invoker = AgentInvoker(worktree_path=repo)

    async def _coach(**kwargs: Any) -> AgentInvocationResult:
        if model_verdict is None:
            raise AssertionError("the model Coach must not be called on this turn")
        return AgentInvocationResult(
            task_id=TASK_ID,
            turn=kwargs.get("turn", 1),
            agent_type="coach",
            success=True,
            report=deepcopy(model_verdict),
            duration_seconds=1.0,
        )

    invoker.invoke_coach = AsyncMock(side_effect=_coach)  # type: ignore[method-assign]
    worktrees_dir = repo / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    orch = AutoBuildOrchestrator(
        repo_root=repo,
        max_turns=5,
        enable_pre_loop=False,
        enable_context=False,
        agent_invoker=invoker,
        worktree_manager=_WorktreeManager(worktrees_dir),
        wave_size=wave_size,
        feature_check_repair=repair,
    )
    orch._progress_display = MagicMock()
    snapshot_task_toolchain(TASK_ID, repo, repo)
    return orch


def player_from(
    repo: Path, reports: List[Dict[str, Any]], sources: List[str]
) -> Callable[..., AgentInvocationResult]:
    """The saved Player reports stand in for the Player, turn by turn.

    Each turn changes the label file as that turn did, writes the saved
    ``player_turn_N.json`` where the Player writes it, and lets the real
    direct-mode results writer produce ``task_work_results.json``.
    """
    invoker = AgentInvoker(worktree_path=repo)
    calls = iter(zip(reports, sources))

    def _invoke_player_safely(*, task_id: str, turn: int, **_: Any) -> AgentInvocationResult:
        report, source = next(calls)
        report = deepcopy(report)
        report["turn"] = turn
        (repo / "apps" / "web" / "src" / "App.tsx").write_text(source)
        (repo / "apps" / "web" / "src" / "App.test.tsx").write_text(
            f"// tests for turn {turn}\n"
        )
        folder = repo / ".guardkit" / "autobuild" / task_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"player_turn_{turn}.json").write_text(json.dumps(report, indent=2))
        invoker._write_direct_mode_results(task_id, report, success=True)
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=True,
            report=report,
            duration_seconds=878.0,
        )

    return _invoke_player_safely


def run_loop(
    orch: AutoBuildOrchestrator,
    repo: Path,
    reports: List[Dict[str, Any]],
    sources: List[str],
):
    orch._invoke_player_safely = player_from(repo, reports, sources)  # type: ignore[method-assign]
    worktree = SimpleNamespace(
        task_id=TASK_ID, path=repo, branch_name=BRANCH, base_branch="main"
    )
    return orch._loop_phase(
        task_id=TASK_ID,
        requirements=REQUEST,
        acceptance_criteria=_criteria(),
        worktree=worktree,
        task_type="feature",
    )


def counting_runner(result: Any) -> Callable[[], FeatureCheckAttempt]:
    """A check runner that returns ``result`` (or raises it) and counts calls."""

    def _run() -> FeatureCheckAttempt:
        _run.calls += 1  # type: ignore[attr-defined]
        if isinstance(result, BaseException):
            raise result
        return result

    _run.calls = 0  # type: ignore[attr-defined]
    return _run


def repair_with(runner: Optional[Callable[[], FeatureCheckAttempt]]) -> FeatureCheckRepair:
    return FeatureCheckRepair(
        failed_attempt=failed_attempt(), request_words=REQUEST, run=runner
    )


# ---------------------------------------------------------------------------
# 1. The replay: repair turn 1 stops, with the sentence
# ---------------------------------------------------------------------------


class TestTheReplayStops:
    def test_repair_turn_1_stops_with_the_sentence(self, tmp_path: Path) -> None:
        repo = make_project(tmp_path)
        runner = counting_runner(passing_attempt())
        orch = make_orchestrator(repo, repair=repair_with(runner))

        history, decision = run_loop(
            orch, repo, [_load("repair_player_turn_1.json")], [APP_PLURAL]
        )

        # One turn, then the stop: no Player turn 2, no model Coach turn.
        assert decision == "unrecoverable_stall"
        assert len(history) == 1
        assert runner.calls == 1, "GuardKit runs the check once per Coach turn"
        orch._agent_invoker.invoke_coach.assert_not_called()

        # The gate's blockers reached the loop as data, never as text.
        report = history[0].coach_result.report
        assert report["direct_mode_blockers"] == [
            {"category": "direct_mode_ac_unverified", "unmet_ids": ["AC-003"]}
        ]
        assert _extract_direct_mode_blockers(history[0]) == [
            {"category": "direct_mode_ac_unverified", "unmet_ids": ["AC-003"]}
        ]
        assert _criteria_only_rejection(history[0]) == ["AC-003"]

        sentence = orch._plan_contradicts_check_sentence
        assert sentence is not None
        assert sentence.startswith(
            "The plan contradicts the project's own check: the project's "
            "declared feature check failed while AC-003 (\""
        )
        assert "a count of `1` reads the singular `1 note`" in sentence
        assert "was met, and passes on the coder's version that leaves it out" in sentence
        checkpoint = _git(repo, "rev-parse", "HEAD")
        assert f"commit `{checkpoint[:12]}`" in sentence
        # The command is never published in the sentence (13 October rule).
        assert CHECK not in sentence

        # The task's result says it: sub-type, error and stopped_because.
        classification = classify_stall(
            history, decision, plan_contradicts_check_fired=True
        )
        assert classification.decision_label == STALL_PLAN_CONTRADICTS_CHECK
        assert orch._build_error_message(decision, history) == sentence

    def test_the_bundle_and_record_carry_both_runs(self, tmp_path: Path) -> None:
        repo = make_project(tmp_path)
        orch = make_orchestrator(repo, repair=repair_with(counting_runner(passing_attempt())))
        run_loop(orch, repo, [_load("repair_player_turn_1.json")], [APP_PLURAL])

        evidence = json.loads(
            (
                repo / ".guardkit" / "autobuild-private" / TASK_ID
                / "coach_evidence_turn_1.json"
            ).read_text()
        )
        record = evidence["whole_feature_check"]
        assert record["ran"] is True
        assert record["outcome"] == "passed"
        assert record["exit_code"] == 0
        assert record["command"] == CHECK
        assert "check-feature: PASS" in record["stdout_tail"]
        previous = record["previous_failed_attempt"]
        assert previous["outcome"] == "failed"
        assert previous["exit_code"] == 1
        assert "check-feature: FAIL" in previous["stdout_tail"]


# ---------------------------------------------------------------------------
# 2. Controls: each gives today's behaviour (no stop)
# ---------------------------------------------------------------------------


def _turn_one_is_sent_back_as_today(history, decision, orch) -> None:
    assert orch._plan_contradicts_check_sentence is None
    # The turn was refused as today, and the loop carried on to turn 2.
    assert history[0].decision == "feedback"
    assert len(history) == 2
    assert decision == "approved"


class TestControls:
    def _two_turns(
        self,
        tmp_path: Path,
        *,
        runner: Optional[Callable[[], FeatureCheckAttempt]],
        repair: bool = True,
        wave_size: int = 1,
        first_report: Optional[Dict[str, Any]] = None,
    ):
        repo = make_project(tmp_path)
        orch = make_orchestrator(
            repo,
            repair=repair_with(runner) if repair else None,
            model_verdict=_load("repair_coach_turn_2.json"),
            wave_size=wave_size,
        )
        history, decision = run_loop(
            orch,
            repo,
            [first_report or _load("repair_player_turn_1.json"), _load("repair_player_turn_2.json")],
            [APP_PLURAL, APP_SINGULAR],
        )
        return orch, history, decision

    def test_the_check_fails_on_the_turn(self, tmp_path: Path) -> None:
        failing = failed_attempt()
        orch, history, decision = self._two_turns(tmp_path, runner=counting_runner(failing))
        _turn_one_is_sent_back_as_today(history, decision, orch)

    def test_the_check_could_not_run(self, tmp_path: Path) -> None:
        could_not = FeatureCheckAttempt(
            attempt=1, command=CHECK, candidate_sha="x", passed=False,
            outcome="could_not_run", exit_code=0,
            could_not_run_reason="the browser could not start",
        )
        orch, history, decision = self._two_turns(tmp_path, runner=counting_runner(could_not))
        _turn_one_is_sent_back_as_today(history, decision, orch)

    def test_the_runner_raises(self, tmp_path: Path) -> None:
        orch, history, decision = self._two_turns(
            tmp_path, runner=counting_runner(RuntimeError("boom"))
        )
        _turn_one_is_sent_back_as_today(history, decision, orch)
        evidence = json.loads(
            (
                orch.repo_root / ".guardkit" / "autobuild-private" / TASK_ID
                / "coach_evidence_turn_1.json"
            ).read_text()
        )
        assert evidence["whole_feature_check"]["ran"] is False
        assert evidence["whole_feature_check"]["skipped_reason"] == "runner_error: RuntimeError"

    def test_a_two_task_wave_runs_nothing(self, tmp_path: Path) -> None:
        runner = counting_runner(passing_attempt())
        orch, history, decision = self._two_turns(tmp_path, runner=runner, wave_size=2)
        _turn_one_is_sent_back_as_today(history, decision, orch)
        assert runner.calls == 0

    def test_the_promise_is_marked_complete(self, tmp_path: Path) -> None:
        report = _load("repair_player_turn_1.json")
        for promise in report["completion_promises"]:
            if promise["criterion_id"] == "AC-003":
                promise["status"] = "complete"
        repo = make_project(tmp_path)
        turn = TurnRecord(
            turn=1,
            player_result=AgentInvocationResult(
                task_id=TASK_ID, turn=1, agent_type="player", success=True,
                report=report, duration_seconds=1.0,
            ),
            coach_result=AgentInvocationResult(
                task_id=TASK_ID, turn=1, agent_type="coach", success=True,
                report={
                    "decision": "feedback",
                    "coach_primary_synthetic_feedback": True,
                    "direct_mode_blockers": [
                        {"category": "direct_mode_ac_unverified", "unmet_ids": ["AC-003"]}
                    ],
                },
                duration_seconds=1.0,
            ),
            decision="feedback",
            feedback="x",
            timestamp="t",
        )
        orch = make_orchestrator(repo, repair=repair_with(counting_runner(passing_attempt())))
        orch._whole_feature_check_by_turn[1] = {"ran": True, "outcome": "passed"}
        assert orch._plan_contradicts_check_stop(turn, "abc") is None

    def test_the_saved_repair_turn_2_does_not_stop(self, tmp_path: Path) -> None:
        """Turn 2 went back to '1 note' and the model Coach approved it."""
        repo = make_project(tmp_path)
        orch = make_orchestrator(
            repo,
            repair=repair_with(counting_runner(failed_attempt())),
            model_verdict=_load("repair_coach_turn_2.json"),
        )
        history, decision = run_loop(
            orch, repo, [_load("repair_player_turn_2.json")], [APP_SINGULAR]
        )
        assert decision == "approved"
        assert orch._plan_contradicts_check_sentence is None

    def test_the_same_turn_outside_a_repair_round(self, tmp_path: Path) -> None:
        orch, history, decision = self._two_turns(tmp_path, runner=None, repair=False)
        _turn_one_is_sent_back_as_today(history, decision, orch)
        evidence = json.loads(
            (
                orch.repo_root / ".guardkit" / "autobuild-private" / TASK_ID
                / "coach_evidence_turn_1.json"
            ).read_text()
        )
        assert "whole_feature_check" not in evidence
        assert "direct_mode_blockers" in history[0].coach_result.report


# ---------------------------------------------------------------------------
# 3. Controls on the structured record itself
# ---------------------------------------------------------------------------


def _record(report: Dict[str, Any], promises_status: str = "incomplete") -> TurnRecord:
    player = _load("repair_player_turn_1.json")
    for promise in player["completion_promises"]:
        if promise["criterion_id"] == "AC-003":
            promise["status"] = promises_status
    return TurnRecord(
        turn=1,
        player_result=AgentInvocationResult(
            task_id=TASK_ID, turn=1, agent_type="player", success=True,
            report=player, duration_seconds=1.0,
        ),
        coach_result=AgentInvocationResult(
            task_id=TASK_ID, turn=1, agent_type="coach", success=True,
            report=report, duration_seconds=1.0,
        ),
        decision=report.get("decision", "feedback"),
        feedback="x",
        timestamp="t",
    )


GATE_REPORT = {
    "decision": "feedback",
    "coach_primary_synthetic_feedback": True,
    "direct_mode_blockers": [
        {"category": "direct_mode_ac_unverified", "unmet_ids": ["AC-003"]}
    ],
}


class TestStructuredRecordControls:
    def _stop(self, tmp_path: Path, record: TurnRecord, ran: Dict[str, Any] = None):
        repo = make_project(tmp_path)
        orch = make_orchestrator(repo, repair=repair_with(None))
        orch._whole_feature_check_by_turn[1] = ran or {"ran": True, "outcome": "passed"}
        return orch._plan_contradicts_check_stop(record, "abc1234")

    def test_the_gate_report_stops(self, tmp_path: Path) -> None:
        assert self._stop(tmp_path, _record(deepcopy(GATE_REPORT))) is not None

    def test_another_gate_blocker_keeps_todays_rejection(self, tmp_path: Path) -> None:
        report = deepcopy(GATE_REPORT)
        report["direct_mode_blockers"].append(
            {"category": "direct_mode_wiring_gap", "unmet_ids": []}
        )
        assert self._stop(tmp_path, _record(report)) is None

    def test_a_leading_no_report_issue_keeps_todays_rejection(self, tmp_path: Path) -> None:
        report = deepcopy(GATE_REPORT)
        report["direct_mode_blockers"].insert(
            0, {"category": "player_timed_out", "unmet_ids": []}
        )
        assert self._stop(tmp_path, _record(report)) is None

    @pytest.mark.parametrize(
        "blockers",
        [
            None,
            "direct_mode_ac_unverified",
            [{"category": "direct_mode_ac_unverified"}],
            [{"category": "direct_mode_ac_unverified", "unmet_ids": "AC-003"}],
            [{"category": "direct_mode_ac_unverified", "unmet_ids": [3]}],
            [{"category": "direct_mode_ac_unverified", "unmet_ids": []}],
            [],
        ],
    )
    def test_missing_or_malformed_blockers_never_stop(self, tmp_path: Path, blockers) -> None:
        report = deepcopy(GATE_REPORT)
        if blockers is None:
            report.pop("direct_mode_blockers")
        else:
            report["direct_mode_blockers"] = blockers
        assert self._stop(tmp_path, _record(report)) is None

    def test_the_players_word_alone_is_never_enough(self, tmp_path: Path) -> None:
        """No GuardKit run on record: the Player's own PASS does not count."""
        repo = make_project(tmp_path)
        orch = make_orchestrator(repo, repair=repair_with(None))
        assert orch._plan_contradicts_check_stop(_record(deepcopy(GATE_REPORT)), "abc") is None

    def test_a_skipped_run_never_stops(self, tmp_path: Path) -> None:
        ran = {"ran": False, "outcome": None, "skipped_reason": "parallel_wave"}
        assert self._stop(tmp_path, _record(deepcopy(GATE_REPORT)), ran) is None

    @staticmethod
    def _model_report(independent: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "decision": "feedback",
            "issues": [{"type": "missing_requirement", "description": "AC-003"}],
            "criteria_verification": [
                {"criterion_id": "AC-001", "result": "verified"},
                {"criterion_id": "AC-003", "result": "rejected"},
            ],
            "validation_results": {"independent_tests": independent},
        }

    def test_a_model_rejection_over_criteria_only_stops(self, tmp_path: Path) -> None:
        """A real passing independent run: flags plus a real command."""
        report = self._model_report(
            {"tests_passed": True, "signal_absent": False, "test_command": "bash scripts/check.sh"}
        )
        assert self._stop(tmp_path, _record(report)) is not None

    def test_a_real_independent_run_is_read_from_the_real_merge(self, tmp_path: Path) -> None:
        """The report shape the orchestrator really builds from a run."""
        from guardkit.orchestrator.quality_gates.coach_validator import (
            IndependentTestResult,
        )

        repo = make_project(tmp_path)
        orch = make_orchestrator(repo, repair=repair_with(None))
        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True),
            independent_tests=IndependentTestResult(
                tests_passed=True, test_command="bash scripts/check.sh",
                test_output_summary="ok", duration_seconds=1.0,
            ),
        )
        ran = self._model_report({})
        ran["validation_results"] = {}
        orch._merge_evidence_test_signal_into_report(ran, bundle)
        assert _criteria_only_rejection(_record(ran)) == ["AC-003"]

        skipped_bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True),
            independent_tests=IndependentTestResult.skipped(
                test_output_summary="No task-specific tests found"
            ),
        )
        skipped = self._model_report({})
        skipped["validation_results"] = {}
        orch._merge_evidence_test_signal_into_report(skipped, skipped_bundle)
        assert skipped["validation_results"]["independent_tests"]["tests_passed"] is True
        assert _criteria_only_rejection(_record(skipped)) is None

    @pytest.mark.parametrize(
        "independent",
        [
            # IndependentTestResult.skipped(): passing flags, no run.
            {"tests_passed": True, "signal_absent": False, "test_command": "skipped"},
            {"tests_passed": True, "signal_absent": False,
             "test_command": "<no test command declared or detected>"},
            # No command recorded at all, or an empty one: unconfirmed.
            {"tests_passed": True, "signal_absent": False},
            {"tests_passed": True, "signal_absent": False, "test_command": ""},
            {"tests_passed": True, "signal_absent": False, "test_command": "   "},
            {"tests_passed": True, "signal_absent": False, "test_command": None},
        ],
    )
    def test_a_skipped_or_unconfirmed_independent_run_never_stops(
        self, tmp_path: Path, independent: Dict[str, Any]
    ) -> None:
        report = self._model_report(independent)
        assert self._stop(tmp_path, _record(report)) is None

    def test_a_model_rejection_with_a_test_failure_keeps_todays_rejection(
        self, tmp_path: Path
    ) -> None:
        report = {
            "decision": "feedback",
            "issues": [
                {"type": "missing_requirement", "description": "AC-003"},
                {"type": "test_failure", "description": "a test failed"},
            ],
            "criteria_verification": [{"criterion_id": "AC-003", "result": "rejected"}],
            "validation_results": {
                "independent_tests": {"tests_passed": True, "signal_absent": False}
            },
        }
        assert self._stop(tmp_path, _record(report)) is None

    def test_a_model_rejection_without_passing_tests_keeps_todays_rejection(
        self, tmp_path: Path
    ) -> None:
        report = {
            "decision": "feedback",
            "issues": [{"type": "missing_requirement", "description": "AC-003"}],
            "criteria_verification": [{"criterion_id": "AC-003", "result": "rejected"}],
            "validation_results": {
                "independent_tests": {"tests_passed": True, "signal_absent": True}
            },
        }
        assert self._stop(tmp_path, _record(report)) is None


# ---------------------------------------------------------------------------
# 4. The feature level: the sentence reaches the receipt, and no second
#    attempt of the check runs
# ---------------------------------------------------------------------------

from unittest.mock import patch  # noqa: E402

from guardkit.orchestrator.coach_verification import HonestyVerification  # noqa: E402
from guardkit.orchestrator.feature_check import (  # noqa: E402
    RECEIPT_RELATIVE_PATH,
    STOPPED_BECAUSE_MARKER,
    whole_feature_check_record,
)
from guardkit.orchestrator.feature_orchestrator import (  # noqa: E402
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (  # noqa: E402
    CoachEvidenceBundle,
)
from guardkit.worktrees import Worktree  # noqa: E402


def _feature(repo: Path) -> Any:
    feature = MagicMock()
    feature.id = "FEAT-15DD"
    feature.name = "Notes count label"
    feature.description = REQUEST
    feature.status = "in_progress"
    feature.smoke_gates = None
    feature.estimated_minutes = None
    feature.file_path = str(repo / ".guardkit/features/FEAT-15DD.yaml")
    feature.scenarios = {}
    task = MagicMock()
    task.id = TASK_ID
    task.dependencies = []
    task.status = "completed"
    task.file_path = str(repo / "tasks/backlog" / f"{TASK_ID}-add-count-label.md")
    feature.tasks = [task]
    feature.orchestration.parallel_groups = [[TASK_ID]]
    return feature


def _approved_wave() -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=1,
        task_ids=[TASK_ID],
        results=[
            TaskExecutionResult(
                task_id=TASK_ID, success=True, total_turns=1, final_decision="approved"
            )
        ],
        all_succeeded=True,
    )


class TestTheFeatureLevel:
    def test_one_failed_check_then_the_stop_with_the_sentence(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        repo = make_project(tmp_path)
        feature = _feature(repo)
        worktree = Worktree(
            task_id="FEAT-15DD", branch_name=BRANCH, path=repo, base_branch="main"
        )
        fo = FeatureOrchestrator(
            repo_root=repo, max_turns=5, worktree_manager=MagicMock(), quiet=True
        )
        check_calls: List[int] = []

        def _attempt(attempt_number, declaration, feature_, worktree_):
            check_calls.append(attempt_number)
            if len(check_calls) == 1:
                return failed_attempt()
            return passing_attempt(attempt_number)

        repairs: List[Any] = []
        sentences: List[Optional[str]] = []

        def _wave(wave_number, task_ids, feature_, worktree_, seed_feedback=None, attempt=0):
            # The real repair-round task: the repair the feature orchestrator
            # built for this round, the saved repair turn 1, the real loop.
            repair = fo._feature_check_repair_for_wave
            repairs.append(repair)
            orch = make_orchestrator(repo, repair=repair)
            history, decision = run_loop(
                orch, repo, [_load("repair_player_turn_1.json")], [APP_PLURAL]
            )
            sentences.append(orch._plan_contradicts_check_sentence)
            return WaveExecutionResult(
                wave_number=wave_number,
                task_ids=list(task_ids),
                results=[
                    TaskExecutionResult(
                        task_id=TASK_ID,
                        success=False,
                        total_turns=len(history),
                        final_decision=decision,
                        error=orch._build_error_message(decision, history),
                        stopped_because=orch._plan_contradicts_check_sentence,
                    )
                ],
                all_succeeded=False,
            )

        wave_results = [_approved_wave()]
        with patch.object(fo, "_one_feature_check_attempt", side_effect=_attempt), \
                patch.object(fo, "_execute_wave", side_effect=_wave), \
                patch(
                    "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
                ):
            outcome = fo._run_feature_check(feature, worktree, wave_results)

        sentence = sentences[0]
        assert sentence and sentence.startswith("The plan contradicts the project's own check")
        # Attempt 1, then GuardKit's one run on the Coach turn, through the
        # SAME runner, and no attempt 2 whatever the budget.
        assert check_calls == [1, 1]
        assert isinstance(repairs[0], FeatureCheckRepair)
        assert repairs[0].failed_attempt.exit_code == 1
        assert fo._feature_check_repair_for_wave is None, "cleared after the round"

        assert outcome.status == "failed"
        assert outcome.reason == sentence
        assert outcome.stopped_because == sentence
        receipt = json.loads((repo / RECEIPT_RELATIVE_PATH).read_text())
        assert receipt["reason"] == sentence
        assert receipt["stopped_because"] == sentence
        assert len(receipt["attempts"]) == 1
        assert wave_results[-1].smoke_gate_result.stderr == sentence

        lines = [
            line for line in capsys.readouterr().out.splitlines()
            if line.startswith(STOPPED_BECAUSE_MARKER + " ")
        ]
        assert len(lines) == 1
        assert json.loads(lines[0].split(" ", 1)[1]) == {
            "feature_id": "FEAT-15DD",
            "sentence": sentence,
        }

    def test_a_repair_that_does_not_stop_keeps_todays_receipt(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """A failed repair round without the stop: no new field, no line."""
        repo = make_project(tmp_path)
        fo = FeatureOrchestrator(
            repo_root=repo, max_turns=5, worktree_manager=MagicMock(), quiet=True
        )

        def _wave(wave_number, task_ids, feature_, worktree_, seed_feedback=None, attempt=0):
            return WaveExecutionResult(
                wave_number=wave_number,
                task_ids=list(task_ids),
                results=[
                    TaskExecutionResult(
                        task_id=TASK_ID, success=False, total_turns=5,
                        final_decision="max_turns_exceeded",
                    )
                ],
                all_succeeded=False,
            )

        with patch.object(fo, "_one_feature_check_attempt", return_value=failed_attempt()), \
                patch.object(fo, "_execute_wave", side_effect=_wave), \
                patch(
                    "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"
                ):
            outcome = fo._run_feature_check(
                _feature(repo),
                Worktree(task_id="FEAT-15DD", branch_name=BRANCH, path=repo, base_branch="main"),
                [_approved_wave()],
            )
        receipt = json.loads((repo / RECEIPT_RELATIVE_PATH).read_text())
        assert "stopped_because" not in receipt
        assert receipt["reason"] == failed_attempt().failure_reason
        assert outcome.stopped_because is None
        assert STOPPED_BECAUSE_MARKER not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 5. The repair travels the runtime-parity path, and only in a repair round
# ---------------------------------------------------------------------------


class TestThreading:
    def test_execute_wave_hands_the_repair_on_only_when_set(self, tmp_path: Path) -> None:
        repo = make_project(tmp_path)
        fo = FeatureOrchestrator(repo_root=repo, worktree_manager=MagicMock(), quiet=True)
        feature = _feature(repo)
        worktree = Worktree(task_id="FEAT-15DD", branch_name=BRANCH, path=repo, base_branch="main")
        seen: List[Dict[str, Any]] = []

        async def _parallel(*args, **kwargs):
            seen.append(kwargs)
            return [TaskExecutionResult(task_id=TASK_ID, success=True, total_turns=1, final_decision="approved")]

        repair = repair_with(None)
        with patch.object(fo, "_execute_wave_parallel", side_effect=_parallel), \
                patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"), \
                patch.object(fo, "_emit_wave_completed", new=AsyncMock()):
            fo._execute_wave(1, [TASK_ID], feature, worktree)
            fo._feature_check_repair_for_wave = repair
            fo._execute_wave(1, [TASK_ID], feature, worktree, seed_feedback="x", attempt=1)
        assert "feature_check_repair" not in seen[0]
        assert seen[1]["feature_check_repair"] is repair

    def test_execute_task_threads_it_and_carries_the_sentence_back(
        self, tmp_path: Path
    ) -> None:
        repo = make_project(tmp_path)
        fo = FeatureOrchestrator(repo_root=repo, worktree_manager=MagicMock(), quiet=True)
        feature = _feature(repo)
        worktree = Worktree(task_id="FEAT-15DD", branch_name=BRANCH, path=repo, base_branch="main")
        repair = repair_with(None)
        sentence = "The plan contradicts the project's own check: x."
        with patch("guardkit.orchestrator.feature_orchestrator.AutoBuildOrchestrator") as cls:
            cls.return_value.orchestrate.return_value = SimpleNamespace(
                success=False, total_turns=1, final_decision="unrecoverable_stall",
                error=sentence, recovery_count=0, turn_history=[],
                stall_classification=None, stopped_because=sentence,
            )
            result = fo._execute_task(feature.tasks[0], feature, worktree, feature_check_repair=repair)
            plain = fo._execute_task(feature.tasks[0], feature, worktree)
        assert cls.call_args_list[0].kwargs["feature_check_repair"] is repair
        assert cls.call_args_list[1].kwargs["feature_check_repair"] is None
        assert result.stopped_because == sentence


# ---------------------------------------------------------------------------
# 6. The Coach's inputs
# ---------------------------------------------------------------------------


def _bundle(record: Optional[Dict[str, Any]]) -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        honesty=HonestyVerification(verified=True),
        whole_feature_check=record,
    )


def _prompt(bundle: CoachEvidenceBundle, *, synthesis: bool = True) -> str:
    invoker = AgentInvoker(worktree_path=Path("/nonexistent-worktree"))
    return invoker._build_coach_prompt(
        TASK_ID,
        1,
        REQUEST,
        {"task_id": TASK_ID},
        acceptance_criteria=[{"id": "AC-003", "text": "1 note"}],
        evidence_bundle=bundle,
        synthesis=synthesis,
    )


class TestTheCoachsInputs:
    def _record(self, stdout: str = "", stderr: str = "") -> Dict[str, Any]:
        turn_run = passing_attempt()
        turn_run.stdout_tail = stdout or turn_run.stdout_tail
        turn_run.stderr_tail = stderr
        return whole_feature_check_record(
            repair_with(lambda: turn_run), wave_size=1
        )

    def test_the_section_carries_both_runs(self) -> None:
        prompt = _prompt(_bundle(self._record()))
        assert "## The project's whole-feature check" in prompt
        section = prompt.split("## The project's whole-feature check", 1)[1]
        section = section.split("## Player's Report", 1)[0]
        assert f"`{CHECK}`" in section
        assert "It decides whether the build is accepted" in section
        assert "Never call its failure out of scope" in section
        assert "Reject that criterion" in section
        assert "the plan contradicts the project's check" in section
        assert "The request decides which one should change" in section
        assert "only a person or the planner can drop it" in section
        on_turn, before = section.split("### On the code that failed before", 1)
        assert "- outcome: passed" in on_turn and "- exit code: 0" in on_turn
        assert "check-feature: PASS" in on_turn
        assert "- outcome: failed" in before and "- exit code: 1" in before
        assert "check-feature: FAIL" in before
        assert REQUEST in before
        # Not repeated inside the evidence-bundle JSON.
        assert '"whole_feature_check"' not in prompt

    def test_each_run_is_cut_to_4000_characters(self) -> None:
        long_out = "\n".join(f"line {i} " + "x" * 80 for i in range(400))
        prompt = _prompt(_bundle(self._record(stdout=long_out, stderr=long_out)))
        section = prompt.split("### On this turn's code", 1)[1].split(
            "### On the code that failed before", 1
        )[0]
        blocks = section.split("~~~text\n")[1:]
        shown = sum(len(b.split("\n~~~", 1)[0]) for b in blocks)
        assert shown <= 4000
        assert "[cut]" in section
        assert long_out.splitlines()[-1] in section, "the END of the output is kept"

    @staticmethod
    def _blocks(section: str) -> List[str]:
        return [b.split("\n~~~", 1)[0] for b in section.split("~~~text\n")[1:]]

    def test_a_stdout_that_fits_is_kept_whole(self) -> None:
        """Coach review F2: stdout is cut first, so a short stdout is never
        shortened to make room for stderr."""
        stdout = "\n".join(f"stdout line {i}" for i in range(100))  # ~1,500 chars
        stderr = "\n".join(f"stderr line {i} " + "y" * 60 for i in range(200))
        prompt = _prompt(_bundle(self._record(stdout=stdout, stderr=stderr)))
        section = prompt.split("### On this turn's code", 1)[1].split(
            "### On the code that failed before", 1
        )[0]
        shown_stdout, shown_stderr = self._blocks(section)
        assert shown_stdout == stdout
        assert len(shown_stdout) + len(shown_stderr) <= 4000
        assert shown_stderr.startswith("[cut]")
        assert stderr.splitlines()[-1] in shown_stderr

    def test_feat_15dd_failing_lines_survive(self) -> None:
        """FEAT-15DD's real output shape: Playwright's stdout tail (the
        assertion's ``unexpected value "1 note"``) beside a long stderr of
        container start-up noise. The failing lines must reach the Coach."""
        data = _load("failed_attempt_1.json")
        # The fixture's scrubbed paths are put back at their recorded length,
        # so stdout is the real 2,980 characters beside 2,347 of stderr.
        scrubbed = data["stdout_tail"].count("<path>")
        real_path = "/" + "p" * (
            (2980 - len(data["stdout_tail"])) // scrubbed + len("<path>") - 1
        )
        data["stdout_tail"] = data["stdout_tail"].replace("<path>", real_path)
        assert len(data["stdout_tail"]) == 2980 and len(data["stderr_tail"]) == 2347
        assert 'unexpected value "1 note"' in data["stdout_tail"]
        turn_run = failed_attempt()  # attempt 2 printed the same shape
        turn_run.stdout_tail = data["stdout_tail"]
        repair = repair_with(lambda: turn_run)
        repair.failed_attempt.stdout_tail = data["stdout_tail"]
        record = whole_feature_check_record(repair, wave_size=1)
        section = AgentInvoker._render_whole_feature_check_section(_bundle(record))
        on_turn, before = section.split("### On the code that failed before", 1)
        for part in (on_turn, before):
            shown_stdout, shown_stderr = self._blocks(part)
            assert 'unexpected value "1 note"' in shown_stdout
            assert "toHaveText(`${expected} notes`)" in shown_stdout
            assert shown_stdout == data["stdout_tail"], "stdout kept whole"
            assert len(shown_stdout) + len(shown_stderr) <= 4000
            assert data["stderr_tail"].splitlines()[-1] in shown_stderr

    def test_the_section_survives_trimming(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(AgentInvoker, "_COACH_SYNTHESIS_MAX_CHARS", 9000)
        bundle = _bundle(self._record())
        bundle.advisory_issues = [{"description": "y" * 20000}]
        full = AgentInvoker._render_whole_feature_check_section(bundle)
        prompt = _prompt(bundle)
        assert full in prompt

    def test_outside_a_repair_round_nothing_is_added(self) -> None:
        bundle = _bundle(None)
        assert AgentInvoker._render_whole_feature_check_section(bundle) == ""
        assert "whole_feature_check" not in bundle.to_dict()
        prompt = _prompt(bundle)
        assert "whole-feature check" not in prompt
        assert _prompt(bundle, synthesis=False).count("whole-feature") == 0

    def test_a_skipped_run_is_said_plainly(self) -> None:
        record = whole_feature_check_record(repair_with(None), wave_size=2)
        assert record["ran"] is False and record["skipped_reason"] == "parallel_wave"
        prompt = _prompt(_bundle(record))
        assert "not run on this turn's code (parallel_wave)" in prompt
        assert "check-feature: FAIL" in prompt, "the failed attempt is always shown"


# ---------------------------------------------------------------------------
# 7. Every other caller of the synthetic report is byte-identical
# ---------------------------------------------------------------------------


class TestOtherCallersUnchanged:
    def test_a_default_synthetic_report_has_no_blockers_key(self, tmp_path: Path) -> None:
        repo = make_project(tmp_path)
        orch = make_orchestrator(repo, repair=None)
        result = orch._emit_synthetic_coach_feedback(
            task_id=TASK_ID, turn=1, worktree=SimpleNamespace(path=repo),
            rationale="Evidence gathering failed: boom", start_time=0.0,
        )
        assert "direct_mode_blockers" not in result.report
        assert list(result.report) == [
            "task_id", "turn", "decision", "validation_results",
            "criteria_verification", "acceptance_criteria_verification",
            "issues", "rationale", "context_used",
            "approved_without_independent_tests", "is_configuration_error",
            "environment_conditional_approval", "honesty_verification",
            "coach_primary_synthetic_feedback", "evidence_repo_signal_absent",
        ]
        written = (
            repo / ".guardkit" / "autobuild-private" / TASK_ID / "coach_turn_1.json"
        ).read_text()
        assert written == json.dumps(result.report, indent=2)
