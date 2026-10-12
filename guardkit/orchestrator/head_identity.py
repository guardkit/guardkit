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
import stat
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


# Tells this process's lines from an earlier process that had the same pid.
_SESSION = uuid.uuid4().hex[:12]


def _identity() -> Dict[str, Any]:
    """Who is writing: the build (Forge exports it) and the process."""
    return {
        "build_id": os.environ.get("GUARDKIT_RUN_OWNER") or None,
        "pid": os.getpid(),
        "session": _SESSION,
    }


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # it exists; it is just not ours to signal
    except OSError:
        return False
    return True


def _stale_unfinished(start: Dict[str, Any]) -> bool:
    """A start with no end that cannot still be running in this build.

    Its process is gone (a crash, or an earlier build in a reused worktree);
    or it carries this process's pid but was written by an earlier process
    that had the same pid; or it belongs to a different build. Such a line
    would otherwise count as overlapping every later invocation for ever.
    """
    pid = start.get("pid")
    if not _pid_alive(pid):
        return True
    if pid == os.getpid() and start.get("session") != _SESSION:
        return True
    mine = os.environ.get("GUARDKIT_RUN_OWNER") or None
    theirs = start.get("build_id")
    return bool(mine and theirs and mine != theirs)


def _now() -> Dict[str, Any]:
    at = time.time()
    return {
        "at": at,
        "at_utc": datetime.fromtimestamp(at, tz=timezone.utc).isoformat(),
    }


#: What a line that could not take the record's lock in time says.
NOT_RECORDED_BUSY = "not recorded: evidence file busy"
RECORDED = "recorded"

# The record's lock is taken without waiting, retried for at most this long.
# It is written around every agent invocation and inside checkpoint
# serialisation, so evidence must never hold either up for longer.
_LOCK_DEADLINE_S = 2.0
_LOCK_RETRY_S = 0.05


#: What a line that could not be written or read in time says.
NOT_RECORDED_UNAVAILABLE = "not recorded: evidence file unavailable"
NOT_RECORDED_TIMED_OUT = "not recorded: evidence file timed out"

# Every read and write of the record runs behind the shared evidence boundary
# (``run_evidence.within_bound``) and the caller waits at most this long: the
# record is written around every agent invocation and inside checkpoint
# serialisation, so a FIFO, a stalled filesystem or a held lock in its place
# must never hold either up.
_IO_BOUND_S = _LOCK_DEADLINE_S + 1.0
# HEAD is read with git for the record; the caller waits at most this long.
_HEAD_BOUND_S = 5.0
# Only the end of the record is read back: overlaps are recent by nature.
_READ_TAIL_BYTES = 1024 * 1024


def _bounded(work, seconds: float, *, what: str, on_failure):
    from guardkit.orchestrator.run_evidence import within_bound

    return within_bound(work, seconds, what=what, on_failure=on_failure)


def _open_record(path: Path, flags: int) -> int:
    """Open the record without following a link and without waiting; the
    opened file must itself be a regular file. Raises ``OSError``."""
    fd = os.open(
        path,
        flags | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        0o644,
    )
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("the record is not a regular file")
    except BaseException:
        os.close(fd)
        raise
    return fd


def _append_unbounded(path: Path, line: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = _open_record(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    try:
        give_up_at = time.monotonic() + _LOCK_DEADLINE_S
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= give_up_at:
                    return NOT_RECORDED_BUSY
                time.sleep(_LOCK_RETRY_S)
        try:
            view = memoryview(line)
            while view:
                written = os.write(fd, view)
                view = view[written:]
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
        return RECORDED
    finally:
        os.close(fd)


def _append_status(worktree: Path, entry: Dict[str, Any]) -> str:
    """Append one JSON line under an exclusive lock; say how it went.

    The whole append (a race-safe open of a regular file, a lock asked for
    without blocking and retried for at most ``_LOCK_DEADLINE_S``, the write)
    runs behind the shared evidence boundary, so the caller is back within
    ``_IO_BOUND_S`` whatever is in the record's place. Returns ``RECORDED``,
    ``NOT_RECORDED_BUSY``, ``NOT_RECORDED_UNAVAILABLE`` (with why) or
    ``NOT_RECORDED_TIMED_OUT``. Never raises.
    """
    path = record_path(worktree)
    try:
        line = (json.dumps(entry, sort_keys=True) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        logger.warning("head identity: could not encode a line for %s: %s", path, exc)
        return f"{NOT_RECORDED_UNAVAILABLE} ({type(exc).__name__}: {exc})"

    def _failed(exc: Optional[BaseException]) -> str:
        return (
            NOT_RECORDED_TIMED_OUT
            if exc is None
            else f"{NOT_RECORDED_UNAVAILABLE} ({type(exc).__name__}: {exc})"
        )

    status = _bounded(
        lambda: _append_unbounded(path, line),
        _IO_BOUND_S,
        what="writing the head-identity record",
        on_failure=_failed,
    )
    if status != RECORDED:
        logger.warning("head identity: %s for %s; this line is dropped.", status, path)
    return status


def _append(worktree: Path, entry: Dict[str, Any]) -> bool:
    """Append one JSON line; True when it was written. Never raises."""
    return _append_status(worktree, entry) == RECORDED


def _read_tail_unbounded(path: Path) -> bytes:
    fd = _open_record(path, os.O_RDONLY)
    try:
        size = os.fstat(fd).st_size
        start = max(0, size - _READ_TAIL_BYTES)
        os.lseek(fd, start, os.SEEK_SET)
        chunks: List[bytes] = []
        remaining = size - start
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if start > 0:
            # The first line read is probably cut; drop it.
            data = data.split(b"\n", 1)[1] if b"\n" in data else b""
        return data
    finally:
        os.close(fd)


def read_entries(worktree: Path) -> List[Dict[str, Any]]:
    """The readable lines at the end of the record (at most the last
    ``_READ_TAIL_BYTES``), in order; ``[]`` when there is none, or when it
    could not be read within the shared evidence boundary. Never raises."""
    path = record_path(worktree)

    def _failed(exc: Optional[BaseException]) -> bytes:
        if not isinstance(exc, FileNotFoundError):
            logger.warning(
                "head identity: %s for %s; read as empty.",
                NOT_RECORDED_TIMED_OUT if exc is None else NOT_RECORDED_UNAVAILABLE,
                path,
            )
        return b""

    data = _bounded(
        lambda: _read_tail_unbounded(path),
        _IO_BOUND_S,
        what="reading the head-identity record",
        on_failure=_failed,
    )
    entries: List[Dict[str, Any]] = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _read_head_for_record(worktree: Path) -> Dict[str, Optional[str]]:
    """``read_head`` for the record only, behind the shared boundary."""
    return _bounded(
        lambda: read_head(worktree),
        _HEAD_BOUND_S,
        what="reading HEAD for the head-identity record",
        on_failure=lambda _exc: {"symbolic_ref": "unreadable", "head": "unreadable"},
    )


def _is_recorded_worktree(worktree: Optional[Path], *, require_record: bool = False) -> bool:
    """``_is_build_worktree`` (and, if asked, "a record exists") behind the
    shared boundary: a metadata call on a stalled filesystem answers False."""
    if worktree is None:
        return False

    def _check() -> bool:
        if not _is_build_worktree(worktree):
            return False
        return (not require_record) or record_path(Path(worktree)).is_file()

    return bool(_bounded(
        _check, _IO_BOUND_S, what="checking the build worktree",
        on_failure=lambda _exc: False,
    ))


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
    if not _is_recorded_worktree(worktree):
        return None
    try:
        worktree = Path(worktree)
        before = _read_head_for_record(worktree)
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
        if finished is None and _stale_unfinished(start):
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
        after = _read_head_for_record(token.worktree)
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
        # Whether the line reached the record: the entry handed back says so.
        entry["record_status"] = _append_status(token.worktree, entry)
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
    if not _is_recorded_worktree(worktree, require_record=only_if_recorded):
        return False
    worktree = Path(worktree)
    try:
        entry = {
            "event": "git_operation",
            "actor": actor,
            "operation": operation,
            "task_id": task_id,
            **_now(),
            **_identity(),
            **_read_head_for_record(worktree),
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
    """The branch every checkpoint of a build must land on.

    Decided ONCE, when the build starts — before its first wave, before any
    agent has run — and handed to every task (``FeatureOrchestrator``). It is
    never re-read at a later task's start: by then an agent may have moved
    HEAD, and adopting wherever HEAD happens to be would bless the move. A
    later task that starts on any other branch is refused at its checkpoint.

    The branch the worktree was declared with (``declared``) wins: it is the
    branch the candidate is merged from, and GuardKit always creates or reuses
    the inner worktree on it (Forge's repair branch is only ever a base
    branch). HEAD's own branch is used only when nothing is declared. If HEAD
    is on another branch already — say a resumed build whose worktree was
    left on a branch an agent made — that is logged now and refused at the
    first checkpoint, never adopted. When neither is known the result is
    ``None`` and an error is logged; the caller then refuses checkpoints
    rather than committing unchecked.
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
            "must land on %s, so they will be refused until HEAD is back on it.",
            worktree, attached, declared, declared,
        )
    if not (attached or declared):
        logger.error(
            "No feature branch could be determined for %s: HEAD is not on a "
            "branch and none was declared. Checkpoints will be refused.",
            worktree,
        )
    return declared or attached
