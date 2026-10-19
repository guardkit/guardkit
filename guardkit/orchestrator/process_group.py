"""Run a project command so that a timeout ends everything it started.

13 October 2026. ``subprocess.run(..., timeout=...)`` kills only the direct
child on a timeout. A project's install or check that starts processes of its
own (a background server, a ``sleep``, a package manager's workers) leaves
them running after the merge has given up on it.

:func:`run_in_own_group` starts the command in a new session, so it and
everything it starts share one process group of their own. On a timeout the
whole group is sent SIGTERM, given a short grace period, then sent SIGKILL.
GuardKit's own process group is never signalled.

16 October 2026. Sending SIGKILL is not the same as the process being gone.
A killed worker closes its output early in exiting, so the runner saw the
end of the output and returned while the worker was still listed as
running (about 1 timeout in 100 on a busy machine; once, still there five
seconds later). The runner now waits, for a bounded time, until nothing in
the group is still running, sending SIGKILL again on each look.

Two rules keep that safe (Codex review, 16 October 2026):

* THE LEADER IS NOT COLLECTED WHILE THE GROUP IS BEING ENDED. The group's id
  is the leader's process number. While the leader has not been collected
  (it is running, or a zombie), the kernel cannot hand that number to any
  other process, so every signal sent to the group by number reaches only
  this command. Nothing here collects the leader: its exit is read with
  ``waitid(..., WNOWAIT)``, which leaves it in place, and the caller collects
  it afterwards. If the leader has already been collected (by the caller,
  or by something else in this process), the group is NOT signalled by
  number at all, and a warning says so.
* NOT KNOWING COUNTS AS RUNNING. The wait ends only on positive evidence:
  the leader has exited, and every other process listed in ``/proc`` has
  been read and is either in another group, dead or a zombie, or has gone
  (its ``/proc`` entry no longer exists). A record that cannot be read, a
  listing that cannot be made, or a group the kernel no longer reports
  while its leader is still uncollected keeps the bounded wait going.

19 October 2026 (a factory build). The build's sandbox ran out of memory while a
command held dozens of test-runner processes, and the kernel stopped GuardKit,
the biggest single process, so the whole build was lost. Three changes:

* NOTHING IS LEFT BEHIND, ALSO WHEN THE COMMAND RETURNS. A command's processes
  are those in its process group, those in its session (``timeout`` and other
  programs move into a group of their own but stay in the session), and those
  carrying the command's own marker (:data:`COMMAND_MARKER_NAME` in their
  environment, a fresh value per command; it finds a process that moved into a
  session of its own). When the command returns, anything of it still running
  is ended the same way as on a timeout, and the log says so in plain words,
  naming the command and how many processes. The leader is still not
  collected until then: the output is read here rather than by
  ``communicate()`` (which collects it), so the group's and the session's
  number stay this command's throughout. A process outside the group is
  pinned (a pidfd) and checked again before it is signalled, so a number
  handed to another process in between is never signalled. No process is
  signalled by number alone: where no pidfd can be had, a process outside
  the group is left running and the log says so plainly. A process that
  keeps the output open after the leader has exited no longer holds the
  caller until the time limit: after ``_PIPE_GRACE_SECONDS`` it is ended and
  the output so far is returned.
* THE COMMAND GOES FIRST WHEN MEMORY RUNS OUT. Its leader's ``oom_score_adj``
  is raised to the maximum (raising needs no privilege; everything it starts
  inherits it), so the kernel stops the command's processes rather than
  GuardKit. A ``shell=True`` command's shell sets it before running the
  command (then runs it exactly as ``shell=True`` would, with ``exec``); a
  program run directly gets it from GuardKit straight after it starts, so
  anything it starts in its first moments may miss it.
* Without ``/proc`` (macOS) the command's group alone is signalled when it
  returns, and nothing is counted. Without ``os.waitid`` (macOS before
  Python 3.13) the leader's exit cannot be read without collecting it, so
  the command is waited for with ``communicate()`` as before, and only a
  timeout ends its group.
"""

from __future__ import annotations

import errno
import logging
import os
import select
import selectors
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

__all__ = [
    "COMMAND_MARKER_NAME",
    "GroupRun",
    "end_process_group",
    "leader_exit_code",
    "run_in_own_group",
    "run_project_command",
]

logger = logging.getLogger(__name__)

_GRACE_SECONDS = 2.0
_DRAIN_SECONDS = 5.0
_KILL_WAIT_SECONDS = 10.0
_LOOK_INTERVAL_SECONDS = 0.05
#: How long the output may stay open after the leader has exited.
_PIPE_GRACE_SECONDS = 1.0
#: How much of a command the log line quotes.
_QUOTED_COMMAND_CHARS = 200

#: Set in each command's environment to a value used by that command alone
#: (19 October 2026). The reserved ``GUARDKIT_`` prefix means no project can
#: declare it.
COMMAND_MARKER_NAME = "GUARDKIT_PROJECT_COMMAND"

#: The shell's first step for a ``shell=True`` command: go first when memory
#: runs out, then run the command exactly as ``/bin/sh -c`` would (``$0`` is
#: the command, ``$@`` the rest, as ``subprocess`` passes them).
_FIRST_TO_GO = (
    '{ echo 1000 > /proc/self/oom_score_adj; } 2>/dev/null; exec /bin/sh -c "$0" "$@"'
)
_OOM_SCORE_ADJ_MAX = "1000"

_PIPE_BUF = select.PIPE_BUF
try:  # as subprocess chooses
    _Selector: Any = selectors.PollSelector
except AttributeError:  # pragma: no cover - a system without poll()
    _Selector = selectors.SelectSelector

_RUNNING = "running"  # the leader has not exited
_EXITED = "exited"  # the leader has exited and is still uncollected (a zombie)
_COLLECTED = "collected"  # the leader has been collected; its number is not ours


@dataclass(frozen=True)
class GroupRun:
    """What one command run produced."""

    returncode: Optional[int]  # None when it timed out
    stdout: str
    stderr: str
    timed_out: bool = False


def _leader_state(proc: subprocess.Popen) -> str:
    """Whether the leader is running, exited but uncollected, or collected.

    Reads the leader's exit without collecting it (``WNOWAIT``).
    """
    if proc.returncode is not None:
        return _COLLECTED
    try:
        info = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return _COLLECTED
    return _RUNNING if info is None else _EXITED


def leader_exit_code(proc: subprocess.Popen) -> Optional[int]:
    """``proc.poll()`` that does not collect the process.

    ``None`` while it runs; its exit code (negative for a signal, as
    ``subprocess`` reports it) once it has exited. The process stays
    uncollected, so its group can still be ended safely afterwards with
    :func:`end_process_group`.
    """
    if proc.returncode is not None:
        return proc.returncode
    try:
        info = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return proc.poll()  # collected elsewhere; subprocess's own answer
    if info is None:
        return None
    if info.si_code == os.CLD_EXITED:
        return info.si_status
    return -info.si_status


_GONE = "gone"


def _read_member(pid: int) -> Union[None, str, Tuple[str, int]]:
    """``(state, group id)`` for ``pid``; :data:`_GONE` when it no longer
    exists; ``None`` when that cannot be told."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8", errors="replace") as fh:
            fields = fh.read().rsplit(")", 1)[1].split()
        return fields[0], int(fields[2])
    except (FileNotFoundError, ProcessLookupError):
        pass
    except (OSError, IndexError, ValueError):
        return None
    # The record vanished while it was being read. Only a missing /proc
    # entry, checked again now, says the process is gone.
    try:
        os.stat(f"/proc/{pid}")
    except FileNotFoundError:
        return _GONE
    except OSError:
        return None
    return None


def _others_finished(pgid: int) -> bool:
    """Positive evidence that no process but the leader is running in ``pgid``."""
    try:
        entries = os.listdir("/proc")
    except OSError:
        return False
    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == pgid:
            continue  # the leader; judged by its exit status instead
        member = _read_member(pid)
        if member == _GONE:
            continue
        if member is None:
            return False
        state, group = member
        if group == pgid and state not in ("Z", "X"):
            return False
    return True


def _group_finished(proc: subprocess.Popen, pgid: int) -> bool:
    """The leader has exited (still uncollected) and nothing else in its
    group is running. Anything uncertain answers ``False``."""
    if _leader_state(proc) != _EXITED:
        return False
    try:
        os.killpg(pgid, 0)  # the uncollected leader must still hold the group
    except OSError:
        return False
    return _others_finished(pgid)


# ---------------------------------------------------------------------------
# The command's processes outside its group: its session and its marker
# (19 October 2026)
# ---------------------------------------------------------------------------


def _now_ticks() -> Optional[int]:
    """Clock ticks since boot, the unit of ``/proc/<pid>/stat`` start times."""
    try:
        with open("/proc/uptime", encoding="ascii") as fh:
            uptime = float(fh.read().split()[0])
        return int(uptime * os.sysconf("SC_CLK_TCK")) - 1  # the clock's rounding
    except (OSError, ValueError, IndexError):
        return None


def _stat_fields(pid: int) -> Optional[Tuple[str, int, int, int]]:
    """``(state, group, session, start time)`` for ``pid``; ``None`` when it
    cannot be read (gone, or never there)."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as fh:
            data = fh.read()
        rest = data[data.rindex(b")") + 2 :].split()
        return rest[0].decode(), int(rest[2]), int(rest[3]), int(rest[19])
    except (OSError, ValueError, IndexError):
        return None


def _marker_entry(marker: Optional[str]) -> Optional[bytes]:
    if marker is None:
        return None
    return f"\0{COMMAND_MARKER_NAME}={marker}\0".encode()


def _carries_marker(pid: int, entry: bytes) -> bool:
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            environ = fh.read()
    except OSError:  # gone, or another user's process
        return False
    return entry in b"\0" + environ


def _belongs(
    pid: int, pgid: int, entry: Optional[bytes], since: Optional[int]
) -> Optional[Tuple[str, int, int, int]]:
    """The stat fields of ``pid`` when it is a live process of the command
    that ``pgid`` leads (other than the leader), else ``None``.

    The group and session tests are sound only while the leader is
    uncollected, which every caller here ensures.
    """
    if pid == pgid or pid == os.getpid():
        return None
    fields = _stat_fields(pid)
    if fields is None or fields[0] in ("Z", "X"):
        return None
    _state, group, session, started = fields
    if group == pgid or session == pgid:
        return fields
    if entry is None:
        return None
    # A process the command started cannot be older than the command.
    if since is not None and started < since:
        return None
    return fields if _carries_marker(pid, entry) else None


def _look(
    pgid: int, entry: Optional[bytes], since: Optional[int]
) -> Tuple[Set[int], Set[int]]:
    """``(every live process of the command but the leader, those of them
    outside its group)``. Without a listing, both are empty."""
    try:
        names = os.listdir("/proc")
    except OSError:
        return set(), set()
    members: Set[int] = set()
    outside: Set[int] = set()
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        fields = _belongs(pid, pgid, entry, since)
        if fields is None:
            continue
        members.add(pid)
        if fields[1] != pgid:
            outside.add(pid)
    return members, outside


def _signal_outside(
    pids: Set[int], pgid: int, entry: Optional[bytes], since: Optional[int], sig: int
) -> Set[int]:
    """Signal each of the command's processes outside its group; return those
    that could not be pinned, and so were not signalled.

    Each is pinned first (a pidfd) and checked again. A pidfd names one
    process, not a number: if the process ends and its number is handed to
    another one after the pidfd is opened, the signal finds the ended process
    and goes nowhere. No process is ever signalled by number alone (Codex
    review, 19 October 2026): where a pidfd cannot be had (a kernel older
    than Linux 5.3, or a security filter that refuses the call) the process
    is left alone, and the caller says so.
    """
    refused: Set[int] = set()
    for pid in pids:
        try:
            handle = os.pidfd_open(pid)
        except AttributeError:  # pragma: no cover - no pidfds in this Python
            refused.add(pid)
            continue
        except OSError as exc:
            if exc.errno != errno.ESRCH:  # ESRCH: it has gone
                refused.add(pid)
            continue
        try:
            if _belongs(pid, pgid, entry, since) is not None:
                signal.pidfd_send_signal(handle, sig)
        except OSError:
            pass  # it ended after it was pinned
        finally:
            os.close(handle)
    return refused


def _signal_group(pgid: int, sig: int) -> None:
    """Signal the command's own group, in one step, by the number its
    uncollected leader pins. A group holding only processes of another user
    (a program run as another user, such as ``sudo``) refuses the signal;
    that is said plainly and the ending goes on."""
    try:
        os.killpg(pgid, sig)
    except PermissionError:
        logger.warning(
            "process group %s could not be signalled: permission refused (a "
            "program in it runs as another user)",
            pgid,
        )


def end_process_group(proc: subprocess.Popen, grace: float = _GRACE_SECONDS) -> None:
    """End every process in the group ``proc`` leads (started with
    ``start_new_session=True``), whether or not ``proc`` itself is still alive.

    SIGTERM goes to the whole group; then the group itself (never only the
    leader) is watched, and anything still in it after ``grace`` seconds,
    such as a worker that ignores SIGTERM after the leader has exited, is
    sent SIGKILL. It returns once nothing in the group is running, or after
    a bounded wait. GuardKit's own group is never signalled.

    19 October 2026: so is anything still in the session ``proc`` started
    (a process that moved into a group of its own), each one pinned and
    checked before it is signalled.

    ``proc`` must not have been collected yet (use :func:`leader_exit_code`,
    not ``proc.poll()``, to see whether it has exited): a collected leader's
    number may already belong to someone else, so its group is then not
    signalled at all, and a warning says so. The caller collects ``proc``
    afterwards.
    """
    _end_group(proc, grace)


@dataclass(frozen=True)
class _Ended:
    """What an ending did: every process of the command it saw (the leader
    apart), and those outside the group left running because no pidfd could
    be had for them."""

    seen: Set[int]
    not_safe: Set[int]


def _end_group(
    proc: subprocess.Popen,
    grace: float,
    entry: Optional[bytes] = None,
    since: Optional[int] = None,
) -> _Ended:
    """SIGTERM the command's own group (and its processes outside the group:
    in its session, or carrying ``entry``), wait briefly, then SIGKILL them
    until nothing is running (bounded). Never collects the leader."""
    pgid = proc.pid  # a session leader's group id is its own pid
    seen: Set[int] = set()
    refused: Set[int] = set()

    def ended() -> _Ended:
        left = _look(pgid, entry, since)[0]
        return _Ended(seen, left & refused)

    if pgid == os.getpgrp():  # pragma: no cover - start_new_session prevents it
        proc.kill()
        return _Ended(seen, set())
    if _leader_state(proc) == _COLLECTED:
        logger.warning(
            "process group %s was not signalled: its leader has already been "
            "collected, so the group's number may belong to another process",
            pgid,
        )
        return _Ended(seen, set())
    # The leader is uncollected, so the number names this command's group
    # and session.
    members, outside = _look(pgid, entry, since)
    seen |= members
    _signal_group(pgid, signal.SIGTERM)
    refused |= _signal_outside(outside, pgid, entry, since, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if _group_finished(proc, pgid):
            members, outside = _look(pgid, entry, since)
            seen |= members
            if not outside - refused:
                return ended()
        time.sleep(_LOOK_INTERVAL_SECONDS)
    # SIGKILL cannot be ignored, but a killed process is only gone once it
    # has finished exiting. Look until nothing is running, sending SIGKILL
    # again on each look in case anything is still in the group.
    deadline = time.monotonic() + _KILL_WAIT_SECONDS
    while True:
        if _leader_state(proc) == _COLLECTED:
            logger.warning(
                "process group %s: its leader was collected by something else "
                "while the group was being ended; it is no longer signalled",
                pgid,
            )
            return _Ended(seen, set())
        members, outside = _look(pgid, entry, since)
        seen |= members
        _signal_group(pgid, signal.SIGKILL)
        refused |= _signal_outside(outside - refused, pgid, entry, since, signal.SIGKILL)
        if _group_finished(proc, pgid) and not _look(pgid, entry, since)[1] - refused:
            return ended()
        if time.monotonic() >= deadline:
            logger.warning(
                "process group %s: something in it was still running %.0f "
                "seconds after SIGKILL, or could not be confirmed gone",
                pgid,
                _KILL_WAIT_SECONDS,
            )
            return ended()
        time.sleep(_LOOK_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Starting a command, reading its output without collecting it, and ending
# whatever it leaves (19 October 2026)
# ---------------------------------------------------------------------------


def _prepare(
    args: Any, *, shell: bool, env: Optional[Mapping[str, str]]
) -> Tuple[Any, Dict[str, str], str, Optional[int]]:
    """``(argv, env, marker, start time)`` for a command started with
    ``shell=False`` and ``start_new_session=True``: a fresh marker in its
    environment and, for ``shell=True``, the shell's first step."""
    marker = uuid.uuid4().hex
    command_env = dict(os.environ if env is None else env)
    command_env[COMMAND_MARKER_NAME] = marker
    if shell:
        # What ``shell=True`` would run, behind the shell's first step.
        shell_args = [args] if isinstance(args, (str, bytes)) else list(args)
        argv: Any = ["/bin/sh", "-c", _FIRST_TO_GO, *shell_args]
    else:
        argv = args if isinstance(args, str) else list(args)
    return argv, command_env, marker, _now_ticks()


def _first_in_line(proc: subprocess.Popen, shell: bool) -> None:
    """A program run directly: raise its ``oom_score_adj`` from here (a shell
    raises its own, see :data:`_FIRST_TO_GO`)."""
    if shell:
        return
    try:
        with open(f"/proc/{proc.pid}/oom_score_adj", "w", encoding="ascii") as fh:
            fh.write(_OOM_SCORE_ADJ_MAX)
    except OSError:
        pass  # no /proc, or already gone


class _Exchange:
    """A command's input and output, read here so the leader is never
    collected by the reading (``communicate()`` collects it).

    Bytes are read from the pipes as ``communicate()`` reads them, and decoded
    the same way at the end.
    """

    def __init__(self, proc: subprocess.Popen, input: Any) -> None:  # noqa: A002
        self.proc = proc
        self.selector = _Selector()
        self.chunks: Dict[Any, List[bytes]] = {}
        self.input = b""
        self.offset = 0
        self.pidfd: Optional[int] = None
        if proc.stdin is not None:
            try:
                proc.stdin.flush()
            except BrokenPipeError:
                pass
            if input:
                if proc.text_mode:
                    input = input.encode(proc.stdin.encoding, proc.stdin.errors)
                self.input = memoryview(input)
                self.selector.register(proc.stdin, selectors.EVENT_WRITE)
            else:
                try:
                    proc.stdin.close()
                except BrokenPipeError:
                    pass
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                self.chunks[stream] = []
                self.selector.register(stream, selectors.EVENT_READ)
        try:
            self.pidfd = os.pidfd_open(proc.pid)
        except (AttributeError, OSError):
            self.pidfd = None  # look every _LOOK_INTERVAL_SECONDS instead
        if self.pidfd is not None:
            self.selector.register(self.pidfd, selectors.EVENT_READ)

    def pipes_open(self) -> bool:
        return any(key.fileobj is not self.pidfd for key in self.selector.get_map().values())

    def pump(self, timeout: float) -> None:
        if not self.selector.get_map():
            time.sleep(min(timeout, _LOOK_INTERVAL_SECONDS))
            return
        if self.pidfd is None:
            timeout = min(timeout, _LOOK_INTERVAL_SECONDS)
        for key, _events in self.selector.select(max(timeout, 0.0)):
            if key.fileobj is self.pidfd:
                # The leader has exited; its pidfd stays readable from now on.
                self.selector.unregister(self.pidfd)
                os.close(self.pidfd)
                self.pidfd = None
            elif key.fileobj is self.proc.stdin:
                chunk = self.input[self.offset : self.offset + _PIPE_BUF]
                try:
                    self.offset += os.write(key.fd, chunk)
                except BrokenPipeError:
                    self._close(key.fileobj)
                else:
                    if self.offset >= len(self.input):
                        self._close(key.fileobj)
            else:
                data = os.read(key.fd, 32768)
                if data:
                    self.chunks[key.fileobj].append(data)
                else:
                    self._close(key.fileobj)

    def _close(self, stream: Any) -> None:
        self.selector.unregister(stream)
        try:
            stream.close()
        except OSError:
            pass

    def wait(self, timeout: Optional[float]) -> bool:
        """Read until the leader has exited (left uncollected) and the output
        has closed, or ``_PIPE_GRACE_SECONDS`` after the exit if something
        still holds it. True when ``timeout`` passed first."""
        deadline = None if timeout is None else time.monotonic() + timeout
        exited_at: Optional[float] = None
        while True:
            now = time.monotonic()
            if _leader_state(self.proc) != _RUNNING:
                if not self.pipes_open():
                    return False
                if exited_at is None:
                    exited_at = now
                if now - exited_at >= _PIPE_GRACE_SECONDS:
                    return False
            if deadline is not None and now >= deadline:
                return True
            wait = 0.5 if deadline is None else min(0.5, deadline - now)
            if exited_at is not None:
                wait = min(wait, _PIPE_GRACE_SECONDS - (now - exited_at))
            self.pump(max(wait, 0.0))

    def drain(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while self.pipes_open() and time.monotonic() < deadline:
            self.pump(min(0.1, max(deadline - time.monotonic(), 0.0)))

    def close(self) -> None:
        for key in list(self.selector.get_map().values()):
            if key.fileobj is self.pidfd:
                self.selector.unregister(self.pidfd)
            else:
                self._close(key.fileobj)
        if self.pidfd is not None:
            os.close(self.pidfd)
            self.pidfd = None
        self.selector.close()

    def output(self) -> Tuple[Any, Any]:
        def text(stream: Any) -> Any:
            if stream is None:
                return None
            data = b"".join(self.chunks.get(stream, []))
            if not self.proc.text_mode:
                return data
            decoded = data.decode(stream.encoding, stream.errors)
            return decoded.replace("\r\n", "\n").replace("\r", "\n")

        return text(self.proc.stdout), text(self.proc.stderr)


def _quoted(args: Any) -> str:
    if isinstance(args, (str, bytes)):
        text = args.decode(errors="replace") if isinstance(args, bytes) else args
    else:
        text = " ".join(str(part) for part in args)
    one_line = " ".join(text.split())
    if len(one_line) > _QUOTED_COMMAND_CHARS:
        one_line = one_line[: _QUOTED_COMMAND_CHARS - 3] + "..."
    return one_line


def _processes(count: int) -> str:
    return "1 process" if count == 1 else f"{count} processes"


def _anything_left(proc: subprocess.Popen, entry: bytes, since: Optional[int]) -> bool:
    """Whether anything of an exited (uncollected) command is seen running.

    Only a process seen is evidence here: a record that cannot be read does
    not start an ending on every command (ending it, once started, still
    counts not knowing as running).
    """
    members, _outside = _look(proc.pid, entry, since)
    return bool(members)


def _end_without_proc(proc: subprocess.Popen) -> None:
    """No ``/proc`` (macOS): the uncollected leader still holds the group's
    number, so the group is signalled by number; nothing can be counted."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except OSError:
            return
        if sig == signal.SIGTERM:
            time.sleep(_LOOK_INTERVAL_SECONDS)


def _can_wait_without_collecting() -> bool:
    """Whether ``os.waitid`` exists. macOS has it only from Python 3.13."""
    try:
        os.waitid  # noqa: B018 - the attribute's presence is the question
    except AttributeError:
        return False
    return True


def _not_safe_sentence(count: int) -> str:
    if not count:
        return ""
    return (
        f" {_processes(count).capitalize()} outside the command's process group "
        f"could not be stopped safely on this system (no pidfd), so "
        f"{'it is' if count == 1 else 'they are'} still running."
    )


def _run(
    proc: subprocess.Popen,
    marker: str,
    since: Optional[int],
    args: Any,
    *,
    input: Any,  # noqa: A002 - subprocess's name
    timeout: Optional[float],
    grace: float,
) -> Tuple[Any, Any, bool]:
    """Run ``proc`` to the end; return ``(stdout, stderr, timed out)``.

    On return or timeout every process of the command is ended before the
    leader is collected, and the log names what was stopped.
    """
    if not _can_wait_without_collecting():
        return _run_without_waitid(proc, input=input, timeout=timeout, grace=grace)
    entry = _marker_entry(marker)
    exchange: Optional[_Exchange] = None
    try:
        exchange = _Exchange(proc, input)
        timed_out = exchange.wait(timeout)
        if timed_out:
            ended = _end_group(proc, grace, entry, since)
            stopped = len(ended.seen - ended.not_safe)
            logger.warning(
                "A project command ran past its time limit (%ss), so it was "
                "stopped along with %s it started.%s The command: %s",
                timeout,
                "everything" if not stopped else f"the {_processes(stopped)}",
                _not_safe_sentence(len(ended.not_safe)),
                _quoted(args),
            )
        elif not Path("/proc/self/stat").exists():
            _end_without_proc(proc)
        elif _anything_left(proc, entry, since):
            ended = _end_group(proc, grace, entry, since)
            if ended.seen:
                left = len(ended.seen)
                stopped = left - len(ended.not_safe)
                if ended.not_safe:
                    done = (
                        f"{stopped} {'was' if stopped == 1 else 'were'} stopped."
                        + _not_safe_sentence(len(ended.not_safe))
                    )
                else:
                    done = f"{'it was' if left == 1 else 'they were'} stopped."
                logger.warning(
                    "A project command finished but left %s running; %s "
                    "The command: %s",
                    _processes(left),
                    done,
                    _quoted(args),
                )
        exchange.drain(_DRAIN_SECONDS)
    except BaseException:
        try:
            _end_group(proc, 0.0, entry, since)
        finally:
            if exchange is not None:
                exchange.close()
            proc.wait()
        raise
    exchange.close()
    proc.wait()
    stdout, stderr = exchange.output()
    return stdout, stderr, timed_out


def _run_without_waitid(
    proc: subprocess.Popen, *, input: Any, timeout: Optional[float], grace: float  # noqa: A002
) -> Tuple[Any, Any, bool]:
    """Where the leader's exit cannot be read without collecting it (macOS
    before Python 3.13): wait with ``communicate()`` as before 19 October
    2026, and on a timeout end the command's group by the number the still
    uncollected leader pins. Nothing outside the group can be found there
    (no ``/proc``), so nothing more is safe to do."""
    try:
        out, err = proc.communicate(input=input, timeout=timeout)
        return out, err, False
    except subprocess.TimeoutExpired:
        # A timed-out communicate() has not collected the leader.
        _signal_group(proc.pid, signal.SIGTERM)
        time.sleep(grace)
        _signal_group(proc.pid, signal.SIGKILL)
        try:
            out, err = proc.communicate(timeout=_DRAIN_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                out, err = proc.communicate(timeout=1)
            except subprocess.TimeoutExpired:  # pragma: no cover
                out, err = None, None
        return out, err, True
    except BaseException:
        if proc.returncode is None:
            _signal_group(proc.pid, signal.SIGKILL)
        proc.wait()
        raise


def run_in_own_group(
    args: Union[str, Sequence[str]],
    *,
    cwd: Union[str, Path],
    env: Optional[Dict[str, str]],
    timeout: float,
    shell: bool = False,
    stdin: Optional[int] = subprocess.DEVNULL,
    grace: float = _GRACE_SECONDS,
) -> GroupRun:
    """Run ``args`` in a process group of its own; end the group on timeout.

    19 October 2026: and end whatever it leaves running when it returns (see
    the module docstring). Output is decoded as UTF-8 with undecodable bytes
    replaced. Raises ``OSError`` when the command cannot be started at all,
    as ``subprocess.run`` does.
    """
    argv, command_env, marker, since = _prepare(args, shell=shell, env=env)
    proc = subprocess.Popen(
        argv,
        shell=False,
        cwd=str(cwd),
        env=command_env,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    )
    _first_in_line(proc, shell)
    stdout, stderr, timed_out = _run(
        proc, marker, since, args, input=None, timeout=timeout, grace=grace
    )
    if timed_out:
        return GroupRun(None, stdout or "", stderr or "", timed_out=True)
    return GroupRun(proc.returncode, stdout or "", stderr or "")


def run_project_command(
    args: Union[str, Sequence[str]],
    *,
    env: Optional[Mapping[str, str]],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[float] = None,
    shell: bool = False,
    capture_output: bool = False,
    text: bool = False,
    check: bool = False,
    stdin: Optional[Union[int, IO[Any]]] = None,
    stdout: Optional[Union[int, IO[Any]]] = None,
    stderr: Optional[Union[int, IO[Any]]] = None,
    input: Optional[Union[str, bytes]] = None,  # noqa: A002 - subprocess.run's name
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    grace: float = _GRACE_SECONDS,
) -> "subprocess.CompletedProcess[Any]":
    """``subprocess.run`` for a project's command, but a timeout ends the
    whole command, not only its first process (13 October 2026).

    The same arguments, results and exceptions as ``subprocess.run``: a
    ``CompletedProcess``, ``subprocess.TimeoutExpired`` carrying what was
    printed before the limit, ``CalledProcessError`` with ``check=True``,
    and ``OSError`` when the command cannot start. The difference is that
    the command runs in a new session, so on a timeout its whole process
    group (a background server, a worker, a ``sleep``) is sent SIGTERM, then
    SIGKILL after ``grace`` seconds. GuardKit's own group is never signalled.

    19 October 2026: what the command leaves running when it returns is
    ended the same way, also outside its group (see the module docstring).
    """
    if capture_output:
        if stdout is not None or stderr is not None:
            raise ValueError("stdout and stderr may not be used with capture_output")
        stdout = stderr = subprocess.PIPE
    if input is not None and stdin is None:
        stdin = subprocess.PIPE
    argv, command_env, marker, since = _prepare(args, shell=shell, env=env)
    proc = subprocess.Popen(
        argv,
        shell=False,
        cwd=str(cwd) if cwd is not None else None,
        env=command_env,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        text=text or None,
        encoding=encoding,
        errors=errors,
        start_new_session=True,
    )
    _first_in_line(proc, shell)
    out, err, timed_out = _run(
        proc, marker, since, args, input=input, timeout=timeout, grace=grace
    )
    if timed_out:
        raise subprocess.TimeoutExpired(args, timeout, output=out, stderr=err)
    if check and proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, args, output=out, stderr=err)
    return subprocess.CompletedProcess(args, proc.returncode, out, err)
