"""AgentInvoker handles Claude Agents SDK invocation for Player and Coach agents."""

import asyncio
import json
import logging
import os
import re
import signal
import threading
import time
from contextlib import aclosing, asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Literal, Optional, Set, Tuple, Union

if TYPE_CHECKING:
    from guardkit.orchestrator.autobuild import DesignContext
    # TASK-HMIG-008R Part C: bundle reference avoids the circular import that
    # would result from a runtime import of
    # guardkit.orchestrator.quality_gates.coach_evidence — the quality_gates
    # package __init__ transitively imports agent_invoker via pre_loop →
    # task_work_interface. Runtime values are duck-typed.
    from guardkit.orchestrator.quality_gates.coach_evidence import (
        CoachEvidenceBundle,
    )

from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
    PlanNotFoundError,
    PlayerReportInvalidError,
    PlayerReportNotFoundError,
    RateLimitExceededError,
    SDKTimeoutError,
    TaskStateError,
    TaskWorkResult,
)
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.llm_instrumentation import (
    classify_error,
    detect_provider,
    extract_token_usage,
    measure_latency,
    sanitise_tool_name,
)
from guardkit.orchestrator.instrumentation.redaction import SecretRedactor
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent, ToolExecEvent
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.prompts import load_protocol
from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    HonestyVerification,
    format_verification_context,
)
from guardkit.orchestrator.schemas import (
    CompletionPromise,
    CriterionVerification,
    CriterionStatus,
    VerificationResult,
)

# TASK-HMIG-006 Phase 3b: HarnessAdapter substrate seam.
# Pure-Python, SDK-free imports — the concrete ClaudeSDKHarness lazily
# imports claude_agent_sdk inside its own invoke() (matches existing
# test-fixture behaviour at tests/orchestrator/instrumentation/
# test_llm_call_events.py which patches sys.modules["claude_agent_sdk"]).
# See Design Decision D-3: orchestrator-side concerns (heartbeat,
# cancel monitor, sdk_debug, llm.call event) stay inline.
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    HarnessEvent,
    ResultMessageEvent,
    ToolResultEvent,
    ToolUseEvent,
    select_harness,
)

# TASK-FIX-RWOP1.3.1: Agent-invocations validation on the producer path.
# task-work.md Step 6.5 declares validate_agent_invocations as "the ONLY
# checkpoint that prevents false reporting". Folding it into
# _write_task_work_results is the producer-runs-gate pattern from
# TASK-FIX-3C9D: without this wiring the Player can emit a results file
# claiming any phases were completed and no deterministic check catches it
# before Coach reads the file.
from installer.core.commands.lib import (
    AgentInvocationTracker,
    validate_agent_invocations,
    ValidationError as AgentInvocationValidationError,
)
from installer.core.commands.lib.agent_invocation_validator import (
    get_expected_phases,
    identify_missing_phases,
)

# TASK-FIX-RWOP1.3.2: Plan-audit gate on the producer path. The
# deterministic auditor in installer.core.commands.lib.plan_audit compares
# the saved plan against actual files/deps/LOC; without this wire the
# `plan_audit` block in task_work_results.json is the Player's self-report
# and can trivially claim "violations: []" while the worktree has extras.
# The producer fold makes Coach see the auditor's verdict, not the Player's.
from installer.core.commands.lib.phase_execution import (
    execute_phase_5_5_plan_audit,
)

# TASK-FIX-RWOP1.4a: Assumption-confidence warn-mode gate on the producer
# path. feature-spec.md:337 claims the Coach verifies low-confidence
# assumptions before accepting a spec, but before this wire no producer
# wrote a Coach-consumable verdict — same "runner without producer" shape
# as TASK-FIX-RWOP1.3.1 (R5 precedent). Coach surfaces the block as a
# non-blocking warning (warn-mode per TASK-FIX-RWOP1.4 Part A).
#
# The checker is imported lazily inside _write_task_work_results because a
# top-level import triggers guardkit.orchestrator.quality_gates.__init__,
# which pulls in pre_loop → task_work_interface → agent_invoker (circular).

# Logger for agent invocations
logger = logging.getLogger(__name__)

# Reverse-map TaskWorkStreamParser phase keys (phase_2.5) to the validator's
# canonical phase IDs (2.5B). The parser regex caps at \d+(?:\.\d+)?, so
# "Phase 2.5B" in task-work output becomes "phase_2.5" in the parser —
# this map reconstructs the ID that get_expected_phase_list('standard')
# emits in agent_invocation_validator.
_PARSER_PHASE_TO_VALIDATOR_PHASE = {
    "phase_2": "2",
    "phase_2.5": "2.5B",
    "phase_2.7": "2.7",
    "phase_3": "3",
    "phase_4": "4",
    "phase_5": "5",
}


# =========================================================================
# Orchestrator-managed-path filter (TASK-FIX-PCN)
# =========================================================================
#
# Sibling of the ``state_transitions.json`` filter at
# :py:meth:`AgentInvoker._create_player_report_from_task_work` (TASK-FIX-1B4C
# Layer 3'). Where that filter handles *recorded* state-bridge moves, this
# pattern-based filter handles the broader class of orchestrator-owned
# paths that any post-turn ``git diff --name-only`` enrichment will sweep
# into the Player report:
#
#   * ``.guardkit/autobuild/<TASK-ID>/*.json`` — per-task sidecars
#     (player_turn_N.json, coach_turn_N.json, turn_state_*.json,
#     state_transitions.json)
#   * ``.guardkit/autobuild/<FEAT-ID>/*.{jsonl,md,json}`` — feature-level
#     autobuild metadata
#   * ``.guardkit/bootstrap_state.json`` — bootstrap phase state
#   * ``tasks/{backlog,design_approved,in_progress,in_review,completed}/...``
#     — task-scaffold markdown files the orchestrator copies during setup
#     (including subfolder variants under feature folders)
#
# These paths are NOT gitignored (so TASK-FIX-IGNR's gitignored→should_fix
# demotion does not apply) and they DO exist on disk (so file-existence
# passes), but they are not Player work product. Without the filter every
# autobuild turn for a non-trivial task accumulates dozens of them across
# files_modified / files_created / tests_written and the Coach's claim
# audit at ``_verify_claims_were_staged`` short-circuits on tracked-but-
# unchanged paths the Player never authored (study-tutor FEAT-39E1 run-5
# PH1-005 — Player went 4 → 25 → 30+ → 179 ghost paths across four turns;
# decision=timeout_budget_exhausted). See TASK-FIX-PCN and the rule
# ``.claude/rules/path-string-mismatch-is-not-dishonesty.md``.
#
# Patterns are intentionally narrow: they only match namespaces fully
# owned by the orchestrator. Player work under unrelated ``tasks/``
# subdirectories or user-scripted ``.guardkit/`` artefacts MUST pass
# through unchanged (AC-4 regression).

_ORCHESTRATOR_MANAGED_PATH_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"^\.guardkit/autobuild/"),
    re.compile(r"^\.guardkit/bootstrap_state\.json$"),
    re.compile(
        r"^tasks/(?:backlog|design_approved|in_progress|in_review|completed)/"
    ),
)


def _is_orchestrator_managed_path(
    path: Any, worktree_path: Optional[Path] = None
) -> bool:
    """Return True when ``path`` lives in an orchestrator-owned namespace.

    Used by :py:meth:`AgentInvoker._strip_orchestrator_managed_paths` to
    keep orchestrator-induced ghost paths out of the Player report.
    Conservative: only namespaces fully owned by the orchestrator match;
    everything else (Player work under ``src/``, ``tests/``, unrelated
    ``tasks/`` subdirectories, user-scripted ``.guardkit/`` artefacts,
    etc.) returns False.

    Parameters
    ----------
    path:
        Path string from the Player report. May be relative
        (``.guardkit/...``) or absolute
        (``/Users/.../FEAT-X/.guardkit/...``).
    worktree_path:
        When provided, absolute path inputs are first normalised to be
        relative to ``worktree_path`` so the same regex set matches
        regardless of the form the Player chose to report. Without
        ``worktree_path``, only relative paths can match — preserving
        the pre-CAUD-J6F1 behaviour for callers that haven't been
        threaded through yet (TASK-FIX-CAUD-J6F1 AC-003a).
    """
    if not isinstance(path, str) or not path:
        return False
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]

    # AC-003a: when an absolute path is reported AND we know the
    # worktree root, fold it down to the worktree-relative form before
    # the regex match. Without this, the patterns at
    # ``_ORCHESTRATOR_MANAGED_PATH_PATTERNS`` (anchored at start-of-
    # string with ``^\.guardkit/...``) cannot match
    # ``/Users/.../FEAT-X/.guardkit/...`` and harness-owned paths in
    # absolute form leak through to the Coach. See TASK-FIX-CAUD-J6F1.
    if worktree_path is not None:
        candidate = Path(normalized)
        if candidate.is_absolute():
            try:
                resolved = candidate.resolve()
                worktree_resolved = worktree_path.resolve()
                normalized = str(
                    resolved.relative_to(worktree_resolved)
                ).replace("\\", "/")
            except (ValueError, OSError):
                # Path is absolute but lives outside the worktree, or
                # resolve() failed. Fall through with the original
                # string — non-orchestrator paths are the typical case
                # here, so a non-match is the correct outcome.
                pass

    return any(p.match(normalized) for p in _ORCHESTRATOR_MANAGED_PATH_PATTERNS)


def _strip_orchestrator_managed_paths(
    report: Dict[str, Any],
    task_id: str,
    worktree_path: Optional[Path] = None,
) -> Set[str]:
    """Strip orchestrator-managed paths from Player-report claim lists.

    Mutates ``report`` in place. Strips matching paths from:

      * ``report["files_modified"]``
      * ``report["files_created"]``
      * ``report["tests_written"]``
      * ``report["completion_promises"][*]["implementation_files"]``
      * ``report["completion_promises"][*]["test_file"]``

    Returns the union of stripped paths so the caller can log a single
    ``Filtered N orchestrator-induced ghost path(s) for {task_id}: [...]``
    summary line (TASK-FIX-PCN AC-5; same format as the run-3-era
    ``state_transitions.json``-driven filter so existing log monitoring
    continues to work).

    Parameters
    ----------
    worktree_path:
        Optional worktree root. When provided, absolute Player-reported
        paths under the worktree are normalised to their
        worktree-relative form before matching, so harness-owned paths
        in absolute form (e.g.
        ``/Users/.../FEAT-X/.guardkit/autobuild/<TASK_ID>/...``) are
        also stripped. See TASK-FIX-CAUD-J6F1 AC-003a.
    """
    stripped: Set[str] = set()

    for key in ("files_modified", "files_created", "tests_written"):
        original = report.get(key) or []
        if not original:
            continue
        kept: List[str] = []
        any_stripped = False
        for path in original:
            if _is_orchestrator_managed_path(path, worktree_path):
                stripped.add(path)
                any_stripped = True
            else:
                kept.append(path)
        if any_stripped:
            report[key] = sorted(kept)

    promises = report.get("completion_promises") or []
    for promise in promises:
        if not isinstance(promise, dict):
            continue
        impl_files = promise.get("implementation_files") or []
        if impl_files:
            kept_impl: List[str] = []
            any_stripped = False
            for path in impl_files:
                if _is_orchestrator_managed_path(path, worktree_path):
                    stripped.add(path)
                    any_stripped = True
                else:
                    kept_impl.append(path)
            if any_stripped:
                promise["implementation_files"] = kept_impl
        test_file = promise.get("test_file")
        if test_file and _is_orchestrator_managed_path(test_file, worktree_path):
            stripped.add(test_file)
            promise["test_file"] = None

    if stripped:
        logger.info(
            f"Filtered {len(stripped)} orchestrator-induced ghost "
            f"path(s) for {task_id}: {sorted(stripped)}"
        )

    return stripped


# =========================================================================
# Partial Data Extraction (TASK-CRV-1540)
# =========================================================================


def _extract_partial_from_messages(events: List[Any]) -> Dict[str, Any]:
    """Extract partial data from accumulated harness events.

    Called in the CancelledError handler to salvage information from
    events that were yielded before cancellation.

    TASK-HMIG-006.2 migration: this used to consume a list of SDK
    ``AssistantMessage`` objects and walked their ``content`` blocks via
    ``type(block).__name__`` duck-typing. Both harnesses now yield typed
    :class:`HarnessEvent` variants — ``AssistantMessageEvent`` for
    assistant text, ``ToolUseEvent`` for each tool call — so this helper
    now dispatches on event types directly. The output schema is
    unchanged (AC-001).

    The parameter type is still ``List[Any]`` because legacy call sites
    pass a list typed as ``List[Any]`` (the orchestrator's
    ``response_messages`` was historically a List of raw SDK objects).
    Each element is dispatched on isinstance: ``AssistantMessageEvent``
    contributes its joined text as one text-block entry,
    ``ToolUseEvent`` contributes the tool name + input keys, and
    ``Write``/``Edit`` tool calls with ``file_path`` populate
    ``file_modifications``. Other elements (including
    ``ResultMessageEvent`` and any legacy SDK objects from non-migrated
    callers) are skipped.

    Parameters
    ----------
    events : List[Any]
        Harness events accumulated during the query loop. Typically a
        list of :class:`HarnessEvent` variants; non-event elements are
        silently skipped.

    Returns
    -------
    Dict[str, Any]
        Partial report with text_block_count, tool_call_count,
        file_modifications, last_text_blocks, message_count. Schema
        unchanged from the pre-migration shape per AC-001.
    """
    text_blocks: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    file_modifications: List[str] = []

    for ev in events:
        try:
            if isinstance(ev, AssistantMessageEvent):
                text = ev.text
                if text:
                    text_blocks.append(text)
            elif isinstance(ev, ToolUseEvent):
                name = ev.name
                inp = ev.input if isinstance(ev.input, dict) else {}
                tool_calls.append({"name": name, "input_keys": list(inp.keys())})
                if name in ("Write", "Edit"):
                    fp = inp.get("file_path", "")
                    if fp:
                        file_modifications.append(fp)
            # ResultMessageEvent and any other element types are silently
            # skipped — they contribute no partial-extract content.
        except Exception:
            # Defensive: skip malformed events
            continue

    return {
        "text_block_count": len(text_blocks),
        "tool_call_count": len(tool_calls),
        "file_modifications": file_modifications,
        "last_text_blocks": text_blocks[-3:] if text_blocks else [],
        "message_count": len(events),
    }


# =========================================================================
# Heartbeat Logging for SDK Invocations
# =========================================================================


@asynccontextmanager
async def async_heartbeat(
    task_id: str,
    phase: str,
    interval: int = 30,
    progress_logger: Optional["TaskProgressLogger"] = None,
) -> AsyncGenerator[None, None]:
    """Context manager that logs heartbeat messages during SDK invocations.

    Provides periodic progress logging to eliminate the perception of "stalling"
    during long-running SDK invocations (10-20+ minutes). When a progress_logger
    is provided, also writes snapshots to the per-task progress log file for
    post-mortem diagnostics of timed-out parallel tasks.

    Args:
        task_id: Task identifier for log messages (e.g., "TASK-001")
        phase: Description of the current phase (e.g., "Player invocation")
        interval: Seconds between heartbeat logs (default: 30)
        progress_logger: Optional TaskProgressLogger for per-task file logging.
            When provided, snapshots are written at progress_logger.interval
            (default: 60s) in addition to console heartbeat logs.

    Yields:
        None - just provides heartbeat logging during context

    Example:
        >>> async with async_heartbeat("TASK-001", "Player invocation"):
        ...     result = await sdk_invoke(...)  # May take 10+ minutes
        # Logs: [TASK-001] Player invocation in progress... (30s elapsed)
        # Logs: [TASK-001] Player invocation in progress... (60s elapsed)
        # etc.
    """
    from guardkit.orchestrator.progress_logger import TaskProgressLogger  # noqa: F811

    snapshot_interval = progress_logger.interval if progress_logger else interval

    async def heartbeat() -> None:
        elapsed = 0
        while True:
            await asyncio.sleep(interval)
            elapsed += interval
            logger.info(f"[{task_id}] {phase} in progress... ({elapsed}s elapsed)")

            # Write per-task progress snapshot at the configured interval
            if progress_logger and elapsed % snapshot_interval == 0:
                progress_logger.log_snapshot(
                    elapsed=elapsed,
                    phase=phase,
                    files_changed=progress_logger._files_changed,
                    last_tool=progress_logger._last_tool,
                )

    if progress_logger:
        progress_logger.log_start(phase)

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        yield
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task


# Feature flag for task-work delegation (set via environment or config)
# When enabled, invoke_player() delegates to `guardkit task-work --implement-only`
# instead of direct SDK invocation
USE_TASK_WORK_DELEGATION = os.environ.get("GUARDKIT_USE_TASK_WORK_DELEGATION", "false").lower() == "true"

# SDK timeout in seconds (default: 1200s/20min, can be overridden via GUARDKIT_SDK_TIMEOUT env var)
# Complexity-6+ tasks with full Phase 3-5 pipeline (implementation, testing, code review)
# need ~900-1200s. 1200s provides adequate headroom for most tasks.
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1200"))

# TASK-ASF-008: Maximum SDK timeout cap to prevent excessively long sessions
# Even with high complexity + task-work mode, timeout should not exceed 1 hour
MAX_SDK_TIMEOUT = 3600

# TASK-FIX-46F2: Retry constants for transient SDK stream errors.
# During autobuild, vLLM SSE streams can be interrupted under GPU contention
# with "SDK API error in stream: unknown". A single retry with backoff avoids
# the expensive state-recovery → re-implementation path.
MAX_SDK_STREAM_RETRIES = 1
SDK_STREAM_RETRY_BACKOFF = 30  # seconds


def detect_timeout_multiplier() -> float:
    """Detect appropriate timeout multiplier from backend URL.

    When ANTHROPIC_BASE_URL points to localhost or 127.0.0.1 (e.g. local vLLM),
    returns 4.0 since local inference is ~4x slower than Anthropic API.

    Override via GUARDKIT_TIMEOUT_MULTIPLIER environment variable.

    Returns:
        Timeout multiplier (default: 1.0 for Anthropic API, 4.0 for local).
    """
    # Explicit override takes priority
    explicit = os.environ.get("GUARDKIT_TIMEOUT_MULTIPLIER")
    if explicit:
        try:
            value = float(explicit)
            return max(0.1, value)
        except ValueError:
            logger.warning(
                f"Invalid GUARDKIT_TIMEOUT_MULTIPLIER value '{explicit}', "
                "falling back to auto-detection"
            )

    # Auto-detect from backend URL
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return 4.0
    return 1.0


# TASK-REV-BB80: SDK max_turns for task-work invocation (separate from adversarial turns)
# /task-work runs multiple phases internally (planning, review, implementation, testing)
# and needs ~50 internal turns. This is NOT the same as orchestrator's max_turns (adversarial rounds).
# TASK-FIX-ASPF-005: Increased from 50 to 100 — with --fresh, Player needs ~35-50 turns
# for scaffolding + file modifications + tests + report writing. 50 left no headroom.
# TASK-FIX-7718: Env var override + auto-reduction for local backends
_SDK_MAX_TURNS_EXPLICIT = os.environ.get("GUARDKIT_SDK_MAX_TURNS")
TASK_WORK_SDK_MAX_TURNS = int(_SDK_MAX_TURNS_EXPLICIT) if _SDK_MAX_TURNS_EXPLICIT is not None else 100
_SDK_MAX_TURNS_IS_OVERRIDE = _SDK_MAX_TURNS_EXPLICIT is not None

# TASK-ABSR-FLOR: Floor for the complexity-scaled SDK max-turn ceiling. Run-3
# J004-012 hit `int(100 * 1.4) = 140` mid-Phase-3 (`task_work_results.json`,
# `ceiling_hit=true`) and was cut off with capabilities.py left half-edited.
# The 150-turn floor adds 9 turns of headroom for J004-012-shaped tasks where
# the complexity heuristic underestimates actual work. Floor only applies when
# the user has NOT set `GUARDKIT_SDK_MAX_TURNS` (env-var-wins semantics — see
# `_calculate_sdk_max_turns`). Strategic fix is TASK-ABSR-CMPL.
SDK_MAX_TURNS_FLOOR = 150


# TASK-ARCH-COACHSPLIT (D-3): the Coach's verdict synthesis runs as a TOOLLESS,
# grammar-enforced model call over the deterministic evidence bundle by default.
# Set GUARDKIT_COACH_SYNTHESIS=0 (or false/no/off) to restore the legacy
# tool-using Coach that investigates with Read/Bash/Grep/Glob and emits the
# verdict in the same agentic loop (the path that is fragile on the llama.cpp +
# Gemma stack — see runs 13/18 and the task forensics). The default is ON
# because the deterministic bundle already carries the evidence the gather
# phase would seek, and a toolless synthesis is the only way to (a) honour the
# GBNF verdict grammar (llama.cpp hard-rejects grammar+tools) and (b) avoid the
# run-18 tool-parse HTTP 500.
_COACH_SYNTHESIS_DISABLED_VALUES = frozenset({"0", "false", "no", "off"})


def _coach_synthesis_enabled() -> bool:
    """Return True when the toolless grammar-enforced Coach synthesis is active.

    Default ON; disabled only by an explicit GUARDKIT_COACH_SYNTHESIS in
    ``{"0", "false", "no", "off"}`` (case-insensitive). Read at invocation
    time (not import time) so tests and operators can toggle it per-run.
    """
    raw = os.environ.get("GUARDKIT_COACH_SYNTHESIS")
    if raw is None:
        return True
    return raw.strip().lower() not in _COACH_SYNTHESIS_DISABLED_VALUES


# TASK-ARCH-COACHBFULL: the B-full investigating Coach runs a tool-using
# Phase-A "gather" (Read/Bash/Grep/Glob) BEFORE the toolless Phase-B verdict
# synthesis, feeding investigation findings into the synthesis prompt. It is
# OPT-IN (default OFF) — the inverse default of GUARDKIT_COACH_SYNTHESIS. B-min
# (toolless synthesis) is the validated default; B-full re-introduces the
# tool-bound g31 path D-3 removed for substrate reliability, so the unproven
# enhancement must not be the default until it earns promotion (see the task's
# "Flag default + promotion criteria"). Any Phase-A failure degrades to B-min
# (strict dominance), so enabling it can only add investigation, never regress.
_COACH_GATHER_ENABLED_VALUES = frozenset({"1", "true", "yes", "on"})


def _coach_gather_enabled() -> bool:
    """Return True when the B-full tool-using Phase-A gather is active.

    Default OFF (opt-in); enabled only by an explicit GUARDKIT_COACH_GATHER in
    ``{"1", "true", "yes", "on"}`` (case-insensitive). Read at invocation time
    (not import time) so tests and operators can toggle it per-run.
    """
    raw = os.environ.get("GUARDKIT_COACH_GATHER")
    if raw is None:
        return False
    return raw.strip().lower() in _COACH_GATHER_ENABLED_VALUES


# TASK-ARCH-COACHBFULL (AC-5): Phase-A gather budget slice. The gather is a
# tool-bound investigation whose findings are advisory; it must not consume the
# whole per-turn budget and starve the load-bearing Phase-B synthesis. Phase A
# is capped at ``max(MIN, FRACTION * effective_timeout)`` (never above the
# effective timeout); Phase B then runs at the FULL effective timeout. Combined
# wall-clock is therefore bounded at ``(1 + FRACTION) * effective`` — documented
# as the opt-in cost. A tighter ``<= 1x`` bound (subtracting gather spend from
# the synthesis budget) was rejected: it risks synthesis timeouts on the slow
# substrate. Revisit under promotion criterion P-5 / TASK-PERF-COACHSYNTH.
_COACH_GATHER_BUDGET_FRACTION = 0.4
_COACH_GATHER_BUDGET_MIN_S = 60


# =========================================================================
# TASK-PSN-003: Promise format reinforcement near SDK turn ceiling
# =========================================================================
# When a task has many acceptance criteria, the completion_promises format
# instructions (injected once at prompt start) can be forgotten by the agent
# after many SDK turns due to context attention degradation.  Adding a
# reinforcement block at the END of the prompt exploits recency bias to keep
# the schema fresh.  The turn_context.json file also carries a reminder so
# the agent has a second source of truth.
#
# Threshold: number of acceptance criteria that triggers stronger emphasis.
# Configurable via env var; default 5 (root-cause incident had ~10+ criteria).
_REINFORCEMENT_THRESHOLD_EXPLICIT = os.environ.get(
    "GUARDKIT_REINFORCEMENT_CRITERIA_THRESHOLD"
)
REINFORCEMENT_CRITERIA_THRESHOLD: int = (
    int(_REINFORCEMENT_THRESHOLD_EXPLICIT)
    if _REINFORCEMENT_THRESHOLD_EXPLICIT is not None
    else 5
)

PROMISE_FORMAT_REMINDER = (
    "\n⚠️ CRITICAL SCHEMA REQUIREMENT — READ BEFORE WRITING YOUR REPORT ⚠️\n"
    "Your completion_promises MUST use these EXACT field names:\n"
    '  ✅ "criterion_id"   (NOT "ac_id", NOT "id", NOT "criteria_id")\n'
    '  ✅ "criterion_text"  (NOT "description", NOT "text", NOT "criteria_text")\n'
    '  ✅ "status"          must be "complete" or "incomplete"\n'
    '                       (NOT "done", NOT "finished", NOT "completed")\n'
    '  ✅ "evidence"        description of what you did\n'
    '  ✅ "test_file"       path to test file (if applicable)\n'
    '  ✅ "implementation_files"  list of files modified/created\n'
)

# Schema reminder included in turn_context.json for file-based reinforcement.
_PROMISE_SCHEMA_FIELDS = {
    "criterion_id": "CORRECT — do NOT use ac_id or id",
    "criterion_text": "CORRECT — do NOT use description or text",
    "status": "must be 'complete' or 'incomplete' — do NOT use done/finished",
    "evidence": "description of what you did",
    "test_file": "path to test file (if applicable)",
    "implementation_files": "list of files modified/created",
}

# =========================================================================
# SDK Async Generator Cleanup Noise Suppression (TASK-FIX-k3l4)
# =========================================================================
# When the SDK's query() async generator is closed between turns, AnyIO's
# cancel scope tries to exit in a new asyncio task, producing RuntimeError
# noise. This handler suppresses only those specific errors.

_SDK_CLEANUP_SUPPRESS_PATTERNS = [
    "Attempted to exit cancel scope in a different task",
    "Command failed with exit code 1",
]

_patched_loops: set = set()


def _install_sdk_cleanup_handler(loop: asyncio.AbstractEventLoop) -> None:
    """Install targeted asyncio exception handler for SDK cleanup noise.

    Idempotent - safe to call multiple times on the same loop.
    Only suppresses known SDK async generator cleanup errors;
    all other asyncio background task errors are passed through.
    """
    if id(loop) in _patched_loops:
        return

    def handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        msg = context.get("message", "")
        exc = context.get("exception")
        exc_msg = str(exc) if exc else ""
        if any(p in msg or p in exc_msg for p in _SDK_CLEANUP_SUPPRESS_PATTERNS):
            return  # suppress known SDK generator cleanup noise
        loop.default_exception_handler(context)

    loop.set_exception_handler(handler)
    _patched_loops.add(id(loop))


# Player report schema - required fields
PLAYER_REPORT_SCHEMA = {
    "task_id": str,
    "turn": int,
    "files_modified": list,
    "files_created": list,
    "tests_written": list,
    "tests_run": bool,
    "tests_passed": bool,
    "implementation_notes": str,
    "concerns": list,
    "requirements_addressed": list,
    "requirements_remaining": list,
}

# Coach decision schema - required fields
COACH_DECISION_SCHEMA = {
    "task_id": str,
    "turn": int,
    "decision": str,  # "approve" or "feedback"
}

# Documentation level to max files mapping
# Used to enforce file count constraints based on documentation_level setting
DOCUMENTATION_LEVEL_MAX_FILES = {
    "minimal": 2,
    "standard": 2,
    "comprehensive": None,  # No limit
}

# TASK-GK-DOC-001: Paths the doc-level file-count check ignores. These are
# orchestrator bookkeeping artefacts (turn dumps, bdd oracle output, task
# plans) that the Player legitimately writes alongside real new code, plus
# empty package markers. Counting them produces false-positive scope
# warnings — see FEAT-PEBR turn-1 log for the original symptom.
_DOC_LEVEL_EXCLUDED_PATTERNS: Tuple[str, ...] = (
    ".guardkit/autobuild/",
    ".guardkit/bdd/",
    ".claude/task-plans/",
)


def _is_doc_level_excluded(path: str) -> bool:
    """Return True if `path` is an orchestrator artefact that should not
    count against the documentation-level file-count constraint.

    Matches absolute and relative paths anchored on the excluded prefix,
    plus empty-package `__init__.py` markers (bare or nested).
    """
    if path == "__init__.py" or path.endswith("/__init__.py"):
        return True
    return any(
        path.startswith(prefix) or f"/{prefix}" in path
        for prefix in _DOC_LEVEL_EXCLUDED_PATTERNS
    )


# =========================================================================
# Stream Parser for Quality Gate Extraction
# =========================================================================


import re


class TaskWorkStreamParser:
    """Stateful incremental parser for task-work SDK stream messages.

    This parser extracts quality gate results from task-work output streams,
    accumulating results across multiple stream messages. It uses regex
    patterns for flexibility and handles unrecognized patterns gracefully.

    Key features:
    - Incremental parsing (called for each stream message)
    - Accumulates results across calls
    - Uses sets for file lists to avoid duplicates
    - Graceful degradation for unrecognized patterns

    Example:
        >>> parser = TaskWorkStreamParser()
        >>> parser.parse_message("Phase 2: Implementation Planning...")
        >>> parser.parse_message("12 tests passed, 0 failed")
        >>> parser.parse_message("Coverage: 85.5%")
        >>> result = parser.to_result()
        >>> result["tests_passed"]
        12
        >>> result["coverage"]
        85.5
    """

    # Pattern constants for matching task-work output
    # Using single pattern per type following YAGNI principle
    PHASE_MARKER_PATTERN = re.compile(r"Phase\s+(\d+(?:\.\d+)?)[:\s]+(.+)")
    PHASE_COMPLETE_PATTERN = re.compile(r"[✓✔]\s+Phase\s+(\d+(?:\.\d+)?)\s+complete", re.IGNORECASE)
    TESTS_PASSED_PATTERN = re.compile(r"(\d+)\s+tests?\s+passed", re.IGNORECASE)
    TESTS_FAILED_PATTERN = re.compile(r"(\d+)\s+tests?\s+failed", re.IGNORECASE)
    COVERAGE_PATTERN = re.compile(r"[Cc]overage[:\s]+(\d+(?:\.\d+)?)%")
    QUALITY_GATES_PASSED_PATTERN = re.compile(r"[Qq]uality\s+gates[:\s]*PASSED|all\s+quality\s+gates\s+passed", re.IGNORECASE)
    QUALITY_GATES_FAILED_PATTERN = re.compile(r"[Qq]uality\s+gates[:\s]*FAILED", re.IGNORECASE)
    FILES_MODIFIED_PATTERN = re.compile(r"(?:Modified|Changed):\s*([^\s,]+(?:\.[a-zA-Z]+|/))")
    FILES_CREATED_PATTERN = re.compile(r"(?:Created|Added):\s*([^\s,]+(?:\.[a-zA-Z]+|/))")
    # Architectural review score patterns
    ARCH_SCORE_PATTERN = re.compile(r"[Aa]rchitectural.*?[Ss]core[:\s]+(\d+)(?:/100)?", re.IGNORECASE)
    ARCH_SUBSCORES_PATTERN = re.compile(r"SOLID[:\s]+(\d+),?\s*DRY[:\s]+(\d+),?\s*YAGNI[:\s]+(\d+)", re.IGNORECASE)
    # Tool invocation patterns for tracking Write/Edit operations
    # Matches: <invoke name="Write"> or <invoke name="Edit">
    TOOL_INVOKE_PATTERN = re.compile(r'<invoke\s+name="(Write|Edit)">')
    # Matches: <parameter name="file_path">/path/to/file</parameter>
    TOOL_FILE_PATH_PATTERN = re.compile(r'<parameter\s+name="file_path">([^<]+)</parameter>')
    # Matches tool result messages like "File created successfully at: /path"
    TOOL_RESULT_CREATED_PATTERN = re.compile(r"File\s+(?:created|written)\s+(?:successfully\s+)?(?:at|to)[:\s]+([^\s]+)", re.IGNORECASE)
    TOOL_RESULT_MODIFIED_PATTERN = re.compile(r"File\s+(?:modified|updated|edited)\s+(?:successfully\s+)?(?:at)?[:\s]+([^\s]+)", re.IGNORECASE)
    # Pytest summary pattern: "X passed" or "X passed, Y failed" or "X passed, Y failed, Z skipped"
    PYTEST_SUMMARY_PATTERN = re.compile(
        r"[=]+\s*(?:(\d+)\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+skipped)?.*?[=]+",
        re.IGNORECASE
    )
    # Alternative pytest pattern for simpler output: "5 passed in 0.23s"
    PYTEST_SIMPLE_PATTERN = re.compile(r"(\d+)\s+passed(?:\s+in\s+[\d.]+s)?", re.IGNORECASE)

    def __init__(self) -> None:
        """Initialize the parser with empty accumulated state."""
        self._phases: Dict[str, Dict[str, Any]] = {}
        self._tests_passed: Optional[int] = None
        self._tests_failed: Optional[int] = None
        self._coverage: Optional[float] = None
        self._quality_gates_passed: Optional[bool] = None
        self._files_modified: set = set()
        self._files_created: set = set()
        # TASK-FIX-CC-COND: Files the Player explicitly authored via Write/Edit
        # tool calls. Distinct from _files_modified/_files_created because
        # those get unioned with worktree-wide `git diff` output downstream
        # (see _create_player_report_from_task_work), which contaminates them
        # with peer-task edits in shared-worktree parallel waves. _files_authored
        # is only ever populated from real tool invocations, so it remains
        # authoritative for source-file contention detection.
        self._files_authored: set = set()
        self._test_files_created: set = set()
        self._arch_score: Optional[int] = None
        self._solid_score: Optional[int] = None
        self._dry_score: Optional[int] = None
        self._yagni_score: Optional[int] = None

    def _match_pattern(
        self,
        pattern: re.Pattern,
        text: str,
    ) -> Optional[re.Match]:
        """Helper to match a pattern against text.

        Args:
            pattern: Compiled regex pattern
            text: Text to search

        Returns:
            Match object if found, None otherwise
        """
        return pattern.search(text)

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file path is a test file.

        Detects Python test files using common naming conventions:
        - test_*.py (pytest default)
        - *_test.py (alternative convention)

        Args:
            file_path: Path to the file

        Returns:
            True if the file is a test file, False otherwise
        """
        if not file_path:
            return False
        # Extract the filename from the path
        name = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        name = name.rsplit("\\", 1)[-1] if "\\" in name else name
        return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")

    @staticmethod
    def _is_valid_file_path(path: str) -> bool:
        """Validate that a string looks like a file path.

        Rejects strings that are clearly not file paths, such as natural language
        words (e.g. 'house') or glob wildcards (e.g. '**').  A valid path must
        contain at least one of: a path separator (/ or \\) or a dot (.).

        Args:
            path: String to validate

        Returns:
            True if the string looks like a file path, False otherwise
        """
        if not path or len(path) < 3:
            return False
        if path in ("*", "**", "***"):
            return False
        if path.startswith("*"):
            return False
        # Must contain a path separator or file extension indicator
        return "/" in path or "\\" in path or "." in path

    def _track_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> None:
        """Track file operations from tool calls.

        Extracts file paths from Write and Edit tool invocations and adds them
        to the appropriate tracking set (created or modified). Also tracks
        test file creation separately.

        Args:
            tool_name: Name of the tool (e.g., "Write", "Edit")
            tool_args: Tool arguments dictionary containing file_path
        """
        # TASK-FIX-PIPELINE: Try multiple key names for file path (Fix 1)
        # Claude Code SDK tools may use different key names
        file_path = (
            tool_args.get("file_path")
            or tool_args.get("path")
            or tool_args.get("file")
            or tool_args.get("filePath")
        )
        if not file_path or not isinstance(file_path, str):
            logger.debug(
                f"Tool {tool_name} call has no recognizable file path key. "
                f"Available keys: {list(tool_args.keys())}"
            )
            return

        if tool_name == "Write":
            self._files_created.add(file_path)
            self._files_authored.add(file_path)
            logger.debug(f"Tool call tracked - file created: {file_path}")
            # Track test files separately
            if self._is_test_file(file_path):
                self._test_files_created.add(file_path)
                logger.debug(f"Test file tracked: {file_path}")
        elif tool_name == "Edit":
            self._files_modified.add(file_path)
            self._files_authored.add(file_path)
            logger.debug(f"Tool call tracked - file modified: {file_path}")

    def _parse_tool_invocations(self, message: str) -> None:
        """Parse tool invocations from message and track file operations.

        Detects Write and Edit tool calls in the message text and extracts
        file paths to track. Handles both XML-style tool invocations and
        tool result messages.

        Args:
            message: Stream message that may contain tool invocations
        """
        # Track XML-style tool invocations: <invoke name="Write">...<parameter name="file_path">
        tool_match = self._match_pattern(self.TOOL_INVOKE_PATTERN, message)
        if tool_match:
            tool_name = tool_match.group(1)
            file_path_match = self._match_pattern(self.TOOL_FILE_PATH_PATTERN, message)
            if file_path_match:
                file_path = file_path_match.group(1).strip()
                self._track_tool_call(tool_name, {"file_path": file_path})

        # Track tool result messages (e.g., "File created successfully at: /path")
        for result_match in self.TOOL_RESULT_CREATED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if file_path and self._is_valid_file_path(file_path):
                self._files_created.add(file_path)
                logger.debug(f"Tool result tracked - file created: {file_path}")

        for result_match in self.TOOL_RESULT_MODIFIED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if file_path and self._is_valid_file_path(file_path):
                self._files_modified.add(file_path)
                logger.debug(f"Tool result tracked - file modified: {file_path}")

    def parse_message(self, message: str) -> None:
        """Parse a single stream message and accumulate results.

        This method extracts quality gate information from a stream message
        and updates the internal state. It handles:
        - Phase markers and completion indicators
        - Test pass/fail counts
        - Coverage percentage
        - Quality gate status
        - File modification lists
        - Tool invocations (Write/Edit) for file tracking

        Args:
            message: Single message from the task-work SDK stream

        Note:
            Unrecognized patterns are logged at debug level but do not
            cause errors (graceful degradation).
        """
        if not message:
            return

        # Tool invocation tracking (Write/Edit operations)
        self._parse_tool_invocations(message)

        # Phase detection
        phase_match = self._match_pattern(self.PHASE_MARKER_PATTERN, message)
        if phase_match:
            phase_num = phase_match.group(1)
            phase_text = phase_match.group(2)[:100]  # Truncate long descriptions
            self._phases[f"phase_{phase_num}"] = {
                "detected": True,
                "text": phase_text,
                "completed": False,
            }
            logger.debug(f"Detected phase {phase_num}: {phase_text}")

        # Phase completion
        complete_match = self._match_pattern(self.PHASE_COMPLETE_PATTERN, message)
        if complete_match:
            phase_num = complete_match.group(1)
            phase_key = f"phase_{phase_num}"
            if phase_key in self._phases:
                self._phases[phase_key]["completed"] = True
            else:
                self._phases[phase_key] = {"detected": True, "completed": True}
            logger.debug(f"Phase {phase_num} completed")

        # Test results - try individual patterns first
        tests_passed_match = self._match_pattern(self.TESTS_PASSED_PATTERN, message)
        if tests_passed_match:
            self._tests_passed = int(tests_passed_match.group(1))
            logger.debug(f"Tests passed: {self._tests_passed}")

        tests_failed_match = self._match_pattern(self.TESTS_FAILED_PATTERN, message)
        if tests_failed_match:
            self._tests_failed = int(tests_failed_match.group(1))
            logger.debug(f"Tests failed: {self._tests_failed}")

        # Parse pytest summary output (e.g., "===== 5 passed, 2 failed in 0.23s =====")
        pytest_summary_match = self._match_pattern(self.PYTEST_SUMMARY_PATTERN, message)
        if pytest_summary_match:
            if pytest_summary_match.group(1):
                passed_count = int(pytest_summary_match.group(1))
                if self._tests_passed is None or passed_count > self._tests_passed:
                    self._tests_passed = passed_count
                    logger.debug(f"Pytest summary - tests passed: {self._tests_passed}")
            if pytest_summary_match.group(2):
                failed_count = int(pytest_summary_match.group(2))
                if self._tests_failed is None or failed_count > self._tests_failed:
                    self._tests_failed = failed_count
                    logger.debug(f"Pytest summary - tests failed: {self._tests_failed}")

        # Also try simpler pytest pattern (e.g., "5 passed in 0.23s")
        if self._tests_passed is None:
            simple_match = self._match_pattern(self.PYTEST_SIMPLE_PATTERN, message)
            if simple_match:
                self._tests_passed = int(simple_match.group(1))
                logger.debug(f"Pytest simple - tests passed: {self._tests_passed}")

        # Coverage
        coverage_match = self._match_pattern(self.COVERAGE_PATTERN, message)
        if coverage_match:
            self._coverage = float(coverage_match.group(1))
            logger.debug(f"Coverage: {self._coverage}%")

        # Quality gates
        if self._match_pattern(self.QUALITY_GATES_PASSED_PATTERN, message):
            self._quality_gates_passed = True
            logger.debug("Quality gates: PASSED")
        elif self._match_pattern(self.QUALITY_GATES_FAILED_PATTERN, message):
            self._quality_gates_passed = False
            logger.debug("Quality gates: FAILED")

        # File modifications (use sets to avoid duplicates)
        for file_match in self.FILES_MODIFIED_PATTERN.finditer(message):
            file_path = file_match.group(1)
            if self._is_valid_file_path(file_path):
                self._files_modified.add(file_path)
                logger.debug(f"File modified: {file_path}")

        for file_match in self.FILES_CREATED_PATTERN.finditer(message):
            file_path = file_match.group(1)
            if self._is_valid_file_path(file_path):
                self._files_created.add(file_path)
                logger.debug(f"File created: {file_path}")

        # Architectural review scores
        arch_score_match = self._match_pattern(self.ARCH_SCORE_PATTERN, message)
        if arch_score_match:
            try:
                self._arch_score = int(arch_score_match.group(1))
                logger.debug(f"Architectural review score: {self._arch_score}")
            except ValueError:
                logger.warning(f"Invalid arch score format: {arch_score_match.group(1)}")

        subscores_match = self._match_pattern(self.ARCH_SUBSCORES_PATTERN, message)
        if subscores_match:
            try:
                self._solid_score = int(subscores_match.group(1))
                self._dry_score = int(subscores_match.group(2))
                self._yagni_score = int(subscores_match.group(3))
                logger.debug(f"SOLID: {self._solid_score}, DRY: {self._dry_score}, YAGNI: {self._yagni_score}")
            except ValueError:
                logger.warning(f"Invalid subscore format in: {message}")

    def to_result(self) -> Dict[str, Any]:
        """Convert accumulated state to a result dictionary.

        Returns:
            Dictionary containing all parsed quality gate information:
            - phases: Dict of detected phases with completion status
            - tests_passed: Number of tests that passed (or None)
            - tests_failed: Number of tests that failed (or None)
            - coverage: Coverage percentage (or None)
            - quality_gates_passed: Boolean or None if not detected
            - files_modified: List of modified file paths
            - files_created: List of created file paths
            - test_files_created: List of test file paths created
            - architectural_review: Dict with score and optional SOLID/DRY/YAGNI
              subscores (or absent if no arch review score found)
        """
        result: Dict[str, Any] = {}

        if self._phases:
            result["phases"] = self._phases

        if self._tests_passed is not None:
            result["tests_passed"] = self._tests_passed

        if self._tests_failed is not None:
            result["tests_failed"] = self._tests_failed

        if self._coverage is not None:
            result["coverage"] = self._coverage

        if self._quality_gates_passed is not None:
            result["quality_gates_passed"] = self._quality_gates_passed

        if self._files_modified:
            result["files_modified"] = sorted(list(self._files_modified))

        if self._files_created:
            result["files_created"] = sorted(list(self._files_created))

        # TASK-FIX-CC-COND: emit files_authored only when non-empty
        # (parity with files_modified/files_created). The downstream
        # producer ``_write_task_work_results`` always persists the field
        # to disk (even as []) so Coach gets a positive presence signal
        # for the new contention-detection path.
        if self._files_authored:
            result["files_authored"] = sorted(list(self._files_authored))

        if self._test_files_created:
            result["test_files_created"] = sorted(list(self._test_files_created))

        if self._arch_score is not None:
            arch_review: Dict[str, Any] = {"score": self._arch_score}
            if self._solid_score is not None:
                arch_review["solid"] = self._solid_score
            if self._dry_score is not None:
                arch_review["dry"] = self._dry_score
            if self._yagni_score is not None:
                arch_review["yagni"] = self._yagni_score
            result["architectural_review"] = arch_review

        return result

    def reset(self) -> None:
        """Reset parser state for reuse.

        Clears all accumulated state, allowing the parser to be reused
        for a new stream.
        """
        self._phases = {}
        self._tests_passed = None
        self._tests_failed = None
        self._coverage = None
        self._quality_gates_passed = None
        self._files_modified = set()
        self._files_created = set()
        self._files_authored = set()
        self._test_files_created = set()
        self._arch_score = None
        self._solid_score = None
        self._dry_score = None
        self._yagni_score = None


@dataclass
class AgentInvocationResult:
    """Result of an agent invocation.

    Attributes:
        task_id: Task identifier (e.g., "TASK-001")
        turn: Turn number (1-based)
        agent_type: "player" or "coach"
        success: True if invocation succeeded
        report: Parsed JSON from agent
        duration_seconds: Time taken for invocation
        error: Error message if failed
    """

    task_id: str
    turn: int
    agent_type: str  # "player" or "coach"
    success: bool
    report: Dict[str, Any]
    duration_seconds: float
    error: Optional[str] = None
    sdk_turns_used: Optional[int] = None      # TASK-VPR-003: Actual SDK turns from ResultMessage
    sdk_max_turns: Optional[int] = None        # TASK-VPR-003: Effective SDK turn ceiling
    sdk_ceiling_hit: bool = False              # TASK-VPR-003: Whether ceiling was hit
    session_id: Optional[str] = None           # TASK-RFX-B20B: SDK session ID for resumption


class AgentInvoker:
    """Handles Claude Agents SDK invocation for Player and Coach agents.

    This class is the bridge between the orchestration layer and AI agents,
    managing agent sessions, context preparation, and response handling.

    Key Responsibilities:
    - Invoke Player and Coach agents via Claude Agents SDK
    - Manage fresh context per turn (no context pollution)
    - Handle SDK integration with appropriate permissions per agent type
    - Parse and validate agent responses (JSON reports)
    - Provide error handling and timeout management
    - Support async/await pattern for concurrent operations

    Example:
        >>> invoker = AgentInvoker(
        ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
        ...     max_turns_per_agent=30,
        ... )
        >>> result = await invoker.invoke_player(
        ...     task_id="TASK-001",
        ...     turn=1,
        ...     requirements="Implement OAuth2 authentication",
        ... )
        >>> assert result.success
        >>> assert result.report["tests_passed"]
    """

    # Class-level lock to serialise git operations across parallel tasks (TASK-FIX-VL04)
    _git_lock = threading.RLock()

    def __init__(
        self,
        worktree_path: Path,
        max_turns_per_agent: int = 30,
        sdk_timeout_seconds: int = DEFAULT_SDK_TIMEOUT,
        use_task_work_delegation: Optional[bool] = None,
        development_mode: str = "tdd",
        cancellation_event: Optional[threading.Event] = None,
        timeout_multiplier: Optional[float] = None,
        emitter: Optional[Any] = None,
        venv_python: Optional[str] = None,
        model_name: Optional[str] = None,  # TASK-FIX-MODELPLUMB
        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
    ):
        """Initialize AgentInvoker.

        Model selection strategy: Both Player and Coach models are delegated
        to the bundled Claude CLI default. The CLI default (currently
        claude-sonnet-4-6) must match the vLLM SERVED_MODEL_NAME when using
        local inference. See docs/guides/simple-local-autobuild.md for details.

        Args:
            worktree_path: Path to the isolated git worktree
            max_turns_per_agent: Maximum turns per agent invocation (default: 30)
            sdk_timeout_seconds: Timeout for SDK invocations (default: 1200s)
            use_task_work_delegation: If True, delegate Player to task-work instead of
                direct SDK. Defaults to USE_TASK_WORK_DELEGATION env var.
            development_mode: Development mode for implementation (default: "tdd").
                Valid values: "standard", "tdd", "bdd"
            cancellation_event: Cooperative cancellation signal from FeatureOrchestrator
                (default: None). When set, _invoke_with_role() monitors the event and
                terminates the SDK subprocess if cancellation is requested.
                (TASK-FIX-ASPF-004)
            timeout_multiplier: Multiplier for all timeout values (default: auto-detect).
                When None, auto-detects from ANTHROPIC_BASE_URL (4.0 for localhost).
                (TASK-FIX-VL05)
            emitter: Optional EventEmitter for instrumentation telemetry.
                Defaults to NullEmitter() when not provided (zero behaviour change
                for existing callers). (TASK-INST-005b)
            venv_python: Optional path to the Python interpreter Coach should
                use when invoking pytest. Typically
                ``BootstrapResult.venv_python`` threaded from the feature
                orchestrator. When None, CoachVerifier falls back to
                filesystem discovery and then PATH pytest. (TASK-FIX-7A05)
        """
        self.worktree_path = Path(worktree_path)
        self._venv_python: Optional[str] = venv_python
        self.max_turns_per_agent = max_turns_per_agent
        self.sdk_timeout_seconds = sdk_timeout_seconds
        self._sdk_timeout_is_override = sdk_timeout_seconds != DEFAULT_SDK_TIMEOUT
        self.timeout_multiplier = (
            timeout_multiplier if timeout_multiplier is not None
            else detect_timeout_multiplier()
        )
        self.use_task_work_delegation = (
            use_task_work_delegation if use_task_work_delegation is not None
            else USE_TASK_WORK_DELEGATION
        )
        self.development_mode = development_mode
        self._cancellation_event: Optional[threading.Event] = cancellation_event
        # TASK-FIX-SPECHANG2: monotonic timestamp of the most recent
        # model-stream event observed inside ``_invoke_with_role``. Read by
        # the specialist no-model-activity watchdog
        # (``specialist_invocations.py``) to distinguish a genuine agent hang
        # (zero ``/v1/responses`` traffic for N seconds) from a slow-but-
        # progressing run. ``0.0`` until the first invocation resets it.
        self._last_activity_monotonic: float = 0.0
        self._baseline_commit: Optional[str] = None
        # TASK-FIX-OBS2: Per-task progress logger for parallel execution diagnostics
        self._progress_logger: Optional["TaskProgressLogger"] = None
        # TASK-CRV-1540: Partial data extracted from response_messages on CancelledError
        self._last_partial_report: Optional[Dict[str, Any]] = None
        # TASK-RFX-B20B: Last captured session_id from ResultMessage for resume
        self._last_session_id: Optional[str] = None
        # TASK-INST-005b: EventEmitter for instrumentation telemetry
        self._emitter = emitter if emitter is not None else NullEmitter()
        # TASK-FIX-MODELPLUMB: default model identifier for invocations that
        # don't specify one. Threaded from the CLI --model flag through
        # AutoBuildOrchestrator. Used as a fallback inside _invoke_with_role
        # when the per-call model kwarg is None — load-bearing for the
        # LangGraph harness (DeepAgents.create_deep_agent fails with
        # "'function' object has no attribute 'name'" when model=None);
        # decorative-but-harmless for the SDK path (routes via
        # ANTHROPIC_BASE_URL).
        self._model_name: Optional[str] = model_name
        # TASK-FIX-COACHBUDG01 (2026-06-06): optional per-role override for
        # Coach. When non-None, `_invoke_with_role` uses this for role='coach'
        # and role='coach_test' invocations; Player and specialist roles stay
        # on `_model_name`. None preserves pre-COACHBUDG01 behaviour (Coach
        # shares Player's model). Sibling pattern to LGFM3 which threaded the
        # model_name kwarg through CoachValidator's SDK test-exec path; the
        # difference here is that LGFM3 unified model selection across all
        # roles while COACHBUDG01 allows per-role divergence (the load-bearing
        # mechanic for swapping Coach to gemma4:26b while Player stays on
        # qwen36-workhorse — TASK-HMIG-013).
        self._coach_model_name: Optional[str] = coach_model_name

        if self.timeout_multiplier != 1.0:
            logger.info(
                f"Timeout multiplier: {self.timeout_multiplier}x "
                f"(sdk_timeout base={self.sdk_timeout_seconds}s → "
                f"effective max={int(MAX_SDK_TIMEOUT * self.timeout_multiplier)}s)"
            )

        # TASK-FIX-7718: Auto-reduce SDK max turns for local backends.
        # TASK-ABSR-MAXT: This field is now used only by the legacy direct-mode
        # path (`_invoke_player_direct`). The task-work invocation path uses the
        # per-task complexity-scaled value from `_calculate_sdk_max_turns(task_id)`
        # instead, so each task gets a turn budget proportional to its complexity.
        if not _SDK_MAX_TURNS_IS_OVERRIDE and self.timeout_multiplier > 1.0:
            self._effective_sdk_max_turns = min(TASK_WORK_SDK_MAX_TURNS, 100)
            logger.info(
                "SDK max turns reduced to %d for local backend "
                "(timeout_multiplier=%.1f)",
                self._effective_sdk_max_turns,
                self.timeout_multiplier,
            )
        else:
            self._effective_sdk_max_turns = TASK_WORK_SDK_MAX_TURNS

    # =========================================================================
    # Per-Task Progress Logging (TASK-FIX-OBS2)
    # =========================================================================

    def set_progress_logger(self, progress_logger: Optional[Any]) -> None:
        """Set the per-task progress logger for parallel execution diagnostics.

        Parameters
        ----------
        progress_logger : Optional[TaskProgressLogger]
            Progress logger instance, or None to disable.
        """
        self._progress_logger = progress_logger

    def _track_tool_use(self, event: "ToolUseEvent") -> None:
        """Track a single tool-use event for progress logging.

        TASK-HMIG-006.2 migration: the previous signature accepted the SDK
        ``AssistantMessage`` and walked its content blocks for
        ``ToolUseBlock`` instances. Both harnesses now yield a
        :class:`ToolUseEvent` per tool call, so this helper consumes one
        typed event per call and the AssistantMessage content walk is gone.

        Parameters
        ----------
        event : ToolUseEvent
            Typed tool-use event yielded by the active harness.
        """
        if not self._progress_logger:
            return
        try:
            name = event.name
            self._progress_logger._last_tool = name
            if name in ("Write", "Edit"):
                self._progress_logger._files_changed += 1
        except Exception:
            pass  # Never crash orchestration for progress tracking

    # =========================================================================
    # Path Resolution Helpers (TASK-FIX-VL01)
    # =========================================================================

    def _resolve_repo_root(self) -> Optional[Path]:
        """Resolve the main repository root from the worktree path.

        In a git worktree setup, worktrees are located at:
            {repo_root}/.guardkit/worktrees/{task_or_feature_id}/

        If the current worktree_path follows this convention, the repo root
        is derived by stripping the ``.guardkit/worktrees/...`` suffix.

        Returns ``None`` when worktree_path IS the repo root (no fallback
        needed) or when the path doesn't match the worktree convention.
        """
        worktree_str = str(self.worktree_path)
        marker = os.sep + ".guardkit" + os.sep + "worktrees" + os.sep
        idx = worktree_str.find(marker)
        if idx >= 0:
            return Path(worktree_str[:idx])
        return None

    # =========================================================================
    # Session Resume Support (TASK-RFX-B20B)
    # =========================================================================

    def set_player_resume_session(self, session_id: Optional[str]) -> None:
        """Set session ID for the next Player invocation to resume from.

        Called by the orchestrator between turns to enable session continuity.
        Pass None to start a fresh session (no resume).

        Args:
            session_id: SDK session ID from a previous ResultMessage, or None.
        """
        self._last_session_id = session_id

    # =========================================================================
    # Cancellation Support (TASK-FIX-ASPF-004)
    # =========================================================================

    def cancel(self) -> None:
        """Cancel any in-progress SDK invocation.

        Sets the cancellation event (if present) and terminates any child
        ``claude`` processes spawned by the SDK. This bridges the gap between
        asyncio cancellation (which only cancels the wrapper) and the actual
        OS subprocess that the SDK spawns.

        Safe to call from any thread.
        """
        if self._cancellation_event:
            self._cancellation_event.set()
        self._kill_child_claude_processes()

    def _kill_child_claude_processes(self) -> None:
        """Find and SIGTERM child ``claude`` CLI processes.

        Uses ``/proc/{pid}/status`` on Linux to walk the process tree from
        the current PID, looking for children whose ``Name:`` field contains
        ``claude`` or ``node`` (the Claude CLI runs as a Node.js process).

        Handles:
        - ``ProcessLookupError`` for processes that exit between enumeration
          and signal delivery.
        - ``PermissionError`` for processes we cannot signal.
        - Non-Linux platforms where ``/proc`` is unavailable (logs warning).
        """
        my_pid = os.getpid()
        proc_path = Path("/proc")

        if not proc_path.exists():
            self._kill_child_processes_fallback(my_pid)
            return

        killed = []
        try:
            for entry in proc_path.iterdir():
                if not entry.name.isdigit():
                    continue
                pid = int(entry.name)
                if pid == my_pid:
                    continue

                status_file = entry / "status"
                try:
                    status_text = status_file.read_text()
                except (OSError, PermissionError):
                    continue

                # Check if this process is a child of our process tree
                ppid_line = None
                name_line = None
                for line in status_text.splitlines():
                    if line.startswith("PPid:"):
                        ppid_line = line.split(":", 1)[1].strip()
                    if line.startswith("Name:"):
                        name_line = line.split(":", 1)[1].strip()

                if ppid_line is None or name_line is None:
                    continue

                # Walk up the process tree to see if this is a descendant
                # of our process. Check both direct children and grandchildren
                # (SDK spawns node which spawns claude).
                if not self._is_descendant_of(pid, my_pid):
                    continue

                # Match claude or node processes (Claude CLI runs as node)
                if "claude" in name_line.lower() or "node" in name_line.lower():
                    try:
                        os.kill(pid, signal.SIGTERM)
                        killed.append((pid, name_line))
                        logger.info(
                            f"TASK-FIX-ASPF-004: Sent SIGTERM to child process "
                            f"pid={pid} name={name_line}"
                        )
                    except ProcessLookupError:
                        logger.debug(
                            f"TASK-FIX-ASPF-004: Process pid={pid} already exited"
                        )
                    except PermissionError:
                        logger.warning(
                            f"TASK-FIX-ASPF-004: Permission denied sending SIGTERM "
                            f"to pid={pid} name={name_line}"
                        )
        except OSError as e:
            logger.warning(f"TASK-FIX-ASPF-004: Error scanning /proc: {e}")

        if killed:
            logger.info(
                f"TASK-FIX-ASPF-004: Terminated {len(killed)} child process(es): "
                f"{[(pid, name) for pid, name in killed]}"
            )
        else:
            logger.debug("TASK-FIX-ASPF-004: No child claude processes found to kill")

    @staticmethod
    def _is_descendant_of(pid: int, ancestor_pid: int, max_depth: int = 10) -> bool:
        """Check if ``pid`` is a descendant of ``ancestor_pid`` via /proc.

        Walks the PPid chain up to ``max_depth`` levels to avoid infinite
        loops from corrupted /proc data.

        Args:
            pid: Process ID to check.
            ancestor_pid: Potential ancestor process ID.
            max_depth: Maximum depth to walk up the tree (default: 10).

        Returns:
            True if ``pid`` is a descendant of ``ancestor_pid``.
        """
        current = pid
        for _ in range(max_depth):
            try:
                status_text = Path(f"/proc/{current}/status").read_text()
            except (OSError, PermissionError):
                return False
            for line in status_text.splitlines():
                if line.startswith("PPid:"):
                    ppid = int(line.split(":", 1)[1].strip())
                    if ppid == ancestor_pid:
                        return True
                    if ppid <= 1:
                        return False  # Reached init/systemd
                    current = ppid
                    break
            else:
                return False  # No PPid line found
        return False

    def _kill_child_processes_fallback(self, my_pid: int) -> None:
        """Kill child claude processes on non-Linux platforms.

        Tries ``psutil`` first (optional dependency), then falls back to
        ``pgrep`` + ``ps`` which are available on macOS and most BSDs.
        """
        try:
            import psutil
            self._kill_child_processes_psutil(my_pid, psutil)
        except ImportError:
            logger.debug(
                "TASK-FIX-DFCB: psutil not available, falling back to pgrep"
            )
            self._kill_child_processes_pgrep(my_pid)

    def _kill_child_processes_psutil(self, my_pid: int, psutil_mod: Any) -> None:
        """Kill child claude/node processes using psutil.

        Args:
            my_pid: Current process ID.
            psutil_mod: The ``psutil`` module (passed to avoid top-level import).
        """
        killed: list = []
        try:
            parent = psutil_mod.Process(my_pid)
            for child in parent.children(recursive=True):
                try:
                    name = child.name().lower()
                    if "claude" not in name and "node" not in name:
                        continue
                    child.terminate()
                    killed.append((child.pid, child.name()))
                    logger.info(
                        f"TASK-FIX-DFCB: Sent SIGTERM to child process "
                        f"pid={child.pid} name={child.name()} (via psutil)"
                    )
                except (psutil_mod.NoSuchProcess, psutil_mod.AccessDenied) as exc:
                    logger.debug(
                        f"TASK-FIX-DFCB: Could not signal process: {exc}"
                    )
        except (psutil_mod.NoSuchProcess, psutil_mod.AccessDenied) as exc:
            logger.warning(
                f"TASK-FIX-DFCB: Error accessing process tree via psutil: {exc}"
            )

        if killed:
            logger.info(
                f"TASK-FIX-DFCB: Terminated {len(killed)} child process(es) "
                f"via psutil: {killed}"
            )
        else:
            logger.debug(
                "TASK-FIX-DFCB: No child claude processes found (psutil)"
            )

    def _kill_child_processes_pgrep(self, my_pid: int) -> None:
        """Kill child claude/node processes using ``pgrep`` and ``ps``.

        Fallback for macOS/BSD when ``psutil`` is not installed.
        Uses ``pgrep -P <pid>`` to find children and grandchildren,
        then ``ps -p <pid> -o comm=`` to check process names.
        """
        import subprocess as sp

        killed: list = []
        try:
            # Find direct children
            result = sp.run(
                ["pgrep", "-P", str(my_pid)],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                logger.debug(
                    "TASK-FIX-DFCB: pgrep found no child processes"
                )
                return

            child_pids = [
                int(p) for p in result.stdout.strip().splitlines() if p.strip()
            ]

            # Also collect grandchildren (SDK -> node -> claude)
            all_pids: set = set(child_pids)
            for cpid in child_pids:
                gc_result = sp.run(
                    ["pgrep", "-P", str(cpid)],
                    capture_output=True, text=True, timeout=5,
                )
                if gc_result.returncode == 0:
                    for line in gc_result.stdout.strip().splitlines():
                        if line.strip():
                            all_pids.add(int(line.strip()))

            # Check each process name and kill claude/node matches
            for pid in all_pids:
                try:
                    ps_result = sp.run(
                        ["ps", "-p", str(pid), "-o", "comm="],
                        capture_output=True, text=True, timeout=5,
                    )
                    if ps_result.returncode != 0:
                        continue
                    name = ps_result.stdout.strip().lower()
                    if "claude" not in name and "node" not in name:
                        continue
                    os.kill(pid, signal.SIGTERM)
                    killed.append((pid, name))
                    logger.info(
                        f"TASK-FIX-DFCB: Sent SIGTERM to child process "
                        f"pid={pid} name={name} (via pgrep)"
                    )
                except ProcessLookupError:
                    logger.debug(
                        f"TASK-FIX-DFCB: Process pid={pid} already exited"
                    )
                except PermissionError:
                    logger.warning(
                        f"TASK-FIX-DFCB: Permission denied sending SIGTERM "
                        f"to pid={pid}"
                    )
        except FileNotFoundError:
            logger.warning(
                "TASK-FIX-DFCB: pgrep not found on this platform, "
                "cannot kill child claude processes"
            )
        except sp.TimeoutExpired:
            logger.warning("TASK-FIX-DFCB: pgrep timed out")
        except OSError as exc:
            logger.warning(f"TASK-FIX-DFCB: Error running pgrep: {exc}")

        if killed:
            logger.info(
                f"TASK-FIX-DFCB: Terminated {len(killed)} child process(es) "
                f"via pgrep: {killed}"
            )
        else:
            logger.debug(
                "TASK-FIX-DFCB: No child claude processes found (pgrep)"
            )

    async def invoke_player(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        mode: Optional[str] = None,
        max_turns: int = 5,
        documentation_level: str = "minimal",
        context: str = "",
        remaining_budget: Optional[float] = None,
    ) -> AgentInvocationResult:
        """Invoke Player agent via task-work delegation or Claude Agents SDK.

        When task-work delegation is enabled (use_task_work_delegation=True),
        the Player delegates to `guardkit task-work --implement-only` which
        leverages the full subagent infrastructure.

        When delegation is disabled (legacy mode), uses direct SDK invocation.

        The Player agent:
        - Has full file system access (Read, Write, Edit, Bash)
        - Works in isolated worktree
        - Implements code and writes tests
        - Creates JSON report at .guardkit/autobuild/{task_id}/player_turn_{turn}.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            requirements: Task requirements (from task markdown)
            feedback: Optional Coach feedback from previous turn (string or Coach decision dict)
            mode: Development mode ("standard", "tdd", or "bdd"), passed to task-work.
                If not provided, uses the instance's development_mode.
            max_turns: Maximum turns allowed for this orchestration (default: 5).
                Used to calculate approaching_limit flag for escape hatch pattern.
            documentation_level: Documentation level for file count constraint validation
                ("minimal", "standard", or "comprehensive"). Default: "minimal" for AutoBuild.
            context: Job-specific context from Graphiti (role constraints, quality gates,
                turn states). Included in Player prompt but kept separate from requirements.
                Default: "" (empty string, no context).
            remaining_budget: Optional remaining wall-clock budget in seconds.
                When provided, sdk_timeout_seconds is capped at this value for
                this invocation then restored. Used to honour per-turn budgets
                and prevent Player from starting turns it cannot finish. (TASK-VRF-003)

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            AgentInvocationError: If invocation fails
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        # TASK-FIX-CAUD-PREFLIGHT-C3B0: Pre-turn-1 git check-ignore fail-fast
        # gate. Walks the task's planned target list through ``git
        # check-ignore`` in the worktree before any SDK turn runs. If a
        # planned target IS ignored, raises ``AgentInvocationError`` with
        # the exact matched rule so the operator can either rebase the
        # worktree (if the rule is from project-root .gitignore) or pick
        # a non-ignored target. Skipped when no plan or frontmatter list
        # is available (identical to the no-plan branch in plan-audit).
        if turn == 1:
            self._run_preflight_ignore_gate(task_id)

        # TASK-FIX-VL06: Record baseline commit before SDK invocation
        # to prevent cross-task file attribution in parallel waves
        if self._baseline_commit is None:
            self._record_baseline()

        # TASK-ASF-008: Calculate dynamic SDK timeout based on task characteristics
        # TASK-VRF-003: Cap SDK timeout at remaining budget (mirrors invoke_coach pattern)
        effective_timeout = self._calculate_sdk_timeout(task_id, remaining_budget=remaining_budget)
        original_timeout = self.sdk_timeout_seconds
        self.sdk_timeout_seconds = effective_timeout

        # Use instance development_mode if mode not provided
        effective_mode = mode if mode is not None else self.development_mode

        # Calculate if we're approaching the turn limit (escape hatch trigger)
        approaching_limit = turn >= max_turns - 1  # True when 2 or fewer turns remain

        try:
            # Write turn context for Player to read (includes approaching_limit)
            self._write_turn_context(task_id, turn, max_turns, approaching_limit)

            # Write Coach feedback for task-work to read (if present and not turn 1)
            if feedback and turn > 1:
                self._write_coach_feedback(task_id, turn, feedback)

            # Route based on implementation_mode from task frontmatter
            # Direct mode tasks bypass task-work delegation (no plan required)
            impl_mode = self._get_implementation_mode(task_id)
            if impl_mode == "direct":
                logger.info(
                    f"Routing to direct Player path for {task_id} (implementation_mode=direct)"
                )
                return await self._invoke_player_direct(
                    task_id=task_id,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=max_turns,
                    context=context,
                )

            # Choose invocation method based on feature flag (task-work or legacy modes)
            if self.use_task_work_delegation:
                logger.info(
                    f"Invoking Player via task-work delegation for {task_id} (turn {turn})"
                )

                # Ensure task is in design_approved state before delegation
                # This bridges AutoBuild state with task-work --implement-only requirements
                self._ensure_design_approved_state(task_id)

                result = await self._invoke_task_work_implement(
                    task_id=task_id,
                    mode=effective_mode,
                    documentation_level=documentation_level,
                    turn=turn,
                    requirements=requirements,
                    feedback=feedback,
                    max_turns=max_turns,
                    context=context,
                )

                duration = time.time() - start_time

                if result.success:
                    # Create Player report from task-work results
                    # AgentInvoker._invoke_task_work_implement() writes task_work_results.json
                    # after parsing task-work output. This method transforms it to
                    # player_turn_{turn}.json format expected by the orchestrator.
                    self._create_player_report_from_task_work(task_id, turn, result)

                    # Load the Player report from file (now exists)
                    report = self._load_agent_report(task_id, turn, "player")
                    self._validate_player_report(report)

                    # TASK-VPR-003: Extract SDK turn data from TaskWorkResult
                    from guardkit.orchestrator.sdk_ceiling import detect_ceiling_hit
                    _sdk_turns_used = result.sdk_turns_used
                    _sdk_max_turns = result.sdk_max_turns
                    _sdk_ceiling_hit = detect_ceiling_hit(_sdk_turns_used, _sdk_max_turns)

                    # TASK-VOPT-002: Per-turn timing instrumentation
                    logger.info(
                        "[%s] SDK invocation complete: %.1fs, %d SDK turns (%.1fs/turn avg)",
                        task_id, duration, _sdk_turns_used or 0,
                        duration / max(_sdk_turns_used or 0, 1),
                    )

                    return AgentInvocationResult(
                        task_id=task_id,
                        turn=turn,
                        agent_type="player",
                        success=True,
                        report=report,
                        duration_seconds=duration,
                        sdk_turns_used=_sdk_turns_used,
                        sdk_max_turns=_sdk_max_turns,
                        sdk_ceiling_hit=_sdk_ceiling_hit,
                        session_id=result.session_id,  # TASK-RFX-B20B
                    )
                else:
                    return AgentInvocationResult(
                        task_id=task_id,
                        turn=turn,
                        agent_type="player",
                        success=False,
                        report={},
                        duration_seconds=duration,
                        error=result.error,
                        session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
                    )
            else:
                # Legacy direct SDK invocation
                logger.info(
                    f"Invoking Player via direct SDK for {task_id} (turn {turn})"
                )
                # Build prompt for Player
                prompt = self._build_player_prompt(
                    task_id, turn, requirements, feedback, context=context
                )

                # Invoke SDK with Player permissions (Read, Write, Edit, Bash)
                # Model selection delegated to CLI default
                # TASK-RFX-B20B: Pass resume_session_id for session continuity
                await self._invoke_with_role(
                    prompt=prompt,
                    agent_type="player",
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                    permission_mode="acceptEdits",
                    resume_session_id=self._last_session_id,
                    task_id=task_id,
                    turn=turn,
                )

                # Load and validate Player report
                report = self._load_agent_report(task_id, turn, "player")
                self._validate_player_report(report)

                duration = time.time() - start_time

                # TASK-VOPT-002: Per-turn timing instrumentation (legacy path)
                logger.info(
                    "[%s] SDK invocation complete: %.1fs (legacy direct mode)",
                    task_id, duration,
                )

                return AgentInvocationResult(
                    task_id=task_id,
                    turn=turn,
                    agent_type="player",
                    success=True,
                    report=report,
                    duration_seconds=duration,
                    session_id=self._last_session_id,  # TASK-RFX-B20B
                )

        except (PlayerReportNotFoundError, PlayerReportInvalidError) as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=str(e),
                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
            )
        except SDKTimeoutError as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
            )
        except (Exception, asyncio.CancelledError) as e:
            duration = time.time() - start_time
            if isinstance(e, asyncio.CancelledError):
                logger.debug(f"CancelledError caught for {task_id}: {e}")
                error_msg = f"Cancelled: {str(e)}"
            else:
                error_msg = f"Unexpected error: {str(e)}"
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=error_msg,
                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
            )
        finally:
            # TASK-ASF-008: Restore original timeout after invocation
            self.sdk_timeout_seconds = original_timeout

    async def invoke_coach(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        remaining_budget: Optional[float] = None,
        evidence_bundle: Optional["CoachEvidenceBundle"] = None,
        coach_context: Optional[str] = None,
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
    ) -> AgentInvocationResult:
        """Invoke Coach agent via Claude Agents SDK with honesty verification.

        The Coach agent:
        - Has read-only access (Read, Bash only)
        - Works in same worktree as Player
        - Validates implementation independently
        - Receives honesty verification context for Player claims
        - Creates JSON decision at .guardkit/autobuild/{task_id}/coach_turn_{turn}.json

        Args:
            task_id: Task identifier
            turn: Current turn number
            requirements: Original task requirements
            player_report: Player's report from current turn
            remaining_budget: Optional remaining wall-clock budget in seconds.
                When provided, sdk_timeout_seconds is capped at this value for
                this invocation then restored. Used to honour per-turn budgets
                and Coach grace periods. (TASK-ABFIX-004)
            evidence_bundle: Optional ``CoachEvidenceBundle`` produced by
                ``CoachValidator.gather_evidence`` upstream (TASK-HMIG-008R Part B).
                When provided, the bundle's pre-computed ``HonestyVerification``
                is used as the canonical honesty channel — ``_verify_player_claims``
                is NOT re-run. This avoids duplicate honesty verification and
                preserves Layer-1 ``resolved_paths`` annotations that
                ``gather_evidence`` produced via state_bridge identity resolution
                (TASK-FIX-1B4A). The bundle is also rendered into the Coach
                prompt as structured evidence so the LLM Coach can read
                deterministic gate outputs (coverage, plan_audit, bdd,
                arch_review, tests) without re-deriving them.
            coach_context: Optional Graphiti / coach context string. Passed
                through to ``_build_coach_prompt`` for inclusion in the prompt.
            acceptance_criteria: Optional structured ACs (``[{"id","text"}]``)
                threaded into the Coach prompt so the synthesis verdict can
                carry a populated ``criteria_verification`` per AC
                (TASK-ARCH-COACHBFULL AC-4 — the run-19 empty-array fix) and so
                the B-full Phase-A gather (TASK-ARCH-COACHBFULL AC-1) has the
                explicit per-AC checklist to investigate against. When ``None``
                the prompt omits the per-criterion section (pre-COACHBFULL
                behaviour).

        Returns:
            AgentInvocationResult with Coach's decision

        Raises:
            AgentInvocationError: If invocation fails
            CoachDecisionNotFoundError: If Coach doesn't create decision
            CoachDecisionInvalidError: If decision JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        # TASK-ABFIX-004: Cap SDK timeout at remaining budget (mirrors invoke_player pattern)
        effective_timeout = self._calculate_sdk_timeout(task_id, remaining_budget=remaining_budget)
        original_timeout = self.sdk_timeout_seconds
        self.sdk_timeout_seconds = effective_timeout

        try:
            # TASK-HMIG-008R Part C: honesty channel unification.
            # When evidence_bundle is provided (autobuild primary path),
            # use the bundle's pre-computed HonestyVerification — it was
            # generated by CoachValidator.gather_evidence with state_bridge
            # identity resolution (Layer 1 / TASK-FIX-1B4A) and is richer
            # than what _verify_player_claims would produce here.
            # When evidence_bundle is None (legacy callers, GUARDKIT_COACH_LEGACY=1
            # fallback path), compute honesty internally as before.
            if evidence_bundle is not None:
                honesty_verification = evidence_bundle.honesty
            else:
                honesty_verification = self._verify_player_claims(player_report)

            # TASK-ARCH-COACHSPLIT (D-3): default to TOOLLESS, grammar-enforced
            # verdict synthesis over the deterministic evidence bundle. The
            # bundle (gather_evidence) already carries the test/coverage/
            # honesty/plan_audit/bdd/arch_review signal the legacy tool-using
            # Coach would investigate, so the Coach can synthesise its verdict
            # without tools — which (a) lets the GBNF grammar enforce the
            # verdict schema (llama.cpp hard-rejects grammar+tools) and (b)
            # eliminates the run-18 tool-parse HTTP 500. GUARDKIT_COACH_SYNTHESIS=0
            # restores the legacy tool-using Coach.
            #
            # Synthesis is gated on the bundle ACTUALLY existing: a toolless
            # "synthesise over the evidence bundle" prompt is incoherent (and an
            # absence-of-failure false-green hazard — the prompt would assert a
            # bundle that was never rendered and the structured guards would be
            # dropped) when no bundle was gathered. Callers without a bundle —
            # the GUARDKIT_COACH_LEGACY=1 fallback after a CoachValidator
            # exception (autobuild.py `_invoke_coach_legacy`), or any direct
            # invoke_coach caller — keep the tool-using Coach so it can
            # investigate with Read/Bash/Grep/Glob in place of the absent
            # deterministic evidence. The autobuild PRIMARY path always passes a
            # bundle (gather_evidence), so it always synthesises.
            synthesis_enabled = (
                _coach_synthesis_enabled() and evidence_bundle is not None
            )

            # TASK-ARCH-COACHBFULL (B-full): optional tool-using Phase-A gather
            # BEFORE the toolless Phase-B synthesis. When enabled (opt-in), the
            # Coach investigates with Read/Bash/Grep/Glob and produces findings
            # TEXT (not a verdict); those findings are threaded into the
            # synthesis prompt below. The gather is gated on synthesis being
            # active (a B-full gather only makes sense ahead of the toolless
            # grammar verdict) and on the opt-in flag. Any failure inside
            # _invoke_coach_gather returns None → degrade to B-min (strict
            # dominance, AC-2). A genuine cancellation (CancelledError) is NOT
            # swallowed there and propagates to the except blocks below (AC-5).
            gather_findings: Optional[str] = None
            if synthesis_enabled and _coach_gather_enabled():
                # effective_timeout is currently in self.sdk_timeout_seconds;
                # cap Phase A at a fraction of it, floored, never above it.
                gather_timeout = min(
                    effective_timeout,
                    max(
                        _COACH_GATHER_BUDGET_MIN_S,
                        int(effective_timeout * _COACH_GATHER_BUDGET_FRACTION),
                    ),
                )
                gather_findings = await self._invoke_coach_gather(
                    task_id=task_id,
                    turn=turn,
                    requirements=requirements,
                    player_report=player_report,
                    honesty_verification=honesty_verification,
                    evidence_bundle=evidence_bundle,
                    acceptance_criteria=acceptance_criteria,
                    gather_timeout=gather_timeout,
                )

            # Build prompt for Coach with verification context.
            prompt = self._build_coach_prompt(
                task_id, turn, requirements, player_report, honesty_verification,
                acceptance_criteria=acceptance_criteria,
                evidence_bundle=evidence_bundle,
                coach_context=coach_context,
                synthesis=synthesis_enabled,
                gather_findings=gather_findings,
            )

            # Invoke the Coach. In both paths return_events=True so the typed
            # HarnessEvent stream comes back for coach_output_parser
            # (TASK-FIX-COACHOUT01 Shape A) — the verdict is parsed from the
            # response text and the orchestrator writes coach_turn_N.json
            # itself; Coach never writes (ADR FB-004, read-only invariant).
            if synthesis_enabled:
                # Load the GBNF verdict grammar; degrade to prompt-only (still
                # toolless) if the packaged grammar can't be read so a
                # packaging glitch never hard-fails the Coach.
                grammar: Optional[str] = None
                try:
                    from guardkit.orchestrator.coach_grammar import (
                        load_coach_verdict_grammar,
                    )

                    grammar = load_coach_verdict_grammar()
                except Exception as exc:  # noqa: BLE001 — degrade, never hard-fail
                    logger.warning(
                        "TASK-ARCH-COACHSPLIT: failed to load Coach verdict "
                        "grammar (%s); running TOOLLESS synthesis WITHOUT a "
                        "grammar constraint (prompt-only). The verdict schema "
                        "is then only prompt-enforced, not grammar-guaranteed.",
                        exc,
                    )

                # allowed_tools=[] makes the harness toolless on EVERY
                # substrate (the SDK harness reads its tool surface from the
                # constructor allowed_tools, which select_harness threads from
                # here). synthesis=True dispatches through invoke_synthesis.
                result_tuple = await self._invoke_with_role(
                    prompt=prompt,
                    agent_type="coach",
                    allowed_tools=[],
                    permission_mode="bypassPermissions",
                    task_id=task_id,
                    turn=turn,
                    return_events=True,
                    synthesis=True,
                    grammar=grammar,
                )
            else:
                # Legacy tool-using Coach (GUARDKIT_COACH_SYNTHESIS disabled).
                # Read-only tools; verdict still parsed from response text.
                result_tuple = await self._invoke_with_role(
                    prompt=prompt,
                    agent_type="coach",
                    allowed_tools=["Read", "Bash", "Grep", "Glob"],
                    permission_mode="bypassPermissions",
                    task_id=task_id,
                    turn=turn,
                    return_events=True,
                )
            assert result_tuple is not None, (
                "_invoke_with_role(return_events=True) must return a tuple "
                "on success; got None"
            )
            _, harness_events = result_tuple

            # TASK-FIX-COACHOUT01 Shape A: extract the structured verdict from
            # Coach's response text and persist coach_turn_N.json from the
            # orchestrator side. The parser raises CoachDecisionNotFoundError
            # / CoachDecisionInvalidError with messages COACHSF01 greps for
            # (autobuild.py:5676-5678) on every failure path — the exceptions
            # propagate to the existing except block at the bottom of this
            # method, which converts them to AgentInvocationResult(
            # success=False, error=str(e)). COACHSF01 then fires the
            # synthetic-feedback safety net unchanged.
            from guardkit.orchestrator.coach_output_parser import (
                extract_and_write as _coach_extract_and_write,
            )
            coach_output_path = self._get_report_path(task_id, turn, "coach")
            _coach_extract_and_write(
                harness_events=harness_events,
                task_id=task_id,
                turn=turn,
                output_path=coach_output_path,
            )

            # Load and validate Coach decision — the file on disk was just
            # written by the parser, so this re-read keeps the existing
            # consumer contract intact. _validate_coach_decision still owns
            # the deep schema check (criteria_verification, severity values,
            # decision-specific field presence) the parser doesn't replicate.
            decision = self._load_agent_report(task_id, turn, "coach")
            self._validate_coach_decision(decision)

            # Add honesty verification to decision for tracking
            decision["honesty_verification"] = {
                "verified": honesty_verification.verified,
                "honesty_score": honesty_verification.honesty_score,
                "discrepancy_count": len(honesty_verification.discrepancies),
            }

            duration = time.time() - start_time

            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=True,
                report=decision,
                duration_seconds=duration,
            )

        except (CoachDecisionNotFoundError, CoachDecisionInvalidError) as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=duration,
                error=str(e),
            )
        except SDKTimeoutError as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
            )
        except Exception as e:
            duration = time.time() - start_time
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="coach",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"Unexpected error: {str(e)}",
            )
        finally:
            # TASK-ABFIX-004: Restore original timeout after invocation
            self.sdk_timeout_seconds = original_timeout

    async def _invoke_coach_gather(
        self,
        *,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        honesty_verification: Optional[HonestyVerification],
        evidence_bundle: Optional["CoachEvidenceBundle"],
        acceptance_criteria: Optional[List[Dict[str, str]]],
        gather_timeout: int,
    ) -> Optional[str]:
        """Phase-A of the B-full investigating Coach: tool-using gather.

        TASK-ARCH-COACHBFULL. Runs a tool-bound Coach invocation
        (``Read``/``Bash``/``Grep``/``Glob`` — read-only, FB-004 preserved)
        that INVESTIGATES the worktree (reads changed files, runs the focused
        test, checks the ACs it is unsure about) and emits investigation
        *findings text*, NOT a fenced JSON verdict. The findings are returned
        as a string for the caller to thread into the toolless Phase-B
        synthesis prompt.

        **Strict dominance (AC-2).** This method NEVER raises an ordinary
        exception: a tool-parse error (the run-18 HTTP-500 class can recur on
        the tool-bound path), an SDK timeout, an ``AgentInvocationError``, or
        empty findings all return ``None`` so the caller degrades to B-min
        (synthesis over the deterministic bundle alone). The turn is never
        failed by a broken gather.

        **Cancellation (AC-5).** ``asyncio.CancelledError`` derives from
        ``BaseException``, NOT ``Exception``, so it is deliberately NOT caught
        here: a genuine operator cancellation mid-gather propagates to
        ``invoke_coach``'s except blocks and aborts the turn rather than
        silently burning the Phase-B budget. The per-call cancel monitor inside
        ``_invoke_with_role`` (agent_invoker.py:3220) covers this gather call
        the same way it covers any other invocation.

        **Budget (AC-5).** ``self.sdk_timeout_seconds`` is set to
        ``gather_timeout`` for the duration of the gather and restored in
        ``finally`` so the subsequent Phase-B synthesis runs at the full
        effective timeout.

        Args:
            gather_timeout: Per-invocation timeout slice for Phase A (already
                bounded by the caller to a fraction of the effective Coach
                timeout).

        Returns:
            The concatenated findings text, or ``None`` on any failure / empty
            output (signal to degrade to B-min).
        """
        prev_timeout = self.sdk_timeout_seconds
        self.sdk_timeout_seconds = gather_timeout
        try:
            prompt = self._build_coach_gather_prompt(
                task_id=task_id,
                turn=turn,
                requirements=requirements,
                player_report=player_report,
                honesty_verification=honesty_verification,
                evidence_bundle=evidence_bundle,
                acceptance_criteria=acceptance_criteria,
            )
            # Tool-bound, read-only Coach. synthesis=False ⇒ dispatched through
            # harness.invoke (NOT invoke_synthesis); no grammar. return_events
            # so we can extract the findings text from the typed stream.
            result_tuple = await self._invoke_with_role(
                prompt=prompt,
                agent_type="coach",
                allowed_tools=["Read", "Bash", "Grep", "Glob"],
                permission_mode="bypassPermissions",
                task_id=task_id,
                turn=turn,
                return_events=True,
                synthesis=False,
            )
            if result_tuple is None:
                return None
            _, harness_events = result_tuple

            # Reuse the substrate-agnostic text collectors the verdict parser
            # uses. Prefer the content channel; fall back to the reasoning
            # channel for hybrid-reasoning models that emit their analysis
            # there (TASK-FIX-COACHBUDG01).
            from guardkit.orchestrator.coach_output_parser import (
                _collect_assistant_reasoning,
                _collect_assistant_text,
            )

            findings = _collect_assistant_text(harness_events).strip()
            if not findings:
                findings = _collect_assistant_reasoning(harness_events).strip()
            if not findings:
                logger.info(
                    "TASK-ARCH-COACHBFULL: Phase-A gather produced no findings "
                    "for %s turn %s; degrading to B-min synthesis.",
                    task_id, turn,
                )
                return None
            logger.info(
                "TASK-ARCH-COACHBFULL: Phase-A gather produced %d chars of "
                "findings for %s turn %s.", len(findings), task_id, turn,
            )
            return findings
        except Exception as exc:  # noqa: BLE001 — strict dominance: never fail the turn
            logger.warning(
                "TASK-ARCH-COACHBFULL: Phase-A gather failed for %s turn %s "
                "(%s: %s); degrading to B-min synthesis.",
                task_id, turn, type(exc).__name__, exc,
            )
            return None
        finally:
            self.sdk_timeout_seconds = prev_timeout

    def _build_coach_gather_prompt(
        self,
        *,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        honesty_verification: Optional[HonestyVerification],
        evidence_bundle: Optional["CoachEvidenceBundle"],
        acceptance_criteria: Optional[List[Dict[str, str]]],
    ) -> str:
        """Build the Phase-A gather prompt (TASK-ARCH-COACHBFULL).

        Frames the turn as an INVESTIGATION whose output is findings text — a
        per-AC compliance checklist (the Block paper's ✅/❌ + notes) — and
        explicitly NOT a fenced JSON verdict (that is Phase B's job). The
        deterministic evidence bundle and honesty verification are rendered as
        the starting dossier so the Coach knows what has already been checked
        and where to focus its probing (read changed files, run the focused
        test, confirm an AC it cannot confirm from the dossier alone).
        """
        # Reuse the existing renderers for the dossier the Coach starts from.
        evidence_section = ""
        if evidence_bundle is not None:
            evidence_section = self._render_evidence_bundle_section(
                evidence_bundle
            )

        honesty_for_section = honesty_verification
        if (
            evidence_bundle is not None
            and evidence_bundle.honesty is not None
        ):
            honesty_for_section = evidence_bundle.honesty
        honesty_section = ""
        if evidence_bundle is not None and honesty_for_section is not None:
            honesty_section = self._render_bundle_honesty_section(
                honesty_for_section
            )
        elif honesty_for_section:
            honesty_section = (
                "\n## Honesty Verification (Pre-Validated)\n\n"
                + format_verification_context(honesty_for_section)
                + "\n"
            )

        # Per-AC checklist the gather must work through.
        criteria_section = ""
        if acceptance_criteria:
            lines = [
                "## Acceptance Criteria to Investigate",
                "",
                "Work through EACH criterion and report whether the worktree "
                "actually satisfies it:",
                "",
            ]
            for criterion in acceptance_criteria:
                lines.append(f"- **{criterion['id']}**: {criterion['text']}")
            criteria_section = "\n".join(lines) + "\n"

        return f"""You are the Coach agent, performing an INVESTIGATION pass \
(Phase A of two).

Task ID: {task_id}
Turn: {turn}

**THIS IS NOT THE VERDICT.** Your job here is to INVESTIGATE and produce
*findings*, which a second toolless pass will turn into the formal verdict. Do
NOT emit a fenced ```json decision block in this response — emit prose findings.

You have READ-ONLY tools: Read, Bash, Grep, Glob. Use them to verify the work
on disk rather than trusting the Player's report:
- Read the changed files named in the Player's report.
- Run the focused test(s) for this task if a test command is available.
- For any acceptance criterion you cannot confirm from the dossier below,
  probe the code directly (grep for the required behaviour; check that the
  implementation is real, not a stub returning a hardcoded default).

## Original Requirements

{requirements}
{criteria_section}## Player's Report

{json.dumps(player_report, indent=2)}
{evidence_section}{honesty_section}
## What to Produce

A per-criterion compliance checklist — for EACH acceptance criterion, one line:

    <AC-ID>: PASS|FAIL|UNSURE — what you checked and what you found

Then a short "IMMEDIATE ACTIONS NEEDED" list naming any criterion that is
unmet, stubbed, or unverifiable, with the file/line evidence you found.

Be concrete and cite file paths and line numbers. These findings are advisory
input to the verdict pass — absent or unverifiable evidence is a FAIL/UNSURE,
never an assumed pass. End your response with the checklist; do not write a
JSON verdict.
"""

    def _build_player_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str],
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
        context: str = "",
        design_context: Optional["DesignContext"] = None,
    ) -> str:
        """Build prompt for Player agent invocation with acceptance criteria.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Task requirements
            feedback: Optional feedback from previous Coach turn
            acceptance_criteria: Optional list of acceptance criteria with id and text
            context: Job-specific context from Graphiti (role constraints, quality gates,
                turn states). Included before requirements for prompt context.
            design_context: Optional design context for UI implementation tasks

        Returns:
            Formatted prompt string for Player agent
        """
        feedback_section = ""
        if feedback and turn > 1:
            feedback_section = f"""
## Coach Feedback from Turn {turn - 1}

{feedback}

Please address all feedback points in this turn.
"""

        # Build context section if provided (Graphiti job-specific context)
        context_section = ""
        if context:
            context_section = f"""
## Job-Specific Context

{context}
"""

        # Build design context section if provided
        design_section = ""
        if design_context:
            design_section = f"""
## Design Context

**Source**: {design_context.source}

### Elements in Design
{self._format_design_elements(design_context.elements)}

### Design Tokens
{self._format_design_tokens(design_context.tokens)}

### Design Boundaries (Prohibition Checklist)
{self._format_design_constraints(design_context.constraints)}

### Instructions
- Generate components matching the design EXACTLY
- Apply design tokens with no approximation
- DO NOT add anything not shown in the design
- Delegate to the appropriate UI specialist
"""

        # Build acceptance criteria section if provided
        criteria_section = ""
        if acceptance_criteria:
            criteria_lines = ["## Acceptance Criteria", ""]
            criteria_lines.append("You MUST create a completion_promise for each criterion:")
            criteria_lines.append("")
            for criterion in acceptance_criteria:
                criteria_lines.append(f"- **{criterion['id']}**: {criterion['text']}")
            criteria_section = "\n".join(criteria_lines) + "\n"

        # Build completion promises example
        promises_example = ""
        if acceptance_criteria:
            example_promises = []
            for criterion in acceptance_criteria[:2]:  # Show first 2 as examples
                example_promises.append(f'''    {{
      "criterion_id": "{criterion['id']}",
      "criterion_text": "{criterion['text'][:50]}...",
      "status": "complete",
      "evidence": "Description of what you did for this criterion",
      "test_file": "tests/test_relevant.py",
      "implementation_files": ["src/file.py"]
    }}''')
            promises_example = f'''
  "completion_promises": [
{",".join(example_promises)}
  ],'''

        prompt = f"""You are the Player agent. Implement the following task.

Task ID: {task_id}
Turn: {turn}
{context_section}{design_section}
## Requirements

{requirements}
{criteria_section}{feedback_section}

## Your Responsibilities

1. Implement the code to satisfy the requirements
2. Write comprehensive tests
3. Run the tests and verify they pass
4. Create your report with completion promises for each acceptance criterion

## Report Format

After implementing, write your report to:
{self.worktree_path}/.guardkit/autobuild/{task_id}/player_turn_{turn}.json

Your report MUST be valid JSON with these fields:
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "files_modified": ["list", "of", "files"],
  "files_created": ["list", "of", "new", "files"],
  "tests_written": ["list", "of", "test", "files"],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "Brief summary of test results",
  "implementation_notes": "What you implemented and why",
  "concerns": ["any", "concerns", "or", "blockers"],
  "requirements_addressed": ["requirements", "completed"],
  "requirements_remaining": ["requirements", "still", "pending"],{promises_example}
}}

**IMPORTANT**: For each acceptance criterion, create a completion_promise with:
- criterion_id: The ID (e.g., "AC-001")
- criterion_text: The full criterion text
- status: "complete" or "incomplete"
- evidence: What you did to satisfy this criterion
- test_file: Path to test file validating this criterion (if applicable)
- implementation_files: List of files modified/created for this criterion

Follow the report format specified in your agent definition.
"""
        # TASK-PSN-003: Append format reinforcement for complex tasks.
        # Placing it at the END of the prompt exploits recency bias so the
        # schema stays fresh even after many SDK turns.
        if acceptance_criteria and len(acceptance_criteria) >= REINFORCEMENT_CRITERIA_THRESHOLD:
            prompt += PROMISE_FORMAT_REMINDER

        return prompt

    def _format_design_elements(self, elements: List[Dict[str, Any]]) -> str:
        """Format design elements for prompt.

        Args:
            elements: List of design element dictionaries

        Returns:
            Formatted markdown string of design elements
        """
        if not elements:
            return "No elements specified"
        lines = []
        for elem in elements:
            name = elem.get("name", "Unknown")
            elem_type = elem.get("type", "component")
            props = elem.get("props", [])
            variants = elem.get("variants", [])
            line = f"- **{name}** ({elem_type})"
            if props:
                line += f"\n  Props: {', '.join(props)}"
            if variants:
                line += f"\n  Variants: {', '.join(variants)}"
            lines.append(line)
        return "\n".join(lines)

    def _format_design_tokens(self, tokens: Dict[str, Any]) -> str:
        """Format design tokens for prompt.

        Args:
            tokens: Dictionary of design tokens

        Returns:
            Formatted JSON string of design tokens
        """
        if not tokens:
            return "No tokens specified"
        return json.dumps(tokens, indent=2)

    def _format_design_constraints(self, constraints: Dict[str, Any]) -> str:
        """Format design constraints/prohibition checklist.

        Args:
            constraints: Dictionary of design constraints

        Returns:
            Formatted markdown string of constraints
        """
        if not constraints:
            return "No specific constraints"
        lines = ["The following constraints MUST be followed:"]
        for key, value in constraints.items():
            if value:
                formatted_key = key.replace("_", " ").title()
                lines.append(f"- ❌ {formatted_key}")
        return "\n".join(lines)

    def _build_coach_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
        honesty_verification: Optional[HonestyVerification] = None,
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
        design_context: Optional["DesignContext"] = None,
        evidence_bundle: Optional["CoachEvidenceBundle"] = None,
        coach_context: Optional[str] = None,
        synthesis: bool = False,
        gather_findings: Optional[str] = None,
    ) -> str:
        """Build prompt for Coach agent invocation with promise verification.

        Args:
            task_id: Task identifier
            turn: Turn number
            requirements: Original task requirements
            player_report: Player's report from current turn
            honesty_verification: Optional verification results for Player claims.
                When ``evidence_bundle`` is also provided, the bundle's
                ``honesty`` field is the canonical source (channel unification
                per plan §4); this parameter then serves only as a legacy
                fallback path for callers that pass it directly.
            acceptance_criteria: Optional list of acceptance criteria with id and text
            design_context: Optional design context for visual verification
            evidence_bundle: Optional ``CoachEvidenceBundle`` from
                ``CoachValidator.gather_evidence`` (TASK-HMIG-008R Part C).
                When provided, the bundle is JSON-rendered into a
                ``<evidence_bundle>...</evidence_bundle>`` section so the
                LLM Coach can read deterministic gate outputs (coverage,
                plan_audit, bdd, arch_review, tests) plus the Layer-1/
                Layer-2 severity recommendations. The five
                absence-of-failure guards (AC-009 + gathering_status guard)
                are emitted in an ``<absence_of_failure_guards>`` section
                so the Coach has explicit instructions for treating absent
                evidence as ABSENT SIGNAL rather than approving on
                absence-of-failure.
            coach_context: Optional Graphiti / coach context string. When
                provided, surfaced in a ``## Coach Context`` section.
            synthesis: When ``True`` (TASK-ARCH-COACHSPLIT D-3), render the
                TOOLLESS synthesis variant: the Coach has NO tools and bases
                its verdict on the deterministic evidence bundle the
                orchestrator already gathered (tests, coverage, honesty,
                plan_audit, bdd, arch_review run independently in
                ``gather_evidence``) rather than re-investigating with
                Read/Bash/Grep/Glob. The "Your Responsibilities" section is
                rewritten accordingly and a toolless-framing banner is added.
                The Decision Format section is identical — the GBNF grammar
                enforces the same schema the examples describe.
            gather_findings: Optional Phase-A investigation findings text
                (TASK-ARCH-COACHBFULL B-full). When provided, rendered into a
                ``## Coach Investigation Findings (Phase A)`` section so the
                toolless synthesis grounds its per-AC verdict on what the
                tool-using gather pass actually found on disk. ``None`` (the
                default, and the B-min path) omits the section entirely.

        Returns:
            Formatted prompt string for Coach agent
        """
        # TASK-HMIG-008R Part C: when an evidence bundle is provided, its
        # `honesty` field is the canonical honesty channel — overriding the
        # legacy honesty_verification parameter to avoid duplicate honesty
        # sections in the prompt. The bundle's honesty was computed by
        # gather_evidence with state_bridge identity resolution and carries
        # resolved_paths annotations that the legacy parameter would lack.
        if evidence_bundle is not None and evidence_bundle.honesty is not None:
            honesty_verification = evidence_bundle.honesty

        # Build honesty verification section. Under the bundle path the
        # section is rendered as structured JSON inside an XML-like tag
        # so the LLM Coach can parse it deterministically and apply the
        # absence-of-failure guards below against specific fields. The
        # legacy free-text format is retained for back-compat callers
        # (no bundle, just honesty_verification).
        honesty_section = ""
        if evidence_bundle is not None and honesty_verification is not None:
            # Bundle path: emit structured XML-tagged JSON section.
            honesty_section = self._render_bundle_honesty_section(
                honesty_verification
            )
        elif honesty_verification:
            # Legacy path: emit prose section.
            honesty_section = f"""
## Honesty Verification (Pre-Validated)

{format_verification_context(honesty_verification)}

{"⚠️ CRITICAL DISCREPANCIES DETECTED - Factor this into your decision!" if honesty_verification.discrepancies else "✓ Player claims verified."}
"""

        # Build evidence bundle section + absence-of-failure guards (Part C).
        evidence_section = ""
        guards_section = ""
        if evidence_bundle is not None:
            evidence_section = self._render_evidence_bundle_section(
                evidence_bundle
            )
            guards_section = self._render_absence_of_failure_guards()

        # Coach context section (Graphiti / external context).
        coach_context_section = ""
        if coach_context:
            coach_context_section = f"""
## Coach Context

{coach_context}
"""

        # TASK-ARCH-COACHBFULL: Phase-A investigation findings section. Rendered
        # only when the B-full gather ran and produced findings; advisory input
        # the toolless synthesis grounds its per-AC verdict on. Absent findings
        # (B-min path) omit the section — never a new false-green: the
        # synthesis banner + absence-of-failure guards still treat
        # unverifiable evidence as FEEDBACK, not approval.
        gather_findings_section = ""
        if gather_findings and gather_findings.strip():
            gather_findings_section = f"""
## Coach Investigation Findings (Phase A)

A tool-using investigation pass ran BEFORE this verdict and probed the worktree
directly (read changed files, ran focused tests, checked acceptance criteria).
Its findings — a per-criterion compliance checklist — are below. Treat them as
authoritative evidence of what is actually on disk, on equal footing with the
Deterministic Evidence Bundle. Where a finding marks a criterion FAIL or UNSURE,
that criterion is NOT satisfied for approval purposes.

{gather_findings.strip()}
"""

        # Build acceptance criteria section for verification
        criteria_section = ""
        if acceptance_criteria:
            criteria_lines = ["## Acceptance Criteria to Verify", ""]
            criteria_lines.append("Verify EACH criterion and create a criteria_verification entry:")
            criteria_lines.append("")
            for criterion in acceptance_criteria:
                criteria_lines.append(f"- **{criterion['id']}**: {criterion['text']}")
            criteria_section = "\n".join(criteria_lines) + "\n"

        # Build criteria verification example
        verification_example = ""
        if acceptance_criteria:
            example_verifications = []
            for criterion in acceptance_criteria[:2]:  # Show first 2 as examples
                example_verifications.append(f'''    {{
      "criterion_id": "{criterion['id']}",
      "result": "verified",
      "notes": "Your reasoning for verification or rejection"
    }}''')
            verification_example = f'''
  "criteria_verification": [
{",".join(example_verifications)}
  ],'''

        # Build visual verification section if design context provided
        visual_verification_section = ""
        if design_context:
            visual_verification_section = f"""
## Visual Verification (Design Mode)

In addition to standard code review:
1. Render the generated component in a browser
2. Capture a screenshot
3. Compare against design reference using SSIM
4. Check prohibition checklist compliance
5. Report: visual fidelity score + any constraint violations

**Visual Reference**: {design_context.visual_reference or "Not available"}

Quality Gates:
- Visual fidelity: >= 95% SSIM match
- Constraint violations: Zero tolerance
- Design tokens: 100% applied (exact match)
"""

        # TASK-ARCH-COACHSPLIT (D-3): the synthesis variant frames the turn
        # as evidence-grounded verdict synthesis with NO tools, and rewrites
        # the responsibilities so the model does not try (and fail) to invoke
        # Read/Bash/Grep/Glob — it has none. The deterministic evidence the
        # tool-using gather phase would have sought has already been produced
        # by CoachValidator.gather_evidence and is rendered above.
        if synthesis:
            # Only assert that a Deterministic Evidence Bundle was rendered when
            # one actually exists. invoke_coach gates synthesis on bundle
            # presence (synthesis ⇒ a bundle was passed), so the with-bundle
            # banner is the production path; the no-bundle branch keeps this
            # builder honest if it is ever invoked with synthesis=True and no
            # bundle directly (so the prompt never claims evidence it lacks).
            if evidence_bundle is not None:
                synthesis_banner = """\
**TOOLLESS SYNTHESIS** — You have NO tools available (no Read, Bash, Grep, or
Glob). Do not attempt to run tests or read files; you cannot. The orchestrator
has ALREADY run the tests, coverage, honesty checks, plan audit, BDD oracle,
and architectural review independently — their results are in the Deterministic
Evidence Bundle above. Base your verdict ENTIRELY on that evidence, the
acceptance criteria, the Player's report, and the honesty verification.

"""
            else:
                synthesis_banner = """\
**TOOLLESS SYNTHESIS** — You have NO tools available (no Read, Bash, Grep, or
Glob). Do not attempt to run tests or read files; you cannot. No deterministic
evidence bundle was provided, so you have ONLY the acceptance criteria, the
Player's report, and the honesty verification to reason from. Absent or
unverifiable evidence is NOT a pass — when you cannot confirm a criterion from
the information here, that is FEEDBACK, not approval.

"""
            responsibilities = (
                "## Your Responsibilities\n\n"
                "1. Synthesise a verdict from the Deterministic Evidence "
                "Bundle above — do NOT attempt to investigate (you have no "
                "tools)\n"
                "2. Treat the bundle's independent_tests / tests / coverage "
                "as the authoritative test signal (the orchestrator ran "
                "them, not the Player)\n"
                "3. Verify EACH acceptance criterion against the evidence "
                "systematically\n"
                "4. Honour the absence-of-failure guards: an ABSENT or "
                "zero-cardinality oracle is NOT a pass — when the evidence "
                "for a criterion is missing, that is FEEDBACK, not approval\n"
                "5. "
                + (
                    "CONSIDER HONESTY DISCREPANCIES in your decision"
                    if honesty_verification
                    and honesty_verification.discrepancies
                    else "Either APPROVE or provide specific FEEDBACK"
                )
            )
        else:
            synthesis_banner = ""
            responsibilities = (
                "## Your Responsibilities\n\n"
                "1. Independently verify the Player's claims\n"
                "2. Run the tests yourself (don't trust Player's report)\n"
                "3. Verify EACH acceptance criterion systematically\n"
                "4. "
                + (
                    "CONSIDER HONESTY DISCREPANCIES in your decision"
                    if honesty_verification
                    and honesty_verification.discrepancies
                    else "Either APPROVE or provide specific FEEDBACK"
                )
            )

        prompt = f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

{synthesis_banner}## Original Requirements

{requirements}
{criteria_section}
## Player's Report

{json.dumps(player_report, indent=2)}
{evidence_section}{honesty_section}{guards_section}{gather_findings_section}{coach_context_section}{visual_verification_section}
{responsibilities}

## Decision Format

End your response with a fenced JSON block. Do **NOT** use Bash to write a file —
the orchestrator parses your decision directly from your response text.

The fenced JSON block MUST appear at the end of your response, after all prose
reasoning, in this exact form:

```json
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "approve" | "feedback",
  ...fields as specified below...
}}
```

For APPROVAL, the JSON block must contain:
```json
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "approve",
  "validation_results": {{
    "requirements_met": ["list", "of", "verified", "requirements"],
    "tests_run": true,
    "tests_passed": true,
    "test_command": "command you ran",
    "test_output_summary": "summary of test results",
    "code_quality": "assessment",
    "edge_cases_covered": ["list", "of", "edge", "cases"]
  }},{verification_example}
  "rationale": "Why you approved"
}}
```

For FEEDBACK, the JSON block must contain:
```json
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "feedback",
  "issues": [
    {{
      "type": "missing_requirement" | "test_failure" | "code_quality" | "edge_case",
      "severity": "critical" | "major" | "minor",
      "description": "Specific issue with file paths and line numbers",
      "requirement": "Which requirement is affected",
      "suggestion": "How to fix it"
    }}
  ],{verification_example}
  "rationale": "Why you're providing feedback"
}}
```

**IMPORTANT**: For each acceptance criterion, create a criteria_verification with:
- criterion_id: The ID (e.g., "AC-001") matching the Player's completion_promise
- result: "verified" if criterion is satisfied, "rejected" if not
- notes: Your reasoning - what you checked and found

**CRITICAL**: The fenced ```json block MUST be the last thing in your response.
Do not write any prose after the closing ``` fence. If you emit exploratory JSON
blocks earlier in your response (e.g. while sketching alternatives), the
orchestrator takes only the **last** fenced block.
"""
        return prompt

    # ------------------------------------------------------------------
    # TASK-HMIG-008R Part C — Coach prompt rendering helpers.
    # ------------------------------------------------------------------

    # Token-budget truncation thresholds (plan §4 "Token budget"):
    _COACH_BDD_DISCOVERIES_LIMIT = 20
    _COACH_BDD_ERRORS_LIMIT = 10
    _COACH_HONESTY_DISCREPANCIES_LIMIT = 20

    def _render_evidence_bundle_section(
        self,
        evidence_bundle: "CoachEvidenceBundle",
    ) -> str:
        """Render the CoachEvidenceBundle as a structured prompt section.

        Emits the bundle as JSON inside ``<evidence_bundle>...</evidence_bundle>``
        XML-like tags so the LLM Coach can locate it deterministically and
        apply the absence-of-failure guards against specific fields.

        Truncation rules (plan §4):

        * ``evidence_bundle.bdd.discoveries`` — keep first 20 entries.
        * ``evidence_bundle.bdd.errors``     — keep first 10 entries.
        * ``evidence_bundle.honesty.discrepancies`` — keep first 20 entries.

        Each truncation appends a ``"... and N more"`` marker so the Coach
        knows the list was bounded. Non-list fields are bounded by gate
        computation and pass through unchanged.

        The bundle's honesty channel is NOT duplicated here — it lives in
        the separate ``<honesty_verification>`` section emitted by
        :py:meth:`_render_bundle_honesty_section`. Both sections read from
        the same bundle.honesty value, but rendering them separately lets
        the absence-of-failure guards reference each by tag.
        """
        try:
            bundle_dict = evidence_bundle.to_dict()
        except Exception as exc:  # noqa: BLE001 — never block prompt build
            logger.error(
                "Failed to serialise evidence_bundle for Coach prompt: %s. "
                "Emitting empty bundle section so the Coach prompt still "
                "carries the absence-of-failure guards.",
                exc,
            )
            bundle_dict = {
                "gathering_status": "partial_exception",
                "gathering_error": f"bundle_serialisation_failed: {exc}",
            }

        # Truncate bdd.discoveries / bdd.errors.
        bdd = bundle_dict.get("bdd")
        if isinstance(bdd, dict):
            discoveries = bdd.get("discoveries")
            if isinstance(discoveries, list) and len(discoveries) > self._COACH_BDD_DISCOVERIES_LIMIT:
                remainder = len(discoveries) - self._COACH_BDD_DISCOVERIES_LIMIT
                bdd["discoveries"] = discoveries[: self._COACH_BDD_DISCOVERIES_LIMIT] + [
                    f"... and {remainder} more (truncated for token budget)"
                ]
            errors = bdd.get("errors")
            if isinstance(errors, list) and len(errors) > self._COACH_BDD_ERRORS_LIMIT:
                remainder = len(errors) - self._COACH_BDD_ERRORS_LIMIT
                bdd["errors"] = errors[: self._COACH_BDD_ERRORS_LIMIT] + [
                    f"... and {remainder} more (truncated for token budget)"
                ]

        # honesty.discrepancies truncation lives inside _render_bundle_honesty_section,
        # but we ALSO truncate the copy nested in bundle_dict["honesty"] so the
        # evidence-bundle JSON the Coach sees is internally consistent.
        honesty = bundle_dict.get("honesty")
        if isinstance(honesty, dict):
            discrepancies = honesty.get("discrepancies")
            if (
                isinstance(discrepancies, list)
                and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
            ):
                remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
                honesty["discrepancies"] = discrepancies[
                    : self._COACH_HONESTY_DISCREPANCIES_LIMIT
                ] + [{
                    "truncated": True,
                    "remainder": remainder,
                    "note": (
                        f"... and {remainder} more discrepancies (truncated "
                        f"for token budget). See full honesty_verification "
                        f"in coach_turn_N.json."
                    ),
                }]

        try:
            payload = json.dumps(bundle_dict, indent=2, default=str)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to JSON-encode truncated evidence_bundle: %s", exc,
            )
            payload = '{"gathering_status": "partial_exception", "gathering_error": "json_encode_failed"}'

        return f"""
## Deterministic Evidence Bundle

<evidence_bundle>
{payload}
</evidence_bundle>
"""

    def _render_bundle_honesty_section(
        self,
        honesty_verification: HonestyVerification,
    ) -> str:
        """Render the bundle's HonestyVerification as a structured prompt section.

        Sourced from ``evidence_bundle.honesty`` (channel unification per
        plan §4). Emits a JSON-structured section inside
        ``<honesty_verification>...</honesty_verification>`` tags so the
        absence-of-failure guards can reference specific fields:

        * ``honesty.discrepancies[*].claim_type``
        * ``honesty.discrepancies[*].severity``
        * ``honesty.resolved_paths`` — Layer-1 (TASK-FIX-1B4A) suppressions.

        Truncation rule: keep first 20 discrepancies (plan §4 token budget).
        """
        from dataclasses import asdict

        try:
            honesty_dict: Dict[str, Any] = asdict(honesty_verification)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to serialise honesty_verification for Coach prompt: %s",
                exc,
            )
            honesty_dict = {
                "verified": True,
                "discrepancies": [],
                "honesty_score": 1.0,
                "resolved_paths": [],
                "should_fix_count": 0,
                "serialisation_error": str(exc),
            }

        discrepancies = honesty_dict.get("discrepancies")
        if (
            isinstance(discrepancies, list)
            and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
        ):
            remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
            honesty_dict["discrepancies"] = discrepancies[
                : self._COACH_HONESTY_DISCREPANCIES_LIMIT
            ] + [{
                "truncated": True,
                "remainder": remainder,
                "note": (
                    f"... and {remainder} more discrepancies (truncated "
                    f"for token budget). See full list in coach_turn_N.json."
                ),
            }]

        try:
            payload = json.dumps(honesty_dict, indent=2, default=str)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to JSON-encode honesty_verification: %s", exc,
            )
            payload = '{"verified": true, "discrepancies": [], "honesty_score": 1.0}'

        return f"""
## Honesty Verification

<honesty_verification>
{payload}
</honesty_verification>
"""

    def _render_absence_of_failure_guards(self) -> str:
        """Render the six absence-of-failure guard sentences (AC-009 + #5 + #6).

        The four guards from the TASK-HMIG-008R task spec (AC-009 points 1-4),
        the fifth guard added per Phase 2.5 review finding #2
        (gathering_status guard), and the sixth guard added by
        TASK-FIX-COACHTESTTO (independent-test absent guard — treat a
        timed-out / transport-errored independent-test oracle as ABSENT rather
        than approving on the Player's self-reported tests). The sentences are
        emitted verbatim inside
        an ``<absence_of_failure_guards>`` block so the Coach can locate
        them deterministically. Wording mirrors
        ``.claude/rules/absence-of-failure-is-not-success.md`` and
        ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` to
        preserve the rule citation chain.
        """
        return """
<absence_of_failure_guards>
CRITICAL READING RULES — apply these BEFORE any approval decision:

1. ZERO-CARDINALITY BDD GUARD.
   If evidence_bundle.bdd is not null AND evidence_bundle.bdd.scenarios_attempted == 0:
   treat as ABSENT SIGNAL — do NOT approve based on absence of failure.
   Surface as feedback: "BDD oracle ran zero scenarios — no evidence of
   passing behaviour." Rule: .claude/rules/absence-of-failure-is-not-success.md.

2. ZERO-CARDINALITY TEST GUARD.
   If evidence_bundle.tests is not null AND evidence_bundle.tests.tests_run == 0:
   treat as ABSENT SIGNAL — do NOT approve. Surface as feedback:
   "No tests ran — cannot verify correctness." Rule:
   .claude/rules/absence-of-failure-is-not-success.md.

3. SOPHISTICATED-LIE GUARD.
   If honesty_verification.discrepancies contains entries with
   severity == "critical" AND claim_type != "file_existence" AND
   claim_type != "claim_audit": you MUST reject the turn. These are
   sophisticated lies (test_result, test_count, promise_file_existence
   fabrications). Structural rejection is mandatory — do not evaluate
   ACs further. Surface a "feedback" decision naming each discrepancy.

4. LAYER-1 PATH DEMOTION GUARD.
   If honesty_verification.discrepancies contains exactly ONE entry with
   claim_type == "file_existence" AND honesty_verification.resolved_paths
   is non-empty: this discrepancy was Layer-1-resolved by state_bridge
   identity lookup (the orchestrator moved the task file, not Player
   dishonesty). Demote to should_fix and continue AC evaluation. Rule:
   .claude/rules/path-string-mismatch-is-not-dishonesty.md (Layer 2).
   Cross-check evidence_bundle.severity_recommendations for the
   structured hint — if present, it confirms this demotion applies.

5. GATHERING-STATUS GUARD.
   If evidence_bundle.gathering_status != "complete": evidence collection
   aborted before all fields were populated. Treat any null/None field as
   ABSENT SIGNAL — do NOT approve. Surface as feedback with the
   gathering_status value verbatim in the rationale so operators can
   diagnose which stage failed (e.g. "partial_honesty_abort",
   "partial_gate_abort", "partial_exception"). When status is
   "partial_exception", also surface evidence_bundle.gathering_error.

6. INDEPENDENT-TEST ABSENT GUARD.
   If evidence_bundle.independent_tests is not null AND
   evidence_bundle.independent_tests.signal_absent == true: the Coach's own
   trust-but-verify pytest run did NOT complete (it timed out or failed at
   the transport layer before producing a verdict). This is ABSENT SIGNAL,
   NOT a passing or failing test result — do NOT approve on the basis of the
   Player's self-reported tests plus the other gates. Surface as feedback:
   "Independent test verification did not complete (signal absent) — cannot
   independently confirm the Player's reported tests." Quote
   independent_tests.test_output_summary verbatim in the rationale so
   operators can see whether it timed out or errored. Rule:
   .claude/rules/absence-of-failure-is-not-success.md.
</absence_of_failure_guards>
"""

    def _verify_player_claims(
        self,
        player_report: Dict[str, Any],
    ) -> HonestyVerification:
        """Verify Player's self-reported claims against reality.

        This method uses CoachVerifier to cross-reference Player claims:
        - Test results vs actual test execution
        - Claimed files vs filesystem state
        - Test counts vs parsed output

        Args:
            player_report: Player's report from current turn

        Returns:
            HonestyVerification with verification results and honesty score

        Note:
            Returns a default verification result if verification fails,
            allowing the workflow to continue while logging the issue.
        """
        try:
            verifier = CoachVerifier(
                self.worktree_path, venv_python=self._venv_python
            )
            verification = verifier.verify_player_report(player_report)

            if verification.discrepancies:
                logger.warning(
                    f"Player honesty verification found {len(verification.discrepancies)} "
                    f"discrepancies (score: {verification.honesty_score:.2f})"
                )
                for disc in verification.discrepancies:
                    logger.warning(
                        f"  [{disc.severity}] {disc.claim_type}: "
                        f"claimed {disc.player_claim}, actual {disc.actual_value}"
                    )
            else:
                logger.info(
                    f"Player claims verified successfully (score: {verification.honesty_score:.2f})"
                )

            return verification

        except Exception as e:
            logger.warning(f"Failed to verify Player claims: {e}")
            # Return default verification (assume honest) to not block workflow
            return HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0)

    async def _invoke_with_role(
        self,
        prompt: str,
        agent_type: Literal["player", "coach"],
        allowed_tools: list[str],
        permission_mode: Literal["acceptEdits", "bypassPermissions"],
        model: Optional[str] = None,
        resume_session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        turn: Optional[int] = None,
        heartbeat_label_override: Optional[str] = None,
        return_events: bool = False,
        synthesis: bool = False,
        grammar: Optional[str] = None,
    ) -> Optional[Tuple[None, List[HarnessEvent]]]:
        """Low-level SDK invocation with role-based permissions.

        This method handles the actual Claude Agent SDK invocation with
        appropriate permissions and timeout handling. Emits an ``llm.call``
        event for every invocation via the injected EventEmitter
        (TASK-INST-005b).

        Args:
            prompt: Formatted prompt for agent
            agent_type: "player" or "coach"
            allowed_tools: List of allowed SDK tools
            permission_mode: "acceptEdits" (Player) or "bypassPermissions" (Coach)
            model: Model identifier, or None to use CLI default
            resume_session_id: Optional SDK session ID to resume from.
                If provided, passed as ``resume`` kwarg to ClaudeAgentOptions.
                If None, starts a fresh session. (TASK-RFX-B20B)
            heartbeat_label_override: Optional explicit phase label for
                ``async_heartbeat``. When provided, replaces the default
                ``f"{agent_type.capitalize()} invocation"`` label. Used by
                :func:`run_specialist` so orchestrator-invoked specialists
                surface as ``"specialist:{name} invocation"`` instead of
                masquerading as Player/Coach invocations (TASK-ABSR-DIAG).
            return_events: When ``True``, return ``(None, harness_events)``
                instead of ``None`` so callers can inspect the typed event
                stream the harness emitted. Used by the Coach call site
                (``invoke_coach``) to feed ``coach_output_parser`` the
                substrate-agnostic ``AssistantMessageEvent`` list it needs
                to extract the structured verdict (TASK-FIX-COACHOUT01
                Shape A). Player and specialist call sites leave this
                ``False`` and continue to receive ``None``.

                The parameter-based mechanism (rather than an instance
                attribute like ``self._last_harness_events``) was chosen by
                the Phase 2.5B architectural review (Gap 1) to avoid the
                hidden stale-state risk a future concurrent-invocation
                refactor would silently activate.
            synthesis: When ``True``, dispatch through
                ``harness.invoke_synthesis(...)`` instead of
                ``harness.invoke(...)`` — a TOOLLESS call (no ``tools`` in
                the substrate request) optionally constrained by ``grammar``.
                Used by the Coach verdict-synthesis path
                (TASK-ARCH-COACHSPLIT D-3). The caller MUST also pass
                ``allowed_tools=[]`` so the harness is constructed toolless
                on every substrate (the SDK harness reads its tool surface
                from the constructor ``allowed_tools``, not from the invoke
                call). All other orchestrator-side concerns (cancel monitor,
                heartbeat, latency, sdk_debug, llm.call event, return_events)
                are identical to the ``invoke`` path.
            grammar: Optional GBNF grammar string forwarded to
                ``invoke_synthesis``. Honoured only on substrates that
                support it (LangGraph/llama.cpp); ignored on the SDK path.
                Ignored entirely when ``synthesis`` is ``False``.

        Returns:
            ``None`` by default. ``(None, harness_events)`` when
            ``return_events=True``. Returns from BOTH the success path AND
            the SDK-timeout / AgentInvocationError paths re-raise — the
            tuple is only returned on a clean invocation completion.

        Raises:
            AgentInvocationError: If SDK invocation fails
            SDKTimeoutError: If invocation exceeds timeout
        """
        # TASK-HMIG-006 Phase 3b: dispatch through HarnessAdapter. The
        # harness owns SDK lazy-import, ClaudeAgentOptions construction,
        # message-stream translation, parse resilience (TASK-FIX-7A03),
        # session_id capture (TASK-RFX-B20B), and generator hygiene
        # (TASK-RFX-8332 / TASK-FIX-GEN1). Per Design Decision D-3,
        # orchestrator-side concerns (heartbeat, cancel monitor,
        # measure_latency, sdk_debug, llm.call event) stay inline. Per
        # D-4, the harness normalises all SDK-specific exceptions
        # (CLINotFoundError / ProcessError / CLIJSONDecodeError /
        # harness-internal ValueError) to AgentInvocationError before
        # they reach this caller.
        from guardkit.orchestrator.sdk_utils import check_assistant_message_error

        # TASK-INST-005b: Instrumentation state for event emission. The
        # response_messages list is populated from event.raw per Design
        # Decision D-1 so the remaining duck-typed consumers
        # (_emit_llm_call_event token extraction, cancelled-error
        # session_id rescan) keep working unchanged. TASK-HMIG-006.2
        # narrowed this contract: ToolUseEvent entries are excluded
        # because the migrated _track_tool_use /
        # _extract_partial_from_messages consumers dispatch on typed
        # events directly via harness_events instead of duck-typing on
        # event.raw.
        call_status: str = "ok"
        call_error: Optional[Exception] = None
        response_messages: List[Any] = []
        # TASK-HMIG-006.2: typed-event canonical record for the migrated
        # _extract_partial_from_messages consumer below. Holds every event
        # the harness yielded (AssistantMessageEvent, ToolUseEvent,
        # ResultMessageEvent) in the order they arrived, so the post-stream
        # and cancelled-error extract paths can dispatch on event variants
        # rather than duck-typing on SDK shapes.
        harness_events: List[HarnessEvent] = []

        # TASK-FIX-SPECHANG2: reset the model-activity clock at the start of
        # the invocation so the specialist watchdog measures the no-activity
        # gap from "this invocation began" rather than from a previous one.
        self._last_activity_monotonic = time.monotonic()

        # Extract task_id from prompt for heartbeat logging (substrate-
        # agnostic — the harness does not need it).
        task_id_match = re.search(r"TASK-[A-Z0-9-]+", prompt)
        heartbeat_task_id = task_id_match.group(0) if task_id_match else "unknown"

        # TASK-DIAG-F4A2: Preserve rendered prompt under sdk_debug/
        # turn_<n>/[coach/] when GUARDKIT_AUTOBUILD_PRESERVE_DEBUG is set.
        # Helper is a no-op otherwise. Substrate-agnostic — operates on
        # whatever the orchestrator constructs.
        from guardkit.orchestrator.sdk_debug import (
            preserve_prompt as _sdk_preserve_prompt,
        )
        _debug_task_id = task_id or heartbeat_task_id
        _debug_turn = turn if turn is not None else 1
        _debug_role = "coach" if agent_type == "coach" else "player"
        # NB: the rendered SDK options object is not available outside
        # the harness; pass `None` here for the options snapshot. The
        # prompt + per-event JSONL still preserve enough context to
        # diagnose SDK stalls (TASK-DIAG-F4A2 acceptance criteria).
        _sdk_debug_dir = _sdk_preserve_prompt(
            workspace_root=self.worktree_path,
            task_id=_debug_task_id,
            turn=_debug_turn,
            role=_debug_role,
            prompt=prompt,
            options=None,
        )

        # TASK-FIX-CTOUT01: monitor task creation moved to AFTER
        # select_harness() (~30 lines below) so the closure can capture
        # the live ``harness`` handle and dispatch
        # ``await harness.cancel()`` alongside the legacy
        # ``_kill_child_claude_processes()`` (TASK-FIX-ASPF-004) call.
        # Under LangGraph, ``harness.cancel()`` is the only thing that
        # actually unblocks the in-flight ``agent.ainvoke()`` — there is
        # no subprocess for the SIGTERM path to kill. Under SDK, both
        # run: ``cancel()`` closes the query() generator from inside the
        # async loop, ``_kill_child_claude_processes()`` provides OS-level
        # escalation as before.
        monitor: Optional[asyncio.Task] = None

        # TASK-FIX-MODELPLUMB: fall back to the orchestrator-stored model
        # name when the caller didn't specify one explicitly. invoke_coach,
        # the legacy direct-SDK Player path, and run_specialist all call
        # _invoke_with_role without a model= kwarg (comments at those sites
        # say "Model selection delegated to CLI default" — this is the
        # mechanism that actually carries the CLI default through).
        #
        # TASK-FIX-COACHBUDG01 (2026-06-06): per-role override. When the
        # role is coach or coach_test AND a coach_model_name was supplied
        # to the orchestrator, prefer that over _model_name. Lets the
        # operator route Coach to gemma4:26b while Player + specialists
        # stay on qwen36-workhorse (the load-bearing mechanic for the
        # F17 substrate-quality fix, TASK-HMIG-013).
        if model is None:
            # `agent_type` is typed Literal["player", "coach"]; only "coach"
            # ever matches here. The coach_test path uses a different
            # invocation route (CoachValidator._get_coach_test_model →
            # select_harness directly), which has its own COACHBUDG01 wire.
            if agent_type == "coach" and self._coach_model_name is not None:
                model = self._coach_model_name
            else:
                model = self._model_name

        try:
            # Construct the harness. select_harness() routes via
            # GUARDKIT_HARNESS env var (default "sdk"). Per Design Decision
            # D-6, harness instances are single-use per invocation — the
            # cleanup-handler installer is invoked inside the harness's
            # invoke() against the running event loop.
            harness = select_harness(
                sdk_timeout_seconds=self.sdk_timeout_seconds,
                allowed_tools=allowed_tools,
                permission_mode=permission_mode,
                # TASK-REV-C4D7: Direct mode also needs ~50 internal turns
                # (same as task-work delegation path fixed in TASK-REV-BB80)
                # TASK-FIX-7718: Use effective turns (auto-reduced for local backends)
                max_turns=self._effective_sdk_max_turns,
                model=model,
                resume_session_id=resume_session_id,
                sdk_debug_dir=_sdk_debug_dir,
                cleanup_handler_installer=_install_sdk_cleanup_handler,
                # TASK-FIX-002R-CONSUME: ``cwd`` is the worktree path the
                # langgraph branch needs to construct a path-confined
                # LocalShellBackend via
                # ``guardkitfactory.harness.build_autobuild_backend(cwd)``.
                # The SDK branch ignores it (popped at the top of
                # ``select_harness``); passing unconditionally keeps the
                # call site harness-agnostic.
                cwd=self.worktree_path,
            )

            # TASK-FIX-ASPF-004 + TASK-FIX-CTOUT01: dispatch cancellation
            # to BOTH the substrate-agnostic ``harness.cancel()`` path
            # (CTOUT01 — the only thing that unblocks LangGraph's
            # in-flight ``agent.ainvoke()``) AND the legacy
            # ``_kill_child_claude_processes()`` SIGTERM (ASPF-004 — OS-
            # level subprocess escalation; no-op under LangGraph). The
            # closure was moved here from earlier in this method so it
            # can capture the live ``harness`` reference returned by
            # ``select_harness()`` above.
            async def _cancel_monitor() -> None:
                """Poll cancellation event; dispatch harness cancel + SIGTERM."""
                while True:
                    await asyncio.sleep(2)
                    if (
                        self._cancellation_event
                        and self._cancellation_event.is_set()
                    ):
                        logger.info(
                            f"TASK-FIX-CTOUT01: Cancellation event detected "
                            f"during {agent_type} invocation; calling "
                            f"harness.cancel() and terminating any SDK "
                            f"subprocess."
                        )
                        # NEW (TASK-FIX-CTOUT01): substrate-agnostic
                        # cooperative cancel. SDK closes the active
                        # query() generator; LangGraph cancels the
                        # asyncio.Task wrapping agent.ainvoke().
                        try:
                            await harness.cancel()
                        except Exception as exc:
                            logger.warning(
                                f"TASK-FIX-CTOUT01: harness.cancel() raised "
                                f"{type(exc).__name__}: {exc} — falling "
                                f"through to subprocess kill."
                            )
                        # LEGACY (TASK-FIX-ASPF-004): SDK-subprocess SIGTERM.
                        # No-op under LangGraph; stays the OS-level
                        # escalation under SDK.
                        self._kill_child_claude_processes()
                        return

            if self._cancellation_event:
                monitor = asyncio.create_task(_cancel_monitor())

            # TASK-HMIG-006 AC-007: surface the resume-intent drop loudly
            # when the caller offers a resume_session_id and the resolved
            # harness does not support resume (e.g. LangGraphHarness Wave-2
            # skeleton). The translator at the selector layer silently
            # drops the kwarg; this warning is the user-facing
            # acknowledgement that the resume intent will not be honoured
            # and the next turn starts fresh. The check is cheap and runs
            # BEFORE measure_latency() opens so the latency band reported
            # for the LLM call event is unaffected.
            if resume_session_id is not None and not harness.supports_resume:
                logger.warning(
                    "TASK-HMIG-006 AC-007: resume_session_id=%s... was supplied but "
                    "harness %s does not support_resume; starting fresh session.",
                    resume_session_id[:16],
                    type(harness).__name__,
                )

            try:
                # TASK-INST-005b: Wrap harness call with latency measurement.
                with measure_latency() as latency:
                    try:
                        async with asyncio.timeout(self.sdk_timeout_seconds):
                            phase_label = (
                                heartbeat_label_override
                                or f"{agent_type.capitalize()} invocation"
                            )
                            async with async_heartbeat(
                                heartbeat_task_id,
                                phase_label,
                                progress_logger=self._progress_logger,
                            ):
                                # TASK-FIX-LGACLOSE: finalise the harness async
                                # generator on EVERY exit (normal, break, raise,
                                # or consumer cancellation) via aclosing() so no
                                # orphaned async_generator_athrow / pending
                                # ainvoke task survives to interpreter shutdown.
                                # TASK-ARCH-COACHSPLIT (D-3): the Coach
                                # verdict-synthesis path dispatches through
                                # the TOOLLESS invoke_synthesis(...) entry
                                # (no `tools` in the substrate request) so a
                                # GBNF grammar can be honoured (llama.cpp
                                # hard-rejects grammar+tools) and no tool-call
                                # parser exists to crash. Everything else in
                                # this loop — events, cancel monitor,
                                # return_events — is substrate- and
                                # path-agnostic.
                                if synthesis:
                                    _harness_call = harness.invoke_synthesis(
                                        prompt=prompt,
                                        role=agent_type,
                                        grammar=grammar,
                                        cwd=self.worktree_path,
                                        timeout_seconds=self.sdk_timeout_seconds,
                                    )
                                else:
                                    _harness_call = harness.invoke(
                                        prompt=prompt,
                                        role=agent_type,
                                        tools=allowed_tools,
                                        cwd=self.worktree_path,
                                        timeout_seconds=self.sdk_timeout_seconds,
                                    )
                                async with aclosing(
                                    _harness_call
                                ) as _harness_stream:
                                    async for event in _harness_stream:
                                        # TASK-FIX-SPECHANG2: record model-
                                        # stream activity for the specialist
                                        # no-model-activity watchdog. Every
                                        # harness event (AssistantMessage /
                                        # ToolUse / Result) is downstream of a
                                        # model call, so a stale gap here means
                                        # zero /v1/responses traffic.
                                        self._last_activity_monotonic = (
                                            time.monotonic()
                                        )

                                        # TASK-HMIG-006.2: keep the typed-event
                                        # stream as the canonical record for the
                                        # post-stream extract path. response_messages
                                        # retains its D-1 purpose (raw SDK shape for
                                        # the remaining duck-typed consumers:
                                        # _emit_llm_call_event token usage, the
                                        # check_assistant_message_error API-error
                                        # scan, the heartbeat ToolUseBlock log on
                                        # the specialist path) but ToolUseEvent
                                        # entries are skipped — they exist only as
                                        # typed events for the migrated
                                        # _track_tool_use / _extract_partial_from_messages
                                        # consumers, and appending them to
                                        # response_messages would mix typed events
                                        # with SDK objects in a list typed
                                        # List[Any].
                                        if not isinstance(event, ToolUseEvent):
                                            raw = event.raw if event.raw is not None else event
                                            response_messages.append(raw)
                                        harness_events.append(event)

                                        # TASK-DIAG-F4A2: Preserve each raw event to
                                        # JSONL when raw is populated.
                                        if _sdk_debug_dir is not None and event.raw is not None:
                                            from guardkit.orchestrator.sdk_debug import (
                                                preserve_event as _sdk_preserve_event,
                                            )
                                            _sdk_preserve_event(_sdk_debug_dir, event.raw)

                                        # TASK-HMIG-006.2: tool-use tracking moved
                                        # to a dedicated ToolUseEvent branch — the
                                        # AssistantMessageEvent.raw walk it used to
                                        # do is gone. Both harnesses now yield one
                                        # ToolUseEvent per tool call.
                                        if isinstance(event, ToolUseEvent):
                                            if self._progress_logger:
                                                self._track_tool_use(event)

                                        # API-error check + heartbeat ToolUseBlock
                                        # log still operate on the raw SDK shape:
                                        # the API-error structure is SDK-specific
                                        # and the heartbeat log is intentionally
                                        # gated to the specialist path.
                                        if isinstance(event, AssistantMessageEvent) and event.raw is not None:
                                            err = check_assistant_message_error(event.raw)
                                            if err:
                                                raise AgentInvocationError(
                                                    f"Agent {agent_type} received API error: {err}"
                                                )
                                            # TASK-FIX-CRSTL-MULT R2: Emit
                                            # ToolUseBlock log lines on the
                                            # specialist path so per-tool signal
                                            # surfaces during long specialist
                                            # invocations. Player/Coach paths
                                            # already get this from the task-work
                                            # delegation path; gating on
                                            # heartbeat_label_override avoids
                                            # double-logging.
                                            if heartbeat_label_override is not None:
                                                content = getattr(event.raw, "content", None) or []
                                                for block in content:
                                                    if type(block).__name__ != "ToolUseBlock":
                                                        continue
                                                    tool_input = getattr(block, "input", {}) or {}
                                                    keys = (
                                                        sorted(tool_input.keys())
                                                        if isinstance(tool_input, dict)
                                                        else []
                                                    )
                                                    logger.info(
                                                        f"[{task_id}] {heartbeat_label_override} "
                                                        f"ToolUseBlock "
                                                        f"{getattr(block, 'name', '?')} "
                                                        f"input keys: {keys}"
                                                    )

                                        # ResultMessageEvent is terminal. The
                                        # in-loop generator drain is now owned by
                                        # the harness (TASK-FIX-GEN1 moved per
                                        # Design Decision D-3); orchestrator only
                                        # captures session_id and breaks.
                                        if isinstance(event, ResultMessageEvent):
                                            # TASK-RFX-B20B: capture session_id for
                                            # resumption. Read from the event field
                                            # (which the harness populates from the
                                            # raw SDK message) so the same code path
                                            # works for any substrate.
                                            self._last_session_id = event.session_id
                                            break
                    except (Exception, asyncio.CancelledError) as exc:
                        if isinstance(exc, asyncio.CancelledError):
                            logger.debug(f"CancelledError caught at _invoke_with_role: {exc}")
                            # TASK-CRV-1540 + TASK-HMIG-006.2: extract partial
                            # data before re-raising. harness_events is the
                            # typed-event canonical record; the migrated
                            # _extract_partial_from_messages dispatches on
                            # event variants instead of duck-typing on raw
                            # SDK shapes, so the LangGraph path now produces
                            # non-empty counts where it used to return zeros.
                            try:
                                self._last_partial_report = _extract_partial_from_messages(
                                    harness_events
                                )
                                logger.info(
                                    f"Extracted partial data from {len(harness_events)} events: "
                                    f"{self._last_partial_report['text_block_count']} text blocks, "
                                    f"{self._last_partial_report['tool_call_count']} tool calls, "
                                    f"{len(self._last_partial_report['file_modifications'])} file mods"
                                )
                            except Exception as extract_err:
                                logger.warning(f"Failed to extract partial data: {extract_err}")
                                self._last_partial_report = None
                            # TASK-RFX-B20B: Scan accumulated messages for
                            # session_id. response_messages still holds raw
                            # SDK ResultMessage objects (TASK-HMIG-006.2 only
                            # excludes ToolUseEvent from the accumulation,
                            # not ResultMessage raws) so this duck-typed
                            # rescan keeps working.
                            for msg in reversed(response_messages):
                                if type(msg).__name__ == "ResultMessage":
                                    self._last_session_id = getattr(msg, "session_id", None)
                                    break
                        call_status = "error"
                        call_error = exc
                        raise
            finally:
                if monitor and not monitor.done():
                    monitor.cancel()
                    with suppress(asyncio.CancelledError):
                        await monitor

                # TASK-INST-005b: Emit llm.call event (fire-and-forget).
                # Token extraction reads usage off the raw SDK ResultMessage
                # objects that live in response_messages via event.raw.
                self._emit_llm_call_event(
                    agent_type=agent_type,
                    model=model,
                    latency_ms=latency.ms,
                    response_messages=response_messages,
                    status=call_status,
                    error=call_error,
                    task_id=heartbeat_task_id,
                )

        except asyncio.TimeoutError:
            raise SDKTimeoutError(
                f"Agent invocation exceeded {self.sdk_timeout_seconds}s timeout"
            )
        except AgentInvocationError:
            # TASK-FIX-7A03: Already-structured AgentInvocationError must
            # pass through untouched — otherwise the blanket Exception
            # handler below would re-wrap it and overwrite its error_class
            # (e.g. the MessageParseError classification emitted by the
            # all-unparseable-stream branch would be lost in transit).
            # Per TASK-HMIG-006 Design Decision D-4, the harness now
            # normalises SDK-specific exceptions (CLINotFoundError,
            # ProcessError, CLIJSONDecodeError, harness-internal
            # ValueError) to AgentInvocationError before they reach this
            # caller — so this pass-through is the primary surfacing path
            # for substrate failures.
            raise
        except ValueError as e:
            # TASK-FIX-7A03 / TASK-HMIG-006 D-4: catch-all for non-harness
            # ValueError raised by select_harness(),
            # _emit_llm_call_event(), or event-dispatch glue. Harness-
            # internal ValueError is already normalised to
            # AgentInvocationError inside the harness; this clause now
            # only fires for orchestrator-side ValueError. Wording
            # preserved verbatim so TASK-FIX-7A02 classification keeps
            # the existing error_class signal.
            raise AgentInvocationError(
                f"SDK value error for {agent_type} "
                f"({type(e).__name__}): {e}",
                error_class=type(e).__name__,
            ) from e
        except Exception as e:
            # TASK-FIX-7A03: Final safety net — augment the error string
            # with type(e).__name__ so the surfaced message is no longer
            # opaque, and populate error_class so downstream classification
            # (TASK-FIX-7A02) gets the signal for exception types we didn't
            # anticipate. Reached only when the harness boundary leaks an
            # exception type other than AgentInvocationError /
            # asyncio.TimeoutError / ValueError — should be rare given the
            # D-4 normalisation, but kept as a safety net.
            raise AgentInvocationError(
                f"SDK invocation failed for {agent_type} "
                f"({type(e).__name__}): {str(e)}",
                error_class=type(e).__name__,
            ) from e

        # TASK-FIX-COACHOUT01 Shape A: hand the typed event stream back to
        # the Coach call site so coach_output_parser.extract_and_write can
        # consume AssistantMessageEvent text without round-tripping through
        # an instance attribute. Reached only on the success path — the
        # except branches above all raise. Player and specialist sites
        # leave return_events at its default and continue to receive None
        # (the implicit fall-through here).
        if return_events:
            return (None, harness_events)
        return None

    def _emit_llm_call_event(
        self,
        agent_type: Literal["player", "coach"],
        model: Optional[str],
        latency_ms: float,
        response_messages: List[Any],
        status: str,
        error: Optional[Exception],
        task_id: str,
    ) -> None:
        """Construct and fire-and-forget an LLMCallEvent.

        Emission is non-blocking via asyncio.create_task(). If the emitter
        raises, the error is logged as a warning but never propagated to
        the caller. (TASK-INST-005b)

        Args:
            agent_type: Agent role ("player" or "coach").
            model: Model identifier or None for CLI default.
            latency_ms: Wall-clock latency of the SDK call in milliseconds.
            response_messages: SDK response messages (for token extraction).
            status: "ok" or "error".
            error: The exception if status is "error", else None.
            task_id: Task identifier extracted from prompt.
        """
        try:
            input_tokens, output_tokens = extract_token_usage(response_messages)

            # Read prompt_profile from instance or use Phase 1 baseline default
            prompt_profile = getattr(self, "_prompt_profile", None) or "digest+rules_bundle"

            # Read run_id from instance or generate a session-level default
            run_id = getattr(self, "_run_id", None) or f"run-{id(self)}"

            # Read current attempt from instance or default to 1
            attempt = getattr(self, "_current_attempt", None) or 1

            # Detect provider from environment base URL
            base_url = os.environ.get("ANTHROPIC_BASE_URL", "")

            event = LLMCallEvent(
                run_id=run_id,
                task_id=task_id,
                agent_role=agent_type,
                attempt=attempt,
                timestamp=datetime.now().isoformat(),
                provider=detect_provider(base_url, model),
                model=model or "default",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                prompt_profile=prompt_profile,
                status=status,
                error_type=classify_error(error),
            )

            async def _safe_emit() -> None:
                """Emit event, swallowing any errors."""
                try:
                    await self._emitter.emit(event)
                except Exception as emit_exc:
                    logger.warning(
                        "LLM call event emission failed: %s. "
                        "Event will not be delivered but LLM call is unaffected.",
                        emit_exc,
                    )

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_safe_emit())
            except RuntimeError:
                # No running event loop — skip emission silently
                logger.debug("No running event loop for LLM call event emission")
        except Exception as build_exc:
            # Event construction failure must never block the SDK call path
            logger.warning(
                "Failed to construct LLM call event: %s. "
                "Instrumentation skipped for this call.",
                build_exc,
            )

    # TASK-INST-005c: Shared SecretRedactor instance (lazy-initialised)
    _tool_exec_redactor: Optional["SecretRedactor"] = None

    # TASK-INST-005c: Tools that emit tool.exec events (Bash-type only)
    _TOOL_EXEC_EVENT_TOOLS = frozenset({"Bash"})

    def _emit_tool_exec_event(
        self,
        tool_name: str,
        cmd: str,
        exit_code: int,
        latency_ms: float,
        stdout_tail: str,
        stderr_tail: str,
        task_id: str,
    ) -> None:
        """Construct and fire-and-forget a ToolExecEvent.

        Only emits events for Bash-type tool invocations (tools with shell
        command semantics). Non-Bash tools (Write, Edit, Glob, etc.) are
        silently ignored.

        Secret redaction is applied to cmd, stdout_tail, and stderr_tail
        before event construction. Tool names are sanitised against shell
        metacharacters. stdout_tail and stderr_tail are truncated to the
        last 500 characters.

        Emission is non-blocking via asyncio.create_task(). If the emitter
        raises, the error is logged as a warning but never propagated to
        the caller. (TASK-INST-005c)

        Args:
            tool_name: Name of the tool invoked (e.g., "Bash").
            cmd: Command string executed by the tool.
            exit_code: Process exit code.
            latency_ms: Execution latency in milliseconds.
            stdout_tail: Tail of stdout output.
            stderr_tail: Tail of stderr output.
            task_id: Task identifier.
        """
        # AC-005: Only emit for Bash-type tools
        if tool_name not in self._TOOL_EXEC_EVENT_TOOLS:
            return

        try:
            # Lazy-initialise the shared redactor
            if self._tool_exec_redactor is None:
                self._tool_exec_redactor = SecretRedactor()

            redactor = self._tool_exec_redactor

            # AC-006: Truncate output to last 500 chars
            stdout_truncated = stdout_tail[-500:] if len(stdout_tail) > 500 else stdout_tail
            stderr_truncated = stderr_tail[-500:] if len(stderr_tail) > 500 else stderr_tail

            # Read run_id from instance or generate a session-level default
            run_id = getattr(self, "_run_id", None) or f"run-{id(self)}"

            # Read current attempt from instance or default to 1
            attempt = getattr(self, "_current_attempt", None) or 1

            # Read current agent role or default to "player"
            agent_role = getattr(self, "_current_agent_role", None) or "player"

            event = ToolExecEvent(
                run_id=run_id,
                task_id=task_id,
                agent_role=agent_role,
                attempt=attempt,
                timestamp=datetime.now().isoformat(),
                tool_name=sanitise_tool_name(tool_name),
                cmd=redactor.redact(cmd),
                exit_code=exit_code,
                latency_ms=latency_ms,
                stdout_tail=redactor.redact(stdout_truncated),
                stderr_tail=redactor.redact(stderr_truncated),
            )

            async def _safe_emit() -> None:
                """Emit event, swallowing any errors."""
                try:
                    await self._emitter.emit(event)
                except Exception as emit_exc:
                    logger.warning(
                        "Tool exec event emission failed: %s. "
                        "Event will not be delivered but tool execution is unaffected.",
                        emit_exc,
                    )

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_safe_emit())
            except RuntimeError:
                # No running event loop — skip emission silently
                logger.debug("No running event loop for tool exec event emission")
        except Exception as build_exc:
            # Event construction failure must never block the tool execution path
            logger.warning(
                "Failed to construct tool exec event: %s. "
                "Instrumentation skipped for this tool call.",
                build_exc,
            )

    def _create_player_report_from_task_work(
        self,
        task_id: str,
        turn: int,
        task_work_result: "TaskWorkResult",
    ) -> None:
        """Create Player report from task-work results.

        When Player delegates to task-work --implement-only, task-work creates
        task_work_results.json but the orchestrator expects player_turn_{turn}.json.
        This method bridges the gap by reading task_work_results.json and creating
        the expected Player report.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Turn number (1-based)
            task_work_result: Result from task-work execution

        Notes:
            - Reads task_work_results.json from .guardkit/autobuild/{task_id}/
            - Transforms to PlayerReport schema (see PLAYER_REPORT_SCHEMA)
            - Writes player_turn_{turn}.json to same directory
            - Detects git changes if not in task_work_results.json
        """
        # Use centralized paths
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        task_work_results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
        player_report_path = TaskArtifactPaths.player_report_path(task_id, turn, self.worktree_path)

        # Initialize report with defaults
        report: Dict[str, Any] = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": [],
            "files_created": [],
            "tests_written": [],
            "tests_run": False,
            "tests_passed": False,
            "test_output_summary": "",
            "implementation_notes": "Implementation via task-work delegation",
            "concerns": [],
            "requirements_addressed": [],
            "requirements_remaining": [],
            # TASK-VPR-003: SDK turn ceiling data
            "sdk_turns_used": None,
            "sdk_max_turns": None,
            "sdk_ceiling_hit": False,
        }

        # Try to read task_work_results.json for richer data
        if task_work_results_path.exists():
            try:
                with open(task_work_results_path, "r") as f:
                    task_work_data = json.load(f)

                # Map task-work fields to Player report fields
                report["files_modified"] = task_work_data.get("files_modified", [])
                report["files_created"] = task_work_data.get("files_created", [])
                # TASK-FIX-CC-COND: propagate files_authored (Player's
                # explicit Write/Edit set). Never union with git diff
                # downstream — that contamination is exactly what this
                # field exists to avoid. Coach's source-file contention
                # detector reads this verbatim.
                if "files_authored" in task_work_data:
                    report["files_authored"] = task_work_data.get(
                        "files_authored", []
                    )

                # Extract test info (conditional on tests_info existing)
                tests_info = task_work_data.get("tests_info", {})
                if tests_info:
                    report["tests_run"] = tests_info.get("tests_run", False)
                    report["tests_passed"] = tests_info.get("tests_passed", False)
                    report["test_output_summary"] = tests_info.get(
                        "output_summary", ""
                    )

                # ALWAYS populate tests_written from file lists (unconditional)
                all_files = report.get("files_created", []) + report.get("files_modified", [])
                tests_from_files = [
                    f for f in all_files
                    if "test_" in Path(f).name.lower() or Path(f).name.lower().endswith("_test.py")
                ]

                # Also extract test files from completion_promises.test_file
                # This catches pre-existing test files (e.g., from scaffolding
                # tasks) that the Player references but didn't create/modify.
                tests_from_promises = set()
                for promise in task_work_data.get("completion_promises", []):
                    test_file = promise.get("test_file")
                    if test_file and isinstance(test_file, str):
                        p = Path(test_file)
                        if (p.name.startswith("test_") and p.name.endswith(".py")) or p.name.endswith("_test.py"):
                            tests_from_promises.add(test_file)

                report["tests_written"] = sorted(
                    list(set(tests_from_files) | tests_from_promises)
                )

                # Extract implementation notes from plan audit if available
                plan_audit = task_work_data.get("plan_audit", {})
                if plan_audit:
                    report["implementation_notes"] = (
                        f"Implementation via task-work delegation. "
                        f"Files planned: {plan_audit.get('files_planned', 0)}, "
                        f"Files actual: {plan_audit.get('files_actual', 0)}"
                    )

                # Propagate completion_promises into player report (TASK-ACR-001)
                completion_promises = task_work_data.get("completion_promises", [])
                if completion_promises:
                    report["completion_promises"] = completion_promises

                # TASK-VPR-003: Extract SDK turn ceiling data
                sdk_turns = task_work_data.get("sdk_turns", {})
                if sdk_turns:
                    report["sdk_turns_used"] = sdk_turns.get("turns_used")
                    report["sdk_max_turns"] = sdk_turns.get("max_turns")
                    report["sdk_ceiling_hit"] = sdk_turns.get("ceiling_hit", False)

                logger.info(
                    f"Created Player report from task_work_results.json for {task_id} turn {turn}"
                )

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(
                    f"Failed to read task_work_results.json, using defaults: {e}"
                )

        # ALWAYS verify/enrich with git detection (TASK-DMRF-003)
        # This ensures we capture changes even if task_work_results.json has empty arrays
        try:
            git_changes = self._detect_git_changes()
            if git_changes:
                original_modified = set(report["files_modified"])
                original_created = set(report["files_created"])

                git_modified = set(git_changes.get("modified", []))
                git_created = set(git_changes.get("created", []))

                # Merge using union (preserves existing + adds git-detected)
                report["files_modified"] = sorted(list(original_modified | git_modified))
                report["files_created"] = sorted(list(original_created | git_created))

                # TASK-FIX-1B4C (Layer 3'): Filter orchestrator-induced ghost
                # paths. When state_bridge moved a task file mid-turn (e.g.
                # backlog → design_approved), `git diff --name-only` against
                # the pre-move baseline reports the source path as deleted.
                # Without -M rename detection, the union-merge above attributes
                # that ghost path to the Player, who never wrote it. Subtract
                # the persisted state-bridge moves so the ghost never reaches
                # the Coach honesty verification. See FEAT-1B452 review report
                # § C4 + § 3.
                try:
                    from guardkit.tasks.state_bridge import TaskStateBridge

                    induced = TaskStateBridge.orchestrator_induced_paths_for(
                        task_id, repo_root=self.worktree_path
                    )
                    if induced:
                        before_modified = set(report["files_modified"])
                        before_created = set(report["files_created"])
                        report["files_modified"] = sorted(
                            set(report["files_modified"]) - induced
                        )
                        report["files_created"] = sorted(
                            set(report["files_created"]) - induced
                        )
                        filtered_paths = (
                            (before_modified | before_created) & induced
                        )
                        if filtered_paths:
                            logger.info(
                                f"Filtered {len(filtered_paths)} "
                                f"orchestrator-induced ghost path(s) for "
                                f"{task_id}: {sorted(filtered_paths)}"
                            )
                except Exception as exc:  # noqa: BLE001 — never block report
                    logger.warning(
                        f"Ghost-path filter failed for {task_id}: {exc}"
                    )

                # TASK-FIX-PIPELINE: Filter invalid entries (Fix 4)
                # TASK-FIX-PV01: Use centralised _is_valid_file_path which also
                # rejects natural language words (e.g. 'house') that lack '/' or '.'.
                report["files_modified"] = sorted(
                    [p for p in report["files_modified"] if TaskWorkStreamParser._is_valid_file_path(p)]
                )
                report["files_created"] = sorted(
                    [p for p in report["files_created"] if TaskWorkStreamParser._is_valid_file_path(p)]
                )

                # Log when git detection adds files not in original report
                new_modified = git_modified - original_modified
                new_created = git_created - original_created
                if new_modified or new_created:
                    logger.info(
                        f"Git detection added: {len(new_modified)} modified, "
                        f"{len(new_created)} created files for {task_id}"
                    )

                # Update implementation notes if we only have git-detected files
                if not task_work_results_path.exists():
                    report["implementation_notes"] = (
                        "Implementation via task-work delegation (git-detected changes)"
                    )
        except Exception as e:
            logger.warning(f"Failed to detect git changes: {e}")

        # Also use task_work_result.output if available
        if task_work_result.output:
            output = task_work_result.output
            # Merge with output data if present (union with git-enriched)
            if "files_modified" in output:
                existing = set(report.get("files_modified", []))
                report["files_modified"] = sorted(list(existing | set(output["files_modified"])))
            if "files_created" in output:
                existing = set(report.get("files_created", []))
                report["files_created"] = sorted(list(existing | set(output["files_created"])))
            if "tests_passed" in output:
                tests_passed_value = output["tests_passed"]
                # Convert count to boolean for PLAYER_REPORT_SCHEMA compliance
                # Parser captures tests_passed as int (count), schema expects bool
                # Note: Check for bool FIRST since bool is a subclass of int in Python
                if isinstance(tests_passed_value, bool):
                    report["tests_passed"] = tests_passed_value
                elif isinstance(tests_passed_value, int):
                    report["tests_passed"] = tests_passed_value > 0
                    report["tests_passed_count"] = tests_passed_value  # Preserve count
                else:
                    report["tests_passed"] = bool(tests_passed_value)
                report["tests_run"] = True

        # TASK-FIX-PIPELINE: Recover agent-written completion_promises (Fix 2)
        # The execution protocol instructs the SDK agent to write player_turn_N.json
        # directly. If the agent did so before this method runs, preserve the
        # agent's completion_promises and requirements_addressed.
        #
        # TASK-FIX-VL01: When the SDK agent (e.g. Qwen3/vLLM) writes to the
        # repo root instead of the worktree, the file won't be at
        # player_report_path. Search both locations with worktree first.
        candidate_paths = [player_report_path]
        repo_root = self._resolve_repo_root()
        if repo_root is not None:
            repo_root_fallback = TaskArtifactPaths.player_report_path(
                task_id, turn, repo_root
            )
            if repo_root_fallback != player_report_path:
                candidate_paths.append(repo_root_fallback)

        for candidate in candidate_paths:
            if not report.get("completion_promises") and candidate.exists():
                try:
                    with open(candidate, "r") as f:
                        agent_written = json.load(f)

                    # Recover completion_promises from agent-written report
                    agent_promises = agent_written.get("completion_promises", [])
                    if agent_promises:
                        report["completion_promises"] = agent_promises
                        logger.info(
                            f"Recovered {len(agent_promises)} completion_promises "
                            f"from agent-written player report for {task_id}"
                        )

                    # Recover requirements_addressed if ours is empty
                    if not report["requirements_addressed"]:
                        agent_reqs = agent_written.get("requirements_addressed", [])
                        if agent_reqs:
                            report["requirements_addressed"] = agent_reqs
                            logger.info(
                                f"Recovered {len(agent_reqs)} requirements_addressed "
                                f"from agent-written player report for {task_id}"
                            )

                    # Recover requirements_remaining if ours is empty
                    if not report["requirements_remaining"]:
                        agent_remaining = agent_written.get("requirements_remaining", [])
                        if agent_remaining:
                            report["requirements_remaining"] = agent_remaining

                    if candidate != player_report_path:
                        logger.warning(
                            f"Recovered player report from repo root fallback: "
                            f"{candidate} (worktree path was {player_report_path})"
                        )
                    break

                except (json.JSONDecodeError, IOError) as e:
                    logger.debug(
                        f"Could not recover player report from {candidate}: {e}"
                    )

        # TASK-FIX-PIPELINE: File-existence verification fallback (Fix 5)
        # When no completion_promises exist after Fix 2 recovery, generate
        # synthetic promises by checking files against acceptance criteria.
        # TASK-FIX-VL02: Use TaskLoader to extract AC from markdown body,
        # not just YAML frontmatter (_load_task_metadata only reads frontmatter).
        if not report.get("completion_promises"):
            acceptance_criteria = []
            try:
                from guardkit.tasks.task_loader import TaskLoader

                task_data = TaskLoader.load_task(
                    task_id, repo_root=self.worktree_path
                )
                acceptance_criteria = task_data.get("acceptance_criteria", [])
            except Exception as e:
                logger.debug(
                    f"Fix 5: TaskLoader.load_task failed for {task_id}: {e}"
                )
                # Fallback to _load_task_metadata (YAML frontmatter only)
                task_file = self._find_task_file(task_id)
                if task_file is None:
                    logger.warning(
                        f"Fix 5: _find_task_file returned None for {task_id} — "
                        f"completion_promises fallback unavailable. "
                        f"Check that task directories are correctly configured."
                    )
                if task_file:
                    task_meta = self._load_task_metadata(task_file)
                    acceptance_criteria = task_meta.get(
                        "acceptance_criteria", []
                    )
            # Generate synthetic promises (outside try/except so it runs
            # regardless of whether TaskLoader or fallback provided AC).
            if acceptance_criteria:
                synthetic_promises = self._generate_file_existence_promises(
                    task_id=task_id,
                    files_created=report.get("files_created", []),
                    files_modified=report.get("files_modified", []),
                    acceptance_criteria=acceptance_criteria,
                    worktree_path=self.worktree_path,
                )
                if synthetic_promises:
                    report["completion_promises"] = synthetic_promises
                    logger.info(
                        f"Generated {len(synthetic_promises)} file-existence promises "
                        f"for {task_id} (agent did not produce promises)"
                    )

        # TASK-FIX-PCN: strip orchestrator-managed paths from claim lists
        # (sibling of the state_transitions.json filter at line 2826-2862).
        # Runs as the final step before disk write so it catches paths
        # contributed by every upstream enrichment path: task_work_results
        # self-report, git diff enrichment, task_work_result.output merge,
        # agent-written player_report recovery, and the synthetic
        # completion_promises generator above. See the module-level
        # docstring on _strip_orchestrator_managed_paths.
        #
        # TASK-FIX-CAUD-J6F1 AC-003a: thread ``self.worktree_path`` so the
        # filter also catches harness-owned paths in absolute form
        # (``/Users/.../FEAT-X/.guardkit/autobuild/<TASK_ID>/...``). The
        # FEAT-JARVIS-006 fail-run-1 incident leaked exactly these into
        # the Coach because the filter only matched relative paths.
        try:
            _strip_orchestrator_managed_paths(
                report, task_id, worktree_path=self.worktree_path
            )
        except Exception as exc:  # noqa: BLE001 — never block report
            logger.warning(
                f"Orchestrator-managed-path filter failed for {task_id}: {exc}"
            )

        # Write Player report
        with open(player_report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Written Player report to {player_report_path}")

        # TASK-FIX-PIPELINE: Update task_work_results.json with enriched data (Fix 3)
        # Coach reads task_work_results.json for quality gate evaluation.
        # It must reflect the enriched file lists and any recovered promises.
        if task_work_results_path.exists():
            try:
                with open(task_work_results_path, "r") as f:
                    task_work_data = json.load(f)

                updated = False

                # Update file lists if enriched data is richer
                if len(report.get("files_modified", [])) > len(task_work_data.get("files_modified", [])):
                    task_work_data["files_modified"] = report["files_modified"]
                    updated = True

                if len(report.get("files_created", [])) > len(task_work_data.get("files_created", [])):
                    task_work_data["files_created"] = report["files_created"]
                    updated = True

                # Propagate completion_promises if not already present
                if report.get("completion_promises") and not task_work_data.get("completion_promises"):
                    task_work_data["completion_promises"] = report["completion_promises"]
                    updated = True

                # Update tests_written from enriched report
                if len(report.get("tests_written", [])) > len(task_work_data.get("tests_written", [])):
                    task_work_data["tests_written"] = report["tests_written"]
                    updated = True

                # TASK-FIX-RWOP1.3.1: re-run the agent-invocations gate against
                # the enriched data. Idempotent when phases/invocations haven't
                # changed — but this is the last on-disk rewrite before Coach
                # reads the file, so it MUST carry the freshest validation
                # block (not a stale one from _write_task_work_results's
                # initial write, which may have raced pre-enrichment).
                # TASK-ABSR-1357: thread task_type so declarative tasks don't
                # trigger a non-actionable Phase-3 advisory.
                workflow_mode = task_work_data.get("workflow_mode") or "implement-only"
                task_type = (
                    task_work_data.get("task_type")
                    if isinstance(task_work_data.get("task_type"), str)
                    else self._lookup_task_type(task_id)
                )
                new_validation = self._compute_agent_invocations_validation(
                    task_work_data, workflow_mode, task_type=task_type
                )
                if task_work_data.get("agent_invocations_validation") != new_validation:
                    task_work_data["agent_invocations_validation"] = new_validation
                    updated = True

                # TASK-FIX-RWOP1.3.2: re-run the plan-audit gate against the
                # enriched worktree state. After the file-existence fallback
                # and promise recovery paths above, the worktree may have
                # gained files the Player didn't report; the auditor scans
                # the actual filesystem, so re-running here gives Coach the
                # freshest verdict.
                new_plan_audit = self._compute_plan_audit_verdict(task_id)
                if task_work_data.get("plan_audit") != new_plan_audit:
                    task_work_data["plan_audit"] = new_plan_audit
                    updated = True

                # TASK-FIX-DF51: re-run the code_review fold against the
                # enriched data. This is the load-bearing call site: by the
                # time we get here, _inject_specialist_records_into_task_work_results
                # has already merged the orchestrator-invoked Phase-5 record
                # into agent_invocations, so the helper's path-2
                # (specialist-completion synthesis) can fire. The initial
                # write at _write_task_work_results runs *before* injection
                # and therefore won't see the orchestrator-sourced record;
                # this enrichment writeback is what actually closes the gap
                # for autobuild runs. Idempotent: returns None when an
                # existing measured score is already present, leaving the
                # legacy Player-stream block alone.
                new_code_review = self._compute_code_review_block(task_work_data)
                if new_code_review is not None and (
                    task_work_data.get("code_review") != new_code_review
                ):
                    task_work_data["code_review"] = new_code_review
                    updated = True

                if updated:
                    with open(task_work_results_path, "w") as f:
                        json.dump(task_work_data, f, indent=2)
                    logger.info(
                        f"Updated task_work_results.json with enriched data for {task_id}"
                    )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to update task_work_results.json: {e}")

    def _run_preflight_ignore_gate(self, task_id: str) -> None:
        """Run the pre-turn-1 ``git check-ignore`` fail-fast gate
        (TASK-FIX-CAUD-PREFLIGHT-C3B0).

        Closes deferred AC-005 of TASK-FIX-CAUD-J6F1. Walks the task's
        planned target list through ``git check-ignore -v --no-index``
        in the worktree. If any planned target IS git-ignored, raises
        ``AgentInvocationError`` with the matched rule so the Player
        does not burn SDK turns creating a file that cannot be tracked.

        Skipped silently when no implementation plan and no frontmatter
        ``files_to_create`` / ``files_to_modify`` list is available —
        identical to the no-plan branch in plan-audit, per the AC-005
        brief.
        """
        from guardkit.orchestrator.preflight_ignore_gate import (
            STATUS_BLOCKED,
            STATUS_PASSED,
            STATUS_SKIPPED,
            format_blocked_message,
            run_preflight_ignore_gate,
        )

        try:
            result = run_preflight_ignore_gate(task_id, self.worktree_path)
        except Exception as exc:
            # Infra-error: log and continue. The Coach still runs the
            # existence floor at turn end, so a broken pre-flight does
            # not weaken the overall detection floor — it only loses
            # the early fail-fast signal.
            logger.warning(
                "preflight_ignore_gate raised unexpectedly for %s: %s. "
                "Continuing without pre-flight.",
                task_id,
                exc,
            )
            return

        if result.status == STATUS_PASSED:
            logger.info(
                "[%s] preflight_ignore_gate: passed (no planned targets are git-ignored)",
                task_id,
            )
            return
        if result.status == STATUS_SKIPPED:
            logger.info(
                "[%s] preflight_ignore_gate: skipped (%s)",
                task_id,
                result.skip_reason or "no source available",
            )
            return
        if result.status == STATUS_BLOCKED:
            message = format_blocked_message(task_id, result)
            logger.error(
                "[%s] preflight_ignore_gate: BLOCKED — fail-fast before turn 1.\n%s",
                task_id,
                message,
            )
            raise AgentInvocationError(message)
        # Defensive: unknown status. Log and continue rather than block.
        logger.warning(
            "[%s] preflight_ignore_gate: unknown status %r; continuing.",
            task_id,
            result.status,
        )

    def _record_baseline(self) -> None:
        """Record git HEAD hash before task execution starts (TASK-FIX-VL06).

        In parallel wave execution, HEAD moves as tasks commit changes.
        Recording a per-task baseline ensures _detect_git_changes() compares
        against the correct starting point, preventing cross-task file
        attribution.
        """
        import subprocess

        with self._git_lock:
            try:
                proc = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.worktree_path),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if proc.returncode == 0:
                    self._baseline_commit = proc.stdout.strip()
                    logger.info(f"Recorded baseline commit: {self._baseline_commit[:8]}")
            except subprocess.TimeoutExpired:
                logger.warning("git rev-parse HEAD timed out, falling back to HEAD")
            except Exception as e:
                logger.warning(f"Failed to record baseline commit: {e}")

    def _detect_git_changes(self) -> Dict[str, list]:
        """Detect git changes in worktree.

        Acquires class-level _git_lock to prevent interleaved git operations
        when multiple AgentInvoker instances run in parallel (wave execution).

        Uses per-task _baseline_commit (TASK-FIX-VL06) when available,
        falling back to HEAD for backward compatibility.

        Returns:
            Dict with "modified" and "created" file lists
        """
        import subprocess

        result = {"modified": [], "created": []}

        with self._git_lock:
            try:
                # Get modified files (tracked) - use baseline commit if available (TASK-FIX-VL06)
                diff_ref = self._baseline_commit or "HEAD"
                proc = subprocess.run(
                    ["git", "diff", "--name-only", diff_ref],
                    cwd=str(self.worktree_path),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if proc.returncode == 0:
                    result["modified"] = [
                        f.strip() for f in proc.stdout.strip().split("\n") if f.strip()
                    ]

                # Get untracked files (new)
                proc = subprocess.run(
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    cwd=str(self.worktree_path),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if proc.returncode == 0:
                    result["created"] = [
                        f.strip() for f in proc.stdout.strip().split("\n") if f.strip()
                    ]

            except subprocess.TimeoutExpired:
                logger.warning("Git command timed out")
            except Exception as e:
                logger.warning(f"Git change detection failed: {e}")

        return result

    def _create_synthetic_direct_mode_report(
        self,
        task_id: str,
        turn: int,
        acceptance_criteria: Optional[List[str]] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create synthetic Player report from git changes for direct mode.

        When SDK invocation completes but doesn't produce player_turn_N.json,
        this method generates a valid report by detecting filesystem changes.
        This prevents unnecessary retries and state recovery.

        Delegates core report construction to
        ``guardkit.orchestrator.synthetic_report.build_synthetic_report``
        (TASK-FIX-D1A3). When ``task_type == "scaffolding"`` and
        ``acceptance_criteria`` is provided, file-existence promises are
        generated automatically.

        Args:
            task_id: Task identifier
            turn: Turn number (1-based)
            acceptance_criteria: Optional acceptance criteria for promise generation
            task_type: Optional task type (e.g. "scaffolding") for promise routing

        Returns:
            Dict conforming to PLAYER_REPORT_SCHEMA with ``_synthetic: True``
        """
        from guardkit.orchestrator.synthetic_report import build_synthetic_report

        files_modified: List[str] = []
        files_created: List[str] = []
        tests_written: List[str] = []
        implementation_notes = "Direct mode SDK invocation completed (synthetic report)"

        try:
            git_changes = self._detect_git_changes()
            if git_changes:
                files_modified = sorted(git_changes.get("modified", []))
                files_created = sorted(git_changes.get("created", []))

                # Identify test files from all changes
                all_files = files_modified + files_created
                tests_written = sorted([
                    f for f in all_files
                    if "test_" in f.lower() or f.lower().endswith("_test.py")
                    or "/tests/" in f or f.startswith("tests/")
                ])

                if all_files:
                    implementation_notes = (
                        f"Direct mode SDK invocation completed "
                        f"(git-detected: {len(files_modified)} modified, "
                        f"{len(files_created)} created)"
                    )
        except Exception as e:
            logger.warning(f"Git change detection failed for synthetic report: {e}")

        return build_synthetic_report(
            task_id=task_id,
            turn=turn,
            files_modified=files_modified,
            files_created=files_created,
            tests_written=tests_written,
            tests_passed=False,
            test_count=0,
            implementation_notes=implementation_notes,
            concerns=[],
            acceptance_criteria=acceptance_criteria,
            task_type=task_type,
            worktree_path=self.worktree_path,
        )

    def _find_task_file(self, task_id: str) -> Optional[Path]:
        """Find task file in standard task directories.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Path to task file if found, None otherwise
        """
        # Standard task directories
        task_dirs = [
            self.worktree_path / "tasks" / "backlog",
            self.worktree_path / "tasks" / "design_approved",
            self.worktree_path / "tasks" / "in_progress",
            self.worktree_path / "tasks" / "in_review",
            self.worktree_path / "tasks" / "completed",
            self.worktree_path / "tasks" / "blocked",
        ]

        for task_dir in task_dirs:
            if not task_dir.exists():
                continue
            # Look for task file matching task_id
            for task_file in task_dir.rglob(f"{task_id}*.md"):
                return task_file

        return None

    def _lookup_task_type(self, task_id: str) -> Optional[str]:
        """Resolve a task's ``task_type`` from its frontmatter.

        Used to thread ``task_type`` into the agent_invocations gate so
        declarative tasks in implement-only mode don't trigger a Phase-3
        advisory (TASK-ABSR-1357). Best-effort: returns None on missing
        file, missing frontmatter, or unparseable YAML — the gate falls
        back to today's behaviour for any non-string result.
        """
        task_file = self._find_task_file(task_id)
        if task_file is None:
            return None
        meta = self._load_task_metadata(task_file)
        value = meta.get("task_type") if isinstance(meta, dict) else None
        if isinstance(value, str) and value:
            return value
        return None

    def _load_task_metadata(self, task_file: Path) -> Dict[str, Any]:
        """Load task metadata from YAML frontmatter.

        Args:
            task_file: Path to task file

        Returns:
            Dict with task metadata (may be empty if no frontmatter)
        """
        import re

        try:
            content = task_file.read_text()
            # Parse YAML frontmatter between --- markers
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                import yaml
                frontmatter = frontmatter_match.group(1)
                return yaml.safe_load(frontmatter) or {}
        except Exception as e:
            logger.debug(f"Failed to load task metadata from {task_file}: {e}")

        return {}

    def _generate_file_existence_promises(
        self,
        task_id: str,
        files_created: list,
        files_modified: list,
        acceptance_criteria: list,
        worktree_path: Path,
    ) -> list:
        """Generate completion promises from file existence checks.

        Thin wrapper around the shared
        ``guardkit.orchestrator.synthetic_report.generate_file_existence_promises``
        function (TASK-FIX-D1A3). The shared function now handles
        ``evidence_type``, directory reference checks, and all regex passes.

        Args:
            task_id: Task identifier
            files_created: Files created by Player
            files_modified: Files modified by Player
            acceptance_criteria: List of AC text strings
            worktree_path: Path to worktree for disk checks

        Returns:
            List of promise dicts with criterion_id, status, evidence, evidence_type
        """
        from guardkit.orchestrator.synthetic_report import (
            generate_file_existence_promises,
        )

        return generate_file_existence_promises(
            files_created=files_created,
            files_modified=files_modified,
            acceptance_criteria=acceptance_criteria,
            worktree_path=worktree_path,
        )

    def _load_agent_report(
        self,
        task_id: str,
        turn: int,
        agent_type: Literal["player", "coach"],
    ) -> Dict[str, Any]:
        """Load and validate agent report JSON.

        Args:
            task_id: Task identifier
            turn: Turn number
            agent_type: "player" or "coach"

        Returns:
            Parsed JSON report

        Raises:
            PlayerReportNotFoundError: If Player report doesn't exist
            CoachDecisionNotFoundError: If Coach decision doesn't exist
            PlayerReportInvalidError: If Player JSON is malformed
            CoachDecisionInvalidError: If Coach JSON is malformed
        """
        report_path = self._get_report_path(task_id, turn, agent_type)

        # Check if report exists
        if not report_path.exists():
            if agent_type == "player":
                raise PlayerReportNotFoundError(
                    f"Player report not found: {report_path}"
                )
            else:
                raise CoachDecisionNotFoundError(
                    f"Coach decision not found: {report_path}"
                )

        # Load and parse JSON
        try:
            with open(report_path) as f:
                report = json.load(f)
        except json.JSONDecodeError as e:
            if agent_type == "player":
                raise PlayerReportInvalidError(
                    f"Invalid JSON in Player report: {str(e)}"
                ) from e
            else:
                raise CoachDecisionInvalidError(
                    f"Invalid JSON in Coach decision: {str(e)}"
                ) from e

        return report

    async def _retry_with_backoff(
        self,
        func,
        *args,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        **kwargs,
    ) -> Any:
        """Retry a function with exponential backoff.

        This is primarily used to handle filesystem buffering race conditions
        where a file is written by a subprocess but not immediately visible
        to the parent process.

        Args:
            func: Function to retry (can be sync or async)
            *args: Positional arguments to pass to func
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay in seconds (default: 0.1)
                          Doubles on each retry (exponential backoff)
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result from successful function call

        Raises:
            Exception from final failed attempt
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    logger.debug(
                        f"Retry attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff

        # All retries exhausted, raise the last exception
        raise last_exception

    def _get_report_path(
        self,
        task_id: str,
        turn: int,
        agent_type: Literal["player", "coach"],
    ) -> Path:
        """Get path to agent report file.

        Args:
            task_id: Task identifier
            turn: Turn number
            agent_type: "player" or "coach"

        Returns:
            Path to report file
        """
        return TaskArtifactPaths.agent_report_path(task_id, agent_type, turn, self.worktree_path)

    def _validate_player_report(self, report: Dict[str, Any]) -> None:
        """Validate Player report has required fields.

        Args:
            report: Parsed Player report JSON

        Raises:
            PlayerReportInvalidError: If required fields are missing or wrong type
        """
        missing_fields = []
        type_errors = []

        for field, expected_type in PLAYER_REPORT_SCHEMA.items():
            if field not in report:
                missing_fields.append(field)
            elif not isinstance(report[field], expected_type):
                type_errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(report[field]).__name__}"
                )

        if missing_fields or type_errors:
            error_msg = "Player report validation failed:\n"
            if missing_fields:
                error_msg += f"Missing fields: {', '.join(missing_fields)}\n"
            if type_errors:
                error_msg += f"Type errors: {', '.join(type_errors)}"
            raise PlayerReportInvalidError(error_msg)

    def _validate_coach_decision(self, decision: Dict[str, Any]) -> None:
        """Validate Coach decision has required fields.

        Args:
            decision: Parsed Coach decision JSON

        Raises:
            CoachDecisionInvalidError: If required fields are missing or wrong type
        """
        missing_fields = []
        type_errors = []

        for field, expected_type in COACH_DECISION_SCHEMA.items():
            if field not in decision:
                missing_fields.append(field)
            elif not isinstance(decision[field], expected_type):
                type_errors.append(
                    f"{field}: expected {expected_type.__name__}, "
                    f"got {type(decision[field]).__name__}"
                )

        # Validate decision value
        if "decision" in decision and decision["decision"] not in ["approve", "feedback"]:
            type_errors.append(
                f"decision: must be 'approve' or 'feedback', got '{decision['decision']}'"
            )

        if missing_fields or type_errors:
            error_msg = "Coach decision validation failed:\n"
            if missing_fields:
                error_msg += f"Missing fields: {', '.join(missing_fields)}\n"
            if type_errors:
                error_msg += f"Type errors: {', '.join(type_errors)}"
            raise CoachDecisionInvalidError(error_msg)

    # =========================================================================
    # Task-Work Delegation Methods
    # =========================================================================

    def _write_coach_feedback(
        self,
        task_id: str,
        turn: int,
        feedback: Union[str, Dict[str, Any]],
    ) -> Path:
        """Write Coach feedback to file for task-work to read.

        When using task-work delegation, Coach feedback from the previous turn
        is written to a file that task-work can read as context.

        The feedback is written in structured JSON format to enable:
        - Categorization of must-fix vs should-fix issues
        - Precise file/line references for subagent context
        - Machine-readable format for automated processing

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (feedback is from turn-1)
            feedback: Coach feedback (can be string or dict from Coach decision)

        Returns:
            Path to the written feedback file (JSON format)
        """
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        # Parse feedback into structured format
        structured_feedback = self._parse_coach_feedback(feedback, turn)

        feedback_path = autobuild_dir / f"coach_feedback_for_turn_{turn}.json"
        with open(feedback_path, "w") as f:
            json.dump(structured_feedback, f, indent=2)

        logger.debug(f"Wrote Coach feedback to {feedback_path}")
        return feedback_path

    def _parse_coach_feedback(
        self,
        feedback: Union[str, Dict[str, Any]],
        turn: int,
    ) -> Dict[str, Any]:
        """Parse Coach feedback into structured format.

        Extracts must-fix and should-fix issues from Coach feedback,
        categorizing them for prioritization by the implementation subagent.

        Args:
            feedback: Raw feedback string from Coach (may be JSON-like or plain text)
            turn: Current turn number

        Returns:
            Structured feedback dictionary with categorized issues
        """
        # Initialize structured feedback
        structured = {
            "turn": turn,
            "feedback_from_turn": turn - 1,
            "feedback_summary": "",
            "must_fix": [],
            "should_fix": [],
            "validation_results": {},
            "raw_feedback": feedback if isinstance(feedback, str) else "",
        }

        # If feedback is already a dict (from Coach decision JSON), extract fields
        if isinstance(feedback, dict):
            structured["feedback_summary"] = feedback.get(
                "rationale", feedback.get("feedback_summary", "")
            )
            structured["validation_results"] = feedback.get("validation_results", {})

            # Extract issues if present
            for issue in feedback.get("issues", []):
                issue_entry = {
                    "issue": issue.get("description", ""),
                    "location": issue.get("location", ""),
                    "suggestion": issue.get("suggestion", ""),
                    "type": issue.get("type", "unknown"),
                }
                # Categorize by severity
                if issue.get("severity") in ["critical", "major"]:
                    structured["must_fix"].append(issue_entry)
                else:
                    structured["should_fix"].append(issue_entry)

        else:
            # Plain text feedback - store as summary
            structured["feedback_summary"] = feedback
            structured["raw_feedback"] = feedback

        return structured

    def load_coach_feedback(self, task_id: str, turn: int) -> Optional[Dict[str, Any]]:
        """Load Coach feedback for a specific turn.

        This method loads the structured Coach feedback from the JSON file
        created by _write_coach_feedback. Used by task-work to inject
        feedback context into implementation subagent prompts.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Turn number for which to load feedback

        Returns:
            Structured feedback dictionary if found, None otherwise
        """
        feedback_path = self._get_coach_feedback_path(task_id, turn)

        if not feedback_path.exists():
            logger.debug(f"No Coach feedback found at {feedback_path}")
            return None

        try:
            with open(feedback_path) as f:
                feedback = json.load(f)
            logger.debug(f"Loaded Coach feedback from {feedback_path}")
            return feedback
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Coach feedback JSON: {e}")
            return None

    def _get_coach_feedback_path(self, task_id: str, turn: int) -> Path:
        """Get path to Coach feedback file for a specific turn.

        Args:
            task_id: Task identifier
            turn: Turn number

        Returns:
            Path to feedback file
        """
        return (
            self.worktree_path
            / ".guardkit"
            / "autobuild"
            / task_id
            / f"coach_feedback_for_turn_{turn}.json"
        )

    def _write_turn_context(
        self,
        task_id: str,
        turn: int,
        max_turns: int,
        approaching_limit: bool,
    ) -> Path:
        """Write turn context for Player agent to read.

        This file provides the Player with orchestration context including:
        - Current turn number and max turns
        - Whether approaching the turn limit (escape hatch trigger)
        - When to generate a blocked_report

        The Player reads this file to determine if it should include
        a blocked_report in its JSON output (escape hatch pattern).

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            max_turns: Maximum turns allowed
            approaching_limit: True if turn >= max_turns - 1

        Returns:
            Path to the written context file
        """
        autobuild_dir = TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        context = {
            "task_id": task_id,
            "turn": turn,
            "max_turns": max_turns,
            "turns_remaining": max_turns - turn,
            "approaching_limit": approaching_limit,
            "escape_hatch_active": approaching_limit,
            "instructions": (
                "If approaching_limit is true and you cannot complete the task, "
                "include a 'blocked_report' field in your player report JSON. "
                "See autobuild-player.md for the blocked_report schema."
            ),
            # TASK-PSN-003: Promise schema reminder — second source of truth so
            # the agent can re-check field names even after many SDK turns.
            "promise_schema_reminder": _PROMISE_SCHEMA_FIELDS,
        }

        context_path = autobuild_dir / "turn_context.json"
        with open(context_path, "w") as f:
            json.dump(context, f, indent=2)

        logger.debug(
            f"Wrote turn context to {context_path}: "
            f"turn={turn}/{max_turns}, approaching_limit={approaching_limit}"
        )
        return context_path

    def load_turn_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load turn context for a task.

        This method loads the turn context file written by _write_turn_context.
        Used by the Player agent to determine if escape hatch is active.

        Args:
            task_id: Task identifier

        Returns:
            Turn context dictionary if found, None otherwise
        """
        context_path = TaskArtifactPaths.autobuild_dir(task_id, self.worktree_path) / "turn_context.json"

        if not context_path.exists():
            logger.debug(f"No turn context found at {context_path}")
            return None

        try:
            with open(context_path) as f:
                context = json.load(f)
            logger.debug(f"Loaded turn context from {context_path}")
            return context
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse turn context JSON: {e}")
            return None

    def _get_implementation_mode(self, task_id: str) -> str:
        """Determine implementation mode from task frontmatter or auto-detection.

        Checks the task file for an explicit `implementation_mode` field in the
        frontmatter first. If no explicit mode is set, defaults to task-work for
        all tasks with complexity >= 2. Direct mode is only auto-selected for
        scaffolding tasks with complexity <= 1.

        Task-work mode is structurally superior for non-trivial tasks:
        - Natural generator exhaustion (no cancel scope race condition)
        - 1.5x SDK timeout multiplier
        - Agent-written reports with real completion_promises
        - Rich stream parsing with tool use tracking

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Implementation mode: "direct" or "task-work"

        Note:
            Import is inside method to avoid circular dependency with TaskLoader.
            Errors are logged but don't fail - defaults to "task-work" behavior.
            Unknown modes (including legacy "manual" mode) are normalized to "task-work".
            Auto-detection only applies when no explicit implementation_mode is set.
        """
        try:
            from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError

            task_data = TaskLoader.load_task(task_id, self.worktree_path)
            frontmatter = task_data.get("frontmatter", {})
            impl_mode = frontmatter.get("implementation_mode")

            # Explicit frontmatter overrides always take priority
            if impl_mode == "direct":
                logger.info(
                    f"[{task_id}] Mode: direct (explicit frontmatter override)"
                )
                return "direct"

            if impl_mode == "task-work":
                logger.info(
                    f"[{task_id}] Mode: task-work (explicit frontmatter override)"
                )
                return "task-work"

            if impl_mode:
                logger.info(
                    f"[{task_id}] Mode: task-work (unknown implementation_mode "
                    f"'{impl_mode}' normalized)"
                )
                return "task-work"

            # No explicit mode - auto-detect based on task type and complexity
            return self._auto_detect_direct_mode(task_id, task_data)

        except Exception as e:
            # Import inside to avoid circular dependency issues at module level
            from guardkit.tasks.task_loader import TaskNotFoundError

            if isinstance(e, TaskNotFoundError):
                logger.debug(f"[{task_id}] Task file not found, using default task-work path")
            else:
                logger.warning(f"[{task_id}] Error loading task for mode detection: {e}")

            return "task-work"

    def _auto_detect_direct_mode(self, task_id: str, task_data: dict) -> str:
        """Auto-detect if a task is eligible for direct mode.

        Direct mode is only used for scaffolding tasks with complexity <= 1.
        All other tasks default to task-work mode, which provides structural
        reliability benefits (natural generator exhaustion, SDK timeout
        multiplier, agent-written reports).

        Args:
            task_id: Task identifier for logging
            task_data: Parsed task data from TaskLoader

        Returns:
            "direct" if eligible, "task-work" otherwise
        """
        frontmatter = task_data.get("frontmatter", {})
        complexity = frontmatter.get("complexity")
        task_type = frontmatter.get("task_type", "")

        # Require explicit complexity score for auto-detection
        if complexity is None:
            logger.info(
                f"[{task_id}] Mode: task-work (auto-selected, "
                "no complexity score)"
            )
            return "task-work"

        try:
            complexity = int(complexity)
        except (ValueError, TypeError):
            logger.info(
                f"[{task_id}] Mode: task-work (auto-selected, "
                f"invalid complexity '{complexity}')"
            )
            return "task-work"

        # Direct mode only for scaffolding tasks with complexity <= 1
        if task_type == "scaffolding" and complexity <= 1:
            logger.info(
                f"[{task_id}] Mode: direct (auto-selected, "
                f"scaffolding task with complexity={complexity})"
            )
            return "direct"

        # All other tasks use task-work for reliability
        logger.info(
            f"[{task_id}] Mode: task-work (auto-selected, "
            f"complexity={complexity}, task_type='{task_type}')"
        )
        return "task-work"

    def _calculate_sdk_timeout(
        self,
        task_id: str,
        remaining_budget: Optional[float] = None,
    ) -> int:
        """Calculate dynamic SDK timeout based on task characteristics.

        Adjusts the base timeout using:
        - Implementation mode multiplier (task-work=1.5x, direct=1.0x)
        - Complexity multiplier (1.0 + complexity/10.0, range 1.1x-2.0x)

        If the user provided a CLI override (sdk_timeout_seconds differs from
        DEFAULT_SDK_TIMEOUT), returns that value unchanged.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            remaining_budget: Optional remaining wall-clock budget in seconds.
                When provided, the effective timeout is capped at this value so
                the SDK call does not exceed the overall task budget. CLI overrides
                take precedence and are never capped. (TASK-ABFIX-004)

        Returns:
            Effective timeout in seconds, capped at MAX_SDK_TIMEOUT (3600s)
        """
        # Respect CLI override: if user explicitly set a timeout, don't recalculate
        if self._sdk_timeout_is_override:
            logger.info(
                f"[{task_id}] SDK timeout: {self.sdk_timeout_seconds}s "
                f"(CLI override, skipping dynamic calculation)"
            )
            return self.sdk_timeout_seconds

        base_timeout = self.sdk_timeout_seconds

        try:
            from guardkit.tasks.task_loader import TaskLoader

            task_data = TaskLoader.load_task(task_id, self.worktree_path)
            frontmatter = task_data.get("frontmatter", {})

            mode = frontmatter.get("implementation_mode", "task-work")
            complexity = frontmatter.get("complexity", 5)

            # Clamp complexity to valid range
            complexity = max(1, min(10, int(complexity)))

        except Exception as e:
            logger.debug(
                f"[{task_id}] Could not load task for timeout calculation: {e}. "
                "Using defaults (mode=task-work, complexity=5)"
            )
            mode = "task-work"
            complexity = 5

        # Mode multiplier
        if mode == "task-work":
            mode_multiplier = 1.5
        else:
            mode_multiplier = 1.0

        # Complexity multiplier: 1.1x (complexity=1) to 2.0x (complexity=10)
        complexity_multiplier = 1.0 + (complexity / 10.0)

        effective_timeout = int(base_timeout * mode_multiplier * complexity_multiplier)

        # TASK-FIX-VL05: Apply local backend timeout multiplier
        if self.timeout_multiplier != 1.0:
            effective_timeout = int(effective_timeout * self.timeout_multiplier)

        # Cap at maximum (also scaled by multiplier for local backends)
        max_timeout = int(MAX_SDK_TIMEOUT * self.timeout_multiplier)
        effective_timeout = min(effective_timeout, max_timeout)

        # Cap at remaining task budget when provided (TASK-ABFIX-004)
        if remaining_budget is not None:
            effective_timeout = min(effective_timeout, int(remaining_budget))

        logger.info(
            f"[{task_id}] SDK timeout: {effective_timeout}s "
            f"(base={base_timeout}s, mode={mode} x{mode_multiplier}, "
            f"complexity={complexity} x{complexity_multiplier:.1f}"
            f"{f', backend x{self.timeout_multiplier}' if self.timeout_multiplier != 1.0 else ''}"
            f"{f', budget_cap={int(remaining_budget)}s' if remaining_budget is not None else ''})"
        )

        return effective_timeout

    def _calculate_sdk_max_turns(self, task_id: str) -> int:
        """Calculate dynamic SDK max turns based on task complexity.

        TASK-ABSR-MAXT: Mirrors `_calculate_sdk_timeout`'s complexity scaling so
        the SDK turn budget grows with task complexity instead of remaining a flat
        hardcoded constant. Without this, complex tasks routinely run out of
        conversation turns even when wall-time budget remains.

        Behaviour:
        - If the user provided a `GUARDKIT_SDK_MAX_TURNS` env-var override
          (`_SDK_MAX_TURNS_IS_OVERRIDE`), returns `TASK_WORK_SDK_MAX_TURNS`
          unchanged (env-var-wins semantics, matches `_calculate_sdk_timeout`'s
          handling of `_sdk_timeout_is_override`).
        - Otherwise, loads the task's complexity from frontmatter via
          `TaskLoader.load_task`, clamps to `[1, 10]`, and returns
          `int(TASK_WORK_SDK_MAX_TURNS * (1.0 + complexity / 10.0))`.
        - Defaults to complexity 5 (1.5x multiplier) on any load error.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Effective max turns for the task-work SDK invocation.
        """
        base = TASK_WORK_SDK_MAX_TURNS

        if _SDK_MAX_TURNS_IS_OVERRIDE:
            logger.info(
                f"[{task_id}] Max turns: {base} "
                f"(env override GUARDKIT_SDK_MAX_TURNS, skipping complexity scaling)"
            )
            return base

        try:
            from guardkit.tasks.task_loader import TaskLoader

            task_data = TaskLoader.load_task(task_id, self.worktree_path)
            frontmatter = task_data.get("frontmatter", {})
            complexity = frontmatter.get("complexity", 5)
            complexity = max(1, min(10, int(complexity)))
        except Exception as e:
            logger.debug(
                f"[{task_id}] Could not load task for max-turns calculation: {e}. "
                "Using default complexity=5"
            )
            complexity = 5

        multiplier = 1.0 + (complexity / 10.0)
        scaled = int(base * multiplier)

        # TASK-ABSR-FLOR: floor the scaled value to SDK_MAX_TURNS_FLOOR (150).
        # Only applied here — the env-override branch above returned early, so
        # an explicit GUARDKIT_SDK_MAX_TURNS bypasses the floor (user's value
        # wins, matching `_calculate_sdk_timeout`'s override semantics).
        effective_max_turns = max(SDK_MAX_TURNS_FLOOR, scaled)
        floor_applied = effective_max_turns > scaled

        logger.info(
            f"[{task_id}] Max turns: {effective_max_turns} "
            f"(base={base}, complexity={complexity} x{multiplier:.1f}"
            f"{f', floored from {scaled} to {SDK_MAX_TURNS_FLOOR}' if floor_applied else ''})"
        )

        return effective_max_turns

    async def _invoke_player_direct(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
        context: str = "",
    ) -> AgentInvocationResult:
        """Invoke Player directly via SDK for direct mode tasks.

        Direct mode tasks bypass task-work delegation and don't require an
        implementation plan. Used for straightforward file changes like
        documentation updates, configuration, or simple modifications.

        After successful invocation, writes a minimal task_work_results.json
        for Coach validation compatibility.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            requirements: Task requirements from markdown
            feedback: Optional Coach feedback from previous turn
            max_turns: Maximum turns allowed
            context: Job-specific context from Graphiti

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
            SDKTimeoutError: If invocation exceeds timeout
        """
        start_time = time.time()

        try:
            logger.info(f"Invoking Player via direct SDK for {task_id} (turn {turn})")

            # Extract structured acceptance criteria so the prompt includes
            # AC IDs and completion_promises examples.  Without this, vLLM
            # models produce generic summaries that fail Coach text matching
            # on Turn 1 (see TASK-INV-0A11).
            acceptance_criteria = self.extract_acceptance_criteria(task_id) or None

            # Build prompt for Player
            prompt = self._build_player_prompt(
                task_id, turn, requirements, feedback,
                acceptance_criteria=acceptance_criteria,
                context=context,
            )

            # Invoke SDK with Player permissions (Read, Write, Edit, Bash)
            # Model selection delegated to CLI default
            # TASK-RFX-B20B: Pass resume_session_id for session continuity
            await self._invoke_with_role(
                prompt=prompt,
                agent_type="player",
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
                permission_mode="acceptEdits",
                resume_session_id=self._last_session_id,
                task_id=task_id,
                turn=turn,
            )

            # Add small delay to allow filesystem buffering to complete
            # This mitigates race conditions where SDK subprocess writes report
            # but parent process doesn't see it immediately
            await asyncio.sleep(0.1)

            # Check if SDK wrote the report; create synthetic if missing
            # In direct mode, the SDK Player sometimes doesn't write
            # player_turn_N.json, causing retries to fail and triggering
            # unnecessary state recovery (wastes a turn)
            used_synthetic = False
            report_path = self._get_report_path(task_id, turn, "player")
            if not report_path.exists():
                logger.info(
                    f"SDK did not write player_turn_{turn}.json for {task_id}, "
                    f"creating synthetic report from git detection"
                )
                # Load acceptance_criteria from task markdown body (not just
                # YAML frontmatter) so file-existence promises can be generated
                # for scaffolding tasks.  TaskLoader parses both frontmatter
                # and the ## Acceptance Criteria section in the body.
                acceptance_criteria = None
                task_type_meta = None
                task_file = self._find_task_file(task_id)
                if task_file:
                    try:
                        from guardkit.tasks.task_loader import TaskLoader
                        task_data = TaskLoader._parse_task_file(task_file, task_id)
                        acceptance_criteria = task_data.get("acceptance_criteria") or None
                        task_type_meta = task_data["frontmatter"].get("task_type")
                    except Exception as e:
                        logger.debug(
                            f"Failed to parse task spec for synthetic promises: {e}"
                        )
                        # Fallback: still try YAML-only for task_type
                        metadata = self._load_task_metadata(task_file)
                        task_type_meta = metadata.get("task_type")

                synthetic_report = self._create_synthetic_direct_mode_report(
                    task_id,
                    turn,
                    acceptance_criteria=acceptance_criteria,
                    task_type=task_type_meta,
                )
                self._write_player_report_for_direct_mode(
                    task_id, turn, synthetic_report, success=True
                )
                used_synthetic = True

            # Load and validate Player report with retry logic
            # Handles filesystem buffering race condition where report file
            # is written by SDK subprocess but not immediately visible
            report = await self._retry_with_backoff(
                self._load_agent_report,
                task_id,
                turn,
                "player",
                max_retries=3,
                initial_delay=0.1,
            )
            self._validate_player_report(report)

            # Write task_work_results.json for Coach compatibility
            self._write_direct_mode_results(task_id, report, success=True)

            # Write player_turn_N.json for orchestrator state tracking
            # This harmonizes direct mode with task-work delegation path
            # Skip if synthetic path already wrote the report (avoid double-write)
            if not used_synthetic:
                self._write_player_report_for_direct_mode(task_id, turn, report, success=True)

            duration = time.time() - start_time

            # TASK-VOPT-002: Per-turn timing instrumentation (direct mode)
            logger.info(
                "[%s] SDK invocation complete: %.1fs (direct mode)",
                task_id, duration,
            )

            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=True,
                report=report,
                duration_seconds=duration,
                session_id=self._last_session_id,  # TASK-RFX-B20B
            )

        except (PlayerReportNotFoundError, PlayerReportInvalidError) as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            error_msg = str(e)
            # Write failure results for Coach
            self._write_direct_mode_results(
                task_id,
                error_report,
                success=False,
                error=error_msg,
            )
            # Write player_turn_N.json for orchestrator state tracking
            self._write_player_report_for_direct_mode(
                task_id,
                turn,
                error_report,
                success=False,
                error=error_msg,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=error_msg,
                session_id=self._last_session_id,  # TASK-RFX-B20B
            )
        except SDKTimeoutError as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            error_msg = f"SDK timeout: {str(e)}"
            self._write_direct_mode_results(
                task_id,
                error_report,
                success=False,
                error=error_msg,
            )
            # Write player_turn_N.json for orchestrator state tracking
            self._write_player_report_for_direct_mode(
                task_id,
                turn,
                error_report,
                success=False,
                error=error_msg,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
            )
        except Exception as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            error_msg = f"Unexpected error: {str(e)}"
            self._write_direct_mode_results(
                task_id,
                error_report,
                success=False,
                error=error_msg,
            )
            # Write player_turn_N.json for orchestrator state tracking
            self._write_player_report_for_direct_mode(
                task_id,
                turn,
                error_report,
                success=False,
                error=error_msg,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report={},
                duration_seconds=duration,
                error=error_msg,
                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
            )

    def _write_direct_mode_results(
        self,
        task_id: str,
        player_report: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ) -> Path:
        """Write task_work_results.json for direct mode Coach validation.

        Creates a minimal results file that Coach can read for validation.
        Direct mode tasks have relaxed quality gate requirements:
        - No architectural review required (marked as passed)
        - No plan audit required (no plan exists)
        - Coverage threshold is optional

        Args:
            task_id: Task identifier
            player_report: Player's report with files and test status
            success: Whether Player invocation succeeded
            error: Error message if success=False

        Returns:
            Path to the written results file
        """
        # Ensure results directory exists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Extract test info from Player report
        tests_run = player_report.get("tests_run", False)
        tests_passed = player_report.get("tests_passed", False)
        tests_written = player_report.get("tests_written", [])

        # Derive test count: use tests_passed_count if available (task-work path),
        # otherwise derive from tests_written list length when tests_passed is True
        tests_passed_count = player_report.get("tests_passed_count", 0)
        if tests_passed_count == 0 and tests_passed and tests_written:
            tests_passed_count = len(tests_written)

        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": success and tests_passed if tests_run else success,
            "success": success,
            "implementation_mode": "direct",
            "phases": {
                "phase_3": {"detected": True, "completed": success},
            },
            "quality_gates": {
                "tests_passing": tests_passed if tests_run else None,
                "tests_passed": tests_passed_count,
                "tests_failed": player_report.get("tests_failed_count", 0),
                "coverage": None,  # No coverage requirement for direct mode
                "coverage_met": True,  # Direct mode relaxes coverage
                "quality_gates_relaxed": True,  # Signal to Coach
                "all_passed": success,
            },
            "files_modified": sorted(list(set(player_report.get("files_modified", [])))),
            "files_created": sorted(list(set(player_report.get("files_created", [])))),
            "tests_written": sorted(list(set(tests_written))),
            "requirements_addressed": player_report.get("requirements_addressed", []),
            "requirements_met": player_report.get("requirements_met",
                player_report.get("requirements_addressed", [])),
            "summary": (
                f"Direct mode implementation {'completed successfully' if success else 'failed'}"
                + (f": {error}" if error else "")
            ),
        }

        if error:
            results["error"] = error
            results["error_type"] = "DirectModeError"

        # Include completion_promises if Player reported them (TASK-FIX-ACA7b)
        completion_promises = player_report.get("completion_promises", [])
        if completion_promises:
            results["completion_promises"] = completion_promises

        # Propagate _synthetic flag from player_report (TASK-FIX-D1A3)
        if player_report.get("_synthetic"):
            results["_synthetic"] = True

        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote direct mode results to {results_file}")

        return results_file

    def _write_player_report_for_direct_mode(
        self,
        task_id: str,
        turn: int,
        player_report: Dict[str, Any],
        success: bool = True,
        error: Optional[str] = None,
    ) -> Path:
        """Write player_turn_N.json for direct mode orchestrator compatibility.

        Direct mode tasks bypass task-work delegation but the AutoBuild orchestrator
        expects player_turn_{turn}.json for state tracking. This method creates that
        file from the direct mode invocation results.

        This harmonizes direct mode Player output with the task-work delegation path,
        ensuring Coach validation and orchestrator state recovery work correctly
        regardless of which path was used.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Turn number (1-based)
            player_report: Player's report from SDK invocation
            success: Whether Player invocation succeeded
            error: Error message if success=False

        Returns:
            Path to the written player report file
        """
        # Ensure autobuild directory exists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        player_report_path = TaskArtifactPaths.player_report_path(
            task_id, turn, self.worktree_path
        )

        # Build PLAYER_REPORT_SCHEMA compliant report
        report: Dict[str, Any] = {
            "task_id": task_id,
            "turn": turn,
            "files_modified": player_report.get("files_modified", []),
            "files_created": player_report.get("files_created", []),
            "tests_written": player_report.get("tests_written", []),
            "tests_run": player_report.get("tests_run", False),
            "tests_passed": player_report.get("tests_passed", False),
            "test_output_summary": player_report.get("test_output_summary", ""),
            "implementation_notes": player_report.get(
                "implementation_notes",
                "Direct mode implementation via SDK"
            ),
            "concerns": player_report.get("concerns", []),
            "requirements_addressed": player_report.get("requirements_addressed", []),
            "requirements_remaining": player_report.get("requirements_remaining", []),
            "implementation_mode": "direct",
        }

        # Include completion_promises if Player reported them (TASK-FIX-ACA7b)
        completion_promises = player_report.get("completion_promises", [])
        if completion_promises:
            report["completion_promises"] = completion_promises

        # Propagate _synthetic flag (mirrors _write_direct_mode_results pattern)
        if player_report.get("_synthetic"):
            report["_synthetic"] = True

        # Add error info if failed
        if not success and error:
            report["error"] = error
            report["success"] = False
        else:
            report["success"] = True

        # Write the report
        player_report_path.write_text(json.dumps(report, indent=2))
        logger.info(f"Wrote direct mode player report to {player_report_path}")

        return player_report_path

    def format_feedback_for_prompt(self, feedback: Dict[str, Any]) -> str:
        """Format structured feedback for inclusion in subagent prompts.

        Converts the structured feedback dictionary into a human-readable
        format suitable for injection into implementation subagent prompts.
        Prioritizes must-fix items over should-fix items.

        Args:
            feedback: Structured feedback from load_coach_feedback()

        Returns:
            Formatted string for prompt injection
        """
        lines = []
        turn = feedback.get("turn", 0)
        from_turn = feedback.get("feedback_from_turn", turn - 1)

        lines.append(f"## Coach Feedback from Turn {from_turn}")
        lines.append("")

        # Summary
        if feedback.get("feedback_summary"):
            lines.append(f"**Summary**: {feedback['feedback_summary']}")
            lines.append("")

        # Must-fix items (critical/major severity)
        must_fix = feedback.get("must_fix", [])
        if must_fix:
            lines.append("### 🔴 MUST FIX (Critical/Major Issues)")
            lines.append("")
            for i, issue in enumerate(must_fix, 1):
                lines.append(f"{i}. **{issue.get('issue', 'Issue')}**")
                if issue.get("location"):
                    lines.append(f"   - Location: `{issue['location']}`")
                if issue.get("suggestion"):
                    lines.append(f"   - Suggestion: {issue['suggestion']}")
                lines.append("")

        # Should-fix items (minor severity)
        should_fix = feedback.get("should_fix", [])
        if should_fix:
            lines.append("### 🟡 SHOULD FIX (Minor Issues)")
            lines.append("")
            for i, issue in enumerate(should_fix, 1):
                lines.append(f"{i}. **{issue.get('issue', 'Issue')}**")
                if issue.get("location"):
                    lines.append(f"   - Location: `{issue['location']}`")
                if issue.get("suggestion"):
                    lines.append(f"   - Suggestion: {issue['suggestion']}")
                lines.append("")

        # Validation results summary
        validation = feedback.get("validation_results", {})
        if validation:
            lines.append("### Validation Results")
            lines.append("")
            if "tests_passed" in validation:
                status = "✅ Passed" if validation["tests_passed"] else "❌ Failed"
                lines.append(f"- Tests: {status}")
            if validation.get("test_output_summary"):
                lines.append(f"- Test Output: {validation['test_output_summary']}")
            if validation.get("code_quality"):
                lines.append(f"- Code Quality: {validation['code_quality']}")
            lines.append("")

        lines.append("---")
        lines.append("*Address all MUST FIX items before submitting. SHOULD FIX items are recommended but optional.*")

        return "\n".join(lines)

    # =========================================================================
    # Task-Work Delegation Methods
    # =========================================================================

    def _build_autobuild_implementation_prompt(
        self,
        task_id: str,
        mode: str = "standard",
        documentation_level: str = "minimal",
        turn: int = 1,
        requirements: str = "",
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
        context: str = "",
    ) -> str:
        """Build implementation prompt using loaded execution protocol.

        TASK-ACO-002: Replaces _build_inline_implement_protocol() with a
        prompt that loads the execution protocol from autobuild_execution_protocol.md
        via load_protocol(), and injects task requirements, coach feedback,
        graphiti context, and turn context inline.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")
            documentation_level: Documentation level ("minimal", "standard",
                or "comprehensive")
            turn: Current turn number (1-based)
            requirements: Task requirements from task markdown
            feedback: Optional Coach feedback from previous turn
            max_turns: Maximum turns allowed for this orchestration
            context: Job-specific context from Graphiti

        Returns:
            Assembled prompt string with protocol and all context sections
        """
        approaching_limit = turn >= max_turns - 1

        # --- Section 1: Header ---
        header = (
            f"You are executing the implementation phase (Phases 3-5) for {task_id}.\n"
            f"\n"
            f"## Context\n"
            f"\n"
            f"- Task ID: {task_id}\n"
            f"- Mode: {mode}\n"
            f"- Documentation Level: {documentation_level}\n"
            f"- Working directory: {self.worktree_path}\n"
        )

        # --- Section 2: Turn context (inline) ---
        turn_section = (
            f"\n## Turn Context\n"
            f"\n"
            f"- Current turn: {turn}\n"
            f"- Max turns: {max_turns}\n"
            f"- Turns remaining: {max_turns - turn}\n"
            f"- Approaching limit: {approaching_limit}\n"
        )
        if approaching_limit:
            turn_section += (
                "\nWARNING: Approaching turn limit. If you cannot complete the task,\n"
                "include a 'blocked_report' field in your player report.\n"
            )

        # --- Section 3: Requirements (inline) ---
        requirements_section = ""
        if requirements:
            requirements_section = (
                f"\n## Task Requirements\n"
                f"\n"
                f"{requirements}\n"
            )

        # --- Section 4: Coach feedback (inline when available) ---
        feedback_section = ""
        if feedback and turn > 1:
            formatted = self._format_feedback_for_prompt(feedback, turn)
            feedback_section = (
                f"\n## Coach Feedback from Turn {turn - 1}\n"
                f"\n"
                f"{formatted}\n"
                f"\n"
                f"Address ALL must_fix items before proceeding.\n"
            )

        # --- Section 5: Graphiti context (inline when available) ---
        context_section = ""
        if context:
            context_section = (
                f"\n## Job-Specific Context\n"
                f"\n"
                f"{context}\n"
            )

        # --- Section 6: Execution protocol (loaded from file) ---
        # TASK-VOPT-001 / TASK-VR6-MP01: Use medium protocol for local
        # backends. Medium (~10KB) restores anti-stub examples and stack
        # patterns that slim (~5.5KB) removed, reducing 24-174% turn
        # inflation observed in vLLM Runs 5-6 while staying well below
        # the full protocol (~19KB).
        if self.timeout_multiplier > 1.0:
            protocol_name = "autobuild_execution_protocol_medium"
        else:
            protocol_name = "autobuild_execution_protocol"
        protocol_content = load_protocol(protocol_name)
        # Substitute placeholders in protocol
        protocol_content = protocol_content.replace("{task_id}", task_id)
        protocol_content = protocol_content.replace("{turn}", str(turn))
        protocol_content = protocol_content.replace("{worktree_path}", str(self.worktree_path))

        # --- Section 7: Implementation plan locations ---
        plan_paths = TaskArtifactPaths.implementation_plan_paths(
            task_id, self.worktree_path
        )
        plan_locations = "\n".join(f"   - {p}" for p in plan_paths)
        plan_section = (
            f"\n## Implementation Plan Locations\n"
            f"\n"
            f"Check these paths in order for the implementation plan:\n"
            f"{plan_locations}\n"
        )

        # Assemble final prompt
        prompt = (
            header
            + turn_section
            + requirements_section
            + feedback_section
            + context_section
            + "\n---\n\n"
            + protocol_content
            + plan_section
        )

        return prompt

    def _format_feedback_for_prompt(
        self,
        feedback: Union[str, Dict[str, Any]],
        turn: int,
    ) -> str:
        """Format Coach feedback for inline prompt inclusion.

        Args:
            feedback: Coach feedback as string or structured dict
            turn: Current turn number

        Returns:
            Formatted feedback string suitable for prompt inclusion
        """
        if isinstance(feedback, str):
            return feedback

        # Structured feedback dict - extract key fields
        parts: List[str] = []

        # Summary/rationale
        rationale = feedback.get("rationale") or feedback.get("feedback_summary", "")
        if rationale:
            parts.append(f"**Summary**: {rationale}")

        # Must-fix issues
        issues = feedback.get("issues", [])
        must_fix = [i for i in issues if i.get("severity") == "must_fix"]
        should_fix = [i for i in issues if i.get("severity") == "should_fix"]

        if must_fix:
            parts.append("\n**Must Fix:**")
            for issue in must_fix:
                desc = issue.get("description", str(issue))
                parts.append(f"- {desc}")

        if should_fix:
            parts.append("\n**Should Fix:**")
            for issue in should_fix:
                desc = issue.get("description", str(issue))
                parts.append(f"- {desc}")

        # If no structured fields found, dump the whole dict
        if not parts:
            return json.dumps(feedback, indent=2)

        return "\n".join(parts)

    def _build_inline_implement_protocol(
        self,
        task_id: str,
        mode: str = "standard",
    ) -> str:
        """Build inline implementation protocol prompt for Phases 3-5.

        TASK-POF-004: Replaces /task-work skill invocation with an inline
        protocol to eliminate ~839KB preamble overhead per Player turn.
        The inline prompt covers Phases 3 (Implementation), 4 (Testing),
        4.5 (Fix Loop), and 5 (Code Review).

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")

        Returns:
            Inline protocol prompt string (target: ≤20KB)
        """
        # Build plan locations list for the prompt
        plan_paths = TaskArtifactPaths.implementation_plan_paths(
            task_id, self.worktree_path
        )
        plan_locations = "\n".join(f"   - {p}" for p in plan_paths)

        # Build feedback file path hint
        autobuild_dir = f".guardkit/autobuild/{task_id}"
        feedback_hint = (
            f"Check for Coach feedback at: {autobuild_dir}/coach_feedback_for_turn_*.json\n"
            "If feedback exists, address ALL must_fix items before proceeding."
        )

        # Build turn context hint
        turn_context_hint = (
            f"Check for turn context at: {autobuild_dir}/turn_context.json\n"
            "If approaching_limit is true and you cannot complete the task,\n"
            "include a 'blocked_report' field in your player report."
        )

        # Mode-specific instructions
        mode_instructions = ""
        if mode == "tdd":
            mode_instructions = """
### TDD Mode
Follow RED-GREEN-REFACTOR cycle:
1. Write failing tests first (RED)
2. Write minimal implementation to pass tests (GREEN)
3. Refactor for quality while keeping tests green (REFACTOR)
"""
        elif mode == "bdd":
            mode_instructions = """
### BDD Mode
Implementation must make BDD step definitions pass:
1. Read the Gherkin scenarios linked in the task
2. Implement code to satisfy Given/When/Then steps
3. Run BDD tests to verify scenarios pass
"""

        protocol = f"""You are executing the implementation phase (Phases 3-5) for {task_id}.

## Context

- Task ID: {task_id}
- Mode: {mode}
- Working directory: {self.worktree_path}

{feedback_hint}

{turn_context_hint}
{mode_instructions}
## Phase 3: Implementation

1. **Read the implementation plan** from one of these locations (check in order):
{plan_locations}

2. **Implement the code changes** described in the plan:
   - Create new files as specified
   - Modify existing files as specified
   - Follow the architecture and patterns from the plan
   - Write production-quality code with proper error handling

3. **Track your changes** - note every file you create or modify.

## Phase 4: Testing

1. **Verify compilation/build** first - ensure no syntax errors:
   - Python: `python -m py_compile <file>` or import check
   - TypeScript: `npx tsc --noEmit`
   - .NET: `dotnet build`

2. **Run the test suite**:
   - Python: `pytest tests/ -v --tb=short`
   - TypeScript: `npm test`
   - .NET: `dotnet test`

3. **Measure coverage** (if available):
   - Python: `pytest tests/ -v --cov --cov-report=term`
   - TypeScript: `npm test -- --coverage`

4. **Coverage Quality Gates**:
   - Line coverage MUST be >=80%
   - Branch coverage MUST be >=75%
   - If below threshold, write additional tests before proceeding

5. **Report results clearly** in your output using these exact formats:
   - `Phase 3: Implementation` (when you start implementing)
   - `Phase 4: Testing` (when you start testing)
   - `X tests passed` and `Y tests failed` (test counts)
   - `Coverage: Z.Z%` (coverage percentage)
   - `Phase 5: Code Review` (when you start review)
   - `Quality gates: PASSED` or `Quality gates: FAILED`

## Phase 4.5: Fix Loop

If tests fail after Phase 4:

1. Analyze the failure output carefully
2. Make targeted fixes to resolve failures
3. Re-run the full test suite
4. **Maximum 3 fix attempts** - if still failing after 3 attempts, report failure
5. Do NOT skip, comment out, or ignore failing tests
6. Do NOT modify test assertions unless they are provably incorrect

Quality Gate: ALL tests MUST pass (0 failures) before proceeding to Phase 5.

## Phase 5: Code Review (Lightweight)

1. Check for obvious code quality issues:
   - Unused imports
   - Missing error handling on external calls
   - Hardcoded secrets or credentials
2. Run linter if available:
   - Python: `ruff check .` or `flake8`
   - TypeScript: `npm run lint`
3. Note any issues found

## Output Format

After completing all phases, output a clear summary:

```
Phase 3: Implementation
  Files created: [list]
  Files modified: [list]

Phase 4: Testing
  X tests passed, Y tests failed
  Coverage: Z.Z%

Phase 5: Code Review
  [any issues or "No issues found"]

Quality gates: PASSED
```

This summary will be parsed automatically. Use the exact marker formats shown above.

## Important Notes

- Focus on implementing what the plan specifies - no scope creep
- Run tests after EVERY significant change
- If a test framework is not set up, set it up first
- All file paths should be relative to the working directory
- Write clean, well-documented code following project conventions
"""
        return protocol

    async def _invoke_task_work_implement(
        self,
        task_id: str,
        mode: str = "standard",
        documentation_level: str = "minimal",
        turn: int = 1,
        requirements: str = "",
        feedback: Optional[Union[str, Dict[str, Any]]] = None,
        max_turns: int = 5,
        context: str = "",
    ) -> TaskWorkResult:
        """Execute Phases 3-5 (implement-only) via SDK with loaded protocol.

        TASK-ACO-002: Uses _build_autobuild_implementation_prompt() which loads
        the execution protocol from autobuild_execution_protocol.md and injects
        task requirements, coach feedback, graphiti context, and turn context
        inline into the prompt.

        Uses setting_sources=["project"] instead of ["user", "project"],
        reducing context loading from ~1,078KB to ~93KB per Player turn.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")
            documentation_level: Documentation level for file count constraint
                validation ("minimal", "standard", or "comprehensive").
                Default: "minimal" for AutoBuild tasks.
            turn: Current turn number (1-based). Default: 1.
            requirements: Task requirements from task markdown. Default: "".
            feedback: Optional Coach feedback from previous turn. Default: None.
            max_turns: Maximum turns allowed. Default: 5.
            context: Job-specific context from Graphiti. Default: "".

        Returns:
            TaskWorkResult with success status and output/error

        Raises:
            SDKTimeoutError: If execution exceeds timeout
        """
        # TASK-ACO-002: Build prompt with loaded protocol and inline context
        prompt = self._build_autobuild_implementation_prompt(
            task_id=task_id,
            mode=mode,
            documentation_level=documentation_level,
            turn=turn,
            requirements=requirements,
            feedback=feedback,
            max_turns=max_turns,
            context=context,
        )

        # TASK-VOPT-001: Log protocol variant and size
        protocol_variant = "medium" if self.timeout_multiplier > 1.0 else "full"
        logger.info(f"Executing inline implement protocol for {task_id} (mode={mode})")
        logger.info(f"Working directory: {self.worktree_path}")
        logger.info(
            f"Inline protocol size: {len(prompt)} bytes "
            f"(variant={protocol_variant}, multiplier={self.timeout_multiplier}x)"
        )

        # TASK-HMIG-006.1: dispatch through HarnessAdapter. Same pattern as
        # the Player path migrated in TASK-HMIG-006 Phase 3b
        # (`_invoke_with_role` at agent_invoker.py:2855) and Coach's
        # independent verifier migrated in TASK-HMIG-006.3
        # (`coach_validator._run_tests_via_sdk`). The harness owns SDK
        # lazy-import, ClaudeAgentOptions construction, parse resilience
        # (TASK-FIX-7A03), session_id capture (TASK-RFX-B20B), and
        # generator hygiene (TASK-RFX-8332 / TASK-FIX-GEN1). Per
        # Design Decision D-3, orchestrator-side concerns (heartbeat,
        # sdk_debug, retry loop, tool tracking, rate-limit detection)
        # stay inline. Per D-4, the harness normalises all SDK-specific
        # exceptions (CLINotFoundError / ProcessError / CLIJSONDecodeError
        # / harness-internal ValueError / SDK import failure) to
        # AgentInvocationError before they reach this caller.
        from guardkit.orchestrator.sdk_utils import check_assistant_message_error

        # TASK-ABSR-MAXT: Complexity-scale max_turns (mirrors _calculate_sdk_timeout).
        # Computed once per invocation so the same value flows into the harness
        # constructor, the parsed result, and the returned TaskWorkResult.
        effective_max_turns = self._calculate_sdk_max_turns(task_id)

        # TASK-DIAG-F4A2: Preserve rendered task-work prompt under
        # sdk_debug/turn_<n>/ when GUARDKIT_AUTOBUILD_PRESERVE_DEBUG is
        # set. Helper is a no-op otherwise. Substrate-agnostic — operates
        # on whatever the orchestrator constructs. The rendered SDK
        # options object now lives inside the harness, so the prompt +
        # per-event JSONL still preserve enough context to diagnose SDK
        # stalls.
        from guardkit.orchestrator.sdk_debug import (
            preserve_prompt as _sdk_preserve_prompt,
            preserve_event as _sdk_preserve_event,
        )
        _sdk_debug_dir = _sdk_preserve_prompt(
            workspace_root=self.worktree_path,
            task_id=task_id,
            turn=turn,
            role="player",
            prompt=prompt,
            options=None,
        )

        # TASK-FBSDK-011: Log invocation configuration. Options are now
        # constructed inside the harness so we log the orchestrator-side
        # knobs only.
        logger.info(f"[{task_id}] Harness invocation starting")
        logger.info(f"[{task_id}] Working directory: {self.worktree_path}")
        logger.info(
            f"[{task_id}] Allowed tools: "
            f"{['Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob', 'Task']}"
        )
        logger.info(f"[{task_id}] Permission mode: acceptEdits")
        logger.info(f"[{task_id}] Max turns: {effective_max_turns}")
        logger.info(f"[{task_id}] SDK timeout: {self.sdk_timeout_seconds}s")
        if self._last_session_id is not None:
            logger.info(
                f"[{task_id}] Resuming SDK session: "
                f"{self._last_session_id[:16]}..."
            )
        logger.debug(f"[{task_id}] Prompt (first 500 chars): {prompt[:500]}...")

        # TASK-FIX-46F2: Retry loop for transient SDK stream errors.
        # Under GPU contention, vLLM SSE streams can be interrupted with
        # "unknown" errors. A single retry avoids expensive state-recovery.
        # Each retry constructs a fresh harness instance per
        # Design Decision D-6 (single-use per invocation).
        _sdk_stream_error: Optional[str] = None
        collected_output: List[str] = []
        message_count = 0
        assistant_count = 0
        tool_count = 0
        result_count = 0
        parser = TaskWorkStreamParser()
        sdk_turns_used = None
        sdk_session_id = None

        try:
            for _sdk_attempt in range(MAX_SDK_STREAM_RETRIES + 1):
                collected_output = []
                # TASK-FIX-STUB-C: Recreate parser per retry so ToolUseBlock
                # file operations from a previous (failed) attempt do not
                # leak into the successful attempt's result.
                parser = TaskWorkStreamParser()
                message_count = 0
                assistant_count = 0
                tool_count = 0
                result_count = 0
                _sdk_stream_error = None
                _pending_bash_tools: Dict[str, Dict[str, Any]] = {}
                sdk_turns_used = None
                sdk_session_id = None

                # Construct the harness. select_harness() routes via
                # GUARDKIT_HARNESS env var (default "sdk"). The SDK harness
                # owns ClaudeAgentOptions construction, the query() call,
                # generator hygiene (TASK-RFX-8332 / TASK-FIX-GEN1), and
                # per-message parse resilience (TASK-FIX-7A03). Per
                # Design Decision D-3, the cleanup-handler installer is
                # passed through so the SDK subprocess gets cleaned up
                # against the running event loop.
                harness = select_harness(
                    sdk_timeout_seconds=self.sdk_timeout_seconds,
                    # TASK-POF-004: Removed "Skill" - inline protocol doesn't invoke skills
                    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"],
                    permission_mode="acceptEdits",
                    # TASK-REV-BB80 / TASK-ABSR-MAXT: Complexity-scaled per-task.
                    max_turns=effective_max_turns,
                    # TASK-RFX-B20B: Resume from prior session if available.
                    resume_session_id=self._last_session_id,
                    sdk_debug_dir=_sdk_debug_dir,
                    cleanup_handler_installer=_install_sdk_cleanup_handler,
                    # TASK-POF-004: Use "project" only - inline protocol replaces
                    # skill invocation (~839KB savings on the SDK path; dropped
                    # by the LangGraph translator).
                    setting_sources=["project"],
                    # TASK-FIX-LGFM2 (sibling-of-LGFM, sibling-of-F9/F1):
                    # Thread the orchestrator-stored model name through to the
                    # harness. Mirrors the kwarg at the _invoke_with_role site
                    # (agent_invoker.py:2863). Without this, the LangGraph
                    # branch hits the harness with model=None, DeepAgents
                    # falls back to its default Anthropic provider, and
                    # llama-swap operators see "Could not resolve
                    # authentication method" at Player turn 1. The main
                    # Player path has no per-call model override, so direct
                    # ``model=self._model_name`` is sufficient (no fallback
                    # needed).
                    model=self._model_name,
                    # TASK-FIX-002R-CONSUME: ``cwd`` is consumed by the
                    # langgraph branch to build a path-confined LocalShellBackend.
                    # The SDK branch ignores it (popped at the top of
                    # select_harness); passing unconditionally keeps the call
                    # site harness-agnostic.
                    cwd=self.worktree_path,
                )

                # TASK-HMIG-006 AC-007: surface the resume-intent drop loudly
                # when the resolved harness does not support resume.
                if (
                    self._last_session_id is not None
                    and not harness.supports_resume
                ):
                    logger.warning(
                        "TASK-HMIG-006 AC-007: _last_session_id=%s... was supplied but "
                        "harness %s does not support_resume; starting fresh session.",
                        self._last_session_id[:16],
                        type(harness).__name__,
                    )

                async with asyncio.timeout(self.sdk_timeout_seconds):
                    async with async_heartbeat(
                        task_id,
                        "task-work implementation",
                        progress_logger=self._progress_logger,
                    ):
                        # TASK-FIX-LGACLOSE: finalise the harness async generator
                        # on every exit (incl. cancellation) — see the specialist
                        # call site for the full rationale.
                        async with aclosing(
                            harness.invoke(
                                prompt=prompt,
                                role="player",
                                tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"],
                                cwd=self.worktree_path,
                                timeout_seconds=self.sdk_timeout_seconds,
                            )
                        ) as _harness_stream:
                            async for event in _harness_stream:
                                message_count += 1
                                # TASK-DIAG-F4A2: Preserve raw event to JSONL
                                # (no-op if disabled). Operates on event.raw to
                                # preserve the SDK-shape JSON the prior path
                                # used to dump.
                                if _sdk_debug_dir is not None and event.raw is not None:
                                    _sdk_preserve_event(_sdk_debug_dir, event.raw)

                                if isinstance(event, AssistantMessageEvent):
                                    # API-error check operates on raw SDK shape;
                                    # only the SDK harness populates event.raw,
                                    # other substrates have raw=None and this
                                    # check is a no-op there.
                                    if event.raw is not None:
                                        err = check_assistant_message_error(event.raw)
                                        if err:
                                            # TASK-FIX-46F2: Retry on transient "unknown" errors.
                                            if (
                                                _sdk_attempt < MAX_SDK_STREAM_RETRIES
                                                and "unknown" in str(err).lower()
                                            ):
                                                logger.warning(
                                                    "[%s] SDK stream error (attempt %d/%d), "
                                                    "retrying in %ds: %s",
                                                    task_id,
                                                    _sdk_attempt + 1,
                                                    MAX_SDK_STREAM_RETRIES + 1,
                                                    SDK_STREAM_RETRY_BACKOFF,
                                                    err,
                                                )
                                                _sdk_stream_error = err
                                                break  # Break event loop to retry
                                            logger.error(
                                                f"[{task_id}] SDK API error in stream: {err}"
                                            )
                                            return TaskWorkResult(
                                                success=False,
                                                output={},
                                                error=f"SDK agent error: {err}",
                                            )
                                    assistant_count += 1
                                    # Collect joined text content for parser
                                    if event.text:
                                        collected_output.append(event.text)
                                        if "Phase" in event.text or "test" in event.text.lower():
                                            logger.debug(
                                                f"SDK progress: {event.text[:100]}..."
                                            )
                                    # Walk raw content blocks for tool tracking +
                                    # per-bash-exec emission. Substrate-agnostic
                                    # via duck-typing on type(block).__name__ —
                                    # matches the heartbeat scan at
                                    # agent_invoker.py:2974-2989 and the SDK
                                    # harness's own ToolUseBlock emission at
                                    # sdk_harness.py:318-328.
                                    content = (
                                        getattr(event.raw, "content", None) or []
                                        if event.raw is not None
                                        else []
                                    )
                                    for block in content:
                                        block_class = type(block).__name__
                                        if block_class == "ToolUseBlock":
                                            tool_count += 1
                                            block_name = getattr(block, "name", "")
                                            logger.debug(f"Tool invoked: {block_name}")
                                            # TASK-FIX-OBS2: Update progress logger with tool use.
                                            if self._progress_logger:
                                                self._progress_logger._last_tool = block_name
                                            # TASK-FIX-STUB-C: Track file operations from
                                            # Write/Edit tools to populate files_created/
                                            # files_modified in task_work_results.json.
                                            if block_name in ("Write", "Edit"):
                                                tool_input = getattr(block, "input", {})
                                                if isinstance(tool_input, dict):
                                                    # TASK-FIX-PIPELINE: Log actual SDK key names (Fix 1).
                                                    logger.info(
                                                        f"[{task_id}] ToolUseBlock {block_name} input keys: "
                                                        f"{list(tool_input.keys())}"
                                                    )
                                                    parser._track_tool_call(
                                                        block_name, tool_input
                                                    )
                                                    # TASK-FIX-OBS2: Track file changes for progress.
                                                    if self._progress_logger:
                                                        self._progress_logger._files_changed += 1
                                                else:
                                                    logger.warning(
                                                        f"[{task_id}] ToolUseBlock {block_name} input is "
                                                        f"{type(tool_input).__name__}, not dict: {str(tool_input)[:200]}"
                                                    )
                                            # TASK-INST-005c: Track Bash tool invocations
                                            # for tool.exec event emission.
                                            elif block_name == "Bash":
                                                tool_input = getattr(block, "input", {})
                                                if isinstance(tool_input, dict):
                                                    _pending_bash_tools[getattr(block, "id", "")] = {
                                                        "cmd": tool_input.get("command", ""),
                                                        "start_ns": time.monotonic_ns(),
                                                    }
                                        elif block_class == "ToolResultBlock":
                                            # TASK-INST-005c: Emit tool.exec event for
                                            # completed Bash tool invocations.
                                            _tool_use_id = getattr(block, "tool_use_id", "")
                                            if _tool_use_id in _pending_bash_tools:
                                                _bash_info = _pending_bash_tools.pop(_tool_use_id)
                                                _block_content = getattr(block, "content", None)
                                                _content_str = (
                                                    str(_block_content) if _block_content else ""
                                                )
                                                _latency = (
                                                    (time.monotonic_ns() - _bash_info["start_ns"])
                                                    / 1_000_000
                                                )
                                                self._emit_tool_exec_event(
                                                    tool_name="Bash",
                                                    cmd=_bash_info["cmd"],
                                                    exit_code=0,
                                                    latency_ms=_latency,
                                                    stdout_tail=_content_str,
                                                    stderr_tail="",
                                                    task_id=task_id,
                                                )
                                            # Extract content from tool results
                                            # if present (parser sees them too).
                                            _result_content = getattr(block, "content", None)
                                            if _result_content:
                                                collected_output.append(str(_result_content))
                                elif isinstance(event, ResultMessageEvent):
                                    result_count += 1
                                    # TASK-VPR-003: Capture SDK turns from ResultMessage.
                                    # ResultMessageEvent does not expose num_turns at
                                    # the typed-event level (TASK-HMIG-006 D-1 left
                                    # this on raw); read from event.raw which the SDK
                                    # harness populates with the original SDK
                                    # ResultMessage. LangGraph harness leaves raw=None
                                    # so sdk_turns_used stays None on that path.
                                    if event.raw is not None:
                                        sdk_turns_used = getattr(
                                            event.raw, "num_turns", None
                                        )
                                    # TASK-RFX-B20B: Capture session_id for resumption.
                                    # Read from typed field so the same code path
                                    # works for any substrate.
                                    sdk_session_id = event.session_id
                                    self._last_session_id = sdk_session_id
                                    logger.info(
                                        f"[{task_id}] SDK completed: turns={sdk_turns_used}"
                                    )
                                    break

                if _sdk_stream_error is None:
                    break  # Stream completed successfully, exit retry loop.
                # TASK-FIX-46F2: Backoff before retry.
                await asyncio.sleep(SDK_STREAM_RETRY_BACKOFF)

            # TASK-FIX-46F2: If retries exhausted with transient error, fall through.
            if _sdk_stream_error is not None:
                logger.error(
                    f"[{task_id}] SDK API error in stream after "
                    f"{MAX_SDK_STREAM_RETRIES + 1} attempts: {_sdk_stream_error}"
                )
                return TaskWorkResult(
                    success=False, output={},
                    error=f"SDK agent error: {_sdk_stream_error}",
                )

            # TASK-FBSDK-011: Log message processing summary.
            logger.info(
                f"[{task_id}] Message summary: total={message_count}, "
                f"assistant={assistant_count}, tools={tool_count}, results={result_count}"
            )

            # Join collected output for parsing.
            output_text = "\n".join(collected_output)

            # Parse text output for quality gate metrics (tests, coverage, phases).
            # Note: parser already has file tracking from ToolUseBlock processing above.
            parser.parse_message(output_text)
            parsed_result = parser.to_result()

            # TASK-VPR-003: Inject SDK turn metrics into parsed result.
            # These flow through to task_work_results.json for Coach and reporting.
            # TASK-ABSR-MAXT: Report the complexity-scaled value actually passed to the SDK.
            parsed_result["sdk_turns_used"] = sdk_turns_used
            parsed_result["sdk_max_turns"] = effective_max_turns

            # Write task_work_results.json for Coach validation.
            self._write_task_work_results(task_id, parsed_result, documentation_level)

            logger.info(f"task-work completed successfully for {task_id}")
            return TaskWorkResult(
                success=True,
                output=parsed_result,
                sdk_turns_used=sdk_turns_used,
                sdk_max_turns=effective_max_turns,
                session_id=sdk_session_id,  # TASK-RFX-B20B
            )

        except asyncio.TimeoutError:
            error_msg = f"task-work execution exceeded {self.sdk_timeout_seconds}s timeout"
            logger.error(f"[{task_id}] SDK TIMEOUT: {error_msg}")
            logger.error(f"[{task_id}] Messages processed before timeout: {message_count}")
            if collected_output:
                last_output = " ".join(collected_output)[-500:]
                logger.error(f"[{task_id}] Last output (500 chars): {last_output}")
            self._write_failure_results(task_id, error_msg, "TimeoutError", collected_output)
            raise SDKTimeoutError(error_msg)

        except AgentInvocationError as e:
            # TASK-HMIG-006.1 / D-4: the harness normalises SDK-specific
            # exceptions (CLINotFoundError / ProcessError /
            # CLIJSONDecodeError / SDK import failure / harness-internal
            # ValueError) to AgentInvocationError. The diagnostic info
            # (exit_code, stderr, error_class) is preserved inside the
            # exception message string; downstream consumers
            # (test assertions, log greps) keep working because the
            # harness mirrors the pre-migration message wording verbatim:
            #
            #   * "Claude Agent SDK import failed." (sdk_harness.py:222)
            #   * "Claude Code CLI not installed."  (sdk_harness.py:422)
            #   * "SDK process failed (exit ...)"   (sdk_harness.py:427)
            #   * "Failed to parse SDK response: ..." (sdk_harness.py:431)
            error_msg = str(e)
            logger.error(
                f"[{task_id}] SDK invocation failed via harness "
                f"(error_class=AgentInvocationError): {error_msg}"
            )
            logger.error(f"[{task_id}] Messages processed: {message_count}")
            if collected_output:
                last_output = " ".join(collected_output)[-500:]
                logger.error(f"[{task_id}] Last output (500 chars): {last_output}")
            self._write_failure_results(
                task_id, error_msg, "AgentInvocationError", collected_output
            )
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

        except Exception as e:
            error_msg = str(e)

            # Check for rate limit in error message.
            is_rate_limit, reset_time = detect_rate_limit(error_msg)

            # Also check collected output for rate limit messages.
            if not is_rate_limit and collected_output:
                last_output = " ".join(collected_output)[-500:]
                is_rate_limit, reset_time = detect_rate_limit(last_output)

            if is_rate_limit:
                logger.error(f"[{task_id}] RATE LIMIT EXCEEDED")
                if reset_time:
                    logger.error(f"[{task_id}] Estimated reset: {reset_time}")
                raise RateLimitExceededError(
                    f"API rate limit exceeded. Reset: {reset_time or 'unknown'}",
                    reset_time=reset_time
                )

            # Catch-all for non-harness failures (e.g. orchestrator-side
            # state errors, asyncio mishaps). Preserves the pre-migration
            # log shape.
            error_msg = f"Unexpected error executing task-work: {str(e)}"
            logger.error(f"[{task_id}] SDK UNEXPECTED ERROR: {type(e).__name__}")
            logger.error(f"[{task_id}] Error message: {str(e)}")
            logger.error(f"[{task_id}] Messages processed: {message_count}")
            logger.exception(f"[{task_id}] Full traceback:")
            if collected_output:
                last_output = " ".join(collected_output)[-500:]
                logger.error(f"[{task_id}] Last output (500 chars): {last_output}")
            self._write_failure_results(task_id, error_msg, type(e).__name__, collected_output)
            return TaskWorkResult(
                success=False,
                output={},
                error=error_msg,
            )

    def _parse_task_work_output(self, stdout: str) -> Dict[str, Any]:
        """Parse task-work stdout into structured output.

        Extracts key information from task-work output including:
        - Test results
        - Coverage metrics
        - Files modified
        - Quality gate status

        Args:
            stdout: Raw stdout from task-work command

        Returns:
            Parsed output dictionary
        """
        output = {
            "raw_output": stdout,
            "tests_passed": False,
            "coverage_line": None,
            "coverage_branch": None,
            "quality_gates_passed": False,
        }

        # Parse test results
        if "All tests passing" in stdout or "✅" in stdout:
            output["tests_passed"] = True

        # Parse coverage (look for patterns like "Coverage: 85.2%")
        import re
        coverage_match = re.search(r"(?:Line )?[Cc]overage:?\s*(\d+(?:\.\d+)?)\s*%", stdout)
        if coverage_match:
            output["coverage_line"] = float(coverage_match.group(1))

        branch_match = re.search(r"[Bb]ranch [Cc]overage:?\s*(\d+(?:\.\d+)?)\s*%", stdout)
        if branch_match:
            output["coverage_branch"] = float(branch_match.group(1))

        # Parse quality gates
        if "All quality gates passed" in stdout or "IN_REVIEW" in stdout:
            output["quality_gates_passed"] = True

        return output

    def _parse_task_work_stream(
        self,
        message: str,
        parser: TaskWorkStreamParser,
    ) -> Dict[str, Any]:
        """Parse a task-work stream message and return accumulated results.

        This method uses TaskWorkStreamParser for incremental stream processing.
        It complements _parse_task_work_output by enabling real-time parsing
        during SDK stream processing rather than batch processing after completion.

        Args:
            message: Single message from the task-work SDK stream
            parser: TaskWorkStreamParser instance for accumulating state

        Returns:
            Current accumulated result dictionary from the parser

        Example:
            >>> parser = TaskWorkStreamParser()
            >>> async for message in query(prompt=prompt, options=options):
            ...     if hasattr(message, 'content'):
            ...         result = self._parse_task_work_stream(str(message.content), parser)
            >>> final_result = parser.to_result()
        """
        parser.parse_message(message)
        return parser.to_result()

    # =========================================================================
    # Acceptance Criteria & Promise-Based Verification Methods
    # =========================================================================

    def extract_acceptance_criteria(self, task_id: str) -> List[Dict[str, str]]:
        """Extract acceptance criteria from task markdown file.

        Reads the task file and extracts acceptance criteria from the
        frontmatter or body content. Each criterion is assigned a unique ID.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            List of criteria dictionaries with 'id' and 'text' keys.
            Returns empty list if task file not found or no criteria.

        Examples:
            >>> invoker = AgentInvoker(worktree_path=Path("."))
            >>> criteria = invoker.extract_acceptance_criteria("TASK-001")
            >>> criteria[0]
            {'id': 'AC-001', 'text': 'OAuth2 authentication flow works correctly'}
        """
        import yaml

        task_file = self._find_task_file(task_id)

        if not task_file:
            logger.warning(f"Task file not found for {task_id}")
            return []

        try:
            with open(task_file, "r") as f:
                content = f.read()

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1]) or {}

                    # Check for acceptance_criteria in frontmatter
                    criteria_list = frontmatter.get("acceptance_criteria", [])
                    if criteria_list:
                        return [
                            {"id": f"AC-{i+1:03d}", "text": criterion}
                            for i, criterion in enumerate(criteria_list)
                        ]

                    # Check body content for ## Acceptance Criteria section
                    body = parts[2]
                    criteria = self._parse_criteria_from_body(body)
                    if criteria:
                        return criteria

            # Fallback: parse entire content as body
            criteria = self._parse_criteria_from_body(content)
            return criteria

        except Exception as e:
            logger.warning(f"Failed to extract acceptance criteria: {e}")
            return []

    def _parse_criteria_from_body(self, body: str) -> List[Dict[str, str]]:
        """Parse acceptance criteria from task body content.

        Looks for an ## Acceptance Criteria section and extracts
        bullet-pointed or numbered items.

        Args:
            body: Task body content (markdown)

        Returns:
            List of criteria dictionaries with 'id' and 'text' keys
        """
        import re

        criteria = []

        # Find the acceptance criteria section
        ac_match = re.search(
            r"##\s*Acceptance\s*Criteria\s*\n(.*?)(?=\n##|\Z)",
            body,
            re.IGNORECASE | re.DOTALL,
        )

        if ac_match:
            ac_section = ac_match.group(1)

            # Extract bullet points or numbered items
            # Matches: - item, * item, 1. item, 1) item
            items = re.findall(
                r"^[\s]*(?:[-*]|\d+[.)]\s*)\s*(.+?)$",
                ac_section,
                re.MULTILINE,
            )

            for i, item in enumerate(items):
                item = item.strip()
                if item:
                    criteria.append({"id": f"AC-{i+1:03d}", "text": item})

        return criteria

    def parse_completion_promises(
        self, player_report: Dict[str, Any]
    ) -> List[CompletionPromise]:
        """Parse completion promises from Player report.

        Extracts the completion_promises field from the Player report
        and converts each entry to a CompletionPromise dataclass.

        Args:
            player_report: Player's JSON report from current turn

        Returns:
            List of CompletionPromise instances

        Examples:
            >>> report = {
            ...     "completion_promises": [
            ...         {"criterion_id": "AC-001", "status": "complete", ...},
            ...     ]
            ... }
            >>> promises = invoker.parse_completion_promises(report)
            >>> promises[0].criterion_id
            'AC-001'
        """
        promises_data = player_report.get("completion_promises", [])
        return [CompletionPromise.from_dict(p) for p in promises_data]

    def parse_criteria_verifications(
        self, coach_decision: Dict[str, Any]
    ) -> List[CriterionVerification]:
        """Parse criteria verifications from Coach decision.

        Extracts the criteria_verification field from the Coach decision
        and converts each entry to a CriterionVerification dataclass.

        Args:
            coach_decision: Coach's JSON decision from current turn

        Returns:
            List of CriterionVerification instances

        Examples:
            >>> decision = {
            ...     "criteria_verification": [
            ...         {"criterion_id": "AC-001", "result": "verified", ...},
            ...     ]
            ... }
            >>> verifications = invoker.parse_criteria_verifications(decision)
            >>> verifications[0].result
            <VerificationResult.VERIFIED: 'verified'>
        """
        verifications_data = coach_decision.get("criteria_verification", [])
        return [CriterionVerification.from_dict(v) for v in verifications_data]

    def _ensure_design_approved_state(self, task_id: str) -> None:
        """Ensure task is in design_approved state before task-work delegation.

        This method bridges AutoBuild orchestration state with task-work's
        state machine requirements. When AutoBuild delegates to
        `task-work --implement-only`, the task must be in `design_approved`
        state with a valid implementation plan.

        This bridge ensures:
        1. Task is in design_approved state (transitions if needed)
        2. Implementation plan exists in expected location
        3. State transitions are logged for debugging

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Raises:
            TaskStateError: If state transition fails
            PlanNotFoundError: If implementation plan is missing
        """
        from guardkit.tasks.state_bridge import TaskStateBridge

        logger.info(f"Ensuring task {task_id} is in design_approved state")

        try:
            # Pass in_autobuild_context=True to fix race condition where
            # autobuild_state hasn't been written yet when stub creation check runs
            bridge = TaskStateBridge(
                task_id,
                self.worktree_path,
                in_autobuild_context=True,
            )
            bridge.ensure_design_approved_state()
            logger.info(f"Task {task_id} state verified: design_approved")

        except PlanNotFoundError as e:
            logger.error(f"Implementation plan not found for {task_id}: {e}")
            raise

        except TaskStateError as e:
            logger.error(f"Failed to ensure design_approved state for {task_id}: {e}")
            raise

    # =========================================================================
    # Task-Work Results Writer Methods
    # =========================================================================

    def _read_json_artifact(self, path: Path) -> Optional[Dict[str, Any]]:
        """Read and parse JSON artifact file with graceful error handling.

        This is a DRY helper method for reading JSON artifact files with
        consistent error handling and logging patterns. Returns None if the
        file doesn't exist or contains invalid JSON.

        Args:
            path: Path to the JSON artifact file

        Returns:
            Parsed JSON data as dict, or None if file not found or invalid

        Example:
            >>> design_path = TaskArtifactPaths.design_results_path(task_id, worktree)
            >>> design_data = self._read_json_artifact(design_path)
            >>> if design_data:
            ...     score = design_data.get("architectural_review", {}).get("score")
        """
        if not path.exists():
            logger.debug(f"JSON artifact not found: {path}")
            return None

        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {path}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error reading {path}: {e}")
            return None

    def _write_design_results(
        self,
        task_id: str,
        result_data: Dict[str, Any],
    ) -> Path:
        """Write design phase results for implement-only mode access.

        Persists Phase 2.5B (Architectural Review) results from pre-loop
        execution to enable implement-only mode to include these scores in
        task_work_results.json for Coach validation.

        Location: .guardkit/autobuild/{task_id}/design_results.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            result_data: Parsed result data from design phase
                Expected keys:
                - architectural_review: Dict with score, solid_score, dry_score, yagni_score
                - complexity_score: Integer complexity score (1-10)

        Returns:
            Path to the written design_results.json file

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> result_data = {
            ...     "architectural_review": {"score": 75, "solid_score": 8, ...},
            ...     "complexity_score": 5
            ... }
            >>> path = invoker._write_design_results("TASK-001", result_data)
            >>> path
            PosixPath('.guardkit/autobuild/TASK-001/design_results.json')
        """
        # Ensure autobuild directory exists
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        design_file = TaskArtifactPaths.design_results_path(task_id, self.worktree_path)

        # Extract design phase data with simplified schema (per arch review)
        design_results: Dict[str, Any] = {
            "architectural_review": result_data.get("architectural_review", {}),
            "complexity_score": result_data.get("complexity_score"),
        }

        # Write design results to file (idempotent - overwrites if exists)
        design_file.write_text(json.dumps(design_results, indent=2))
        logger.info(f"Wrote design_results.json to {design_file}")

        return design_file

    def _read_design_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Read design phase results from pre-loop execution.

        Reads Phase 2.5B results persisted by pre-loop for use in
        implement-only mode. Returns None if pre-loop was disabled or
        design results are unavailable.

        Args:
            task_id: Task identifier (e.g., "TASK-001")

        Returns:
            Parsed design results dict, or None if not available

        Example:
            >>> design_data = invoker._read_design_results("TASK-001")
            >>> if design_data:
            ...     arch_review = design_data.get("architectural_review", {})
            ...     score = arch_review.get("score", 0)
        """
        design_file = TaskArtifactPaths.design_results_path(task_id, self.worktree_path)
        return self._read_json_artifact(design_file)

    def _resolve_worktree_python_executable(self) -> Optional[str]:
        """Resolve the worktree's venv interpreter for BDD oracle subprocesses.

        Resolution order: ``<worktree>/.venv/bin/python3`` →
        ``<worktree>/.venv/bin/python`` → ``None``.

        Without this, ``run_bdd_for_task`` falls back to whichever ``pytest`` is
        first on ``PATH`` — typically a user-level interpreter that cannot
        import the worktree's editable-installed package, causing the BDD
        oracle to fail with ``ModuleNotFoundError`` even though the worktree's
        own venv is correctly populated. See TASK-AB-001 / FEAT-FG-001.
        """
        venv_bin = Path(self.worktree_path) / ".venv" / "bin"
        for candidate in (venv_bin / "python3", venv_bin / "python"):
            if candidate.is_file():
                return str(candidate)

        logger.warning(
            "BDD oracle running against system pytest; worktree-local imports "
            "may fail (no .venv/bin/python[3] under %s).",
            self.worktree_path,
        )
        return None

    def _run_bdd_oracle(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Run task-level BDD oracle (TASK-BDD-E8954).

        Activation is by artefact presence: if no ``features/*.feature`` file
        in the worktree carries a ``@task:<TASK-ID>`` tag (or pytest-bdd is
        not importable), this returns ``None`` and behaviour is identical to
        before BDD wiring existed. Errors during execution are swallowed and
        logged — BDD failures must never break task-work result writing.
        """
        try:
            from guardkit.orchestrator.quality_gates.bdd_runner import (
                run_bdd_for_task,
            )

            python_executable = self._resolve_worktree_python_executable()
            logger.info(
                "BDD oracle invoking run_bdd_for_task for %s with python_executable=%s",
                task_id,
                python_executable,
            )
            result = run_bdd_for_task(
                task_id,
                self.worktree_path,
                python_executable=python_executable,
            )
        except Exception as exc:  # noqa: BLE001 — protect task-work writer
            logger.warning(
                "BDD oracle raised %s for %s; treating as skipped.",
                exc.__class__.__name__,
                task_id,
            )
            return None

        if result is None:
            return None
        return result.to_dict()

    @staticmethod
    def _extract_invocations_from_result_data(
        result_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Reconstruct the agent_invocations list validate_agent_invocations expects.

        Prefers an explicit ``agent_invocations`` key (if the Player emitted one
        per task-work.md Step 3.5); otherwise falls back to the parser's
        ``phases`` dict and reverse-maps phase_{N} → validator phase ID.
        """
        explicit = result_data.get("agent_invocations")
        if (
            isinstance(explicit, list)
            and explicit
            and all(isinstance(x, dict) for x in explicit)
        ):
            return explicit

        invocations: List[Dict[str, Any]] = []
        phases = result_data.get("phases") or {}
        for phase_key, phase_data in phases.items():
            if not isinstance(phase_data, dict):
                continue
            if not phase_data.get("completed"):
                continue
            phase_id = _PARSER_PHASE_TO_VALIDATOR_PHASE.get(phase_key)
            if phase_id is None and isinstance(phase_key, str) and phase_key.startswith("phase_"):
                phase_id = phase_key[len("phase_"):]
            if phase_id is None:
                continue
            invocations.append({
                "phase": phase_id,
                "agent": phase_data.get("text") or "unknown",
                "status": "completed",
            })
        return invocations

    def _compute_agent_invocations_validation(
        self,
        results: Dict[str, Any],
        workflow_mode: str,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run validate_agent_invocations against ``results``; return a gate block.

        Shape::

            {"status": "passed" | "violation" | "validator_error",
             "expected_phases": int | None,
             "actual_invocations": int | None,
             "missing_phases": list[str],
             "violation_message": str | None}

        Never raises. A validator crash yields ``validator_error`` so Coach can
        decide — the validator is a gate, not a blocker of artefact emission
        (per TASK-FIX-RWOP1.3.1 Implementation Notes).

        ``task_type`` is propagated so declarative tasks in
        ``implement-only`` mode expect 2 phases (Testing, Code Review)
        instead of 3 — there is no Phase-3 stack-specific specialist to
        invoke when the schema *is* the implementation (TASK-ABSR-1357).
        Falls back to ``results.get("task_type")`` when not supplied.
        """
        if task_type is None:
            task_type_from_results = results.get("task_type")
            if isinstance(task_type_from_results, str):
                task_type = task_type_from_results
        try:
            invocations = self._extract_invocations_from_result_data(results)

            # No invocation evidence at all — the Player didn't emit
            # `agent_invocations` and the stream parser didn't capture any
            # phase markers. That can happen for non-SDK fixture writes
            # (tests, synthetic seeds) or for a pipeline failure before any
            # phase ran. Record `no_data` so Coach neither blocks nor
            # approves on spurious grounds — a genuine Player misbehaviour
            # will be caught by upstream stream-parse errors.
            if not invocations:
                expected = get_expected_phases(workflow_mode, task_type)
                return {
                    "status": "no_data",
                    "expected_phases": expected,
                    "actual_invocations": 0,
                    "missing_phases": [],
                    "violation_message": None,
                }

            # Populate tracker.invocations directly — record_invocation() and
            # mark_complete() call display_log() which prints to stdout,
            # which would flood autobuild logs on every producer write.
            # The validator only reads tracker.invocations; it doesn't care
            # how the list was populated.
            tracker = AgentInvocationTracker()
            for inv in invocations:
                phase = inv.get("phase")
                if phase is None:
                    continue
                tracker.invocations.append({
                    "phase": phase,
                    "agent": inv.get("agent") or "unknown",
                    "phase_description": f"Phase {phase}",
                    "agent_source": "unknown",
                    "status": inv.get("status", "completed"),
                })

            expected = get_expected_phases(workflow_mode, task_type)
            actual = sum(
                1 for inv in tracker.invocations if inv.get("status") == "completed"
            )

            try:
                validate_agent_invocations(tracker, workflow_mode, task_type)
                return {
                    "status": "passed",
                    "expected_phases": expected,
                    "actual_invocations": actual,
                    "missing_phases": [],
                    "violation_message": None,
                }
            except AgentInvocationValidationError as exc:
                missing = [
                    m["phase"]
                    for m in identify_missing_phases(
                        tracker, workflow_mode, task_type
                    )
                ]
                return {
                    "status": "violation",
                    "expected_phases": expected,
                    "actual_invocations": actual,
                    "missing_phases": missing,
                    "violation_message": str(exc),
                }
        except Exception as exc:  # noqa: BLE001 — gate must never block artefacts
            logger.warning(
                "agent_invocations validator raised %s; recording validator_error.",
                exc.__class__.__name__,
            )
            return {
                "status": "validator_error",
                "expected_phases": None,
                "actual_invocations": None,
                "missing_phases": [],
                "violation_message": f"{exc.__class__.__name__}: {exc}",
            }

    # TASK-OSI-002: Validation-gate refactor — credit orchestrator-invoked
    # specialists. When TASK-OSI-004/005 land, the orchestrator runs Phase 4
    # (test-orchestrator) and Phase 5 (code-reviewer) directly and writes
    # `specialist_results.json` into the autobuild dir. This method merges
    # those records into `task_work_results.json`'s `agent_invocations` list
    # tagged `source: "orchestrator"` and re-runs the validation gate so the
    # on-disk block credits the orchestrator-owned phases. Player-emitted
    # Phase 4/5 entries are dropped — orchestrator records are the single
    # source of truth for those phases (structural double-count prevention).
    _ORCHESTRATOR_SPECIALIST_PHASES: Tuple[Tuple[str, str, str], ...] = (
        ("4", "phase_4", "test-orchestrator"),
        ("5", "phase_5", "code-reviewer"),
    )

    def _inject_specialist_records_into_task_work_results(
        self, task_id: str
    ) -> Optional[Path]:
        """Merge orchestrator-invoked Phase 4/5 records into task_work_results.

        Reads ``.guardkit/autobuild/{task_id}/specialist_results.json``
        (produced by TASK-OSI-004 / TASK-OSI-005) and merges Phase 4/5
        entries into ``task_work_results.json``'s ``agent_invocations``
        list, tagging each merged entry ``source: "orchestrator"``.

        Player-emitted Phase 4/5 entries (``source`` absent or
        ``source == "player"``) are dropped during the merge. Other phases
        in the existing list are preserved verbatim. After the merge the
        method re-runs ``_compute_agent_invocations_validation`` and writes
        the updated ``agent_invocations_validation`` block back to disk.

        If ``specialist_results.json`` is absent, the method logs a warning
        and inserts skipped Phase 4/5 records so the gate still produces a
        well-formed validation block — never raises (same invariant as the
        producer-side gate in ``_write_task_work_results``).

        Returns:
            Path to the rewritten ``task_work_results.json``, or ``None``
            if that file is missing (nothing to merge into).
        """
        results_path = TaskArtifactPaths.task_work_results_path(
            task_id, self.worktree_path
        )
        if not results_path.exists():
            logger.warning(
                "task_work_results.json not found at %s; skipping "
                "specialist record injection",
                results_path,
            )
            return None

        try:
            task_work_data = json.loads(results_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to read task_work_results.json at %s: %s",
                results_path,
                exc,
            )
            return None

        autobuild_dir = TaskArtifactPaths.autobuild_dir(
            task_id, self.worktree_path
        )
        specialist_results_path = autobuild_dir / "specialist_results.json"
        specialist_data: Optional[Dict[str, Any]] = None
        if specialist_results_path.exists():
            try:
                specialist_data = json.loads(
                    specialist_results_path.read_text()
                )
                if not isinstance(specialist_data, dict):
                    logger.warning(
                        "specialist_results.json at %s is not a JSON object; "
                        "treating as absent",
                        specialist_results_path,
                    )
                    specialist_data = None
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "Failed to read specialist_results.json at %s: %s; "
                    "treating as absent",
                    specialist_results_path,
                    exc,
                )
                specialist_data = None
        else:
            logger.warning(
                "specialist_results.json not found at %s; inserting skipped "
                "Phase 4/5 records to keep the gate block structured",
                specialist_results_path,
            )

        # Drop Player-emitted Phase 4/5 entries — orchestrator records
        # below are the single source of truth for those phases.
        existing = task_work_data.get("agent_invocations")
        if not isinstance(existing, list):
            existing = []

        orchestrator_phase_ids = {
            phase_id for phase_id, _, _ in self._ORCHESTRATOR_SPECIALIST_PHASES
        }
        filtered: List[Dict[str, Any]] = []
        for inv in existing:
            if not isinstance(inv, dict):
                continue
            phase = str(inv.get("phase", ""))
            source = inv.get("source")
            if phase in orchestrator_phase_ids and source != "orchestrator":
                # Drop Player-emitted (or untagged) Phase 4/5 — replaced
                # below by orchestrator-sourced records.
                continue
            filtered.append(inv)

        # Build the orchestrator-sourced records.
        orchestrator_records: List[Dict[str, Any]] = []
        for phase_id, phase_key, agent_name in self._ORCHESTRATOR_SPECIALIST_PHASES:
            block = (specialist_data or {}).get(phase_key)
            if not isinstance(block, dict):
                # Either specialist_results.json is absent or this phase's
                # block is missing/malformed — synthesize a skipped record.
                missing_reason = (
                    "specialist_results.json not found"
                    if specialist_data is None
                    else f"specialist_results.json missing {phase_key} block"
                )
                orchestrator_records.append({
                    "phase": phase_id,
                    "agent": agent_name,
                    "status": "skipped",
                    "source": "orchestrator",
                    "error": missing_reason,
                })
                continue

            block_status = block.get("status", "skipped")
            # Map specialist outcome ("passed"/"failed"/"skipped") to the
            # invocation tracker's vocabulary. Only "passed" credits the
            # phase as completed; "failed" and "skipped" leave it
            # uncredited so a real specialist failure surfaces as a gate
            # violation rather than a silent pass.
            if block_status == "passed":
                invocation_status = "completed"
            elif block_status == "failed":
                invocation_status = "failed"
            else:
                invocation_status = "skipped"

            record: Dict[str, Any] = {
                "phase": phase_id,
                "agent": agent_name,
                "status": invocation_status,
                "source": "orchestrator",
            }
            if "duration_seconds" in block:
                record["duration_seconds"] = block["duration_seconds"]
            if block.get("error"):
                record["error"] = block["error"]
            orchestrator_records.append(record)

        merged = filtered + orchestrator_records
        task_work_data["agent_invocations"] = merged

        # Re-run the gate against the merged ledger so the on-disk
        # validation block credits orchestrator-invoked phases. Direct-mode
        # tasks (workflow_mode=="direct") expect Phase 3 only — see
        # `get_expected_phases("direct")` — and so will not trigger a
        # false Phase 4/5 violation when specialist_results.json is absent.
        # TASK-ABSR-1357: thread task_type so declarative tasks in
        # implement-only mode expect [4, 5] (not [3, 4, 5]).
        workflow_mode = task_work_data.get("workflow_mode") or "implement-only"
        task_type = (
            task_work_data.get("task_type")
            if isinstance(task_work_data.get("task_type"), str)
            else self._lookup_task_type(task_id)
        )
        new_validation = self._compute_agent_invocations_validation(
            task_work_data, workflow_mode, task_type=task_type
        )
        task_work_data["agent_invocations_validation"] = new_validation

        try:
            results_path.write_text(json.dumps(task_work_data, indent=2))
        except OSError as exc:
            logger.warning(
                "Failed to write merged task_work_results.json at %s: %s",
                results_path,
                exc,
            )
            return None

        logger.info(
            "Injected orchestrator specialist records into %s "
            "(merged=%d, validation=%s)",
            results_path,
            len(merged),
            new_validation.get("status"),
        )
        return results_path

    def _extract_explicit_planned_files(
        self,
        task_id: str,
    ) -> Set[str]:
        """Return file paths declared in the task body's explicit sections.

        Implements TASK-GK-PA-002 AC-1: when a task body contains
        non-empty ``## Files to Create`` and/or ``## Files to Modify``
        sections (the FM-001 convention introduced by
        TASK-FRR-PEB-FM-001 / commit ``02aac9c``), those lists are the
        authoritative ``planned_files`` set. The plan-audit fallback path
        ``_compute_plan_audit_verdict`` consults this helper before
        running the prose regex scan, so well-formed tasks no longer
        false-positive on prose typos in ``## Implementation notes``
        (FEAT-PEBR run-2 root cause).

        The section-boundary regex is ``(?=\\n##(?!#)|\\Z)`` so a
        ``### Subsection`` header inside the section does not terminate
        it prematurely (subsections legitimately appear under
        ``## Files to Create`` for grouped declarations).

        Bullet extraction handles four common shapes:

        - ``- `path/to/file.py```
        - ``- `path/to/file.py` — description`` (em-dash separator)
        - ``- `path/to/file.py` - description`` (space-dash-space)
        - ``- path/to/file.py``

        Sections that contain no parseable bullets (header-only or
        stubs like ``- _none_``) are treated as **absent**, not
        authoritative-empty — otherwise placeholder sections would
        accidentally bypass both the explicit-section comparison and the
        AC prose-scan fallback, leaving plan-audit blind.

        Args:
            task_id: Task ID whose body should be inspected.

        Returns:
            Union of paths declared in ``## Files to Create`` and
            ``## Files to Modify``, as a set of repo-relative path
            strings. Returns an empty set when neither section is
            present or both are empty (so callers can ``if explicit:``
            to detect the FM-001 convention).
        """
        import re as _re

        task_file = self._find_task_file(task_id)
        if task_file is None:
            return set()
        try:
            content = task_file.read_text(errors="replace")
        except OSError:
            return set()
        # Strip frontmatter the same way ``_scan_ac_for_missing_paths``
        # does, to keep the two helpers' body-shape contracts identical.
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2] if len(parts) >= 3 else content
        else:
            body = content

        # ``(?=^##(?!#)|\Z)`` stops at the next line-start ``## ``
        # header but not at ``### Subsection`` headers — the latter are
        # legitimate children of ``## Files to Create``. We anchor the
        # lookahead with ``^`` (MULTILINE) instead of ``\n##`` so a
        # blank line absorbed by ``\s*\n`` after the section header
        # doesn't push the cursor past the next section's start.
        section_pattern = (
            r"^##\s+Files\s+to\s+{action}\s*\n(.*?)(?=^##(?!#)|\Z)"
        )
        sections: List[str] = []
        for action in ("Create", "Modify"):
            match = _re.search(
                section_pattern.format(action=action),
                body,
                _re.IGNORECASE | _re.MULTILINE | _re.DOTALL,
            )
            if match:
                sections.append(match.group(1))

        paths: Set[str] = set()
        for section_text in sections:
            for line in section_text.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                # Bullet indicator: ``-`` or ``*`` followed by space.
                # Numbered lists (``1.``) are unusual for these sections
                # and are intentionally skipped to keep extraction tight.
                if not (stripped.startswith("- ") or stripped.startswith("* ")):
                    continue
                item = stripped[2:].strip()
                # Strip trailing description after em-dash (U+2014) or
                # ``" - "`` (space-dash-space). Bare ``-`` is left alone
                # so paths like ``feat-pebr-rev2/file.py`` survive.
                for sep in ("—", " - "):
                    idx = item.find(sep)
                    if idx != -1:
                        item = item[:idx].strip()
                        break
                # First backtick-quoted token wins when present;
                # otherwise the leading whitespace-token is the path.
                backtick_match = _re.match(r"`([^`]+)`", item)
                if backtick_match:
                    candidate = backtick_match.group(1).strip()
                else:
                    candidate = item.split()[0] if item else ""
                if not candidate:
                    continue
                # Skip placeholder bullets like ``_none_`` or ``N/A``.
                if candidate.startswith("_") or candidate.lower() in {
                    "n/a",
                    "none",
                    "tbd",
                }:
                    continue
                # Skip wildcards — ``planned_files`` is a literal set.
                if "*" in candidate:
                    continue
                paths.add(candidate)
        return paths

    def _scan_ac_for_missing_paths(
        self,
        task_id: str,
        *,
        flag_basenames: bool = False,
    ) -> List[str]:
        """Return AC-cited file paths that are absent from the worktree.

        Implements TASK-AB-FIX-INVAB1 AC-005's escalation rule: when the
        plan auditor reports ``skipped`` (no plan on disk), inspect the
        task's acceptance criteria for path-shaped tokens — and elevate
        the verdict to ``violation`` if any named path is missing.

        Uses the same regex set as
        ``synthetic_report.generate_file_existence_promises`` (primary
        ``[\\w./\\-]+\\.\\w{1,5}`` plus backtick / single-quoted /
        double-quoted variants) so AC-005 escalation parity matches the
        synthetic-report path that produces completion_promises.

        Bare basenames (tokens without a ``/`` separator, e.g.
        ``pipeline_consumer.py``) are skipped by default — TASK-GK-AC-001
        traced FEAT-PEBR Wave-1's UNRECOVERABLE_STALL to this scanner
        flagging files that exist deeper in the tree. AC text routinely
        names files by basename when the surrounding paragraph already
        established the directory; treating that as a missing-file
        signal is a false positive. Callers that genuinely need the
        old behaviour (none today, but synthetic-report parity is
        preserved) can pass ``flag_basenames=True``.

        TASK-GK-PA-002 narrows the scan body to the ``## Acceptance
        Criteria`` (or ``## Acceptance criterion``) section only.
        Earlier behaviour scanned the whole post-frontmatter body —
        which let prose paths in ``## Implementation notes`` (FEAT-PEBR
        run-2 surfaced a typo cross-reference there) trip the scanner.
        That mismatched the function's name and docstring; the slice
        re-aligns them. If the AC header is absent, the scanner falls
        back to whole-body scanning so non-standard task structures
        keep their pre-fix behaviour.

        Args:
            task_id: Task ID whose acceptance criteria should be scanned.
            flag_basenames: When ``True`` (legacy / synthetic-report
                parity behaviour), bare basenames missing from the
                worktree root count as missing. When ``False`` (default),
                only fully-qualified paths (those containing ``/``) are
                checked against the worktree, so a basename that exists
                anywhere under the tree does not trip the escalation.

        Returns:
            Sorted, deduplicated list of paths the AC text names that
            are absent from ``self.worktree_path``. Returns an empty list
            when the task file or its acceptance_criteria can't be read,
            so failure to introspect doesn't block the verdict pipeline.
        """
        import re as _re

        task_file = self._find_task_file(task_id)
        if task_file is None:
            return []
        try:
            content = task_file.read_text(errors="replace")
        except OSError:
            return []
        # Body after the YAML frontmatter — that's where AC text lives.
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2] if len(parts) >= 3 else content
        else:
            body = content
        # TASK-GK-PA-002 AC-2: restrict the scan to the AC section only.
        # ``(?=^##(?!#)|\Z)`` (MULTILINE) so a ``### Subsection`` header
        # inside the AC block (rare but possible — e.g. ``### Edge
        # cases``) does not terminate it, and an empty AC body followed
        # by another ``##`` section terminates correctly. Falls back to
        # whole-body scanning when the AC header is absent so
        # non-standard task structures keep their pre-fix behaviour.
        ac_match = _re.search(
            r"^##\s+Acceptance\s+(?:Criteria|criterion)\s*\n(.*?)(?=^##(?!#)|\Z)",
            body,
            _re.IGNORECASE | _re.MULTILINE | _re.DOTALL,
        )
        if ac_match:
            body = ac_match.group(1)
        primary = _re.findall(r"[\w./\-]+\.\w{1,5}", body)
        backtick = _re.findall(r"`([^`]+\.[a-zA-Z]+)`", body)
        double_q = _re.findall(r'"([^"]+\.[a-zA-Z]+)"', body)
        single_q = _re.findall(r"'([^']+\.[a-zA-Z]+)'", body)
        paths: List[str] = []
        seen: set = set()
        for p in primary + backtick + double_q + single_q:
            if "*" in p:
                continue
            if p in seen:
                continue
            seen.add(p)
            paths.append(p)
        # Filter to obvious source-file extensions and exclude paths
        # that look like documentation / metadata so the escalation
        # signal stays focused on implementation gaps. Keep this list
        # narrow on purpose — TASK-AB-FIX-INVAB1 §"Don't break"
        # warns against tightening helpers that already serve the
        # synthetic-report pipeline. False positives here would block
        # otherwise-passing tasks; false negatives degrade silently to
        # current behaviour.
        source_exts = (
            ".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".go", ".java",
            ".rb", ".rs",
        )
        missing: List[str] = []
        for p in paths:
            if not p.endswith(source_exts):
                continue
            # Skip bare basenames unless the caller opts in. AC text
            # often refers to files by basename (e.g. "modify
            # pipeline_consumer.py") even when the file lives at
            # src/forge/adapters/nats/pipeline_consumer.py. Treating
            # that as a missing-file signal is the FEAT-PEBR Wave-1
            # false-positive root cause (TASK-GK-AC-001).
            if not flag_basenames and "/" not in p:
                continue
            if not (self.worktree_path / p).exists():
                missing.append(p)
        return sorted(set(missing))

    def _compute_code_review_block(
        self, task_work_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Derive ``code_review`` from the orchestrator-invoked Phase-5 record.

        TASK-FIX-DF51: producer-side fold for ``code_review.score``. Mirrors the
        sibling fixes (TASK-FIX-RWOP1.3.1 agent_invocations gate; TASK-FIX-RWOP1.3.2
        plan_audit gate): Coach reads ``task_work_results["code_review"]["score"]``,
        but no upstream producer was writing that key for the OSI architecture
        (orchestrator-invoked code-reviewer in
        :mod:`guardkit.orchestrator.specialist_invocations`). The result is the
        canonical *runner-without-producer* anti-pattern — the gate runs but is
        structurally unsatisfiable, so every Coach turn rejects with
        ``must_fix/architectural`` "Architectural review score below threshold"
        regardless of actual review quality.

        Resolution order:

        1. **Player-stream score wins.** If ``task_work_data["code_review"]``
           already carries a ``score`` (populated by the legacy
           ``architectural_review`` extraction in
           :meth:`_write_task_work_results`, sourced from
           :class:`TaskWorkStreamParser` parsing the Player's own prose
           ``"Architectural Score: N/100"`` markers), return ``None`` to
           signal "leave the existing block alone." This keeps the legacy
           single-process ``/task-work`` path behaviourally unchanged.
        2. **Phase-5 specialist completion → synthesise.** Look at
           ``agent_invocations`` for a ``phase == "5"`` record from the
           orchestrator-invoked code-reviewer (``source == "orchestrator"``).
           Map ``status`` to a synthesised block:

           ============  ===========  ====================================
           inv status    score        explanation
           ============  ===========  ====================================
           completed     100          Read-only specialist ran to clean SDK
                                      completion. We didn't *measure* a
                                      numeric score (the read-only agent
                                      can't write a sidecar), so 100 is the
                                      natural ceiling that signals "max
                                      confidence we have." The ``source``
                                      field marks the score as synthesised.
           failed        0            Explicit fail — gate must reject.
           ============  ===========  ====================================

           AC-005: when the specialist crashed, timed out, or was skipped
           (``status == "skipped"``), return ``None``. The on-disk
           ``code_review`` key is left absent so the consumer's
           ``code_review.get("score", 0)`` default-to-0 path still applies.
           This preserves the ability of a real review failure to surface
           as a gate failure rather than being masked by a synthesised
           pass.
        3. **No phase-5 record at all.** Return ``None``; same default-to-0
           fallback applies (existing behaviour for non-OSI / pre-injection
           writes).

        The synthesised block always carries an explicit ``source`` field so
        a reader of ``coach_turn_N.json`` can distinguish a measured
        prose-parsed score from a completion-marker synthesis. Subscores
        (``solid``/``dry``/``yagni``) are not synthesised — they only appear
        when the Player's stream parser captured them (path 1 above).

        Args:
            task_work_data: The in-progress results dict, after
                ``arch_review_data`` extraction and after
                ``agent_invocations`` injection (when called from
                :meth:`_create_player_report_from_task_work`) or before
                injection (when called from :meth:`_write_task_work_results`
                — in that case path 2 may legitimately fire if the Player
                emitted Phase-5 records itself).

        Returns:
            A dict to assign to ``task_work_data["code_review"]``, or
            ``None`` to leave the existing key (or absence of key) alone.

        Notes:
            Never raises. Defensive against missing/malformed
            ``agent_invocations`` entries — a non-list, non-dict, or
            wrong-typed entry is silently ignored and resolution falls
            through to the next path.
        """
        existing = task_work_data.get("code_review")
        if isinstance(existing, dict) and "score" in existing:
            return None

        invocations = task_work_data.get("agent_invocations")
        if not isinstance(invocations, list):
            return None

        for inv in invocations:
            if not isinstance(inv, dict):
                continue
            if str(inv.get("phase", "")) != "5":
                continue
            if inv.get("agent") != "code-reviewer":
                continue
            if inv.get("source") != "orchestrator":
                continue
            status = inv.get("status")
            if status == "completed":
                return {
                    "score": 100,
                    "status": "completed",
                    "source": "orchestrator_specialist_completion",
                }
            if status == "failed":
                block: Dict[str, Any] = {
                    "score": 0,
                    "status": "failed",
                    "source": "orchestrator_specialist_failure",
                }
                error = inv.get("error")
                if isinstance(error, str) and error:
                    block["error"] = error
                return block
            return None

        return None

    def _compute_plan_audit_verdict(self, task_id: str) -> Dict[str, Any]:
        """Run the deterministic plan auditor; return a Coach-consumable block.

        Mirrors ``_compute_agent_invocations_validation``'s shape contract:
        produces a stable dict that the Coach gate reads directly. Four
        statuses:

        - ``passed``: plan exists, audit ran, severity != high
        - ``violation``: plan exists, audit ran, severity == high
        - ``skipped``: no saved plan at worktree-relative path
        - ``auditor_error``: auditor crashed (non-blocking for Coach)

        The block also carries back-compat ``violations`` (int) so the
        existing ``plan_audit.violations == 0`` gate in coach_validator
        keeps working and test fixtures that set ``violations=N``
        continue to exercise the same path. The auditor's deterministic
        fields (severity, extra_files, missing_files, loc_variance_pct)
        are exposed for Coach feedback so the Player can correct course.

        Never raises: auditor exceptions become ``auditor_error`` so the
        producer always writes the artefact (same invariant as the
        agent_invocations gate).
        """
        try:
            result = execute_phase_5_5_plan_audit(
                task_id=task_id,
                task_context={},
                non_interactive=True,
                workspace_root=self.worktree_path,
            )
        except Exception as exc:  # noqa: BLE001 — gate must never block artefacts
            logger.warning(
                "plan_audit auditor raised %s; recording auditor_error.",
                exc.__class__.__name__,
            )
            return {
                "status": "auditor_error",
                "severity": None,
                "violations": 0,
                "extra_files": [],
                "missing_files": [],
                "extra_modifications": [],
                "missing_modifications": [],
                "extra_dependencies": [],
                "missing_dependencies": [],
                "loc_variance_pct": None,
                "discrepancies_count": 0,
                "message": f"{exc.__class__.__name__}: {exc}",
            }

        if result.get("skipped"):
            # TASK-GK-PA-002 AC-1: when the task body declares explicit
            # ``## Files to Create`` / ``## Files to Modify`` sections
            # (FM-001 convention, commit ``02aac9c``), those lists are
            # the authoritative ``planned_files`` set. Compare against
            # the worktree directly and skip the prose regex scan —
            # FEAT-PEBR run-2 surfaced that prose typos in
            # ``## Implementation notes`` were tripping the AC scanner
            # even when every declared file was on disk.
            explicit = self._extract_explicit_planned_files(task_id)
            if explicit:
                missing = sorted(
                    p for p in explicit
                    if not (self.worktree_path / p).exists()
                )
                if missing:
                    return {
                        "status": "violation",
                        "severity": "high",
                        "violations": len(missing),
                        "extra_files": [],
                        "missing_files": missing,
                        "extra_modifications": [],
                        "missing_modifications": [],
                        "extra_dependencies": [],
                        "missing_dependencies": [],
                        "loc_variance_pct": None,
                        "discrepancies_count": len(missing),
                        "message": (
                            f"task body declares {len(explicit)} planned "
                            f"file(s); {len(missing)} not on disk: "
                            f"{', '.join(missing[:3])}"
                            f"{', ...' if len(missing) > 3 else ''}"
                        ),
                    }
                return {
                    "status": "passed",
                    "severity": "low",
                    "violations": 0,
                    "extra_files": [],
                    "missing_files": [],
                    "extra_modifications": [],
                    "missing_modifications": [],
                    "extra_dependencies": [],
                    "missing_dependencies": [],
                    "loc_variance_pct": None,
                    "discrepancies_count": 0,
                    "message": (
                        f"no plan on disk; all {len(explicit)} task-body-"
                        "declared file(s) present"
                    ),
                }

            # TASK-AB-FIX-INVAB1 AC-005: a "no plan on disk" outcome is
            # not a free pass. When AC text names a file path that
            # doesn't exist on disk, escalate to a high-severity
            # violation so coach_validator's plan_audit gate fires
            # ``decision: feedback`` automatically.
            ac_missing = self._scan_ac_for_missing_paths(task_id)
            if ac_missing:
                return {
                    "status": "violation",
                    "severity": "high",
                    "violations": len(ac_missing),
                    "extra_files": [],
                    "missing_files": ac_missing,
                    "extra_modifications": [],
                    "missing_modifications": [],
                    "extra_dependencies": [],
                    "missing_dependencies": [],
                    "loc_variance_pct": None,
                    "discrepancies_count": len(ac_missing),
                    "message": (
                        "no plan on disk; AC names file path(s) that do "
                        f"not exist on disk: {', '.join(ac_missing)}"
                    ),
                }
            return {
                "status": "skipped",
                "severity": None,
                "violations": 0,
                "extra_files": [],
                "missing_files": [],
                "extra_modifications": [],
                "missing_modifications": [],
                "extra_dependencies": [],
                "missing_dependencies": [],
                "loc_variance_pct": None,
                "discrepancies_count": 0,
                "message": "no implementation plan on disk",
            }

        if result.get("decision") == "error":
            return {
                "status": "auditor_error",
                "severity": None,
                "violations": 0,
                "extra_files": [],
                "missing_files": [],
                "extra_modifications": [],
                "missing_modifications": [],
                "extra_dependencies": [],
                "missing_dependencies": [],
                "loc_variance_pct": None,
                "discrepancies_count": 0,
                "message": result.get("error") or "auditor returned error",
            }

        report = result.get("report")
        if report is None:
            # Defensive: non-skipped, non-error, but no report — treat as
            # auditor_error rather than fabricating a passed verdict.
            return {
                "status": "auditor_error",
                "severity": None,
                "violations": 0,
                "extra_files": [],
                "missing_files": [],
                "extra_modifications": [],
                "missing_modifications": [],
                "extra_dependencies": [],
                "missing_dependencies": [],
                "loc_variance_pct": None,
                "discrepancies_count": 0,
                "message": "auditor returned no report",
            }

        # Extract deterministic fields from the report's discrepancy list.
        extra_files: List[str] = []
        missing_files: List[str] = []
        extra_modifications: List[str] = []
        missing_modifications: List[str] = []
        extra_deps: List[str] = []
        missing_deps: List[str] = []
        loc_variance_pct: Optional[float] = None

        for disc in report.discrepancies:
            # Modify-axis branches checked BEFORE the generic
            # creation-axis ``extra`` / ``missing`` discriminators so
            # the new modification messages route correctly.
            if disc.category == "files" and "unplanned modification" in disc.message:
                # TASK-GK-PA-001 Phase 4.5: producer message is
                # ``f"{N} unplanned modification(s)"`` (digit-prefixed) per
                # plan_audit.py:516. The previous ``startswith`` check
                # never matched, so ``extra_modifications`` was structurally
                # always ``[]``. Use substring match to route correctly.
                extra_modifications = (
                    list(disc.actual) if isinstance(disc.actual, list) else []
                )
            elif disc.category == "files" and "not modified" in disc.message:
                missing_modifications = (
                    list(disc.planned) if isinstance(disc.planned, list) else []
                )
            elif disc.category == "files" and "extra" in disc.message:
                extra_files = list(disc.actual) if isinstance(disc.actual, list) else []
            elif disc.category == "files" and (
                "missing" in disc.message or "not created" in disc.message
            ):
                missing_files = list(disc.planned) if isinstance(disc.planned, list) else []
            elif disc.category == "dependencies" and "extra" in disc.message:
                extra_deps = list(disc.actual) if isinstance(disc.actual, list) else []
            elif disc.category == "dependencies" and (
                "missing" in disc.message or "not added" in disc.message
            ):
                missing_deps = list(disc.planned) if isinstance(disc.planned, list) else []
            elif disc.category == "loc":
                loc_variance_pct = disc.variance

        severity = report.severity
        # High severity → block the turn; medium/low → informational only.
        # `violations` is a back-compat count consumed by existing Coach
        # code (`violations == 0 → pass`). Count high-severity items so
        # severity-high maps to violations>0 without breaking the legacy
        # fixture contract that hand-sets violations=N.
        high_count = sum(
            1 for d in report.discrepancies if d.severity == "high"
        )
        violations = high_count
        status = "violation" if severity == "high" else "passed"

        return {
            "status": status,
            "severity": severity,
            "violations": violations,
            "extra_files": extra_files,
            "missing_files": missing_files,
            "extra_modifications": extra_modifications,
            "missing_modifications": missing_modifications,
            "extra_dependencies": extra_deps,
            "missing_dependencies": missing_deps,
            "loc_variance_pct": loc_variance_pct,
            "discrepancies_count": len(report.discrepancies),
            "message": (
                f"severity={severity}, {len(report.discrepancies)} discrepanc(ies)"
                + (f", {len(extra_files)} extra file(s)" if extra_files else "")
                + (f", {len(missing_files)} missing file(s)" if missing_files else "")
                + (
                    f", {len(extra_modifications)} unplanned modification(s)"
                    if extra_modifications
                    else ""
                )
                + (
                    f", {len(missing_modifications)} unmodified planned file(s)"
                    if missing_modifications
                    else ""
                )
            ),
        }

    def _write_task_work_results(
        self,
        task_id: str,
        result_data: Dict[str, Any],
        documentation_level: str = "standard",
    ) -> Path:
        """Write task-work results to JSON file for Coach validation.

        This method creates a structured results file at the expected location
        that Coach can read to validate quality gate results. The file format
        matches the schema expected by Coach's validation logic.

        Location: .guardkit/autobuild/{task_id}/task_work_results.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            result_data: Parsed result data from TaskWorkStreamParser.to_result()
                Expected keys:
                - phases: Dict of detected phases
                - tests_passed: Number of tests passed
                - tests_failed: Number of tests failed
                - coverage: Coverage percentage
                - quality_gates_passed: Boolean quality gate status
                - files_modified: List of modified file paths
                - files_created: List of created file paths
                - architectural_review: Dict with overall score and optional subscores
            documentation_level: Documentation level ("minimal", "standard", or
                "comprehensive"). Used to validate file count constraints.

        Returns:
            Path to the written results file

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> parser = TaskWorkStreamParser()
            >>> parser.parse_message("12 tests passed, 0 failed")
            >>> parser.parse_message("Coverage: 85.5%")
            >>> result_data = parser.to_result()
            >>> results_path = invoker._write_task_work_results("TASK-001", result_data)
            >>> results_path
            PosixPath('.guardkit/autobuild/TASK-001/task_work_results.json')
        """
        # Ensure results directory exists (uses centralized paths)
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Extract test metrics with safe defaults
        tests_passed = result_data.get("tests_passed", 0)
        tests_failed = result_data.get("tests_failed", 0)
        coverage = result_data.get("coverage")
        quality_gates_passed = result_data.get("quality_gates_passed")

        # Determine completion status from available data
        # Completed if quality gates passed or if we have passing tests with no failures
        completed = quality_gates_passed or (
            tests_passed is not None and tests_passed > 0 and tests_failed == 0
        )

        # Extract architectural review score and subscores from result_data
        # The architectural_review object from Phase 2.5B contains overall score
        # and optional SOLID/DRY/YAGNI subscores for detailed evaluation
        arch_review_data = result_data.get("architectural_review", {})
        code_review: Dict[str, Any] = {}
        if arch_review_data:
            # Extract overall score (required for CoachValidator)
            if "score" in arch_review_data:
                code_review["score"] = arch_review_data["score"]

            # Include optional subscores if present
            if "solid" in arch_review_data:
                code_review["solid"] = arch_review_data["solid"]
            if "dry" in arch_review_data:
                code_review["dry"] = arch_review_data["dry"]
            if "yagni" in arch_review_data:
                code_review["yagni"] = arch_review_data["yagni"]

        # Build structured results matching Coach expectations
        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": completed,
            "phases": result_data.get("phases", {}),
            "quality_gates": {
                "tests_passing": tests_failed == 0 if tests_failed is not None else None,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "coverage": coverage,
                "coverage_met": coverage >= 80 if coverage is not None else None,
                "all_passed": quality_gates_passed,
            },
            # Deduplicate file lists using set conversion
            "files_modified": sorted(list(set(result_data.get("files_modified", [])))),
            "files_created": sorted(list(set(result_data.get("files_created", [])))),
            # TASK-FIX-CC-COND: persist files_authored separately. This is
            # the Player's *intent* (Write/Edit tool calls), distinct from
            # files_modified/files_created which the orchestrator unions
            # with worktree-wide git diff downstream. Coach's source-file
            # contention detector reads this field to avoid attributing
            # peer-task edits to this task in parallel waves.
            "files_authored": sorted(
                list(set(result_data.get("files_authored", []) or []))
            ),
            "tests_written": sorted(list(set(result_data.get("tests_written", [])))),
            "summary": self._generate_summary(result_data),
        }

        # TASK-VPR-003: Add SDK turn ceiling data to results
        sdk_turns_used_val = result_data.get("sdk_turns_used")
        sdk_max_turns_val = result_data.get("sdk_max_turns")
        results["sdk_turns"] = {
            "turns_used": sdk_turns_used_val,
            "max_turns": sdk_max_turns_val,
            "ceiling_hit": (
                sdk_turns_used_val is not None
                and sdk_max_turns_val is not None
                and sdk_turns_used_val >= sdk_max_turns_val
            ),
        }

# Add code_review field if architectural review data was found
        if code_review:
            results["code_review"] = code_review

        # Include completion_promises if present in result data (TASK-ACR-001)
        completion_promises = result_data.get("completion_promises", [])
        if completion_promises:
            results["completion_promises"] = completion_promises

        # Merge design results if available (for implement-only mode)
        design_data = self._read_design_results(task_id)
        if design_data:
            logger.info("Merging design phase results into task_work_results.json")
            # Merge architectural review scores from pre-loop
            if "architectural_review" in design_data:
                results["architectural_review"] = design_data["architectural_review"]
            # Merge complexity score from pre-loop
            if "complexity_score" in design_data:
                results["complexity_score"] = design_data["complexity_score"]

        # TASK-BDD-E8954: BDD oracle. Activation is by artefact presence — if a
        # features/*.feature file exists with a @task:<TASK-ID> tag and
        # pytest-bdd is installable, run the scenarios and persist a three-state
        # bdd_results block. Silently skipped (returns None) otherwise so the
        # default behaviour for tasks without BDD scaffolding is identical to
        # before this wiring landed.
        bdd_results = self._run_bdd_oracle(task_id)
        if bdd_results is not None:
            results["bdd_results"] = bdd_results

        # Filter invalid path entries before validation (TASK-FIX-PV01)
        # Ensures _validate_file_count_constraint sees only real file paths,
        # not natural language fragments or glob wildcards captured by regexes.
        results["files_created"] = [
            f for f in results["files_created"]
            if TaskWorkStreamParser._is_valid_file_path(f)
        ]
        results["files_modified"] = [
            f for f in results["files_modified"]
            if TaskWorkStreamParser._is_valid_file_path(f)
        ]
        # TASK-FIX-CC-COND: parity filter for files_authored.
        results["files_authored"] = [
            f for f in results["files_authored"]
            if TaskWorkStreamParser._is_valid_file_path(f)
        ]

        # Validate file count constraint for documentation level
        self._validate_file_count_constraint(
            task_id=task_id,
            documentation_level=documentation_level,
            files_created=results["files_created"],
        )

        # TASK-FIX-RWOP1.3.1: agent_invocations gate on the producer side.
        # task-work.md Step 6.5 calls this "the ONLY checkpoint that prevents
        # false reporting" — it runs after all enrichment and before the file
        # hits disk, so Coach sees the validation block when it reads the
        # results. Autobuild Player path invokes task-work --implement-only
        # (Phases 3/4/5), so workflow_mode defaults to "implement-only".
        # TASK-ABSR-1357: thread task_type so declarative tasks in
        # implement-only mode expect [4, 5] only — there is no Phase-3
        # stack-specific specialist to invoke when the schema *is* the
        # implementation. Persist task_type into the on-disk results so
        # downstream re-runs (specialist injection / enrichment writeback)
        # can pick it up via the fallback in
        # ``_compute_agent_invocations_validation`` without re-reading
        # the task file.
        workflow_mode = result_data.get("workflow_mode") or "implement-only"
        task_type = (
            result_data.get("task_type")
            if isinstance(result_data.get("task_type"), str)
            else self._lookup_task_type(task_id)
        )
        if task_type is not None:
            results["task_type"] = task_type
        results["agent_invocations_validation"] = (
            self._compute_agent_invocations_validation(
                results, workflow_mode, task_type=task_type
            )
        )

        # TASK-FIX-RWOP1.3.2: plan_audit gate on the producer side. The
        # deterministic auditor OVERRIDES any Player-supplied plan_audit
        # block (the Player-prose block is untrustworthy — it could claim
        # violations=[] while the worktree has extras). Coach reads
        # plan_audit.severity and plan_audit.violations from this block,
        # not from the Player's self-report.
        results["plan_audit"] = self._compute_plan_audit_verdict(task_id)

        # TASK-FIX-DF51: code_review gate on the producer side. Coach reads
        # task_work_results["code_review"]["score"] but no upstream producer
        # was writing it under the OSI architecture, so the gate kept failing
        # forever (must_fix/architectural). The fold below synthesises the
        # block from the Phase-5 specialist record when no Player-stream
        # score is available; see _compute_code_review_block for the full
        # resolution order. Returns None to leave any existing block (set
        # above from arch_review_data) untouched.
        new_code_review = self._compute_code_review_block(results)
        if new_code_review is not None:
            results["code_review"] = new_code_review

        # TASK-FIX-RWOP1.4a: assumption-confidence warn-mode gate on the
        # producer side. Coach reads unconfirmed_low_confidence_assumptions
        # and surfaces it as a non-blocking warning (see feature-spec.md:337
        # for the prose claim this wire validates). Same fix-shape as the
        # 1.3.1 agent_invocations gate; warn-mode per TASK-FIX-RWOP1.4
        # Part A decision — escalation to block-mode is a separate task.
        # Lazy import — see the comment on the top-of-file import block.
        from guardkit.orchestrator.quality_gates.assumption_confidence_checker import (
            check_unconfirmed_low_confidence_assumptions,
        )
        results["unconfirmed_low_confidence_assumptions"] = (
            check_unconfirmed_low_confidence_assumptions(self.worktree_path)
        )

        # Write results to file
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote task_work_results.json to {results_file}")

        return results_file

    def _write_failure_results(
        self,
        task_id: str,
        error: str,
        error_type: str,
        partial_output: Optional[List[str]] = None,
    ) -> Path:
        """Write task_work_results.json with failure status.

        Called on ALL error paths to ensure Coach receives actionable information
        instead of "results not found". This enables intelligent feedback based
        on the specific error type that occurred.

        Location: .guardkit/autobuild/{task_id}/task_work_results.json

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            error: Error message describing what failed
            error_type: Exception type name (e.g., "ProcessError", "TimeoutError")
            partial_output: Any output collected before failure (optional)

        Returns:
            Path to the written results file

        Raises:
            OSError: If directory creation or file write fails

        Example:
            >>> invoker._write_failure_results(
            ...     "TASK-001",
            ...     "SDK process failed (exit 1): Command not found",
            ...     "ProcessError",
            ...     ["Phase 2 started...", "Planning..."]
            ... )
            PosixPath('.guardkit/autobuild/TASK-001/task_work_results.json')
        """
        # Ensure results directory exists (uses centralized paths)
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Build failure results matching Coach expectations
        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": False,
            "success": False,
            "error": error,
            "error_type": error_type,
            "partial_output": partial_output or [],
            "phases": {},
            "quality_gates": {
                "all_passed": False,
                "compilation": {
                    "passed": False,
                    "error": "SDK invocation failed before testing",
                },
                "tests": {
                    "passed": False,
                    "error": "SDK invocation failed before testing",
                },
            },
            "files_modified": [],
            "files_created": [],
            "summary": f"Failed: {error_type} - {error}",
        }

        # Write results to file
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote failure results to {results_file}")

        return results_file

    def _generate_summary(self, result_data: Dict[str, Any]) -> str:
        """Generate human-readable summary from task-work results.

        Creates a concise summary string from the parsed result data,
        suitable for display in reports and Coach decision rationale.

        Args:
            result_data: Parsed result data from TaskWorkStreamParser.to_result()

        Returns:
            Human-readable summary string. Returns "Implementation completed"
            if no meaningful data is available.

        Example:
            >>> result_data = {"tests_passed": 12, "coverage": 85.5, "quality_gates_passed": True}
            >>> invoker._generate_summary(result_data)
            '12 tests passed, 85.5% coverage, all quality gates passed'
        """
        parts: List[str] = []

        # Add test count if available
        tests_passed = result_data.get("tests_passed")
        if tests_passed is not None and tests_passed > 0:
            parts.append(f"{tests_passed} tests passed")

        # Add tests failed if any
        tests_failed = result_data.get("tests_failed")
        if tests_failed is not None and tests_failed > 0:
            parts.append(f"{tests_failed} tests failed")

        # Add coverage if available
        coverage = result_data.get("coverage")
        if coverage is not None:
            parts.append(f"{coverage}% coverage")

        # Add quality gate status
        quality_gates_passed = result_data.get("quality_gates_passed")
        if quality_gates_passed is True:
            parts.append("all quality gates passed")
        elif quality_gates_passed is False:
            parts.append("quality gates failed")

        return ", ".join(parts) if parts else "Implementation completed"

    def _validate_file_count_constraint(
        self,
        task_id: str,
        documentation_level: str,
        files_created: List[str],
    ) -> None:
        """Validate that files created do not exceed documentation level limit.

        This method enforces documentation level constraints by logging a warning
        when the number of created files exceeds the limit for the specified level.
        This is monitoring-only and does not block execution.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            documentation_level: One of "minimal", "standard", or "comprehensive"
            files_created: List of files created by the agent

        Note:
            - "minimal" and "standard" levels have a limit of 2 files
            - "comprehensive" has no limit (None)
            - Unknown levels are treated as having no limit

        Example:
            >>> invoker._validate_file_count_constraint(
            ...     "TASK-001",
            ...     "minimal",
            ...     ["file1.py", "file2.py", "file3.py"]
            ... )
            # Logs: [TASK-001] Documentation level constraint violated: ...
        """
        max_files = DOCUMENTATION_LEVEL_MAX_FILES.get(documentation_level)

        # Comprehensive or unknown levels have no limit
        if max_files is None:
            return

        # TASK-GK-DOC-001: filter out orchestrator artefacts (turn dumps,
        # bdd oracle output, task plans, empty package markers) before
        # counting. Only real new code should count toward the limit.
        files_for_count = [
            f for f in files_created if not _is_doc_level_excluded(f)
        ]
        actual_count = len(files_for_count)

        if actual_count > max_files:
            # Show first 5 files to avoid overly long log messages
            files_preview = files_for_count[:5]
            suffix = "..." if len(files_for_count) > 5 else ""
            logger.warning(
                f"[{task_id}] Documentation level constraint violated: "
                f"created {actual_count} files, max allowed {max_files} "
                f"for {documentation_level} level. Files: {files_preview}{suffix}"
            )


# =========================================================================
# Module-level utility functions
# =========================================================================


def detect_rate_limit(error_text: str) -> Tuple[bool, Optional[str]]:
    """Detect if error is a rate limit error.

    Args:
        error_text: Error message or output text to check

    Returns:
        Tuple of (is_rate_limit, reset_time)
        reset_time is None if not parseable
    """
    patterns = [
        (r"hit your limit.*resets?\s+(\d+(?::\d+)?(?:\s*(?:am|pm))?(?:\s*\([^)]+\))?)", True),
        (r"rate limit", False),
        (r"too many requests", False),
        (r"429", False),
        (r"quota exceeded", False),
    ]

    text_lower = error_text.lower()
    for pattern, has_reset_time in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            reset_time = match.group(1) if has_reset_time and match.lastindex else None
            return True, reset_time

    return False, None
