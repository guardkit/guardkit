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
  signalled by number alone: where no pidfd can be had or signalled through,
  a process outside the group is left running and the log says so plainly. A process that
  keeps the output open after the leader has exited no longer holds the
  caller until the time limit: after ``_PIPE_GRACE_SECONDS`` it is ended and
  the output so far is returned.
* THE COMMAND GOES FIRST WHEN MEMORY RUNS OUT. Its leader's ``oom_score_adj``
  is raised to the maximum (raising needs no privilege; everything it starts
  inherits it), so the kernel stops the command's processes rather than
  GuardKit. A ``shell=True`` command's shell sets it before running the
  command (then runs it exactly as ``shell=True`` would, with ``exec``); a
  program run directly gets it in the child before ``exec``
  (:func:`_first_in_line_before_exec`), so nothing it starts escapes it.
* A factory launch (``m0_fence.is_factory_launch``) runs no project command
  until the real clean-up has passed an END-TO-END SELF-TEST in this process
  (:func:`_self_test`, cached on success): a tiny command leaves a process in
  a session of its own, is stopped exactly as a project command is, and the
  process must be gone. That proves the ``/proc`` listing and record reads,
  ``waitid`` and the pidfd calls together. A failure raises
  :class:`CleanupUnavailableError` (an ``OSError``, ``errno`` ENOSYS, the
  reason as ``strerror``) before the command starts. Any of those failing
  later, mid-run, ends that command the same way (the group by its pinned
  number, the rest through pidfds) instead of falling back to a reduced or
  silently empty clean-up. A person's own run keeps the reduced clean-up
  below, with one warning.
* Without ``/proc`` (macOS) the command's group alone is signalled when it
  returns, and nothing is counted. Without a working ``os.waitid`` (macOS
  before Python 3.13, or a filter that refuses the call) the leader's exit
  cannot be read without collecting it, so the command is waited for with
  ``communicate()`` as before, and only a timeout ends its group. No wait
  for the leader is ever unbounded (:func:`_collect`).
"""

from __future__ import annotations

import errno
import logging
import os
import select
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

from guardkit.orchestrator.m0_fence import is_factory_launch

__all__ = [
    "COMMAND_MARKER_NAME",
    "CleanupUnavailableError",
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
    except OSError as exc:
        # waitid refused (a filter): the leader's state cannot be read, so
        # the command cannot be watched safely. Never read as "running",
        # which could wait for ever.
        raise _cleanup_failure(
            _refused("waitid", True, exc), before_launch=False
        ) from exc
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
    except (FileNotFoundError, ProcessLookupError, ValueError, IndexError):
        return None  # gone, or never there
    except OSError as exc:
        # A record that cannot be read is not an absent process: on a factory
        # launch the command cannot be watched safely.
        if _is_factory_launch():
            raise _cleanup_failure(
                f"a process record in /proc could not be read ({exc.strerror or exc})",
                before_launch=False,
            ) from exc
        return None


def _marker_entry(marker: Optional[str]) -> Optional[bytes]:
    if marker is None:
        return None
    return f"\0{COMMAND_MARKER_NAME}={marker}\0".encode()


def _carries_marker(pid: int, entry: bytes) -> bool:
    """Whether ``pid``'s environment holds ``entry``.

    A process that has gone does not. Another user's process, whose
    environment this user may not read, is not this command's. Any other
    failure to read it (this user's own process, unreadable) is not an
    absent marker: on a factory launch the command cannot be watched safely.
    """
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            environ = fh.read()
    except (FileNotFoundError, ProcessLookupError):
        return False
    except OSError as exc:
        if isinstance(exc, PermissionError) and not _could_be_this_commands(pid):
            return False
        if _is_factory_launch():
            raise _cleanup_failure(
                f"a process's environment in /proc could not be read "
                f"({exc.strerror or exc})",
                before_launch=False,
            ) from exc
        return False
    return entry in b"\0" + environ


def _status_fields(pid: int) -> Dict[str, str]:
    try:
        with open(f"/proc/{pid}/status", encoding="ascii", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return {}
    fields = {}
    for line in text.splitlines():
        name, _, value = line.partition(":")
        fields[name] = value.strip()
    return fields


def _status_fields_checked(pid: int) -> Dict[str, str]:
    """``/proc/<pid>/status`` as fields; raises on any failure to read it
    (``FileNotFoundError``/``ProcessLookupError`` when it has gone)."""
    with open(f"/proc/{pid}/status", encoding="ascii", errors="replace") as fh:
        text = fh.read()
    fields = {}
    for line in text.splitlines():
        name, _, value = line.partition(":")
        fields[name] = value.strip()
    return fields


def _metadata_unreadable(exc: OSError) -> None:
    """A process's environment and its ``/proc`` metadata both cannot be
    read, and it has not gone: on a factory launch that ends the command (it
    could be one of the command's, and nothing can tell); on a person's own
    run it is said."""
    reason = f"a process's /proc metadata could not be read ({exc.strerror or exc})"
    if _is_factory_launch():
        raise _cleanup_failure(reason, before_launch=False) from exc
    logger.warning(
        "%s, so whether it is a project command's own could not be told.", reason.capitalize()
    )


def _could_be_this_commands(pid: int) -> bool:
    """Whether a process whose environment cannot be read may still be one
    of this command's, so that the refusal is a failure, not a boundary.

    Not this command's: one whose ``/proc`` records belong to another user
    (another user's, or one that is not dumpable, such as ``sshd`` or
    ``ssh-agent``); one in a deeper pid namespace (a container's); one
    holding capabilities this process lacks. Those are refused by design.
    A process the command starts has none of these, and the self-test
    proved its environment can be read.
    """
    try:
        if os.stat(f"/proc/{pid}/environ").st_uid != os.geteuid():
            return False
        theirs = _status_fields_checked(pid)
    except (FileNotFoundError, ProcessLookupError):
        return False  # gone
    except OSError as exc:
        _metadata_unreadable(exc)
        return True  # a person's run: not knowing counts as possibly ours
    ours = _status_fields(os.getpid())
    if not theirs or not ours:
        return True  # not knowing counts as possibly ours
    if len(theirs.get("NSpid", "").split()) != len(ours.get("NSpid", "").split()):
        return False
    try:
        their_caps = int(theirs.get("CapPrm", "0"), 16)
        our_caps = int(ours.get("CapPrm", "0"), 16)
    except ValueError:
        return True
    return their_caps & ~our_caps == 0


def _why_uninspectable(pid: int) -> Optional[str]:
    """When ``pid``'s environment cannot be read and it was excluded as "not
    this command's" by a by-design boundary, the plain reason; ``None`` when
    the environment can be read, the process is gone, or it was not excluded
    that way.

    Deliberate concealment (a child that calls ``setsid`` and
    ``prctl(PR_SET_DUMPABLE, 0)`` keeps the marker but makes its ``/proc``
    records root-owned) lands here: the concealment is out of scope for the
    stop (an accidental runaway never does it, and the sandbox contains
    adversarial code), but it must not be silent. The caller names it.
    """
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            fh.read()
        return None  # readable: inspected normally
    except (FileNotFoundError, ProcessLookupError):
        return None  # gone
    except OSError:
        pass
    try:
        if os.stat(f"/proc/{pid}/environ").st_uid != os.geteuid():
            return "its /proc records belong to another user, or it is not dumpable"
        theirs = _status_fields_checked(pid)
    except (FileNotFoundError, ProcessLookupError):
        return None  # gone
    except OSError as exc:
        # Never silent: named, though it cannot be told apart.
        return f"its /proc metadata could not be read ({exc.strerror or exc})"
    ours = _status_fields(os.getpid())
    if not theirs or not ours:
        return None
    if len(theirs.get("NSpid", "").split()) != len(ours.get("NSpid", "").split()):
        return "it is in a deeper pid namespace"
    try:
        if int(theirs.get("CapPrm", "0"), 16) & ~int(ours.get("CapPrm", "0"), 16):
            return "it holds capabilities this process lacks"
    except ValueError:
        return None
    return None


def _uninspectable_newcomers(leader: int, since: Optional[int]) -> List[Tuple[int, str]]:
    """Live processes that started during the command (``/proc`` stat, which
    stays readable), are outside its group and session, and were excluded
    only because they could not be inspected. ``(pid, reason)`` each. Never
    raises: a warning path must not fail the command."""
    found: List[Tuple[int, str]] = []
    try:
        names = os.listdir("/proc")
    except OSError:
        return found
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == leader or pid == os.getpid():
            continue
        try:
            with open(f"/proc/{pid}/stat", "rb") as fh:
                data = fh.read()
            rest = data[data.rindex(b")") + 2 :].split()
            state, group, session, started = (
                rest[0].decode(), int(rest[2]), int(rest[3]), int(rest[19])
            )
        except (OSError, ValueError, IndexError):
            continue
        if state in ("Z", "X") or group == leader or session == leader:
            continue
        if since is not None and started < since:
            continue  # it predates the command
        try:
            reason = _why_uninspectable(pid)
        except Exception:  # noqa: BLE001
            continue
        if reason is not None:
            found.append((pid, reason))
    return found


def _warn_uninspectable(leader: int, since: Optional[int]) -> str:
    """Log and return a plain sentence for processes that started during the
    command but could not be inspected (so a hidden runaway cannot be
    silent); empty when there are none. They are not killed: they may be
    unrelated system processes. The command text is never named here: it may
    carry a secret, and this warning is published."""
    newcomers = _uninspectable_newcomers(leader, since)
    if not newcomers:
        return ""
    listed = "; ".join(f"pid {pid} ({reason})" for pid, reason in newcomers)
    sentence = (
        f"A project command left {_processes(len(newcomers))} that started while "
        f"it ran and could not be inspected, so whether they are its own could "
        f"not be told and they were left alone: {listed}."
    )
    logger.warning("%s", sentence)
    return sentence


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
    outside its group)``. Without a listing: on a factory launch
    :class:`CleanupUnavailableError`, on a person's own run both empty and a
    warning."""
    try:
        names = os.listdir("/proc")
    except OSError as exc:
        # A listing that cannot be made is not an empty one: on a factory
        # launch it ends the command; on a person's own run it is said.
        if _is_factory_launch():
            raise _cleanup_failure(
                f"/proc could not be listed ({exc.strerror or exc})", before_launch=False
            ) from exc
        logger.warning(
            "/proc could not be listed (%s), so what a project command left "
            "running cannot be found or stopped.",
            exc.strerror or exc,
        )
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


#: The system call numbers of pidfd_open and pidfd_send_signal: the same on
#: every Linux architecture (they come from the unified syscall table).
_SYS_PIDFD_OPEN = 434
_SYS_PIDFD_SEND_SIGNAL = 424
_LIBC: List[Any] = []


def _raw_syscall(number: int, *args: Any) -> int:
    """``syscall(2)`` through ctypes, for a Python built without the pidfd
    wrappers (some standalone builds, such as uv-managed ones). Raises
    ``OSError`` with the call's own error."""
    import ctypes

    if not _LIBC:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        _LIBC.append(libc)
    result = _LIBC[0].syscall(ctypes.c_long(number), *args)
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return int(result)


def _c_int(value: int) -> Any:
    import ctypes

    return ctypes.c_int(value)


def _has_wrapper(module: str) -> bool:
    try:
        if module == "os":
            os.pidfd_open  # noqa: B018 - the attribute's presence is the question
        else:
            signal.pidfd_send_signal  # noqa: B018
    except AttributeError:
        return False
    return True


def _pidfd_open(pid: int) -> int:
    """``os.pidfd_open``, or the system call itself where this Python build
    lacks the wrapper (Linux only)."""
    if _has_wrapper("os"):
        return os.pidfd_open(pid)
    if sys.platform != "linux":
        raise OSError(errno.ENOSYS, "pidfd_open is a Linux system call")
    return _raw_syscall(_SYS_PIDFD_OPEN, _c_int(pid), _c_int(0))


def _pidfd_send_signal(handle: int, sig: int) -> None:
    """``signal.pidfd_send_signal``, or the system call itself where this
    Python build lacks the wrapper (Linux only)."""
    if _has_wrapper("signal"):
        signal.pidfd_send_signal(handle, sig)
        return
    if sys.platform != "linux":
        raise OSError(errno.ENOSYS, "pidfd_send_signal is a Linux system call")
    _raw_syscall(
        _SYS_PIDFD_SEND_SIGNAL, _c_int(handle), _c_int(int(sig)), None, _c_int(0)
    )


def _signal_outside(
    pids: Set[int], pgid: int, entry: Optional[bytes], since: Optional[int], sig: int
) -> Set[int]:
    """Signal each of the command's processes outside its group; return those
    that could not be pinned or whose signal was refused, and so were not
    signalled.

    Each is pinned first (a pidfd) and checked again. A pidfd names one
    process, not a number: if the process ends and its number is handed to
    another one after the pidfd is opened, the signal finds the ended process
    and goes nowhere. No process is ever signalled by number alone (Codex
    review, 19 October 2026): where a pidfd cannot be had or signalled
    through, the process is left alone; on a factory launch that ends the
    command with :class:`CleanupUnavailableError`, on a person's own run the
    caller says so.
    """
    refused: Set[int] = set()
    for pid in pids:
        try:
            handle = _pidfd_open(pid)
        except OSError as exc:
            if exc.errno != errno.ESRCH:  # ESRCH: it has gone
                _refusal_mid_run(_refused("pidfd_open", _has_wrapper("os"), exc), exc)
                refused.add(pid)
            continue
        try:
            if _belongs(pid, pgid, entry, since) is not None:
                _pidfd_send_signal(handle, sig)
        except OSError as exc:
            # Only ESRCH means it ended after it was pinned; anything else (a
            # refusal) means it was not signalled.
            if exc.errno != errno.ESRCH:
                if isinstance(exc, CleanupUnavailableError):
                    raise
                _refusal_mid_run(
                    _refused("pidfd_send_signal", _has_wrapper("signal"), exc), exc
                )
                refused.add(pid)
        finally:
            os.close(handle)
    return refused


def _refusal_mid_run(reason: str, cause: OSError) -> None:
    """On a factory launch a refused pidfd call ends the command; on a
    person's own run the process is reported as not stopped."""
    if _is_factory_launch():
        raise _cleanup_failure(reason, before_launch=False) from cause


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


def _first_in_line_before_exec() -> None:
    """Runs in the child between fork and exec, for a program run directly
    (a ``shell=True`` command's shell raises its own, see
    :data:`_FIRST_TO_GO`): the score is in place before the program can
    start anything, and GuardKit's own is never touched.

    CPython warns that ``preexec_fn`` is not safe in a threaded program: the
    child could deadlock on a lock another thread held at the fork. This
    function takes no Python-level lock, imports nothing and calls only
    ``open``/``write``/``close`` (async-signal-safe system calls) through
    ``os``; every error is swallowed, so a launch failure is still the
    program's own ``OSError``.
    """
    try:
        fd = os.open("/proc/self/oom_score_adj", os.O_WRONLY)
        try:
            os.write(fd, b"1000")
        finally:
            os.close(fd)
    except BaseException:  # noqa: BLE001 - nothing may escape into the child
        pass


def _collect(proc: subprocess.Popen) -> None:
    """Collect the ended leader, never waiting without bound: after
    ``_KILL_WAIT_SECONDS`` it is sent SIGKILL (its group, by the number it
    still pins) and given ``_DRAIN_SECONDS`` more; then it is left, said
    plainly."""
    try:
        proc.wait(timeout=_KILL_WAIT_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    _signal_group(proc.pid, signal.SIGKILL)
    try:
        proc.wait(timeout=_DRAIN_SECONDS)
    except subprocess.TimeoutExpired:
        logger.warning(
            "a project command's first process (%s) could not be collected; "
            "it is left as it is",
            proc.pid,
        )


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
            self.pidfd = _pidfd_open(proc.pid)
        except OSError:
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


def _is_factory_launch() -> bool:
    """GuardKit's one factory-launch predicate: any value of
    ``GUARDKIT_FACTORY_LAUNCH`` at all, whitespace included; only unset or
    exactly empty is a person's own run."""
    return is_factory_launch()


class CleanupUnavailableError(OSError):
    """This system cannot stop everything a project command leaves (an
    ``OSError`` with ``errno`` ENOSYS and the plain sentence as ``strerror``,
    so a caller that treats "could not start" as the command's failure, and
    reports ``strerror``, says why). ``reason`` is the clause alone."""

    reason: str = ""


_ADVICE = (
    "Run the factory where /proc can be read and waitid, pidfd_open and "
    "pidfd_send_signal are allowed (Linux 5.3 or later)."
)


def _cleanup_failure(reason: str, *, before_launch: bool) -> CleanupUnavailableError:
    if before_launch:
        text = (
            f"The factory does not run project commands here: {reason}, so what a "
            f"command leaves running could not all be stopped safely. {_ADVICE}"
        )
    else:
        text = (
            f"A project command was ended because {reason}, so what it left "
            f"running could not all be stopped safely. {_ADVICE}"
        )
    error = CleanupUnavailableError(errno.ENOSYS, text)
    error.reason = reason
    return error


def _refused(call: str, wrapper: bool, exc: OSError) -> str:
    """The plain clause naming why ``call`` cannot be used here."""
    reason = exc.strerror or str(exc)
    if wrapper:
        return f"{call} is refused here by the kernel or a security filter ({reason})"
    if sys.platform != "linux":
        return f"this Python build lacks {call}, and this system is not Linux"
    return (
        f"this Python build lacks {call}, and the system call itself is "
        f"refused by the kernel or a security filter ({reason})"
    )


def _missing_capability() -> Optional[str]:
    """Why this system cannot end everything a command leaves, as a plain
    clause, or ``None``.

    Ending a process that left the command's group needs ``/proc`` (to find
    it), ``os.waitid`` (to keep the leader uncollected meanwhile) and a pidfd
    that can be opened and signalled through (to signal that one process and
    no other). Both are tried on this process itself, through the Python
    wrappers or, where this Python build lacks them, the system calls
    themselves.
    """
    if not Path("/proc/self/stat").exists():
        return "/proc is missing (it is needed to find a command's processes)"
    waitid_problem = _waitid_problem()
    if waitid_problem is not None:
        return waitid_problem
    try:
        handle = _pidfd_open(os.getpid())
    except OSError as exc:
        return _refused("pidfd_open", _has_wrapper("os"), exc)
    try:
        # Signal 0 checks that signalling through a pidfd is allowed too (a
        # filter may allow opening one and refuse sending).
        _pidfd_send_signal(handle, 0)
    except OSError as exc:
        return _refused("pidfd_send_signal", _has_wrapper("signal"), exc)
    finally:
        os.close(handle)
    return None


_CAPABILITY: List[Optional[str]] = []
_WARNED: List[bool] = []
#: The self-test's success, once per process (a later failure mid-run ends
#: that command, so a stale success is safe).
_SELF_TEST_PASSED: List[bool] = []
_SELF_TEST_LOCK = threading.Lock()
_IN_SELF_TEST = threading.local()

#: The self-test's command (argument 1: a private folder). It starts one
#: process that moves into a session of its own (carrying the command's
#: marker, as every process of a command does), lets go of the output and
#: writes its pid; the command then waits for the self-test's "go", prints
#: that pid and the marker, and returns, leaving the process running.
_SELF_TEST_CODE = (
    "import os, sys, time\n"
    "folder = sys.argv[1]\n"
    "pid = os.fork()\n"
    "if pid == 0:\n"
    "    os.setsid()\n"
    "    null = os.open(os.devnull, os.O_RDWR)\n"
    "    for fd in (0, 1, 2):\n"
    "        os.dup2(null, fd)\n"
    "    with open(os.path.join(folder, 'child.tmp'), 'w') as fh:\n"
    "        fh.write(str(os.getpid()))\n"
    "    os.rename(os.path.join(folder, 'child.tmp'), os.path.join(folder, 'child'))\n"
    "    time.sleep(30)\n"
    "    os._exit(0)\n"
    "deadline = time.monotonic() + 20\n"
    "while not os.path.exists(os.path.join(folder, 'go')) and time.monotonic() < deadline:\n"
    "    time.sleep(0.01)\n"
    f"print(pid, os.environ.get({COMMAND_MARKER_NAME!r}, ''), flush=True)\n"
)
_SELF_TEST_WAIT_SECONDS = 20.0


def _self_test_child_check(pid: int, handle: int, since: Optional[int]) -> Tuple[Optional[str], bytes]:
    """Check, through the pinned pidfd ``handle``, that ``pid`` is the
    self-test's own process: alive, the leader of a session of its own,
    started after the self-test, with a readable environment carrying a
    command marker. Returns ``(problem, marker entry)``."""
    try:
        _pidfd_send_signal(handle, 0)  # still the pinned process, still alive
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return "the clean-up self-test's process ended before it could be checked", b""
        return _refused("pidfd_send_signal", _has_wrapper("signal"), exc), b""
    fields = _stat_fields(pid)
    if fields is None or fields[0] in ("Z", "X"):
        return "the clean-up self-test's process ended before it could be checked", b""
    _state, _group, session, started = fields
    if session != pid or (since is not None and started < since):
        return "the clean-up self-test's process is not the one it started", b""
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            environ = fh.read()
    except OSError as exc:
        return (
            f"the clean-up self-test's process environment could not be read "
            f"({exc.strerror or exc})"
        ), b""
    prefix = f"{COMMAND_MARKER_NAME}=".encode()
    for item in environ.split(b"\0"):
        if item.startswith(prefix) and len(item) > len(prefix):
            return None, b"\0" + item + b"\0"
    return "the clean-up self-test's process does not carry the command's marker", b""


def _has_ended(handle: int, seconds: float) -> bool:
    """Whether the pinned process has ended, waiting at most ``seconds``
    (a pidfd becomes readable when its process exits)."""
    poller = select.poll()
    poller.register(handle, select.POLLIN)
    return bool(poller.poll(int(seconds * 1000)))


def _end_self_test_leftovers(pids: Set[int], entry: bytes, since: Optional[int]) -> None:
    """Kill what the self-test left, through pidfds, each checked again after
    pinning (alive, started after the self-test, carrying its marker), so a
    number handed on in between is never signalled."""
    for pid in pids:
        try:
            handle = _pidfd_open(pid)
        except OSError:
            continue
        try:
            fields = _stat_fields(pid)
            if (
                fields is not None
                and fields[0] not in ("Z", "X")
                and (since is None or fields[3] >= since)
                and _carries_marker(pid, entry)
            ):
                _pidfd_send_signal(handle, signal.SIGKILL)
        except OSError:
            pass
        finally:
            os.close(handle)


def _self_test_command(folder: str, outcome: Dict[str, Any]) -> None:
    """The self-test's command, run like any project command (in its own
    thread, so the self-test can pin the process it leaves meanwhile)."""
    _IN_SELF_TEST.active = True
    try:
        outcome["done"] = run_project_command(
            [sys.executable, "-I", "-c", _SELF_TEST_CODE, folder],
            env={"PATH": os.defpath},
            cwd="/",
            capture_output=True,
            text=True,
            timeout=60,
            grace=1.0,
        )
    except BaseException as exc:  # noqa: BLE001 - reported by the self-test
        outcome["error"] = exc


def _self_test_error_reason(error: BaseException) -> str:
    """The plain reason for the self-test's command failing with ``error``:
    a capability failure's own clause, else the exception as it is."""
    if isinstance(error, CleanupUnavailableError):
        return error.reason or str(error)
    return f"the clean-up self-test could not run ({type(error).__name__}: {error})"


def _self_test() -> Optional[str]:
    """Run the real clean-up end to end once; ``None`` when it worked, else
    the plain reason.

    A tiny command, run through :func:`run_project_command` like any
    project command, leaves a process in a session of its own. While the
    command waits, that process is pinned (a pidfd) and checked to be the
    one it started, carrying the command's marker; then the command
    returns and the real stop runs. Afterwards the pinned process must have
    ended (its pidfd readable), and nothing carrying the marker may be left
    in ``/proc``. That proves, on this system, the ``/proc`` listing and
    record reads, ``waitid`` and the pidfd calls the clean-up needs, and it
    does not rely on the marker scan to see its own process.
    """
    folder = tempfile.mkdtemp(prefix="guardkit-cleanup-self-test-")
    outcome: Dict[str, Any] = {}
    since = _now_ticks()
    worker = threading.Thread(
        target=_self_test_command, args=(folder, outcome), name="clean-up self-test",
        daemon=True,
    )
    handle: Optional[int] = None
    entry = b""
    problem: Optional[str] = None
    try:
        worker.start()
        child_file = Path(folder) / "child"
        deadline = time.monotonic() + _SELF_TEST_WAIT_SECONDS
        while not child_file.exists() and worker.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not child_file.exists():
            worker.join(_SELF_TEST_WAIT_SECONDS + 60)
            error = outcome.get("error")
            if error is not None:
                return _self_test_error_reason(error)
            problem = "the clean-up self-test's process did not start"
        else:
            pid = int(child_file.read_text(encoding="ascii"))
            try:
                handle = _pidfd_open(pid)
            except OSError as exc:
                problem = _refused("pidfd_open", _has_wrapper("os"), exc)
            else:
                try:
                    problem, entry = _self_test_child_check(pid, handle, since)
                except CleanupUnavailableError as exc:
                    problem = exc.reason or str(exc)
        (Path(folder) / "go").write_text("go", encoding="ascii")
        worker.join(_SELF_TEST_WAIT_SECONDS + 60)
        if worker.is_alive():
            return problem or "the clean-up self-test's command did not finish"
        error = outcome.get("error")
        if error is not None and not isinstance(error, CleanupUnavailableError):
            # A crash in the command's run is the real cause: reported as it
            # is, before any consequence the independent check saw.
            return _self_test_error_reason(error)
        if problem is not None:
            return problem
        if error is not None:
            return _self_test_error_reason(error)
        done = outcome["done"]
        words = (done.stdout or "").split()
        printed = f"\0{COMMAND_MARKER_NAME}={words[1]}\0".encode() if len(words) == 2 else b""
        if done.returncode != 0 or handle is None or entry != printed:
            return (
                "the clean-up self-test's command did not run as expected "
                f"(exit {done.returncode})"
            )
        # Independent of the marker scan: the pinned process itself.
        if not _has_ended(handle, _GRACE_SECONDS):
            try:
                _pidfd_send_signal(handle, signal.SIGKILL)
            except OSError:
                pass
            return "the clean-up self-test's left-behind process was still running after the stop"
        # And nothing else carrying the marker.
        left: Set[int] = set()
        try:
            for name in os.listdir("/proc"):
                if not name.isdigit():
                    continue
                fields = _stat_fields(int(name))
                if (
                    fields is not None
                    and fields[0] not in ("Z", "X")
                    # Only what started after the self-test can be its own.
                    and (since is None or fields[3] >= since)
                    and _carries_marker(int(name), entry)
                ):
                    left.add(int(name))
        except CleanupUnavailableError as exc:
            return exc.reason or str(exc)
        except OSError as exc:
            return f"/proc could not be listed ({exc.strerror or exc})"
        if left:
            _end_self_test_leftovers(left, entry, since)
            return "the clean-up self-test left a process running after the stop"
        return None
    finally:
        if handle is not None:
            os.close(handle)
        shutil.rmtree(folder, ignore_errors=True)


def _check_capability() -> None:
    """Before a command starts. On a factory launch the real clean-up must
    have passed its end-to-end self-test in this process (run once, cached
    on success only), else :class:`CleanupUnavailableError`; any failure
    later, mid-run, ends that command (``before_launch=False``). On a
    person's own run, what is missing is worked out once and warned about
    once, and the reduced clean-up goes on."""
    if getattr(_IN_SELF_TEST, "active", False):
        return
    if _is_factory_launch():
        if _SELF_TEST_PASSED:
            return
        with _SELF_TEST_LOCK:
            if _SELF_TEST_PASSED:
                return
            reason = _self_test()
            if reason is None:
                _SELF_TEST_PASSED.append(True)
                return
        raise _cleanup_failure(reason, before_launch=True)
    if not _CAPABILITY:
        _CAPABILITY.append(_missing_capability())
    missing = _CAPABILITY[0]
    if missing is not None and not _WARNED:
        _WARNED.append(True)
        logger.warning(
            "Here %s, so a process a project command moves out of its process "
            "group may be left running after the command.",
            missing,
        )


def _waitid_problem() -> Optional[str]:
    """Why a leader's exit cannot be read without collecting it, as a plain
    clause, or ``None`` when it can.

    ``os.waitid`` must exist (macOS has it only from Python 3.13) and the
    call must work: it is tried on this process itself, which is never its
    own child, so a working call answers "no such child" (ECHILD) and a
    refusal by the kernel or a filter answers otherwise. One system call,
    nothing collected.
    """
    try:
        os.waitid  # noqa: B018 - the attribute's presence is the question
    except AttributeError:
        return "os.waitid is missing (macOS has it from Python 3.13)"
    try:
        os.waitid(os.P_PID, os.getpid(), os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return None
    except OSError as exc:
        return _refused("waitid", True, exc)
    return None


def _can_wait_without_collecting() -> bool:
    """Whether a leader's exit can be read without collecting it."""
    return _waitid_problem() is None


def _not_safe_sentence(count: int) -> str:
    if not count:
        return ""
    return (
        f" {_processes(count).capitalize()} outside the command's process group "
        f"could not be stopped safely on this system (it does not allow "
        f"signalling one process through a pidfd), so "
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
    if not _is_factory_launch() and not _can_wait_without_collecting():
        # A person's own run only: a factory launch never takes the reduced
        # path (its self-test proved waitid; a refusal later ends the command).
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
        except Exception:  # noqa: BLE001 - e.g. waitid refused mid-run
            _end_hard(proc, entry, since)
        finally:
            if exchange is not None:
                exchange.close()
            _collect(proc)
        raise
    exchange.close()
    _collect(proc)
    stdout, stderr = exchange.output()
    if _is_factory_launch() and Path("/proc/self/stat").exists():
        # Logged, never folded into the command's own output: that output is
        # the project's, published under the merge's redaction rules, and
        # this note is GuardKit's observation, not the command's.
        _warn_uninspectable(proc.pid, since)
    return stdout, stderr, timed_out


def _end_hard(proc: subprocess.Popen, entry: Optional[bytes], since: Optional[int]) -> None:
    """End the command after a failure while watching it, without waitid.

    This process never collects the leader before this, so its number (the
    group's and the session's) is still this command's: the group is sent
    SIGKILL by that number, and each process of the command outside the
    group (in the session, or carrying the marker) is sent SIGKILL through a
    pidfd, checked after pinning. A few looks, bounded; every failure here
    is swallowed (the caller reports the original one).
    """
    _signal_group(proc.pid, signal.SIGKILL)
    deadline = time.monotonic() + _GRACE_SECONDS
    while time.monotonic() < deadline:
        try:
            _members, outside = _look(proc.pid, entry, since)
            if not outside:
                return
            if _signal_outside(outside, proc.pid, entry, since, signal.SIGKILL):
                return  # refused: nothing more can be done safely
        except Exception:  # noqa: BLE001
            return
        time.sleep(_LOOK_INTERVAL_SECONDS)


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
        _collect(proc)
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
    _check_capability()
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
        preexec_fn=None if shell else _first_in_line_before_exec,
    )
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
    _check_capability()
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
        preexec_fn=None if shell else _first_in_line_before_exec,
    )
    out, err, timed_out = _run(
        proc, marker, since, args, input=input, timeout=timeout, grace=grace
    )
    if timed_out:
        raise subprocess.TimeoutExpired(args, timeout, output=out, stderr=err)
    if check and proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, args, output=out, stderr=err)
    return subprocess.CompletedProcess(args, proc.returncode, out, err)
