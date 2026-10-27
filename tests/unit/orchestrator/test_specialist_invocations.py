"""Tests for guardkit.orchestrator.specialist_invocations.

The orchestrator-side Phase 4/5 specialists (``invoke_test_orchestrator``,
``invoke_code_reviewer`` and the deterministic Phase-4 runner) were removed in
the cull of 27 October 2026. What remains is :func:`run_specialist` and its
no-model-activity watchdog:

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
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import asyncio
import time

from guardkit.orchestrator.specialist_invocations import (
    SpecialistInvocationResult,
    _no_activity_watchdog_exceeded,
    run_specialist,
)


def _make_fake_agent_invoker(
    *,
    invoke_side_effect=None,
    invoke_result=(
        None,
        [SimpleNamespace(type="assistant_message", text="Review report available.")],
    ),
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
    invoker._invoke_with_role = AsyncMock(
        side_effect=invoke_side_effect,
        return_value=invoke_result,
    )
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "specialist_name",
    ["test-orchestrator", "code-reviewer"],
)
async def test_run_specialist_heartbeat_label_includes_specialist_name(
    tmp_path: Path, specialist_name: str
) -> None:
    """run_specialist must thread a ``heartbeat_label_override`` kwarg
    containing ``"specialist:{name}"`` into ``_invoke_with_role`` so
    orchestrator-driven specialists are visually distinct from the
    actual task-work Player in heartbeat logs (TASK-ABSR-DIAG).
    """
    invoker = _make_fake_agent_invoker()

    await run_specialist(
        specialist_name=specialist_name,
        worktree_path=tmp_path,
        task_id="TASK-ABSR-DIAG",
        sdk_timeout=42,
        prompt="do the thing",
        allowed_tools=["Read"],
        agent_invoker=invoker,
    )

    invoker._invoke_with_role.assert_awaited_once()
    kwargs = invoker._invoke_with_role.await_args.kwargs
    assert "heartbeat_label_override" in kwargs, (
        "run_specialist must pass heartbeat_label_override to _invoke_with_role"
    )
    override = kwargs["heartbeat_label_override"]
    assert isinstance(override, str)
    assert f"specialist:{specialist_name}" in override
    assert "invocation" in override


# =============================================================================
# No-model-activity watchdog (TASK-FIX-SPECHANG2)
# =============================================================================
#
# The 600s duration cap (TASK-FIX-SPECHANG) bounds a hang but does not
# eliminate it. Run-9 turn-2 showed the test-orchestrator make zero
# /v1/responses calls for ~480s before the cap fired. The watchdog detects
# that no-model-activity gap and terminates with a distinct reason BEFORE the
# blunt cap, while a normally-progressing specialist (continuous activity)
# is never killed.


def test_no_activity_watchdog_exceeded_predicate() -> None:
    """Pure threshold predicate: gap >= threshold fires; disabled when <= 0."""
    # Gap exactly at threshold → exceeded.
    assert _no_activity_watchdog_exceeded(100.0, 250.0, 150.0) is True
    # Gap beyond threshold → exceeded.
    assert _no_activity_watchdog_exceeded(100.0, 300.0, 150.0) is True
    # Gap below threshold → not exceeded (AC-2: don't kill progressing run).
    assert _no_activity_watchdog_exceeded(100.0, 200.0, 150.0) is False
    # Watchdog disabled (0 or negative threshold) → never fires.
    assert _no_activity_watchdog_exceeded(0.0, 10_000.0, 0.0) is False
    assert _no_activity_watchdog_exceeded(0.0, 10_000.0, -1.0) is False


@pytest.mark.asyncio
async def test_run_specialist_watchdog_captures_last_assistant_message(
    tmp_path: Path,
) -> None:
    """A progressing watchdog call returns events for final-text capture."""
    seen: dict[str, object] = {}

    async def _complete(**kwargs: object):
        seen.update(kwargs)
        invoker._last_activity_monotonic = time.monotonic()
        await asyncio.sleep(0.01)
        return (
            None,
            [
                SimpleNamespace(type="assistant_message", text="first report"),
                SimpleNamespace(type="tool_result", text="ignored"),
                SimpleNamespace(type="assistant_message", text="   "),
                SimpleNamespace(type="assistant_message", text="final report"),
            ],
        )

    invoker = _make_fake_agent_invoker(invoke_side_effect=_complete)
    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-PHASE5-CAPTURE",
        sdk_timeout=42,
        prompt="review",
        allowed_tools=["Read"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
        capture_final_message=True,
    )

    assert result.status == "passed"
    assert result.final_message == "final report"
    assert seen["return_events"] is True


@pytest.mark.asyncio
async def test_run_specialist_watchdog_terminates_hung_specialist(
    tmp_path: Path,
) -> None:
    """AC-1/AC-3: a specialist that stops producing harness events (never
    refreshes the activity clock) is terminated with the distinct
    'hang detected (no model activity for Ns)' reason, and child processes
    are reaped — well before the long inner sleep would complete.
    """
    async def _hang(**_: object) -> None:
        # Simulate a genuine hang: no activity updates for far longer than
        # the watchdog window.
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_hang)

    started = time.monotonic()
    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
        capture_final_message=True,
    )
    elapsed = time.monotonic() - started

    assert result.status == "failed"
    assert result.final_message is None
    assert invoker._invoke_with_role.await_args.kwargs["return_events"] is True
    assert result.error is not None
    assert "hang detected (no model activity" in result.error
    assert result.result_file is None
    # Terminated promptly — did NOT wait for the 10s inner sleep.
    assert elapsed < 5.0
    invoker._kill_child_claude_processes.assert_called_once()


@pytest.mark.asyncio
async def test_run_specialist_watchdog_allows_progressing_specialist(
    tmp_path: Path,
) -> None:
    """AC-2: a specialist that keeps refreshing the activity clock
    (continuous model calls) completes normally and is never killed by the
    watchdog.
    """
    async def _progressing(**_: object) -> None:
        # Refresh the activity clock faster than the watchdog window, the way
        # _invoke_with_role does on every harness event.
        for _ in range(8):
            invoker._last_activity_monotonic = time.monotonic()
            await asyncio.sleep(0.05)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_progressing)

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
    )

    assert result.status == "passed"
    assert result.error is None
    assert result.result_file == (
        tmp_path / ".guardkit" / "autobuild" / "TASK-OSI-001" / "specialist_results.json"
    )
    invoker._kill_child_claude_processes.assert_not_called()


@pytest.mark.asyncio
async def test_run_specialist_watchdog_survives_buffered_langgraph_run(
    tmp_path: Path,
) -> None:
    """TASK-FIX-SPECINVOKE01 regression: a specialist that yields ZERO harness
    events for the whole run (the LangGraph harness's await-then-yield cadence)
    but whose model activity is surfaced ONLY via the ``on_model_activity``
    callback is NOT false-killed by the watchdog.

    This is the exact FEAT-9DDE run-3 scenario: ~18 successful ``/v1/responses``
    POSTs, but ``0 events`` reached the consumer loop, so the event-keyed clock
    froze and the watchdog wrongly fired at 150 s. The fix threads
    ``AgentInvoker._bump_activity`` into the harness as ``on_model_activity``;
    here we drive the *real* ``_bump_activity`` from the callback channel (never
    touching the clock via event yields) and prove the watchdog stays quiet —
    in deliberate contrast to ``test_run_specialist_watchdog_terminates_hung_
    specialist`` (no callback pings → still killed).
    """
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    invoker = _make_fake_agent_invoker()
    # Bind the production _bump_activity onto the mock so the callback channel
    # updates the same attribute the watchdog polls.
    invoker._bump_activity = lambda: AgentInvoker._bump_activity(invoker)

    async def _buffered_run(**_: object) -> None:
        # Mimic LangGraph: the consumer loop sees NO events (never sets the
        # clock itself); the only activity signal is the harness callback,
        # which fires on each model/tool boundary. Pings span well past the
        # 0.2 s watchdog window.
        for _ in range(8):
            invoker._bump_activity()  # what _ModelActivityCallbackHandler does
            await asyncio.sleep(0.05)

    invoker._invoke_with_role = AsyncMock(side_effect=_buffered_run)

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
    )

    assert result.status == "passed"
    assert result.error is None
    invoker._kill_child_claude_processes.assert_not_called()


@pytest.mark.asyncio
async def test_run_specialist_watchdog_synthesises_and_restores_cancellation_event(
    tmp_path: Path,
) -> None:
    """When no cancellation_event is supplied, the watchdog synthesises one
    (so the in-flight _cancel_monitor can dispatch harness.cancel() + SIGTERM)
    and restores the invoker's original None afterwards.
    """
    seen: dict[str, object] = {}

    async def _capture_then_hang(**_: object) -> None:
        seen["event_during_call"] = invoker._cancellation_event
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_capture_then_hang)
    assert invoker._cancellation_event is None

    await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        no_activity_watchdog_seconds=0.2,
    )

    # A real Event was installed for the duration of the call …
    assert isinstance(seen["event_during_call"], threading.Event)
    # … and it was set when the watchdog fired (cooperative cancel signal).
    assert seen["event_during_call"].is_set()
    # … and the invoker's original (None) is restored afterwards.
    assert invoker._cancellation_event is None



# =============================================================================
# Shape A — specialist-hang termination does NOT cascade into the shared
# task-level cancellation_event (TASK-FIX-SPECCOCH01 AC-1, AC-3).
# =============================================================================
#
# Before the fix the watchdog set the caller-supplied (shared) event to drive
# ``_cancel_monitor`` into ``harness.cancel()``. The shared event is also the
# signal autobuild._loop_phase polls for the Coach grace-period branch
# (autobuild.py:3077-3087), so a healthy hang of the test-orchestrator
# specialist would cap the subsequent Coach invocation at
# ``COACH_GRACE_PERIOD_SECONDS`` and silently drop the Coach verdict (F22 /
# I-011, surfaced in run-10 of FEAT-AOF). Shape A delivers the watchdog signal
# through a specialist-local event, leaving the shared event untouched.


@pytest.mark.asyncio
async def test_watchdog_does_not_set_shared_cancellation_event(
    tmp_path: Path,
) -> None:
    """AC-1: when the watchdog terminates a hung specialist, the caller's
    shared task-level cancellation_event must NOT be set.

    Decouples specialist-hang detection from the Coach grace-period
    cascade — the grace-period branch in autobuild._loop_phase only fires
    when the shared event is set, and Shape A reserves that signal for
    the real task-timeout / outer-orchestrator-cancel path.
    """
    async def _hang(**_: object) -> None:
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_hang)
    shared_event = threading.Event()
    assert not shared_event.is_set()

    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-FIX-SPECCOCH01",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        cancellation_event=shared_event,
        no_activity_watchdog_seconds=0.2,
    )

    # The watchdog fired and reported the hang …
    assert result.status == "failed"
    assert "hang detected (no model activity" in (result.error or "")
    # … but the caller's shared event was NEVER touched. This is the
    # load-bearing assertion that prevents the F22 grace-period cascade.
    assert not shared_event.is_set()


@pytest.mark.asyncio
async def test_watchdog_uses_specialist_local_event_distinct_from_shared(
    tmp_path: Path,
) -> None:
    """AC-1 (mechanism check): the event installed on the invoker for the
    duration of a watchdog-protected call must be a brand-new
    specialist-local Event — NOT the caller-supplied shared event.

    Pins the implementation contract that the cancel-monitor polling
    target is decoupled from the caller's task-level signal. Without
    this, the test above could pass by accident if a future refactor
    set the shared event back to ``False`` after firing.
    """
    seen: dict[str, object] = {}

    async def _capture_then_hang(**_: object) -> None:
        seen["event_during_call"] = invoker._cancellation_event
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_capture_then_hang)
    shared_event = threading.Event()

    await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-FIX-SPECCOCH01",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        cancellation_event=shared_event,
        no_activity_watchdog_seconds=0.2,
    )

    installed = seen["event_during_call"]
    assert isinstance(installed, threading.Event)
    # The local event is a distinct object from the caller's shared event …
    assert installed is not shared_event
    # … the local event WAS set by the watchdog (cooperative cancel) …
    assert installed.is_set()
    # … and the shared event remains unset (no grace-period cascade).
    assert not shared_event.is_set()
    # And the invoker's _cancellation_event attribute is restored to its
    # pre-call value (None on the fake), even though we overrode it.
    assert invoker._cancellation_event is None


@pytest.mark.asyncio
async def test_external_shared_event_still_aborts_specialist(
    tmp_path: Path,
) -> None:
    """AC-1 (CTOUT01 compatibility): when the caller's shared event is set
    *externally* mid-invocation (real task-timeout path), the watchdog
    must still terminate the in-flight specialist. The shared event's
    state is forwarded into the specialist-local event so
    ``_cancel_monitor`` dispatches ``harness.cancel()`` + SIGTERM.

    Without this, decoupling the watchdog from the shared event would
    silently break the in-flight LangGraph cleanup contract on the
    legitimate cancellation path.
    """
    shared_event = threading.Event()

    async def _hang_until_external_cancel(**_: object) -> None:
        # Trip the shared event from inside the specialist coroutine to
        # simulate an external FeatureOrchestrator timeout firing while
        # the specialist is still in-flight.
        await asyncio.sleep(0.1)
        shared_event.set()
        await asyncio.sleep(10.0)

    invoker = _make_fake_agent_invoker(invoke_side_effect=_hang_until_external_cancel)

    started = time.monotonic()
    result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=tmp_path,
        task_id="TASK-FIX-SPECCOCH01",
        sdk_timeout=600,
        prompt="run the tests",
        allowed_tools=["Read", "Bash", "Write"],
        agent_invoker=invoker,
        cancellation_event=shared_event,
        # Watchdog window large enough that the *hang* branch cannot
        # fire on the first few polls (the no-activity gap grows from 0
        # and only crosses the threshold near t ≈ 5). Poll interval is
        # derived as ``watchdog/5`` (capped) so this gives 1 s polling —
        # the shared-event forward fires on the second poll, well before
        # the inner 10 s sleep or the hang branch.
        no_activity_watchdog_seconds=5.0,
    )
    elapsed = time.monotonic() - started

    assert result.status == "failed"
    assert result.error == "specialist invocation cancelled"
    # Terminated promptly via the shared-event forward, NOT the 10s inner
    # sleep or the watchdog window.
    assert elapsed < 3.0
    # The hang-reason error was NOT used — this is the shared-event
    # forwarding branch, not the watchdog-detected-hang branch.
    assert "hang detected" not in (result.error or "")


# ===========================================================================
# What the specialist said — the optional capture (review-leg second ask)
# ===========================================================================
#
# The review leg needs the words a specialist used when it finished without
# writing its report: an empty directory says nothing about what it did with
# its minutes. The capture is opt-in, so every other caller is untouched.


@pytest.mark.asyncio
async def test_final_message_is_none_and_unasked_for_by_default(tmp_path: Path) -> None:
    """No capture requested: no extra kwarg, and ``final_message`` stays None."""
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

    assert result.final_message is None
    assert "return_events" not in invoker._invoke_with_role.await_args.kwargs


@pytest.mark.asyncio
async def test_capture_keeps_the_last_thing_the_specialist_said(
    tmp_path: Path,
) -> None:
    """With the capture on, the last assistant message comes back on the result."""
    from guardkit.orchestrator.harness.adapter import AssistantMessageEvent

    invoker = _make_fake_agent_invoker()
    invoker._invoke_with_role = AsyncMock(
        return_value=(
            None,
            [
                AssistantMessageEvent(text="I am reading the files."),
                AssistantMessageEvent(text="I have finished my review."),
            ],
        )
    )

    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="review the diff",
        allowed_tools=["Read", "Grep"],
        agent_invoker=invoker,
        capture_final_message=True,
    )

    assert result.final_message == "I have finished my review."
    assert invoker._invoke_with_role.await_args.kwargs["return_events"] is True


@pytest.mark.asyncio
async def test_capture_stays_none_when_there_is_nothing_to_read(
    tmp_path: Path,
) -> None:
    """A runner that hands nothing back leaves ``final_message`` empty, not guessed."""
    invoker = _make_fake_agent_invoker()
    invoker._invoke_with_role = AsyncMock(return_value=None)

    result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=tmp_path,
        task_id="TASK-OSI-001",
        sdk_timeout=42,
        prompt="review the diff",
        allowed_tools=["Read", "Grep"],
        agent_invoker=invoker,
        capture_final_message=True,
    )

    assert result.final_message is None
