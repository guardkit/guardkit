"""
Seam tests S8: task-type profiles → task state.

Tests the task-type profiles the Coach turn reads (``tests_required``) and the
task state bridge (state file moves, frontmatter updates).

Since the cull (27 October 2026) ``CoachValidator.validate`` and its quality
gates (test counts, coverage, architecture score, zero-test) are gone, with
their tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

import pytest

from guardkit.models.task_types import (
    TaskType,
    get_profile,
)
from guardkit.tasks.state_bridge import TaskStateBridge

if TYPE_CHECKING:
    pass


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def task_file_factory(tmp_task_dir: Dict[str, Path]):
    """
    Factory fixture to create task markdown files with frontmatter.

    Creates task files in the specified state directory with the given
    frontmatter and content.

    Args:
        tmp_task_dir: Fixture providing GuardKit directory structure.

    Returns:
        Callable that creates task files and returns their path.
    """

    def create_task(
        task_id: str,
        state: str = "in_progress",
        task_type: str = "feature",
        title: str = "Test Task",
        extra_frontmatter: Dict[str, Any] | None = None,
        content: str = "## Test Task Content\n",
    ) -> Path:
        """
        Create a task file with the given parameters.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            state: State directory to place the task in
            task_type: Task type for quality gate profile
            title: Task title
            extra_frontmatter: Additional frontmatter fields
            content: Task body content

        Returns:
            Path to the created task file
        """
        state_dir = tmp_task_dir.get(state, tmp_task_dir["in_progress"])
        state_dir.mkdir(parents=True, exist_ok=True)

        # Build frontmatter
        frontmatter_dict = {
            "id": task_id,
            "title": title,
            "status": state,
            "task_type": task_type,
        }
        if extra_frontmatter:
            frontmatter_dict.update(extra_frontmatter)

        # Format frontmatter as YAML
        frontmatter_lines = ["---"]
        for key, value in frontmatter_dict.items():
            if isinstance(value, bool):
                frontmatter_lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (list, dict)):
                frontmatter_lines.append(f"{key}: {json.dumps(value)}")
            else:
                frontmatter_lines.append(f"{key}: {value}")
        frontmatter_lines.append("---")
        frontmatter_lines.append("")

        # Combine frontmatter and content
        file_content = "\n".join(frontmatter_lines) + content

        # Create task file
        task_filename = f"{task_id}-test-task.md"
        task_path = state_dir / task_filename
        task_path.write_text(file_content, encoding="utf-8")

        return task_path

    return create_task


# ============================================================================
# S8 Seam Tests: Quality Gates → State Transitions
# ============================================================================


@pytest.mark.seam
class TestQualityGateStateTransitions:
    """The task state bridge and the task-type profiles."""

    def test_real_task_file_state_verification(
        self,
        tmp_task_dir: Dict[str, Path],
        task_file_factory,
    ):
        """
        Test: Verify state changes by re-reading task file after transition.

        Creates a real task file and verifies that successful validation
        doesn't automatically move the file (that's the orchestrator's job),
        but the state bridge CAN move files when instructed.
        """
        task_id = "TASK-STATE-001"

        # Create task file in backlog
        task_path = task_file_factory(
            task_id=task_id,
            state="backlog",
            task_type="feature",
            title="State Transition Test",
        )

        # Verify task is in backlog
        assert "backlog" in str(task_path)
        assert task_path.exists()

        # Read initial state
        initial_content = task_path.read_text()
        assert "status: backlog" in initial_content

        # Create state bridge and transition to design_approved
        bridge = TaskStateBridge(
            task_id=task_id,
            repo_root=tmp_task_dir["root"],
        )

        # Create a stub implementation plan (required for transition)
        plan_dir = tmp_task_dir["task_plans"]
        plan_path = plan_dir / f"{task_id}-implementation-plan.md"
        plan_path.write_text(
            f"# Implementation Plan: {task_id}\n\n"
            "## Overview\nTest implementation plan.\n\n"
            "## Steps\n1. Step one\n2. Step two\n"
        )

        # Transition to design_approved
        new_path = bridge.transition_to_design_approved()

        # Verify task moved to design_approved directory
        assert "design_approved" in str(new_path)
        assert new_path.exists()

        # Verify old path no longer exists
        assert not task_path.exists(), "Task should have been moved from backlog"

        # Verify frontmatter was updated
        new_content = new_path.read_text()
        assert "status: design_approved" in new_content

    def test_quality_gate_profile_by_task_type(self):
        """
        Test: Verify quality gate profiles correctly vary by task type.

        ``tests_required`` decides whether a red required suite sends a
        turn back (``quality_gates/required_suite.py``).
        """
        # FEATURE profile - the project's tests are required
        feature_profile = get_profile(TaskType.FEATURE)
        assert feature_profile.tests_required is True

        # DOCUMENTATION profile - no tests required
        doc_profile = get_profile(TaskType.DOCUMENTATION)
        assert doc_profile.tests_required is False

        # SCAFFOLDING profile - no tests required
        scaffolding_profile = get_profile(TaskType.SCAFFOLDING)
        assert scaffolding_profile.tests_required is False

        # TESTING profile - TASK-ABFIX-012: tests ARE required (deliverable IS
        # passing tests); coverage still not required.
        testing_profile = get_profile(TaskType.TESTING)
        assert testing_profile.tests_required is True

        # REFACTOR profile - full validation like FEATURE
        refactor_profile = get_profile(TaskType.REFACTOR)
        assert refactor_profile.tests_required is True
