"""Orchestrator-side specialist runners for AutoBuild Phases 4 and 5.

This module houses the orchestrator-driven specialist invocations that
replace the Player LLM's discretionary ``Task(subagent_type=...)`` calls.
Wave 1 of the OSI feature shipped the skeleton — the result dataclass
and the shared :func:`run_specialist` helper. Wave 2 added
:func:`invoke_test_orchestrator` (Phase 4) and Wave 3 adds
:func:`invoke_code_reviewer` (Phase 5). Both runners call
:func:`run_specialist` to delegate into
:class:`AgentInvoker._invoke_with_role` via composition.

References:

* TASK-OSI-001 — this module skeleton.
* TASK-OSI-004 — :func:`invoke_test_orchestrator`.
* TASK-OSI-005 — :func:`invoke_code_reviewer`.
* TASK-REV-119C1 — review that scoped the orchestrator-side invocation
  redesign and locked in the contract documented in
  ``tasks/in_progress/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

from guardkit.lib.pytest_summary import parse_pytest_summary

if TYPE_CHECKING:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

logger = logging.getLogger(__name__)

# Directories under the worktree root where a task markdown may live.
# rglob is used inside each so feature-grouped subfolders (e.g.
# ``tasks/in_progress/orchestrator-side-specialist-invocation/``) are
# also searched.
_TASK_SEARCH_DIRS: tuple[str, ...] = (
    "tasks/in_progress",
    "tasks/backlog",
    "tasks/in_review",
    "tasks/blocked",
)

# Defaults used when ``phase_4_summary.json`` is missing, malformed, or
# the run failed/skipped. Kept as a module constant so the same defaults
# apply to every code path that produces a phase_4 block.
_PHASE_4_AGENT_FIELD_DEFAULTS: dict[str, Any] = {
    "tests_run": 0,
    "tests_failed": 0,
    "coverage_pct": 0.0,
    "output_summary": "",
    "quality_gates_passed": False,
}

# Phase 5 agent-derived field defaults. The orchestrator-side code-reviewer
# specialist runs without ``Write`` (review must NOT modify source files), so
# the runner can't read structured review output from a sidecar file the way
# Phase 4 does with ``phase_4_summary.json``. These defaults keep the §4.1
# specialist_results.json schema well-formed while real review content flows
# through the SDK message stream / instrumentation.
_PHASE_5_AGENT_FIELD_DEFAULTS: dict[str, Any] = {
    "issues": [],
    "quality_score": 0.0,
    "recommendations": [],
    "output_summary": "Review completed by orchestrator-invoked code-reviewer.",
}

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

# TASK-PERF-SPECLAT01: per-specialist SDK-timeout ceiling for the Phase 5
# code-reviewer.
#
# The code-reviewer is an *agentic* read-only specialist (Read/Grep/Search)
# that makes many tool round-trips and never self-terminates — on a slow
# locally-served model it runs to whatever ``sdk_timeout`` it is handed. Before
# this cap existed the only bound was the wall clamp in
# ``AgentInvoker``-derived ``_cap_specialist_timeout``; with the (large) default
# ``COACH_GRACE_PERIOD_SECONDS`` reservation that left ~2130s available, so
# FEAT-9DDE run-6 turn-2's code-reviewer ran **35.6 min (2138s)** to its
# ``SDKTimeoutError`` and consumed >½ the 80-min task budget in one turn,
# foreclosing convergence with ``timeout_budget_exhausted``. This is the exact
# symmetric counterpart of ``_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS``:
# convert the SDK timeout into a graceful bounded specialist failure at the
# 10-minute mark instead of letting it eat the whole Player/Coach budget.
# Operator-tunable via ``GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP``.
_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS: int = int(
    os.environ.get("GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP", "600")
)

# TASK-FIX-SPECHANG2: per-specialist no-model-activity watchdog ceiling.
#
# The 600s duration cap above bounds a hang but does not *eliminate* it.
# Run-9 turn-2 (2026-06-07; see
# ``../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md``)
# showed the test-orchestrator make its last model call at ~90s, then ZERO
# ``/v1/responses`` POSTs for ~480s until it hit the 600s cap and
# ``SDKTimeoutError``d — a genuine agent hang that wasted ~480s of idle
# wall-clock and returned 0 results. A watchdog keyed on *no model activity*
# terminates that hang far sooner, with a clearer signal, while the 600s cap
# stays as the blunt outer backstop.
#
# Default 150s sits comfortably above turn-1's healthy continuous-call run
# (~240s total, with model calls throughout, never a 150s silent gap) so a
# normally-progressing specialist is never killed (AC-2). Operator-tunable
# via ``GUARDKIT_SPECIALIST_WATCHDOG_SECONDS``; set to ``0`` to disable.
_TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS: float = float(
    os.environ.get("GUARDKIT_SPECIALIST_WATCHDOG_SECONDS", "150")
)

# TASK-PERF-SPECLAT01: the no-activity watchdog is specialist-agnostic (its env
# var is already named ``GUARDKIT_SPECIALIST_WATCHDOG_SECONDS``). Expose a
# generic alias so both the test-orchestrator and the code-reviewer can share
# the same threshold without the misleading ``_TEST_ORCHESTRATOR_`` prefix.
_SPECIALIST_NO_ACTIVITY_WATCHDOG_SECONDS: float = (
    _TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS
)

# Distinct, grep-able reason emitted when the watchdog (not the duration cap)
# terminates a specialist. AC-3: hang vs cap must be distinguishable in logs
# and the review summary.
_WATCHDOG_HANG_REASON_TEMPLATE: str = "hang detected (no model activity for {seconds}s)"

# TASK-AB-PERTASKFG01 AC-004: Phase-4 test EXECUTION mode.
#
# Root cause of the per-task verification false-green (validation-smoke repro,
# 2026-06-18): Phase-4 ran tests by asking a hangable LLM ``test-orchestrator``
# specialist to emit ``Bash`` tool calls and self-report pass/coverage. Under
# gpt-oss the specialist emitted no parseable tool call, the no-activity
# watchdog tripped at 162s, ``tests_run=0`` was returned, and the narrative
# regex then fabricated ``all_passed/100% coverage`` (closed downstream by
# fixes #2/#3b/#4, but still a 2-3 min/turn hang). ``running tests must not be
# able to hang`` — so by default Phase-4 execution is a DETERMINISTIC
# venv-pinned ``<venv_python> -m pytest`` subprocess (no model in the loop),
# reusing the Coach's proven ``run_independent_tests`` runner so Player Phase-4
# and Coach independent verification execute the IDENTICAL pinned-pytest
# command (single source of truth — no divergence).
#
# ``subprocess`` (default): deterministic-first; the LLM specialist is used
#   ONLY as a fallback when no pytest test command is detectable (preserves
#   non-Python / npm / dotnet stacks).
# ``sdk``: emergency revert to the legacy LLM ``test-orchestrator`` specialist
#   for execution (mirrors the ``GUARDKIT_HARNESS`` revert lever).
def _resolve_phase_4_execution_mode() -> str:
    """Return the Phase-4 test-execution mode (``"subprocess"`` | ``"sdk"``).

    Reads ``GUARDKIT_PHASE4_TEST_EXECUTION`` at call time (not import time) so
    tests and operators can flip it per-invocation. Any unrecognised value
    degrades to the deterministic default.
    """
    mode = os.environ.get("GUARDKIT_PHASE4_TEST_EXECUTION", "subprocess").strip().lower()
    return mode if mode in ("subprocess", "sdk") else "subprocess"


# TASK-SBHO-001: env-tunable ceiling for the final specialist prompt string.
# Mirrors the _trim_synthesis_prompt pattern: loud truncation marker,
# WARNING log, degrade-never-raise. Default 300k chars ≈ 85k tokens.
# Applied as a backstop AFTER the per-builder seed caps (e.g. the ~2000-char
# seed cap in _build_code_reviewer_prompt).
SPECIALIST_PROMPT_MAX_CHARS_ENV = "GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS"
SPECIALIST_PROMPT_MAX_CHARS: int = int(
    os.environ.get(SPECIALIST_PROMPT_MAX_CHARS_ENV, "300000")
)


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
) -> tuple[Literal["passed", "failed"], Optional[str]]:
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
        ``("passed", None)`` on clean completion, or ``("failed", reason)``
        on a detected hang, an external cancellation, or any exception
        raised by the invocation. Never propagates.
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

    try:
        await invoke_task
    except asyncio.CancelledError:
        if hang_reason is None:
            # External cancellation (e.g. FeatureOrchestrator timeout), not
            # the watchdog — surface as a generic failed result.
            return "failed", "specialist invocation cancelled"
    except Exception as exc:  # noqa: BLE001 — runner must never raise
        if hang_reason is None:
            _reap_specialist_processes(agent_invoker, specialist_name)
            return "failed", f"{type(exc).__name__}: {exc}"

    if hang_reason is not None:
        _reap_specialist_processes(agent_invoker, specialist_name)
        return "failed", hang_reason
    if external_cancel:
        # Shared-event cancellation came from outside; the in-flight LangGraph
        # cleanup contract has already been honoured via the local forward.
        return "failed", "specialist invocation cancelled"
    return "passed", None


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
            behaves exactly as before. Not available under the no-activity
            watchdog, which does not hand its invocation's return value back;
            there ``final_message`` stays ``None`` and the caller says so.

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
    }

    # Only the direct path can hand back what the model said: the watchdog
    # path returns its own (status, error) pair and drops the invocation's
    # return value. So the extra kwarg is added only where it can be read.
    capturing = capture_final_message and not watchdog_enabled
    if capturing:
        invoke_kwargs["return_events"] = True

    try:
        if watchdog_enabled:
            # ``specialist_local_event`` is guaranteed non-None inside this
            # branch by the construction above; assert that for the type
            # checker and to document the invariant for future readers.
            assert specialist_local_event is not None
            status, error_message = await _run_specialist_with_watchdog(
                agent_invoker=agent_invoker,
                invoke_kwargs=invoke_kwargs,
                watchdog_seconds=float(no_activity_watchdog_seconds),
                specialist_local_event=specialist_local_event,
                shared_cancellation_event=cancellation_event,
                specialist_name=specialist_name,
                task_id=task_id,
            )
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


def _load_task_context(worktree_path: Path, task_id: str) -> str:
    """Best-effort read of the task markdown's Description + Acceptance.

    Searches ``tasks/{in_progress,backlog,in_review,blocked}`` recursively
    for a file whose name starts with ``{task_id}``. Returns the
    Description and Acceptance Criteria sections concatenated. Falls
    back to a one-line stub on any failure — this helper never raises.
    """
    fallback = f"Task context unavailable for {task_id}"
    try:
        task_file: Optional[Path] = None
        for rel in _TASK_SEARCH_DIRS:
            search_root = worktree_path / rel
            if not search_root.exists():
                continue
            for candidate in search_root.rglob(f"{task_id}*.md"):
                if candidate.is_file():
                    task_file = candidate
                    break
            if task_file is not None:
                break

        if task_file is None:
            return fallback

        text = task_file.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — best-effort context load
        logger.debug(
            "_load_task_context: failed to read task markdown for %s: %s",
            task_id,
            exc,
        )
        return fallback

    description = _extract_section(text, "Description")
    acceptance = _extract_section(text, "Acceptance Criteria")

    if not description and not acceptance:
        return fallback

    parts: list[str] = []
    if description:
        parts.append("## Description\n" + description.strip())
    if acceptance:
        parts.append("## Acceptance Criteria\n" + acceptance.strip())
    return "\n\n".join(parts)


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


def _load_phase_3_summary(worktree_path: Path, task_id: str) -> str:
    """Format a short bulleted summary from ``task_work_results.json``.

    Pulls ``files_created``, ``files_modified``, ``test_files_created``
    when present. Returns a sentinel string on any failure — this helper
    never raises.
    """
    fallback = "Phase 3 summary unavailable."
    try:
        # Local import avoids pulling the path module at module load
        # time and matches the existing TYPE_CHECKING convention used
        # elsewhere in this file.
        from guardkit.orchestrator.paths import TaskArtifactPaths

        results_path = TaskArtifactPaths.task_work_results_path(
            task_id, worktree_path
        )
        if not results_path.exists():
            return fallback
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — best-effort summary load
        logger.debug(
            "_load_phase_3_summary: failed to read task_work_results for %s: %s",
            task_id,
            exc,
        )
        return fallback

    if not isinstance(data, dict):
        return fallback

    lines: list[str] = []
    for label, key in (
        ("Files created", "files_created"),
        ("Files modified", "files_modified"),
        ("Test files created", "test_files_created"),
    ):
        value = data.get(key)
        if isinstance(value, list) and value:
            preview = ", ".join(str(v) for v in value[:5])
            suffix = "" if len(value) <= 5 else f" (+{len(value) - 5} more)"
            lines.append(f"- {label} ({len(value)}): {preview}{suffix}")

    if not lines:
        return fallback

    return "\n".join(lines)


def _build_test_orchestrator_prompt(
    task_id: str,
    task_context: str,
    phase_3_summary: str,
    summary_path: Path,
) -> str:
    """Render the focused prompt the test-orchestrator specialist receives.

    The agent definition (``installer/core/agents/test-orchestrator.md``)
    already encodes the execution protocol. This prompt only carries
    task-specific context plus the structured-output contract the
    orchestrator expects to read from disk afterwards.
    """
    summary_relative = summary_path.as_posix()
    prompt = (
        f"You are the test-orchestrator specialist for task {task_id}.\n\n"
        "Task context (from the task markdown):\n"
        f"{task_context}\n\n"
        "Phase 3 implementation summary (from task_work_results.json):\n"
        f"{phase_3_summary}\n\n"
        "Your job:\n"
        "1. Detect the project's test runner (pytest, npm test, dotnet test, etc.).\n"
        "2. Run the test suite for the changed code with coverage where supported.\n"
        "3. Write a structured JSON summary to:\n"
        f"   {summary_relative}\n"
        "   The JSON object MUST contain these keys:\n"
        "     - tests_run (int): total tests executed\n"
        "     - tests_failed (int): count of failing tests\n"
        "     - coverage_pct (float): line coverage as a percentage 0-100\n"
        "     - output_summary (str): one-line summary, under 200 chars\n"
        "     - quality_gates_passed (bool): true only if all gates green\n"
        "Do not duplicate your system protocol in your response — just run "
        "the suite and write the JSON file. The orchestrator reads the file "
        "directly; conversational output is not used."
    )
    # Keep the prompt under ~2000 chars per the task spec.
    if len(prompt) > 2000:
        # Trim the task_context first (largest variable section).
        overflow = len(prompt) - 2000
        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]
        prompt = prompt.replace(
            task_context, trimmed_context + "\n[...truncated]"
        )
    return prompt


def _read_phase_4_summary(summary_path: Path) -> dict[str, Any]:
    """Read ``phase_4_summary.json`` and merge over the field defaults.

    Returns a dict with all five agent-derived keys populated. Missing
    or malformed input degrades to the defaults — this helper never
    raises. Type-checks each field individually so a single bad value
    does not poison the whole dict.
    """
    merged: dict[str, Any] = dict(_PHASE_4_AGENT_FIELD_DEFAULTS)
    try:
        if not summary_path.exists():
            return merged
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — never raise
        logger.warning(
            "_read_phase_4_summary: failed to load %s: %s", summary_path, exc
        )
        return merged

    if not isinstance(data, dict):
        return merged

    for key, default in _PHASE_4_AGENT_FIELD_DEFAULTS.items():
        if key not in data:
            continue
        value = data[key]
        if isinstance(default, bool) and isinstance(value, bool):
            merged[key] = value
        elif isinstance(default, int) and not isinstance(default, bool):
            if isinstance(value, bool):
                # bool is a subclass of int — reject explicitly.
                continue
            if isinstance(value, int):
                merged[key] = value
        elif isinstance(default, float):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                merged[key] = float(value)
        elif isinstance(default, str) and isinstance(value, str):
            merged[key] = value
    return merged


def _merge_specialist_block(
    specialist_results_path: Path,
    phase_key: str,
    phase_block: dict[str, Any],
) -> None:
    """Idempotent merge-write of one phase block into ``specialist_results.json``.

    Preserves all other top-level keys when the file already exists and is
    well-formed; overwrites the file with a fresh dict on parse failure
    (logging a warning) so downstream consumers always see a usable file.
    Never raises. Used by both :func:`invoke_test_orchestrator` (writes
    ``phase_4``) and :func:`invoke_code_reviewer` (writes ``phase_5``).
    """
    try:
        specialist_results_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:  # noqa: BLE001 — never raise
        logger.warning(
            "_merge_specialist_block: failed to ensure dir %s: %s",
            specialist_results_path.parent,
            exc,
        )
        return

    existing: dict[str, Any] = {}
    if specialist_results_path.exists():
        try:
            loaded = json.loads(
                specialist_results_path.read_text(encoding="utf-8")
            )
            if isinstance(loaded, dict):
                existing = loaded
            else:
                logger.warning(
                    "_merge_specialist_block: %s did not contain a JSON "
                    "object; overwriting.",
                    specialist_results_path,
                )
        except Exception as exc:  # noqa: BLE001 — overwrite on parse fail
            logger.warning(
                "_merge_specialist_block: %s unparseable (%s); overwriting.",
                specialist_results_path,
                exc,
            )
            existing = {}

    merged = dict(existing)
    merged[phase_key] = phase_block

    try:
        specialist_results_path.write_text(
            json.dumps(merged, indent=2), encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001 — never raise
        logger.warning(
            "_merge_specialist_block: failed to write %s: %s",
            specialist_results_path,
            exc,
        )


def _write_specialist_results(
    specialist_results_path: Path,
    phase_4_block: dict[str, Any],
) -> None:
    """Phase 4 wrapper around :func:`_merge_specialist_block`.

    Preserved as a named helper so :func:`invoke_test_orchestrator` reads
    naturally; the merge mechanics live in
    :func:`_merge_specialist_block`. Never raises.
    """
    _merge_specialist_block(specialist_results_path, "phase_4", phase_4_block)


def _read_phase_4_block(specialist_results_path: Path) -> dict[str, Any]:
    """Read the ``phase_4`` block from ``specialist_results.json``.

    Returns the agent-derived fields merged over
    :data:`_PHASE_4_AGENT_FIELD_DEFAULTS`. Missing file, malformed JSON,
    missing/wrong-typed phase_4 entry all degrade to defaults — this
    helper never raises. Used by :func:`invoke_code_reviewer` to render
    the Phase 4 summary into the code-reviewer prompt.
    """
    merged: dict[str, Any] = dict(_PHASE_4_AGENT_FIELD_DEFAULTS)
    try:
        if not specialist_results_path.exists():
            return merged
        data = json.loads(specialist_results_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — never raise
        logger.warning(
            "_read_phase_4_block: failed to load %s: %s",
            specialist_results_path,
            exc,
        )
        return merged

    if not isinstance(data, dict):
        return merged
    block = data.get("phase_4")
    if not isinstance(block, dict):
        return merged

    for key, default in _PHASE_4_AGENT_FIELD_DEFAULTS.items():
        if key not in block:
            continue
        value = block[key]
        if isinstance(default, bool) and isinstance(value, bool):
            merged[key] = value
        elif isinstance(default, int) and not isinstance(default, bool):
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                merged[key] = value
        elif isinstance(default, float):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                merged[key] = float(value)
        elif isinstance(default, str) and isinstance(value, str):
            merged[key] = value
    return merged


def _build_code_reviewer_prompt(
    task_id: str,
    task_context: str,
    phase_4_summary: dict[str, Any],
    *,
    max_chars: int | None = None,
) -> str:
    """Render the prompt the code-reviewer specialist receives.

    The agent definition (``installer/core/agents/code-reviewer.md``)
    already encodes the review checklist. This prompt only carries
    task-specific context plus the structured Phase 4 summary so the
    reviewer can ground its review in the actual test outcomes.

    The string ``"Phase 4 summary"`` is part of the prompt contract — the
    unit test introspects for it (TASK-OSI-005 AC d).

    Two budget layers apply:
    1. A ~2000-char seed cap (historic, trims task_context first).
    2. An env-tunable overall backstop
       (``GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS``, default 300000) applied
       after the seed cap. This is the **primary** budget for large task
       contexts.

    Truncation is **loud**: a visible notice is inserted inside the prompt
    naming what was cut and by how much, and a WARNING is logged.
    """
    if max_chars is None:
        max_chars = SPECIALIST_PROMPT_MAX_CHARS

    summary_lines = (
        f"- tests_run: {phase_4_summary.get('tests_run', 0)}\n"
        f"- tests_failed: {phase_4_summary.get('tests_failed', 0)}\n"
        f"- coverage_pct: {phase_4_summary.get('coverage_pct', 0.0)}\n"
        f"- quality_gates_passed: "
        f"{phase_4_summary.get('quality_gates_passed', False)}\n"
        f"- output_summary: {phase_4_summary.get('output_summary', '')}"
    )

    prompt = (
        f"You are the code-reviewer specialist for task {task_id}.\n\n"
        "Task context (from the task markdown):\n"
        f"{task_context}\n\n"
        "Phase 4 summary (test-orchestrator outcome):\n"
        f"{summary_lines}\n\n"
        "Your job:\n"
        "1. Review the implementation in the worktree against the task's "
        "acceptance criteria using Read/Search/Grep.\n"
        "2. Apply the review checklist from your agent definition (build, "
        "requirements, code quality, testing, security, performance, "
        "documentation).\n"
        "3. Report findings via your normal response stream — the "
        "orchestrator records the review outcome in specialist_results.json.\n"
        "Do NOT modify source files: the Write tool is intentionally "
        "withheld from this invocation."
    )

    # Layer 1: Keep the prompt under ~2000 chars to match the
    # test-orchestrator runner's seed cap. Trim the variable-length
    # task_context first.
    if len(prompt) > 2000:
        overflow = len(prompt) - 2000
        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]
        prompt = prompt.replace(
            task_context, trimmed_context + "\n[...truncated]"
        )

    # Layer 2: Overall backstop budget (env-tunable). Applied after the
    # seed cap so the 2000-char historic behaviour is preserved when under
    # budget. Trim task_context first (it's the variable-length section).
    if len(prompt) > max_chars:
        overflow = len(prompt) - max_chars
        # Reserve space for the truncation marker (~80 chars).
        marker_reservation = 80
        overflow += marker_reservation
        # Find where task_context appears and trim it.
        task_context_marker = "Task context (from the task markdown):\n"
        ctx_start = prompt.find(task_context_marker)
        if ctx_start != -1:
            ctx_start += len(task_context_marker)
            # Find the end of the task_context (next double-newline or end)
            ctx_end = prompt.find("\n\n", ctx_start)
            if ctx_end != -1:
                original_ctx = prompt[ctx_start:ctx_end]
                keep_ctx = max(0, len(original_ctx) - overflow)
                trimmed_ctx = original_ctx[:keep_ctx]
                prompt = (
                    prompt[:ctx_start]
                    + trimmed_ctx
                    + f"\n\n[...truncated: {overflow} more chars of task "
                    f"context elided to fit within {max_chars}-char budget.]"
                    + prompt[ctx_end:]
                )
                logger.warning(
                    "specialist prompt: task_context truncated (%d chars "
                    "elided) to fit within %d-char budget",
                    overflow,
                    max_chars,
                )
            else:
                prompt = (
                    prompt[:max_chars]
                    + f"\n... [specialist prompt truncated at "
                    f"{max_chars} chars — {len(prompt) - max_chars} more "
                    f"chars not shown.]"
                )
                logger.warning(
                    "specialist prompt: hard-trimmed at %d chars (%d chars "
                    "elided)",
                    max_chars,
                    len(prompt) - max_chars,
                )
        else:
            prompt = (
                prompt[:max_chars]
                + f"\n... [specialist prompt truncated at {max_chars} chars "
                f"— {len(prompt) - max_chars} more chars not shown.]"
            )
            logger.warning(
                "specialist prompt: hard-trimmed at %d chars (%d chars "
                "elided)",
                max_chars,
                len(prompt) - max_chars,
            )

    return prompt


def _parse_pytest_counts(
    output: Optional[str],
) -> tuple[int, int, Optional[int]]:
    """Parse ``(tests_run, tests_failed, tests_skipped)`` from pytest output.

    ``tests_run`` = passed + failed + errors + xpassed + xfailed (skipped
    excluded — a skipped test executed no assertions). Best-effort: returns
    ``(0, 0, None)`` when no recognisable summary token is present. Counts are
    metadata only — the authoritative pass/fail signal is the subprocess
    return code (carried by :attr:`IndependentTestResult.tests_passed`), so a
    parse miss never changes the gate verdict. ``max`` per class tolerates
    pytest reprinting the summary.

    TASK-AB-SKIPVIS01: ``tests_skipped`` is a separate ADVISORY count, never
    folded into ``tests_run`` / ``tests_failed`` and never read by any verdict
    logic. Tri-state: ``None`` = unparseable output (unknown, never 0-coerced),
    ``0`` = summary parsed cleanly with no ``skipped`` token, ``N`` = N tests
    skipped (e.g. a worktree venv missing an optional extra silently turning
    tests into skips).

    TASK-AB-REVIEWCLEAN01 (item 1): count extraction is delegated to the
    shared ``guardkit.lib.pytest_summary`` parser. This one-shot count
    consumer keeps its historic ``(0, 0, None)`` shape on a parse miss —
    ``tests_run``/``tests_failed`` are 0-coerced here (metadata only; the
    return code is authoritative) while ``tests_skipped`` stays ``None``.
    """
    summary = parse_pytest_summary(output)
    return (summary.tests_run or 0, summary.tests_failed or 0, summary.skipped)


def _load_task_work_results(
    worktree_path: Path, task_id: str
) -> Optional[dict[str, Any]]:
    """Load the Player's ``task_work_results.json`` for test-command detection.

    The deterministic Phase-4 runner passes this to the Coach's
    ``run_independent_tests`` so it detects the same task-specific test files
    the Coach will. Best-effort: returns ``None`` (degrade to glob/diff
    detection) on any read/parse failure. Never raises.
    """
    path = (
        Path(worktree_path)
        / ".guardkit"
        / "autobuild"
        / task_id
        / "task_work_results.json"
    )
    try:
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001 — detection is best-effort
        logger.warning("[%s] _load_task_work_results failed: %s", task_id, exc)
        return None


def _test_command_source(validator: Any) -> Optional[str]:
    """Where the validator's chosen test command came from, in plain words.

    Best-effort and defensive: a stand-in validator (tests, an older build)
    need not carry the accessor, and whatever it returns must be a plain
    string before it goes into a JSON record. ``None`` when unknown.
    """
    getter = getattr(validator, "test_command_source", None)
    if not callable(getter):
        return None
    try:
        source = getter()
    except Exception:  # noqa: BLE001 — forensic metadata never breaks a run
        return None
    return source if isinstance(source, str) and source else None


def _ran_the_declaration(validator: Any) -> bool:
    """Whether the validator ran the repository's DECLARED command.

    Best-effort and defensive, like :func:`_test_command_source`: a stand-in
    validator need not carry the accessor. ``False`` when unknown — which
    leaves the leg's verdict exactly what it has always been.
    """
    getter = getattr(validator, "ran_the_repository_declaration", None)
    if not callable(getter):
        return False
    try:
        return bool(getter())
    except Exception:  # noqa: BLE001 — a verdict never depends on metadata
        return False


def _base_failing(validator: Any) -> tuple[bool, list, Optional[str]]:
    """What the base was already failing, and where that was learned.

    ``(base_known, failing_ids, source_in_plain_words)``; ``(False, [], None)``
    when the validator cannot answer.
    """
    getter = getattr(validator, "base_failing_tests", None)
    if not callable(getter):
        return False, [], None
    try:
        known, ids, source = getter()
        return bool(known), list(ids), str(source)
    except Exception:  # noqa: BLE001 — forensic metadata never breaks a run
        return False, [], None


def _compare_against_base(
    validator: Any,
    result: Any,
    task_work_results: Optional[dict[str, Any]],
) -> Optional[Any]:
    """The zero-net-new reading of a red whole-suite run, or ``None``.

    ``None`` means "no reading available" — an older validator, a stack whose
    failing test names cannot be parsed, or an exception — and the leg then
    reports the red exactly as it does today. Never turns a red leg green by
    accident: only a positive comparison saying ``passes`` does that.
    """
    getter = getattr(validator, "compare_suite_against_base", None)
    if not callable(getter):
        return None
    try:
        return getter(result, task_work_results)
    except Exception as exc:  # noqa: BLE001 — fail closed to the real verdict
        logger.debug("zero-net-new comparison skipped (%s)", exc)
        return None


def _run_deterministic_phase_4(
    worktree_path: Path,
    task_id: str,
    agent_invoker: "AgentInvoker",
    *,
    sdk_timeout: int,
    turn: Optional[int],
    wave_size: int = 1,
    component: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Execute Phase-4 tests deterministically and return a phase_4 block.

    TASK-AB-PERTASKFG01 AC-004. Reuses the Coach's
    ``CoachValidator(coach_test_execution="subprocess").run_independent_tests``
    so Player Phase-4 execution and Coach independent verification run the
    IDENTICAL command — no LLM in the loop, so it cannot hang. That identity
    is the point of this function, and it survives the change below because
    both sides ask the SAME method for the command.

    WHAT COMMAND. Since Rich's ruling of 2026-09-09, a repository that has
    declared how its tests are run (``.guardkit/config.yaml``,
    ``toolchain.test``) has that command run here — the same declaration the
    merge-ready checkpoint has always honoured. A repository that declares
    nothing is exactly what it was: the venv-pinned ``<venv python> -m
    pytest`` on the task's own test files, same argv, same parsing, same
    fallbacks.

    WHAT IT COSTS, said plainly: a declared command is usually the whole
    suite, where the old guess ran only the task's own tests, so a leg can now
    go red for a defect somebody else left behind. That is the repository's
    own declaration and the estate's law. Because a red leg is only useful if
    a person can see what ran, the record below carries the command and where
    it came from ("repository toolchain declaration") beside the interpreter
    that was already there. The declared command may also be a script rather
    than a pytest run, and slower; it stays inside the same phase timeout, and
    a timeout is reported exactly as one is today (an absent signal, never a
    pass).

    Returns
    -------
    Optional[dict]
        A phase_4 block (``status`` ∈ {passed, failed} + the agent-derived
        fields) when a deterministic run produced a usable signal, or ``None``
        when no pytest test command could be detected, the runner is
        unavailable, or it raised — in which case the caller falls back to the
        LLM ``test-orchestrator`` specialist so non-Python / npm / dotnet stacks
        (and unexpected runner errors) keep their existing behaviour.

    Result mapping is absence-of-failure-safe
    (``.claude/rules/absence-of-failure-is-not-success.md``): an ABSENT oracle
    signal (collection/conftest import failure, runner absent, timeout) is
    NEVER a pass — it maps to ``status="failed"`` so the #2 quality_gates
    reconcile fires against any narrative false-green and Phase 5 is skipped.
    """
    # Lazy import: avoid any import-time coupling between this module and the
    # quality-gates package (no cycle today, but keep it loose).
    try:
        from guardkit.orchestrator.coach_verification import (
            InterpreterResolutionError,
        )
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )
    except Exception as exc:  # noqa: BLE001 — degrade to the specialist path
        logger.warning(
            "[%s] deterministic Phase-4 unavailable (CoachValidator import "
            "failed: %s); falling back to test-orchestrator specialist",
            task_id,
            exc,
        )
        return None

    # Cap the subprocess timeout at the same ceiling as the LLM specialist so a
    # pathological suite cannot exceed the Player/Coach budget; on timeout the
    # runner reports signal_absent -> the absent branch below (never a pass).
    test_timeout = min(int(sdk_timeout), _TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS)
    venv_python = getattr(agent_invoker, "_venv_python", None)

    start = time.monotonic()
    try:
        validator = CoachValidator(
            worktree_path=str(worktree_path),
            task_id=task_id,
            coach_test_execution="subprocess",  # never an LLM turn — cannot hang
            test_timeout=test_timeout,
            venv_python=venv_python,
            # WS3-S1 Q1 SPLIT: this is THE independent-test verdict path inside
            # autobuild — an unresolved interpreter here is exactly the poison
            # the hard-abort exists to stop.
            in_autobuild_context=True,
            turn=turn or 1,
            # TASK-AB-NPDET01: the non-Python whole-suite guard needs the real
            # wave size — without it the runner believes wave_size=1 and would
            # run a parallel wave's sibling tests.
            wave_size=wave_size,
            # TASK-AB-BASETEMP01: label the per-run pytest --basetemp so a
            # leaked tmp dir is attributable to the deterministic Phase-4
            # runner rather than the Coach's own independent run.
            basetemp_context="phase4",
            # PER-COMPONENT SEAM — HONOURED HERE (phase-4 threading lane).
            # The task's component selector now rides the chain
            # ``autobuild._execute_turn`` -> ``invoke_test_orchestrator`` ->
            # here, so a component task's Phase-4 block runs THAT component's
            # declared command in THAT component's declared directory — the
            # same oracle the Coach's own ``run_independent_tests`` uses, so
            # the Player's narrative and the Coach's verdict can no longer
            # disagree about which product was tested.
            #
            # ``component=None`` (every single-toolchain repo, and every task
            # that names no component) leaves ``CoachValidator._component``
            # falsy: the declared-component rung in ``_detect_test_command`` is
            # not entered and ``_component_run_cwd`` returns the worktree
            # unchanged — the pre-existing root path, byte for byte.
            #
            # A component the repo does not declare is NEVER silently degraded
            # to the root oracle: the Coach records a detection ABSENCE, which
            # ``run_independent_tests`` returns as ``signal_absent`` and the
            # absent branch below maps to ``status="failed"``. Absence of
            # failure is not success.
            component=component,
        )
        task_work_results = _load_task_work_results(Path(worktree_path), task_id)
        result = validator.run_independent_tests(
            task_work_results=task_work_results, turn=turn
        )
    except InterpreterResolutionError:
        # WS3-S1 Q1 SPLIT: an interpreter-resolution hard-abort must NOT
        # degrade to the LLM test-orchestrator specialist (which would run
        # pytest under the same broken interpreter and re-open the DD4F
        # soft-fail). Propagate so the run fails loud with the named
        # remediation.
        raise
    except Exception as exc:  # noqa: BLE001 — degrade to the specialist path
        logger.warning(
            "[%s] deterministic Phase-4 run raised (%s); falling back to "
            "test-orchestrator specialist",
            task_id,
            exc,
        )
        return None

    duration = time.monotonic() - start
    summary = (result.test_output_summary or "")[:200]
    command_source = _test_command_source(validator)
    logger.info(
        "[%s] deterministic Phase-4 test command: %s (source: %s)",
        task_id,
        result.test_command,
        command_source or "unknown",
    )

    # No pytest test command detected (``run_independent_tests`` returns the
    # "skipped" sentinel when ``_detect_test_command`` finds nothing). This is
    # NOT an absent oracle — there is simply nothing for the deterministic
    # runner to execute. Return None so the caller falls back to the LLM
    # ``test-orchestrator`` specialist, preserving non-Python / npm / dotnet
    # stacks and the shared-worktree "no task-specific tests" path unchanged.
    # The deterministic runner only TAKES OVER when there ARE pytest tests to
    # run — exactly the case the hang was observed in.
    if result.test_command == "skipped" and not result.signal_absent:
        return None

    # ABSENT signal: the oracle ran but produced NO verdict (collection/conftest
    # import failure, runner absent, returncode-5 no-tests-collected, timeout).
    # absence-of-failure: NEVER a pass. status="failed" arms the #2 reconcile
    # and skips Phase 5. (This is the validation-smoke conftest-import repro that
    # motivated TASK-AB-PERTASKFG01.)
    if result.signal_absent:
        # TASK-ABFIX-010 (W2): carry an explicit ``signal_absent`` boolean
        # (not just the error-string prefix) so the downstream
        # narrative-false-green reconciliation in ``agent_invoker`` can branch
        # on it deterministically and keep the absent signal as ``None``
        # (UNKNOWN) rather than coercing it to an explicit ``False``. See
        # ``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.
        return {
            "status": "failed",
            "duration_seconds": duration,
            "error": f"absent test signal (deterministic Phase 4): {summary[:160]}",
            "signal_absent": True,
            # TASK-AB-ZEROTESTLOUD01 (AC-001): machine-readable marker — a
            # Phase-4 record with ZERO collected tests is VERIFIER
            # INFRASTRUCTURE, never a Player-quality signal. Schema-additive
            # (downstream consumers match these keys, never feedback text),
            # with the resolved interpreter and probed command so the
            # "which interpreter did the verifier actually run?" forensic
            # dig is one grep (FEAT-ABL-005 run 4 / TASK-AB-RESUMEVENV01).
            "verifier_infrastructure": True,
            "resolved_interpreter": result.resolved_interpreter,
            "test_command": result.test_command,
            "test_command_source": command_source,
            **{**_PHASE_4_AGENT_FIELD_DEFAULTS, "output_summary": summary},
        }

    tests_run, tests_failed, tests_skipped = _parse_pytest_counts(
        result.raw_output
    )

    # ZERO NET-NEW, NOT ALL-GREEN (Rich's second ruling, 2026-09-09).
    #
    # No real repository is all green — forge's suite carries about thirty
    # base failures, guardkit's eleven to fourteen, all triaged — so a leg
    # that demanded a green suite would fail on every red repository for
    # ever. The bar is instead: nothing NEWLY red. A failure the branch's
    # base already had is not this leg's failure.
    #
    # It applies ONLY when the command came from the repository's own
    # declaration, because only then is the leg running the whole suite and
    # therefore exposed to somebody else's defect. A run of the task's own
    # test files is judged exactly as it always was: every failure in it is
    # this task's. That is why a repository declaring nothing keeps today's
    # verdict, byte for byte, as well as today's argv.
    #
    # The base's failing set is not a new mechanism: it is the build's
    # measured wave-0 baseline and the repository's own known-failure
    # ledger, the two the estate already keeps and the Coach's own gate
    # already subtracts. See
    # ``CoachValidator.compare_suite_against_base`` for what happens when
    # neither is on record.
    declared_run = _ran_the_declaration(validator)
    base_known, base_failing_ids, base_source = (
        _base_failing(validator) if declared_run else (False, [], None)
    )
    comparison = (
        _compare_against_base(validator, result, task_work_results)
        if declared_run
        else None
    )

    stale_note: Optional[str] = None
    if result.tests_passed and base_known and base_failing_ids:
        stale_note = (
            f"{len(base_failing_ids)} test(s) recorded as failing on the base "
            f"did not fail here — the record has gone stale in the good "
            f"direction (or this command did not select them). The base's "
            f"failing set came from {base_source}."
        )
        logger.info("[%s] %s", task_id, stale_note)

    if result.tests_passed:
        # returncode 0 (and not signal_absent, so not the returncode-5
        # no-tests-collected case) => >=1 test ran and passed. coverage_pct is
        # left at the default: the deterministic run is a pass/fail oracle, not
        # a coverage measurement (parity with the Coach). On a pass the #2
        # reconcile does NOT fire, so the Player's narrative coverage is
        # untouched — no fabricated coverage enters the gate from here.
        return {
            "status": "passed",
            "duration_seconds": duration,
            "error": None,
            "tests_run": tests_run,
            "tests_failed": 0,
            # TASK-AB-SKIPVIS01: advisory only — no verdict logic reads it.
            "tests_skipped": tests_skipped,
            # TASK-AB-RESUMEVENV01 (AC-003): forensic evidence only.
            "resolved_interpreter": result.resolved_interpreter,
            # Which command ran, and why that one. Forensic only — no verdict
            # rule reads either — but a person reading this record should not
            # have to guess whether the repository's declaration or the venv
            # default produced it.
            "test_command": result.test_command,
            "test_command_source": command_source,
            # Where the base's failing set came from, so the forensic
            # question "what did the verifier forgive, and on whose word?"
            # is one grep. ``None`` when the leg ran the task's own tests
            # and nothing was forgiven or could be.
            "baseline_source": base_source,
            # A3: a test the base was failing that PASSES now is never a
            # failure — it is one plain line saying the record has gone
            # stale in the good direction.
            "stale_base_entries": list(base_failing_ids) if base_known else [],
            "baseline_note": stale_note,
            "coverage_pct": 0.0,
            "output_summary": summary,
            "quality_gates_passed": True,
        }

    # ran-and-failed. Before this is a verdict, ask the zero-net-new
    # question — but only for a declared whole-suite run, and only when the
    # comparison could be made at all.
    if comparison is not None and comparison.passes:
        # Every failure was already failing on the base, and the run visibly
        # did work (at least one test passed). Nothing NEW is red, so the leg
        # passes and says in words how many failures it forgave and on whose
        # word. The failing tests themselves are somebody's to fix — the
        # merge door and the ledger's own review date are where that happens,
        # not here.
        logger.info(
            "[%s] deterministic Phase-4 PASSES on zero net-new: %s",
            task_id,
            comparison.note,
        )
        return {
            "status": "passed",
            "duration_seconds": duration,
            "error": None,
            "tests_run": tests_run,
            # Nothing is charged to this leg; the three real numbers are
            # carried beside it rather than hidden behind a zero.
            "tests_failed": 0,
            "tests_skipped": tests_skipped,
            "resolved_interpreter": result.resolved_interpreter,
            "test_command": result.test_command,
            "test_command_source": command_source,
            "failures_total": comparison.failures_total,
            "failures_inherited": comparison.inherited,
            "failures_new": 0,
            "new_failing_tests": [],
            "stale_base_entries": list(comparison.stale_base_entries),
            "baseline_source": comparison.base_source,
            "baseline_note": comparison.note,
            "coverage_pct": 0.0,
            "output_summary": f"{comparison.note} {summary}"[:400],
            "quality_gates_passed": True,
        }

    # A genuine failure verdict. When the comparison could be made, the leg
    # names ONLY what is newly red: a red leg naming twenty failures of which
    # nineteen are inherited is a leg nobody reads; "one test is newly
    # failing: <id>" is one that gets fixed.
    if comparison is not None:
        named = ", ".join(comparison.new_failures[:10]) or "(none named)"
        error = (
            f"tests failed (deterministic Phase 4): "
            f"{comparison.failures_total} failed, {comparison.inherited} "
            f"already failing on the base, {len(comparison.new_failures)} "
            f"newly failing: {named}"
        )
    else:
        error = f"tests failed (deterministic Phase 4): {summary[:160]}"

    return {
        "status": "failed",
        "duration_seconds": duration,
        "error": error[:400],
        "tests_run": tests_run,
        "tests_failed": tests_failed or max(1, tests_run),
        # TASK-AB-SKIPVIS01: advisory only — no verdict logic reads it.
        "tests_skipped": tests_skipped,
        # TASK-AB-RESUMEVENV01 (AC-003): forensic evidence only. NOTE: no
        # ``verifier_infrastructure`` marker here — a ran-and-failed verdict
        # is a genuine Player signal (TASK-AB-ZEROTESTLOUD01 AC-005).
        "resolved_interpreter": result.resolved_interpreter,
        # A red leg must say WHICH command went red and where it came from:
        # a whole declared suite can fail on somebody else's defect, and that
        # reads very differently from the task's own tests failing.
        "test_command": result.test_command,
        "test_command_source": command_source,
        # THE THREE NUMBERS a person needs from a red whole-suite leg: how
        # many failed, how many the base already had, how many are new — and
        # the new ones by name. Absent (``None``/empty) when the leg ran the
        # task's own tests, where every failure is this task's by definition.
        "failures_total": comparison.failures_total if comparison else None,
        "failures_inherited": comparison.inherited if comparison else None,
        "failures_new": (
            len(comparison.new_failures) if comparison else None
        ),
        "new_failing_tests": (
            list(comparison.new_failures) if comparison else []
        ),
        "stale_base_entries": (
            list(comparison.stale_base_entries) if comparison else []
        ),
        "baseline_source": comparison.base_source if comparison else base_source,
        "baseline_note": comparison.note if comparison else None,
        "coverage_pct": 0.0,
        "output_summary": summary,
        "quality_gates_passed": False,
    }


async def invoke_test_orchestrator(
    worktree_path: Path,
    task_id: str,
    sdk_timeout: int,
    agent_invoker: "AgentInvoker",
    cancellation_event: Optional[threading.Event] = None,
    *,
    turn: Optional[int] = None,
    wave_size: int = 1,
    component: Optional[str] = None,
) -> SpecialistInvocationResult:
    """Run the Phase 4 test-orchestrator specialist under orchestrator control.

    Loads task context and a Phase 3 summary, builds a focused prompt,
    delegates SDK invocation to :func:`run_specialist`, then writes the
    ``phase_4`` block to ``.guardkit/autobuild/{task_id}/specialist_results.json``
    while preserving any pre-existing ``phase_5`` block. The function
    never raises for recoverable specialist failures — the autobuild turn
    loop owns recovery. The one exception is
    :class:`~guardkit.orchestrator.coach_verification.InterpreterResolutionError`
    from the deterministic Phase-4 runner: inside an autobuild run an
    unresolved interpreter is a HARD-ABORT (Q1 SPLIT, WS3-S1) that MUST
    propagate — falling back to the LLM specialist would run pytest under the
    same broken interpreter and re-open the DD4F soft-fail.

    Args:
        worktree_path: Worktree the specialist operates against.
        task_id: AutoBuild task ID; used for path resolution and prompt
            framing.
        sdk_timeout: Per-invocation SDK timeout in seconds.
        agent_invoker: :class:`AgentInvoker` whose ``_invoke_with_role``
            performs the SDK call (via :func:`run_specialist`).
        cancellation_event: Optional :class:`threading.Event` that
            signals cancellation to the SDK monitor.
        turn: Optional autobuild turn number forwarded for instrumentation.
        wave_size: Number of tasks in the current parallel wave; forwarded to
            the deterministic runner's non-Python whole-suite guard.
        component: Optional per-component selector from the task's
            frontmatter. When set, the deterministic Phase-4 runner resolves
            THAT component's declared test command and directory, so an app
            task is judged by its own toolchain rather than the repo root's.
            ``None`` (the default, and every single-toolchain repo) preserves
            the root path exactly.

    Returns:
        The :class:`SpecialistInvocationResult` produced by
        :func:`run_specialist`, unmodified. The on-disk
        ``specialist_results.json`` reflects the run regardless of
        outcome.
    """
    autobuild_dir = (
        Path(worktree_path) / ".guardkit" / "autobuild" / task_id
    )
    summary_path = autobuild_dir / "phase_4_summary.json"
    specialist_results_path = autobuild_dir / "specialist_results.json"

    # TASK-AB-PERTASKFG01 AC-004: deterministic-first Phase-4 execution.
    # Run tests as a venv-pinned subprocess (no hangable LLM turn) by default;
    # the legacy ``test-orchestrator`` specialist is reached only when this is
    # explicitly reverted (``GUARDKIT_PHASE4_TEST_EXECUTION=sdk``) or when no
    # pytest test command is detectable (non-Python stack safety valve).
    #
    # PER-COMPONENT PIN (mirrors ``CoachValidator.run_independent_tests``'s
    # ``component_pinned_subprocess`` law): the LLM ``test-orchestrator``
    # specialist runs with the WORKTREE ROOT as its cwd and is handed no
    # component directory, so under an ``sdk`` revert a component task would
    # silently run the wrong product's tests from the wrong directory. A named
    # component therefore FORCES the deterministic path — the only path where
    # the component's declared cwd is honoured — and says so out loud.
    _mode = _resolve_phase_4_execution_mode()
    if component and _mode == "sdk":
        logger.warning(
            "[%s] Component %r selected: forcing the deterministic SUBPROCESS "
            "Phase-4 path despite GUARDKIT_PHASE4_TEST_EXECUTION=sdk. The SDK "
            "specialist runs with the worktree root as cwd and would test the "
            "wrong component.",
            task_id,
            component,
        )
        _mode = "subprocess"
    if _mode == "subprocess":
        det_block = _run_deterministic_phase_4(
            worktree_path=Path(worktree_path),
            task_id=task_id,
            agent_invoker=agent_invoker,
            sdk_timeout=sdk_timeout,
            turn=turn,
            wave_size=wave_size,
            component=component,
        )
        if det_block is not None:
            _write_specialist_results(specialist_results_path, det_block)
            logger.info(
                "[%s] Phase-4 executed deterministically (subprocess pytest): "
                "status=%s tests_run=%s tests_failed=%s in %.1fs",
                task_id,
                det_block.get("status"),
                det_block.get("tests_run"),
                det_block.get("tests_failed"),
                det_block.get("duration_seconds", 0.0),
            )
            return SpecialistInvocationResult(
                specialist_name="test-orchestrator",
                phase="4",
                status=det_block["status"],
                duration_seconds=float(det_block.get("duration_seconds", 0.0)),
                result_file=specialist_results_path,
                error=det_block.get("error"),
            )
        if component:
            # For a component task the runner cannot reach here by "no test
            # command detected" — a named component always resolves to either
            # a declared command or a LOUD absence (status="failed"). Reaching
            # here means the runner itself was unavailable or raised, and the
            # LLM specialist that follows runs with the worktree ROOT as cwd.
            # Say so: the resulting Phase-4 block is the root oracle, not this
            # component's.
            logger.warning(
                "[%s] deterministic Phase-4 unavailable for component %r; the "
                "test-orchestrator specialist that follows runs from the "
                "worktree ROOT, so its block is NOT this component's oracle.",
                task_id,
                component,
            )
        logger.info(
            "[%s] deterministic Phase-4 found no detectable test command; "
            "falling back to the test-orchestrator specialist",
            task_id,
        )

    task_context = _load_task_context(Path(worktree_path), task_id)
    phase_3_summary = _load_phase_3_summary(Path(worktree_path), task_id)
    prompt = _build_test_orchestrator_prompt(
        task_id=task_id,
        task_context=task_context,
        phase_3_summary=phase_3_summary,
        summary_path=summary_path,
    )

    # TASK-FIX-SPECHANG: cap the caller-supplied sdk_timeout at the
    # test-orchestrator-specific ceiling so a polling specialist cannot
    # burn the full Player/Coach budget.
    capped_sdk_timeout = min(sdk_timeout, _TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS)
    if capped_sdk_timeout < sdk_timeout:
        logger.info(
            "[%s] test-orchestrator sdk_timeout capped from %ds to %ds "
            "(TASK-FIX-SPECHANG)",
            task_id,
            sdk_timeout,
            capped_sdk_timeout,
        )

    run_result = await run_specialist(
        specialist_name="test-orchestrator",
        worktree_path=Path(worktree_path),
        task_id=task_id,
        sdk_timeout=capped_sdk_timeout,
        prompt=prompt,
        allowed_tools=["Read", "Write", "Bash", "Search"],
        agent_invoker=agent_invoker,
        cancellation_event=cancellation_event,
        turn=turn,
        # TASK-FIX-SPECHANG2: terminate a genuinely hung test-orchestrator
        # (no /v1/responses traffic for N seconds) well before the blunt
        # capped duration timeout fires.
        no_activity_watchdog_seconds=_TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS,
    )

    if run_result.status == "passed":
        agent_fields = _read_phase_4_summary(summary_path)
    else:
        agent_fields = dict(_PHASE_4_AGENT_FIELD_DEFAULTS)

    phase_4_block: dict[str, Any] = {
        "status": run_result.status,
        "duration_seconds": run_result.duration_seconds,
        "error": run_result.error,
        **agent_fields,
    }

    _write_specialist_results(specialist_results_path, phase_4_block)

    return run_result


async def invoke_code_reviewer(
    worktree_path: Path,
    task_id: str,
    phase4_result: SpecialistInvocationResult,
    sdk_timeout: int,
    agent_invoker: "AgentInvoker",
    cancellation_event: Optional[threading.Event] = None,
    *,
    turn: Optional[int] = None,
) -> SpecialistInvocationResult:
    """Run the Phase 5 code-reviewer specialist under orchestrator control.

    Loads task context plus the Phase 4 outcome from
    ``specialist_results.json``, builds a prompt that includes a structured
    "Phase 4 summary" section, delegates SDK invocation to
    :func:`run_specialist`, then appends a ``phase_5`` block to
    ``.guardkit/autobuild/{task_id}/specialist_results.json`` while
    preserving the existing ``phase_4`` block. The function never raises
    into the caller on SDK / tool failures — the autobuild turn loop owns
    recovery.

    Defensive guard: if ``phase4_result.status != "passed"`` the function
    raises :class:`ValueError`. The turn-loop wiring (TASK-OSI-006) is
    responsible for skipping this runner when Phase 4 failed; this assert
    catches caller bugs early rather than silently writing a phase_5
    block based on a stale Phase 4 outcome.

    The orchestrator-side ``code-reviewer`` runs without ``Write``: review
    output goes to the ``phase_5`` block written by this runner, not via
    the agent's tools (review must NOT modify source files). Per-field
    semantic content (issues, recommendations, quality_score) defaults to
    placeholders — real review content flows through the SDK message
    stream and instrumentation. See
    :data:`_PHASE_5_AGENT_FIELD_DEFAULTS`.

    Args:
        worktree_path: Worktree the specialist reviews.
        task_id: AutoBuild task ID; used for path resolution and prompt
            framing.
        phase4_result: Outcome of :func:`invoke_test_orchestrator`. Must
            have ``status == "passed"`` — see defensive guard above.
        sdk_timeout: Per-invocation SDK timeout in seconds.
        agent_invoker: :class:`AgentInvoker` whose ``_invoke_with_role``
            performs the SDK call (via :func:`run_specialist`).
        cancellation_event: Optional :class:`threading.Event` that signals
            cancellation to the SDK monitor inside ``_invoke_with_role``.
        turn: Optional autobuild turn number forwarded for instrumentation.

    Returns:
        :class:`SpecialistInvocationResult` with ``phase="5"``. The
        on-disk ``specialist_results.json`` reflects the run regardless
        of outcome (success writes a passed phase_5 block; SDK failure
        writes a failed phase_5 block with ``error`` populated and the
        existing phase_4 block preserved).

    Raises:
        ValueError: When ``phase4_result.status != "passed"``. Caller bug.
    """
    if phase4_result.status != "passed":
        raise ValueError(
            "invoke_code_reviewer requires phase4_result.status='passed' "
            f"(got '{phase4_result.status}'). The turn-loop wiring "
            "(TASK-OSI-006) is responsible for skipping the code-reviewer "
            "when Phase 4 did not pass; this guard catches caller bugs."
        )

    autobuild_dir = Path(worktree_path) / ".guardkit" / "autobuild" / task_id
    specialist_results_path = autobuild_dir / "specialist_results.json"

    task_context = _load_task_context(Path(worktree_path), task_id)
    phase_4_summary = _read_phase_4_block(specialist_results_path)
    prompt = _build_code_reviewer_prompt(
        task_id=task_id,
        task_context=task_context,
        phase_4_summary=phase_4_summary,
    )

    # TASK-PERF-SPECLAT01: cap the caller-supplied sdk_timeout at the
    # code-reviewer-specific ceiling so an agentic review pass on a slow model
    # cannot burn the full Player/Coach budget (symmetric with the Phase 4
    # test-orchestrator cap).
    capped_sdk_timeout = min(sdk_timeout, _CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS)
    if capped_sdk_timeout < sdk_timeout:
        logger.info(
            "[%s] code-reviewer sdk_timeout capped from %ds to %ds "
            "(TASK-PERF-SPECLAT01)",
            task_id,
            sdk_timeout,
            capped_sdk_timeout,
        )

    run_result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=Path(worktree_path),
        task_id=task_id,
        sdk_timeout=capped_sdk_timeout,
        prompt=prompt,
        allowed_tools=["Read", "Search", "Grep"],
        agent_invoker=agent_invoker,
        cancellation_event=cancellation_event,
        turn=turn,
        # TASK-PERF-SPECLAT01: terminate a genuinely hung code-reviewer
        # (no /v1/responses traffic for N seconds) well before the capped
        # duration timeout fires — same protection the test-orchestrator has.
        no_activity_watchdog_seconds=_SPECIALIST_NO_ACTIVITY_WATCHDOG_SECONDS,
    )

    phase_5_block: dict[str, Any] = {
        "status": run_result.status,
        "duration_seconds": run_result.duration_seconds,
        "error": run_result.error,
        **_PHASE_5_AGENT_FIELD_DEFAULTS,
    }

    _merge_specialist_block(specialist_results_path, "phase_5", phase_5_block)

    return run_result
