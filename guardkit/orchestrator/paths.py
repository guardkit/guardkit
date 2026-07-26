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
    # TASK-SBHO-002: Orchestrator-private artifact directory.
    # Coach evidence and verdict are written here instead of the shared worktree
    # so the Player cannot casually read judge evidence.  This relocation removes
    # the casual read, not a determined process; full enforcement = the sandbox lane.
    TASK_PRIVATE_DIR: str = ".guardkit/autobuild-private/{task_id}"
    # QAV shadow receipt — the log-only second-opinion record written beside the
    # coach verdict it shadows (guardkit/qa/qav_shadow.py). Default-OFF lane.
    QAV_SHADOW: str = ".guardkit/autobuild/{task_id}/qav_shadow_turn_{turn}.json"
    TASK_WORK_RESULTS: str = ".guardkit/autobuild/{task_id}/task_work_results.json"
    DESIGN_RESULTS: str = ".guardkit/autobuild/{task_id}/design_results.json"
    COACH_FEEDBACK: str = ".guardkit/autobuild/{task_id}/coach_feedback_{turn}.json"
    VERIFICATION_CONTEXT: str = ".guardkit/autobuild/{task_id}/verification_context_{turn}.json"
    SECURITY_REVIEW: str = ".guardkit/autobuild/{task_id}/security_review.json"

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
    def qav_shadow_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for the QAV shadow receipt (beside the coach decision).

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
            Path to the qav_shadow_turn_{turn}.json receipt file

        Example
        -------
        >>> path = TaskArtifactPaths.qav_shadow_path("TASK-001", 1, Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/qav_shadow_turn_1.json')
        """
        return worktree / cls.QAV_SHADOW.format(task_id=task_id, turn=turn)

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
    def design_results_path(cls, task_id: str, worktree: Path) -> Path:
        """Get path for design results file.

        Design results store Phase 2.5B (Architectural Review) scores from
        pre-loop execution, enabling implement-only mode to access these
        scores during the Player-Coach loop.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the design_results.json file

        Example
        -------
        >>> path = TaskArtifactPaths.design_results_path("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/design_results.json')
        """
        return worktree / cls.DESIGN_RESULTS.format(task_id=task_id)

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
    def security_review_path(cls, task_id: str, worktree: Path) -> Path:
        """Get path for security review results file.

        Security review results store Phase 2.5C findings from pre-loop
        execution, enabling Coach to verify security review results
        without re-running the checks.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the security_review.json file

        Example
        -------
        >>> path = TaskArtifactPaths.security_review_path("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild/TASK-001/security_review.json')
        """
        return worktree / cls.SECURITY_REVIEW.format(task_id=task_id)

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
        # TASK-SBHO-002 (coordinator fix-and-re-verify): the COACH report is an
        # orchestrator-private artifact — resolve private-first with legacy
        # fallback. The PLAYER report stays in the shared worktree by design.
        if agent_type == "coach":
            return cls.coach_decision_path(task_id, turn, worktree)
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

    # =========================================================================
    # TASK-SBHO-002: Private directory accessors (orchestrator-only evidence)
    # =========================================================================

    @classmethod
    def task_private_dir(cls, task_id: str, worktree: Path) -> Path:
        """Get the orchestrator-private directory for task artifacts.

        Coach evidence and verdict files live here — invisible to the Player
        running in the shared worktree.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the .guardkit/autobuild-private/{task_id} directory

        Example
        -------
        >>> path = TaskArtifactPaths.task_private_dir("TASK-001", Path("/repo"))
        >>> path
        PosixPath('/repo/.guardkit/autobuild-private/TASK-001')
        """
        # TASK-SBHO-002 (coordinator fix-and-re-verify): the private dir must
        # live OUTSIDE the shared worktree — a rename inside it removes
        # nothing from the Player's reach. Feature/task worktrees live at
        # <repo>/.guardkit/worktrees/<id>; for those, resolve to the MAIN
        # checkout's .guardkit/autobuild-private. Otherwise (repo-root runs,
        # hermetic tmp roots) resolve beside the given root.
        wt = Path(worktree)
        if wt.parent.name == "worktrees" and wt.parent.parent.name == ".guardkit":
            root = wt.parent.parent.parent
        else:
            root = wt
        return root / cls.TASK_PRIVATE_DIR.format(task_id=task_id)

    @classmethod
    def coach_evidence_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for coach evidence bundle, with legacy fallback.

        Primary location: private directory (`.guardkit/autobuild-private/`).
        Fallback: legacy worktree location (`.guardkit/autobuild/`) if the
        private file does not exist (backward compatibility for older runs).

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
            Path to the coach_evidence_turn_{turn}.json file
            (private dir if present, else legacy worktree path)
        """
        private_path = cls.task_private_dir(task_id, worktree) / f"coach_evidence_turn_{turn}.json"
        if private_path.exists():
            return private_path
        legacy_path = cls.autobuild_dir(task_id, worktree) / f"coach_evidence_turn_{turn}.json"
        if legacy_path.exists():
            logger.debug("coach_evidence: falling back to legacy path %s", legacy_path)
            return legacy_path
        return private_path  # return primary path even if missing (caller handles)

    @classmethod
    def coach_decision_path(cls, task_id: str, turn: int, worktree: Path) -> Path:
        """Get path for coach decision, with legacy fallback.

        Primary location: private directory (`.guardkit/autobuild-private/`).
        Fallback: legacy worktree location (`.guardkit/autobuild/`) if the
        private file does not exist (backward compatibility for older runs).

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
            Path to the coach_turn_{turn}.json file
            (private dir if present, else legacy worktree path)
        """
        private_path = cls.task_private_dir(task_id, worktree) / f"coach_turn_{turn}.json"
        if private_path.exists():
            return private_path
        legacy_path = cls.autobuild_dir(task_id, worktree) / f"coach_turn_{turn}.json"
        if legacy_path.exists():
            logger.debug("coach_decision: falling back to legacy path %s", legacy_path)
            return legacy_path
        return private_path  # return primary path even if missing (caller handles)

    @classmethod
    def private_artifact_path(cls, task_id: str, artifact_name: str, worktree: Path) -> Path:
        """Get path for an artifact in the orchestrator-private directory.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        artifact_name : str
            File name (e.g., "coach_evidence_turn_1.json")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the artifact in the private directory
        """
        return cls.task_private_dir(task_id, worktree) / artifact_name

    @classmethod
    def legacy_artifact_path(cls, task_id: str, artifact_name: str, worktree: Path) -> Path:
        """Get path for an artifact in the legacy worktree location.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-001")
        artifact_name : str
            File name (e.g., "coach_turn_1.json")
        worktree : Path
            Path to the worktree/repository root

        Returns
        -------
        Path
            Path to the artifact in the legacy autobuild directory
        """
        return cls.autobuild_dir(task_id, worktree) / artifact_name


# ============================================================================
# Oracle-path stripping for Player-facing feedback
# ============================================================================

# Pattern that matches worktree-relative file paths (e.g. from behavioural
# oracle reports).  We replace them with a placeholder so the Player sees
# the scenario/AC id instead of a file path that leaks coach evidence.
_ORACLE_PATH_RE: Optional["re.Pattern[str]"] = None


def _oracle_path_re() -> "re.Pattern[str]":
    """Lazy-compile the oracle-path regex."""
    global _ORACLE_PATH_RE
    if _ORACLE_PATH_RE is None:
        import re as _re
        # Match paths like  src/tests/test_oracle.py  or  tests/unit/oracle.py
        # — anything that looks like a worktree-relative file path.
        _ORACLE_PATH_RE = _re.compile(
            r"(?:^|[\s(])"
            r"((?:[a-zA-Z0-9_\-/]+)"
            r"\.(?:py|js|ts|md|txt))"
        )
    return _ORACLE_PATH_RE


def strip_oracle_paths(text: str) -> str:
    """Remove worktree-relative oracle file paths from *text*.

    Player-facing feedback (coach_feedback) must not contain paths to oracle
    files because those paths are part of the coach evidence that was relocated
    to the orchestrator-private directory.  This function replaces any
    worktree-relative file path with ``<oracle-file>`` so the Player sees
    the scenario/AC identifier instead.

    Parameters
    ----------
    text : str
        Raw text that may contain oracle file paths.

    Returns
    -------
    str
        Text with oracle paths replaced.
    """
    # Replace the entire match (prefix + path) with just the placeholder.
    return _oracle_path_re().sub(" [<oracle-file>]", text)




# ============================================================================
# Public API
# ============================================================================

__all__ = ["TaskArtifactPaths", "strip_oracle_paths"]
