"""TASK-FIX-COACHNARR01 — Coach feedback must quote deterministic discrepancy
records verbatim, not paraphrase them.

Reproduces and closes the FEAT-C332 run-2 (TASK-QAWE-002) false narrative: the
deterministic honesty gate found a REAL discrepancy (the Player claimed test
runs while the test-orchestrator specialist had hung — TASK-FIX-SPECVIOL01),
but the degraded B-min synthesis Coach invented a wrong explanation, claiming
two tracked, present-on-disk test files "do not exist on disk". The Player got
unactionable feedback and burned a turn.

These tests exercise the pure reconciler functions directly (AC-001 / AC-002 /
AC-003) and then drive the REAL ``invoke_coach`` synthesis path with a mocked
harness to prove the corrected narrative reaches the on-disk
``coach_turn_N.json`` the Player reads.

Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency,
matching the convention in ``test_coach_independent_test_absent_guard.py``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_narrative_reconciler import (
    DETERMINISTIC_SOURCE,
    extract_file_existence_paths,
    reconcile_narrative,
    render_deterministic_issues,
    strip_unsupported_nonexistence_claims,
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


# ---------------------------------------------------------------------------
# Fixtures / helpers — the FEAT-C332 run-2 records
# ---------------------------------------------------------------------------

# Verbatim rationale from
# .guardkit/autobuild/FEAT-C332-run2-artifacts-TASK-QAWE-002/coach_turn_1.json
FEATC332_RATIONALE = (
    "The implementation cannot be validated because the evidence gathering "
    "process was aborted (`partial_honesty_abort`) due to a critical honesty "
    "discrepancy. The Player claimed to have run tests in files "
    "(`tests/orchestrator/test_coach_evidence_bundle.py` and "
    "`tests/unit/orchestrator/quality_gates/test_coach_validator.py`) that do "
    "not exist on disk. Consequently, no independent test results, coverage, "
    "or quality gate data are available to confirm the requirements were met."
)

FEATC332_ISSUE_DESCRIPTION = (
    "The Player claimed to have run existing test suites in "
    "`tests/orchestrator/test_coach_evidence_bundle.py` and "
    "`tests/unit/orchestrator/quality_gates/test_coach_validator.py`, but "
    "these files do not exist on disk. This discrepancy caused the evidence "
    "gathering process to abort (`partial_honesty_abort`), making it "
    "impossible to verify the implementation."
)


def _featc332_honesty() -> HonestyVerification:
    """The actual FEAT-C332 discrepancy was a ``test_result`` claim (the hung
    specialist), NOT a ``file_existence`` discrepancy. So the set of supported
    non-existence paths is empty and the rationale's claim is fabricated."""
    return HonestyVerification(
        verified=False,
        discrepancies=[
            Discrepancy(
                claim_type="test_result",
                player_claim="tests_passed: true (50/50)",
                actual_value=(
                    "test-orchestrator specialist hung; no independent "
                    "test run completed"
                ),
                severity="critical",
            )
        ],
        honesty_score=0.0,
    )


# ---------------------------------------------------------------------------
# AC-001 — deterministic records embedded verbatim
# ---------------------------------------------------------------------------


class TestEmbedDeterministicRecords:
    def test_render_embeds_record_fields_verbatim(self) -> None:
        honesty = _featc332_honesty()
        issues = render_deterministic_issues(honesty)

        assert len(issues) == 1
        issue = issues[0]
        assert issue["category"] == "honesty"
        assert issue["severity"] == "must_fix"  # critical -> must_fix
        details = issue["details"]
        assert details["source"] == DETERMINISTIC_SOURCE
        # Verbatim copies of the record.
        assert details["claim_type"] == "test_result"
        assert details["player_claim"] == "tests_passed: true (50/50)"
        assert "specialist hung" in details["actual_value"]
        assert details["severity"] == "critical"
        # The description quotes the record, not a paraphrase.
        assert "tests_passed: true (50/50)" in issue["description"]
        assert "specialist hung" in issue["description"]

    def test_feedback_verdict_gets_records_prepended(self) -> None:
        decision = {
            "decision": "feedback",
            "rationale": "Some rationale without any non-existence claim.",
            "issues": [
                {"severity": "must_fix", "category": "x", "description": "y"}
            ],
        }
        result = reconcile_narrative(decision, _featc332_honesty())

        assert result.embedded_issue_count == 1
        assert result.changed is True
        # Prepended, so the deterministic record is first.
        assert decision["issues"][0]["details"]["source"] == DETERMINISTIC_SOURCE
        assert decision["issues"][1]["description"] == "y"

    def test_embedding_is_idempotent(self) -> None:
        decision = {
            "decision": "feedback",
            "rationale": "no claims here",
            "issues": [],
        }
        reconcile_narrative(decision, _featc332_honesty())
        count_after_first = len(decision["issues"])
        reconcile_narrative(decision, _featc332_honesty())
        assert len(decision["issues"]) == count_after_first

    def test_approve_verdict_does_not_get_records_embedded(self) -> None:
        # Embedding a must_fix honesty record into an approve verdict would be
        # self-contradictory; approve-over-discrepancy is owned by other guards.
        decision = {"decision": "approve", "rationale": "looks good", "issues": []}
        result = reconcile_narrative(decision, _featc332_honesty())
        assert result.embedded_issue_count == 0
        assert decision["issues"] == []


# ---------------------------------------------------------------------------
# AC-002 / AC-003 — unsupported non-existence claims corrected
# ---------------------------------------------------------------------------


class TestStripUnsupportedNonexistenceClaims:
    def test_featc332_rationale_no_longer_claims_files_missing(self) -> None:
        # AC-003: with no file_existence discrepancy, the verbatim FEAT-C332
        # rationale must NOT survive with a "does not exist on disk" claim.
        corrected, paths = strip_unsupported_nonexistence_claims(
            FEATC332_RATIONALE, supported_paths=set()
        )
        assert "do not exist on disk" not in corrected
        assert "does not exist on disk" not in corrected
        assert "tests/orchestrator/test_coach_evidence_bundle.py" in {
            *paths
        }  # path was flagged as corrected
        assert (
            "tests/unit/orchestrator/quality_gates/test_coach_validator.py"
            in paths
        )
        # The corrective phrasing is present.
        assert "could not be independently verified" in corrected

    def test_supported_path_claim_is_preserved(self) -> None:
        # A genuine file_existence discrepancy supports the claim — leave it.
        text = "The file `src/missing.py` does not exist on disk."
        corrected, paths = strip_unsupported_nonexistence_claims(
            text, supported_paths={"src/missing.py"}
        )
        assert corrected == text
        assert paths == []

    def test_no_nonexistence_phrase_is_untouched(self) -> None:
        text = "Tests passed and coverage is acceptable."
        corrected, paths = strip_unsupported_nonexistence_claims(text, set())
        assert corrected == text
        assert paths == []

    def test_pathless_nonexistence_phrase_left_unattributed(self) -> None:
        # No path to attribute the assertion to -> cannot judge -> leave it.
        text = "Some files do not exist on disk."
        corrected, paths = strip_unsupported_nonexistence_claims(text, set())
        assert corrected == text
        assert paths == []

    def test_mixed_clause_with_one_supported_path_is_preserved(self) -> None:
        text = (
            "Files `a/real.py` and `b/fake.py` do not exist on disk."
        )
        corrected, paths = strip_unsupported_nonexistence_claims(
            text, supported_paths={"a/real.py"}
        )
        # At least one supported path -> do not disturb the clause.
        assert corrected == text
        assert paths == []


class TestReconcileNarrativeEndToEnd:
    def test_featc332_reproducer_rationale_and_issue_corrected(self) -> None:
        decision = {
            "task_id": "TASK-QAWE-002",
            "turn": 1,
            "decision": "feedback",
            "rationale": FEATC332_RATIONALE,
            "issues": [
                {
                    "type": "test_failure",
                    "severity": "critical",
                    "description": FEATC332_ISSUE_DESCRIPTION,
                    "requirement": "AC-008",
                    "suggestion": "Ensure all claimed test files exist.",
                }
            ],
        }
        result = reconcile_narrative(decision, _featc332_honesty())

        assert result.changed is True
        # AC-003: no surviving "does not exist on disk" claim anywhere.
        assert "do not exist on disk" not in decision["rationale"]
        for issue in decision["issues"]:
            assert "do not exist on disk" not in issue.get("description", "")
            assert "does not exist on disk" not in issue.get("description", "")
        # AC-001: the real record was embedded verbatim.
        det = [
            i
            for i in decision["issues"]
            if isinstance(i.get("details"), dict)
            and i["details"].get("source") == DETERMINISTIC_SOURCE
        ]
        assert len(det) == 1
        assert det[0]["details"]["claim_type"] == "test_result"


class TestExtractFileExistencePaths:
    def test_extracts_only_file_existence_class(self) -> None:
        honesty = HonestyVerification(
            verified=False,
            discrepancies=[
                Discrepancy(
                    claim_type="file_existence",
                    player_claim="files_created: src/foo.py",
                    actual_value="File does not exist",
                    severity="critical",
                ),
                Discrepancy(
                    claim_type="test_result",
                    player_claim="tests_passed: true",
                    actual_value="hung",
                    severity="critical",
                ),
            ],
        )
        paths = extract_file_existence_paths(honesty)
        assert paths == {"src/foo.py"}

    def test_empty_when_no_file_existence(self) -> None:
        assert extract_file_existence_paths(_featc332_honesty()) == set()


# ---------------------------------------------------------------------------
# Integration — the corrected narrative reaches coach_turn_N.json on disk
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _feedback_events(task_id: str, turn: int) -> list:
    """The FEAT-C332 shape: a feedback verdict whose rationale + issue fabricate
    a 'do not exist on disk' cause for tracked, present files."""
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": "feedback",
        "rationale": FEATC332_RATIONALE,
        "issues": [
            {
                "type": "test_failure",
                "severity": "critical",
                "description": FEATC332_ISSUE_DESCRIPTION,
            }
        ],
        "criteria_verification": [],
    }
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


class TestInvokeCoachPersistsCorrectedNarrative:
    def test_corrected_narrative_written_to_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_COACH_SYNTHESIS", "1")
        invoker = _make_invoker(tmp_path)
        task_id, turn = "TASK-QAWE-002", 1

        bundle = CoachEvidenceBundle(
            honesty=_featc332_honesty(),
            gathering_status="partial_honesty_abort",
        )

        iwr = AsyncMock(return_value=(None, _feedback_events(task_id, turn)))
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id=task_id,
                    turn=turn,
                    requirements="reqs",
                    player_report={"files_modified": [], "tests_passed": True},
                    evidence_bundle=bundle,
                )
            )

        assert result.success is True
        coach_path = invoker._get_report_path(task_id, turn, "coach")
        on_disk = json.loads(coach_path.read_text())

        # AC-003: the persisted artifact the Player reads is corrected.
        assert "do not exist on disk" not in on_disk["rationale"]
        for issue in on_disk["issues"]:
            assert "do not exist on disk" not in issue.get("description", "")
        # AC-001: the deterministic record rides along verbatim.
        assert any(
            isinstance(i.get("details"), dict)
            and i["details"].get("source") == DETERMINISTIC_SOURCE
            for i in on_disk["issues"]
        )
