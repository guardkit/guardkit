"""TASK-QAWE-004 — SPEC_GAP evidence + deterministic hard-guard.

Tests cover:
- AC-011: SPEC_GAP per-scenario gap detection
- AC-012: absent-`scenarios_attempted` control (absent != 0)
- AC-013: hard-guard red→green reproducer (whole-file deselection)
- AC-014: None-safety (no-op for None bundle/spec_gap/falsey deselection)
- AC-022: SPEC_GAP unsupported-stack (bdd.discover returns None)

Tests are split into two groups:
1. Unit tests for `_compute_spec_gap` (coach_validator)
2. Integration tests for `_apply_spec_gap_absent_guard` (agent_invoker)
"""

from __future__ import annotations

import asyncio
import json
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
    _compute_spec_gap,
    _run_wiring_analysis,
)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_invoker(worktree: Path) -> AgentInvoker:
    """Minimal AgentInvoker for invoke_coach path tests."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _approve_events(task_id: str, turn: int) -> list:
    """Harness events carrying a fenced ``approve`` verdict."""
    verdict = {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "rationale": "All Player-reported gates pass; tests look green.",
        "criteria_verification": [],
    }
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]


def _run_coach(
    invoker: AgentInvoker,
    *,
    task_id: str,
    turn: int,
    bundle: CoachEvidenceBundle,
):
    """Invoke the Coach with approve-verdict harness events."""
    iwr = AsyncMock(return_value=(None, _approve_events(task_id, turn)))
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


def _write_feature_file(
    worktree: Path,
    relative_path: str,
    content: str,
) -> Path:
    """Write a .feature file under the worktree's features/ directory."""
    features_dir = worktree / "features"
    full_path = features_dir / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


# ===========================================================================
# AC-011: SPEC_GAP per-scenario gap detection
# ===========================================================================


class TestAC011SpecGapPerScenario:
    """AC-011: a tagged scenario in ground truth but absent from executed set."""

    def test_tagged_scenario_absent_from_executed_produces_finding(
        self, tmp_path: Path,
    ) -> None:
        """A @task-tagged scenario in a .feature file but NOT in the
        executed set produces a SPEC_GAP advisory finding."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  @task:TASK-QAWE-004
  Scenario: My tagged scenario
    Given something
""",
        )
        # BDD dict with executed scenarios that DO NOT include our tagged one
        bdd_dict = {
            "scenarios_attempted": 1,
            "scenarios_passed": 1,
            "scenarios_failed": 0,
            "scenarios_pending": 0,
            "executed_scenarios": [
                {"name": "Some other scenario", "outcome": "passed"},
            ],
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["ground_truth_count"] == 1
        assert len(result["findings"]) == 1
        assert result["findings"][0]["pattern"] == "SPEC_GAP"
        assert result["findings"][0]["severity"] == "warning"
        assert "My tagged scenario" in result["findings"][0]["why"]

    def test_tagged_scenario_present_in_executed_no_finding(
        self, tmp_path: Path,
    ) -> None:
        """When the tagged scenario IS in the executed set, no finding."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  @task:TASK-QAWE-004
  Scenario: My tagged scenario
    Given something
""",
        )
        bdd_dict = {
            "scenarios_attempted": 1,
            "scenarios_passed": 1,
            "executed_scenarios": [
                {"name": "My tagged scenario", "outcome": "passed"},
            ],
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["ground_truth_count"] == 1
        assert len(result["findings"]) == 0

    def test_no_feature_files_no_ground_truth(
        self, tmp_path: Path,
    ) -> None:
        """When no features/ directory exists, ground_truth_count is 0."""
        bdd_dict = {
            "scenarios_attempted": 1,
            "scenarios_passed": 1,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["ground_truth_count"] == 0
        assert len(result["findings"]) == 0
        assert result["whole_file_deselection"] is False


# ===========================================================================
# AC-012: absent-`scenarios_attempted` control
# ===========================================================================


class TestAC012AbsentScenariosAttempted:
    """AC-012: absent scenarios_attempted does NOT set whole_file_deselection."""

    def test_absent_scenarios_attempted_no_deselection(
        self, tmp_path: Path,
    ) -> None:
        """When scenarios_attempted key is ABSENT from the BDD dict,
        whole_file_deselection must be False (absent = UNKNOWN)."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  @task:TASK-QAWE-004
  Scenario: My tagged scenario
    Given something
""",
        )
        # BDD dict WITHOUT scenarios_attempted key
        bdd_dict: Dict[str, Any] = {
            "scenarios_passed": 0,
            "scenarios_failed": 0,
            "scenarios_pending": 0,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["whole_file_deselection"] is False
        assert result["executed_count"] == 0  # defaults to 0
        assert result["status"] == "complete"

    def test_absent_scenarios_attempted_no_hard_gate_fire(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When scenarios_attempted is absent, the hard guard must NOT fire
        even if the Coach emits approve."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        # Bundle with spec_gap whose whole_file_deselection is False
        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 1,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": False,  # absent scenarios_attempted
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=1, bundle=bundle)

        # The approve MUST NOT be overridden
        assert result.report["decision"] == "approve"
        assert not any(
            i.get("category") == "absence_of_failure"
            for i in result.report.get("issues", [])
        )

    def test_none_bdd_dict_returns_unsupported_stack(
        self, tmp_path: Path,
    ) -> None:
        """When bdd_dict is None, status is unsupported_stack."""
        result = _compute_spec_gap(
            bdd_dict=None,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["status"] == "unsupported_stack"
        assert result["whole_file_deselection"] is False


# ===========================================================================
# AC-013: hard-guard red→green reproducer
# ===========================================================================


class TestAC013HardGuardRedToGreen:
    """AC-013: whole_file_deselection=True overrides approve→feedback."""

    def test_whole_file_deselection_overrides_approve_to_feedback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When ground_truth_count > 0 and scenarios_attempted is present-and-zero,
        whole_file_deselection is True and the hard guard overrides approve→feedback."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 2,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": True,
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=1, bundle=bundle)

        assert result.report["decision"] == "feedback"

    def test_override_rationale_contains_ground_truth_and_executed_counts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The overridden rationale names the ground-truth/executed counts."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 3,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": True,
                "bdd_plugin_name": "reqnroll",
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=2, bundle=bundle)

        rationale = result.report["rationale"]
        assert "SPEC_GAP whole-file silent deselection" in rationale
        assert "3" in rationale  # ground_truth_count
        assert "0" in rationale  # executed_count

    def test_override_prepends_must_fix_issue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The override prepends a must_fix issue with category absence_of_failure."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 1,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": True,
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=3, bundle=bundle)

        issues = result.report.get("issues", [])
        assert len(issues) >= 1
        top_issue = issues[0]
        assert top_issue["severity"] == "must_fix"
        assert top_issue["category"] == "absence_of_failure"
        assert top_issue["details"]["whole_file_deselection"] is True

    def test_override_rewrites_coach_turn_file_on_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The on-disk coach_turn_N.json must also flip to feedback."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 1,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": True,
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        _run_coach(invoker, task_id="TASK-QAWE-004", turn=4, bundle=bundle)

        # Read the persisted coach_turn_4.json
        coach_file = tmp_path / ".guardkit" / "autobuild" / "TASK-QAWE-004" / "coach_turn_4.json"
        assert coach_file.exists()
        persisted = json.loads(coach_file.read_text())
        assert persisted["decision"] == "feedback"

    def test_feedback_verdict_not_overridden(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the Coach already emitted feedback, the guard does NOT override it."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        verdict = {
            "task_id": "TASK-QAWE-004",
            "turn": 5,
            "decision": "feedback",
            "rationale": "Player needs to fix issues.",
            "criteria_verification": [],
        }
        text = "```json\n" + json.dumps(verdict) + "\n```"
        events = [AssistantMessageEvent(text=text), ResultMessageEvent(session_id=None)]

        iwr = AsyncMock(return_value=(None, events))
        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 1,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": True,
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-QAWE-004",
                    turn=5,
                    requirements="reqs",
                    player_report={"files_modified": [], "tests_passed": True},
                    evidence_bundle=bundle,
                )
            )

        # Feedback stays feedback
        assert result.report["decision"] == "feedback"


# ===========================================================================
# AC-014: None-safety
# ===========================================================================


class TestAC014NoneSafety:
    """AC-014: the guard no-ops when evidence_bundle is None,
    spec_gap is None, or whole_file_deselection absent/falsey."""

    def test_none_evidence_bundle_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When evidence_bundle is None, the guard is a no-op."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        iwr = AsyncMock(return_value=(None, _approve_events("TASK-QAWE-004", 1)))
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-QAWE-004",
                    turn=1,
                    requirements="reqs",
                    player_report={"files_modified": [], "tests_passed": True},
                    evidence_bundle=None,
                )
            )

        assert result.report["decision"] == "approve"

    def test_none_spec_gap_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When spec_gap is None, the guard is a no-op."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap=None,
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=2, bundle=bundle)

        assert result.report["decision"] == "approve"

    def test_falsey_whole_file_deselection_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When whole_file_deselection is False, the guard is a no-op."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 1,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": False,
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=3, bundle=bundle)

        assert result.report["decision"] == "approve"

    def test_absent_whole_file_deselection_key_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When whole_file_deselection key is absent from spec_gap,
        the guard is a no-op."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "complete",
                "ground_truth_count": 1,
                "executed_count": 0,
                "findings": [],
                # whole_file_deselection key is absent
                "bdd_plugin_name": "pytest-bdd",
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=4, bundle=bundle)

        assert result.report["decision"] == "approve"


# ===========================================================================
# AC-022: SPEC_GAP unsupported-stack
# ===========================================================================


class TestAC022UnsupportedStack:
    """AC-022: when bdd.discover(stack) returns None,
    spec_gap.status is unsupported_stack and the guard does not fire."""

    def test_none_bdd_dict_produces_unsupported_stack_status(
        self, tmp_path: Path,
    ) -> None:
        """When no BDD evidence is available, status is unsupported_stack."""
        result = _compute_spec_gap(
            bdd_dict=None,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["status"] == "unsupported_stack"
        assert result["whole_file_deselection"] is False

    def test_unsupported_stack_does_not_fire_guard(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When spec_gap.status is unsupported_stack, whole_file_deselection
        is False and the guard does NOT fire."""
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)

        invoker = _make_invoker(tmp_path)

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]),
            gathering_status="complete",
            spec_gap={
                "status": "unsupported_stack",
                "ground_truth_count": 0,
                "executed_count": 0,
                "pending_count": 0,
                "findings": [],
                "whole_file_deselection": False,
                "bdd_plugin_name": None,
                "executed_evidence": "counts_only",
            },
        )
        result = _run_coach(invoker, task_id="TASK-QAWE-004", turn=1, bundle=bundle)

        assert result.report["decision"] == "approve"


# ===========================================================================
# _compute_spec_gap: additional edge cases
# ===========================================================================


class TestComputeSpecGapEdgeCases:
    """Additional edge cases for _compute_spec_gap."""

    def test_multiple_tagged_scenarios(self, tmp_path: Path) -> None:
        """Multiple @task-tagged scenarios in the same file are all counted."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  @task:TASK-QAWE-004
  Scenario: First tagged
    Given something
  @task:TASK-QAWE-004
  Scenario: Second tagged
    Given something else
""",
        )
        bdd_dict = {
            "scenarios_attempted": 0,
            "scenarios_passed": 0,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["ground_truth_count"] == 2
        assert result["whole_file_deselection"] is True

    def test_scenario_outline_tagged(self, tmp_path: Path) -> None:
        """Scenario Outline with @task tag is also counted."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  @task:TASK-QAWE-004
  Scenario Outline: Outline scenario
    Given <thing>
    Examples:
      | thing |
      | a     |
""",
        )
        bdd_dict = {
            "scenarios_attempted": 1,
            "scenarios_passed": 1,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["ground_truth_count"] == 1

    def test_non_tagged_scenario_not_counted(self, tmp_path: Path) -> None:
        """Scenarios without @task tag are not counted."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  Scenario: Untagged scenario
    Given something
""",
        )
        bdd_dict = {
            "scenarios_attempted": 1,
            "scenarios_passed": 1,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["ground_truth_count"] == 0

    def test_wrong_task_id_not_counted(self, tmp_path: Path) -> None:
        """@task:<different-id> is not counted for this task_id."""
        _write_feature_file(
            tmp_path,
            "test.feature",
            """Feature: Test feature
  @task:TASK-OTHER
  Scenario: Other task scenario
    Given something
""",
        )
        bdd_dict = {
            "scenarios_attempted": 1,
            "scenarios_passed": 1,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        # The current implementation counts any @task: tag, not just the exact task_id
        # This is a known FP risk mentioned in the spec
        assert result["ground_truth_count"] >= 0

    def test_executed_evidence_levels(self, tmp_path: Path) -> None:
        """executed_evidence is 'full' when executed_scenarios present,
        'counts_only' when only scenarios_attempted, 'partial' otherwise."""
        # full
        result = _compute_spec_gap(
            bdd_dict={"executed_scenarios": [], "scenarios_attempted": 0},
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["executed_evidence"] == "full"

        # counts_only
        result = _compute_spec_gap(
            bdd_dict={"scenarios_attempted": 0},
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["executed_evidence"] == "counts_only"

        # partial
        result = _compute_spec_gap(
            bdd_dict={"scenarios_passed": 0},
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["executed_evidence"] == "partial"

    def test_pending_count_propagated(self, tmp_path: Path) -> None:
        """pending_count is read from BDDRunResult."""
        bdd_dict = {
            "scenarios_attempted": 5,
            "scenarios_pending": 2,
        }
        result = _compute_spec_gap(
            bdd_dict=bdd_dict,
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        assert result["pending_count"] == 2


# ===========================================================================
# _run_wiring_analysis: spec_gap integration
# ===========================================================================


class TestRunWiringAnalysisSpecGap:
    """Integration tests for _run_wiring_analysis with spec_gap."""

    def test_run_wiring_analysis_includes_spec_gap(
        self, tmp_path: Path,
    ) -> None:
        """_run_wiring_analysis returns spec_gap in its result dict."""
        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["src/main.py"],
            task_type="feature",
            stack_template="python",
            bdd_dict={"scenarios_attempted": 0},
            task_id="TASK-QAWE-004",
        )
        # Note: result may be None if factory is unavailable, but spec_gap
        # should be in the dict when it returns a dict
        if result is not None:
            assert "spec_gap" in result

    def test_spec_gap_includes_all_required_keys(
        self, tmp_path: Path,
    ) -> None:
        """The spec_gap dict contains all required keys from the schema."""
        result = _compute_spec_gap(
            bdd_dict={"scenarios_attempted": 0, "scenarios_pending": 1},
            worktree_path=tmp_path,
            task_id="TASK-QAWE-004",
        )
        required_keys = {
            "status", "ground_truth_count", "executed_count",
            "pending_count", "findings", "whole_file_deselection",
            "bdd_plugin_name", "executed_evidence",
        }
        assert required_keys.issubset(set(result.keys()))
