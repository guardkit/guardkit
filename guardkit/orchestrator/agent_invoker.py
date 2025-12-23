"""AgentInvoker handles Claude Agents SDK invocation for Player and Coach agents."""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Literal, Optional

from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
    PlayerReportInvalidError,
    PlayerReportNotFoundError,
    SDKTimeoutError,
)

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
        sdk_timeout_seconds: int = 300,
    ):
        """Initialize AgentInvoker.

        Args:
            worktree_path: Path to the isolated git worktree
            max_turns_per_agent: Maximum turns per agent invocation (default: 30)
            player_model: Model to use for Player agent (default: claude-sonnet-4-5)
            coach_model: Model to use for Coach agent (default: claude-sonnet-4-5)
            sdk_timeout_seconds: Timeout for SDK invocations (default: 300s)
        """
        self.worktree_path = Path(worktree_path)
        self.max_turns_per_agent = max_turns_per_agent
        self.player_model = player_model
        self.coach_model = coach_model
        self.sdk_timeout_seconds = sdk_timeout_seconds

    async def invoke_player(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str] = None,
    ) -> AgentInvocationResult:
        """Invoke Player agent via Claude Agents SDK.

        The Player agent:
        - Has full file system access (Read, Write, Edit, Bash)
        - Works in isolated worktree
        - Implements code and writes tests
        - Creates JSON report at .guardkit/autobuild/{task_id}/player_turn_{turn}.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            requirements: Task requirements (from task markdown)
            feedback: Optional Coach feedback from previous turn

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            AgentInvocationError: If invocation fails
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        try:
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
        """Invoke Coach agent via Claude Agents SDK.

        The Coach agent:
        - Has read-only access (Read, Bash only)
        - Works in same worktree as Player
        - Validates implementation independently
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
            # Build prompt for Coach
            prompt = self._build_coach_prompt(task_id, turn, requirements, player_report)

            # Invoke SDK with Coach permissions (Read, Bash only - no Write/Edit)
            await self._invoke_with_role(
                prompt=prompt,
                agent_type="coach",
                allowed_tools=["Read", "Bash", "Grep", "Glob"],
                permission_mode="default",
                model=self.coach_model,
            )

            # Load and validate Coach decision
            decision = self._load_agent_report(task_id, turn, "coach")
            self._validate_coach_decision(decision)

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
    ) -> str:
        """Build prompt for Player agent invocation.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Task requirements
            feedback: Optional feedback from previous Coach turn

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

        prompt = f"""You are the Player agent. Implement the following task.

Task ID: {task_id}
Turn: {turn}

## Requirements

{requirements}
{feedback_section}

## Your Responsibilities

1. Implement the code to satisfy the requirements
2. Write comprehensive tests
3. Run the tests and verify they pass
4. Create your report

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
  "requirements_remaining": ["requirements", "still", "pending"]
}}

Follow the report format specified in your agent definition.
"""
        return prompt

    def _build_coach_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
    ) -> str:
        """Build prompt for Coach agent invocation.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Original task requirements
            player_report: Player's report from current turn

        Returns:
            Formatted prompt string for Coach agent
        """
        prompt = f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

## Original Requirements

{requirements}

## Player's Report

{json.dumps(player_report, indent=2)}

## Your Responsibilities

1. Independently verify the Player's claims
2. Run the tests yourself (don't trust Player's report)
3. Check all requirements are met
4. Either APPROVE or provide specific FEEDBACK

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
  }},
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
  ],
  "rationale": "Why you're providing feedback"
}}

Follow the decision format specified in your agent definition.
"""
        return prompt

    async def _invoke_with_role(
        self,
        prompt: str,
        agent_type: Literal["player", "coach"],
        allowed_tools: list[str],
        permission_mode: Literal["acceptEdits", "default"],
        model: str,
    ) -> None:
        """Low-level SDK invocation with role-based permissions.

        This method handles the actual Claude Agents SDK invocation with
        appropriate permissions and timeout handling.

        Args:
            prompt: Formatted prompt for agent
            agent_type: "player" or "coach"
            allowed_tools: List of allowed SDK tools
            permission_mode: "acceptEdits" (Player) or "default" (Coach)
            model: Model identifier

        Raises:
            AgentInvocationError: If SDK invocation fails
            SDKTimeoutError: If invocation exceeds timeout
        """
        try:
            # Note: Actual SDK integration will be added when SDK is available
            # This is a placeholder for the SDK invocation pattern
            #
            # from claude_code_sdk import query, ClaudeCodeOptions
            #
            # options = ClaudeCodeOptions(
            #     cwd=str(self.worktree_path),
            #     allowed_tools=allowed_tools,
            #     permission_mode=permission_mode,
            #     max_turns=self.max_turns_per_agent,
            #     model=model,
            # )
            #
            # async with asyncio.timeout(self.sdk_timeout_seconds):
            #     async for message in query(prompt=prompt, options=options):
            #         # Process SDK messages (progress tracking, etc.)
            #         yield message

            # For now, raise NotImplementedError to indicate SDK integration needed
            raise NotImplementedError(
                "Claude Agents SDK integration pending. "
                "This will be completed when SDK is available."
            )

        except asyncio.TimeoutError:
            raise SDKTimeoutError(
                f"Agent invocation exceeded {self.sdk_timeout_seconds}s timeout"
            )
        except NotImplementedError:
            # Re-raise NotImplementedError for testing
            raise
        except Exception as e:
            raise AgentInvocationError(
                f"SDK invocation failed for {agent_type}: {str(e)}"
            ) from e

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
        autobuild_dir = self.worktree_path / ".guardkit" / "autobuild" / task_id
        return autobuild_dir / f"{agent_type}_turn_{turn}.json"

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
