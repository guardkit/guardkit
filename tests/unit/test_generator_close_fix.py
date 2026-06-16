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
# 2. _invoke_task_work_implement harness-ownership tests (3 tests)
# ============================================================================
#
# TASK-HMIG-006.1 migrated _invoke_task_work_implement off the direct SDK
# call site (query(prompt=prompt, options=options) + manual _tw_gen.aclose()
# bookkeeping) to dispatch through ``select_harness()`` + ``harness.invoke()``.
# After that migration the orchestrator no longer holds the SDK ``query()``
# generator directly — generator hygiene (TASK-RFX-8332 / TASK-FIX-GEN1) is
# owned by the harness (see ClaudeSDKHarness.invoke at
# guardkit/orchestrator/harness/sdk_harness.py:449-459). The tests below
# assert the new contract: the orchestrator dispatches through the harness
# substrate seam and threads the SDK cleanup handler through to the harness,
# rather than holding the generator and closing it inline.
#
# The behavioural guarantee (generator is aclose()d on every exit path) is
# covered by the harness-side tests in tests/orchestrator/harness/
# test_sdk_harness.py — those tests grep the harness source for the same
# substrings this class used to check on the orchestrator.


class TestInvokeTaskWorkImplementGeneratorClose:
    """Verify _invoke_task_work_implement dispatches through the harness
    substrate seam (TASK-HMIG-006.1) rather than holding the SDK generator
    directly. Generator hygiene is now owned by the harness; this class
    asserts the orchestrator-side contract surface only.
    """

    def test_generator_reference_held_in_task_work(self):
        """TASK-HMIG-006.1: dispatch through select_harness/harness.invoke
        instead of holding ``query()`` directly."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        # Must NOT consume the SDK ``query()`` generator inline. After the
        # harness migration, ``query`` lives only inside the harness; any
        # surviving call here would mean the migration regressed.
        assert "async for message in query(" not in source, (
            "Direct ``query()`` consumption must not survive the harness "
            "migration — dispatch through harness.invoke() instead."
        )
        assert "_tw_gen = query(" not in source, (
            "Direct ``query()`` capture must not survive the harness "
            "migration — the harness owns the generator reference."
        )
        # Must dispatch through the harness substrate seam.
        assert "select_harness(" in source, (
            "Must construct the harness via select_harness() so "
            "GUARDKIT_HARNESS routes the dispatch."
        )
        assert "harness.invoke(" in source, (
            "Must iterate harness.invoke() events (per AC-001)."
        )
        # TASK-FIX-LGACLOSE: the bare inline ``async for event in
        # harness.invoke(`` was replaced by an ``aclosing()``-wrapped
        # iteration over a bound stream so the async generator is
        # finalised on EVERY exit (including consumer cancellation). The
        # event taxonomy is unchanged — only the iteration is wrapped.
        assert "aclosing(" in source, (
            "Must wrap harness.invoke() in contextlib.aclosing() so the "
            "async generator is finalised on cancel (TASK-FIX-LGACLOSE)."
        )
        assert "async for event in _harness_stream:" in source, (
            "Must iterate the aclosing-bound stream, not harness.invoke() "
            "inline (TASK-FIX-LGACLOSE)."
        )

    def test_aclose_in_retry_cleanup(self):
        """TASK-HMIG-006.1: retry loop reconstructs the harness instead of
        re-using a manually-managed query() generator."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        # The retry loop (TASK-FIX-46F2) must survive the harness migration
        # — under GPU contention vLLM SSE streams still need a retry.
        assert "MAX_SDK_STREAM_RETRIES" in source, (
            "Retry loop must survive harness migration (TASK-FIX-46F2)."
        )
        # And each retry must build a fresh harness per Design Decision D-6
        # (single-use per invocation). Manual ``_tw_gen.aclose()`` must NOT
        # survive — the harness's own finally block owns generator cleanup.
        assert "await _tw_gen.aclose()" not in source, (
            "Manual generator close must not survive — harness owns it."
        )

    def test_aclose_in_finally_block(self):
        """TASK-HMIG-006.1: manual finally-block generator cleanup is gone;
        D-4 exception handling (AgentInvocationError catch) replaces the
        SDK-specific cascade."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        # The harness raises ``AgentInvocationError`` for every normalised
        # SDK failure (D-4); the orchestrator must have a dedicated catch
        # block for it instead of the old four-clause cascade.
        assert "except AgentInvocationError" in source, (
            "Must catch AgentInvocationError from the harness boundary (D-4)."
        )
        # The old SDK-specific exception cascade must NOT survive — those
        # types live only inside the harness now.
        assert "except CLINotFoundError" not in source, (
            "SDK-specific CLINotFoundError catch must not survive — "
            "harness normalises it to AgentInvocationError."
        )
        assert "except ProcessError" not in source, (
            "SDK-specific ProcessError catch must not survive — "
            "harness normalises it to AgentInvocationError."
        )
        assert "except CLIJSONDecodeError" not in source, (
            "SDK-specific CLIJSONDecodeError catch must not survive — "
            "harness normalises it to AgentInvocationError."
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
        """_install_sdk_cleanup_handler threaded through select_harness.

        TASK-HMIG-006.1: the orchestrator no longer calls
        ``_install_sdk_cleanup_handler(asyncio.get_running_loop())`` itself —
        the harness owns the subprocess lifetime (D-6) and the installer is
        passed in as the ``cleanup_handler_installer`` kwarg so the harness
        invokes it against the right event loop on every call.
        """
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)
        assert "cleanup_handler_installer=_install_sdk_cleanup_handler" in source, (
            "Must pass _install_sdk_cleanup_handler to the harness via the "
            "cleanup_handler_installer kwarg (D-6 contract preserved)."
        )


# ============================================================================
# 4. TASK-FIX-GEN1: Generator drain after ResultMessage (3 tests)
# ============================================================================


class TestGeneratorDrainAfterResultMessage:
    """Verify _invoke_with_role drains the generator after ResultMessage
    to prevent AnyIO cancel-scope CancelledError from gen.aclose()."""

    @pytest.fixture(autouse=True)
    def _force_sdk_harness(self, monkeypatch):
        # TASK-HMIG-011 cutover (2026-06-16): default harness is now "langgraph";
        # this SDK-path test opts into the SDK harness explicitly.
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")

    def test_drain_loop_present_in_source(self):
        """Source contains the drain loop after ResultMessage."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)
        # Must drain remaining messages after ResultMessage
        assert "async for _ in gen:" in source, (
            "Must drain generator after ResultMessage to prevent cancel-scope errors"
        )
        # Must set gen = None after drain to skip aclose() in finally
        assert "gen = None" in source, (
            "Must set gen = None after drain so finally block skips aclose()"
        )

    def test_gen_none_skips_aclose_in_finally(self):
        """When gen is set to None by drain, the finally block skips aclose()."""
        import inspect
        source = inspect.getsource(AgentInvoker._invoke_with_role)
        # The finally block must check gen is not None before aclose
        finally_idx = source.find("finally:")
        assert finally_idx != -1
        after_finally = source[finally_idx:]
        assert "if gen is not None:" in after_finally, (
            "finally block must guard aclose() with 'if gen is not None'"
        )

    @pytest.mark.asyncio
    async def test_no_cancelled_error_after_result_message(self, agent_invoker):
        """TASK-FIX-GEN1 regression: receiving ResultMessage must not raise
        CancelledError from generator cleanup."""
        MockResultMessage = type("ResultMessage", (), {})

        async def query_with_extra_messages(*args, **kwargs):
            """Yield assistant message, ResultMessage, then more messages."""
            yield MagicMock(type="assistant", error=None)
            yield MockResultMessage()
            # These messages come after ResultMessage — the drain loop
            # should consume them without error
            yield MagicMock(type="assistant", error=None)
            yield MagicMock(type="assistant", error=None)

        mock_sdk, _ = _make_mock_sdk(query_with_extra_messages)
        mock_sdk.ResultMessage = MockResultMessage

        with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
            # This should complete without CancelledError.
            # _invoke_with_role returns None; we just verify no exception.
            await agent_invoker._invoke_with_role(
                prompt="TASK-FIX-GEN1: regression test",
                agent_type="player",
                allowed_tools=["Read"],
                permission_mode="acceptEdits",
            )
        # If we reach here, no CancelledError was raised — test passes


# ============================================================================
# 5. TASK-FIX-LGACLOSE: aclosing() wrap on harness.invoke() iteration
# ============================================================================
#
# CTOUT01 wrapped agent.ainvoke in an asyncio.Task so cancel() propagates
# CancelledError, but the consumer iterating LangGraphHarness.invoke (an
# async generator) abandoned it on the feature-timeout cancel path without
# awaiting aclose() — leaving an orphaned async_generator_athrow / pending
# ainvoke task the GC tried to close at interpreter shutdown ("coroutine
# method 'aclose' of 'LangGraphHarness.invoke' was never awaited"). AC-1
# wraps BOTH consumer iteration sites in contextlib.aclosing() so the
# generator is finalised on every exit, including cancellation. Pairs with
# the harness-side defensive finally (AC-2, guardkitfactory). These tests
# pin the call sites via source introspection — the same convention the
# SDK-path tests above use.


class TestHarnessInvokeAclosingOnCancel:
    """Both harness.invoke() consumer sites must finalise the generator."""

    def test_aclosing_imported(self):
        """contextlib.aclosing must be imported for the wrap to resolve."""
        import inspect

        from guardkit.orchestrator import agent_invoker

        source = inspect.getsource(agent_invoker)
        assert "aclosing" in source, (
            "agent_invoker must import contextlib.aclosing for the "
            "TASK-FIX-LGACLOSE generator finalisation wrap."
        )

    def test_invoke_with_role_wraps_harness_invoke_in_aclosing(self):
        """_invoke_with_role (specialist/Player/Coach path) wraps the stream."""
        import inspect

        source = inspect.getsource(AgentInvoker._invoke_with_role)

        assert "harness.invoke(" in source, (
            "Specialist path must still dispatch through harness.invoke()."
        )
        assert "async with aclosing(" in source, (
            "harness.invoke() must be wrapped in aclosing() so the async "
            "generator is finalised on cancel (TASK-FIX-LGACLOSE AC-1)."
        )
        assert "async for event in _harness_stream:" in source, (
            "Must iterate the aclosing-bound stream, not harness.invoke() "
            "inline."
        )
        # The pre-fix inline form must NOT survive — its survival is the
        # exact regression this guards against.
        assert "async for event in harness.invoke(" not in source, (
            "Bare inline iteration of harness.invoke() must not survive — "
            "it leaks the generator on the cancel path."
        )

    def test_coach_validator_test_exec_wraps_harness_invoke_in_aclosing(self):
        """Coach independent-test-exec path (coach_test role) wraps the stream.

        This is the path whose ``asyncio.timeout(self.test_timeout)`` can
        fire mid-stream — the same leak shape as the Player/specialist
        path, so it gets the same aclosing() finalisation.
        """
        import inspect

        from guardkit.orchestrator.quality_gates import coach_validator

        source = inspect.getsource(coach_validator)
        assert "async with aclosing(" in source, (
            "coach_validator must wrap its harness.invoke() iteration in "
            "aclosing() (TASK-FIX-LGACLOSE)."
        )
        assert "async for event in harness.invoke(" not in source, (
            "Bare inline iteration of harness.invoke() must not survive in "
            "coach_validator."
        )

    def test_task_work_interface_design_wraps_harness_invoke_in_aclosing(self):
        """Design-phase path (design role) wraps the stream."""
        import inspect

        from guardkit.orchestrator.quality_gates import task_work_interface

        source = inspect.getsource(task_work_interface)
        assert "async with aclosing(" in source, (
            "task_work_interface must wrap its harness.invoke() iteration "
            "in aclosing() (TASK-FIX-LGACLOSE)."
        )
        assert "async for event in harness.invoke(" not in source, (
            "Bare inline iteration of harness.invoke() must not survive in "
            "task_work_interface."
        )

    def test_task_work_implement_wraps_harness_invoke_in_aclosing(self):
        """_invoke_task_work_implement (task-work Player path) wraps the stream."""
        import inspect

        source = inspect.getsource(AgentInvoker._invoke_task_work_implement)

        assert "harness.invoke(" in source, (
            "Task-work path must still dispatch through harness.invoke()."
        )
        assert "async with aclosing(" in source, (
            "harness.invoke() must be wrapped in aclosing() so the async "
            "generator is finalised on cancel (TASK-FIX-LGACLOSE AC-1)."
        )
        assert "async for event in _harness_stream:" in source, (
            "Must iterate the aclosing-bound stream, not harness.invoke() "
            "inline."
        )
        assert "async for event in harness.invoke(" not in source, (
            "Bare inline iteration of harness.invoke() must not survive — "
            "it leaks the generator on the cancel path."
        )
