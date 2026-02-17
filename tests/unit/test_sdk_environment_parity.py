"""
Comprehensive test suite for TASK-PCTD-3182: SDK Bash environment parity
for Coach test execution.

Tests cover:
    - TestSdkUtils: check_assistant_message_error utility function
    - TestCoachValidatorInit: CoachValidator __init__ with coach_test_execution param
    - TestExtractContentText: _extract_content_text static method
    - TestRunTestsViaSdk: _run_tests_via_sdk async method (all mocked)
    - TestRunIndependentTestsSdkFallback: run_independent_tests dispatch logic
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
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


# ============================================================================
# Helpers
# ============================================================================


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
# 2. TestCoachValidatorInit (2 tests)
# ============================================================================


class TestCoachValidatorInit:
    """Tests for CoachValidator.__init__() parameter handling."""

    def test_init_default_sdk_execution(self, tmp_path):
        """Default coach_test_execution is 'sdk'."""
        validator = CoachValidator(str(tmp_path))

        assert validator._coach_test_execution == "sdk"

    def test_init_subprocess_execution(self, tmp_path):
        """coach_test_execution='subprocess' is stored correctly."""
        validator = CoachValidator(str(tmp_path), coach_test_execution="subprocess")

        assert validator._coach_test_execution == "subprocess"


# ============================================================================
# 3. TestExtractContentText (4 tests)
# ============================================================================


class TestExtractContentText:
    """Tests for CoachValidator._extract_content_text() static method."""

    def test_extract_from_none(self):
        """None input returns empty string."""
        result = CoachValidator._extract_content_text(None)

        assert result == ""

    def test_extract_from_string(self):
        """Plain string input is returned unchanged."""
        result = CoachValidator._extract_content_text("test output")

        assert result == "test output"

    def test_extract_from_list_of_dicts(self):
        """List of dicts with 'text' keys are joined with newlines."""
        content = [{"text": "line1"}, {"text": "line2"}]

        result = CoachValidator._extract_content_text(content)

        assert result == "line1\nline2"

    def test_extract_from_unexpected_type(self):
        """Unexpected type (int) is converted to string representation."""
        result = CoachValidator._extract_content_text(42)

        assert result == "42"


# ============================================================================
# 4. TestRunTestsViaSdk (7 tests)
# ============================================================================


class TestRunTestsViaSdk:
    """Tests for CoachValidator._run_tests_via_sdk() async method (all mocked)."""

    async def test_sdk_bash_is_error_true(self, tmp_path):
        """ToolResultBlock with is_error=True yields tests_passed=False."""
        mock_sdk = _make_mock_sdk_module()

        assistant_msg = _make_assistant_msg(mock_sdk, error=None)
        user_msg = _make_user_msg_with_tool_block(
            mock_sdk,
            content="command not found: pytest",
            is_error=True,
        )

        async def fake_query(*args, **kwargs):
            yield assistant_msg
            yield user_msg

        mock_sdk.query = fake_query

        validator = CoachValidator(str(tmp_path))

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            result = await validator._run_tests_via_sdk("pytest tests/")

        assert result.tests_passed is False
        assert result.duration_seconds >= 0.0

    async def test_sdk_bash_is_error_false(self, tmp_path):
        """ToolResultBlock with is_error=False yields tests_passed=True."""
        mock_sdk = _make_mock_sdk_module()

        assistant_msg = _make_assistant_msg(mock_sdk, error=None)
        user_msg = _make_user_msg_with_tool_block(
            mock_sdk,
            content="5 passed in 0.42s",
            is_error=False,
        )

        async def fake_query(*args, **kwargs):
            yield assistant_msg
            yield user_msg

        mock_sdk.query = fake_query

        validator = CoachValidator(str(tmp_path))

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            result = await validator._run_tests_via_sdk("pytest tests/")

        assert result.tests_passed is True
        assert result.duration_seconds >= 0.0

    async def test_sdk_bash_is_error_none_with_passed(self, tmp_path):
        """is_error=None and output containing 'passed' yields tests_passed=True."""
        mock_sdk = _make_mock_sdk_module()

        assistant_msg = _make_assistant_msg(mock_sdk, error=None)
        user_msg = _make_user_msg_with_tool_block(
            mock_sdk,
            content="10 passed in 1.23s",
            is_error=None,
        )

        async def fake_query(*args, **kwargs):
            yield assistant_msg
            yield user_msg

        mock_sdk.query = fake_query

        validator = CoachValidator(str(tmp_path))

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            result = await validator._run_tests_via_sdk("pytest tests/")

        assert result.tests_passed is True

    async def test_sdk_bash_is_error_none_with_failed(self, tmp_path):
        """is_error=None and output containing failure indicator (no success words) yields tests_passed=False."""
        mock_sdk = _make_mock_sdk_module()

        assistant_msg = _make_assistant_msg(mock_sdk, error=None)
        user_msg = _make_user_msg_with_tool_block(
            mock_sdk,
            content="FAILED test_auth.py::test_login - AssertionError: assert False",
            is_error=None,
        )

        async def fake_query(*args, **kwargs):
            yield assistant_msg
            yield user_msg

        mock_sdk.query = fake_query

        validator = CoachValidator(str(tmp_path))

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            result = await validator._run_tests_via_sdk("pytest tests/")

        assert result.tests_passed is False

    async def test_sdk_assistant_message_error(self, tmp_path):
        """AssistantMessage with error field set yields tests_passed=False with SDK API error in summary."""
        mock_sdk = _make_mock_sdk_module()

        # This message has a real error string - check_assistant_message_error fires on it
        error_assistant_msg = _make_assistant_msg(mock_sdk, error="overloaded_error")

        async def fake_query(*args, **kwargs):
            yield error_assistant_msg

        mock_sdk.query = fake_query

        validator = CoachValidator(str(tmp_path))

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            result = await validator._run_tests_via_sdk("pytest tests/")

        assert result.tests_passed is False
        assert "SDK API error" in result.test_output_summary

    async def test_sdk_timeout(self, tmp_path):
        """asyncio.TimeoutError from SDK yields tests_passed=False mentioning timeout."""
        mock_sdk = _make_mock_sdk_module()

        async def fake_query(*args, **kwargs):
            raise asyncio.TimeoutError()
            yield  # make it an async generator

        mock_sdk.query = fake_query

        validator = CoachValidator(str(tmp_path), test_timeout=300)

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            # Patch asyncio.timeout context manager to raise TimeoutError on exit
            with patch("asyncio.timeout") as mock_timeout_cm:
                mock_ctx = MagicMock()
                mock_ctx.__aenter__ = AsyncMock(return_value=None)
                mock_ctx.__aexit__ = AsyncMock(side_effect=asyncio.TimeoutError())
                mock_timeout_cm.return_value = mock_ctx

                result = await validator._run_tests_via_sdk("pytest tests/")

        assert result.tests_passed is False
        # The summary says "timed out" (e.g. "SDK test execution timed out after 300s")
        summary_lower = result.test_output_summary.lower()
        assert "timed out" in summary_lower or "timeout" in summary_lower

    async def test_sdk_import_error(self, tmp_path):
        """ImportError from claude_agent_sdk import raises (caller catches)."""
        validator = CoachValidator(str(tmp_path))

        # Simulate claude_agent_sdk not installed
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            with pytest.raises((ImportError, TypeError)):
                await validator._run_tests_via_sdk("pytest tests/")


# ============================================================================
# 5. TestRunIndependentTestsSdkFallback (3 tests)
# ============================================================================


class TestRunIndependentTestsSdkFallback:
    """Tests for CoachValidator.run_independent_tests() SDK-first + subprocess fallback."""

    def test_sdk_first_dispatch(self, tmp_path):
        """coach_test_execution='sdk' calls _run_tests_via_sdk via asyncio bridge."""
        validator = CoachValidator(
            str(tmp_path),
            test_command="pytest tests/",
            coach_test_execution="sdk",
        )

        sdk_result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/",
            test_output_summary="5 passed",
            duration_seconds=1.0,
        )

        with patch.object(validator, "_run_tests_via_sdk", return_value=sdk_result):
            with patch("asyncio.get_event_loop") as mock_get_loop:
                mock_loop = MagicMock()
                mock_loop.run_until_complete.return_value = sdk_result
                mock_get_loop.return_value = mock_loop

                result = validator.run_independent_tests()

        assert result.tests_passed is True
        mock_loop.run_until_complete.assert_called_once()

    def test_subprocess_when_configured(self, tmp_path):
        """coach_test_execution='subprocess' bypasses SDK, calls subprocess.run."""
        validator = CoachValidator(
            str(tmp_path),
            test_command="pytest tests/",
            coach_test_execution="subprocess",
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "5 passed"
        mock_proc.stderr = ""

        with patch("subprocess.run", return_value=mock_proc) as mock_subprocess:
            result = validator.run_independent_tests()

        mock_subprocess.assert_called_once()
        assert result.tests_passed is True

    def test_fallback_to_subprocess_on_sdk_error(self, tmp_path):
        """coach_test_execution='sdk' but SDK raises falls back to subprocess.run."""
        validator = CoachValidator(
            str(tmp_path),
            test_command="pytest tests/",
            coach_test_execution="sdk",
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "3 passed"
        mock_proc.stderr = ""

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.run_until_complete.side_effect = RuntimeError("SDK unavailable")
            mock_get_loop.return_value = mock_loop

            with patch("subprocess.run", return_value=mock_proc) as mock_subprocess:
                result = validator.run_independent_tests()

        mock_subprocess.assert_called_once()
        assert result.tests_passed is True


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
        """check_assistant_message_error is imported and called in _invoke_with_role SDK loop."""
        import inspect

        from guardkit.orchestrator import agent_invoker as ai_module

        source = inspect.getsource(ai_module)

        # Verify the import exists in the module source
        assert (
            "from guardkit.orchestrator.sdk_utils import check_assistant_message_error"
            in source
        )

        # Verify it is called at least once in the module
        assert "check_assistant_message_error(message)" in source

    def test_agent_invoker_task_work_implement_checks_error(self):
        """check_assistant_message_error is called in _invoke_task_work_implement SDK loop."""
        import inspect

        from guardkit.orchestrator import agent_invoker as ai_module

        source = inspect.getsource(ai_module)

        # Count the number of call-sites - there should be at least 2 (one per loop)
        call_count = source.count("check_assistant_message_error(message)")
        assert call_count >= 2, (
            f"Expected at least 2 call-sites for check_assistant_message_error in "
            f"agent_invoker.py but found {call_count}"
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
        assert "check_assistant_message_error(message)" in source
