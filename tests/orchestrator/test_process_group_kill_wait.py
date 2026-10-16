"""After SIGKILL the runner waits until the command's group is really gone.

16 October 2026. A full test run on a loaded machine found a worker that had
been sent SIGKILL still listed after ``run_project_command`` returned. The
runner now keeps looking (and keeps sending SIGKILL) until no live process
is left in the group, for a bounded time. These tests drive that loop with
a stand-in for the operating system, so they do not depend on timing.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

import pytest

from guardkit.orchestrator import process_group


class _FakeProc:
    pid = 424242

    def poll(self) -> None:
        return None


@pytest.fixture
def signals(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[int, int]]:
    sent: List[Tuple[int, int]] = []

    def killpg(pgid: int, sig: int) -> None:
        sent.append((pgid, sig))

    monkeypatch.setattr(process_group.os, "killpg", killpg)
    monkeypatch.setattr(process_group.os, "getpgrp", lambda: 1)
    monkeypatch.setattr(process_group.time, "sleep", lambda _s: None)
    return sent


def test_the_runner_waits_until_no_live_member_is_left(
    monkeypatch: pytest.MonkeyPatch, signals: List[Tuple[int, int]]
) -> None:
    """A killed worker still exiting keeps the runner waiting; it returns
    as soon as nothing live is left."""
    looks = iter([True, True, True, False])
    monkeypatch.setattr(process_group, "_group_alive", lambda _pgid: True)
    monkeypatch.setattr(process_group, "_group_has_live_member", lambda _pgid: next(looks))

    process_group._end_group(_FakeProc(), grace=0.0)

    kills = [sig for _pgid, sig in signals if sig == signal.SIGKILL]
    assert signals[0] == (_FakeProc.pid, signal.SIGTERM)
    assert len(kills) == 4, signals  # one per look, until the group was empty
    with pytest.raises(StopIteration):
        next(looks)


def test_the_wait_after_sigkill_is_bounded(
    monkeypatch: pytest.MonkeyPatch, signals: List[Tuple[int, int]]
) -> None:
    """A process that never goes cannot hang the runner."""
    clock = iter(float(n) for n in range(10_000))
    monkeypatch.setattr(process_group.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(process_group, "_group_alive", lambda _pgid: True)
    monkeypatch.setattr(process_group, "_group_has_live_member", lambda _pgid: True)

    process_group._end_group(_FakeProc(), grace=0.0)

    kills = [sig for _pgid, sig in signals if sig == signal.SIGKILL]
    assert 1 <= len(kills) <= process_group._KILL_WAIT_SECONDS + 2, signals


def test_the_wait_stops_when_the_group_has_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Once no process has the group's id, SIGKILL fails and the runner stops."""
    sent: List[int] = []

    def killpg(_pgid: int, sig: int) -> None:
        sent.append(sig)
        if sig == signal.SIGKILL:
            raise ProcessLookupError

    monkeypatch.setattr(process_group.os, "killpg", killpg)
    monkeypatch.setattr(process_group.os, "getpgrp", lambda: 1)
    monkeypatch.setattr(process_group, "_group_alive", lambda _pgid: True)
    process_group._end_group(_FakeProc(), grace=0.0)
    assert sent == [signal.SIGTERM, signal.SIGKILL]


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_zombie_is_not_a_live_member() -> None:
    """A finished child nobody has reaped yet does not keep the runner waiting."""
    child = subprocess.Popen(
        [sys.executable, "-c", "pass"], start_new_session=True
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with open(f"/proc/{child.pid}/stat", encoding="utf-8") as fh:
                if fh.read().rsplit(")", 1)[1].split()[0] == "Z":
                    break
            time.sleep(0.02)
        assert process_group._group_alive(child.pid)  # the zombie still holds the group
        assert not process_group._group_has_live_member(child.pid)
    finally:
        child.wait()
    assert not process_group._group_alive(child.pid)


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="needs /proc")
def test_a_running_member_is_live() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True
    )
    try:
        assert process_group._group_has_live_member(child.pid)
    finally:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()
