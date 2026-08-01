"""LANE-WF — A WARNING MUST NEVER BURN A BUILD.

Regression lane for the live receipt ``build-FEAT-STV1-20260801195639``
(2026-08-01, study-tutor ``TASK-STV1-001``). The Player fixed its turn-1
failures; turns 2-5 each carried the SAME two deterministic honesty records as
the *first* issue on the verdict::

    Deterministic honesty record (claim_audit_unmodified, severity=should_fix):
    Player claim: Player claimed file src/study_tutor/http/app.py.
    Actual: Path is tracked in git but 'git status --porcelain' shows no change
    for it ... this is a warning, not a turn-rejecting fabrication.

The record's own prose says *warning*. The build ended
``max_turns_exceeded`` and the coordinator merged the (green) tree by hand.

The taxonomy (found, not invented):

* ``Discrepancy.severity`` ∈ {``critical``, ``should_fix``, ``warning``,
  ``info``} — ``coach_verification.Discrepancy``.
* ``critical`` alone is turn-rejecting: ``CoachValidator._honesty_issues_from``
  filters ``severity == "critical"`` into ``must_fix`` issues, and only those
  short-circuit ``gather_evidence`` with ``gathering_status ==
  "partial_honesty_abort"`` — which
  ``AgentInvoker._reconcile_incomplete_evidence_gathering`` turns into the
  approve→feedback flip.
* the ``claim_audit_*`` advisory family (``claim_audit_gitignored``,
  ``claim_audit_unmodified``, ``claim_audit_cross_repo``) is emitted at
  ``should_fix`` and rides along as ``advisory_issues``.

What this file pins:

1. **The STV1 shape**: an ``approve`` + only repeated ``should_fix``
   claim-audit records APPROVES, with the records recorded verbatim on the
   payload (never silently dropped) and a WARNING log.
2. **The must_fix path is byte-unchanged**: a ``critical`` record still
   rejects (``partial_honesty_abort`` → the deterministic flip), and the
   reconciler still declines to embed it into an ``approve``.
3. **Mixed** must+should: still flips, both recorded.
4. **Empty** records: nothing changes.
5. **Mutation pin, both directions**: ``reconcile_narrative`` NEVER writes
   ``decision['decision']`` on any path.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_narrative_reconciler import (
    DETERMINISTIC_SOURCE,
    MUST_FIX_DISCREPANCY_SEVERITIES,
    is_must_fix_class,
    partition_by_class,
    reconcile_narrative,
    render_deterministic_issues,
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
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# The STV1 records — copied verbatim from
# forge-state/receipts/build-FEAT-STV1-20260801195639/.guardkit/
#   autobuild-private/TASK-STV1-001/coach_evidence_turn_{2..5}.json
# ---------------------------------------------------------------------------

STV1_ACTUAL_VALUE = (
    "Path is tracked in git but 'git status --porcelain' shows no change "
    "for it — the Player claimed work on a file it did not actually modify "
    "this turn. Most likely cause: the report writer swept an "
    "orchestrator-managed path (e.g. a file under .guardkit/autobuild/ or "
    "tasks/<state>/) into files_modified. Defence-in-depth for the "
    "agent_invoker-side filter; this is a warning, not a turn-rejecting "
    "fabrication."
)

STV1_PATHS = (
    "src/study_tutor/http/app.py",
    "tests/unit/http/test_version.py",
)


def _stv1_advisory_record(path: str) -> Discrepancy:
    return Discrepancy(
        claim_type="claim_audit_unmodified",
        player_claim=f"Player claimed file {path}",
        actual_value=STV1_ACTUAL_VALUE,
        severity="should_fix",
    )


def _stv1_honesty() -> HonestyVerification:
    """The exact turn-2..5 honesty channel: advisory-only, score 1.0."""
    return HonestyVerification(
        verified=False,  # verified is "zero discrepancies", not "zero critical"
        discrepancies=[_stv1_advisory_record(p) for p in STV1_PATHS],
        honesty_score=1.0,
        should_fix_count=2,
    )


def _critical_record() -> Discrepancy:
    """A fabrication-class record — the sophisticated-lie shape."""
    return Discrepancy(
        claim_type="test_result",
        player_claim="tests_passed: true (50/50)",
        actual_value="0 tests collected; the Player fabricated the run",
        severity="critical",
    )


def _critical_honesty() -> HonestyVerification:
    return HonestyVerification(
        verified=False,
        discrepancies=[_critical_record()],
        honesty_score=0.0,
    )


def _mixed_honesty() -> HonestyVerification:
    return HonestyVerification(
        verified=False,
        discrepancies=[
            _critical_record(),
            _stv1_advisory_record(STV1_PATHS[0]),
        ],
        honesty_score=0.0,
        should_fix_count=1,
    )


class _VerdictLockedDict(dict):
    """A decision dict whose ``decision`` key CANNOT be rewritten.

    The mutation pin for "a warning never burns a build": any attempt to
    reassign the verdict from inside ``reconcile_narrative`` raises, so the
    invariant is enforced structurally rather than by an equality assertion a
    later refactor could satisfy by writing the same value back.
    """

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: D105
        if key == "decision":
            raise AssertionError(
                "reconcile_narrative must never write decision['decision'] "
                f"(attempted -> {value!r})"
            )
        super().__setitem__(key, value)


def _deterministic_issues(decision: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        i
        for i in decision.get("issues") or []
        if isinstance(i.get("details"), dict)
        and i["details"].get("source") == DETERMINISTIC_SOURCE
    ]


# ---------------------------------------------------------------------------
# 0. The severity taxonomy itself
# ---------------------------------------------------------------------------


class TestSeverityTaxonomy:
    def test_only_critical_is_must_fix_class(self) -> None:
        assert MUST_FIX_DISCREPANCY_SEVERITIES == frozenset({"critical"})
        assert is_must_fix_class(_critical_record()) is True
        for severity in ("should_fix", "warning", "info"):
            assert (
                is_must_fix_class(
                    Discrepancy(
                        claim_type="claim_audit_unmodified",
                        player_claim="x",
                        actual_value="y",
                        severity=severity,
                    )
                )
                is False
            ), f"{severity} must be advisory, never turn-rejecting"

    def test_partition_splits_mixed_records(self) -> None:
        must_fix, advisory = partition_by_class(_mixed_honesty())
        assert [d.claim_type for d in must_fix] == ["test_result"]
        assert [d.claim_type for d in advisory] == ["claim_audit_unmodified"]

    def test_claim_audit_advisory_family_is_should_fix(self) -> None:
        """``_honesty_issues_from`` is the severity source of truth."""
        validator = CoachValidator.__new__(CoachValidator)
        honesty = HonestyVerification(
            verified=False,
            discrepancies=[
                Discrepancy(
                    claim_type=claim_type,
                    player_claim="Player claimed file a/b.py",
                    actual_value="...",
                    severity="should_fix",
                )
                for claim_type in (
                    "claim_audit_unmodified",
                    "claim_audit_gitignored",
                    "claim_audit_cross_repo",
                )
            ],
            should_fix_count=3,
        )
        issues = validator._honesty_issues_from(honesty)
        assert len(issues) == 3
        assert {i["severity"] for i in issues} == {"should_fix"}
        assert {i["category"] for i in issues} == {"claim_audit"}

    def test_critical_content_claim_is_must_fix(self) -> None:
        validator = CoachValidator.__new__(CoachValidator)
        issues = validator._honesty_issues_from(_critical_honesty())
        assert [i["severity"] for i in issues] == ["must_fix"]
        assert [i["category"] for i in issues] == ["honesty"]


# ---------------------------------------------------------------------------
# 1. The STV1 regression shape — approve stays approve, records survive
# ---------------------------------------------------------------------------


class TestStv1AdvisoryRecordsNeverBurnTheTurn:
    def test_approve_with_only_should_fix_records_stays_approve(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        decision = _VerdictLockedDict(
            {
                "decision": "approve",
                "rationale": "All acceptance criteria met; tests green.",
                "issues": [],
            }
        )

        with caplog.at_level(logging.WARNING):
            result = reconcile_narrative(decision, _stv1_honesty())

        # (a) the verdict is untouched — the _VerdictLockedDict would have
        # raised on any write; assert the value too for the reader.
        assert decision["decision"] == "approve"

        # (b) the records are on the approve's payload, verbatim.
        assert result.advisory_records_recorded == 2
        assert result.embedded_issue_count == 2
        assert result.changed is True
        recorded = _deterministic_issues(decision)
        assert len(recorded) == 2
        for issue, path in zip(recorded, STV1_PATHS):
            assert issue["severity"] == "should_fix"
            assert issue["category"] == "honesty"
            details = issue["details"]
            assert details["claim_type"] == "claim_audit_unmodified"
            assert details["severity"] == "should_fix"
            assert details["player_claim"] == f"Player claimed file {path}"
            assert details["actual_value"] == STV1_ACTUAL_VALUE
            # the record's own prose survives byte-for-byte
            assert "not a turn-rejecting fabrication" in details["actual_value"]

        # (c) logged at WARNING.
        assert any(
            r.levelno == logging.WARNING and "LANE-WF" in r.getMessage()
            for r in caplog.records
        )

    def test_advisory_records_are_appended_not_headlined(self) -> None:
        """On an approve the warning rides along BEHIND the real content.

        Prepending is the feedback path's contract (the record is the reason
        for the rejection). On an approve, prepending is what made an advisory
        record read as the headline finding in the STV1 receipts.
        """
        decision = _VerdictLockedDict(
            {
                "decision": "approve",
                "rationale": "ok",
                "issues": [
                    {
                        "severity": "should_fix",
                        "category": "style",
                        "description": "pre-existing observation",
                    }
                ],
            }
        )
        reconcile_narrative(decision, _stv1_honesty())

        assert decision["issues"][0]["category"] == "style"
        assert len(decision["issues"]) == 3
        assert _deterministic_issues(decision) == decision["issues"][1:]

    def test_repeated_turns_do_not_double_record(self) -> None:
        """Turns 2-5 carried the SAME two records; re-reconciling is a no-op."""
        decision = _VerdictLockedDict(
            {"decision": "approve", "rationale": "ok", "issues": []}
        )
        reconcile_narrative(decision, _stv1_honesty())
        first = json.dumps(decision["issues"], sort_keys=True)

        for _ in range(4):  # turns 2..5
            again = reconcile_narrative(decision, _stv1_honesty())
            assert again.advisory_records_recorded == 0
            assert again.changed is False

        assert json.dumps(decision["issues"], sort_keys=True) == first
        assert decision["decision"] == "approve"

    def test_gather_evidence_does_not_abort_on_advisory_records(
        self, tmp_path: Path
    ) -> None:
        """The gate itself: advisory-only records never reach the abort seam.

        ``partial_honesty_abort`` is the ONLY honesty-sourced status that the
        deterministic verdict override (``_reconcile_incomplete_evidence_gathering``)
        turns into a rejection.
        """
        _init_git_worktree(tmp_path)
        _write_results(tmp_path, "TASK-STV1-001", _passing_results())

        validator = CoachValidator(str(tmp_path), task_id="TASK-STV1-001")
        with patch.object(
            validator, "_verify_honesty", return_value=_stv1_honesty()
        ):
            bundle = validator.gather_evidence(
                task_id="TASK-STV1-001",
                turn=2,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "x",
                },
            )

        assert bundle.gathering_status != "partial_honesty_abort"
        advisory_claim_types = {
            i.get("details", {}).get("claim_type")
            for i in bundle.advisory_issues
            if isinstance(i.get("details"), dict)
        }
        assert "claim_audit_unmodified" in advisory_claim_types


# ---------------------------------------------------------------------------
# 2. The must_fix path — byte-unchanged vs main
# ---------------------------------------------------------------------------


class TestMustFixPathUnchanged:
    def test_feedback_still_gets_critical_record_prepended(self) -> None:
        decision = _VerdictLockedDict(
            {
                "decision": "feedback",
                "rationale": "rejected",
                "issues": [
                    {"severity": "must_fix", "category": "x", "description": "y"}
                ],
            }
        )
        result = reconcile_narrative(decision, _critical_honesty())

        assert result.embedded_issue_count == 1
        assert result.advisory_records_recorded == 0
        assert decision["issues"][0]["severity"] == "must_fix"
        assert decision["issues"][0]["details"]["source"] == DETERMINISTIC_SOURCE
        assert decision["issues"][1]["description"] == "y"

    def test_approve_over_critical_record_is_left_to_the_real_guard(
        self,
    ) -> None:
        """Byte-unchanged from main: no embed, no verdict touch.

        The flip for a critical record is owned by
        ``gather_evidence`` → ``partial_honesty_abort`` →
        ``_reconcile_incomplete_evidence_gathering`` (asserted below), not by
        this narrative seam.
        """
        decision = _VerdictLockedDict(
            {"decision": "approve", "rationale": "looks good", "issues": []}
        )
        result = reconcile_narrative(decision, _critical_honesty())

        assert result.embedded_issue_count == 0
        assert result.advisory_records_recorded == 0
        assert result.changed is False
        assert decision["issues"] == []

    def test_gather_evidence_aborts_on_critical_record(
        self, tmp_path: Path
    ) -> None:
        _init_git_worktree(tmp_path)
        _write_results(tmp_path, "TASK-STV1-001", _passing_results())

        validator = CoachValidator(str(tmp_path), task_id="TASK-STV1-001")
        with patch.object(
            validator, "_verify_honesty", return_value=_critical_honesty()
        ):
            bundle = validator.gather_evidence(
                task_id="TASK-STV1-001",
                turn=2,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "x",
                },
            )

        assert bundle.gathering_status == "partial_honesty_abort"

    def test_critical_record_still_flips_an_approve(self, tmp_path: Path) -> None:
        """The end of the must_fix path: approve → feedback, deterministically."""
        invoker = _build_invoker(tmp_path)
        decision: Dict[str, Any] = {
            "decision": "approve",
            "rationale": "all good",
            "issues": [],
        }
        bundle = CoachEvidenceBundle(
            honesty=_critical_honesty(),
            gathering_status="partial_honesty_abort",
        )

        invoker._reconcile_incomplete_evidence_gathering(
            decision=decision,
            evidence_bundle=bundle,
            task_id="TASK-STV1-001",
            turn=2,
            coach_output_path=tmp_path / "coach_turn_2.json",
        )

        assert decision["decision"] == "feedback"

    def test_advisory_only_bundle_does_not_flip_an_approve(
        self, tmp_path: Path
    ) -> None:
        """The same guard, the STV1 status: complete → the approve survives."""
        invoker = _build_invoker(tmp_path)
        decision: Dict[str, Any] = {
            "decision": "approve",
            "rationale": "all good",
            "issues": [],
        }
        bundle = CoachEvidenceBundle(
            honesty=_stv1_honesty(),
            gathering_status="complete",
        )

        invoker._reconcile_incomplete_evidence_gathering(
            decision=decision,
            evidence_bundle=bundle,
            task_id="TASK-STV1-001",
            turn=2,
            coach_output_path=tmp_path / "coach_turn_2.json",
        )

        assert decision["decision"] == "approve"


# ---------------------------------------------------------------------------
# 3. Mixed + empty
# ---------------------------------------------------------------------------


class TestMixedAndEmptyRecords:
    def test_mixed_records_flip_and_both_are_recorded(
        self, tmp_path: Path
    ) -> None:
        # The flip half: a critical record in the mix still aborts gathering.
        _init_git_worktree(tmp_path)
        _write_results(tmp_path, "TASK-STV1-001", _passing_results())
        validator = CoachValidator(str(tmp_path), task_id="TASK-STV1-001")
        with patch.object(
            validator, "_verify_honesty", return_value=_mixed_honesty()
        ):
            bundle = validator.gather_evidence(
                task_id="TASK-STV1-001",
                turn=2,
                task={
                    "acceptance_criteria": ["AC-001"],
                    "task_type": "feature",
                    "description": "x",
                },
            )
        assert bundle.gathering_status == "partial_honesty_abort"

        # The record half: the resulting feedback carries BOTH verbatim, each
        # at its own severity.
        decision = _VerdictLockedDict(
            {"decision": "feedback", "rationale": "rejected", "issues": []}
        )
        result = reconcile_narrative(decision, _mixed_honesty())

        assert result.embedded_issue_count == 2
        recorded = _deterministic_issues(decision)
        assert [i["severity"] for i in recorded] == ["must_fix", "should_fix"]
        assert [i["details"]["claim_type"] for i in recorded] == [
            "test_result",
            "claim_audit_unmodified",
        ]

    def test_approve_with_mixed_records_is_left_to_the_real_guard(self) -> None:
        decision = _VerdictLockedDict(
            {"decision": "approve", "rationale": "ok", "issues": []}
        )
        result = reconcile_narrative(decision, _mixed_honesty())

        assert result.embedded_issue_count == 0
        assert result.advisory_records_recorded == 0
        assert decision["issues"] == []

    @pytest.mark.parametrize("verdict", ["approve", "feedback"])
    def test_empty_records_change_nothing(self, verdict: str) -> None:
        decision = _VerdictLockedDict(
            {
                "decision": verdict,
                "rationale": "nothing to reconcile",
                "issues": [],
            }
        )
        result = reconcile_narrative(
            decision, HonestyVerification(verified=True, discrepancies=[])
        )

        assert result.changed is False
        assert result.embedded_issue_count == 0
        assert result.advisory_records_recorded == 0
        assert decision["issues"] == []
        assert decision["rationale"] == "nothing to reconcile"

    def test_render_subset_is_the_advisory_partition(self) -> None:
        honesty = _mixed_honesty()
        _, advisory = partition_by_class(honesty)
        rendered = render_deterministic_issues(honesty, discrepancies=advisory)
        assert [i["details"]["claim_type"] for i in rendered] == [
            "claim_audit_unmodified"
        ]
        # default (no subset) is byte-unchanged: every record, in order
        assert [
            i["details"]["claim_type"]
            for i in render_deterministic_issues(honesty)
        ] == ["test_result", "claim_audit_unmodified"]


# ---------------------------------------------------------------------------
# 4. The Coach prompt must frame advisory records as advisory
# ---------------------------------------------------------------------------


class TestCoachPromptAdvisoryFraming:
    def test_advisory_honesty_record_guard_is_rendered(
        self, tmp_path: Path
    ) -> None:
        guards = _build_invoker(tmp_path)._render_absence_of_failure_guards()
        assert "ADVISORY HONESTY-RECORD GUARD" in guards
        # the pre-existing turn-rejecting guard is untouched
        assert "SOPHISTICATED-LIE GUARD" in guards

    def test_advisory_only_records_do_not_trigger_the_honesty_directive(
        self, tmp_path: Path
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-STV1-001",
            turn=2,
            requirements="reqs",
            player_report={"files_modified": list(STV1_PATHS)},
            evidence_bundle=CoachEvidenceBundle(
                honesty=_stv1_honesty(), gathering_status="complete"
            ),
        )
        assert "CONSIDER HONESTY DISCREPANCIES" not in prompt
        # the records themselves still reach the Coach — recorded, not hidden
        assert "claim_audit_unmodified" in prompt

    def test_critical_records_still_trigger_the_honesty_directive(
        self, tmp_path: Path
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_coach_prompt(
            task_id="TASK-STV1-001",
            turn=2,
            requirements="reqs",
            player_report={"files_modified": []},
            evidence_bundle=CoachEvidenceBundle(
                honesty=_critical_honesty(), gathering_status="complete"
            ),
        )
        assert "CONSIDER HONESTY DISCREPANCIES" in prompt


# ---------------------------------------------------------------------------
# 5. The operator log must not blame the warning
# ---------------------------------------------------------------------------


class TestOperatorSummaryNeverHeadlinesAWarning:
    """The STV1 receipt line, exactly.

    The v4 contract emits every Coach finding at the CONSTANT severity
    ``"major"`` (``coach_output_parser._adapt_v4_to_internal``). That value was
    missing from ``_build_feedback_summary``'s severity map, so it scored the
    unknown default (99) and lost to the ``should_fix`` advisory riding along —
    printing the warning as the reason for five turns whose actual blocker was
    a failing ``spec_conformance`` rule.
    """

    @staticmethod
    def _summary(issues: List[Dict[str, Any]]) -> str:
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        return AutoBuildOrchestrator._build_feedback_summary(
            None,  # type: ignore[arg-type] — the body does not touch self
            {"issues": issues},
            "fallback text",
        )

    def _stv1_issues(self) -> List[Dict[str, Any]]:
        advisory = render_deterministic_issues(_stv1_honesty())
        finding = {
            "type": "finding",
            "severity": "major",
            "description": (
                'spec_conformance.failures: rule_id="R-STV1-TESTS", '
                'kind="assert_command", detail="Command exited 1 (expected 0)"'
            ),
            "suggestion": "",
            "requirement": "",
        }
        return [*advisory, finding]

    def test_v4_finding_outranks_the_advisory_record(self) -> None:
        summary = self._summary(self._stv1_issues())
        assert summary.startswith("Feedback: spec_conformance.failures")
        assert "Deterministic honesty record" not in summary

    def test_advisory_record_still_shown_when_it_is_all_there_is(self) -> None:
        summary = self._summary(render_deterministic_issues(_stv1_honesty()))
        assert "Deterministic honesty record" in summary

    def test_must_fix_honesty_record_still_headlines(self) -> None:
        """Byte-unchanged: a critical record IS the reason — it leads."""
        issues = [
            {
                "type": "finding",
                "severity": "major",
                "description": "spec_conformance.failures: something else",
            },
            *render_deterministic_issues(_critical_honesty()),
        ]
        summary = self._summary(issues)
        assert "Deterministic honesty record" in summary

    def test_v4_major_outranks_a_plain_should_fix_issue(self) -> None:
        """Mechanism 1 in isolation: "major" must be IN the severity map.

        No advisory-source marker here, so only the severity ranking can
        decide — a v4 rejection reason must not lose to a should_fix rider.
        """
        summary = self._summary(
            [
                {"severity": "should_fix", "description": "rider observation"},
                {"severity": "major", "description": "the real blocker"},
            ]
        )
        assert summary == "Feedback: the real blocker"

    def test_advisory_record_loses_even_when_its_severity_ranks_better(
        self,
    ) -> None:
        """Mechanism 2 in isolation: the advisory-last tiebreak.

        A ``should_fix`` advisory record outranks a ``minor`` finding on
        severity alone — but the finding is the reason the turn was rejected.
        """
        issues = [
            *render_deterministic_issues(_stv1_honesty()),
            {"severity": "minor", "description": "the real blocker"},
        ]
        summary = self._summary(issues)
        assert summary == "Feedback: the real blocker"

    def test_existing_must_fix_over_warning_contract_holds(self) -> None:
        summary = self._summary(
            [
                {"severity": "warning", "description": "Advisory (non-blocking)"},
                {"severity": "must_fix", "description": "Plan audit detected"},
            ]
        )
        assert summary == "Feedback: Plan audit detected"


# ---------------------------------------------------------------------------
# 6. End to end — the approve and its records reach coach_turn_N.json
# ---------------------------------------------------------------------------


def _approve_events(task_id: str, turn: int) -> list:
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "rationale": "All acceptance criteria verified against the evidence.",
        "issues": [],
        "criteria_verification": [],
    }
    return [
        AssistantMessageEvent(text="```json\n" + json.dumps(verdict) + "\n```"),
        ResultMessageEvent(session_id=None),
    ]


class TestApproveSurvivesToDisk:
    def test_approve_with_advisory_records_persists_as_approve(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_SYNTHESIS", "1")
        invoker = _make_full_invoker(tmp_path)
        task_id, turn = "TASK-STV1-001", 2

        bundle = CoachEvidenceBundle(
            honesty=_stv1_honesty(), gathering_status="complete"
        )
        iwr = AsyncMock(return_value=(None, _approve_events(task_id, turn)))
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id=task_id,
                    turn=turn,
                    requirements="reqs",
                    player_report={
                        "files_modified": list(STV1_PATHS),
                        "tests_passed": True,
                    },
                    evidence_bundle=bundle,
                )
            )

        assert result.success is True
        assert result.report["decision"] == "approve"

        on_disk = json.loads(
            invoker._get_report_path(task_id, turn, "coach").read_text()
        )
        assert on_disk["decision"] == "approve"
        recorded = _deterministic_issues(on_disk)
        assert len(recorded) == 2
        assert {i["details"]["claim_type"] for i in recorded} == {
            "claim_audit_unmodified"
        }
        assert all(i["severity"] == "should_fix" for i in recorded)


# ---------------------------------------------------------------------------
# Fixture helpers (mirrors tests/orchestrator/test_coach_zero_cardinality_guard.py)
# ---------------------------------------------------------------------------


def _init_git_worktree(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"],
        check=True,
        capture_output=True,
    )


def _write_results(worktree: Path, task_id: str, results: dict) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(results))


def _passing_results() -> dict:
    return {
        "task_id": "TASK-STV1-001",
        "quality_gates": {
            "all_passed": True,
            "tests_run": 5,
            "tests_failed": 0,
            "coverage_met": True,
            "line_coverage": 0.85,
            "branch_coverage": 0.78,
        },
        "code_review": {"score": 80},
        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
        "files_modified": list(STV1_PATHS),
        "files_created": [],
        "tests_written": [],
    }


def _build_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


def _make_full_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def test_unknown_severity_shape_never_acquires_verdict_power():
    """Coordinator pin (the WF coach's one surviving mutant): a record with NO
    severity attribute defaults to ADVISORY — an unknown shape must never
    acquire turn-rejecting power by accident."""
    from guardkit.orchestrator.coach_narrative_reconciler import is_must_fix_class

    class _NoSeverity:
        pass

    assert is_must_fix_class(_NoSeverity()) is False
