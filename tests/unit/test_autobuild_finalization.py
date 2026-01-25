"""
Tests for AutoBuild post-loop finalization functions.

This module tests the finalize_autobuild() and generate_summary() functions
which implement minimal post-loop finalization per Option D architecture.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.autobuild import (
    finalize_autobuild,
    generate_summary,
    OrchestrationResult,
    TurnRecord,
    AgentInvocationResult,
)


@pytest.fixture
def mock_worktree(tmp_path):
    """Create mock worktree directory structure."""
    worktree_path = tmp_path / "worktrees" / "TASK-TEST"
    worktree_path.mkdir(parents=True)
    return worktree_path


@pytest.fixture
def mock_loop_result_approved():
    """Create mock OrchestrationResult for approved decision."""
    return OrchestrationResult(
        task_id="TASK-TEST",
        success=True,
        total_turns=2,
        final_decision="approved",
        turn_history=[],
        worktree=MagicMock(path=Path("/tmp/worktree")),
        error=None,
    )


@pytest.fixture
def mock_loop_result_max_turns():
    """Create mock OrchestrationResult for max_turns_exceeded decision."""
    return OrchestrationResult(
        task_id="TASK-TEST",
        success=False,
        total_turns=5,
        final_decision="max_turns_exceeded",
        turn_history=[],
        worktree=MagicMock(path=Path("/tmp/worktree")),
        error="Maximum turns exceeded",
    )


@pytest.fixture
def mock_loop_result_pre_loop_blocked():
    """Create mock OrchestrationResult for pre_loop_blocked decision."""
    return OrchestrationResult(
        task_id="TASK-TEST",
        success=False,
        total_turns=0,
        final_decision="pre_loop_blocked",
        turn_history=[],
        worktree=MagicMock(path=Path("/tmp/worktree")),
        error="Architectural review failed",
    )


@pytest.fixture
def mock_loop_result_error():
    """Create mock OrchestrationResult for error decision."""
    return OrchestrationResult(
        task_id="TASK-TEST",
        success=False,
        total_turns=1,
        final_decision="error",
        turn_history=[],
        worktree=MagicMock(path=Path("/tmp/worktree")),
        error="SDK timeout",
    )


@pytest.fixture
def mock_task_work_results(mock_worktree):
    """Create mock task_work_results.json file."""
    results_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST"
    results_dir.mkdir(parents=True)
    results_file = results_dir / "task_work_results.json"

    results = {
        "files_created": ["src/feature.py", "tests/test_feature.py"],
        "files_modified": ["src/existing.py"],
        "tests_info": {
            "total": 10,
            "passed": 10,
            "failed": 0,
            "all_passed": True,
        },
        "coverage": {
            "line": 85.5,
            "branch": 78.0,
        },
        "architectural_score": 82,
        "plan_audit": {
            "file_variance": 0.05,
            "loc_variance": 0.12,
            "scope_creep_detected": False,
        },
    }

    with open(results_file, "w") as f:
        json.dump(results, f)

    return results_file


class TestGenerateSummary:
    """Tests for generate_summary() function."""

    def test_generate_summary_includes_task_work_results(
        self, mock_worktree, mock_task_work_results, mock_loop_result_approved
    ):
        """Summary includes all fields from task_work_results.json."""
        summary = generate_summary(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert summary["files_created"] == ["src/feature.py", "tests/test_feature.py"]
        assert summary["files_modified"] == ["src/existing.py"]
        assert summary["tests_info"]["all_passed"] is True
        assert summary["coverage"]["line"] == 85.5
        assert summary["architectural_score"] == 82

    def test_generate_summary_includes_plan_audit(
        self, mock_worktree, mock_task_work_results, mock_loop_result_approved
    ):
        """Summary includes plan_audit results from task-work Phase 5.5."""
        summary = generate_summary(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert "plan_audit" in summary
        assert summary["plan_audit"]["scope_creep_detected"] is False
        assert summary["plan_audit"]["file_variance"] == 0.05

    def test_generate_summary_handles_missing_results_file(
        self, mock_worktree, mock_loop_result_approved
    ):
        """Returns minimal summary when task_work_results.json doesn't exist."""
        summary = generate_summary(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert summary["files_created"] == []
        assert summary["files_modified"] == []
        assert summary["tests_info"] == {}
        assert summary["coverage"] == {}
        assert summary["architectural_score"] is None
        assert summary["plan_audit"] == {}

    def test_generate_summary_handles_corrupted_json(
        self, mock_worktree, mock_loop_result_approved
    ):
        """Returns minimal summary when JSON is corrupted."""
        results_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-TEST"
        results_dir.mkdir(parents=True)
        results_file = results_dir / "task_work_results.json"

        with open(results_file, "w") as f:
            f.write("not valid json{{{")

        summary = generate_summary(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert summary["files_created"] == []
        assert summary["architectural_score"] is None


class TestFinalizeAutobuild:
    """Tests for finalize_autobuild() function."""

    def test_finalize_preserves_worktree(
        self, mock_worktree, mock_loop_result_approved
    ):
        """Finalization preserves worktree path in result."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert result["worktree"] == str(mock_worktree)

    def test_finalize_updates_status_approved(
        self, mock_worktree, mock_loop_result_approved
    ):
        """Approved decision maps to in_review status."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert result["status"] == "in_review"

    def test_finalize_updates_status_max_turns(
        self, mock_worktree, mock_loop_result_max_turns
    ):
        """Max turns exceeded decision maps to blocked status."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_max_turns,
        )

        assert result["status"] == "blocked"

    def test_finalize_updates_status_pre_loop_blocked(
        self, mock_worktree, mock_loop_result_pre_loop_blocked
    ):
        """Pre-loop blocked decision maps to blocked status."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_pre_loop_blocked,
        )

        assert result["status"] == "blocked"

    def test_finalize_updates_status_error(
        self, mock_worktree, mock_loop_result_error
    ):
        """Error decision maps to blocked status."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_error,
        )

        assert result["status"] == "blocked"

    def test_finalize_builds_next_steps_approved(
        self, mock_worktree, mock_loop_result_approved
    ):
        """Approved decision includes review and merge instructions."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert len(result["next_steps"]) > 0
        assert any("Review changes" in step for step in result["next_steps"])
        assert any("diff" in step.lower() for step in result["next_steps"])
        assert any("merge" in step.lower() for step in result["next_steps"])

    def test_finalize_builds_next_steps_max_turns(
        self, mock_worktree, mock_loop_result_max_turns
    ):
        """Max turns exceeded includes guidance for manual intervention."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_max_turns,
        )

        assert len(result["next_steps"]) > 0
        assert any("manual" in step.lower() for step in result["next_steps"])

    def test_finalize_builds_next_steps_pre_loop_blocked(
        self, mock_worktree, mock_loop_result_pre_loop_blocked
    ):
        """Pre-loop blocked includes review guidance."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_pre_loop_blocked,
        )

        assert len(result["next_steps"]) > 0
        assert any("pre-loop" in step.lower() for step in result["next_steps"])

    def test_finalize_builds_next_steps_error(
        self, mock_worktree, mock_loop_result_error
    ):
        """Error decision includes debugging guidance."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_error,
        )

        assert len(result["next_steps"]) > 0
        assert any("error" in step.lower() or "fix" in step.lower() for step in result["next_steps"])

    def test_finalize_includes_summary(
        self, mock_worktree, mock_task_work_results, mock_loop_result_approved
    ):
        """Finalization result includes summary from generate_summary()."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        assert "summary" in result
        assert result["summary"]["files_created"] == ["src/feature.py", "tests/test_feature.py"]
        assert result["summary"]["architectural_score"] == 82


class TestIntegration:
    """Integration tests for finalization workflow."""

    def test_full_finalization_workflow_approved(
        self, mock_worktree, mock_task_work_results, mock_loop_result_approved
    ):
        """Full workflow produces correct result for approved decision."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_approved,
        )

        # Status
        assert result["status"] == "in_review"

        # Worktree preserved
        assert result["worktree"] == str(mock_worktree)

        # Next steps
        assert len(result["next_steps"]) >= 3

        # Summary includes task-work results
        assert result["summary"]["files_created"] == ["src/feature.py", "tests/test_feature.py"]
        assert result["summary"]["tests_info"]["all_passed"] is True
        assert result["summary"]["plan_audit"]["scope_creep_detected"] is False

    def test_full_finalization_workflow_blocked(
        self, mock_worktree, mock_loop_result_max_turns
    ):
        """Full workflow produces correct result for blocked decision."""
        result = finalize_autobuild(
            "TASK-TEST",
            mock_worktree,
            mock_loop_result_max_turns,
        )

        # Status
        assert result["status"] == "blocked"

        # Worktree still preserved for inspection
        assert result["worktree"] == str(mock_worktree)

        # Next steps provided
        assert len(result["next_steps"]) > 0
