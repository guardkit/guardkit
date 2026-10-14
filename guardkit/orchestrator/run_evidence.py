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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from guardkit.lib.project_git import unreadable_folders

logger = logging.getLogger(__name__)

# Optional open() flags, read directly from os (not through getattr) so the
# launch guard sees os used only through its attributes; 0 where absent.
try:
    _O_NOFOLLOW = os.O_NOFOLLOW
except AttributeError:  # pragma: no cover - not on every platform
    _O_NOFOLLOW = 0
try:
    _O_NONBLOCK = os.O_NONBLOCK
except AttributeError:  # pragma: no cover - not on every platform
    _O_NONBLOCK = 0


# =========================================================================
# The words a record uses
# =========================================================================

SOURCE_UNCHANGED = "source unchanged between start and end of the command"
SOURCE_CHANGED = "source changed during the command"
NOT_DECLARED = "not declared"
NOT_LOOKED_UP = "not looked up by the caller that ran this command"
NOT_AVAILABLE = "not available"
NOT_RECORDED_TOO_LARGE = "not recorded: too large"
NOT_RECORDED_TIMED_OUT = "not recorded: timed out"
NOT_RECORDED_INCOMPLETE = "not recorded: incomplete (some entries could not be read)"
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
    #: Most output kept from a helper's stdout (it is hashed in full).
    git_output_bytes: int = 16 * 1024 * 1024
    docker_output_bytes: int = 8 * 1024 * 1024


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
    #: How much stdout the helper wrote in all, and its SHA-256, when the
    #: runner streamed it (``stdout`` then holds only what was kept). ``None``
    #: from a runner that does not say; readers then use ``stdout`` itself.
    stdout_total: Optional[int] = None
    stdout_sha256: Optional[str] = None
    stdout_truncated: bool = False


Runner = Callable[..., HelperRun]

#: After a helper is killed at its limit, how long its pipes are drained
#: before they are abandoned (a ``setsid`` child can hold them open forever).
_DRAIN_SECONDS = 5.0
#: Default retention of a helper's stdout and stderr. Output beyond it is
#: read (so the helper never blocks on a full pipe) and hashed, not kept.
_DEFAULT_KEEP_BYTES = 8 * 1024 * 1024
_STDERR_KEEP_BYTES = 64 * 1024


class _Sink:
    """Keeps the first ``keep`` bytes of a stream and hashes all of it."""

    def __init__(self, keep: int) -> None:
        self.keep = max(0, int(keep))
        self.kept = bytearray()
        self.total = 0
        self.digest = hashlib.sha256()

    def add(self, chunk: bytes) -> None:
        self.total += len(chunk)
        self.digest.update(chunk)
        room = self.keep - len(self.kept)
        if room > 0:
            self.kept += chunk[:room]


def _kill_group(proc: "subprocess.Popen[bytes]") -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        try:
            proc.kill()
        except OSError:
            pass


def _default_runner(
    args: Union[str, Sequence[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: float,
    shell: bool = False,
    keep_bytes: int = _DEFAULT_KEEP_BYTES,
) -> HelperRun:
    """Run one helper command with a hard timeout and bounded output.

    Deliberately built on ``Popen`` rather than ``subprocess.run``: a great
    many existing tests replace ``subprocess.run`` with a scripted fake that
    expects an exact sequence of calls, and evidence capture must never take a
    slot in that sequence. The helper runs in its own session so a timeout
    kills everything it started.

    OUTPUT IS STREAMED. Both pipes are read as the helper writes, so it never
    blocks on a full pipe; the first ``keep_bytes`` of stdout (64 KiB of
    stderr) are kept and the whole of stdout is counted and hashed, so the
    result says how much there was and what it was without holding it.

    THE LIMIT, EXACTLY. At ``timeout`` the helper's process group is killed;
    its pipes are then drained for up to 5 seconds (``_DRAIN_SECONDS``) and
    closed, whoever still holds them (a ``setsid`` child, a daemon), and the
    process is waited on for up to 5 seconds more. So a timed-out helper
    returns at most ``timeout`` + 5 seconds after it started, and in the
    worst case ``timeout`` + 10. A helper that exits in time but leaves a
    child holding its pipes is read for at most 5 seconds after it exits.
    """
    import selectors

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
    out, err = _Sink(keep_bytes), _Sink(_STDERR_KEEP_BYTES)
    deadline = time.monotonic() + float(timeout)
    timed_out = False
    stop_reading_at: Optional[float] = None
    selector = selectors.DefaultSelector()
    try:
        selector.register(proc.stdout, selectors.EVENT_READ, out)
        selector.register(proc.stderr, selectors.EVENT_READ, err)
        while selector.get_map():
            now = time.monotonic()
            if stop_reading_at is None:
                if proc.poll() is not None:
                    stop_reading_at = now + _DRAIN_SECONDS
                elif now >= deadline:
                    timed_out = True
                    _kill_group(proc)
                    stop_reading_at = now + _DRAIN_SECONDS
            elif now >= stop_reading_at:
                break
            horizon = stop_reading_at if stop_reading_at is not None else deadline
            for key, _events in selector.select(timeout=max(0.0, min(horizon - now, 0.2))):
                try:
                    chunk = os.read(key.fd, 65536)
                except OSError:
                    chunk = b""
                if chunk:
                    key.data.add(chunk)
                else:
                    selector.unregister(key.fileobj)
    finally:
        selector.close()
        for stream in (proc.stdout, proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
    if not timed_out and proc.poll() is None:
        # Both pipes closed but the helper is still running.
        try:
            proc.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc)
    if timed_out:
        try:
            proc.wait(timeout=_DRAIN_SECONDS)
        except subprocess.TimeoutExpired:
            pass
    return HelperRun(
        None if timed_out else proc.returncode,
        bytes(out.kept),
        bytes(err.kept),
        timed_out=timed_out,
        stdout_total=out.total,
        stdout_sha256=out.digest.hexdigest(),
        stdout_truncated=out.total > len(out.kept),
    )


def _git_runner(
    args: Union[str, Sequence[str]],
    *,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: float,
    shell: bool = False,
    keep_bytes: int = _DEFAULT_KEEP_BYTES,
) -> HelperRun:
    """The bounded runner, for git: the command goes through the factory's git
    helper first (fixed environment and settings, no project program).

    Of ``env`` only the names the helper takes from a caller are passed on
    (the temporary index, and no optional locks). Git's own error text is
    replaced: ``stderr`` holds the helper's sentence on failure, and on
    success only the names of folders git could not open, which is what makes
    a listing incomplete.
    """
    from guardkit.lib import project_git

    if shell or isinstance(args, str):
        raise ValueError("git commands are given as a list")
    extra = {
        name: value
        for name, value in (env or {}).items()
        if name in ("GIT_INDEX_FILE", "GIT_OPTIONAL_LOCKS")
    }
    prepared = project_git.prepare_git(list(args), cwd=cwd, env=extra, timeout=timeout)
    if prepared.refusal or prepared.argv is None:
        return HelperRun(
            project_git.REFUSED_EXIT_CODE, b"", (prepared.refusal or "").encode()
        )
    # An inline literal ``["git", ...]``: git is found through the helper's
    # fixed PATH, whose first folder is the one git was found in.
    run = _default_runner(
        ["git", *prepared.argv[1:]], cwd=cwd, env=prepared.env, timeout=timeout,
        keep_bytes=keep_bytes,
    )
    if run.timed_out:
        run.stderr = project_git.timeout_sentence(prepared.label, timeout).encode()
    elif run.returncode != 0:
        run.stderr = project_git.failure_sentence(prepared.label, run.returncode).encode()
    else:
        run.stderr = "".join(
            f"could not open directory '{folder}'\n"
            for folder in project_git.unreadable_folders(run.stderr)
        ).encode()
    return run


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


class _TimedOut(Exception):
    """A helper command used to build the manifest ran out of time."""


def is_git_worktree(root: Path) -> bool:
    """True when ``root`` itself carries Git metadata (a ``.git`` dir or file).

    Asked of the root only, on purpose: an isolated copy sits beside the
    worktree, inside the build's own clone, and must never be taken for part
    of that clone.
    """
    # ``os.path.exists`` answers False, never raises, for a root that cannot
    # be looked into; the walk then reports that root as unreadable.
    return os.path.exists(os.path.join(str(root), ".git"))




def _git_file_set(
    root: Path, runner: Runner, limits: EvidenceLimits
) -> Tuple[List[str], Optional[str], List[str]]:
    run = runner(
        ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
        env=_git_env(),
        timeout=limits.git_timeout,
        keep_bytes=limits.git_output_bytes,
    )
    if run.timed_out:
        raise _TimedOut(
            f"listing the files with git took longer than {limits.git_timeout:g}s"
        )
    if run.returncode != 0:
        raise RuntimeError(
            f"git ls-files exited {run.returncode}: {_first_line(run.stderr)}"
        )
    if run.stdout_truncated:
        raise _TooLarge(f"the file list is over {limits.git_output_bytes} bytes")
    # Git lists what it can and only WARNS about a directory it could not
    # open (exit 0), so that warning is what makes the listing incomplete.
    unreadable = unreadable_folders(run.stderr)
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
    return sorted(paths), head, unreadable


def _walk_file_set(
    root: Path, limits: EvidenceLimits, deadline: float
) -> Tuple[List[str], List[str]]:
    """Every entry under ``root``, never following a symbolic link.

    Returns the paths and the directories (``"."`` for the root itself) whose
    contents could not be listed.
    """
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
    unlisted = sorted(
        {os.path.relpath(full, str(root)).replace(os.sep, "/") for full in unreadable}
    )
    for rel in unlisted:
        if rel != ".":
            paths.append(rel)
    return sorted(set(p.replace(os.sep, "/") for p in paths)), unlisted


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
                # A link whose target could not be read is an unread entry,
                # so the manifest is incomplete and is never compared.
                entries.append([rel, "unreadable", f"link target: {type(exc).__name__}"])
                continue
            entries.append([rel, "symlink", target])
        elif stat.S_ISREG(st.st_mode):
            if hashed + st.st_size > limits.max_bytes:
                raise _TooLarge(f"more than {limits.max_bytes} bytes to hash")
            mode, digest_or_reason, read = _hash_regular_file(
                full, limits.max_bytes - hashed, deadline, limits
            )
            hashed += read
            if mode is None:
                entries.append([rel, "unreadable", digest_or_reason])
                continue
            entries.append([rel, f"{mode:o}", digest_or_reason])
        elif stat.S_ISDIR(st.st_mode):
            # Listed as a directory only when its contents could not be
            # listed (it could not be entered) or Git names it (a submodule).
            readable = os.access(full, os.R_OK | os.X_OK)
            entries.append([rel, "directory" if readable else "unreadable", ""])
        else:
            entries.append([rel, "special", f"{st.st_mode:o}"])
    return entries


def _hash_regular_file(
    full: str, budget: int, deadline: float, limits: EvidenceLimits
) -> Tuple[Optional[int], str, int]:
    """Hash one file as it is OPENED, inside the byte and time bounds.

    The open never follows a link and never waits (``O_NOFOLLOW |
    O_NONBLOCK``), and the opened file must itself be a regular file: a path
    swapped for a link, a FIFO or a device after it was listed is recorded as
    unreadable, never read. The byte budget and the deadline are checked on
    every read, so a file that grows while it is hashed cannot take the
    capture past either bound. Returns ``(mode, sha256, bytes read)`` or
    ``(None, reason, bytes read)``.
    """
    flags = os.O_RDONLY | _O_NOFOLLOW | _O_NONBLOCK
    try:
        fd = os.open(full, flags)
    except OSError as exc:
        return None, type(exc).__name__, 0
    read = 0
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            return None, "not a regular file when opened", 0
        digest = hashlib.sha256()
        while True:
            if time.monotonic() > deadline:
                raise _TooLarge(f"hashing took longer than {limits.max_seconds:g}s")
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            read += len(chunk)
            if read > budget:
                raise _TooLarge(f"more than {limits.max_bytes} bytes to hash")
            digest.update(chunk)
        return opened.st_mode, digest.hexdigest(), read
    except OSError as exc:
        return None, type(exc).__name__, read
    finally:
        os.close(fd)


def manifest_digest(entries: Sequence[Sequence[str]]) -> str:
    """One SHA-256 over the whole manifest, in path order."""
    digest = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: e[0]):
        digest.update("\0".join(str(part) for part in entry).encode("utf-8"))
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"


# =========================================================================
# The one boundary around filesystem capture
# =========================================================================

#: Added to a capture's own deadline before the caller stops waiting for it.
_BOUND_MARGIN_S = 2.0
#: Added to the sum of a capture phase's inner limits.
_PHASE_MARGIN_S = 3.0
#: The largest inventory timeout a project may declare (the schema's bound).
_INVENTORY_TIMEOUT_MAX = 600.0


def within_bound(
    work: Callable[[], Any],
    seconds: float,
    *,
    what: str,
    on_failure: Callable[[Optional[BaseException]], Any],
) -> Any:
    """Run diagnostic ``work`` so that the caller is back after ``seconds``.

    THE ONE BOUNDARY for evidence I/O (run records, head identity). A
    deadline checked between reads cannot interrupt a read, a write, an open,
    a directory listing or a metadata call that has itself stalled (a hung
    network filesystem, a FUSE mount, a FIFO with no peer). So the work runs
    in a daemon thread and the caller waits for it at most ``seconds``.

    Returns what ``work`` returned; otherwise ``on_failure(exc)`` when it
    raised, or ``on_failure(None)`` when it did not finish in time. A thread
    that did not finish is left behind: the work must touch only its own
    local objects, and its late result is discarded. Never raises.
    """
    import threading

    box: List[Any] = []

    def _run() -> None:
        try:
            box.append(("ok", work()))
        except BaseException as exc:  # noqa: BLE001 — evidence never fails a run
            box.append(("error", exc))

    worker = threading.Thread(target=_run, name=f"guardkit-evidence: {what}", daemon=True)
    worker.start()
    worker.join(timeout=max(0.0, seconds))
    if box:
        kind, value = box[0]
        return value if kind == "ok" else on_failure(value)
    logger.warning(
        "evidence: %s did not finish within %.1fs; recorded as timed out and "
        "left behind.", what, seconds,
    )
    return on_failure(None)


def _within_bound(
    capture: Callable[[], Dict[str, Any]],
    seconds: float,
    *,
    what: str,
    clock: Callable[[], float],
) -> Dict[str, Any]:
    """A filesystem capture behind :func:`within_bound`, as a record."""

    def _failed(exc: Optional[BaseException]) -> Dict[str, Any]:
        if exc is not None:
            return {
                "status": f"not recorded: capture error ({type(exc).__name__}: {exc})"
            }
        return {
            "taken_at": _utc(clock()),
            "status": NOT_RECORDED_TIMED_OUT,
            "limit_reached": f"{what} did not finish within {seconds:g}s",
        }

    return within_bound(capture, seconds, what=what, on_failure=_failed)


def source_manifest(
    root: Union[str, Path],
    *,
    limits: Optional[EvidenceLimits] = None,
    runner: Optional[Runner] = None,
    clock: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """A content manifest of ``root``, back within its bound. Never raises.

    The manifest is taken behind :func:`_within_bound`: the caller waits at
    most the manifest's own time limit plus a small margin, whatever the
    filesystem does.
    """
    limits = limits or DEFAULT_LIMITS
    return _within_bound(
        lambda: _source_manifest(root, limits=limits, runner=runner, clock=clock),
        limits.max_seconds + _BOUND_MARGIN_S,
        what="the source manifest",
        clock=clock,
    )


def _source_manifest(
    root: Union[str, Path],
    *,
    limits: EvidenceLimits,
    runner: Optional[Runner] = None,
    clock: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """A content manifest of ``root``. Never raises.

    The returned dict carries a private ``_entries`` list (the full manifest)
    for comparison; :class:`CommandEvidence` strips it before anything is
    written.
    """
    runner = runner or _git_runner
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
            paths, head, unlisted = _git_file_set(root, runner, limits)
            record["head"] = head
        else:
            record["file_set"] = (
                "plain directory without Git metadata: every entry it holds"
            )
            paths, unlisted = _walk_file_set(root, limits, deadline)
        entries = _describe(root, paths, limits, deadline)
    except _TooLarge as exc:
        record["status"] = NOT_RECORDED_TOO_LARGE
        record["limit_reached"] = str(exc)
        return record
    except _TimedOut as exc:
        record["status"] = NOT_RECORDED_TIMED_OUT
        record["limit_reached"] = str(exc)
        return record
    except Exception as exc:  # noqa: BLE001 — capture never fails a run
        record["status"] = f"not recorded: capture error ({type(exc).__name__}: {exc})"
        return record
    # COMPLETENESS. A manifest that could not see every entry's contents, or
    # could not list a directory, is not an identity: two such manifests can
    # agree while the bytes nobody could read differed. It is kept, as
    # diagnosis, but never compared.
    unreadable = sorted(
        set(unlisted) | {e[0] for e in entries if e[1] == "unreadable"}
    )
    record["file_count"] = len(entries)
    record["_entries"] = entries
    if unreadable:
        record["status"] = NOT_RECORDED_INCOMPLETE
        record["unreadable"] = unreadable[: limits.changed_paths]
        record["unreadable_total"] = len(unreadable)
        record["partial_digest"] = manifest_digest(entries)
        return record
    record["status"] = RECORDED
    record["digest"] = manifest_digest(entries)
    return record


def compare_manifests(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    limit: int = DEFAULT_LIMITS.changed_paths,
) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """The plain-words verdict on two manifests, what changed and what is new.

    The verdict is about the source the command STARTED with: it reads
    "source changed during the command" only when an entry that existed
    before was modified (contents, mode or link target) or removed. Entries
    that appeared during the command (caches, build output, anything a run
    writes) are reported separately as files created during the command,
    whatever the language; they never decide the verdict. Returns
    ``(verdict, changed, created)``; the last two are bounded.
    """
    if before.get("status") != RECORDED or after.get("status") != RECORDED:
        why = []
        if before.get("status") != RECORDED:
            why.append(f"before: {before.get('status')}")
        if after.get("status") != RECORDED:
            why.append(f"after: {after.get('status')}")
        return f"not compared ({'; '.join(why)})", None, None
    if before.get("digest") == after.get("digest"):
        return SOURCE_UNCHANGED, None, None
    old = {e[0]: tuple(e[1:]) for e in before.get("_entries", [])}
    new = {e[0]: tuple(e[1:]) for e in after.get("_entries", [])}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    modified = sorted(p for p in set(old) & set(new) if old[p] != new[p])
    created = (
        {"paths": added[:limit], "total": len(added), "truncated": len(added) > limit}
        if added
        else None
    )
    changed = (
        {
            "modified": modified[:limit],
            "removed": removed[:limit],
            "total": len(modified) + len(removed),
            "truncated": len(modified) > limit or len(removed) > limit,
        }
        if (modified or removed)
        else None
    )
    if changed:
        return SOURCE_CHANGED, changed, created
    return (
        f"{SOURCE_UNCHANGED}; {len(added)} files created during the command",
        None,
        created,
    )


def originating_worktree_identity(
    worktree: Union[str, Path],
    *,
    limits: Optional[EvidenceLimits] = None,
    runner: Optional[Runner] = None,
    clock: Callable[[], float] = time.time,
) -> Dict[str, Any]:
    """The origin's identity, back within its bound. Never raises.

    Taken behind :func:`_within_bound`, waiting at most the Git timeout plus
    a small margin; see :func:`_originating_worktree_identity`.
    """
    limits = limits or DEFAULT_LIMITS

    def _capture() -> Dict[str, Any]:
        return _originating_worktree_identity(
            worktree, limits=limits, runner=runner, clock=clock
        )

    record = _within_bound(
        _capture,
        limits.git_timeout + _BOUND_MARGIN_S,
        what="the originating worktree identity",
        clock=clock,
    )
    record.setdefault("worktree", str(worktree))
    return record


def _originating_worktree_identity(
    worktree: Union[str, Path],
    *,
    limits: EvidenceLimits,
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
    runner = runner or _git_runner
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


COPY_STABLE = "worktree unchanged while copying"
COPY_UNSTABLE = "changed while copying (the copy may hold a mix)"


def mark_copy_stability(
    at_start: Optional[Mapping[str, Any]], at_end: Optional[Mapping[str, Any]]
) -> Dict[str, Any]:
    """The origin identity taken as copying began, with whether it held.

    ``at_start`` and ``at_end`` are :func:`originating_worktree_identity`
    results from just before and just after the copy. Never raises.
    """
    record: Dict[str, Any] = dict(at_start or {})
    end = dict(at_end or {})
    record["after_copy"] = {
        k: end.get(k) for k in ("status", "head", "tree_with_untracked", "taken_at")
    }
    if record.get("status") != RECORDED or end.get("status") != RECORDED:
        record["stable_during_copy"] = "not known (an identity was not recorded)"
    elif (record.get("head"), record.get("tree_with_untracked")) == (
        end.get("head"),
        end.get("tree_with_untracked"),
    ):
        record["stable_during_copy"] = COPY_STABLE
    else:
        record["stable_during_copy"] = COPY_UNSTABLE
    return record


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
    #: What the record says when nothing is declared (a component says so).
    not_declared: str = NOT_DECLARED
    #: When set, the declaration has NOT been read yet: it is read from this
    #: main checkout inside the evidence boundary (see :func:`resolve_request`).
    declaration_from: Optional[Path] = None


def request_from_declaration(
    kind: str,
    declaration: Any,
    *,
    component: Any = None,
    component_name: Optional[str] = None,
    **observer: Any,
) -> EvidenceRequest:
    """Build a request from a toolchain declaration (or ``None``).

    When a component is selected, ONLY that component's own declaration is
    used — the per-component rule: the root's command is never run in a
    component's directory. Never raises.
    """
    source = component if component is not None else declaration
    command = getattr(source, "environment_inventory", None) if source is not None else None
    timeout = (
        int(getattr(source, "environment_inventory_timeout", 120) or 120)
        if command
        else 120
    )
    not_declared = (
        f"not declared for component {component_name or '(unnamed)'}"
        if component is not None
        else NOT_DECLARED
    )
    return EvidenceRequest(
        kind=kind,
        observer=dict(observer),
        environment_inventory=command or None,
        inventory_timeout=timeout,
        not_declared=not_declared,
    )


def request_from_repo(kind: str, repo_root: Optional[Path], **observer: Any) -> EvidenceRequest:
    """A request whose declaration is read later, from the MAIN checkout.

    Nothing is read here: reading the declaration is file I/O, so it happens
    inside the evidence boundary when the record begins
    (:func:`resolve_request`). The same reader every repo-level declaration
    uses; never the build worktree, which the builder edits. Never raises.
    """
    if repo_root is None:
        return request_from_declaration(kind, None, **observer)
    return EvidenceRequest(
        kind=kind, observer=dict(observer), declaration_from=Path(repo_root)
    )


#: How long reading a deferred declaration may take before the record says so.
_DECLARATION_BOUND_S = 5.0


def resolve_request(request: EvidenceRequest) -> EvidenceRequest:
    """Read a deferred request's declaration; any other request is returned
    as it is. Bounded by ``_DECLARATION_BOUND_S``; never raises."""
    if request.declaration_from is None:
        return request
    root = request.declaration_from

    def _read() -> EvidenceRequest:
        from guardkit.orchestrator.toolchain_declaration import (
            load_toolchain_declaration,
        )

        return request_from_declaration(
            request.kind, load_toolchain_declaration(root), **request.observer
        )

    def _failed(exc: Optional[BaseException]) -> EvidenceRequest:
        why = (
            f"timed out reading the toolchain declaration after {_DECLARATION_BOUND_S:g}s"
            if exc is None
            else f"could not read the toolchain declaration ({type(exc).__name__}: {exc})"
        )
        return EvidenceRequest(
            kind=request.kind, observer=dict(request.observer), not_declared=f"not recorded: {why}"
        )

    return within_bound(
        _read, _DECLARATION_BOUND_S, what="reading the toolchain declaration", on_failure=_failed
    )


def run_environment_inventory(
    request: EvidenceRequest,
    *,
    cwd: Union[str, Path],
    env: Optional[Mapping[str, str]],
    limits: EvidenceLimits = DEFAULT_LIMITS,
    runner: Optional[Runner] = None,
) -> Dict[str, Any]:
    """Run the declared inventory command and keep its output. Never raises.

    ``env`` is the environment of the command this record is for, which every
    caller builds with ``project_command_env``. The inventory is the project's
    own command and its output is kept in receipts, so it never runs with
    ``None`` (which would inherit the factory's whole environment, credentials
    included): it is recorded as not run instead.
    """
    if not request.inventory_looked_up:
        return {"status": NOT_LOOKED_UP}
    command = request.environment_inventory
    if not command:
        return {"status": request.not_declared or NOT_DECLARED}
    if env is None:
        return {
            "command": command,
            "directory": str(cwd),
            "status": (
                "not recorded: the command this record is for had no project "
                "environment, and the inventory never runs with the factory's"
            ),
        }
    runner = runner or _default_runner
    record: Dict[str, Any] = {"command": command, "directory": str(cwd)}
    try:
        run = runner(
            command,
            cwd=cwd,
            env=env,
            timeout=float(request.inventory_timeout),
            shell=True,
            keep_bytes=limits.inventory_output_bytes,
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
    total = run.stdout_total if run.stdout_total is not None else len(run.stdout)
    record.update(
        {
            "status": RECORDED,
            "exit_code": run.returncode,
            "output_sha256": run.stdout_sha256 or hashlib.sha256(run.stdout).hexdigest(),
            "output_bytes": total,
            "output": run.stdout[:cap].decode("utf-8", errors="replace"),
            "output_truncated": total > min(cap, len(run.stdout)),
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
        run = probe.runner(
            argv, timeout=limits.docker_timeout, keep_bytes=limits.docker_output_bytes
        )
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
            # The daemon wrote more than was read into memory; the events
            # above come from the first part only.
            "output_truncated": bool(run.stdout_truncated),
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
        limits: Optional[EvidenceLimits] = None,
        clock: Callable[[], float] = time.time,
        declared_settings: Sequence[str] = (),
    ) -> None:
        self.request = request or EvidenceRequest(kind="declared command", inventory_looked_up=False)
        #: The project's ``launch.settings`` names, so the record can say
        #: which of them were not set where the factory runs (names only).
        self.declared_settings = tuple(declared_settings or ())
        self.command = command
        self.execution_root = Path(execution_root)
        self.cwd = Path(cwd) if cwd is not None else self.execution_root
        self.env = env
        self.execution_root_is = execution_root_is
        self.origin = origin
        self.runner = runner
        self.docker = docker
        self.limits = limits or DEFAULT_LIMITS
        self.clock = clock
        self._inventory: Dict[str, Any] = {"status": "not recorded: begin() was not called"}
        self._before: Dict[str, Any] = {"status": "not recorded: begin() was not called"}
        self._started: Optional[float] = None
        self._errors: List[str] = []
        self._finished: Optional[Dict[str, Any]] = None

    # ---- the two capture phases ------------------------------------------
    #
    # Everything this record does before the command (reading a deferred
    # declaration, running the inventory, the before observation) is ONE
    # phase, and everything after it (the after observation, finding Docker
    # and reading its events) is another. Each phase runs entirely inside one
    # ``within_bound`` with a fixed overall deadline: the sum of its inner
    # limits plus a margin. Whatever did not complete by then is recorded as
    # "not recorded: timed out". The command itself never runs inside the
    # boundary; it runs between the two phases, in the caller's own thread.

    def _begin_bound(self) -> float:
        req = self.request
        inventory = (
            float(req.inventory_timeout)
            if req.environment_inventory
            else (_INVENTORY_TIMEOUT_MAX if req.declaration_from is not None else 0.0)
        )
        declaration = _DECLARATION_BOUND_S if req.declaration_from is not None else 0.0
        return (
            declaration
            + inventory
            + 2 * _DRAIN_SECONDS
            + self.limits.max_seconds
            + _BOUND_MARGIN_S
            + _PHASE_MARGIN_S
        )

    def _finish_bound(self) -> float:
        return (
            self.limits.max_seconds
            + _BOUND_MARGIN_S
            + self.limits.docker_timeout
            + 2 * _DRAIN_SECONDS
            + _PHASE_MARGIN_S
        )

    def _run_phase(self, name: str, work: Callable[[Dict[str, Any]], None], seconds: float) -> Dict[str, Any]:
        """Run ``work(state)`` inside one boundary; return what it completed.

        ``state`` belongs to the phase's own thread. On expiry the caller
        takes a copy of what was completed and never looks at it again, so a
        late write from an abandoned thread changes nothing the caller holds.
        """
        state: Dict[str, Any] = {}

        def _failed(exc: Optional[BaseException]) -> bool:
            if exc is not None:
                self._errors.append(f"{name}: {type(exc).__name__}: {exc}")
            else:
                self._errors.append(f"{name}: did not finish within {seconds:g}s")
            return False

        within_bound(
            lambda: (work(state), True)[1],
            seconds,
            what=f"the {name} phase of the run record",
            on_failure=_failed,
        )
        return dict(state)

    def begin(self) -> "CommandEvidence":
        timed_out = {
            "status": NOT_RECORDED_TIMED_OUT,
            "limit_reached": "the record's begin phase did not finish in time",
        }

        def _work(state: Dict[str, Any]) -> None:
            request = resolve_request(self.request)
            state["request"] = request
            state["inventory"] = run_environment_inventory(
                request, cwd=self.cwd, env=self.env, limits=self.limits, runner=self.runner
            )
            state["before"] = source_manifest(
                self.execution_root, limits=self.limits, runner=self.runner, clock=self.clock
            )

        try:
            done = self._run_phase("begin", _work, self._begin_bound())
            if "request" in done:
                self.request = done["request"]
            self._inventory = done.get("inventory", dict(timed_out))
            self._before = done.get("before", dict(timed_out))
        except Exception as exc:  # noqa: BLE001
            self._errors.append(f"begin: {type(exc).__name__}: {exc}")
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
        timed_out = {
            "status": NOT_RECORDED_TIMED_OUT,
            "limit_reached": "the record's finish phase did not finish in time",
        }
        started = self._started

        def _work(state: Dict[str, Any]) -> None:
            try:
                state["after"] = source_manifest(
                    self.execution_root, limits=self.limits, runner=self.runner, clock=self.clock
                )
            except Exception as exc:  # noqa: BLE001 — one part failing keeps the rest
                state["after"] = {
                    "status": f"not recorded: capture error ({type(exc).__name__}: {exc})"
                }
                state.setdefault("errors", []).append(f"source after: {type(exc).__name__}: {exc}")
            if started is None:
                state["events"] = {
                    "what_this_shows": WHAT_THE_EVENTS_SHOW,
                    "status": "not recorded: the command's start time was not taken",
                }
                return
            try:
                state["events"] = docker_events_between(
                    started, ended, probe=self.docker, limits=self.limits
                )
            except Exception as exc:  # noqa: BLE001 — one part failing keeps the rest
                state.setdefault("errors", []).append(
                    f"container events: {type(exc).__name__}: {exc}"
                )
                state["events"] = {
                    "what_this_shows": WHAT_THE_EVENTS_SHOW,
                    "status": f"not recorded: capture error ({type(exc).__name__}: {exc})",
                }

        done = self._run_phase("finish", _work, self._finish_bound())
        self._errors.extend(done.get("errors", []))
        after = done.get("after", dict(timed_out))
        events_done = done.get("events")
        verdict, changed, created = compare_manifests(
            self._before, after, limit=self.limits.changed_paths
        )
        entries = self._before.get("_entries") or []
        manifest_copy: Optional[Dict[str, Any]] = None
        if self._before.get("_entries") is not None:
            manifest_copy = {
                "of": "the before observation",
                "complete": self._before.get("status") == RECORDED,
                "entry_format": MANIFEST_ENTRY_FORMAT,
                "entries": entries[: self.limits.inline_entries],
                "entries_total": len(entries),
                "truncated": len(entries) > self.limits.inline_entries,
            }
        events = events_done or {"what_this_shows": WHAT_THE_EVENTS_SHOW, **timed_out}
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
                "files_created_during_the_command": created,
                "manifest": manifest_copy,
            },
            "container_events": events,
            "environment": self._environment_names(),
        }
        if self._errors:
            record["capture_errors"] = list(self._errors)
        return record

    def _environment_names(self) -> Dict[str, Any]:
        """What the command's environment held, by name only, never value."""
        if self.env is None:
            return {"status": "not recorded: the command was given no environment"}
        names = sorted(str(name) for name in self.env)
        missing = [name for name in self.declared_settings if name not in self.env]
        out: Dict[str, Any] = {"names": names}
        if missing:
            out["declared_but_not_set"] = missing
            out["sentences"] = [
                f"the project declares `{name}` in `launch.settings`, but it is "
                f"not set where the factory runs, so the command ran without it"
                for name in missing
            ]
        return out


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
    "NOT_RECORDED_INCOMPLETE",
    "NOT_RECORDED_TIMED_OUT",
    "NOT_RECORDED_TOO_LARGE",
    "SOURCE_CHANGED",
    "SOURCE_UNCHANGED",
    "compare_manifests",
    "default_docker_probe",
    "docker_events_between",
    "manifest_digest",
    "mark_copy_stability",
    "originating_worktree_identity",
    "request_from_declaration",
    "request_from_repo",
    "resolve_request",
    "run_environment_inventory",
    "source_manifest",
    "start_command_evidence",
    "within_bound",
]
