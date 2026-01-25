"""AgentInvoker handles Claude Agents SDK invocation for Player and Coach agents."""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Union

from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
    PlanNotFoundError,
    PlayerReportInvalidError,
    PlayerReportNotFoundError,
    SDKTimeoutError,
    TaskStateError,
    TaskWorkResult,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
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

# SDK timeout in seconds (default: 900s/15min, can be overridden via GUARDKIT_SDK_TIMEOUT env var)
# With pre-loop disabled for feature-build (TASK-FB-FIX-015), the loop phase needs ~600-900s.
# A 900s default aligns with orchestrator defaults and provides adequate headroom.
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "900"))

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
    FILES_MODIFIED_PATTERN = re.compile(r"(?:Modified|Changed):\s*([^\s,]+)")
    FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+)")
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

    def _track_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
        """Track file operations from tool calls.

        Extracts file paths from Write and Edit tool invocations and adds them
        to the appropriate tracking set (created or modified). Also tracks
        test file creation separately.

        Args:
            tool_name: Name of the tool (e.g., "Write", "Edit")
            tool_args: Tool arguments dictionary containing file_path
        """
        file_path = tool_args.get("file_path")
        if not file_path or not isinstance(file_path, str):
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
            if file_path:
                self._files_created.add(file_path)
                logger.debug(f"Tool result tracked - file created: {file_path}")

        for result_match in self.TOOL_RESULT_MODIFIED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if file_path:
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
            self._files_modified.add(file_path)
            logger.debug(f"File modified: {file_path}")

        for file_match in self.FILES_CREATED_PATTERN.finditer(message):
            file_path = file_match.group(1)
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
            sdk_timeout_seconds: Timeout for SDK invocations (default: 900s)
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

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            AgentInvocationError: If invocation fails
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

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
                prompt = self._build_player_prompt(task_id, turn, requirements, feedback)

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
    ) -> str:
        """Build prompt for Player agent invocation with acceptance criteria.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Task requirements
            feedback: Optional feedback from previous Coach turn
            acceptance_criteria: Optional list of acceptance criteria with id and text

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

    def _build_coach_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        honesty_verification: Optional[HonestyVerification] = None,
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Build prompt for Coach agent invocation with promise verification.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Original task requirements
            player_report: Player's report from current turn
            honesty_verification: Optional verification results for Player claims
            acceptance_criteria: Optional list of acceptance criteria with id and text

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

        prompt = f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

## Original Requirements

{requirements}
{criteria_section}
## Player's Report

{json.dumps(player_report, indent=2)}
{honesty_section}
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

        try:
            options = ClaudeAgentOptions(
                cwd=str(self.worktree_path),
                allowed_tools=allowed_tools,
                permission_mode=permission_mode,
                max_turns=self.max_turns_per_agent,
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

                # Extract test info
                tests_info = task_work_data.get("tests_info", {})
                if tests_info:
                    report["tests_run"] = tests_info.get("tests_run", False)
                    report["tests_passed"] = tests_info.get("tests_passed", False)
                    report["test_output_summary"] = tests_info.get(
                        "output_summary", ""
                    )
                    # Extract test files as tests_written
                    report["tests_written"] = [
                        f
                        for f in report["files_created"] + report["files_modified"]
                        if "test" in f.lower() or f.endswith("_test.py")
                    ]

                # Extract implementation notes from plan audit if available
                plan_audit = task_work_data.get("plan_audit", {})
                if plan_audit:
                    report["implementation_notes"] = (
                        f"Implementation via task-work delegation. "
                        f"Files planned: {plan_audit.get('files_planned', 0)}, "
                        f"Files actual: {plan_audit.get('files_actual', 0)}"
                    )

                logger.info(
                    f"Created Player report from task_work_results.json for {task_id} turn {turn}"
                )

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to read task_work_results.json, using defaults: {e}"
                )
        else:
            # Fallback: detect git changes
            logger.info(
                f"task_work_results.json not found, detecting git changes for {task_id}"
            )
            try:
                git_changes = self._detect_git_changes()
                report["files_modified"] = git_changes.get("modified", [])
                report["files_created"] = git_changes.get("created", [])
                report["implementation_notes"] = (
                    "Implementation via task-work delegation (git-detected changes)"
                )
            except Exception as e:
                logger.warning(f"Failed to detect git changes: {e}")

        # Also use task_work_result.output if available
        if task_work_result.output:
            output = task_work_result.output
            # Override with output data if present (more recent than file)
            if "files_modified" in output:
                report["files_modified"] = output["files_modified"]
            if "files_created" in output:
                report["files_created"] = output["files_created"]
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

        # Write Player report
        with open(player_report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Written Player report to {player_report_path}")

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
        """Determine implementation mode from task frontmatter.

        Checks the task file for an `implementation_mode` field in the frontmatter.
        Used to route direct mode tasks to the legacy SDK path (bypassing task-work
        delegation which requires an implementation plan).

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Implementation mode: "direct", "task-work", or "task-work" (default)

        Note:
            Import is inside method to avoid circular dependency with TaskLoader.
            Errors are logged but don't fail - defaults to "task-work" behavior.
        """
        try:
            from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError

            task_data = TaskLoader.load_task(task_id, self.worktree_path)
            impl_mode = task_data.get("frontmatter", {}).get("implementation_mode")

            if impl_mode:
                logger.debug(f"[{task_id}] Detected implementation_mode: {impl_mode}")
                return impl_mode

            logger.debug(f"[{task_id}] No implementation_mode set, defaulting to task-work")
            return "task-work"

        except Exception as e:
            # Import inside to avoid circular dependency issues at module level
            from guardkit.tasks.task_loader import TaskNotFoundError

            if isinstance(e, TaskNotFoundError):
                logger.debug(f"[{task_id}] Task file not found, using default task-work path")
            else:
                logger.warning(f"[{task_id}] Error loading task for mode detection: {e}")

            return "task-work"

    async def _invoke_player_direct(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
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
            prompt = self._build_player_prompt(task_id, turn, requirements, feedback)

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

            # Write task_work_results.json for Coach compatibility
            self._write_direct_mode_results(task_id, report, success=True)

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
            # Write failure results for Coach
            self._write_direct_mode_results(
                task_id,
                {"task_id": task_id, "turn": turn},
                success=False,
                error=str(e),
            )
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
            self._write_direct_mode_results(
                task_id,
                {"task_id": task_id, "turn": turn},
                success=False,
                error=f"SDK timeout: {str(e)}",
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
            self._write_direct_mode_results(
                task_id,
                {"task_id": task_id, "turn": turn},
                success=False,
                error=f"Unexpected error: {str(e)}",
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"Unexpected error: {str(e)}",
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
                "tests_passed": player_report.get("tests_passed_count", 0),
                "tests_failed": player_report.get("tests_failed_count", 0),
                "coverage": None,  # No coverage requirement for direct mode
                "coverage_met": True,  # Direct mode relaxes coverage
                "quality_gates_relaxed": True,  # Signal to Coach
                "all_passed": success,
            },
            "files_modified": sorted(list(set(player_report.get("files_modified", [])))),
            "files_created": sorted(list(set(player_report.get("files_created", [])))),
            "summary": (
                f"Direct mode implementation {'completed successfully' if success else 'failed'}"
                + (f": {error}" if error else "")
            ),
        }

        if error:
            results["error"] = error
            results["error_type"] = "DirectModeError"

        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote direct mode results to {results_file}")

        return results_file

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

    async def _invoke_task_work_implement(
        self,
        task_id: str,
        mode: str = "standard",
        documentation_level: str = "minimal",
    ) -> TaskWorkResult:
        """Execute task-work --implement-only via SDK query() in worktree context.

        Delegates Player implementation to the full task-work command via
        Claude Agent SDK query(). This uses the complete subagent infrastructure for:
        - Implementation planning
        - Architectural review
        - Testing
        - Code review

        The SDK invocation pattern follows _invoke_with_role() but invokes
        the /task-work slash command directly instead of using a custom prompt.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")
            documentation_level: Documentation level for file count constraint
                validation ("minimal", "standard", or "comprehensive").
                Default: "minimal" for AutoBuild tasks.

        Returns:
            TaskWorkResult with success status and output/error

        Raises:
            SDKTimeoutError: If execution exceeds timeout
        """
        prompt = f"/task-work {task_id} --implement-only --mode={mode}"

        logger.info(f"Executing via SDK: {prompt}")
        logger.info(f"Working directory: {self.worktree_path}")

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

        try:
            options = ClaudeAgentOptions(
                cwd=str(self.worktree_path),
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
                permission_mode="acceptEdits",
                max_turns=50,  # task-work can take many turns
                # TASK-FB-FIX-014: Include "user" to load skills from ~/.claude/commands/
                # Without "user", the SDK can't find /task-work skill
                setting_sources=["user", "project"],
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

            # Parse output using stream parser for structured data
            parser = TaskWorkStreamParser()
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
            bridge = TaskStateBridge(task_id, self.worktree_path)
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
            "summary": self._generate_summary(result_data),
        }

# Add code_review field if architectural review data was found
        if code_review:
            results["code_review"] = code_review

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

        actual_count = len(files_created)

        if actual_count > max_files:
            # Show first 5 files to avoid overly long log messages
            files_preview = files_created[:5]
            suffix = "..." if len(files_created) > 5 else ""
            logger.warning(
                f"[{task_id}] Documentation level constraint violated: "
                f"created {actual_count} files, max allowed {max_files} "
                f"for {documentation_level} level. Files: {files_preview}{suffix}"
            )
