"""Unit tests for AgentInvoker class."""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    PlayerReportNotFoundError,
    PlayerReportInvalidError,
    CoachDecisionNotFoundError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
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
            assert call_kwargs["permission_mode"] == "default"
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
    async def test_sdk_invocation_not_implemented(self, agent_invoker):
        """SDK invocation raises NotImplementedError (SDK not yet integrated)."""
        with pytest.raises(NotImplementedError) as exc_info:
            await agent_invoker._invoke_with_role(
                prompt="Test prompt",
                agent_type="player",
                allowed_tools=["Read", "Write"],
                permission_mode="acceptEdits",
                model="claude-sonnet-4-5-20250929",
            )

        assert "SDK integration pending" in str(exc_info.value)

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
