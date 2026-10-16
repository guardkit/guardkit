"""Ending a command's process group: wait until it is really gone, safely.

16 October 2026. A full test run on a loaded machine found a worker that had
been sent SIGKILL still listed after ``run_project_command`` returned. The
runner now keeps looking (and keeps sending SIGKILL) until nothing in the
group is running, for a bounded time, under two rules from the Codex review:

* the group's leader is never collected while the group is being ended, so
  the group's number cannot be handed to another process and every signal
  sent by number reaches only this command; a leader that is already
  collected means the group is not signalled by number at all;
* not knowing counts as running: only positive evidence ends the wait.

Most tests drive the loop with stand-ins for the operating system, so they do
not depend on timing; the last ones use real processes.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterator, List, Tuple

import pytest

from guardkit.orchestrator import process_group

needs_proc = pytest.mark.skipif(
    not Path("/proc/self/stat").exists(), reason="needs /proc"
)


class _Leader:
    """A command leader that fails the test if anything collects it."""

    pid = 424242
    returncode = None

    def poll(self) -> Any:
        raise AssertionError("the leader was collected while its group was being ended")

    wait = poll
    communicate = poll


def _states(*values: str) -> Iterator[str]:
    """The leader's state on each look; the last value repeats."""
    for value in values:
        yield value
    while True:
        yield values[-1]


@pytest.fixture
def os_stand_in(monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, int]]:
    """Record signals; never sleep; GuardKit's own group is 1."""
    log: List[Tuple[str, int]] = []

    def killpg(pgid: int, sig: int) -> None:
        log.append(("signal", sig))

    monkeypatch.setattr(process_group.os, "killpg", killpg)
    monkeypatch.setattr(process_group.os, "getpgrp", lambda: 1)
    monkeypatch.setattr(process_group.time, "sleep", lambda _s: None)
    return log


def _watch_leader(monkeypatch: pytest.MonkeyPatch, log: list, states: Iterator[str]) -> None:
    def leader_state(_proc: Any) -> str:
        state = next(states)
        log.append(("look", state))
        return state

    monkeypatch.setattr(process_group, "_leader_state", leader_state)


# ---------------------------------------------------------------------------
# The leader is not collected until the group has finished
# ---------------------------------------------------------------------------


def test_the_runner_keeps_killing_until_nothing_is_left_and_never_collects_the_leader(
    monkeypatch: pytest.MonkeyPatch, os_stand_in: list
) -> None:
    _watch_leader(monkeypatch, os_stand_in, _states(process_group._RUNNING, process_group._EXITED))
    finished = iter([False, False, False, True])
    monkeypatch.setattr(process_group, "_group_finished", lambda _p, _g: next(finished))

    process_group._end_group(_Leader(), grace=0.0)  # _Leader fails on any collect

    kills = [v for kind, v in os_stand_in if kind == "signal" and v == signal.SIGKILL]
    assert os_stand_in[1] == ("signal", signal.SIGTERM)
    assert len(kills) == 4, os_stand_in
    with pytest.raises(StopIteration):
        next(finished)


@needs_proc
def test_a_real_group_is_ended_and_its_leader_is_left_for_the_caller() -> None:
    """The shell exits on SIGTERM, its worker ignores SIGTERM. When the group
    has been ended the worker is gone and the shell is still uncollected, so
    its number (the group's) still belongs to this command."""
    proc = subprocess.Popen(
        ["/bin/sh", "-c", '(trap "" TERM; exec sleep 300) & echo $!; wait'],
        stdout=subprocess.PIPE, start_new_session=True, text=True,
    )
    try:
        worker = int(proc.stdout.readline())
        process_group.end_process_group(proc, grace=0.2)
        assert proc.returncode is None, "the leader was collected during the cleanup"
        assert process_group._leader_state(proc) == process_group._EXITED
        os.killpg(proc.pid, 0)  # the uncollected leader still holds the group
        member = process_group._read_member(worker)
        assert member == process_group._GONE or member[0] in ("Z", "X"), member
        assert process_group.leader_exit_code(proc) == -signal.SIGTERM
        assert proc.returncode is None
    finally:
        proc.wait(timeout=10)
        proc.stdout.close()
    assert proc.returncode == -signal.SIGTERM


# ---------------------------------------------------------------------------
# A leader collected elsewhere: the group's number is not signalled
# ---------------------------------------------------------------------------


def test_a_leader_already_collected_means_no_signal_by_number(
    monkeypatch: pytest.MonkeyPatch, os_stand_in: list, caplog: pytest.LogCaptureFixture
) -> None:
    _watch_leader(monkeypatch, os_stand_in, _states(process_group._COLLECTED))
    with caplog.at_level(logging.WARNING, logger=process_group.__name__):
        process_group._end_group(_Leader(), grace=1.0)
    assert [e for e in os_stand_in if e[0] == "signal"] == []
    assert "was not signalled" in caplog.text


def test_a_leader_collected_between_looks_stops_the_signals(
    monkeypatch: pytest.MonkeyPatch, os_stand_in: list, caplog: pytest.LogCaptureFixture
) -> None:
    """The group disappears and its number could be reused between a look and
    the next signal: every signal is sent only straight after a look that
    found the leader uncollected, and none after a look that did not."""
    states = _states(
        process_group._RUNNING,  # before SIGTERM
        process_group._EXITED,  # before the first SIGKILL
        process_group._EXITED,  # before the second
        process_group._COLLECTED,  # something else collected it: stop
    )
    _watch_leader(monkeypatch, os_stand_in, states)
    monkeypatch.setattr(process_group, "_group_finished", lambda _p, _g: False)

    with caplog.at_level(logging.WARNING, logger=process_group.__name__):
        process_group._end_group(_Leader(), grace=0.0)

    for before, entry in zip(os_stand_in, os_stand_in[1:]):
        if entry[0] == "signal":
            assert before == ("look", process_group._RUNNING) or before == (
                "look", process_group._EXITED,
            ), os_stand_in
    assert os_stand_in[-1] == ("look", process_group._COLLECTED), os_stand_in
    assert [v for kind, v in os_stand_in if kind == "signal"] == [
        signal.SIGTERM, signal.SIGKILL, signal.SIGKILL,
    ]
    assert "no longer signalled" in caplog.text


def test_the_wait_after_sigkill_is_bounded(
    monkeypatch: pytest.MonkeyPatch, os_stand_in: list, caplog: pytest.LogCaptureFixture
) -> None:
    """Something that never goes (or never can be confirmed gone) cannot hang
    the runner."""
    clock = iter(float(n) for n in range(10_000))
    monkeypatch.setattr(process_group.time, "monotonic", lambda: next(clock))
    _watch_leader(monkeypatch, os_stand_in, _states(process_group._EXITED))
    monkeypatch.setattr(process_group, "_group_finished", lambda _p, _g: False)

    with caplog.at_level(logging.WARNING, logger=process_group.__name__):
        process_group._end_group(_Leader(), grace=0.0)

    kills = [v for kind, v in os_stand_in if kind == "signal" and v == signal.SIGKILL]
    assert 1 <= len(kills) <= process_group._KILL_WAIT_SECONDS + 2, os_stand_in
    assert "still running" in caplog.text


# ---------------------------------------------------------------------------
# Not knowing counts as running
# ---------------------------------------------------------------------------


def _proc_listing(monkeypatch: pytest.MonkeyPatch, pids: List[int]) -> None:
    monkeypatch.setattr(process_group.os, "listdir", lambda _p: [str(p) for p in pids] + ["self"])


def test_listed_but_unreadable_records_are_not_evidence_of_an_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _proc_listing(monkeypatch, [11, 12])

    def unreadable(path: str, *a: Any, **k: Any) -> Any:
        raise PermissionError(13, "Permission denied", path)

    monkeypatch.setattr(process_group, "open", unreadable, raising=False)
    assert process_group._others_finished(10) is False


def test_a_record_that_vanished_but_whose_entry_is_still_there_is_not_an_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _proc_listing(monkeypatch, [11])

    def vanished(path: str, *a: Any, **k: Any) -> Any:
        raise FileNotFoundError(2, "No such file", path)

    monkeypatch.setattr(process_group, "open", vanished, raising=False)
    monkeypatch.setattr(process_group.os, "stat", lambda _p: os.stat_result((0,) * 10))
    assert process_group._others_finished(10) is False

    def stat_unreadable(path: str) -> Any:
        raise PermissionError(13, "Permission denied", path)

    monkeypatch.setattr(process_group.os, "stat", stat_unreadable)
    assert process_group._others_finished(10) is False


def test_a_record_whose_entry_is_gone_is_finished(monkeypatch: pytest.MonkeyPatch) -> None:
    _proc_listing(monkeypatch, [11])

    def gone(path: str, *a: Any, **k: Any) -> Any:
        raise FileNotFoundError(2, "No such file", path)

    def stat_gone(path: str) -> Any:
        raise FileNotFoundError(2, "No such file", path)

    monkeypatch.setattr(process_group, "open", gone, raising=False)
    monkeypatch.setattr(process_group.os, "stat", stat_gone)
    assert process_group._others_finished(10) is True


def test_a_listing_that_cannot_be_made_is_not_an_end(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_listing(_p: str) -> Any:
        raise PermissionError(13, "Permission denied", "/proc")

    monkeypatch.setattr(process_group.os, "listdir", no_listing)
    assert process_group._others_finished(10) is False


def test_the_group_is_not_finished_when_the_kernel_disagrees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The leader is exited and uncollected, so the kernel must still report
    its group; if it does not, nothing is concluded."""
    monkeypatch.setattr(process_group, "_leader_state", lambda _p: process_group._EXITED)
    monkeypatch.setattr(process_group, "_others_finished", lambda _g: True)

    def no_group(_pgid: int, _sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(process_group.os, "killpg", no_group)
    assert process_group._group_finished(_Leader(), 424242) is False
    monkeypatch.setattr(process_group.os, "killpg", lambda _g, _s: None)
    assert process_group._group_finished(_Leader(), 424242) is True


def test_the_group_is_not_finished_while_the_leader_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_group, "_others_finished", lambda _g: True)
    monkeypatch.setattr(process_group.os, "killpg", lambda _g, _s: None)
    for state in (process_group._RUNNING, process_group._COLLECTED):
        monkeypatch.setattr(process_group, "_leader_state", lambda _p, s=state: s)
        assert process_group._group_finished(_Leader(), 424242) is False


# ---------------------------------------------------------------------------
# Real processes: members, zombies and the leader's exit read without
# collecting it
# ---------------------------------------------------------------------------


@needs_proc
def test_a_running_member_is_not_finished_and_a_zombie_is() -> None:
    leader = subprocess.Popen(
        [sys.executable, "-c", "import os, time; os.fork() or time.sleep(30); time.sleep(30)"],
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and process_group._others_finished(leader.pid):
            time.sleep(0.02)
        assert not process_group._others_finished(leader.pid), "the forked member was missed"
    finally:
        os.killpg(leader.pid, signal.SIGKILL)
        leader.wait()

    # A member that has finished but is not collected yet is not running.
    child = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    try:
        while process_group._leader_state(child) != process_group._EXITED:
            time.sleep(0.02)
        member = process_group._read_member(child.pid)
        assert member != process_group._GONE and member[0] == "Z"
    finally:
        child.wait()


@needs_proc
def test_the_leaders_exit_is_read_without_collecting_it() -> None:
    proc = subprocess.Popen([sys.executable, "-c", "raise SystemExit(7)"])
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and process_group.leader_exit_code(proc) is None:
            time.sleep(0.02)
        assert process_group.leader_exit_code(proc) == 7
        assert proc.returncode is None
        assert process_group._leader_state(proc) == process_group._EXITED
    finally:
        assert proc.wait(timeout=5) == 7
    assert process_group._leader_state(proc) == process_group._COLLECTED
    assert process_group.leader_exit_code(proc) == 7
