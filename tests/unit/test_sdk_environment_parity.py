"""
Comprehensive test suite for TASK-PCTD-3182: SDK Bash environment parity
for Coach test execution.

Tests cover:
    - TestSdkUtils: check_assistant_message_error utility function
    (The Coach's own SDK test path and its tests were removed on 1 November
    2026: the declared test command runs as declared, through the shell.)
    - TestLoadCoachConfig: AutoBuildOrchestrator._load_coach_config
    - TestBug472DefenseInExistingPaths: Verify check_assistant_message_error usage

Coverage Target: >=80%
Test Count: 25 tests
"""

import asyncio
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.sdk_utils import check_assistant_message_error
from tests.conftest import M0_FLEET_SEAT


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture(autouse=True)
def _pin_sdk_harness(monkeypatch):
    """TASK-HMIG-011: SDK-environment-parity tests run on the SDK substrate.
    Pin GUARDKIT_HARNESS=sdk so the post-cutover ``langgraph`` default (not
    importable in CI's tests.yml) is not resolved."""
    monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")


def _make_mock_sdk_module() -> MagicMock:
    """Build a minimal mock of the claude_agent_sdk module."""
    mock_module = MagicMock(spec=ModuleType)

    # Named SDK types needed by _run_tests_via_sdk.
    # These must be real Python types so isinstance() works when the
    # production code does: from claude_agent_sdk import AssistantMessage, ...
    mock_module.AssistantMessage = type("AssistantMessage", (), {})
    mock_module.UserMessage = type("UserMessage", (), {})
    mock_module.ToolResultBlock = type("ToolResultBlock", (), {})
    mock_module.TextBlock = type("TextBlock", (), {})
    mock_module.ClaudeAgentOptions = MagicMock(return_value=MagicMock())
    mock_module.CLINotFoundError = Exception
    mock_module.ProcessError = Exception
    mock_module.CLIJSONDecodeError = Exception

    return mock_module


def _make_assistant_msg(mock_sdk: MagicMock, error=None) -> MagicMock:
    """Create a mock AssistantMessage.

    Sets __class__ so isinstance(msg, AssistantMessage) passes, and
    explicitly sets error=None to prevent auto-generated truthy MagicMock
    attribute from triggering check_assistant_message_error.
    """
    msg = MagicMock()
    msg.__class__ = mock_sdk.AssistantMessage
    msg.error = error
    msg.content = []
    return msg


def _make_user_msg_with_tool_block(
    mock_sdk: MagicMock,
    content: str,
    is_error,
) -> MagicMock:
    """Create a mock UserMessage carrying one ToolResultBlock.

    Sets __class__ on both the user message and the tool block so that
    isinstance() checks inside _run_tests_via_sdk pass correctly.
    Also explicitly sets error=None on the user message so
    check_assistant_message_error does not fire on this message.
    """
    tool_block = MagicMock()
    # Must set __class__ so isinstance(block, ToolResultBlock) passes
    tool_block.__class__ = mock_sdk.ToolResultBlock
    tool_block.content = content
    tool_block.is_error = is_error

    user_msg = MagicMock()
    user_msg.__class__ = mock_sdk.UserMessage
    user_msg.content = [tool_block]
    # Explicitly set error=None so check_assistant_message_error does not fire
    user_msg.error = None
    return user_msg


# ============================================================================
# 1. TestSdkUtils (3 tests)
# ============================================================================


@pytest.fixture(autouse=True)
def _routine_fleet_route(m0_routine_fleet_route):
    """Declare the routine local-fleet route (leg-invocation stage-2 design §3).

    The M0 effective-seat fence at the top of ``select_harness`` refuses any
    harness whose seat cannot be shown to be local — including a seat that was
    never named, which is what these tests used to build (``model=None`` falls
    to DeepAgents' ``ChatAnthropic("claude-sonnet-4-6")`` or the bundled SDK
    CLI default). Their subject is SDK/harness plumbing, not seat choice, so
    they state the estate's routine condition — a named local seat behind a
    local endpoint, see ``tests/conftest.py`` — rather than switch the fence
    off with ``GUARDKIT_ALLOW_FRONTIER``, which would hide the next regression.
    """


class TestSdkUtils:
    """Tests for guardkit/orchestrator/sdk_utils.py."""

    def test_check_assistant_message_error_returns_none_when_no_error(self):
        """Message with error=None returns None (no error present)."""
        message = MagicMock()
        message.error = None

        result = check_assistant_message_error(message)

        assert result is None

    def test_check_assistant_message_error_returns_error_string(self):
        """Message with error='API rate limited' returns the error string."""
        message = MagicMock()
        message.error = "API rate limited"

        result = check_assistant_message_error(message)

        assert result == "API rate limited"

    def test_check_assistant_message_error_no_error_attr(self):
        """Plain object without error attribute returns None."""

        class PlainObject:
            pass

        obj = PlainObject()

        result = check_assistant_message_error(obj)

        assert result is None


# ============================================================================
# 6. TestLoadCoachConfig (3 tests)
# ============================================================================


class TestLoadCoachConfig:
    """Tests for AutoBuildOrchestrator._load_coach_config()."""

    def _make_orchestrator(self, repo_root: Path):
        """Create a bare AutoBuildOrchestrator instance (bypasses heavy __init__)."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orch.repo_root = repo_root
        return orch

    def test_no_config_file(self, tmp_path):
        """Missing .guardkit/config.yaml returns empty dict."""
        orch = self._make_orchestrator(tmp_path)

        result = orch._load_coach_config()

        assert result == {}

    def test_valid_config(self, tmp_path):
        """Config with autobuild.coach.test_execution returns the coach section."""
        config_dir = tmp_path / ".guardkit"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text(
            "autobuild:\n  coach:\n    test_execution: subprocess\n"
        )

        orch = self._make_orchestrator(tmp_path)

        result = orch._load_coach_config()

        assert result == {"test_execution": "subprocess"}

    def test_invalid_yaml(self, tmp_path):
        """Non-dict YAML at top level returns empty dict."""
        config_dir = tmp_path / ".guardkit"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"
        # YAML that parses to a list, not a dict
        config_file.write_text("- item1\n- item2\n")

        orch = self._make_orchestrator(tmp_path)

        result = orch._load_coach_config()

        assert result == {}


# ============================================================================
# 7. TestBug472DefenseInExistingPaths (3 tests)
# ============================================================================


class TestBug472DefenseInExistingPaths:
    """Verify check_assistant_message_error is called in SDK stream loops (bug #472 defense)."""

    def test_agent_invoker_invoke_with_role_checks_error(self):
        """check_assistant_message_error is imported and called on the SDK
        AssistantMessage in _invoke_with_role.

        TASK-HMIG-006 / TASK-HMIG-006.1: after the harness migration the
        SDK ``AssistantMessage`` is reached via the typed ``AssistantMessageEvent.raw``
        slot (raw is populated by the SDK harness; LangGraph harness leaves
        it ``None`` and the API-error check is a no-op there). The bug-#472
        defence is preserved — the literal call form moved from
        ``check_assistant_message_error(message)`` to
        ``check_assistant_message_error(event.raw)``.
        """
        import inspect

        from guardkit.orchestrator import agent_invoker as ai_module

        source = inspect.getsource(ai_module)

        # Verify the import exists in the module source
        assert (
            "from guardkit.orchestrator.sdk_utils import check_assistant_message_error"
            in source
        )

        # Verify the API-error check is called at least once on the raw
        # SDK AssistantMessage (event.raw shape post-harness-migration).
        assert "check_assistant_message_error(event.raw)" in source, (
            "bug-#472 defence must survive harness migration via "
            "check_assistant_message_error(event.raw)"
        )

    def test_agent_invoker_task_work_implement_checks_error(self):
        """check_assistant_message_error is called in both _invoke_with_role
        and _invoke_task_work_implement SDK loops.

        TASK-HMIG-006 / TASK-HMIG-006.1: bug #472 defence is upheld at both
        call sites via ``check_assistant_message_error(event.raw)``.
        """
        import inspect

        from guardkit.orchestrator import agent_invoker as ai_module

        source = inspect.getsource(ai_module)

        # Count the number of call-sites - there should be at least 2
        # (one per loop, both passing event.raw post-harness-migration).
        call_count = source.count("check_assistant_message_error(event.raw)")
        assert call_count >= 2, (
            f"Expected at least 2 call-sites for "
            f"check_assistant_message_error(event.raw) in agent_invoker.py "
            f"but found {call_count}"
        )

    def test_task_work_interface_execute_via_sdk_checks_error(self):
        """check_assistant_message_error is called in task_work_interface._execute_via_sdk."""
        import inspect

        from guardkit.orchestrator.quality_gates import task_work_interface as twi_module

        source = inspect.getsource(twi_module)

        assert (
            "from guardkit.orchestrator.sdk_utils import check_assistant_message_error"
            in source
        )
        # TASK-HMIG-006.4: the design phase now routes through the
        # HarnessAdapter, so the bug-#472 defence checks the raw SDK shape
        # carried on the HarnessEvent (event.raw) rather than a bare
        # `message`. The defence is still present and unconditional.
        assert "check_assistant_message_error(event.raw)" in source
