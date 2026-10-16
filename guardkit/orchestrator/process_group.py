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
seconds later). The runner now waits, for a bounded time, until no live
process is left in the group, sending SIGKILL again on each look.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Dict, Mapping, Optional, Sequence, Union

__all__ = ["GroupRun", "end_process_group", "run_in_own_group", "run_project_command"]

_GRACE_SECONDS = 2.0
_DRAIN_SECONDS = 5.0
_KILL_WAIT_SECONDS = 10.0


@dataclass(frozen=True)
class GroupRun:
    """What one command run produced."""

    returncode: Optional[int]  # None when it timed out
    stdout: str
    stderr: str
    timed_out: bool = False


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _group_has_live_member(pgid: int) -> bool:
    """Whether any process that is not already a zombie is in group ``pgid``.

    A zombie has finished; only its parent's reaping is outstanding, and
    an orphan's new parent (which may be a container's first process) may
    never do that. Where ``/proc`` cannot be read, any member counts.
    """
    if not _group_alive(pgid):
        return False
    try:
        entries = os.listdir("/proc")
    except OSError:
        return True
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat", encoding="utf-8", errors="replace") as fh:
                fields = fh.read().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue  # gone since the listing, or not readable
        if len(fields) > 2 and fields[2] == str(pgid) and fields[0] not in ("Z", "X"):
            return True
    return False


def end_process_group(proc: subprocess.Popen, grace: float = _GRACE_SECONDS) -> None:
    """End every process in the group ``proc`` leads (started with
    ``start_new_session=True``), whether or not ``proc`` itself is still alive.

    SIGTERM goes to the whole group; then the group itself (never only the
    leader) is watched, and anything still in it after ``grace`` seconds,
    such as a worker that ignores SIGTERM after the leader has exited, is
    sent SIGKILL. It returns once no live process is left in the group, or
    after a bounded wait. GuardKit's own group is never signalled.
    """
    _end_group(proc, grace)


def _end_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM the command's own group, wait briefly, then SIGKILL it.

    Judged on the group's original id, not on the leader: the leader may
    exit on SIGTERM while a member that ignores it lives on.
    """
    pgid = proc.pid  # a session leader's group id is its own pid
    if pgid == os.getpgrp():  # pragma: no cover - start_new_session prevents it
        proc.kill()
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        proc.poll()  # reap the leader so only live members keep the group
        if not _group_alive(pgid):
            return
        time.sleep(0.05)
    # SIGKILL cannot be ignored, but a killed process is only gone once it
    # has finished exiting. Wait for that, so that when this returns nothing
    # the command started is still running; send SIGKILL again on each look
    # in case anything is still in the group.
    deadline = time.monotonic() + _KILL_WAIT_SECONDS
    while True:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            return
        proc.poll()
        if not _group_has_live_member(pgid) or time.monotonic() >= deadline:
            return
        time.sleep(0.05)


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
        _end_group(proc, 0.0)
        proc.wait()
        raise
    if check and proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, args, output=out, stderr=err)
    return subprocess.CompletedProcess(args, proc.returncode, out, err)
