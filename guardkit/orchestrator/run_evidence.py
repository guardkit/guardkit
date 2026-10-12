"""What a declared command actually ran against (repair 7, 12 October 2026).

WHY THIS EXISTS
---------------
After the four-worker trial nobody could say which dependency versions a
failing or a passing suite used, which uncommitted bytes were present when it
ran, or whether one build's fixture cleanup removed another build's
containers. The other repairs make outcomes honest; this module makes the next
diagnosis possible. It RECORDS. It never decides, changes or fails anything:
every capture error is written down as such and the command's own outcome is
untouched.

WHAT ONE RECORD HOLDS
---------------------
For one declared command GuardKit runs (the baseline probe, the independent
suite in the worktree or in its isolated copy, a smoke command, the
whole-feature check):

1. **The source the command actually ran against.** The *execution root* is
   named, which is not always the build worktree: a parallel wave runs the
   suite in an isolated copy that has no ``.git``. A content manifest of that
   root is taken immediately before and immediately after the command — every
   regular file's relative path, mode and SHA-256, and every symbolic link
   with its target (never followed).

   * Where the root is a Git worktree, the file set is Git's own: tracked and
     untracked files, with ignored files excluded
     (``git ls-files -co --exclude-standard -z``).
   * An isolated copy has no Git metadata, so its manifest covers exactly the
     files the copy holds.
   * For an isolated copy the ORIGINATING worktree's identity is recorded
     separately, at the moment of copying: its HEAD plus a tree id written
     from a temporary index over tracked and untracked files. The real index
     is never touched.

   The record says "source unchanged between start and end of the command" or
   "source changed during the command". Two observations are not a continuous
   one, and the record says that too.

2. **The resolved environment, where the project says how.** The optional
   declaration ``toolchain.environment_inventory`` (a command, read the same
   way as every other toolchain command) is run in the command's own
   directory and environment, just before the source is first observed; its
   output is kept, bounded, with a SHA-256 of the whole. There is no central
   default and no stack-specific logic: a project that declares nothing gets
   "not declared".

3. **Container activity during the command, as raw evidence only.** When a
   Docker command-line tool is reachable, the container and network events of
   the command's own start-to-end interval are kept, size-capped, with the
   observing build, task and turn. **Nothing here attributes an event to a
   command or a build.** Daemon events do not name their cause, and other
   actors (another build's fixture cleanup, say) remove containers outside any
   declared command. A missing Docker tool is "not available", never
   "no events".

OVERHEAD IS BOUNDED
-------------------
A manifest stops at :attr:`EvidenceLimits.max_files` files,
:attr:`EvidenceLimits.max_bytes` bytes hashed or
:attr:`EvidenceLimits.max_seconds` seconds, whichever comes first, and then
says "not recorded: too large" rather than slowing or failing the command.
Every subprocess this module starts has a timeout. The command's own
subprocess is never wrapped or changed.

TEST FENCE
----------
``GUARDKIT_RUN_EVIDENCE_DOCKER=0`` switches the Docker query off (recorded as
switched off, never as "no events"). The test suite sets it for every test so
no test reads a real daemon; a test about the Docker capture injects a fake.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import signal
import stat
import subprocess
import tempfile
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)


# =========================================================================
# The words a record uses
# =========================================================================

SOURCE_UNCHANGED = "source unchanged between start and end of the command"
SOURCE_CHANGED = "source changed during the command"
NOT_DECLARED = "not declared"
NOT_LOOKED_UP = "not looked up by the caller that ran this command"
NOT_AVAILABLE = "not available"
NOT_RECORDED_TOO_LARGE = "not recorded: too large"
RECORDED = "recorded"

WHAT_THE_SOURCE_CHECK_SHOWS = (
    "Two observations of the execution root, taken immediately before and "
    "immediately after the command. They do not show what the bytes were at "
    "every moment in between."
)
WHAT_THE_EVENTS_SHOW = (
    "Raw container and network events the Docker daemon reported for the "
    "command's own start-to-end interval. Daemon events do not name their "
    "cause: nothing here says which command or which build caused an event."
)
MANIFEST_ENTRY_FORMAT = [
    "relative path",
    "file mode in octal, or 'symlink', 'directory', 'missing', 'special', "
    "'unreadable'",
    "SHA-256 of the contents, or the link target, or why it could not be read",
]

#: Set by Forge per build (the build ID). Names the observing build.
RUN_OWNER_ENV = "GUARDKIT_RUN_OWNER"
#: ``0`` / ``false`` / ``off`` / ``no`` switches the Docker query off.
DOCKER_SWITCH_ENV = "GUARDKIT_RUN_EVIDENCE_DOCKER"

#: Event types kept from ``docker events``.
DOCKER_EVENT_TYPES = ("container", "network")

#: Git environment variables that would point a ``git -C <root>`` command at
#: somewhere other than ``<root>``. Removed from every git call here.
_GIT_REDIRECT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)


@dataclass(frozen=True)
class EvidenceLimits:
    """Every bound this module honours. Defaults are the production bounds."""

    max_files: int = 20_000
    max_bytes: int = 256 * 1024 * 1024
    max_seconds: float = 15.0
    inline_entries: int = 500
    changed_paths: int = 200
    git_timeout: float = 30.0
    inventory_output_bytes: int = 64 * 1024
    docker_timeout: float = 15.0
    docker_events: int = 500
    docker_bytes: int = 256 * 1024


DEFAULT_LIMITS = EvidenceLimits()


# =========================================================================
# Running a helper command (never subprocess.run — see _default_runner)
# =========================================================================


@dataclass
class HelperRun:
    """What one helper command did."""

    returncode: Optional[int]
    stdout: bytes = b""
    stderr: bytes = b""
    timed_out: bool = False


Runner = Callable[..., HelperRun]


def _default_runner(
    args: Union[str, Sequence[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: float,
    shell: bool = False,
) -> HelperRun:
    """Run one helper command with a hard timeout.

    Deliberately built on ``Popen`` rather than ``subprocess.run``: a great
    many existing tests replace ``subprocess.run`` with a scripted fake that
    expects an exact sequence of calls, and evidence capture must never take a
    slot in that sequence. The helper runs in its own session so a timeout
    kills everything it started.
    """
    proc = subprocess.Popen(  # noqa: S603 — argv or a project-declared command
        args if shell else list(args),
        cwd=str(cwd) if cwd is not None else None,
        env=dict(env) if env is not None else None,
        shell=shell,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            proc.kill()
        out, err = proc.communicate()
        return HelperRun(None, out or b"", err or b"", timed_out=True)
    return HelperRun(proc.returncode, out or b"", err or b"")


def _git_env(extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_REDIRECT_VARS}
    # Never take an optional lock on the real repository while observing it.
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env.update(extra or {})
    return env


def _first_line(data: bytes, limit: int = 300) -> str:
    text = data.decode("utf-8", errors="replace").strip()
    return text.splitlines()[0][:limit] if text else ""


def _utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# =========================================================================
# 1. The source a command ran against
# =========================================================================


class _TooLarge(Exception):
    """A manifest bound was reached."""


def is_git_worktree(root: Path) -> bool:
    """True when ``root`` itself carries Git metadata (a ``.git`` dir or file).

    Asked of the root only, on purpose: an isolated copy sits beside the
    worktree, inside the build's own clone, and must never be taken for part
    of that clone.
    """
    return (Path(root) / ".git").exists()


def _git_file_set(
    root: Path, runner: Runner, limits: EvidenceLimits
) -> Tuple[List[str], Optional[str]]:
    run = runner(
        ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
        env=_git_env(),
        timeout=limits.git_timeout,
    )
    if run.timed_out:
        raise _TooLarge(
            f"listing the files with git took longer than {limits.git_timeout:g}s"
        )
    if run.returncode != 0:
        raise RuntimeError(
            f"git ls-files exited {run.returncode}: {_first_line(run.stderr)}"
        )
    seen = set()
    paths: List[str] = []
    for raw in run.stdout.split(b"\0"):
        if not raw:
            continue
        rel = os.fsdecode(raw)
        if rel not in seen:  # an unmerged path is listed once per stage
            seen.add(rel)
            paths.append(rel)
            if len(paths) > limits.max_files:
                raise _TooLarge(f"more than {limits.max_files} files")
    head_run = runner(
        ["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
        env=_git_env(),
        timeout=limits.git_timeout,
    )
    head = (
        head_run.stdout.decode("utf-8", errors="replace").strip() or None
        if head_run.returncode == 0
        else None
    )
    return sorted(paths), head


def _walk_file_set(root: Path, limits: EvidenceLimits, deadline: float) -> List[str]:
    """Every entry under ``root``, never following a symbolic link."""
    paths: List[str] = []
    unreadable: List[str] = []

    def _onerror(exc: OSError) -> None:
        if exc.filename:
            unreadable.append(str(exc.filename))

    for dirpath, dirnames, filenames in os.walk(
        str(root), followlinks=False, onerror=_onerror
    ):
        if time.monotonic() > deadline:
            raise _TooLarge(f"listing took longer than {limits.max_seconds:g}s")
        rel_dir = os.path.relpath(dirpath, str(root))
        keep_dirs = []
        for name in dirnames:
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                # A link to a directory is recorded as a link, never entered.
                paths.append(os.path.normpath(os.path.join(rel_dir, name)))
            else:
                keep_dirs.append(name)
        dirnames[:] = keep_dirs
        for name in filenames:
            paths.append(os.path.normpath(os.path.join(rel_dir, name)))
        if len(paths) > limits.max_files:
            raise _TooLarge(f"more than {limits.max_files} files")
    for full in unreadable:
        rel = os.path.relpath(full, str(root))
        if rel != ".":
            paths.append(rel)
    return sorted(set(p.replace(os.sep, "/") for p in paths))


def _describe(
    root: Path, paths: Sequence[str], limits: EvidenceLimits, deadline: float
) -> List[List[str]]:
    entries: List[List[str]] = []
    hashed = 0
    for rel in paths:
        if time.monotonic() > deadline:
            raise _TooLarge(f"hashing took longer than {limits.max_seconds:g}s")
        full = os.path.join(str(root), rel)
        try:
            st = os.lstat(full)
        except FileNotFoundError:
            entries.append([rel, "missing", ""])
            continue
        except OSError as exc:
            entries.append([rel, "unreadable", type(exc).__name__])
            continue
        if stat.S_ISLNK(st.st_mode):
            try:
                target = os.readlink(full)
            except OSError as exc:
                target = f"<unreadable link: {type(exc).__name__}>"
            entries.append([rel, "symlink", target])
        elif stat.S_ISREG(st.st_mode):
            hashed += st.st_size
            if hashed > limits.max_bytes:
                raise _TooLarge(f"more than {limits.max_bytes} bytes to hash")
            digest = hashlib.sha256()
            try:
                with open(full, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError as exc:
                entries.append([rel, "unreadable", type(exc).__name__])
                continue
            entries.append([rel, f"{st.st_mode:o}", digest.hexdigest()])
        elif stat.S_ISDIR(st.st_mode):
            # Listed as a directory only when its contents could not be
            # listed (it could not be entered) or Git names it (a submodule).
            readable = os.access(full, os.R_OK | os.X_OK)
            entries.append([rel, "directory" if readable else "unreadable", ""])
        else:
            entries.append([rel, "special", f"{st.st_mode:o}"])
    return entries


def manifest_digest(entries: Sequence[Sequence[str]]) -> str:
    """One SHA-256 over the whole manifest, in path order."""
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: e[0]):
        digest.update("\0".join(str(part) for part in entry).encode("utf-8"))
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"


def source_manifest(
    root: Union[str, Path],
    *,
    limits: EvidenceLimits = DEFAULT_LIMITS,
    runner: Optional[Runner] = None,
    clock: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """A content manifest of ``root``. Never raises.

    The returned dict carries a private ``_entries`` list (the full manifest)
    for comparison; :class:`CommandEvidence` strips it before anything is
    written.
    """
    runner = runner or _default_runner
    root = Path(root)
    record: Dict[str, Any] = {"taken_at": _utc(clock())}
    deadline = time.monotonic() + limits.max_seconds
    try:
        if not root.is_dir():
            record["status"] = "not recorded: the directory does not exist"
            return record
        if is_git_worktree(root):
            record["file_set"] = (
                "Git worktree: tracked and untracked files, ignored files "
                "excluded (git ls-files -co --exclude-standard)"
            )
            paths, head = _git_file_set(root, runner, limits)
            record["head"] = head
        else:
            record["file_set"] = (
                "plain directory without Git metadata: every entry it holds"
            )
            paths = _walk_file_set(root, limits, deadline)
        entries = _describe(root, paths, limits, deadline)
    except _TooLarge as exc:
        record["status"] = NOT_RECORDED_TOO_LARGE
        record["limit_reached"] = str(exc)
        return record
    except Exception as exc:  # noqa: BLE001 — capture never fails a run
        record["status"] = f"not recorded: capture error ({type(exc).__name__}: {exc})"
        return record
    record["status"] = RECORDED
    record["file_count"] = len(entries)
    record["digest"] = manifest_digest(entries)
    record["_entries"] = entries
    return record


def compare_manifests(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    limit: int = DEFAULT_LIMITS.changed_paths,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """The plain-words verdict on two manifests, and what changed (bounded)."""
    if before.get("status") != RECORDED or after.get("status") != RECORDED:
        why = []
        if before.get("status") != RECORDED:
            why.append(f"before: {before.get('status')}")
        if after.get("status") != RECORDED:
            why.append(f"after: {after.get('status')}")
        return f"not compared ({'; '.join(why)})", None
    if before.get("digest") == after.get("digest"):
        return SOURCE_UNCHANGED, None
    old = {e[0]: tuple(e[1:]) for e in before.get("_entries", [])}
    new = {e[0]: tuple(e[1:]) for e in after.get("_entries", [])}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    modified = sorted(p for p in set(old) & set(new) if old[p] != new[p])
    total = len(added) + len(removed) + len(modified)
    return SOURCE_CHANGED, {
        "added": added[:limit],
        "removed": removed[:limit],
        "modified": modified[:limit],
        "total": total,
        "truncated": any(len(x) > limit for x in (added, removed, modified)),
    }


def originating_worktree_identity(
    worktree: Union[str, Path],
    *,
    limits: EvidenceLimits = DEFAULT_LIMITS,
    runner: Optional[Runner] = None,
    clock: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """HEAD plus a temporary-index tree id of ``worktree``. Never raises.

    The tree id is written from a TEMPORARY index (``GIT_INDEX_FILE``) after
    ``git add -A``, so it covers tracked and untracked files (ignored ones
    excluded) and the worktree's real index is never written. The temporary
    index starts as a copy of the real one only so that Git can skip
    re-hashing files whose stat data has not changed; the copy is read, never
    the original written.
    """
    runner = runner or _default_runner
    worktree = Path(worktree)
    record: Dict[str, Any] = {"worktree": str(worktree), "taken_at": _utc(clock())}
    if not is_git_worktree(worktree):
        record["status"] = (
            "not recorded: the originating directory is not a Git worktree"
        )
        return record
    scratch = None
    try:
        head_run = runner(
            ["git", "-C", str(worktree), "rev-parse", "--verify", "-q", "HEAD"],
            env=_git_env(),
            timeout=limits.git_timeout,
        )
        record["head"] = (
            head_run.stdout.decode("utf-8", errors="replace").strip() or None
            if head_run.returncode == 0
            else None
        )
        scratch = Path(tempfile.mkdtemp(prefix="guardkit-evidence-index-"))
        temp_index = scratch / "index"
        index_run = runner(
            ["git", "-C", str(worktree), "rev-parse", "--git-path", "index"],
            env=_git_env(),
            timeout=limits.git_timeout,
        )
        if index_run.returncode == 0:
            real_index = Path(index_run.stdout.decode("utf-8", errors="replace").strip())
            if not real_index.is_absolute():
                real_index = worktree / real_index
            if real_index.is_file():
                shutil.copyfile(str(real_index), str(temp_index))
        env = _git_env({"GIT_INDEX_FILE": str(temp_index)})
        add = runner(
            ["git", "-C", str(worktree), "add", "-A"],
            env=env,
            timeout=limits.git_timeout,
        )
        if add.timed_out or add.returncode != 0:
            record["status"] = (
                "not recorded: git add into a temporary index "
                + (
                    f"took longer than {limits.git_timeout:g}s"
                    if add.timed_out
                    else f"exited {add.returncode}: {_first_line(add.stderr)}"
                )
            )
            return record
        tree = runner(
            ["git", "-C", str(worktree), "write-tree"],
            env=env,
            timeout=limits.git_timeout,
        )
        if tree.returncode != 0:
            record["status"] = (
                f"not recorded: git write-tree exited {tree.returncode}: "
                f"{_first_line(tree.stderr)}"
            )
            return record
        record["tree_with_untracked"] = tree.stdout.decode(
            "utf-8", errors="replace"
        ).strip()
        record["status"] = RECORDED
        return record
    except Exception as exc:  # noqa: BLE001 — capture never fails a run
        record["status"] = f"not recorded: capture error ({type(exc).__name__}: {exc})"
        return record
    finally:
        if scratch is not None:
            shutil.rmtree(str(scratch), ignore_errors=True)


# =========================================================================
# 2. The resolved environment, where the project declares how
# =========================================================================


@dataclass(frozen=True)
class EvidenceRequest:
    """What the caller knows about one command it is about to run.

    ``environment_inventory`` is the project's declared inventory command,
    ``None`` when the declaration says nothing. ``inventory_looked_up`` is
    False only for a caller that did not read the declaration at all, so its
    record says exactly that instead of claiming "not declared".
    """

    kind: str
    observer: Dict[str, Any] = field(default_factory=dict)
    environment_inventory: Optional[str] = None
    inventory_timeout: int = 120
    inventory_looked_up: bool = True


_REQUESTED: "ContextVar[Optional[EvidenceRequest]]" = ContextVar(
    "guardkit_run_evidence_request", default=None
)


@contextmanager
def requested(request: Optional[EvidenceRequest]):
    """Hand ``request`` to the declared-command runner called inside.

    For runners whose signature many tests replace with fakes (the smoke
    gate): the caller states what it knows without changing the call.
    """
    token = _REQUESTED.set(request)
    try:
        yield request
    finally:
        _REQUESTED.reset(token)


def current_request() -> Optional[EvidenceRequest]:
    """The request set by the innermost :func:`requested`, if any."""
    return _REQUESTED.get()


def request_from_declaration(
    kind: str,
    declaration: Any,
    *,
    component: Any = None,
    **observer: Any,
) -> EvidenceRequest:
    """Build a request from a toolchain declaration (or ``None``).

    A selected component's own ``environment_inventory`` wins; otherwise the
    root block's. Never raises.
    """
    command: Optional[str] = None
    timeout = 120
    for source in (component, declaration):
        if source is None:
            continue
        value = getattr(source, "environment_inventory", None)
        if value:
            command = value
            timeout = int(getattr(source, "environment_inventory_timeout", 120) or 120)
            break
    return EvidenceRequest(
        kind=kind,
        observer=dict(observer),
        environment_inventory=command,
        inventory_timeout=timeout,
    )


def request_from_repo(kind: str, repo_root: Optional[Path], **observer: Any) -> EvidenceRequest:
    """Build a request by reading ``toolchain`` from the MAIN checkout.

    The same reader every repo-level declaration uses; never the build
    worktree, which the builder edits. Never raises.
    """
    declaration = None
    if repo_root is not None:
        try:
            from guardkit.orchestrator.toolchain_declaration import (
                load_toolchain_declaration,
            )

            declaration = load_toolchain_declaration(Path(repo_root))
        except Exception as exc:  # noqa: BLE001
            logger.debug("run evidence: could not read the declaration: %s", exc)
    return request_from_declaration(kind, declaration, **observer)


def run_environment_inventory(
    request: EvidenceRequest,
    *,
    cwd: Union[str, Path],
    env: Optional[Mapping[str, str]],
    limits: EvidenceLimits = DEFAULT_LIMITS,
    runner: Optional[Runner] = None,
) -> Dict[str, Any]:
    """Run the declared inventory command and keep its output. Never raises."""
    if not request.inventory_looked_up:
        return {"status": NOT_LOOKED_UP}
    command = request.environment_inventory
    if not command:
        return {"status": NOT_DECLARED}
    runner = runner or _default_runner
    record: Dict[str, Any] = {"command": command, "directory": str(cwd)}
    try:
        run = runner(
            command,
            cwd=cwd,
            env=env,
            timeout=float(request.inventory_timeout),
            shell=True,
        )
    except Exception as exc:  # noqa: BLE001 — capture never fails a run
        record["status"] = f"not recorded: capture error ({type(exc).__name__}: {exc})"
        return record
    if run.timed_out:
        record["status"] = (
            f"not recorded: timed out after {request.inventory_timeout}s"
        )
        return record
    cap = limits.inventory_output_bytes
    record.update(
        {
            "status": RECORDED,
            "exit_code": run.returncode,
            "output_sha256": hashlib.sha256(run.stdout).hexdigest(),
            "output_bytes": len(run.stdout),
            "output": run.stdout[:cap].decode("utf-8", errors="replace"),
            "output_truncated": len(run.stdout) > cap,
            "stderr_head": run.stderr[:2000].decode("utf-8", errors="replace"),
        }
    )
    return record


# =========================================================================
# 3. Container activity during the command (raw, never attributed)
# =========================================================================


@dataclass
class DockerProbe:
    """How the Docker query is made. Injectable so tests never reach a daemon."""

    runner: Runner = _default_runner
    which: Callable[[str], Optional[str]] = shutil.which
    switched_off: bool = False


def default_docker_probe() -> DockerProbe:
    raw = (os.environ.get(DOCKER_SWITCH_ENV) or "").strip().lower()
    return DockerProbe(switched_off=raw in {"0", "false", "off", "no"})


def _event_time_ns(event: Mapping[str, Any]) -> Optional[int]:
    nano = event.get("timeNano")
    if isinstance(nano, (int, float)) and nano > 0:
        return int(nano)
    secs = event.get("time")
    if isinstance(secs, (int, float)) and secs > 0:
        return int(secs) * 1_000_000_000
    return None


def docker_events_between(
    started: float,
    ended: float,
    *,
    probe: Optional[DockerProbe] = None,
    limits: EvidenceLimits = DEFAULT_LIMITS,
) -> Dict[str, Any]:
    """Container and network events from ``started`` to ``ended``. Never raises.

    The query asks the daemon for exactly that interval, and the answer is
    filtered again here by each event's own timestamp, so an event outside the
    interval is never kept whatever the daemon returns. A second-resolution
    timestamp is compared at second resolution.
    """
    probe = probe or default_docker_probe()
    record: Dict[str, Any] = {"what_this_shows": WHAT_THE_EVENTS_SHOW}
    if probe.switched_off:
        record["status"] = f"not recorded: switched off by {DOCKER_SWITCH_ENV}"
        return record
    try:
        if not probe.which("docker"):
            record["status"] = NOT_AVAILABLE
            record["reason"] = "no Docker command-line tool was found on PATH"
            return record
        argv = [
            "docker",
            "events",
            "--since",
            f"{started:.6f}",
            "--until",
            f"{ended:.6f}",
            "--format",
            "{{json .}}",
        ]
        for kind in DOCKER_EVENT_TYPES:
            argv[2:2] = ["--filter", f"type={kind}"]
        run = probe.runner(argv, timeout=limits.docker_timeout)
    except Exception as exc:  # noqa: BLE001 — capture never fails a run
        record["status"] = NOT_AVAILABLE
        record["reason"] = f"the Docker query could not start ({type(exc).__name__}: {exc})"
        return record
    if run.timed_out:
        record["status"] = NOT_AVAILABLE
        record["reason"] = f"docker events took longer than {limits.docker_timeout:g}s"
        return record
    if run.returncode != 0:
        record["status"] = NOT_AVAILABLE
        record["reason"] = (
            f"docker events exited {run.returncode}: {_first_line(run.stderr)}"
        )
        return record

    start_ns = int(started * 1_000_000_000)
    end_ns = int(ended * 1_000_000_000)
    kept: List[Dict[str, Any]] = []
    in_interval = 0
    outside = 0
    unreadable = 0
    kept_bytes = 0
    truncated = False
    for line in run.stdout.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            unreadable += 1
            continue
        if not isinstance(event, dict) or event.get("Type") not in DOCKER_EVENT_TYPES:
            outside += 1
            continue
        at = _event_time_ns(event)
        if at is None:
            unreadable += 1
            continue
        if event.get("timeNano"):
            inside = start_ns <= at <= end_ns
        else:  # second resolution only
            inside = int(started) <= at // 1_000_000_000 <= int(ended)
        if not inside:
            outside += 1
            continue
        in_interval += 1
        size = len(line.encode("utf-8"))
        if len(kept) >= limits.docker_events or kept_bytes + size > limits.docker_bytes:
            truncated = True
            continue
        kept.append(event)
        kept_bytes += size
    record.update(
        {
            "status": RECORDED,
            "events": kept,
            "events_in_interval": in_interval,
            "events_kept": len(kept),
            "truncated": truncated,
            "dropped_outside_interval_or_type": outside,
            "unreadable_lines": unreadable,
        }
    )
    return record


# =========================================================================
# One command's record
# =========================================================================


def _public_manifest(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in record.items() if not k.startswith("_")}


class CommandEvidence:
    """The record of one declared command, from just before it to just after.

    Use::

        evidence = CommandEvidence(request, command=..., execution_root=...,
                                   cwd=..., env=...).begin()
        try:
            proc = subprocess.run(...)   # the command itself, unchanged
        finally:
            receipt["run_evidence"] = evidence.finish()

    Neither ``begin`` nor ``finish`` ever raises.
    """

    def __init__(
        self,
        request: Optional[EvidenceRequest],
        *,
        command: Any,
        execution_root: Union[str, Path],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Mapping[str, str]] = None,
        execution_root_is: str = "the build worktree",
        origin: Optional[Dict[str, Any]] = None,
        runner: Optional[Runner] = None,
        docker: Optional[DockerProbe] = None,
        limits: EvidenceLimits = DEFAULT_LIMITS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.request = request or EvidenceRequest(kind="declared command", inventory_looked_up=False)
        self.command = command
        self.execution_root = Path(execution_root)
        self.cwd = Path(cwd) if cwd is not None else self.execution_root
        self.env = env
        self.execution_root_is = execution_root_is
        self.origin = origin
        self.runner = runner
        self.docker = docker
        self.limits = limits
        self.clock = clock
        self._inventory: Dict[str, Any] = {"status": "not recorded: begin() was not called"}
        self._before: Dict[str, Any] = {"status": "not recorded: begin() was not called"}
        self._started: Optional[float] = None
        self._errors: List[str] = []
        self._finished: Optional[Dict[str, Any]] = None

    def begin(self) -> "CommandEvidence":
        try:
            self._inventory = run_environment_inventory(
                self.request,
                cwd=self.cwd,
                env=self.env,
                limits=self.limits,
                runner=self.runner,
            )
        except Exception as exc:  # noqa: BLE001
            self._errors.append(f"inventory: {type(exc).__name__}: {exc}")
        try:
            self._before = source_manifest(
                self.execution_root, limits=self.limits, runner=self.runner, clock=self.clock
            )
        except Exception as exc:  # noqa: BLE001
            self._errors.append(f"source before: {type(exc).__name__}: {exc}")
        try:
            self._started = self.clock()
        except Exception as exc:  # noqa: BLE001
            self._errors.append(f"clock: {type(exc).__name__}: {exc}")
        return self

    def finish(self) -> Dict[str, Any]:
        if self._finished is not None:
            return self._finished
        try:
            self._finished = self._build()
        except Exception as exc:  # noqa: BLE001 — capture never fails a run
            self._finished = {
                "command_kind": self.request.kind,
                "capture_errors": self._errors + [f"record: {type(exc).__name__}: {exc}"],
            }
        return self._finished

    def _build(self) -> Dict[str, Any]:
        ended = self.clock()
        after = source_manifest(
            self.execution_root, limits=self.limits, runner=self.runner, clock=self.clock
        )
        verdict, changed = compare_manifests(
            self._before, after, limit=self.limits.changed_paths
        )
        entries = self._before.get("_entries") or []
        manifest_copy: Optional[Dict[str, Any]] = None
        if self._before.get("status") == RECORDED:
            manifest_copy = {
                "of": "the before observation",
                "entry_format": MANIFEST_ENTRY_FORMAT,
                "entries": entries[: self.limits.inline_entries],
                "entries_total": len(entries),
                "truncated": len(entries) > self.limits.inline_entries,
            }
        if self._started is None:
            events = {
                "what_this_shows": WHAT_THE_EVENTS_SHOW,
                "status": "not recorded: the command's start time was not taken",
            }
        else:
            events = docker_events_between(
                self._started, ended, probe=self.docker, limits=self.limits
            )
        observer = {
            "build": (os.environ.get(RUN_OWNER_ENV) or "").strip() or "not stated",
        }
        observer.update(self.request.observer)
        record: Dict[str, Any] = {
            "command_kind": self.request.kind,
            "command": self.command if isinstance(self.command, str) else list(self.command),
            "observer": observer,
            "execution_root": str(self.execution_root),
            "execution_root_is": self.execution_root_is,
            "command_directory": str(self.cwd),
            "originating_worktree": self.origin,
            "interval": {
                "started_at": _utc(self._started) if self._started else None,
                "ended_at": _utc(ended),
                "started_unix": self._started,
                "ended_unix": ended,
            },
            "environment_inventory": self._inventory,
            "source": {
                "what_this_shows": WHAT_THE_SOURCE_CHECK_SHOWS,
                "verdict": verdict,
                "before": _public_manifest(self._before),
                "after": _public_manifest(after),
                "changed_paths": changed,
                "manifest": manifest_copy,
            },
            "container_events": events,
        }
        if self._errors:
            record["capture_errors"] = list(self._errors)
        return record


def start_command_evidence(request: Optional[EvidenceRequest], **kwargs: Any) -> CommandEvidence:
    """``CommandEvidence(request, **kwargs).begin()`` that never raises."""
    try:
        return CommandEvidence(request, **kwargs).begin()
    except Exception as exc:  # noqa: BLE001
        logger.warning("run evidence could not start: %s", exc)
        return _FailedEvidence(f"{type(exc).__name__}: {exc}")


class _FailedEvidence(CommandEvidence):
    """Stands in when the evidence object itself could not be built."""

    def __init__(self, reason: str) -> None:  # noqa: D401 — no super().__init__
        self._reason = reason

    def begin(self) -> "CommandEvidence":
        return self

    def finish(self) -> Dict[str, Any]:
        return {"capture_errors": [f"evidence could not start: {self._reason}"]}


__all__ = [
    "CommandEvidence",
    "DEFAULT_LIMITS",
    "DOCKER_SWITCH_ENV",
    "DockerProbe",
    "EvidenceLimits",
    "EvidenceRequest",
    "HelperRun",
    "NOT_AVAILABLE",
    "NOT_DECLARED",
    "NOT_LOOKED_UP",
    "NOT_RECORDED_TOO_LARGE",
    "SOURCE_CHANGED",
    "SOURCE_UNCHANGED",
    "compare_manifests",
    "current_request",
    "default_docker_probe",
    "docker_events_between",
    "manifest_digest",
    "originating_worktree_identity",
    "request_from_declaration",
    "request_from_repo",
    "requested",
    "run_environment_inventory",
    "source_manifest",
    "start_command_evidence",
]
