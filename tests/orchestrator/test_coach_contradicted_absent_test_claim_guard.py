"""TASK-FIX-COACHMISREAD01 — void a Coach objection that contradicts the record.

The case, in plain words. On 4 September 2026 the build ``build-FEAT-44A8``
ran the documentation task ``TASK-44A8-004``. Documentation tasks do not need
tests, so the separate ("independent") test run was skipped on purpose, and
the Coach's own evidence record said exactly that:
``independent_tests.signal_absent=false``,
``independent_tests.test_command="skipped"``, ``tests.tests_required=false``.
The Coach rejected the turn anyway, all three times, with one objection
quoting ``"independent_tests.signal_absent=true"`` — the opposite of what its
record said.

Prompt guard #6 (``INDEPENDENT-TEST ABSENT GUARD``) tells the Coach to write
almost that exact sentence, but only when the field is true, and the existing
deterministic backstop
``AgentInvoker._reconcile_absent_independent_test_signal`` only handles the
other direction (record says absent, Coach approves anyway). Nothing handled
this inverse. ``_reconcile_contradicted_absent_test_claim`` does.

The two files in ``tests/fixtures/coach-misread-2026-09-04/`` are byte-for-byte
copies of that build's real turn-1 records (see the PROVENANCE.txt beside
them), so these tests are graded against what actually happened rather than a
hand-written imitation.

Tests drive the REAL ``invoke_coach`` synthesis path (a mocked harness emits
the verdict; the parser, loader, validator and every deterministic guard run
for real against a tmp worktree), matching the convention in
``test_coach_independent_test_absent_guard.py``. Async tests use
``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional
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
    IndependentTestResult,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "coach-misread-2026-09-04"
)


# ---------------------------------------------------------------------------
# fixture loading — the real build-FEAT-44A8 / TASK-44A8-004 turn-1 records
# ---------------------------------------------------------------------------


def _load_receipt(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text())


def _real_evidence() -> Dict[str, Any]:
    return _load_receipt("coach_evidence_turn_1.json")


def _real_verdict() -> Dict[str, Any]:
    return _load_receipt("coach_turn_1.json")


def _real_false_finding_text() -> str:
    """The Coach's single objection, verbatim from the real receipt."""
    issues = _real_verdict()["issues"]
    assert len(issues) == 1, "fixture expected to carry exactly one finding"
    return issues[0]["description"]


def _bundle_from_receipt(
    evidence: Optional[Dict[str, Any]] = None,
) -> CoachEvidenceBundle:
    """Rebuild the evidence bundle from the saved record.

    Only the legs this guard and its neighbours read are rehydrated
    (``independent_tests`` as the real dataclass, ``tests`` / ``task_type`` /
    ``profile_name`` as saved). ``honesty`` is rebuilt from the saved values,
    which on this receipt are a clean pass.
    """
    evidence = evidence if evidence is not None else _real_evidence()
    ind = evidence["independent_tests"]
    honesty = evidence["honesty"]
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=honesty["verified"],
            discrepancies=[],
            honesty_score=honesty["honesty_score"],
            resolved_paths=[],
            should_fix_count=honesty.get("should_fix_count", 0),
        ),
        gathering_status=evidence["gathering_status"],
        tests=evidence["tests"],
        independent_tests=IndependentTestResult(
            tests_passed=ind["tests_passed"],
            test_command=ind["test_command"],
            test_output_summary=ind["test_output_summary"],
            duration_seconds=ind["duration_seconds"],
            raw_output=ind["raw_output"],
            signal_absent=ind["signal_absent"],
            tests_skipped=ind["tests_skipped"],
            resolved_interpreter=ind["resolved_interpreter"],
        ),
        task_type=evidence["task_type"],
        profile_name=evidence["profile_name"],
    )


# ---------------------------------------------------------------------------
# harness helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """A minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    path (mirrors ``_make_invoker`` in
    test_coach_independent_test_absent_guard.py)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _v4_reject_events(findings: List[str]) -> list:
    """Harness events carrying the Coach v4 wire shape this build really used:
    ``{"verdict": "reject", "findings": [{"locus": "..."}]}``. The parser
    adapts it into the internal decision shape saved in coach_turn_1.json."""
    wire = {"verdict": "reject", "findings": [{"locus": f} for f in findings]}
    return [
        AssistantMessageEvent(text=json.dumps(wire)),
        ResultMessageEvent(session_id=None),
    ]


def _run_coach(
    invoker: AgentInvoker,
    *,
    task_id: str,
    turn: int,
    bundle: CoachEvidenceBundle,
    findings: List[str],
):
    """Invoke the Coach with ``_invoke_with_role`` mocked to return the
    rejection the real seat emitted. Everything else runs for real."""
    iwr = AsyncMock(return_value=(None, _v4_reject_events(findings)))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="Document the API surface.",
                player_report={"files_modified": ["docs/API.md"], "tests_passed": True},
                evidence_bundle=bundle,
            )
        )


@pytest.fixture(autouse=True)
def _coach_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Synthesis path on (default), gather off, v4 contract — the shape the
    real build ran under."""
    monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
    monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
    monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")


# ---------------------------------------------------------------------------
# (a) the real case — the false objection is voided and the turn is approved
# ---------------------------------------------------------------------------


class TestRealBuildMisreadIsCorrected:
    def test_real_receipt_rejection_becomes_approve(self, tmp_path: Path) -> None:
        """The real turn-1 bundle and verdict from build-FEAT-44A8 /
        TASK-44A8-004. The record says the test run was skipped on purpose;
        the Coach's only objection says the test signal was absent. The
        objection is removed and, with nothing else objected to, the turn is
        approved. Fails on main (which returns the misread ``feedback``)."""
        invoker = _make_invoker(tmp_path)
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(),
            findings=[false_finding],
        )

        assert result.success is True
        assert result.report["decision"] == "approve"
        assert result.report["issues"] == []

    def test_marker_records_the_voided_text_and_the_record(
        self, tmp_path: Path
    ) -> None:
        """The correction is machine-readable, not just prose: the marker flag
        is set, the voided finding is kept verbatim, and the record values it
        contradicted are named."""
        invoker = _make_invoker(tmp_path)
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(),
            findings=[false_finding],
        )

        assert result.report["contradicted_absent_claim_voided"] is True
        marker = result.report["contradicted_absent_claim"]
        assert marker["voided_text"] == [false_finding]
        assert marker["voided_findings"][0]["description"] == false_finding
        assert marker["overridden_decision"] == "feedback"
        assert marker["record"]["signal_absent"] is False
        assert marker["record"]["test_command"] == "skipped"
        assert marker["record"]["tests_required"] is False
        assert marker["record"]["task_type"] == "documentation"
        # The record's own note is quoted so an operator sees WHY it skipped.
        assert (
            marker["record"]["test_output_summary"]
            == _real_evidence()["independent_tests"]["test_output_summary"]
        )

    def test_rationale_says_plainly_what_happened(self, tmp_path: Path) -> None:
        """The approval explains itself in ordinary words: a mandated skip,
        and an objection that contradicted it."""
        invoker = _make_invoker(tmp_path)

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(),
            findings=[_real_false_finding_text()],
        )

        rationale = result.report["rationale"]
        assert "skipped ON PURPOSE" in rationale
        assert "does not require tests" in rationale
        assert "contradicts that record" in rationale

    def test_override_rewrites_coach_turn_file_on_disk(
        self, tmp_path: Path
    ) -> None:
        """The on-disk ``coach_turn_N.json`` must carry the promoted verdict —
        the Layer-4 late-approval reader
        (``feature_orchestrator._check_late_approval``) reads ``decision``
        straight off disk, so an in-memory-only change would be lost."""
        invoker = _make_invoker(tmp_path)

        _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=2,
            bundle=_bundle_from_receipt(),
            findings=[_real_false_finding_text()],
        )

        on_disk = json.loads(
            invoker._get_report_path("TASK-44A8-004", 2, "coach").read_text()
        )
        assert on_disk["decision"] == "approve"
        assert on_disk["contradicted_absent_claim_voided"] is True
        assert on_disk["issues"] == []


# ---------------------------------------------------------------------------
# (b) a GENUINE absent signal is never touched — guard #6 keeps failing closed
# ---------------------------------------------------------------------------


class TestGenuineAbsentSignalStillFailsClosed:
    def test_signal_absent_true_leaves_the_rejection_standing(
        self, tmp_path: Path
    ) -> None:
        """The same bundle with ``signal_absent=True``: now the Coach's
        sentence is TRUE, the record really has no test signal, and the turn
        must stay rejected with the objection intact. This is the path that
        must never regress."""
        invoker = _make_invoker(tmp_path)
        evidence = _real_evidence()
        evidence["independent_tests"]["signal_absent"] = True
        evidence["independent_tests"]["tests_passed"] = False
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(evidence),
            findings=[false_finding],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report
        descriptions = [i.get("description") for i in result.report["issues"]]
        assert false_finding in descriptions


# ---------------------------------------------------------------------------
# (c) a real objection alongside the false one keeps the turn rejected
# ---------------------------------------------------------------------------


class TestOtherFindingsSurvive:
    def test_only_the_false_finding_is_voided_and_verdict_stays_feedback(
        self, tmp_path: Path
    ) -> None:
        """A rejection carrying the false absent-signal claim PLUS a genuine
        objection: the false one goes, the genuine one stays, and the turn is
        still rejected. The guard can never turn a real rejection into an
        approval."""
        invoker = _make_invoker(tmp_path)
        false_finding = _real_false_finding_text()
        real_finding = (
            "AC-002 not delivered: docs/API.md documents no error responses"
        )

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(),
            findings=[false_finding, real_finding],
        )

        assert result.report["decision"] == "feedback"
        descriptions = [i.get("description") for i in result.report["issues"]]
        assert descriptions == [real_finding]
        assert result.report["contradicted_absent_claim_voided"] is True
        marker = result.report["contradicted_absent_claim"]
        assert marker["voided_text"] == [false_finding]
        assert marker["overridden_decision"] is None

    def test_unrelated_finding_alone_is_never_touched(
        self, tmp_path: Path
    ) -> None:
        """A rejection with no absent-signal claim at all is completely
        untouched — no voiding, no marker, still rejected."""
        invoker = _make_invoker(tmp_path)
        real_finding = "AC-001 not delivered: docs/API.md was not created"

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(),
            findings=[real_finding],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report
        descriptions = [i.get("description") for i in result.report["issues"]]
        assert descriptions == [real_finding]


# ---------------------------------------------------------------------------
# (d) out of scope: the tests actually ran, or the skip was not mandated
# ---------------------------------------------------------------------------


class TestOutOfScopeBundles:
    def test_tests_actually_ran_is_out_of_scope(self, tmp_path: Path) -> None:
        """A bundle where the independent tests really RAN (test_command is a
        real pytest command, tests required) with a Coach claiming the signal
        was absent: not this guard's case. Nothing is voided and the turn
        stays rejected — whether that claim is right is for a human or another
        guard to settle, not this one."""
        invoker = _make_invoker(tmp_path)
        evidence = _real_evidence()
        evidence["independent_tests"]["test_command"] = "pytest -q"
        evidence["independent_tests"]["test_output_summary"] = "12 passed"
        evidence["tests"]["tests_required"] = True
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(evidence),
            findings=[false_finding],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report
        descriptions = [i.get("description") for i in result.report["issues"]]
        assert false_finding in descriptions

    def test_skip_on_a_profile_that_requires_tests_is_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        """``test_command == "skipped"`` has a second, very different cause:
        the profile DOES require tests but no task-specific test was found
        (the zero-test anomaly). That is a legitimate thing to reject over, so
        the guard must not fire — only ``tests_required is False`` makes the
        skip mandated."""
        invoker = _make_invoker(tmp_path)
        evidence = _real_evidence()
        evidence["tests"]["tests_required"] = True
        evidence["independent_tests"]["test_output_summary"] = (
            "Independent verification skipped: no task-specific tests found."
        )
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(evidence),
            findings=[false_finding],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report

    def test_missing_tests_required_key_is_unknown_and_no_ops(
        self, tmp_path: Path
    ) -> None:
        """Absent-key safety: a bundle whose gate slice does not carry
        ``tests_required`` at all is UNKNOWN, never assumed False."""
        invoker = _make_invoker(tmp_path)
        evidence = _real_evidence()
        evidence["tests"].pop("tests_required")
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(evidence),
            findings=[false_finding],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report

    def test_no_independent_tests_leg_is_a_no_op(self, tmp_path: Path) -> None:
        """No independent-test leg at all: nothing to contradict, no-op."""
        invoker = _make_invoker(tmp_path)
        bundle = _bundle_from_receipt()
        bundle.independent_tests = None
        false_finding = _real_false_finding_text()

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=bundle,
            findings=[false_finding],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report


class TestPromotionIsStillOfferedToTheFailClosedGuards:
    """The ordering safety property.

    Every other deterministic guard acts only on an ``approve`` verdict. If
    this guard promoted a rejection to an approval AFTER them, a turn one of
    them would have blocked could slip through unblocked. It therefore runs
    BEFORE them, and they get to flip the promotion straight back.
    """

    def test_a_spec_gap_deselection_flips_the_promotion_back(
        self, tmp_path: Path
    ) -> None:
        """Mandated skip + only the false absent-signal objection, but the
        SPEC_GAP leg reports whole-file silent deselection — the acceptance
        scenarios for this task were never executed.
        ``_apply_spec_gap_absent_guard`` acts ONLY on an ``approve`` and
        returns immediately on a ``feedback``, so it can block this turn only
        if the promotion reaches it. The false objection is still voided, and
        the turn must still end rejected, with the deselection as the reason.

        This is the test that pins the ordering: move the guard after
        ``_apply_spec_gap_absent_guard`` and this goes red with an
        ``approve``."""
        invoker = _make_invoker(tmp_path)
        bundle = _bundle_from_receipt()
        bundle.spec_gap = {
            "whole_file_deselection": True,
            "ground_truth_count": 3,
            "executed_count": 0,
            "bdd_plugin_name": "pytest-bdd",
        }

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=bundle,
            findings=[_real_false_finding_text()],
        )

        assert result.report["decision"] == "feedback"
        # the misreading was still corrected ...
        assert result.report["contradicted_absent_claim_voided"] is True
        # ... and the real blocker is what now stands in its place
        categories = [i.get("category") for i in result.report["issues"]]
        assert "absence_of_failure" in categories
        assert "whole-file silent deselection" in result.report["rationale"]
        on_disk = json.loads(
            invoker._get_report_path("TASK-44A8-004", 1, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"

    def test_incomplete_evidence_gathering_is_a_no_op(
        self, tmp_path: Path
    ) -> None:
        """A mandated skip is only trustworthy when the evidence pass
        finished. On an aborted gather the guard refuses to act at all — that
        case belongs to guard #5."""
        invoker = _make_invoker(tmp_path)
        evidence = _real_evidence()
        evidence["gathering_status"] = "partial_gate_abort"

        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(evidence),
            findings=[_real_false_finding_text()],
        )

        assert result.report["decision"] == "feedback"
        assert "contradicted_absent_claim_voided" not in result.report


# ---------------------------------------------------------------------------
# the matcher itself — what counts as "claims the signal was absent"
# ---------------------------------------------------------------------------


class TestClaimMatcher:
    @pytest.mark.parametrize(
        "text",
        [
            'independent_tests.signal_absent=true: "Independent test '
            'verification skipped (tests not required for documentation '
            'tasks)" — the trust-but-verify run did not execute',
            "Independent test verification did not complete (signal absent)",
            "the independent verification never ran",
            "independent_tests produced no verdict",
        ],
    )
    def test_absent_signal_claims_are_matched(self, text: str) -> None:
        assert AgentInvoker._claims_independent_test_signal_absent(
            {"description": text}
        )

    @pytest.mark.parametrize(
        "text",
        [
            "AC-002 not delivered: docs/API.md documents no error responses",
            "The README section on independent tests is out of date",
            "The migration step did not run before the seed step",
            "independent_tests.signal_absent=false but coverage is missing",
            "",
        ],
    )
    def test_unrelated_or_half_matching_text_is_not_matched(
        self, text: str
    ) -> None:
        assert not AgentInvoker._claims_independent_test_signal_absent(
            {"description": text}
        )

    def test_a_second_call_changes_nothing(self, tmp_path: Path) -> None:
        """Idempotent: re-running the guard over an already-corrected decision
        finds no matching finding and leaves it exactly as it was."""
        invoker = _make_invoker(tmp_path)
        result = _run_coach(
            invoker,
            task_id="TASK-44A8-004",
            turn=1,
            bundle=_bundle_from_receipt(),
            findings=[_real_false_finding_text()],
        )
        before = deepcopy(result.report)

        invoker._reconcile_contradicted_absent_test_claim(
            decision=result.report,
            evidence_bundle=_bundle_from_receipt(),
            task_id="TASK-44A8-004",
            turn=1,
            coach_output_path=invoker._get_report_path(
                "TASK-44A8-004", 1, "coach"
            ),
        )

        assert result.report == before
