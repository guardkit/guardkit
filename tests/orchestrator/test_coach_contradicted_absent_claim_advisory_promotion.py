"""The absent-signal guard must not be blocked by warnings that never reject.

The case, in plain words. On 4 September 2026 the build ``build-FEAT-99E2``
ran the documentation task ``TASK-DEACT-005``. Documentation tasks do not need
tests, so the separate ("independent") test run was skipped on purpose, and
the coach's own evidence record said exactly that
(``independent_tests.signal_absent=false``, ``test_command="skipped"``,
``tests.tests_required=false``). The coach rejected turn 3 anyway, quoting
``independent_tests.signal_absent=true``.

``AgentInvoker._reconcile_contradicted_absent_test_claim`` removes that false
objection. Standing next to it on this turn are six deterministic honesty
records of type ``claim_audit_unmodified``, all at severity ``should_fix`` —
warnings which guardkit's own reconciler says never reject a turn
(``coach_narrative_reconciler``: "a warning never burns a build"). If the
guard counted those as blockers the turn would stay rejected with no rejecting
reason on it.

Live, those records are embedded AFTER this guard runs, so on the first pass
the guard sees the coach's objection alone. These tests cover BOTH orders —
the live one end to end through ``invoke_coach``, and the already-embedded one
by calling the guard directly — so the guard gives the same answer whichever
way round the two steps happen.

The two files in ``tests/fixtures/coach-misread-2026-09-04/deact-005-turn3/``
are byte-for-byte copies of that build's real turn-3 records (see the
PROVENANCE.txt beside them).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_narrative_reconciler import (
    DETERMINISTIC_SOURCE,
)
from guardkit.orchestrator.coach_verification import (
    Discrepancy,
    HonestyVerification,
)
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
    / "deact-005-turn3"
)


# ---------------------------------------------------------------------------
# fixture loading — the real build-FEAT-99E2 / TASK-DEACT-005 turn-3 records
# ---------------------------------------------------------------------------


def _real_evidence() -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / "coach_evidence_turn_3.json").read_text())


def _real_verdict() -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / "coach_turn_3.json").read_text())


def _real_false_finding_text() -> str:
    """The coach's own objection, verbatim — the last issue on the saved
    verdict (the six ahead of it are the embedded honesty records)."""
    issues = _real_verdict()["issues"]
    coach_findings = [
        i for i in issues if not (i.get("details") or {}).get("source")
    ]
    assert len(coach_findings) == 1, "fixture expected one coach finding"
    return coach_findings[0]["description"]


def _real_embedded_honesty_issues() -> List[Dict[str, Any]]:
    """The six ``claim_audit_unmodified`` records as they were embedded on the
    saved verdict — the shape the guard sees if it runs after the reconciler."""
    issues = [
        i
        for i in _real_verdict()["issues"]
        if (i.get("details") or {}).get("source") == DETERMINISTIC_SOURCE
    ]
    assert len(issues) == 6, "fixture expected six embedded honesty records"
    assert all(i["severity"] == "should_fix" for i in issues)
    return issues


def _bundle_from_receipt(
    evidence: Optional[Dict[str, Any]] = None,
) -> CoachEvidenceBundle:
    """Rebuild the evidence bundle from the saved record, honesty records and
    all (this turn's honesty leg carries the six ``should_fix`` records)."""
    evidence = evidence if evidence is not None else _real_evidence()
    ind = evidence["independent_tests"]
    honesty = evidence["honesty"]
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=honesty["verified"],
            discrepancies=[
                Discrepancy(
                    claim_type=d["claim_type"],
                    player_claim=d["player_claim"],
                    actual_value=d["actual_value"],
                    severity=d["severity"],
                )
                for d in honesty["discrepancies"]
            ],
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
# harness helpers (same convention as
# test_coach_contradicted_absent_test_claim_guard.py)
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _v4_reject_events(findings: List[str]) -> list:
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
    iwr = AsyncMock(return_value=(None, _v4_reject_events(findings)))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="Document the deactivation endpoint.",
                player_report={
                    "files_modified": ["docs/API.md"],
                    "tests_passed": True,
                },
                evidence_bundle=bundle,
            )
        )


def _call_guard_directly(
    invoker: AgentInvoker,
    *,
    decision: Dict[str, Any],
    bundle: CoachEvidenceBundle,
    tmp_path: Path,
) -> Dict[str, Any]:
    """Run only the guard, over a decision whose issues are already what the
    test wants. This is the order the receipt on disk is in."""
    out = tmp_path / "coach_turn_3.json"
    invoker._reconcile_contradicted_absent_test_claim(
        decision=decision,
        evidence_bundle=bundle,
        task_id="TASK-DEACT-005",
        turn=3,
        coach_output_path=out,
    )
    return decision


def _decision_with(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "task_id": "TASK-DEACT-005",
        "turn": 3,
        "decision": "feedback",
        "issues": issues,
    }


def _honesty_issue(severity: str, record_severity: str) -> Dict[str, Any]:
    """One deterministic honesty record at the given severities."""
    return {
        "severity": severity,
        "category": "honesty",
        "description": (
            f"Deterministic honesty record (claim_audit_unmodified, "
            f"severity={record_severity}): Player claim: docs/API.md."
        ),
        "details": {
            "source": DETERMINISTIC_SOURCE,
            "claim_type": "claim_audit_unmodified",
            "player_claim": "Player claimed file docs/API.md",
            "actual_value": "no change recorded for it",
            "severity": record_severity,
        },
    }


@pytest.fixture(autouse=True)
def _coach_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
    monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
    monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")


# ---------------------------------------------------------------------------
# (a) the real turn, end to end — the live order
# ---------------------------------------------------------------------------


class TestRealTurnThreeEndToEnd:
    def test_the_turn_is_approved_and_the_warnings_ride_along(
        self, tmp_path: Path
    ) -> None:
        """The real turn-3 bundle and objection. The false objection goes, the
        six honesty warnings stay attached, and the turn is approved."""
        result = _run_coach(
            _make_invoker(tmp_path),
            task_id="TASK-DEACT-005",
            turn=3,
            bundle=_bundle_from_receipt(),
            findings=[_real_false_finding_text()],
        )

        assert result.success is True
        assert result.report["decision"] == "approve"
        assert result.report["contradicted_absent_claim_voided"] is True
        # the six warnings survive onto the approve, none of them blocking
        issues = result.report["issues"]
        assert len(issues) == 6
        assert all(
            (i.get("details") or {}).get("source") == DETERMINISTIC_SOURCE
            for i in issues
        )
        assert all(i["severity"] == "should_fix" for i in issues)

    def test_the_persisted_receipt_agrees_with_the_returned_verdict(
        self, tmp_path: Path
    ) -> None:
        """The file the operator reads must say what the caller was told."""
        invoker = _make_invoker(tmp_path)
        result = _run_coach(
            invoker,
            task_id="TASK-DEACT-005",
            turn=3,
            bundle=_bundle_from_receipt(),
            findings=[_real_false_finding_text()],
        )
        on_disk = json.loads(
            invoker._get_report_path("TASK-DEACT-005", 3, "coach").read_text()
        )
        assert on_disk["decision"] == result.report["decision"] == "approve"


# ---------------------------------------------------------------------------
# (b) the other order — the warnings are already on the decision
# ---------------------------------------------------------------------------


class TestWarningsAlreadyEmbedded:
    def test_voided_plus_only_should_fix_records_becomes_approve(
        self, tmp_path: Path
    ) -> None:
        """The saved receipt's exact shape: six ``should_fix`` honesty records
        ahead of the one false objection. Promoted, warnings kept, and the
        receipt says the promotion happened over them."""
        decision = _decision_with(
            [*_real_embedded_honesty_issues(), {
                "type": "finding",
                "severity": "major",
                "description": _real_false_finding_text(),
                "suggestion": "",
                "requirement": "",
            }]
        )

        out = _call_guard_directly(
            _make_invoker(tmp_path),
            decision=decision,
            bundle=_bundle_from_receipt(),
            tmp_path=tmp_path,
        )

        assert out["decision"] == "approve"
        assert out["contradicted_absent_claim_voided"] is True
        assert out["contradicted_absent_claim_voided_then_approved"] is True
        marker = out["contradicted_absent_claim"]
        assert marker["promotion_basis"] == "advisory_records_only"
        assert marker["overridden_decision"] == "feedback"
        assert len(marker["retained_advisory_findings"]) == 6
        assert len(out["issues"]) == 6
        assert "never reject a turn" in out["rationale"]

    def test_a_major_non_honesty_finding_keeps_the_turn_rejected(
        self, tmp_path: Path
    ) -> None:
        """One real objection standing beside the false one still blocks. The
        false objection is voided; the verdict is not touched."""
        real_objection = {
            "type": "finding",
            "severity": "major",
            "description": (
                "spec_conformance.failures: R-OV-1 — the endpoint is not "
                "documented in docs/API.md"
            ),
            "suggestion": "",
            "requirement": "",
        }
        decision = _decision_with(
            [
                *_real_embedded_honesty_issues(),
                real_objection,
                {
                    "type": "finding",
                    "severity": "major",
                    "description": _real_false_finding_text(),
                },
            ]
        )

        out = _call_guard_directly(
            _make_invoker(tmp_path),
            decision=decision,
            bundle=_bundle_from_receipt(),
            tmp_path=tmp_path,
        )

        assert out["decision"] == "feedback"
        assert out["contradicted_absent_claim_voided"] is True
        assert "contradicted_absent_claim_voided_then_approved" not in out
        assert out["contradicted_absent_claim"]["overridden_decision"] is None
        assert out["contradicted_absent_claim"]["retained_advisory_findings"] == []
        assert real_objection in out["issues"]

    def test_a_critical_honesty_record_keeps_the_turn_rejected(
        self, tmp_path: Path
    ) -> None:
        """A turn-rejecting honesty record is not a warning. Its own module
        says only ``critical`` records reject a turn — so this one blocks the
        promotion even though it comes from the same deterministic source."""
        critical = _honesty_issue(severity="must_fix", record_severity="critical")
        decision = _decision_with(
            [
                critical,
                {
                    "type": "finding",
                    "severity": "major",
                    "description": _real_false_finding_text(),
                },
            ]
        )

        out = _call_guard_directly(
            _make_invoker(tmp_path),
            decision=decision,
            bundle=_bundle_from_receipt(),
            tmp_path=tmp_path,
        )

        assert out["decision"] == "feedback"
        assert out["contradicted_absent_claim_voided"] is True
        assert "contradicted_absent_claim_voided_then_approved" not in out
        assert out["issues"] == [critical]

    def test_nothing_voided_leaves_the_decision_untouched(
        self, tmp_path: Path
    ) -> None:
        """No false objection to remove: the guard writes nothing at all, not
        even when every finding standing is a warning."""
        issues = _real_embedded_honesty_issues()
        decision = _decision_with(list(issues))

        out = _call_guard_directly(
            _make_invoker(tmp_path),
            decision=decision,
            bundle=_bundle_from_receipt(),
            tmp_path=tmp_path,
        )

        assert out["decision"] == "feedback"
        assert out["issues"] == issues
        assert "contradicted_absent_claim_voided" not in out
        assert "contradicted_absent_claim_voided_then_approved" not in out

    def test_running_the_guard_twice_gives_the_same_answer(
        self, tmp_path: Path
    ) -> None:
        """Idempotent: the second pass finds no false objection and changes
        nothing, so an approve stays an approve."""
        invoker = _make_invoker(tmp_path)
        decision = _decision_with(
            [*_real_embedded_honesty_issues(), {
                "type": "finding",
                "severity": "major",
                "description": _real_false_finding_text(),
            }]
        )
        first = _call_guard_directly(
            invoker, decision=decision, bundle=_bundle_from_receipt(),
            tmp_path=tmp_path,
        )
        snapshot = json.dumps(first, sort_keys=True)
        second = _call_guard_directly(
            invoker, decision=first, bundle=_bundle_from_receipt(),
            tmp_path=tmp_path,
        )
        assert json.dumps(second, sort_keys=True) == snapshot
        assert second["decision"] == "approve"


# ---------------------------------------------------------------------------
# (c) the classifier itself
# ---------------------------------------------------------------------------


class TestNeverRejectingFindingClassifier:
    def test_a_should_fix_honesty_record_is_never_rejecting(self) -> None:
        assert (
            AgentInvoker._is_never_rejecting_finding(
                _honesty_issue("should_fix", "should_fix")
            )
            is True
        )

    @pytest.mark.parametrize(
        "issue",
        [
            pytest.param(
                _honesty_issue("must_fix", "critical"), id="critical-record"
            ),
            pytest.param(
                _honesty_issue("should_fix", "critical"),
                id="critical-record-rendered-soft",
            ),
            pytest.param(
                _honesty_issue("must_fix", "should_fix"),
                id="rendered-must-fix",
            ),
            pytest.param(
                {"severity": "should_fix", "description": "a coach objection"},
                id="no-details",
            ),
            pytest.param(
                {
                    "severity": "should_fix",
                    "description": "x",
                    "details": {"source": "somewhere_else"},
                },
                id="other-source",
            ),
            pytest.param("not a dict", id="not-a-dict"),
            pytest.param({}, id="empty"),
        ],
    )
    def test_everything_else_still_blocks(self, issue: Any) -> None:
        assert AgentInvoker._is_never_rejecting_finding(issue) is False
