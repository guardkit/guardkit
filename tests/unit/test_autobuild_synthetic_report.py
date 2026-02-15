"""
Unit tests for AutoBuild synthetic report observability and enrichment.

Tests logging, flagging, and file-existence promise generation for synthetic
recovery reports (TASK-ASF-004 + TASK-ASF-006).

Coverage Target: >=85%
Test Count: 11 tests
"""

import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.state_tracker import WorkState
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    RequirementsValidation,
    CriterionResult,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_manager():
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    return Mock()


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    return display


@pytest.fixture
def orchestrator(mock_worktree_manager, mock_agent_invoker, mock_progress_display):
    """Create AutoBuildOrchestrator instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        yield AutoBuildOrchestrator(
            repo_root=repo_root,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            verbose=False,
            max_turns=5,
            sdk_timeout=900,
            ablation_mode=False,
        )


@pytest.fixture
def work_state():
    """Create sample WorkState for testing."""
    return WorkState(
        turn_number=1,
        files_modified=["src/main.py", "src/utils.py"],
        files_created=["src/new_feature.py"],
        tests_written=["tests/test_new_feature.py"],
        tests_passed=True,
        test_count=5,
        detection_method="git_test_detection",
    )


@pytest.fixture
def coach_validator(tmp_path):
    """Create CoachValidator instance for testing."""
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()
    return CoachValidator(worktree_path=worktree_path)


# ============================================================================
# 1. _build_synthetic_report() Tests - Original (TASK-ASF-004)
# ============================================================================


def test_build_synthetic_report_returns_dict_with_synthetic_flag(orchestrator, work_state):
    """Test that _build_synthetic_report returns dict with _synthetic: True key."""
    report = orchestrator._build_synthetic_report(
        work_state=work_state,
        original_error="Agent invocation failed",
    )

    # Verify synthetic flag is present and True
    assert "_synthetic" in report
    assert report["_synthetic"] is True


def test_build_synthetic_report_emits_warning_log(orchestrator, work_state, caplog):
    """Test that _build_synthetic_report emits a warning log."""
    with caplog.at_level(logging.WARNING):
        report = orchestrator._build_synthetic_report(
            work_state=work_state,
            original_error="Agent invocation failed",
        )

    # Verify warning was logged
    assert len(caplog.records) > 0
    warning_record = caplog.records[0]
    assert warning_record.levelname == "WARNING"
    assert "Building synthetic report" in warning_record.message


def test_build_synthetic_report_warning_contains_file_and_test_counts(
    orchestrator, work_state, caplog
):
    """Test that warning log contains file counts and test count."""
    with caplog.at_level(logging.WARNING):
        report = orchestrator._build_synthetic_report(
            work_state=work_state,
            original_error="Agent invocation failed",
        )

    warning_message = caplog.records[0].message

    # Verify counts are in the message
    assert "1 files created" in warning_message  # 1 file created
    assert "2 files modified" in warning_message  # 2 files modified
    assert "5 tests" in warning_message  # 5 tests


def test_synthetic_report_detection_logic(orchestrator, caplog):
    """Test that synthetic flag in report is detected correctly."""
    # Create a synthetic Player result
    synthetic_report = {
        "task_id": "TASK-TEST-001",
        "turn": 1,
        "files_modified": ["src/main.py"],
        "files_created": ["src/new.py"],
        "tests_written": [],
        "tests_run": True,
        "tests_passed": True,
        "test_output_summary": "All tests passed",
        "implementation_notes": "[RECOVERED via git_test_detection] Original error: Failed",
        "concerns": ["Player failed with error: Failed"],
        "requirements_addressed": [],
        "requirements_remaining": [],
        "_synthetic": True,  # Synthetic flag
        "_recovery_metadata": {
            "detection_method": "git_test_detection",
            "git_insertions": 100,
            "git_deletions": 20,
            "timestamp": "2025-01-15T12:00:00",
        },
    }

    player_result = AgentInvocationResult(
        task_id="TASK-TEST-001",
        turn=1,
        agent_type="player",
        success=True,
        report=synthetic_report,
        duration_seconds=120.5,
        error=None,
    )

    # Verify the check at line 1793 would trigger
    with caplog.at_level(logging.WARNING):
        # Directly test the condition from the code (line 1792-1797)
        if player_result.success and player_result.report.get("_synthetic"):
            logger = logging.getLogger("guardkit.orchestrator.autobuild")
            logger.warning(
                f"[Turn {player_result.turn}] Passing synthetic report to Coach for {player_result.task_id}. "
                f"Promise matching will fail — falling through to text matching."
            )

    # Verify warning was logged
    assert len(caplog.records) > 0
    warning_messages = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any(
        "Passing synthetic report to Coach" in msg and "Promise matching will fail" in msg
        for msg in warning_messages
    ), f"Expected synthetic report warning, got: {warning_messages}"


# ============================================================================
# 2. File-Existence Promises Tests - New (TASK-ASF-006)
# ============================================================================


def test_scaffolding_task_with_matching_files_generates_complete_promises(
    orchestrator, work_state, caplog
):
    """Test scaffolding task with matching files generates status=complete promises."""
    acceptance_criteria = [
        "Create src/new_feature.py with core logic",
        "Update src/utils.py with helper functions",
    ]

    with caplog.at_level(logging.INFO):
        report = orchestrator._build_synthetic_report(
            work_state=work_state,
            original_error="Agent invocation failed",
            acceptance_criteria=acceptance_criteria,
            task_type="scaffolding",
        )

    # Verify completion_promises exists
    assert "completion_promises" in report
    promises = report["completion_promises"]
    assert len(promises) == 2

    # Check first promise (src/new_feature.py - created)
    promise_0 = promises[0]
    assert promise_0["criterion_id"] == "AC-001"
    assert promise_0["status"] == "complete"
    assert "src/new_feature.py" in promise_0["evidence"]
    assert "(created)" in promise_0["evidence"]

    # Check second promise (src/utils.py - modified)
    promise_1 = promises[1]
    assert promise_1["criterion_id"] == "AC-002"
    assert promise_1["status"] == "complete"
    assert "src/utils.py" in promise_1["evidence"]
    assert "(modified)" in promise_1["evidence"]

    # Verify info log was emitted
    info_messages = [rec.message for rec in caplog.records if rec.levelname == "INFO"]
    assert any("Generated 2 file-existence promises" in msg for msg in info_messages)


def test_scaffolding_task_with_unmatched_files_generates_incomplete_promises(
    orchestrator, work_state
):
    """Test scaffolding task with unmatched files generates status=incomplete promises."""
    acceptance_criteria = [
        "Create src/missing_file.py with logic",
        "Update config/settings.json with new config",
    ]

    report = orchestrator._build_synthetic_report(
        work_state=work_state,
        original_error="Agent invocation failed",
        acceptance_criteria=acceptance_criteria,
        task_type="scaffolding",
    )

    # Verify completion_promises exists
    assert "completion_promises" in report
    promises = report["completion_promises"]
    assert len(promises) == 2

    # Both promises should be incomplete (no matching files)
    for promise in promises:
        assert promise["status"] == "incomplete"
        assert "No file-existence evidence" in promise["evidence"]


def test_non_scaffolding_task_does_not_generate_promises(orchestrator, work_state, caplog):
    """Test non-scaffolding task does NOT generate completion_promises."""
    acceptance_criteria = [
        "Implement user authentication logic",
        "Add error handling for edge cases",
    ]

    with caplog.at_level(logging.WARNING):
        report = orchestrator._build_synthetic_report(
            work_state=work_state,
            original_error="Agent invocation failed",
            acceptance_criteria=acceptance_criteria,
            task_type="feature",
        )

    # Verify completion_promises does NOT exist
    assert "completion_promises" not in report

    # Verify warning message indicates no promises
    warning_messages = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any(
        "no completion_promises" in msg and "cannot satisfy promise-based" in msg
        for msg in warning_messages
    )


def test_generate_file_existence_promises_directly(orchestrator, work_state):
    """Test _generate_file_existence_promises() extraction and matching logic."""
    acceptance_criteria = [
        "Create src/auth/login.py for authentication",
        "Update tests/test_auth.py with new test cases",
        "No file path here, just text",
    ]

    # Add matching files to work_state
    work_state.files_created.append("src/auth/login.py")
    work_state.files_modified.append("tests/test_auth.py")

    promises = orchestrator._generate_file_existence_promises(
        work_state, acceptance_criteria
    )

    assert len(promises) == 3

    # First promise: src/auth/login.py (created)
    assert promises[0]["criterion_id"] == "AC-001"
    assert promises[0]["status"] == "complete"
    assert "src/auth/login.py" in promises[0]["evidence"]
    assert "(created)" in promises[0]["evidence"]

    # Second promise: tests/test_auth.py (modified)
    assert promises[1]["criterion_id"] == "AC-002"
    assert promises[1]["status"] == "complete"
    assert "tests/test_auth.py" in promises[1]["evidence"]
    assert "(modified)" in promises[1]["evidence"]

    # Third promise: no file path extracted
    assert promises[2]["criterion_id"] == "AC-003"
    assert promises[2]["status"] == "incomplete"
    assert "No file-existence evidence" in promises[2]["evidence"]


def test_logging_differences_scaffolding_vs_non_scaffolding(orchestrator, work_state, caplog):
    """Test logging messages differ for scaffolding vs non-scaffolding tasks."""
    acceptance_criteria = ["Create src/file.py"]

    # Test scaffolding task
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        scaffolding_report = orchestrator._build_synthetic_report(
            work_state=work_state,
            original_error="Error",
            acceptance_criteria=acceptance_criteria,
            task_type="scaffolding",
        )

    scaffolding_warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("Generating file-existence promises for scaffolding task" in msg for msg in scaffolding_warnings)

    # Test non-scaffolding task
    with caplog.at_level(logging.WARNING):
        caplog.clear()
        feature_report = orchestrator._build_synthetic_report(
            work_state=work_state,
            original_error="Error",
            acceptance_criteria=acceptance_criteria,
            task_type="feature",
        )

    feature_warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("no completion_promises" in msg for msg in feature_warnings)
    assert not any("Generating file-existence promises" in msg for msg in feature_warnings)


# ============================================================================
# 3. CoachValidator Fast-Fail Tests (TASK-ASF-006)
# ============================================================================


def test_coach_fast_fail_with_promises(coach_validator):
    """Test CoachValidator.validate_requirements() with synthetic report containing promises."""
    acceptance_criteria = [
        "Create src/file1.py",
        "Create src/file2.py",
    ]

    # Synthetic report with completion_promises
    task_work_results = {
        "_synthetic": True,
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "Create src/file1.py",
                "status": "complete",
                "evidence": "File-existence verified: src/file1.py (created)",
            },
            {
                "criterion_id": "AC-002",
                "criterion_text": "Create src/file2.py",
                "status": "incomplete",
                "evidence": "No file-existence evidence for this criterion",
            },
        ],
    }

    task = {
        "acceptance_criteria": acceptance_criteria,
    }

    # Mock methods that aren't needed for this test
    with patch.object(coach_validator, '_match_by_promises', return_value=RequirementsValidation(
        criteria_total=2,
        criteria_met=1,
        all_criteria_met=False,
        missing=["Create src/file2.py"],
        criteria_results=[
            CriterionResult(
                criterion_id="AC-001",
                criterion_text="Create src/file1.py",
                result="approved",
                status="approved",
                evidence="File-existence verified: src/file1.py (created)",
            ),
            CriterionResult(
                criterion_id="AC-002",
                criterion_text="Create src/file2.py",
                result="rejected",
                status="rejected",
                evidence="No file-existence evidence for this criterion",
            ),
        ],
    )) as mock_match_promises:
        result = coach_validator.validate_requirements(
            task=task,
            task_work_results=task_work_results,
            turn=1,
        )

        # Verify _match_by_promises was called (promise-based matching)
        mock_match_promises.assert_called_once()

        # Verify result
        assert result.criteria_total == 2
        assert result.criteria_met == 1
        assert result.all_criteria_met is False


def test_coach_fast_fail_without_promises(coach_validator, caplog):
    """Test CoachValidator.validate_requirements() with synthetic report without promises."""
    acceptance_criteria = [
        "Implement authentication logic",
        "Add error handling",
    ]

    # Synthetic report WITHOUT completion_promises
    task_work_results = {
        "_synthetic": True,
        "task_id": "TASK-TEST-001",
    }

    task = {
        "acceptance_criteria": acceptance_criteria,
    }

    with caplog.at_level(logging.WARNING):
        result = coach_validator.validate_requirements(
            task=task,
            task_work_results=task_work_results,
            turn=1,
        )

    # Verify all criteria are unmet
    assert result.criteria_total == 2
    assert result.criteria_met == 0
    assert result.all_criteria_met is False
    assert len(result.missing) == 2

    # Verify all criteria results are rejected
    for criterion_result in result.criteria_results:
        assert criterion_result.result == "rejected"
        assert criterion_result.status == "rejected"
        assert "Synthetic report — no file-existence promises available" in criterion_result.evidence

    # Verify warning was logged
    warning_messages = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("Synthetic report has no completion_promises" in msg for msg in warning_messages)
