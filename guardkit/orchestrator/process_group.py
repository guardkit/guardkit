"""Run a project command so that a timeout ends everything it started.

13 October 2026. ``subprocess.run(..., timeout=...)`` kills only the direct
child on a timeout. A project's install or check that starts processes of its
own (a background server, a ``sleep``, a package manager's workers) leaves
them running after the merge has given up on it.

:func:`run_in_own_group` starts the command in a new session, so it and
everything it starts share one process group of their own. On a timeout the
whole group is sent SIGTERM, given a short grace period, then sent SIGKILL.
GuardKit's own process group is never signalled.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

__all__ = ["GroupRun", "run_in_own_group"]

_GRACE_SECONDS = 2.0
_DRAIN_SECONDS = 5.0


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


def _end_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM the command's own group, wait briefly, then SIGKILL it."""
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
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


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
