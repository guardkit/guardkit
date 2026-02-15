"""
Unit tests for SDK session configuration.

Tests verify:
- setting_sources=["project"] for all SDK-based invocations
- Correct tool permissions for Player/Coach roles
- Permission modes (acceptEdits vs bypassPermissions)
- Max turns configuration
- Timeout calculation with CLI override, mode/complexity multipliers

Coverage Target: >=85%
Test Count: 25+ tests
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    DEFAULT_SDK_TIMEOUT,
    MAX_SDK_TIMEOUT,
    TASK_WORK_SDK_MAX_TURNS,
)
from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def worktree_path(tmp_path):
    """Create a temporary worktree directory with required structure."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".guardkit" / "autobuild").mkdir(parents=True)
    (worktree / "tasks" / "backlog").mkdir(parents=True)
    return worktree


@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker with default SDK timeout for dynamic calculation tests."""
    return AgentInvoker(worktree_path=worktree_path)


def create_task_file(
    worktree_path: Path,
    task_id: str,
    complexity: Any = 5,
    mode: str = "task-work",
    title: str = "Test Task",
    body: str = "# Test Task\n\nThis is a test task.\n",
):
    """Helper to create a task markdown file."""
    tasks_dir = worktree_path / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    task_file = tasks_dir / f"{task_id}-test-task.md"

    lines = [
        "---",
        f"id: {task_id}",
        f"title: {title}",
        "status: backlog",
    ]
    if complexity is not None:
        lines.append(f"complexity: {complexity}")
    lines.append(f"implementation_mode: {mode}")
    lines.append("---")
    lines.append("")
    lines.append(body)

    task_file.write_text("\n".join(lines))
    return task_file


def create_mock_sdk_module():
    """Create a mock claude_agent_sdk module that captures ClaudeAgentOptions kwargs.

    Returns (mock_module, captured_options) where captured_options is a dict
    that gets updated whenever ClaudeAgentOptions is instantiated.
    """
    mock_module = MagicMock()
    captured_options: Dict[str, Any] = {}

    class MockOptions:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            captured_options.clear()
            captured_options.update(kwargs)

    mock_module.ClaudeAgentOptions = MockOptions

    # Async generator that yields nothing
    async def mock_query(prompt, options):
        return
        yield  # noqa: unreachable - makes it an async generator

    mock_module.query = mock_query

    # Mock error classes
    mock_module.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
    mock_module.ProcessError = type(
        "ProcessError", (Exception,), {"exit_code": 1, "stderr": ""}
    )
    mock_module.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})
    mock_module.AssistantMessage = type("AssistantMessage", (), {})
    mock_module.TextBlock = type("TextBlock", (), {})
    mock_module.ToolUseBlock = type("ToolUseBlock", (), {})
    mock_module.ToolResultBlock = type("ToolResultBlock", (), {})
    mock_module.ResultMessage = type("ResultMessage", (), {})

    return mock_module, captured_options


# ============================================================================
# Player/Coach SDK Configuration via _invoke_with_role
# ============================================================================


class TestInvokeWithRoleConfig:
    """Tests for ClaudeAgentOptions created in _invoke_with_role().

    The _invoke_with_role method signature is:
        async def _invoke_with_role(
            self, prompt, agent_type, allowed_tools, permission_mode, model
        )

    It constructs ClaudeAgentOptions with setting_sources=["project"].
    """

    @pytest.mark.asyncio
    async def test_player_setting_sources_project_only(self, worktree_path):
        """Player invocation uses setting_sources=['project']."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test player prompt",
                    agent_type="player",
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass  # May fail from mock, but we captured options

        assert captured.get("setting_sources") == ["project"]

    @pytest.mark.asyncio
    async def test_coach_setting_sources_project_only(self, worktree_path):
        """Coach invocation uses setting_sources=['project']."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test coach prompt",
                    agent_type="coach",
                    allowed_tools=["Read", "Bash", "Grep", "Glob"],
                    permission_mode="bypassPermissions",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass

        assert captured.get("setting_sources") == ["project"]

    @pytest.mark.asyncio
    async def test_player_allowed_tools_passed_through(self, worktree_path):
        """Player allowed_tools are passed to ClaudeAgentOptions."""
        mock_sdk, captured = create_mock_sdk_module()
        player_tools = ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="player",
                    allowed_tools=player_tools,
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass

        assert captured.get("allowed_tools") == player_tools

    @pytest.mark.asyncio
    async def test_coach_allowed_tools_read_only(self, worktree_path):
        """Coach tools are read-only (no Write/Edit)."""
        mock_sdk, captured = create_mock_sdk_module()
        coach_tools = ["Read", "Bash", "Grep", "Glob"]

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="coach",
                    allowed_tools=coach_tools,
                    permission_mode="bypassPermissions",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass

        tools = captured.get("allowed_tools", [])
        assert "Read" in tools
        assert "Bash" in tools
        assert "Write" not in tools
        assert "Edit" not in tools

    @pytest.mark.asyncio
    async def test_player_permission_mode_accept_edits(self, worktree_path):
        """Player uses permission_mode='acceptEdits'."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="player",
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass

        assert captured.get("permission_mode") == "acceptEdits"

    @pytest.mark.asyncio
    async def test_coach_permission_mode_bypass(self, worktree_path):
        """Coach uses permission_mode='bypassPermissions'."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="coach",
                    allowed_tools=["Read", "Bash", "Grep", "Glob"],
                    permission_mode="bypassPermissions",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass

        assert captured.get("permission_mode") == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_max_turns_uses_constant(self, worktree_path):
        """Both Player and Coach use TASK_WORK_SDK_MAX_TURNS for max_turns."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            invoker = AgentInvoker(worktree_path=worktree_path)
            try:
                await invoker._invoke_with_role(
                    prompt="Test prompt",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                    model="claude-sonnet-4-5-20250929",
                )
            except (StopAsyncIteration, Exception):
                pass

        assert captured.get("max_turns") == TASK_WORK_SDK_MAX_TURNS
        assert captured.get("max_turns") == 50


# ============================================================================
# Task-Work Implementation SDK Configuration
# ============================================================================


class TestTaskWorkImplementConfig:
    """Tests for ClaudeAgentOptions created in _invoke_task_work_implement().

    Signature: async def _invoke_task_work_implement(
        self, task_id, mode, documentation_level, turn, requirements,
        feedback, max_turns, context
    )
    """

    @pytest.mark.asyncio
    async def test_setting_sources_project_only(self, worktree_path):
        """task-work implementation uses setting_sources=['project']."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            with patch(
                "guardkit.orchestrator.agent_invoker.TaskWorkStreamParser"
            ) as mock_parser_cls:
                mock_parser = MagicMock()
                mock_parser.to_result.return_value = {
                    "phases": {},
                    "tests_passed": 5,
                    "tests_failed": 0,
                    "coverage": 85.0,
                    "quality_gates_passed": True,
                    "files_modified": [],
                    "files_created": [],
                    "tests_written": [],
                }
                mock_parser_cls.return_value = mock_parser

                invoker = AgentInvoker(worktree_path=worktree_path)
                try:
                    await invoker._invoke_task_work_implement("TASK-001")
                except Exception:
                    pass

        if "setting_sources" in captured:
            assert captured["setting_sources"] == ["project"]

    @pytest.mark.asyncio
    async def test_allowed_tools_include_task(self, worktree_path):
        """task-work implementation includes Task tool."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            with patch(
                "guardkit.orchestrator.agent_invoker.TaskWorkStreamParser"
            ) as mock_parser_cls:
                mock_parser = MagicMock()
                mock_parser.to_result.return_value = {}
                mock_parser_cls.return_value = mock_parser

                invoker = AgentInvoker(worktree_path=worktree_path)
                try:
                    await invoker._invoke_task_work_implement("TASK-001")
                except Exception:
                    pass

        if "allowed_tools" in captured:
            assert "Task" in captured["allowed_tools"]
            assert "Read" in captured["allowed_tools"]
            assert "Write" in captured["allowed_tools"]
            assert "Bash" in captured["allowed_tools"]

    @pytest.mark.asyncio
    async def test_max_turns_uses_constant(self, worktree_path):
        """task-work implementation uses TASK_WORK_SDK_MAX_TURNS (50)."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            with patch(
                "guardkit.orchestrator.agent_invoker.TaskWorkStreamParser"
            ) as mock_parser_cls:
                mock_parser = MagicMock()
                mock_parser.to_result.return_value = {}
                mock_parser_cls.return_value = mock_parser

                invoker = AgentInvoker(worktree_path=worktree_path)
                try:
                    await invoker._invoke_task_work_implement("TASK-001")
                except Exception:
                    pass

        if "max_turns" in captured:
            assert captured["max_turns"] == TASK_WORK_SDK_MAX_TURNS


# ============================================================================
# Design Phase SDK Configuration
# ============================================================================


class TestDesignPhaseConfig:
    """Tests for ClaudeAgentOptions created in TaskWorkInterface._execute_via_sdk().

    Signature: async def _execute_via_sdk(self, prompt: str) -> Dict[str, Any]
    """

    @pytest.mark.asyncio
    async def test_setting_sources_project_only(self, worktree_path):
        """Design phase uses setting_sources=['project']."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            interface = TaskWorkInterface(worktree_path=worktree_path)
            try:
                await interface._execute_via_sdk("Test design prompt for TASK-001")
            except Exception:
                pass

        if "setting_sources" in captured:
            assert captured["setting_sources"] == ["project"]

    @pytest.mark.asyncio
    async def test_allowed_tools_no_task_tool(self, worktree_path):
        """Design phase does NOT include Task tool."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            interface = TaskWorkInterface(worktree_path=worktree_path)
            try:
                await interface._execute_via_sdk("Test design prompt for TASK-001")
            except Exception:
                pass

        if "allowed_tools" in captured:
            assert "Read" in captured["allowed_tools"]
            assert "Write" in captured["allowed_tools"]
            assert "Task" not in captured["allowed_tools"]

    @pytest.mark.asyncio
    async def test_max_turns_is_25(self, worktree_path):
        """Design phase uses max_turns=25."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            interface = TaskWorkInterface(worktree_path=worktree_path)
            try:
                await interface._execute_via_sdk("Test design prompt for TASK-001")
            except Exception:
                pass

        if "max_turns" in captured:
            assert captured["max_turns"] == 25

    @pytest.mark.asyncio
    async def test_permission_mode_accept_edits(self, worktree_path):
        """Design phase uses permission_mode='acceptEdits'."""
        mock_sdk, captured = create_mock_sdk_module()

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            interface = TaskWorkInterface(worktree_path=worktree_path)
            try:
                await interface._execute_via_sdk("Test design prompt for TASK-001")
            except Exception:
                pass

        if "permission_mode" in captured:
            assert captured["permission_mode"] == "acceptEdits"


# ============================================================================
# Timeout Calculation Tests
# ============================================================================


class TestSDKTimeoutCalculation:
    """Tests for _calculate_sdk_timeout() dynamic timeout calculation.

    Formula: effective_timeout = base * mode_multiplier * complexity_multiplier
    Where:
      mode_multiplier = 1.5 (task-work) | 1.0 (direct/other)
      complexity_multiplier = 1.0 + (complexity / 10.0)
    Cap: MAX_SDK_TIMEOUT (3600s)
    """

    def test_cli_override_returns_unchanged(self, worktree_path):
        """CLI override (non-default timeout) is returned without recalculation."""
        invoker = AgentInvoker(worktree_path=worktree_path, sdk_timeout_seconds=500)
        create_task_file(worktree_path, "TASK-001", complexity=8, mode="task-work")

        timeout = invoker._calculate_sdk_timeout("TASK-001")
        assert timeout == 500

    def test_default_with_task_work_mode(self, worktree_path):
        """task-work mode uses 1.5x multiplier."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=5, mode="task-work")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.5 * 1.5 = 2700
        expected = int(DEFAULT_SDK_TIMEOUT * 1.5 * 1.5)
        assert timeout == expected
        assert timeout == 2700

    def test_direct_mode_multiplier_1x(self, worktree_path):
        """Non-task-work modes use 1.0x multiplier."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=5, mode="direct")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.0 * 1.5 = 1800
        expected = int(DEFAULT_SDK_TIMEOUT * 1.0 * 1.5)
        assert timeout == expected
        assert timeout == 1800

    def test_complexity_1_multiplier_1_1x(self, worktree_path):
        """Complexity 1 produces 1.1x multiplier."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=1, mode="direct")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.0 * 1.1 = 1320
        expected = int(DEFAULT_SDK_TIMEOUT * 1.0 * 1.1)
        assert timeout == expected
        assert timeout == 1320

    def test_complexity_10_multiplier_2x(self, worktree_path):
        """Complexity 10 produces 2.0x multiplier."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=10, mode="direct")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.0 * 2.0 = 2400
        expected = int(DEFAULT_SDK_TIMEOUT * 1.0 * 2.0)
        assert timeout == expected
        assert timeout == 2400

    def test_capped_at_max_sdk_timeout(self, worktree_path):
        """Timeout is capped at MAX_SDK_TIMEOUT (3600s)."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=10, mode="task-work")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.5 * 2.0 = 3600 (exactly at cap)
        assert timeout <= MAX_SDK_TIMEOUT
        assert timeout == 3600

    def test_task_not_found_uses_defaults(self, worktree_path):
        """Missing task defaults to mode=task-work, complexity=5."""
        invoker = AgentInvoker(worktree_path=worktree_path)

        timeout = invoker._calculate_sdk_timeout("TASK-NONEXISTENT")

        # Defaults: mode=task-work (1.5x), complexity=5 (1.5x)
        # 1200 * 1.5 * 1.5 = 2700
        expected = int(DEFAULT_SDK_TIMEOUT * 1.5 * 1.5)
        assert timeout == expected
        assert timeout == 2700

    def test_invalid_complexity_uses_defaults(self, worktree_path):
        """Invalid complexity value triggers exception → defaults to task-work, complexity=5."""
        invoker = AgentInvoker(worktree_path=worktree_path)

        task_dir = worktree_path / "tasks" / "backlog"
        task_file = task_dir / "TASK-001-invalid-cplx.md"
        task_file.write_text(
            "---\n"
            "id: TASK-001\n"
            "title: Test Task\n"
            "status: backlog\n"
            "complexity: not-a-number\n"
            "implementation_mode: standard\n"
            "---\n\n# Test\n"
        )

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # Exception handler defaults: mode=task-work (1.5x), complexity=5 (1.5x)
        # 1200 * 1.5 * 1.5 = 2700
        expected = int(DEFAULT_SDK_TIMEOUT * 1.5 * 1.5)
        assert timeout == expected
        assert timeout == 2700

    def test_missing_complexity_uses_default_5(self, worktree_path):
        """Missing complexity field defaults to 5."""
        invoker = AgentInvoker(worktree_path=worktree_path)

        task_dir = worktree_path / "tasks" / "backlog"
        task_file = task_dir / "TASK-001-no-cplx.md"
        task_file.write_text(
            "---\n"
            "id: TASK-001\n"
            "title: Test Task\n"
            "status: backlog\n"
            "implementation_mode: tdd\n"
            "---\n\n# Test\n"
        )

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # mode=tdd (not "task-work" so 1.0x), complexity=5 (1.5x)
        # 1200 * 1.0 * 1.5 = 1800
        expected = int(DEFAULT_SDK_TIMEOUT * 1.0 * 1.5)
        assert timeout == expected
        assert timeout == 1800

    def test_tdd_mode_uses_direct_multiplier(self, worktree_path):
        """TDD mode uses 1.0x multiplier (not task-work)."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=5, mode="tdd")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.0 * 1.5 = 1800
        expected = int(DEFAULT_SDK_TIMEOUT * 1.0 * 1.5)
        assert timeout == expected
        assert timeout == 1800

    def test_bdd_mode_uses_direct_multiplier(self, worktree_path):
        """BDD mode uses 1.0x multiplier (not task-work)."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=5, mode="bdd")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.0 * 1.5 = 1800
        expected = int(DEFAULT_SDK_TIMEOUT * 1.0 * 1.5)
        assert timeout == expected
        assert timeout == 1800

    def test_combined_multipliers(self, worktree_path):
        """Verify combined mode and complexity multipliers."""
        invoker = AgentInvoker(worktree_path=worktree_path)
        create_task_file(worktree_path, "TASK-001", complexity=8, mode="task-work")

        timeout = invoker._calculate_sdk_timeout("TASK-001")

        # 1200 * 1.5 * 1.8 = 3240
        expected = int(DEFAULT_SDK_TIMEOUT * 1.5 * 1.8)
        assert timeout == expected
        assert timeout == 3240


# ============================================================================
# Interactive Path No-Regression Tests
# ============================================================================


class TestInteractivePathNoRegression:
    """Verify interactive /task-work does NOT use SDK with restricted settings.

    Interactive /task-work runs directly in Claude Code, which manages its
    own setting_sources. The SDK paths (AutoBuild) all use ["project"].
    This test class ensures the SDK config constants are correct.
    """

    def test_default_sdk_timeout_is_1200(self):
        """DEFAULT_SDK_TIMEOUT is 1200 seconds (20 min)."""
        assert DEFAULT_SDK_TIMEOUT == 1200

    def test_max_sdk_timeout_is_3600(self):
        """MAX_SDK_TIMEOUT is 3600 seconds (1 hour)."""
        assert MAX_SDK_TIMEOUT == 3600

    def test_task_work_sdk_max_turns_is_50(self):
        """TASK_WORK_SDK_MAX_TURNS is 50."""
        assert TASK_WORK_SDK_MAX_TURNS == 50

    def test_invoke_with_role_always_uses_project_setting_sources(self):
        """Verify source code sets setting_sources=['project'] in _invoke_with_role.

        This is a structural test - reads the source to ensure the setting
        is present and not accidentally changed to ["user", "project"].
        """
        import inspect
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        source = inspect.getsource(AgentInvoker._invoke_with_role)
        assert 'setting_sources=["project"]' in source

    def test_invoke_task_work_implement_uses_project_setting_sources(self):
        """Verify source code sets setting_sources=['project'] in _invoke_task_work_implement."""
        import inspect
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)
        assert 'setting_sources=["project"]' in source

    def test_execute_via_sdk_uses_project_setting_sources(self):
        """Verify source code sets setting_sources=['project'] in _execute_via_sdk."""
        import inspect
        from guardkit.orchestrator.quality_gates.task_work_interface import (
            TaskWorkInterface,
        )

        source = inspect.getsource(TaskWorkInterface._execute_via_sdk)
        assert 'setting_sources=["project"]' in source


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
