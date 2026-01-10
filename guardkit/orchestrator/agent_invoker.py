"""AgentInvoker handles Claude Agents SDK invocation for Player and Coach agents."""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
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

# Feature flag for task-work delegation (set via environment or config)
# When enabled, invoke_player() delegates to `guardkit task-work --implement-only`
# instead of direct SDK invocation
USE_TASK_WORK_DELEGATION = os.environ.get("GUARDKIT_USE_TASK_WORK_DELEGATION", "false").lower() == "true"

# SDK timeout in seconds (default: 600s, can be overridden via GUARDKIT_SDK_TIMEOUT env var)
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))

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

    def __init__(self) -> None:
        """Initialize the parser with empty accumulated state."""
        self._phases: Dict[str, Dict[str, Any]] = {}
        self._tests_passed: Optional[int] = None
        self._tests_failed: Optional[int] = None
        self._coverage: Optional[float] = None
        self._quality_gates_passed: Optional[bool] = None
        self._files_modified: set = set()
        self._files_created: set = set()

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

    def parse_message(self, message: str) -> None:
        """Parse a single stream message and accumulate results.

        This method extracts quality gate information from a stream message
        and updates the internal state. It handles:
        - Phase markers and completion indicators
        - Test pass/fail counts
        - Coverage percentage
        - Quality gate status
        - File modification lists

        Args:
            message: Single message from the task-work SDK stream

        Note:
            Unrecognized patterns are logged at debug level but do not
            cause errors (graceful degradation).
        """
        if not message:
            return

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

        # Test results
        tests_passed_match = self._match_pattern(self.TESTS_PASSED_PATTERN, message)
        if tests_passed_match:
            self._tests_passed = int(tests_passed_match.group(1))
            logger.debug(f"Tests passed: {self._tests_passed}")

        tests_failed_match = self._match_pattern(self.TESTS_FAILED_PATTERN, message)
        if tests_failed_match:
            self._tests_failed = int(tests_failed_match.group(1))
            logger.debug(f"Tests failed: {self._tests_failed}")

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
            sdk_timeout_seconds: Timeout for SDK invocations (default: 600s)
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

            # Choose invocation method based on feature flag
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
                )

                duration = time.time() - start_time

                if result.success:
                    # Create Player report from task-work results
                    # task-work creates task_work_results.json, but orchestrator expects
                    # player_turn_{turn}.json - this bridges the gap
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

            async with asyncio.timeout(self.sdk_timeout_seconds):
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
                report["tests_passed"] = output["tests_passed"]
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
                setting_sources=["project"],  # Load CLAUDE.md from worktree
            )

            collected_output = []
            async with asyncio.timeout(self.sdk_timeout_seconds):
                async for message in query(prompt=prompt, options=options):
                    # Collect message content for parsing
                    # Stream processing will be enhanced by TASK-SDK-002
                    if hasattr(message, 'content'):
                        collected_output.append(str(message.content))

            # Join collected output for parsing
            output_text = "\n".join(collected_output)

            logger.info(f"task-work completed successfully for {task_id}")
            return TaskWorkResult(
                success=True,
                output=self._parse_task_work_output(output_text),
            )

        except asyncio.TimeoutError:
            error_msg = f"task-work execution exceeded {self.sdk_timeout_seconds}s timeout"
            logger.error(error_msg)
            raise SDKTimeoutError(error_msg)

        except CLINotFoundError as e:
            error_msg = (
                "Claude Code CLI not installed. "
                "Run: npm install -g @anthropic-ai/claude-code"
            )
            logger.error(error_msg)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except ProcessError as e:
            error_msg = f"SDK process failed (exit {e.exit_code}): {e.stderr}"
            logger.error(error_msg)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except CLIJSONDecodeError as e:
            error_msg = f"Failed to parse SDK response: {e}"
            logger.error(error_msg)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except Exception as e:
            logger.exception(f"Unexpected error executing task-work: {e}")
            return TaskWorkResult(
                success=False,
                output={},
                error=str(e),
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

    def _write_task_work_results(self, task_id: str, result_data: Dict[str, Any]) -> Path:
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
        from datetime import datetime

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

        # Write results to file
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote task_work_results.json to {results_file}")

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
