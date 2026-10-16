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
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Dict, Mapping, Optional, Sequence, Tuple, Union

__all__ = [
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


def end_process_group(proc: subprocess.Popen, grace: float = _GRACE_SECONDS) -> None:
    """End every process in the group ``proc`` leads (started with
    ``start_new_session=True``), whether or not ``proc`` itself is still alive.

    SIGTERM goes to the whole group; then the group itself (never only the
    leader) is watched, and anything still in it after ``grace`` seconds,
    such as a worker that ignores SIGTERM after the leader has exited, is
    sent SIGKILL. It returns once nothing in the group is running, or after
    a bounded wait. GuardKit's own group is never signalled.

    ``proc`` must not have been collected yet (use :func:`leader_exit_code`,
    not ``proc.poll()``, to see whether it has exited): a collected leader's
    number may already belong to someone else, so its group is then not
    signalled at all, and a warning says so. The caller collects ``proc``
    afterwards.
    """
    _end_group(proc, grace)


def _end_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM the command's own group, wait briefly, then SIGKILL it until
    nothing in it is running (bounded). Never collects the leader."""
    pgid = proc.pid  # a session leader's group id is its own pid
    if pgid == os.getpgrp():  # pragma: no cover - start_new_session prevents it
        proc.kill()
        return
    if _leader_state(proc) == _COLLECTED:
        logger.warning(
            "process group %s was not signalled: its leader has already been "
            "collected, so the group's number may belong to another process",
            pgid,
        )
        return
    # The leader is uncollected, so the number names this command's group.
    os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if _group_finished(proc, pgid):
            return
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
            return
        os.killpg(pgid, signal.SIGKILL)
        if _group_finished(proc, pgid):
            return
        if time.monotonic() >= deadline:
            logger.warning(
                "process group %s: something in it was still running %.0f "
                "seconds after SIGKILL, or could not be confirmed gone",
                pgid,
                _KILL_WAIT_SECONDS,
            )
            return
        time.sleep(_LOOK_INTERVAL_SECONDS)


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

    Output is decoded as UTF-8 with undecodable bytes replaced. Raises
    ``OSError`` when the command cannot be started at all, as
    ``subprocess.run`` does.
    """
    proc = subprocess.Popen(
        args if shell else list(args),
        shell=shell,
        cwd=str(cwd),
        env=env,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return GroupRun(proc.returncode, stdout or "", stderr or "")
    except subprocess.TimeoutExpired:
        # A timed-out communicate() has not collected the leader, so its
        # group's number is still this command's (see _end_group).
        _end_group(proc, grace)
        try:
            stdout, stderr = proc.communicate(timeout=_DRAIN_SECONDS)
        except subprocess.TimeoutExpired:
            # Something left the group and still holds the output open.
            proc.kill()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:  # pragma: no cover
                pass
            stdout, stderr = "", ""
        return GroupRun(None, stdout or "", stderr or "", timed_out=True)


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
    """
    if capture_output:
        if stdout is not None or stderr is not None:
            raise ValueError("stdout and stderr may not be used with capture_output")
        stdout = stderr = subprocess.PIPE
    if input is not None and stdin is None:
        stdin = subprocess.PIPE
    proc = subprocess.Popen(
        args if shell or isinstance(args, str) else list(args),
        shell=shell,
        cwd=str(cwd) if cwd is not None else None,
        env=dict(env) if env is not None else None,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        text=text or None,
        encoding=encoding,
        errors=errors,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        # A timed-out communicate() has not collected the leader, so its
        # group's number is still this command's (see _end_group).
        _end_group(proc, grace)
        try:
            out, err = proc.communicate(timeout=_DRAIN_SECONDS)
        except subprocess.TimeoutExpired:
            # Something left the group and still holds the output open.
            proc.kill()
            try:
                out, err = proc.communicate(timeout=1)
            except subprocess.TimeoutExpired:  # pragma: no cover
                out, err = None, None
        raise subprocess.TimeoutExpired(args, timeout, output=out, stderr=err)
    except BaseException:
        # If the leader was already collected, _end_group says so and sends
        # nothing by number.
        _end_group(proc, 0.0)
        proc.wait()
        raise
    if check and proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, args, output=out, stderr=err)
    return subprocess.CompletedProcess(args, proc.returncode, out, err)
