"""A project command leaves nothing running, goes first when memory runs out,
and is told no one is watching (19 October 2026).

In a factory build, the sandbox ran out of memory while a command held
dozens of test-runner processes under ``timeout N <test command> | tail``, and
the kernel stopped GuardKit, the biggest single process. The runner for the
commands a build is judged by ended a command's process group on a timeout
only: nothing when the command returned, and nothing that moved out of the
group (``timeout`` moves itself and what it runs into a group of its own).

These tests show, with harmless ``sleep`` processes standing in for a
forgotten server, watcher or test run:

* what a command leaves running is ended when it returns, also in a group of
  its own (``timeout``), in a session of its own (``setsid``, found by the
  command's marker) and without the marker (found by the session); the log
  says so, naming the command and how many processes;
* a process that keeps the output open does not hold the caller until the
  time limit;
* on a timeout the command and everything it started are ended;
* processes the command did not start are never touched;
* the command's processes go first when memory runs out, GuardKit's own
  process does not change, and a program run directly cannot start anything
  before its score is set;
* ``run_project_command`` still behaves as ``subprocess.run``;
* the project's commands get ``CI=true`` unless the project declares ``CI``.

No network, no model and no ``claude``. Every process started here is killed
by the test's own clean-up if the code under test fails to.
"""

from __future__ import annotations

import errno
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import textwrap
import time
from pathlib import Path
from typing import Iterator, List, Set

import pytest

from guardkit.orchestrator import process_group
from guardkit.orchestrator import project_command_env as pce
from guardkit.orchestrator.launch_declaration import LaunchDeclaration
from guardkit.orchestrator.process_group import (
    COMMAND_MARKER_NAME,
    run_in_own_group,
    run_project_command,
)

linux_only = pytest.mark.skipif(
    sys.platform != "linux" or not Path("/proc/self/stat").exists(),
    reason="the process checks read /proc",
)

_ENV = {"PATH": "/usr/bin:/bin"}
_WAIT_FOR = "while [ ! -s {name} ]; do sleep 0.05; done"


def _alive(pid: int) -> bool:
    try:
        data = Path(f"/proc/{pid}/stat").read_bytes()
    except OSError:
        return False
    return data[data.rindex(b")") + 2 :].split()[0] not in (b"Z", b"X")


def _pid(folder: Path, name: str) -> int:
    return int((folder / name).read_text().strip())


@pytest.fixture
def started(tmp_path: Path) -> Iterator[List[int]]:
    """Pids the test started; any still running at the end are killed."""
    pids: List[int] = []
    yield pids
    for name in ("bg.pid", "inner.pid", "fg.pid"):
        file = tmp_path / name
        if file.exists():
            try:
                pids.append(int(file.read_text().strip()))
            except ValueError:
                pass
    for pid in pids:
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def _run(tmp_path: Path, command: str, **kwargs):
    kwargs.setdefault("timeout", 60)
    kwargs.setdefault("env", dict(_ENV))
    return run_project_command(
        command, shell=True, cwd=str(tmp_path), capture_output=True, text=True, **kwargs,
    )


# ---------------------------------------------------------------------------
# What a command leaves behind
# ---------------------------------------------------------------------------


@linux_only
class TestLeftoversAreEnded:
    def test_a_background_process_is_ended_when_the_command_returns(
        self, tmp_path: Path, started: List[int], caplog: pytest.LogCaptureFixture
    ) -> None:
        command = "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; echo started"
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            proc = _run(tmp_path, command)

        assert proc.returncode == 0
        assert proc.stdout == "started\n"
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert caplog.records[-1].getMessage() == (
            "A project command finished but left 1 process running; it was "
            f"stopped. The command: {command}"
        )

    def test_run_in_own_group_ends_it_too(
        self, tmp_path: Path, started: List[int]
    ) -> None:
        run = run_in_own_group(
            "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; echo started",
            shell=True, cwd=tmp_path, env=dict(_ENV), timeout=60,
        )

        assert (run.returncode, run.stdout, run.timed_out) == (0, "started\n", False)
        assert not _alive(_pid(tmp_path, "bg.pid"))

    def test_a_process_in_a_group_of_its_own_is_ended(
        self, tmp_path: Path, started: List[int], caplog: pytest.LogCaptureFixture
    ) -> None:
        # The incident's shape: ``timeout`` moves itself and what it runs
        # into a process group of its own, still in the command's session.
        if shutil.which("timeout", path=_ENV["PATH"]) is None:
            pytest.skip("no timeout program")
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            proc = _run(
                tmp_path,
                "timeout 120 sh -c 'echo $$ > inner.pid; exec sleep 300' "
                ">/dev/null 2>&1 & echo $! > bg.pid; "
                + _WAIT_FOR.format(name="inner.pid"),
            )

        assert proc.returncode == 0
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert not _alive(_pid(tmp_path, "inner.pid"))
        assert "left 2 processes running; they were stopped" in caplog.text

    def test_a_process_in_a_session_of_its_own_is_ended(
        self, tmp_path: Path, started: List[int]
    ) -> None:
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")
        _run(
            tmp_path,
            "setsid sh -c 'echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
            + _WAIT_FOR.format(name="bg.pid"),
        )

        assert not _alive(_pid(tmp_path, "bg.pid"))

    def test_a_process_without_the_marker_is_ended_by_its_session(
        self, tmp_path: Path, started: List[int]
    ) -> None:
        # Out of the group (``timeout``) and without the marker: only the
        # session finds it.
        if shutil.which("timeout", path=_ENV["PATH"]) is None:
            pytest.skip("no timeout program")
        _run(
            tmp_path,
            f"env -u {COMMAND_MARKER_NAME} timeout 120 sh -c 'echo $$ > bg.pid; "
            "exec sleep 300' >/dev/null 2>&1 & " + _WAIT_FOR.format(name="bg.pid"),
        )

        assert not _alive(_pid(tmp_path, "bg.pid"))

    def test_a_process_that_ignores_sigterm_is_killed(
        self, tmp_path: Path, started: List[int], caplog: pytest.LogCaptureFixture
    ) -> None:
        # One in the command's group, one outside it (setsid): SIGKILL ends
        # both after SIGTERM's grace.
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")
        began = time.monotonic()
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            proc = _run(
                tmp_path,
                "sh -c 'trap \"\" TERM; echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
                "setsid sh -c 'trap \"\" TERM; echo $$ > inner.pid; exec sleep 300' "
                ">/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="bg.pid") + "; " + _WAIT_FOR.format(name="inner.pid"),
                grace=0.5,
            )
        took = time.monotonic() - began

        assert proc.returncode == 0
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert not _alive(_pid(tmp_path, "inner.pid"))
        assert took >= 0.5
        assert "left 2 processes running; they were stopped" in caplog.text
        assert "still running" not in caplog.text

    @pytest.mark.personal_run
    def test_without_a_pidfd_a_process_outside_the_group_is_never_signalled(
        self,
        tmp_path: Path,
        started: List[int],
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # A security filter may refuse pidfd_open (EPERM). The command's own
        # group is still ended (by the number its uncollected leader pins),
        # but a process that left the group is never signalled by number:
        # it is left running and the log says so plainly.
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")

        def refused(_pid: int) -> int:
            raise PermissionError(errno.EPERM, "refused by a filter")

        def no_kill(pid: int, sig: int) -> None:
            raise AssertionError(f"signalled {pid} by number")

        monkeypatch.setattr(process_group.os, "pidfd_open", refused)
        monkeypatch.setattr(process_group.os, "kill", no_kill)
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            proc = _run(
                tmp_path,
                "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; "
                "setsid sh -c 'echo $$ > inner.pid; exec sleep 300' >/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="inner.pid"),
                grace=0.3,
            )

        monkeypatch.undo()  # the clean-up below signals the one left running

        assert proc.returncode == 0
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert _alive(_pid(tmp_path, "inner.pid"))
        assert (
            "left 2 processes running; 1 was stopped. 1 process outside the "
            "command's process group could not be stopped safely on this system "
            "(it does not allow signalling one process through a pidfd), so it is "
            "still running."
        ) in caplog.text

    @pytest.mark.personal_run
    def test_a_refused_signal_through_a_pidfd_is_reported_not_counted(
        self,
        tmp_path: Path,
        started: List[int],
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # The pidfd opens but the signal is refused (EPERM): the process was
        # not signalled, so it is reported as still running, never as gone.
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")

        def refused(_handle: int, _sig: int) -> None:
            raise PermissionError(errno.EPERM, "refused by a filter")

        monkeypatch.setattr(process_group.signal, "pidfd_send_signal", refused)
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            _run(
                tmp_path,
                "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; "
                "setsid sh -c 'echo $$ > inner.pid; exec sleep 300' >/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="inner.pid"),
                grace=0.3,
            )
        monkeypatch.undo()

        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert _alive(_pid(tmp_path, "inner.pid"))
        assert "left 2 processes running; 1 was stopped. 1 process outside" in caplog.text

    def test_a_process_that_no_longer_belongs_after_pinning_is_not_signalled(
        self, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The re-check after pinning: a process listed as the command's but no
        # longer its own once pinned (its number was handed on before the
        # pidfd was opened) is not signalled.
        stranger = subprocess.Popen(["sleep", "300"], start_new_session=True)
        started.append(stranger.pid)
        monkeypatch.setattr(process_group, "_belongs", lambda *_a: None)
        monkeypatch.setattr(
            process_group, "_pidfd_send_signal",
            lambda handle, sig: pytest.fail("signalled a process that is not the command's"),
        )
        try:
            refused = process_group._signal_outside(
                {stranger.pid}, os.getpid() + 1, None, None, signal.SIGKILL
            )
            time.sleep(0.2)
            assert refused == set()
            assert _alive(stranger.pid)
        finally:
            monkeypatch.undo()
            stranger.kill()
            stranger.wait()

    def test_a_number_reused_after_pinning_is_never_signalled(
        self, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Simulated at the check/signal boundary: the pidfd was opened for the
        # process that held the number, which then ended; the number now
        # names another process, which even passes the ownership check. The
        # signal goes to the ended process, so the other one is untouched.
        gone = subprocess.Popen(["true"])
        stale = os.pidfd_open(gone.pid)
        gone.wait()
        victim = subprocess.Popen(["sleep", "300"], start_new_session=True)
        started.append(victim.pid)
        monkeypatch.setattr(
            process_group, "_belongs", lambda *_a: ("S", victim.pid, victim.pid, 0)
        )
        monkeypatch.setattr(process_group.os, "pidfd_open", lambda pid: os.dup(stale))
        monkeypatch.setattr(
            process_group.os, "kill", lambda pid, sig: pytest.fail(f"signalled {pid}")
        )
        try:
            refused = process_group._signal_outside(
                {victim.pid}, os.getpid() + 1, None, None, signal.SIGKILL
            )
            time.sleep(0.2)
            assert refused == set()
            assert _alive(victim.pid)
        finally:
            monkeypatch.undo()
            os.close(stale)
            victim.kill()
            victim.wait()

    def test_an_interrupted_run_still_ends_the_command(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The caller is interrupted while the command runs (Ctrl-C, a
        # cancelled task): the command and what it started are ended, then
        # the interruption goes on.
        def interrupted(self, _timeout):
            deadline = time.monotonic() + 20
            while not (tmp_path / "fg.pid").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            raise KeyboardInterrupt

        process_group._check_capability()  # the self-test, before wait is patched
        monkeypatch.setattr(process_group._Exchange, "wait", interrupted)
        began = time.monotonic()
        with pytest.raises(KeyboardInterrupt):
            _run(
                tmp_path,
                "setsid sh -c 'echo $$ > bg.pid; exec sleep 600' >/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="bg.pid")
                + "; echo $$ > fg.pid; exec sleep 600",
            )

        # Ended, not waited for: the command would run ten minutes.
        assert time.monotonic() - began < 30
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert not _alive(_pid(tmp_path, "fg.pid"))

    def test_a_group_that_refuses_the_signal_is_said_plainly(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        def refused(_pgid: int, _sig: int) -> None:
            raise PermissionError(errno.EPERM, "another user's process")

        monkeypatch.setattr(process_group.os, "killpg", refused)
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            process_group._signal_group(424242, signal.SIGTERM)

        assert "could not be signalled: permission refused" in caplog.text

    def test_a_process_holding_the_output_does_not_hold_the_caller(
        self, tmp_path: Path, started: List[int]
    ) -> None:
        began = time.monotonic()
        proc = _run(tmp_path, "sleep 300 & echo $! > bg.pid; echo done", timeout=40)
        took = time.monotonic() - began

        assert took < 20
        assert (proc.returncode, proc.stdout) == (0, "done\n")
        assert not _alive(_pid(tmp_path, "bg.pid"))

    def test_a_timeout_ends_the_command_and_everything_it_started(
        self, tmp_path: Path, started: List[int], caplog: pytest.LogCaptureFixture
    ) -> None:
        began = time.monotonic()
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            with pytest.raises(subprocess.TimeoutExpired) as caught:
                _run(
                    tmp_path,
                    "setsid sh -c 'echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
                    + _WAIT_FOR.format(name="bg.pid")
                    + "; echo $$ > fg.pid; echo partial; sleep 300",
                    timeout=2,
                )
        took = time.monotonic() - began

        assert took < 20
        assert caught.value.stdout == "partial\n"
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert not _alive(_pid(tmp_path, "fg.pid"))
        assert "ran past its time limit (2s)" in caplog.text

    def test_processes_the_command_did_not_start_are_left_alone(
        self, tmp_path: Path, started: List[int]
    ) -> None:
        before = subprocess.Popen(["sleep", "300"], start_new_session=True, env=dict(_ENV))
        started.append(before.pid)
        strangers = [before]
        stranger_env = {**_ENV, COMMAND_MARKER_NAME: "f" * 32}

        def start_during() -> None:
            during = subprocess.Popen(["sleep", "300"], start_new_session=True, env=stranger_env)
            started.append(during.pid)
            strangers.append(during)

        timer = threading.Timer(0.3, start_during)
        timer.start()
        try:
            proc = _run(tmp_path, "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; sleep 1.5")
            timer.join()

            assert proc.returncode == 0
            assert len(strangers) == 2
            assert not _alive(_pid(tmp_path, "bg.pid"))
            assert all(_alive(p.pid) for p in strangers)
        finally:
            timer.cancel()
            timer.join()
            for p in strangers:
                p.kill()
                p.wait()

    def test_end_process_group_also_ends_the_session(
        self, started: List[int]
    ) -> None:
        # The serve probe's shape: started by the caller, ended with
        # end_process_group. A worker that left the group still goes.
        if shutil.which("timeout", path=_ENV["PATH"]) is None:
            pytest.skip("no timeout program")
        proc = subprocess.Popen(
            ["/bin/sh", "-c", "timeout 120 sleep 300 & echo $!; wait"],
            stdout=subprocess.PIPE, start_new_session=True, text=True, env=dict(_ENV),
        )
        try:
            worker = int(proc.stdout.readline())
            started.append(worker)
            process_group.end_process_group(proc, grace=0.5)
            assert proc.returncode is None, "the leader was collected during the cleanup"
            assert not _alive(worker)
        finally:
            proc.wait(timeout=10)
            proc.stdout.close()

    def test_a_quick_command_says_nothing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            proc = _run(tmp_path, "echo hi")
        assert proc.stdout == "hi\n"
        assert caplog.records == []


# ---------------------------------------------------------------------------
# First in line when memory runs out
# ---------------------------------------------------------------------------


@linux_only
class TestCommandsGoFirstWhenMemoryRunsOut:
    def test_a_shell_command_and_what_it_starts(self, tmp_path: Path) -> None:
        shell = _run(tmp_path, "cat /proc/$$/oom_score_adj")
        child = _run(tmp_path, "cat /proc/self/oom_score_adj")
        grandchild = _run(tmp_path, "sh -c 'sh -c \"cat /proc/self/oom_score_adj\"'")

        assert shell.stdout == child.stdout == grandchild.stdout == "1000\n"

    def test_guardkits_own_value_never_changes(self, tmp_path: Path) -> None:
        # In a fresh process, so no earlier test can have changed it first.
        script = (
            "import subprocess\n"
            "from pathlib import Path\n"
            "from guardkit.orchestrator.process_group import run_project_command\n"
            "own = Path('/proc/self/oom_score_adj').read_text().strip()\n"
            "env = {'PATH': '/usr/bin:/bin'}\n"
            "run_project_command('true', shell=True, env=env, timeout=30)\n"
            "run_project_command(['true'], env=env, timeout=30)\n"
            "try:\n"
            "    run_project_command('sleep 30', shell=True, env=env, timeout=1)\n"
            "except subprocess.TimeoutExpired:\n"
            "    pass\n"
            "print(own, Path('/proc/self/oom_score_adj').read_text().strip())\n"
        )
        root = Path(process_group.__file__).resolve().parents[2]
        done = subprocess.run(
            [sys.executable, "-c", script], cwd=str(tmp_path), capture_output=True,
            text=True, timeout=60, env={**os.environ, "PYTHONPATH": str(root)},
        )
        assert done.returncode == 0, done.stderr
        before, after = done.stdout.split()
        assert before == after
        assert after != "1000"

    def test_a_program_run_directly_cannot_fork_before_its_score_is_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Synchronised, not timed: Popen does not return until the program
        # has already started a child and that child has recorded its score.
        # A score written after Popen returns would be too late for it.
        record = tmp_path / "child.txt"
        process_group._check_capability()  # the self-test, before Popen is patched
        base = process_group.subprocess.Popen

        class ReturnsLate(base):  # type: ignore[misc, valid-type]
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if record.exists() and record.read_text(encoding="ascii"):
                        break
                    time.sleep(0.01)

        monkeypatch.setattr(process_group.subprocess, "Popen", ReturnsLate)
        proc = run_project_command(
            ["sh", "-c", f"sh -c 'cat /proc/self/oom_score_adj > {record}'; echo done"],
            cwd=str(tmp_path), env=dict(_ENV), capture_output=True, text=True, timeout=30,
        )
        monkeypatch.undo()

        assert proc.stdout == "done\n"
        assert record.read_text(encoding="ascii") == "1000\n"
        assert Path("/proc/self/oom_score_adj").read_text().strip() != "1000"

    def test_a_program_run_directly_and_what_it_starts_later(self, tmp_path: Path) -> None:
        proc = run_project_command(
            ["sh", "-c", "sleep 0.3; cat /proc/$$/oom_score_adj; "
             "sh -c 'cat /proc/self/oom_score_adj'"],
            cwd=str(tmp_path), env=dict(_ENV), capture_output=True, text=True, timeout=30,
        )
        assert proc.stdout == "1000\n1000\n"

    def test_the_shell_still_leads_the_session(self, tmp_path: Path) -> None:
        proc = _run(tmp_path, "awk '{print $6}' /proc/$$/stat; echo $$")
        session, shell = proc.stdout.split()
        assert session == shell


class TestCleanupCapability:
    """A factory build must leave nothing running: where a command's
    leftovers cannot all be stopped safely, a factory launch's project
    commands are refused before they start; a person's own run goes on with
    the reduced clean-up and one warning."""

    _MISSING = (
        "pidfd_open is refused here by the kernel or a security filter "
        "(Operation not permitted)"
    )

    _ADVICE = (
        "Run the factory where /proc can be read and waitid, pidfd_open and "
        "pidfd_send_signal are allowed (Linux 5.3 or later)."
    )

    @pytest.fixture
    def missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A factory launch: the self-test fails; a person's run: the check
        # finds the same thing missing.
        monkeypatch.setattr(process_group, "_self_test", lambda: self._MISSING)
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        monkeypatch.setattr(process_group, "_CAPABILITY", [self._MISSING])
        monkeypatch.setattr(process_group, "_WARNED", [])

    @pytest.fixture
    def fresh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The self-test runs again (for real) in this test."""
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        monkeypatch.setattr(process_group, "_CAPABILITY", [])

    @pytest.fixture
    def passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The self-test passed earlier in this process (a cached success)."""
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])

    @linux_only
    def test_this_system_has_everything_needed(self) -> None:
        assert process_group._missing_capability() is None

    @staticmethod
    def _self_test_processes() -> Set[int]:
        marker_name = process_group.COMMAND_MARKER_NAME.encode()
        found = set()
        for name in os.listdir("/proc"):
            if not name.isdigit():
                continue
            try:
                environ = Path(f"/proc/{name}/environ").read_bytes()
                cmdline = Path(f"/proc/{name}/cmdline").read_bytes()
            except OSError:
                continue
            if marker_name in environ and b"os.setsid()" in cmdline and _alive(int(name)):
                found.add(int(name))
        return found

    @linux_only
    def test_the_self_test_passes_here_and_leaves_nothing(self) -> None:
        before_fds = len(os.listdir("/proc/self/fd"))
        before = self._self_test_processes()  # earlier tests' refused ones
        assert process_group._self_test() is None
        assert len(os.listdir("/proc/self/fd")) == before_fds
        assert self._self_test_processes() - before == set()

    @linux_only
    def test_a_refused_pidfd_is_named(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def refused(_pid: int) -> int:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group.os, "pidfd_open", refused)
        assert process_group._missing_capability() == self._MISSING

    @linux_only
    def test_a_refused_signal_through_a_pidfd_is_named_and_refuses_a_factory_launch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A filter may allow opening a pidfd and refuse signalling through it.
        def refused(_handle: int, _sig: int) -> None:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group.signal, "pidfd_send_signal", refused)
        monkeypatch.setattr(process_group, "_CAPABILITY", [])
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        monkeypatch.setenv("GUARDKIT_FACTORY_LAUNCH", "build-x")
        expected = (
            "pidfd_send_signal is refused here by the kernel or a security filter "
            "(Operation not permitted)"
        )

        assert process_group._missing_capability() == expected
        with pytest.raises(process_group.CleanupUnavailableError) as caught:
            _run(tmp_path, "touch ran")
        assert caught.value.reason == expected
        assert not (tmp_path / "ran").exists()

    @linux_only
    def test_a_python_without_the_pidfd_wrappers_uses_the_system_calls(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Some standalone Python builds (uv-managed ones) lack os.pidfd_open
        # and signal.pidfd_send_signal although the kernel has the calls.
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")
        monkeypatch.delattr(os, "pidfd_open")
        monkeypatch.delattr(signal, "pidfd_send_signal")
        monkeypatch.setattr(process_group, "_CAPABILITY", [])
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])

        assert process_group._missing_capability() is None
        assert process_group._self_test() is None
        _run(
            tmp_path,
            "setsid sh -c 'echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
            + _WAIT_FOR.format(name="bg.pid"),
        )
        monkeypatch.undo()

        assert not _alive(_pid(tmp_path, "bg.pid"))

    @linux_only
    def test_without_wrappers_or_system_calls_the_python_build_is_named(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refused(_number: int, *_args: object) -> int:
            raise OSError(errno.EPERM, "Operation not permitted")

        monkeypatch.delattr(os, "pidfd_open")
        monkeypatch.setattr(process_group, "_raw_syscall", refused)
        monkeypatch.setattr(process_group, "_CAPABILITY", [])
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        expected = (
            "this Python build lacks pidfd_open, and the system call itself is "
            "refused by the kernel or a security filter (Operation not permitted)"
        )

        assert process_group._missing_capability() == expected
        with pytest.raises(process_group.CleanupUnavailableError, match="Python build lacks"):
            _run(tmp_path, "touch ran")
        assert not (tmp_path / "ran").exists()

    def test_without_wrappers_off_linux_the_platform_is_named(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if not Path("/proc/self/stat").exists():
            pytest.skip("needs /proc")
        monkeypatch.delattr(os, "pidfd_open", raising=False)
        monkeypatch.setattr(process_group.sys, "platform", "darwin")
        assert process_group._missing_capability() == (
            "this Python build lacks pidfd_open, and this system is not Linux"
        )

    @linux_only
    @pytest.mark.parametrize("send", ["works", "refused"])
    def test_the_probe_closes_its_pidfd(
        self, monkeypatch: pytest.MonkeyPatch, send: str
    ) -> None:
        if send == "refused":
            def refused(_handle: int, _sig: int) -> None:
                raise PermissionError(errno.EPERM, "Operation not permitted")

            monkeypatch.setattr(signal, "pidfd_send_signal", refused)
        before = len(os.listdir("/proc/self/fd"))
        for _ in range(20):
            process_group._missing_capability()
        assert len(os.listdir("/proc/self/fd")) == before

    @linux_only
    def test_a_refused_waitid_is_named_and_neither_entry_point_starts_the_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # os.waitid exists but a filter refuses it: the probe makes the call.
        def refused(*_args: object) -> None:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group.os, "waitid", refused)
        monkeypatch.setattr(process_group, "_CAPABILITY", [])
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        expected = (
            "waitid is refused here by the kernel or a security filter "
            "(Operation not permitted)"
        )
        assert process_group._missing_capability() == expected
        for run in (
            lambda: _run(tmp_path, "touch ran"),
            lambda: run_in_own_group(
                "touch ran", shell=True, cwd=tmp_path, env=dict(_ENV), timeout=30
            ),
        ):
            with pytest.raises(process_group.CleanupUnavailableError) as caught:
                run()
            assert expected in caught.value.strerror
        assert not (tmp_path / "ran").exists()

    @linux_only
    @pytest.mark.personal_run
    def test_a_refused_waitid_on_a_persons_run_falls_back_and_never_hangs(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def refused(*_args: object) -> None:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group.os, "waitid", refused)
        monkeypatch.setattr(process_group, "_CAPABILITY", [])
        monkeypatch.setattr(process_group, "_WARNED", [])
        assert _run(tmp_path, "echo ok").stdout == "ok\n"
        with pytest.raises(subprocess.TimeoutExpired):
            _run(tmp_path, "echo $$ > fg.pid; exec sleep 300", timeout=1, grace=0.2)
        monkeypatch.undo()
        assert not _alive(_pid(tmp_path, "fg.pid"))

    def test_collecting_the_leader_never_waits_without_bound(
        self, started: List[int], monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Even where the leader cannot be ended (its group refuses the
        # signal), collecting it gives up after a bounded wait and says so.
        leader = subprocess.Popen(["sleep", "300"], start_new_session=True)
        started.append(leader.pid)
        monkeypatch.setattr(process_group, "_KILL_WAIT_SECONDS", 0.2)
        monkeypatch.setattr(process_group, "_DRAIN_SECONDS", 0.2)
        monkeypatch.setattr(process_group.os, "killpg", lambda _pgid, _sig: None)
        began = time.monotonic()
        try:
            with caplog.at_level(logging.WARNING, logger=process_group.__name__):
                process_group._collect(leader)
            assert time.monotonic() - began < 5
            assert "could not be collected" in caplog.text
        finally:
            monkeypatch.undo()
            leader.kill()
            leader.wait()

    @linux_only
    def test_waitid_refused_while_a_command_runs_never_hangs(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The probe passes (self is no child), then watching the leader is
        # refused: the command is ended and collected within bounds, and the
        # caller hears why.
        real_waitid = os.waitid
        own = os.getpid()

        def flaky(idtype: int, ident: int, options: int):
            # Refused once the command is under way (it has written its pid).
            if ident == own or not (tmp_path / "fg.pid").exists():
                return real_waitid(idtype, ident, options)
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group.os, "waitid", flaky)
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")
        began = time.monotonic()
        with pytest.raises(
            process_group.CleanupUnavailableError,
            match="was ended because waitid is refused here",
        ):
            # A process in a session of its own, one in another group of the
            # same session (timeout), then the shell itself.
            _run(
                tmp_path,
                "setsid sh -c 'echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
                "timeout 120 sh -c 'echo $$ > inner.pid; exec sleep 300' >/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="bg.pid") + "; " + _WAIT_FOR.format(name="inner.pid")
                + "; echo $$ > fg.pid; exec sleep 300",
            )
        monkeypatch.undo()

        assert time.monotonic() - began < 30
        assert not _alive(_pid(tmp_path, "fg.pid"))
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert not _alive(_pid(tmp_path, "inner.pid"))

    @linux_only
    def test_the_declared_install_says_why_it_could_not_start(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: None
    ) -> None:
        from guardkit.orchestrator.merge_environment import MergeEnvironment
        from guardkit.orchestrator.merge_executor import prepare_tree

        tree = _work_folder(tmp_path)
        done = prepare_tree(
            tree,
            MergeEnvironment(
                install_argv=("touch", "ran"), install_text="touch ran", install_timeout=30
            ),
            "the target",
        )

        assert done.env is None
        assert done.problem == (
            "the declared install (`touch ran`) could not start on the target: "
            f"The factory does not run project commands here: {self._MISSING}, "
            "so what a command leaves running could not all be stopped safely. "
            f"{self._ADVICE}"
        )
        assert not (tree / "ran").exists()

    def test_a_factory_launch_runs_no_project_command(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: None
    ) -> None:
        monkeypatch.setenv("GUARDKIT_FACTORY_LAUNCH", "build-x")
        for run in (
            lambda: _run(tmp_path, "touch ran"),
            lambda: run_in_own_group(
                "touch ran", shell=True, cwd=tmp_path, env=dict(_ENV), timeout=30
            ),
        ):
            with pytest.raises(process_group.CleanupUnavailableError) as caught:
                run()
            assert isinstance(caught.value, OSError)
            assert caught.value.errno == errno.ENOSYS
            assert caught.value.strerror == (
                f"The factory does not run project commands here: {self._MISSING}, "
                "so what a command leaves running could not all be stopped safely. "
                f"{self._ADVICE}"
            )
        assert not (tmp_path / "ran").exists()

    @pytest.mark.personal_run
    def test_a_persons_own_run_goes_on_with_one_warning(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        missing: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.delenv("GUARDKIT_FACTORY_LAUNCH", raising=False)
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            first = _run(tmp_path, "touch ran; echo ok")
            second = _run(tmp_path, "echo ok")

        assert first.stdout == second.stdout == "ok\n"
        assert (tmp_path / "ran").exists()
        warnings = [r for r in caplog.records if "may be left running" in r.getMessage()]
        assert len(warnings) == 1

    @pytest.mark.personal_run
    def test_an_empty_factory_signal_is_not_a_factory_launch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: None
    ) -> None:
        monkeypatch.setenv("GUARDKIT_FACTORY_LAUNCH", "")
        assert _run(tmp_path, "echo ok").stdout == "ok\n"

    @pytest.mark.parametrize("value", ["   ", "0", "false"])
    def test_any_other_factory_signal_is_a_factory_launch_and_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: None, value: str
    ) -> None:
        # Whitespace or "0" can never switch the refusal off.
        monkeypatch.setenv("GUARDKIT_FACTORY_LAUNCH", value)
        with pytest.raises(process_group.CleanupUnavailableError):
            _run(tmp_path, "touch ran")
        assert not (tmp_path / "ran").exists()


class TestTheRuleOnAFactoryLaunch:
    """Codex review, 20 October 2026: the probe proved less than the clean-up
    needs. On a factory launch the real clean-up passes an end-to-end
    self-test first, and any failure of it later, mid-run, ends that command
    with a plain error: never the reduced path, never a silent empty scan.
    A person's own run keeps the reduced clean-up, with a warning."""

    @staticmethod
    def _deny_proc_listing(monkeypatch: pytest.MonkeyPatch, when=lambda: True) -> None:
        real_listdir = os.listdir

        def listdir(path="."):
            if str(path) == "/proc" and when():
                raise PermissionError(errno.EACCES, "Permission denied")
            return real_listdir(path)

        monkeypatch.setattr(process_group.os, "listdir", listdir)

    @linux_only
    def test_a_denied_proc_listing_fails_the_self_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._deny_proc_listing(monkeypatch)
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        for run in (
            lambda: _run(tmp_path, "touch ran"),
            lambda: run_in_own_group(
                "touch ran", shell=True, cwd=tmp_path, env=dict(_ENV), timeout=30
            ),
        ):
            with pytest.raises(process_group.CleanupUnavailableError) as caught:
                run()
            assert caught.value.reason == "/proc could not be listed (Permission denied)"
            assert caught.value.strerror.startswith(
                "The factory does not run project commands here: /proc could not be listed"
            )
        assert not (tmp_path / "ran").exists()

    @linux_only
    def test_a_listing_denied_mid_run_ends_a_factory_command(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])
        self._deny_proc_listing(monkeypatch, when=lambda: (tmp_path / "fg.pid").exists())
        with pytest.raises(
            process_group.CleanupUnavailableError,
            match="was ended because /proc could not be listed",
        ):
            _run(tmp_path, "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; echo $$ > fg.pid")
        monkeypatch.undo()
        # The command's own group was still ended, by its pinned number.
        assert not _alive(_pid(tmp_path, "bg.pid"))

    @linux_only
    @pytest.mark.personal_run
    def test_a_listing_denied_on_a_persons_run_is_said(
        self,
        tmp_path: Path,
        started: List[int],
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setattr(process_group, "_CAPABILITY", [None])
        self._deny_proc_listing(monkeypatch)
        with caplog.at_level(logging.WARNING, logger=process_group.__name__):
            proc = _run(tmp_path, "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; echo ok")
        assert proc.stdout == "ok\n"
        assert "/proc could not be listed" in caplog.text

    @linux_only
    def test_a_cached_success_then_a_refused_waitid_ends_the_command(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Never the person's reduced path: the factory command is ended and
        # the caller hears why.
        def refused(*_args: object) -> None:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])
        monkeypatch.setattr(process_group.os, "waitid", refused)
        began = time.monotonic()
        with pytest.raises(
            process_group.CleanupUnavailableError, match="was ended because waitid is refused"
        ):
            _run(tmp_path, "echo $$ > fg.pid; exec sleep 300")
        monkeypatch.undo()
        assert time.monotonic() - began < 30
        if (tmp_path / "fg.pid").exists():
            assert not _alive(_pid(tmp_path, "fg.pid"))

    @linux_only
    def test_a_refused_pidfd_mid_run_ends_a_factory_command(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")

        def refused(_handle: int, _sig: int) -> None:
            raise PermissionError(errno.EPERM, "Operation not permitted")

        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])
        monkeypatch.setattr(process_group.signal, "pidfd_send_signal", refused)
        with pytest.raises(
            process_group.CleanupUnavailableError,
            match="was ended because pidfd_send_signal is refused",
        ):
            _run(
                tmp_path,
                "setsid sh -c 'echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="bg.pid"),
            )
        monkeypatch.undo()


@linux_only
class TestTheSelfTestSeesForItself:
    """Codex review, 20 October 2026: the self-test must not rely on the
    marker scan it is testing, a denied environment read is not an absent
    marker, and the self-test's own emergency kill checks ownership after
    pinning."""

    @staticmethod
    def _deny_environ(monkeypatch: pytest.MonkeyPatch, which) -> None:
        real_open = open

        def guarded(path, *args, **kwargs):
            text = str(path)
            if text.startswith("/proc/") and text.endswith("/environ"):
                pid = int(text.split("/")[2])
                if which(pid):
                    raise PermissionError(errno.EACCES, "Permission denied")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(process_group, "open", guarded, raising=False)

    def test_a_denied_environment_read_fails_the_self_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        own = os.getpid()
        self._deny_environ(monkeypatch, lambda pid: pid != own)
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [])
        with pytest.raises(process_group.CleanupUnavailableError) as caught:
            _run(tmp_path, "touch ran")
        assert caught.value.reason == (
            "the clean-up self-test's process environment could not be read "
            "(Permission denied)"
        )
        assert not (tmp_path / "ran").exists()

    def test_a_denied_environment_read_mid_run_ends_a_factory_command(
        self, tmp_path: Path, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if shutil.which("setsid", path=_ENV["PATH"]) is None:
            pytest.skip("no setsid program")

        def escapee(pid: int) -> bool:
            file = tmp_path / "bg.pid"
            return file.exists() and file.read_text().strip() == str(pid)

        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])
        self._deny_environ(monkeypatch, escapee)
        with pytest.raises(
            process_group.CleanupUnavailableError,
            match="was ended because a process's environment in /proc could not be read",
        ):
            _run(
                tmp_path,
                "setsid sh -c 'echo $$ > bg.pid; exec sleep 300' >/dev/null 2>&1 & "
                + _WAIT_FOR.format(name="bg.pid"),
            )

    def test_the_self_test_checks_its_own_process_not_only_the_scan(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A scan that misses marked processes would leave the self-test's
        # process running; the pinned pidfd shows it, so the test fails.
        monkeypatch.setattr(process_group, "_carries_marker", lambda _pid, _entry: False)
        assert process_group._self_test() == (
            "the clean-up self-test's left-behind process was still running after the stop"
        )

    def test_the_emergency_kill_checks_ownership_after_pinning(
        self, started: List[int], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A number listed as the self-test's but handed on before it was
        # pinned: the process it names now does not carry the marker, so it
        # is not signalled.
        stranger = subprocess.Popen(["sleep", "300"], start_new_session=True)
        started.append(stranger.pid)
        monkeypatch.setattr(
            process_group, "_pidfd_send_signal",
            lambda handle, sig: pytest.fail("signalled a process that is not the self-test's"),
        )
        try:
            process_group._end_self_test_leftovers(
                {stranger.pid}, f"\0{COMMAND_MARKER_NAME}={'f' * 32}\0".encode(), None
            )
            time.sleep(0.2)
            assert _alive(stranger.pid)
        finally:
            monkeypatch.undo()
            stranger.kill()
            stranger.wait()

    def test_a_hidden_runaway_is_warned_about_not_killed(
        self,
        tmp_path: Path,
        started: List[int],
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # A child that deliberately conceals itself (setsid, keep the marker,
        # make itself non-dumpable, close its output, outlive the command):
        # it cannot be inspected, so it is not killed, but it is named in a
        # plain warning. The command text is never in that warning (it may
        # carry a secret, and the warning is published).
        monkeypatch.setattr(process_group, "_SELF_TEST_PASSED", [True])
        caplog.set_level(logging.WARNING, logger=process_group.__name__)
        child = textwrap.dedent(
            """
            import ctypes, os, time
            pid = os.fork()
            if pid == 0:
                os.setsid()
                ctypes.CDLL(None).prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE = 4
                null = os.open(os.devnull, os.O_RDWR)
                for fd in (0, 1, 2):
                    os.dup2(null, fd)
                with open(%r, "w") as fh:
                    fh.write(str(os.getpid()))
                time.sleep(300)
                os._exit(0)
            while not os.path.exists(%r):
                time.sleep(0.01)
            """
        ) % (str(tmp_path / "hidden.pid"), str(tmp_path / "hidden.pid"))
        proc = run_project_command(
            [sys.executable, "-c", child, "a-secret-token"],
            cwd=str(tmp_path), env=dict(_ENV), capture_output=True, text=True, timeout=30,
        )
        hidden = int((tmp_path / "hidden.pid").read_text())
        started.append(hidden)

        assert proc.returncode == 0
        assert _alive(hidden)  # not killed
        warnings = [
            r.getMessage() for r in caplog.records if "could not be inspected" in r.getMessage()
        ]
        assert any(f"pid {hidden} (" in w for w in warnings), warnings
        # Logged, not folded into the command's own output, and the command
        # text (which could carry a secret) is never named in the warning.
        assert "[guardkit]" not in (proc.stderr or "")
        assert all("a-secret-token" not in w for w in warnings)

    def test_processes_refused_by_design_are_told_apart(self) -> None:
        # This process: could be a command's. PID 1 (another user's): not.
        assert process_group._could_be_this_commands(os.getpid())
        assert not process_group._could_be_this_commands(1)

    @pytest.mark.personal_run
    def test_another_users_process_is_not_this_commands(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Its environment cannot be read by design; that is no failure.
        monkeypatch.setenv("GUARDKIT_FACTORY_LAUNCH", "1")
        self._deny_environ(monkeypatch, lambda pid: True)
        monkeypatch.setattr(process_group, "_could_be_this_commands", lambda pid: False)
        assert process_group._carries_marker(os.getpid(), b"\0X=y\0") is False


@pytest.mark.personal_run
class TestWithoutWaitid:
    """macOS before Python 3.13 has no ``os.waitid``: commands still run (with
    ``communicate()``, as before), and a timeout still ends the group."""

    @pytest.fixture(autouse=True)
    def _no_waitid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delattr(os, "waitid")

    @pytest.mark.parametrize(
        ("args", "kwargs"),
        [
            ("echo hi; echo err >&2; exit 3", {"shell": True, "capture_output": True, "text": True}),
            (["cat"], {"input": "piped in\n", "capture_output": True, "text": True}),
            ("exit 4", {"shell": True}),
        ],
    )
    def test_the_same_result_as_subprocess_run(self, tmp_path: Path, args, kwargs) -> None:
        ours = run_project_command(args, cwd=str(tmp_path), env=dict(_ENV), timeout=30, **kwargs)
        theirs = subprocess.run(args, cwd=str(tmp_path), env=dict(_ENV), timeout=30, **kwargs)
        assert (ours.returncode, ours.stdout, ours.stderr) == (
            theirs.returncode, theirs.stdout, theirs.stderr,
        )

    def test_run_in_own_group_runs(self, tmp_path: Path) -> None:
        run = run_in_own_group("echo hi", shell=True, cwd=tmp_path, env=dict(_ENV), timeout=30)
        assert (run.returncode, run.stdout, run.timed_out) == (0, "hi\n", False)

    @linux_only
    def test_a_timeout_ends_the_group(self, tmp_path: Path, started: List[int]) -> None:
        with pytest.raises(subprocess.TimeoutExpired):
            _run(
                tmp_path,
                "sleep 300 >/dev/null 2>&1 & echo $! > bg.pid; echo $$ > fg.pid; exec sleep 300",
                timeout=1,
                grace=0.2,
            )
        assert not _alive(_pid(tmp_path, "bg.pid"))
        assert not _alive(_pid(tmp_path, "fg.pid"))


# ---------------------------------------------------------------------------
# Still subprocess.run's shape
# ---------------------------------------------------------------------------


class TestStillShapedLikeSubprocessRun:
    @pytest.mark.parametrize(
        ("args", "kwargs"),
        [
            ("echo hi; echo err >&2; exit 3", {"shell": True, "capture_output": True, "text": True}),
            ("printf 'a\\r\\nb\\rc'", {"shell": True, "capture_output": True, "text": True}),
            ("printf 'a\\r\\nb'", {"shell": True, "capture_output": True}),
            (["printf", "%s|", "one", "two words"], {"capture_output": True, "text": True}),
            (["cat"], {"input": "piped in\n", "capture_output": True, "text": True}),
            (["cat"], {"input": b"bytes in", "capture_output": True}),
            ("printf '[%s]' \"$0\" \"$1\"", {"shell": True, "capture_output": True, "text": True}),
            (
                ["printf '[%s]' \"$0\" \"$1\"", "zero", "one"],
                {"shell": True, "capture_output": True, "text": True},
            ),
            ("exit 4", {"shell": True}),
            (["true"], {"stdout": subprocess.DEVNULL}),
        ],
    )
    def test_the_same_result(self, tmp_path: Path, args, kwargs) -> None:
        ours = run_project_command(args, cwd=str(tmp_path), env=dict(_ENV), timeout=30, **kwargs)
        theirs = subprocess.run(args, cwd=str(tmp_path), env=dict(_ENV), timeout=30, **kwargs)

        assert (ours.args, ours.returncode, ours.stdout, ours.stderr) == (
            theirs.args, theirs.returncode, theirs.stdout, theirs.stderr,
        )

    def test_check_raises_as_subprocess_run_does(self, tmp_path: Path) -> None:
        with pytest.raises(subprocess.CalledProcessError) as caught:
            run_project_command(
                "echo out; exit 5", shell=True, cwd=str(tmp_path), env=dict(_ENV),
                capture_output=True, text=True, check=True, timeout=30,
            )
        assert (caught.value.returncode, caught.value.stdout) == (5, "out\n")

    def test_a_program_that_does_not_exist_cannot_start(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_project_command(
                ["no-such-program-anywhere"], cwd=str(tmp_path), env=dict(_ENV), timeout=30,
            )
        with pytest.raises(FileNotFoundError):
            run_in_own_group(
                ["no-such-program-anywhere"], cwd=tmp_path, env=dict(_ENV), timeout=30,
            )

    def test_each_command_has_its_own_marker_and_the_env_given_is_unchanged(
        self, tmp_path: Path
    ) -> None:
        env = dict(_ENV)
        first = _run(tmp_path, f'printf "%s" "${COMMAND_MARKER_NAME}"', env=env)
        second = _run(tmp_path, f'printf "%s" "${COMMAND_MARKER_NAME}"', env=env)
        assert len(first.stdout) == 32 and len(second.stdout) == 32
        assert first.stdout != second.stdout
        assert env == _ENV


# ---------------------------------------------------------------------------
# CI=true unless the project says otherwise
# ---------------------------------------------------------------------------


def _work_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "repo"
    folder.mkdir()
    subprocess.run(["git", "init", "-q", str(folder)], check=True, env=dict(_ENV, HOME=str(tmp_path)))
    return folder


class TestCi:
    def test_a_project_command_has_ci_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CI", "0")  # not copied: the project does not declare it
        env = pce.project_command_environment(_work_folder(tmp_path), None)
        assert env["CI"] == "true"

    def test_a_project_that_declares_ci_keeps_its_own_value(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CI", "0")
        env = pce.project_command_environment(
            _work_folder(tmp_path), LaunchDeclaration(settings=("CI",), scratch=())
        )
        assert env["CI"] == "0"

    def test_a_declared_ci_not_set_here_falls_back_to_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CI", raising=False)
        env = pce.project_command_environment(
            _work_folder(tmp_path), LaunchDeclaration(settings=("CI",), scratch=())
        )
        assert env["CI"] == "true"

    def test_a_value_the_project_wrote_wins(self, tmp_path: Path) -> None:
        env = pce.project_command_environment(
            _work_folder(tmp_path), None, overlay={"CI": "false"}
        )
        assert env["CI"] == "false"
