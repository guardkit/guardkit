"""Unit tests for AgentInvoker class."""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    USE_TASK_WORK_DELEGATION,
)
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    PlayerReportNotFoundError,
    PlayerReportInvalidError,
    CoachDecisionNotFoundError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
    TaskWorkResult,
)


# ==================== Fixtures ====================


@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree


@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker instance."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
    )


@pytest.fixture
def sample_player_report():
    """Sample Player report JSON."""
    return {
        "task_id": "TASK-001",
        "turn": 1,
        "files_modified": ["src/auth.py"],
        "files_created": ["tests/test_auth.py"],
        "tests_written": ["tests/test_auth.py"],
        "tests_run": True,
        "tests_passed": True,
        "test_output_summary": "5 passed in 0.23s",
        "implementation_notes": "Implemented OAuth2 flow",
        "concerns": [],
        "requirements_addressed": ["OAuth2 authentication"],
        "requirements_remaining": [],
    }


@pytest.fixture
def sample_coach_approval():
    """Sample Coach approval decision."""
    return {
        "task_id": "TASK-001",
        "turn": 1,
        "decision": "approve",
        "validation_results": {
            "requirements_met": ["All acceptance criteria verified"],
            "tests_run": True,
            "tests_passed": True,
            "test_command": "pytest tests/ -v",
            "test_output_summary": "12 passed in 1.45s",
            "code_quality": "Good",
            "edge_cases_covered": ["Token refresh", "Auth failure"],
        },
        "rationale": "Implementation complete",
    }


@pytest.fixture
def sample_coach_feedback():
    """Sample Coach feedback decision."""
    return {
        "task_id": "TASK-001",
        "turn": 1,
        "decision": "feedback",
        "issues": [
            {
                "type": "missing_requirement",
                "severity": "critical",
                "description": "Missing HTTPS enforcement",
                "requirement": "Secure authentication",
                "suggestion": "Add SSL/TLS check",
            }
        ],
        "rationale": "Security requirement not met",
    }


def create_report_file(worktree_path: Path, task_id: str, turn: int, agent_type: str, report: Dict[str, Any]):
    """Helper to create agent report file."""
    autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    report_path = autobuild_dir / f"{agent_type}_turn_{turn}.json"
    report_path.write_text(json.dumps(report, indent=2))
    return report_path


# ==================== Initialization Tests ====================


class TestAgentInvokerInit:
    """Test AgentInvoker initialization."""

    def test_init_with_defaults(self, worktree_path):
        """AgentInvoker initializes with default values."""
        invoker = AgentInvoker(worktree_path=worktree_path)

        assert invoker.worktree_path == worktree_path
        assert invoker.max_turns_per_agent == 30
        assert invoker.player_model == "claude-sonnet-4-5-20250929"
        assert invoker.coach_model == "claude-sonnet-4-5-20250929"
        assert invoker.sdk_timeout_seconds == 300

    def test_init_with_custom_values(self, worktree_path):
        """AgentInvoker accepts custom configuration."""
        invoker = AgentInvoker(
            worktree_path=worktree_path,
            max_turns_per_agent=50,
            player_model="claude-opus-4-5-20251101",
            coach_model="claude-sonnet-4-5-20250929",
            sdk_timeout_seconds=120,
        )

        assert invoker.max_turns_per_agent == 50
        assert invoker.player_model == "claude-opus-4-5-20251101"
        assert invoker.coach_model == "claude-sonnet-4-5-20250929"
        assert invoker.sdk_timeout_seconds == 120


# ==================== Player Invocation Tests ====================


class TestPlayerInvocation:
    """Test Player agent invocation."""

    @pytest.mark.asyncio
    async def test_invoke_player_success(
        self, agent_invoker, worktree_path, sample_player_report
    ):
        """Player invocation succeeds and returns report."""
        # Setup: Create Player report file
        create_report_file(
            worktree_path, "TASK-001", 1, "player", sample_player_report
        )

        # Mock SDK invocation
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ) as mock_sdk:
            # Execute
            result = await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
            )

            # Verify
            assert result.success is True
            assert result.agent_type == "player"
            assert result.task_id == "TASK-001"
            assert result.turn == 1
            assert result.report == sample_player_report
            assert result.duration_seconds > 0
            assert result.error is None

            # Verify SDK was called with correct parameters
            mock_sdk.assert_called_once()
            call_kwargs = mock_sdk.call_args.kwargs
            assert call_kwargs["agent_type"] == "player"
            assert call_kwargs["allowed_tools"] == [
                "Read",
                "Write",
                "Edit",
                "Bash",
                "Grep",
                "Glob",
            ]
            assert call_kwargs["permission_mode"] == "acceptEdits"
            assert call_kwargs["model"] == agent_invoker.player_model

    @pytest.mark.asyncio
    async def test_invoke_player_with_feedback(
        self, agent_invoker, worktree_path, sample_player_report
    ):
        """Player receives feedback from previous turn."""
        # Setup
        create_report_file(
            worktree_path, "TASK-001", 2, "player", sample_player_report
        )
        feedback = "Please add error handling for token expiration"

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=2,
                requirements="Implement OAuth2 authentication",
                feedback=feedback,
            )

            # Verify
            assert result.success is True
            assert result.turn == 2

    @pytest.mark.asyncio
    async def test_invoke_player_report_not_found(self, agent_invoker):
        """Raises error if Player doesn't create report."""
        # Mock SDK (report file won't be created)
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
            )

            # Verify
            assert result.success is False
            assert "Player report not found" in result.error
            assert result.report == {}

    @pytest.mark.asyncio
    async def test_invoke_player_report_invalid_json(
        self, agent_invoker, worktree_path
    ):
        """Raises error if Player report is malformed JSON."""
        # Setup: Create invalid JSON file
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        autobuild_dir.mkdir(parents=True)
        report_path = autobuild_dir / "player_turn_1.json"
        report_path.write_text("{ invalid json }")

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
            )

            # Verify
            assert result.success is False
            assert "Invalid JSON" in result.error

    @pytest.mark.asyncio
    async def test_invoke_player_report_missing_fields(
        self, agent_invoker, worktree_path
    ):
        """Raises error if Player report is missing required fields."""
        # Setup: Create report with missing fields
        incomplete_report = {
            "task_id": "TASK-001",
            "turn": 1,
            # Missing required fields
        }
        create_report_file(
            worktree_path, "TASK-001", 1, "player", incomplete_report
        )

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
            )

            # Verify
            assert result.success is False
            assert "validation failed" in result.error
            assert "Missing fields" in result.error


# ==================== Coach Invocation Tests ====================


class TestCoachInvocation:
    """Test Coach agent invocation."""

    @pytest.mark.asyncio
    async def test_invoke_coach_success(
        self, agent_invoker, worktree_path, sample_player_report, sample_coach_approval
    ):
        """Coach invocation succeeds and returns decision."""
        # Setup: Create Coach decision file
        create_report_file(
            worktree_path, "TASK-001", 1, "coach", sample_coach_approval
        )

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ) as mock_sdk:
            # Execute
            result = await agent_invoker.invoke_coach(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
                player_report=sample_player_report,
            )

            # Verify
            assert result.success is True
            assert result.agent_type == "coach"
            assert result.task_id == "TASK-001"
            assert result.turn == 1
            assert result.report == sample_coach_approval
            assert result.duration_seconds > 0

            # Verify SDK was called with read-only permissions
            mock_sdk.assert_called_once()
            call_kwargs = mock_sdk.call_args.kwargs
            assert call_kwargs["agent_type"] == "coach"
            assert call_kwargs["allowed_tools"] == ["Read", "Bash", "Grep", "Glob"]
            assert call_kwargs["permission_mode"] == "bypassPermissions"
            assert "Write" not in call_kwargs["allowed_tools"]
            assert "Edit" not in call_kwargs["allowed_tools"]

    @pytest.mark.asyncio
    async def test_invoke_coach_approval(
        self, agent_invoker, worktree_path, sample_player_report, sample_coach_approval
    ):
        """Coach approves implementation."""
        # Setup
        create_report_file(
            worktree_path, "TASK-001", 1, "coach", sample_coach_approval
        )

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_coach(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
                player_report=sample_player_report,
            )

            # Verify
            assert result.success is True
            assert result.report["decision"] == "approve"

    @pytest.mark.asyncio
    async def test_invoke_coach_feedback(
        self, agent_invoker, worktree_path, sample_player_report, sample_coach_feedback
    ):
        """Coach provides feedback."""
        # Setup
        create_report_file(
            worktree_path, "TASK-001", 1, "coach", sample_coach_feedback
        )

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_coach(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
                player_report=sample_player_report,
            )

            # Verify
            assert result.success is True
            assert result.report["decision"] == "feedback"
            assert len(result.report["issues"]) > 0

    @pytest.mark.asyncio
    async def test_invoke_coach_decision_not_found(self, agent_invoker, sample_player_report):
        """Raises error if Coach doesn't create decision."""
        # Mock SDK (decision file won't be created)
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_coach(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
                player_report=sample_player_report,
            )

            # Verify
            assert result.success is False
            assert "Coach decision not found" in result.error

    @pytest.mark.asyncio
    async def test_invoke_coach_invalid_decision_value(
        self, agent_invoker, worktree_path, sample_player_report
    ):
        """Raises error if Coach decision has invalid value."""
        # Setup: Create decision with invalid value
        invalid_decision = {
            "task_id": "TASK-001",
            "turn": 1,
            "decision": "maybe",  # Invalid - must be "approve" or "feedback"
        }
        create_report_file(
            worktree_path, "TASK-001", 1, "coach", invalid_decision
        )

        # Mock SDK
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            # Execute
            result = await agent_invoker.invoke_coach(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
                player_report=sample_player_report,
            )

            # Verify
            assert result.success is False
            assert "validation failed" in result.error


# ==================== Prompt Building Tests ====================


class TestPromptBuilding:
    """Test prompt construction."""

    def test_build_player_prompt_first_turn(self, agent_invoker):
        """Player prompt for turn 1 has no feedback section."""
        prompt = agent_invoker._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2 authentication",
            feedback=None,
        )

        assert "Task ID: TASK-001" in prompt
        assert "Turn: 1" in prompt
        assert "Implement OAuth2 authentication" in prompt
        assert "Coach Feedback" not in prompt
        assert ".guardkit/autobuild/TASK-001/player_turn_1.json" in prompt

    def test_build_player_prompt_with_feedback(self, agent_invoker):
        """Player prompt includes feedback from previous turn."""
        feedback = "Please add error handling for token expiration"
        prompt = agent_invoker._build_player_prompt(
            task_id="TASK-001",
            turn=2,
            requirements="Implement OAuth2 authentication",
            feedback=feedback,
        )

        assert "Turn: 2" in prompt
        assert "Coach Feedback from Turn 1" in prompt
        assert feedback in prompt
        assert "Please address all feedback points" in prompt

    def test_build_coach_prompt(self, agent_invoker, sample_player_report):
        """Coach prompt includes requirements and Player report."""
        prompt = agent_invoker._build_coach_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2 authentication",
            player_report=sample_player_report,
        )

        assert "Task ID: TASK-001" in prompt
        assert "Turn: 1" in prompt
        assert "Implement OAuth2 authentication" in prompt
        assert "Player's Report" in prompt
        assert ".guardkit/autobuild/TASK-001/coach_turn_1.json" in prompt
        # Verify Player report is included as JSON
        assert '"task_id": "TASK-001"' in prompt
        assert '"tests_passed": true' in prompt


# ==================== Report Validation Tests ====================


class TestReportValidation:
    """Test report validation."""

    def test_validate_player_report_valid(self, agent_invoker, sample_player_report):
        """Valid Player report passes validation."""
        # Should not raise
        agent_invoker._validate_player_report(sample_player_report)

    def test_validate_player_report_missing_field(self, agent_invoker):
        """Raises error if required field missing."""
        incomplete_report = {
            "task_id": "TASK-001",
            "turn": 1,
            # Missing other required fields
        }

        with pytest.raises(PlayerReportInvalidError) as exc_info:
            agent_invoker._validate_player_report(incomplete_report)

        assert "Missing fields" in str(exc_info.value)
        assert "files_modified" in str(exc_info.value)

    def test_validate_player_report_wrong_type(self, agent_invoker, sample_player_report):
        """Raises error if field has wrong type."""
        invalid_report = sample_player_report.copy()
        invalid_report["tests_run"] = "yes"  # Should be bool

        with pytest.raises(PlayerReportInvalidError) as exc_info:
            agent_invoker._validate_player_report(invalid_report)

        assert "Type errors" in str(exc_info.value)

    def test_validate_coach_decision_approve(self, agent_invoker, sample_coach_approval):
        """Valid Coach approval passes validation."""
        # Should not raise
        agent_invoker._validate_coach_decision(sample_coach_approval)

    def test_validate_coach_decision_feedback(self, agent_invoker, sample_coach_feedback):
        """Valid Coach feedback passes validation."""
        # Should not raise
        agent_invoker._validate_coach_decision(sample_coach_feedback)

    def test_validate_coach_decision_invalid_value(self, agent_invoker):
        """Raises error if decision value is invalid."""
        invalid_decision = {
            "task_id": "TASK-001",
            "turn": 1,
            "decision": "maybe",  # Invalid
        }

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            agent_invoker._validate_coach_decision(invalid_decision)

        assert "must be 'approve' or 'feedback'" in str(exc_info.value)


# ==================== SDK Integration Tests ====================


class TestSDKIntegration:
    """Test SDK integration patterns."""

    @pytest.mark.asyncio
    async def test_sdk_invocation_calls_query(self, agent_invoker):
        """SDK invocation calls claude_agent_sdk.query() with correct options."""
        # Create async generator mock for query()
        async def mock_query_gen(*args, **kwargs):
            yield MagicMock(type="assistant")
            yield MagicMock(type="result", subtype="success")

        # Create mock SDK module
        mock_sdk = MagicMock()
        mock_sdk.query = mock_query_gen
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
        mock_sdk.ProcessError = type("ProcessError", (Exception,), {})
        mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            await agent_invoker._invoke_with_role(
                prompt="Test prompt",
                agent_type="player",
                allowed_tools=["Read", "Write"],
                permission_mode="acceptEdits",
                model="claude-sonnet-4-5-20250929",
            )

            # Verify ClaudeAgentOptions was constructed correctly
            mock_sdk.ClaudeAgentOptions.assert_called_once()
            options_kwargs = mock_sdk.ClaudeAgentOptions.call_args.kwargs
            assert options_kwargs["cwd"] == str(agent_invoker.worktree_path)
            assert options_kwargs["allowed_tools"] == ["Read", "Write"]
            assert options_kwargs["permission_mode"] == "acceptEdits"
            assert options_kwargs["max_turns"] == agent_invoker.max_turns_per_agent
            assert options_kwargs["model"] == "claude-sonnet-4-5-20250929"
            assert options_kwargs["setting_sources"] == ["project"]

    @pytest.mark.asyncio
    async def test_sdk_handles_cli_not_found(self, agent_invoker):
        """SDK raises AgentInvocationError when CLI not found."""
        # Create mock SDK module with CLINotFoundError
        CLINotFoundError = type("CLINotFoundError", (Exception,), {})

        async def mock_query_error(*args, **kwargs):
            raise CLINotFoundError("Claude Code not found")
            yield  # Make it a generator

        mock_sdk = MagicMock()
        mock_sdk.query = mock_query_error
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.CLINotFoundError = CLINotFoundError
        mock_sdk.ProcessError = type("ProcessError", (Exception,), {})
        mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            with pytest.raises(AgentInvocationError) as exc_info:
                await agent_invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )

            assert "Claude Code CLI not installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sdk_handles_import_error(self, agent_invoker):
        """SDK raises AgentInvocationError when SDK not installed."""
        # Patch the import to raise ImportError
        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": None}):
            with pytest.raises(AgentInvocationError) as exc_info:
                await agent_invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )

            assert "Claude Agent SDK not installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sdk_handles_timeout(self, agent_invoker):
        """SDK raises SDKTimeoutError when invocation times out."""
        async def mock_query_timeout(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate long-running operation
            yield MagicMock()

        # Create mock SDK module
        mock_sdk = MagicMock()
        mock_sdk.query = mock_query_timeout
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
        mock_sdk.ProcessError = type("ProcessError", (Exception,), {})
        mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

        # Set a very short timeout for testing
        agent_invoker.sdk_timeout_seconds = 0.01

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            with pytest.raises(SDKTimeoutError) as exc_info:
                await agent_invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_coach_uses_bypass_permissions(self, agent_invoker, worktree_path, sample_player_report, sample_coach_approval):
        """Coach invocation uses bypassPermissions mode."""
        # Setup: Create Coach decision file
        create_report_file(
            worktree_path, "TASK-001", 1, "coach", sample_coach_approval
        )

        # Create async generator mock for query()
        async def mock_query_gen(*args, **kwargs):
            yield MagicMock(type="result")

        mock_sdk = MagicMock()
        mock_sdk.query = mock_query_gen
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
        mock_sdk.ProcessError = type("ProcessError", (Exception,), {})
        mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            await agent_invoker.invoke_coach(
                task_id="TASK-001",
                turn=1,
                requirements="Test requirements",
                player_report=sample_player_report,
            )

            # Verify Coach uses bypassPermissions
            options_kwargs = mock_sdk.ClaudeAgentOptions.call_args.kwargs
            assert options_kwargs["permission_mode"] == "bypassPermissions"
            assert "Write" not in options_kwargs["allowed_tools"]
            assert "Edit" not in options_kwargs["allowed_tools"]

    @pytest.mark.asyncio
    async def test_fresh_context_per_turn(self, agent_invoker, worktree_path, sample_player_report):
        """Each invocation creates new SDK session (no context pollution)."""
        # Setup: Create report files for multiple turns
        create_report_file(worktree_path, "TASK-001", 1, "player", sample_player_report)
        create_report_file(worktree_path, "TASK-001", 2, "player", sample_player_report)

        # Mock SDK to track invocations
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ) as mock_sdk:
            # Execute turn 1
            await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=1,
                requirements="Implement OAuth2 authentication",
            )

            # Execute turn 2
            await agent_invoker.invoke_player(
                task_id="TASK-001",
                turn=2,
                requirements="Implement OAuth2 authentication",
                feedback="Add error handling",
            )

            # Verify SDK was called twice (fresh context each time)
            assert mock_sdk.call_count == 2

            # Verify each call had different prompts (turn 2 has feedback)
            call_1_prompt = mock_sdk.call_args_list[0].kwargs["prompt"]
            call_2_prompt = mock_sdk.call_args_list[1].kwargs["prompt"]

            assert "Turn: 1" in call_1_prompt
            assert "Turn: 2" in call_2_prompt
            assert "Coach Feedback" not in call_1_prompt
            assert "Coach Feedback" in call_2_prompt


# ==================== Helper Method Tests ====================


class TestHelperMethods:
    """Test internal helper methods."""

    def test_get_report_path_player(self, agent_invoker, worktree_path):
        """Get correct path for Player report."""
        path = agent_invoker._get_report_path("TASK-001", 1, "player")

        expected = worktree_path / ".guardkit" / "autobuild" / "TASK-001" / "player_turn_1.json"
        assert path == expected

    def test_get_report_path_coach(self, agent_invoker, worktree_path):
        """Get correct path for Coach decision."""
        path = agent_invoker._get_report_path("TASK-001", 1, "coach")

        expected = worktree_path / ".guardkit" / "autobuild" / "TASK-001" / "coach_turn_1.json"
        assert path == expected

    def test_load_agent_report_success(
        self, agent_invoker, worktree_path, sample_player_report
    ):
        """Load agent report successfully."""
        # Setup
        create_report_file(worktree_path, "TASK-001", 1, "player", sample_player_report)

        # Execute
        report = agent_invoker._load_agent_report("TASK-001", 1, "player")

        # Verify
        assert report == sample_player_report

    def test_load_agent_report_not_found_player(self, agent_invoker):
        """Raise PlayerReportNotFoundError if report doesn't exist."""
        with pytest.raises(PlayerReportNotFoundError) as exc_info:
            agent_invoker._load_agent_report("TASK-001", 1, "player")

        assert "Player report not found" in str(exc_info.value)

    def test_load_agent_report_not_found_coach(self, agent_invoker):
        """Raise CoachDecisionNotFoundError if decision doesn't exist."""
        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            agent_invoker._load_agent_report("TASK-001", 1, "coach")

        assert "Coach decision not found" in str(exc_info.value)


# ==================== Task-Work Delegation Tests ====================


class TestTaskWorkDelegation:
    """Test task-work delegation functionality."""

    @pytest.fixture
    def delegation_invoker(self, worktree_path):
        """Create AgentInvoker with task-work delegation enabled."""
        return AgentInvoker(
            worktree_path=worktree_path,
            max_turns_per_agent=30,
            sdk_timeout_seconds=60,
            use_task_work_delegation=True,
        )

    @pytest.fixture
    def legacy_invoker(self, worktree_path):
        """Create AgentInvoker with task-work delegation disabled (legacy)."""
        return AgentInvoker(
            worktree_path=worktree_path,
            max_turns_per_agent=30,
            sdk_timeout_seconds=60,
            use_task_work_delegation=False,
        )

    def test_init_with_delegation_enabled(self, worktree_path):
        """AgentInvoker can be initialized with task-work delegation enabled."""
        invoker = AgentInvoker(
            worktree_path=worktree_path,
            use_task_work_delegation=True,
        )
        assert invoker.use_task_work_delegation is True

    def test_init_with_delegation_disabled(self, worktree_path):
        """AgentInvoker can be initialized with task-work delegation disabled."""
        invoker = AgentInvoker(
            worktree_path=worktree_path,
            use_task_work_delegation=False,
        )
        assert invoker.use_task_work_delegation is False

    def test_init_defaults_to_env_var(self, worktree_path):
        """AgentInvoker defaults use_task_work_delegation to USE_TASK_WORK_DELEGATION."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        assert invoker.use_task_work_delegation == USE_TASK_WORK_DELEGATION


class TestWriteCoachFeedback:
    """Test _write_coach_feedback method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            use_task_work_delegation=True,
        )

    def test_write_coach_feedback_creates_file(self, invoker, worktree_path):
        """_write_coach_feedback creates feedback file in correct location."""
        feedback = "Please add error handling for edge cases."

        path = invoker._write_coach_feedback(
            task_id="TASK-001",
            turn=2,
            feedback=feedback,
        )

        # Verify file exists
        assert path.exists()

        # Verify path is correct
        expected_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-001" /
            "coach_feedback_for_turn_2.md"
        )
        assert path == expected_path

    def test_write_coach_feedback_content(self, invoker, worktree_path):
        """_write_coach_feedback writes correct content."""
        feedback = "Add unit tests for the authentication module."

        path = invoker._write_coach_feedback(
            task_id="TASK-001",
            turn=3,
            feedback=feedback,
        )

        content = path.read_text()

        # Verify content includes feedback
        assert "Add unit tests for the authentication module." in content
        assert "Turn 3" in content
        assert "Turn 2" in content  # Feedback is from previous turn

    def test_write_coach_feedback_creates_directories(self, invoker, worktree_path):
        """_write_coach_feedback creates parent directories if needed."""
        feedback = "Test feedback"

        path = invoker._write_coach_feedback(
            task_id="TASK-NEW",
            turn=2,
            feedback=feedback,
        )

        # Verify directories were created
        assert (worktree_path / ".guardkit" / "autobuild" / "TASK-NEW").is_dir()
        assert path.exists()


class TestInvokeTaskWorkImplement:
    """Test _invoke_task_work_implement method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
            use_task_work_delegation=True,
        )

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_success(self, invoker, worktree_path):
        """_invoke_task_work_implement returns success on exit code 0."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(
                b"All tests passing\nCoverage: 85.2%\nIN_REVIEW",
                b"",
            )
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            # Verify result
            assert result.success is True
            assert result.exit_code == 0
            assert result.error is None

            # Verify subprocess was called correctly
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args
            assert "guardkit" in call_args.args
            assert "task-work" in call_args.args
            assert "TASK-001" in call_args.args
            assert "--implement-only" in call_args.args
            assert "--mode=tdd" in call_args.args
            assert call_args.kwargs["cwd"] == str(worktree_path)

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_failure(self, invoker):
        """_invoke_task_work_implement returns failure on non-zero exit code."""
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"Error: tests failed")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="standard",
            )

            # Verify result
            assert result.success is False
            assert result.exit_code == 1
            assert "Error: tests failed" in result.error

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_timeout(self, invoker):
        """_invoke_task_work_implement raises SDKTimeoutError on timeout."""
        # Set very short timeout
        invoker.sdk_timeout_seconds = 0.001

        # Mock subprocess that takes too long
        mock_process = AsyncMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        mock_process.communicate = slow_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with pytest.raises(SDKTimeoutError) as exc_info:
                await invoker._invoke_task_work_implement(
                    task_id="TASK-001",
                    mode="tdd",
                )

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_command_not_found(self, invoker):
        """_invoke_task_work_implement handles missing guardkit command."""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            assert result.success is False
            assert "guardkit command not found" in result.error
            assert result.exit_code == -1

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_mode_passed(self, invoker, worktree_path):
        """_invoke_task_work_implement passes mode parameter correctly."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="standard",
            )

            call_args = mock_exec.call_args
            assert "--mode=standard" in call_args.args


class TestParseTaskWorkOutput:
    """Test _parse_task_work_output method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_parse_output_with_all_metrics(self, invoker):
        """Parse output with all metrics present."""
        stdout = """
Task Work Complete - TASK-001

✅ All tests passing!

Test Results:
- Passed: 15
- Failed: 0

Coverage: 85.2%
Branch Coverage: 78.5%

All quality gates passed
IN_REVIEW
"""
        result = invoker._parse_task_work_output(stdout)

        assert result["tests_passed"] is True
        assert result["coverage_line"] == 85.2
        assert result["coverage_branch"] == 78.5
        assert result["quality_gates_passed"] is True
        assert "All tests passing" in result["raw_output"]

    def test_parse_output_with_no_metrics(self, invoker):
        """Parse output with no metrics."""
        stdout = "Some generic output without metrics"

        result = invoker._parse_task_work_output(stdout)

        assert result["tests_passed"] is False
        assert result["coverage_line"] is None
        assert result["coverage_branch"] is None
        assert result["quality_gates_passed"] is False

    def test_parse_output_with_checkmark(self, invoker):
        """Parse output with checkmark emoji indicates tests passed."""
        stdout = "Tests: ✅ 10/10 passed"

        result = invoker._parse_task_work_output(stdout)

        assert result["tests_passed"] is True

    def test_parse_output_line_coverage_formats(self, invoker):
        """Parse various line coverage formats."""
        test_cases = [
            ("Line coverage: 90%", 90.0),
            ("Coverage: 85.5%", 85.5),
            ("coverage:75%", 75.0),
        ]

        for stdout, expected in test_cases:
            result = invoker._parse_task_work_output(stdout)
            assert result["coverage_line"] == expected, f"Failed for: {stdout}"


class TestInvokePlayerWithDelegation:
    """Test invoke_player method with task-work delegation."""

    @pytest.fixture
    def delegation_invoker(self, worktree_path):
        """Create AgentInvoker with task-work delegation enabled."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
            use_task_work_delegation=True,
        )

    @pytest.mark.asyncio
    async def test_invoke_player_uses_delegation(
        self, delegation_invoker, worktree_path, sample_player_report
    ):
        """invoke_player uses task-work delegation when enabled."""
        # Setup: Create Player report file that task-work would create
        create_report_file(
            worktree_path, "TASK-001", 1, "player", sample_player_report
        )

        # Mock _invoke_task_work_implement
        mock_result = TaskWorkResult(
            success=True,
            output={"tests_passed": True},
            exit_code=0,
        )
        with patch.object(
            delegation_invoker,
            "_ensure_design_approved_state",
        ):
            with patch.object(
                delegation_invoker,
                "_invoke_task_work_implement",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_invoke:
                result = await delegation_invoker.invoke_player(
                    task_id="TASK-001",
                    turn=1,
                    requirements="Implement feature",
                    mode="tdd",
                )

                # Verify delegation was called
                mock_invoke.assert_called_once_with(
                    task_id="TASK-001",
                    mode="tdd",
                )

                # Verify result
                assert result.success is True
                assert result.agent_type == "player"
                assert result.report == sample_player_report

    @pytest.mark.asyncio
    async def test_invoke_player_writes_feedback_before_delegation(
        self, delegation_invoker, worktree_path, sample_player_report
    ):
        """invoke_player writes feedback before delegating."""
        # Setup
        create_report_file(
            worktree_path, "TASK-001", 2, "player", sample_player_report
        )
        feedback = "Please fix the error handling"

        mock_result = TaskWorkResult(
            success=True,
            output={},
            exit_code=0,
        )

        with patch.object(
            delegation_invoker,
            "_ensure_design_approved_state",
        ):
            with patch.object(
                delegation_invoker,
                "_invoke_task_work_implement",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                with patch.object(
                    delegation_invoker,
                    "_write_coach_feedback",
                ) as mock_write:
                    await delegation_invoker.invoke_player(
                        task_id="TASK-001",
                        turn=2,
                        requirements="Implement feature",
                        feedback=feedback,
                    )

                    # Verify feedback was written
                    mock_write.assert_called_once_with("TASK-001", 2, feedback)

    @pytest.mark.asyncio
    async def test_invoke_player_skips_feedback_on_turn_1(
        self, delegation_invoker, worktree_path, sample_player_report
    ):
        """invoke_player doesn't write feedback on turn 1."""
        # Setup
        create_report_file(
            worktree_path, "TASK-001", 1, "player", sample_player_report
        )

        mock_result = TaskWorkResult(
            success=True,
            output={},
            exit_code=0,
        )

        with patch.object(
            delegation_invoker,
            "_ensure_design_approved_state",
        ):
            with patch.object(
                delegation_invoker,
                "_invoke_task_work_implement",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                with patch.object(
                    delegation_invoker,
                    "_write_coach_feedback",
                ) as mock_write:
                    await delegation_invoker.invoke_player(
                        task_id="TASK-001",
                        turn=1,
                        requirements="Implement feature",
                        feedback=None,  # No feedback on turn 1
                    )

                    # Verify feedback was NOT written
                    mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoke_player_returns_error_on_delegation_failure(
        self, delegation_invoker, worktree_path
    ):
        """invoke_player returns error when delegation fails."""
        mock_result = TaskWorkResult(
            success=False,
            output={},
            error="task-work failed: tests not passing",
            exit_code=1,
        )

        with patch.object(
            delegation_invoker,
            "_ensure_design_approved_state",
        ):
            with patch.object(
                delegation_invoker,
                "_invoke_task_work_implement",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await delegation_invoker.invoke_player(
                    task_id="TASK-001",
                    turn=1,
                    requirements="Implement feature",
                )

                # Verify error is returned
                assert result.success is False
                assert "task-work failed" in result.error
                assert result.report == {}


class TestInvokePlayerLegacy:
    """Test invoke_player method with legacy SDK invocation."""

    @pytest.fixture
    def legacy_invoker(self, worktree_path):
        """Create AgentInvoker with task-work delegation disabled."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
            use_task_work_delegation=False,
        )

    @pytest.mark.asyncio
    async def test_invoke_player_uses_legacy_sdk(
        self, legacy_invoker, worktree_path, sample_player_report
    ):
        """invoke_player uses direct SDK when delegation disabled."""
        # Setup: Create Player report file
        create_report_file(
            worktree_path, "TASK-001", 1, "player", sample_player_report
        )

        # Mock SDK invocation
        with patch.object(
            legacy_invoker, "_invoke_with_role", new_callable=AsyncMock
        ) as mock_sdk:
            result = await legacy_invoker.invoke_player(
                task_id="TASK-001",
                turn=1,
                requirements="Implement feature",
            )

            # Verify SDK was called (not delegation)
            mock_sdk.assert_called_once()

            # Verify result
            assert result.success is True
            assert result.report == sample_player_report
