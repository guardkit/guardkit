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

# Distinct, grep-able reason emitted when the watchdog (not the duration cap)
# terminates a specialist. AC-3: hang vs cap must be distinguishable in logs
# and the review summary.
_WATCHDOG_HANG_REASON_TEMPLATE: str = "hang detected (no model activity for {seconds}s)"


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
    """

    specialist_name: str
    phase: str
    status: Literal["passed", "failed", "skipped"]
    duration_seconds: float
    result_file: Optional[Path]
    error: Optional[str]


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
                await agent_invoker._invoke_with_role(**invoke_kwargs)
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
) -> str:
    """Render the prompt the code-reviewer specialist receives.

    The agent definition (``installer/core/agents/code-reviewer.md``)
    already encodes the review checklist. This prompt only carries
    task-specific context plus the structured Phase 4 summary so the
    reviewer can ground its review in the actual test outcomes.

    The string ``"Phase 4 summary"`` is part of the prompt contract — the
    unit test introspects for it (TASK-OSI-005 AC d).
    """
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

    # Keep the prompt under ~2000 chars to match the test-orchestrator runner's
    # cap. Trim the variable-length task_context first.
    if len(prompt) > 2000:
        overflow = len(prompt) - 2000
        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]
        prompt = prompt.replace(
            task_context, trimmed_context + "\n[...truncated]"
        )
    return prompt


async def invoke_test_orchestrator(
    worktree_path: Path,
    task_id: str,
    sdk_timeout: int,
    agent_invoker: "AgentInvoker",
    cancellation_event: Optional[threading.Event] = None,
    *,
    turn: Optional[int] = None,
) -> SpecialistInvocationResult:
    """Run the Phase 4 test-orchestrator specialist under orchestrator control.

    Loads task context and a Phase 3 summary, builds a focused prompt,
    delegates SDK invocation to :func:`run_specialist`, then writes the
    ``phase_4`` block to ``.guardkit/autobuild/{task_id}/specialist_results.json``
    while preserving any pre-existing ``phase_5`` block. The function
    never raises — the autobuild turn loop owns recovery.

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

    run_result = await run_specialist(
        specialist_name="code-reviewer",
        worktree_path=Path(worktree_path),
        task_id=task_id,
        sdk_timeout=sdk_timeout,
        prompt=prompt,
        allowed_tools=["Read", "Search", "Grep"],
        agent_invoker=agent_invoker,
        cancellation_event=cancellation_event,
        turn=turn,
    )

    phase_5_block: dict[str, Any] = {
        "status": run_result.status,
        "duration_seconds": run_result.duration_seconds,
        "error": run_result.error,
        **_PHASE_5_AGENT_FIELD_DEFAULTS,
    }

    _merge_specialist_block(specialist_results_path, "phase_5", phase_5_block)

    return run_result
