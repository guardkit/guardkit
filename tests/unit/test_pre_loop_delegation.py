"""
Unit tests for pre-loop quality gates delegation to task-work.

Tests cover:
    - PreLoopQualityGates: Pre-loop execution and max_turns determination
    - TaskWorkInterface: Task-work invocation and result parsing
    - Exception handling: QualityGateBlocked, CheckpointRejectedError

Test Organization:
    - TestPreLoopQualityGates: Main pre-loop execution tests
    - TestTaskWorkInterface: Task-work delegation tests
    - TestComplexityToMaxTurns: Complexity-based max_turns mapping
    - TestExceptionHandling: Quality gate exception scenarios
"""

import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from dataclasses import dataclass

import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates import (
    PreLoopQualityGates,
    TaskWorkInterface,
    QualityGateError,
    QualityGateBlocked,
    DesignPhaseError,
    CheckpointRejectedError,
)
from guardkit.orchestrator.quality_gates.pre_loop import PreLoopResult
from guardkit.orchestrator.quality_gates.task_work_interface import DesignPhaseResult


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_task_work_interface():
    """Create mock TaskWorkInterface.

    Note: We use MagicMock with AsyncMock for execute_design_phase since
    that method is now async. The execute_design_phase returns an awaitable.
    """
    interface = MagicMock()
    # Make execute_design_phase an AsyncMock since it's now async
    interface.execute_design_phase = AsyncMock()
    return interface


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def mock_plan_file(tmp_worktree):
    """Create an actual plan file for tests that need file existence validation."""
    plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
    plan_dir.mkdir(parents=True)
    plan_path = plan_dir / "implementation_plan.md"
    plan_path.write_text("# Implementation Plan\n\n## Steps\n- Step 1\n- Step 2\n- Step 3")
    return str(plan_path)


@pytest.fixture
def mock_design_result(mock_plan_file):
    """Create a standard mock DesignPhaseResult with existing plan file."""
    return DesignPhaseResult(
        implementation_plan={"steps": ["Step 1", "Step 2", "Step 3"]},
        plan_path=mock_plan_file,  # Uses actual file path
        complexity={"score": 5, "factors": ["files", "patterns"]},
        checkpoint_result="approved",
        architectural_review={"score": 85, "solid": 80, "dry": 90, "yagni": 85},
        clarifications={"scope": "standard", "testing": "integration"},
    )


def make_design_result(
    complexity_score: int = 5,
    checkpoint_result: str = "approved",
    arch_score: int = 85,
    plan: Optional[Dict[str, Any]] = None,
    plan_path: Optional[str] = None,
) -> DesignPhaseResult:
    """Helper to create DesignPhaseResult with customizable values.

    Note: Tests using this helper need to provide a real plan_path if
    testing the full execute() flow, as plan validation now checks
    file existence. Use mock_plan_file fixture for this.
    """
    return DesignPhaseResult(
        implementation_plan=plan or {"steps": ["Step 1"]},
        plan_path=plan_path,  # Default to None, tests must provide valid path
        complexity={"score": complexity_score},
        checkpoint_result=checkpoint_result,
        architectural_review={"score": arch_score},
        clarifications={},
    )


# ============================================================================
# Test PreLoopQualityGates
# ============================================================================


class TestPreLoopQualityGates:
    """Test PreLoopQualityGates execution."""

    def test_execute_delegates_to_task_work(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test execute() delegates to TaskWorkInterface.execute_design_phase()."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {"no_questions": True}))

        # Verify delegation - execute adds skip_arch_review to options
        mock_task_work_interface.execute_design_phase.assert_called_once_with(
            "TASK-001",
            {"no_questions": True, "skip_arch_review": False},
        )

        # Verify result type
        assert isinstance(result, PreLoopResult)

    def test_passes_no_questions_flag(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test no_questions flag is passed through to task-work."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        asyncio.run(gates.execute("TASK-001", {"no_questions": True}))

        # Verify no_questions passed
        call_args = mock_task_work_interface.execute_design_phase.call_args
        assert call_args[0][1].get("no_questions") is True

    def test_passes_with_questions_flag(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test with_questions flag is passed through to task-work."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        asyncio.run(gates.execute("TASK-001", {"with_questions": True}))

        # Verify with_questions passed
        call_args = mock_task_work_interface.execute_design_phase.call_args
        assert call_args[0][1].get("with_questions") is True

    def test_passes_answers_flag(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test answers flag is passed through to task-work."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        asyncio.run(gates.execute("TASK-001", {"answers": "1:Y 2:N 3:JWT"}))

        # Verify answers passed
        call_args = mock_task_work_interface.execute_design_phase.call_args
        assert call_args[0][1].get("answers") == "1:Y 2:N 3:JWT"

    def test_passes_docs_flag(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test docs flag is passed through to task-work."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        asyncio.run(gates.execute("TASK-001", {"docs": "minimal"}))

        # Verify docs passed
        call_args = mock_task_work_interface.execute_design_phase.call_args
        assert call_args[0][1].get("docs") == "minimal"

    def test_passes_defaults_flag(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test defaults flag is passed through to task-work."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        asyncio.run(gates.execute("TASK-001", {"defaults": True}))

        # Verify defaults passed
        call_args = mock_task_work_interface.execute_design_phase.call_args
        assert call_args[0][1].get("defaults") is True

    def test_extracts_plan_for_player(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test implementation plan is extracted for Player agent."""
        plan = {"steps": ["Step 1", "Step 2", "Step 3"]}
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            plan=plan,
            plan_path=mock_plan_file,
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify plan extracted
        assert result.plan == plan
        assert result.plan_path == mock_plan_file

    def test_extracts_complexity_score(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test complexity score is extracted from result."""
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            complexity_score=7,
            plan_path=mock_plan_file,
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        assert result.complexity == 7

    def test_extracts_architectural_score(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test architectural review score is extracted."""
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            arch_score=92,
            plan_path=mock_plan_file,
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        assert result.architectural_score == 92

    def test_checkpoint_passed_on_approved(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test checkpoint_passed is True when checkpoint approves."""
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            checkpoint_result="approved",
            plan_path=mock_plan_file,
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        assert result.checkpoint_passed is True

    def test_checkpoint_passed_on_skipped(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test checkpoint_passed is True when checkpoint skipped (low complexity)."""
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            checkpoint_result="skipped",
            plan_path=mock_plan_file,
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        assert result.checkpoint_passed is True

    def test_checkpoint_rejection_blocks_loop(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test CheckpointRejectedError is raised when checkpoint rejects."""
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            checkpoint_result="rejected",
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(CheckpointRejectedError):
            asyncio.run(gates.execute("TASK-001", {}))

    def test_validate_prerequisites_with_valid_worktree(self, tmp_worktree):
        """Test validate_prerequisites returns True for valid worktree."""
        gates = PreLoopQualityGates(worktree_path=str(tmp_worktree))

        assert gates.validate_prerequisites("TASK-001") is True

    def test_validate_prerequisites_with_invalid_worktree(self, tmp_path):
        """Test validate_prerequisites returns False for invalid worktree."""
        gates = PreLoopQualityGates(worktree_path=str(tmp_path / "nonexistent"))

        assert gates.validate_prerequisites("TASK-001") is False

    def test_supported_options_returns_dict(self, tmp_worktree):
        """Test supported_options returns option descriptions."""
        gates = PreLoopQualityGates(worktree_path=str(tmp_worktree))

        options = gates.supported_options

        assert isinstance(options, dict)
        assert "no_questions" in options
        assert "with_questions" in options
        assert "answers" in options
        assert "defaults" in options
        assert "docs" in options


# ============================================================================
# Test Complexity-to-MaxTurns Mapping
# ============================================================================


# ============================================================================
# Test Plan Validation (TASK-FB-FIX-002)
# ============================================================================


class TestPlanValidation:
    """Test plan existence validation in pre-loop."""

    def test_raises_when_plan_path_is_none(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test QualityGateBlocked raised when plan_path is None."""
        result = DesignPhaseResult(
            implementation_plan={"steps": ["Step 1"]},
            plan_path=None,  # No plan path
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 85},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(QualityGateBlocked) as exc_info:
            asyncio.run(gates.execute("TASK-001", {}))

        assert exc_info.value.gate_name == "plan_generation"
        assert "TASK-001" in exc_info.value.reason
        assert "did not return plan path" in exc_info.value.reason
        assert exc_info.value.details["plan_path"] is None

    def test_raises_when_plan_file_missing(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test QualityGateBlocked raised when plan file doesn't exist."""
        # Use a path that doesn't exist
        nonexistent_path = str(tmp_worktree / "nonexistent" / "plan.md")
        result = DesignPhaseResult(
            implementation_plan={"steps": ["Step 1"]},
            plan_path=nonexistent_path,
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 85},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(QualityGateBlocked) as exc_info:
            asyncio.run(gates.execute("TASK-001", {}))

        assert exc_info.value.gate_name == "plan_validation"
        assert "TASK-001" in exc_info.value.reason
        assert "not found at" in exc_info.value.reason
        assert exc_info.value.details["plan_path"] == nonexistent_path

    def test_error_message_suggests_manual_debug(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test error message includes actionable suggestion to run task-work manually."""
        result = DesignPhaseResult(
            implementation_plan={"steps": ["Step 1"]},
            plan_path=None,
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 85},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(QualityGateBlocked) as exc_info:
            asyncio.run(gates.execute("TASK-001", {}))

        # Check that error message suggests running task-work manually
        assert "--design-only" in exc_info.value.reason
        assert "manually" in exc_info.value.reason.lower()

    def test_success_when_plan_file_exists(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test successful execution when plan file exists."""
        # Create a plan file that exists
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        plan_path = plan_dir / "implementation_plan.md"
        plan_path.write_text("# Implementation Plan\n\n## Steps\n- Step 1")

        result = DesignPhaseResult(
            implementation_plan={"steps": ["Step 1"]},
            plan_path=str(plan_path),
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 85},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        # Should not raise
        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify result is correct
        assert pre_loop_result.plan_path == str(plan_path)
        assert pre_loop_result.complexity == 5
        assert pre_loop_result.checkpoint_passed is True

    def test_validation_checks_path_before_existence(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test that None plan_path is caught before file existence check."""
        result = DesignPhaseResult(
            implementation_plan={"steps": ["Step 1"]},
            plan_path=None,
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 85},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(QualityGateBlocked) as exc_info:
            asyncio.run(gates.execute("TASK-001", {}))

        # Should be plan_generation error, not plan_validation
        assert exc_info.value.gate_name == "plan_generation"

    def test_empty_string_plan_path_treated_as_missing(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test that empty string plan_path is treated as missing."""
        result = DesignPhaseResult(
            implementation_plan={"steps": ["Step 1"]},
            plan_path="",  # Empty string
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 85},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(QualityGateBlocked) as exc_info:
            asyncio.run(gates.execute("TASK-001", {}))

        # Empty string is falsy, should be caught as plan_generation error
        assert exc_info.value.gate_name == "plan_generation"


# ============================================================================
# Test Relative Path Resolution (TASK-FB-FIX-007)
# ============================================================================


class TestRelativePathResolution:
    """Test that relative plan paths are resolved against worktree."""

    def test_resolves_relative_path_against_worktree(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Verify relative plan paths are resolved against worktree directory."""
        # Create plan in worktree with relative path structure
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.md"
        plan_file.write_text("# Test Plan\n\nTest content that meets minimum length.")

        # Create mock result with RELATIVE path (as SDK returns)
        result = DesignPhaseResult(
            implementation_plan={"content": "test"},
            plan_path="docs/state/TASK-001/implementation_plan.md",  # Relative!
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify path was resolved to absolute
        assert Path(pre_loop_result.plan_path).is_absolute()
        assert Path(pre_loop_result.plan_path).exists()
        assert str(tmp_worktree) in pre_loop_result.plan_path

    def test_absolute_path_unchanged(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Verify absolute plan paths are left unchanged."""
        # Create plan in worktree
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.md"
        plan_file.write_text("# Test Plan\n\nTest content that meets minimum length.")

        # Create mock result with ABSOLUTE path
        result = DesignPhaseResult(
            implementation_plan={"content": "test"},
            plan_path=str(plan_file),  # Absolute!
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify path remains the same
        assert pre_loop_result.plan_path == str(plan_file)

    def test_fallback_search_when_resolved_path_not_found(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Verify fallback search when SDK path resolves to nonexistent file."""
        # Create plan in a DIFFERENT location than SDK reports
        # SDK reports docs/state path but plan is in .claude/task-plans
        plan_dir = tmp_worktree / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "TASK-001-implementation-plan.md"
        plan_file.write_text("# Test Plan\n\nTest content that meets minimum length.")

        # SDK returns a relative path that won't exist after resolution
        result = DesignPhaseResult(
            implementation_plan={"content": "test"},
            plan_path="docs/state/TASK-001/implementation_plan.md",  # Won't exist
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify fallback found the plan in .claude/task-plans
        assert Path(pre_loop_result.plan_path).exists()
        assert ".claude/task-plans" in pre_loop_result.plan_path

    def test_fallback_search_when_sdk_returns_none(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Verify fallback search when SDK returns None for plan path."""
        # Create plan that fallback should find
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.md"
        plan_file.write_text("# Test Plan\n\nTest content that meets minimum length.")

        # SDK returns None for plan path
        result = DesignPhaseResult(
            implementation_plan={"content": "test"},
            plan_path=None,  # No path returned!
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify fallback found the plan
        assert Path(pre_loop_result.plan_path).exists()
        assert str(tmp_worktree) in pre_loop_result.plan_path

    def test_raises_when_no_plan_found_anywhere(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Verify error when no plan found in SDK path or fallback locations."""
        # SDK returns a path but no plan exists anywhere
        result = DesignPhaseResult(
            implementation_plan={"content": "test"},
            plan_path="docs/state/TASK-001/implementation_plan.md",
            complexity={"score": 5},
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        with pytest.raises(QualityGateBlocked) as exc_info:
            asyncio.run(gates.execute("TASK-001", {}))

        # Should fail with plan_validation (path exists but file doesn't)
        assert exc_info.value.gate_name == "plan_validation"


class TestComplexityToMaxTurns:
    """Test complexity score to max_turns mapping."""

    @pytest.mark.parametrize(
        "complexity,expected_turns",
        [
            (1, 3),  # Simple: 1-3 → 3 turns
            (2, 3),
            (3, 3),
            (4, 5),  # Medium: 4-6 → 5 turns
            (5, 5),
            (6, 5),
            (7, 7),  # Complex: 7-10 → 7 turns
            (8, 7),
            (9, 7),
            (10, 7),
        ],
    )
    def test_determines_max_turns_from_complexity(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
        complexity,
        expected_turns,
    ):
        """Test max_turns is correctly determined from complexity score."""
        mock_task_work_interface.execute_design_phase.return_value = make_design_result(
            complexity_score=complexity,
            plan_path=mock_plan_file,
        )

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        assert result.max_turns == expected_turns

    def test_unexpected_complexity_defaults_to_5(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test unexpected complexity values default to 5 turns."""
        # Create a mock result with out-of-range complexity
        result = DesignPhaseResult(
            implementation_plan={},
            plan_path=mock_plan_file,
            complexity={"score": 15},  # Out of expected range
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        assert pre_loop_result.max_turns == 5

    def test_missing_complexity_defaults_to_5_turns(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_plan_file,
    ):
        """Test missing complexity score defaults to 5 turns."""
        result = DesignPhaseResult(
            implementation_plan={},
            plan_path=mock_plan_file,
            complexity={},  # No score
            checkpoint_result="approved",
            architectural_review={"score": 80},
            clarifications={},
        )
        mock_task_work_interface.execute_design_phase.return_value = result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        pre_loop_result = asyncio.run(gates.execute("TASK-001", {}))

        assert pre_loop_result.max_turns == 5


# ============================================================================
# Test TaskWorkInterface
# ============================================================================


class TestTaskWorkInterface:
    """Test TaskWorkInterface delegation."""

    def test_build_task_work_args_basic(self, tmp_worktree):
        """Test basic command args with task_id and --design-only."""
        interface = TaskWorkInterface(tmp_worktree)

        args = interface._build_task_work_args("TASK-001", {})

        assert "TASK-001" in args
        assert "--design-only" in args

    def test_build_task_work_args_with_no_questions(self, tmp_worktree):
        """Test --no-questions flag is added."""
        interface = TaskWorkInterface(tmp_worktree)

        args = interface._build_task_work_args(
            "TASK-001",
            {"no_questions": True},
        )

        assert "--no-questions" in args

    def test_build_task_work_args_with_questions(self, tmp_worktree):
        """Test --with-questions flag is added."""
        interface = TaskWorkInterface(tmp_worktree)

        args = interface._build_task_work_args(
            "TASK-001",
            {"with_questions": True},
        )

        assert "--with-questions" in args

    def test_build_task_work_args_with_answers(self, tmp_worktree):
        """Test --answers flag is added with value."""
        interface = TaskWorkInterface(tmp_worktree)

        args = interface._build_task_work_args(
            "TASK-001",
            {"answers": "1:Y 2:N"},
        )

        assert "--answers" in args
        assert "1:Y 2:N" in args

    def test_build_task_work_args_with_docs(self, tmp_worktree):
        """Test --docs flag is added."""
        interface = TaskWorkInterface(tmp_worktree)

        args = interface._build_task_work_args(
            "TASK-001",
            {"docs": "comprehensive"},
        )

        assert "--docs=comprehensive" in args

    def test_build_task_work_args_with_defaults(self, tmp_worktree):
        """Test --defaults flag is added."""
        interface = TaskWorkInterface(tmp_worktree)

        args = interface._build_task_work_args(
            "TASK-001",
            {"defaults": True},
        )

        assert "--defaults" in args

    def test_parse_design_result_extracts_all_fields(self, tmp_worktree):
        """Test _parse_design_result extracts all expected fields."""
        interface = TaskWorkInterface(tmp_worktree)

        raw_result = {
            "implementation_plan": {"steps": ["Step 1"]},
            "plan_path": "/path/to/plan.md",
            "complexity": {"score": 6},
            "checkpoint_result": "approved",
            "architectural_review": {"score": 88},
            "clarifications": {"q1": "answer1"},
        }

        result = interface._parse_design_result(raw_result)

        assert result.implementation_plan == {"steps": ["Step 1"]}
        assert result.plan_path == "/path/to/plan.md"
        assert result.complexity == {"score": 6}
        assert result.checkpoint_result == "approved"
        assert result.architectural_review == {"score": 88}
        assert result.clarifications == {"q1": "answer1"}

    def test_parse_design_result_provides_defaults(self, tmp_worktree):
        """Test _parse_design_result provides sensible defaults."""
        interface = TaskWorkInterface(tmp_worktree)

        raw_result = {}  # Empty result

        result = interface._parse_design_result(raw_result)

        assert result.implementation_plan == {}
        assert result.complexity == {"score": 5}
        assert result.checkpoint_result == "approved"

    def test_parse_design_result_blocks_low_arch_score(self, tmp_worktree):
        """Test QualityGateBlocked raised for low architectural score."""
        interface = TaskWorkInterface(tmp_worktree)

        raw_result = {
            "architectural_review": {"score": 45},  # Below threshold of 60
        }

        with pytest.raises(QualityGateBlocked) as exc_info:
            interface._parse_design_result(raw_result)

        assert "architectural_review" in exc_info.value.gate_name
        assert exc_info.value.details["score"] == 45

    @pytest.mark.parametrize("score", [60, 70, 80, 100])
    def test_parse_design_result_passes_acceptable_arch_scores(
        self,
        tmp_worktree,
        score,
    ):
        """Test acceptable architectural scores (>=60) pass validation."""
        interface = TaskWorkInterface(tmp_worktree)

        raw_result = {
            "architectural_review": {"score": score},
        }

        # Should not raise
        result = interface._parse_design_result(raw_result)
        assert result.architectural_review["score"] == score


# ============================================================================
# Test Exception Handling
# ============================================================================


class TestExceptionHandling:
    """Test quality gate exception scenarios."""

    def test_quality_gate_error_base_exception(self):
        """Test QualityGateError is the base exception."""
        error = QualityGateError("Test error")
        assert str(error) == "Test error"

    def test_quality_gate_blocked_attributes(self):
        """Test QualityGateBlocked has required attributes."""
        error = QualityGateBlocked(
            reason="Score too low",
            gate_name="architectural_review",
            details={"score": 45},
        )

        assert error.reason == "Score too low"
        assert error.gate_name == "architectural_review"
        assert error.details == {"score": 45}
        assert "architectural_review" in str(error)
        assert "Score too low" in str(error)

    def test_design_phase_error_attributes(self):
        """Test DesignPhaseError has required attributes."""
        error = DesignPhaseError(
            phase="2.7",
            error="Complexity evaluation failed",
        )

        assert error.phase == "2.7"
        assert error.error == "Complexity evaluation failed"
        assert "2.7" in str(error)
        assert "Complexity evaluation failed" in str(error)

    def test_checkpoint_rejected_error_attributes(self):
        """Test CheckpointRejectedError has required attributes."""
        error = CheckpointRejectedError(
            reason="Plan too complex - split into smaller tasks",
        )

        assert error.reason == "Plan too complex - split into smaller tasks"
        assert "Plan too complex" in str(error)

    def test_checkpoint_rejected_error_default_reason(self):
        """Test CheckpointRejectedError has default reason."""
        error = CheckpointRejectedError()

        assert "rejected" in error.reason.lower()

    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy."""
        assert issubclass(QualityGateBlocked, QualityGateError)
        assert issubclass(DesignPhaseError, QualityGateError)
        assert issubclass(CheckpointRejectedError, QualityGateError)


# ============================================================================
# Test PreLoopResult Dataclass
# ============================================================================


class TestPreLoopResult:
    """Test PreLoopResult dataclass."""

    def test_preloop_result_required_fields(self):
        """Test PreLoopResult has required fields."""
        result = PreLoopResult(
            plan={"steps": ["Step 1"]},
            plan_path="/path/to/plan.md",
            complexity=5,
            max_turns=5,
            checkpoint_passed=True,
        )

        assert result.plan == {"steps": ["Step 1"]}
        assert result.plan_path == "/path/to/plan.md"
        assert result.complexity == 5
        assert result.max_turns == 5
        assert result.checkpoint_passed is True

    def test_preloop_result_optional_fields_defaults(self):
        """Test PreLoopResult optional fields have defaults."""
        result = PreLoopResult(
            plan={},
            plan_path=None,
            complexity=3,
            max_turns=3,
            checkpoint_passed=True,
        )

        assert result.architectural_score is None
        assert result.clarifications == {}

    def test_preloop_result_all_fields(self):
        """Test PreLoopResult with all fields populated."""
        result = PreLoopResult(
            plan={"steps": ["Step 1", "Step 2"]},
            plan_path="/path/to/plan.md",
            complexity=7,
            max_turns=7,
            checkpoint_passed=True,
            architectural_score=92,
            clarifications={"scope": "standard"},
        )

        assert result.architectural_score == 92
        assert result.clarifications == {"scope": "standard"}


# ============================================================================
# Test SDK Timeout Propagation (TASK-FB-FIX-009)
# ============================================================================


class TestSdkTimeoutPropagation:
    """Test sdk_timeout propagation through PreLoopQualityGates."""

    def test_default_sdk_timeout_is_900(self, tmp_worktree):
        """Test default sdk_timeout is 1200 seconds (updated default)."""
        gates = PreLoopQualityGates(worktree_path=str(tmp_worktree))

        assert gates.sdk_timeout == 1200

    def test_custom_sdk_timeout_stored(self, tmp_worktree):
        """Test custom sdk_timeout is stored in instance."""
        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            sdk_timeout=1800,
        )

        assert gates.sdk_timeout == 1800

    def test_sdk_timeout_passed_to_task_work_interface(self, tmp_worktree):
        """Test sdk_timeout is passed to TaskWorkInterface when created internally."""
        with patch(
            "guardkit.orchestrator.quality_gates.pre_loop.TaskWorkInterface"
        ) as mock_interface_cls:
            mock_interface = MagicMock()
            mock_interface_cls.return_value = mock_interface

            PreLoopQualityGates(
                worktree_path=str(tmp_worktree),
                sdk_timeout=1200,
            )

            # Verify TaskWorkInterface was created with sdk_timeout_seconds
            mock_interface_cls.assert_called_once_with(
                Path(tmp_worktree),
                sdk_timeout_seconds=1200,
            )

    def test_injected_interface_bypasses_sdk_timeout(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test injected interface is used directly (sdk_timeout not used)."""
        # When interface is injected, sdk_timeout is stored but not used
        # for creating a new interface
        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
            sdk_timeout=900,
        )

        # The injected interface is used, sdk_timeout is still stored
        assert gates.sdk_timeout == 900
        assert gates._interface is mock_task_work_interface

    def test_sdk_timeout_min_value(self, tmp_worktree):
        """Test sdk_timeout can be set to minimum valid value."""
        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            sdk_timeout=60,  # Minimum valid timeout
        )

        assert gates.sdk_timeout == 60

    def test_sdk_timeout_max_value(self, tmp_worktree):
        """Test sdk_timeout can be set to maximum valid value."""
        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            sdk_timeout=3600,  # Maximum valid timeout
        )

        assert gates.sdk_timeout == 3600


# ============================================================================
# Test Integration with AutoBuild Orchestrator
# ============================================================================


class TestOrchestratorIntegration:
    """Test pre-loop gates integration with AutoBuild orchestrator."""

    def test_gates_can_be_injected_into_orchestrator(
        self,
        tmp_worktree,
        mock_task_work_interface,
    ):
        """Test PreLoopQualityGates can be dependency-injected."""
        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        # Verify gates has expected interface
        assert hasattr(gates, "execute")
        assert hasattr(gates, "validate_prerequisites")
        assert hasattr(gates, "supported_options")

    def test_gates_execute_returns_expected_type(
        self,
        tmp_worktree,
        mock_task_work_interface,
        mock_design_result,
    ):
        """Test execute returns PreLoopResult for orchestrator consumption."""
        mock_task_work_interface.execute_design_phase.return_value = mock_design_result

        gates = PreLoopQualityGates(
            worktree_path=str(tmp_worktree),
            interface=mock_task_work_interface,
        )

        result = asyncio.run(gates.execute("TASK-001", {}))

        # Verify orchestrator can use result
        assert isinstance(result, PreLoopResult)
        assert hasattr(result, "plan")
        assert hasattr(result, "max_turns")
        assert hasattr(result, "complexity")
        assert hasattr(result, "checkpoint_passed")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
