"""Run one orchestrator-side specialist agent with a time limit.

:func:`run_specialist` delegates into ``AgentInvoker._invoke_with_role`` with a
wall-clock limit and a no-activity watchdog. The headless review leg
(``review_runner``) uses it. (27 October 2026: the test-phase and code-review
specialists that ran inside every build turn were removed with the checks
they fed.)
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Optional,
)


if TYPE_CHECKING:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

logger = logging.getLogger(__name__)


# Per-specialist SDK-timeout ceiling for the Phase 4 test-orchestrator.
#
# The caller-supplied ``sdk_timeout`` is shared with Player/Coach and can
# reach 2340s on the canary batch. The test-orchestrator specialist has
# been observed to launch ``pytest`` with ``Bash run_in_background=true``
# then poll ``TaskOutput`` every ~30s until the SDK timeout fires —
# burning ~38min per turn even when pytest itself would finish in <2min
# (TASK-HMIG-009A AC-003 rep 1, 2026-06-03; see
# ``docs/reviews/autobuild-migration/long-run-1.md``). The cap is a hard
# orchestrator-side ceiling that converts the SDK timeout into a graceful
# specialist failure at the 10-minute mark instead of letting it consume
# the full Player/Coach budget. Suites that legitimately need >600s
# should be decomposed at the task level, not papered over here.
_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS: int = 600


# Distinct, grep-able reason emitted when the watchdog (not the duration cap)
# terminates a specialist. AC-3: hang vs cap must be distinguishable in logs
# and the review summary.
_WATCHDOG_HANG_REASON_TEMPLATE: str = "hang detected (no model activity for {seconds}s)"


# TASK-AB-REVIEWCLEAN01 (item 1): the pytest-summary regex + count semantics
# now live in guardkit.lib.pytest_summary (the single source of truth shared
# with coach_validator's advisory skip-count reader). ``_parse_pytest_counts``
# below adapts that parser to this module's historic
# ``(tests_run, tests_failed, tests_skipped)`` tuple shape.


# Reverse lookup of guardkit.orchestrator.phase_specialists.STATIC_PHASE_SPECIALISTS
# scoped to specialists this module is responsible for. Kept inline rather
# than imported to avoid a hard module dependency for a 2-entry table.
_SPECIALIST_PHASES: dict[str, str] = {
    "test-orchestrator": "4",
    "code-reviewer": "5",
}

# agent_type / permission_mode each specialist runs as inside _invoke_with_role.
# test-orchestrator writes test artefacts to the worktree (player role,
# acceptEdits). code-reviewer is read-only review (coach role,
# bypassPermissions matches coach_validator's expectations).
_SPECIALIST_INVOCATION_PROFILE: dict[
    str,
    tuple[Literal["player", "coach"], Literal["acceptEdits", "bypassPermissions"]],
] = {
    "test-orchestrator": ("player", "acceptEdits"),
    "code-reviewer": ("coach", "bypassPermissions"),
}


@dataclass
class SpecialistInvocationResult:
    """Outcome of a single orchestrator-driven specialist invocation.

    Populated by :func:`run_specialist` and consumed by the OSI Wave-2/3
    runners (TASK-OSI-004, TASK-OSI-005) and the gate-credit injector
    (TASK-OSI-002). ``result_file`` points at the conventional
    ``specialist_results.json`` location when known; callers may overwrite
    it after they confirm the file actually landed on disk.

    ``final_message`` is the last thing the specialist said in words. It is
    filled in only when the caller asks for it (``run_specialist(...,
    capture_final_message=True)``) and stays ``None`` otherwise, so every
    existing caller and every existing result is exactly what it was. The
    review leg asks for it: when a specialist finishes without writing its
    report, the only record of what it did with its minutes is what it said.
    """

    specialist_name: str
    phase: str
    status: Literal["passed", "failed", "skipped"]
    duration_seconds: float
    result_file: Optional[Path]
    error: Optional[str]
    final_message: Optional[str] = None


def _final_assistant_text(invoke_result: Any) -> Optional[str]:
    """The last thing the model said, out of a ``return_events`` invocation.

    ``_invoke_with_role(return_events=True)`` returns ``(None, events)``. The
    events are read by duck-typing (``type`` / ``text``) rather than by
    importing the harness event classes, so this helper cannot break on a
    harness that grows a new event shape. Returns ``None`` when there is
    nothing to read — the caller then says so plainly rather than inventing
    text.
    """
    if not isinstance(invoke_result, tuple) or len(invoke_result) != 2:
        return None
    events = invoke_result[1]
    if not isinstance(events, (list, tuple)):
        return None
    for event in reversed(events):
        if getattr(event, "type", None) != "assistant_message":
            continue
        text = getattr(event, "text", "")
        if isinstance(text, str) and text.strip():
            return text
    return None


def _reap_specialist_processes(
    agent_invoker: "AgentInvoker", specialist_name: str
) -> None:
    """Best-effort reap of child ``claude`` processes; never raises.

    Shared by the failure paths in :func:`run_specialist` and
    :func:`_run_specialist_with_watchdog` so a hung or crashed specialist
    cannot leak subprocesses across turns.
    """
    try:
        agent_invoker._kill_child_claude_processes()
    except Exception as cleanup_exc:  # noqa: BLE001
        logger.warning(
            "run_specialist(%s): _kill_child_claude_processes raised "
            "during cleanup: %s",
            specialist_name,
            cleanup_exc,
        )


def _no_activity_watchdog_exceeded(
    last_activity_monotonic: float,
    now_monotonic: float,
    watchdog_seconds: float,
) -> bool:
    """Pure predicate: has the no-model-activity gap reached the threshold?

    Returns ``True`` when ``now - last_activity >= watchdog_seconds`` and
    the watchdog is enabled (``watchdog_seconds > 0``). Isolated as a
    pure function so the threshold decision is unit-testable without
    spinning up an event loop (TASK-FIX-SPECHANG2 AC-1/AC-2).
    """
    if watchdog_seconds <= 0:
        return False
    return (now_monotonic - last_activity_monotonic) >= watchdog_seconds


async def _run_specialist_with_watchdog(
    *,
    agent_invoker: "AgentInvoker",
    invoke_kwargs: dict[str, Any],
    watchdog_seconds: float,
    specialist_local_event: threading.Event,
    shared_cancellation_event: Optional[threading.Event],
    specialist_name: str,
    task_id: str,
    poll_interval: Optional[float] = None,
) -> tuple[Literal["passed", "failed"], Optional[str], Any]:
    """Run ``_invoke_with_role`` under a no-model-activity watchdog.

    Races the invocation against a poll loop that reads
    ``agent_invoker._last_activity_monotonic`` (updated per harness event
    inside ``_invoke_with_role``). When the no-activity gap reaches
    ``watchdog_seconds``, the invocation is terminated cooperatively by
    setting ``specialist_local_event`` (the event the in-flight
    ``_cancel_monitor`` polls), which dispatches ``harness.cancel()`` +
    SIGTERM. The asyncio task is then hard-cancelled so this coroutine
    returns promptly rather than waiting on the 2s monitor poll. The
    distinct ``hang detected (no model activity for Ns)`` reason fires
    well before the blunt 600s duration cap (AC-1, AC-3 of
    TASK-FIX-SPECHANG2).

    TASK-FIX-SPECCOCH01 (Shape A): the watchdog's cancellation signal is
    delivered through the **specialist-local** event, NOT through the
    caller-supplied ``shared_cancellation_event``. The shared event is
    reserved for the real task-timeout / outer-orchestrator-cancel path
    that drives the Coach grace-period branch
    (``autobuild.py`` ``COACH_GRACE_PERIOD_SECONDS``). Without this
    separation a healthy specialist hang would cascade into Coach being
    capped at the grace-period budget and silently dropping its verdict
    (F22 / I-011, surfaced in run-10 of FEAT-AOF).

    The shared event is still monitored on each poll: if it is set
    externally (e.g. ``FeatureOrchestrator`` timeout) the watchdog
    forwards the signal into ``specialist_local_event`` so the in-flight
    LangGraph cleanup contract (CTOUT01, see
    ``.claude/rules/harness-cancellation-contract.md``) is preserved on
    the legitimate task-timeout path.

    A normally-progressing specialist keeps the activity clock fresh, so
    the watchdog never trips for it (AC-2 of TASK-FIX-SPECHANG2).

    Returns:
        ``("passed", None, invoke_result)`` on clean completion, or
        ``("failed", reason, None)`` on a detected hang, an external
        cancellation, or any exception raised by the invocation. Never
        propagates and never returns a partial result from a failed call.
    """
    poll = (
        poll_interval
        if poll_interval is not None
        else min(max(watchdog_seconds / 5.0, 0.05), 15.0)
    )
    invoke_task: asyncio.Task = asyncio.ensure_future(
        agent_invoker._invoke_with_role(**invoke_kwargs)
    )
    hang_reason: Optional[str] = None
    external_cancel = False

    while True:
        done, _pending = await asyncio.wait({invoke_task}, timeout=poll)
        if invoke_task in done:
            break

        # Forward real (caller-driven) cancellation into the specialist's
        # local scope so the in-flight _cancel_monitor still terminates the
        # invocation when the outer task budget is exhausted. The shared
        # event itself is never written to by this watchdog.
        if (
            shared_cancellation_event is not None
            and shared_cancellation_event.is_set()
        ):
            external_cancel = True
            specialist_local_event.set()
            invoke_task.cancel()
            break

        now = time.monotonic()
        last_activity = getattr(agent_invoker, "_last_activity_monotonic", now)
        if _no_activity_watchdog_exceeded(last_activity, now, watchdog_seconds):
            gap = now - last_activity
            hang_reason = _WATCHDOG_HANG_REASON_TEMPLATE.format(seconds=round(gap))
            logger.warning(
                "[%s] run_specialist(%s): %s — terminating before the %ds "
                "duration cap",
                task_id,
                specialist_name,
                hang_reason,
                _TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS,
            )
            # TASK-FIX-SPECCOCH01: set ONLY the specialist-local event.
            # The caller's shared cancellation_event MUST NOT be touched —
            # that is the signal that drives the Coach grace-period
            # cascade in autobuild._loop_phase.
            specialist_local_event.set()
            invoke_task.cancel()
            break

    invoke_result: Any = None
    try:
        invoke_result = await invoke_task
    except asyncio.CancelledError:
        if hang_reason is None:
            # External cancellation (e.g. FeatureOrchestrator timeout), not
            # the watchdog — surface as a generic failed result.
            return "failed", "specialist invocation cancelled", None
    except Exception as exc:  # noqa: BLE001 — runner must never raise
        if hang_reason is None:
            _reap_specialist_processes(agent_invoker, specialist_name)
            return "failed", f"{type(exc).__name__}: {exc}", None

    if hang_reason is not None:
        _reap_specialist_processes(agent_invoker, specialist_name)
        return "failed", hang_reason, None
    if external_cancel:
        # Shared-event cancellation came from outside; the in-flight LangGraph
        # cleanup contract has already been honoured via the local forward.
        return "failed", "specialist invocation cancelled", None
    return "passed", None, invoke_result


async def run_specialist(
    specialist_name: str,
    worktree_path: Path,
    task_id: str,
    sdk_timeout: int,
    prompt: str,
    allowed_tools: list[str],
    agent_invoker: "AgentInvoker",
    *,
    cancellation_event: Optional[threading.Event] = None,
    turn: Optional[int] = None,
    no_activity_watchdog_seconds: Optional[float] = None,
    capture_final_message: bool = False,
    recursion_limit: Optional[int] = None,
    max_tool_result_chars: Optional[int] = None,
    tool_counter: Any = None,
) -> SpecialistInvocationResult:
    """Run a specialist agent under the orchestrator's control.

    Delegates to :meth:`AgentInvoker._invoke_with_role` via composition so
    SDK invocation, instrumentation, and cancellation handling stay in one
    place. Exceptions and timeouts are caught and converted into a
    ``status="failed"`` result; child ``claude`` processes are reaped via
    :meth:`AgentInvoker._kill_child_claude_processes` in a ``finally``
    block so a hung specialist cannot leak subprocesses across turns.

    Args:
        specialist_name: Canonical specialist agent name
            (``"test-orchestrator"`` or ``"code-reviewer"``).
        worktree_path: Worktree the specialist operates against. Surfaced
            on the result for callers that need to compute the
            conventional ``specialist_results.json`` path.
        task_id: AutoBuild task ID; used for the conventional result-file
            path and for log/error messages.
        sdk_timeout: Per-invocation SDK timeout in seconds. Temporarily
            replaces ``agent_invoker.sdk_timeout_seconds`` for the
            duration of the call; the original value is restored in
            ``finally``.
        prompt: Fully-rendered prompt for the specialist.
        allowed_tools: SDK ``allowed_tools`` list for this specialist.
        agent_invoker: :class:`AgentInvoker` whose
            :meth:`_invoke_with_role` performs the actual SDK call.
        cancellation_event: Optional :class:`threading.Event` that, when
            set, signals the SDK monitor inside ``_invoke_with_role`` to
            kill the subprocess. When provided, temporarily replaces
            ``agent_invoker._cancellation_event`` for the call.
        turn: Optional autobuild turn number, forwarded to
            ``_invoke_with_role`` for instrumentation labelling.
        no_activity_watchdog_seconds: When set to a positive value, run the
            invocation under a no-model-activity watchdog: if the specialist
            stops producing harness events for this many seconds it is
            terminated with a distinct ``hang detected (no model activity
            for Ns)`` failure, before the blunt duration cap fires
            (TASK-FIX-SPECHANG2). ``None`` / ``0`` disables the watchdog and
            preserves the legacy direct-await behaviour.
        capture_final_message: When ``True``, keep the last thing the
            specialist said in words on the result's ``final_message``.
            Costs one extra kwarg to ``_invoke_with_role``
            (``return_events=True``), which changes what that call *returns*
            and nothing else. Defaults to ``False``, so every existing caller
            behaves exactly as before. The watchdog returns a completed
            invocation payload only on its clean-success path; hangs,
            cancellations, and exceptions cannot contribute stale text.
        recursion_limit: Optional step cap for the run, passed to
            ``_invoke_with_role`` exactly as the Coach evidence pass passes
            it (LangGraph only; the SDK harness keeps its turn ceiling).
            ``None`` (the default) leaves the call unchanged.
        max_tool_result_chars: Optional per-tool-result size limit, passed
            the same way. ``None`` (the default) leaves the call unchanged.
        tool_counter: Optional ``ToolCallCounter`` handed to
            ``_invoke_with_role`` so the caller can record which tools the run
            used, even when it is cut off. ``None`` leaves the call unchanged.

    Returns:
        :class:`SpecialistInvocationResult` with ``status="passed"`` on
        success, ``status="failed"`` on any exception or timeout, and
        ``error`` populated with the exception message on failure. The
        function never propagates exceptions to the caller — the
        autobuild turn loop owns recovery decisions.
    """
    phase = _SPECIALIST_PHASES.get(specialist_name, "")
    profile = _SPECIALIST_INVOCATION_PROFILE.get(
        specialist_name, ("coach", "bypassPermissions")
    )
    agent_type, permission_mode = profile

    conventional_result_file = (
        Path(worktree_path)
        / ".guardkit"
        / "autobuild"
        / task_id
        / "specialist_results.json"
    )

    watchdog_enabled = bool(
        no_activity_watchdog_seconds and no_activity_watchdog_seconds > 0
    )

    previous_timeout = agent_invoker.sdk_timeout_seconds
    previous_cancellation = agent_invoker._cancellation_event

    # TASK-FIX-SPECCOCH01 (Shape A): when the watchdog is enabled, always
    # install a fresh **specialist-local** event as the in-flight
    # ``_cancel_monitor`` polling target. Setting this event signals
    # ``harness.cancel()`` + SIGTERM without touching the caller's shared
    # ``cancellation_event``. The shared event is monitored separately
    # inside ``_run_specialist_with_watchdog`` and forwarded into the
    # specialist-local event when set externally (preserves the CTOUT01
    # in-flight LangGraph cleanup contract on the real task-timeout path).
    #
    # When the watchdog is disabled the legacy direct-passthrough is kept:
    # the caller's event (if any) becomes the monitor's polling target.
    specialist_local_event: Optional[threading.Event] = None
    if watchdog_enabled:
        specialist_local_event = threading.Event()
        effective_cancellation = specialist_local_event
    else:
        effective_cancellation = cancellation_event
    cancellation_overridden = (
        effective_cancellation is not None
        and effective_cancellation is not previous_cancellation
    )
    if cancellation_overridden:
        agent_invoker._cancellation_event = effective_cancellation

    agent_invoker.sdk_timeout_seconds = sdk_timeout
    # Seed the activity clock so a watchdog poll that lands before the first
    # harness event measures the gap from "invocation began".
    agent_invoker._last_activity_monotonic = time.monotonic()

    started_at = time.monotonic()
    error_message: Optional[str] = None
    final_message: Optional[str] = None
    status: Literal["passed", "failed", "skipped"] = "passed"

    # TASK-ABSR-DIAG: Surface orchestrator-invoked specialists in heartbeat
    # logs as "specialist:{name} invocation" instead of inheriting the
    # generic "Player invocation" / "Coach invocation" label from
    # agent_type.capitalize(). Without this, a Phase-4 test-orchestrator
    # invocation (agent_type="player") logs identically to the actual
    # task-work Player and operators reading run history conflate them.
    heartbeat_label_override = f"specialist:{specialist_name} invocation"

    invoke_kwargs: dict[str, Any] = {
        "prompt": prompt,
        "agent_type": agent_type,
        "allowed_tools": allowed_tools,
        "permission_mode": permission_mode,
        "task_id": task_id,
        "turn": turn,
        "heartbeat_label_override": heartbeat_label_override,
        # 13 October 2026: the llm.call event names the specialist. Its
        # permission role (``agent_type``) is "coach" for the code reviewer,
        # which wrongly put the reviewer's timeouts on the Coach's record.
        "event_role": "specialist",
        "event_agent_name": specialist_name,
        # 19 October 2026 (review R1): the specialists' own shell folders. The
        # permission role above makes the test orchestrator a "player" and the
        # code reviewer a "coach"; without this they would share the
        # builder's or the checker's home and temporary folders.
        "shell_role": "specialist",
    }

    capturing = capture_final_message
    if capturing:
        invoke_kwargs["return_events"] = True
    if recursion_limit is not None:
        invoke_kwargs["recursion_limit"] = recursion_limit
    if max_tool_result_chars is not None:
        invoke_kwargs["max_tool_result_chars"] = max_tool_result_chars
    if tool_counter is not None:
        invoke_kwargs["tool_counter"] = tool_counter

    try:
        if watchdog_enabled:
            # ``specialist_local_event`` is guaranteed non-None inside this
            # branch by the construction above; assert that for the type
            # checker and to document the invariant for future readers.
            assert specialist_local_event is not None
            (
                status,
                error_message,
                invoke_result,
            ) = await _run_specialist_with_watchdog(
                agent_invoker=agent_invoker,
                invoke_kwargs=invoke_kwargs,
                watchdog_seconds=float(no_activity_watchdog_seconds),
                specialist_local_event=specialist_local_event,
                shared_cancellation_event=cancellation_event,
                specialist_name=specialist_name,
                task_id=task_id,
            )
            if status == "passed" and capturing:
                final_message = _final_assistant_text(invoke_result)
            if status == "failed":
                logger.warning(
                    "run_specialist(%s) failed for %s: %s",
                    specialist_name,
                    task_id,
                    error_message,
                )
        else:
            try:
                invoke_result = await agent_invoker._invoke_with_role(**invoke_kwargs)
                if capturing:
                    final_message = _final_assistant_text(invoke_result)
            except Exception as exc:  # noqa: BLE001 — runner must never raise
                status = "failed"
                error_message = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "run_specialist(%s) failed for %s: %s",
                    specialist_name,
                    task_id,
                    error_message,
                )
                _reap_specialist_processes(agent_invoker, specialist_name)
    finally:
        agent_invoker.sdk_timeout_seconds = previous_timeout
        if cancellation_overridden:
            agent_invoker._cancellation_event = previous_cancellation

    duration_seconds = time.monotonic() - started_at

    return SpecialistInvocationResult(
        specialist_name=specialist_name,
        phase=phase,
        status=status,
        duration_seconds=duration_seconds,
        result_file=conventional_result_file if status == "passed" else None,
        error=error_message,
        final_message=final_message,
    )


def _extract_section(text: str, heading: str) -> str:
    """Return the body of a ``## {heading}`` section, or ``""`` if absent.

    Captures everything after the heading up to the next ``## `` heading
    or end-of-file. Tolerates trailing whitespace on the heading line.
    """
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s+|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(text)
    if match is None:
        return ""
    return match.group(1).strip()
