"""AgentInvoker handles Claude Agents SDK invocation for Player and Coach agents."""

import asyncio
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Literal, Optional, Tuple, Union

if TYPE_CHECKING:
    from guardkit.orchestrator.autobuild import DesignContext

from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
    PlanNotFoundError,
    PlayerReportInvalidError,
    PlayerReportNotFoundError,
    RateLimitExceededError,
    SDKTimeoutError,
    TaskStateError,
    TaskWorkResult,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.prompts import load_protocol
from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    HonestyVerification,
    format_verification_context,
)
from guardkit.orchestrator.schemas import (
    CompletionPromise,
    CriterionVerification,
    CriterionStatus,
    VerificationResult,
)

# Logger for agent invocations
logger = logging.getLogger(__name__)


# =========================================================================
# Heartbeat Logging for SDK Invocations
# =========================================================================


@asynccontextmanager
async def async_heartbeat(
    task_id: str,
    phase: str,
    interval: int = 30,
) -> AsyncGenerator[None, None]:
    """Context manager that logs heartbeat messages during SDK invocations.

    Provides periodic progress logging to eliminate the perception of "stalling"
    during long-running SDK invocations (10-20+ minutes).

    Args:
        task_id: Task identifier for log messages (e.g., "TASK-001")
        phase: Description of the current phase (e.g., "Player invocation")
        interval: Seconds between heartbeat logs (default: 30)

    Yields:
        None - just provides heartbeat logging during context

    Example:
        >>> async with async_heartbeat("TASK-001", "Player invocation"):
        ...     result = await sdk_invoke(...)  # May take 10+ minutes
        # Logs: [TASK-001] Player invocation in progress... (30s elapsed)
        # Logs: [TASK-001] Player invocation in progress... (60s elapsed)
        # etc.
    """
    async def heartbeat() -> None:
        elapsed = 0
        while True:
            await asyncio.sleep(interval)
            elapsed += interval
            logger.info(f"[{task_id}] {phase} in progress... ({elapsed}s elapsed)")

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task


# Feature flag for task-work delegation (set via environment or config)
# When enabled, invoke_player() delegates to `guardkit task-work --implement-only`
# instead of direct SDK invocation
USE_TASK_WORK_DELEGATION = os.environ.get("GUARDKIT_USE_TASK_WORK_DELEGATION", "false").lower() == "true"

# SDK timeout in seconds (default: 1200s/20min, can be overridden via GUARDKIT_SDK_TIMEOUT env var)
# Complexity-6+ tasks with full Phase 3-5 pipeline (implementation, testing, code review)
# need ~900-1200s. 1200s provides adequate headroom for most tasks.
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1200"))

# TASK-ASF-008: Maximum SDK timeout cap to prevent excessively long sessions
# Even with high complexity + task-work mode, timeout should not exceed 1 hour
MAX_SDK_TIMEOUT = 3600

# TASK-REV-BB80: SDK max_turns for task-work invocation (separate from adversarial turns)
# /task-work runs multiple phases internally (planning, review, implementation, testing)
# and needs ~50 internal turns. This is NOT the same as orchestrator's max_turns (adversarial rounds).
TASK_WORK_SDK_MAX_TURNS = 50

# Player report schema - required fields
PLAYER_REPORT_SCHEMA = {
    "task_id": str,
    "turn": int,
    "files_modified": list,
    "files_created": list,
    "tests_written": list,
    "tests_run": bool,
    "tests_passed": bool,
    "implementation_notes": str,
    "concerns": list,
    "requirements_addressed": list,
    "requirements_remaining": list,
}

# Coach decision schema - required fields
COACH_DECISION_SCHEMA = {
    "task_id": str,
    "turn": int,
    "decision": str,  # "approve" or "feedback"
}

# Documentation level to max files mapping
# Used to enforce file count constraints based on documentation_level setting
DOCUMENTATION_LEVEL_MAX_FILES = {
    "minimal": 2,
    "standard": 2,
    "comprehensive": None,  # No limit
}


# =========================================================================
# Stream Parser for Quality Gate Extraction
# =========================================================================


import re


class TaskWorkStreamParser:
    """Stateful incremental parser for task-work SDK stream messages.

    This parser extracts quality gate results from task-work output streams,
    accumulating results across multiple stream messages. It uses regex
    patterns for flexibility and handles unrecognized patterns gracefully.

    Key features:
    - Incremental parsing (called for each stream message)
    - Accumulates results across calls
    - Uses sets for file lists to avoid duplicates
    - Graceful degradation for unrecognized patterns

    Example:
        >>> parser = TaskWorkStreamParser()
        >>> parser.parse_message("Phase 2: Implementation Planning...")
        >>> parser.parse_message("12 tests passed, 0 failed")
        >>> parser.parse_message("Coverage: 85.5%")
        >>> result = parser.to_result()
        >>> result["tests_passed"]
        12
        >>> result["coverage"]
        85.5
    """

    # Pattern constants for matching task-work output
    # Using single pattern per type following YAGNI principle
    PHASE_MARKER_PATTERN = re.compile(r"Phase\s+(\d+(?:\.\d+)?)[:\s]+(.+)")
    PHASE_COMPLETE_PATTERN = re.compile(r"[✓✔]\s+Phase\s+(\d+(?:\.\d+)?)\s+complete", re.IGNORECASE)
    TESTS_PASSED_PATTERN = re.compile(r"(\d+)\s+tests?\s+passed", re.IGNORECASE)
    TESTS_FAILED_PATTERN = re.compile(r"(\d+)\s+tests?\s+failed", re.IGNORECASE)
    COVERAGE_PATTERN = re.compile(r"[Cc]overage[:\s]+(\d+(?:\.\d+)?)%")
    QUALITY_GATES_PASSED_PATTERN = re.compile(r"[Qq]uality\s+gates[:\s]*PASSED|all\s+quality\s+gates\s+passed", re.IGNORECASE)
    QUALITY_GATES_FAILED_PATTERN = re.compile(r"[Qq]uality\s+gates[:\s]*FAILED", re.IGNORECASE)
    FILES_MODIFIED_PATTERN = re.compile(r"(?:Modified|Changed):\s*([^\s,]+(?:\.[a-zA-Z]+|/))")
    FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+(?:\.[a-zA-Z]+|/))")
    # Architectural review score patterns
    ARCH_SCORE_PATTERN = re.compile(r"[Aa]rchitectural.*?[Ss]core[:\s]+(\d+)(?:/100)?", re.IGNORECASE)
    ARCH_SUBSCORES_PATTERN = re.compile(r"SOLID[:\s]+(\d+),?\s*DRY[:\s]+(\d+),?\s*YAGNI[:\s]+(\d+)", re.IGNORECASE)
    # Tool invocation patterns for tracking Write/Edit operations
    # Matches: <invoke name="Write"> or <invoke name="Edit">
    TOOL_INVOKE_PATTERN = re.compile(r'<invoke\s+name="(Write|Edit)">')
    # Matches: <parameter name="file_path">/path/to/file</parameter>
    TOOL_FILE_PATH_PATTERN = re.compile(r'<parameter\s+name="file_path">([^<]+)</parameter>')
    # Matches tool result messages like "File created successfully at: /path"
    TOOL_RESULT_CREATED_PATTERN = re.compile(r"File\s+(?:created|written)\s+(?:successfully\s+)?(?:at|to)[:\s]+([^\s]+)", re.IGNORECASE)
    TOOL_RESULT_MODIFIED_PATTERN = re.compile(r"File\s+(?:modified|updated|edited)\s+(?:successfully\s+)?(?:at)?[:\s]+([^\s]+)", re.IGNORECASE)
    # Pytest summary pattern: "X passed" or "X passed, Y failed" or "X passed, Y failed, Z skipped"
    PYTEST_SUMMARY_PATTERN = re.compile(
        r"[=]+\s*(?:(\d+)\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+skipped)?.*?[=]+",
        re.IGNORECASE
    )
    # Alternative pytest pattern for simpler output: "5 passed in 0.23s"
    PYTEST_SIMPLE_PATTERN = re.compile(r"(\d+)\s+passed(?:\s+in\s+[\d.]+s)?", re.IGNORECASE)

    def __init__(self) -> None:
        """Initialize the parser with empty accumulated state."""
        self._phases: Dict[str, Dict[str, Any]] = {}
        self._tests_passed: Optional[int] = None
        self._tests_failed: Optional[int] = None
        self._coverage: Optional[float] = None
        self._quality_gates_passed: Optional[bool] = None
        self._files_modified: set = set()
        self._files_created: set = set()
        self._test_files_created: set = set()
        self._arch_score: Optional[int] = None
        self._solid_score: Optional[int] = None
        self._dry_score: Optional[int] = None
        self._yagni_score: Optional[int] = None

    def _match_pattern(
        self,
        pattern: re.Pattern,
        text: str,
    ) -> Optional[re.Match]:
        """Helper to match a pattern against text.

        Args:
            pattern: Compiled regex pattern
            text: Text to search

        Returns:
            Match object if found, None otherwise
        """
        return pattern.search(text)

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file path is a test file.

        Detects Python test files using common naming conventions:
        - test_*.py (pytest default)
        - *_test.py (alternative convention)

        Args:
            file_path: Path to the file

        Returns:
            True if the file is a test file, False otherwise
        """
        if not file_path:
            return False
        # Extract the filename from the path
        name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        name = name.rsplit("\\", 1)[-1] if "\\" in name else name
        return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")

    @staticmethod
    def _is_valid_file_path(path: str) -> bool:
        """Validate that a string looks like a file path.

        Rejects strings that are clearly not file paths, such as natural language
        words (e.g. 'house') or glob wildcards (e.g. '**').  A valid path must
        contain at least one of: a path separator (/ or \\) or a dot (.).

        Args:
            path: String to validate

        Returns:
            True if the string looks like a file path, False otherwise
        """
        if not path or len(path) < 3:
            return False
        if path in ("*", "**", "***"):
            return False
        if path.startswith("*"):
            return False
        # Must contain a path separator or file extension indicator
        return "/" in path or "\\" in path or "." in path

    def _track_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
        """Track file operations from tool calls.

        Extracts file paths from Write and Edit tool invocations and adds them
        to the appropriate tracking set (created or modified). Also tracks
        test file creation separately.

        Args:
            tool_name: Name of the tool (e.g., "Write", "Edit")
            tool_args: Tool arguments dictionary containing file_path
        """
        # TASK-FIX-PIPELINE: Try multiple key names for file path (Fix 1)
        # Claude Code SDK tools may use different key names
        file_path = (
            tool_args.get("file_path")
            or tool_args.get("path")
            or tool_args.get("file")
            or tool_args.get("filePath")
        )
        if not file_path or not isinstance(file_path, str):
            logger.debug(
                f"Tool {tool_name} call has no recognizable file path key. "
                f"Available keys: {list(tool_args.keys())}"
            )
            return

        if tool_name == "Write":
            self._files_created.add(file_path)
            logger.debug(f"Tool call tracked - file created: {file_path}")
            # Track test files separately
            if self._is_test_file(file_path):
                self._test_files_created.add(file_path)
                logger.debug(f"Test file tracked: {file_path}")
        elif tool_name == "Edit":
            self._files_modified.add(file_path)
            logger.debug(f"Tool call tracked - file modified: {file_path}")

    def _parse_tool_invocations(self, message: str) -> None:
        """Parse tool invocations from message and track file operations.

        Detects Write and Edit tool calls in the message text and extracts
        file paths to track. Handles both XML-style tool invocations and
        tool result messages.

        Args:
            message: Stream message that may contain tool invocations
        """
        # Track XML-style tool invocations: <invoke name="Write">...<parameter name="file_path">
        tool_match = self._match_pattern(self.TOOL_INVOKE_PATTERN, message)
        if tool_match:
            tool_name = tool_match.group(1)
            file_path_match = self._match_pattern(self.TOOL_FILE_PATH_PATTERN, message)
            if file_path_match:
                file_path = file_path_match.group(1).strip()
                self._track_tool_call(tool_name, {"file_path": file_path})

        # Track tool result messages (e.g., "File created successfully at: /path")
        for result_match in self.TOOL_RESULT_CREATED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if file_path and self._is_valid_file_path(file_path):
                self._files_created.add(file_path)
                logger.debug(f"Tool result tracked - file created: {file_path}")

        for result_match in self.TOOL_RESULT_MODIFIED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if file_path and self._is_valid_file_path(file_path):
                self._files_modified.add(file_path)
                logger.debug(f"Tool result tracked - file modified: {file_path}")

    def parse_message(self, message: str) -> None:
        """Parse a single stream message and accumulate results.

        This method extracts quality gate information from a stream message
        and updates the internal state. It handles:
        - Phase markers and completion indicators
        - Test pass/fail counts
        - Coverage percentage
        - Quality gate status
        - File modification lists
        - Tool invocations (Write/Edit) for file tracking

        Args:
            message: Single message from the task-work SDK stream

        Note:
            Unrecognized patterns are logged at debug level but do not
            cause errors (graceful degradation).
        """
        if not message:
            return

        # Tool invocation tracking (Write/Edit operations)
        self._parse_tool_invocations(message)

        # Phase detection
        phase_match = self._match_pattern(self.PHASE_MARKER_PATTERN, message)
        if phase_match:
            phase_num = phase_match.group(1)
            phase_text = phase_match.group(2)[:100]  # Truncate long descriptions
            self._phases[f"phase_{phase_num}"] = {
                "detected": True,
                "text": phase_text,
                "completed": False,
            }
            logger.debug(f"Detected phase {phase_num}: {phase_text}")

        # Phase completion
        complete_match = self._match_pattern(self.PHASE_COMPLETE_PATTERN, message)
        if complete_match:
            phase_num = complete_match.group(1)
            phase_key = f"phase_{phase_num}"
            if phase_key in self._phases:
                self._phases[phase_key]["completed"] = True
            else:
                self._phases[phase_key] = {"detected": True, "completed": True}
            logger.debug(f"Phase {phase_num} completed")

        # Test results - try individual patterns first
        tests_passed_match = self._match_pattern(self.TESTS_PASSED_PATTERN, message)
        if tests_passed_match:
            self._tests_passed = int(tests_passed_match.group(1))
            logger.debug(f"Tests passed: {self._tests_passed}")

        tests_failed_match = self._match_pattern(self.TESTS_FAILED_PATTERN, message)
        if tests_failed_match:
            self._tests_failed = int(tests_failed_match.group(1))
            logger.debug(f"Tests failed: {self._tests_failed}")

        # Parse pytest summary output (e.g., "===== 5 passed, 2 failed in 0.23s =====")
        pytest_summary_match = self._match_pattern(self.PYTEST_SUMMARY_PATTERN, message)
        if pytest_summary_match:
            if pytest_summary_match.group(1):
                passed_count = int(pytest_summary_match.group(1))
                if self._tests_passed is None or passed_count > self._tests_passed:
                    self._tests_passed = passed_count
                    logger.debug(f"Pytest summary - tests passed: {self._tests_passed}")
            if pytest_summary_match.group(2):
                failed_count = int(pytest_summary_match.group(2))
                if self._tests_failed is None or failed_count > self._tests_failed:
                    self._tests_failed = failed_count
                    logger.debug(f"Pytest summary - tests failed: {self._tests_failed}")

        # Also try simpler pytest pattern (e.g., "5 passed in 0.23s")
        if self._tests_passed is None:
            simple_match = self._match_pattern(self.PYTEST_SIMPLE_PATTERN, message)
            if simple_match:
                self._tests_passed = int(simple_match.group(1))
                logger.debug(f"Pytest simple - tests passed: {self._tests_passed}")

        # Coverage
        coverage_match = self._match_pattern(self.COVERAGE_PATTERN, message)
        if coverage_match:
            self._coverage = float(coverage_match.group(1))
            logger.debug(f"Coverage: {self._coverage}%")

        # Quality gates
        if self._match_pattern(self.QUALITY_GATES_PASSED_PATTERN, message):
            self._quality_gates_passed = True
            logger.debug("Quality gates: PASSED")
        elif self._match_pattern(self.QUALITY_GATES_FAILED_PATTERN, message):
            self._quality_gates_passed = False
            logger.debug("Quality gates: FAILED")

        # File modifications (use sets to avoid duplicates)
        for file_match in self.FILES_MODIFIED_PATTERN.finditer(message):
            file_path = file_match.group(1)
            if self._is_valid_file_path(file_path):
                self._files_modified.add(file_path)
                logger.debug(f"File modified: {file_path}")

        for file_match in self.FILES_CREATED_PATTERN.finditer(message):
            file_path = file_match.group(1)
            if self._is_valid_file_path(file_path):
                self._files_created.add(file_path)
                logger.debug(f"File created: {file_path}")

        # Architectural review scores
        arch_score_match = self._match_pattern(self.ARCH_SCORE_PATTERN, message)
        if arch_score_match:
            try:
                self._arch_score = int(arch_score_match.group(1))
                logger.debug(f"Architectural review score: {self._arch_score}")
            except ValueError:
                logger.warning(f"Invalid arch score format: {arch_score_match.group(1)}")

        subscores_match = self._match_pattern(self.ARCH_SUBSCORES_PATTERN, message)
        if subscores_match:
            try:
                self._solid_score = int(subscores_match.group(1))
                self._dry_score = int(subscores_match.group(2))
                self._yagni_score = int(subscores_match.group(3))
                logger.debug(f"SOLID: {self._solid_score}, DRY: {self._dry_score}, YAGNI: {self._yagni_score}")
            except ValueError:
                logger.warning(f"Invalid subscore format in: {message}")

    def to_result(self) -> Dict[str, Any]:
        """Convert accumulated state to a result dictionary.

        Returns:
            Dictionary containing all parsed quality gate information:
            - phases: Dict of detected phases with completion status
            - tests_passed: Number of tests that passed (or None)
            - tests_failed: Number of tests that failed (or None)
            - coverage: Coverage percentage (or None)
            - quality_gates_passed: Boolean or None if not detected
            - files_modified: List of modified file paths
            - files_created: List of created file paths
            - test_files_created: List of test file paths created
            - architectural_review: Dict with score and optional SOLID/DRY/YAGNI
              subscores (or absent if no arch review score found)
        """
        result: Dict[str, Any] = {}

        if self._phases:
            result["phases"] = self._phases

        if self._tests_passed is not None:
            result["tests_passed"] = self._tests_passed

        if self._tests_failed is not None:
            result["tests_failed"] = self._tests_failed

        if self._coverage is not None:
            result["coverage"] = self._coverage

        if self._quality_gates_passed is not None:
            result["quality_gates_passed"] = self._quality_gates_passed

        if self._files_modified:
            result["files_modified"] = sorted(list(self._files_modified))

        if self._files_created:
            result["files_created"] = sorted(list(self._files_created))

        if self._test_files_created:
            result["test_files_created"] = sorted(list(self._test_files_created))

        if self._arch_score is not None:
            arch_review: Dict[str, Any] = {"score": self._arch_score}
            if self._solid_score is not None:
                arch_review["solid"] = self._solid_score
            if self._dry_score is not None:
                arch_review["dry"] = self._dry_score
            if self._yagni_score is not None:
                arch_review["yagni"] = self._yagni_score
            result["architectural_review"] = arch_review

        return result

    def reset(self) -> None:
        """Reset parser state for reuse.

        Clears all accumulated state, allowing the parser to be reused
        for a new stream.
        """
        self._phases = {}
        self._tests_passed = None
        self._tests_failed = None
        self._coverage = None
        self._quality_gates_passed = None
        self._files_modified = set()
        self._files_created = set()
        self._test_files_created = set()
        self._arch_score = None
        self._solid_score = None
        self._dry_score = None
        self._yagni_score = None


@dataclass
class AgentInvocationResult:
    """Result of an agent invocation.

    Attributes:
        task_id: Task identifier (e.g., "TASK-001")
        turn: Turn number (1-based)
        agent_type: "player" or "coach"
        success: True if invocation succeeded
        report: Parsed JSON from agent
        duration_seconds: Time taken for invocation
        error: Error message if failed
    """

    task_id: str
    turn: int
    agent_type: str  # "player" or "coach"
    success: bool
    report: Dict[str, Any]
    duration_seconds: float
    error: Optional[str] = None


class AgentInvoker:
    """Handles Claude Agents SDK invocation for Player and Coach agents.

    This class is the bridge between the orchestration layer and AI agents,
    managing agent sessions, context preparation, and response handling.

    Key Responsibilities:
    - Invoke Player and Coach agents via Claude Agents SDK
    - Manage fresh context per turn (no context pollution)
    - Handle SDK integration with appropriate permissions per agent type
    - Parse and validate agent responses (JSON reports)
    - Provide error handling and timeout management
    - Support async/await pattern for concurrent operations

    Example:
        >>> invoker = AgentInvoker(
        ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
        ...     max_turns_per_agent=30,
        ... )
        >>> result = await invoker.invoke_player(
        ...     task_id="TASK-001",
        ...     turn=1,
        ...     requirements="Implement OAuth2 authentication",
        ... )
        >>> assert result.success
        >>> assert result.report["tests_passed"]
    """

    def __init__(
        self,
        worktree_path: Path,
        max_turns_per_agent: int = 30,
        player_model: str = "claude-sonnet-4-5-20250929",
        coach_model: str = "claude-sonnet-4-5-20250929",
        sdk_timeout_seconds: int = DEFAULT_SDK_TIMEOUT,
        use_task_work_delegation: Optional[bool] = None,
        development_mode: str = "tdd",
    ):
        """Initialize AgentInvoker.

        Args:
            worktree_path: Path to the isolated git worktree
            max_turns_per_agent: Maximum turns per agent invocation (default: 30)
            player_model: Model to use for Player agent (default: claude-sonnet-4-5)
            coach_model: Model to use for Coach agent (default: claude-sonnet-4-5)
            sdk_timeout_seconds: Timeout for SDK invocations (default: 1200s)
            use_task_work_delegation: If True, delegate Player to task-work instead of
                direct SDK. Defaults to USE_TASK_WORK_DELEGATION env var.
            development_mode: Development mode for implementation (default: "tdd").
                Valid values: "standard", "tdd", "bdd"
        """
        self.worktree_path = Path(worktree_path)
        self.max_turns_per_agent = max_turns_per_agent
        self.player_model = player_model
        self.coach_model = coach_model
        self.sdk_timeout_seconds = sdk_timeout_seconds
        self._sdk_timeout_is_override = sdk_timeout_seconds != DEFAULT_SDK_TIMEOUT
        self.use_task_work_delegation = (
            use_task_work_delegation if use_task_work_delegation is not None
            else USE_TASK_WORK_DELEGATION
        )
        self.development_mode = development_mode

    async def invoke_player(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        mode: Optional[str] = None,
        max_turns: int = 5,
        documentation_level: str = "minimal",
        context: str = "",
    ) -> AgentInvocationResult:
        """Invoke Player agent via task-work delegation or Claude Agents SDK.

        When task-work delegation is enabled (use_task_work_delegation=True),
        the Player delegates to `guardkit task-work --implement-only` which
        leverages the full subagent infrastructure.

        When delegation is disabled (legacy mode), uses direct SDK invocation.

        The Player agent:
        - Has full file system access (Read, Write, Edit, Bash)
        - Works in isolated worktree
        - Implements code and writes tests
        - Creates JSON report at .guardkit/autobuild/{task_id}/player_turn_{turn}.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            requirements: Task requirements (from task markdown)
            feedback: Optional Coach feedback from previous turn (string or Coach decision dict)
            mode: Development mode ("standard", "tdd", or "bdd"), passed to task-work.
                If not provided, uses the instance's development_mode.
            max_turns: Maximum turns allowed for this orchestration (default: 5).
                Used to calculate approaching_limit flag for escape hatch pattern.
            documentation_level: Documentation level for file count constraint validation
                ("minimal", "standard", or "comprehensive"). Default: "minimal" for AutoBuild.
            context: Job-specific context from Graphiti (role constraints, quality gates,
                turn states). Included in Player prompt but kept separate from requirements.
                Default: "" (empty string, no context).

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            AgentInvocationError: If invocation fails
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        # TASK-ASF-008: Calculate dynamic SDK timeout based on task characteristics
        effective_timeout = self._calculate_sdk_timeout(task_id)
        original_timeout = self.sdk_timeout_seconds
        self.sdk_timeout_seconds = effective_timeout

        # Use instance development_mode if mode not provided
        effective_mode = mode if mode is not None else self.development_mode

        # Calculate if we're approaching the turn limit (escape hatch trigger)
        approaching_limit = turn >= max_turns - 1  # True when 2 or fewer turns remain

        try:
            # Write turn context for Player to read (includes approaching_limit)
            self._write_turn_context(task_id, turn, max_turns, approaching_limit)

            # Write Coach feedback for task-work to read (if present and not turn 1)
            if feedback and turn > 1:
                self._write_coach_feedback(task_id, turn, feedback)

            # Route based on implementation_mode from task frontmatter
            # Direct mode tasks bypass task-work delegation (no plan required)
            impl_mode = self._get_implementation_mode(task_id)
            if impl_mode == "direct":
                logger.info(
                    f"Routing to direct Player path for {task_id} (implementation_mode=direct)"
                )
                return await self._invoke_player_direct(
                    task_id=task_id,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=max_turns,
                    context=context,
                )

            # Choose invocation method based on feature flag (task-work or legacy modes)
            if self.use_task_work_delegation:
                logger.info(
                    f"Invoking Player via task-work delegation for {task_id} (turn {turn})"
                )

                # Ensure task is in design_approved state before delegation
                # This bridges AutoBuild state with task-work --implement-only requirements
                self._ensure_design_approved_state(task_id)

                result = await self._invoke_task_work_implement(
                    task_id=task_id,
                    mode=effective_mode,
                    documentation_level=documentation_level,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=max_turns,
                    context=context,
                )

                duration = time.time() - start_time

                if result.success:
                    # Create Player report from task-work results
                    # AgentInvoker._invoke_task_work_implement() writes task_work_results.json
                    # after parsing task-work output. This method transforms it to
                    # player_turn_{turn}.json format expected by the orchestrator.
                    self._create_player_report_from_task_work(task_id, turn, result)

                    # Load the Player report from file (now exists)
                    report = self._load_agent_report(task_id, turn, "player")
                    self._validate_player_report(report)

                    return AgentInvocationResult(
                        task_id=task_id,
                        turn=turn,
                        agent_type="player",
                        success=True,
                        report=report,
                        duration_seconds=duration,
                    )
                else:
                    return AgentInvocationResult(
                        task_id=task_id,
                        turn=turn,
                        agent_type="player",
                        success=False,
                        report={},
                        duration_seconds=duration,
                        error=result.error,
                    )
            else:
                # Legacy direct SDK invocation
                logger.info(
                    f"Invoking Player via direct SDK for {task_id} (turn {turn})"
                )
                # Build prompt for Player
                prompt = self._build_player_prompt(
                    task_id, turn, requirements, feedback, context=context
                )

                # Invoke SDK with Player permissions (Read, Write, Edit, Bash)
                await self._invoke_with_role(
                    prompt=prompt,
                    agent_type="player",
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                    permission_mode="acceptEdits",
                    model=self.player_model,
                )

                # Load and validate Player report
                report = self._load_agent_report(task_id, turn, "player")
                self._validate_player_report(report)

                duration = time.time() - start_time

                return AgentInvocationResult(
                    task_id=task_id,
                    turn=turn,
                    agent_type="player",
                    success=True,
                    report=report,
                    duration_seconds=duration,
                )

        except (PlayerReportNotFoundError, PlayerReportInvalidError) as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=str(e),
            )
        except SDKTimeoutError as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
            )
        except Exception as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"Unexpected error: {str(e)}",
            )
        finally:
            # TASK-ASF-008: Restore original timeout after invocation
            self.sdk_timeout_seconds = original_timeout

    async def invoke_coach(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
    ) -> AgentInvocationResult:
        """Invoke Coach agent via Claude Agents SDK with honesty verification.

        The Coach agent:
        - Has read-only access (Read, Bash only)
        - Works in same worktree as Player
        - Validates implementation independently
        - Receives honesty verification context for Player claims
        - Creates JSON decision at .guardkit/autobuild/{task_id}/coach_turn_{turn}.json

        Args:
            task_id: Task identifier
            turn: Current turn number
            requirements: Original task requirements
            player_report: Player's report from current turn

        Returns:
            AgentInvocationResult with Coach's decision

        Raises:
            AgentInvocationError: If invocation fails
            CoachDecisionNotFoundError: If Coach doesn't create decision
            CoachDecisionInvalidError: If decision JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        try:
            # Verify Player claims before invoking Coach
            honesty_verification = self._verify_player_claims(player_report)

            # Build prompt for Coach with verification context
            prompt = self._build_coach_prompt(
                task_id, turn, requirements, player_report, honesty_verification
            )

            # Invoke SDK with Coach permissions (Read, Bash only - no Write/Edit)
            # Coach uses bypassPermissions since it's read-only anyway
            await self._invoke_with_role(
                prompt=prompt,
                agent_type="coach",
                allowed_tools=["Read", "Bash", "Grep", "Glob"],
                permission_mode="bypassPermissions",
                model=self.coach_model,
            )

            # Load and validate Coach decision
            decision = self._load_agent_report(task_id, turn, "coach")
            self._validate_coach_decision(decision)

            # Add honesty verification to decision for tracking
            decision["honesty_verification"] = {
                "verified": honesty_verification.verified,
                "honesty_score": honesty_verification.honesty_score,
                "discrepancy_count": len(honesty_verification.discrepancies),
            }

            duration = time.time() - start_time

            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=True,
                report=decision,
                duration_seconds=duration,
            )

        except (CoachDecisionNotFoundError, CoachDecisionInvalidError) as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=duration,
                error=str(e),
            )
        except SDKTimeoutError as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
            )
        except Exception as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"Unexpected error: {str(e)}",
            )

    def _build_player_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str],
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
        context: str = "",
        design_context: Optional["DesignContext"] = None,
    ) -> str:
        """Build prompt for Player agent invocation with acceptance criteria.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Task requirements
            feedback: Optional feedback from previous Coach turn
            acceptance_criteria: Optional list of acceptance criteria with id and text
            context: Job-specific context from Graphiti (role constraints, quality gates,
                turn states). Included before requirements for prompt context.
            design_context: Optional design context for UI implementation tasks

        Returns:
            Formatted prompt string for Player agent
        """
        feedback_section = ""
        if feedback and turn > 1:
            feedback_section = f"""
## Coach Feedback from Turn {turn - 1}

{feedback}

Please address all feedback points in this turn.
"""

        # Build context section if provided (Graphiti job-specific context)
        context_section = ""
        if context:
            context_section = f"""
## Job-Specific Context

{context}
"""

        # Build design context section if provided
        design_section = ""
        if design_context:
            design_section = f"""
## Design Context

**Source**: {design_context.source}

### Elements in Design
{self._format_design_elements(design_context.elements)}

### Design Tokens
{self._format_design_tokens(design_context.tokens)}

### Design Boundaries (Prohibition Checklist)
{self._format_design_constraints(design_context.constraints)}

### Instructions
- Generate components matching the design EXACTLY
- Apply design tokens with no approximation
- DO NOT add anything not shown in the design
- Delegate to the appropriate UI specialist
"""

        # Build acceptance criteria section if provided
        criteria_section = ""
        if acceptance_criteria:
            criteria_lines = ["## Acceptance Criteria", ""]
            criteria_lines.append("You MUST create a completion_promise for each criterion:")
            criteria_lines.append("")
            for criterion in acceptance_criteria:
                criteria_lines.append(f"- **{criterion['id']}**: {criterion['text']}")
            criteria_section = "\n".join(criteria_lines) + "\n"

        # Build completion promises example
        promises_example = ""
        if acceptance_criteria:
            example_promises = []
            for criterion in acceptance_criteria[:2]:  # Show first 2 as examples
                example_promises.append(f'''    {{
      "criterion_id": "{criterion['id']}",
      "criterion_text": "{criterion['text'][:50]}...",
      "status": "complete",
      "evidence": "Description of what you did for this criterion",
      "test_file": "tests/test_relevant.py",
      "implementation_files": ["src/file.py"]
    }}''')
            promises_example = f'''
  "completion_promises": [
{",".join(example_promises)}
  ],'''

        prompt = f"""You are the Player agent. Implement the following task.

Task ID: {task_id}
Turn: {turn}
{context_section}{design_section}
## Requirements

{requirements}
{criteria_section}{feedback_section}

## Your Responsibilities

1. Implement the code to satisfy the requirements
2. Write comprehensive tests
3. Run the tests and verify they pass
4. Create your report with completion promises for each acceptance criterion

## Report Format

After implementing, write your report to:
.guardkit/autobuild/{task_id}/player_turn_{turn}.json

Your report MUST be valid JSON with these fields:
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "files_modified": ["list", "of", "files"],
  "files_created": ["list", "of", "new", "files"],
  "tests_written": ["list", "of", "test", "files"],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "Brief summary of test results",
  "implementation_notes": "What you implemented and why",
  "concerns": ["any", "concerns", "or", "blockers"],
  "requirements_addressed": ["requirements", "completed"],
  "requirements_remaining": ["requirements", "still", "pending"],{promises_example}
}}

**IMPORTANT**: For each acceptance criterion, create a completion_promise with:
- criterion_id: The ID (e.g., "AC-001")
- criterion_text: The full criterion text
- status: "complete" or "incomplete"
- evidence: What you did to satisfy this criterion
- test_file: Path to test file validating this criterion (if applicable)
- implementation_files: List of files modified/created for this criterion

Follow the report format specified in your agent definition.
"""
        return prompt

    def _format_design_elements(self, elements: List[Dict[str, Any]]) -> str:
        """Format design elements for prompt.

        Args:
            elements: List of design element dictionaries

        Returns:
            Formatted markdown string of design elements
        """
        if not elements:
            return "No elements specified"
        lines = []
        for elem in elements:
            name = elem.get("name", "Unknown")
            elem_type = elem.get("type", "component")
            props = elem.get("props", [])
            variants = elem.get("variants", [])
            line = f"- **{name}** ({elem_type})"
            if props:
                line += f"\n  Props: {', '.join(props)}"
            if variants:
                line += f"\n  Variants: {', '.join(variants)}"
            lines.append(line)
        return "\n".join(lines)

    def _format_design_tokens(self, tokens: Dict[str, Any]) -> str:
        """Format design tokens for prompt.

        Args:
            tokens: Dictionary of design tokens

        Returns:
            Formatted JSON string of design tokens
        """
        if not tokens:
            return "No tokens specified"
        return json.dumps(tokens, indent=2)

    def _format_design_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format design constraints/prohibition checklist.

        Args:
            constraints: Dictionary of design constraints

        Returns:
            Formatted markdown string of constraints
        """
        if not constraints:
            return "No specific constraints"
        lines = ["The following constraints MUST be followed:"]
        for key, value in constraints.items():
            if value:
                formatted_key = key.replace("_", " ").title()
                lines.append(f"- ❌ {formatted_key}")
        return "\n".join(lines)

    def _build_coach_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        honesty_verification: Optional[HonestyVerification] = None,
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
        design_context: Optional["DesignContext"] = None,
    ) -> str:
        """Build prompt for Coach agent invocation with promise verification.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Original task requirements
            player_report: Player's report from current turn
            honesty_verification: Optional verification results for Player claims
            acceptance_criteria: Optional list of acceptance criteria with id and text
            design_context: Optional design context for visual verification

        Returns:
            Formatted prompt string for Coach agent
        """
        # Build honesty verification section
        honesty_section = ""
        if honesty_verification:
            honesty_section = f"""
## Honesty Verification (Pre-Validated)

{format_verification_context(honesty_verification)}

{"⚠️ CRITICAL DISCREPANCIES DETECTED - Factor this into your decision!" if honesty_verification.discrepancies else "✓ Player claims verified."}
"""

        # Build acceptance criteria section for verification
        criteria_section = ""
        if acceptance_criteria:
            criteria_lines = ["## Acceptance Criteria to Verify", ""]
            criteria_lines.append("Verify EACH criterion and create a criteria_verification entry:")
            criteria_lines.append("")
            for criterion in acceptance_criteria:
                criteria_lines.append(f"- **{criterion['id']}**: {criterion['text']}")
            criteria_section = "\n".join(criteria_lines) + "\n"

        # Build criteria verification example
        verification_example = ""
        if acceptance_criteria:
            example_verifications = []
            for criterion in acceptance_criteria[:2]:  # Show first 2 as examples
                example_verifications.append(f'''    {{
      "criterion_id": "{criterion['id']}",
      "result": "verified",
      "notes": "Your reasoning for verification or rejection"
    }}''')
            verification_example = f'''
  "criteria_verification": [
{",".join(example_verifications)}
  ],'''

        # Build visual verification section if design context provided
        visual_verification_section = ""
        if design_context:
            visual_verification_section = f"""
## Visual Verification (Design Mode)

In addition to standard code review:
1. Render the generated component in a browser
2. Capture a screenshot
3. Compare against design reference using SSIM
4. Check prohibition checklist compliance
5. Report: visual fidelity score + any constraint violations

**Visual Reference**: {design_context.visual_reference or "Not available"}

Quality Gates:
- Visual fidelity: >= 95% SSIM match
- Constraint violations: Zero tolerance
- Design tokens: 100% applied (exact match)
"""

        prompt = f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

## Original Requirements

{requirements}
{criteria_section}
## Player's Report

{json.dumps(player_report, indent=2)}
{honesty_section}{visual_verification_section}
## Your Responsibilities

1. Independently verify the Player's claims
2. Run the tests yourself (don't trust Player's report)
3. Verify EACH acceptance criterion systematically
4. {"CONSIDER HONESTY DISCREPANCIES in your decision" if honesty_verification and honesty_verification.discrepancies else "Either APPROVE or provide specific FEEDBACK"}

## Decision Format

Write your decision to:
.guardkit/autobuild/{task_id}/coach_turn_{turn}.json

Your decision MUST be valid JSON with these fields:

For APPROVAL:
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "approve",
  "validation_results": {{
    "requirements_met": ["list", "of", "verified", "requirements"],
    "tests_run": true,
    "tests_passed": true,
    "test_command": "command you ran",
    "test_output_summary": "summary of test results",
    "code_quality": "assessment",
    "edge_cases_covered": ["list", "of", "edge", "cases"]
  }},{verification_example}
  "rationale": "Why you approved"
}}

For FEEDBACK:
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "feedback",
  "issues": [
    {{
      "type": "missing_requirement" | "test_failure" | "code_quality" | "edge_case",
      "severity": "critical" | "major" | "minor",
      "description": "Specific issue with file paths and line numbers",
      "requirement": "Which requirement is affected",
      "suggestion": "How to fix it"
    }}
  ],{verification_example}
  "rationale": "Why you're providing feedback"
}}

**IMPORTANT**: For each acceptance criterion, create a criteria_verification with:
- criterion_id: The ID (e.g., "AC-001") matching the Player's completion_promise
- result: "verified" if criterion is satisfied, "rejected" if not
- notes: Your reasoning - what you checked and found

Follow the decision format specified in your agent definition.
"""
        return prompt

    def _verify_player_claims(
        self,
        player_report: Dict[str, Any],
    ) -> HonestyVerification:
        """Verify Player's self-reported claims against reality.

        This method uses CoachVerifier to cross-reference Player claims:
        - Test results vs actual test execution
        - Claimed files vs filesystem state
        - Test counts vs parsed output

        Args:
            player_report: Player's report from current turn

        Returns:
            HonestyVerification with verification results and honesty score

        Note:
            Returns a default verification result if verification fails,
            allowing the workflow to continue while logging the issue.
        """
        try:
            verifier = CoachVerifier(self.worktree_path)
            verification = verifier.verify_player_report(player_report)

            if verification.discrepancies:
                logger.warning(
                    f"Player honesty verification found {len(verification.discrepancies)} "
                    f"discrepancies (score: {verification.honesty_score:.2f})"
                )
                for disc in verification.discrepancies:
                    logger.warning(
                        f"  [{disc.severity}] {disc.claim_type}: "
                        f"claimed {disc.player_claim}, actual {disc.actual_value}"
                    )
            else:
                logger.info(
                    f"Player claims verified successfully (score: {verification.honesty_score:.2f})"
                )

            return verification

        except Exception as e:
            logger.warning(f"Failed to verify Player claims: {e}")
            # Return default verification (assume honest) to not block workflow
            return HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0)

    async def _invoke_with_role(
        self,
        prompt: str,
        agent_type: Literal["player", "coach"],
        allowed_tools: list[str],
        permission_mode: Literal["acceptEdits", "bypassPermissions"],
        model: str,
    ) -> None:
        """Low-level SDK invocation with role-based permissions.

        This method handles the actual Claude Agent SDK invocation with
        appropriate permissions and timeout handling.

        Args:
            prompt: Formatted prompt for agent
            agent_type: "player" or "coach"
            allowed_tools: List of allowed SDK tools
            permission_mode: "acceptEdits" (Player) or "bypassPermissions" (Coach)
            model: Model identifier

        Raises:
            AgentInvocationError: If SDK invocation fails
            SDKTimeoutError: If invocation exceeds timeout
        """
        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                CLINotFoundError,
                ProcessError,
                CLIJSONDecodeError,
                AssistantMessage,
            )
        except ImportError as e:
            import sys
            diagnosis = (
                f"Claude Agent SDK import failed.\n"
                f"  Error: {e}\n"
                f"  Python: {sys.executable}\n"
                f"  sys.path (first 3): {sys.path[:3]}\n\n"
                f"To fix:\n"
                f"  pip install claude-agent-sdk\n"
                f"  # OR for full autobuild support:\n"
                f"  pip install guardkit-py[autobuild]"
            )
            raise AgentInvocationError(diagnosis) from e

        from guardkit.orchestrator.sdk_utils import check_assistant_message_error

        try:
            options = ClaudeAgentOptions(
                cwd=str(self.worktree_path),
                allowed_tools=allowed_tools,
                permission_mode=permission_mode,
                # TASK-REV-C4D7: Direct mode also needs ~50 internal turns
                # (same as task-work delegation path fixed in TASK-REV-BB80)
                max_turns=TASK_WORK_SDK_MAX_TURNS,
                model=model,
                setting_sources=["project"],  # Load CLAUDE.md from worktree
            )

            # Extract task_id from prompt for heartbeat logging
            task_id_match = re.search(r"TASK-[A-Z0-9-]+", prompt)
            heartbeat_task_id = task_id_match.group(0) if task_id_match else "unknown"

            async with asyncio.timeout(self.sdk_timeout_seconds):
                async with async_heartbeat(
                    heartbeat_task_id,
                    f"{agent_type.capitalize()} invocation",
                ):
                    async for message in query(prompt=prompt, options=options):
                        err = check_assistant_message_error(message)
                        if err:
                            raise AgentInvocationError(
                                f"Agent {agent_type} received API error: {err}"
                            )
                        # Progress tracking handled by ProgressDisplay
                        # Agent writes report to JSON file, which is loaded after
                        # the query completes via _load_agent_report()
                        pass

        except asyncio.TimeoutError:
            raise SDKTimeoutError(
                f"Agent invocation exceeded {self.sdk_timeout_seconds}s timeout"
            )
        except CLINotFoundError as e:
            raise AgentInvocationError(
                "Claude Code CLI not installed. "
                "Run: npm install -g @anthropic-ai/claude-code"
            ) from e
        except ProcessError as e:
            raise AgentInvocationError(
                f"SDK process failed (exit {e.exit_code}): {e.stderr}"
            ) from e
        except CLIJSONDecodeError as e:
            raise AgentInvocationError(
                f"Failed to parse SDK response: {e}"
            ) from e
        except Exception as e:
            raise AgentInvocationError(
                f"SDK invocation failed for {agent_type}: {str(e)}"
            ) from e

    def _create_player_report_from_task_work(
        self,
        task_id: str,
        turn: int,
        task_work_result: "TaskWorkResult",
    ) -> None:
        """Create Player report from task-work results.

        When Player delegates to task-work --implement-only, task-work creates
        task_work_results.json but the orchestrator expects player_turn_{turn}.json.
        This method bridges the gap by reading task_work_results.json and creating
        the expected Player report.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Turn number (1-based)
            task_work_result: Result from task-work execution

        Notes:
            - Reads task_work_results.json from .guardkit/autobuild/{task_id}/
            - Transforms to PlayerReport schema (see PLAYER_REPORT_SCHEMA)
            - Writes player_turn_{turn}.json to same directory
            - Detects git changes if not in task_work_results.json
        """
        # Use centralized paths
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        task_work_results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
        player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, self.worktree_path)

        # Initialize report with defaults
        report: Dict[str, Any] = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": [],
            "files_created": [],
            "tests_written": [],
            "tests_run": False,
            "tests_passed": False,
            "test_output_summary": "",
            "implementation_notes": "Implementation via task-work delegation",
            "concerns": [],
            "requirements_addressed": [],
            "requirements_remaining": [],
        }

        # Try to read task_work_results.json for richer data
        if task_work_results_path.exists():
            try:
                with open(task_work_results_path, "r") as f:
                    task_work_data = json.load(f)

                # Map task-work fields to Player report fields
                report["files_modified"] = task_work_data.get("files_modified", [])
                report["files_created"] = task_work_data.get("files_created", [])

                # Extract test info (conditional on tests_info existing)
                tests_info = task_work_data.get("tests_info", {})
                if tests_info:
                    report["tests_run"] = tests_info.get("tests_run", False)
                    report["tests_passed"] = tests_info.get("tests_passed", False)
                    report["test_output_summary"] = tests_info.get(
                        "output_summary", ""
                    )

                # ALWAYS populate tests_written from file lists (unconditional)
                all_files = report.get("files_created", []) + report.get("files_modified", [])
                tests_from_files = [
                    f for f in all_files
                    if "test_" in Path(f).name.lower() or Path(f).name.lower().endswith("_test.py")
                ]

                # Also extract test files from completion_promises.test_file
                # This catches pre-existing test files (e.g., from scaffolding
                # tasks) that the Player references but didn't create/modify.
                tests_from_promises = set()
                for promise in task_work_data.get("completion_promises", []):
                    test_file = promise.get("test_file")
                    if test_file and isinstance(test_file, str):
                        p = Path(test_file)
                        if (p.name.startswith("test_") and p.name.endswith(".py")) or p.name.endswith("_test.py"):
                            tests_from_promises.add(test_file)

                report["tests_written"] = sorted(
                    list(set(tests_from_files) | tests_from_promises)
                )

                # Extract implementation notes from plan audit if available
                plan_audit = task_work_data.get("plan_audit", {})
                if plan_audit:
                    report["implementation_notes"] = (
                        f"Implementation via task-work delegation. "
                        f"Files planned: {plan_audit.get('files_planned', 0)}, "
                        f"Files actual: {plan_audit.get('files_actual', 0)}"
                    )

                # Propagate completion_promises into player report (TASK-ACR-001)
                completion_promises = task_work_data.get("completion_promises", [])
                if completion_promises:
                    report["completion_promises"] = completion_promises

                logger.info(
                    f"Created Player report from task_work_results.json for {task_id} turn {turn}"
                )

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to read task_work_results.json, using defaults: {e}"
                )

        # ALWAYS verify/enrich with git detection (TASK-DMRF-003)
        # This ensures we capture changes even if task_work_results.json has empty arrays
        try:
            git_changes = self._detect_git_changes()
            if git_changes:
                original_modified = set(report["files_modified"])
                original_created = set(report["files_created"])

                git_modified = set(git_changes.get("modified", []))
                git_created = set(git_changes.get("created", []))

                # Merge using union (preserves existing + adds git-detected)
                report["files_modified"] = sorted(list(original_modified | git_modified))
                report["files_created"] = sorted(list(original_created | git_created))

                # TASK-FIX-PIPELINE: Filter invalid entries (Fix 4)
                # TASK-FIX-PV01: Use centralised _is_valid_file_path which also
                # rejects natural language words (e.g. 'house') that lack '/' or '.'.
                report["files_modified"] = sorted(
                    [p for p in report["files_modified"] if TaskWorkStreamParser._is_valid_file_path(p)]
                )
                report["files_created"] = sorted(
                    [p for p in report["files_created"] if TaskWorkStreamParser._is_valid_file_path(p)]
                )

                # Log when git detection adds files not in original report
                new_modified = git_modified - original_modified
                new_created = git_created - original_created
                if new_modified or new_created:
                    logger.info(
                        f"Git detection added: {len(new_modified)} modified, "
                        f"{len(new_created)} created files for {task_id}"
                    )

                # Update implementation notes if we only have git-detected files
                if not task_work_results_path.exists():
                    report["implementation_notes"] = (
                        "Implementation via task-work delegation (git-detected changes)"
                    )
        except Exception as e:
            logger.warning(f"Failed to detect git changes: {e}")

        # Also use task_work_result.output if available
        if task_work_result.output:
            output = task_work_result.output
            # Merge with output data if present (union with git-enriched)
            if "files_modified" in output:
                existing = set(report.get("files_modified", []))
                report["files_modified"] = sorted(list(existing | set(output["files_modified"])))
            if "files_created" in output:
                existing = set(report.get("files_created", []))
                report["files_created"] = sorted(list(existing | set(output["files_created"])))
            if "tests_passed" in output:
                tests_passed_value = output["tests_passed"]
                # Convert count to boolean for PLAYER_REPORT_SCHEMA compliance
                # Parser captures tests_passed as int (count), schema expects bool
                # Note: Check for bool FIRST since bool is a subclass of int in Python
                if isinstance(tests_passed_value, bool):
                    report["tests_passed"] = tests_passed_value
                elif isinstance(tests_passed_value, int):
                    report["tests_passed"] = tests_passed_value > 0
                    report["tests_passed_count"] = tests_passed_value  # Preserve count
                else:
                    report["tests_passed"] = bool(tests_passed_value)
                report["tests_run"] = True

        # TASK-FIX-PIPELINE: Recover agent-written completion_promises (Fix 2)
        # The execution protocol instructs the SDK agent to write player_turn_N.json
        # directly. If the agent did so before this method runs, preserve the
        # agent's completion_promises and requirements_addressed.
        if not report.get("completion_promises") and player_report_path.exists():
            try:
                with open(player_report_path, "r") as f:
                    agent_written = json.load(f)

                # Recover completion_promises from agent-written report
                agent_promises = agent_written.get("completion_promises", [])
                if agent_promises:
                    report["completion_promises"] = agent_promises
                    logger.info(
                        f"Recovered {len(agent_promises)} completion_promises "
                        f"from agent-written player report for {task_id}"
                    )

                # Recover requirements_addressed if ours is empty
                if not report["requirements_addressed"]:
                    agent_reqs = agent_written.get("requirements_addressed", [])
                    if agent_reqs:
                        report["requirements_addressed"] = agent_reqs
                        logger.info(
                            f"Recovered {len(agent_reqs)} requirements_addressed "
                            f"from agent-written player report for {task_id}"
                        )

                # Recover requirements_remaining if ours is empty
                if not report["requirements_remaining"]:
                    agent_remaining = agent_written.get("requirements_remaining", [])
                    if agent_remaining:
                        report["requirements_remaining"] = agent_remaining

            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"No agent-written player report to recover from: {e}")

        # TASK-FIX-PIPELINE: File-existence verification fallback (Fix 5)
        # When no completion_promises exist after Fix 2 recovery, generate
        # synthetic promises by checking files against acceptance criteria.
        if not report.get("completion_promises"):
            # Load task metadata to get acceptance_criteria
            task_file = self._find_task_file(task_id)
            if task_file is None:
                logger.warning(
                    f"Fix 5: _find_task_file returned None for {task_id} — "
                    f"completion_promises fallback unavailable. "
                    f"Check that task directories are correctly configured."
                )
            if task_file:
                task_meta = self._load_task_metadata(task_file)
                acceptance_criteria = task_meta.get("acceptance_criteria", [])
                if acceptance_criteria:
                    synthetic_promises = self._generate_file_existence_promises(
                        task_id=task_id,
                        files_created=report.get("files_created", []),
                        files_modified=report.get("files_modified", []),
                        acceptance_criteria=acceptance_criteria,
                        worktree_path=self.worktree_path,
                    )
                    if synthetic_promises:
                        report["completion_promises"] = synthetic_promises
                        logger.info(
                            f"Generated {len(synthetic_promises)} file-existence promises "
                            f"for {task_id} (agent did not produce promises)"
                        )

        # Write Player report
        with open(player_report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Written Player report to {player_report_path}")

        # TASK-FIX-PIPELINE: Update task_work_results.json with enriched data (Fix 3)
        # Coach reads task_work_results.json for quality gate evaluation.
        # It must reflect the enriched file lists and any recovered promises.
        if task_work_results_path.exists():
            try:
                with open(task_work_results_path, "r") as f:
                    task_work_data = json.load(f)

                updated = False

                # Update file lists if enriched data is richer
                if len(report.get("files_modified", [])) > len(task_work_data.get("files_modified", [])):
                    task_work_data["files_modified"] = report["files_modified"]
                    updated = True

                if len(report.get("files_created", [])) > len(task_work_data.get("files_created", [])):
                    task_work_data["files_created"] = report["files_created"]
                    updated = True

                # Propagate completion_promises if not already present
                if report.get("completion_promises") and not task_work_data.get("completion_promises"):
                    task_work_data["completion_promises"] = report["completion_promises"]
                    updated = True

                # Update tests_written from enriched report
                if len(report.get("tests_written", [])) > len(task_work_data.get("tests_written", [])):
                    task_work_data["tests_written"] = report["tests_written"]
                    updated = True

                if updated:
                    with open(task_work_results_path, "w") as f:
                        json.dump(task_work_data, f, indent=2)
                    logger.info(
                        f"Updated task_work_results.json with enriched data for {task_id}"
                    )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to update task_work_results.json: {e}")

    def _detect_git_changes(self) -> Dict[str, list]:
        """Detect git changes in worktree.

        Returns:
            Dict with "modified" and "created" file lists
        """
        import subprocess

        result = {"modified": [], "created": []}

        try:
            # Get modified files (tracked)
            proc = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0:
                result["modified"] = [
                    f.strip() for f in proc.stdout.strip().split("\n") if f.strip()
                ]

            # Get untracked files (new)
            proc = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0:
                result["created"] = [
                    f.strip() for f in proc.stdout.strip().split("\n") if f.strip()
                ]

        except subprocess.TimeoutExpired:
            logger.warning("Git command timed out")
        except Exception as e:
            logger.warning(f"Git change detection failed: {e}")

        return result

    def _create_synthetic_direct_mode_report(
        self,
        task_id: str,
        turn: int,
        acceptance_criteria: Optional[List[str]] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create synthetic Player report from git changes for direct mode.

        When SDK invocation completes but doesn't produce player_turn_N.json,
        this method generates a valid report by detecting filesystem changes.
        This prevents unnecessary retries and state recovery.

        Delegates core report construction to
        ``guardkit.orchestrator.synthetic_report.build_synthetic_report``
        (TASK-FIX-D1A3). When ``task_type == "scaffolding"`` and
        ``acceptance_criteria`` is provided, file-existence promises are
        generated automatically.

        Args:
            task_id: Task identifier
            turn: Turn number (1-based)
            acceptance_criteria: Optional acceptance criteria for promise generation
            task_type: Optional task type (e.g. "scaffolding") for promise routing

        Returns:
            Dict conforming to PLAYER_REPORT_SCHEMA with ``_synthetic: True``
        """
        from guardkit.orchestrator.synthetic_report import build_synthetic_report

        files_modified: List[str] = []
        files_created: List[str] = []
        tests_written: List[str] = []
        implementation_notes = "Direct mode SDK invocation completed (synthetic report)"

        try:
            git_changes = self._detect_git_changes()
            if git_changes:
                files_modified = sorted(git_changes.get("modified", []))
                files_created = sorted(git_changes.get("created", []))

                # Identify test files from all changes
                all_files = files_modified + files_created
                tests_written = sorted([
                    f for f in all_files
                    if "test_" in f.lower() or f.lower().endswith("_test.py")
                    or "/tests/" in f or f.startswith("tests/")
                ])

                if all_files:
                    implementation_notes = (
                        f"Direct mode SDK invocation completed "
                        f"(git-detected: {len(files_modified)} modified, "
                        f"{len(files_created)} created)"
                    )
        except Exception as e:
            logger.warning(f"Git change detection failed for synthetic report: {e}")

        return build_synthetic_report(
            task_id=task_id,
            turn=turn,
            files_modified=files_modified,
            files_created=files_created,
            tests_written=tests_written,
            tests_passed=False,
            test_count=0,
            implementation_notes=implementation_notes,
            concerns=[],
            acceptance_criteria=acceptance_criteria,
            task_type=task_type,
        )

    def _find_task_file(self, task_id: str) -> Optional[Path]:
        """Find task file in standard task directories.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Path to task file if found, None otherwise
        """
        # Standard task directories
        task_dirs = [
            self.worktree_path / "tasks" / "backlog",
            self.worktree_path / "tasks" / "design_approved",
            self.worktree_path / "tasks" / "in_progress",
            self.worktree_path / "tasks" / "in_review",
            self.worktree_path / "tasks" / "completed",
            self.worktree_path / "tasks" / "blocked",
        ]

        for task_dir in task_dirs:
            if not task_dir.exists():
                continue
            # Look for task file matching task_id
            for task_file in task_dir.rglob(f"{task_id}*.md"):
                return task_file

        return None

    def _load_task_metadata(self, task_file: Path) -> Dict[str, Any]:
        """Load task metadata from YAML frontmatter.

        Args:
            task_file: Path to task file

        Returns:
            Dict with task metadata (may be empty if no frontmatter)
        """
        import re

        try:
            content = task_file.read_text()
            # Parse YAML frontmatter between --- markers
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                import yaml
                frontmatter = frontmatter_match.group(1)
                return yaml.safe_load(frontmatter) or {}
        except Exception as e:
            logger.debug(f"Failed to load task metadata from {task_file}: {e}")

        return {}

    def _generate_file_existence_promises(
        self,
        task_id: str,
        files_created: list,
        files_modified: list,
        acceptance_criteria: list,
        worktree_path: Path,
    ) -> list:
        """Generate completion promises from file existence checks.

        Thin wrapper around the shared
        ``guardkit.orchestrator.synthetic_report.generate_file_existence_promises``
        function (TASK-FIX-D1A3). The shared function now handles
        ``evidence_type``, directory reference checks, and all regex passes.

        Args:
            task_id: Task identifier
            files_created: Files created by Player
            files_modified: Files modified by Player
            acceptance_criteria: List of AC text strings
            worktree_path: Path to worktree for disk checks

        Returns:
            List of promise dicts with criterion_id, status, evidence, evidence_type
        """
        from guardkit.orchestrator.synthetic_report import (
            generate_file_existence_promises,
        )

        return generate_file_existence_promises(
            files_created=files_created,
            files_modified=files_modified,
            acceptance_criteria=acceptance_criteria,
            worktree_path=worktree_path,
        )

    def _load_agent_report(
        self,
        task_id: str,
        turn: int,
        agent_type: Literal["player", "coach"],
    ) -> Dict[str, Any]:
        """Load and validate agent report JSON.

        Args:
            task_id: Task identifier
            turn: Turn number
            agent_type: "player" or "coach"

        Returns:
            Parsed JSON report

        Raises:
            PlayerReportNotFoundError: If Player report doesn't exist
            CoachDecisionNotFoundError: If Coach decision doesn't exist
            PlayerReportInvalidError: If Player JSON is malformed
            CoachDecisionInvalidError: If Coach JSON is malformed
        """
        report_path = self._get_report_path(task_id, turn, agent_type)

        # Check if report exists
        if not report_path.exists():
            if agent_type == "player":
                raise PlayerReportNotFoundError(
                    f"Player report not found: {report_path}"
                )
            else:
                raise CoachDecisionNotFoundError(
                    f"Coach decision not found: {report_path}"
                )

        # Load and parse JSON
        try:
            with open(report_path) as f:
                report = json.load(f)
        except json.JSONDecodeError as e:
            if agent_type == "player":
                raise PlayerReportInvalidError(
                    f"Invalid JSON in Player report: {str(e)}"
                ) from e
            else:
                raise CoachDecisionInvalidError(
                    f"Invalid JSON in Coach decision: {str(e)}"
                ) from e

        return report

    async def _retry_with_backoff(
        self,
        func,
        *args,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        **kwargs,
    ) -> Any:
        """Retry a function with exponential backoff.

        This is primarily used to handle filesystem buffering race conditions
        where a file is written by a subprocess but not immediately visible
        to the parent process.

        Args:
            func: Function to retry (can be sync or async)
            *args: Positional arguments to pass to func
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 0.1)
                          Doubles on each retry (exponential backoff)
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result from successful function call

        Raises:
            Exception from final failed attempt
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.debug(
                        f"Retry attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff

        # All retries exhausted, raise the last exception
        raise last_exception

    def _get_report_path(
        self,
        task_id: str,
        turn: int,
        agent_type: Literal["player", "coach"],
    ) -> Path:
        """Get path to agent report file.

        Args:
            task_id: Task identifier
            turn: Turn number
            agent_type: "player" or "coach"

        Returns:
            Path to report file
        """
        return TaskArtifactPaths.agent_report_path(task_id, agent_type, turn, self.worktree_path)

    def _validate_player_report(self, report: Dict[str, Any]) -> None:
        """Validate Player report has required fields.

        Args:
            report: Parsed Player report JSON

        Raises:
            PlayerReportInvalidError: If required fields are missing or wrong type
        """
        missing_fields = []
        type_errors = []

        for field, expected_type in PLAYER_REPORT_SCHEMA.items():
            if field not in report:
                missing_fields.append(field)
            elif not isinstance(report[field], expected_type):
                type_errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(report[field]).__name__}"
                )

        if missing_fields or type_errors:
            error_msg = "Player report validation failed:\n"
            if missing_fields:
                error_msg += f"Missing fields: {', '.join(missing_fields)}\n"
            if type_errors:
                error_msg += f"Type errors: {', '.join(type_errors)}"
            raise PlayerReportInvalidError(error_msg)

    def _validate_coach_decision(self, decision: Dict[str, Any]) -> None:
        """Validate Coach decision has required fields.

        Args:
            decision: Parsed Coach decision JSON

        Raises:
            CoachDecisionInvalidError: If required fields are missing or wrong type
        """
        missing_fields = []
        type_errors = []

        for field, expected_type in COACH_DECISION_SCHEMA.items():
            if field not in decision:
                missing_fields.append(field)
            elif not isinstance(decision[field], expected_type):
                type_errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(decision[field]).__name__}"
                )

        # Validate decision value
        if "decision" in decision and decision["decision"] not in ["approve", "feedback"]:
            type_errors.append(
                f"decision: must be 'approve' or 'feedback', got '{decision['decision']}'"
            )

        if missing_fields or type_errors:
            error_msg = "Coach decision validation failed:\n"
            if missing_fields:
                error_msg += f"Missing fields: {', '.join(missing_fields)}\n"
            if type_errors:
                error_msg += f"Type errors: {', '.join(type_errors)}"
            raise CoachDecisionInvalidError(error_msg)

    # =========================================================================
    # Task-Work Delegation Methods
    # =========================================================================

    def _write_coach_feedback(
        self,
        task_id: str,
        turn: int,
        feedback: Union[str, Dict[str, Any]],
    ) -> Path:
        """Write Coach feedback to file for task-work to read.

        When using task-work delegation, Coach feedback from the previous turn
        is written to a file that task-work can read as context.

        The feedback is written in structured JSON format to enable:
        - Categorization of must-fix vs should-fix issues
        - Precise file/line references for subagent context
        - Machine-readable format for automated processing

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (feedback is from turn-1)
            feedback: Coach feedback (can be string or dict from Coach decision)

        Returns:
            Path to the written feedback file (JSON format)
        """
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        # Parse feedback into structured format
        structured_feedback = self._parse_coach_feedback(feedback, turn)

        feedback_path = autobuild_dir / f"coach_feedback_for_turn_{turn}.json"
        with open(feedback_path, "w") as f:
            json.dump(structured_feedback, f, indent=2)

        logger.debug(f"Wrote Coach feedback to {feedback_path}")
        return feedback_path

    def _parse_coach_feedback(
        self,
        feedback: Union[str, Dict[str, Any]],
        turn: int,
    ) -> Dict[str, Any]:
        """Parse Coach feedback into structured format.

        Extracts must-fix and should-fix issues from Coach feedback,
        categorizing them for prioritization by the implementation subagent.

        Args:
            feedback: Raw feedback string from Coach (may be JSON-like or plain text)
            turn: Current turn number

        Returns:
            Structured feedback dictionary with categorized issues
        """
        # Initialize structured feedback
        structured = {
            "turn": turn,
            "feedback_from_turn": turn - 1,
            "feedback_summary": "",
            "must_fix": [],
            "should_fix": [],
            "validation_results": {},
            "raw_feedback": feedback if isinstance(feedback, str) else "",
        }

        # If feedback is already a dict (from Coach decision JSON), extract fields
        if isinstance(feedback, dict):
            structured["feedback_summary"] = feedback.get(
                "rationale", feedback.get("feedback_summary", "")
            )
            structured["validation_results"] = feedback.get("validation_results", {})

            # Extract issues if present
            for issue in feedback.get("issues", []):
                issue_entry = {
                    "issue": issue.get("description", ""),
                    "location": issue.get("location", ""),
                    "suggestion": issue.get("suggestion", ""),
                    "type": issue.get("type", "unknown"),
                }
                # Categorize by severity
                if issue.get("severity") in ["critical", "major"]:
                    structured["must_fix"].append(issue_entry)
                else:
                    structured["should_fix"].append(issue_entry)

        else:
            # Plain text feedback - store as summary
            structured["feedback_summary"] = feedback
            structured["raw_feedback"] = feedback

        return structured

    def load_coach_feedback(self, task_id: str, turn: int) -> Optional[Dict[str, Any]]:
        """Load Coach feedback for a specific turn.

        This method loads the structured Coach feedback from the JSON file
        created by _write_coach_feedback. Used by task-work to inject
        feedback context into implementation subagent prompts.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Turn number for which to load feedback

        Returns:
            Structured feedback dictionary if found, None otherwise
        """
        feedback_path = self._get_coach_feedback_path(task_id, turn)

        if not feedback_path.exists():
            logger.debug(f"No Coach feedback found at {feedback_path}")
            return None

        try:
            with open(feedback_path) as f:
                feedback = json.load(f)
            logger.debug(f"Loaded Coach feedback from {feedback_path}")
            return feedback
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Coach feedback JSON: {e}")
            return None

    def _get_coach_feedback_path(self, task_id: str, turn: int) -> Path:
        """Get path to Coach feedback file for a specific turn.

        Args:
            task_id: Task identifier
            turn: Turn number

        Returns:
            Path to feedback file
        """
        return (
            self.worktree_path
            / ".guardkit"
            / "autobuild"
            / task_id
            / f"coach_feedback_for_turn_{turn}.json"
        )

    def _write_turn_context(
        self,
        task_id: str,
        turn: int,
        max_turns: int,
        approaching_limit: bool,
    ) -> Path:
        """Write turn context for Player agent to read.

        This file provides the Player with orchestration context including:
        - Current turn number and max turns
        - Whether approaching the turn limit (escape hatch trigger)
        - When to generate a blocked_report

        The Player reads this file to determine if it should include
        a blocked_report in its JSON output (escape hatch pattern).

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            max_turns: Maximum turns allowed
            approaching_limit: True if turn >= max_turns - 1

        Returns:
            Path to the written context file
        """
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        context = {
            "task_id": task_id,
            "turn": turn,
            "max_turns": max_turns,
            "turns_remaining": max_turns - turn,
            "approaching_limit": approaching_limit,
            "escape_hatch_active": approaching_limit,
            "instructions": (
                "If approaching_limit is true and you cannot complete the task, "
                "include a 'blocked_report' field in your player report JSON. "
                "See autobuild-player.md for the blocked_report schema."
            ),
        }

        context_path = autobuild_dir / "turn_context.json"
        with open(context_path, "w") as f:
            json.dump(context, f, indent=2)

        logger.debug(
            f"Wrote turn context to {context_path}: "
            f"turn={turn}/{max_turns}, approaching_limit={approaching_limit}"
        )
        return context_path

    def load_turn_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load turn context for a task.

        This method loads the turn context file written by _write_turn_context.
        Used by the Player agent to determine if escape hatch is active.

        Args:
            task_id: Task identifier

        Returns:
            Turn context dictionary if found, None otherwise
        """
        context_path = TaskArtifactPaths.autobuild_dir(task_id, self.worktree_path) / "turn_context.json"

        if not context_path.exists():
            logger.debug(f"No turn context found at {context_path}")
            return None

        try:
            with open(context_path) as f:
                context = json.load(f)
            logger.debug(f"Loaded turn context from {context_path}")
            return context
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse turn context JSON: {e}")
            return None

    def _get_implementation_mode(self, task_id: str) -> str:
        """Determine implementation mode from task frontmatter or auto-detection.

        Checks the task file for an explicit `implementation_mode` field in the
        frontmatter first. If no explicit mode is set, auto-detects eligibility
        for direct mode based on complexity (<=3) and absence of high-risk keywords.

        Direct mode avoids the task-work preamble overhead by sending a custom
        prompt directly to the SDK with project-only context.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Implementation mode: "direct" or "task-work"

        Note:
            Import is inside method to avoid circular dependency with TaskLoader.
            Errors are logged but don't fail - defaults to "task-work" behavior.
            Unknown modes (including legacy "manual" mode) are normalized to "task-work".
            Auto-detection only applies when no explicit implementation_mode is set.
        """
        try:
            from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError

            task_data = TaskLoader.load_task(task_id, self.worktree_path)
            frontmatter = task_data.get("frontmatter", {})
            impl_mode = frontmatter.get("implementation_mode")

            # Explicit frontmatter overrides always take priority
            if impl_mode == "direct":
                logger.debug(f"[{task_id}] Explicit implementation_mode: direct")
                return "direct"

            if impl_mode == "task-work":
                logger.debug(f"[{task_id}] Explicit implementation_mode: task-work")
                return "task-work"

            if impl_mode:
                logger.debug(
                    f"[{task_id}] Unknown implementation_mode '{impl_mode}', "
                    "normalizing to task-work"
                )
                return "task-work"

            # No explicit mode - auto-detect based on complexity and risk
            return self._auto_detect_direct_mode(task_id, task_data)

        except Exception as e:
            # Import inside to avoid circular dependency issues at module level
            from guardkit.tasks.task_loader import TaskNotFoundError

            if isinstance(e, TaskNotFoundError):
                logger.debug(f"[{task_id}] Task file not found, using default task-work path")
            else:
                logger.warning(f"[{task_id}] Error loading task for mode detection: {e}")

            return "task-work"

    def _auto_detect_direct_mode(self, task_id: str, task_data: dict) -> str:
        """Auto-detect if a task is eligible for direct mode.

        Tasks with complexity <=3 and no high-risk keywords in title or
        description are routed to direct mode to avoid preamble overhead.

        Args:
            task_id: Task identifier for logging
            task_data: Parsed task data from TaskLoader

        Returns:
            "direct" if eligible, "task-work" otherwise
        """
        from guardkit.orchestrator.intensity_detector import HIGH_RISK_KEYWORDS

        frontmatter = task_data.get("frontmatter", {})
        complexity = frontmatter.get("complexity")

        # Require explicit complexity score for auto-detection
        if complexity is None:
            logger.debug(
                f"[{task_id}] No complexity score in frontmatter, "
                "skipping auto-detection (task-work)"
            )
            return "task-work"

        try:
            complexity = int(complexity)
        except (ValueError, TypeError):
            logger.debug(
                f"[{task_id}] Invalid complexity value '{complexity}', "
                "skipping auto-detection (task-work)"
            )
            return "task-work"

        if complexity > 3:
            logger.debug(
                f"[{task_id}] Complexity {complexity} > 3, not eligible "
                "for auto-direct mode (task-work)"
            )
            return "task-work"

        # Check for high-risk keywords in title and content
        title = frontmatter.get("title", "")
        content = task_data.get("content", "")
        searchable_text = f"{title} {content}".lower()

        if any(keyword in searchable_text for keyword in HIGH_RISK_KEYWORDS):
            logger.debug(
                f"[{task_id}] High-risk keywords detected in task, "
                "not eligible for auto-direct mode (task-work)"
            )
            return "task-work"

        # Check acceptance criteria count - tasks with >=2 AC need task-work
        # for richer agent-written reports
        import re
        ac_list = frontmatter.get("acceptance_criteria", [])
        if isinstance(ac_list, list) and len(ac_list) >= 2:
            ac_count = len(ac_list)
        else:
            # Parse from markdown content (checkbox items under AC section)
            ac_items = re.findall(r'^\s*-\s*\[[ x]\]', content, re.MULTILINE)
            ac_count = len(ac_items)

        if ac_count >= 2:
            logger.debug(
                f"[{task_id}] Task has {ac_count} acceptance criteria (>=2), "
                "not eligible for auto-direct mode (task-work)"
            )
            return "task-work"

        logger.info(
            f"[{task_id}] Auto-detected direct mode "
            f"(complexity={complexity}, no high-risk keywords, "
            f"ac_count={ac_count})"
        )
        return "direct"

    def _calculate_sdk_timeout(self, task_id: str) -> int:
        """Calculate dynamic SDK timeout based on task characteristics.

        Adjusts the base timeout using:
        - Implementation mode multiplier (task-work=1.5x, direct=1.0x)
        - Complexity multiplier (1.0 + complexity/10.0, range 1.1x-2.0x)

        If the user provided a CLI override (sdk_timeout_seconds differs from
        DEFAULT_SDK_TIMEOUT), returns that value unchanged.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Effective timeout in seconds, capped at MAX_SDK_TIMEOUT (3600s)
        """
        # Respect CLI override: if user explicitly set a timeout, don't recalculate
        if self._sdk_timeout_is_override:
            logger.info(
                f"[{task_id}] SDK timeout: {self.sdk_timeout_seconds}s "
                f"(CLI override, skipping dynamic calculation)"
            )
            return self.sdk_timeout_seconds

        base_timeout = self.sdk_timeout_seconds

        try:
            from guardkit.tasks.task_loader import TaskLoader

            task_data = TaskLoader.load_task(task_id, self.worktree_path)
            frontmatter = task_data.get("frontmatter", {})

            mode = frontmatter.get("implementation_mode", "task-work")
            complexity = frontmatter.get("complexity", 5)

            # Clamp complexity to valid range
            complexity = max(1, min(10, int(complexity)))

        except Exception as e:
            logger.debug(
                f"[{task_id}] Could not load task for timeout calculation: {e}. "
                "Using defaults (mode=task-work, complexity=5)"
            )
            mode = "task-work"
            complexity = 5

        # Mode multiplier
        if mode == "task-work":
            mode_multiplier = 1.5
        else:
            mode_multiplier = 1.0

        # Complexity multiplier: 1.1x (complexity=1) to 2.0x (complexity=10)
        complexity_multiplier = 1.0 + (complexity / 10.0)

        effective_timeout = int(base_timeout * mode_multiplier * complexity_multiplier)

        # Cap at maximum
        effective_timeout = min(effective_timeout, MAX_SDK_TIMEOUT)

        logger.info(
            f"[{task_id}] SDK timeout: {effective_timeout}s "
            f"(base={base_timeout}s, mode={mode} x{mode_multiplier}, "
            f"complexity={complexity} x{complexity_multiplier:.1f})"
        )

        return effective_timeout

    async def _invoke_player_direct(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
        context: str = "",
    ) -> AgentInvocationResult:
        """Invoke Player directly via SDK for direct mode tasks.

        Direct mode tasks bypass task-work delegation and don't require an
        implementation plan. Used for straightforward file changes like
        documentation updates, configuration, or simple modifications.

        After successful invocation, writes a minimal task_work_results.json
        for Coach validation compatibility.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            requirements: Task requirements from markdown
            feedback: Optional Coach feedback from previous turn
            max_turns: Maximum turns allowed
            context: Job-specific context from Graphiti

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        try:
            logger.info(f"Invoking Player via direct SDK for {task_id} (turn {turn})")

            # Build prompt for Player
            prompt = self._build_player_prompt(
                task_id, turn, requirements, feedback, context=context
            )

            # Invoke SDK with Player permissions (Read, Write, Edit, Bash)
            await self._invoke_with_role(
                prompt=prompt,
                agent_type="player",
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                permission_mode="acceptEdits",
                model=self.player_model,
            )

            # Add small delay to allow filesystem buffering to complete
            # This mitigates race conditions where SDK subprocess writes report
            # but parent process doesn't see it immediately
            await asyncio.sleep(0.1)

            # Check if SDK wrote the report; create synthetic if missing
            # In direct mode, the SDK Player sometimes doesn't write
            # player_turn_N.json, causing retries to fail and triggering
            # unnecessary state recovery (wastes a turn)
            report_path = self._get_report_path(task_id, turn, "player")
            if not report_path.exists():
                logger.info(
                    f"SDK did not write player_turn_{turn}.json for {task_id}, "
                    f"creating synthetic report from git detection"
                )
                # Load acceptance_criteria and task_type from task frontmatter
                # so file-existence promises can be generated for scaffolding tasks
                acceptance_criteria = None
                task_type_meta = None
                task_file = self._find_task_file(task_id)
                if task_file:
                    metadata = self._load_task_metadata(task_file)
                    acceptance_criteria = metadata.get("acceptance_criteria")
                    task_type_meta = metadata.get("task_type")

                synthetic_report = self._create_synthetic_direct_mode_report(
                    task_id,
                    turn,
                    acceptance_criteria=acceptance_criteria,
                    task_type=task_type_meta,
                )
                self._write_player_report_for_direct_mode(
                    task_id, turn, synthetic_report, success=True
                )

            # Load and validate Player report with retry logic
            # Handles filesystem buffering race condition where report file
            # is written by SDK subprocess but not immediately visible
            report = await self._retry_with_backoff(
                self._load_agent_report,
                task_id,
                turn,
                "player",
                max_retries=3,
                initial_delay=0.1,
            )
            self._validate_player_report(report)

            # Write task_work_results.json for Coach compatibility
            self._write_direct_mode_results(task_id, report, success=True)

            # Write player_turn_N.json for orchestrator state tracking
            # This harmonizes direct mode with task-work delegation path
            self._write_player_report_for_direct_mode(task_id, turn, report, success=True)

            duration = time.time() - start_time

            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=True,
                report=report,
                duration_seconds=duration,
            )

        except (PlayerReportNotFoundError, PlayerReportInvalidError) as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            error_msg = str(e)
            # Write failure results for Coach
            self._write_direct_mode_results(
                task_id,
                error_report,
                success=False,
                error=error_msg,
            )
            # Write player_turn_N.json for orchestrator state tracking
            self._write_player_report_for_direct_mode(
                task_id,
                turn,
                error_report,
                success=False,
                error=error_msg,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=error_msg,
            )
        except SDKTimeoutError as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            error_msg = f"SDK timeout: {str(e)}"
            self._write_direct_mode_results(
                task_id,
                error_report,
                success=False,
                error=error_msg,
            )
            # Write player_turn_N.json for orchestrator state tracking
            self._write_player_report_for_direct_mode(
                task_id,
                turn,
                error_report,
                success=False,
                error=error_msg,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
            )
        except Exception as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            error_msg = f"Unexpected error: {str(e)}"
            self._write_direct_mode_results(
                task_id,
                error_report,
                success=False,
                error=error_msg,
            )
            # Write player_turn_N.json for orchestrator state tracking
            self._write_player_report_for_direct_mode(
                task_id,
                turn,
                error_report,
                success=False,
                error=error_msg,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=error_msg,
            )

    def _write_direct_mode_results(
        self,
        task_id: str,
        player_report: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ) -> Path:
        """Write task_work_results.json for direct mode Coach validation.

        Creates a minimal results file that Coach can read for validation.
        Direct mode tasks have relaxed quality gate requirements:
        - No architectural review required (marked as passed)
        - No plan audit required (no plan exists)
        - Coverage threshold is optional

        Args:
            task_id: Task identifier
            player_report: Player's report with files and test status
            success: Whether Player invocation succeeded
            error: Error message if success=False

        Returns:
            Path to the written results file
        """
        # Ensure results directory exists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Extract test info from Player report
        tests_run = player_report.get("tests_run", False)
        tests_passed = player_report.get("tests_passed", False)
        tests_written = player_report.get("tests_written", [])

        # Derive test count: use tests_passed_count if available (task-work path),
        # otherwise derive from tests_written list length when tests_passed is True
        tests_passed_count = player_report.get("tests_passed_count", 0)
        if tests_passed_count == 0 and tests_passed and tests_written:
            tests_passed_count = len(tests_written)

        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": success and tests_passed if tests_run else success,
            "success": success,
            "implementation_mode": "direct",
            "phases": {
                "phase_3": {"detected": True, "completed": success},
            },
            "quality_gates": {
                "tests_passing": tests_passed if tests_run else None,
                "tests_passed": tests_passed_count,
                "tests_failed": player_report.get("tests_failed_count", 0),
                "coverage": None,  # No coverage requirement for direct mode
                "coverage_met": True,  # Direct mode relaxes coverage
                "quality_gates_relaxed": True,  # Signal to Coach
                "all_passed": success,
            },
            "files_modified": sorted(list(set(player_report.get("files_modified", [])))),
            "files_created": sorted(list(set(player_report.get("files_created", [])))),
            "tests_written": sorted(list(set(tests_written))),
            "summary": (
                f"Direct mode implementation {'completed successfully' if success else 'failed'}"
                + (f": {error}" if error else "")
            ),
        }

        if error:
            results["error"] = error
            results["error_type"] = "DirectModeError"

        # Include completion_promises if Player reported them (TASK-FIX-ACA7b)
        completion_promises = player_report.get("completion_promises", [])
        if completion_promises:
            results["completion_promises"] = completion_promises

        # Propagate _synthetic flag from player_report (TASK-FIX-D1A3)
        if player_report.get("_synthetic"):
            results["_synthetic"] = True

        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote direct mode results to {results_file}")

        return results_file

    def _write_player_report_for_direct_mode(
        self,
        task_id: str,
        turn: int,
        player_report: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ) -> Path:
        """Write player_turn_N.json for direct mode orchestrator compatibility.

        Direct mode tasks bypass task-work delegation but the AutoBuild orchestrator
        expects player_turn_{turn}.json for state tracking. This method creates that
        file from the direct mode invocation results.

        This harmonizes direct mode Player output with the task-work delegation path,
        ensuring Coach validation and orchestrator state recovery work correctly
        regardless of which path was used.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Turn number (1-based)
            player_report: Player's report from SDK invocation
            success: Whether Player invocation succeeded
            error: Error message if success=False

        Returns:
            Path to the written player report file
        """
        # Ensure autobuild directory exists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        player_report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, self.worktree_path
        )

        # Build PLAYER_REPORT_SCHEMA compliant report
        report: Dict[str, Any] = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": player_report.get("files_modified", []),
            "files_created": player_report.get("files_created", []),
            "tests_written": player_report.get("tests_written", []),
            "tests_run": player_report.get("tests_run", False),
            "tests_passed": player_report.get("tests_passed", False),
            "test_output_summary": player_report.get("test_output_summary", ""),
            "implementation_notes": player_report.get(
                "implementation_notes",
                "Direct mode implementation via SDK"
            ),
            "concerns": player_report.get("concerns", []),
            "requirements_addressed": player_report.get("requirements_addressed", []),
            "requirements_remaining": player_report.get("requirements_remaining", []),
            "implementation_mode": "direct",
        }

        # Include completion_promises if Player reported them (TASK-FIX-ACA7b)
        completion_promises = player_report.get("completion_promises", [])
        if completion_promises:
            report["completion_promises"] = completion_promises

        # Add error info if failed
        if not success and error:
            report["error"] = error
            report["success"] = False
        else:
            report["success"] = True

        # Write the report
        player_report_path.write_text(json.dumps(report, indent=2))
        logger.info(f"Wrote direct mode player report to {player_report_path}")

        return player_report_path

    def format_feedback_for_prompt(self, feedback: Dict[str, Any]) -> str:
        """Format structured feedback for inclusion in subagent prompts.

        Converts the structured feedback dictionary into a human-readable
        format suitable for injection into implementation subagent prompts.
        Prioritizes must-fix items over should-fix items.

        Args:
            feedback: Structured feedback from load_coach_feedback()

        Returns:
            Formatted string for prompt injection
        """
        lines = []
        turn = feedback.get("turn", 0)
        from_turn = feedback.get("feedback_from_turn", turn - 1)

        lines.append(f"## Coach Feedback from Turn {from_turn}")
        lines.append("")

        # Summary
        if feedback.get("feedback_summary"):
            lines.append(f"**Summary**: {feedback['feedback_summary']}")
            lines.append("")

        # Must-fix items (critical/major severity)
        must_fix = feedback.get("must_fix", [])
        if must_fix:
            lines.append("### 🔴 MUST FIX (Critical/Major Issues)")
            lines.append("")
            for i, issue in enumerate(must_fix, 1):
                lines.append(f"{i}. **{issue.get('issue', 'Issue')}**")
                if issue.get("location"):
                    lines.append(f"   - Location: `{issue['location']}`")
                if issue.get("suggestion"):
                    lines.append(f"   - Suggestion: {issue['suggestion']}")
                lines.append("")

        # Should-fix items (minor severity)
        should_fix = feedback.get("should_fix", [])
        if should_fix:
            lines.append("### 🟡 SHOULD FIX (Minor Issues)")
            lines.append("")
            for i, issue in enumerate(should_fix, 1):
                lines.append(f"{i}. **{issue.get('issue', 'Issue')}**")
                if issue.get("location"):
                    lines.append(f"   - Location: `{issue['location']}`")
                if issue.get("suggestion"):
                    lines.append(f"   - Suggestion: {issue['suggestion']}")
                lines.append("")

        # Validation results summary
        validation = feedback.get("validation_results", {})
        if validation:
            lines.append("### Validation Results")
            lines.append("")
            if "tests_passed" in validation:
                status = "✅ Passed" if validation["tests_passed"] else "❌ Failed"
                lines.append(f"- Tests: {status}")
            if validation.get("test_output_summary"):
                lines.append(f"- Test Output: {validation['test_output_summary']}")
            if validation.get("code_quality"):
                lines.append(f"- Code Quality: {validation['code_quality']}")
            lines.append("")

        lines.append("---")
        lines.append("*Address all MUST FIX items before submitting. SHOULD FIX items are recommended but optional.*")

        return "\n".join(lines)

    # =========================================================================
    # Task-Work Delegation Methods
    # =========================================================================

    def _build_autobuild_implementation_prompt(
        self,
        task_id: str,
        mode: str = "standard",
        documentation_level: str = "minimal",
        turn: int = 1,
        requirements: str = "",
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
        context: str = "",
    ) -> str:
        """Build implementation prompt using loaded execution protocol.

        TASK-ACO-002: Replaces _build_inline_implement_protocol() with a
        prompt that loads the execution protocol from autobuild_execution_protocol.md
        via load_protocol(), and injects task requirements, coach feedback,
        graphiti context, and turn context inline.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")
            documentation_level: Documentation level ("minimal", "standard",
                or "comprehensive")
            turn: Current turn number (1-based)
            requirements: Task requirements from task markdown
            feedback: Optional Coach feedback from previous turn
            max_turns: Maximum turns allowed for this orchestration
            context: Job-specific context from Graphiti

        Returns:
            Assembled prompt string with protocol and all context sections
        """
        approaching_limit = turn >= max_turns - 1

        # --- Section 1: Header ---
        header = (
            f"You are executing the implementation phase (Phases 3-5) for {task_id}.\n"
            f"\n"
            f"## Context\n"
            f"\n"
            f"- Task ID: {task_id}\n"
            f"- Mode: {mode}\n"
            f"- Documentation Level: {documentation_level}\n"
            f"- Working directory: {self.worktree_path}\n"
        )

        # --- Section 2: Turn context (inline) ---
        turn_section = (
            f"\n## Turn Context\n"
            f"\n"
            f"- Current turn: {turn}\n"
            f"- Max turns: {max_turns}\n"
            f"- Turns remaining: {max_turns - turn}\n"
            f"- Approaching limit: {approaching_limit}\n"
        )
        if approaching_limit:
            turn_section += (
                "\nWARNING: Approaching turn limit. If you cannot complete the task,\n"
                "include a 'blocked_report' field in your player report.\n"
            )

        # --- Section 3: Requirements (inline) ---
        requirements_section = ""
        if requirements:
            requirements_section = (
                f"\n## Task Requirements\n"
                f"\n"
                f"{requirements}\n"
            )

        # --- Section 4: Coach feedback (inline when available) ---
        feedback_section = ""
        if feedback and turn > 1:
            formatted = self._format_feedback_for_prompt(feedback, turn)
            feedback_section = (
                f"\n## Coach Feedback from Turn {turn - 1}\n"
                f"\n"
                f"{formatted}\n"
                f"\n"
                f"Address ALL must_fix items before proceeding.\n"
            )

        # --- Section 5: Graphiti context (inline when available) ---
        context_section = ""
        if context:
            context_section = (
                f"\n## Job-Specific Context\n"
                f"\n"
                f"{context}\n"
            )

        # --- Section 6: Execution protocol (loaded from file) ---
        protocol_content = load_protocol("autobuild_execution_protocol")
        # Substitute placeholders in protocol
        protocol_content = protocol_content.replace("{task_id}", task_id)
        protocol_content = protocol_content.replace("{turn}", str(turn))

        # --- Section 7: Implementation plan locations ---
        plan_paths = TaskArtifactPaths.implementation_plan_paths(
            task_id, self.worktree_path
        )
        plan_locations = "\n".join(f"   - {p}" for p in plan_paths)
        plan_section = (
            f"\n## Implementation Plan Locations\n"
            f"\n"
            f"Check these paths in order for the implementation plan:\n"
            f"{plan_locations}\n"
        )

        # Assemble final prompt
        prompt = (
            header
            + turn_section
            + requirements_section
            + feedback_section
            + context_section
            + "\n---\n\n"
            + protocol_content
            + plan_section
        )

        return prompt

    def _format_feedback_for_prompt(
        self,
        feedback: Union[str, Dict[str, Any]],
        turn: int,
    ) -> str:
        """Format Coach feedback for inline prompt inclusion.

        Args:
            feedback: Coach feedback as string or structured dict
            turn: Current turn number

        Returns:
            Formatted feedback string suitable for prompt inclusion
        """
        if isinstance(feedback, str):
            return feedback

        # Structured feedback dict - extract key fields
        parts: List[str] = []

        # Summary/rationale
        rationale = feedback.get("rationale") or feedback.get("feedback_summary", "")
        if rationale:
            parts.append(f"**Summary**: {rationale}")

        # Must-fix issues
        issues = feedback.get("issues", [])
        must_fix = [i for i in issues if i.get("severity") == "must_fix"]
        should_fix = [i for i in issues if i.get("severity") == "should_fix"]

        if must_fix:
            parts.append("\n**Must Fix:**")
            for issue in must_fix:
                desc = issue.get("description", str(issue))
                parts.append(f"- {desc}")

        if should_fix:
            parts.append("\n**Should Fix:**")
            for issue in should_fix:
                desc = issue.get("description", str(issue))
                parts.append(f"- {desc}")

        # If no structured fields found, dump the whole dict
        if not parts:
            return json.dumps(feedback, indent=2)

        return "\n".join(parts)

    def _build_inline_implement_protocol(
        self,
        task_id: str,
        mode: str = "standard",
    ) -> str:
        """Build inline implementation protocol prompt for Phases 3-5.

        TASK-POF-004: Replaces /task-work skill invocation with an inline
        protocol to eliminate ~839KB preamble overhead per Player turn.
        The inline prompt covers Phases 3 (Implementation), 4 (Testing),
        4.5 (Fix Loop), and 5 (Code Review).

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")

        Returns:
            Inline protocol prompt string (target: ≤20KB)
        """
        # Build plan locations list for the prompt
        plan_paths = TaskArtifactPaths.implementation_plan_paths(
            task_id, self.worktree_path
        )
        plan_locations = "\n".join(f"   - {p}" for p in plan_paths)

        # Build feedback file path hint
        autobuild_dir = f".guardkit/autobuild/{task_id}"
        feedback_hint = (
            f"Check for Coach feedback at: {autobuild_dir}/coach_feedback_for_turn_*.json\n"
            "If feedback exists, address ALL must_fix items before proceeding."
        )

        # Build turn context hint
        turn_context_hint = (
            f"Check for turn context at: {autobuild_dir}/turn_context.json\n"
            "If approaching_limit is true and you cannot complete the task,\n"
            "include a 'blocked_report' field in your player report."
        )

        # Mode-specific instructions
        mode_instructions = ""
        if mode == "tdd":
            mode_instructions = """
### TDD Mode
Follow RED-GREEN-REFACTOR cycle:
1. Write failing tests first (RED)
2. Write minimal implementation to pass tests (GREEN)
3. Refactor for quality while keeping tests green (REFACTOR)
"""
        elif mode == "bdd":
            mode_instructions = """
### BDD Mode
Implementation must make BDD step definitions pass:
1. Read the Gherkin scenarios linked in the task
2. Implement code to satisfy Given/When/Then steps
3. Run BDD tests to verify scenarios pass
"""

        protocol = f"""You are executing the implementation phase (Phases 3-5) for {task_id}.

## Context

- Task ID: {task_id}
- Mode: {mode}
- Working directory: {self.worktree_path}

{feedback_hint}

{turn_context_hint}
{mode_instructions}
## Phase 3: Implementation

1. **Read the implementation plan** from one of these locations (check in order):
{plan_locations}

2. **Implement the code changes** described in the plan:
   - Create new files as specified
   - Modify existing files as specified
   - Follow the architecture and patterns from the plan
   - Write production-quality code with proper error handling

3. **Track your changes** - note every file you create or modify.

## Phase 4: Testing

1. **Verify compilation/build** first - ensure no syntax errors:
   - Python: `python -m py_compile <file>` or import check
   - TypeScript: `npx tsc --noEmit`
   - .NET: `dotnet build`

2. **Run the test suite**:
   - Python: `pytest tests/ -v --tb=short`
   - TypeScript: `npm test`
   - .NET: `dotnet test`

3. **Measure coverage** (if available):
   - Python: `pytest tests/ -v --cov --cov-report=term`
   - TypeScript: `npm test -- --coverage`

4. **Coverage Quality Gates**:
   - Line coverage MUST be >=80%
   - Branch coverage MUST be >=75%
   - If below threshold, write additional tests before proceeding

5. **Report results clearly** in your output using these exact formats:
   - `Phase 3: Implementation` (when you start implementing)
   - `Phase 4: Testing` (when you start testing)
   - `X tests passed` and `Y tests failed` (test counts)
   - `Coverage: Z.Z%` (coverage percentage)
   - `Phase 5: Code Review` (when you start review)
   - `Quality gates: PASSED` or `Quality gates: FAILED`

## Phase 4.5: Fix Loop

If tests fail after Phase 4:

1. Analyze the failure output carefully
2. Make targeted fixes to resolve failures
3. Re-run the full test suite
4. **Maximum 3 fix attempts** - if still failing after 3 attempts, report failure
5. Do NOT skip, comment out, or ignore failing tests
6. Do NOT modify test assertions unless they are provably incorrect

Quality Gate: ALL tests MUST pass (0 failures) before proceeding to Phase 5.

## Phase 5: Code Review (Lightweight)

1. Check for obvious code quality issues:
   - Unused imports
   - Missing error handling on external calls
   - Hardcoded secrets or credentials
2. Run linter if available:
   - Python: `ruff check .` or `flake8`
   - TypeScript: `npm run lint`
3. Note any issues found

## Output Format

After completing all phases, output a clear summary:

```
Phase 3: Implementation
  Files created: [list]
  Files modified: [list]

Phase 4: Testing
  X tests passed, Y tests failed
  Coverage: Z.Z%

Phase 5: Code Review
  [any issues or "No issues found"]

Quality gates: PASSED
```

This summary will be parsed automatically. Use the exact marker formats shown above.

## Important Notes

- Focus on implementing what the plan specifies - no scope creep
- Run tests after EVERY significant change
- If a test framework is not set up, set it up first
- All file paths should be relative to the working directory
- Write clean, well-documented code following project conventions
"""
        return protocol

    async def _invoke_task_work_implement(
        self,
        task_id: str,
        mode: str = "standard",
        documentation_level: str = "minimal",
        turn: int = 1,
        requirements: str = "",
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
        context: str = "",
    ) -> TaskWorkResult:
        """Execute Phases 3-5 (implement-only) via SDK with loaded protocol.

        TASK-ACO-002: Uses _build_autobuild_implementation_prompt() which loads
        the execution protocol from autobuild_execution_protocol.md and injects
        task requirements, coach feedback, graphiti context, and turn context
        inline into the prompt.

        Uses setting_sources=["project"] instead of ["user", "project"],
        reducing context loading from ~1,078KB to ~93KB per Player turn.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")
            documentation_level: Documentation level for file count constraint
                validation ("minimal", "standard", or "comprehensive").
                Default: "minimal" for AutoBuild tasks.
            turn: Current turn number (1-based). Default: 1.
            requirements: Task requirements from task markdown. Default: "".
            feedback: Optional Coach feedback from previous turn. Default: None.
            max_turns: Maximum turns allowed. Default: 5.
            context: Job-specific context from Graphiti. Default: "".

        Returns:
            TaskWorkResult with success status and output/error

        Raises:
            SDKTimeoutError: If execution exceeds timeout
        """
        # TASK-ACO-002: Build prompt with loaded protocol and inline context
        prompt = self._build_autobuild_implementation_prompt(
            task_id=task_id,
            mode=mode,
            documentation_level=documentation_level,
            turn=turn,
            requirements=requirements,
            feedback=feedback,
            max_turns=max_turns,
            context=context,
        )

        logger.info(f"Executing inline implement protocol for {task_id} (mode={mode})")
        logger.info(f"Working directory: {self.worktree_path}")
        logger.info(f"Inline protocol size: {len(prompt)} bytes")

        try:
            from claude_agent_sdk import (
                query,
                ClaudeAgentOptions,
                CLINotFoundError,
                ProcessError,
                CLIJSONDecodeError,
                # TASK-FB-FIX-013: Import message types for proper ContentBlock iteration
                AssistantMessage,
                TextBlock,
                ToolUseBlock,
                ToolResultBlock,
                ResultMessage,
            )
        except ImportError as e:
            import sys
            diagnosis = (
                f"Claude Agent SDK import failed.\n"
                f"  Error: {e}\n"
                f"  Python: {sys.executable}\n"
                f"  sys.path (first 3): {sys.path[:3]}\n\n"
                f"To fix:\n"
                f"  pip install claude-agent-sdk\n"
                f"  # OR for full autobuild support:\n"
                f"  pip install guardkit-py[autobuild]"
            )
            logger.error(diagnosis)
            return TaskWorkResult(
                success=False,
                output={},
                error=diagnosis,
            )

        from guardkit.orchestrator.sdk_utils import check_assistant_message_error

        try:
            options = ClaudeAgentOptions(
                cwd=str(self.worktree_path),
                # TASK-POF-004: Removed "Skill" - inline protocol doesn't invoke skills
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"],
                permission_mode="acceptEdits",
                # TASK-REV-BB80: Use dedicated constant, NOT self.max_turns_per_agent
                # max_turns_per_agent is for adversarial turns (default: 5)
                # task-work needs ~50 internal turns for all phases
                max_turns=TASK_WORK_SDK_MAX_TURNS,
                # TASK-POF-004: Use "project" only - inline protocol replaces
                # skill invocation, no need to load user commands (~839KB savings)
                setting_sources=["project"],
            )

            # TASK-FBSDK-011: Log SDK configuration before invocation
            logger.info(f"[{task_id}] SDK invocation starting")
            logger.info(f"[{task_id}] Working directory: {self.worktree_path}")
            logger.info(f"[{task_id}] Allowed tools: {options.allowed_tools}")
            logger.info(f"[{task_id}] Setting sources: {options.setting_sources}")
            logger.info(f"[{task_id}] Permission mode: {options.permission_mode}")
            logger.info(f"[{task_id}] Max turns: {options.max_turns}")
            logger.info(f"[{task_id}] SDK timeout: {self.sdk_timeout_seconds}s")
            logger.debug(f"[{task_id}] Prompt (first 500 chars): {prompt[:500]}...")

            collected_output: List[str] = []
            # TASK-FIX-STUB-C: Create parser before stream loop so ToolUseBlock
            # file operations can be tracked during processing (not just after)
            parser = TaskWorkStreamParser()
            # TASK-FBSDK-011: Track message statistics
            message_count = 0
            assistant_count = 0
            tool_count = 0
            result_count = 0
            async with asyncio.timeout(self.sdk_timeout_seconds):
                async with async_heartbeat(task_id, "task-work implementation"):
                    async for message in query(prompt=prompt, options=options):
                        # TASK-FBSDK-011: Track message counts
                        message_count += 1
                        # TASK-FB-FIX-013: Properly iterate ContentBlocks instead of str()
                        # message.content is a list[ContentBlock], not a string
                        # Mirrors TASK-FB-FIX-005 pattern from task_work_interface.py
                        if isinstance(message, AssistantMessage):
                            err = check_assistant_message_error(message)
                            if err:
                                logger.error(f"[{task_id}] SDK API error in stream: {err}")
                                return TaskWorkResult(success=False, output={}, error=f"SDK agent error: {err}")
                            assistant_count += 1
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    collected_output.append(block.text)
                                    # Log progress for debugging
                                    if "Phase" in block.text or "test" in block.text.lower():
                                        logger.debug(f"SDK progress: {block.text[:100]}...")
                                elif isinstance(block, ToolUseBlock):
                                    tool_count += 1
                                    logger.debug(f"Tool invoked: {block.name}")
                                    # TASK-FIX-STUB-C: Track file operations from
                                    # Write/Edit tools to populate files_created/
                                    # files_modified in task_work_results.json
                                    if block.name in ("Write", "Edit"):
                                        tool_input = getattr(block, "input", {})
                                        if isinstance(tool_input, dict):
                                            # TASK-FIX-PIPELINE: Log actual SDK key names (Fix 1)
                                            logger.info(
                                                f"[{task_id}] ToolUseBlock {block.name} input keys: "
                                                f"{list(tool_input.keys())}"
                                            )
                                            parser._track_tool_call(
                                                block.name, tool_input
                                            )
                                        else:
                                            logger.warning(
                                                f"[{task_id}] ToolUseBlock {block.name} input is "
                                                f"{type(tool_input).__name__}, not dict: {str(tool_input)[:200]}"
                                            )
                                elif isinstance(block, ToolResultBlock):
                                    # Extract content from tool results if present
                                    if block.content:
                                        collected_output.append(str(block.content))
                        elif isinstance(message, ResultMessage):
                            result_count += 1
                            logger.info(f"SDK completed: turns={message.num_turns}")

            # TASK-FBSDK-011: Log message processing summary
            logger.info(
                f"[{task_id}] Message summary: total={message_count}, "
                f"assistant={assistant_count}, tools={tool_count}, results={result_count}"
            )

            # Join collected output for parsing
            output_text = "\n".join(collected_output)

            # Parse text output for quality gate metrics (tests, coverage, phases)
            # Note: parser already has file tracking from ToolUseBlock processing above
            parser.parse_message(output_text)
            parsed_result = parser.to_result()

            # Write task_work_results.json for Coach validation
            self._write_task_work_results(task_id, parsed_result, documentation_level)

            logger.info(f"task-work completed successfully for {task_id}")
            return TaskWorkResult(
                success=True,
                output=parsed_result,
            )

        except asyncio.TimeoutError:
            error_msg = f"task-work execution exceeded {self.sdk_timeout_seconds}s timeout"
            logger.error(f"[{task_id}] SDK TIMEOUT: {error_msg}")
            logger.error(f"[{task_id}] Messages processed before timeout: {message_count}")
            if collected_output:
                last_output = " ".join(collected_output)[-500:]
                logger.error(f"[{task_id}] Last output (500 chars): {last_output}")
            self._write_failure_results(task_id, error_msg, "TimeoutError", collected_output)
            raise SDKTimeoutError(error_msg)

        except CLINotFoundError as e:
            error_msg = (
                "Claude Code CLI not installed. "
                "Run: npm install -g @anthropic-ai/claude-code"
            )
            logger.error(error_msg)
            self._write_failure_results(task_id, error_msg, "CLINotFoundError", collected_output)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except ProcessError as e:
            error_msg = f"SDK process failed (exit {e.exit_code}): {e.stderr}"
            logger.error(f"[{task_id}] SDK PROCESS ERROR")
            logger.error(f"[{task_id}] Exit code: {e.exit_code}")
            logger.error(f"[{task_id}] Stderr: {e.stderr}")
            logger.error(f"[{task_id}] Messages processed: {message_count}")
            if collected_output:
                last_output = " ".join(collected_output)[-500:]
                logger.error(f"[{task_id}] Last output (500 chars): {last_output}")
            self._write_failure_results(task_id, error_msg, "ProcessError", collected_output)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except CLIJSONDecodeError as e:
            error_msg = f"Failed to parse SDK response: {e}"
            logger.error(error_msg)
            self._write_failure_results(task_id, error_msg, "CLIJSONDecodeError", collected_output)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except Exception as e:
            error_msg = str(e)

            # Check for rate limit in error message
            is_rate_limit, reset_time = detect_rate_limit(error_msg)

            # Also check collected output for rate limit messages
            if not is_rate_limit and collected_output:
                last_output = " ".join(collected_output)[-500:]
                is_rate_limit, reset_time = detect_rate_limit(last_output)

            if is_rate_limit:
                logger.error(f"[{task_id}] RATE LIMIT EXCEEDED")
                if reset_time:
                    logger.error(f"[{task_id}] Estimated reset: {reset_time}")
                raise RateLimitExceededError(
                    f"API rate limit exceeded. Reset: {reset_time or 'unknown'}",
                    reset_time=reset_time
                )

            # Original generic error handling continues...
            error_msg = f"Unexpected error executing task-work: {str(e)}"
            logger.error(f"[{task_id}] SDK UNEXPECTED ERROR: {type(e).__name__}")
            logger.error(f"[{task_id}] Error message: {str(e)}")
            logger.error(f"[{task_id}] Messages processed: {message_count}")
            logger.exception(f"[{task_id}] Full traceback:")
            if collected_output:
                last_output = " ".join(collected_output)[-500:]
                logger.error(f"[{task_id}] Last output (500 chars): {last_output}")
            self._write_failure_results(task_id, error_msg, type(e).__name__, collected_output)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

    def _parse_task_work_output(self, stdout: str) -> Dict[str, Any]:
        """Parse task-work stdout into structured output.

        Extracts key information from task-work output including:
        - Test results
        - Coverage metrics
        - Files modified
        - Quality gate status

        Args:
            stdout: Raw stdout from task-work command

        Returns:
            Parsed output dictionary
        """
        output = {
            "raw_output": stdout,
            "tests_passed": False,
            "coverage_line": None,
            "coverage_branch": None,
            "quality_gates_passed": False,
        }

        # Parse test results
        if "All tests passing" in stdout or "✅" in stdout:
            output["tests_passed"] = True

        # Parse coverage (look for patterns like "Coverage: 85.2%")
        import re
        coverage_match = re.search(r"(?:Line )?[Cc]overage:?\s*(\d+(?:\.\d+)?)\s*%", stdout)
        if coverage_match:
            output["coverage_line"] = float(coverage_match.group(1))

        branch_match = re.search(r"[Bb]ranch [Cc]overage:?\s*(\d+(?:\.\d+)?)\s*%", stdout)
        if branch_match:
            output["coverage_branch"] = float(branch_match.group(1))

        # Parse quality gates
        if "All quality gates passed" in stdout or "IN_REVIEW" in stdout:
            output["quality_gates_passed"] = True

        return output

    def _parse_task_work_stream(
        self,
        message: str,
        parser: TaskWorkStreamParser,
    ) -> Dict[str, Any]:
        """Parse a task-work stream message and return accumulated results.

        This method uses TaskWorkStreamParser for incremental stream processing.
        It complements _parse_task_work_output by enabling real-time parsing
        during SDK stream processing rather than batch processing after completion.

        Args:
            message: Single message from the task-work SDK stream
            parser: TaskWorkStreamParser instance for accumulating state

        Returns:
            Current accumulated result dictionary from the parser

        Example:
            >>> parser = TaskWorkStreamParser()
            >>> async for message in query(prompt=prompt, options=options):
            ...     if hasattr(message, 'content'):
            ...         result = self._parse_task_work_stream(str(message.content), parser)
            >>> final_result = parser.to_result()
        """
        parser.parse_message(message)
        return parser.to_result()

    # =========================================================================
    # Acceptance Criteria & Promise-Based Verification Methods
    # =========================================================================

    def extract_acceptance_criteria(self, task_id: str) -> List[Dict[str, str]]:
        """Extract acceptance criteria from task markdown file.

        Reads the task file and extracts acceptance criteria from the
        frontmatter or body content. Each criterion is assigned a unique ID.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            List of criteria dictionaries with 'id' and 'text' keys.
            Returns empty list if task file not found or no criteria.

        Examples:
            >>> invoker = AgentInvoker(worktree_path=Path("."))
            >>> criteria = invoker.extract_acceptance_criteria("TASK-001")
            >>> criteria[0]
            {'id': 'AC-001', 'text': 'OAuth2 authentication flow works correctly'}
        """
        import yaml

        # Look for task file in various locations
        task_file = None
        possible_paths = [
            self.worktree_path / "tasks" / "in_progress" / f"{task_id}.md",
            self.worktree_path / "tasks" / "backlog" / f"{task_id}.md",
            self.worktree_path / "tasks" / "in_review" / f"{task_id}.md",
        ]

        # Also check for subdirectories (e.g., tasks/in_progress/feature-name/TASK-001.md)
        for status_dir in ["in_progress", "backlog", "in_review"]:
            status_path = self.worktree_path / "tasks" / status_dir
            if status_path.exists():
                for subdir in status_path.iterdir():
                    if subdir.is_dir():
                        possible_task = subdir / f"{task_id}.md"
                        if possible_task.exists():
                            possible_paths.insert(0, possible_task)

        for path in possible_paths:
            if path.exists():
                task_file = path
                break

        if not task_file:
            logger.warning(f"Task file not found for {task_id}")
            return []

        try:
            with open(task_file, "r") as f:
                content = f.read()

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}

                    # Check for acceptance_criteria in frontmatter
                    criteria_list = frontmatter.get("acceptance_criteria", [])
                    if criteria_list:
                        return [
                            {"id": f"AC-{i+1:03d}", "text": criterion}
                            for i, criterion in enumerate(criteria_list)
                        ]

                    # Check body content for ## Acceptance Criteria section
                    body = parts[2]
                    criteria = self._parse_criteria_from_body(body)
                    if criteria:
                        return criteria

            # Fallback: parse entire content as body
            criteria = self._parse_criteria_from_body(content)
            return criteria

        except Exception as e:
            logger.warning(f"Failed to extract acceptance criteria: {e}")
            return []

    def _parse_criteria_from_body(self, body: str) -> List[Dict[str, str]]:
        """Parse acceptance criteria from task body content.

        Looks for an ## Acceptance Criteria section and extracts
        bullet-pointed or numbered items.

        Args:
            body: Task body content (markdown)

        Returns:
            List of criteria dictionaries with 'id' and 'text' keys
        """
        import re

        criteria = []

        # Find the acceptance criteria section
        ac_match = re.search(
            r"##\s*Acceptance\s*Criteria\s*\n(.*?)(?=\n##|\Z)",
            body,
            re.IGNORECASE | re.DOTALL,
        )

        if ac_match:
            ac_section = ac_match.group(1)

            # Extract bullet points or numbered items
            # Matches: - item, * item, 1. item, 1) item
            items = re.findall(
                r"^[\s]*(?:[-*]|\d+[.)]\s*)\s*(.+?)$",
                ac_section,
                re.MULTILINE,
            )

            for i, item in enumerate(items):
                item = item.strip()
                if item:
                    criteria.append({"id": f"AC-{i+1:03d}", "text": item})

        return criteria

    def parse_completion_promises(
        self, player_report: Dict[str, Any]
    ) -> List[CompletionPromise]:
        """Parse completion promises from Player report.

        Extracts the completion_promises field from the Player report
        and converts each entry to a CompletionPromise dataclass.

        Args:
            player_report: Player's JSON report from current turn

        Returns:
            List of CompletionPromise instances

        Examples:
            >>> report = {
            ...     "completion_promises": [
            ...         {"criterion_id": "AC-001", "status": "complete", ...},
            ...     ]
            ... }
            >>> promises = invoker.parse_completion_promises(report)
            >>> promises[0].criterion_id
            'AC-001'
        """
        promises_data = player_report.get("completion_promises", [])
        return [CompletionPromise.from_dict(p) for p in promises_data]

    def parse_criteria_verifications(
        self, coach_decision: Dict[str, Any]
    ) -> List[CriterionVerification]:
        """Parse criteria verifications from Coach decision.

        Extracts the criteria_verification field from the Coach decision
        and converts each entry to a CriterionVerification dataclass.

        Args:
            coach_decision: Coach's JSON decision from current turn

        Returns:
            List of CriterionVerification instances

        Examples:
            >>> decision = {
            ...     "criteria_verification": [
            ...         {"criterion_id": "AC-001", "result": "verified", ...},
            ...     ]
            ... }
            >>> verifications = invoker.parse_criteria_verifications(decision)
            >>> verifications[0].result
            <VerificationResult.VERIFIED: 'verified'>
        """
        verifications_data = coach_decision.get("criteria_verification", [])
        return [CriterionVerification.from_dict(v) for v in verifications_data]

    def _ensure_design_approved_state(self, task_id: str) -> None:
        """Ensure task is in design_approved state before task-work delegation.

        This method bridges AutoBuild orchestration state with task-work's
        state machine requirements. When AutoBuild delegates to
        `task-work --implement-only`, the task must be in `design_approved`
        state with a valid implementation plan.

        This bridge ensures:
        1. Task is in design_approved state (transitions if needed)
        2. Implementation plan exists in expected location
        3. State transitions are logged for debugging

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Raises:
            TaskStateError: If state transition fails
            PlanNotFoundError: If implementation plan is missing
        """
        from guardkit.tasks.state_bridge import TaskStateBridge

        logger.info(f"Ensuring task {task_id} is in design_approved state")

        try:
            # Pass in_autobuild_context=True to fix race condition where
            # autobuild_state hasn't been written yet when stub creation check runs
            bridge = TaskStateBridge(
                task_id,
                self.worktree_path,
                in_autobuild_context=True,
            )
            bridge.ensure_design_approved_state()
            logger.info(f"Task {task_id} state verified: design_approved")

        except PlanNotFoundError as e:
            logger.error(f"Implementation plan not found for {task_id}: {e}")
            raise

        except TaskStateError as e:
            logger.error(f"Failed to ensure design_approved state for {task_id}: {e}")
            raise

    # =========================================================================
    # Task-Work Results Writer Methods
    # =========================================================================

    def _read_json_artifact(self, path: Path) -> Optional[Dict[str, Any]]:
        """Read and parse JSON artifact file with graceful error handling.

        This is a DRY helper method for reading JSON artifact files with
        consistent error handling and logging patterns. Returns None if the
        file doesn't exist or contains invalid JSON.

        Args:
            path: Path to the JSON artifact file

        Returns:
            Parsed JSON data as dict, or None if file not found or invalid

        Example:
            >>> design_path = TaskArtifactPaths.design_results_path(task_id, worktree)
            >>> design_data = self._read_json_artifact(design_path)
            >>> if design_data:
            ...     score = design_data.get("architectural_review", {}).get("score")
        """
        if not path.exists():
            logger.debug(f"JSON artifact not found: {path}")
            return None

        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error reading {path}: {e}")
            return None

    def _write_design_results(
        self,
        task_id: str,
        result_data: Dict[str, Any],
    ) -> Path:
        """Write design phase results for implement-only mode access.

        Persists Phase 2.5B (Architectural Review) results from pre-loop
        execution to enable implement-only mode to include these scores in
        task_work_results.json for Coach validation.

        Location: .guardkit/autobuild/{task_id}/design_results.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            result_data: Parsed result data from design phase
                Expected keys:
                - architectural_review: Dict with score, solid_score, dry_score, yagni_score
                - complexity_score: Integer complexity score (1-10)

        Returns:
            Path to the written design_results.json file

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> result_data = {
            ...     "architectural_review": {"score": 75, "solid_score": 8, ...},
            ...     "complexity_score": 5
            ... }
            >>> path = invoker._write_design_results("TASK-001", result_data)
            >>> path
            PosixPath('.guardkit/autobuild/TASK-001/design_results.json')
        """
        # Ensure autobuild directory exists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        design_file = TaskArtifactPaths.design_results_path(task_id, self.worktree_path)

        # Extract design phase data with simplified schema (per arch review)
        design_results: Dict[str, Any] = {
            "architectural_review": result_data.get("architectural_review", {}),
            "complexity_score": result_data.get("complexity_score"),
        }

        # Write design results to file (idempotent - overwrites if exists)
        design_file.write_text(json.dumps(design_results, indent=2))
        logger.info(f"Wrote design_results.json to {design_file}")

        return design_file

    def _read_design_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Read design phase results from pre-loop execution.

        Reads Phase 2.5B results persisted by pre-loop for use in
        implement-only mode. Returns None if pre-loop was disabled or
        design results are unavailable.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Parsed design results dict, or None if not available

        Example:
            >>> design_data = invoker._read_design_results("TASK-001")
            >>> if design_data:
            ...     arch_review = design_data.get("architectural_review", {})
            ...     score = arch_review.get("score", 0)
        """
        design_file = TaskArtifactPaths.design_results_path(task_id, self.worktree_path)
        return self._read_json_artifact(design_file)

    def _write_task_work_results(
        self,
        task_id: str,
        result_data: Dict[str, Any],
        documentation_level: str = "standard",
    ) -> Path:
        """Write task-work results to JSON file for Coach validation.

        This method creates a structured results file at the expected location
        that Coach can read to validate quality gate results. The file format
        matches the schema expected by Coach's validation logic.

        Location: .guardkit/autobuild/{task_id}/task_work_results.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            result_data: Parsed result data from TaskWorkStreamParser.to_result()
                Expected keys:
                - phases: Dict of detected phases
                - tests_passed: Number of tests passed
                - tests_failed: Number of tests failed
                - coverage: Coverage percentage
                - quality_gates_passed: Boolean quality gate status
                - files_modified: List of modified file paths
                - files_created: List of created file paths
                - architectural_review: Dict with overall score and optional subscores
            documentation_level: Documentation level ("minimal", "standard", or
                "comprehensive"). Used to validate file count constraints.

        Returns:
            Path to the written results file

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> parser = TaskWorkStreamParser()
            >>> parser.parse_message("12 tests passed, 0 failed")
            >>> parser.parse_message("Coverage: 85.5%")
            >>> result_data = parser.to_result()
            >>> results_path = invoker._write_task_work_results("TASK-001", result_data)
            >>> results_path
            PosixPath('.guardkit/autobuild/TASK-001/task_work_results.json')
        """
        # Ensure results directory exists (uses centralized paths)
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Extract test metrics with safe defaults
        tests_passed = result_data.get("tests_passed", 0)
        tests_failed = result_data.get("tests_failed", 0)
        coverage = result_data.get("coverage")
        quality_gates_passed = result_data.get("quality_gates_passed")

        # Determine completion status from available data
        # Completed if quality gates passed or if we have passing tests with no failures
        completed = quality_gates_passed or (
            tests_passed is not None and tests_passed > 0 and tests_failed == 0
        )

        # Extract architectural review score and subscores from result_data
        # The architectural_review object from Phase 2.5B contains overall score
        # and optional SOLID/DRY/YAGNI subscores for detailed evaluation
        arch_review_data = result_data.get("architectural_review", {})
        code_review: Dict[str, Any] = {}
        if arch_review_data:
            # Extract overall score (required for CoachValidator)
            if "score" in arch_review_data:
                code_review["score"] = arch_review_data["score"]

            # Include optional subscores if present
            if "solid" in arch_review_data:
                code_review["solid"] = arch_review_data["solid"]
            if "dry" in arch_review_data:
                code_review["dry"] = arch_review_data["dry"]
            if "yagni" in arch_review_data:
                code_review["yagni"] = arch_review_data["yagni"]

        # Build structured results matching Coach expectations
        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": completed,
            "phases": result_data.get("phases", {}),
            "quality_gates": {
                "tests_passing": tests_failed == 0 if tests_failed is not None else None,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "coverage": coverage,
                "coverage_met": coverage >= 80 if coverage is not None else None,
                "all_passed": quality_gates_passed,
            },
            # Deduplicate file lists using set conversion
            "files_modified": sorted(list(set(result_data.get("files_modified", [])))),
            "files_created": sorted(list(set(result_data.get("files_created", [])))),
            "tests_written": sorted(list(set(result_data.get("tests_written", [])))),
            "summary": self._generate_summary(result_data),
        }

# Add code_review field if architectural review data was found
        if code_review:
            results["code_review"] = code_review

        # Include completion_promises if present in result data (TASK-ACR-001)
        completion_promises = result_data.get("completion_promises", [])
        if completion_promises:
            results["completion_promises"] = completion_promises

        # Merge design results if available (for implement-only mode)
        design_data = self._read_design_results(task_id)
        if design_data:
            logger.info("Merging design phase results into task_work_results.json")
            # Merge architectural review scores from pre-loop
            if "architectural_review" in design_data:
                results["architectural_review"] = design_data["architectural_review"]
            # Merge complexity score from pre-loop
            if "complexity_score" in design_data:
                results["complexity_score"] = design_data["complexity_score"]

        # Filter invalid path entries before validation (TASK-FIX-PV01)
        # Ensures _validate_file_count_constraint sees only real file paths,
        # not natural language fragments or glob wildcards captured by regexes.
        results["files_created"] = [
            f for f in results["files_created"]
            if TaskWorkStreamParser._is_valid_file_path(f)
        ]
        results["files_modified"] = [
            f for f in results["files_modified"]
            if TaskWorkStreamParser._is_valid_file_path(f)
        ]

        # Validate file count constraint for documentation level
        self._validate_file_count_constraint(
            task_id=task_id,
            documentation_level=documentation_level,
            files_created=results["files_created"],
        )

        # Write results to file
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote task_work_results.json to {results_file}")

        return results_file

    def _write_failure_results(
        self,
        task_id: str,
        error: str,
        error_type: str,
        partial_output: Optional[List[str]] = None,
    ) -> Path:
        """Write task_work_results.json with failure status.

        Called on ALL error paths to ensure Coach receives actionable information
        instead of "results not found". This enables intelligent feedback based
        on the specific error type that occurred.

        Location: .guardkit/autobuild/{task_id}/task_work_results.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            error: Error message describing what failed
            error_type: Exception type name (e.g., "ProcessError", "TimeoutError")
            partial_output: Any output collected before failure (optional)

        Returns:
            Path to the written results file

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> invoker._write_failure_results(
            ...     "TASK-001",
            ...     "SDK process failed (exit 1): Command not found",
            ...     "ProcessError",
            ...     ["Phase 2 started...", "Planning..."]
            ... )
            PosixPath('.guardkit/autobuild/TASK-001/task_work_results.json')
        """
        # Ensure results directory exists (uses centralized paths)
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Build failure results matching Coach expectations
        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": False,
            "success": False,
            "error": error,
            "error_type": error_type,
            "partial_output": partial_output or [],
            "phases": {},
            "quality_gates": {
                "all_passed": False,
                "compilation": {
                    "passed": False,
                    "error": "SDK invocation failed before testing",
                },
                "tests": {
                    "passed": False,
                    "error": "SDK invocation failed before testing",
                },
            },
            "files_modified": [],
            "files_created": [],
            "summary": f"Failed: {error_type} - {error}",
        }

        # Write results to file
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote failure results to {results_file}")

        return results_file

    def _generate_summary(self, result_data: Dict[str, Any]) -> str:
        """Generate human-readable summary from task-work results.

        Creates a concise summary string from the parsed result data,
        suitable for display in reports and Coach decision rationale.

        Args:
            result_data: Parsed result data from TaskWorkStreamParser.to_result()

        Returns:
            Human-readable summary string. Returns "Implementation completed"
            if no meaningful data is available.

        Example:
            >>> result_data = {"tests_passed": 12, "coverage": 85.5, "quality_gates_passed": True}
            >>> invoker._generate_summary(result_data)
            '12 tests passed, 85.5% coverage, all quality gates passed'
        """
        parts: List[str] = []

        # Add test count if available
        tests_passed = result_data.get("tests_passed")
        if tests_passed is not None and tests_passed > 0:
            parts.append(f"{tests_passed} tests passed")

        # Add tests failed if any
        tests_failed = result_data.get("tests_failed")
        if tests_failed is not None and tests_failed > 0:
            parts.append(f"{tests_failed} tests failed")

        # Add coverage if available
        coverage = result_data.get("coverage")
        if coverage is not None:
            parts.append(f"{coverage}% coverage")

        # Add quality gate status
        quality_gates_passed = result_data.get("quality_gates_passed")
        if quality_gates_passed is True:
            parts.append("all quality gates passed")
        elif quality_gates_passed is False:
            parts.append("quality gates failed")

        return ", ".join(parts) if parts else "Implementation completed"

    def _validate_file_count_constraint(
        self,
        task_id: str,
        documentation_level: str,
        files_created: List[str],
    ) -> None:
        """Validate that files created do not exceed documentation level limit.

        This method enforces documentation level constraints by logging a warning
        when the number of created files exceeds the limit for the specified level.
        This is monitoring-only and does not block execution.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            documentation_level: One of "minimal", "standard", or "comprehensive"
            files_created: List of files created by the agent

        Note:
            - "minimal" and "standard" levels have a limit of 2 files
            - "comprehensive" has no limit (None)
            - Unknown levels are treated as having no limit

        Example:
            >>> invoker._validate_file_count_constraint(
            ...     "TASK-001",
            ...     "minimal",
            ...     ["file1.py", "file2.py", "file3.py"]
            ... )
            # Logs: [TASK-001] Documentation level constraint violated: ...
        """
        max_files = DOCUMENTATION_LEVEL_MAX_FILES.get(documentation_level)

        # Comprehensive or unknown levels have no limit
        if max_files is None:
            return

        # Exclude internal AutoBuild artifacts from the count
        user_files = [
            f for f in files_created
            if ".guardkit/autobuild/" not in f
        ]

        actual_count = len(user_files)

        if actual_count > max_files:
            # Show first 5 files to avoid overly long log messages
            files_preview = user_files[:5]
            suffix = "..." if len(user_files) > 5 else ""
            logger.warning(
                f"[{task_id}] Documentation level constraint violated: "
                f"created {actual_count} user files, max allowed {max_files} "
                f"for {documentation_level} level. Files: {files_preview}{suffix}"
            )


# =========================================================================
# Module-level utility functions
# =========================================================================


def detect_rate_limit(error_text: str) -> Tuple[bool, Optional[str]]:
    """Detect if error is a rate limit error.

    Args:
        error_text: Error message or output text to check

    Returns:
        Tuple of (is_rate_limit, reset_time)
        reset_time is None if not parseable
    """
    patterns = [
        (r"hit your limit.*resets?\s+(\d+(?::\d+)?(?:\s*(?:am|pm))?(?:\s*\([^)]+\))?)", True),
        (r"rate limit", False),
        (r"too many requests", False),
        (r"429", False),
        (r"quota exceeded", False),
    ]

    text_lower = error_text.lower()
    for pattern, has_reset_time in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            reset_time = match.group(1) if has_reset_time and match.lastindex else None
            return True, reset_time

    return False, None
