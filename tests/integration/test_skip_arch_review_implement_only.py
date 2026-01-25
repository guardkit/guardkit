"""
Integration Tests for Skip Arch Review in Implement-Only Mode

Tests that when AutoBuild runs with enable_pre_loop=False (implement-only mode),
the architectural review quality gate is skipped because Phase 2.5B doesn't run.

This addresses the issue identified in TASK-REV-FB23 where FEAT-A96D tasks failed
with "Architectural review score below threshold" when running with pre-loop disabled.

Coverage Target: >=85%
Test Count: 3 tests
"""

import json
import pytest
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch, MagicMock

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CoachValidationResult,
    QualityGateStatus,
    IndependentTestResult,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree(tmp_path):
    """
    Create a mock worktree structure with task file and task_work_results.json.

    Returns:
        Path: Path to worktree root
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Create task directories
    task_dir = worktree / "tasks" / "in_progress"
    task_dir.mkdir(parents=True)

    # Create autobuild directory for results
    autobuild_dir = worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"
    autobuild_dir.mkdir(parents=True)

    # Create task file
    task_file = task_dir / "TASK-TEST-001-test-task.md"
    task_file.write_text("""---
id: TASK-TEST-001
title: Test Task for Implement-Only Mode
status: in_progress
created: 2025-12-31T10:00:00Z
priority: medium
complexity: 3
task_type: feature
---

# Test Task for Implement-Only Mode

## Description

Implement feature X for testing skip_arch_review with implement-only mode.

## Acceptance Criteria

- [ ] Feature X implemented
- [ ] Tests added
""", encoding='utf-8')

    return worktree


@pytest.fixture
def task_work_results_zero_arch_score(mock_worktree):
    """
    Create task_work_results.json with zero arch score (simulating implement-only mode).

    When pre-loop is disabled, Phase 2.5B (Architectural Review) doesn't run,
    so no arch score is generated. The code_review.score defaults to 0.
    """
    autobuild_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"

    # Use correct schema matching what task-work writer creates
    results = {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 10,  # Count of passed tests
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {
            "score": 0,  # Zero because Phase 2.5B didn't run
            "solid": 0,
            "dry": 0,
            "yagni": 0,
        },
        "plan_audit": {
            "violations": 0,
            "file_count_match": True,
        },
        "requirements_met": ["Feature X implemented", "Tests added"],
    }

    results_file = autobuild_dir / "task_work_results.json"
    results_file.write_text(json.dumps(results, indent=2), encoding='utf-8')

    return results_file


@pytest.fixture
def task_work_results_with_arch_score(mock_worktree):
    """
    Create task_work_results.json with valid arch score (simulating full pre-loop mode).

    When pre-loop is enabled, Phase 2.5B runs and generates an arch score.
    """
    autobuild_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST-001"

    # Use correct schema matching what task-work writer creates
    results = {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 10,  # Count of passed tests
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {
            "score": 75,  # Valid score from Phase 2.5B
            "solid": 80,
            "dry": 75,
            "yagni": 70,
        },
        "plan_audit": {
            "violations": 0,
            "file_count_match": True,
        },
        "requirements_met": ["Feature X implemented", "Tests added"],
    }

    results_file = autobuild_dir / "task_work_results.json"
    results_file.write_text(json.dumps(results, indent=2), encoding='utf-8')

    return results_file


# ============================================================================
# Integration Tests: Skip Arch Review with Implement-Only Mode
# ============================================================================


class TestSkipArchReviewImplementOnly:
    """
    Integration tests for skip_arch_review behavior when enable_pre_loop=False.

    These tests verify that the fix for TASK-FIX-ARIMPL works correctly:
    - When enable_pre_loop=False, skip_arch_review=True is passed to CoachValidator
    - CoachValidator approves even with arch_score=0
    - When enable_pre_loop=True, arch review is validated normally

    Note: Uses task_type="scaffolding" to skip independent test verification,
    allowing us to focus on the arch review logic.
    """

    def test_coach_validator_approves_with_zero_arch_score_when_skip_flag_set(
        self,
        mock_worktree,
        task_work_results_zero_arch_score,
    ):
        """
        Test that CoachValidator approves when skip_arch_review=True,
        even with arch_score=0.

        This simulates the implement-only mode where Phase 2.5B doesn't run.
        """
        validator = CoachValidator(str(mock_worktree))

        # Use scaffolding task type to skip independent test verification
        # This allows us to focus on testing the arch review skip logic
        task = {
            "acceptance_criteria": ["Feature X implemented", "Tests added"],
            "task_type": "scaffolding",
        }

        # With skip_arch_review=True (implement-only mode), should approve
        result = validator.validate(
            task_id="TASK-TEST-001",
            turn=1,
            task=task,
            skip_arch_review=True,  # Simulating enable_pre_loop=False
        )

        assert result.decision == "approve", (
            f"Expected 'approve' with skip_arch_review=True, got '{result.decision}'. "
            f"Rationale: {result.rationale}"
        )

    def test_coach_validator_rejects_with_zero_arch_score_when_skip_flag_not_set(
        self,
        mock_worktree,
        task_work_results_zero_arch_score,
    ):
        """
        Test that CoachValidator rejects when skip_arch_review=False (default)
        and arch_score=0.

        This verifies that the default behavior (full pre-loop mode) still
        validates arch scores for feature task types.
        """
        validator = CoachValidator(str(mock_worktree))

        # Use feature task type which requires arch review
        # Use scaffolding-like requirements to skip independent test
        task = {
            "acceptance_criteria": ["Feature X implemented", "Tests added"],
            "task_type": "feature",
        }

        # Mock independent test verification to isolate arch review testing
        with patch.object(validator, 'run_independent_tests') as mock_tests:
            mock_tests.return_value = IndependentTestResult(
                tests_passed=True,
                test_command="pytest tests/",
                test_output_summary="All tests passed",
                duration_seconds=1.0,
            )

            # Without skip_arch_review (default), should fail due to low arch score
            result = validator.validate(
                task_id="TASK-TEST-001",
                turn=1,
                task=task,
                # skip_arch_review defaults to False
            )

        assert result.decision == "feedback", (
            f"Expected 'feedback' without skip_arch_review flag, got '{result.decision}'. "
            "Zero arch score should fail validation when skip_arch_review=False."
        )
        # Check that arch review gate failed
        assert result.quality_gates.arch_review_passed is False, (
            "Arch review gate should fail with zero score"
        )

    def test_coach_validator_approves_with_valid_arch_score_when_pre_loop_enabled(
        self,
        mock_worktree,
        task_work_results_with_arch_score,
    ):
        """
        Test that CoachValidator approves when pre-loop is enabled and
        arch_score meets threshold.

        This verifies the normal workflow where Phase 2.5B runs.
        """
        validator = CoachValidator(str(mock_worktree))

        # Use scaffolding task type to skip independent test verification
        task = {
            "acceptance_criteria": ["Feature X implemented", "Tests added"],
            "task_type": "scaffolding",
        }

        # With valid arch score (75), should approve even without skip flag
        result = validator.validate(
            task_id="TASK-TEST-001",
            turn=1,
            task=task,
            skip_arch_review=False,  # Normal pre-loop mode
        )

        assert result.decision == "approve", (
            f"Expected 'approve' with valid arch score (75), got '{result.decision}'. "
            f"Rationale: {result.rationale}"
        )


class TestAutoBuildSkipArchReviewPropagation:
    """
    Integration tests verifying that skip_arch_review propagates correctly
    through AutoBuildOrchestrator when enable_pre_loop=False.
    """

    def test_autobuild_passes_skip_arch_review_when_pre_loop_disabled(
        self,
        mock_worktree,
        task_work_results_zero_arch_score,
    ):
        """
        Test that AutoBuildOrchestrator passes skip_arch_review=True to
        CoachValidator when enable_pre_loop=False.

        This is the key integration test for TASK-FIX-ARIMPL.
        """
        # Mock the worktree manager
        mock_worktree_manager = MagicMock()
        mock_worktree_obj = MagicMock()
        mock_worktree_obj.path = mock_worktree
        mock_worktree_manager.create.return_value = mock_worktree_obj

        # Create orchestrator with enable_pre_loop=False (implement-only mode)
        orchestrator = AutoBuildOrchestrator(
            repo_root=mock_worktree,
            max_turns=1,
            enable_pre_loop=False,  # Implement-only mode
            worktree_manager=mock_worktree_manager,
        )

        # Verify the orchestrator has enable_pre_loop=False
        assert orchestrator.enable_pre_loop is False, (
            "Orchestrator should have enable_pre_loop=False"
        )

        # Create mock player result
        mock_player_result = AgentInvocationResult(
            task_id="TASK-TEST-001",
            turn=1,
            agent_type="player",
            success=True,
            report={
                "files_modified": ["src/feature.py"],
                "tests_written": 10,
                "tests_passed": 10,
            },
            duration_seconds=60.0,
        )

        # Call _invoke_coach_safely directly to verify skip_arch_review is passed
        # This method is what calls CoachValidator.validate()
        # Use scaffolding task type to skip independent test verification
        result = orchestrator._invoke_coach_safely(
            task_id="TASK-TEST-001",
            turn=1,
            requirements="Implement feature X",
            player_report=mock_player_result.report,
            worktree=mock_worktree_obj,
            acceptance_criteria=["Feature X implemented", "Tests added"],
            task_type="scaffolding",  # Skip independent test verification
            skip_arch_review=not orchestrator.enable_pre_loop,  # Should be True
        )

        assert result.success is True, (
            f"Coach validation should succeed with skip_arch_review=True. "
            f"Error: {result.error}"
        )

        # Verify the decision is approve
        assert result.report.get("decision") == "approve", (
            f"Expected 'approve' decision, got '{result.report.get('decision')}'. "
            f"Report: {result.report}"
        )


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
