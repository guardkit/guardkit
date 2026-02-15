"""
Unit tests for TASK-REV-E719 Run 3 stall fixes.

Covers three fixes:
1. Fix 1: Criteria parser ignores indented sub-bullets (task_loader.py)
2. Fix 2: Hybrid matching fallback for missing promises (coach_validator.py)
3. Fix 3: Stall detector differentiates partial progress (autobuild.py)
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.tasks.task_loader import TaskLoader
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CriterionResult,
    RequirementsValidation,
)
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


# ============================================================================
# Fix 1: Criteria Parser -- Indented Sub-Bullets
# ============================================================================


class TestCriteriaParserSubBullets:
    """Test that _extract_acceptance_criteria ignores indented sub-bullets."""

    def test_nested_sub_bullets_not_inflated(self, tmp_path):
        """Indented sub-bullets should NOT be parsed as separate criteria.

        This is the exact pattern from TASK-SFT-001 that caused 10 criteria
        instead of 6.
        """
        task_file = tmp_path / "tasks" / "backlog" / "TASK-TEST-001.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            """---
id: TASK-TEST-001
title: Test nested criteria
---

## Acceptance Criteria

- [ ] `tests/seam/` directory exists with `__init__.py`
- [ ] `tests/seam/conftest.py` provides shared fixtures:
  - `graphiti_mock_client` — AsyncMock that records upsert calls
  - `cli_runner` — Click CliRunner configured for seam testing
  - `tmp_task_dir` — Temporary task directory with proper structure
  - `minimal_spec_fixture` — Path to minimal architecture spec
- [ ] `pytest.ini` or `pyproject.toml` registers `@pytest.mark.seam` marker
- [ ] `tests/seam/` tests are discovered and run by `pytest tests/seam/`
- [ ] Existing tests are NOT moved (migration is a separate task)
- [ ] `tests/fixtures/minimal-spec.md` fixture file created
"""
        )

        task_data = TaskLoader.load_task("TASK-TEST-001", repo_root=tmp_path)

        # Should be 6 criteria, not 10
        assert len(task_data["acceptance_criteria"]) == 6

    def test_top_level_bullets_still_parsed(self, tmp_path):
        """Top-level list items should still be parsed correctly."""
        task_file = tmp_path / "tasks" / "backlog" / "TASK-TEST-002.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            """---
id: TASK-TEST-002
title: Test flat criteria
---

## Acceptance Criteria

- [ ] First criterion
- [ ] Second criterion
- [ ] Third criterion
"""
        )

        task_data = TaskLoader.load_task("TASK-TEST-002", repo_root=tmp_path)
        assert len(task_data["acceptance_criteria"]) == 3
        assert task_data["acceptance_criteria"][0] == "First criterion"

    def test_mixed_bullet_styles(self, tmp_path):
        """Different top-level bullet styles should all be parsed."""
        task_file = tmp_path / "tasks" / "backlog" / "TASK-TEST-003.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            """---
id: TASK-TEST-003
title: Test mixed bullets
---

## Acceptance Criteria

- [ ] Checkbox item
- [x] Completed checkbox item
- Plain bullet item
* Star bullet item
"""
        )

        task_data = TaskLoader.load_task("TASK-TEST-003", repo_root=tmp_path)
        assert len(task_data["acceptance_criteria"]) == 4

    def test_deeply_indented_sub_bullets_ignored(self, tmp_path):
        """Multiple levels of indentation should all be ignored."""
        task_file = tmp_path / "tasks" / "backlog" / "TASK-TEST-004.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            """---
id: TASK-TEST-004
title: Test deep nesting
---

## Acceptance Criteria

- [ ] Parent criterion
  - Sub-bullet level 1
    - Sub-bullet level 2
      - Sub-bullet level 3
- [ ] Second parent criterion
"""
        )

        task_data = TaskLoader.load_task("TASK-TEST-004", repo_root=tmp_path)
        assert len(task_data["acceptance_criteria"]) == 2

    def test_tab_indented_sub_bullets_ignored(self, tmp_path):
        """Tab-indented sub-bullets should also be ignored."""
        task_file = tmp_path / "tasks" / "backlog" / "TASK-TEST-005.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(
            "---\nid: TASK-TEST-005\ntitle: Test tabs\n---\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] Parent criterion\n"
            "\t- Tab-indented sub-bullet\n"
            "- [ ] Second criterion\n"
        )

        task_data = TaskLoader.load_task("TASK-TEST-005", repo_root=tmp_path)
        assert len(task_data["acceptance_criteria"]) == 2


# ============================================================================
# Fix 2: Hybrid Matching Fallback
# ============================================================================


class TestHybridMatchingFallback:
    """Test _hybrid_fallback method in CoachValidator."""

    def _make_validator(self, tmp_path):
        """Create a CoachValidator with temporary worktree."""
        worktree = tmp_path / "worktree"
        worktree.mkdir(parents=True, exist_ok=True)
        return CoachValidator(str(worktree))

    def test_hybrid_upgrades_rejected_criteria(self, tmp_path):
        """Criteria rejected by promises should be upgraded via text matching."""
        validator = self._make_validator(tmp_path)

        # Promise-based validation: AC-001 verified, AC-002 rejected
        promise_validation = RequirementsValidation(
            criteria_total=2,
            criteria_met=1,
            all_criteria_met=False,
            missing=["tests/fixtures/minimal-spec.md fixture file created for system-plan seam tests"],
            criteria_results=[
                CriterionResult(
                    criterion_id="AC-001",
                    criterion_text="Create tests/seam directory",
                    result="verified",
                    status="verified",
                    evidence="Player completed AC-001",
                ),
                CriterionResult(
                    criterion_id="AC-002",
                    criterion_text="tests/fixtures/minimal-spec.md fixture file created for system-plan seam tests",
                    result="rejected",
                    status="rejected",
                    evidence="No completion promise for AC-002",
                ),
            ],
        )

        # requirements_addressed contains text that closely matches AC-002
        requirements_addressed = [
            "Created tests/seam directory with __init__.py",
            "tests/fixtures/minimal-spec.md fixture file created for system-plan seam tests",
        ]

        result = validator._hybrid_fallback(
            promise_validation,
            [
                "Create tests/seam directory",
                "tests/fixtures/minimal-spec.md fixture file created for system-plan seam tests",
            ],
            requirements_addressed,
        )

        assert result.criteria_met == 2
        assert result.all_criteria_met is True
        assert len(result.missing) == 0
        # AC-001 should still be from promises
        assert result.criteria_results[0].evidence == "Player completed AC-001"
        # AC-002 should be upgraded via text fallback
        assert "[Text fallback]" in result.criteria_results[1].evidence

    def test_hybrid_keeps_verified_from_promises(self, tmp_path):
        """Criteria already verified by promises should not be re-evaluated."""
        validator = self._make_validator(tmp_path)

        promise_validation = RequirementsValidation(
            criteria_total=2,
            criteria_met=2,
            all_criteria_met=True,
            missing=[],
            criteria_results=[
                CriterionResult(
                    criterion_id="AC-001",
                    criterion_text="Create directory",
                    result="verified",
                    status="verified",
                    evidence="Player completed AC-001",
                ),
                CriterionResult(
                    criterion_id="AC-002",
                    criterion_text="Add tests",
                    result="verified",
                    status="verified",
                    evidence="Player completed AC-002",
                ),
            ],
        )

        result = validator._hybrid_fallback(
            promise_validation,
            ["Create directory", "Add tests"],
            ["Some text"],
        )

        assert result.criteria_met == 2
        assert result.all_criteria_met is True
        # Both should retain original promise evidence
        assert result.criteria_results[0].evidence == "Player completed AC-001"
        assert result.criteria_results[1].evidence == "Player completed AC-002"

    def test_hybrid_does_not_false_positive(self, tmp_path):
        """Text matching should not match unrelated requirements_addressed."""
        validator = self._make_validator(tmp_path)

        promise_validation = RequirementsValidation(
            criteria_total=2,
            criteria_met=1,
            all_criteria_met=False,
            missing=["Implement OAuth2 authentication flow"],
            criteria_results=[
                CriterionResult(
                    criterion_id="AC-001",
                    criterion_text="Create directory",
                    result="verified",
                    status="verified",
                    evidence="Player completed AC-001",
                ),
                CriterionResult(
                    criterion_id="AC-002",
                    criterion_text="Implement OAuth2 authentication flow",
                    result="rejected",
                    status="rejected",
                    evidence="No completion promise for AC-002",
                ),
            ],
        )

        # requirements_addressed has unrelated content
        requirements_addressed = [
            "Created conftest.py with fixtures",
            "Added __init__.py file",
        ]

        result = validator._hybrid_fallback(
            promise_validation,
            ["Create directory", "Implement OAuth2 authentication flow"],
            requirements_addressed,
        )

        # AC-002 should still be rejected (no match)
        assert result.criteria_met == 1
        assert result.all_criteria_met is False
        assert "Implement OAuth2 authentication flow" in result.missing

    def test_validate_requirements_uses_hybrid(self, tmp_path):
        """validate_requirements should use hybrid fallback when promises exist but miss some criteria."""
        validator = self._make_validator(tmp_path)

        # Create task_work_results.json with promises for only AC-001
        results_dir = tmp_path / "worktree" / ".guardkit" / "autobuild" / "TASK-001"
        results_dir.mkdir(parents=True, exist_ok=True)

        task_work_results = {
            "task_id": "TASK-001",
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "status": "complete",
                    "evidence": "Created directory",
                },
            ],
            "requirements_addressed": [
                "Created tests/seam directory with __init__.py",
                "tests/fixtures/minimal-spec.md fixture file created for seam tests",
            ],
        }

        task = {
            "acceptance_criteria": [
                "Create tests/seam directory",
                "tests/fixtures/minimal-spec.md fixture file created for seam tests",
            ],
        }

        result = validator.validate_requirements(task, task_work_results)

        # AC-001 should be verified via promises
        assert result.criteria_results[0].result == "verified"
        # AC-002 should be verified via hybrid text fallback (exact or substring match)
        assert result.criteria_results[1].result == "verified"
        assert result.all_criteria_met is True


# ============================================================================
# Fix 3: Stall Detector Partial Progress
# ============================================================================


class TestStallDetectorPartialProgress:
    """Test that stall detector differentiates partial progress from zero progress."""

    def test_zero_progress_stalls_at_threshold(self):
        """0 criteria passing should trigger stall at default threshold (3 turns)."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        assert orchestrator._is_feedback_stalled("Same feedback", 0) is False
        assert orchestrator._is_feedback_stalled("Same feedback", 0) is False
        assert orchestrator._is_feedback_stalled("Same feedback", 0) is True

    def test_partial_progress_does_not_stall_at_3(self):
        """Partial progress (>0 criteria) should NOT trigger stall at 3 turns."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False
        # With partial progress, extended threshold applies (3+2=5)
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False

    def test_partial_progress_stalls_at_extended_threshold(self):
        """Partial progress should trigger stall at extended threshold (5 turns)."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False  # Turn 1
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False  # Turn 2
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False  # Turn 3
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False  # Turn 4
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is True   # Turn 5

    def test_partial_progress_resets_on_different_feedback(self):
        """Different feedback should reset the stall counter."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        orchestrator._is_feedback_stalled("Same feedback", 6)
        orchestrator._is_feedback_stalled("Same feedback", 6)
        orchestrator._is_feedback_stalled("Same feedback", 6)
        # Different feedback breaks the streak
        orchestrator._is_feedback_stalled("Different feedback", 6)
        orchestrator._is_feedback_stalled("Same feedback", 6)
        orchestrator._is_feedback_stalled("Same feedback", 6)
        # Only 2 turns of new streak, should not stall
        assert orchestrator._is_feedback_stalled("Same feedback", 6) is False

    def test_partial_progress_resets_on_criteria_increase(self):
        """Increasing criteria count should reset the stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        orchestrator._is_feedback_stalled("Same feedback", 6)
        orchestrator._is_feedback_stalled("Same feedback", 6)
        orchestrator._is_feedback_stalled("Same feedback", 6)
        # Criteria increased from 6 to 7 - different count breaks the streak
        assert orchestrator._is_feedback_stalled("Same feedback", 7) is False

    def test_zero_progress_custom_threshold(self):
        """Zero progress with custom threshold should still fire at that threshold."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=10,
        )

        for _ in range(4):
            result = orchestrator._is_feedback_stalled("Fix it", 0, threshold=5)
            assert result is False

        assert orchestrator._is_feedback_stalled("Fix it", 0, threshold=5) is True
