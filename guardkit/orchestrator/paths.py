"""
Centralized path resolution for task artifacts.

This module provides the TaskArtifactPaths class that centralizes all task artifact
path logic, eliminating duplication across agent_invoker.py, pre_loop.py,
task_work_interface.py, and state_bridge.py.

Architecture:
    Single source of truth for all task-related file paths. All path constants
    and resolution logic live here, enabling consistent path handling across
    the AutoBuild orchestration system.

Path Categories:
    1. Implementation Plans: Design phase output (.claude/task-plans, docs/state)
    2. AutoBuild Artifacts: Player reports, Coach decisions, task-work results
    3. State Directories: Task state files, complexity scores

Example:
    >>> from guardkit.orchestrator.paths import TaskArtifactPaths
    >>> from pathlib import Path
    >>>
    >>> worktree = Path("/path/to/worktree")
    >>> task_id = "TASK-001"
    >>>
    >>> # Find existing plan
    >>> plan = TaskArtifactPaths.find_implementation_plan(task_id, worktree)
    >>>
    >>> # Get player report path for turn 1
    >>> report = TaskArtifactPaths.player_report_path(task_id, 1, worktree)
    >>>
    >>> # Ensure all directories exist
    >>> TaskArtifactPaths.ensure_task_dirs(task_id, worktree)
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class TaskArtifactPaths:
    """Centralized path resolution for task artifacts.

    All task-related file paths should be resolved through this class
    to ensure consistency and maintainability across the orchestrator.

    Path Templates (using {task_id} and {turn} placeholders):
        - Implementation plans: Multiple locations checked in priority order
        - Player reports: .guardkit/autobuild/{task_id}/player_turn_{turn}.json
        - Coach decisions: .guardkit/autobuild/{task_id}/coach_turn_{turn}.json
        - Task-work results: .guardkit/autobuild/{task_id}/task_work_results.json

    Attributes:
        PLAN_LOCATIONS: List of template strings for implementation plan paths
        PLAYER_REPORT: Template string for Player report path
        COACH_DECISION: Template string for Coach decision path
        TASK_WORK_RESULTS: Template string for task-work results path
        TASK_STATE_DIR: Template string for task state directory
        COMPLEXITY_SCORE: Template string for complexity score path
        AUTOBUILD_DIR: Template string for autobuild directory

    Example:
        >>> paths = TaskArtifactPaths.implementation_plan_paths("TASK-001", Path("/repo"))
        >>> for p in paths:
        ...     print(p)
        /repo/.claude/task-plans/TASK-001-implementation-plan.md
        /repo/.claude/task-plans/TASK-001-implementation-plan.json
        /repo/docs/state/TASK-001/implementation_plan.md
        /repo/docs/state/TASK-001/implementation_plan.json
    """

    # Implementation plan locations (in priority order)
    # Primary: .claude/task-plans (current standard)
    # Secondary: docs/state (legacy/alternative)
    PLAN_LOCATIONS: List[str] = [
        ".claude/task-plans/{task_id}-implementation-plan.md",
        ".claude/task-plans/{task_id}-implementation-plan.json",
        "docs/state/{task_id}/implementation_plan.md",
        "docs/state/{task_id}/implementation_plan.json",
    ]

    # AutoBuild artifact paths
    AUTOBUILD_DIR: str = ".guardkit/autobuild/{task_id}"
    PLAYER_REPORT: str = ".guardkit/autobuild/{task_id}/player_turn_{turn}.json"
    COACH_DECISION: str = ".guardkit/autobuild/{task_id}/coach_turn_{turn}.json"
    TASK_WORK_RESULTS: str = ".guardkit/autobuild/{task_id}/task_work_results.json"
    COACH_FEEDBACK: str = ".guardkit/autobuild/{task_id}/coach_feedback_{turn}.json"
    VERIFICATION_CONTEXT: str = ".guardkit/autobuild/{task_id}/verification_context_{turn}.json"

    # Task state paths
    TASK_STATE_DIR: str = "docs/state/{task_id}"
    COMPLEXITY_SCORE: str = "docs/state/{task_id}/complexity_score.json"

    # Directory templates for ensure_task_dirs
    REQUIRED_DIRS: List[str] = [
        ".guardkit/autobuild/{task_id}",
        ".claude/task-plans",
        "docs/state/{task_id}",
    ]

    # =========================================================================
    # Implementation Plan Methods
    # =========================================================================

    @classmethod
    def implementation_plan_paths(cls, task_id: str, worktree: Path) -> List[Path]:
        """Get all possible implementation plan paths in priority order.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        List[Path]
            List of paths to check for implementation plan, in priority order

        Example
        -------
        >>> paths = TaskArtifactPaths.implementation_plan_paths("TASK-001", Path("/repo"))
        >>> paths[0]
        PosixPath('/repo/.claude/task-plans/TASK-001-implementation-plan.md')
        """
        return [
            worktree / loc.format(task_id=task_id)
            for loc in cls.PLAN_LOCATIONS
        ]

    @classmethod
    def find_implementation_plan(
        cls,
        task_id: str,
        worktree: Path,
        min_content_length: int = 50,
    ) -> Optional[Path]:
        """Find first existing implementation plan file.

        Searches all plan locations in priority order and returns the first
        existing file that has sufficient content (not empty/stub).

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root
        min_content_length : int, optional
            Minimum file content length to consider valid (default: 50)

        Returns
        -------
        Optional[Path]
            Path to the first existing plan file, or None if not found

        Example
        -------
        >>> plan = TaskArtifactPaths.find_implementation_plan("TASK-001", Path("/repo"))
        >>> if plan:
        ...     print(f"Found plan at: {plan}")
        ... else:
        ...     print("No plan found")
        """
        for path in cls.implementation_plan_paths(task_id, worktree):
            if path.exists():
                # Verify plan has meaningful content
                try:
                    content = path.read_text().strip()
                    if len(content) >= min_content_length:
                        logger.debug(f"Found valid implementation plan at: {path}")
                        return path
                    else:
                        logger.warning(
                            f"Plan file exists but appears empty ({len(content)} chars): {path}"
                        )
                except IOError as e:
                    logger.warning(f"Could not read plan file {path}: {e}")

        logger.debug(f"No implementation plan found for {task_id}")
        return None

    @classmethod
    def preferred_plan_path(cls, task_id: str, worktree: Path) -> Path:
        """Get the preferred path for creating a new implementation plan.

        Returns the primary plan location (Markdown in .claude/task-plans)
        regardless of whether the file exists.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Preferred path for new implementation plan

        Example
        -------
        >>> path = TaskArtifactPaths.preferred_plan_path("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/.claude/task-plans/TASK-001-implementation-plan.md')
        """
        return worktree / cls.PLAN_LOCATIONS[0].format(task_id=task_id)

    # =========================================================================
    # AutoBuild Artifact Methods
    # =========================================================================

    @classmethod
    def autobuild_dir(cls, task_id: str, worktree: Path) -> Path:
        """Get autobuild directory for a task.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the autobuild directory

        Example
        -------
        >>> path = TaskArtifactPaths.autobuild_dir("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001')
        """
        return worktree / cls.AUTOBUILD_DIR.format(task_id=task_id)

    @classmethod
    def player_report_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for Player report.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        turn : int
            Turn number (1-indexed)
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the Player report file

        Example
        -------
        >>> path = TaskArtifactPaths.player_report_path("TASK-001", 1, Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/player_turn_1.json')
        """
        return worktree / cls.PLAYER_REPORT.format(task_id=task_id, turn=turn)

    @classmethod
    def coach_decision_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for Coach decision.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        turn : int
            Turn number (1-indexed)
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the Coach decision file

        Example
        -------
        >>> path = TaskArtifactPaths.coach_decision_path("TASK-001", 1, Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/coach_turn_1.json')
        """
        return worktree / cls.COACH_DECISION.format(task_id=task_id, turn=turn)

    @classmethod
    def task_work_results_path(cls, task_id: str, worktree: Path) -> Path:
        """Get path for task-work results file.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the task_work_results.json file

        Example
        -------
        >>> path = TaskArtifactPaths.task_work_results_path("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/task_work_results.json')
        """
        return worktree / cls.TASK_WORK_RESULTS.format(task_id=task_id)

    @classmethod
    def coach_feedback_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for Coach feedback file.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        turn : int
            Turn number (1-indexed)
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the coach_feedback_{turn}.json file

        Example
        -------
        >>> path = TaskArtifactPaths.coach_feedback_path("TASK-001", 1, Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/coach_feedback_1.json')
        """
        return worktree / cls.COACH_FEEDBACK.format(task_id=task_id, turn=turn)

    @classmethod
    def verification_context_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for verification context file.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        turn : int
            Turn number (1-indexed)
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the verification_context_{turn}.json file

        Example
        -------
        >>> path = TaskArtifactPaths.verification_context_path("TASK-001", 1, Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/verification_context_1.json')
        """
        return worktree / cls.VERIFICATION_CONTEXT.format(task_id=task_id, turn=turn)

    @classmethod
    def agent_report_path(
        cls,
        task_id: str,
        agent_type: str,
        turn: int,
        worktree: Path,
    ) -> Path:
        """Get path for any agent report (Player or Coach).

        Generic method for getting report paths by agent type.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        agent_type : str
            Type of agent ("player" or "coach")
        turn : int
            Turn number (1-indexed)
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the agent's report file

        Example
        -------
        >>> path = TaskArtifactPaths.agent_report_path("TASK-001", "player", 1, Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/player_turn_1.json')
        """
        return cls.autobuild_dir(task_id, worktree) / f"{agent_type}_turn_{turn}.json"

    # =========================================================================
    # Task State Methods
    # =========================================================================

    @classmethod
    def task_state_dir(cls, task_id: str, worktree: Path) -> Path:
        """Get task state directory.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the task state directory

        Example
        -------
        >>> path = TaskArtifactPaths.task_state_dir("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/docs/state/TASK-001')
        """
        return worktree / cls.TASK_STATE_DIR.format(task_id=task_id)

    @classmethod
    def complexity_score_path(cls, task_id: str, worktree: Path) -> Path:
        """Get path for complexity score file.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the complexity_score.json file

        Example
        -------
        >>> path = TaskArtifactPaths.complexity_score_path("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/docs/state/TASK-001/complexity_score.json')
        """
        return worktree / cls.COMPLEXITY_SCORE.format(task_id=task_id)

    # =========================================================================
    # Directory Management Methods
    # =========================================================================

    @classmethod
    def ensure_task_dirs(cls, task_id: str, worktree: Path) -> None:
        """Ensure all task directories exist.

        Creates all required directories for task artifacts if they don't exist.
        Uses mkdir with parents=True for nested directory creation.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Example
        -------
        >>> TaskArtifactPaths.ensure_task_dirs("TASK-001", Path("/repo"))
        # Creates:
        # - /repo/.guardkit/autobuild/TASK-001/
        # - /repo/.claude/task-plans/
        # - /repo/docs/state/TASK-001/
        """
        for dir_template in cls.REQUIRED_DIRS:
            dir_path = worktree / dir_template.format(task_id=task_id)
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {dir_path}")

    @classmethod
    def ensure_autobuild_dir(cls, task_id: str, worktree: Path) -> Path:
        """Ensure autobuild directory exists and return path.

        Convenience method that creates the autobuild directory and returns
        its path in one call.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the autobuild directory

        Example
        -------
        >>> path = TaskArtifactPaths.ensure_autobuild_dir("TASK-001", Path("/repo"))
        >>> path.exists()
        True
        """
        autobuild_path = cls.autobuild_dir(task_id, worktree)
        autobuild_path.mkdir(parents=True, exist_ok=True)
        return autobuild_path

    @classmethod
    def ensure_plan_dir(cls, worktree: Path) -> Path:
        """Ensure task-plans directory exists and return path.

        Parameters
        ----------
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the task-plans directory

        Example
        -------
        >>> path = TaskArtifactPaths.ensure_plan_dir(Path("/repo"))
        >>> path
        PosixPath('/repo/.claude/task-plans')
        """
        plan_dir = worktree / ".claude" / "task-plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        return plan_dir


# ============================================================================
# Public API
# ============================================================================

__all__ = ["TaskArtifactPaths"]
