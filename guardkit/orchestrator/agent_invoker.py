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
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, FrozenSet, List, Literal, Optional, Sequence, Set, Tuple, Union

from guardkit.lib.project_git import run_git

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
    from guardkit.orchestrator.harness.selector import ProjectDocument
    from guardkit.orchestrator.build_review import ReviewChange

from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    AgentLaunchRefusedError,
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
    PlanNotFoundError,
    PlayerReportInvalidError,
    PlayerReportNotFoundError,
    RateLimitExceededError,
    SDKTimeoutError,
    TaskStateError,
    TaskWorkResult,
    find_agent_launch_refusal,
)
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.llm_instrumentation import (
    classify_error,
    extract_token_usage,
    measure_latency,
    sanitise_tool_name,
)
from guardkit.orchestrator.instrumentation.redaction import SecretRedactor
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent, ToolExecEvent
from guardkit.orchestrator.paths import (
    TaskArtifactPaths,
    prepare_builder_scratch_dir,
)
from guardkit.orchestrator.docker_fixtures import render_player_recipes
from guardkit.orchestrator.launch_declaration import load_launch_snapshot
from guardkit.orchestrator.prompts import load_protocol
from guardkit.orchestrator import evidence_repos as evidence_repos_lib
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.failing_test_feedback import must_fix_items, split_must_fix_item
from guardkit.orchestrator.synthetic_report import (
    SHARED_WORKING_COPY_FIELD,
    mark_shared_working_copy,
    player_timeout_details,
)
from guardkit.orchestrator.schemas import (
    CompletionPromise,
    CriterionVerification,
)
from guardkit.orchestrator.stale_test_attribution import (
    _normalise_relpath,
    extract_failing_test_lines,
    runtime_parity_rationale,
    stale_test_notes,
)
from guardkit.orchestrator.authored_files import (
    NOT_TRACKED as _AUTHORED_NOT_TRACKED,
    SHELL_COMMAND_COUNT_KEY as _AUTHORED_SHELL_COUNT_KEY,
    TRACKED as _AUTHORED_TRACKED,
    TRACKING_KEY as _AUTHORED_TRACKING_KEY,
)

# TASK-CMIR-002: contract-resolution seam for coach synthesis prompt.
# ``GUARDKIT_COACH_CONTRACT`` selects which Decision Format the Coach
# synthesis prompt renders: ``"v4"`` (normative v4 block, task-trained
# contract) or ``"coachsplit"`` (byte-identical to today's legacy format,
# the default).
_COACH_CONTRACT_ENV = "GUARDKIT_COACH_CONTRACT"
_COACH_CONTRACT_DEFAULT = "coachsplit"


def _resolve_coach_contract() -> str:
    """Return the active coach-contract identifier.

    Delegates to the shared resolver (env > .guardkit/config.yaml
    ``autobuild.coach.contract`` > default) — one source of truth.

    Returns:
        One of ``"v4"`` or ``"coachsplit"``.
    """
    from guardkit.orchestrator.coach_contract import resolve_coach_contract
    return resolve_coach_contract()


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

_RUNTIME_EVIDENCE_TRACE_LIMIT = 64

_RUNTIME_TOOL_CATEGORIES = {
    "bash": "execute",
    "delegate": "delegate",
    "edit": "write",
    "edit_file": "write",
    "execute": "execute",
    "glob": "search",
    "grep": "search",
    "list_files": "read",
    "ls": "read",
    "plan": "plan",
    "read": "read",
    "read_file": "read",
    "search": "search",
    "task": "delegate",
    "todo_read": "plan",
    "todo_write": "plan",
    "write": "write",
    "write_file": "write",
    "write_todos": "plan",
}
_RUNTIME_USAGE_FIELDS = {
    "input_tokens": ("input_tokens", "prompt_tokens"),
    "output_tokens": ("output_tokens", "completion_tokens"),
    "total_tokens": ("total_tokens",),
    "cache_creation_input_tokens": ("cache_creation_input_tokens",),
    "cache_read_input_tokens": ("cache_read_input_tokens",),
}


def _nonnegative_exact_int(value: Any) -> Optional[int]:
    """Return a nonnegative built-in integer, excluding booleans."""
    if type(value) is int and value >= 0:
        return value
    return None


def _runtime_tool_category(name: object) -> str:
    """Map a tool name to the fixed, non-payload reporting vocabulary."""
    if not isinstance(name, str):
        return "other"
    return _RUNTIME_TOOL_CATEGORIES.get(name.casefold(), "other")


def _normalise_terminal_usage(usage: object) -> Dict[str, Any]:
    """Normalise only terminal-message usage into fixed nullable fields."""
    source = usage if isinstance(usage, dict) else {}
    normalised: Dict[str, Any] = {
        "scope": "terminal_message",
        "completeness": (
            "reported_by_harness" if isinstance(usage, dict) else "not_reported"
        ),
    }
    for output_name, aliases in _RUNTIME_USAGE_FIELDS.items():
        value = None
        for alias in aliases:
            candidate = _nonnegative_exact_int(source.get(alias))
            if candidate is not None:
                value = candidate
                break
        normalised[output_name] = value
    return normalised


# The 29 October 2026 builder skills change: which of the project's declared
# skill files and documents the builder opened. At most this many distinct paths
# per kind are recorded, from at most this many read calls per attempt.
_DECLARED_READS_LIMIT = 64
_DECLARED_READ_CALLS_LIMIT = 4096
_READ_FILE_TOOLS = frozenset({"read_file", "read"})


def _read_file_path(name: object, tool_input: object) -> Optional[str]:
    """The path a read_file (or SDK Read) call asked for, else ``None``."""
    if not isinstance(name, str) or name.casefold() not in _READ_FILE_TOOLS:
        return None
    if not isinstance(tool_input, dict):
        return None
    path = tool_input.get("file_path", tool_input.get("path"))
    return path if isinstance(path, str) and path else None


def _successful_read_paths(
    requests: Sequence[Tuple[str, str]], results: Sequence[Tuple[str, bool]]
) -> List[str]:
    """The paths of the read requests whose result came back without error.

    Matched by tool call id (Codex review R1, 29 October 2026): a read that
    failed, for example of a missing file, is not a read. A request with no
    id, or with no result, is not counted.
    """
    succeeded = {call_id for call_id, is_error in results if call_id and not is_error}
    return [path for call_id, path in requests if call_id and call_id in succeeded]


def _declared_reads(worktree: Path, read_paths: Sequence[str]) -> Dict[str, Any]:
    """Which declared skill files and documents the builder read, with counts.

    Rich asked on 29 October 2026 whether the builder uses the installed
    skills; this records it for each builder turn. Only paths the project
    declares are kept: files inside an ``autobuild.player.skills`` folder
    (``skills``) and the ``autobuild.player.required_documents``
    (``documents``), each as a repository-relative path (links such as
    ``.agents/skills`` resolved) with the number of read_file calls that
    succeeded (the caller passes only those, Codex review R1). Every
    other path is ignored and no file content is kept. It only records:
    nothing here can refuse or change the work, and a failure leaves the
    record empty with ``"unavailable": true``.
    """
    record: Dict[str, Any] = {"skills": {}, "documents": {}, "truncated": False}
    try:
        from guardkit.orchestrator.harness.selector import (
            _load_player_project_inputs,
        )

        root = Path(os.path.realpath(worktree))
        inputs = _load_player_project_inputs(Path(worktree))
        skill_roots = [
            resolved
            for resolved in (
                Path(os.path.realpath(root / value)) for value in inputs["skills"]
            )
            if resolved.is_relative_to(root)
        ]
        documents = {
            Path(os.path.realpath(root / value))
            for value in inputs["required_documents"]
        }
        for raw in read_paths:
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = root / candidate
            resolved = Path(os.path.realpath(candidate))
            if not resolved.is_relative_to(root):
                continue
            if resolved in documents:
                bucket = record["documents"]
            elif any(resolved.is_relative_to(skill) for skill in skill_roots):
                bucket = record["skills"]
            else:
                continue
            relative = resolved.relative_to(root).as_posix()
            if relative not in bucket and len(bucket) >= _DECLARED_READS_LIMIT:
                record["truncated"] = True
                continue
            bucket[relative] = bucket.get(relative, 0) + 1
    except Exception as exc:  # noqa: BLE001 - a record never stops the work
        logger.debug("Declared reads not recorded: %s", exc)
        record = {
            "skills": {},
            "documents": {},
            "truncated": False,
            "unavailable": True,
        }
    return record


def _build_task_work_runtime_evidence(
    *,
    harness_name: str,
    message_count: int,
    assistant_count: int,
    result_count: int,
    tool_uses: List[Tuple[str, str]],
    tool_results: List[Tuple[str, bool]],
    terminal_usage: object,
    attempt_wall_duration_ms: int,
    selected_attempt: int,
    discarded_attempts: int,
    sdk_turns_used: Optional[int],
    sdk_max_turns: Optional[int],
    wall_timeout_seconds: int,
    declared_reads: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build bounded, payload-free evidence for one selected attempt.

    ``declared_reads`` (see :func:`_declared_reads`) is added as it is when
    given: declared paths and counts only.
    """
    use_positions: Dict[str, List[int]] = {}
    result_values: Dict[str, List[bool]] = {}
    missing_use_ids = 0
    missing_result_ids = 0
    categories = {
        "read": 0,
        "write": 0,
        "search": 0,
        "execute": 0,
        "plan": 0,
        "delegate": 0,
        "other": 0,
    }

    for index, (tool_use_id, category) in enumerate(tool_uses):
        categories[category] += 1
        if tool_use_id:
            use_positions.setdefault(tool_use_id, []).append(index)
        else:
            missing_use_ids += 1
    for tool_use_id, is_error in tool_results:
        if tool_use_id:
            result_values.setdefault(tool_use_id, []).append(is_error)
        else:
            missing_result_ids += 1

    outcomes = ["missing_result"] * len(tool_uses)
    paired = 0
    for tool_use_id, positions in use_positions.items():
        results = result_values.get(tool_use_id, [])
        for position, is_error in zip(positions, results):
            outcomes[position] = "error" if is_error else "ok"
            paired += 1

    duplicate_use_ids = sum(
        max(0, len(positions) - 1) for positions in use_positions.values()
    )
    duplicate_result_ids = sum(
        max(0, len(values) - 1) for values in result_values.values()
    )
    trace = [
        {
            "ordinal": f"tool-{index + 1:04d}",
            "category": category,
            "outcome": outcomes[index],
            "duration_ms": None,
        }
        for index, (_, category) in enumerate(
            tool_uses[:_RUNTIME_EVIDENCE_TRACE_LIMIT]
        )
    ]

    sdk_supported = harness_name == "sdk"
    ceiling_hit: Optional[bool]
    if sdk_supported and sdk_turns_used is not None and sdk_max_turns is not None:
        ceiling_hit = sdk_turns_used >= sdk_max_turns
    else:
        ceiling_hit = None

    evidence: Dict[str, Any] = {
        "schema_version": 1,
        "attempt": {
            "selected": selected_attempt,
            "discarded": discarded_attempts,
            "completeness": (
                "terminal_result_observed" if result_count > 0 else "stream_ended"
            ),
        },
        "events": {
            "total": message_count,
            "assistant": assistant_count,
            "result": result_count,
            "tool_use": len(tool_uses),
            "tool_result": len(tool_results),
        },
        "pairing": {
            "paired": paired,
            "unmatched_use": len(tool_uses) - paired,
            "unmatched_result": len(tool_results) - paired,
            "error_result": sum(1 for _, is_error in tool_results if is_error),
            "duplicate_use_ids": duplicate_use_ids,
            "duplicate_result_ids": duplicate_result_ids,
            "missing_use_ids": missing_use_ids,
            "missing_result_ids": missing_result_ids,
        },
        "categories": categories,
        "tool_trace": trace,
        "trace_truncated": len(tool_uses) > _RUNTIME_EVIDENCE_TRACE_LIMIT,
        "terminal_usage": _normalise_terminal_usage(terminal_usage),
        "timing": {
            "attempt_wall_duration_ms": attempt_wall_duration_ms,
            "duration_supported": False,
            "event_delivery": (
                "streaming" if sdk_supported else "buffered_post_run"
            ),
        },
        "model_calls": {"count": None, "supported": False},
        "limits": {
            "sdk_turns": {
                "turns_used": sdk_turns_used if sdk_supported else None,
                "max_turns": sdk_max_turns if sdk_supported else None,
                "ceiling_hit": ceiling_hit,
                "supported": sdk_supported,
                "limit_kind": "sdk_turns" if sdk_supported else "unsupported",
            },
            "wall_timeout": {
                "seconds": wall_timeout_seconds,
                "supported": True,
                "limit_kind": "whole_attempt_wall_time",
            },
        },
    }
    if declared_reads is not None:
        evidence["declared_reads"] = declared_reads
    return evidence

# TASK-FIX-RWOP1.3.1: Agent-invocations validation on the producer path.
# task-work.md Step 6.5 declares validate_agent_invocations as "the ONLY
# checkpoint that prevents false reporting". Folding it into
# _write_task_work_results is the producer-runs-gate pattern from
# TASK-FIX-3C9D: without this wiring the Player can emit a results file
# claiming any phases were completed and no deterministic check catches it
# before Coach reads the file.

# TASK-FIX-RWOP1.3.2: Plan-audit gate on the producer path. The
# deterministic auditor in installer.core.commands.lib.plan_audit compares
# the saved plan against actual files/deps/LOC; without this wire the
# `plan_audit` block in task_work_results.json is the Player's self-report
# and can trivially claim "violations: []" while the worktree has extras.
# The producer fold makes Coach see the auditor's verdict, not the Player's.

# TASK-FIX-RWOP1.4a: Assumption-confidence warn-mode gate on the producer
# path. feature-spec.md's "Gating rule" claims the Coach verifies low-confidence
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
#   * ``.local/...`` / ``**/site-packages/...`` / ``.venv*/...`` —
#     environment-install artefacts the *bootstrap* writes into the worktree
#     (TASK-FIX-EVBINST01). The bootstrap's ``pip install`` (and any PEP-668
#     ``--user``/userbase fallback) lands packages under ``.local/`` or a
#     ``site-packages/`` tree; ``.local/`` is not in the worktree
#     ``.gitignore`` (only ``.venv*/`` is), so the per-turn checkpoint
#     ``git add -A`` commits it and the post-baseline ``git diff`` sweeps
#     every package file into ``files_modified``. FEAT-9DDE run-6 saw 136
#     ``.local/.../site-packages/_pytest/*`` paths attributed to the Player,
#     generating 136 spurious ``claim_audit_unmodified`` honesty records that
#     drowned the 2 real Coach findings. This is the *over-wide* direction of
#     the evidence-boundary defect (``.claude/rules/
#     evidence-boundary-narrower-than-write-surface.md``): the diff aperture
#     collects orchestrator-installed environment artefacts and attributes
#     them to the Player.
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
    # Environment-install artefacts the bootstrap writes into the worktree
    # (TASK-FIX-EVBINST01). Anchored / segment-scoped so no legitimate Player
    # source/test/doc path matches:
    #   ^\.local/             PEP-668 --user / userbase installs
    #   (?:.*/)?site-packages/  any site-packages tree (venv or user). NOTE:
    #                         these patterns are applied with ``re.match``
    #                         (anchored at start), so the leading ``(?:.*/)?``
    #                         is required to catch a ``site-packages/`` segment
    #                         that appears mid-path (e.g.
    #                         ``lib/python3.12/site-packages/...``).
    #   ^\.venv[^/]*/         .venv, .venv-*, .venv312 (defence-in-depth;
    #                         already gitignored, but absolute-form or
    #                         already-tracked variants still flow through diff)
    re.compile(r"^\.local/"),
    re.compile(r"(?:.*/)?site-packages/"),
    re.compile(r"^\.venv[^/]*/"),
    # The JavaScript/TypeScript equivalent of site-packages (TS-lane D.1c,
    # design §B.6 companion fix). Without this row, an `npm ci`/`npm install`
    # in a target repo that does NOT gitignore node_modules floods
    # files_modified / files_created with thousands of ghost paths the Player
    # never authored — the exact `claim_audit_unmodified` flood FEAT-9DDE
    # run-6 hit with site-packages, in a new alphabet.
    #   (?:.*/)?node_modules/   any node_modules tree: the repo root's, and a
    #                           monorepo's packages/<pkg>/node_modules/. Same
    #                           `re.match` (start-anchored) contract as
    #                           site-packages above, hence the `(?:.*/)?`.
    re.compile(r"(?:.*/)?node_modules/"),
    # Residual harness/orchestrator-managed namespaces (TASK-FIX-EVBINST02).
    # FEAT-9DDE run-8 coach_turn_2.json still raised should_fix
    # ``claim_audit_unmodified`` records on two more namespaces the Player
    # never authors. Anchored at ``^`` (worktree-root-relative) so no
    # legitimate Player path matches:
    #   ^large_tool_results/   harness tool-result spillover (fc_<hash> files
    #                          the SDK writes when a tool result is too large
    #                          to inline; swept into files_modified by the
    #                          post-turn ``git diff``)
    #   ^\.claude/task-plans/  orchestrator-created plan stubs
    #                          (``TASK-XXX-implementation-plan.md``). Kept
    #                          anchored to ``task-plans/`` so other
    #                          ``.claude/`` paths a Player might legitimately
    #                          author are not over-broadened (AC-2).
    re.compile(r"^large_tool_results/"),
    re.compile(r"^\.claude/task-plans/"),
    # npm's own caches, minted INSIDE the worktree (JX lane). The mirror of
    # the same three classes added to
    # ``worktree_checkpoints.CHECKPOINT_EXCLUDE_PATHSPECS``: the checkpoint
    # keeps them out of the COMMIT, this row keeps them out of the Player's
    # CLAIM LISTS, and both are needed — the post-turn ``git diff`` aperture
    # sees on-disk churn regardless of what was committed. FEAT-TST1's real
    # checkpoint carried 1365 ``.tmp/`` + 8 ``.npm/`` paths beside ~10 of
    # real work; unfiltered, that is the FEAT-9DDE run-6 claim-audit flood.
    #   (?:.*/)?\.tmp/   node's compile cache (`.tmp/node-compile-cache/...`),
    #                    at the worktree root and at any nested depth — same
    #                    `(?:.*/)?` contract as node_modules above. Matches a
    #                    `.tmp` DIRECTORY segment only, so a Player's
    #                    `fixtures/data.tmp` file passes through.
    #   (?:.*/)?\.npm/   npm's `_logs/` + `_update-notifier-last-checked`.
    #   \.guardkit-git\.lock  the harness's cross-process git lock, root or
    #                    nested; never Player work product.
    re.compile(r"(?:.*/)?\.tmp/"),
    re.compile(r"(?:.*/)?\.npm/"),
    re.compile(r"(?:.*/)?\.guardkit-git\.lock$"),
    # GuardKit's own records that this list did not name (19 October 2026).
    # ``worktree_checkpoints.FACTORY_RECORD_PATHS`` is the list of folders
    # GuardKit and the coding model write records to; a test now pins that
    # every one of them is matched here too. Build FEAT-D31F's repair ran at
    # the repository root, where the Coach's private records folder sits
    # inside the build folder: 13 of its records and the memory query log
    # were listed as files the builder created, the code reviewer was sent to
    # read them, and they made every turn look busy to the stall check.
    #   .guardkit/autobuild-private/  the Coach's private records
    #   .guardkit/qav-shadow/         the shadow judge's queue
    #   .guardkit/memory-query-log.jsonl*  the memory query log and its
    #                    rotated copy, written in whatever folder a command
    #                    runs in, so matched at any depth
    #   .guardkit/worktrees/          GuardKit's inner build folders
    #   conversation_history/         the coding model's session records
    re.compile(r"^\.guardkit/autobuild-private/"),
    re.compile(r"^\.guardkit/qav-shadow/"),
    re.compile(r"(?:.*/)?\.guardkit/memory-query-log\.jsonl"),
    re.compile(r"^\.guardkit/worktrees/"),
    re.compile(r"^conversation_history/"),
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
        (``<worktree>/FEAT-X/.guardkit/...``).
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
    # ``<worktree>/FEAT-X/.guardkit/...`` and harness-owned paths in
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
        ``<worktree>/FEAT-X/.guardkit/autobuild/<TASK_ID>/...``) are
        also stripped. See TASK-FIX-CAUD-J6F1 AC-003a.
    """
    stripped: Set[str] = set()

    for key in ("files_modified", "files_created", "tests_written", "claimed_files_modified", "claimed_files_created"):
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


# Constructor-fallback default for the (legacy-named) task-work "delegation" flag.
# NOTE (TASK-ACO-002): the name is historical. When enabled, invoke_player() does
# NOT shell `guardkit task-work --implement-only` and does NOT read
# installer/core/commands/task-work.md — _invoke_task_work_implement() builds an
# INLINE SDK prompt from the backend-selected autobuild_execution_protocol[_medium|_slim].md
# (see _build_autobuild_implementation_prompt in this module — pinned by NAME,
# not line: the 2026-08-02 re-pinning moved its own target). AutoBuild
# hardwires this True at all three AgentInvoker sites (autobuild.py:2439/:2472/:8856);
# this env default only affects direct constructor use. The compact _build_player_prompt
# path serves implementation_mode: direct (_invoke_player_direct), not this flag.
USE_TASK_WORK_DELEGATION = os.environ.get("GUARDKIT_USE_TASK_WORK_DELEGATION", "false").lower() == "true"

# SDK timeout in seconds (default: 1200s/20min, can be overridden via GUARDKIT_SDK_TIMEOUT env var)
# Complexity-6+ tasks with full Phase 3-5 pipeline (implementation, testing, code review)
# need ~900-1200s. 1200s provides adequate headroom for most tasks.
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1200"))

# TASK-ASF-008: Finite SDK timeout cap.  The unconfigured 1200s base retains
# its historical 3600s ceiling.  When GUARDKIT_SDK_TIMEOUT deliberately raises
# the base, allow the full task-work/complexity scale (at most 3x) up to a hard
# two-hour ceiling instead of silently clipping a configured 1800s base to one
# hour (1800 * 1.5 * 1.5 = 4050s for the ordinary complexity-5 task).
_DEFAULT_MAX_SDK_TIMEOUT = 3600
_ABSOLUTE_MAX_SDK_TIMEOUT = 7200
MAX_SDK_TIMEOUT = min(
    _ABSOLUTE_MAX_SDK_TIMEOUT,
    max(_DEFAULT_MAX_SDK_TIMEOUT, DEFAULT_SDK_TIMEOUT * 3),
)

# TASK-FIX-46F2: Retry constants for transient SDK stream errors.
# During autobuild, vLLM SSE streams can be interrupted under GPU contention
# with "SDK API error in stream: unknown". A single retry with backoff avoids
# the expensive state-recovery → re-implementation path.
MAX_SDK_STREAM_RETRIES = 1
SDK_STREAM_RETRY_BACKOFF = 30  # seconds


def turn_pressure(turn: int, max_turns: int) -> Tuple[bool, bool]:
    """The ONE rule for "is the Player running out of turns?".

    Returns ``(approaching_limit, final_turn)``.

    ``final_turn`` is simply ``turn >= max_turns`` — the last turn the Player
    will ever get. ``approaching_limit`` is the escape-hatch trigger: the point
    from which the Player should start considering a ``blocked_report``.

    The threshold is *not* a plain ``turn >= max_turns - 1``. That form is a lie
    in the degenerate case: ``work_runner.DEFAULT_MAX_TURNS`` is **2**, so
    ``1 >= 1`` made every *first* work-leg prompt say "Approaching turn limit …
    include a blocked_report" — the Player was told it was out of time on turn
    one of two, before it had written a line. A warning that fires on the first
    turn is not a warning, it is pressure to give up.

    So:

    * ``max_turns <= 2`` — warn on the FINAL turn only. With one or two turns
      there is no "one before last" worth naming; the first turn is clean.
    * ``max_turns >= 3`` — keep one-before-last semantics: approaching on the
      penultimate turn, final warning on the last.

    Stated once and used by every reader (``invoke_player``'s turn-context write
    and the implementation-prompt builder) so the prompt the Player reads and the
    ``turn_context.json`` it may consult can never disagree.
    """
    final_turn = turn >= max_turns
    if max_turns <= 2:
        return final_turn, final_turn
    return turn >= max_turns - 1, final_turn


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


# The build reviewer design of 29 October 2026: the review's look-up pass runs
# on every review (``AgentInvoker._invoke_coach_gather``), read-only, before
# the toolless, grammar-constrained verdict call. Its time is a slice of the
# review's: ``max(MIN, FRACTION * effective_timeout)``, never above it; the
# verdict call then runs at the full effective timeout.
_COACH_GATHER_BUDGET_FRACTION = 0.4
_COACH_GATHER_BUDGET_MIN_S = 60

# TASK-PERF-COACHSYNTH: each look-up tool result is cut at this many
# characters (with a visible marker), so a single read of a large file cannot
# fill the model's window; the reviewer pages with offset and limit. Its
# number of tool calls is bounded by the shared tool limit in guardkitfactory
# (40 tool-using model turns, then an answer), which replaced the 12-step
# graph ceiling that threw everything away when it tripped.
_COACH_GATHER_MAX_TOOL_RESULT_CHARS = int(
    os.environ.get("GUARDKIT_COACH_GATHER_MAX_TOOL_RESULT_CHARS", "12000")
)


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
    # TASK-AB-REVIEWCLEAN01 (item 1): this STREAMING parser is deliberately
    # NOT consolidated onto guardkit.lib.pytest_summary. It is a different
    # shape from the two one-shot count readers (specialist_invocations /
    # coach_validator, which DO share that lib): (1) it accumulates max-wins
    # across many stream messages, not a single captured output string; (2)
    # its summary regex is anchored to pytest's ``====`` decoration so it
    # cannot match an "N passed" fragment in arbitrary mid-stream prose,
    # whereas the lib parser matches outcome tokens anywhere; (3) its
    # positional capture semantics differ. Folding it in would change
    # observable behaviour (e.g. it would begin capturing the passed count on
    # failing-run summaries the decoration-anchored pattern currently misses),
    # which AC-007 forbids. The three-state skip contract below is kept
    # byte-identical to the lib's.
    # Pytest summary pattern: "X passed" or "X passed, Y failed" or "X passed, Y failed, Z skipped"
    PYTEST_SUMMARY_PATTERN = re.compile(
        r"[=]+\s*(?:(\d+)\s+passed)?(?:,?\s*(\d+)\s+failed)?(?:,?\s*(\d+)\s+skipped)?.*?[=]+",
        re.IGNORECASE
    )
    # TASK-AB-SKIPVIS01: independent skip-token search over a matched summary
    # line. The positional group(3) above only matches in passed-then-failed
    # adjacency, but pytest orders failed BEFORE passed on every failing run
    # ("2 failed, 3 passed, 1 skipped"), so deriving the skip count from
    # group(3) coerced a real skip count to 0 on failing-run summaries.
    PYTEST_SKIPPED_TOKEN_PATTERN = re.compile(r"(\d+)\s+skipped\b", re.IGNORECASE)
    # Alternative pytest pattern for simpler output: "5 passed in 0.23s"
    PYTEST_SIMPLE_PATTERN = re.compile(r"(\d+)\s+passed(?:\s+in\s+[\d.]+s)?", re.IGNORECASE)

    def __init__(
        self,
        worktree_root: Optional[Union[str, Path]] = None,
        scratch_root: Optional[Union[str, Path]] = None,
    ) -> None:
        """Initialize the parser with empty accumulated state.

        Args:
            worktree_root: The task's working folder. When given, an absolute
                tool-call path inside it is recorded relative to it (see
                ``_record_authored_path``). When omitted, paths are recorded
                exactly as the tool call gave them.
            scratch_root: 3 October 2026. The builder's scratch folder, only
                when it was checked (``prepare_builder_scratch_dir``) and the
                harness's backend really allows writes there
                (``provided_scratch_root``). Nothing in it is part of the
                project, so no path in it is listed. ``None`` leaves nothing
                off.
        """
        self._worktree_root: Optional[str] = (
            str(worktree_root) if worktree_root else None
        )
        self._scratch_root: Optional[str] = (
            os.path.normpath(str(scratch_root)) if scratch_root else None
        )
        # Where the folder really is, recorded once now that it has been
        # checked, so a later swap of the folder for a symlink cannot move
        # the boundary (see ``_in_scratch``).
        self._scratch_real: Optional[str] = (
            os.path.realpath(self._scratch_root) if self._scratch_root else None
        )
        self._phases: Dict[str, Dict[str, Any]] = {}
        self._tests_passed: Optional[int] = None
        self._tests_failed: Optional[int] = None
        # TASK-AB-SKIPVIS01: advisory skip count. None = no parseable pytest
        # summary seen (unknown, never 0-coerced); 0 = a summary parsed
        # cleanly with no skip token; N = N tests skipped. Never read by any
        # gate/verdict logic.
        self._tests_skipped: Optional[int] = None
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
        # 3 October 2026: write/edit requests waiting for their result, by
        # call id (see ``record_tool_request``).
        self._pending_tool_writes: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        # 13 October 2026: where each listed path came from. Nothing is ever
        # removed from the lists above because of these; they only let the
        # final report tell a confirmed scratch write from a claim (see
        # ``AgentInvoker._set_aside_written_then_removed``).
        #   * confirmed: a write request whose own result arrived and was not
        #     an error (the success branch of ``record_tool_result``). A write
        #     with no call id, one whose result never came, and one parsed
        #     from text are NOT confirmed.
        #   * named in words: a path the builder named in its own text (the
        #     "Created:/Modified:" lines and the text-form tool patterns).
        #   * unconfirmed: a path that ANY write reached without its own
        #     successful result (no call id, a result that never arrived, or
        #     parsed from text). One such write disqualifies the path, however
        #     many confirmed writes it also had.
        self._confirmed_write_paths: set = set()
        self._named_in_words_paths: set = set()
        self._unconfirmed_write_paths: set = set()
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

    # TS-lane D.1c: the TypeScript/JavaScript test-file naming conventions.
    # A vitest/jest suite is ``<subject>.test.ts`` or ``<subject>.spec.ts``
    # (``.tsx`` for component suites) — none of which the Python-only
    # ``test_*.py`` / ``*_test.py`` rules below could ever match, so a
    # TypeScript build's ``tests written`` count was structurally zero no
    # matter how many suites the Player actually wrote. Attribution, not
    # verdict: this feeds the Player report's tests-written signal.
    _TS_TEST_FILE_SUFFIXES: Tuple[str, ...] = (
        ".test.ts",
        ".spec.ts",
        ".test.tsx",
        ".spec.tsx",
        # Coordinator cure (D.1c coach): the two sibling recognisers
        # (state_tracker, coach_validator) already accept plain-JS suites —
        # this one must not attribute them zero.
        ".test.js",
        ".spec.js",
    )

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file path is a test file.

        Detects test files using each supported stack's common naming
        conventions:

        Python (unchanged):
        - test_*.py (pytest default)
        - *_test.py (alternative convention)

        TypeScript / JavaScript (TS-lane D.1c):
        - *.test.ts / *.spec.ts (vitest, jest)
        - *.test.tsx / *.spec.tsx (component suites)

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
        if name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py"):
            return True
        # A bare ``.test.ts`` dotfile is not a suite — require a subject name,
        # mirroring the Python rules (a bare ``test_`` is False there too).
        return any(
            name.endswith(suffix) and len(name) > len(suffix)
            for suffix in self._TS_TEST_FILE_SUFFIXES
        )

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

    def _record_authored_path(self, file_path: str) -> str:
        """Normalise one tool-call path to the task's working folder.

        The local builder's file tools take an absolute path — its schema says
        "Must be absolute, not relative", and every ``write_file`` / ``edit_file``
        call in the preserved tool streams is absolute (checked, not guessed:
        ``~/forge-state/receipts/build-FEAT-*/worktrees/*/.guardkit/autobuild/
        TASK-*/sdk_debug/turn_*/messages.jsonl``. The two kept 19 September
        builds hold 47 ``write_file`` and 50 ``edit_file`` calls, 97 of 97
        absolute and 96 rooted at the task's worktree; every build in that
        folder together holds 161, all absolute). Every
        reader of ``files_authored`` expects a worktree-relative path, so an
        absolute path inside the worktree is made relative here.

        A path outside the worktree, or already relative, is kept as it is:
        guessing would be worse than recording what the builder actually said.
        """
        if not self._worktree_root:
            return file_path
        normalised = _normalise_relpath(file_path, self._worktree_root)
        return normalised if normalised else file_path

    def _in_scratch(self, path: str) -> bool:
        """True when ``path`` is inside the builder's scratch folder.

        Such a path is left off every list, whether it came from a tool call
        or from the builder's own words: nothing there can be a product file,
        so leaving it off cannot hide a real claim. Only this folder is left
        off. A file written inside the worktree and later deleted, including
        a file git tracks, stays listed, and the existence check still
        reports it missing (unchanged, out of scope).
        """
        if self._scratch_root is None:
            return False
        if not os.path.isabs(path) and self._worktree_root:
            path = os.path.join(self._worktree_root, path)

        def inside(candidate: str, root: str) -> bool:
            return candidate == root or candidate.startswith(root + os.sep)

        # Both the path as written and where it really lands (following any
        # symlink, including one placed inside the scratch folder) must be in
        # the folder. So a project path such as ``src/app.py`` is never taken
        # for scratch, and neither is ``<scratch>/link/app.py`` when ``link``
        # points into the project. If the folder is there, it must still be
        # the real folder recorded when it was checked, not since swapped for
        # a symlink or a file. A folder the builder simply removed still
        # counts: its paths then resolve to where it was, so the landing check
        # below still holds unless a parent folder has moved. If any of that
        # cannot be worked out, keep the path.
        if not inside(os.path.normpath(path), self._scratch_root):
            return False
        try:
            root = self._scratch_root
            if os.path.lexists(root) and (
                os.path.islink(root)
                or not os.path.isdir(root)
                or os.path.realpath(root) != self._scratch_real
            ):
                return False
            landed = os.path.realpath(path)
        except (OSError, ValueError):
            return False
        return inside(landed, self._scratch_real)

    def record_tool_request(
        self, tool_use_id: Any, tool_name: str, tool_args: Dict[str, Any]
    ) -> None:
        """Hold a write/edit request until its result says whether it worked.

        3 October 2026. The list used to be filled when the builder *asked* to
        write, so a write the factory refused (a scratch file aimed at
        ``/tmp``, outside the worktree) stayed on it and the honesty check
        called it fabricated (FEAT-D586, FEAT-E592). Both the local and the
        hosted harness pair each tool call with its result by call id, so the
        path is recorded by :meth:`record_tool_result` once the result is
        known. A request with no call id cannot be paired and is recorded now,
        as before; one whose result never arrives is recorded by
        :meth:`to_result`, also as before.
        """
        if _runtime_tool_category(tool_name) != "write":
            return
        if isinstance(tool_use_id, str) and tool_use_id:
            self._pending_tool_writes[tool_use_id] = (tool_name, tool_args)
        else:
            recorded = self._track_tool_call(tool_name, tool_args)
            if recorded:
                self._unconfirmed_write_paths.add(recorded)

    def record_tool_result(self, tool_use_id: Any, is_error: bool) -> None:
        """Record a held write/edit now its result has arrived.

        A result with an error records nothing: the file was never written. A
        failed write retried successfully to the same path is recorded once,
        by the retry.
        """
        if not isinstance(tool_use_id, str):
            return
        held = self._pending_tool_writes.pop(tool_use_id, None)
        if held is None:
            return
        tool_name, tool_args = held
        if is_error:
            logger.debug(
                f"Tool {tool_name} call {tool_use_id} failed; its path is not "
                f"recorded as written."
            )
            return
        recorded = self._track_tool_call(tool_name, tool_args)
        # The one place a write is CONFIRMED: a request with a call id met
        # its own result, and the result was not an error.
        if recorded:
            self._confirmed_write_paths.add(recorded)

    def _track_tool_call(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Optional[str]:
        """Track file operations from a write-category tool call.

        Accepts ANY tool whose name maps to the ``"write"`` category in
        :data:`_RUNTIME_TOOL_CATEGORIES` — the one list of tool names in this
        module. That table already knows ``Write``/``Edit`` (the hosted
        builder) and ``write_file``/``edit_file`` (the local builder), so a new
        builder's tool name is added in one place, not two.

        Args:
            tool_name: Name of the tool (e.g. ``"Write"``, ``"write_file"``)
            tool_args: Tool arguments dictionary containing the file path

        Returns:
            The path as recorded on the lists, or ``None`` when nothing was
            recorded.
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
            return None

        if _runtime_tool_category(tool_name) != "write":
            logger.debug(f"Tool {tool_name} is not a write tool; not tracked.")
            return None

        if self._in_scratch(file_path):
            logger.debug(f"Scratch-folder write not tracked: {file_path}")
            return None

        recorded = self._record_authored_path(file_path)
        # Which side of the created/modified split this call lands on, read off
        # the same names the category table already holds: a "write"-shaped
        # name creates, anything else in the write category amends.
        base = tool_name.strip().casefold()
        if base.endswith("_file"):
            base = base[: -len("_file")]

        self._files_authored.add(recorded)
        if base == "write":
            self._files_created.add(recorded)
            logger.debug(f"Tool call tracked - file created: {recorded}")
            # Track test files separately
            if self._is_test_file(recorded):
                self._test_files_created.add(recorded)
                logger.debug(f"Test file tracked: {recorded}")
        else:
            self._files_modified.add(recorded)
            logger.debug(f"Tool call tracked - file modified: {recorded}")
        return recorded

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
                recorded = self._track_tool_call(tool_name, {"file_path": file_path})
                # Parsed from text: named in words, never confirmed.
                if recorded:
                    self._named_in_words_paths.add(recorded)
                    self._unconfirmed_write_paths.add(recorded)

        # Track tool result messages (e.g., "File created successfully at: /path")
        for result_match in self.TOOL_RESULT_CREATED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if (
                file_path
                and self._is_valid_file_path(file_path)
                and not self._in_scratch(file_path)
            ):
                self._files_created.add(file_path)
                self._named_in_words_paths.add(file_path)
                self._unconfirmed_write_paths.add(file_path)
                logger.debug(f"Tool result tracked - file created: {file_path}")

        for result_match in self.TOOL_RESULT_MODIFIED_PATTERN.finditer(message):
            file_path = result_match.group(1).strip()
            if (
                file_path
                and self._is_valid_file_path(file_path)
                and not self._in_scratch(file_path)
            ):
                self._files_modified.add(file_path)
                self._named_in_words_paths.add(file_path)
                self._unconfirmed_write_paths.add(file_path)
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
            # TASK-AB-SKIPVIS01: advisory skip count, derived from an
            # INDEPENDENT token search over the matched summary line — never
            # from the positional group(3), which only matches in
            # passed-then-failed adjacency and so misses the skip token on
            # every failing-run summary (pytest orders failed before passed:
            # "2 failed, 3 passed, 1 skipped"). Tri-state contract: None =
            # no parseable summary ever seen (unknown stays unknown, never
            # 0-coerced); 0 = a summary matched cleanly and carries no
            # 'skipped' token; N = N skipped.
            skipped_token_match = self.PYTEST_SKIPPED_TOKEN_PATTERN.search(
                pytest_summary_match.group(0)
            )
            if skipped_token_match:
                skipped_count = int(skipped_token_match.group(1))
                if self._tests_skipped is None or skipped_count > self._tests_skipped:
                    self._tests_skipped = skipped_count
                    logger.debug(f"Pytest summary - tests skipped: {self._tests_skipped}")
            elif pytest_summary_match.group(1) or pytest_summary_match.group(2):
                # A cleanly parsed summary (it carried a passed/failed count)
                # with no skip token is positively zero skips (0).
                if self._tests_skipped is None:
                    self._tests_skipped = 0

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

        # File modifications (use sets to avoid duplicates). A scratch-folder
        # path named in the builder's own words is left off too: it can never
        # be a product file, so the claim is harmless.
        for file_match in self.FILES_MODIFIED_PATTERN.finditer(message):
            file_path = file_match.group(1)
            if self._is_valid_file_path(file_path) and not self._in_scratch(file_path):
                self._files_modified.add(file_path)
                self._named_in_words_paths.add(file_path)
                logger.debug(f"File modified: {file_path}")

        for file_match in self.FILES_CREATED_PATTERN.finditer(message):
            file_path = file_match.group(1)
            if self._is_valid_file_path(file_path) and not self._in_scratch(file_path):
                self._files_created.add(file_path)
                self._named_in_words_paths.add(file_path)
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
            - tests_skipped: Advisory skip count (omitted when no parseable
              pytest summary was seen — unknown stays unknown; TASK-AB-SKIPVIS01)
            - coverage: Coverage percentage (or None)
            - quality_gates_passed: Boolean or None if not detected
            - files_modified: List of modified file paths
            - files_created: List of created file paths
            - test_files_created: List of test file paths created
            - architectural_review: Dict with score and optional SOLID/DRY/YAGNI
              subscores (or absent if no arch review score found)
        """
        # A write whose result never arrived stays on the list, as before,
        # and is never a confirmed write.
        for tool_name, tool_args in self._pending_tool_writes.values():
            recorded = self._track_tool_call(tool_name, tool_args)
            if recorded:
                self._unconfirmed_write_paths.add(recorded)
        self._pending_tool_writes = {}

        result: Dict[str, Any] = {}

        if self._phases:
            result["phases"] = self._phases

        if self._tests_passed is not None:
            result["tests_passed"] = self._tests_passed

        if self._tests_failed is not None:
            result["tests_failed"] = self._tests_failed

        # TASK-AB-SKIPVIS01: advisory only. Omitted when None (no parseable
        # pytest summary) — mirrors tests_passed/tests_failed absence handling.
        if self._tests_skipped is not None:
            result["tests_skipped"] = self._tests_skipped

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

        # 13 October 2026: where the listed paths came from (see __init__).
        if self._confirmed_write_paths:
            result["confirmed_write_paths"] = sorted(self._confirmed_write_paths)
        if self._named_in_words_paths:
            result["named_in_words_paths"] = sorted(self._named_in_words_paths)
        if self._unconfirmed_write_paths:
            result["unconfirmed_write_paths"] = sorted(self._unconfirmed_write_paths)

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
        self._tests_skipped = None
        self._coverage = None
        self._quality_gates_passed = None
        self._files_modified = set()
        self._files_created = set()
        self._files_authored = set()
        self._test_files_created = set()
        self._pending_tool_writes = {}
        self._confirmed_write_paths = set()
        self._named_in_words_paths = set()
        self._unconfirmed_write_paths = set()
        self._arch_score = None
        self._solid_score = None
        self._dry_score = None
        self._yagni_score = None


class ToolCallCounter:
    """Counts one model run's tool calls by name (13 October 2026).

    Handed to :meth:`AgentInvoker._invoke_with_role` by a caller that wants a
    record of which tools a run used (the code reviewer). It is owned by the
    caller, so the counts survive a run that is cut off.

    Two sources feed it. On LangGraph it hangs on the harness's native tool
    hook, which fires while the run is still going; it counts tool starts.
    On the SDK harness it counts the tool events in the stream. LangGraph
    also replays its tool events in the stream after a finished run, so the
    native counts win whenever there are any.

    Only tool names are kept, never arguments, paths or results. A name is
    whatever the model wrote (a call to a tool that does not exist reaches
    the stream as written), so a name is kept only when it is one of the
    tools actually bound for this run (:meth:`bind`, called by
    ``_invoke_with_role`` once the harness is chosen) and is a plain name —
    letters, digits and ``_ . : -``, at most 64 characters. Every other name,
    including any name seen before the tools are bound, is counted as
    ``"other"``. No method raises: a fault in counting must never stop a run.
    """

    #: The shape a kept name must have, on top of being a bound tool.
    _PLAIN_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
    OTHER = "other"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._native: Dict[str, int] = {}
        self._streamed: Dict[str, int] = {}
        self._bound: frozenset = frozenset()

    def bind(self, tool_names: Any) -> None:
        """Set the tools actually bound for this run; only these keep a name."""
        try:
            names = frozenset(
                name for name in tool_names or ()
                if isinstance(name, str) and self._PLAIN_NAME.fullmatch(name)
            )
        except Exception:  # noqa: BLE001 — counting must never raise
            names = frozenset()
        with self._lock:
            self._bound = names

    def _bump(self, table: Dict[str, int], name: object) -> None:
        if isinstance(name, str) and name in self._bound:
            key = name
        else:
            key = self.OTHER
        table[key] = table.get(key, 0) + 1

    def record_native(self, event: object) -> None:
        """Count a native (LangGraph) tool event; only starts are counted."""
        try:
            if getattr(event, "phase", None) != "start":
                return
            with self._lock:
                self._bump(self._native, getattr(event, "tool_name", None))
        except Exception:  # noqa: BLE001 — counting must never raise
            pass

    def record_streamed(self, name: object) -> None:
        """Count a tool call seen in the harness event stream."""
        try:
            with self._lock:
                self._bump(self._streamed, name)
        except Exception:  # noqa: BLE001 — counting must never raise
            pass

    def counts(self) -> Dict[str, int]:
        """Tool name to number of calls."""
        with self._lock:
            return dict(self._native or self._streamed)

    def total(self) -> int:
        """Total number of tool calls."""
        return sum(self.counts().values())


def _bound_tool_names(harness: Any, allowed_tools: Any, role: str) -> frozenset:
    """The tool names a harness binds for this invocation, for the counter.

    The SDK harness binds the requested names themselves. The LangGraph
    harness binds the DeepAgents tools its read-only table gives for a
    read-only request (guardkitfactory ``read_only_allowlist``); for any other
    request, or a guardkitfactory without that table, the names are not known
    here and the set is empty, so every name counts as ``"other"``.
    """
    if type(harness).__module__.startswith("guardkitfactory"):
        try:
            from guardkitfactory.harness.langgraph_harness import (
                read_only_allowlist,
            )

            return frozenset(read_only_allowlist(allowed_tools, role) or ())
        except Exception:  # noqa: BLE001 — unknown names count as "other"
            return frozenset()
    return frozenset(
        name for name in allowed_tools or () if isinstance(name, str)
    )


def _native_tool_sink(
    debug_dir: Optional[Path],
    preserve_event_checked: Any,
    tool_counter: Optional[ToolCallCounter],
) -> Optional[Any]:
    """The LangGraph native tool hook: the debug copy, the counter, or both.

    ``None`` when neither is wanted, which keeps the harness exactly as it
    was without them. The counter runs first and never raises; the debug
    copy keeps its existing fail-closed behaviour.
    """
    if debug_dir is None and tool_counter is None:
        return None

    def _sink(event: Any) -> None:
        if tool_counter is not None:
            tool_counter.record_native(event)
        if debug_dir is not None:
            preserve_event_checked(debug_dir, event)

    return _sink


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
    sdk_ceiling_hit: Optional[bool] = None     # TASK-VPR-003: Whether ceiling was hit
    session_id: Optional[str] = None           # TASK-RFX-B20B: SDK session ID for resumption


# TASK-CMIR-002 (coordinator fix-and-re-verify): the NORMATIVE v4 Decision Format
# block — byte-parity with the training corpus instruction (adf build_v4_sft.py
# V4_DECISION_FORMAT) and docs/coach-contract-mirror-scope-and-buildplan.md §4 Fix B.
# Any edit here breaks train==serve parity; change the corpus + retrain instead.
_V4_DECISION_FORMAT_BLOCK = '## Decision Format\n\nRespond with the verdict as a SINGLE RAW JSON object — no ```json fence, no\ncode fence of any kind, no prose before or after it. Your entire response is\nthe JSON object and nothing else; the orchestrator parses your response text\ndirectly as JSON. Do **NOT** use Bash to write a file.\n\nThe exact contract:\n\n{"verdict": "approve" | "reject", "findings": [{"locus": "<the specific in-bundle signal>"}]}\n\n- "verdict": "approve" when the deterministic evidence supports every\n  acceptance criterion; "reject" when any signal in the bundle defeats or\n  fails to support approval.\n- "approve" REQUIRES "findings": [] (empty list).\n- "reject" REQUIRES at least one finding. Each finding\'s "locus" must name the\n  exact bundle field, value, file path, or symbol that carries the defeating\n  signal, quoting the bundle\'s own text (e.g. "bdd.scenarios_attempted=0 while\n  bdd.feature_files lists \\"features/x.feature\\""). A generic locus\n  ("not safe", "tests insufficient") is a contract violation.\n- No other keys: no class, no task_id, no rationale — the two keys above are\n  the entire contract.'


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

    #: A gate-driven repair round handed over in memory (see ``__init__``);
    #: declared here too so an invoker built without ``__init__`` reads None.
    repair_round: Optional[Any] = None
    #: In a repair round, the non-protected files the latest plan audit put in
    #: front of the reviewer (what the round made or changed beyond the task
    #: document). Read by the orchestrator when the reviewer approves the turn.
    repair_round_inventory: Optional[FrozenSet[str]] = None
    #: This Coach turn's repair-round review (``_repair_round_review``).
    _repair_review: Optional[Dict[str, Any]] = None

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
        evidence_repos: Optional[List["EvidenceRepo"]] = None,  # TASK-AB-XREPOEV01
        sdk_timeout_is_override: Optional[bool] = None,
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
            sdk_timeout_is_override: Whether ``sdk_timeout_seconds`` came from
                an explicit CLI/task override. ``None`` retains the legacy
                value-comparison inference for direct callers.
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
            evidence_repos: Resolved sibling repos whose writes count as task
                evidence (TASK-AB-XREPOEV01). Default None -> empty -> zero
                behaviour change; the evidence boundary stays scoped to the
                worktree. When populated, the post-turn diff merges per-repo
                git changes into the Player report as repo-qualified paths
                (``<repo>:<path>``) and CoachVerifier resolves those claims
                against the right repo root.
        """
        self.worktree_path = Path(worktree_path)
        # A gate-driven repair round (20 October 2026), handed over in memory
        # by the orchestrator that re-opened the task
        # (guardkit/orchestrator/repair_round.py). ``None`` on every ordinary
        # turn; nothing on disk sets it.
        self.repair_round: Optional[Any] = None
        self._venv_python: Optional[str] = venv_python
        self.max_turns_per_agent = max_turns_per_agent
        self.sdk_timeout_seconds = sdk_timeout_seconds
        self._sdk_timeout_is_override = (
            sdk_timeout_seconds != DEFAULT_SDK_TIMEOUT
            if sdk_timeout_is_override is None
            else sdk_timeout_is_override
        )
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
        from guardkit.orchestrator.task_work_scope import current_lease
        lease = current_lease(worktree_path)
        self.task_work_scope = lease.scope if lease else None
        self._baseline_commit: Optional[str] = (self.task_work_scope.baseline_commit if self.task_work_scope else None)
        # True when other tasks in the same wave are changing this working
        # copy at the same time. Set by the orchestrator. A report this
        # invoker builds from git is then marked as shared and carries no
        # evidence for the task (build FEAT-2C42, 8 October 2026).
        self.shared_working_copy: bool = False
        # 29 October 2026: each fresh task's ``toolchain.language_servers``,
        # pinned in memory by AutoBuild before the builder's first turn
        # (``pin_language_servers``); ``None`` when it declares none. A task
        # missing here was resumed in a new process (``_language_servers_for``).
        self._pinned_language_servers: Dict[str, Optional[List[Any]]] = {}
        # TASK-AB-XREPOEV01: declared sibling repos whose writes count as task
        # evidence (default empty -> undeclared sibling-repo writes stay
        # invisible, AC-003). Per-repo HEAD baselines are recorded alongside
        # the worktree baseline so the post-turn diff attributes only this
        # task's sibling-repo writes.
        self._evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
        self._evidence_baselines: Dict[str, Optional[str]] = {}
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
            # Same one list of write-tool names as the file tracker. Before
            # 2026-09-21 this tested for ``Write``/``Edit`` only, so every
            # local build's progress line read ``files_changed=0`` however many
            # files the builder wrote.
            if _runtime_tool_category(name) == "write":
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
        import subprocess

        killed: list = []
        try:
            # Find direct children
            result = subprocess.run(
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
                gc_result = subprocess.run(
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
                    ps_result = subprocess.run(
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
        except subprocess.TimeoutExpired:
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
            context: Job-specific context from the memory backend (role constraints, quality gates,
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

        # Calculate if we're approaching the turn limit (escape hatch trigger).
        # ``turn_pressure`` is the ONE rule — see its docstring for why a plain
        # ``turn >= max_turns - 1`` lies when max_turns is 2 (the work leg's default).
        approaching_limit, _final_turn = turn_pressure(turn, max_turns)

        try:
            # Write turn context for Player to read (includes approaching_limit)
            self._write_turn_context(task_id, turn, max_turns, approaching_limit)

            # Write feedback for task-work to read whenever there is any.
            # Feedback on turn 1 is a gate's seed: a post-wave gate (smoke,
            # wiring, the whole-feature check) failed AFTER this task was
            # approved and the wave was re-entered with the gate's output. The
            # old ``turn > 1`` guard dropped exactly that feedback, so every
            # gate-driven re-entry ran a Player that had been told nothing
            # (found by driving the real runner, 19 September 2026).
            if feedback:
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

                    # TASK-VPR-003: Extract SDK turn data from TaskWorkResult
                    from guardkit.orchestrator.sdk_ceiling import detect_ceiling_hit
                    _sdk_turns_used = result.sdk_turns_used
                    _sdk_max_turns = result.sdk_max_turns
                    _sdk_ceiling_hit = detect_ceiling_hit(
                        _sdk_turns_used,
                        _sdk_max_turns,
                        unknown_is_none=True,
                    )

                    # TASK-VOPT-002: Per-turn timing instrumentation
                    if _sdk_turns_used is None:
                        logger.info(
                            "[%s] Harness invocation complete: %.1fs, SDK turns unknown",
                            task_id,
                            duration,
                        )
                    else:
                        logger.info(
                            "[%s] SDK invocation complete: %.1fs, %d SDK turns (%.1fs/turn avg)",
                            task_id, duration, _sdk_turns_used,
                            duration / max(_sdk_turns_used, 1),
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
        except AgentLaunchRefusedError:
            # The agent never started and would be refused again next turn.
            # Let the orchestrator's unrecoverable path stop the task.
            raise
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
        project_documents: Optional[Sequence["ProjectDocument"]] = None,
        turn_left: bool = False,
    ) -> AgentInvocationResult:
        """Review one builder turn (the build reviewer design of 29 October 2026).

        Two model calls (``guardkit/orchestrator/build_review.py``):

        - a read-only look-up pass, given the change itself (git, from the
          task's starting commit) and the project's check result, that answers
          five questions against the change and the code with read-only tools
          bounded by the shared tool limit;
        - a smaller toolless verdict call that turns its findings into issues
          carrying a pattern and a location.

        The verdict is advice: the turn is sent back by the five ordinary-code
        rules, or once per task for located findings when ``turn_left`` (the
        repair turn). The orchestrator writes the verdict to
        ``coach_turn_{turn}.json`` in the task's private folder.

        Args:
            task_id: Task identifier
            turn: Current turn number
            requirements: Original task requirements
            player_report: Player's report from current turn
            remaining_budget: Optional remaining wall-clock budget in seconds.
                When provided, sdk_timeout_seconds is capped at this value for
                this invocation then restored. Used to honour per-turn budgets
                and Coach grace periods. (TASK-ABFIX-004)
            evidence_bundle: Optional ``CoachEvidenceBundle`` from
                ``CoachValidator.gather_evidence``: the project's own check
                results, rendered into the prompt and read by the guards that
                may send the turn back.
            coach_context: Optional memory / coach context string. Passed
                through to ``_build_coach_prompt`` for inclusion in the prompt.
            acceptance_criteria: Optional structured ACs (``[{"id","text"}]``)
                threaded into the Coach prompt so the synthesis verdict can
                carry a populated ``criteria_verification`` per AC
                (TASK-ARCH-COACHBFULL AC-4 — the run-19 empty-array fix) and so
                the look-up pass has the criteria to check. When ``None`` the
                prompts omit the per-criterion section.
            project_documents: Optional project instructions and binding
                documents (``harness.selector.load_project_documents_at_commit``).
                Only their paths reach the look-up pass, which reads the part
                of one a question needs (the build reviewer design of 29
                October 2026: their full text is no longer pasted in).
            turn_left: Whether the task has a builder turn left after this
                one, so located findings may get the one repair turn.

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
            documents = tuple(project_documents or ())

            # A gate-driven repair round (20 October 2026): what the round
            # made, changed or deleted beyond the task document, read from git
            # on every repair-round turn whatever audit path the task takes.
            # The prompt's repair section and the protected-file refusal below
            # both come from this one step.
            self._repair_review = self._repair_round_review(task_id)

            # The build reviewer design of 29 October 2026: the look-up pass
            # runs on every review. It is given the change itself (git, from
            # the task's starting commit) and reads the code with read-only
            # tools, bounded by the shared tool limit; its time is a slice of
            # this review's. Any failure gives no findings text and the
            # verdict call still runs (a reviewer finding is never a refusal).
            from guardkit.orchestrator import build_review

            change = build_review.write_change(
                task_id, turn, self.worktree_path, getattr(self, "_baseline_commit", None)
            )
            sent_back = list(self._review_repair_sent_for(task_id, turn) or ())
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
                evidence_bundle=evidence_bundle,
                acceptance_criteria=acceptance_criteria,
                gather_timeout=gather_timeout,
                change=change,
                sent_back=sent_back,
                document_paths=[str(d.path) for d in documents],
            )

            # Build prompt for Coach with verification context.
            prompt = self._build_coach_prompt(
                task_id, turn, requirements, player_report,
                acceptance_criteria=acceptance_criteria,
                evidence_bundle=evidence_bundle,
                coach_context=coach_context,
                gather_findings=gather_findings,
            )

            # TASK-FIX-COACHOUT01 Shape A: extract the structured verdict from
            # Coach's response text and persist coach_turn_N.json from the
            # orchestrator side.
            from guardkit.orchestrator.coach_output_parser import (
                extract_and_write as _coach_extract_and_write,
            )
            from guardkit.orchestrator.paths import TaskArtifactPaths

            # TASK-SBHO-002: coach verdict goes to the orchestrator-private
            # directory so the Player cannot read judge evidence.  This
            # relocation removes the casual read, not a determined process;
            # full enforcement = the sandbox lane.
            coach_output_path = TaskArtifactPaths.private_artifact_path(
                task_id, f"coach_turn_{turn}.json", self.worktree_path
            )
            try:
                # The verdict call: toolless and grammar-constrained, so the
                # GBNF grammar can force the verdict's shape (llama.cpp
                # refuses a grammar with tools). return_events=True so the
                # typed HarnessEvent stream comes back for
                # coach_output_parser; the orchestrator writes
                # coach_turn_N.json itself, the reviewer never writes.
                # Load the GBNF verdict grammar; degrade to prompt-only (still
                # toolless) if the packaged grammar can't be read so a
                # packaging glitch never hard-fails the Coach.
                # Contract-aware: resolves GUARDKIT_COACH_CONTRACT > config >
                # default and selects the matching grammar file (TASK-CMIR-003).
                grammar: Optional[str] = None
                try:
                    from guardkit.orchestrator.coach_grammar import (
                        load_coach_verdict_grammar,
                    )

                    grammar = load_coach_verdict_grammar(
                        contract=None,  # resolve at call site
                    )
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
                assert result_tuple is not None, (
                    "_invoke_with_role(return_events=True) must return a tuple "
                    "on success; got None"
                )
                _, harness_events = result_tuple

                _coach_extract_and_write(
                    harness_events=harness_events,
                    task_id=task_id,
                    turn=turn,
                    output_path=coach_output_path,
                )
                decision = self._load_agent_report_from(
                    task_id, turn, "coach", coach_output_path
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — the reviewer is advice
                # The reviewer's verdict is advice (27 October 2026): when its
                # call fails, or gives no readable verdict, the turn goes on
                # with no reviewer findings.
                logger.warning(
                    "[%s] Turn %s: the reviewer gave no readable verdict (%s); "
                    "the turn goes on without its findings.",
                    task_id, turn, exc,
                )
                decision = {
                    "task_id": task_id,
                    "turn": turn,
                    "decision": "approve",
                    "issues": [],
                    "rationale": f"The reviewer gave no readable verdict: {exc}",
                }
            if not isinstance(decision.get("issues"), list):
                decision["issues"] = []

            # The reviewer's verdict is advice (Rich, 27 October 2026): the
            # turn is sent back only when the project's own tests or declared
            # checks ran and failed, or a repair round changed a protected
            # file (the five calls below), or, once per task, for the
            # reviewer's located findings (the repair turn after them).
            reviewer_issues = list(decision["issues"])
            decision["decision"] = "approve"
            self._persist_coach_decision(
                decision, coach_output_path, tag="reviewer-advice", kind="annotated"
            )

            # The project's required test suite ran and failed.
            self._apply_independent_test_code_failure_guard(
                decision=decision,
                evidence_bundle=evidence_bundle,
                task_id=task_id,
                turn=turn,
                coach_output_path=coach_output_path,
            )

            # The feature's declared smoke command ran and failed.
            self._apply_runtime_parity_guard(
                decision=decision,
                evidence_bundle=evidence_bundle,
                task_id=task_id,
                turn=turn,
                coach_output_path=coach_output_path,
            )

            # The declared behavioural check ran and failed.
            self._apply_behavioural_oracle_guard(
                decision=decision,
                evidence_bundle=evidence_bundle,
                task_id=task_id,
                turn=turn,
                coach_output_path=coach_output_path,
            )

            # The secrets check found a secret in this task's changes.
            self._apply_security_check_guard(
                decision=decision,
                evidence_bundle=evidence_bundle,
                task_id=task_id,
                turn=turn,
                coach_output_path=coach_output_path,
            )

            # A repair round that changed a protected file.
            self._enforce_repair_round_protected(
                decision=decision,
                review=self._repair_review,
                task_id=task_id,
                turn=turn,
                coach_output_path=coach_output_path,
            )

            # The one repair turn for the reviewer's located findings, or
            # what this review leaves for the merge card.
            self._apply_review_repair_turn(
                decision=decision,
                reviewer_issues=reviewer_issues,
                task_id=task_id,
                turn=turn,
                turn_left=turn_left,
                coach_output_path=coach_output_path,
            )

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
        evidence_bundle: Optional["CoachEvidenceBundle"],
        acceptance_criteria: Optional[List[Dict[str, str]]],
        gather_timeout: int,
        change: Optional["ReviewChange"] = None,
        sent_back: Sequence[Dict[str, Any]] = (),
        document_paths: Sequence[str] = (),
    ) -> Optional[str]:
        """The review's look-up pass: read-only, against the change and the code.

        The build reviewer design of 29 October 2026. It asks for
        ``["Read", "Search", "Grep", "Glob"]``, so the harness builds its
        read-only graph: read_file, ls, grep, glob and the code tools (with
        ``code_references`` when the task's language servers were pinned in
        this process), no write and no shell, bounded by the shared tool limit
        (40 tool-using model turns, or a repeated identical call, then the
        tools are withdrawn and the answer asked for). Each tool result is cut
        at :data:`_COACH_GATHER_MAX_TOOL_RESULT_CHARS`; the pass has its slice
        of the review's time.

        Returns the findings text, or ``None`` on any failure or an empty
        answer: the verdict call then runs without it (a reviewer finding is
        never a refusal). ``asyncio.CancelledError`` is not caught: a real
        cancellation stops the review.
        """
        from guardkit.orchestrator import build_review

        prev_timeout = self.sdk_timeout_seconds
        self.sdk_timeout_seconds = gather_timeout
        try:
            prompt = self._build_coach_gather_prompt(
                task_id=task_id,
                turn=turn,
                requirements=requirements,
                player_report=player_report,
                evidence_bundle=evidence_bundle,
                acceptance_criteria=acceptance_criteria,
                change=change,
                sent_back=sent_back,
                document_paths=document_paths,
            )
            result_tuple = await self._invoke_with_role(
                prompt=prompt,
                agent_type="coach",
                allowed_tools=list(build_review.LOOKUP_TOOLS),
                permission_mode="bypassPermissions",
                task_id=task_id,
                turn=turn,
                return_events=True,
                synthesis=False,
                max_tool_result_chars=_COACH_GATHER_MAX_TOOL_RESULT_CHARS,
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
                    "[%s] Turn %s: the review's look-up pass gave no findings "
                    "text; the verdict runs without it.",
                    task_id, turn,
                )
                return None
            logger.info(
                "[%s] Turn %s: the review's look-up pass gave %d characters of "
                "findings.", task_id, turn, len(findings),
            )
            return findings
        except Exception as exc:  # noqa: BLE001 — the review goes on without it
            logger.warning(
                "[%s] Turn %s: the review's look-up pass failed (%s: %s); the "
                "verdict runs without it.",
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
        evidence_bundle: Optional["CoachEvidenceBundle"],
        acceptance_criteria: Optional[List[Dict[str, str]]],
        change: Optional["ReviewChange"] = None,
        sent_back: Sequence[Dict[str, Any]] = (),
        document_paths: Sequence[str] = (),
    ) -> str:
        """The look-up pass's prompt (``build_review.build_lookup_prompt``):
        the task, the change, the project's check, the builder's notes, any
        findings sent back for repair, the project's document paths, and the
        five questions."""
        from guardkit.orchestrator import build_review

        check_section = ""
        if evidence_bundle is not None:
            check_section = self._render_evidence_bundle_section(evidence_bundle).strip()
        if change is None:
            change = build_review.ReviewChange(
                "", None, None, "The change was not given to this review."
            )
        return build_review.build_lookup_prompt(
            task_id=task_id,
            turn=turn,
            requirements=requirements,
            acceptance_criteria=acceptance_criteria,
            change=change,
            check_section=check_section,
            player_report=player_report,
            sent_back=sent_back,
            document_paths=document_paths,
        )

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
            context: Job-specific context from the memory backend (role constraints, quality gates,
                turn states). Included before requirements for prompt context.
            design_context: Optional design context for UI implementation tasks

        Returns:
            Formatted prompt string for Player agent
        """
        feedback_section = ""
        if feedback:
            # Turn-1 feedback is a gate's seed (see invoke_player); there is
            # no "turn 0" Coach to attribute it to.
            heading = (
                f"Coach Feedback from Turn {turn - 1}"
                if turn > 1
                else "Feedback from the check that failed after this task was approved"
            )
            feedback_section = f"""
## {heading}

{feedback}

Please address all feedback points in this turn.
"""

        # Build context section if provided (memory-backend job-specific context)
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


        # TASK-AB-INVARIANTTEST01: responsibility 2 carries the
        # invariant-not-snapshot constraint (location 1 of the three
        # Player-prompt locations; locations 2-3 live in
        # installer/core/agents/autobuild-player.md, and the matching
        # Coach-side detection is advisory guard #8 in
        # _render_absence_of_failure_guards).
        prompt = f"""You are the Player agent. Implement the following task.

Task ID: {task_id}
Turn: {turn}
{context_section}{design_section}
## Requirements

{requirements}
{criteria_section}{feedback_section}

## Your Responsibilities

1. Implement the code to satisfy the requirements
2. Write comprehensive tests that assert LASTING INVARIANTS, never
   point-in-time snapshots of the current task boundary
   (invariant-not-snapshot): never assert that a method raises
   NotImplementedError, or that a directory/table/config is empty or absent,
   when a later task in THIS feature implements/fills it; scope any boundary
   pin to methods/paths NO task in this feature will implement, and say which
   task owns each excluded piece. Tests exercising env-read configuration
   MUST pin the FULL relevant env-var surface with monkeypatch.setenv/delenv
   (hermetic-env): a test whose outcome can change with the host environment
   is not a test of the code, and its failure diff can print live ambient
   values
3. Run the tests and verify they pass
4. Create your report with completion promises for each acceptance criterion.
   Mark a criterion incomplete when your implementation departs from its exact
   text, even when the departure is documented or resolves a safety problem.
   Only an authoritative amended criterion changes the target. Report an
   unsafe or conflicting requirement as a concern; do not claim it is fulfilled
   and do not restore unsafe behaviour merely to make the words match.

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
        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
        evidence_bundle: Optional["CoachEvidenceBundle"] = None,
        coach_context: Optional[str] = None,
        gather_findings: Optional[str] = None,
    ) -> str:
        """The verdict call's prompt (the build reviewer design of 29 October 2026).

        Kept: the task and its criteria, the look-up pass's findings, the
        project's check result (``evidence_bundle``), the builder's concerns,
        its "remaining" list and git's file lists, and any memory context.
        In a repair round, the whole-feature check and the round's files.
        Not given any more: the project's documents in full (the look-up pass
        reads the part a question needs), the builder's whole report, the
        "no tools" attribution banner and its paperwork responsibilities, and
        reply prose the grammar already forces.
        """
        from guardkit.orchestrator import build_review

        # TASK-CMIR-002: contract resolution — must happen before any
        # contract-aware rendering (criteria, decision format).
        contract = _resolve_coach_contract()
        is_v4 = contract == "v4"

        evidence_section = ""
        if evidence_bundle is not None:
            evidence_section = self._render_evidence_bundle_section(
                evidence_bundle
            )
        else:
            evidence_section = (
                "\n## Deterministic Evidence Bundle\n\n"
                "No check result was recorded for this turn.\n"
            )

        coach_context_section = ""
        if coach_context:
            coach_context_section = f"""
## Coach Context

{coach_context}
"""

        if gather_findings and gather_findings.strip():
            findings_body = self._truncate_gather_findings(gather_findings.strip())
        else:
            findings_body = (
                "The look-up pass gave no findings (it failed, or ran out of time). "
                "Report no finding you cannot see in the check result above."
            )
        findings_section = f"""
## Look-up findings

A look-up pass read the change and the code with read-only tools and answered
five questions. Its findings, one per line with a place in the code:

{findings_body}
"""

        criteria_section = ""
        if acceptance_criteria:
            criteria_lines = ["## Acceptance Criteria to Verify", ""]
            for criterion in acceptance_criteria:
                criteria_lines.append(f"- **{criterion['id']}**: {criterion['text']}")
            criteria_section = "\n".join(criteria_lines) + "\n"

        # 18 October 2026: in a whole-feature repair round only, the project's
        # whole-feature check, with what it printed on this turn's code and on
        # the code that failed before. "" on every other turn.
        whole_feature_check_section = self._render_whole_feature_check_section(
            evidence_bundle
        )
        # 20 October 2026: in a gate-driven repair round only, the extra files
        # for the reviewer to judge against the failing gate. "" otherwise.
        repair_round_section = self._render_repair_round_section(
            getattr(self, "_repair_review", None)
        )

        patterns = ", ".join(f"`{p}`" for p in build_review.FINDING_PATTERNS)
        if is_v4:
            instructions = f"""
## Your Responsibilities

1. Turn each look-up finding of the five kinds ({patterns}) into one
   finding whose locus is `PATTERN path:line: one plain sentence`. Keep its
   words; add a finding only when the check result above plainly shows it
   (`NOT_TESTED` when the check ran no test).
2. A criterion that conflicts with a project document is one finding whose
   locus is `CRITERION_CONFLICT path:line: one plain sentence`: advice for
   the person approving the build; it does not decide the verdict.
3. Either APPROVE (no finding of the five kinds) or REJECT with those findings.
"""
        else:
            instructions = f"""
## Your Responsibilities

1. Turn each look-up finding of the five kinds ({patterns}) into one issue,
   with its `pattern` and its `location` (`path:line`). Keep its words; add a
   finding only when the check result above plainly shows it (`NOT_TESTED`
   when the check ran no test).
2. A finding about a criterion that conflicts with a project document is
   `CRITERION_CONFLICT`, severity "minor": advice.
3. For each acceptance criterion, a `criteria_verification` entry: "verified"
   unless a finding says the criterion is not done or not tested.
4. Decide "approve" when there is no finding of the five kinds; otherwise
   "feedback".
"""

        if is_v4:
            decision_format_block = "\n" + _V4_DECISION_FORMAT_BLOCK + "\n"
        else:
            decision_format_block = f"""
## Decision Format

End your response with one fenced ```json block, the last thing you write:

```json
{{
  "task_id": "{task_id}",
  "turn": {turn},
  "decision": "approve" | "feedback",
  "issues": [
    {{
      "pattern": "NOT_TESTED",
      "severity": "major",
      "location": "src/notes/list.py:42",
      "description": "One plain sentence: what is wrong and what the task or code says.",
      "suggestion": "How to fix it"
    }}
  ],
  "criteria_verification": [
    {{"criterion_id": "AC-001", "result": "verified" | "rejected", "notes": "why"}}
  ],
  "validation_results": {{"tests_passed": true, "test_output_summary": "what the check printed"}},
  "rationale": "One or two sentences"
}}
```

Use `"issues": []` when there are no findings.
"""

        prompt = f"""You are the Coach agent. Write the verdict for one builder turn from the findings below.

Task ID: {task_id}
Turn: {turn}

## Original Requirements

{requirements}
{criteria_section}{whole_feature_check_section}{repair_round_section}
## Player's Report

The builder's concerns, what it says remains, and the files git saw it create and change:

{build_review.render_builder_notes(player_report)}
{evidence_section}{findings_section}{coach_context_section}{instructions}{decision_format_block}"""
        # TASK-SELFFIX-003: enforce the overall verdict-prompt budget. The
        # repair-round sections are never trimmed.
        untrimmed = prompt
        prompt = self._trim_synthesis_prompt(
            untrimmed,
            protected_section=whole_feature_check_section + repair_round_section,
        )
        # A repair round's section that did not survive is tried once more
        # with only the gate's output cut shorter; the file lists are never
        # cut. invoke_coach refuses the turn if it still did not survive.
        sections = self._repair_round_sections(getattr(self, "_repair_review", None))
        if sections and not any(section in prompt for section in sections):
            shorter = sections[-1]
            prompt = self._trim_synthesis_prompt(
                untrimmed.replace(repair_round_section, shorter, 1),
                protected_section=whole_feature_check_section + shorter,
            )

        return prompt

    #: In a repair round the end of the gate's output is cut to this many
    #: characters when the full section does not fit the synthesis budget;
    #: the file lists are never cut (20 October 2026).
    _REPAIR_SECTION_SHORT_GATE_OUTPUT = 1000

    def _render_repair_round_section(
        self,
        review: Optional[Dict[str, Any]],
        gate_output_limit: Optional[int] = None,
    ) -> str:
        """Render ``## This is a repair round``, or ``""`` (20 October 2026).

        ``review`` is :meth:`_repair_round_review` for this turn, ``None``
        outside a repair round. The section puts in front of the reviewer
        every file the round made, changed or deleted that the task document
        does not name, says which ones the failing gate's output names, shows
        the end of that output, and asks the reviewer to refuse the turn if
        any of them is not needed to make the failing check pass. Every file
        is listed; only the gate's output is ever cut. ``invoke_coach`` does
        not run the model unless this section reaches it whole, and refuses a
        protected file whatever the reviewer decides.
        """
        round_ = getattr(self, "repair_round", None)
        if round_ is None or not review or review.get("unavailable"):
            return ""
        from guardkit.orchestrator.feature_check import cut_tail
        from guardkit.orchestrator.repair_round import GATE_OUTPUT_PROMPT_LIMIT

        limit = GATE_OUTPUT_PROMPT_LIMIT if gate_output_limit is None else gate_output_limit
        named = set(review.get("files_the_gate_names") or [])
        made = sorted(review.get("files_made_this_round") or [])
        changed = sorted(review.get("files_changed_this_round") or [])

        def _listed(paths: List[str]) -> List[str]:
            if not paths:
                return ["- (none)"]
            return [
                f"- `{path}`" + (" (the failing check's output names it)" if path in named else "")
                for path in paths
            ]

        lines = [
            "",
            f"## This is a repair round (round {round_.round_number})",
            "",
            "This task was approved, and a check that ran after it failed. The "
            "task was re-opened so the builder could make that check pass, and "
            "doing so can need files the task document does not name. In a "
            "repair round the plan audit does not refuse the turn for how many "
            "such files there are: you judge them.",
            "",
            "For each file listed below, decide whether it is needed to make the "
            "failing check pass. If any of them is unrelated product work, refuse "
            "the turn (feedback, must_fix) and name the file. A protected file "
            "(migrations, container, dependency, deploy and environment files) "
            "made, changed or deleted here is refused whatever you decide.",
            "",
            "Files this round made that the task document does not name:",
            *_listed(made),
            "",
            "Existing files this round changed or deleted that the task document does not name:",
            *_listed(changed),
            "",
            "The failing check's output, as the builder was given it (the end of it):",
            "~~~text",
            cut_tail(round_.gate_output or "", limit) or "(nothing)",
            "~~~",
            "",
        ]
        return "\n".join(lines)

    def _repair_round_sections(self, review: Optional[Dict[str, Any]]) -> Tuple[str, ...]:
        """The repair-round section as it may be sent: whole, then with only
        the gate's output cut shorter. ``()`` outside a repair round."""
        full = self._render_repair_round_section(review)
        if not full:
            return ()
        short = self._render_repair_round_section(
            review, gate_output_limit=self._REPAIR_SECTION_SHORT_GATE_OUTPUT
        )
        return (full,) if short == full else (full, short)

    def _repair_round_review(self, task_id: str) -> Optional[Dict[str, Any]]:
        """What this repair-round turn made, changed or deleted, from git.

        Runs on every repair-round turn before the Coach, whatever audit path
        the task takes (a task document with file sections, a player's note,
        or no declaration at all). Returns:

        * ``None`` only outside a repair round (no ``RepairRound`` on this
          invoker);
        * ``{"unavailable": reason}`` in a repair round whose facts cannot be
          established, whatever the cause - the round was unavailable at the
          re-open, the task's checkpoint record is missing or unreadable, the
          round is not in this task's history, git cannot answer, the
          protected paths cannot be listed or fingerprinted, or anything
          raised.
          ``_enforce_repair_round_protected`` then refuses the turn;
        * the review otherwise.

        Renames are a removed path and a new path. Never raises. Sets
        :attr:`repair_round_inventory` (the non-protected files listed) only
        for a complete review, for the orchestrator to carry if the reviewer
        approves.
        """
        self.repair_round_inventory = None
        round_ = getattr(self, "repair_round", None)
        if round_ is None:
            return None

        def _unavailable(reason: str) -> Dict[str, Any]:
            logger.warning(
                "[%s] The repair round's record of what changed could not be "
                "read (%s).", task_id, reason,
            )
            return {"unavailable": reason}

        if getattr(round_, "unavailable", None):
            return _unavailable(f"at the re-open: {round_.unavailable}")
        try:
            from guardkit.orchestrator.repair_round import (
                display_key,
                factory_owned_path,
                fingerprint_names,
                protected_files,
                protected_fingerprint_changes,
            )
            from guardkit.tasks.state_bridge import TaskStateBridge
            from installer.core.commands.lib.plan_audit import (
                PlanAuditor,
                _is_protected,
                _repair_round_protected,
            )

            declared = self._read_declared_file_sections(task_id)
            declared, _, _ = self._resolve_bare_declared_names(declared)
            declared_paths = set(declared.get("create") or []) | set(
                declared.get("modify") or []
            )
            induced = TaskStateBridge.orchestrator_induced_paths_for(
                task_id, repo_root=self.worktree_path
            )

            def _excluded(path: str) -> bool:
                return path in induced or _is_orchestrator_managed_path(
                    path, worktree_path=self.worktree_path
                )

            facts = PlanAuditor(
                workspace_root=self.worktree_path,
                path_exclusion=_excluded,
                repair_round=round_,
                task_work_scope=self.task_work_scope,
            )._repair_round_facts(task_id)
            if not facts:
                return _unavailable(
                    "no usable checkpoint record, the round is not in this "
                    "task's history, or git could not say what changed"
                )
            existed = set(facts.get("existed_at_round_start") or ())
            changed_this_round = list(facts.get("changed_this_round") or ())
            beyond = [p for p in changed_this_round if p not in declared_paths]
            # Every protected path, whatever git thinks of it (tracked,
            # untracked or ignored, file or symlink), compared by fingerprint
            # with what the re-open recorded: a write through a symlink or to
            # an ignored .env is seen. Raises if any read fails.
            current = protected_files(self.worktree_path)
            before = dict(round_.protected_fingerprints)
            fingerprint_touched = protected_fingerprint_changes(
                before.items(),
                {key: fingerprint for key, (_, fingerprint) in current.items()},
            )

            def _names(key: str) -> Set[str]:
                # The protected names the walk met for the record, at the
                # re-open and now: a deleted file keeps its baseline names.
                names: Set[str] = set(fingerprint_names(before.get(key, "")))
                names.update(current.get(key, ((), ""))[0])
                return names or {display_key(key)}

            def _named(key: str, names: Set[str]) -> str:
                shown = display_key(key)
                others = sorted(name for name in names if name != shown)
                return shown if not others else f"{shown} (as {', '.join(others)})"

            fingerprint_protected: Set[str] = set()
            for key in fingerprint_touched:
                names = _names(key)
                # Only the actual object path authorizes its change. Aliases
                # are incomplete diagnostic witnesses, never permission.
                actual = display_key(key)
                if actual in declared_paths:
                    continue
                # Collection has already applied package/cache exclusions.
                # The broad managed-path helper would hide protected aliases
                # into packages; only actual factory/induced records qualify.
                if actual in induced or factory_owned_path(actual):
                    continue
                fingerprint_protected.add(_named(key, names))
            protected = sorted(
                _repair_round_protected(changed_this_round, declared_paths)
                | fingerprint_protected
            )
            self.repair_round_inventory = frozenset(
                path for path in beyond if not _is_protected(path)
            )
            return {
                "round_number": facts.get("round_number"),
                "start_commit": facts.get("start_commit"),
                "files_the_gate_names": sorted(facts.get("implicated_paths") or []),
                "files_made_this_round": sorted(p for p in beyond if p not in existed),
                "files_changed_this_round": sorted(p for p in beyond if p in existed),
                "protected": protected,
            }
        except Exception as exc:  # noqa: BLE001 — becomes an explicit unavailable review
            self.repair_round_inventory = None
            return _unavailable(str(exc) or type(exc).__name__)

    def _review_repair_sent_for(
        self, task_id: str, turn: int
    ) -> Optional[List[Dict[str, Any]]]:
        """The findings this task's repair turn was given, or ``None`` when it
        has not had one (Codex review R2).

        This process's memory first; otherwise the task's own recorded
        reviews before ``turn``, so a resumed task (a new process) keeps its
        one repair turn used and its next review still checks those findings
        first.
        """
        from guardkit.orchestrator import build_review
        from guardkit.orchestrator.paths import TaskArtifactPaths

        sent: Dict[str, List[Dict[str, Any]]] = self.__dict__.setdefault(
            "_review_repair_sent", {}
        )
        if task_id in sent:
            return sent[task_id]
        recorded = build_review.repair_findings_sent(
            TaskArtifactPaths.task_private_dir(task_id, self.worktree_path), turn
        )
        if recorded is not None:
            sent[task_id] = recorded
        return recorded

    def _apply_review_repair_turn(
        self,
        *,
        decision: Dict[str, Any],
        reviewer_issues: List[Any],
        task_id: str,
        turn: int,
        turn_left: bool,
        coach_output_path: "Path",
    ) -> None:
        """The one repair turn for the reviewer's located findings, or what
        this review leaves for the merge card (the build reviewer design of
        29 October 2026).

        When no ordinary-code rule sent the turn back, the verdict has
        findings of the five kinds with a ``path:line`` place, the task has a
        turn left, this task has not had its repair turn, and
        ``GUARDKIT_REVIEW_REPAIR_TURN`` is not off: the turn goes back to the
        builder with ALL of those findings as its feedback, and the next
        review checks them first. Otherwise the review's findings (at most
        ten, advice included) are recorded as what it leaves
        (``review_leftovers``), for the feature's build review notes.
        Nothing is ever refused on a reviewer finding.
        """
        from guardkit.orchestrator import build_review

        sent: Dict[str, List[Dict[str, Any]]] = self.__dict__.setdefault(
            "_review_repair_sent", {}
        )
        located = build_review.located_findings(reviewer_issues)
        if (
            decision.get("decision") == "approve"
            and located
            and turn_left
            and self._review_repair_sent_for(task_id, turn) is None
            and build_review.repair_turn_enabled()
        ):
            sent[task_id] = located
            others = [i for i in decision.get("issues") or [] if i not in reviewer_issues]
            decision["issues"] = build_review.repair_issues(located) + others
            decision["decision"] = "feedback"
            decision[build_review.REPAIR_KEY] = True
            decision[build_review.LEFTOVERS_KEY] = []
            logger.info(
                "[%s] Turn %s: the reviewer found %d located finding(s); the "
                "builder gets one repair turn for them.",
                task_id, turn, len(located),
            )
        else:
            decision[build_review.LEFTOVERS_KEY] = build_review.leftovers(reviewer_issues)
        self._persist_coach_decision(
            decision, coach_output_path, tag="review-repair-turn", kind="annotated"
        )

    def _enforce_repair_round_protected(
        self,
        *,
        decision: Dict[str, Any],
        review: Optional[Dict[str, Any]],
        task_id: str,
        turn: int,
        coach_output_path: "Path",
    ) -> None:
        """Send back a repair-round turn that touched a protected file.

        Deterministic, and the last guard: an ``approve`` becomes
        ``feedback`` with a must_fix, and a ``feedback`` gains the same
        must_fix. Re-persisted to ``coach_turn_N.json``. Outside a repair
        round, or when the round's record of what changed could not be read,
        it does nothing.
        """
        if getattr(self, "repair_round", None) is None:
            return
        if review is None or review.get("unavailable"):
            return
        protected = list(review.get("protected") or [])
        if not protected:
            return
        category = "repair_round_protected"
        description = (
            f"This repair round made, changed or deleted {len(protected)} "
            "protected file(s) the task document does not name: "
            + ", ".join(protected)
            + ". A repair round never does; put them back as they were."
        )
        details: Dict[str, Any] = {"protected": protected}
        log_reason = "it touched protected file(s) " + ", ".join(protected)
        issue = {
            "severity": "must_fix",
            "category": category,
            "description": description,
            "details": details,
        }
        issues = decision.setdefault("issues", [])
        if not any(i.get("category") == category for i in issues if isinstance(i, dict)):
            issues.append(issue)
        if decision.get("decision") == "approve":
            logger.warning(
                "[%s] Turn %s: the reviewer approved, but this repair-round "
                "turn is refused: %s.",
                task_id, turn, log_reason,
            )
            decision["decision"] = "feedback"
            decision["rationale"] = description
        self._persist_coach_decision(
            decision, coach_output_path, tag="REPAIR-ROUND-GUARD"
        )

    # 18 October 2026: how much of one run's output (stdout and stderr
    # together) the whole-feature check section shows.
    _COACH_WHOLE_FEATURE_OUTPUT_LIMIT = 4000
    # The least room stderr keeps when it has output and stdout is long.
    _COACH_WHOLE_FEATURE_STDERR_FLOOR = 500

    @classmethod
    def _render_whole_feature_check_section(
        cls,
        evidence_bundle: Optional["CoachEvidenceBundle"],
    ) -> str:
        """Render ``## The project's whole-feature check``, or ``""``.

        Present only when the bundle carries ``whole_feature_check`` (a
        whole-feature repair round). It shows the declared command, and for
        this turn's run and the attempt that failed before: the outcome, the
        exit code and the end of the output, each run cut to 4,000
        characters. Nothing is parsed from the output. The instructions say
        the committed check decides the build and how to apply the
        request-first rule; the decision grammar is unchanged.
        """
        record = getattr(evidence_bundle, "whole_feature_check", None)
        if not isinstance(record, dict):
            return ""
        from guardkit.orchestrator.feature_check import cut_tail

        limit = cls._COACH_WHOLE_FEATURE_OUTPUT_LIMIT

        def _run_block(run: Dict[str, Any]) -> List[str]:
            stdout = str(run.get("stdout_tail") or "")
            stderr = str(run.get("stderr_tail") or "")
            # stdout first (coach review F2, 19 October 2026): a check's
            # failing lines are usually there, so a stdout that fits is kept
            # whole. stderr keeps a small floor when it has anything, and
            # otherwise only the room stdout left. The end of each stream is
            # kept when cut; together they never pass the limit.
            stderr_floor = min(len(stderr), cls._COACH_WHOLE_FEATURE_STDERR_FLOOR)
            stdout = cut_tail(stdout, limit - stderr_floor) if stdout else ""
            stderr = cut_tail(stderr, limit - len(stdout)) if stderr else ""
            exit_code = run.get("exit_code")
            outcome = run.get("outcome") or "unknown"
            lines = [
                f"- outcome: {outcome}",
                f"- exit code: {exit_code if exit_code is not None else 'none'}"
                + (" (timed out)" if run.get("timed_out") else ""),
                "- standard output (the end of it):",
                "~~~text",
                stdout or "(nothing)",
                "~~~",
                "- standard error (the end of it):",
                "~~~text",
                stderr or "(nothing)",
                "~~~",
            ]
            return lines

        previous = record.get("previous_failed_attempt")
        previous = previous if isinstance(previous, dict) else {}
        command = record.get("command") or previous.get("command") or "(not recorded)"
        lines: List[str] = [
            "",
            "## The project's whole-feature check",
            "",
            f"The project committed this check for the finished feature: `{command}`.",
            "It decides whether the build is accepted, whatever the task's own "
            "test command covers. Never call its failure out of scope, and never "
            "dismiss it as not run by the task's own test command.",
            "",
            "Below is what it printed on this turn's code and on the code that "
            "failed before.",
            "",
            "If a plan criterion and this check cannot both hold, do not send the "
            "Player to break the check. Reject that criterion, with notes that "
            "name the check's failing lines, and say in the rationale that the "
            "plan contradicts the project's check.",
            "",
            "The request decides which one should change. If the request asked "
            "for the criterion's behaviour, the check has to change. If it did "
            "not, the criterion should go. You do not approve a plan criterion "
            "away: only a person or the planner can drop it.",
            "",
            "### On this turn's code",
            "",
        ]
        if record.get("ran") is True:
            lines.extend(_run_block(record))
        else:
            reason = record.get("skipped_reason") or "not recorded"
            lines.append(
                f"- not run on this turn's code ({reason}). Nothing is known "
                "about this turn from the check; do not read its absence as "
                "a pass or a failure."
            )
        lines.extend(["", "### On the code that failed before", ""])
        if previous:
            lines.extend(_run_block(previous))
        else:
            lines.append("- not recorded")
        request_words = str(record.get("request_words") or "").strip()
        if request_words:
            lines.extend(["", "### The words of the request", "", request_words])
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # TASK-HMIG-008R Part C — Coach prompt rendering helpers.
    # ------------------------------------------------------------------

    # TASK-PERF-COACHSYNTH (AC-4 / Lever C): cap the look-up findings text
    # rendered into the verdict prompt. The look-up pass is bounded at the
    # source (the tool limit and the per-tool-result cut), but the text the
    # model writes can still be large. Truncation is MARKED, never silent.
    # ~16 k chars ≈ ~4 k tokens of findings.
    _COACH_GATHER_FINDINGS_LIMIT_CHARS = int(
        os.environ.get("GUARDKIT_COACH_GATHER_FINDINGS_LIMIT_CHARS", "16000")
    )

    @classmethod
    def _truncate_gather_findings(cls, findings: str) -> str:
        """Cap findings at the char budget with a visible truncation marker."""
        limit = cls._COACH_GATHER_FINDINGS_LIMIT_CHARS
        if limit <= 0 or len(findings) <= limit:
            return findings
        elided = len(findings) - limit
        return (
            findings[:limit]
            + f"\n\n... [look-up findings cut here: {elided} more characters "
            f"were not included.] ..."
        )

    # TASK-SELFFIX-003: overall synthesis-prompt budget.
    # The per-tool-result gather cap (GUARDKIT_COACH_GATHER_MAX_TOOL_RESULT_CHARS)
    # bounds individual tool results, but nothing bounded the RENDERED synthesis
    # prompt itself. Task-work coach bundles reached 109,634 tokens and overflowed
    # the crash-tested 98,304 window. This budget enforces a hard ceiling on the
    # full rendered prompt.
    #
    # Evidence — a real task, filed in ANOTHER repository.
    # The overflow was measured on an autobuild run in the *api_test*
    # repository on 2026-07-25: feature FEAT-8737, task SMOKE-002, turn 1.
    # The coach call came back HTTP 400 carrying ``n_prompt_tokens: 109634``.
    #
    # That task exists and is filed: api_test holds it under
    # ``tasks/design_approved/`` as the SMOKE-002 record
    # (``...-add-seed-template-and-stdlib-probe.md``). It is simply filed
    # THERE and not here. The reference is written without its ``TASK-``
    # prefix on purpose: the dead-task-id lint
    # (tests/rules/test_no_dead_task_id_references.py) resolves every such
    # prefix against *this* repository's ``tasks/`` alone, and has no way to
    # express a cross-repo citation — so spelling the prefix here would
    # assert a local record that does not exist. That is a limitation of the
    # lint, not a defect in the evidence. The prefix is the only thing
    # dropped; every measurement below is unchanged.
    #
    # Investigation note — fields dominating the oversized bundle shape:
    # Analysis of that 109,634-token receipt identified the following as the
    # primary contributors to the oversized bundle size:
    #   1. ``completion_promises`` in the player report JSON — a large array
    #      of per-AC verification objects (each with criterion_text, evidence,
    #      implementation_files) can easily exceed 50k chars with 200+ items.
    #   2. ``raw_output`` and ``output_tail`` in the evidence bundle — the
    #      untrimmed test runner output and BDD runner output can each carry
    #      tens of thousands of characters of raw terminal output.
    #   3. ``discoveries`` and ``errors`` lists in the BDD section — when
    #      many scenarios run, these arrays add significant JSON overhead.
    # The trimming strategy in _trim_synthesis_prompt targets these fields
    # first (player report JSON, then evidence bundle string values) before
    # resorting to aggressive bundle truncation.
    _COACH_SYNTHESIS_MAX_CHARS = int(
        os.environ.get("GUARDKIT_COACH_SYNTHESIS_MAX_CHARS", "300000")
    )

    # Fields that carry verdict-bearing content — NEVER trimmed.
    _VERDICT_BEARING_MARKERS = (
        "## Original Requirements",
        "## Acceptance Criteria to Verify",
        "stub_scan",
        "behavioural_oracle",
        "<evidence_bundle>",
        "## Deterministic Evidence Bundle",
    )

    # Stands in for the protected repair-round sections while the rest of the
    # prompt is trimmed, so no trimming step can see, search or cut them.
    _PROTECTED_SECTION_PLACEHOLDER = "\x00[guardkit: protected section]\x00"

    @classmethod
    def _trim_synthesis_prompt(cls, prompt: str, protected_section: str = "") -> str:
        """Enforce the synthesis-prompt budget, never touching ``protected_section``.

        ``protected_section`` is a repair round's whole-feature check and file
        sections. While the rest of the prompt is trimmed it is replaced by a
        short placeholder, with the budget reduced by its length, so no step,
        including the last-resort tail cut, can cut inside it. It is then put
        back unchanged. If the placeholder itself does not survive (only
        possible when the head of the prompt alone overflows), the section is
        absent.
        """
        budget = cls._COACH_SYNTHESIS_MAX_CHARS
        if not protected_section or protected_section not in prompt:
            return cls._trim_synthesis_prompt_within(prompt, budget)
        if len(prompt) <= budget:
            return prompt
        placeholder = cls._PROTECTED_SECTION_PLACEHOLDER
        head, _, tail = prompt.partition(protected_section)
        remaining = budget - len(protected_section) + len(placeholder)
        if remaining <= len(placeholder):
            # No room for anything but the documents: trim without them, so
            # the caller sees the section missing and refuses the turn.
            return cls._trim_synthesis_prompt_within(head + tail, budget)
        trimmed = cls._trim_synthesis_prompt_within(head + placeholder + tail, remaining)
        if placeholder not in trimmed:
            return trimmed
        return trimmed.replace(placeholder, protected_section, 1)

    @classmethod
    def _trim_synthesis_prompt_within(cls, prompt: str, budget: int) -> str:
        """Enforce the overall synthesis-prompt character budget.

        When ``synthesis=True`` the Coach receives the full rendered prompt
        (requirements, acceptance criteria, player report, evidence bundle,
        etc.), which can exceed the model's crash-tested window.

        This method enforces a hard ceiling of ``budget`` characters
        (``GUARDKIT_COACH_SYNTHESIS_MAX_CHARS``, default 300,000 chars ≈ 85k
        tokens, less any protected section ``_trim_synthesis_prompt`` set
        aside). If the prompt is within budget it returns unchanged. If it
        exceeds the budget it trims low-signal content first — raw output
        tails, large JSON sections — and NEVER the verdict-bearing fields
        (requirements, acceptance criteria, honesty, stub_scan,
        behavioural_oracle).

        Truncation is **loud**: a visible notice is inserted inside the
        prompt naming what was cut and by how much, and a WARNING is logged.

        Parameters
        ----------
        prompt : str
            The fully-rendered synthesis prompt string.
        budget : int
            The character ceiling for ``prompt``.

        Returns
        -------
        str
            The prompt, trimmed to budget if necessary.
        """
        prompt_len = len(prompt)

        if prompt_len <= budget:
            return prompt

        # We need to trim. Strategy: identify low-signal sections and shrink
        # them, preserving all verdict-bearing content.
        trimmed = prompt
        total_elided = 0

        # --- 1. Trim player_report JSON (can be very large with completion_promises) ---
        # Look for the player_report JSON section and truncate it if oversized.
        # The player report is rendered as ``json.dumps(player_report, indent=2)``
        # between "## Player's Report" and the next section header.
        player_report_marker = "## Player's Report"
        player_start = trimmed.find(player_report_marker)
        if player_start != -1:
            # Find the next section header after player report
            rest = trimmed[player_start + len(player_report_marker):]
            next_section = rest.find("\n## ")
            if next_section == -1:
                # Player report is the last section before responsibilities
                next_section = rest.find("\n## Decision Format")
            if next_section != -1:
                player_section_start = player_start + len(player_report_marker)
                player_section_end = player_start + len(player_report_marker) + next_section
                player_section = trimmed[player_section_start:player_section_end]

                # Try to extract and shrink the JSON portion
                json_start = player_section.find("{")
                if json_start != -1:
                    # Count the JSON chars
                    json_len = len(player_section) - json_start
                    if json_len > 50000:  # If player report JSON is > 50k chars, trim it
                        # Keep the first 5000 chars of JSON and elide the rest
                        keep = 5000
                        elided = json_len - keep
                        total_elided += elided
                        trimmed = (
                            trimmed[:player_section_start + json_start]
                            + player_section[json_start:json_start + keep]
                            + "\n  ... [player_report truncated: "
                            f"{elided} chars elided from completion_promises and file lists. "
                            "Full report available in player_turn_N.json.] ..."
                            + trimmed[player_section_end:]
                        )

        # --- 2. Trim evidence_bundle JSON sections (large findings lists) ---
        # The evidence bundle is rendered as JSON inside <evidence_bundle> tags.
        # We look for large string values (raw_output, output_tail, test_output_summary)
        # and truncate them.
        bundle_start = trimmed.find("<evidence_bundle>")
        bundle_end = trimmed.find("</evidence_bundle>")
        if bundle_start != -1 and bundle_end != -1:
            bundle_content_start = bundle_start + len("<evidence_bundle>")
            bundle_content_end = bundle_end
            bundle_inner = trimmed[bundle_content_start:bundle_content_end]

            # Truncate large string values in the JSON bundle
            # Look for raw_output, output_tail, test_output_summary fields
            for field_name in ("raw_output", "output_tail", "test_output_summary"):
                # Find all occurrences of this field in the JSON
                search_start = 0
                while True:
                    pattern = f'"{field_name}": "'
                    idx = bundle_inner.find(pattern, search_start)
                    if idx == -1:
                        break
                    # Find the end of this string value
                    value_start = idx + len(pattern)
                    # Find the closing quote (handling escaped quotes)
                    j = value_start
                    while j < len(bundle_inner):
                        if bundle_inner[j] == '\\' and j + 1 < len(bundle_inner):
                            j += 2  # Skip escaped character
                            continue
                        if bundle_inner[j] == '"':
                            break
                        j += 1
                    value_end = j
                    value = bundle_inner[value_start:value_end]

                    if len(value) > 5000:  # Truncate if > 5k chars
                        elided = len(value) - 5000
                        total_elided += elided
                        replacement = value[:5000]
                        trimmed = (
                            trimmed[:bundle_content_start + idx + len(pattern)]
                            + replacement
                            + "... [truncated: "
                            f"{elided} chars elided from {field_name}]"
                            + trimmed[bundle_content_start + value_end:]
                        )
                        # Update bundle_inner after modification
                        bundle_inner = trimmed[bundle_content_start:bundle_end]
                    search_start = value_end

        # --- 3. Trim gather_findings if present and oversized ---
        findings_marker = "## Look-up findings"
        findings_start = trimmed.find(findings_marker)
        if findings_start != -1:
            rest = trimmed[findings_start + len(findings_marker):]
            next_section = rest.find("\n## ")
            if next_section != -1:
                findings_section_start = findings_start + len(findings_marker)
                findings_section_end = findings_start + len(findings_marker) + next_section
                findings_text = trimmed[findings_section_start:findings_section_end]
                if len(findings_text) > 20000:
                    elided = len(findings_text) - 20000
                    total_elided += elided
                    trimmed = (
                        trimmed[:findings_section_start]
                        + findings_text[:20000]
                        + "\n\n... [investigation findings truncated: "
                        f"{elided} more chars elided.] ..."
                        + trimmed[findings_section_end:]
                    )

        # --- 4. If still over budget, trim the evidence bundle further ---
        # This is the last resort: truncate the bundle JSON more aggressively
        if len(trimmed) > budget:
            bundle_start = trimmed.find("<evidence_bundle>")
            bundle_end = trimmed.find("</evidence_bundle>")
            if bundle_start != -1 and bundle_end != -1:
                bundle_content_start = bundle_start + len("<evidence_bundle>")
                bundle_content_end = bundle_end
                bundle_inner = trimmed[bundle_content_start:bundle_content_end]

                # Truncate any string value > 2000 chars
                for field_name in ("output_tail", "test_output_summary", "stderr_tail",
                                   "raw_output_excerpt", "output", "notes", "description"):
                    search_start = 0
                    while True:
                        pattern = f'"{field_name}": "'
                        idx = bundle_inner.find(pattern, search_start)
                        if idx == -1:
                            break
                        value_start = idx + len(pattern)
                        j = value_start
                        while j < len(bundle_inner):
                            if bundle_inner[j] == '\\' and j + 1 < len(bundle_inner):
                                j += 2
                                continue
                            if bundle_inner[j] == '"':
                                break
                            j += 1
                        value_end = j
                        value = bundle_inner[value_start:value_end]

                        if len(value) > 2000:
                            elided = len(value) - 2000
                            total_elided += elided
                            replacement = value[:2000]
                            trimmed = (
                                trimmed[:bundle_content_start + idx + len(pattern)]
                                + replacement
                                + "... [truncated: "
                                f"{elided} chars elided from {field_name}]"
                                + trimmed[bundle_content_start + value_end:]
                            )
                            bundle_inner = trimmed[bundle_content_start:bundle_end]
                        search_start = value_end

        # --- 5. If STILL over budget after all trimming, truncate the bundle JSON ---
        if len(trimmed) > budget:
            bundle_start = trimmed.find("<evidence_bundle>")
            bundle_end = trimmed.find("</evidence_bundle>")
            if bundle_start != -1 and bundle_end != -1:
                bundle_content_start = bundle_start + len("<evidence_bundle>")
                bundle_content_end = bundle_end
                bundle_inner = trimmed[bundle_content_start:bundle_content_end]

                # Calculate how much we need to trim
                current_len = len(trimmed)
                excess = current_len - budget
                # Keep 80% of the bundle content
                keep = int(len(bundle_inner) * 0.8)
                elided = len(bundle_inner) - keep
                total_elided += elided

                trimmed = (
                    trimmed[:bundle_content_start]
                    + bundle_inner[:keep]
                    + "\n\n... [evidence_bundle truncated: "
                    f"{elided} chars elided from bundle JSON to fit synthesis-prompt budget. "
                    "Verdict-bearing fields (requirements, acceptance criteria, honesty, "
                    "stub_scan, behavioural_oracle) were preserved. Full bundle available "
                    "in coach_turn_N.json.] ..."
                    + trimmed[bundle_content_end:]
                )

        # --- 6. Final safety: if still over, truncate from the end (least critical) ---
        if len(trimmed) > budget:
            excess = len(trimmed) - budget
            total_elided += excess
            notice = (
                f"\n\n... [prompt truncated at {budget}-character budget: "
                f"{excess} additional chars removed from end. "
                "Verdict-bearing fields were preserved. Full prompt context "
                "available in coach_turn_N.json and coach_evidence.] ..."
            )
            # Reserve space for the notice so final length <= budget
            trimmed = trimmed[:budget - len(notice)] + notice

        # --- Log the truncation ---
        if total_elided > 0:
            logger.warning(
                "TASK-SELFFIX-003: synthesis prompt trimmed from %d to %d chars "
                "(budget: %d). Total elided: %d chars. "
                "Truncation is loud: a visible notice was inserted into the prompt.",
                prompt_len,
                len(trimmed),
                budget,
                total_elided,
            )

        return trimmed

    def _render_evidence_bundle_section(
        self,
        evidence_bundle: "CoachEvidenceBundle",
    ) -> str:
        """Render the CoachEvidenceBundle as a structured prompt section.

        Emits the bundle as JSON inside ``<evidence_bundle>...</evidence_bundle>``
        XML-like tags. The run records (source manifests, environment
        inventory) stay in ``coach_evidence_turn_N.json`` and are kept out of
        the prompt.
        """
        try:
            bundle_dict = evidence_bundle.to_dict()
        except Exception as exc:  # noqa: BLE001 — never block prompt build
            logger.error(
                "Failed to serialise evidence_bundle for Coach prompt: %s.", exc,
            )
            bundle_dict = {
                "gathering_status": "partial_exception",
                "gathering_error": f"bundle_serialisation_failed: {exc}",
            }

        for leg_for_prompt in ("independent_tests", "behavioural_oracle"):
            leg = bundle_dict.get(leg_for_prompt)
            if isinstance(leg, dict):
                leg.pop("run_evidence", None)

        # The whole-feature check (repair rounds only) has its own protected
        # section in the prompt; it is not repeated inside this JSON.
        bundle_dict.pop("whole_feature_check", None)

        try:
            payload = json.dumps(bundle_dict, indent=2, default=str)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to JSON-encode evidence_bundle: %s", exc,
            )
            payload = '{"gathering_status": "partial_exception", "gathering_error": "json_encode_failed"}'

        return f"""
## Deterministic Evidence Bundle

<evidence_bundle>
{payload}
</evidence_bundle>
"""

    def _bump_activity(self) -> None:
        """Refresh the no-model-activity clock from a substrate callback.

        TASK-FIX-SPECINVOKE01. Threaded into the LangGraph harness as
        ``on_model_activity`` so each real LLM/tool boundary refreshes the
        same ``_last_activity_monotonic`` the specialist watchdog polls. The
        consumer loop in :meth:`_invoke_with_role` only updates that clock when
        a :class:`HarnessEvent` is *yielded*, but the LangGraph harness awaits
        the whole ``agent.ainvoke()`` before yielding any event — so without
        this callback the clock froze for the entire run and the watchdog
        false-killed a live, model-active specialist at 150 s (FEAT-9DDE
        run 3). Synchronous and trivial: a single atomic attribute store on the
        event-loop thread, safe against the sibling watchdog task's read.
        """
        self._last_activity_monotonic = time.monotonic()

    def pin_language_servers(
        self, task_id: str, language_servers: Optional[List[Any]]
    ) -> None:
        """Keep a fresh task's pinned ``language_servers`` in memory: they
        are what the builder's ``code_references`` uses."""
        if not hasattr(self, "_pinned_language_servers"):
            self._pinned_language_servers = {}
        self._pinned_language_servers[task_id] = list(language_servers or []) or None

    def _builder_language_servers(
        self, task_id: Optional[str]
    ) -> Optional[List[Dict[str, Any]]]:
        """The ``toolchain.language_servers`` entries for this task's builder.

        A fresh task: the list AutoBuild kept in memory. A resumed task has
        none in memory, so the snapshot file's list (the builder's own server
        can do nothing its shell cannot). ``None`` means no
        ``code_references``. The reviewer's are
        :meth:`_reviewer_language_servers`.
        """
        if task_id is None:
            return None
        pinned: Dict[str, Optional[List[Any]]] = getattr(
            self, "_pinned_language_servers", {}
        )
        if task_id in pinned:
            servers = pinned[task_id]
        else:
            from guardkit.orchestrator.toolchain_declaration import (
                load_toolchain_snapshot,
            )

            snapshot = load_toolchain_snapshot(task_id, self.worktree_path)
            servers = snapshot.language_servers if snapshot is not None else None
        if not servers:
            return None
        return [
            server.model_dump(mode="json", exclude_none=True)
            if hasattr(server, "model_dump") else dict(server)
            for server in servers
        ]

    def _reviewer_language_servers(
        self, task_id: Optional[str]
    ) -> Optional[List[Dict[str, Any]]]:
        """The ``toolchain.language_servers`` entries for the review's look-up pass.

        The build reviewer design of 29 October 2026: only the list AutoBuild
        kept in memory before the builder's first turn, never the snapshot
        file (it sits where the builder's shell can write). A resumed task has
        no list in memory, so its reviewer gets no ``code_references`` and
        uses the literal search. ``None`` means no ``code_references``.
        """
        if task_id is None:
            return None
        pinned: Dict[str, Optional[List[Any]]] = getattr(
            self, "_pinned_language_servers", {}
        )
        servers = pinned.get(task_id)
        if not servers:
            return None
        return [
            server.model_dump(mode="json", exclude_none=True)
            if hasattr(server, "model_dump") else dict(server)
            for server in servers
        ]

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
        recursion_limit: Optional[int] = None,
        max_tool_result_chars: Optional[int] = None,
        event_role: Optional[str] = None,
        event_agent_name: Optional[str] = None,
        tool_counter: Optional[ToolCallCounter] = None,
        shell_role: Optional[str] = None,
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
            recursion_limit: TASK-PERF-COACHSYNTH. Optional hard ceiling on
                the LangGraph/DeepAgents super-step count for this single
                invocation. ``None`` preserves the substrate default (25 on
                LangGraph; ``max_turns`` governs the SDK). A specialist may
                pass one; the review's look-up pass does not (its bound is the
                shared tool limit, which ends with an answer). Dropped on the
                SDK path (which bounds cycles via ``max_turns``).
            max_tool_result_chars: TASK-PERF-COACHSYNTH. Optional per-tool-
                result truncation budget forwarded to
                ``build_autobuild_backend``. ``None`` leaves tool results
                uncapped (Player/synthesis behaviour). The review's look-up
                pass passes a limit so a single ``read``/``grep`` cannot dump
                an unbounded payload into the running context. LangGraph-only.
            event_role: The role written on the ``llm.call`` event, when it
                is not the permission role ``agent_type`` (13 October 2026:
                :func:`run_specialist` passes ``"specialist"``, because the
                code reviewer runs with the Coach's permissions but is not
                the Coach). Defaults to ``agent_type``.
            event_agent_name: The agent's name for that event (the
                specialist's name). ``None`` by default.
            tool_counter: Optional :class:`ToolCallCounter` (13 October 2026,
                the code reviewer's record). On LangGraph it is hung on the
                native tool hook, alongside the debug copy when that is on;
                on the SDK harness it counts the stream's tool events. It
                keeps tool names only. ``None`` (the default) changes nothing.
            shell_role: 19 October 2026. The shell's role when it is not the
                one ``agent_type`` implies (``select_harness``'s
                ``shell_role``): :func:`run_specialist` passes
                ``"specialist"`` so a specialist running with the Player's or
                the Coach's permissions gets the specialists' own home and
                temporary folders. ``None`` (the default) changes nothing.

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

        # TASK-OBS-9F43 AC-3: Track current agent role and attempt for tool.exec events
        # Set at each _invoke_with_role entry so tool executions emit the correct agent_role and attempt
        self._current_agent_role = agent_type
        self._current_attempt = turn if turn is not None else 1

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
            preserve_event_checked as _sdk_preserve_event_checked,
        )
        from guardkit.orchestrator.head_identity import observe_invocation
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
                # TASK-PERF-COACHSYNTH: gather-bound knobs. Both default None
                # (unbounded / substrate-default) and are popped by
                # select_harness before the SDK harness sees them; only the
                # LangGraph branch honours them. The review's look-up pass
                # sets the tool-result cut.
                recursion_limit=recursion_limit,
                max_tool_result_chars=max_tool_result_chars,
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
                # TASK-FIX-SPECINVOKE01: substrate-aware activity signal.
                # LangGraph-only (popped before the SDK harness sees it). The
                # harness pings this on every LLM/tool boundary so the
                # specialist no-model-activity watchdog measures real model
                # progress rather than this harness's await-then-yield event
                # cadence (which froze ``_last_activity_monotonic`` and
                # false-killed live specialists at 150 s — FEAT-9DDE run 3).
                on_model_activity=self._bump_activity,
                on_native_tool_event=_native_tool_sink(
                    _sdk_debug_dir, _sdk_preserve_event_checked, tool_counter
                ),
                harness_role=agent_type,
                # The task's pinned `launch:` settings and scratch folders for
                # the shell (LangGraph only). None without a task or a block.
                launch_declaration=load_launch_snapshot(task_id, self.worktree_path),
                # 29 October 2026: the code_references settings (LangGraph
                # only): the builder's, and the review look-up pass's (the
                # build reviewer design: in-memory only); none for the
                # verdict call or a specialist.
                language_servers=(
                    self._builder_language_servers(task_id)
                    if agent_type == "player" and shell_role is None
                    else self._reviewer_language_servers(task_id)
                    if agent_type == "coach" and shell_role is None
                    and allowed_tools and not synthesis
                    else None
                ),
                # 19 October 2026: only when a caller names one (a specialist).
                **({"shell_role": shell_role} if shell_role is not None else {}),
            )

            if tool_counter is not None:
                # Only names of tools this harness actually binds are kept in
                # the count; anything the model invents counts as "other".
                tool_counter.bind(
                    _bound_tool_names(harness, allowed_tools, agent_type)
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
                                # 12 October 2026 (build 0D7C): HEAD and its
                                # branch are recorded before and after, with
                                # the invocations that overlapped. Evidence
                                # only; the stream passes through unchanged.
                                async with aclosing(
                                    observe_invocation(
                                        _harness_call,
                                        self.worktree_path,
                                        role=(
                                            heartbeat_label_override
                                            or agent_type
                                        ).removesuffix(" invocation"),
                                        task_id=_debug_task_id,
                                        turn=turn,
                                    )
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
                                        # TASK-FIX-COACHTRES01: exclude BOTH typed
                                        # tool events from response_messages. They
                                        # carry no SDK ``raw`` object (raw=None) and
                                        # are consumed as typed events elsewhere —
                                        # appending the bare event would mix typed
                                        # events with SDK objects in this List[Any]
                                        # (the same reasoning that already excluded
                                        # ToolUseEvent). ToolResultEvent is new to
                                        # the Player stream as of the capture fix.
                                        if not isinstance(event, (ToolUseEvent, ToolResultEvent)):
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
                                            if tool_counter is not None:
                                                tool_counter.record_streamed(
                                                    getattr(event, "name", None)
                                                )

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
                        if not isinstance(exc, asyncio.CancelledError):
                            # Retain a returned failed graph before the outer
                            # handler wraps it. Diagnostics never feed events
                            # or recovery reports and cannot mask this error.
                            try:
                                from guardkit.orchestrator.sdk_debug import preserve_failure
                                preserve_failure(_sdk_debug_dir, exc)
                            except Exception:
                                logger.warning("Failed graph debug preservation unavailable")
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
                    agent_type=event_role or agent_type,
                    model=model,
                    latency_ms=latency.ms,
                    response_messages=response_messages,
                    status=call_status,
                    error=call_error,
                    task_id=heartbeat_task_id,
                    agent_name=event_agent_name,
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

    def _extract_server_resolved_model(self, response_messages: List[Any]) -> Optional[str]:
        """Extract server-resolved model from SDK response messages.

        TASK-OBS-9F43: Prefer server-resolved model over literal "default" fallback.

        Args:
            response_messages: Raw SDK response messages (AssistantMessage, ResultMessage, etc.)

        Returns:
            Server-resolved model name if available, else None.

        Priority:
            1. AssistantMessage.model (SDK harness)
            2. First key in ResultMessage.model_usage (both harnesses)
            3. A LangChain message's ``response_metadata`` (``model_name`` or
               ``model``), the name the model server put in its reply: the
               LangGraph harness hands back a graph state
               (``{"messages": [...]}``) or a single message (20 October
               2026). The last message that names one wins.
        """
        for msg in response_messages:
            reported = self._langchain_reported_model(msg)
            if reported:
                return reported
            # 20 October 2026 (review round 1): the Claude SDK's own
            # AssistantMessage and ResultMessage dataclasses carry no
            # ``.type``, so the class is recognised by name as well. A
            # ``.type`` of "assistant" / "result" is still accepted for the
            # objects that do carry one.
            kind = type(msg).__name__
            msg_type = getattr(msg, "type", None)

            # Try AssistantMessage.model (SDK harness)
            if kind == "AssistantMessage" or msg_type == "assistant":
                model_val = getattr(msg, "model", None)
                if model_val and isinstance(model_val, str):
                    return model_val

            # Try ResultMessage.model_usage (keyed by model name)
            if kind == "ResultMessage" or msg_type == "result":
                model_usage = getattr(msg, "model_usage", None)
                if model_usage and isinstance(model_usage, dict) and len(model_usage) > 0:
                    # Return first key (model name)
                    first = next(iter(model_usage.keys()))
                    if isinstance(first, str) and first:
                        return first

        return None

    @staticmethod
    def _langchain_reported_model(msg: Any) -> Optional[str]:
        """The model a LangChain reply (or graph state) says answered, or None.

        Reads ``response_metadata["model_name"]`` / ``["model"]``, which
        LangChain's chat clients fill from the server's own reply. A graph
        state dict is searched from its last message back.
        """

        def _named(item: Any) -> Optional[str]:
            metadata = getattr(item, "response_metadata", None)
            if not isinstance(metadata, dict):
                return None
            for key in ("model_name", "model"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return None

        if isinstance(msg, dict):
            messages = msg.get("messages")
            if isinstance(messages, list):
                for item in reversed(messages):
                    named = _named(item)
                    if named:
                        return named
            return None
        return _named(msg)

    def _emit_llm_call_event(
        self,
        agent_type: str,
        model: Optional[str],
        latency_ms: float,
        response_messages: List[Any],
        status: str,
        error: Optional[Exception],
        task_id: str,
        agent_name: Optional[str] = None,
    ) -> None:
        """Construct and fire-and-forget an LLMCallEvent.

        Emission is non-blocking via asyncio.create_task(). If the emitter
        raises, the error is logged as a warning but never propagated to
        the caller. (TASK-INST-005b)

        Args:
            agent_type: Role written on the event ("player", "coach" or
                "specialist").
            model: Model identifier or None for CLI default.
            latency_ms: Wall-clock latency of the SDK call in milliseconds.
            response_messages: SDK response messages (for token extraction).
            status: "ok" or "error".
            error: The exception if status is "error", else None.
            task_id: Task identifier extracted from prompt.
            agent_name: Optional agent name (a specialist's name).
        """
        try:
            input_tokens, output_tokens = extract_token_usage(response_messages)

            # Read prompt_profile from instance or use Phase 1 baseline default
            prompt_profile = getattr(self, "_prompt_profile", None) or "digest+rules_bundle"

            # Read run_id from instance or generate a session-level default
            run_id = getattr(self, "_run_id", None) or f"run-{id(self)}"

            # Read current attempt from instance or default to 1
            attempt = getattr(self, "_current_attempt", None) or 1

            # 20 October 2026: record where the call went and the model that
            # answered, never a client default. Until then the configured
            # model name won and the provider was read from
            # ANTHROPIC_BASE_URL alone, so a factory turn (an OpenAI-
            # compatible client on a local model seat, asked for the CLI's
            # default model name) was recorded as an Anthropic call to that
            # Anthropic model. Now:
            # * provider: the route the harness really took (seat_for_record);
            # * model: the name the server reported when it reported one;
            #   else the requested name when a vendor's own API served it
            #   (that API serves exactly the model named); else "unknown";
            # * requested_model: the name GuardKit asked for, as sent.
            from guardkit.orchestrator.harness.selector import seat_for_record

            seat = seat_for_record(model)
            server_model = self._extract_server_resolved_model(response_messages)
            if server_model:
                resolved_model = server_model
            elif seat.requested_model and seat.provider in ("anthropic", "openai"):
                prefix, sep, bare = seat.requested_model.partition(":")
                resolved_model = (
                    bare if sep and prefix.strip().lower() == seat.provider
                    else seat.requested_model
                )
            else:
                resolved_model = "unknown"

            event = LLMCallEvent(
                run_id=run_id,
                task_id=task_id,
                agent_role=agent_type,
                attempt=attempt,
                timestamp=datetime.now().isoformat(),
                provider=seat.provider,
                model=resolved_model,
                requested_model=seat.requested_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                prompt_profile=prompt_profile,
                status=status,
                error_type=classify_error(error),
                agent_name=agent_name,
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
            "sdk_ceiling_hit": None,
        }

        # 13 October 2026: where the listed paths came from, read from the
        # results file (see ``_set_aside_written_then_removed``). Absent in an
        # older record, which then sets nothing aside.
        confirmed_write_paths: List[str] = []
        named_in_words_paths: List[str] = []
        unconfirmed_write_paths: List[str] = []

        # Try to read task_work_results.json for richer data
        if task_work_results_path.exists():
            try:
                with open(task_work_results_path, "r") as f:
                    task_work_data = json.load(f)

                confirmed_write_paths = list(
                    task_work_data.get("confirmed_write_paths") or []
                )
                named_in_words_paths = list(
                    task_work_data.get("named_in_words_paths") or []
                )
                unconfirmed_write_paths = list(
                    task_work_data.get("unconfirmed_write_paths") or []
                )

                # Map task-work fields to Player report fields
                report["files_modified"] = self._file_claims(task_work_data, "modified")
                report["files_created"] = self._file_claims(task_work_data, "created")
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
                    report["sdk_ceiling_hit"] = sdk_turns.get("ceiling_hit")
                runtime_evidence = task_work_data.get("runtime_evidence")
                if isinstance(runtime_evidence, dict):
                    # Preserve the bounded artifact object byte-for-byte in the report.
                    report["runtime_evidence"] = runtime_evidence

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

                report["claimed_files_modified"] = sorted(original_modified)
                report["claimed_files_created"] = sorted(original_created)
                report["files_modified"] = sorted(git_modified)
                report["files_created"] = sorted(git_created)
                report["scope_id"] = git_changes["scope_id"]
                report["baseline_commit"] = git_changes["baseline_commit"]

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
                report["claimed_files_modified"] = sorted(list(set(report.get("claimed_files_modified", [])) | set(self._file_claims(output, "modified"))))
            if "files_created" in output:
                existing = set(report.get("files_created", []))
                report["claimed_files_created"] = sorted(list(set(report.get("claimed_files_created", [])) | set(self._file_claims(output, "created"))))
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
        # (``<worktree>/FEAT-X/.guardkit/autobuild/<TASK_ID>/...``). The
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

        # 13 October 2026: a scratch file the builder wrote (confirmed by its
        # own successful result), never named, and then removed again is not
        # a claim. Every check runs here, once, after every list above has
        # been assembled; see ``_set_aside_written_then_removed``.
        written_then_removed = self._set_aside_written_then_removed(
            report,
            confirmed_write_paths,
            named_in_words_paths,
            unconfirmed_write_paths,
        )
        report["files_written_then_removed"] = written_then_removed
        if written_then_removed:
            logger.info(
                f"Set aside {len(written_then_removed)} file(s) {task_id} wrote "
                f"and removed again without naming them: {written_then_removed}"
            )

        self._apply_scope_inventory(report)
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

                # Carry the filtered claims as well as the observed inventory
                # through the report -> Coach results rewrite.
                for key in ("claimed_files_created", "claimed_files_modified"):
                    task_work_data[key] = list(report.get(key, []))
                self._apply_scope_inventory(task_work_data)
                updated = True

                # Propagate completion_promises if not already present
                if report.get("completion_promises") and not task_work_data.get("completion_promises"):
                    task_work_data["completion_promises"] = report["completion_promises"]
                    updated = True

                # Update tests_written from enriched report
                if len(report.get("tests_written", [])) > len(task_work_data.get("tests_written", [])):
                    task_work_data["tests_written"] = report["tests_written"]
                    updated = True

                # 13 October 2026: the Coach's honesty checks read THIS file,
                # so a path set aside above is taken out of the same three
                # lists here. ``files_authored`` is never shortened.
                removed_set = set(written_then_removed)
                if task_work_data.get("files_written_then_removed") != written_then_removed:
                    task_work_data["files_written_then_removed"] = written_then_removed
                    updated = True
                if removed_set:
                    for key in ("files_created", "files_modified", "tests_written", "claimed_files_created", "claimed_files_modified"):
                        before = list(task_work_data.get(key) or [])
                        after = [
                            entry
                            for entry in before
                            if not (
                                isinstance(entry, str)
                                and _normalise_relpath(entry, str(self.worktree_path))
                                in removed_set
                            )
                        ]
                        if after != before:
                            task_work_data[key] = after
                            updated = True

                if updated:
                    with open(task_work_results_path, "w") as f:
                        json.dump(task_work_data, f, indent=2)
                    logger.info(
                        f"Updated task_work_results.json with enriched data for {task_id}"
                    )
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to update task_work_results.json: {e}")

    def _record_baseline(self) -> None:
        """Use the admission baseline, never recapture a later HEAD."""
        from guardkit.orchestrator.task_work_scope import current_lease, ScopeUnavailable
        scope = self.task_work_scope
        lease = current_lease(self.worktree_path)
        if scope is None or lease is None:
            raise ScopeUnavailable("No admitted task scope for baseline capture")
        lease.verify(scope)
        self._baseline_commit = scope.baseline_commit
        self._evidence_baselines = {repo.root: repo.baseline for repo in scope.repositories[1:]}

    def _file_claims(self, report, kind):
        """Retain claims across rewrites without trusting a supplied split.

        A raw report can supply claimed_* itself. Only an actual match to
        this lease's observed inventory lets files_* be treated as the
        previously written observation rather than another asserted list.
        """
        import subprocess
        from guardkit.orchestrator.task_work_scope import ScopeUnavailable

        key = "files_" + kind
        raw = list(report.get(key, []) or [])
        claimed_key = "claimed_" + key
        if claimed_key not in report:
            return raw
        claimed = list(report.get(claimed_key, []) or [])
        try:
            observed = self._detect_git_changes()
            if (report.get("scope_id") == observed["scope_id"]
                    and set(raw) == set(observed[kind])):
                return claimed
        except (ScopeUnavailable, OSError, subprocess.SubprocessError):
            pass
        return sorted(set(raw) | set(claimed))

    def _apply_scope_inventory(self, report):
        """Separate Player claims from the one authoritative observed inventory."""
        import subprocess
        from guardkit.orchestrator.task_work_scope import ScopeUnavailable
        for name in ("modified", "created"):
            report.setdefault("claimed_files_" + name, list(report.get("files_" + name, [])))
        try:
            changes = self._detect_git_changes()
        except (ScopeUnavailable, OSError, subprocess.SubprocessError) as exc:
            report.update(files_modified=[], files_created=[], file_inventory_available=False,
                          file_inventory_error=str(exc))
            return
        report.update(files_modified=changes["modified"], files_created=changes["created"],
                      file_inventory_available=True, scope_id=changes["scope_id"],
                      baseline_commit=changes["baseline_commit"], round_id=self.task_work_scope.round_id)

    def _set_aside_written_then_removed(
        self,
        report: Dict[str, Any],
        confirmed_write_paths: Sequence[str],
        named_in_words_paths: Sequence[str],
        unconfirmed_write_paths: Sequence[str] = (),
    ) -> List[str]:
        """Take a confirmed, unnamed, removed scratch write off the claim lists.

        13 October 2026 (first web fixture proof). The builder wrote a probe
        test file, edited it, and removed it. The write tracker had listed the
        path, nothing removed it, and the claim audit called the missing file
        fabricated: a critical finding on a turn whose tests passed.

        A path is set aside only when ALL of these hold now, after every list
        has been assembled:

        * its write was CONFIRMED (``confirmed_write_paths``: a request with a
          call id met its own successful result), and NO write reached it
          unconfirmed (``unconfirmed_write_paths``: no call id, a result that
          never arrived, or parsed from text). An earlier confirmed write never
          excuses a later unconfirmed one;
        * the builder never named it in its own words, and no completion
          promise names it;
        * it is a path inside the worktree, and nothing exists there now;
        * ``git status`` lists nothing for it (so it is not a tracked
          deletion, and not otherwise changed); and
        * ``git ls-files --error-unmatch`` says git does not track it.

        Only then is it taken out of ``files_created``, ``files_modified`` and
        ``tests_written``, the lists the claim audit and the existence check
        read. ``files_authored`` is never shortened: it is the record of real
        write calls, and the contention detector reads it as authoritative.
        Any failure to check sets nothing aside, which is the behaviour before
        this existed. Returns the paths set aside, worktree-relative and
        sorted.
        """
        import subprocess
        from pathlib import PurePosixPath

        root = Path(self.worktree_path)

        def norm(path: Any) -> Optional[str]:
            if not isinstance(path, str) or not path.strip():
                return None
            return _normalise_relpath(path, str(root)) or None

        try:
            named: Set[str] = {n for n in map(norm, named_in_words_paths) if n}
            # Any unconfirmed write disqualifies the path, like a name does.
            named.update(n for n in map(norm, unconfirmed_write_paths) if n)
            for promise in report.get("completion_promises") or []:
                if not isinstance(promise, dict):
                    continue
                for entry in promise.get("implementation_files") or []:
                    n = norm(entry)
                    if n:
                        named.add(n)
                test_file = promise.get("test_file")
                if isinstance(test_file, str):
                    for part in test_file.split(","):
                        n = norm(part.strip())
                        if n:
                            named.add(n)

            candidates: List[str] = []
            for path in confirmed_write_paths:
                n = norm(path)
                if not n or n in named or n in candidates:
                    continue
                pure = PurePosixPath(n)
                if pure.is_absolute() or ".." in pure.parts:
                    continue
                if os.path.lexists(root / n):
                    continue
                candidates.append(n)
            if not candidates:
                return []

            with self._git_lock:
                status = run_git(
                    [
                        "status", "--porcelain=v1", "--untracked-files=all", "-z",
                        "--", *candidates,
                    ],
                    cwd=root,
                    timeout=30,
                )
                if status.returncode != 0:
                    return []
                # Over-collect on purpose: anything git mentions is kept.
                listed: Set[str] = set()
                for token in status.stdout.split("\0"):
                    if token:
                        listed.add(token)
                        listed.add(token[3:])

                removed: List[str] = []
                for n in candidates:
                    if n in listed:
                        continue
                    tracked = run_git(
                        ["ls-files", "--error-unmatch", "--", n],
                        cwd=root,
                        timeout=30,
                    )
                    # 0 = tracked, 1 = git does not know it, anything else is
                    # a failure to check.
                    if tracked.returncode == 1:
                        removed.append(n)
        except Exception as exc:  # noqa: BLE001 — never block the report
            logger.warning(f"Written-then-removed check failed: {exc}")
            return []

        if not removed:
            return []
        removed_set = set(removed)
        for key in ("files_created", "files_modified", "tests_written", "claimed_files_created", "claimed_files_modified"):
            entries = report.get(key)
            if isinstance(entries, list):
                report[key] = [e for e in entries if norm(e) not in removed_set]
        return sorted(removed)

    def _detect_git_changes(self) -> Dict[str, list]:
        """Detect git changes in worktree.

        Acquires class-level _git_lock to prevent interleaved git operations
        when multiple AgentInvoker instances run in parallel (wave execution).

        Uses per-task _baseline_commit (TASK-FIX-VL06) when available,
        falling back to HEAD for backward compatibility.

        Returns:
            Dict with "modified" and "created" file lists
        """
        from guardkit.orchestrator.task_work_scope import collect_changes
        observed = collect_changes(getattr(self, "task_work_scope", None))
        observed["modified"] = sorted(set(observed["modified"] + observed["deleted"]))
        return observed

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

        # Other tasks in this wave change the same working copy, so git's
        # list may hold their files: build no promises or inferred
        # requirements from it, and say so.
        shared = bool(getattr(self, "shared_working_copy", False))
        report = build_synthetic_report(
            task_id=task_id,
            turn=turn,
            files_modified=files_modified,
            files_created=files_created,
            tests_written=tests_written,
            tests_passed=False,
            test_count=0,
            implementation_notes=implementation_notes,
            concerns=[],
            acceptance_criteria=None if shared else acceptance_criteria,
            task_type=task_type,
            worktree_path=self.worktree_path,
        )
        if shared:
            mark_shared_working_copy(report)
        return report

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

    def _load_agent_report_from(
        self,
        task_id: str,
        turn: int,
        agent_type: Literal["player", "coach"],
        report_path: Path,
    ) -> Dict[str, Any]:
        """Load and validate agent report JSON from a specific path.

        Used when the report was written to a non-standard location
        (e.g. the orchestrator-private directory for coach decisions).

        Args:
            task_id: Task identifier
            turn: Turn number
            agent_type: "player" or "coach"
            report_path: Explicit path to the report file

        Returns:
            Parsed JSON report

        Raises:
            PlayerReportNotFoundError: If Player report doesn't exist
            CoachDecisionNotFoundError: If Coach decision doesn't exist
            PlayerReportInvalidError: If Player JSON is malformed
            CoachDecisionInvalidError: If Coach JSON is malformed
        """
        if not report_path.exists():
            if agent_type == "player":
                raise PlayerReportNotFoundError(
                    f"Player report not found: {report_path}"
                )
            else:
                raise CoachDecisionNotFoundError(
                    f"Coach decision not found: {report_path}"
                )

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

    def _persist_coach_decision(
        self,
        decision: Dict[str, Any],
        coach_output_path: "Path",
        *,
        tag: str,
        kind: str = "overridden",
    ) -> None:
        """Fail-open re-persist of ``coach_turn_N.json`` after a guard mutated
        the loaded ``decision`` dict (TASK-AB-REVIEWCLEAN01 item 2).

        The single seam every deterministic Coach guard routes its disk write
        through, so the
        ``deterministic-verdict-override-must-persist-to-disk`` contract is
        impossible to forget on the next guard: the on-disk file must match
        the in-memory verdict before the Layer-4 late-approval reader
        (``feature_orchestrator._check_late_approval``) consumes it. The write
        is **fail-open** — an ``OSError`` logs WARNING and returns; the
        in-memory mutation (carried in the returned result) already governs
        the turn, so a disk hiccup must never un-reject it. The verdict itself
        is fail-closed (decided before this call).

        ``tag`` is the originating guard's marker (for operator log
        correlation); ``kind`` selects the WARNING noun.
        """
        try:
            coach_output_path.parent.mkdir(parents=True, exist_ok=True)
            coach_output_path.write_text(json.dumps(decision, indent=2))
        except OSError as exc:
            noun = self._PERSIST_KIND_NOUN.get(kind, "override")
            logger.warning(
                "%s: failed to re-persist %s verdict to %s (%s); "
                "in-memory %s still applies",
                tag, kind, coach_output_path, exc, noun,
            )

    def _apply_runtime_parity_guard(
        self,
        *,
        decision: Dict[str, Any],
        evidence_bundle: Optional["CoachEvidenceBundle"],
        task_id: str,
        turn: int,
        coach_output_path: Path,
    ) -> None:
        """Fail closed when the deliverable runs its tests but not its entry point.

        TASK-AB-COACHRUNPARITY01 (arm b). Deterministic backstop for the
        runtime-parity hard-gate. Fires **only** when
        ``runtime_parity.ran is True and runtime_parity.passed is False`` — the
        per-task Coach ran the deliverable's declared runtime entry point (the
        feature smoke command, single-task waves only) and it FAILED. This is
        the "passes pytest but does not run" defect: pytest puts the worktree
        root on ``sys.path`` so imports resolve, but a standalone
        ``python <module>`` invocation does not.

        Narrow:

        * Only an ``approve`` is overridden; a ``feedback`` verdict is untouched.
        * No-op when ``evidence_bundle`` or ``evidence_bundle.runtime_parity``
          is ``None``.
        * No-op when ``ran is False`` (ABSENT signal — no command, parallel
          wave, or runner error) or ``passed is True`` (the entry point ran
          cleanly). An absent runtime signal NEVER blocks
          (``absence-of-failure-is-not-success.md``); only a ran-and-failed one.

        Mutates ``decision`` in place and re-persists ``coach_turn_N.json``.

        Args:
            decision: The loaded, schema-validated Coach verdict dict.
            evidence_bundle: The bundle the synthesis verdict was built over,
                or ``None`` for legacy/tool-using callers (no-op when ``None``).
            task_id: Task identifier (for the WARNING log).
            turn: Current turn number (for the WARNING log).
            coach_output_path: Path to ``coach_turn_N.json`` to re-persist on
                override.
        """
        if decision.get("decision") != "approve":
            return
        if evidence_bundle is None:
            return
        runtime_parity = getattr(evidence_bundle, "runtime_parity", None)
        if runtime_parity is None:
            return
        # Only a ran-and-failed result blocks. Absent (ran=False) or
        # ran-and-passed are no-ops.
        if not getattr(runtime_parity, "ran", False):
            return
        if getattr(runtime_parity, "passed", False):
            return

        original_decision = decision["decision"]
        command = getattr(runtime_parity, "command", "<unknown>")
        exit_code = getattr(runtime_parity, "exit_code", None)
        timed_out = getattr(runtime_parity, "timed_out", False)
        stderr_tail = getattr(runtime_parity, "stderr_tail", "") or ""
        # 2026-07-04 code review: pytest writes its FAILED short-summary lines
        # to STDOUT, not stderr — parse the combined ``output_tail`` when the
        # record carries one (additive field mirroring
        # ``_build_smoke_feedback``'s stdout+stderr join), falling back to
        # ``stderr_tail`` for older records that predate the field.
        output_tail = getattr(runtime_parity, "output_tail", None) or ""
        evidence_tail = output_tail or stderr_tail

        reason_detail = (
            f"timed out after the runtime-parity timeout"
            if timed_out
            else f"exit={exit_code}, expected=0"
        )
        # TASK-AB-STALEATTRIB01: surface the failing-test evidence to the
        # Player. ``_extract_feedback`` (autobuild.py) carries an issue's
        # ``test_output`` verbatim but never reads ``details`` — so the output
        # tail (and, when parseable, the pytest failing-test node IDs) must
        # live in ``test_output`` to reach the Player at all.
        failing_lines = extract_failing_test_lines(evidence_tail)
        bounded_tail = evidence_tail[-2000:]
        tail_label = "output (tail)" if output_tail else "stderr (tail)"
        if failing_lines:
            test_output = (
                "Failing tests:\n"
                + "\n".join(failing_lines)
                + f"\n\n{tail_label}:\n"
                + bounded_tail
            )
        else:
            test_output = bounded_tail

        # TASK-AB-STALEATTRIB01: conditional framing — when the smoke command
        # is recognisably a test-runner invocation, a red here is a failing
        # TEST in the feature smoke suite, not a standalone-run/import defect.
        # Non-test-runner smoke commands keep the runs-standalone framing.
        # TASK-AB-REVIEWCLEAN01 (item 6): the wording lives in
        # stale_test_attribution.runtime_parity_rationale (shared with the
        # post-wave smoke-gate header composer).
        rationale = runtime_parity_rationale(command, reason_detail)

        # TASK-AB-STALEATTRIB01: authorship join — when the failing test's
        # file was authored by exactly one OTHER task, name it and grant the
        # narrowly-scoped stale-assertion permission. Fails OPEN on any
        # miss/ambiguity/missing-record/exception
        # (path-string-mismatch-is-not-dishonesty.md); never suppresses or
        # reclassifies the red signal — the verdict flip below is untouched.
        notes = stale_test_notes(
            failing_lines, getattr(self, "worktree_path", None), {task_id}
        )
        if notes:
            rationale = rationale + "\n\n" + "\n\n".join(notes)

        decision["decision"] = "feedback"
        decision["rationale"] = rationale
        override_issue = {
            "severity": "must_fix",
            "category": "runtime_parity",
            "description": rationale,
            "test_output": test_output,
            "details": {
                "command": command,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "stderr_tail": stderr_tail[-2000:],
                "output_tail": output_tail[-2000:] if output_tail else None,
                "overridden_decision": original_decision,
            },
        }
        decision["issues"] = [override_issue, *decision.get("issues", [])]

        logger.warning(
            "TASK-AB-COACHRUNPARITY01: overriding Coach verdict %r->'feedback' "
            "for %s turn %s — runtime-parity failure (passes pytest but the "
            "deliverable's runtime entry point failed: %s). Command: %s",
            original_decision,
            task_id,
            turn,
            reason_detail,
            command,
        )

        self._persist_coach_decision(
            decision, coach_output_path, tag="TASK-AB-COACHRUNPARITY01"
        )

    def _apply_security_check_guard(
        self,
        *,
        decision: Dict[str, Any],
        evidence_bundle: Optional["CoachEvidenceBundle"],
        task_id: str,
        turn: int,
        coach_output_path: Path,
    ) -> None:
        """Send the turn back when the secrets check found a secret.

        A safety fence the cull keeps (brief item 4). Only a run that exited
        non-zero changes the decision; the check exits non-zero only for a
        confirmed secret. Mutates ``decision`` and re-persists it.
        """
        if decision.get("decision") not in ("approve", "feedback"):
            return
        result = getattr(evidence_bundle, "security_check", None)
        if not isinstance(result, dict) or not result.get("ran") or result.get("passed"):
            return
        output = str(result.get("output_tail") or "")[-2000:]
        description = (
            "The secrets check found what looks like a secret in this task's "
            "changes; read it from the environment or a secret file instead."
        )
        decision["decision"] = "feedback"
        decision["rationale"] = description
        decision["issues"] = [
            {
                "severity": "must_fix",
                "category": "secret_in_change",
                "description": description,
                "test_output": output,
            },
            *decision.get("issues", []),
        ]
        logger.warning(
            "[%s] Turn %s sent back: the secrets check found a secret.", task_id, turn,
        )
        self._persist_coach_decision(
            decision, coach_output_path, tag="security-check"
        )

    def _apply_independent_test_code_failure_guard(
        self,
        *,
        decision: Dict[str, Any],
        evidence_bundle: Optional["CoachEvidenceBundle"],
        task_id: str,
        turn: int,
        coach_output_path: Path,
    ) -> None:
        """Fail closed when a task's REQUIRED test suite RAN and FAILED.

        TASK-ABFIX-012 began this as a TESTING-only backstop for the FMDR-004
        false-approval. Factory reliability repair 1 (12 October 2026) widened
        it to the one acceptance rule in
        :mod:`guardkit.orchestrator.quality_gates.required_suite`, shared with
        the legacy Coach path: B463's declarative direct-mode task was approved
        with 1 failed / 871 passed because this guard returned early for every
        type but ``testing``.

        Fires when ALL hold:

        * ``decision == "approve"`` — a feedback verdict already rejects; untouched.
        * ``independent_tests`` (the tests of the parts the task changed) RAN
          and FAILED: ``tests_passed is False`` AND ``signal_absent is False``,
          whatever the task type. An ABSENT signal sends nothing back; a check
          that could not run stops the task before the reviewer runs.

        The failure classification exempts nothing (``code``,
        ``infrastructure``, ``parallel_contention`` and none alike); it only
        shapes the feedback words.

        Mutates ``decision`` in place and re-persists ``coach_turn_N.json`` so the
        operator artifact and the Layer-4 late-approval reconciliation cannot
        resurrect the overridden ``approve`` (``harness-cancellation-contract.md``).
        """
        from guardkit.orchestrator.quality_gates.required_suite import (
            required_suite_override,
        )

        if decision.get("decision") != "approve":
            return
        if evidence_bundle is None:
            return
        classification = getattr(
            evidence_bundle, "independent_test_classification", None
        )
        override = required_suite_override(
            task_type=getattr(evidence_bundle, "task_type", None),
            independent_tests=getattr(evidence_bundle, "independent_tests", None),
            failure_class=getattr(classification, "failure_class", None),
            confidence=getattr(classification, "confidence", None),
            raw_output_excerpt=getattr(classification, "raw_output_excerpt", None),
        )
        if override is None:
            return

        original_decision = decision["decision"]
        decision["decision"] = "feedback"
        decision["rationale"] = override["rationale"]
        override["issue"]["details"]["overridden_decision"] = original_decision
        decision["issues"] = [override["issue"], *decision.get("issues", [])]

        logger.warning(
            "TASK-ABFIX-012: overriding Coach verdict %r->'feedback' for %s turn "
            "%s — the required test suite ran and FAILED (task_type=%s, "
            "classification=%s).",
            original_decision,
            task_id,
            turn,
            getattr(evidence_bundle, "task_type", None),
            getattr(classification, "failure_class", None),
        )

        self._persist_coach_decision(
            decision, coach_output_path, tag="TASK-ABFIX-012"
        )

    def _apply_behavioural_oracle_guard(
        self,
        *,
        decision: Dict[str, Any],
        evidence_bundle: Optional["CoachEvidenceBundle"],
        task_id: str,
        turn: int,
        coach_output_path: Path,
    ) -> None:
        """Send the turn back when the declared behavioural check ran and failed.

        TASK-QAV-004. Only a ran-and-failed outcome (``status == "ran"`` and
        ``passed`` not true, a timeout included) changes the decision; a check
        that did not run, or passed, changes nothing. Mutates ``decision`` in
        place and re-persists ``coach_turn_N.json``.
        """
        decision_value = decision.get("decision")
        if decision_value not in ("approve", "feedback"):
            return
        if evidence_bundle is None:
            return
        oracle = getattr(evidence_bundle, "behavioural_oracle", None)
        if not isinstance(oracle, dict):
            return
        if oracle.get("status") != "ran":
            return
        if oracle.get("passed") is True:
            return

        # ran-and-failed (including timeout) → hard RED override
        timed_out = oracle.get("timed_out", False)
        # TS-lane D.1a: a DECLARED oracle has no ``oracle_path`` — it is a
        # shell command, and the result dict carries ``command`` instead.
        # Falling straight to "<unknown>" made every declared-oracle failure
        # anonymous in the override rationale below. Name the command.
        oracle_path = (
            oracle.get("oracle_path") or oracle.get("command") or "<unknown>"
        )
        output_tail = (oracle.get("output_tail") or "").strip()
        exit_code = oracle.get("exit_code")
        duration = oracle.get("duration", 0)
        provenance = oracle.get("provenance", "unknown")

        # Build the failure reason
        if timed_out:
            reason = (
                f"behavioural oracle timed out after {duration:.0f}s "
                f"(oracle: {oracle_path})"
            )
        else:
            reason = (
                f"behavioural oracle failed with exit_code={exit_code} "
                f"(oracle: {oracle_path}, duration={duration:.1f}s)"
            )

        # AC-1: name the cause and include failure output
        rationale = (
            f"Behavioural round-trip oracle FAILED — {reason}. "
            f"The oracle is independent evidence that the Coach did not author. "
            f"This overrides the Coach's approve verdict to feedback. "
            f"Provenance: {provenance}. "
            f"Failure output: {output_tail or '<empty>'}"
        )

        override_issue = {
            "severity": "must_fix",
            "category": "behavioural_oracle_failure",
            "description": rationale,
            "test_output": output_tail,
            "details": {
                "oracle_path": oracle_path,
                "provenance": provenance,
                "exit_code": exit_code,
                "duration": duration,
                "timed_out": timed_out,
                "output_tail": output_tail,
                "overridden_decision": decision_value,
            },
        }

        decision["decision"] = "feedback"
        decision["rationale"] = rationale
        decision["issues"] = [override_issue, *decision.get("issues", [])]

        logger.warning(
            "TASK-QAV-004: overriding Coach verdict %r->'feedback' for "
            "%s turn %s — behavioural oracle ran-and-failed "
            "(%s). Oracle: %s",
            decision_value,
            task_id,
            turn,
            "timed_out" if timed_out else "exit_code=" + str(exit_code),
            oracle_path,
        )

        # AC-2: re-persist so the on-disk coach_turn_N.json carries the
        # override, not the stale approve (deterministic-verdict-override-
        # must-persist-to-disk).
        self._persist_coach_decision(
            decision, coach_output_path, tag="TASK-QAV-004"
        )

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

        # TASK-SBHO-002: strip worktree-relative oracle paths from all text
        # fields so the Player-facing coach_feedback file does not leak paths
        # to oracle files that live in the orchestrator-private directory.
        structured_feedback = self._strip_oracle_paths_from_feedback(
            structured_feedback,
        )

        feedback_path = autobuild_dir / f"coach_feedback_for_turn_{turn}.json"
        with open(feedback_path, "w") as f:
            json.dump(structured_feedback, f, indent=2)

        logger.debug(f"Wrote Coach feedback to {feedback_path}")
        return feedback_path

    def _strip_oracle_paths_from_feedback(
        self, feedback: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Remove worktree-relative oracle paths from feedback text fields.

        TASK-SBHO-002: Player-facing coach_feedback must not contain paths
        to oracle files.  This mutates the structured feedback dict in place,
        replacing any worktree-relative file path with ``<oracle-file>``.

        Args:
            feedback: Structured feedback dict with text fields to sanitize.

        Returns:
            The same dict, mutated in place.
        """
        from guardkit.orchestrator.paths import strip_oracle_paths

        # Sanitize top-level summary
        summary = feedback.get("feedback_summary")
        if isinstance(summary, str):
            feedback["feedback_summary"] = strip_oracle_paths(summary)

        # Sanitize issue descriptions and suggestions
        for key in ("must_fix", "should_fix"):
            issues = feedback.get(key)
            if not isinstance(issues, list):
                continue
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                for field in ("description", "suggestion", "details"):
                    val = issue.get(field)
                    if isinstance(val, str):
                        issue[field] = strip_oracle_paths(val)
                # Also scrub nested details dict
                details = issue.get("details")
                if isinstance(details, dict):
                    for dkey, dval in details.items():
                        if isinstance(dval, str):
                            details[dkey] = strip_oracle_paths(dval)

        return feedback

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
                # Categorize by severity. "must_fix" is the severity the
                # quality gates themselves use; it was missing here, so a
                # gate's own must-fix issue was filed as should-fix.
                if issue.get("severity") in ["must_fix", "critical", "major"]:
                    structured["must_fix"].append(issue_entry)
                else:
                    structured["should_fix"].append(issue_entry)

        else:
            # Plain text feedback - store as summary
            structured["feedback_summary"] = feedback
            structured["raw_feedback"] = feedback
            # The text is what AutoBuildOrchestrator._extract_feedback wrote,
            # and it starts each must-fix issue with MUST_FIX_MARKER. Read
            # those back into must_fix, so the list the Player is told to
            # address is not empty when the turn failed for a must-fix reason
            # (build FEAT-895D, 8 October 2026: a failing test was the only
            # must-fix reason and the list was empty for three turns). Text
            # with no marked line gives an empty list, as before.
            for item in must_fix_items(feedback):
                issue_text, suggestion = split_must_fix_item(item)
                structured["must_fix"].append({
                    "issue": issue_text,
                    "location": "",
                    "suggestion": suggestion,
                    "type": "must_fix",
                })

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
            approaching_limit: The escape-hatch trigger, as computed by
                :func:`turn_pressure` (penultimate turn onwards when
                max_turns >= 3; the FINAL turn only when max_turns <= 2)

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
        - 1.5x SDK timeout multiplier (direct mode has had the same since
          FEAT-2C42, 8 October 2026)
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
        - Implementation mode multiplier (task-work and direct 1.5x, any
          other mode 1.0x; direct was 1.0x before FEAT-2C42, 8 October 2026)
        - Complexity multiplier (1.0 + complexity/10.0, range 1.1x-2.0x)

        If the caller marks the timeout as an explicit CLI/task override,
        returns that value unchanged.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            remaining_budget: Optional remaining wall-clock budget in seconds.
                When provided, the effective timeout is capped at this value so
                the SDK call does not exceed the overall task budget. CLI overrides
                take precedence and are never capped. (TASK-ABFIX-004)

        Returns:
            Effective timeout in seconds, capped at the finite MAX_SDK_TIMEOUT
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

        # Mode multiplier. Direct mode gets the same 1.5x as task-work
        # (8 October 2026): measured since 1 October, 31% of direct-mode
        # turns ran out of time at 1.0x before writing their report, and the
        # turns that finished took up to 2304 s against a 2160-2340 s
        # allowance. The finite cap and the remaining-budget cap below still
        # apply, so a turn never outlasts the task's own budget.
        if mode in ("task-work", "direct"):
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
            context: Job-specific context from the memory backend

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
            # The turn ran out of time before the coder wrote its own report.
            # Say so in fields, not only in the error text, so the state
            # tracker, the evidence gate's feedback and the final summary can
            # all tell a timeout apart from other failures (build FEAT-2C42,
            # 8 October 2026).
            timeout_details = player_timeout_details(
                self.sdk_timeout_seconds, duration
            )
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
                failure_details=timeout_details,
            )
            return AgentInvocationResult(
                task_id=task_id,
                turn=turn,
                agent_type="player",
                success=False,
                report=dict(timeout_details),
                duration_seconds=duration,
                error=f"SDK timeout after {self.sdk_timeout_seconds}s: {str(e)}",
                session_id=self._last_session_id,  # TASK-RFX-B20B: preserve for retry
            )
        except Exception as e:
            duration = time.time() - start_time
            error_report = {"task_id": task_id, "turn": turn}
            refused = self._launch_refusal_error(task_id, e)
            error_msg = str(refused) if refused else f"Unexpected error: {str(e)}"
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
            if refused is not None:
                raise refused from e
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

    def _launch_refusal_error(
        self, task_id: str, error: BaseException
    ) -> Optional[AgentLaunchRefusedError]:
        """Map a harness launch refusal in ``error``'s chain to GuardKit's error.

        Returns ``None`` for every other failure, which keeps its existing
        handling.
        """
        refusal = find_agent_launch_refusal(error)
        if refusal is None:
            return None
        refused = AgentLaunchRefusedError.from_refusal(refusal)
        logger.error(f"[{task_id}] AGENT LAUNCH REFUSED: {refused}")
        return refused

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
                # B9 Lane C: direct mode measures NOTHING, so it may not write
                # a measured value. ``None`` is UNKNOWN; the relaxation is
                # carried by ``quality_gates_relaxed`` beside it, and the Coach
                # reads ``implementation_mode == "direct"`` to decide the gate
                # is not required (recording ``coverage_relaxed_by:
                # direct_mode``). Writing ``True`` here was a measurement the
                # factory never took.
                "coverage_met": None,  # UNKNOWN — direct mode measures nothing
                "quality_gates_relaxed": True,  # Signal to Coach
                "all_passed": success,
            },
            "files_modified": sorted(list(set(self._file_claims(player_report, "modified")))),
            "files_created": sorted(list(set(self._file_claims(player_report, "created")))),
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

        scope = getattr(self, "task_work_scope", None)
        if scope is not None:
            results.update(scope_id=scope.scope_id, baseline_commit=scope.baseline_commit, round_id=scope.round_id)
        if isinstance(player_report.get("original_failure"), dict):
            results["original_failure"] = player_report["original_failure"]
        self._apply_scope_inventory(results)
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
        failure_details: Optional[Dict[str, Any]] = None,
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
            failure_details: Extra fields saying why the turn failed (for a
                timeout: ``timed_out``, ``timeout_seconds``,
                ``elapsed_seconds``). Written only when ``success`` is False.

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
            "files_modified": self._file_claims(player_report, "modified"),
            "files_created": self._file_claims(player_report, "created"),
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
        # A report built from a working copy other tasks were also changing
        # says so, so nothing downstream counts it as this task's evidence.
        if player_report.get(SHARED_WORKING_COPY_FIELD):
            report[SHARED_WORKING_COPY_FIELD] = True

        # Add error info if failed
        if not success and error:
            report["error"] = error
            report["success"] = False
            if failure_details:
                report.update(failure_details)
        else:
            report["success"] = True

        # Write the report
        scope = getattr(self, "task_work_scope", None)
        if scope is not None:
            report["scope_id"] = scope.scope_id
            report["baseline_commit"] = scope.baseline_commit
            report["round_id"] = scope.round_id
        if isinstance(player_report.get("original_failure"), dict):
            report["original_failure"] = player_report["original_failure"]
        self._apply_scope_inventory(report)
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
        scratch_folder: Optional[Path] = None,
    ) -> str:
        """Build implementation prompt using loaded execution protocol.

        TASK-ACO-002: Replaces _build_inline_implement_protocol() with a
        prompt that loads the execution protocol from autobuild_execution_protocol.md
        via load_protocol(), and injects task requirements, coach feedback,
        memory context, and turn context inline.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            mode: Development mode ("standard", "tdd", or "bdd")
            documentation_level: Documentation level ("minimal", "standard",
                or "comprehensive")
            turn: Current turn number (1-based)
            requirements: Task requirements from task markdown
            feedback: Optional Coach feedback from previous turn
            max_turns: Maximum turns allowed for this orchestration
            context: Job-specific context from the memory backend
            scratch_folder: The builder's scratch folder, given only when the
                selected harness provides it; ``None`` leaves its line out

        Returns:
            Assembled prompt string with protocol and all context sections
        """
        # The ONE rule (see ``turn_pressure``): with max_turns=2 — the work
        # leg's default — the warning fires on turn 2 only. Turn one of two is
        # clean; telling the Player it is out of time before it has written a
        # line is pressure to give up, not a warning.
        approaching_limit, final_turn = turn_pressure(turn, max_turns)

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
            f"- Final turn: {final_turn}\n"
        )
        if final_turn:
            turn_section += (
                "\nWARNING: This is your FINAL turn. If you cannot complete the task,\n"
                "include a 'blocked_report' field in your player report.\n"
            )
        elif approaching_limit:
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

        # This route serves the ordinary task-work Player and does not consume
        # _build_player_prompt().  Keep the acceptance-criterion reporting
        # contract in the assembled prompt so both full and medium execution
        # protocols receive it.
        criterion_reporting_section = (
            "\n## Acceptance-Criterion Reporting\n"
            "\n"
            "A documented conflict or implementation departure does not satisfy "
            "an acceptance criterion. Mark it incomplete unless an authoritative "
            "amendment changes the target. Report an unsafe or conflicting "
            "requirement as a concern; do not restore unsafe behaviour merely to "
            "make the words match.\n"
        )


        # --- Section 4: Coach feedback (inline when available) ---
        feedback_section = ""
        if feedback:
            # Turn-1 feedback is a gate's seed (see invoke_player): the wave
            # was re-entered because a check that ran AFTER this task was
            # approved failed. It must reach the Player or the re-entry
            # repairs nothing.
            formatted = self._format_feedback_for_prompt(feedback, turn)
            heading = (
                f"Coach Feedback from Turn {turn - 1}"
                if turn > 1
                else "Feedback from the check that failed after this task was approved"
            )
            feedback_section = (
                f"\n## {heading}\n"
                f"\n"
                f"{formatted}\n"
                f"\n"
                f"Address ALL must_fix items before proceeding.\n"
            )

        # --- Section 5: memory context (inline when available) ---
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
        # 3 October 2026 (concurrent builds): the test-fixture recipes come
        # from docker_fixtures, the same source the Coach uses, with this
        # task's own container names and a free loopback port, so two tasks
        # or two builds never start or remove each other's containers.
        protocol_content = render_player_recipes(protocol_content, task_id)
        # 3 October 2026: name the builder's scratch folder, the one place
        # outside the worktree the factory lets it write, only when the
        # caller knows the selected harness provides it. Otherwise the line
        # naming it is left out.
        if scratch_folder is not None:
            protocol_content = protocol_content.replace(
                "{scratch_folder}", str(scratch_folder)
            )
        else:
            protocol_content = "\n".join(
                line
                for line in protocol_content.splitlines()
                if "{scratch_folder}" not in line
            )

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
            + criterion_reporting_section
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
        task requirements, coach feedback, memory context, and turn context
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
            context: Job-specific context from the memory backend. Default: "".

        Returns:
            TaskWorkResult with success status and output/error

        Raises:
            SDKTimeoutError: If execution exceeds timeout
        """
        from guardkit.orchestrator.harness.selector import (
            provided_scratch_root,
            resolve_harness_name,
        )

        # 3 October 2026: only the local (LangGraph) builder's file backend
        # can allow a scratch folder, so only then is one prepared. Whether
        # the backend really accepted it is checked once the harness exists.
        scratch_folder = (
            prepare_builder_scratch_dir(self.worktree_path)
            if resolve_harness_name() == "langgraph"
            else None
        )

        def _build_prompt() -> str:
            # TASK-ACO-002: Build prompt with loaded protocol and inline context
            return self._build_autobuild_implementation_prompt(
                task_id=task_id,
                mode=mode,
                documentation_level=documentation_level,
                turn=turn,
                requirements=requirements,
                feedback=feedback,
                max_turns=max_turns,
                context=context,
                scratch_folder=scratch_folder,
            )

        prompt = _build_prompt()

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
        resolved_harness_name = resolve_harness_name()

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
            preserve_event_checked as _sdk_preserve_event_checked,
        )
        from guardkit.orchestrator.head_identity import observe_invocation
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
        if resolved_harness_name == "sdk":
            logger.info(f"[{task_id}] SDK max turns: {effective_max_turns}")
        else:
            logger.info(
                f"[{task_id}] SDK max turns: unknown "
                f"(unsupported by {resolved_harness_name} harness)"
            )
        logger.info(
            f"[{task_id}] Whole-attempt wall timeout: {self.sdk_timeout_seconds}s"
        )
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
        parser = TaskWorkStreamParser(worktree_root=self.worktree_path)
        sdk_turns_used = None
        sdk_session_id = None
        terminal_usage: object = None
        typed_tool_uses: List[Tuple[str, str]] = []
        typed_tool_results: List[Tuple[str, bool]] = []
        # (tool call id, path) of each read_file request; only those whose
        # result came back without error are counted (Codex review R1).
        typed_read_paths: List[Tuple[str, str]] = []
        attempt_wall_duration_ms = 0

        try:
            for _sdk_attempt in range(MAX_SDK_STREAM_RETRIES + 1):
                collected_output = []
                message_count = 0
                assistant_count = 0
                tool_count = 0
                result_count = 0
                _sdk_stream_error = None
                _pending_bash_tools: Dict[str, Dict[str, Any]] = {}
                sdk_turns_used = None
                sdk_session_id = None
                terminal_usage = None
                typed_tool_uses = []
                typed_tool_results = []
                typed_read_paths = []
                attempt_started_ns = time.monotonic_ns()

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
                    harness_role="player",
                    # Keep the main task-work Player on the same substrate-aware
                    # activity signal as the direct Player route. Native skills
                    # may trigger nested model/tool work before the first event
                    # is yielded back to this loop.
                    on_model_activity=self._bump_activity,
                    on_native_tool_event=(
                        lambda event: _sdk_preserve_event_checked(_sdk_debug_dir, event)
                    ) if _sdk_debug_dir is not None else None,
                    scratch_root=scratch_folder,
                    launch_declaration=load_launch_snapshot(
                        task_id, self.worktree_path
                    ),
                    language_servers=self._builder_language_servers(task_id),
                )

                # 3 October 2026: keep the scratch folder only if the
                # harness's backend really allows it (an older factory, or one
                # that refused the folder, does not). Otherwise the builder is
                # not told about it and nothing is left off its file list.
                if (
                    scratch_folder is not None
                    and provided_scratch_root(harness) != scratch_folder
                ):
                    logger.warning(
                        f"[{task_id}] Builder scratch folder not provided by the "
                        f"harness; the builder is not told about it."
                    )
                    scratch_folder = None
                    prompt = _build_prompt()
                    # Keep the saved debug copy equal to what is sent. This
                    # only happens on the first attempt, before any event is
                    # saved, so rewriting the folder loses nothing.
                    if _sdk_debug_dir is not None:
                        _sdk_preserve_prompt(
                            workspace_root=self.worktree_path,
                            task_id=task_id,
                            turn=turn,
                            role="player",
                            prompt=prompt,
                            options=None,
                        )
                # TASK-FIX-STUB-C: Recreate parser per retry so ToolUseBlock
                # file operations from a previous (failed) attempt do not
                # leak into the successful attempt's result.
                parser = TaskWorkStreamParser(
                    worktree_root=self.worktree_path, scratch_root=scratch_folder
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
                        # HEAD recorded before and after (build 0D7C);
                        # the stream passes through unchanged.
                        async with aclosing(
                            observe_invocation(
                                harness.invoke(
                                    prompt=prompt,
                                    role="player",
                                    tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task"],
                                    cwd=self.worktree_path,
                                    timeout_seconds=self.sdk_timeout_seconds,
                                ),
                                self.worktree_path,
                                role="player (task-work)",
                                task_id=task_id,
                                turn=turn,
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

                                if isinstance(event, ToolUseEvent):
                                    tool_count += 1
                                    _tool_category = _runtime_tool_category(
                                        event.name
                                    )
                                    typed_tool_uses.append(
                                        (
                                            event.tool_use_id
                                            if isinstance(event.tool_use_id, str)
                                            else "",
                                            _tool_category,
                                        )
                                    )
                                    _read_path = _read_file_path(
                                        event.name, event.input
                                    )
                                    if (
                                        _read_path is not None
                                        and len(typed_read_paths)
                                        < _DECLARED_READ_CALLS_LIMIT
                                    ):
                                        typed_read_paths.append(
                                            (
                                                event.tool_use_id
                                                if isinstance(event.tool_use_id, str)
                                                else "",
                                                _read_path,
                                            )
                                        )
                                    # 2026-09-21 repair. Every harness yields
                                    # one typed event per tool call; only the
                                    # hosted one also fills ``event.raw``, and
                                    # the raw-content walk below was the ONLY
                                    # place that fed the file tracker. On the
                                    # local builder ``event.raw`` is None, so
                                    # ``files_authored`` came out empty on
                                    # every task while the builder wrote real
                                    # files (kept 19 September records: write
                                    # category 6-12 calls per task, list
                                    # empty). Feed the tracker from the typed
                                    # event instead, for any tool the category
                                    # table calls a write.
                                    # 3 October 2026: this is now the ONLY
                                    # place a tool write is tracked, for both
                                    # harnesses, and the path waits for the
                                    # call's result (``record_tool_request``).
                                    if _tool_category == "write":
                                        _typed_input = (
                                            event.input
                                            if isinstance(event.input, dict)
                                            else {}
                                        )
                                        parser.record_tool_request(
                                            event.tool_use_id,
                                            event.name,
                                            _typed_input,
                                        )
                                    self._track_tool_use(event)
                                elif isinstance(event, ToolResultEvent):
                                    typed_tool_results.append(
                                        (
                                            event.tool_use_id
                                            if isinstance(event.tool_use_id, str)
                                            else "",
                                            bool(event.is_error),
                                        )
                                    )
                                    parser.record_tool_result(
                                        event.tool_use_id, bool(event.is_error)
                                    )
                                elif isinstance(event, AssistantMessageEvent):
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
                                    # Walk raw SDK content blocks for parser file
                                    # tracking and per-bash-exec emission.
                                    # Uses duck-typing on type(block).__name__ —
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
                                            block_name = getattr(block, "name", "")
                                            logger.debug(f"Tool invoked: {block_name}")
                                            # Write/Edit blocks are not tracked here
                                            # (3 October 2026): the SDK harness
                                            # yields a typed ToolUseEvent for each
                                            # of them first, and the branch above
                                            # records the path once its result is
                                            # known. Tracking the raw block too put
                                            # a refused write on the list.
                                            # TASK-INST-005c: Track Bash tool invocations
                                            # for tool.exec event emission.
                                            if block_name == "Bash":
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
                                                # TASK-OBS-9F43 AC-4: Extract real exit_code and stderr
                                                # from ToolResultBlock instead of hardcoding
                                                _exit_code = getattr(block, "exit_code", 0)
                                                _stderr = getattr(block, "stderr", "")
                                                # Fallback to stdout for content if no separate stdout field
                                                _stdout = getattr(block, "stdout", _content_str)

                                                self._emit_tool_exec_event(
                                                    tool_name="Bash",
                                                    cmd=_bash_info["cmd"],
                                                    exit_code=_exit_code,  # Real exit code
                                                    latency_ms=_latency,
                                                    stdout_tail=_stdout,
                                                    stderr_tail=_stderr,  # Real stderr
                                                    task_id=task_id,
                                                )
                                            # Extract content from tool results
                                            # if present (parser sees them too).
                                            _result_content = getattr(block, "content", None)
                                            if _result_content:
                                                collected_output.append(str(_result_content))
                                elif isinstance(event, ResultMessageEvent):
                                    result_count += 1
                                    terminal_usage = event.usage
                                    # TASK-VPR-003: Capture SDK turns from ResultMessage.
                                    # ResultMessageEvent does not expose num_turns at
                                    # the typed-event level (TASK-HMIG-006 D-1 left
                                    # this on raw); read from event.raw which the SDK
                                    # harness populates with the original SDK
                                    # ResultMessage. LangGraph harness leaves raw=None
                                    # so sdk_turns_used stays None on that path.
                                    if event.raw is not None:
                                        sdk_turns_used = _nonnegative_exact_int(
                                            getattr(event.raw, "num_turns", None)
                                        )
                                    # TASK-RFX-B20B: Capture session_id for resumption.
                                    # Read from typed field so the same code path
                                    # works for any substrate.
                                    sdk_session_id = event.session_id
                                    self._last_session_id = sdk_session_id
                                    turns_log = (
                                        str(sdk_turns_used)
                                        if sdk_turns_used is not None
                                        else "unknown"
                                    )
                                    logger.info(
                                        f"[{task_id}] Harness completed: SDK turns={turns_log}"
                                    )
                                    break

                if _sdk_stream_error is None:
                    attempt_wall_duration_ms = max(
                        0, (time.monotonic_ns() - attempt_started_ns) // 1_000_000
                    )
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
                f"assistant={assistant_count}, tool_uses={tool_count}, "
                f"tool_results={len(typed_tool_results)}, results={result_count}"
            )

            # Join collected output for parsing.
            output_text = "\n".join(collected_output)

            # Parse text output for quality gate metrics (tests, coverage, phases).
            # Note: parser already has file tracking from the typed tool events above.
            parser.parse_message(output_text)
            parsed_result = parser.to_result()

            # TASK-VPR-003: Inject SDK turn metrics into parsed result.
            sdk_supported = resolved_harness_name == "sdk"
            reported_sdk_turns = sdk_turns_used if sdk_supported else None
            reported_sdk_max_turns = (
                effective_max_turns if sdk_supported else None
            )
            parsed_result["sdk_turns_used"] = reported_sdk_turns
            parsed_result["sdk_max_turns"] = reported_sdk_max_turns
            parsed_result["sdk_turns_supported"] = sdk_supported
            # 2026-09-21. Say whether the file list was recorded at all, so a
            # reader can keep "the tracking failed" apart from "this task
            # changed nothing". At least one tool event seen ⇒ the stream that
            # feeds the tracker was working, so an empty list means the builder
            # wrote no file with its file tools. No tool event at all ⇒ the
            # list says nothing.
            parsed_result[_AUTHORED_TRACKING_KEY] = (
                _AUTHORED_TRACKED if typed_tool_uses else _AUTHORED_NOT_TRACKED
            )
            # A file written by a shell command is not in the list. Count the
            # shell commands so a card line can say so.
            parsed_result[_AUTHORED_SHELL_COUNT_KEY] = sum(
                1 for _, _category in typed_tool_uses if _category == "execute"
            )
            runtime_evidence = _build_task_work_runtime_evidence(
                harness_name=resolved_harness_name,
                message_count=message_count,
                assistant_count=assistant_count,
                result_count=result_count,
                tool_uses=typed_tool_uses,
                tool_results=typed_tool_results,
                terminal_usage=terminal_usage,
                attempt_wall_duration_ms=attempt_wall_duration_ms,
                selected_attempt=_sdk_attempt + 1,
                discarded_attempts=_sdk_attempt,
                sdk_turns_used=reported_sdk_turns,
                sdk_max_turns=reported_sdk_max_turns,
                wall_timeout_seconds=self.sdk_timeout_seconds,
                declared_reads=_declared_reads(
                    self.worktree_path,
                    _successful_read_paths(typed_read_paths, typed_tool_results),
                ),
            )

            # Write task_work_results.json for Coach validation.
            self._write_task_work_results(
                task_id,
                parsed_result,
                documentation_level,
                runtime_evidence=runtime_evidence,
            )

            logger.info(f"task-work completed successfully for {task_id}")
            return TaskWorkResult(
                success=True,
                output=parsed_result,
                sdk_turns_used=reported_sdk_turns,
                sdk_max_turns=reported_sdk_max_turns,
                session_id=sdk_session_id,  # TASK-RFX-B20B
            )

        except asyncio.TimeoutError:
            error_msg = f"task-work execution exceeded {self.sdk_timeout_seconds}s timeout"
            logger.error(f"[{task_id}] HARNESS WALL TIMEOUT: {error_msg}")
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
            refused = self._launch_refusal_error(task_id, e)
            if refused is not None:
                self._write_failure_results(
                    task_id, str(refused), "AgentLaunchRefusedError", collected_output
                )
                raise refused from e
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
            # A refused agent launch never reached the model; it is not an
            # implementation failure and must not be retried as one.
            refused = self._launch_refusal_error(task_id, e)
            if refused is not None:
                self._write_failure_results(
                    task_id, str(refused), "AgentLaunchRefusedError", collected_output
                )
                raise refused from e

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
            # Step 1 (24 October 2026): task-state bookkeeping never ends the
            # task; the failure is logged and the work goes on.
            logger.warning(
                f"Could not ensure design_approved state for {task_id}: {e}; "
                f"the task goes on"
            )

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

    # R1 DE-WIRE (Rich 08-14): _resolve_worktree_python_executable and
    # _run_bdd_oracle (TASK-BDD-E8954) removed — the orchestrator no longer
    # executes BDD scenarios. bdd_runner.py remains on disk, unreferenced,
    # until R2 deletes it at graduation. Gherkin AUTHORING (feature-spec,
    # gherkin_official validation) is untouched.

    # R1 DE-WIRE (Rich 08-14): _run_bdd_authoring_sweep
    # (TASK-AB-BDDAUTHOR01) removed with its invocation — no turn runs
    # pytest-bdd glue sweeps any more.

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

    def _read_declared_file_sections(
        self,
        task_id: str,
    ) -> Dict[str, Optional[List[str]]]:
        """What the task document itself says it will create and change.

        Two answers, kept apart under the keys ``create`` and ``modify``,
        because "creates nothing and changes two files" is a thing a task must
        be able to say. For each of the two:

        * ``None`` - the task document has no such heading at all. It made no
          claim, so nothing is compared on that side.
        * ``[]`` - the heading is there and declares nothing, written as the
          single line ``- _none_``. That is a claim: this task creates (or
          changes) nothing, and anything found beyond it is sprawl.

        Empty is not the same as absent, and that is where this reader differs
        from :meth:`_extract_explicit_planned_files`. That one merges the two
        sections into a single set and treats a section holding only
        ``- _none_`` as though it were not there; it keeps that job, and the
        caller that wants a merged set still calls it.

        The two section names are not new: they are the convention already in
        this estate, added by hand to fourteen task documents in May.

        Args:
            task_id: Task ID whose body should be read.

        Returns:
            ``{"create": ..., "modify": ...}`` as described above. Both are
            ``None`` when the task file cannot be found or read at all.
        """
        absent: Dict[str, Optional[List[str]]] = {"create": None, "modify": None}

        task_file = self._find_task_file(task_id)
        if task_file is None:
            return absent
        try:
            content = task_file.read_text(errors="replace")
        except OSError:
            return absent
        return self.declared_file_sections_in_text(content)

    @staticmethod
    def declared_file_sections_in_text(
        content: str,
        *,
        keep_every_entry: bool = False,
    ) -> Dict[str, Optional[List[str]]]:
        """The ``create`` / ``modify`` answer of
        :meth:`_read_declared_file_sections`, read from a task document's text
        (with or without its frontmatter). The one parser of those sections:
        the orchestrator's task-start coverage check asks it too (20 October
        2026).

        ``keep_every_entry`` (23 October 2026) keeps the entries the default
        reading drops, names starting with ``_`` and wildcards, and leaves
        out only the no-file markers. The coverage check uses it, because a
        dropped ``__init__.py`` or ``src/*`` must still count as source.
        """
        import re as _re

        # Strip the frontmatter the same way the other readers here do, so
        # all of them see the same shape of body.
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2] if len(parts) >= 3 else content
        else:
            body = content

        # Stop at the next top-level heading but not at a "### Subsection",
        # which is a legitimate child of these sections.
        section_pattern = r"^##\s+Files\s+to\s+{action}\s*\n(.*?)(?=^##(?!#)|\Z)"

        declared: Dict[str, Optional[List[str]]] = {"create": None, "modify": None}
        for key, action in (("create", "Create"), ("modify", "Modify")):
            match = _re.search(
                section_pattern.format(action=action),
                body,
                _re.IGNORECASE | _re.MULTILINE | _re.DOTALL,
            )
            if match is None:
                continue
            has_bullets, paths = AgentInvoker._paths_in_declared_section(
                match.group(1), keep_every_entry=keep_every_entry
            )
            if not has_bullets:
                # A heading with nothing at all under it is not a claim, it is
                # an unfinished task document. The way to say "this task
                # creates nothing" is to write the line ``- _none_``.
                continue
            declared[key] = paths
        return declared

    @staticmethod
    def _paths_in_declared_section(
        section_text: str,
        *,
        keep_every_entry: bool = False,
    ) -> Tuple[bool, List[str]]:
        """Read one declared section: was anything listed, and which paths.

        The first answer is whether the section has any bullet at all. A
        bullet that says ``_none_`` (or ``n/a``, ``none``, ``tbd``) declares
        no path, but it is still a bullet and still a claim: this task creates
        (or changes) nothing. Bullets carrying a trailing description after an
        em dash or a spaced hyphen keep only the path. Wildcards are skipped:
        a declaration is a list of real files.
        """
        import re as _re

        has_bullets = False
        paths: List[str] = []
        for line in section_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if not (stripped.startswith("- ") or stripped.startswith("* ")):
                continue
            has_bullets = True
            item = stripped[2:].strip()
            for separator in ("—", " - "):
                found_at = item.find(separator)
                if found_at != -1:
                    item = item[:found_at].strip()
                    break
            backticked = _re.match(r"`([^`]+)`", item)
            if backticked:
                candidate = backticked.group(1).strip()
            else:
                candidate = item.split()[0] if item else ""
            if not candidate:
                continue
            # A generated task can render the no-file marker as an outer
            # Markdown bullet whose code-span text is "- _none_". Compare a
            # separately normalised value so that shape remains an empty
            # declaration without changing any real path this parser returns.
            sentinel_candidate = candidate
            has_nested_bullet = sentinel_candidate.startswith(("- ", "* "))
            if has_nested_bullet:
                sentinel_candidate = sentinel_candidate[2:].strip()
            if keep_every_entry:
                # Only a no-file marker (``_none_``, ``None``, ``n/a``) is
                # left out; every other entry is kept as written.
                if sentinel_candidate.strip("_*. ").lower() not in {
                    "n/a",
                    "none",
                    "tbd",
                }:
                    if candidate not in paths:
                        paths.append(candidate)
                continue
            nested_no_file_marker = (
                has_nested_bullet
                and sentinel_candidate.strip("_*. ").lower()
                in {"n/a", "none", "tbd"}
            )
            if (
                candidate.startswith("_")
                or candidate.lower() in {"n/a", "none", "tbd"}
                or nested_no_file_marker
            ):
                continue
            if "*" in candidate:
                continue
            if candidate not in paths:
                paths.append(candidate)
        return has_bullets, paths

    def _resolve_bare_declared_names(
        self,
        declared: Dict[str, Optional[List[str]]],
    ) -> Tuple[Dict[str, Optional[List[str]]], Dict[str, str], Dict[str, List[str]]]:
        """Replace each bare declared name that means exactly one file.

        Returns the declaration with those names replaced, what each resolved
        name became, and which bare names matched more than one file. When
        nothing is bare, or git cannot list the repository, the declaration is
        returned unchanged. Never raises.
        """
        from guardkit.orchestrator.declared_paths import (
            is_bare_name,
            repository_files,
            resolve_bare_names,
        )

        every = list(declared["create"] or []) + list(declared["modify"] or [])
        if not any(is_bare_name(entry) for entry in every):
            return declared, {}, {}
        try:
            candidates = repository_files(self.worktree_path)
            if candidates is None:
                return declared, {}, {}

            def _excluded(path: str) -> bool:
                return _is_orchestrator_managed_path(
                    path, worktree_path=self.worktree_path
                )

            resolved: Dict[str, str] = {}
            ambiguous: Dict[str, List[str]] = {}
            out: Dict[str, Optional[List[str]]] = {}
            for key in ("create", "modify"):
                outcome = resolve_bare_names(
                    declared[key],
                    worktree_path=self.worktree_path,
                    candidates=candidates,
                    excluded=_excluded,
                )
                if outcome is None:
                    out[key] = None
                    continue
                out[key] = outcome.paths
                resolved.update(outcome.resolved)
                ambiguous.update(outcome.ambiguous)
            return out, resolved, ambiguous
        except Exception as exc:  # noqa: BLE001 — the audit must still run
            logger.warning(
                "resolving bare file names in the task document raised %s; "
                "they are checked as written.",
                exc.__class__.__name__,
            )
            return declared, {}, {}

    def _write_task_work_results(
        self,
        task_id: str,
        result_data: Dict[str, Any],
        documentation_level: str = "standard",
        *,
        runtime_evidence: Optional[Dict[str, Any]] = None,
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
                # ``coverage`` is the last percentage the builder's TEXT
                # matched, kept for information only. It is not a measurement
                # of the project's gate (Go alone prints a 0.0% line for a
                # package with no tests before the real one), and 80 is not
                # the project's number. No verdict is drawn from it, and no
                # coverage is measured on the per-task path.
                "coverage": coverage,
                "coverage_met": None,
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
            # 2026-09-21: the marker that keeps "the tracking failed" apart
            # from "this task changed nothing". ``tracked`` only when the
            # caller saw at least one tool event; anything else is
            # ``not_tracked``, because not knowing is the honest default.
            _AUTHORED_TRACKING_KEY: (
                _AUTHORED_TRACKED
                if result_data.get(_AUTHORED_TRACKING_KEY) == _AUTHORED_TRACKED
                else _AUTHORED_NOT_TRACKED
            ),
            # How many shell commands ran. A file written by a shell command
            # never reaches the list above, so a reader can say why an empty
            # list may still not be the whole story. ``None`` when unknown.
            _AUTHORED_SHELL_COUNT_KEY: _nonnegative_exact_int(
                result_data.get(_AUTHORED_SHELL_COUNT_KEY)
            ),
            "tests_written": sorted(list(set(result_data.get("tests_written", [])))),
            # 13 October 2026: where the listed paths came from (see
            # ``TaskWorkStreamParser.__init__``). Read only by
            # ``_set_aside_written_then_removed`` when the report is built.
            "confirmed_write_paths": sorted(
                {
                    p
                    for p in (result_data.get("confirmed_write_paths") or [])
                    if isinstance(p, str) and p
                }
            ),
            "named_in_words_paths": sorted(
                {
                    p
                    for p in (result_data.get("named_in_words_paths") or [])
                    if isinstance(p, str) and p
                }
            ),
            "unconfirmed_write_paths": sorted(
                {
                    p
                    for p in (result_data.get("unconfirmed_write_paths") or [])
                    if isinstance(p, str) and p
                }
            ),
            "summary": self._generate_summary(result_data),
        }

        # TASK-VPR-003: Add SDK turn ceiling data to results
        sdk_turns_used_val = _nonnegative_exact_int(
            result_data.get("sdk_turns_used")
        )
        sdk_max_turns_val = _nonnegative_exact_int(
            result_data.get("sdk_max_turns")
        )
        sdk_turns_supported = result_data.get("sdk_turns_supported")
        if type(sdk_turns_supported) is not bool:
            sdk_turns_supported = sdk_max_turns_val is not None
        sdk_ceiling_hit = (
            sdk_turns_used_val >= sdk_max_turns_val
            if sdk_turns_supported
            and sdk_turns_used_val is not None
            and sdk_max_turns_val is not None
            else None
        )
        results["sdk_turns"] = {
            "turns_used": sdk_turns_used_val if sdk_turns_supported else None,
            "max_turns": sdk_max_turns_val if sdk_turns_supported else None,
            "ceiling_hit": sdk_ceiling_hit,
            "supported": sdk_turns_supported,
            "limit_kind": "sdk_turns" if sdk_turns_supported else "unsupported",
        }
        if isinstance(runtime_evidence, dict):
            results["runtime_evidence"] = runtime_evidence

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

        # R1 DE-WIRE (Rich 08-14): the BDD oracle invocation (TASK-BDD-E8954)
        # is removed — task_work_results no longer carries a bdd_results key.
        # bdd_runner.py stays on disk unreferenced until R2 deletes it.

        # R1 DE-WIRE (Rich 08-14): the BDD authoring-sweep invocation
        # (TASK-AB-BDDAUTHOR01) is removed — task_work_results no longer
        # carries a bdd_authoring_sweep key.

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

        task_type = (
            result_data.get("task_type")
            if isinstance(result_data.get("task_type"), str)
            else self._lookup_task_type(task_id)
        )
        if task_type is not None:
            results["task_type"] = task_type

        # Write results to file
        self._apply_scope_inventory(results)
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
        self._original_invocation_failure = {"type": error_type, "message": error,
            "task_id": task_id, "phase": "player",
            "scope_id": getattr(getattr(self, "task_work_scope", None), "scope_id", None)}
        # Ensure results directory exists (uses centralized paths)
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)

        results_file = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

        # Build failure results matching Coach expectations
        results: Dict[str, Any] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "completed": False,
            "success": False,
            "implementation_mode": "task-work",
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
        self._apply_scope_inventory(results)
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"Wrote failure results to {results_file}")

        return results_file

    def _write_recovered_task_work_failure(
        self,
        task_id: str,
        player_report: Dict[str, Any],
        original_error: Optional[str],
    ) -> Path:
        """Attach recovered partial state without converting a timeout to success.

        The task-work invocation writes the authoritative failure receipt
        before state recovery inspects the worktree. Recovery can prove useful
        files and tests exist, but it cannot prove the interrupted Phases 3-5
        completed. Keep the original failure fields and phase record while
        adding bounded evidence for Coach feedback and the next Player turn.
        """
        TaskArtifactPaths.ensure_autobuild_dir(task_id, self.worktree_path)
        results_file = TaskArtifactPaths.task_work_results_path(
            task_id, self.worktree_path
        )

        results: Dict[str, Any] = {}
        try:
            loaded = json.loads(results_file.read_text())
            if isinstance(loaded, dict):
                results = loaded
        except (OSError, json.JSONDecodeError):
            pass

        mode = player_report.get("original_failure", {}).get("mode") or results.get("implementation_mode") or "task-work"
        if mode == "direct":
            self._write_direct_mode_results(task_id, player_report, success=False, error=original_error)
            results = json.loads(results_file.read_text())
        elif not results or results.get("success") is not False:
            self._write_failure_results(
                task_id,
                original_error or "task-work invocation failed",
                player_report.get("original_failure", {}).get("type", "ExecutionError"),
            )
            results = json.loads(results_file.read_text())

        recovery_metadata = player_report.get("_recovery_metadata")
        if not isinstance(recovery_metadata, dict):
            recovery_metadata = {}

        def _merged_paths(field: str) -> List[str]:
            existing = results.get(field)
            recovered = player_report.get(field)
            return sorted(
                {
                    str(path)
                    for group in (existing, recovered)
                    if isinstance(group, list)
                    for path in group
                    if isinstance(path, str) and path
                }
            )

        # These status fields remain authoritative even when recovered tests
        # passed. A timed-out implementation has not completed or passed.
        results["original_failure"] = player_report.get("original_failure", {})
        results["completed"] = False
        results["success"] = False
        results["implementation_mode"] = mode
        results["phases"] = (
            results.get("phases")
            if isinstance(results.get("phases"), dict)
            else {}
        )
        quality_gates = results.get("quality_gates")
        if not isinstance(quality_gates, dict):
            quality_gates = {}
        quality_gates["all_passed"] = False
        results["quality_gates"] = quality_gates
        results["files_modified"] = _merged_paths("files_modified")
        results["files_created"] = _merged_paths("files_created")
        results["tests_written"] = _merged_paths("tests_written")

        preserved_error = results.get("error")
        if not isinstance(preserved_error, str) or not preserved_error:
            preserved_error = original_error or "task-work invocation failed"
            results["error"] = preserved_error
        results.setdefault("error_type", player_report.get("original_failure", {}).get("type", "ExecutionError"))

        results["recovery"] = {
            "state_recovered": True,
            "completion_claimed": False,
            "detection_method": recovery_metadata.get("detection_method"),
            "tests_run": bool(player_report.get("tests_run")),
            "tests_passed": bool(player_report.get("tests_passed")),
            "test_count": player_report.get("test_count", 0),
            "requirements_addressed": player_report.get(
                "requirements_addressed", []
            ),
            "partial_data": player_report.get("partial_data"),
            "original_error": preserved_error,
        }
        results["_synthetic"] = True
        results["summary"] = (
            f"Failed: {results.get('error_type', 'ExecutionError')} - "
            f"{preserved_error}. Partial work was recovered for the next turn; "
            "completion was not established."
        )

        self._apply_scope_inventory(results)
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(
            "Preserved failed task-work receipt with recovered partial state at %s",
            results_file,
        )
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
