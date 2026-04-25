"""Orchestrator-side specialist runners for AutoBuild Phases 4 and 5.

This module houses the orchestrator-driven specialist invocations that
replace the Player LLM's discretionary ``Task(subagent_type=...)`` calls.
Wave 1 of the OSI feature ships only the skeleton — the result dataclass
and the shared :func:`run_specialist` helper. The specialist-specific
runners (``invoke_test_orchestrator``, ``invoke_code_reviewer``) land in
TASK-OSI-004 and TASK-OSI-005 respectively and call :func:`run_specialist`
to delegate into :class:`AgentInvoker._invoke_with_role` via composition.

References:

* TASK-OSI-001 — this module skeleton.
* TASK-REV-119C1 — review that scoped the orchestrator-side invocation
  redesign and locked in the contract documented in
  ``tasks/in_progress/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md``.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from guardkit.orchestrator.agent_invoker import AgentInvoker

logger = logging.getLogger(__name__)


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

    previous_timeout = agent_invoker.sdk_timeout_seconds
    previous_cancellation = agent_invoker._cancellation_event
    if cancellation_event is not None:
        agent_invoker._cancellation_event = cancellation_event

    agent_invoker.sdk_timeout_seconds = sdk_timeout

    started_at = time.monotonic()
    error_message: Optional[str] = None
    status: Literal["passed", "failed", "skipped"] = "passed"

    try:
        await agent_invoker._invoke_with_role(
            prompt=prompt,
            agent_type=agent_type,
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            task_id=task_id,
            turn=turn,
        )
    except Exception as exc:  # noqa: BLE001 — runner must never raise
        status = "failed"
        error_message = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "run_specialist(%s) failed for %s: %s",
            specialist_name,
            task_id,
            error_message,
        )
        try:
            agent_invoker._kill_child_claude_processes()
        except Exception as cleanup_exc:  # noqa: BLE001
            logger.warning(
                "run_specialist(%s): _kill_child_claude_processes raised "
                "during failure cleanup: %s",
                specialist_name,
                cleanup_exc,
            )
    finally:
        agent_invoker.sdk_timeout_seconds = previous_timeout
        if cancellation_event is not None:
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
