"""State tracker module for unified state representation and multi-layered detection.

This module provides the StateTracker abstraction and MultiLayeredStateTracker
implementation for detecting and capturing work state even when Player JSON
reports are missing.

Architecture:
    StateTracker ABC defines the interface (fixes DIP violation)
    MultiLayeredStateTracker implements cascade detection:
        1. Player JSON report (highest fidelity, if available)
        2. Test execution results (verifies implementation quality)
        3. Git changes (detects file-level work)

Design Patterns:
    - Strategy Pattern: StateTracker ABC enables interchangeable strategies
    - Chain of Responsibility: Cascade detection (Player → Tests → Git)
    - Dataclass Pattern: Lightweight state containers (GuardKit standard)

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.state_tracker import MultiLayeredStateTracker
    >>>
    >>> tracker = MultiLayeredStateTracker(
    ...     task_id="TASK-001",
    ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
    ... )
    >>>
    >>> state = tracker.capture_state(turn=1)
    >>> if state:
    ...     print(f"Detection method: {state.detection_method}")
    ...     print(f"Files modified: {len(state.files_modified)}")
    ...     print(f"Tests passed: {state.tests_passed}")
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from guardkit.orchestrator.state_detection import (
    GitChangesSummary,
    TestResultsSummary,
    detect_git_changes,
    detect_test_results,
)

logger = logging.getLogger(__name__)

# Type alias for detection methods
DetectionMethod = Literal[
    "player_report",
    "git_test_detection",
    "git_only",
    "test_only",
    "comprehensive",
]


@dataclass
class WorkState:
    """Unified work state representation from multiple detection sources.

    This dataclass captures the complete state of work performed during a turn,
    synthesized from multiple detection methods (Player report, git, tests).

    Attributes:
        turn_number: Turn number (1-indexed)
        files_modified: List of file paths that were modified
        files_created: List of file paths that were created
        tests_written: List of test file paths
        tests_passed: Whether tests are passing
        test_count: Number of tests run
        git_changes: Optional GitChangesSummary from git detection
        test_results: Optional TestResultsSummary from test execution
        player_report: Optional Player report JSON (if available)
        timestamp: ISO 8601 timestamp when state was captured
        detection_method: How state was detected

    Note:
        Fields are explicitly Optional per architectural review recommendation.
    """

    turn_number: int
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    tests_written: List[str] = field(default_factory=list)
    tests_passed: bool = False
    test_count: int = 0
    git_changes: Optional[GitChangesSummary] = None
    test_results: Optional[TestResultsSummary] = None
    player_report: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    detection_method: DetectionMethod = "git_test_detection"

    @property
    def has_work(self) -> bool:
        """True if any work was detected."""
        return (
            len(self.files_modified) > 0
            or len(self.files_created) > 0
            or len(self.tests_written) > 0
            or self.test_count > 0
        )

    @property
    def total_files_changed(self) -> int:
        """Total number of files with changes."""
        return len(self.files_modified) + len(self.files_created)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Handles nested dataclasses (GitChangesSummary, TestResultsSummary).

        Returns:
            JSON-serializable dictionary
        """
        result = {
            "turn_number": self.turn_number,
            "files_modified": self.files_modified,
            "files_created": self.files_created,
            "tests_written": self.tests_written,
            "tests_passed": self.tests_passed,
            "test_count": self.test_count,
            "timestamp": self.timestamp,
            "detection_method": self.detection_method,
        }

        # Convert nested dataclasses
        if self.git_changes:
            result["git_changes"] = asdict(self.git_changes)
        else:
            result["git_changes"] = None

        if self.test_results:
            result["test_results"] = asdict(self.test_results)
        else:
            result["test_results"] = None

        # Exclude full player report (too large)
        result["player_report_available"] = self.player_report is not None

        return result


class StateTracker(ABC):
    """Abstract state tracking interface (fixes DIP violation).

    This ABC defines the interface for state tracking strategies, allowing
    the AutoBuildOrchestrator to depend on the abstraction rather than
    concrete implementations.

    Implementations should provide:
        - capture_state: Detect and capture current work state
    """

    @abstractmethod
    def capture_state(self, turn: int) -> Optional[WorkState]:
        """Capture current work state via available detection methods.

        Args:
            turn: Turn number (1-indexed)

        Returns:
            WorkState if any work detected, None otherwise
        """
        pass


class MultiLayeredStateTracker(StateTracker):
    """Multi-layered state tracker using cascade detection.

    This implementation uses multiple detection methods to capture work state,
    providing redundancy when Player JSON reports are missing.

    Detection Cascade (priority order):
        1. Player JSON report - Highest fidelity, complete context
        2. CoachVerifier test results - Verifies implementation quality
        3. Git changes - Detects file-level work (fallback)

    Attributes:
        task_id: Task identifier
        worktree_path: Path to git worktree
        autobuild_dir: Path to .guardkit/autobuild/{task_id}/

    Example:
        >>> tracker = MultiLayeredStateTracker(
        ...     task_id="TASK-001",
        ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
        ... )
        >>>
        >>> # Capture state after Player invocation
        >>> state = tracker.capture_state(turn=1)
        >>> if state:
        ...     if state.detection_method == "player_report":
        ...         print("Full Player report available")
        ...     else:
        ...         print(f"Fallback detection: {state.detection_method}")
    """

    def __init__(
        self,
        task_id: str,
        worktree_path: Path,
    ):
        """Initialize MultiLayeredStateTracker.

        Args:
            task_id: Task identifier
            worktree_path: Path to git worktree
        """
        self.task_id = task_id
        self.worktree_path = Path(worktree_path)
        self.autobuild_dir = self.worktree_path / ".guardkit" / "autobuild" / task_id

    def capture_state(self, turn: int) -> Optional[WorkState]:
        """Capture work state using cascade detection.

        Detection order:
        1. Try loading Player JSON report (highest fidelity)
        2. Always capture git state (independent verification)
        3. Always run tests (independent verification)
        4. Synthesize WorkState from available sources

        Args:
            turn: Turn number (1-indexed)

        Returns:
            WorkState if any work detected, None otherwise
        """
        logger.info(f"Capturing state for {self.task_id} turn {turn}")

        # Layer 1: Try Player report (highest fidelity)
        player_report = self._load_player_report(turn)

        # Layer 2: Git detection (always run for verification)
        git_changes = detect_git_changes(self.worktree_path)

        # Layer 3: Test detection (always run for verification)
        test_results = detect_test_results(
            self.worktree_path,
            task_id=self.task_id,
            turn=turn,
        )

        # Synthesize WorkState from available sources
        return self._synthesize_state(
            turn=turn,
            player_report=player_report,
            git_changes=git_changes,
            test_results=test_results,
        )

    def _load_player_report(self, turn: int) -> Optional[Dict[str, Any]]:
        """Load Player JSON report if available.

        Args:
            turn: Turn number

        Returns:
            Player report dictionary, or None if not found
        """
        report_path = self.autobuild_dir / f"player_turn_{turn}.json"

        if not report_path.exists():
            logger.debug(f"Player report not found: {report_path}")
            return None

        try:
            with open(report_path, "r") as f:
                report = json.load(f)
            logger.info(f"Loaded Player report from {report_path}")
            return report
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in Player report: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to load Player report: {e}")
            return None

    def _synthesize_state(
        self,
        turn: int,
        player_report: Optional[Dict[str, Any]],
        git_changes: Optional[GitChangesSummary],
        test_results: Optional[TestResultsSummary],
    ) -> Optional[WorkState]:
        """Synthesize WorkState from all detection sources.

        Priority:
        - If Player report available: Use as source of truth, git/tests for verification
        - If no Player report: Use git + tests for detection
        - If neither: Return None

        Args:
            turn: Turn number
            player_report: Optional Player report
            git_changes: Optional git detection results
            test_results: Optional test execution results

        Returns:
            WorkState if any work detected, None otherwise
        """
        # Case 1: Player report available (highest fidelity)
        if player_report:
            return self._state_from_player_report(
                turn=turn,
                player_report=player_report,
                git_changes=git_changes,
                test_results=test_results,
            )

        # Case 2: No Player report, but git or test detection available
        if git_changes or test_results:
            return self._state_from_detection(
                turn=turn,
                git_changes=git_changes,
                test_results=test_results,
            )

        # Case 3: No work detected
        logger.info(f"No work detected for {self.task_id} turn {turn}")
        return None

    def _state_from_player_report(
        self,
        turn: int,
        player_report: Dict[str, Any],
        git_changes: Optional[GitChangesSummary],
        test_results: Optional[TestResultsSummary],
    ) -> WorkState:
        """Create WorkState from Player report with verification context.

        Args:
            turn: Turn number
            player_report: Player report (source of truth)
            git_changes: Optional git detection for verification
            test_results: Optional test results for verification

        Returns:
            WorkState with player_report as primary source
        """
        # Use test_results for test status (independent verification)
        tests_passed = (
            test_results.tests_passed
            if test_results and test_results.tests_run
            else player_report.get("tests_passed", False)
        )
        test_count = (
            test_results.test_count
            if test_results and test_results.tests_run
            else 0
        )

        return WorkState(
            turn_number=turn,
            files_modified=player_report.get("files_modified", []),
            files_created=player_report.get("files_created", []),
            tests_written=player_report.get("tests_written", []),
            tests_passed=tests_passed,
            test_count=test_count,
            git_changes=git_changes,
            test_results=test_results,
            player_report=player_report,
            timestamp=datetime.now().isoformat(),
            detection_method="player_report",
        )

    def _state_from_detection(
        self,
        turn: int,
        git_changes: Optional[GitChangesSummary],
        test_results: Optional[TestResultsSummary],
    ) -> WorkState:
        """Create WorkState from git and test detection (fallback path).

        Args:
            turn: Turn number
            git_changes: Git detection results
            test_results: Test execution results

        Returns:
            WorkState synthesized from detection
        """
        # Determine detection method
        if git_changes and test_results and test_results.tests_run:
            detection_method: DetectionMethod = "git_test_detection"
        elif git_changes and (not test_results or not test_results.tests_run):
            detection_method = "git_only"
        elif test_results and test_results.tests_run:
            detection_method = "test_only"
        else:
            detection_method = "git_test_detection"

        # Extract file lists from git
        files_modified = git_changes.files_modified if git_changes else []
        files_created = git_changes.files_added if git_changes else []

        # Identify test files from created/modified
        tests_written = [
            f for f in files_created + files_modified
            if _is_test_file(f)
        ]

        # Extract test results
        tests_passed = test_results.tests_passed if test_results else False
        test_count = test_results.test_count if test_results else 0

        logger.info(
            f"State from detection ({detection_method}): "
            f"{len(files_modified)} modified, {len(files_created)} created, "
            f"{test_count} tests"
        )

        return WorkState(
            turn_number=turn,
            files_modified=files_modified,
            files_created=files_created,
            tests_written=tests_written,
            tests_passed=tests_passed,
            test_count=test_count,
            git_changes=git_changes,
            test_results=test_results,
            player_report=None,
            timestamp=datetime.now().isoformat(),
            detection_method=detection_method,
        )

    def save_state(self, state: WorkState) -> Path:
        """Save WorkState to JSON file for persistence.

        Args:
            state: WorkState to save

        Returns:
            Path to saved state file
        """
        self.autobuild_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.autobuild_dir / f"work_state_turn_{state.turn_number}.json"

        with open(state_path, "w") as f:
            json.dump(state.to_dict(), f, indent=2)

        logger.info(f"Saved work state to {state_path}")
        return state_path


def _is_test_file(file_path: str) -> bool:
    """Check if a file path is a test file.

    Args:
        file_path: File path to check

    Returns:
        True if file is a test file
    """
    path = Path(file_path)
    name = path.name.lower()

    # Common test file patterns
    test_patterns = [
        name.startswith("test_"),
        name.endswith("_test.py"),
        name.endswith(".test.ts"),
        name.endswith(".test.tsx"),
        name.endswith(".test.js"),
        name.endswith(".test.jsx"),
        name.endswith("_spec.rb"),
        name.endswith("_test.go"),
        "tests/" in str(path).lower(),
        "test/" in str(path).lower(),
    ]

    return any(test_patterns)


__all__ = [
    "DetectionMethod",
    "WorkState",
    "StateTracker",
    "MultiLayeredStateTracker",
]
