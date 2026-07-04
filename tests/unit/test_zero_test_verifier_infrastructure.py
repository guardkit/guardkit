"""TASK-AB-ZEROTESTLOUD01 — zero-collected-tests surfaces as VERIFIER
INFRASTRUCTURE, never as Player quality.

FEAT-ABL-005 run 4: 8 consecutive turns recorded ``absent test signal
(deterministic Phase 4): tests_run=0`` (root cause: the TASK-AB-RESUMEVENV01
interpreter defect). The absent-signal machinery behaved correctly — what
failed was diagnosis/attribution: the Coach *appeared* to reject on quality
while it was actually blind. These tests pin the loudness half, with verdict
semantics UNCHANGED:

- AC-001: the deterministic Phase-4 absent branch and the Coach-side absent
  override/annotation carry a machine-readable ``verifier_infrastructure``
  marker with the resolved interpreter and probed command (schema-additive,
  never string-matched).
- AC-002: Player-facing feedback states the NOT-a-code-signal framing.
- AC-003: a trailing window of marked turns co-fires ``STALL_ENVIRONMENT``
  and the terminal message names verifier infrastructure + interpreter +
  remediation.
- AC-004: the marker never becomes an approval input — guard #6 fires first
  and unchanged; the environment-class conditional-approval amnesty
  (TASK-ABSR-2468) never fires on an absent signal.
- AC-005: tri-state ``None`` in checkpoints is preserved; a genuine
  ran-and-failed turn gains no marker and is untouched.

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching ``tests/orchestrator/test_coach_independent_test_absent_guard.py``.

Coverage Target: >=85%
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator import specialist_invocations as si
from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import (
    STALL_ENVIRONMENT,
    STALL_FEEDBACK_GENERIC,
    AutoBuildOrchestrator,
    TurnRecord,
    _extract_verifier_infrastructure_signal,
    classify_stall,
)
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


_INTERPRETER = "/wt/.venv/bin/python"
_COMMAND = "pytest tests/unit/test_fixture.py -v"


# ---------------------------------------------------------------------------
# helpers (mirrors test_coach_independent_test_absent_guard.py)
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _absent_independent() -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=False,
        test_command=_COMMAND,
        test_output_summary="collected 0 items (rc=5)",
        duration_seconds=0.4,
        signal_absent=True,
        resolved_interpreter=_INTERPRETER,
    )


def _bundle(independent: Optional[IndependentTestResult]) -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        independent_tests=independent,
    )


def _verdict_events(task_id: str, turn: int, decision: str) -> list:
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
        "rationale": (
            "All gates look green."
            if decision == "approve"
            else "Tests failed — fix the implementation."
        ),
        "criteria_verification": [],
        "issues": (
            []
            if decision == "approve"
            else [
                {
                    "severity": "must_fix",
                    "category": "test_failure",
                    "description": "Tests did not pass.",
                }
            ]
        ),
    }
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


def _run_coach(
    invoker: AgentInvoker,
    *,
    task_id: str,
    turn: int,
    bundle: CoachEvidenceBundle,
    verdict: str = "approve",
):
    iwr = AsyncMock(return_value=(None, _verdict_events(task_id, turn, verdict)))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="reqs",
                player_report={"files_modified": [], "tests_passed": True},
                evidence_bundle=bundle,
            )
        )


def _marker_issues(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        issue
        for issue in report.get("issues", [])
        if isinstance(issue, dict)
        and isinstance(issue.get("details"), dict)
        and issue["details"].get("verifier_infrastructure") is True
    ]


# ---------------------------------------------------------------------------
# turn-record builders for stall classification
# ---------------------------------------------------------------------------


def _player_result(turn: int, task_id: str = "TASK-ZTL") -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={"files_modified": ["src/x.py"], "tests_passed": True},
        duration_seconds=5.0,
        error=None,
    )


def _marked_absent_turn(turn: int, task_id: str = "TASK-ZTL") -> TurnRecord:
    """A feedback turn whose coach report carries the verifier-infrastructure
    marker issue (the shape _reconcile_absent_independent_test_signal emits)."""
    coach_result = AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": "Independent test verification did not complete.",
            "validation_results": {
                "independent_tests": {
                    "tests_passed": False,
                    "test_command": _COMMAND,
                    "signal_absent": True,
                    "resolved_interpreter": _INTERPRETER,
                },
            },
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "absence_of_failure",
                    "description": (
                        "Verification infrastructure could not collect/run "
                        "any tests — this is NOT a signal about your code."
                    ),
                    "details": {
                        "signal_absent": True,
                        "verifier_infrastructure": True,
                        "resolved_interpreter": _INTERPRETER,
                        "test_command": _COMMAND,
                    },
                }
            ],
        },
        duration_seconds=0.5,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_player_result(turn, task_id),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_result.report["feedback"],
        timestamp=f"2026-07-04T10:0{turn}:00Z",
    )


def _genuine_failure_turn(turn: int, task_id: str = "TASK-ZTL") -> TurnRecord:
    """A ran-and-failed feedback turn — no marker anywhere."""
    coach_result = AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "decision": "feedback",
            "feedback": "2 tests failed.",
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "test_verification",
                    "description": "FAILED tests/test_x.py::test_a",
                    "failure_classification": "code",
                }
            ],
        },
        duration_seconds=0.5,
        error=None,
    )
    return TurnRecord(
        turn=turn,
        player_result=_player_result(turn, task_id),
        coach_result=coach_result,
        decision="feedback",
        feedback=coach_result.report["feedback"],
        timestamp=f"2026-07-04T10:0{turn}:00Z",
    )


# ---------------------------------------------------------------------------
# AC-001 — deterministic Phase-4 absent branch carries the marker
# ---------------------------------------------------------------------------


class TestDeterministicPhase4Marker:
    def _run_block(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        outcome: IndependentTestResult,
    ) -> Optional[Dict[str, Any]]:
        class _FakeCoachValidator:
            def __init__(self, **kwargs):
                pass

            def run_independent_tests(self, **kwargs):
                return outcome

        monkeypatch.setattr(
            "guardkit.orchestrator.quality_gates.coach_validator.CoachValidator",
            _FakeCoachValidator,
        )
        invoker = MagicMock()
        invoker._venv_python = None
        return si._run_deterministic_phase_4(
            worktree_path=tmp_path,
            task_id="TASK-AB-ZEROTESTLOUD01",
            agent_invoker=invoker,
            sdk_timeout=300,
            turn=1,
        )

    def test_absent_block_carries_marker_interpreter_and_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        block = self._run_block(tmp_path, monkeypatch, _absent_independent())
        assert block is not None
        assert block["verifier_infrastructure"] is True
        assert block["resolved_interpreter"] == _INTERPRETER
        assert block["test_command"] == _COMMAND
        # Verdict semantics UNCHANGED: still status=failed + signal_absent +
        # the exact error prefix the ABFIX-010 reconciliation branches on.
        assert block["status"] == "failed"
        assert block["signal_absent"] is True
        assert block["error"].startswith("absent test signal (deterministic Phase 4)")
        assert block["tests_run"] == 0

    def test_genuine_ran_and_failed_block_gains_no_marker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-005: a real pytest failure is a genuine Player signal."""
        outcome = IndependentTestResult(
            tests_passed=False,
            test_command=_COMMAND,
            test_output_summary="1 failed, 3 passed",
            duration_seconds=0.3,
            raw_output="1 failed, 3 passed",
            signal_absent=False,
            resolved_interpreter=_INTERPRETER,
        )
        block = self._run_block(tmp_path, monkeypatch, outcome)
        assert block is not None
        assert block["status"] == "failed"
        assert "verifier_infrastructure" not in block
        assert "signal_absent" not in block
        assert block["error"].startswith("tests failed (deterministic Phase 4)")


# ---------------------------------------------------------------------------
# AC-001/AC-002/AC-004 — Coach-side override: marker + honest framing;
# a marked absent turn can NEVER end approved (guard #6 fires first, unchanged)
# ---------------------------------------------------------------------------


class TestCoachOverrideMarkerAndFraming:
    def test_marked_absent_approve_can_never_end_approved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-004: even when the LLM emits approve over an absent signal
        carrying the marker inputs, guard #6 flips it to feedback."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=1,
            bundle=_bundle(_absent_independent()),
            verdict="approve",
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"

    def test_override_issue_carries_marker_interpreter_and_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=2,
            bundle=_bundle(_absent_independent()),
            verdict="approve",
        )

        marked = _marker_issues(result.report)
        assert len(marked) == 1
        details = marked[0]["details"]
        assert details["resolved_interpreter"] == _INTERPRETER
        assert details["test_command"] == _COMMAND
        assert details["signal_absent"] is True
        assert marked[0]["category"] == "absence_of_failure"

    def test_override_rationale_has_not_a_code_signal_framing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-002: the framing names the interpreter and command, says it is
        NOT a code signal, and says not to rewrite the implementation."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=3,
            bundle=_bundle(_absent_independent()),
            verdict="approve",
        )

        rationale = result.report["rationale"]
        assert "Verification infrastructure could not collect/run any tests" in rationale
        assert f"interpreter: {_INTERPRETER}" in rationale
        assert f"command: {_COMMAND}" in rationale
        assert "NOT a signal about your code" in rationale
        assert "do not rewrite the implementation" in rationale
        assert "worktree venv" in rationale
        # Pre-existing guard-#6 wording preserved (COACHFG01 pins).
        assert (
            "Independent test verification did not complete (signal absent)"
            in rationale
        )


class TestCoachFeedbackAnnotation:
    def test_feedback_verdict_gains_marker_but_keeps_decision_and_rationale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=4,
            bundle=_bundle(_absent_independent()),
            verdict="feedback",
        )

        assert result.report["decision"] == "feedback"
        # LLM's own rationale untouched (annotation only).
        assert result.report["rationale"] == "Tests failed — fix the implementation."
        marked = _marker_issues(result.report)
        assert len(marked) == 1
        assert marked[0]["details"]["resolved_interpreter"] == _INTERPRETER
        assert "NOT a signal about your code" in marked[0]["description"]
        # The annotation is not an override — no overridden_decision detail.
        assert "overridden_decision" not in marked[0]["details"]

    def test_annotation_is_appended_should_fix_never_top_priority(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """2026-07-04 code review (FIX 5): the annotation is attribution —
        ``should_fix`` and APPENDED, so it never lands ABOVE (and apparently
        contradicts) the LLM's genuine must_fix issues. The stall extractor
        is position/severity independent, so it still matches."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=8,
            bundle=_bundle(_absent_independent()),
            verdict="feedback",
        )

        issues = result.report["issues"]
        # The LLM's genuine must_fix issue keeps top priority.
        assert issues[0]["category"] == "test_failure"
        assert issues[0]["severity"] == "must_fix"
        # The annotation is the LAST issue, severity should_fix.
        marked = _marker_issues(result.report)
        assert len(marked) == 1
        assert issues[-1] == marked[0]
        assert marked[0]["severity"] == "should_fix"

    def test_flip_path_override_stays_prepended_must_fix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FIX 5 scope guard: the APPROVE flip-path override is load-bearing
        must_fix and stays prepended — only the ANNOTATION path changed."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=9,
            bundle=_bundle(_absent_independent()),
            verdict="approve",
        )

        assert result.report["decision"] == "feedback"
        issues = result.report["issues"]
        assert issues[0]["details"].get("verifier_infrastructure") is True
        assert issues[0]["severity"] == "must_fix"
        assert issues[0]["details"]["overridden_decision"] == "approve"

    def test_feedback_annotation_is_persisted_to_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """deterministic-verdict-override-must-persist-to-disk: the marker
        must survive to coach_turn_N.json for the stall classifier/operator."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        _run_coach(
            invoker,
            task_id="TASK-ZTL",
            turn=5,
            bundle=_bundle(_absent_independent()),
            verdict="feedback",
        )

        on_disk = json.loads(
            invoker._get_report_path("TASK-ZTL", 5, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"
        assert len(_marker_issues(on_disk)) == 1

    def test_annotation_is_idempotent(self, tmp_path: Path) -> None:
        """A decision already carrying the marker is not double-annotated."""
        invoker = _make_invoker(tmp_path)
        marker_issue = {
            "severity": "must_fix",
            "category": "absence_of_failure",
            "description": "already marked",
            "details": {"verifier_infrastructure": True},
        }
        decision = {
            "task_id": "TASK-ZTL",
            "turn": 6,
            "decision": "feedback",
            "rationale": "existing",
            "issues": [marker_issue],
        }
        invoker._reconcile_absent_independent_test_signal(
            decision=decision,
            evidence_bundle=_bundle(_absent_independent()),
            task_id="TASK-ZTL",
            turn=6,
            coach_output_path=tmp_path / "coach_turn_6.json",
        )
        assert decision["issues"] == [marker_issue]

    def test_genuine_failure_feedback_gains_no_marker(
        self, tmp_path: Path
    ) -> None:
        """AC-005: ran-and-failed (signal_absent=False) is untouched."""
        invoker = _make_invoker(tmp_path)
        decision = {
            "task_id": "TASK-ZTL",
            "turn": 7,
            "decision": "feedback",
            "rationale": "2 failed",
            "issues": [],
        }
        genuine = IndependentTestResult(
            tests_passed=False,
            test_command=_COMMAND,
            test_output_summary="2 failed, 8 passed",
            duration_seconds=1.0,
            signal_absent=False,
            resolved_interpreter=_INTERPRETER,
        )
        invoker._reconcile_absent_independent_test_signal(
            decision=decision,
            evidence_bundle=_bundle(genuine),
            task_id="TASK-ZTL",
            turn=7,
            coach_output_path=tmp_path / "coach_turn_7.json",
        )
        assert decision["issues"] == []
        assert decision["decision"] == "feedback"


# ---------------------------------------------------------------------------
# AC-004 — the amnesty never fires on an absent signal (legacy validate path)
# ---------------------------------------------------------------------------


class TestAmnestyNeverFedByAbsentSignal:
    def test_environment_conditional_approval_rejects_absent_signal(
        self, tmp_path: Path
    ) -> None:
        """Even with a known-broken bootstrap + ambiguous infrastructure
        classification + all Player gates passed, an ABSENT signal must not
        ride the TASK-ABSR-2468 amnesty into an approval."""
        worktree = tmp_path / "worktree"
        results_dir = worktree / ".guardkit" / "autobuild" / "TASK-001"
        results_dir.mkdir(parents=True)
        (results_dir / "task_work_results.json").write_text(
            json.dumps(
                {
                    "quality_gates": {
                        "tests_passing": True,
                        "tests_passed": 15,
                        "tests_failed": 0,
                        "coverage": 85,
                        "coverage_met": True,
                        "all_passed": True,
                    },
                    "code_review": {"score": 82},
                    "plan_audit": {"violations": 0},
                }
            )
        )
        state_dir = worktree / ".guardkit"
        (state_dir / "bootstrap_state.json").write_text(
            json.dumps({"content_hash": "x", "success": False})
        )

        validator = CoachValidator(str(worktree))
        absent = _absent_independent()
        task = {
            "acceptance_criteria": ["works"],
            "requires_infrastructure": [],
            "_docker_available": True,
        }
        with patch.object(
            validator, "run_independent_tests", return_value=absent
        ), patch.object(
            validator,
            "_classify_test_failure",
            return_value=("infrastructure", "ambiguous"),
        ):
            result = validator.validate("TASK-001", 1, task)

        assert result.decision != "approve"
        assert result.environment_conditional_approval is False


# ---------------------------------------------------------------------------
# AC-004 extension (2026-07-04 code review) — the signal_absent exclusion
# covers EVERY conditional-approval clause on the legacy validate() path,
# not only the TASK-ABSR-2468 environment amnesty.
# ---------------------------------------------------------------------------


def _green_player_results(worktree: Path, task_id: str = "TASK-001") -> None:
    """All Player gates green + requirements met (mirrors
    tests/unit/test_env_conditional_approval.py::_make_passing_results)."""
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(
        json.dumps(
            {
                "quality_gates": {
                    "tests_passing": True,
                    "tests_passed": 15,
                    "tests_failed": 0,
                    "coverage": 85,
                    "coverage_met": True,
                    "all_passed": True,
                },
                "code_review": {"score": 82},
                "plan_audit": {"violations": 0},
                "requirements_met": ["works"],
            }
        )
    )


class TestConditionalApprovalClausesRejectAbsentSignal:
    """Absent oracle + gates green must NOT ride any conditional-approval
    clause (parallel_contention / collection_error / code-in-parallel) into
    an approve — absence-of-failure-is-not-success. Genuine ran-and-failed
    signals keep their ABSR-2468/ABFIX-005 amnesties (load-bearing)."""

    def _validate(
        self,
        worktree: Path,
        *,
        wave_size: int,
        classification: tuple,
        independent: IndependentTestResult,
    ):
        _green_player_results(worktree)
        validator = CoachValidator(str(worktree), wave_size=wave_size)
        task = {
            "acceptance_criteria": ["works"],
            "requires_infrastructure": [],
            "_docker_available": True,
        }
        with patch.object(
            validator, "run_independent_tests", return_value=independent
        ), patch.object(
            validator, "_classify_test_failure", return_value=classification
        ):
            return validator.validate("TASK-001", 1, task)

    def test_parallel_contention_clause_rejects_absent_signal(
        self, tmp_path: Path
    ) -> None:
        """An ABSENT oracle in a parallel wave (e.g. TimeoutExpired →
        raw_output=None → _classify_test_failure(None) returns
        parallel_contention) must stay feedback, never conditional-approve."""
        result = self._validate(
            tmp_path / "worktree",
            wave_size=2,
            classification=("parallel_contention", "high"),
            independent=_absent_independent(),
        )
        assert result.decision == "feedback"
        assert result.approved_without_independent_tests is False

    def test_collection_error_clause_rejects_absent_signal(
        self, tmp_path: Path
    ) -> None:
        result = self._validate(
            tmp_path / "worktree",
            wave_size=1,
            classification=("collection_error", "high"),
            independent=_absent_independent(),
        )
        assert result.decision == "feedback"
        assert result.approved_without_independent_tests is False

    def test_code_in_parallel_clause_rejects_absent_signal(
        self, tmp_path: Path
    ) -> None:
        result = self._validate(
            tmp_path / "worktree",
            wave_size=2,
            classification=("code", "n/a"),
            independent=_absent_independent(),
        )
        assert result.decision == "feedback"
        assert result.approved_without_independent_tests is False

    def test_ran_and_failed_parallel_contention_keeps_amnesty(
        self, tmp_path: Path
    ) -> None:
        """A GENUINE ran-and-failed parallel-contention failure with all
        gates green still gets its TASK-ABFIX-005 conditional approval —
        the absent-signal exclusion must not break the real-signal amnesty."""
        genuine = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/",
            test_output_summary="ImportError during collection",
            duration_seconds=0.4,
            raw_output="ImportError while importing test module",
            signal_absent=False,
        )
        result = self._validate(
            tmp_path / "worktree",
            wave_size=2,
            classification=("parallel_contention", "high"),
            independent=genuine,
        )
        assert result.decision == "approve"
        assert result.approved_without_independent_tests is True

    def test_ran_and_failed_collection_error_keeps_amnesty(
        self, tmp_path: Path
    ) -> None:
        genuine = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/",
            test_output_summary="errors during collection",
            duration_seconds=0.4,
            raw_output="2 errors during collection",
            signal_absent=False,
        )
        result = self._validate(
            tmp_path / "worktree",
            wave_size=1,
            classification=("collection_error", "high"),
            independent=genuine,
        )
        assert result.decision == "approve"
        assert result.approved_without_independent_tests is True


# ---------------------------------------------------------------------------
# AC-005 — tri-state None preserved in the checkpoint signal
# ---------------------------------------------------------------------------


class TestCheckpointTriStatePreserved:
    def test_marked_absent_turn_extracts_none(self, tmp_path: Path) -> None:
        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        turn = _marked_absent_turn(1)
        assert orchestrator._extract_tests_passed(turn) is None


# ---------------------------------------------------------------------------
# AC-003 — stall co-fire + terminal message
# ---------------------------------------------------------------------------


class TestExtractVerifierInfrastructureSignal:
    def test_extracts_marked_issue(self) -> None:
        issue = _extract_verifier_infrastructure_signal(_marked_absent_turn(1))
        assert issue is not None
        assert issue["details"]["resolved_interpreter"] == _INTERPRETER

    def test_unmarked_turn_is_absent_signal(self) -> None:
        assert (
            _extract_verifier_infrastructure_signal(_genuine_failure_turn(1))
            is None
        )

    def test_missing_coach_result_is_absent_signal(self) -> None:
        record = TurnRecord(
            turn=1,
            player_result=_player_result(1),
            coach_result=None,
            decision="feedback",
            feedback="x",
            timestamp="2026-07-04T10:00:00Z",
        )
        assert _extract_verifier_infrastructure_signal(record) is None


class TestStallCoFire:
    def test_three_marked_trailing_turns_co_fire_environment_stall(self) -> None:
        history = [
            _marked_absent_turn(1),
            _marked_absent_turn(2),
            _marked_absent_turn(3),
        ]
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_ENVIRONMENT in classification.co_fires
        assert classification.decision_label == STALL_ENVIRONMENT

    def test_two_of_three_marked_turns_do_not_co_fire(self) -> None:
        history = [
            _marked_absent_turn(1),
            _genuine_failure_turn(2),
            _marked_absent_turn(3),
        ]
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_ENVIRONMENT not in classification.co_fires
        assert classification.decision_label == STALL_FEEDBACK_GENERIC

    def test_genuine_failure_turns_do_not_co_fire(self) -> None:
        history = [
            _genuine_failure_turn(1),
            _genuine_failure_turn(2),
            _genuine_failure_turn(3),
        ]
        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_ENVIRONMENT not in classification.co_fires


class _FakeWorktreeManager:
    def __init__(self, worktrees_dir: Path) -> None:
        self.worktrees_dir = worktrees_dir


class TestTerminalStallMessage:
    def _orchestrator(self, tmp_path: Path) -> AutoBuildOrchestrator:
        worktrees_dir = tmp_path / ".guardkit" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        return AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=10,
            worktree_manager=_FakeWorktreeManager(worktrees_dir),
            enable_context=False,
        )

    def test_message_names_verifier_infrastructure_interpreter_and_remediation(
        self, tmp_path: Path
    ) -> None:
        orchestrator = self._orchestrator(tmp_path)
        history = [
            _marked_absent_turn(1),
            _marked_absent_turn(2),
            _marked_absent_turn(3),
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        assert f"[{STALL_ENVIRONMENT}]" in message
        assert "Verifier infrastructure failure" in message
        assert _INTERPRETER in message
        assert _COMMAND in message
        assert "re-run environment bootstrap" in message
        assert "worktree venv" in message
        # It must NOT imply Player quality.
        assert "Review task_type classification" not in message

    def test_unmarked_stall_keeps_existing_messages(self, tmp_path: Path) -> None:
        orchestrator = self._orchestrator(tmp_path)
        history = [
            _genuine_failure_turn(1),
            _genuine_failure_turn(2),
            _genuine_failure_turn(3),
        ]
        message = orchestrator._build_summary_details(
            history, "unrecoverable_stall"
        )
        assert "Verifier infrastructure failure" not in message
        assert "Unrecoverable stall detected" in message


# ---------------------------------------------------------------------------
# 2026-07-04 code review (FIX 2) — classifier and diagnostic share ONE
# trailing-window threshold; a caller-side change cannot silently strand the
# diagnostic on a diverged private default.
# ---------------------------------------------------------------------------


class TestStallThresholdSingleSource:
    def _orchestrator(self, tmp_path: Path) -> AutoBuildOrchestrator:
        worktrees_dir = tmp_path / ".guardkit" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        return AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=10,
            worktree_manager=_FakeWorktreeManager(worktrees_dir),
            enable_context=False,
        )

    def test_diagnostic_and_classifier_agree_when_threshold_2_passed_to_both(
        self, tmp_path: Path
    ) -> None:
        """With a 2-turn marked window and threshold=2 threaded into BOTH,
        the sub-type fires AND the diagnostic renders — no silent None."""
        orchestrator = self._orchestrator(tmp_path)
        history = [_marked_absent_turn(1), _marked_absent_turn(2)]

        classification = classify_stall(
            history, "unrecoverable_stall", threshold=2
        )
        assert classification is not None
        assert STALL_ENVIRONMENT in classification.co_fires

        message = orchestrator._build_verifier_infrastructure_stall_diagnostic(
            history, threshold=2
        )
        assert message is not None
        assert "Verifier infrastructure failure" in message

    def test_diagnostic_and_classifier_agree_on_shared_default(
        self, tmp_path: Path
    ) -> None:
        """At the shared default, a 2-turn window fires NEITHER — the pair
        stays in agreement in the negative direction too."""
        orchestrator = self._orchestrator(tmp_path)
        history = [_marked_absent_turn(1), _marked_absent_turn(2)]

        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_ENVIRONMENT not in classification.co_fires
        assert (
            orchestrator._build_verifier_infrastructure_stall_diagnostic(
                history
            )
            is None
        )

    def test_defaults_are_the_shared_module_constant(self) -> None:
        """The single source of truth: both signatures default to
        ``STALL_CLASSIFICATION_THRESHOLD``."""
        import inspect

        from guardkit.orchestrator.autobuild import (
            STALL_CLASSIFICATION_THRESHOLD,
        )

        assert (
            inspect.signature(classify_stall).parameters["threshold"].default
            == STALL_CLASSIFICATION_THRESHOLD
        )
        assert (
            inspect.signature(
                AutoBuildOrchestrator._build_verifier_infrastructure_stall_diagnostic
            )
            .parameters["threshold"]
            .default
            == STALL_CLASSIFICATION_THRESHOLD
        )
