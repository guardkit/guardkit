"""
Integration tests for direct mode criteria matching (TASK-TEST-D1A5).

Exercises the full path: direct mode invocation -> synthetic report generation
-> Coach validation for scaffolding tasks with file-existence acceptance criteria.

This path was identified as untested by Q1 in the SFT-001 diagnostic diagrams
and confirmed as broken by TASK-REV-F248.

Coverage Target: >=90%
Test Count: 4 tests
"""

import json
import logging
from pathlib import Path

import pytest

from guardkit.orchestrator.synthetic_report import build_synthetic_report
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    RequirementsValidation,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree


@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker instance for direct mode testing."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
    )


@pytest.fixture
def coach_validator(worktree_path):
    """Create CoachValidator instance for testing."""
    return CoachValidator(worktree_path=worktree_path)


# ============================================================================
# Test 1: Full end-to-end path (Q1 bug path from SFT-001)
# ============================================================================


def test_direct_mode_scaffolding_criteria_matching(coach_validator):
    """Verify Coach can verify acceptance criteria from direct mode synthetic reports.

    This is the Q1 bug path from SFT-001 diagnostic diagrams.
    End-to-end: synthetic report -> _synthetic flag -> file-existence promises
    -> Coach approval.
    """
    # Setup: scaffolding task with file-existence acceptance criteria
    acceptance_criteria = [
        "Create src/auth/login.py with authentication logic",
        "Create tests/test_login.py with unit tests",
    ]

    # Act: Create synthetic report via build_synthetic_report() with files matching AC
    player_report = build_synthetic_report(
        task_id="TASK-TEST-D1A5",
        turn=1,
        files_modified=[],
        files_created=["src/auth/login.py", "tests/test_login.py"],
        tests_written=["tests/test_login.py"],
        tests_passed=False,
        test_count=0,
        implementation_notes="Direct mode SDK invocation completed (synthetic report)",
        concerns=[],
        acceptance_criteria=acceptance_criteria,
        task_type="scaffolding",
    )

    # Verify synthetic report has the right shape
    assert player_report["_synthetic"] is True
    assert "completion_promises" in player_report
    assert len(player_report["completion_promises"]) == 2

    # Simulate _write_direct_mode_results: propagate _synthetic and promises
    task_work_results = {
        "task_id": "TASK-TEST-D1A5",
        "completed": True,
        "success": True,
        "implementation_mode": "direct",
        "files_modified": [],
        "files_created": ["src/auth/login.py", "tests/test_login.py"],
        "_synthetic": True,
        "completion_promises": player_report["completion_promises"],
    }

    task = {"acceptance_criteria": acceptance_criteria}

    # Assert: Coach validate_requirements() returns all_criteria_met=True
    result = coach_validator.validate_requirements(
        task=task,
        task_work_results=task_work_results,
        turn=1,
    )

    assert result.all_criteria_met is True
    assert result.criteria_met == 2
    assert result.criteria_total == 2
    assert len(result.missing) == 0

    # Verify each criterion was verified via file-existence promises
    for cr in result.criteria_results:
        assert cr.result == "verified"
        assert "File-existence verified" in cr.evidence


# ============================================================================
# Test 2: _write_direct_mode_results sets _synthetic flag
# ============================================================================


def test_direct_mode_results_include_synthetic_flag(agent_invoker, worktree_path):
    """Verify _write_direct_mode_results sets _synthetic: True for synthetic reports."""
    task_id = "TASK-TEST-SYN"

    # Create a synthetic player report (as build_synthetic_report would)
    player_report = {
        "task_id": task_id,
        "turn": 1,
        "files_modified": ["src/existing.py"],
        "files_created": ["src/new_module.py"],
        "tests_written": ["tests/test_new_module.py"],
        "tests_run": False,
        "tests_passed": False,
        "test_output_summary": "",
        "implementation_notes": "Direct mode completed",
        "concerns": [],
        "requirements_addressed": [],
        "requirements_remaining": [],
        "_synthetic": True,
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "Create src/new_module.py",
                "status": "complete",
                "evidence": "File-existence verified: src/new_module.py (created)",
                "evidence_type": "file_existence",
            },
        ],
    }

    # Act: Write direct mode results
    results_path = agent_invoker._write_direct_mode_results(
        task_id=task_id,
        player_report=player_report,
        success=True,
    )

    # Assert: Read the written file and verify _synthetic flag propagated
    assert results_path.exists()
    results = json.loads(results_path.read_text())

    assert results["_synthetic"] is True
    assert results["implementation_mode"] == "direct"

    # Also verify completion_promises were propagated
    assert "completion_promises" in results
    assert len(results["completion_promises"]) == 1
    assert results["completion_promises"][0]["criterion_id"] == "AC-001"
    assert results["completion_promises"][0]["status"] == "complete"


# ============================================================================
# Test 3: Coach enters file-existence path for direct mode synthetic
# ============================================================================


def test_coach_uses_file_existence_for_direct_mode_synthetic(
    coach_validator, caplog
):
    """Verify Coach validate_requirements() enters file-existence path
    when task_work_results has _synthetic: True with completion_promises.
    """
    acceptance_criteria = [
        "Create src/models/user.py with user model",
        "Create src/models/schema.py with Pydantic schema",
    ]

    # Simulate direct mode task_work_results with synthetic flag and promises
    task_work_results = {
        "task_id": "TASK-TEST-PATH",
        "_synthetic": True,
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "Create src/models/user.py with user model",
                "status": "complete",
                "evidence": "File-existence verified: src/models/user.py (created)",
                "evidence_type": "file_existence",
            },
            {
                "criterion_id": "AC-002",
                "criterion_text": "Create src/models/schema.py with Pydantic schema",
                "status": "complete",
                "evidence": "File-existence verified: src/models/schema.py (created)",
                "evidence_type": "file_existence",
            },
        ],
    }

    task = {"acceptance_criteria": acceptance_criteria}

    # Capture logs to verify the synthetic path is taken
    with caplog.at_level(
        logging.INFO, logger="guardkit.orchestrator.quality_gates.coach_validator"
    ):
        result = coach_validator.validate_requirements(
            task=task,
            task_work_results=task_work_results,
            turn=1,
        )

    # Assert Coach entered the synthetic/file-existence path
    info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any(
        "Synthetic report detected" in msg for msg in info_messages
    ), f"Expected synthetic path log, got: {info_messages}"

    # Assert all criteria verified
    assert result.all_criteria_met is True
    assert result.criteria_met == 2

    # Assert evidence comes from file-existence promises (not text matching)
    for cr in result.criteria_results:
        assert cr.result == "verified"
        assert "File-existence verified" in cr.evidence


# ============================================================================
# Test 4: Regression — task-work mode (non-synthetic) unaffected
# ============================================================================


def test_task_work_mode_criteria_matching_unchanged(coach_validator):
    """Verify task-work mode (agent-written reports) still works as before.

    Non-synthetic reports should use the normal promise/text matching path,
    NOT the synthetic fast-fail path.
    """
    acceptance_criteria = [
        "Implement user login endpoint",
        "Add input validation for credentials",
    ]

    # task-work mode results: NO _synthetic flag, uses completion_promises normally
    task_work_results = {
        "task_id": "TASK-TEST-NORMAL",
        "completed": True,
        "success": True,
        "implementation_mode": "task-work",
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "Implement user login endpoint",
                "status": "complete",
                "evidence": "Player completed AC-001: login endpoint implemented",
                "evidence_type": "agent_report",
            },
            {
                "criterion_id": "AC-002",
                "criterion_text": "Add input validation for credentials",
                "status": "complete",
                "evidence": "Player completed AC-002: validation added",
                "evidence_type": "agent_report",
            },
        ],
    }

    task = {"acceptance_criteria": acceptance_criteria}

    result = coach_validator.validate_requirements(
        task=task,
        task_work_results=task_work_results,
        turn=1,
    )

    # Normal path should also verify all criteria
    assert result.all_criteria_met is True
    assert result.criteria_met == 2

    # Evidence should come from agent report, not file-existence
    for cr in result.criteria_results:
        assert cr.result == "verified"
        # Should NOT contain "Synthetic report" evidence
        assert "Synthetic report" not in cr.evidence
