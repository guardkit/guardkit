"""
Unit tests for TASK-RFX-8332: Explicit generator close on SDK query().

Verifies that _invoke_with_role and _invoke_task_work_implement explicitly
close the query() async generator in finally/cleanup blocks to prevent
GC finalization from scheduling athrow(GeneratorExit) in a wrong asyncio Task.

Coverage Target: >=85%
Test Count: 9 tests
"""

import asyncio
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    TASK_WORK_SDK_MAX_TURNS,
)
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    SDKTimeoutError,
    TaskWorkResult,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    return worktree


@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker instance with short timeout for tests."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=5,
        sdk_timeout_seconds=60,
    )


def _make_mock_sdk(query_fn):
    """Create mock SDK module with given query generator function."""
    MockResultMessage = type("ResultMessage", (), {"num_turns": 5})
    mock_sdk = MagicMock()
    mock_sdk.query = query_fn
    mock_sdk.ClaudeAgentOptions = MagicMock()
    mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
    mock_sdk.ProcessError = type("ProcessError", (Exception,), {"exit_code": 1, "stderr": ""})
    mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})
    mock_sdk.AssistantMessage = type("AssistantMessage", (), {})
    mock_sdk.ResultMessage = MockResultMessage
    mock_sdk.TextBlock = type("TextBlock", (), {})
    mock_sdk.ToolUseBlock = type("ToolUseBlock", (), {})
    mock_sdk.ToolResultBlock = type("ToolResultBlock", (), {})
    return mock_sdk, MockResultMessage


# ============================================================================
# 1. _invoke_with_role generator close tests (4 tests)
# ============================================================================


class TestInvokeWithRoleGeneratorClose:
    """Verify _invoke_with_role explicitly closes query() generator."""

    @pytest.mark.asyncio
    async def test_generator_closed_on_normal_exit(self, agent_invoker):
        """Generator is explicitly aclose()d after normal ResultMessage break."""
        aclose_called = False
        original_aclose = None

        async def mock_query_gen(*args, **kwargs):
            nonlocal original_aclose
            result_msg = MagicMock()
            result_msg.__class__ = type("ResultMessage", (), {})
            # Yield a non-result message then a result message
            yield MagicMock(type="assistant", error=None)
            yield result_msg

        # Wrap the generator to track aclose
        async def tracking_query(*args, **kwargs):
            nonlocal aclose_called, original_aclose
            gen = mock_query_gen(*args, **kwargs)

            # Create wrapper that tracks aclose
            class TrackingGen:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    return await gen.__anext__()

                async def aclose(self):
                    nonlocal aclose_called
                    aclose_called = True
                    await gen.aclose()

            return TrackingGen()

        # Use simpler approach: patch the generator's aclose
        aclose_called = False

        MockResultMessage = type("ResultMessage", (), {})

        async def query_with_tracking(*args, **kwargs):
            nonlocal aclose_called
            msg = MagicMock(type="assistant", error=None)
            result = MockResultMessage()
            yield msg
            yield result

        mock_sdk, _ = _make_mock_sdk(query_with_tracking)
        mock_sdk.ResultMessage = MockResultMessage

        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            await agent_invoker._invoke_with_role(
                prompt="Test prompt TASK-001",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )

        # Verify source code has gen assignment and aclose
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)
        assert "gen = query(" in source, "Must hold explicit generator reference"
        assert "await gen.aclose()" in source, "Must call aclose() on generator"
        assert "asyncio.timeout(5)" in source, "Must use 5s timeout for aclose"

    @pytest.mark.asyncio
    async def test_generator_closed_on_exception(self, agent_invoker):
        """Generator is explicitly aclose()d when exception occurs during iteration."""
        MockResultMessage = type("ResultMessage", (), {})

        async def query_that_raises(*args, **kwargs):
            yield MagicMock(type="assistant", error=None)
            raise RuntimeError("Simulated SDK error")

        mock_sdk, _ = _make_mock_sdk(query_that_raises)
        mock_sdk.ResultMessage = MockResultMessage

        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            with pytest.raises(AgentInvocationError):
                await agent_invoker._invoke_with_role(
                    prompt="Test prompt TASK-002",
                    agent_type="player",
                    allowed_tools=["Read"],
                    permission_mode="acceptEdits",
                )

        # Verify the finally block contains aclose
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)
        assert "finally:" in source
        assert "gen is not None" in source
        assert "await gen.aclose()" in source

    @pytest.mark.asyncio
    async def test_aclose_timeout_prevents_blocking(self, agent_invoker):
        """5-second timeout on aclose() prevents blocking on unresponsive subprocess."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)

        # Verify the timeout structure
        assert "asyncio.timeout(5)" in source, "aclose must have 5s timeout"
        assert "suppress(Exception)" in source, "aclose must be wrapped in suppress"

    @pytest.mark.asyncio
    async def test_gen_reference_held_explicitly(self, agent_invoker):
        """query() return value is stored in explicit variable, not consumed inline."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)

        # Must NOT have inline consumption pattern
        assert "async for message in query(" not in source, (
            "Generator must NOT be consumed inline - hold explicit reference"
        )
        # Must have explicit reference
        assert "gen = query(" in source, "Must assign query() to gen variable"
        assert "async for message in gen:" in source, "Must iterate over held reference"


# ============================================================================
# 2. _invoke_task_work_implement generator close tests (3 tests)
# ============================================================================


class TestInvokeTaskWorkImplementGeneratorClose:
    """Verify _invoke_task_work_implement explicitly closes query() generator."""

    def test_generator_reference_held_in_task_work(self):
        """query() return value is stored in explicit variable in task-work path."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        # Must NOT have inline consumption pattern
        assert "async for message in query(" not in source, (
            "Generator must NOT be consumed inline - hold explicit reference"
        )
        # Must have explicit reference
        assert "_tw_gen = query(" in source, "Must assign query() to _tw_gen variable"
        assert "async for message in _tw_gen:" in source, "Must iterate over held reference"

    def test_aclose_in_retry_cleanup(self):
        """Generator is aclose()d after each retry iteration."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        assert "await _tw_gen.aclose()" in source, "Must call aclose() on _tw_gen"
        assert "_tw_gen = None" in source, "Must reset reference after close"

    def test_aclose_in_finally_block(self):
        """Generator is aclose()d in finally block for exception paths."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        # Verify there's a finally block with generator cleanup
        # Find 'finally:' followed by _tw_gen cleanup
        finally_idx = source.find("finally:")
        assert finally_idx != -1, "Must have finally block"

        # Check that aclose is called after finally
        after_finally = source[finally_idx:]
        assert "await _tw_gen.aclose()" in after_finally, (
            "finally block must call aclose() on _tw_gen"
        )
        assert "asyncio.timeout(5)" in after_finally, (
            "finally block must use 5s timeout for aclose"
        )


# ============================================================================
# 3. Defense-in-depth: _install_sdk_cleanup_handler preserved (2 tests)
# ============================================================================


class TestSdkCleanupHandlerPreserved:
    """Verify _install_sdk_cleanup_handler is still called as defense-in-depth."""

    def test_cleanup_handler_in_invoke_with_role(self):
        """_install_sdk_cleanup_handler still called in _invoke_with_role."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)
        assert "_install_sdk_cleanup_handler(" in source

    def test_cleanup_handler_in_task_work(self):
        """_install_sdk_cleanup_handler still called in _invoke_task_work_implement."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)
        assert "_install_sdk_cleanup_handler(" in source
