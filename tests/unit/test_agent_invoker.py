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
    DOCUMENTATION_LEVEL_MAX_FILES,
    TaskWorkStreamParser,
    TASK_WORK_SDK_MAX_TURNS,
    USE_TASK_WORK_DELEGATION,
    async_heartbeat,
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
        assert invoker.sdk_timeout_seconds == 900  # Harmonized default per TASK-FIX-SDKT
        assert invoker.development_mode == "tdd"  # Default is tdd

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

    def test_init_with_development_mode(self, worktree_path):
        """AgentInvoker accepts development_mode parameter."""
        invoker = AgentInvoker(
            worktree_path=worktree_path,
            development_mode="standard",
        )
        assert invoker.development_mode == "standard"

        invoker_bdd = AgentInvoker(
            worktree_path=worktree_path,
            development_mode="bdd",
        )
        assert invoker_bdd.development_mode == "bdd"


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
            # Check core fields from sample_coach_approval are present
            assert result.report["decision"] == sample_coach_approval["decision"]
            assert result.report["task_id"] == sample_coach_approval["task_id"]
            assert result.report["turn"] == sample_coach_approval["turn"]
            # Honesty verification is now added by invoke_coach
            assert "honesty_verification" in result.report
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
            # TASK-REV-C4D7: Direct mode now uses TASK_WORK_SDK_MAX_TURNS (50)
            # instead of agent_invoker.max_turns_per_agent
            assert options_kwargs["max_turns"] == TASK_WORK_SDK_MAX_TURNS
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
        """SDK raises AgentInvocationError with diagnostic info when SDK not installed.

        The error message includes:
        - Actual ImportError message
        - Python executable path
        - First 3 sys.path entries
        - Installation options
        """
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

            error_message = str(exc_info.value)
            # Verify the error message contains expected diagnostic components
            assert "Claude Agent SDK import failed" in error_message
            assert "Error:" in error_message
            assert "Python:" in error_message
            assert "sys.path" in error_message
            assert "pip install" in error_message

    @pytest.mark.asyncio
    async def test_sdk_import_error_includes_diagnostic_info(self, agent_invoker):
        """SDK ImportError includes complete diagnostic information.

        Test verifies all diagnostic components are present:
        - Error message label
        - Python executable path
        - sys.path entries
        - Both installation options
        """
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

            error_message = str(exc_info.value)

            # Verify all diagnostic components
            assert "Error:" in error_message, "Missing 'Error:' label in diagnostic"
            assert "Python:" in error_message, "Missing 'Python:' label for executable path"
            assert "sys.path" in error_message, "Missing 'sys.path' diagnostic info"

            # Verify installation options
            assert "pip install claude-agent-sdk" in error_message, \
                "Missing 'pip install claude-agent-sdk' installation option"
            assert "pip install guardkit-py[autobuild]" in error_message, \
                "Missing 'pip install guardkit-py[autobuild]' installation option"

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

    def test_write_coach_feedback_creates_json_file(self, invoker, worktree_path):
        """_write_coach_feedback creates JSON feedback file in correct location."""
        feedback = "Please add error handling for edge cases."

        path = invoker._write_coach_feedback(
            task_id="TASK-001",
            turn=2,
            feedback=feedback,
        )

        # Verify file exists
        assert path.exists()

        # Verify path is correct (now JSON format)
        expected_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-001" /
            "coach_feedback_for_turn_2.json"
        )
        assert path == expected_path

    def test_write_coach_feedback_string_content(self, invoker, worktree_path):
        """_write_coach_feedback writes string feedback as structured JSON."""
        feedback = "Add unit tests for the authentication module."

        path = invoker._write_coach_feedback(
            task_id="TASK-001",
            turn=3,
            feedback=feedback,
        )

        # Load and verify JSON content
        with open(path) as f:
            content = json.load(f)

        # Verify structure
        assert content["turn"] == 3
        assert content["feedback_from_turn"] == 2
        assert content["feedback_summary"] == feedback
        assert content["raw_feedback"] == feedback
        assert content["must_fix"] == []
        assert content["should_fix"] == []

    def test_write_coach_feedback_dict_content(self, invoker, worktree_path):
        """_write_coach_feedback writes dict feedback with issues categorization."""
        feedback = {
            "task_id": "TASK-001",
            "turn": 1,
            "decision": "feedback",
            "rationale": "Missing error handling",
            "issues": [
                {
                    "type": "missing_requirement",
                    "severity": "critical",
                    "description": "No error handling for network failures",
                    "location": "src/api/client.py:45",
                    "suggestion": "Add try/except with retry logic",
                },
                {
                    "type": "code_quality",
                    "severity": "minor",
                    "description": "Consider extracting helper",
                    "location": "src/api/client.py:30-60",
                    "suggestion": "Create _make_request() method",
                },
            ],
            "validation_results": {
                "tests_run": True,
                "tests_passed": False,
                "test_output_summary": "2 failed, 8 passed",
            },
        }

        path = invoker._write_coach_feedback(
            task_id="TASK-001",
            turn=2,
            feedback=feedback,
        )

        # Load and verify JSON content
        with open(path) as f:
            content = json.load(f)

        # Verify structure
        assert content["turn"] == 2
        assert content["feedback_from_turn"] == 1
        assert content["feedback_summary"] == "Missing error handling"

        # Verify must_fix contains critical issues
        assert len(content["must_fix"]) == 1
        assert content["must_fix"][0]["issue"] == "No error handling for network failures"
        assert content["must_fix"][0]["location"] == "src/api/client.py:45"

        # Verify should_fix contains minor issues
        assert len(content["should_fix"]) == 1
        assert content["should_fix"][0]["issue"] == "Consider extracting helper"

        # Verify validation results preserved
        assert content["validation_results"]["tests_passed"] is False

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


class TestLoadCoachFeedback:
    """Test load_coach_feedback method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            use_task_work_delegation=True,
        )

    def test_load_coach_feedback_success(self, invoker, worktree_path):
        """load_coach_feedback loads existing feedback file."""
        # Create feedback file
        feedback_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        feedback_dir.mkdir(parents=True)
        feedback_path = feedback_dir / "coach_feedback_for_turn_2.json"
        feedback_data = {
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Add more tests",
            "must_fix": [{"issue": "Missing tests", "location": "src/auth.py"}],
            "should_fix": [],
            "validation_results": {},
        }
        with open(feedback_path, "w") as f:
            json.dump(feedback_data, f)

        # Load feedback
        result = invoker.load_coach_feedback("TASK-001", 2)

        assert result is not None
        assert result["turn"] == 2
        assert result["feedback_summary"] == "Add more tests"
        assert len(result["must_fix"]) == 1

    def test_load_coach_feedback_not_found(self, invoker):
        """load_coach_feedback returns None when file doesn't exist."""
        result = invoker.load_coach_feedback("TASK-NONEXISTENT", 2)
        assert result is None

    def test_load_coach_feedback_invalid_json(self, invoker, worktree_path):
        """load_coach_feedback returns None on invalid JSON."""
        # Create invalid JSON file
        feedback_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        feedback_dir.mkdir(parents=True)
        feedback_path = feedback_dir / "coach_feedback_for_turn_2.json"
        feedback_path.write_text("{ invalid json }")

        result = invoker.load_coach_feedback("TASK-001", 2)
        assert result is None


class TestFormatFeedbackForPrompt:
    """Test format_feedback_for_prompt method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_format_feedback_with_must_fix(self, invoker):
        """format_feedback_for_prompt formats must-fix issues."""
        feedback = {
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Critical issues found",
            "must_fix": [
                {
                    "issue": "No error handling",
                    "location": "src/api/client.py:45",
                    "suggestion": "Add try/except",
                },
            ],
            "should_fix": [],
            "validation_results": {},
        }

        result = invoker.format_feedback_for_prompt(feedback)

        assert "Coach Feedback from Turn 1" in result
        assert "Critical issues found" in result
        assert "MUST FIX" in result
        assert "No error handling" in result
        assert "src/api/client.py:45" in result
        assert "Add try/except" in result

    def test_format_feedback_with_should_fix(self, invoker):
        """format_feedback_for_prompt formats should-fix issues."""
        feedback = {
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Minor improvements needed",
            "must_fix": [],
            "should_fix": [
                {
                    "issue": "Consider refactoring",
                    "location": "src/utils.py:10-30",
                    "suggestion": "Extract helper function",
                },
            ],
            "validation_results": {},
        }

        result = invoker.format_feedback_for_prompt(feedback)

        assert "SHOULD FIX" in result
        assert "Consider refactoring" in result
        assert "Extract helper function" in result

    def test_format_feedback_with_validation_results(self, invoker):
        """format_feedback_for_prompt includes validation results."""
        feedback = {
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Tests failing",
            "must_fix": [],
            "should_fix": [],
            "validation_results": {
                "tests_passed": False,
                "test_output_summary": "2 failed, 8 passed",
                "code_quality": "Needs improvement",
            },
        }

        result = invoker.format_feedback_for_prompt(feedback)

        assert "Validation Results" in result
        assert "❌ Failed" in result
        assert "2 failed, 8 passed" in result
        assert "Needs improvement" in result

    def test_format_feedback_prioritizes_must_fix(self, invoker):
        """format_feedback_for_prompt shows must-fix before should-fix."""
        feedback = {
            "turn": 2,
            "feedback_from_turn": 1,
            "feedback_summary": "Multiple issues",
            "must_fix": [{"issue": "Critical bug", "location": "", "suggestion": ""}],
            "should_fix": [{"issue": "Minor improvement", "location": "", "suggestion": ""}],
            "validation_results": {},
        }

        result = invoker.format_feedback_for_prompt(feedback)

        # Must fix should appear before should fix
        must_fix_pos = result.find("MUST FIX")
        should_fix_pos = result.find("SHOULD FIX")
        assert must_fix_pos < should_fix_pos


class TestParseCoachFeedback:
    """Test _parse_coach_feedback method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_parse_string_feedback(self, invoker):
        """_parse_coach_feedback handles plain string feedback."""
        result = invoker._parse_coach_feedback("Please add more tests", 2)

        assert result["turn"] == 2
        assert result["feedback_from_turn"] == 1
        assert result["feedback_summary"] == "Please add more tests"
        assert result["raw_feedback"] == "Please add more tests"
        assert result["must_fix"] == []
        assert result["should_fix"] == []

    def test_parse_dict_feedback_critical(self, invoker):
        """_parse_coach_feedback categorizes critical issues as must-fix."""
        feedback = {
            "rationale": "Security issue found",
            "issues": [
                {
                    "description": "SQL injection vulnerability",
                    "severity": "critical",
                    "location": "src/db.py:42",
                    "suggestion": "Use parameterized queries",
                    "type": "security",
                },
            ],
            "validation_results": {"tests_passed": True},
        }

        result = invoker._parse_coach_feedback(feedback, 2)

        assert result["feedback_summary"] == "Security issue found"
        assert len(result["must_fix"]) == 1
        assert result["must_fix"][0]["issue"] == "SQL injection vulnerability"
        assert result["must_fix"][0]["type"] == "security"
        assert len(result["should_fix"]) == 0
        assert result["validation_results"]["tests_passed"] is True

    def test_parse_dict_feedback_major(self, invoker):
        """_parse_coach_feedback categorizes major issues as must-fix."""
        feedback = {
            "issues": [
                {
                    "description": "Missing error handling",
                    "severity": "major",
                    "location": "src/api.py:10",
                },
            ],
        }

        result = invoker._parse_coach_feedback(feedback, 2)

        assert len(result["must_fix"]) == 1
        assert len(result["should_fix"]) == 0

    def test_parse_dict_feedback_minor(self, invoker):
        """_parse_coach_feedback categorizes minor issues as should-fix."""
        feedback = {
            "issues": [
                {
                    "description": "Consider using helper function",
                    "severity": "minor",
                    "location": "src/utils.py:5",
                },
            ],
        }

        result = invoker._parse_coach_feedback(feedback, 2)

        assert len(result["must_fix"]) == 0
        assert len(result["should_fix"]) == 1
        assert result["should_fix"][0]["issue"] == "Consider using helper function"

    def test_parse_dict_feedback_mixed_severities(self, invoker):
        """_parse_coach_feedback properly categorizes mixed severity issues."""
        feedback = {
            "rationale": "Multiple issues found",
            "issues": [
                {"description": "Critical bug", "severity": "critical"},
                {"description": "Major issue", "severity": "major"},
                {"description": "Minor style", "severity": "minor"},
                {"description": "Unknown severity"},  # No severity - should be should-fix
            ],
        }

        result = invoker._parse_coach_feedback(feedback, 3)

        assert len(result["must_fix"]) == 2  # critical + major
        assert len(result["should_fix"]) == 2  # minor + unknown


class TestInvokeTaskWorkImplement:
    """Test _invoke_task_work_implement method with SDK query() invocation."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
            use_task_work_delegation=True,
        )

    def _create_mock_sdk(self, query_gen):
        """Create mock SDK module with given query generator.

        TASK-FB-FIX-013: Updated to include AssistantMessage, TextBlock, and other
        message types for proper ContentBlock iteration testing.
        """
        mock_sdk = MagicMock()
        mock_sdk.query = query_gen
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
        mock_sdk.ProcessError = type("ProcessError", (Exception,), {"exit_code": 1, "stderr": ""})
        mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

        # TASK-FB-FIX-013: Add message type classes for isinstance() checks
        # These are real classes that isinstance() can check against
        class MockTextBlock:
            def __init__(self, text):
                self.type = "text"
                self.text = text

        class MockToolUseBlock:
            def __init__(self, name="test_tool"):
                self.type = "tool_use"
                self.name = name

        class MockToolResultBlock:
            def __init__(self, content=None):
                self.type = "tool_result"
                self.content = content

        class MockAssistantMessage:
            def __init__(self, content):
                self.content = content  # List of ContentBlocks

        class MockResultMessage:
            def __init__(self, num_turns=1):
                self.num_turns = num_turns

        mock_sdk.AssistantMessage = MockAssistantMessage
        mock_sdk.TextBlock = MockTextBlock
        mock_sdk.ToolUseBlock = MockToolUseBlock
        mock_sdk.ToolResultBlock = MockToolResultBlock
        mock_sdk.ResultMessage = MockResultMessage

        return mock_sdk

    def _create_assistant_message(self, mock_sdk, text):
        """Helper to create a properly-structured AssistantMessage with TextBlock content."""
        text_block = mock_sdk.TextBlock(text)
        return mock_sdk.AssistantMessage([text_block])

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_success(self, invoker, worktree_path):
        """_invoke_task_work_implement returns success when SDK query completes."""
        # TASK-FB-FIX-013: Use proper AssistantMessage with TextBlock content
        mock_sdk = self._create_mock_sdk(lambda *args, **kwargs: None)

        async def mock_query_gen(*args, **kwargs):
            # Simulate output with passing tests (TaskWorkStreamParser format)
            # Use proper AssistantMessage with TextBlock content
            text_block = mock_sdk.TextBlock("10 tests passed, 0 tests failed\nCoverage: 85.2%\nAll quality gates passed")
            yield mock_sdk.AssistantMessage([text_block])
            yield mock_sdk.ResultMessage(num_turns=5)

        mock_sdk.query = mock_query_gen

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            # Verify result
            assert result.success is True
            assert result.error is None
            # TaskWorkStreamParser returns test count as integer
            assert result.output.get("tests_passed") == 10
            assert result.output.get("tests_failed") == 0

            # Verify ClaudeAgentOptions was configured correctly
            mock_sdk.ClaudeAgentOptions.assert_called_once()
            options_kwargs = mock_sdk.ClaudeAgentOptions.call_args.kwargs
            assert options_kwargs["cwd"] == str(worktree_path)
            assert "Read" in options_kwargs["allowed_tools"]
            assert "Write" in options_kwargs["allowed_tools"]
            assert "Edit" in options_kwargs["allowed_tools"]
            assert "Bash" in options_kwargs["allowed_tools"]
            assert "Task" in options_kwargs["allowed_tools"]
            assert "Skill" in options_kwargs["allowed_tools"]
            assert options_kwargs["permission_mode"] == "acceptEdits"
            # TASK-REV-BB80: Uses dedicated TASK_WORK_SDK_MAX_TURNS constant (50)
            # NOT max_turns_per_agent, because task-work needs many internal turns
            assert options_kwargs["max_turns"] == 50
            # TASK-FB-FIX-014: Now includes "user" for skill loading
            assert options_kwargs["setting_sources"] == ["user", "project"]

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_sdk_process_error(self, invoker):
        """_invoke_task_work_implement returns failure on SDK ProcessError."""
        # Create ProcessError with required attributes
        ProcessError = type("ProcessError", (Exception,), {})

        async def mock_query_error(*args, **kwargs):
            error = ProcessError("Process failed")
            error.exit_code = 1
            error.stderr = "Error: tests failed"
            raise error
            yield  # Make it a generator

        mock_sdk = self._create_mock_sdk(mock_query_error)
        mock_sdk.ProcessError = ProcessError

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="standard",
            )

            # Verify result
            assert result.success is False
            assert "SDK process failed" in result.error

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_timeout(self, invoker):
        """_invoke_task_work_implement raises SDKTimeoutError on timeout."""
        # Set very short timeout
        invoker.sdk_timeout_seconds = 0.001

        async def mock_query_slow(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate long-running operation
            yield MagicMock()

        mock_sdk = self._create_mock_sdk(mock_query_slow)

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            with pytest.raises(SDKTimeoutError) as exc_info:
                await invoker._invoke_task_work_implement(
                    task_id="TASK-001",
                    mode="tdd",
                )

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_cli_not_found(self, invoker):
        """_invoke_task_work_implement handles missing Claude CLI."""
        CLINotFoundError = type("CLINotFoundError", (Exception,), {})

        async def mock_query_cli_error(*args, **kwargs):
            raise CLINotFoundError("Claude Code not found")
            yield  # Make it a generator

        mock_sdk = self._create_mock_sdk(mock_query_cli_error)
        mock_sdk.CLINotFoundError = CLINotFoundError

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            assert result.success is False
            assert "Claude Code CLI not installed" in result.error

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_sdk_import_error(self, invoker):
        """_invoke_task_work_implement handles missing SDK import."""
        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": None}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            assert result.success is False
            assert "Claude Agent SDK import failed" in result.error
            assert "pip install claude-agent-sdk" in result.error

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_mode_passed(self, invoker, worktree_path):
        """_invoke_task_work_implement passes mode parameter in prompt correctly."""
        captured_prompt = None

        async def mock_query_capture(*args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = kwargs.get("prompt") or (args[0] if args else None)
            yield MagicMock(content="Success")

        mock_sdk = self._create_mock_sdk(mock_query_capture)

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="standard",
            )

            # Verify the prompt contains the correct task-work command
            assert captured_prompt is not None
            assert "/task-work TASK-001 --implement-only --mode=standard" in captured_prompt

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_json_decode_error(self, invoker):
        """_invoke_task_work_implement handles SDK JSON decode errors."""
        CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

        async def mock_query_json_error(*args, **kwargs):
            raise CLIJSONDecodeError("Invalid JSON response")
            yield  # Make it a generator

        mock_sdk = self._create_mock_sdk(mock_query_json_error)
        mock_sdk.CLIJSONDecodeError = CLIJSONDecodeError

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            assert result.success is False
            assert "Failed to parse SDK response" in result.error

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_collects_output(self, invoker):
        """_invoke_task_work_implement collects message content for parsing."""
        # TASK-FB-FIX-013: Use proper AssistantMessage with TextBlock content
        mock_sdk = self._create_mock_sdk(lambda *args, **kwargs: None)

        async def mock_query_multi_message(*args, **kwargs):
            # Simulate multiple messages with content (TaskWorkStreamParser format)
            # Each message is an AssistantMessage with TextBlock content
            for content in ["Starting...", "8 tests passed, 0 tests failed", "Coverage: 90%", "All quality gates passed"]:
                text_block = mock_sdk.TextBlock(content)
                yield mock_sdk.AssistantMessage([text_block])
            yield mock_sdk.ResultMessage(num_turns=10)

        mock_sdk.query = mock_query_multi_message

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

            assert result.success is True
            # TaskWorkStreamParser returns test count as integer
            assert result.output.get("tests_passed") == 8
            # TaskWorkStreamParser uses 'coverage' not 'coverage_line'
            assert result.output.get("coverage") == 90.0
            assert result.output.get("quality_gates_passed") is True

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_writes_results_file(self, invoker, worktree_path):
        """_invoke_task_work_implement writes task_work_results.json after success."""
        # TASK-FB-FIX-013: Use proper AssistantMessage with TextBlock content
        mock_sdk = self._create_mock_sdk(lambda *args, **kwargs: None)

        async def mock_query_gen(*args, **kwargs):
            # Simulate output with passing tests and coverage
            text_block = mock_sdk.TextBlock("12 tests passed, 0 failed\nCoverage: 85.5%\nAll quality gates passed\nIN_REVIEW")
            yield mock_sdk.AssistantMessage([text_block])
            yield mock_sdk.ResultMessage(num_turns=8)

        mock_sdk.query = mock_query_gen

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-001",
                mode="tdd",
            )

        assert result.success is True

        # Verify results file was written
        results_path = worktree_path / ".guardkit" / "autobuild" / "TASK-001" / "task_work_results.json"
        assert results_path.exists(), "task_work_results.json should be written after successful invocation"

        # Verify content has required fields for Coach validation
        content = json.loads(results_path.read_text())
        assert content["task_id"] == "TASK-001"
        assert "quality_gates" in content
        assert "timestamp" in content
        assert "completed" in content

    @pytest.mark.asyncio
    async def test_invoke_task_work_implement_results_file_has_quality_gates(self, invoker, worktree_path):
        """_invoke_task_work_implement writes results with quality gate metrics."""
        # TASK-FB-FIX-013: Use proper AssistantMessage with TextBlock content
        mock_sdk = self._create_mock_sdk(lambda *args, **kwargs: None)

        async def mock_query_gen(*args, **kwargs):
            text_block = mock_sdk.TextBlock("15 tests passed, 0 failed\nCoverage: 92.5%\nAll quality gates passed")
            yield mock_sdk.AssistantMessage([text_block])
            yield mock_sdk.ResultMessage(num_turns=6)

        mock_sdk.query = mock_query_gen

        import sys
        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            result = await invoker._invoke_task_work_implement(
                task_id="TASK-QG-001",
                mode="standard",
            )

        assert result.success is True

        # Verify quality gates in results file
        results_path = worktree_path / ".guardkit" / "autobuild" / "TASK-QG-001" / "task_work_results.json"
        content = json.loads(results_path.read_text())

        quality_gates = content["quality_gates"]
        assert quality_gates["tests_passed"] == 15
        assert quality_gates["tests_failed"] == 0
        assert quality_gates["coverage"] == 92.5
        assert quality_gates["coverage_met"] is True
        assert quality_gates["tests_passing"] is True


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
        # Setup: Create task_work_results.json that task-work creates
        # (Player report is now created from this by _create_player_report_from_task_work)
        task_work_results = {
            "files_modified": ["src/auth.py"],
            "files_created": ["tests/test_auth.py"],
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
                "output_summary": "5 passed in 0.23s",
            },
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        autobuild_dir.mkdir(parents=True, exist_ok=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_results, indent=2)
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
                    documentation_level="minimal",
                )

                # Verify result
                assert result.success is True
                assert result.agent_type == "player"
                # Report is created from task_work_results.json
                assert result.report["task_id"] == "TASK-001"
                assert result.report["turn"] == 1
                assert result.report["files_modified"] == ["src/auth.py"]
                assert result.report["files_created"] == ["tests/test_auth.py"]
                assert result.report["tests_passed"] is True

    @pytest.mark.asyncio
    async def test_invoke_player_writes_feedback_before_delegation(
        self, delegation_invoker, worktree_path, sample_player_report
    ):
        """invoke_player writes feedback before delegating."""
        # Setup: Create task_work_results.json (Player report created from this)
        task_work_results = {"files_modified": [], "files_created": []}
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        autobuild_dir.mkdir(parents=True, exist_ok=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_results)
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
        # Setup: Create task_work_results.json (Player report created from this)
        task_work_results = {"files_modified": [], "files_created": []}
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        autobuild_dir.mkdir(parents=True, exist_ok=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_results)
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


# ==================== Acceptance Criteria Extraction Tests ====================


class TestExtractAcceptanceCriteria:
    """Test extract_acceptance_criteria method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    @pytest.fixture
    def task_dir(self, worktree_path):
        """Create task directory structure."""
        task_dir = worktree_path / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        return task_dir

    def test_extract_from_frontmatter(self, invoker, task_dir):
        """Extract acceptance criteria from YAML frontmatter."""
        task_content = """---
id: TASK-001
title: Implement OAuth2
acceptance_criteria:
  - OAuth2 authentication flow works correctly
  - Token refresh handles expiry edge case
  - Error responses are properly formatted
---

# Task Description

Implement OAuth2 authentication.
"""
        task_file = task_dir / "TASK-001.md"
        task_file.write_text(task_content)

        result = invoker.extract_acceptance_criteria("TASK-001")

        assert len(result) == 3
        assert result[0]["id"] == "AC-001"
        assert result[0]["text"] == "OAuth2 authentication flow works correctly"
        assert result[1]["id"] == "AC-002"
        assert result[1]["text"] == "Token refresh handles expiry edge case"
        assert result[2]["id"] == "AC-003"
        assert result[2]["text"] == "Error responses are properly formatted"

    def test_extract_from_body_bullets(self, invoker, task_dir):
        """Extract acceptance criteria from markdown body with bullets."""
        task_content = """---
id: TASK-002
title: Add Error Handling
---

# Task Description

Add error handling to the API.

## Acceptance Criteria

- All API errors return JSON format
- Error codes follow HTTP standards
- Stack traces are not exposed in production
"""
        task_file = task_dir / "TASK-002.md"
        task_file.write_text(task_content)

        result = invoker.extract_acceptance_criteria("TASK-002")

        assert len(result) == 3
        assert result[0]["id"] == "AC-001"
        assert result[0]["text"] == "All API errors return JSON format"
        assert result[1]["id"] == "AC-002"
        assert result[1]["text"] == "Error codes follow HTTP standards"

    def test_extract_from_body_numbered(self, invoker, task_dir):
        """Extract acceptance criteria from numbered list in body."""
        task_content = """---
id: TASK-003
title: Database Migration
---

# Description

Migrate database schema.

## Acceptance Criteria

1. All data is preserved during migration
2. Migration is reversible
3. Downtime is under 5 minutes
"""
        task_file = task_dir / "TASK-003.md"
        task_file.write_text(task_content)

        result = invoker.extract_acceptance_criteria("TASK-003")

        assert len(result) == 3
        assert result[0]["text"] == "All data is preserved during migration"
        assert result[1]["text"] == "Migration is reversible"
        assert result[2]["text"] == "Downtime is under 5 minutes"

    def test_extract_returns_empty_when_no_file(self, invoker):
        """Return empty list when task file doesn't exist."""
        result = invoker.extract_acceptance_criteria("TASK-NONEXISTENT")
        assert result == []

    def test_extract_returns_empty_when_no_criteria(self, invoker, task_dir):
        """Return empty list when no acceptance criteria found."""
        task_content = """---
id: TASK-004
title: Simple Task
---

# Description

A simple task with no acceptance criteria section.
"""
        task_file = task_dir / "TASK-004.md"
        task_file.write_text(task_content)

        result = invoker.extract_acceptance_criteria("TASK-004")
        assert result == []

    def test_extract_checks_multiple_directories(self, invoker, worktree_path):
        """Check multiple task directories for task file."""
        # Create task in backlog instead of in_progress
        backlog_dir = worktree_path / "tasks" / "backlog"
        backlog_dir.mkdir(parents=True)

        task_content = """---
id: TASK-005
title: Backlog Task
acceptance_criteria:
  - Criterion from backlog
---
"""
        task_file = backlog_dir / "TASK-005.md"
        task_file.write_text(task_content)

        result = invoker.extract_acceptance_criteria("TASK-005")

        assert len(result) == 1
        assert result[0]["text"] == "Criterion from backlog"

    def test_extract_checks_subdirectories(self, invoker, worktree_path):
        """Check subdirectories within task status directories."""
        # Create task in a feature subdirectory
        feature_dir = worktree_path / "tasks" / "in_progress" / "feature-auth"
        feature_dir.mkdir(parents=True)

        task_content = """---
id: TASK-006
title: Feature Task
acceptance_criteria:
  - Criterion from feature directory
---
"""
        task_file = feature_dir / "TASK-006.md"
        task_file.write_text(task_content)

        result = invoker.extract_acceptance_criteria("TASK-006")

        assert len(result) == 1
        assert result[0]["text"] == "Criterion from feature directory"


class TestParseCriteriaFromBody:
    """Test _parse_criteria_from_body method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_parse_bullet_points_dash(self, invoker):
        """Parse criteria with dash bullet points."""
        body = """
## Acceptance Criteria

- First criterion
- Second criterion
- Third criterion
"""
        result = invoker._parse_criteria_from_body(body)

        assert len(result) == 3
        assert result[0]["id"] == "AC-001"
        assert result[0]["text"] == "First criterion"
        assert result[1]["text"] == "Second criterion"
        assert result[2]["text"] == "Third criterion"

    def test_parse_bullet_points_asterisk(self, invoker):
        """Parse criteria with asterisk bullet points."""
        body = """
## Acceptance Criteria

* First item
* Second item
"""
        result = invoker._parse_criteria_from_body(body)

        assert len(result) == 2
        assert result[0]["text"] == "First item"
        assert result[1]["text"] == "Second item"

    def test_parse_numbered_list_dot(self, invoker):
        """Parse criteria with numbered list using dots."""
        body = """
## Acceptance Criteria

1. First numbered
2. Second numbered
3. Third numbered
"""
        result = invoker._parse_criteria_from_body(body)

        assert len(result) == 3
        assert result[0]["text"] == "First numbered"

    def test_parse_numbered_list_paren(self, invoker):
        """Parse criteria with numbered list using parentheses."""
        body = """
## Acceptance Criteria

1) First paren
2) Second paren
"""
        result = invoker._parse_criteria_from_body(body)

        assert len(result) == 2
        assert result[0]["text"] == "First paren"

    def test_parse_case_insensitive_header(self, invoker):
        """Parse with case-insensitive header matching."""
        body = """
## acceptance criteria

- Lowercase header criterion
"""
        result = invoker._parse_criteria_from_body(body)

        assert len(result) == 1
        assert result[0]["text"] == "Lowercase header criterion"

    def test_parse_stops_at_next_section(self, invoker):
        """Stop parsing at next ## section."""
        body = """
## Acceptance Criteria

- First criterion
- Second criterion

## Implementation Notes

This is not a criterion.
"""
        result = invoker._parse_criteria_from_body(body)

        assert len(result) == 2
        assert "Implementation Notes" not in str(result)

    def test_parse_returns_empty_when_no_section(self, invoker):
        """Return empty list when no acceptance criteria section."""
        body = """
## Description

Some description.

## Notes

Some notes.
"""
        result = invoker._parse_criteria_from_body(body)
        assert result == []

    def test_parse_handles_indented_items(self, invoker):
        """Handle indented list items."""
        body = """
## Acceptance Criteria

  - Indented item
    - Nested item (should also be captured)
"""
        result = invoker._parse_criteria_from_body(body)

        # Should capture both indented items
        assert len(result) >= 1
        assert result[0]["text"] == "Indented item"


class TestParseCompletionPromises:
    """Test parse_completion_promises method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_parse_single_promise(self, invoker):
        """Parse single completion promise from player report."""
        report = {
            "task_id": "TASK-001",
            "turn": 1,
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "criterion_text": "OAuth2 flow works",
                    "status": "complete",
                    "evidence": "Implemented in oauth.py",
                    "test_file": "tests/test_oauth.py",
                    "implementation_files": ["src/oauth.py"],
                }
            ],
        }

        result = invoker.parse_completion_promises(report)

        assert len(result) == 1
        assert result[0].criterion_id == "AC-001"
        assert result[0].criterion_text == "OAuth2 flow works"
        from guardkit.orchestrator.schemas import CriterionStatus
        assert result[0].status == CriterionStatus.COMPLETE
        assert result[0].evidence == "Implemented in oauth.py"
        assert result[0].test_file == "tests/test_oauth.py"
        assert result[0].implementation_files == ["src/oauth.py"]

    def test_parse_multiple_promises(self, invoker):
        """Parse multiple completion promises from player report."""
        report = {
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "criterion_text": "First criterion",
                    "status": "complete",
                    "evidence": "Done",
                },
                {
                    "criterion_id": "AC-002",
                    "criterion_text": "Second criterion",
                    "status": "incomplete",
                    "evidence": "WIP",
                },
            ],
        }

        result = invoker.parse_completion_promises(report)

        assert len(result) == 2
        assert result[0].criterion_id == "AC-001"
        assert result[1].criterion_id == "AC-002"
        from guardkit.orchestrator.schemas import CriterionStatus
        assert result[1].status == CriterionStatus.INCOMPLETE

    def test_parse_empty_promises(self, invoker):
        """Return empty list when no completion_promises field."""
        report = {
            "task_id": "TASK-001",
            "turn": 1,
        }

        result = invoker.parse_completion_promises(report)

        assert result == []

    def test_parse_empty_promises_list(self, invoker):
        """Return empty list when completion_promises is empty."""
        report = {
            "completion_promises": [],
        }

        result = invoker.parse_completion_promises(report)

        assert result == []


class TestParseCriteriaVerifications:
    """Test parse_criteria_verifications method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_parse_single_verification(self, invoker):
        """Parse single criteria verification from coach decision."""
        decision = {
            "task_id": "TASK-001",
            "turn": 1,
            "decision": "approve",
            "criteria_verification": [
                {
                    "criterion_id": "AC-001",
                    "result": "verified",
                    "notes": "All tests pass",
                }
            ],
        }

        result = invoker.parse_criteria_verifications(decision)

        assert len(result) == 1
        assert result[0].criterion_id == "AC-001"
        from guardkit.orchestrator.schemas import VerificationResult
        assert result[0].result == VerificationResult.VERIFIED
        assert result[0].notes == "All tests pass"

    def test_parse_multiple_verifications(self, invoker):
        """Parse multiple criteria verifications from coach decision."""
        decision = {
            "criteria_verification": [
                {
                    "criterion_id": "AC-001",
                    "result": "verified",
                    "notes": "Good",
                },
                {
                    "criterion_id": "AC-002",
                    "result": "rejected",
                    "notes": "Missing tests",
                },
            ],
        }

        result = invoker.parse_criteria_verifications(decision)

        assert len(result) == 2
        assert result[0].criterion_id == "AC-001"
        assert result[1].criterion_id == "AC-002"
        from guardkit.orchestrator.schemas import VerificationResult
        assert result[0].result == VerificationResult.VERIFIED
        assert result[1].result == VerificationResult.REJECTED

    def test_parse_empty_verifications(self, invoker):
        """Return empty list when no criteria_verification field."""
        decision = {
            "task_id": "TASK-001",
            "decision": "approve",
        }

        result = invoker.parse_criteria_verifications(decision)

        assert result == []

    def test_parse_empty_verifications_list(self, invoker):
        """Return empty list when criteria_verification is empty."""
        decision = {
            "criteria_verification": [],
        }

        result = invoker.parse_criteria_verifications(decision)

        assert result == []


# ==================== Turn Context Tests ====================


class TestWriteTurnContext:
    """Test _write_turn_context method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_write_turn_context_creates_file(self, invoker, worktree_path):
        """_write_turn_context creates JSON context file."""
        path = invoker._write_turn_context(
            task_id="TASK-001",
            turn=1,
            max_turns=5,
            approaching_limit=False,
        )

        assert path.exists()
        expected_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-001" / "turn_context.json"
        )
        assert path == expected_path

    def test_write_turn_context_content(self, invoker, worktree_path):
        """_write_turn_context writes correct content."""
        invoker._write_turn_context(
            task_id="TASK-002",
            turn=3,
            max_turns=5,
            approaching_limit=False,
        )

        context_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-002" / "turn_context.json"
        )
        with open(context_path) as f:
            content = json.load(f)

        assert content["task_id"] == "TASK-002"
        assert content["turn"] == 3
        assert content["max_turns"] == 5
        assert content["turns_remaining"] == 2
        assert content["approaching_limit"] is False
        assert content["escape_hatch_active"] is False

    def test_write_turn_context_approaching_limit(self, invoker, worktree_path):
        """_write_turn_context marks approaching_limit correctly."""
        invoker._write_turn_context(
            task_id="TASK-003",
            turn=4,
            max_turns=5,
            approaching_limit=True,
        )

        context_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-003" / "turn_context.json"
        )
        with open(context_path) as f:
            content = json.load(f)

        assert content["approaching_limit"] is True
        assert content["escape_hatch_active"] is True
        assert content["turns_remaining"] == 1


class TestLoadTurnContext:
    """Test load_turn_context method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_load_turn_context_success(self, invoker, worktree_path):
        """load_turn_context loads existing context file."""
        # Create context file
        context_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        context_dir.mkdir(parents=True)
        context_path = context_dir / "turn_context.json"
        context_data = {
            "task_id": "TASK-001",
            "turn": 2,
            "max_turns": 5,
            "approaching_limit": False,
        }
        with open(context_path, "w") as f:
            json.dump(context_data, f)

        result = invoker.load_turn_context("TASK-001")

        assert result is not None
        assert result["task_id"] == "TASK-001"
        assert result["turn"] == 2

    def test_load_turn_context_not_found(self, invoker):
        """load_turn_context returns None when file doesn't exist."""
        result = invoker.load_turn_context("TASK-NONEXISTENT")
        assert result is None

    def test_load_turn_context_invalid_json(self, invoker, worktree_path):
        """load_turn_context returns None on invalid JSON."""
        context_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-001"
        context_dir.mkdir(parents=True)
        context_path = context_dir / "turn_context.json"
        context_path.write_text("{ invalid json }")

        result = invoker.load_turn_context("TASK-001")
        assert result is None


# ==================== Player Prompt with Acceptance Criteria Tests ====================


class TestBuildPlayerPromptWithCriteria:
    """Test _build_player_prompt with acceptance criteria."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    def test_prompt_includes_criteria_section(self, invoker):
        """Player prompt includes acceptance criteria section."""
        criteria = [
            {"id": "AC-001", "text": "OAuth2 flow works correctly"},
            {"id": "AC-002", "text": "Token refresh handles expiry"},
        ]

        prompt = invoker._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2",
            feedback=None,
            acceptance_criteria=criteria,
        )

        assert "## Acceptance Criteria" in prompt
        assert "AC-001" in prompt
        assert "OAuth2 flow works correctly" in prompt
        assert "AC-002" in prompt
        assert "Token refresh handles expiry" in prompt

    def test_prompt_includes_completion_promise_example(self, invoker):
        """Player prompt includes completion_promises example."""
        criteria = [
            {"id": "AC-001", "text": "OAuth2 flow works correctly"},
        ]

        prompt = invoker._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2",
            feedback=None,
            acceptance_criteria=criteria,
        )

        assert "completion_promises" in prompt
        assert '"criterion_id": "AC-001"' in prompt

    def test_prompt_without_criteria(self, invoker):
        """Player prompt without criteria doesn't include criteria section."""
        prompt = invoker._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Simple task",
            feedback=None,
            acceptance_criteria=None,
        )

        # Should not have structured criteria section
        assert "You MUST create a completion_promise for each criterion" not in prompt


# ==================== Coach Prompt with Verification Tests ====================


class TestBuildCoachPromptWithVerification:
    """Test _build_coach_prompt with acceptance criteria verification."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(worktree_path=worktree_path)

    @pytest.fixture
    def sample_player_report(self):
        """Sample Player report for Coach prompt."""
        return {
            "task_id": "TASK-001",
            "turn": 1,
            "files_modified": ["src/auth.py"],
            "tests_passed": True,
        }

    def test_prompt_includes_criteria_to_verify(self, invoker, sample_player_report):
        """Coach prompt includes acceptance criteria to verify."""
        criteria = [
            {"id": "AC-001", "text": "OAuth2 flow works correctly"},
            {"id": "AC-002", "text": "Token refresh handles expiry"},
        ]

        prompt = invoker._build_coach_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2",
            player_report=sample_player_report,
            acceptance_criteria=criteria,
        )

        assert "## Acceptance Criteria to Verify" in prompt
        assert "AC-001" in prompt
        assert "AC-002" in prompt

    def test_prompt_includes_verification_example(self, invoker, sample_player_report):
        """Coach prompt includes criteria_verification example."""
        criteria = [
            {"id": "AC-001", "text": "OAuth2 flow works correctly"},
        ]

        prompt = invoker._build_coach_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement OAuth2",
            player_report=sample_player_report,
            acceptance_criteria=criteria,
        )

        assert "criteria_verification" in prompt
        assert '"result": "verified"' in prompt

    def test_prompt_without_criteria(self, invoker, sample_player_report):
        """Coach prompt without criteria doesn't include verification section."""
        prompt = invoker._build_coach_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Simple task",
            player_report=sample_player_report,
            acceptance_criteria=None,
        )

        # Should not have structured verification section
        assert "## Acceptance Criteria to Verify" not in prompt


# ============================================================================
# TASK-FB-RPT1: Player Report Creation from Task-Work Results
# ============================================================================


class TestCreatePlayerReportFromTaskWork:
    """Test _create_player_report_from_task_work method.

    These tests verify that Player reports are correctly created from
    task-work results, bridging the gap between task-work's output format
    (task_work_results.json) and the expected Player report format
    (player_turn_{turn}.json).

    Coverage Target: >=85%
    Test Count: 8 tests
    """

    @pytest.fixture
    def invoker_with_worktree(self, worktree_path):
        """Create AgentInvoker with worktree path."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
            use_task_work_delegation=True,
        )

    @pytest.fixture
    def sample_task_work_results(self):
        """Sample task_work_results.json content."""
        return {
            "files_modified": ["src/auth.py", "src/config.py"],
            "files_created": ["tests/test_auth.py", "src/oauth.py"],
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
                "output_summary": "12 tests passed in 0.45s",
            },
            "coverage": {"line": 85.5, "branch": 78.2},
            "plan_audit": {
                "files_planned": 4,
                "files_actual": 4,
            },
        }

    def test_creates_player_report_from_task_work_results(
        self, invoker_with_worktree, worktree_path, sample_task_work_results
    ):
        """_create_player_report_from_task_work creates player_turn_{turn}.json from task_work_results.json."""
        task_id = "TASK-001"
        turn = 1

        # Create task_work_results.json
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(sample_task_work_results, indent=2)
        )

        # Create TaskWorkResult
        task_work_result = TaskWorkResult(
            success=True,
            output={},
            exit_code=0,
        )

        # Execute
        invoker_with_worktree._create_player_report_from_task_work(
            task_id=task_id,
            turn=turn,
            task_work_result=task_work_result,
        )

        # Verify player report was created
        player_report_path = autobuild_dir / f"player_turn_{turn}.json"
        assert player_report_path.exists()

        # Verify report content
        report = json.loads(player_report_path.read_text())
        assert report["task_id"] == task_id
        assert report["turn"] == turn
        # Files are sorted after git verification merge (TASK-DMRF-003)
        assert set(report["files_modified"]) == set(sample_task_work_results["files_modified"])
        assert set(report["files_created"]) == set(sample_task_work_results["files_created"])
        assert report["tests_run"] is True
        assert report["tests_passed"] is True
        assert report["test_output_summary"] == "12 tests passed in 0.45s"

    def test_extracts_test_files_from_created_modified(
        self, invoker_with_worktree, worktree_path
    ):
        """_create_player_report_from_task_work identifies test files correctly."""
        task_id = "TASK-002"
        turn = 2

        # Create task_work_results.json with test files
        task_work_data = {
            "files_modified": ["tests/test_auth.py", "src/auth.py"],
            "files_created": ["tests/test_oauth.py", "src/oauth_test.py"],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Execute
        invoker_with_worktree._create_player_report_from_task_work(
            task_id=task_id, turn=turn, task_work_result=task_work_result
        )

        # Verify tests_written extracted correctly
        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )
        # Should include files with "test" in name
        assert "tests/test_auth.py" in report["tests_written"]
        assert "tests/test_oauth.py" in report["tests_written"]
        assert "src/oauth_test.py" in report["tests_written"]
        # Should NOT include non-test files
        assert "src/auth.py" not in report["tests_written"]

    def test_creates_report_without_task_work_results_file(
        self, invoker_with_worktree, worktree_path
    ):
        """_create_player_report_from_task_work creates report with defaults when task_work_results.json missing."""
        task_id = "TASK-003"
        turn = 1

        # Don't create task_work_results.json

        task_work_result = TaskWorkResult(
            success=True,
            output={"files_created": ["src/new_file.py"]},
            exit_code=0,
        )

        # Mock git detection to avoid actual git calls
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": ["src/changed.py"], "created": []},
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        # Verify report was created with task_work_result.output data
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        report_path = autobuild_dir / f"player_turn_{turn}.json"
        assert report_path.exists()

        report = json.loads(report_path.read_text())
        # Output overrides git detection
        assert report["files_created"] == ["src/new_file.py"]

    def test_output_overrides_file_data(
        self, invoker_with_worktree, worktree_path, sample_task_work_results
    ):
        """task_work_result.output takes precedence over task_work_results.json file data."""
        task_id = "TASK-004"
        turn = 1

        # Create task_work_results.json
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(sample_task_work_results)
        )

        # TaskWorkResult with different output data
        task_work_result = TaskWorkResult(
            success=True,
            output={
                "files_modified": ["src/override.py"],
                "tests_passed": False,
            },
            exit_code=0,
        )

        invoker_with_worktree._create_player_report_from_task_work(
            task_id=task_id, turn=turn, task_work_result=task_work_result
        )

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )
        # Output should override file data
        assert report["files_modified"] == ["src/override.py"]
        assert report["tests_passed"] is False
        assert report["tests_run"] is True  # Set when tests_passed is in output

    def test_handles_malformed_task_work_results_json(
        self, invoker_with_worktree, worktree_path
    ):
        """_create_player_report_from_task_work handles malformed JSON gracefully."""
        task_id = "TASK-005"
        turn = 1

        # Create malformed JSON
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            "{ invalid json content"
        )

        task_work_result = TaskWorkResult(
            success=True,
            output={"files_created": ["src/file.py"]},
            exit_code=0,
        )

        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": [], "created": []},
        ):
            # Should not raise exception
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        # Verify report was still created
        report_path = autobuild_dir / f"player_turn_{turn}.json"
        assert report_path.exists()

    def test_creates_autobuild_directory_if_missing(
        self, invoker_with_worktree, worktree_path
    ):
        """_create_player_report_from_task_work creates autobuild directory if it doesn't exist."""
        task_id = "TASK-006"
        turn = 1

        # Directory doesn't exist
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        assert not autobuild_dir.exists()

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": [], "created": []},
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        # Directory should now exist
        assert autobuild_dir.exists()
        assert (autobuild_dir / f"player_turn_{turn}.json").exists()

    def test_report_includes_all_required_fields(
        self, invoker_with_worktree, worktree_path
    ):
        """Created report includes all fields from PLAYER_REPORT_SCHEMA."""
        task_id = "TASK-007"
        turn = 1

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": [], "created": []},
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Verify all required fields from PLAYER_REPORT_SCHEMA
        required_fields = [
            "task_id",
            "turn",
            "files_modified",
            "files_created",
            "tests_written",
            "tests_run",
            "tests_passed",
            "implementation_notes",
            "concerns",
            "requirements_addressed",
            "requirements_remaining",
        ]
        for field in required_fields:
            assert field in report, f"Missing required field: {field}"

    def test_implementation_notes_include_plan_audit_info(
        self, invoker_with_worktree, worktree_path
    ):
        """Implementation notes include plan audit info when available."""
        task_id = "TASK-008"
        turn = 1

        task_work_data = {
            "files_modified": [],
            "files_created": [],
            "plan_audit": {
                "files_planned": 5,
                "files_actual": 4,
            },
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        invoker_with_worktree._create_player_report_from_task_work(
            task_id=task_id, turn=turn, task_work_result=task_work_result
        )

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )
        assert "Files planned: 5" in report["implementation_notes"]
        assert "Files actual: 4" in report["implementation_notes"]

    def test_tests_passed_is_boolean_when_int_provided(
        self, invoker_with_worktree, worktree_path
    ):
        """tests_passed should be bool even when output provides int count (TASK-FBSDK-015).

        The TaskWorkStreamParser captures tests_passed as an integer (count of passing tests),
        but PLAYER_REPORT_SCHEMA expects a boolean. This test verifies the type conversion.
        """
        task_id = "TASK-009"
        turn = 1

        # TaskWorkResult with tests_passed as int (from parser)
        task_work_result = TaskWorkResult(
            success=True,
            output={
                "tests_passed": 7,  # Parser provides count as int
                "files_created": ["src/feature.py"],
            },
            exit_code=0,
        )

        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": [], "created": []},
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Verify tests_passed is boolean, not int
        assert isinstance(report["tests_passed"], bool), \
            f"tests_passed should be bool, got {type(report['tests_passed']).__name__}"
        assert report["tests_passed"] is True  # 7 > 0 = True

        # Verify test count is preserved in separate field
        assert "tests_passed_count" in report, \
            "tests_passed_count should be added to preserve the original count"
        assert report["tests_passed_count"] == 7

    def test_tests_passed_is_false_when_zero_int_provided(
        self, invoker_with_worktree, worktree_path
    ):
        """tests_passed should be False when int count is 0 (TASK-FBSDK-015)."""
        task_id = "TASK-010"
        turn = 1

        # TaskWorkResult with tests_passed as 0
        task_work_result = TaskWorkResult(
            success=True,
            output={
                "tests_passed": 0,  # No tests passed
                "files_created": ["src/feature.py"],
            },
            exit_code=0,
        )

        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": [], "created": []},
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Verify tests_passed is False when count is 0
        assert isinstance(report["tests_passed"], bool)
        assert report["tests_passed"] is False  # 0 > 0 = False
        assert report["tests_passed_count"] == 0

    def test_tests_passed_remains_bool_when_bool_provided(
        self, invoker_with_worktree, worktree_path
    ):
        """tests_passed should remain bool when output already provides bool (TASK-FBSDK-015)."""
        task_id = "TASK-011"
        turn = 1

        # TaskWorkResult with tests_passed as bool (already correct type)
        task_work_result = TaskWorkResult(
            success=True,
            output={
                "tests_passed": True,  # Already a boolean
                "files_created": ["src/feature.py"],
            },
            exit_code=0,
        )

        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": [], "created": []},
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Verify tests_passed remains boolean
        assert isinstance(report["tests_passed"], bool)
        assert report["tests_passed"] is True
        # tests_passed_count should NOT be set for bool input
        assert "tests_passed_count" not in report

    # ==================== Git Verification Step Tests (TASK-DMRF-003) ====================

    def test_git_verification_enriches_empty_task_work_results(
        self, invoker_with_worktree, worktree_path
    ):
        """Git detection enriches report when task_work_results.json has empty arrays (TASK-DMRF-003)."""
        task_id = "TASK-GIT-001"
        turn = 1

        # Create task_work_results.json with empty file arrays
        task_work_data = {
            "files_modified": [],
            "files_created": [],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Mock git detection to return files
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={
                "modified": ["src/changed.py", "src/updated.py"],
                "created": ["src/new_file.py"],
            },
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Git-detected files should be in the report
        assert "src/changed.py" in report["files_modified"]
        assert "src/updated.py" in report["files_modified"]
        assert "src/new_file.py" in report["files_created"]

    def test_git_verification_merges_with_existing_files(
        self, invoker_with_worktree, worktree_path
    ):
        """Git detection merges with existing files (union, not replacement) (TASK-DMRF-003)."""
        task_id = "TASK-GIT-002"
        turn = 1

        # Create task_work_results.json with some files already
        task_work_data = {
            "files_modified": ["src/existing.py"],
            "files_created": ["src/original.py"],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Mock git detection to return additional files
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={
                "modified": ["src/git_detected.py"],
                "created": ["src/git_new.py"],
            },
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Both original AND git-detected files should be present
        assert "src/existing.py" in report["files_modified"]
        assert "src/git_detected.py" in report["files_modified"]
        assert "src/original.py" in report["files_created"]
        assert "src/git_new.py" in report["files_created"]

    def test_git_verification_deduplicates_files(
        self, invoker_with_worktree, worktree_path
    ):
        """Git detection does not duplicate files already in report (TASK-DMRF-003)."""
        task_id = "TASK-GIT-003"
        turn = 1

        # Create task_work_results.json with files
        task_work_data = {
            "files_modified": ["src/shared.py", "src/unique_orig.py"],
            "files_created": ["src/common.py"],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Mock git detection to return some overlapping files
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={
                "modified": ["src/shared.py", "src/unique_git.py"],  # shared.py overlaps
                "created": ["src/common.py", "src/new_git.py"],  # common.py overlaps
            },
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # No duplicates - each file should appear only once
        assert report["files_modified"].count("src/shared.py") == 1
        assert report["files_created"].count("src/common.py") == 1
        # All unique files should be present
        assert "src/unique_orig.py" in report["files_modified"]
        assert "src/unique_git.py" in report["files_modified"]
        assert "src/new_git.py" in report["files_created"]

    def test_git_verification_always_runs_even_with_file(
        self, invoker_with_worktree, worktree_path
    ):
        """Git detection always runs, even when task_work_results.json exists (TASK-DMRF-003)."""
        task_id = "TASK-GIT-004"
        turn = 1

        # Create task_work_results.json
        task_work_data = {
            "files_modified": ["src/from_file.py"],
            "files_created": [],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Mock git detection and track if it was called
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={"modified": ["src/from_git.py"], "created": []},
        ) as mock_git:
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

            # Git detection should always be called
            mock_git.assert_called_once()

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Both file and git sources should be present
        assert "src/from_file.py" in report["files_modified"]
        assert "src/from_git.py" in report["files_modified"]

    def test_git_verification_handles_detection_failure(
        self, invoker_with_worktree, worktree_path
    ):
        """Git detection failure should not break report creation (TASK-DMRF-003)."""
        task_id = "TASK-GIT-005"
        turn = 1

        # Create task_work_results.json
        task_work_data = {
            "files_modified": ["src/preserved.py"],
            "files_created": ["src/kept.py"],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Mock git detection to raise exception
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            side_effect=Exception("Git error: not a repository"),
        ):
            # Should not raise exception
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        # Report should still be created with original data
        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )
        assert report["files_modified"] == ["src/preserved.py"]
        assert report["files_created"] == ["src/kept.py"]

    def test_git_verification_sorts_file_lists(
        self, invoker_with_worktree, worktree_path
    ):
        """Git verification should produce sorted file lists (TASK-DMRF-003)."""
        task_id = "TASK-GIT-006"
        turn = 1

        # Create task_work_results.json with unsorted files
        task_work_data = {
            "files_modified": ["src/zebra.py", "src/alpha.py"],
            "files_created": ["src/beta.py"],
            "tests_info": {"tests_run": True, "tests_passed": True},
        }
        autobuild_dir = worktree_path / ".guardkit" / "autobuild" / task_id
        autobuild_dir.mkdir(parents=True)
        (autobuild_dir / "task_work_results.json").write_text(
            json.dumps(task_work_data)
        )

        task_work_result = TaskWorkResult(success=True, output={}, exit_code=0)

        # Mock git detection with unsorted files
        with patch.object(
            invoker_with_worktree,
            "_detect_git_changes",
            return_value={
                "modified": ["src/middle.py"],
                "created": ["src/aardvark.py", "src/zoo.py"],
            },
        ):
            invoker_with_worktree._create_player_report_from_task_work(
                task_id=task_id, turn=turn, task_work_result=task_work_result
            )

        report = json.loads(
            (autobuild_dir / f"player_turn_{turn}.json").read_text()
        )

        # Files should be sorted alphabetically
        assert report["files_modified"] == ["src/alpha.py", "src/middle.py", "src/zebra.py"]
        assert report["files_created"] == ["src/aardvark.py", "src/beta.py", "src/zoo.py"]


class TestDetectGitChanges:
    """Test _detect_git_changes method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
        )

    def test_detect_git_changes_returns_dict(self, invoker):
        """_detect_git_changes returns dict with modified and created keys."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="")
            result = invoker._detect_git_changes()

        assert "modified" in result
        assert "created" in result
        assert isinstance(result["modified"], list)
        assert isinstance(result["created"], list)

    def test_detect_git_changes_parses_modified_files(self, invoker):
        """_detect_git_changes parses modified files from git diff."""
        with patch("subprocess.run") as mock_run:
            # First call for modified files
            mock_modified = Mock(returncode=0, stdout="src/auth.py\nsrc/config.py\n")
            # Second call for untracked files
            mock_untracked = Mock(returncode=0, stdout="")
            mock_run.side_effect = [mock_modified, mock_untracked]

            result = invoker._detect_git_changes()

        assert result["modified"] == ["src/auth.py", "src/config.py"]

    def test_detect_git_changes_parses_untracked_files(self, invoker):
        """_detect_git_changes parses untracked files from git ls-files."""
        with patch("subprocess.run") as mock_run:
            # First call for modified files
            mock_modified = Mock(returncode=0, stdout="")
            # Second call for untracked files
            mock_untracked = Mock(returncode=0, stdout="src/new_file.py\ntests/test_new.py\n")
            mock_run.side_effect = [mock_modified, mock_untracked]

            result = invoker._detect_git_changes()

        assert result["created"] == ["src/new_file.py", "tests/test_new.py"]

    def test_detect_git_changes_handles_git_failure(self, invoker):
        """_detect_git_changes returns empty lists when git fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")
            result = invoker._detect_git_changes()

        # Should return empty lists, not raise
        assert result["modified"] == []
        assert result["created"] == []

    def test_detect_git_changes_handles_timeout(self, invoker):
        """_detect_git_changes handles subprocess timeout."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)
            result = invoker._detect_git_changes()

        # Should return empty lists, not raise
        assert result["modified"] == []
        assert result["created"] == []


# ==================== TaskWorkStreamParser Tests ====================


class TestTaskWorkStreamParser:
    """Test TaskWorkStreamParser for quality gate extraction.

    The TaskWorkStreamParser is a stateful incremental parser that extracts
    quality gate results from task-work SDK stream messages.

    Coverage Target: >=90%
    Test Count: 20+ tests
    """

    @pytest.fixture
    def parser(self):
        """Create a fresh TaskWorkStreamParser instance."""
        return TaskWorkStreamParser()

    # -------------- Phase Detection Tests --------------

    def test_parse_phase_marker(self, parser):
        """Parser extracts phase markers with description."""
        parser.parse_message("Phase 2: Implementation Planning")
        result = parser.to_result()

        assert "phases" in result
        assert "phase_2" in result["phases"]
        assert result["phases"]["phase_2"]["detected"] is True
        assert "Implementation Planning" in result["phases"]["phase_2"]["text"]
        assert result["phases"]["phase_2"]["completed"] is False

    def test_parse_phase_marker_with_decimal(self, parser):
        """Parser extracts phase markers with decimal numbers (e.g., Phase 2.5)."""
        parser.parse_message("Phase 2.5: Architectural Review")
        result = parser.to_result()

        assert "phase_2.5" in result["phases"]
        assert result["phases"]["phase_2.5"]["detected"] is True
        assert "Architectural Review" in result["phases"]["phase_2.5"]["text"]

    def test_parse_phase_complete_marker(self, parser):
        """Parser detects phase completion markers."""
        parser.parse_message("Phase 3: Implementation")
        parser.parse_message("✓ Phase 3 complete")
        result = parser.to_result()

        assert result["phases"]["phase_3"]["completed"] is True

    def test_parse_phase_complete_without_prior_detection(self, parser):
        """Parser handles completion marker without prior phase detection."""
        parser.parse_message("✓ Phase 4.5 complete")
        result = parser.to_result()

        assert "phase_4.5" in result["phases"]
        assert result["phases"]["phase_4.5"]["completed"] is True
        assert result["phases"]["phase_4.5"]["detected"] is True

    def test_parse_multiple_phases(self, parser):
        """Parser accumulates multiple phases."""
        parser.parse_message("Phase 2: Planning")
        parser.parse_message("✓ Phase 2 complete")
        parser.parse_message("Phase 3: Implementation")
        parser.parse_message("✓ Phase 3 complete")
        result = parser.to_result()

        assert len(result["phases"]) == 2
        assert result["phases"]["phase_2"]["completed"] is True
        assert result["phases"]["phase_3"]["completed"] is True

    # -------------- Test Results Tests --------------

    def test_parse_tests_passed(self, parser):
        """Parser extracts test pass count."""
        parser.parse_message("12 tests passed")
        result = parser.to_result()

        assert result["tests_passed"] == 12

    def test_parse_tests_passed_singular(self, parser):
        """Parser handles singular 'test passed'."""
        parser.parse_message("1 test passed")
        result = parser.to_result()

        assert result["tests_passed"] == 1

    def test_parse_tests_failed(self, parser):
        """Parser extracts test fail count."""
        parser.parse_message("3 tests failed")
        result = parser.to_result()

        assert result["tests_failed"] == 3

    def test_parse_tests_both_counts(self, parser):
        """Parser extracts both pass and fail counts from same message."""
        parser.parse_message("12 tests passed, 2 tests failed")
        result = parser.to_result()

        assert result["tests_passed"] == 12
        assert result["tests_failed"] == 2

    def test_parse_tests_case_insensitive(self, parser):
        """Parser handles case variations in test results."""
        parser.parse_message("15 Tests Passed")
        result = parser.to_result()

        assert result["tests_passed"] == 15

    # -------------- Coverage Tests --------------

    def test_parse_coverage_percentage(self, parser):
        """Parser extracts coverage percentage."""
        parser.parse_message("Coverage: 85.5%")
        result = parser.to_result()

        assert result["coverage"] == 85.5

    def test_parse_coverage_integer(self, parser):
        """Parser handles integer coverage."""
        parser.parse_message("coverage: 90%")
        result = parser.to_result()

        assert result["coverage"] == 90.0

    def test_parse_coverage_no_space(self, parser):
        """Parser handles coverage without space after colon."""
        parser.parse_message("Coverage:87.3%")
        result = parser.to_result()

        assert result["coverage"] == 87.3

    # -------------- Quality Gates Tests --------------

    def test_parse_quality_gates_passed(self, parser):
        """Parser detects quality gates passed."""
        parser.parse_message("Quality gates: PASSED")
        result = parser.to_result()

        assert result["quality_gates_passed"] is True

    def test_parse_quality_gates_passed_lowercase(self, parser):
        """Parser handles quality gates passed in lowercase."""
        parser.parse_message("all quality gates passed")
        result = parser.to_result()

        assert result["quality_gates_passed"] is True

    def test_parse_quality_gates_failed(self, parser):
        """Parser detects quality gates failed."""
        parser.parse_message("Quality gates: FAILED")
        result = parser.to_result()

        assert result["quality_gates_passed"] is False

    # -------------- File Modification Tests --------------

    def test_parse_file_modified(self, parser):
        """Parser extracts modified file paths."""
        parser.parse_message("Modified: src/auth.py")
        result = parser.to_result()

        assert "files_modified" in result
        assert "src/auth.py" in result["files_modified"]

    def test_parse_file_created(self, parser):
        """Parser extracts created file paths."""
        parser.parse_message("Created: tests/test_auth.py")
        result = parser.to_result()

        assert "files_created" in result
        assert "tests/test_auth.py" in result["files_created"]

    def test_parse_file_changed_variant(self, parser):
        """Parser handles 'Changed:' variant for modified files."""
        parser.parse_message("Changed: src/config.py")
        result = parser.to_result()

        assert "src/config.py" in result["files_modified"]

    def test_parse_file_added_variant(self, parser):
        """Parser handles 'Added:' variant for created files."""
        parser.parse_message("Added: src/new_module.py")
        result = parser.to_result()

        assert "src/new_module.py" in result["files_created"]

    def test_parse_multiple_files_same_message(self, parser):
        """Parser extracts multiple files from same message."""
        parser.parse_message("Modified: src/a.py Modified: src/b.py")
        result = parser.to_result()

        assert len(result["files_modified"]) == 2
        assert "src/a.py" in result["files_modified"]
        assert "src/b.py" in result["files_modified"]

    def test_file_deduplication(self, parser):
        """Parser deduplicates file paths across messages."""
        parser.parse_message("Modified: src/auth.py")
        parser.parse_message("Modified: src/auth.py")
        result = parser.to_result()

        assert result["files_modified"].count("src/auth.py") == 1

    def test_files_sorted_in_result(self, parser):
        """Parser returns files sorted alphabetically."""
        parser.parse_message("Modified: src/z_file.py")
        parser.parse_message("Modified: src/a_file.py")
        parser.parse_message("Modified: src/m_file.py")
        result = parser.to_result()

        assert result["files_modified"] == [
            "src/a_file.py",
            "src/m_file.py",
            "src/z_file.py",
        ]

    # -------------- Incremental Parsing Tests --------------

    def test_incremental_parsing_accumulates(self, parser):
        """Parser accumulates results across multiple messages."""
        parser.parse_message("Phase 2: Planning")
        parser.parse_message("8 tests passed")
        parser.parse_message("Coverage: 92%")
        parser.parse_message("all quality gates passed")
        parser.parse_message("Modified: src/main.py")
        result = parser.to_result()

        assert "phase_2" in result["phases"]
        assert result["tests_passed"] == 8
        assert result["coverage"] == 92.0
        assert result["quality_gates_passed"] is True
        assert "src/main.py" in result["files_modified"]

    def test_later_value_overwrites_earlier(self, parser):
        """Later parsed values overwrite earlier ones."""
        parser.parse_message("5 tests passed")
        parser.parse_message("10 tests passed")
        result = parser.to_result()

        assert result["tests_passed"] == 10

    # -------------- Edge Cases Tests --------------

    def test_parse_empty_message(self, parser):
        """Parser handles empty messages gracefully."""
        parser.parse_message("")
        result = parser.to_result()

        assert result == {}

    def test_parse_none_equivalent(self, parser):
        """Parser handles None-like empty input."""
        parser.parse_message("")
        parser.parse_message("")
        result = parser.to_result()

        assert result == {}

    def test_parse_unrecognized_patterns(self, parser):
        """Parser ignores unrecognized patterns without error."""
        parser.parse_message("This is some random text")
        parser.parse_message("Building artifacts...")
        parser.parse_message("Done in 2.5s")
        result = parser.to_result()

        # Should have empty result, not raise errors
        assert result == {}

    def test_parse_long_phase_text_truncated(self, parser):
        """Parser truncates long phase text to 100 characters."""
        long_text = "A" * 200
        parser.parse_message(f"Phase 1: {long_text}")
        result = parser.to_result()

        assert len(result["phases"]["phase_1"]["text"]) == 100

    # -------------- Architectural Review Score Tests --------------

    def test_parse_architectural_review_score(self, parser):
        """Parser extracts architectural review score."""
        parser.parse_message("Architectural Score: 82/100")
        result = parser.to_result()

        assert "architectural_review" in result
        assert result["architectural_review"]["score"] == 82

    def test_parse_architectural_review_score_no_denominator(self, parser):
        """Parser handles score without /100 suffix."""
        parser.parse_message("Architectural score: 75")
        result = parser.to_result()

        assert result["architectural_review"]["score"] == 75

    def test_parse_architectural_review_subscores(self, parser):
        """Parser extracts SOLID/DRY/YAGNI subscores."""
        parser.parse_message("Architectural Score: 80")
        parser.parse_message("SOLID: 85, DRY: 80, YAGNI: 82")
        result = parser.to_result()

        assert result["architectural_review"]["solid"] == 85
        assert result["architectural_review"]["dry"] == 80
        assert result["architectural_review"]["yagni"] == 82

    def test_parse_architectural_review_subscores_no_commas(self, parser):
        """Parser handles subscores without commas."""
        parser.parse_message("Architectural Score: 80")
        parser.parse_message("SOLID: 85 DRY: 80 YAGNI: 82")
        result = parser.to_result()

        assert result["architectural_review"]["solid"] == 85
        assert result["architectural_review"]["dry"] == 80
        assert result["architectural_review"]["yagni"] == 82

    def test_parse_architectural_review_score_and_subscores(self, parser):
        """Parser combines overall score with subscores."""
        parser.parse_message("Architectural Score: 82")
        parser.parse_message("SOLID: 45, DRY: 23, YAGNI: 17")
        result = parser.to_result()

        assert result["architectural_review"]["score"] == 82
        assert result["architectural_review"]["solid"] == 45
        assert result["architectural_review"]["dry"] == 23
        assert result["architectural_review"]["yagni"] == 17

    def test_parse_architectural_review_case_insensitive(self, parser):
        """Parser handles case variations."""
        parser.parse_message("architectural SCORE: 90")
        result = parser.to_result()

        assert result["architectural_review"]["score"] == 90

    def test_parse_architectural_review_no_score_returns_empty(self, parser):
        """Parser returns empty result when no arch score found."""
        parser.parse_message("Some other message")
        result = parser.to_result()

        assert "architectural_review" not in result

    def test_architectural_review_reset_clears_scores(self, parser):
        """Reset clears architectural review state."""
        parser.parse_message("Architectural Score: 82")
        parser.parse_message("SOLID: 85, DRY: 80, YAGNI: 82")

        parser.reset()
        result = parser.to_result()

        assert "architectural_review" not in result

    # -------------- Reset Tests --------------

    def test_reset_clears_state(self, parser):
        """Reset clears all accumulated state."""
        parser.parse_message("12 tests passed")
        parser.parse_message("Coverage: 85%")
        parser.parse_message("Modified: src/file.py")

        parser.reset()
        result = parser.to_result()

        assert result == {}

    def test_reset_allows_reuse(self, parser):
        """Parser can be reused after reset."""
        parser.parse_message("5 tests passed")
        parser.reset()
        parser.parse_message("10 tests passed")
        result = parser.to_result()

        assert result["tests_passed"] == 10

    # -------------- Tool Invocation Tracking Tests --------------

    def test_track_write_tool_call(self, parser):
        """Verify _track_tool_call adds Write paths to files_created."""
        parser._track_tool_call("Write", {"file_path": "/path/to/new_file.py"})
        result = parser.to_result()

        assert "files_created" in result
        assert "/path/to/new_file.py" in result["files_created"]

    def test_track_edit_tool_call(self, parser):
        """Verify _track_tool_call adds Edit paths to files_modified."""
        parser._track_tool_call("Edit", {"file_path": "/path/to/existing_file.py"})
        result = parser.to_result()

        assert "files_modified" in result
        assert "/path/to/existing_file.py" in result["files_modified"]

    def test_track_tool_call_ignores_unknown_tool(self, parser):
        """Verify _track_tool_call ignores unknown tool names."""
        parser._track_tool_call("Read", {"file_path": "/path/to/file.py"})
        parser._track_tool_call("Bash", {"command": "ls -la"})
        parser._track_tool_call("Unknown", {"file_path": "/path/to/file.py"})
        result = parser.to_result()

        assert "files_created" not in result
        assert "files_modified" not in result

    def test_track_tool_call_ignores_missing_file_path(self, parser):
        """Verify _track_tool_call handles missing file_path gracefully."""
        parser._track_tool_call("Write", {})
        parser._track_tool_call("Edit", {"other_arg": "value"})
        result = parser.to_result()

        assert "files_created" not in result
        assert "files_modified" not in result

    def test_track_tool_call_ignores_non_string_file_path(self, parser):
        """Verify _track_tool_call handles non-string file_path gracefully."""
        parser._track_tool_call("Write", {"file_path": 123})
        parser._track_tool_call("Edit", {"file_path": ["list", "not", "string"]})
        parser._track_tool_call("Write", {"file_path": None})
        result = parser.to_result()

        assert "files_created" not in result
        assert "files_modified" not in result

    def test_parse_tool_invocation_xml_write(self, parser):
        """Parse XML-style Write tool invocation."""
        message = '''<invoke name="Write">
<parameter name="file_path">/src/utils/helper.py</parameter>
<parameter name="content">print("hello")</parameter>
</invoke>'''
        parser.parse_message(message)
        result = parser.to_result()

        assert "files_created" in result
        assert "/src/utils/helper.py" in result["files_created"]

    def test_parse_tool_invocation_xml_edit(self, parser):
        """Parse XML-style Edit tool invocation."""
        message = '''<invoke name="Edit">
<parameter name="file_path">/src/models/user.py</parameter>
<parameter name="old_string">def old_method</parameter>
<parameter name="new_string">def new_method</parameter>
</invoke>'''
        parser.parse_message(message)
        result = parser.to_result()

        assert "files_modified" in result
        assert "/src/models/user.py" in result["files_modified"]

    def test_parse_tool_invocation_xml_with_whitespace(self, parser):
        """Parse XML tool invocation with extra whitespace in file_path."""
        message = '''<invoke name="Write">
<parameter name="file_path">  /src/new_module.py  </parameter>
</invoke>'''
        parser.parse_message(message)
        result = parser.to_result()

        assert "files_created" in result
        assert "/src/new_module.py" in result["files_created"]

    def test_parse_tool_result_created(self, parser):
        """Parse 'File created successfully at:' message."""
        parser.parse_message("File created successfully at: /tests/test_new.py")
        result = parser.to_result()

        assert "files_created" in result
        assert "/tests/test_new.py" in result["files_created"]

    def test_parse_tool_result_written(self, parser):
        """Parse 'File written to:' message variant."""
        parser.parse_message("File written to: /src/output.json")
        result = parser.to_result()

        assert "files_created" in result
        assert "/src/output.json" in result["files_created"]

    def test_parse_tool_result_modified(self, parser):
        """Parse 'File modified successfully at:' message."""
        parser.parse_message("File modified successfully at: /src/config.py")
        result = parser.to_result()

        assert "files_modified" in result
        assert "/src/config.py" in result["files_modified"]

    def test_parse_tool_result_updated(self, parser):
        """Parse 'File updated at:' message variant."""
        parser.parse_message("File updated at: /src/settings.yaml")
        result = parser.to_result()

        assert "files_modified" in result
        assert "/src/settings.yaml" in result["files_modified"]

    def test_parse_tool_result_edited(self, parser):
        """Parse 'File edited at:' message variant."""
        parser.parse_message("File edited at: /src/main.py")
        result = parser.to_result()

        assert "files_modified" in result
        assert "/src/main.py" in result["files_modified"]

    def test_tool_tracking_deduplication(self, parser):
        """Verify duplicate paths are deduplicated across tracking methods."""
        # Add same file via multiple methods
        parser._track_tool_call("Write", {"file_path": "/src/utils.py"})
        parser.parse_message("File created successfully at: /src/utils.py")
        parser.parse_message('''<invoke name="Write">
<parameter name="file_path">/src/utils.py</parameter>
</invoke>''')
        result = parser.to_result()

        assert "files_created" in result
        assert len(result["files_created"]) == 1
        assert "/src/utils.py" in result["files_created"]

    def test_tool_tracking_deduplication_modified(self, parser):
        """Verify duplicate modified paths are deduplicated."""
        parser._track_tool_call("Edit", {"file_path": "/src/models.py"})
        parser.parse_message("File modified at: /src/models.py")
        parser._track_tool_call("Edit", {"file_path": "/src/models.py"})
        result = parser.to_result()

        assert "files_modified" in result
        assert len(result["files_modified"]) == 1
        assert "/src/models.py" in result["files_modified"]

    def test_tool_tracking_multiple_files_single_message(self, parser):
        """Parse multiple tool results from single message."""
        message = """File created successfully at: /src/a.py
File created successfully at: /src/b.py
File modified at: /src/c.py"""
        parser.parse_message(message)
        result = parser.to_result()

        assert "files_created" in result
        assert "/src/a.py" in result["files_created"]
        assert "/src/b.py" in result["files_created"]
        assert "files_modified" in result
        assert "/src/c.py" in result["files_modified"]

    def test_tool_tracking_with_other_patterns(self, parser):
        """Tool tracking works alongside other pattern matching."""
        parser.parse_message("Phase 3: Implementation")
        parser.parse_message('''<invoke name="Write">
<parameter name="file_path">/src/feature.py</parameter>
</invoke>''')
        parser.parse_message("File created successfully at: /tests/test_feature.py")
        parser.parse_message("12 tests passed")
        parser.parse_message("Coverage: 85%")
        result = parser.to_result()

        assert "phase_3" in result["phases"]
        assert result["tests_passed"] == 12
        assert result["coverage"] == 85.0
        assert "/src/feature.py" in result["files_created"]
        assert "/tests/test_feature.py" in result["files_created"]

    def test_tool_tracking_reset_clears_state(self, parser):
        """Reset clears tool tracking state."""
        parser._track_tool_call("Write", {"file_path": "/src/new.py"})
        parser._track_tool_call("Edit", {"file_path": "/src/old.py"})
        parser.reset()
        result = parser.to_result()

        assert "files_created" not in result
        assert "files_modified" not in result

    def test_tool_tracking_case_insensitive_result_patterns(self, parser):
        """Tool result patterns are case-insensitive."""
        parser.parse_message("FILE CREATED successfully at: /src/upper.py")
        parser.parse_message("file modified AT: /src/lower.py")
        result = parser.to_result()

        assert "/src/upper.py" in result["files_created"]
        assert "/src/lower.py" in result["files_modified"]

    def test_tool_tracking_sorted_output(self, parser):
        """Tool tracking output is sorted alphabetically."""
        parser._track_tool_call("Write", {"file_path": "/z_file.py"})
        parser._track_tool_call("Write", {"file_path": "/a_file.py"})
        parser._track_tool_call("Write", {"file_path": "/m_file.py"})
        result = parser.to_result()

        assert result["files_created"] == ["/a_file.py", "/m_file.py", "/z_file.py"]

    # =========================================================================
    # Test File Detection Tests (TASK-FTF-002)
    # =========================================================================

    def test_is_test_file_with_test_prefix(self, parser):
        """_is_test_file detects test_ prefix pattern."""
        assert parser._is_test_file("test_feature.py") is True
        assert parser._is_test_file("/path/to/test_feature.py") is True
        assert parser._is_test_file("src/tests/test_auth.py") is True

    def test_is_test_file_with_test_suffix(self, parser):
        """_is_test_file detects _test.py suffix pattern."""
        assert parser._is_test_file("feature_test.py") is True
        assert parser._is_test_file("/path/to/auth_test.py") is True
        assert parser._is_test_file("src/tests/user_test.py") is True

    def test_is_test_file_rejects_non_test_files(self, parser):
        """_is_test_file rejects non-test files."""
        assert parser._is_test_file("feature.py") is False
        assert parser._is_test_file("test_config.json") is False
        assert parser._is_test_file("testing_utils.py") is False
        assert parser._is_test_file("contest.py") is False
        assert parser._is_test_file("") is False
        assert parser._is_test_file("test_") is False

    def test_is_test_file_handles_windows_paths(self, parser):
        """_is_test_file handles Windows-style paths."""
        assert parser._is_test_file("C:\\project\\tests\\test_feature.py") is True
        assert parser._is_test_file("src\\tests\\auth_test.py") is True

    def test_track_tool_call_tracks_test_files(self, parser):
        """_track_tool_call adds test files to test_files_created set."""
        parser._track_tool_call("Write", {"file_path": "/tests/test_feature.py"})
        result = parser.to_result()

        assert "test_files_created" in result
        assert "/tests/test_feature.py" in result["test_files_created"]
        assert "/tests/test_feature.py" in result["files_created"]

    def test_track_tool_call_tracks_multiple_test_files(self, parser):
        """_track_tool_call tracks multiple test files."""
        parser._track_tool_call("Write", {"file_path": "tests/test_auth.py"})
        parser._track_tool_call("Write", {"file_path": "tests/test_user.py"})
        parser._track_tool_call("Write", {"file_path": "src/feature.py"})
        result = parser.to_result()

        assert len(result["test_files_created"]) == 2
        assert "tests/test_auth.py" in result["test_files_created"]
        assert "tests/test_user.py" in result["test_files_created"]
        assert len(result["files_created"]) == 3

    def test_track_tool_call_deduplicates_test_files(self, parser):
        """_track_tool_call deduplicates test files."""
        parser._track_tool_call("Write", {"file_path": "tests/test_feature.py"})
        parser._track_tool_call("Write", {"file_path": "tests/test_feature.py"})
        result = parser.to_result()

        assert len(result["test_files_created"]) == 1

    def test_edit_does_not_track_test_files(self, parser):
        """_track_tool_call does not track test files for Edit operations."""
        parser._track_tool_call("Edit", {"file_path": "tests/test_feature.py"})
        result = parser.to_result()

        assert "test_files_created" not in result
        assert "tests/test_feature.py" in result["files_modified"]

    def test_reset_clears_test_files(self, parser):
        """reset() clears test_files_created set."""
        parser._track_tool_call("Write", {"file_path": "tests/test_feature.py"})
        parser.reset()
        result = parser.to_result()

        assert "test_files_created" not in result

    def test_test_files_sorted_output(self, parser):
        """test_files_created output is sorted alphabetically."""
        parser._track_tool_call("Write", {"file_path": "tests/test_z.py"})
        parser._track_tool_call("Write", {"file_path": "tests/test_a.py"})
        parser._track_tool_call("Write", {"file_path": "tests/test_m.py"})
        result = parser.to_result()

        assert result["test_files_created"] == [
            "tests/test_a.py",
            "tests/test_m.py",
            "tests/test_z.py",
        ]

    # =========================================================================
    # Pytest Summary Pattern Tests (TASK-FTF-002)
    # =========================================================================

    def test_parse_pytest_summary_passed_only(self, parser):
        """parse_message extracts passed count from pytest summary."""
        parser.parse_message("===== 15 passed in 0.23s =====")
        result = parser.to_result()

        assert result["tests_passed"] == 15

    def test_parse_pytest_summary_passed_and_failed(self, parser):
        """parse_message extracts passed and failed from pytest summary."""
        parser.parse_message("===== 10 passed, 3 failed in 0.45s =====")
        result = parser.to_result()

        assert result["tests_passed"] == 10
        assert result["tests_failed"] == 3

    def test_parse_pytest_summary_passed_failed_skipped(self, parser):
        """parse_message handles full pytest summary with skipped."""
        parser.parse_message("===== 8 passed, 2 failed, 1 skipped in 0.30s =====")
        result = parser.to_result()

        assert result["tests_passed"] == 8
        assert result["tests_failed"] == 2

    def test_parse_pytest_simple_pattern(self, parser):
        """parse_message extracts from simple pytest output."""
        parser.parse_message("5 passed in 0.12s")
        result = parser.to_result()

        assert result["tests_passed"] == 5

    def test_parse_pytest_simple_without_time(self, parser):
        """parse_message extracts simple passed count without time."""
        parser.parse_message("20 passed")
        result = parser.to_result()

        assert result["tests_passed"] == 20

    def test_parse_pytest_prefers_higher_count(self, parser):
        """parse_message keeps higher test count when multiple matches."""
        # Earlier simple match
        parser.parse_message("5 tests passed")
        # Later pytest summary should update if higher
        parser.parse_message("===== 15 passed in 0.23s =====")
        result = parser.to_result()

        assert result["tests_passed"] == 15

    def test_parse_pytest_keeps_existing_if_higher(self, parser):
        """parse_message keeps existing count if higher than summary."""
        parser.parse_message("25 tests passed")
        # Lower count in summary should not overwrite
        parser.parse_message("===== 15 passed in 0.23s =====")
        result = parser.to_result()

        assert result["tests_passed"] == 25


class TestParseTaskWorkStream:
    """Test AgentInvoker._parse_task_work_stream method."""

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
        )

    def test_parse_task_work_stream_returns_result(self, invoker):
        """_parse_task_work_stream returns accumulated result."""
        parser = TaskWorkStreamParser()
        result = invoker._parse_task_work_stream("12 tests passed", parser)

        assert result["tests_passed"] == 12

    def test_parse_task_work_stream_accumulates(self, invoker):
        """_parse_task_work_stream accumulates across calls."""
        parser = TaskWorkStreamParser()
        invoker._parse_task_work_stream("Phase 2: Planning", parser)
        invoker._parse_task_work_stream("8 tests passed", parser)
        result = invoker._parse_task_work_stream("Coverage: 90%", parser)

        assert "phase_2" in result["phases"]
        assert result["tests_passed"] == 8
        assert result["coverage"] == 90.0

    def test_parse_task_work_stream_with_empty_message(self, invoker):
        """_parse_task_work_stream handles empty messages."""
        parser = TaskWorkStreamParser()
        result = invoker._parse_task_work_stream("", parser)

        assert result == {}

    def test_parse_task_work_stream_integration_pattern(self, invoker):
        """_parse_task_work_stream works with typical integration pattern."""
        parser = TaskWorkStreamParser()
        messages = [
            "Starting task-work...",
            "Phase 2: Implementation Planning",
            "✓ Phase 2 complete",
            "Phase 3: Implementation",
            "Modified: src/feature.py",
            "Created: tests/test_feature.py",
            "Running tests...",
            "15 tests passed, 0 tests failed",
            "Coverage: 88.5%",
            "all quality gates passed",
            "✓ Phase 3 complete",
        ]

        for message in messages:
            invoker._parse_task_work_stream(message, parser)

        result = parser.to_result()

        assert result["phases"]["phase_2"]["completed"] is True
        assert result["phases"]["phase_3"]["completed"] is True
        assert result["tests_passed"] == 15
        assert result["tests_failed"] == 0
        assert result["coverage"] == 88.5
        assert result["quality_gates_passed"] is True
        assert "src/feature.py" in result["files_modified"]
        assert "tests/test_feature.py" in result["files_created"]


# ==================== Task Work Results Writer Tests ====================


class TestWriteTaskWorkResults:
    """Test AgentInvoker._write_task_work_results method.

    This method writes parsed quality gate results to task_work_results.json
    in the format expected by Coach validation.

    Coverage Target: >=90%
    Test Count: 15+ tests
    """

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
        )

    # -------------- Basic Write Tests --------------

    def test_write_creates_file(self, invoker, worktree_path):
        """_write_task_work_results creates the results file."""
        result_data = {"tests_passed": 10, "tests_failed": 0}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        assert results_path.exists()
        assert results_path.name == "task_work_results.json"

    def test_write_creates_directory_structure(self, invoker, worktree_path):
        """_write_task_work_results creates directory structure if not exists."""
        result_data = {"tests_passed": 5}

        results_path = invoker._write_task_work_results("TASK-NEW-001", result_data)

        expected_dir = worktree_path / ".guardkit" / "autobuild" / "TASK-NEW-001"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

    def test_write_correct_location(self, invoker, worktree_path):
        """Results file is written to correct Coach-expected location."""
        result_data = {"tests_passed": 10}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        expected_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-001" / "task_work_results.json"
        )
        assert results_path == expected_path

    def test_write_valid_json(self, invoker, worktree_path):
        """Results file contains valid JSON."""
        result_data = {"tests_passed": 10, "coverage": 85.5}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        content = results_path.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    # -------------- Schema Validation Tests --------------

    def test_write_includes_task_id(self, invoker, worktree_path):
        """Results include task_id field."""
        result_data = {}

        results_path = invoker._write_task_work_results("TASK-XYZ-123", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["task_id"] == "TASK-XYZ-123"

    def test_write_includes_timestamp(self, invoker, worktree_path):
        """Results include ISO format timestamp."""
        result_data = {}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert "timestamp" in parsed
        # Verify ISO format (should parse without error)
        from datetime import datetime
        datetime.fromisoformat(parsed["timestamp"])

    def test_write_includes_quality_gates_section(self, invoker, worktree_path):
        """Results include quality_gates nested structure."""
        result_data = {
            "tests_passed": 12,
            "tests_failed": 0,
            "coverage": 85.5,
            "quality_gates_passed": True,
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert "quality_gates" in parsed
        qg = parsed["quality_gates"]
        assert qg["tests_passing"] is True
        assert qg["tests_passed"] == 12
        assert qg["tests_failed"] == 0
        assert qg["coverage"] == 85.5
        assert qg["coverage_met"] is True
        assert qg["all_passed"] is True

    def test_write_includes_phases(self, invoker, worktree_path):
        """Results include phases information."""
        result_data = {
            "phases": {
                "phase_3": {"detected": True, "text": "Implementation", "completed": True},
                "phase_4": {"detected": True, "text": "Testing", "completed": True},
            }
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert "phases" in parsed
        assert "phase_3" in parsed["phases"]
        assert "phase_4" in parsed["phases"]

    def test_write_includes_file_lists(self, invoker, worktree_path):
        """Results include files_modified and files_created."""
        result_data = {
            "files_modified": ["src/auth.py", "src/config.py"],
            "files_created": ["tests/test_auth.py"],
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert "files_modified" in parsed
        assert "files_created" in parsed
        assert "src/auth.py" in parsed["files_modified"]
        assert "tests/test_auth.py" in parsed["files_created"]

    def test_write_deduplicates_file_lists(self, invoker, worktree_path):
        """Results deduplicate file lists."""
        result_data = {
            "files_modified": ["src/auth.py", "src/auth.py", "src/config.py"],
            "files_created": ["tests/test.py", "tests/test.py"],
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["files_modified"].count("src/auth.py") == 1
        assert parsed["files_created"].count("tests/test.py") == 1

    def test_write_sorts_file_lists(self, invoker, worktree_path):
        """Results have sorted file lists."""
        result_data = {
            "files_modified": ["z_file.py", "a_file.py", "m_file.py"],
            "files_created": [],
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["files_modified"] == ["a_file.py", "m_file.py", "z_file.py"]

    # -------------- Completion Status Tests --------------

    def test_write_completed_true_when_quality_gates_passed(self, invoker, worktree_path):
        """completed is True when quality_gates_passed is True."""
        result_data = {"quality_gates_passed": True}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["completed"] is True

    def test_write_completed_true_when_tests_pass_no_failures(self, invoker, worktree_path):
        """completed is True when tests pass with no failures."""
        result_data = {"tests_passed": 10, "tests_failed": 0}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["completed"] is True

    def test_write_completed_false_when_tests_fail(self, invoker, worktree_path):
        """completed is False when tests fail."""
        result_data = {
            "tests_passed": 8,
            "tests_failed": 2,
            "quality_gates_passed": False,
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["completed"] is False

    # -------------- Edge Cases Tests --------------

    def test_write_handles_empty_result_data(self, invoker, worktree_path):
        """_write_task_work_results handles empty result data gracefully."""
        result_data = {}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["task_id"] == "TASK-001"
        assert parsed["completed"] is False
        assert parsed["phases"] == {}
        assert parsed["files_modified"] == []
        assert parsed["files_created"] == []

    def test_write_handles_none_coverage(self, invoker, worktree_path):
        """_write_task_work_results handles None coverage."""
        result_data = {"tests_passed": 10, "coverage": None}

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["quality_gates"]["coverage"] is None
        assert parsed["quality_gates"]["coverage_met"] is None

    def test_write_handles_partial_data(self, invoker, worktree_path):
        """_write_task_work_results handles partial result data."""
        result_data = {"tests_passed": 5}  # Only tests_passed provided

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert parsed["quality_gates"]["tests_passed"] == 5
        assert parsed["quality_gates"]["tests_failed"] == 0
        assert parsed["quality_gates"]["coverage"] is None

    def test_write_includes_summary(self, invoker, worktree_path):
        """Results include human-readable summary."""
        result_data = {
            "tests_passed": 12,
            "coverage": 85.5,
            "quality_gates_passed": True,
        }

        results_path = invoker._write_task_work_results("TASK-001", result_data)

        parsed = json.loads(results_path.read_text())
        assert "summary" in parsed
        assert "12 tests passed" in parsed["summary"]
        assert "85.5% coverage" in parsed["summary"]

    def test_write_overwrites_existing_file(self, invoker, worktree_path):
        """_write_task_work_results overwrites existing file."""
        # Write first version
        result_data_v1 = {"tests_passed": 5}
        invoker._write_task_work_results("TASK-001", result_data_v1)

        # Write second version
        result_data_v2 = {"tests_passed": 15}
        results_path = invoker._write_task_work_results("TASK-001", result_data_v2)

        parsed = json.loads(results_path.read_text())
        assert parsed["quality_gates"]["tests_passed"] == 15


# ==================== Generate Summary Tests ====================


class TestGenerateSummary:
    """Test AgentInvoker._generate_summary method.

    This method generates human-readable summaries from task-work results.

    Coverage Target: >=90%
    Test Count: 10+ tests
    """

    @pytest.fixture
    def invoker(self, worktree_path):
        """Create AgentInvoker instance."""
        return AgentInvoker(
            worktree_path=worktree_path,
            sdk_timeout_seconds=60,
        )

    # -------------- Basic Summary Tests --------------

    def test_summary_with_tests_passed(self, invoker):
        """Summary includes test pass count."""
        result_data = {"tests_passed": 12}

        summary = invoker._generate_summary(result_data)

        assert "12 tests passed" in summary

    def test_summary_with_tests_failed(self, invoker):
        """Summary includes test fail count."""
        result_data = {"tests_failed": 3}

        summary = invoker._generate_summary(result_data)

        assert "3 tests failed" in summary

    def test_summary_with_coverage(self, invoker):
        """Summary includes coverage percentage."""
        result_data = {"coverage": 85.5}

        summary = invoker._generate_summary(result_data)

        assert "85.5% coverage" in summary

    def test_summary_with_quality_gates_passed(self, invoker):
        """Summary indicates quality gates passed."""
        result_data = {"quality_gates_passed": True}

        summary = invoker._generate_summary(result_data)

        assert "all quality gates passed" in summary

    def test_summary_with_quality_gates_failed(self, invoker):
        """Summary indicates quality gates failed."""
        result_data = {"quality_gates_passed": False}

        summary = invoker._generate_summary(result_data)

        assert "quality gates failed" in summary

    # -------------- Combined Summary Tests --------------

    def test_summary_combined_all_fields(self, invoker):
        """Summary combines all available fields."""
        result_data = {
            "tests_passed": 12,
            "coverage": 85.5,
            "quality_gates_passed": True,
        }

        summary = invoker._generate_summary(result_data)

        assert "12 tests passed" in summary
        assert "85.5% coverage" in summary
        assert "all quality gates passed" in summary
        # Verify comma separation
        assert ", " in summary

    def test_summary_combined_with_failures(self, invoker):
        """Summary combines all fields including failures."""
        result_data = {
            "tests_passed": 8,
            "tests_failed": 2,
            "coverage": 75.0,
            "quality_gates_passed": False,
        }

        summary = invoker._generate_summary(result_data)

        assert "8 tests passed" in summary
        assert "2 tests failed" in summary
        assert "75.0% coverage" in summary
        assert "quality gates failed" in summary

    # -------------- Edge Cases Tests --------------

    def test_summary_empty_data(self, invoker):
        """Summary returns default for empty data."""
        result_data = {}

        summary = invoker._generate_summary(result_data)

        assert summary == "Implementation completed"

    def test_summary_zero_tests_not_included(self, invoker):
        """Summary doesn't include zero test count."""
        result_data = {"tests_passed": 0}

        summary = invoker._generate_summary(result_data)

        assert "0 tests passed" not in summary

    def test_summary_zero_failures_not_included(self, invoker):
        """Summary doesn't include zero failure count."""
        result_data = {"tests_passed": 10, "tests_failed": 0}

        summary = invoker._generate_summary(result_data)

        assert "0 tests failed" not in summary

    def test_summary_none_values_not_included(self, invoker):
        """Summary doesn't include None values."""
        result_data = {
            "tests_passed": None,
            "coverage": None,
            "quality_gates_passed": None,
        }

        summary = invoker._generate_summary(result_data)

        assert summary == "Implementation completed"

    def test_summary_integer_coverage(self, invoker):
        """Summary handles integer coverage."""
        result_data = {"coverage": 90}

        summary = invoker._generate_summary(result_data)

        assert "90% coverage" in summary


# =========================================================================
# Heartbeat Logging Tests (TASK-FBP-002)
# =========================================================================


class TestHeartbeatLogging:
    """Test heartbeat logging during SDK invocations.

    Coverage Target: 100% for async_heartbeat context manager
    Test Count: 5 tests
    """

    @pytest.mark.asyncio
    async def test_heartbeat_logs_at_interval(self, caplog):
        """Heartbeat logs every N seconds during long operations."""
        import logging

        caplog.set_level(logging.INFO, logger="guardkit.orchestrator.agent_invoker")

        # Use a short interval for testing (1 second)
        async with async_heartbeat("TASK-001", "Player invocation", interval=1):
            await asyncio.sleep(2.5)  # Should log at 1s and 2s

        # Verify heartbeat messages were logged
        assert "[TASK-001] Player invocation in progress... (1s elapsed)" in caplog.text
        assert "[TASK-001] Player invocation in progress... (2s elapsed)" in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_cancelled_on_completion(self, caplog):
        """Heartbeat stops cleanly when context exits."""
        import logging

        caplog.set_level(logging.INFO, logger="guardkit.orchestrator.agent_invoker")

        async with async_heartbeat("TASK-002", "Coach validation", interval=1):
            await asyncio.sleep(0.1)  # Exit quickly before first heartbeat

        # Wait a bit to ensure no stray logs after context exit
        await asyncio.sleep(1.5)

        # No heartbeat should have been logged (we exited too early)
        assert "[TASK-002] Coach validation in progress..." not in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_cancelled_on_exception(self, caplog):
        """Heartbeat stops cleanly when exception occurs."""
        import logging

        caplog.set_level(logging.INFO, logger="guardkit.orchestrator.agent_invoker")

        with pytest.raises(ValueError):
            async with async_heartbeat("TASK-003", "test phase", interval=1):
                await asyncio.sleep(0.1)
                raise ValueError("Test exception")

        # Wait a bit to ensure no stray logs after exception
        await asyncio.sleep(1.5)

        # No heartbeat should have been logged (we exited too early)
        assert "[TASK-003] test phase in progress..." not in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_uses_correct_task_id(self, caplog):
        """Heartbeat logs use the provided task_id."""
        import logging

        caplog.set_level(logging.INFO, logger="guardkit.orchestrator.agent_invoker")

        async with async_heartbeat("TASK-FBP-002", "design phase", interval=1):
            await asyncio.sleep(1.5)

        assert "[TASK-FBP-002] design phase in progress..." in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_does_not_block_operation(self):
        """Heartbeat does not interfere with the wrapped operation."""
        result = None

        async def long_operation():
            await asyncio.sleep(0.1)
            return "success"

        async with async_heartbeat("TASK-004", "test phase", interval=1):
            result = await long_operation()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_heartbeat_custom_interval(self, caplog):
        """Heartbeat respects custom interval parameter."""
        import logging

        caplog.set_level(logging.INFO, logger="guardkit.orchestrator.agent_invoker")

        # Use 2 second interval, wait 3 seconds
        async with async_heartbeat("TASK-005", "test phase", interval=2):
            await asyncio.sleep(3.5)

        # Should log at 2s but not at 1s
        assert "(1s elapsed)" not in caplog.text
        assert "(2s elapsed)" in caplog.text


# ==================== File Count Constraint Validation Tests ====================


class TestFileCountConstraintValidation:
    """Tests for documentation level file count constraints."""

    def test_documentation_level_max_files_constant(self):
        """Verify constant mapping is correct."""
        assert DOCUMENTATION_LEVEL_MAX_FILES["minimal"] == 2
        assert DOCUMENTATION_LEVEL_MAX_FILES["standard"] == 2
        assert DOCUMENTATION_LEVEL_MAX_FILES["comprehensive"] is None

    def test_validate_file_count_minimal_within_limit(self, agent_invoker, caplog):
        """Minimal level allows up to 2 files without warning."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        agent_invoker._validate_file_count_constraint(
            task_id="TASK-001",
            documentation_level="minimal",
            files_created=["file1.py", "file2.py"],
        )

        # No warning should be logged for 2 files (within limit)
        assert "Documentation level constraint violated" not in caplog.text

    def test_validate_file_count_minimal_exceeds_limit(self, agent_invoker, caplog):
        """Minimal level logs warning when >2 files created."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        agent_invoker._validate_file_count_constraint(
            task_id="TASK-001",
            documentation_level="minimal",
            files_created=["file1.py", "file2.py", "file3.py"],
        )

        # Warning should be logged for 3 files (exceeds limit of 2)
        assert "Documentation level constraint violated" in caplog.text
        assert "created 3 files" in caplog.text
        assert "max allowed 2" in caplog.text
        assert "minimal" in caplog.text

    def test_validate_file_count_standard_within_limit(self, agent_invoker, caplog):
        """Standard level allows up to 2 files without warning."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        agent_invoker._validate_file_count_constraint(
            task_id="TASK-002",
            documentation_level="standard",
            files_created=["src/module.py"],
        )

        # No warning for 1 file (within limit)
        assert "Documentation level constraint violated" not in caplog.text

    def test_validate_file_count_standard_exceeds_limit(self, agent_invoker, caplog):
        """Standard level logs warning when >2 files created."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        agent_invoker._validate_file_count_constraint(
            task_id="TASK-002",
            documentation_level="standard",
            files_created=["a.py", "b.py", "c.py", "d.py"],
        )

        # Warning should be logged for 4 files (exceeds limit of 2)
        assert "Documentation level constraint violated" in caplog.text
        assert "created 4 files" in caplog.text

    def test_validate_file_count_comprehensive_unlimited(self, agent_invoker, caplog):
        """Comprehensive level has no file limit."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        # Create 10 files - should not trigger warning
        agent_invoker._validate_file_count_constraint(
            task_id="TASK-003",
            documentation_level="comprehensive",
            files_created=[f"file{i}.py" for i in range(10)],
        )

        # No warning should be logged (comprehensive has no limit)
        assert "Documentation level constraint violated" not in caplog.text

    def test_validate_file_count_unknown_level_no_limit(self, agent_invoker, caplog):
        """Unknown documentation level is treated as having no limit."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        agent_invoker._validate_file_count_constraint(
            task_id="TASK-004",
            documentation_level="unknown_level",
            files_created=[f"file{i}.py" for i in range(15)],
        )

        # No warning for unknown level (treated as no limit)
        assert "Documentation level constraint violated" not in caplog.text

    def test_validate_file_count_empty_files_list(self, agent_invoker, caplog):
        """Empty files list should not trigger warning."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        agent_invoker._validate_file_count_constraint(
            task_id="TASK-005",
            documentation_level="minimal",
            files_created=[],
        )

        # No warning for empty list
        assert "Documentation level constraint violated" not in caplog.text

    def test_validate_file_count_warning_includes_file_preview(self, agent_invoker, caplog):
        """Warning message includes preview of created files."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        files = ["a.py", "b.py", "c.py", "d.py"]
        agent_invoker._validate_file_count_constraint(
            task_id="TASK-006",
            documentation_level="minimal",
            files_created=files,
        )

        # Check that file names appear in warning
        assert "a.py" in caplog.text

    def test_validate_file_count_truncates_long_file_list(self, agent_invoker, caplog):
        """Warning truncates file list when more than 5 files."""
        import logging

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker")

        # Create 8 files
        files = [f"file{i}.py" for i in range(8)]
        agent_invoker._validate_file_count_constraint(
            task_id="TASK-007",
            documentation_level="minimal",
            files_created=files,
        )

        # Check that ellipsis is added for truncated list
        assert "..." in caplog.text
        assert "created 8 files" in caplog.text


# ==================== Tests for Direct Mode Routing (TASK-FB-2D8B) ====================


class TestDirectModeRouting:
    """Test suite for direct mode task routing.

    Tests the implementation_mode: direct routing logic that bypasses
    task-work delegation for simple tasks that don't require an
    implementation plan.
    """

    @pytest.fixture
    def direct_mode_task_file(self, worktree_path):
        """Create a task file with implementation_mode: direct."""
        tasks_dir = worktree_path / "tasks" / "backlog"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / "TASK-DIRECT-001-test-task.md"
        task_file.write_text("""---
id: TASK-DIRECT-001
title: Direct mode test task
status: backlog
implementation_mode: direct
---

# Test Task

## Description
Test direct mode routing.

## Acceptance Criteria
- [ ] File created successfully
""")
        return task_file

    @pytest.fixture
    def task_work_mode_task_file(self, worktree_path):
        """Create a task file with implementation_mode: task-work."""
        tasks_dir = worktree_path / "tasks" / "backlog"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / "TASK-TW-001-test-task.md"
        task_file.write_text("""---
id: TASK-TW-001
title: Task-work mode test task
status: backlog
implementation_mode: task-work
---

# Test Task

## Description
Test task-work mode routing.

## Acceptance Criteria
- [ ] Feature implemented
""")
        return task_file

    def test_get_implementation_mode_direct(self, agent_invoker, direct_mode_task_file):
        """_get_implementation_mode returns 'direct' for direct mode tasks."""
        mode = agent_invoker._get_implementation_mode("TASK-DIRECT-001")
        assert mode == "direct"

    def test_get_implementation_mode_task_work(self, agent_invoker, task_work_mode_task_file):
        """_get_implementation_mode returns 'task-work' for task-work mode tasks."""
        mode = agent_invoker._get_implementation_mode("TASK-TW-001")
        assert mode == "task-work"

    def test_get_implementation_mode_default(self, agent_invoker, worktree_path):
        """_get_implementation_mode returns 'task-work' when no mode specified."""
        # Create task file without implementation_mode
        tasks_dir = worktree_path / "tasks" / "backlog"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / "TASK-NOMODE-001-test.md"
        task_file.write_text("""---
id: TASK-NOMODE-001
title: No mode specified
status: backlog
---

# Test Task
""")

        mode = agent_invoker._get_implementation_mode("TASK-NOMODE-001")
        assert mode == "task-work"

    def test_get_implementation_mode_task_not_found(self, agent_invoker):
        """_get_implementation_mode returns 'task-work' when task file not found."""
        mode = agent_invoker._get_implementation_mode("TASK-NONEXISTENT-001")
        assert mode == "task-work"

    def test_get_implementation_mode_unknown_normalized_to_task_work(
        self, agent_invoker, worktree_path
    ):
        """_get_implementation_mode normalizes unknown modes (like 'manual') to 'task-work'."""
        # Create task file with legacy 'manual' mode (now deprecated)
        tasks_dir = worktree_path / "tasks" / "backlog"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / "TASK-MANUAL-001-test.md"
        task_file.write_text("""---
id: TASK-MANUAL-001
title: Task with legacy manual mode
status: backlog
implementation_mode: manual
---

# Test Task

## Description
Task with deprecated manual mode - should be normalized to task-work.
""")

        mode = agent_invoker._get_implementation_mode("TASK-MANUAL-001")
        # Unknown modes (including legacy 'manual') should be normalized to task-work
        assert mode == "task-work"

    @pytest.mark.asyncio
    async def test_direct_mode_bypasses_task_work_delegation(
        self, agent_invoker, worktree_path, direct_mode_task_file, sample_player_report
    ):
        """Direct mode tasks bypass task-work delegation."""
        # Create player report
        create_report_file(
            worktree_path, "TASK-DIRECT-001", 1, "player", sample_player_report
        )

        # Mock SDK invocation (not task-work delegation)
        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ) as mock_sdk, patch.object(
            agent_invoker, "_invoke_task_work_implement", new_callable=AsyncMock
        ) as mock_task_work:

            result = await agent_invoker.invoke_player(
                task_id="TASK-DIRECT-001",
                turn=1,
                requirements="Create documentation",
            )

            # Verify direct SDK was called, not task-work delegation
            assert mock_sdk.called
            assert not mock_task_work.called
            assert result.success is True

    @pytest.mark.asyncio
    async def test_direct_mode_writes_results_file(
        self, agent_invoker, worktree_path, direct_mode_task_file, sample_player_report
    ):
        """Direct mode writes task_work_results.json for Coach."""
        create_report_file(
            worktree_path, "TASK-DIRECT-001", 1, "player", sample_player_report
        )

        with patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ):
            await agent_invoker.invoke_player(
                task_id="TASK-DIRECT-001",
                turn=1,
                requirements="Create documentation",
            )

        # Verify results file was created
        results_path = (
            worktree_path / ".guardkit" / "autobuild" / "TASK-DIRECT-001" / "task_work_results.json"
        )
        assert results_path.exists()

        results = json.loads(results_path.read_text())
        assert results["task_id"] == "TASK-DIRECT-001"
        assert results["implementation_mode"] == "direct"
        assert results["success"] is True

    @pytest.mark.asyncio
    async def test_task_work_mode_still_uses_delegation(
        self, agent_invoker, worktree_path, task_work_mode_task_file
    ):
        """Task-work mode tasks continue using task-work delegation when flag is set."""
        # Enable task-work delegation
        agent_invoker.use_task_work_delegation = True

        # Mock the task-work path to avoid needing full setup
        with patch.object(
            agent_invoker, "_ensure_design_approved_state"
        ) as mock_ensure, patch.object(
            agent_invoker, "_invoke_task_work_implement", new_callable=AsyncMock
        ) as mock_task_work, patch.object(
            agent_invoker, "_invoke_with_role", new_callable=AsyncMock
        ) as mock_sdk:
            mock_task_work.return_value = TaskWorkResult(success=False, output={}, error="Mock")

            result = await agent_invoker.invoke_player(
                task_id="TASK-TW-001",
                turn=1,
                requirements="Implement feature",
            )

            # Verify task-work delegation was attempted (not direct SDK)
            assert mock_ensure.called
            assert mock_task_work.called
            assert not mock_sdk.called

    def test_write_direct_mode_results_creates_file(self, agent_invoker, worktree_path):
        """_write_direct_mode_results creates task_work_results.json."""
        task_id = "TASK-DM-001"
        player_report = {
            "task_id": task_id,
            "turn": 1,
            "files_modified": ["README.md"],
            "files_created": ["docs/new-file.md"],
            "tests_run": False,
            "tests_passed": False,
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        assert result_path.exists()
        results = json.loads(result_path.read_text())

        assert results["task_id"] == task_id
        assert results["implementation_mode"] == "direct"
        assert results["success"] is True
        assert results["files_created"] == ["docs/new-file.md"]
        assert results["files_modified"] == ["README.md"]

    def test_write_direct_mode_results_handles_failure(self, agent_invoker, worktree_path):
        """_write_direct_mode_results handles failure cases."""
        task_id = "TASK-DM-002"
        player_report = {"task_id": task_id, "turn": 1}
        error_msg = "Player report not found"

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=False, error=error_msg
        )

        results = json.loads(result_path.read_text())

        assert results["success"] is False
        assert results["error"] == error_msg
        assert results["completed"] is False

    def test_direct_mode_results_coach_compatible(self, agent_invoker, worktree_path):
        """Direct mode results contain fields needed by Coach."""
        task_id = "TASK-DM-003"
        player_report = {
            "task_id": task_id,
            "files_modified": ["src/main.py"],
            "tests_run": True,
            "tests_passed": True,
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())

        # Verify Coach-required fields
        assert "task_id" in results
        assert "completed" in results
        assert "quality_gates" in results
        assert "summary" in results
        assert "files_created" in results
        assert "files_modified" in results

        # Verify quality_gates structure
        gates = results["quality_gates"]
        assert "all_passed" in gates
        assert gates["quality_gates_relaxed"] is True  # Signal to Coach

    def test_direct_mode_results_deduplicates_files(self, agent_invoker, worktree_path):
        """Direct mode results deduplicate and sort file lists."""
        task_id = "TASK-DM-004"
        player_report = {
            "task_id": task_id,
            "files_modified": ["b.py", "a.py", "b.py", "c.py", "a.py"],
            "files_created": ["z.py", "a.py", "z.py"],
            "tests_run": True,
            "tests_passed": True,
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())

        # Verify deduplication and sorting
        assert results["files_modified"] == ["a.py", "b.py", "c.py"]
        assert results["files_created"] == ["a.py", "z.py"]

    # ========================================================================
    # Direct Mode Test Count Propagation Tests (TASK-FIX-CEE8a)
    # ========================================================================

    def test_direct_mode_derives_test_count_from_tests_written(
        self, agent_invoker, worktree_path
    ):
        """AC-001: tests_passed=True with tests_written list produces correct count."""
        task_id = "TASK-CEE8a-001"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "tests_written": ["tests/test_a.py", "tests/test_b.py"],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passed"] == 2

    def test_direct_mode_zero_count_when_tests_failed(
        self, agent_invoker, worktree_path
    ):
        """AC-002: tests_passed=False with tests_written list produces 0."""
        task_id = "TASK-CEE8a-002"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": False,
            "tests_written": ["tests/test_a.py"],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passed"] == 0

    def test_direct_mode_zero_count_when_tests_written_empty(
        self, agent_invoker, worktree_path
    ):
        """AC-003: tests_passed=True with empty tests_written produces 0."""
        task_id = "TASK-CEE8a-003"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "tests_written": [],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passed"] == 0

    def test_direct_mode_preserves_explicit_tests_passed_count(
        self, agent_invoker, worktree_path
    ):
        """AC-004: task-work path with tests_passed_count=12 still works."""
        task_id = "TASK-CEE8a-004"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "tests_passed_count": 12,
            "tests_written": ["tests/test_a.py"],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passed"] == 12

    def test_direct_mode_no_tests_written_field(
        self, agent_invoker, worktree_path
    ):
        """Direct mode Player with no tests_written field produces 0."""
        task_id = "TASK-CEE8a-005"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passed"] == 0

    def test_direct_mode_no_tests_run(
        self, agent_invoker, worktree_path
    ):
        """Direct mode Player that didn't run tests produces 0."""
        task_id = "TASK-CEE8a-006"
        player_report = {
            "task_id": task_id,
            "tests_run": False,
            "tests_passed": False,
            "tests_written": ["tests/test_a.py"],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["quality_gates"]["tests_passed"] == 0

    # ========================================================================
    # Direct Mode tests_written Propagation Tests (TASK-FIX-93A1)
    # ========================================================================

    def test_direct_mode_results_include_tests_written(
        self, agent_invoker, worktree_path
    ):
        """AC-001: _write_direct_mode_results includes tests_written in results."""
        task_id = "TASK-93A1-DM-001"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "tests_written": ["tests/health/test_router.py", "tests/api/test_endpoints.py"],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert "tests_written" in results
        assert results["tests_written"] == [
            "tests/api/test_endpoints.py",
            "tests/health/test_router.py",
        ]

    def test_direct_mode_results_tests_written_empty_when_no_tests(
        self, agent_invoker, worktree_path
    ):
        """AC-004: tests_written is [] when Player reports no tests."""
        task_id = "TASK-93A1-DM-002"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "tests_written": [],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["tests_written"] == []

    def test_direct_mode_results_tests_written_defaults_empty(
        self, agent_invoker, worktree_path
    ):
        """tests_written defaults to [] when Player report has no field."""
        task_id = "TASK-93A1-DM-003"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["tests_written"] == []

    def test_direct_mode_results_tests_written_deduplicated(
        self, agent_invoker, worktree_path
    ):
        """AC-005: tests_written is deduplicated in direct mode results."""
        task_id = "TASK-93A1-DM-004"
        player_report = {
            "task_id": task_id,
            "tests_run": True,
            "tests_passed": True,
            "tests_written": [
                "tests/test_a.py",
                "tests/test_b.py",
                "tests/test_a.py",  # duplicate
            ],
            "files_modified": ["src/main.py"],
        }

        result_path = agent_invoker._write_direct_mode_results(
            task_id, player_report, success=True
        )

        results = json.loads(result_path.read_text())
        assert results["tests_written"] == ["tests/test_a.py", "tests/test_b.py"]

    # ========================================================================
    # Direct Mode Player Report Tests (TASK-PRH-001)
    # ========================================================================

    def test_write_player_report_for_direct_mode_creates_file(
        self, agent_invoker, worktree_path
    ):
        """_write_player_report_for_direct_mode creates player_turn_N.json."""
        task_id = "TASK-PRH-001"
        turn = 1
        player_report = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": ["README.md"],
            "files_created": ["docs/new-file.md"],
            "tests_run": False,
            "tests_passed": False,
            "implementation_notes": "Test implementation",
        }

        result_path = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report, success=True
        )

        assert result_path.exists()
        report = json.loads(result_path.read_text())

        assert report["task_id"] == task_id
        assert report["turn"] == turn
        assert report["implementation_mode"] == "direct"
        assert report["success"] is True
        assert report["files_created"] == ["docs/new-file.md"]
        assert report["files_modified"] == ["README.md"]

    def test_write_player_report_for_direct_mode_handles_failure(
        self, agent_invoker, worktree_path
    ):
        """_write_player_report_for_direct_mode handles failure cases."""
        task_id = "TASK-PRH-002"
        turn = 2
        player_report = {"task_id": task_id, "turn": turn}
        error_msg = "Player SDK invocation failed"

        result_path = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report, success=False, error=error_msg
        )

        report = json.loads(result_path.read_text())

        assert report["success"] is False
        assert report["error"] == error_msg
        assert report["task_id"] == task_id
        assert report["turn"] == turn

    def test_write_player_report_for_direct_mode_schema_compliant(
        self, agent_invoker, worktree_path
    ):
        """Player report contains all PLAYER_REPORT_SCHEMA fields."""
        task_id = "TASK-PRH-003"
        turn = 1
        player_report = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": ["src/main.py"],
            "files_created": ["tests/test_main.py"],
            "tests_written": ["test_feature"],
            "tests_run": True,
            "tests_passed": True,
            "test_output_summary": "5 passed in 0.2s",
            "implementation_notes": "Added feature X",
            "concerns": ["Performance may degrade for large inputs"],
            "requirements_addressed": ["REQ-001"],
            "requirements_remaining": ["REQ-002"],
        }

        result_path = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report, success=True
        )

        report = json.loads(result_path.read_text())

        # Verify all PLAYER_REPORT_SCHEMA fields are present
        from guardkit.orchestrator.agent_invoker import PLAYER_REPORT_SCHEMA

        for field, expected_type in PLAYER_REPORT_SCHEMA.items():
            assert field in report, f"Missing required field: {field}"
            assert isinstance(
                report[field], expected_type
            ), f"Field {field} has wrong type: expected {expected_type}, got {type(report[field])}"

    def test_write_player_report_for_direct_mode_correct_path(
        self, agent_invoker, worktree_path
    ):
        """Player report is written to correct path."""
        task_id = "TASK-PRH-004"
        turn = 3
        player_report = {"task_id": task_id, "turn": turn}

        result_path = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report, success=True
        )

        # Verify path follows TaskArtifactPaths convention
        expected_path = worktree_path / f".guardkit/autobuild/{task_id}/player_turn_{turn}.json"
        assert result_path == expected_path
        assert result_path.exists()

    def test_write_player_report_for_direct_mode_defaults_for_missing_fields(
        self, agent_invoker, worktree_path
    ):
        """Player report provides defaults for missing fields."""
        task_id = "TASK-PRH-005"
        turn = 1
        # Minimal report with only task_id and turn
        player_report = {"task_id": task_id, "turn": turn}

        result_path = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report, success=True
        )

        report = json.loads(result_path.read_text())

        # Verify defaults are applied
        assert report["files_modified"] == []
        assert report["files_created"] == []
        assert report["tests_written"] == []
        assert report["tests_run"] is False
        assert report["tests_passed"] is False
        assert report["test_output_summary"] == ""
        assert "Direct mode" in report["implementation_notes"]
        assert report["concerns"] == []
        assert report["requirements_addressed"] == []
        assert report["requirements_remaining"] == []

    def test_write_player_report_for_direct_mode_overwrites_existing(
        self, agent_invoker, worktree_path
    ):
        """Player report can overwrite existing file (idempotent)."""
        task_id = "TASK-PRH-006"
        turn = 1

        # First write
        player_report_v1 = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": ["v1.py"],
        }
        result_path = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report_v1, success=True
        )

        report_v1 = json.loads(result_path.read_text())
        assert report_v1["files_modified"] == ["v1.py"]

        # Second write (overwrite)
        player_report_v2 = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": ["v2.py", "v2_extra.py"],
        }
        result_path_v2 = agent_invoker._write_player_report_for_direct_mode(
            task_id, turn, player_report_v2, success=True
        )

        report_v2 = json.loads(result_path_v2.read_text())
        assert report_v2["files_modified"] == ["v2.py", "v2_extra.py"]
        assert result_path == result_path_v2


# ============================================================================
# Retry Mechanism Tests
# ============================================================================


class TestRetryMechanism:
    """Test retry mechanism for filesystem race conditions."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_immediately(self, agent_invoker):
        """Test that retry returns immediately when function succeeds on first try."""
        call_count = 0

        def successful_function():
            nonlocal call_count
            call_count += 1
            return {"result": "success"}

        result = await agent_invoker._retry_with_backoff(
            successful_function,
            max_retries=3,
            initial_delay=0.1,
        )

        assert result == {"result": "success"}
        assert call_count == 1  # Should only be called once

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_one_retry(self, agent_invoker):
        """Test that retry succeeds after one failed attempt."""
        call_count = 0

        def fails_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError("File not ready yet")
            return {"result": "success"}

        import time

        start = time.time()
        result = await agent_invoker._retry_with_backoff(
            fails_once,
            max_retries=3,
            initial_delay=0.1,
        )
        elapsed = time.time() - start

        assert result == {"result": "success"}
        assert call_count == 2  # Should be called twice
        # Should have delayed at least 0.1s for first retry
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_two_retries(self, agent_invoker):
        """Test that retry succeeds after two failed attempts with exponential backoff."""
        call_count = 0

        def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise FileNotFoundError("File not ready yet")
            return {"result": "success"}

        import time

        start = time.time()
        result = await agent_invoker._retry_with_backoff(
            fails_twice,
            max_retries=3,
            initial_delay=0.1,
        )
        elapsed = time.time() - start

        assert result == {"result": "success"}
        assert call_count == 3  # Should be called three times
        # Should have delayed 0.1s + 0.2s = 0.3s total
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_retry_exhausts_all_attempts(self, agent_invoker):
        """Test that retry raises exception after all attempts are exhausted."""
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise FileNotFoundError("File never appears")

        with pytest.raises(FileNotFoundError, match="File never appears"):
            await agent_invoker._retry_with_backoff(
                always_fails,
                max_retries=3,
                initial_delay=0.1,
            )

        assert call_count == 3  # Should attempt 3 times

    @pytest.mark.asyncio
    async def test_retry_with_function_args(self, agent_invoker):
        """Test that retry correctly passes arguments to the function."""
        call_count = 0

        def function_with_args(arg1, arg2, kwarg1=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        result = await agent_invoker._retry_with_backoff(
            function_with_args,
            "value1",
            "value2",
            kwarg1="kwvalue",
            max_retries=3,
            initial_delay=0.1,
        )

        assert result == {"arg1": "value1", "arg2": "value2", "kwarg1": "kwvalue"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff_timing(self, agent_invoker):
        """Test that retry uses exponential backoff (100ms, 200ms, 400ms)."""
        call_count = 0
        call_times = []

        def fails_twice():
            nonlocal call_count
            call_times.append(asyncio.get_event_loop().time())
            call_count += 1
            if call_count <= 2:
                raise ValueError("Not ready")
            return "success"

        await agent_invoker._retry_with_backoff(
            fails_twice,
            max_retries=3,
            initial_delay=0.1,
        )

        # Verify exponential backoff delays
        # Attempt 1 -> wait 100ms -> Attempt 2 -> wait 200ms -> Attempt 3
        assert len(call_times) == 3

        # Check delays between attempts (allow 10% tolerance for timing variance)
        delay_1_2 = call_times[1] - call_times[0]
        delay_2_3 = call_times[2] - call_times[1]

        assert 0.09 <= delay_1_2 <= 0.15  # ~100ms
        assert 0.18 <= delay_2_3 <= 0.25  # ~200ms


# ==================== Class Integrity Tests ====================


class TestAgentInvokerClassIntegrity:
    """Verify AgentInvoker class has all expected methods.

    Guards against regression where module-level function insertions
    accidentally break the class scope (see TASK-REV-AB04).
    """

    def test_all_critical_methods_exist_on_class(self):
        """All critical methods must be attributes of AgentInvoker class."""
        critical_methods = [
            "_ensure_design_approved_state",
            "_invoke_task_work_implement",
            "_write_task_work_results",
            "_write_failure_results",
            "_read_json_artifact",
            "_generate_summary",
            "_validate_file_count_constraint",
            "extract_acceptance_criteria",
            "parse_completion_promises",
            "parse_criteria_verifications",
        ]
        for method_name in critical_methods:
            assert hasattr(AgentInvoker, method_name), (
                f"AgentInvoker missing method '{method_name}'. "
                f"This may indicate a class scope break caused by a "
                f"module-level function inserted in the class body."
            )

    def test_class_method_count_not_degraded(self):
        """AgentInvoker should have at least 38 methods (guard against scope breaks)."""
        import ast
        from pathlib import Path

        source = Path("guardkit/orchestrator/agent_invoker.py").read_text()
        tree = ast.parse(source)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == "AgentInvoker":
                methods = [
                    c
                    for c in ast.iter_child_nodes(node)
                    if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                assert len(methods) >= 38, (
                    f"AgentInvoker has only {len(methods)} methods, expected 38+. "
                    f"Methods may have been orphaned by a module-level function "
                    f"insertion breaking the class scope."
                )
                break
        else:
            pytest.fail("AgentInvoker class not found in source file")

    def test_detect_rate_limit_is_module_level(self):
        """detect_rate_limit should be a module-level function, not nested."""
        from guardkit.orchestrator.agent_invoker import detect_rate_limit

        assert callable(detect_rate_limit)
        # Verify it works
        is_rate_limit, _ = detect_rate_limit("rate limit exceeded")
        assert is_rate_limit is True
        is_rate_limit, _ = detect_rate_limit("normal error message")
        assert is_rate_limit is False
