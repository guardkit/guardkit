"""TASK-AB-NULLEVID01 — fail-closed when the Coach approves over an incomplete
evidence pass (``gathering_status != "complete"``).

Reproduces and closes the FEAT-SMP-002 retro null-evidence-approve gap: when
``gather_evidence`` aborts early (e.g. ``partial_honesty_abort``) the bundle is
returned with everything downstream ``None`` and ``signal_absent`` is never set
(no ``IndependentTestResult`` is even constructed) — so the guard-#6 backstop
``_reconcile_absent_independent_test_signal`` explicitly no-ops and the only
thing standing between a null-evidence turn and ``approve`` was prompt guard #5
(advisory text). These tests drive the REAL ``invoke_coach`` synthesis decision
path (mocked harness emits the verdict; ``extract_and_write`` →
``_load_agent_report`` → ``_validate_coach_decision`` all run for real against
a tmp worktree) and assert the deterministic post-synthesis guard overrides
``approve``→``feedback`` when, and only when, the evidence pass is incomplete.

Instance of ``.claude/rules/structural-defence-beats-prompt-instruction.md``
(prompt guard #5 stays as defence-in-depth; the code guard is the enforcement)
and ``.claude/rules/deterministic-verdict-override-must-persist-to-disk.md``
(the on-disk ``coach_turn_N.json`` must flip too).

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching the convention in ``test_coach_independent_test_absent_guard.py``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    QualityGateStatus,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """A minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    path (mirrors ``_make_invoker`` in test_coach_independent_test_absent_guard
    — does NOT short-circuit ``_invoke_with_role``; the downstream
    parser/loader/validator run for real)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _bundle(
    gathering_status: str,
    gathering_error: Optional[str] = None,
    quality_gates: Optional[QualityGateStatus] = None,
    gate_feedback: Optional[dict] = None,
) -> CoachEvidenceBundle:
    """Build a bundle for incomplete-gathering reconciliation tests."""
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status=gathering_status,  # type: ignore[arg-type]
        gathering_error=gathering_error,
        quality_gates=quality_gates,
        gate_feedback=gate_feedback,
    )


def _coverage_gate_bundle(task_id: str, turn: int) -> CoachEvidenceBundle:
    gates = QualityGateStatus(
        tests_passed=True,
        coverage_met=False,
        arch_review_passed=True,
        plan_audit_passed=True,
    )
    gate_feedback = {
        "task_id": task_id,
        "turn": turn,
        "decision": "feedback",
        "validation_results": {
            "quality_gates": {
                "tests_passed": True,
                "coverage_met": False,
                "arch_review_passed": True,
                "plan_audit_passed": True,
                "all_gates_passed": False,
            },
            "independent_tests": None,
            "requirements": None,
        },
        "issues": [{
            "severity": "must_fix",
            "category": "coverage",
            "description": "Coverage threshold not met",
            "details": {
                "line_coverage": 62.5,
                "branch_coverage": None,
                "provenance": "player_task_work_results",
            },
        }],
        "rationale": "1 quality gate(s) failed",
    }
    return _bundle(
        "partial_gate_abort",
        quality_gates=gates,
        gate_feedback=gate_feedback,
    )


def _verdict_events(
    task_id: str,
    turn: int,
    decision: str,
    verdict_overrides: Optional[dict] = None,
) -> list:
    """Harness events carrying a fenced verdict."""
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": decision,
        "rationale": "All Player-reported gates pass; tests look green."
        if decision == "approve"
        else "Feedback: honesty discrepancies must be fixed.",
        "criteria_verification": [],
    }
    if verdict_overrides:
        verdict.update(verdict_overrides)
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


def _run_coach(
    invoker: AgentInvoker,
    *,
    task_id: str,
    turn: int,
    bundle: CoachEvidenceBundle,
    decision: str = "approve",
    verdict_overrides: Optional[dict] = None,
):
    """Invoke the Coach with a mocked model boundary and real reconciliation."""
    iwr = AsyncMock(return_value=(None, _verdict_events(
        task_id,
        turn,
        decision,
        verdict_overrides,
    )))
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


# ---------------------------------------------------------------------------
# AC-001/AC-002/AC-003 — reproducer: incomplete-gathering approve is overridden
# ---------------------------------------------------------------------------


class TestIncompleteGatheringOverride:
    def test_partial_honesty_abort_approve_is_overridden_to_feedback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-001 (FEAT-SMP-002 retro reproducer). An ``approve`` verdict
        synthesised over a ``partial_honesty_abort`` bundle (everything
        downstream ``None``, ``signal_absent`` never set) MUST be returned as
        ``feedback``. This fails without the guard (the false-green approve is
        returned) and passes once the deterministic guard lands."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)  # default ON
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)  # gather OFF
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-SMP2",
            turn=1,
            bundle=_bundle("partial_honesty_abort"),
        )

        assert result.success is True
        assert result.report["decision"] == "feedback"

    def test_override_rationale_and_prepended_must_fix_issue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-002. The overridden verdict names the actual gathering_status in
        the rationale, instructs a complete evidence pass next turn, and
        PREPENDS a ``must_fix`` / ``absence_of_failure`` issue."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-SMP2",
            turn=2,
            bundle=_bundle("partial_honesty_abort"),
        )

        rationale = result.report["rationale"]
        assert "partial_honesty_abort" in rationale
        assert "Evidence gathering did not complete" in rationale
        assert "complete evidence pass" in rationale

        issues = result.report["issues"]
        assert issues[0]["severity"] == "must_fix"
        assert issues[0]["category"] == "absence_of_failure"
        assert issues[0]["details"]["gathering_status"] == "partial_honesty_abort"
        assert issues[0]["details"]["overridden_decision"] == "approve"

    def test_override_rewrites_coach_turn_file_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-003. The on-disk ``coach_turn_N.json`` must also flip to
        ``feedback`` — Layer-4 late-approval reconciliation
        (``feature_orchestrator._check_late_approval``) reads ``decision``
        straight off disk, so an in-memory-only override would be resurrected
        as ``approve``. Mirrors
        ``test_override_rewrites_coach_turn_file_on_disk`` in the guard-#6
        tests. See
        .claude/rules/deterministic-verdict-override-must-persist-to-disk.md."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        _run_coach(
            invoker,
            task_id="TASK-SMP2",
            turn=3,
            bundle=_bundle("partial_honesty_abort"),
        )

        on_disk = json.loads(
            invoker._get_report_path("TASK-SMP2", 3, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"

    def test_partial_gate_abort_approve_is_overridden(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-001. ``partial_gate_abort`` fires too: quality gates FAILED and
        independent tests never ran — an approve over failed/aborted gates is
        exactly the false-green this guard exists to stop (every legitimate
        conditional-approval clause requires ``all_gates_passed=True``, which
        only arises on a ``complete`` bundle)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-GATEAB",
            turn=1,
            bundle=_bundle("partial_gate_abort"),
        )

        assert result.report["decision"] == "feedback"
        assert "partial_gate_abort" in result.report["rationale"]

    def test_partial_exception_approve_is_overridden_and_names_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-001/AC-002. ``partial_exception`` fires and the rationale
        surfaces ``gathering_error`` verbatim so operators can diagnose which
        helper errored."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-GEXC",
            turn=1,
            bundle=_bundle(
                "partial_exception",
                gathering_error="quality_gates_exception: KeyError('tests')",
            ),
        )

        assert result.report["decision"] == "feedback"
        rationale = result.report["rationale"]
        assert "partial_exception" in rationale
        assert "quality_gates_exception: KeyError('tests')" in rationale


# ---------------------------------------------------------------------------
# Item 60 — source-owned quality-gate feedback replaces model gate prose
# ---------------------------------------------------------------------------


class TestDeterministicPartialGateFeedback:
    @pytest.mark.parametrize("model_decision", ["approve", "feedback"])
    def test_valid_payload_replaces_fabricated_gate_claims_in_memory_and_disk(
        self,
        model_decision: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        invented_issue = {
            "severity": "must_fix",
            "category": "test_failure",
            "description": "Zero tests ran and the plan audit is missing",
            "details": {"failed_count": 0, "total_count": 0},
        }
        overrides = {
            "rationale": (
                "Zero tests ran; plan audit missing despite green coverage."
            ),
            "issues": [invented_issue],
            "validation_results": {
                "quality_gates": {
                    "tests_passed": False,
                    "coverage_met": True,
                    "arch_review_passed": True,
                    "plan_audit_passed": False,
                    "all_gates_passed": False,
                }
            },
        }

        result = _run_coach(
            invoker,
            task_id="TASK-TRUTHFUL-GATES",
            turn=2,
            bundle=_coverage_gate_bundle("TASK-TRUTHFUL-GATES", 2),
            decision=model_decision,
            verdict_overrides=overrides,
        )

        report = result.report
        assert report["task_id"] == "TASK-TRUTHFUL-GATES"
        assert report["turn"] == 2
        assert report["decision"] == "feedback"
        assert report["rationale"] == "1 quality gate(s) failed"
        assert [issue["category"] for issue in report["issues"]] == [
            "coverage"
        ]
        assert report["issues"][0]["details"] == {
            "line_coverage": 62.5,
            "branch_coverage": None,
            "provenance": "player_task_work_results",
        }
        assert report["validation_results"]["quality_gates"] == {
            "tests_passed": True,
            "coverage_met": False,
            "arch_review_passed": True,
            "plan_audit_passed": True,
            "all_gates_passed": False,
        }
        on_disk = json.loads(
            invoker._get_report_path(
                "TASK-TRUTHFUL-GATES", 2, "coach"
            ).read_text()
        )
        for field in (
            "task_id", "turn", "decision", "issues", "rationale",
            "validation_results",
        ):
            assert on_disk[field] == report[field]

    @pytest.mark.parametrize("malformation", ["mismatch", "missing_fields"])
    def test_malformed_or_mismatched_payload_keeps_generic_fail_closed_guard(
        self,
        malformation: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        bundle = _coverage_gate_bundle("TASK-BAD-GATE-PAYLOAD", 1)
        assert bundle.gate_feedback is not None
        if malformation == "mismatch":
            bundle.gate_feedback["validation_results"]["quality_gates"][
                "coverage_met"
            ] = True
        else:
            bundle.gate_feedback = {"decision": "feedback"}

        result = _run_coach(
            invoker,
            task_id="TASK-BAD-GATE-PAYLOAD",
            turn=1,
            bundle=bundle,
        )

        assert result.report["decision"] == "feedback"
        assert result.report["issues"][0]["category"] == (
            "absence_of_failure"
        )
        assert "partial_gate_abort" in result.report["rationale"]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("task_id", "TASK-PREVIOUS"),
            ("turn", 1),
            ("turn", True),
            ("turn", "2"),
        ],
    )
    def test_stale_or_noninteger_identity_keeps_generic_fail_closed_guard(
        self,
        field: str,
        value: object,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        bundle = _coverage_gate_bundle("TASK-CURRENT-GATE-PAYLOAD", 2)
        assert bundle.gate_feedback is not None
        bundle.gate_feedback[field] = value

        result = _run_coach(
            invoker,
            task_id="TASK-CURRENT-GATE-PAYLOAD",
            turn=2,
            bundle=bundle,
        )

        assert result.report["decision"] == "feedback"
        assert result.report["issues"][0]["category"] == "absence_of_failure"
        assert result.report["rationale"] != "1 quality gate(s) failed"
        assert result.report["validation_results"] == {}

    @pytest.mark.parametrize(
        "malformation",
        [
            "issue_string",
            "issue_missing_details",
            "details_list",
            "independent_tests",
            "requirements",
            "extra_validation_result",
            "extra_quality_gate",
        ],
    )
    def test_malformed_nested_source_payload_keeps_generic_guard(
        self,
        malformation: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        bundle = _coverage_gate_bundle("TASK-NESTED-GATE-PAYLOAD", 3)
        assert bundle.gate_feedback is not None
        if malformation == "issue_string":
            bundle.gate_feedback["issues"] = ["bad"]
        elif malformation == "issue_missing_details":
            bundle.gate_feedback["issues"][0].pop("details")
        elif malformation == "details_list":
            bundle.gate_feedback["issues"][0]["details"] = []
        elif malformation == "independent_tests":
            bundle.gate_feedback["validation_results"]["independent_tests"] = {
                "tests_passed": False,
                "test_command": "fabricated",
            }
        elif malformation == "requirements":
            bundle.gate_feedback["validation_results"]["requirements"] = {
                "criteria_total": 1,
                "criteria_met": 0,
                "all_criteria_met": False,
                "missing": ["AC-001"],
            }
        elif malformation == "extra_validation_result":
            bundle.gate_feedback["validation_results"]["invented"] = {}
        else:
            bundle.gate_feedback["validation_results"]["quality_gates"][
                "invented"
            ] = True

        result = _run_coach(
            invoker,
            task_id="TASK-NESTED-GATE-PAYLOAD",
            turn=3,
            bundle=bundle,
        )

        assert result.report["decision"] == "feedback"
        assert result.report["issues"][0]["category"] == "absence_of_failure"
        assert result.report["rationale"] != "1 quality gate(s) failed"
        assert result.report["validation_results"] == {}

    def test_valid_advisory_issue_fields_and_severity_are_preserved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        bundle = _coverage_gate_bundle("TASK-GATE-ADVISORY", 4)
        assert bundle.gate_feedback is not None
        advisory = {
            "severity": "warning",
            "category": "agent_invocations_advisory",
            "description": "Advisory fields remain source owned",
            "details": {
                "missing_phases": ["5"],
                "expected_phases": 2,
                "actual_invocations": 1,
            },
            "source": "deterministic-advisory",
        }
        bundle.gate_feedback["issues"].insert(0, advisory)

        result = _run_coach(
            invoker,
            task_id="TASK-GATE-ADVISORY",
            turn=4,
            bundle=bundle,
            decision="feedback",
        )

        assert result.report["issues"][0] == advisory
        assert result.report["issues"][0]["severity"] == "warning"


# ---------------------------------------------------------------------------
# AC-005 — no over-reach, no happy-path regression
# ---------------------------------------------------------------------------


class TestGuardDoesNotOverReach:
    def test_complete_bundle_approve_is_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-005. A ``complete`` bundle with an ``approve`` verdict is
        returned as ``approve`` untouched (nothing downstream reads as
        absent-by-abort)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker, task_id="TASK-OK", turn=1, bundle=_bundle("complete")
        )

        assert result.report["decision"] == "approve"

    def test_feedback_verdict_is_untouched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-005. A ``feedback`` verdict already rejects the turn — the guard
        is a no-op even over an aborted-gathering bundle (no prepended
        override issue, original rationale preserved)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-FB",
            turn=1,
            bundle=_bundle("partial_honesty_abort"),
            decision="feedback",
        )

        assert result.report["decision"] == "feedback"
        assert "Evidence gathering did not complete" not in result.report["rationale"]
        assert not any(
            i.get("details", {}).get("gathering_status")
            for i in result.report.get("issues", [])
        )

    def test_bundle_none_fails_open(self, tmp_path: Path) -> None:
        """Fail-open: no evidence bundle at all (legacy/tool-using callers) —
        the guard must not fire. Exercised on the guard method directly (the
        full ``invoke_coach`` bundle-less path runs the legacy tool-using
        Coach, out of scope here)."""
        invoker = _make_invoker(tmp_path)
        decision = {"decision": "approve", "rationale": "ok", "issues": []}

        invoker._reconcile_incomplete_evidence_gathering(
            decision=decision,
            evidence_bundle=None,
            task_id="TASK-LEGACY",
            turn=1,
            coach_output_path=tmp_path / "coach_turn_1.json",
        )

        assert decision["decision"] == "approve"
        assert decision["issues"] == []

    def test_missing_gathering_status_attribute_fails_open(
        self, tmp_path: Path
    ) -> None:
        """Fail-open: a legacy bundle shape with NO ``gathering_status``
        attribute is not positive evidence of an abort — the guard must not
        fire on evidence-less legacy paths."""
        invoker = _make_invoker(tmp_path)
        decision = {"decision": "approve", "rationale": "ok", "issues": []}

        class _LegacyBundle:  # no gathering_status attribute at all
            pass

        invoker._reconcile_incomplete_evidence_gathering(
            decision=decision,
            evidence_bundle=_LegacyBundle(),  # type: ignore[arg-type]
            task_id="TASK-LEGACY",
            turn=1,
            coach_output_path=tmp_path / "coach_turn_1.json",
        )

        assert decision["decision"] == "approve"
        assert decision["issues"] == []


# ---------------------------------------------------------------------------
# 2026-07-04 code review (FIX 4) — the partial_gate_abort route must not hide
# verifier infrastructure. When the failing Phase-4 gate stems from an ABSENT
# verifier signal (the FEAT-ABL-005 run-4 shape: zero collected tests from a
# broken venv → quality gates fail → gather_evidence partial_gate_abort →
# independent_tests=None → guard #6 no-ops), the guard must (a) use the
# infrastructure framing and (b) attach the verifier_infrastructure marker so
# the TASK-AB-ZEROTESTLOUD01 stall extractor schema-matches this route too.
# Without the markers, the generic framing is byte-identical to before.
# ---------------------------------------------------------------------------


_INFRA_INTERPRETER = "/wt/.venv/bin/python"
_INFRA_COMMAND = "pytest tests/ -v"


def _write_phase4_infra_markers(worktree: Path, task_id: str) -> None:
    """Write the deterministic Phase-4 absent record the runner emits
    (``specialist_invocations._run_deterministic_phase_4`` absent branch)."""
    autobuild_dir = worktree / ".guardkit" / "autobuild" / task_id
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    (autobuild_dir / "specialist_results.json").write_text(
        json.dumps(
            {
                "phase_4": {
                    "status": "failed",
                    "error": (
                        "absent test signal (deterministic Phase 4): "
                        "collected 0 items (rc=5)"
                    ),
                    "signal_absent": True,
                    "verifier_infrastructure": True,
                    "resolved_interpreter": _INFRA_INTERPRETER,
                    "test_command": _INFRA_COMMAND,
                    "tests_run": 0,
                    "output_summary": "collected 0 items (rc=5)",
                }
            }
        )
    )


class TestVerifierInfrastructureOnGateAbortRoute:
    def test_deterministic_replacement_retains_infrastructure_annotation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        _write_phase4_infra_markers(tmp_path, "TASK-VINFRA-ITEM60")

        result = _run_coach(
            invoker,
            task_id="TASK-VINFRA-ITEM60",
            turn=1,
            bundle=_coverage_gate_bundle("TASK-VINFRA-ITEM60", 1),
            decision="feedback",
            verdict_overrides={
                "rationale": "Invented zero-test complaint",
                "issues": [{
                    "severity": "must_fix",
                    "category": "test_failure",
                    "description": "Zero tests ran",
                    "details": {"total_count": 0},
                }],
            },
        )

        assert result.report["rationale"] == "1 quality gate(s) failed"
        assert result.report["issues"][0]["category"] == "coverage"
        marked = [
            issue
            for issue in result.report["issues"]
            if issue.get("details", {}).get("verifier_infrastructure") is True
        ]
        assert len(marked) == 1
        assert marked[0]["severity"] == "should_fix"
        assert marked[0]["details"]["resolved_interpreter"] == (
            _INFRA_INTERPRETER
        )
        on_disk = json.loads(
            invoker._get_report_path(
                "TASK-VINFRA-ITEM60", 1, "coach"
            ).read_text()
        )
        for field in (
            "task_id", "turn", "decision", "issues", "rationale",
            "validation_results",
        ):
            assert on_disk[field] == result.report[field]

    def test_gate_abort_with_marker_flips_with_infra_framing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FIX 4a: the flipped approve names verifier infrastructure (guard
        #6's wording), NOT the quality-implying generic framing, and its
        prepended issue carries the machine-readable marker + interpreter +
        command (FIX 4b)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        _write_phase4_infra_markers(tmp_path, "TASK-VINFRA")

        result = _run_coach(
            invoker,
            task_id="TASK-VINFRA",
            turn=1,
            bundle=_bundle("partial_gate_abort"),
        )

        assert result.report["decision"] == "feedback"
        rationale = result.report["rationale"]
        assert "partial_gate_abort" in rationale
        assert (
            "Verification infrastructure could not collect/run any tests"
            in rationale
        )
        assert f"interpreter: {_INFRA_INTERPRETER}" in rationale
        assert f"command: {_INFRA_COMMAND}" in rationale
        assert "NOT a signal about your code" in rationale
        assert "do not rewrite the implementation" in rationale
        # The generic quality-implying stage text must NOT frame this turn.
        assert "quality gates failed; independent tests" not in rationale

        issue = result.report["issues"][0]
        assert issue["severity"] == "must_fix"
        details = issue["details"]
        assert details["verifier_infrastructure"] is True
        assert details["signal_absent"] is True
        assert details["resolved_interpreter"] == _INFRA_INTERPRETER
        assert details["test_command"] == _INFRA_COMMAND
        assert details["overridden_decision"] == "approve"

    def test_gate_abort_without_marker_keeps_generic_framing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail open: absent markers → the pre-FIX-4 generic framing,
        byte-identical (no verifier_infrastructure detail invented)."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-NOMARK",
            turn=1,
            bundle=_bundle("partial_gate_abort"),
        )

        assert result.report["decision"] == "feedback"
        rationale = result.report["rationale"]
        assert "quality gates failed; independent tests and requirements" in rationale
        assert "Verification infrastructure" not in rationale
        details = result.report["issues"][0]["details"]
        assert "verifier_infrastructure" not in details

    def test_honesty_abort_never_probes_infra_markers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The probe is gate-abort-scoped: other abort statuses never ran the
        Phase-4 gate, so no infra attribution is invented even when marker
        files exist on disk."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        _write_phase4_infra_markers(tmp_path, "TASK-HONAB")

        result = _run_coach(
            invoker,
            task_id="TASK-HONAB",
            turn=1,
            bundle=_bundle("partial_honesty_abort"),
        )

        assert result.report["decision"] == "feedback"
        assert "Verification infrastructure" not in result.report["rationale"]
        details = result.report["issues"][0]["details"]
        assert "verifier_infrastructure" not in details

    def test_feedback_over_marked_gate_abort_gains_appended_annotation(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A feedback verdict on the marked gate-abort route is ANNOTATED
        (appended should_fix marker issue) so the stall extractor matches the
        runtime-dominant route too — verdict and rationale untouched."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        invoker = _make_invoker(tmp_path)
        _write_phase4_infra_markers(tmp_path, "TASK-VINFRA-FB")

        result = _run_coach(
            invoker,
            task_id="TASK-VINFRA-FB",
            turn=1,
            bundle=_bundle("partial_gate_abort"),
            decision="feedback",
        )

        assert result.report["decision"] == "feedback"
        # LLM's own rationale untouched (annotation only).
        assert (
            result.report["rationale"]
            == "Feedback: honesty discrepancies must be fixed."
        )
        issues = result.report["issues"]
        marked = [
            i
            for i in issues
            if isinstance(i.get("details"), dict)
            and i["details"].get("verifier_infrastructure") is True
        ]
        assert len(marked) == 1
        assert issues[-1] == marked[0]
        assert marked[0]["severity"] == "should_fix"
        assert marked[0]["details"]["resolved_interpreter"] == _INFRA_INTERPRETER
        assert "NOT a signal about your code" in marked[0]["description"]
        assert "overridden_decision" not in marked[0]["details"]
        # Persisted for the stall classifier / operator.
        on_disk = json.loads(
            invoker._get_report_path("TASK-VINFRA-FB", 1, "coach").read_text()
        )
        assert any(
            isinstance(i.get("details"), dict)
            and i["details"].get("verifier_infrastructure") is True
            for i in on_disk.get("issues", [])
        )

    def test_feedback_without_marker_stays_untouched(
        self, tmp_path: Path
    ) -> None:
        """Fail open (AC-005 preserved): no markers → the feedback verdict is
        completely untouched on the gate-abort route."""
        invoker = _make_invoker(tmp_path)
        decision = {"decision": "feedback", "rationale": "gates failed", "issues": []}

        invoker._reconcile_incomplete_evidence_gathering(
            decision=decision,
            evidence_bundle=_bundle("partial_gate_abort"),
            task_id="TASK-NOMARK-FB",
            turn=1,
            coach_output_path=tmp_path / "coach_turn_1.json",
        )

        assert decision == {
            "decision": "feedback",
            "rationale": "gates failed",
            "issues": [],
        }

    def test_feedback_annotation_is_idempotent(self, tmp_path: Path) -> None:
        invoker = _make_invoker(tmp_path)
        _write_phase4_infra_markers(tmp_path, "TASK-IDEM")
        marker_issue = {
            "severity": "should_fix",
            "category": "absence_of_failure",
            "description": "already marked",
            "details": {"verifier_infrastructure": True},
        }
        decision = {
            "decision": "feedback",
            "rationale": "gates failed",
            "issues": [marker_issue],
        }

        invoker._reconcile_incomplete_evidence_gathering(
            decision=decision,
            evidence_bundle=_bundle("partial_gate_abort"),
            task_id="TASK-IDEM",
            turn=1,
            coach_output_path=tmp_path / "coach_turn_1.json",
        )

        assert decision["issues"] == [marker_issue]

    def test_three_marked_gate_abort_turns_co_fire_environment_stall(
        self, tmp_path: Path
    ) -> None:
        """End-to-end schema match: three feedback turns annotated by THIS
        guard co-fire STALL_ENVIRONMENT via the existing
        ``_extract_verifier_infrastructure_signal`` extractor — the
        TASK-AB-ZEROTESTLOUD01 diagnostic is reachable on this route."""
        from guardkit.orchestrator.agent_invoker import AgentInvocationResult
        from guardkit.orchestrator.autobuild import (
            STALL_ENVIRONMENT,
            TurnRecord,
            classify_stall,
        )

        invoker = _make_invoker(tmp_path)
        _write_phase4_infra_markers(tmp_path, "TASK-ENVSTALL")

        history = []
        for turn in (1, 2, 3):
            decision = {
                "decision": "feedback",
                "rationale": "quality gates failed",
                "issues": [],
            }
            invoker._reconcile_incomplete_evidence_gathering(
                decision=decision,
                evidence_bundle=_bundle("partial_gate_abort"),
                task_id="TASK-ENVSTALL",
                turn=turn,
                coach_output_path=tmp_path / f"coach_turn_{turn}.json",
            )
            coach_result = AgentInvocationResult(
                task_id="TASK-ENVSTALL",
                turn=turn,
                agent_type="coach",
                success=True,
                report=decision,
                duration_seconds=0.1,
                error=None,
            )
            player_result = AgentInvocationResult(
                task_id="TASK-ENVSTALL",
                turn=turn,
                agent_type="player",
                success=True,
                report={"files_modified": []},
                duration_seconds=1.0,
                error=None,
            )
            history.append(
                TurnRecord(
                    turn=turn,
                    player_result=player_result,
                    coach_result=coach_result,
                    decision="feedback",
                    feedback="quality gates failed",
                    timestamp=f"2026-07-04T12:0{turn}:00Z",
                )
            )

        classification = classify_stall(history, "unrecoverable_stall")
        assert classification is not None
        assert STALL_ENVIRONMENT in classification.co_fires


# ---------------------------------------------------------------------------
# AC-003 — fail-open on the write, fail-closed on the verdict
# ---------------------------------------------------------------------------


class TestPersistenceFailure:
    def test_oserror_on_repersist_logs_warning_and_keeps_override(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """AC-003. A disk hiccup on the re-persist must never unblock the
        turn: the in-memory override still applies and a WARNING is logged.
        (``coach_output_path`` points at a directory so ``write_text`` raises
        ``IsADirectoryError``, an ``OSError`` subclass.)"""
        invoker = _make_invoker(tmp_path)
        decision = {"decision": "approve", "rationale": "ok", "issues": []}
        blocked_path = tmp_path / "coach_turn_1.json"
        blocked_path.mkdir()  # write_text on a directory raises OSError

        with caplog.at_level(logging.WARNING):
            invoker._reconcile_incomplete_evidence_gathering(
                decision=decision,
                evidence_bundle=_bundle("partial_honesty_abort"),
                task_id="TASK-DISK",
                turn=1,
                coach_output_path=blocked_path,
            )

        # Fail-closed on the verdict: the in-memory override applies.
        assert decision["decision"] == "feedback"
        assert decision["issues"][0]["severity"] == "must_fix"
        # Fail-open on the write: WARNING logged, no exception propagated.
        assert any(
            "failed to re-persist overridden verdict" in rec.message
            for rec in caplog.records
        )
