"""Where a build worktree's HEAD was, before and after each agent ran.

12 October 2026, after build 0D7C. It finished with its checkout detached at
a later checkpoint while its branch still named an older commit, so the merge
guard refused it. The reflog showed a stash-like reset, then a checkout to the
baseline and back by commit ID, inside task three's first turn. Who did that
was never established: several agents with shell access were running in that
worktree, and some factory code also runs checkouts.

The protection itself is at the checkpoint (``worktree_checkpoints``), where
the damage would be committed. This module only keeps the evidence that would
name the actor next time. It never stops anything.

* Before and after every agent invocation (Player, Coach, specialists, the
  Coach's test runner, the design phase) it writes one line each to
  ``.guardkit/autobuild/head-identity.jsonl`` in the worktree: the symbolic
  ref and the commit HEAD named, the build, task, turn and role, and the
  process. Parallel tasks share one worktree, so the record is shared too.
* The "after" line lists every other invocation whose time overlapped this
  one, and every factory git operation recorded in the interval. A change it
  sees is attributed to "this invocation or an overlapping one", never to one
  phase alone when others overlapped. Another task's checkpoint legitimately
  advances the branch during an invocation; the record says so instead of
  calling it a fault.
* Factory git operations that can move a worktree's HEAD (the checkpoint, and
  GuardKit's branch checkouts for a merge) write a line too, with the build
  and task they acted for, so a later reading can tell them from an agent.

The record sits under ``.guardkit/autobuild/``, which the per-turn change
measurement already treats as the orchestrator's own bookkeeping. Writing it
never raises: a record that cannot be written is logged and skipped.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

# The record, relative to the worktree.
RECORD_RELATIVE_PATH = Path(".guardkit") / "autobuild" / "head-identity.jsonl"

# How long each read of HEAD may take.
_GIT_TIMEOUT_S = 10

# The words an observed change is attributed with when others overlapped.
ATTRIBUTION_OVERLAPPING = "this invocation or an overlapping one"
ATTRIBUTION_ALONE = (
    "this invocation, or something outside every recorded invocation "
    "(no other recorded invocation overlapped it)"
)


def record_path(worktree: Path) -> Path:
    """The record file for ``worktree``."""
    return Path(worktree) / RECORD_RELATIVE_PATH


def _is_build_worktree(worktree: Optional[Path]) -> bool:
    """A worktree the factory builds in has a ``.guardkit`` folder."""
    return worktree is not None and (Path(worktree) / ".guardkit").is_dir()


def _git(worktree: Path, *args: str) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("head identity: git %s failed in %s: %s", args, worktree, exc)
        return None


def read_head(worktree: Path) -> Dict[str, Optional[str]]:
    """The symbolic ref HEAD is attached to (``None`` when detached) and the
    commit it names. A value git could not give is ``"unreadable"``."""
    symbolic: Optional[str] = "unreadable"
    proc = _git(worktree, "symbolic-ref", "-q", "HEAD")
    if proc is not None:
        if proc.returncode == 0:
            symbolic = proc.stdout.strip() or None
        elif proc.returncode == 1:
            symbolic = None  # detached
    head: Optional[str] = "unreadable"
    proc = _git(worktree, "rev-parse", "HEAD")
    if proc is not None and proc.returncode == 0:
        head = proc.stdout.strip() or "unreadable"
    return {"symbolic_ref": symbolic, "head": head}


def _identity() -> Dict[str, Any]:
    """Who is writing: the build (Forge exports it) and the process."""
    return {
        "build_id": os.environ.get("GUARDKIT_RUN_OWNER") or None,
        "pid": os.getpid(),
    }


def _now() -> Dict[str, Any]:
    at = time.time()
    return {
        "at": at,
        "at_utc": datetime.fromtimestamp(at, tz=timezone.utc).isoformat(),
    }


def _append(worktree: Path, entry: Dict[str, Any]) -> bool:
    """Append one JSON line under an exclusive lock. Never raises."""
    path = record_path(worktree)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
                handle.flush()
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("head identity: could not write %s: %s", path, exc)
        return False


def read_entries(worktree: Path) -> List[Dict[str, Any]]:
    """Every readable line of the record, in order; ``[]`` when there is none."""
    path = record_path(worktree)
    entries: List[Dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return entries
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


@dataclass
class InvocationToken:
    """What the "before" line recorded, kept for the "after" line."""

    invocation_id: str
    worktree: Path
    role: str
    task_id: Optional[str]
    turn: Optional[int]
    started_at: float
    before: Dict[str, Optional[str]]


def invocation_started(
    worktree: Optional[Path],
    *,
    role: str,
    task_id: Optional[str] = None,
    turn: Optional[int] = None,
) -> Optional[InvocationToken]:
    """Write the "before" line. ``None`` (nothing written) outside a build
    worktree or when anything goes wrong."""
    if not _is_build_worktree(worktree):
        return None
    try:
        worktree = Path(worktree)
        before = read_head(worktree)
        stamp = _now()
        token = InvocationToken(
            invocation_id=f"{os.getpid()}-{uuid.uuid4().hex[:12]}",
            worktree=worktree,
            role=role,
            task_id=task_id,
            turn=turn,
            started_at=stamp["at"],
            before=before,
        )
        _append(worktree, {
            "event": "invocation_start",
            "invocation_id": token.invocation_id,
            "role": role,
            "task_id": task_id,
            "turn": turn,
            **stamp,
            **_identity(),
            **before,
        })
        return token
    except Exception as exc:  # noqa: BLE001 — evidence only, never a stop
        logger.warning("head identity: could not record an invocation start: %s", exc)
        return None


def _overlapping(
    entries: List[Dict[str, Any]], token: InvocationToken, ended_at: float
) -> List[Dict[str, Any]]:
    """Other invocations whose time overlapped ``token``'s, from the record."""
    starts: Dict[str, Dict[str, Any]] = {}
    ends: Dict[str, float] = {}
    for entry in entries:
        ident = entry.get("invocation_id")
        if not isinstance(ident, str) or ident == token.invocation_id:
            continue
        if entry.get("event") == "invocation_start":
            starts[ident] = entry
        elif entry.get("event") == "invocation_end":
            at = entry.get("at")
            if isinstance(at, (int, float)):
                ends[ident] = float(at)
    overlapping: List[Dict[str, Any]] = []
    for ident, start in starts.items():
        began = start.get("at")
        if not isinstance(began, (int, float)) or began > ended_at:
            continue
        finished = ends.get(ident)
        if finished is not None and finished < token.started_at:
            continue
        overlapping.append({
            "invocation_id": ident,
            "role": start.get("role"),
            "task_id": start.get("task_id"),
            "turn": start.get("turn"),
            "build_id": start.get("build_id"),
            "pid": start.get("pid"),
            "ended": finished is not None,
        })
    return overlapping


def _git_operations_between(
    entries: List[Dict[str, Any]], started_at: float, ended_at: float
) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for entry in entries:
        at = entry.get("at")
        if (
            entry.get("event") == "git_operation"
            and isinstance(at, (int, float))
            and started_at <= at <= ended_at
        ):
            found.append({
                key: entry.get(key)
                for key in ("actor", "operation", "task_id", "build_id", "at_utc")
            })
    return found


def invocation_finished(token: Optional[InvocationToken]) -> Optional[Dict[str, Any]]:
    """Write the "after" line and return it. Logs a warning, never raises and
    never stops anything, when HEAD or its branch changed."""
    if token is None:
        return None
    try:
        after = read_head(token.worktree)
        stamp = _now()
        entries = read_entries(token.worktree)
        overlapping = _overlapping(entries, token, stamp["at"])
        git_operations = _git_operations_between(
            entries, token.started_at, stamp["at"]
        )
        ref_changed = after["symbolic_ref"] != token.before["symbolic_ref"]
        head_changed = after["head"] != token.before["head"]
        attribution = None
        if ref_changed or head_changed:
            attribution = ATTRIBUTION_OVERLAPPING if overlapping else ATTRIBUTION_ALONE
        entry = {
            "event": "invocation_end",
            "invocation_id": token.invocation_id,
            "role": token.role,
            "task_id": token.task_id,
            "turn": token.turn,
            **stamp,
            **_identity(),
            **after,
            "before": token.before,
            "symbolic_ref_changed": ref_changed,
            "head_changed": head_changed,
            "overlapping_invocations": overlapping,
            "git_operations_during": git_operations,
            "attribution": attribution,
        }
        _append(token.worktree, entry)
        if ref_changed:
            # Plain words for the operator. Never a stop: the checkpoint is
            # where a detached or switched HEAD is refused.
            logger.warning(
                "[%s] HEAD's branch changed during the %s invocation (turn %s): "
                "before %s at %s, after %s at %s. Attributed to %s%s.",
                token.task_id, token.role, token.turn,
                token.before["symbolic_ref"] or "detached", token.before["head"],
                after["symbolic_ref"] or "detached", after["head"],
                attribution,
                (
                    ": " + ", ".join(
                        f"{o['role']} of {o['task_id']} turn {o['turn']}"
                        for o in overlapping
                    )
                    if overlapping else ""
                ),
            )
        return entry
    except Exception as exc:  # noqa: BLE001 — evidence only, never a stop
        logger.warning("head identity: could not record an invocation end: %s", exc)
        return None


async def observe_invocation(
    stream: AsyncIterator[Any],
    worktree: Optional[Path],
    *,
    role: str,
    task_id: Optional[str] = None,
    turn: Optional[int] = None,
) -> AsyncIterator[Any]:
    """Pass a harness event stream through unchanged, recording HEAD around it.

    The "before" line is written when the stream is first read, which is when
    the harness starts the agent; the "after" line when the stream ends or is
    closed, however that happens. The wrapped stream is closed here, so a
    caller's ``aclosing`` still finalises it.
    """
    token = invocation_started(worktree, role=role, task_id=task_id, turn=turn)
    try:
        async for event in stream:
            yield event
    finally:
        try:
            closer = getattr(stream, "aclose", None)
            if closer is not None:
                await closer()
        finally:
            invocation_finished(token)


def record_git_operation(
    worktree: Optional[Path],
    *,
    actor: str,
    operation: str,
    task_id: Optional[str] = None,
    only_if_recorded: bool = False,
    detail: Optional[Dict[str, Any]] = None,
) -> bool:
    """Write one line for a factory git operation run in ``worktree``.

    ``only_if_recorded`` writes it only where agent invocations have already
    been recorded — that is, in a build's worktree — so an operation run in a
    repository's main copy leaves no record there. Returns whether a line was
    written. Never raises.
    """
    if not _is_build_worktree(worktree):
        return False
    worktree = Path(worktree)
    if only_if_recorded and not record_path(worktree).is_file():
        return False
    try:
        entry = {
            "event": "git_operation",
            "actor": actor,
            "operation": operation,
            "task_id": task_id,
            **_now(),
            **_identity(),
            **read_head(worktree),
        }
        if detail:
            entry["detail"] = detail
        return _append(worktree, entry)
    except Exception as exc:  # noqa: BLE001 — evidence only, never a stop
        logger.warning("head identity: could not record a git operation: %s", exc)
        return False


def expected_checkpoint_branch(
    worktree: Optional[Path], declared: Optional[str]
) -> Optional[str]:
    """The branch a task's checkpoints must land on, decided at task start.

    The branch HEAD is attached to when the task starts is the observed fact,
    so it wins; the branch the worktree was declared with (``declared``) is
    used when HEAD is already detached, or cannot be read. A disagreement is
    logged. ``None`` (no check) when neither is known.
    """
    declared = declared if isinstance(declared, str) and declared else None
    attached: Optional[str] = None
    if worktree is not None and (Path(worktree) / ".git").exists():
        symbolic = read_head(Path(worktree))["symbolic_ref"]
        if symbolic and symbolic.startswith("refs/heads/"):
            attached = symbolic[len("refs/heads/"):]
    if attached and declared and attached != declared:
        logger.warning(
            "Worktree %s is on branch %s, not the declared %s; checkpoints "
            "will be kept on %s, the branch it is actually on.",
            worktree, attached, declared, attached,
        )
    return attached or declared
