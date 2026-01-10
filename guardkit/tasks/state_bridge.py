"""
Task State Bridge - Manages state transitions between AutoBuild and task-work.

This module provides the TaskStateBridge class which bridges AutoBuild's orchestration
state with task-work's state requirements, ensuring tasks are in the correct state
(design_approved) before implement-only execution.

Architecture:
    Implements the Bridge Pattern to decouple AutoBuild's orchestration from
    task-work's state machine requirements. This enables:
    - Atomic state transitions with file locking
    - Implementation plan validation
    - State transition logging for debugging
    - Concurrent safety for Conductor.build worktrees

Example:
    >>> from guardkit.tasks.state_bridge import TaskStateBridge
    >>>
    >>> bridge = TaskStateBridge("TASK-001", Path("/path/to/repo"))
    >>> bridge.ensure_design_approved_state()  # Ensures task is ready
    >>> # Now safe to run task-work --implement-only
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import frontmatter

from guardkit.orchestrator.exceptions import (
    PlanNotFoundError,
    StateValidationError,
    TaskStateError,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError

logger = logging.getLogger(__name__)


# State directories in order of typical transition
STATE_DIRECTORIES = [
    "backlog",
    "in_progress",
    "design_approved",
    "in_review",
    "blocked",
    "completed",
]


class TaskStateBridge:
    """
    Bridge between AutoBuild orchestration and task-work state machine.

    Manages state transitions to ensure tasks are in the correct state
    (design_approved) before task-work --implement-only execution.

    Responsibilities:
    - Ensure tasks are in design_approved state before implement-only
    - Verify implementation plan existence
    - Handle state transitions with atomic file operations
    - Provide logging for state transition debugging

    Attributes
    ----------
    task_id : str
        Task identifier (e.g., "TASK-001")
    repo_root : Path
        Path to the repository root
    logger : logging.Logger
        Logger instance for state transition logging

    Example
    -------
    >>> bridge = TaskStateBridge("TASK-001", Path("/path/to/repo"))
    >>> bridge.ensure_design_approved_state()
    True
    >>> bridge.verify_implementation_plan_exists()
    Path('/path/to/repo/.claude/task-plans/TASK-001-implementation-plan.md')
    """

    def __init__(self, task_id: str, repo_root: Path):
        """
        Initialize TaskStateBridge.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        repo_root : Path
            Path to the repository root
        """
        self.task_id = task_id
        self.repo_root = Path(repo_root)
        self.logger = logging.getLogger(f"{__name__}.{task_id}")

    def ensure_design_approved_state(self) -> bool:
        """
        Ensure task is in design_approved state with valid implementation plan.

        This method:
        1. Checks if task is already in design_approved state
        2. If not, transitions task from current state to design_approved
        3. Updates task frontmatter with design_approved status
        4. Verifies implementation plan exists

        Returns
        -------
        bool
            True if state is valid, raises exception otherwise

        Raises
        ------
        TaskStateError
            If state transition fails
        PlanNotFoundError
            If implementation plan missing
        TaskNotFoundError
            If task file cannot be found

        Example
        -------
        >>> bridge = TaskStateBridge("TASK-001", Path("/repo"))
        >>> bridge.ensure_design_approved_state()
        True
        """
        self.logger.info(f"Ensuring task {self.task_id} is in design_approved state")

        # Get current task state
        current_state, task_path = self._get_current_state()
        self.logger.debug(f"Current state: {current_state}, path: {task_path}")

        # If already in design_approved, just verify plan exists
        if current_state == "design_approved":
            self.logger.info(f"Task {self.task_id} already in design_approved state")
            self.verify_implementation_plan_exists()
            return True

        # Transition to design_approved state
        new_path = self.transition_to_design_approved()
        self.logger.info(
            f"Task {self.task_id} transitioned to design_approved at {new_path}"
        )

        # Verify plan exists after transition
        self.verify_implementation_plan_exists()

        return True

    def transition_to_design_approved(self) -> Path:
        """
        Move task to design_approved directory and update frontmatter.

        This method:
        1. Finds the current task file
        2. Updates frontmatter with status: design_approved
        3. Moves file to tasks/design_approved/ directory

        Returns
        -------
        Path
            New task file location

        Raises
        ------
        TaskStateError
            If transition fails
        TaskNotFoundError
            If task file not found

        Example
        -------
        >>> bridge = TaskStateBridge("TASK-001", Path("/repo"))
        >>> new_path = bridge.transition_to_design_approved()
        >>> print(new_path)
        Path('/repo/tasks/design_approved/TASK-001-description.md')
        """
        # Get current state and path
        current_state, task_path = self._get_current_state()

        self.logger.info(
            f"Transitioning task {self.task_id} from {current_state} to design_approved"
        )

        # Update frontmatter with new status
        self._update_task_frontmatter(task_path, {"status": "design_approved"})

        # Move file to design_approved directory
        new_path = self._move_task_to_state(task_path, "design_approved")

        self.logger.info(f"Task file moved to: {new_path}")

        return new_path

    def verify_implementation_plan_exists(self) -> Path:
        """
        Verify implementation plan exists in expected location.

        This method checks multiple possible locations for the implementation plan:
        1. .claude/task-plans/{task_id}-implementation-plan.md
        2. .claude/task-plans/{task_id}-implementation-plan.json
        3. docs/state/{task_id}/implementation_plan.md
        4. docs/state/{task_id}/implementation_plan.json

        Returns
        -------
        Path
            Plan file location

        Raises
        ------
        PlanNotFoundError
            If plan missing or invalid

        Example
        -------
        >>> bridge = TaskStateBridge("TASK-001", Path("/repo"))
        >>> plan_path = bridge.verify_implementation_plan_exists()
        >>> print(plan_path)
        Path('/repo/.claude/task-plans/TASK-001-implementation-plan.md')
        """
        # Check possible plan locations
        plan_paths = self._get_plan_paths()

        for plan_path in plan_paths:
            if plan_path.exists():
                # Verify plan has content (not empty)
                content = plan_path.read_text().strip()
                if len(content) > 50:  # Minimal content check
                    self.logger.debug(f"Found valid implementation plan at: {plan_path}")
                    return plan_path
                else:
                    self.logger.warning(
                        f"Plan file exists but appears empty: {plan_path}"
                    )

        # No valid plan found
        raise PlanNotFoundError(
            f"Implementation plan not found for {self.task_id}. "
            f"Expected at one of: {[str(p) for p in plan_paths]}. "
            f"Run task-work --design-only first to generate the plan.",
            plan_path=str(plan_paths[0]),
            task_id=self.task_id,
        )

    def get_current_state(self) -> str:
        """
        Get the current state of the task.

        Returns
        -------
        str
            Current state (backlog, in_progress, design_approved, etc.)

        Raises
        ------
        TaskNotFoundError
            If task file cannot be found
        """
        state, _ = self._get_current_state()
        return state

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_current_state(self) -> Tuple[str, Path]:
        """
        Find task file and determine current state from directory location.

        Returns
        -------
        Tuple[str, Path]
            Current state name and path to task file

        Raises
        ------
        TaskNotFoundError
            If task file cannot be found in any state directory
        """
        tasks_dir = self.repo_root / "tasks"

        for state in STATE_DIRECTORIES:
            state_dir = tasks_dir / state
            if not state_dir.exists():
                continue

            # Search for task file in this state directory (including subdirs)
            for task_path in state_dir.rglob(f"{self.task_id}*.md"):
                return state, task_path

        # Task not found
        raise TaskNotFoundError(
            f"Task {self.task_id} not found in any state directory.\n"
            f"Searched: {[str(tasks_dir / s) for s in STATE_DIRECTORIES]}"
        )

    def _get_plan_paths(self) -> List[Path]:
        """
        Get list of possible implementation plan paths.

        Uses centralized TaskArtifactPaths for consistent path resolution.

        Returns
        -------
        List[Path]
            List of paths to check for implementation plan
        """
        return TaskArtifactPaths.implementation_plan_paths(self.task_id, self.repo_root)

    def _update_task_frontmatter(self, task_path: Path, updates: Dict[str, Any]) -> None:
        """
        Update task frontmatter fields while preserving existing content.

        Parameters
        ----------
        task_path : Path
            Path to task markdown file
        updates : Dict[str, Any]
            Dictionary of frontmatter fields to update

        Raises
        ------
        TaskStateError
            If file read/write fails
        """
        try:
            # Read existing file
            with open(task_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Update frontmatter fields
            for key, value in updates.items():
                post.metadata[key] = value

            # Write back
            with open(task_path, "w", encoding="utf-8") as f:
                f.write(frontmatter.dumps(post))

            self.logger.debug(f"Updated frontmatter for {task_path}: {updates}")

        except Exception as e:
            raise TaskStateError(
                f"Failed to update frontmatter for {self.task_id}: {e}",
                task_id=self.task_id,
            ) from e

    def _move_task_to_state(self, current_path: Path, new_state: str) -> Path:
        """
        Move task file to new state directory.

        Parameters
        ----------
        current_path : Path
            Current task file path
        new_state : str
            Target state (design_approved, in_progress, etc.)

        Returns
        -------
        Path
            New task file location

        Raises
        ------
        TaskStateError
            If move operation fails
        """
        # Determine new directory
        new_state_dir = self.repo_root / "tasks" / new_state

        # Create state directory if it doesn't exist
        new_state_dir.mkdir(parents=True, exist_ok=True)

        # Determine new path (preserve filename)
        new_path = new_state_dir / current_path.name

        try:
            # Move file (shutil.move handles cross-filesystem moves)
            shutil.move(str(current_path), str(new_path))
            self.logger.info(
                f"Moved task file: {current_path} -> {new_path}"
            )
            return new_path

        except Exception as e:
            raise TaskStateError(
                f"Failed to move task {self.task_id} to {new_state}: {e}",
                task_id=self.task_id,
                expected_state=new_state,
            ) from e


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "TaskStateBridge",
    "STATE_DIRECTORIES",
]
