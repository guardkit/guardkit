"""Skeleton tests for guardkit.orchestrator.specialist_invocations.

Pins the contract that TASK-OSI-004 / TASK-OSI-005 build on:

* :func:`run_specialist` delegates to ``AgentInvoker._invoke_with_role``
  with the right agent_type / permission_mode for each specialist.
* The runner restores ``sdk_timeout_seconds`` and ``_cancellation_event``
  on the AgentInvoker after the call, even when the call raises.
* On exception, the runner returns ``status="failed"`` with ``error``
  populated and reaps child claude processes — it never propagates the
  exception.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.orchestrator.specialist_invocations import (
    SpecialistInvocationResult,
    run_specialist,
)


def _make_fake_agent_invoker(
    *,
    invoke_side_effect=None,
    sdk_timeout_seconds: int = 1200,
    cancellation_event: threading.Event | None = None,
) -> MagicMock:
    """Return a MagicMock that mimics the AgentInvoker surface we touch.

    Only the attributes/methods :func:`run_specialist` reads or writes are
    populated. Pulling in the real AgentInvoker would require the SDK and
    a real worktree, neither of which this skeleton-level test needs.
    """
    invoker = MagicMock(name="AgentInvoker")
    invoker.sdk_timeout_seconds = sdk_timeout_seconds
    invoker._cancellation_event = cancellation_event
    invoker._invoke_with_role = AsyncMock(side_effect=invoke_side_effect)
    invoker._kill_child_claude_processes = MagicMock()
    return invoker


@pytest.mark.asyncio
async def test_run_specialist_happy_path_returns_passed(tmp_path: Path) -> None:
    """Successful delegation produces a passed result with phase derived
    from specialist_name and the conventional result_file path filled in.
    """
    invoker = _make_fake_agent_invoker()

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
    )

    assert isinstance(result, SpecialistInvocationResult)
    assert result.specialist_name == "test-orchestrator"
    assert result.phase == "4"
    assert result.status == "passed"
    assert result.error is None
    assert result.result_file == (
        tmp_path / ".guardkit" / "autobuild" / "TASK-OSI-001" / "specialist_results.json"
    )
    assert result.duration_seconds >= 0

    invoker._invoke_with_role.assert_awaited_once()
    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert kwargs["prompt"] == "run the tests"
    assert kwargs["agent_type"] == "player"
    assert kwargs["permission_mode"] == "acceptEdits"
    assert kwargs["allowed_tools"] == ["Read", "Bash", "Write"]
    assert kwargs["task_id"] == "TASK-OSI-001"

    invoker._kill_child_claude_processes.assert_not_called()


@pytest.mark.asyncio
async def test_run_specialist_code_reviewer_runs_as_coach(tmp_path: Path) -> None:
    """code-reviewer must run as agent_type=coach with bypassPermissions
    so the existing read-only invariant the gate enforces holds.
    """
    invoker = _make_fake_agent_invoker()

    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="review the diff",
        allowed_tools=["Read", "Grep"],
        agent_invoker=invoker,
    )

    assert result.phase == "5"
    assert result.status == "passed"

    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert kwargs["agent_type"] == "coach"
    assert kwargs["permission_mode"] == "bypassPermissions"


@pytest.mark.asyncio
async def test_run_specialist_failure_returns_failed_and_reaps(tmp_path: Path) -> None:
    """When ``_invoke_with_role`` raises, the runner must return a failed
    result, populate ``error``, and reap child claude processes — never
    propagate.
    """
    boom = RuntimeError("SDK exploded")
    invoker = _make_fake_agent_invoker(invoke_side_effect=boom)

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
    )

    assert result.status == "failed"
    assert result.error is not None
    assert "RuntimeError" in result.error
    assert "SDK exploded" in result.error
    # On failure we leave result_file unset so callers cannot assume the
    # specialist actually wrote the conventional file.
    assert result.result_file is None
    invoker._kill_child_claude_processes.assert_called_once()


@pytest.mark.asyncio
async def test_run_specialist_restores_state_after_call(tmp_path: Path) -> None:
    """The runner must restore ``sdk_timeout_seconds`` and
    ``_cancellation_event`` on the AgentInvoker on both the success and
    the failure paths so subsequent invocations see the original state.
    """
    original_timeout = 1234
    original_event = threading.Event()
    invoker = _make_fake_agent_invoker(
        sdk_timeout_seconds=original_timeout,
        cancellation_event=original_event,
    )
    override_event = threading.Event()

    # Inside the call, sdk_timeout_seconds must reflect the override.
    captured: dict[str, object] = {}

    async def _capture(**_: object) -> None:
        captured["timeout"] = invoker.sdk_timeout_seconds
        captured["cancellation"] = invoker._cancellation_event

    invoker._invoke_with_role = AsyncMock(side_effect=_capture)

    await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=99,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        cancellation_event=override_event,
    )

    assert captured["timeout"] == 99
    assert captured["cancellation"] is override_event
    # State must be restored after the call, regardless of success.
    assert invoker.sdk_timeout_seconds == original_timeout
    assert invoker._cancellation_event is original_event


@pytest.mark.asyncio
async def test_run_specialist_restores_state_on_failure(tmp_path: Path) -> None:
    """Same restore invariant on the failure path."""
    original_timeout = 1234
    original_event = threading.Event()
    invoker = _make_fake_agent_invoker(
        invoke_side_effect=RuntimeError("boom"),
        sdk_timeout_seconds=original_timeout,
        cancellation_event=original_event,
    )

    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=77,
        prompt="review",
        allowed_tools=["Read"],
        agent_invoker=invoker,
        cancellation_event=threading.Event(),
    )

    assert result.status == "failed"
    assert invoker.sdk_timeout_seconds == original_timeout
    assert invoker._cancellation_event is original_event
