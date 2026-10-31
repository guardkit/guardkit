"""Repair 7, connected: the Coach's independent check records what it ran on.

Real commands and real git; only Docker is faked (and the suite-wide fence
keeps any real daemon out of reach). The isolated-copy path and its records
were removed with the copy itself (31 October 2026: unreachable once every
task ran alone).

* WORKTREE PATH: a write during the command is "source changed during the
  command".
* A declared inventory is saved; an undeclared one says "not declared".
* Recording never changes the outcome, even when capture itself breaks.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator import run_evidence
from guardkit.orchestrator.quality_gates.coach_validator import (
    EVIDENCE_SDK,
    EVIDENCE_WORKTREE,
    CoachValidator,
)
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block


def _git(cwd: Path, *args: str, env=None) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True, env=env
    ).stdout


@pytest.fixture
def worktree(tmp_path) -> Path:
    """A build clone with a feature worktree, as the live runner lays it out."""
    clone = tmp_path / "build-clone"
    clone.mkdir()
    _git(clone, "init", "-q", "-b", "main")
    _git(clone, "config", "user.email", "t@example.invalid")
    _git(clone, "config", "user.name", "t")
    (clone / "README").write_text("clone\n")
    _git(clone, "add", "README")
    _git(clone, "commit", "-q", "-m", "init")
    wt = clone / ".guardkit" / "worktrees" / "FEAT-X"
    wt.parent.mkdir(parents=True)
    _git(clone, "worktree", "add", "-q", "-b", "feat", str(wt))
    (wt / "src.txt").write_text("committed source\n")
    _git(wt, "add", "src.txt")
    _git(wt, "commit", "-q", "-m", "source")
    # Dirty bytes the build left uncommitted: they are part of what ran.
    (wt / "untracked.txt").write_text("copied untracked bytes\n")
    return wt


def _temp_index_tree(wt: Path, scratch: Path) -> str:
    env = dict(os.environ, GIT_INDEX_FILE=str(scratch / "index"))
    _git(wt, "add", "-A", env=env)
    return _git(wt, "write-tree", env=env).strip()


def _validator(wt: Path, cmd: str, *, wave_size: int = 1, toolchain=None) -> CoachValidator:
    v = CoachValidator(
        worktree_path=str(wt),
        task_id="TASK-R7-001",
        test_command=cmd,
        wave_size=wave_size,
        toolchain=toolchain,
    )
    v._coach_test_execution = "subprocess"
    return v


def test_a_write_during_a_worktree_run_is_recorded(worktree):
    result = _validator(worktree, "printf more >> untracked.txt", wave_size=1).run_independent_tests()

    record = result.run_evidence["runs"][0]
    assert record["command_kind"] == EVIDENCE_WORKTREE
    assert record["source"]["verdict"] == run_evidence.SOURCE_CHANGED
    assert record["source"]["changed_paths"]["modified"] == ["untracked.txt"]


def test_a_declared_inventory_is_saved_on_the_record(worktree):
    toolchain = parse_toolchain_block(
        {"test": "true", "environment_inventory": "printf 'tool 1.2.3\\n'"}
    )
    result = _validator(worktree, "true", wave_size=1, toolchain=toolchain).run_independent_tests()

    inventory = result.run_evidence["runs"][0]["environment_inventory"]
    assert inventory["status"] == "recorded"
    assert inventory["output"] == "tool 1.2.3\n"
    assert inventory["output_sha256"] == hashlib.sha256(b"tool 1.2.3\n").hexdigest()


@pytest.mark.parametrize("cmd,passed", [("true", True), ("echo 1 failed; exit 1", False)])
def test_a_capture_failure_never_changes_the_outcome(worktree, monkeypatch, cmd, passed):
    baseline = _validator(worktree, cmd).run_independent_tests()

    def _broken(*_a, **_k):
        raise RuntimeError("manifest exploded")

    monkeypatch.setattr(run_evidence, "source_manifest", _broken)
    monkeypatch.setattr(
        run_evidence, "docker_events_between", _broken
    )
    broken = _validator(worktree, cmd).run_independent_tests()

    assert broken.tests_passed is baseline.tests_passed is passed
    assert broken.signal_absent == baseline.signal_absent
    assert broken.test_output_summary == baseline.test_output_summary
    assert broken.run_evidence["runs"][0]["capture_errors"]


def test_the_record_stays_out_of_the_coach_prompt_but_in_the_bundle(worktree):
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    result = _validator(worktree, "true", wave_size=1).run_independent_tests()
    bundle = CoachEvidenceBundle(
        independent_tests=result,
    )

    text = AgentInvoker._render_evidence_bundle_section(AgentInvoker.__new__(AgentInvoker), bundle)
    payload = json.loads(text.split("<evidence_bundle>")[1].split("</evidence_bundle>")[0])
    assert "run_evidence" not in payload["independent_tests"]
    assert payload["independent_tests"]["tests_passed"] is True
    # The bundle itself (what coach_turn_N.json is written from) keeps it.
    assert bundle.to_dict()["independent_tests"]["run_evidence"]["runs"]


def test_a_python_run_keeps_the_verdict_and_lists_what_it_made(worktree):
    import sys

    (worktree / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    cmd = f'"{sys.executable}" -m pytest -q test_ok.py'
    result = _validator(worktree, cmd).run_independent_tests()

    assert result.tests_passed, result.test_output_summary
    source = result.run_evidence["runs"][0]["source"]
    assert source["verdict"].startswith(run_evidence.SOURCE_UNCHANGED + "; ")
    assert "files created during the command" in source["verdict"]
    created = source["files_created_during_the_command"]
    assert created["total"] > 0
    assert any("__pycache__" in p or ".pytest_cache" in p for p in created["paths"])


@pytest.mark.parametrize(
    "route", ["the declared command in the worktree", "through the SDK"]
)
def test_every_route_returns_the_object_the_check_made_with_its_record(worktree, monkeypatch, route):
    """The pytest-argv routes and the SDK route hand back the very result the
    check produced (not a copy), with the run record attached; a failing
    pytest run keeps its exit status beside the record."""
    import sys
    from unittest.mock import AsyncMock

    from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult

    (worktree / "test_red.py").write_text("def test_red():\n    assert 1 == 2\n")
    made = []

    if route == "through the SDK":
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        v = CoachValidator(
            str(worktree), task_id="TASK-R7-001", test_command="pytest test_red.py",
            coach_test_execution="sdk",
        )
        sentinel = IndependentTestResult(
            tests_passed=True, test_command="pytest test_red.py",
            test_output_summary="sdk ran", duration_seconds=1.0,
        )
        made.append(sentinel)
        monkeypatch.setattr(v, "_run_tests_via_sdk", AsyncMock(return_value=sentinel))
    else:
        real_from_run = IndependentTestResult.from_run.__func__

        def _recording_from_run(cls, **kwargs):
            obj = real_from_run(cls, **kwargs)
            made.append(obj)
            return obj

        monkeypatch.setattr(
            IndependentTestResult, "from_run", classmethod(_recording_from_run)
        )
        v = _validator(worktree, f'"{sys.executable}" -m pytest -q -p no:cacheprovider test_red.py')

    result = v.run_independent_tests()

    assert made and result is made[-1]
    runs = result.run_evidence["runs"]
    assert len(runs) == 1
    expected_kind = {
        "the declared command in the worktree": EVIDENCE_WORKTREE,
        "through the SDK": EVIDENCE_SDK,
    }[route]
    assert runs[0]["command_kind"] == expected_kind
    if route != "through the SDK":
        assert result.tests_passed is False
        assert result.exit_code == 1
        assert result.failure_receipt()["exit_code"] == 1
        assert runs[0]["command"] == v.test_command  # run exactly as declared


# ---------------------------------------------------------------------------
# Behavioural-oracle routes (implementation review round 1, R1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command,passed,timed_out",
    [("true", True, False), ("exit 3", False, False), ("sleep 30", False, True)],
)
def test_a_declared_oracle_command_carries_its_run_record(worktree, monkeypatch, command, passed, timed_out):
    monkeypatch.setenv("GUARDKIT_ORACLE_TIMEOUT", "1")
    v = CoachValidator(worktree_path=worktree, task_id="TASK-R7-001")
    task = {"id": "TASK-R7-001", "task_type": "feature", "behavioural_oracle": {"command": command}}

    result = v._produce_behavioural_oracle(task=task)

    assert result["status"] == "ran"
    assert result["passed"] is passed and result["timed_out"] is timed_out
    record = result["run_evidence"]
    assert record["command_kind"] == "behavioural oracle"
    assert record["execution_root"] == str(worktree)
    assert record["source"]["verdict"] == run_evidence.SOURCE_UNCHANGED
    json.dumps(result)
    # The oracle's record goes on the oracle's receipt, not the suite's runs.
    assert not v._run_evidence_log


def test_the_oracle_record_stays_out_of_the_prompt(worktree):
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    v = CoachValidator(worktree_path=worktree, task_id="TASK-R7-001")
    oracle = v._produce_behavioural_oracle(
        task={"behavioural_oracle": {"command": "true"}}
    )
    bundle = CoachEvidenceBundle(
        behavioural_oracle=oracle,
    )
    text = AgentInvoker._render_evidence_bundle_section(AgentInvoker.__new__(AgentInvoker), bundle)
    payload = json.loads(text.split("<evidence_bundle>")[1].split("</evidence_bundle>")[0])
    assert "run_evidence" not in payload["behavioural_oracle"]
    assert bundle.to_dict()["behavioural_oracle"]["run_evidence"]


def test_an_inventory_that_floods_its_output_does_not_change_the_verdict(worktree):
    toolchain = parse_toolchain_block(
        {"test": "true", "environment_inventory": "head -c 20000000 /dev/zero"}
    )
    for cmd, passed in (("true", True), ("exit 1", False)):
        result = _validator(worktree, cmd, wave_size=1, toolchain=toolchain).run_independent_tests()
        assert result.tests_passed is passed
        inventory = result.run_evidence["runs"][0]["environment_inventory"]
        assert inventory["output_bytes"] == 20_000_000
        assert inventory["output_truncated"] is True


def test_a_stalled_filesystem_leaves_the_check_and_its_result_unchanged(worktree, monkeypatch):
    """Round 2, R3: a read that never returns cannot hold the Coach's check,
    and the result it returns is the one the check made."""
    import threading
    import time
    from guardkit.orchestrator.quality_gates.coach_validator import IndependentTestResult

    (worktree / "stall.bin").write_bytes(b"stuck")
    release = threading.Event()
    real_read = os.read

    def _read(fd, n):
        try:
            name = os.readlink(f"/proc/self/fd/{fd}")
        except OSError:
            name = ""
        if name.endswith("stall.bin"):
            release.wait()
        return real_read(fd, n)

    monkeypatch.setattr(run_evidence.os, "read", _read)
    monkeypatch.setattr(
        run_evidence, "DEFAULT_LIMITS",
        run_evidence.EvidenceLimits(max_seconds=0.5, git_timeout=0.5),
    )
    made = []
    real_from_run = IndependentTestResult.from_run.__func__

    def _recording(cls, **kwargs):
        made.append(real_from_run(cls, **kwargs))
        return made[-1]

    monkeypatch.setattr(IndependentTestResult, "from_run", classmethod(_recording))
    try:
        for cmd, passed in (("true", True), ("exit 1", False)):
            started = time.monotonic()
            result = _validator(worktree, cmd, wave_size=1).run_independent_tests()
            assert time.monotonic() - started < 10
            assert result is made[-1] and result.tests_passed is passed
            source = result.run_evidence["runs"][0]["source"]
            assert source["before"]["status"] == run_evidence.NOT_RECORDED_TIMED_OUT
            assert source["verdict"].startswith("not compared")
    finally:
        release.set()
        _settle_evidence_threads()


# ---------------------------------------------------------------------------
# Implementation review round 4, R10: whole capture phases are bounded
# ---------------------------------------------------------------------------


@pytest.fixture
def quick_phases(monkeypatch):
    """Small inner limits so a phase bound is a few seconds, and a release
    for anything a test leaves blocked."""
    import threading

    monkeypatch.setattr(run_evidence, "_DRAIN_SECONDS", 0.2)
    monkeypatch.setattr(
        run_evidence, "DEFAULT_LIMITS",
        run_evidence.EvidenceLimits(max_seconds=0.5, git_timeout=0.5, docker_timeout=0.5),
    )
    release = threading.Event()
    yield release
    release.set()


def _timed_check(worktree, cmd, **kw):
    import time

    started = time.monotonic()
    result = _validator(worktree, cmd, wave_size=1, **kw).run_independent_tests()
    return result, time.monotonic() - started


def _settle_evidence_threads(timeout: float = 20.0) -> None:
    import threading
    import time

    give_up_at = time.monotonic() + timeout
    for thread in threading.enumerate():
        if thread.name.startswith("guardkit-evidence"):
            thread.join(timeout=max(0.0, give_up_at - time.monotonic()))
            assert not thread.is_alive(), f"{thread.name} did not settle"


def _forbid_real_docker(monkeypatch) -> list:
    """Fail on any real ``docker`` process, from any thread, at any time
    while the patch holds; returns the list of attempts."""
    attempts: list = []
    real_popen = run_evidence.subprocess.Popen

    class _Guarded(real_popen):  # type: ignore[misc, valid-type]
        def __init__(self, args, *a, **k):
            argv = args if isinstance(args, (list, tuple)) else str(args).split()
            if argv and str(argv[0]).endswith("docker"):
                attempts.append(list(argv))
                raise AssertionError("a real docker process was started")
            super().__init__(args, *a, **k)

    monkeypatch.setattr(run_evidence.subprocess, "Popen", _Guarded)
    return attempts


def test_a_blocked_docker_discovery_is_left_behind_at_the_phase_bound(worktree, monkeypatch, quick_phases):
    attempts = _forbid_real_docker(monkeypatch)
    fake_calls: list = []

    def _blocked_which(_name):
        quick_phases.wait()
        return "/usr/bin/docker"

    def _fake_runner(argv, **kwargs):
        fake_calls.append(list(argv))
        return run_evidence.HelperRun(0, b"", b"")

    monkeypatch.setattr(
        run_evidence, "default_docker_probe",
        lambda: run_evidence.DockerProbe(runner=_fake_runner, which=_blocked_which),
    )
    for cmd, passed in (("true", True), ("exit 1", False)):
        result, elapsed = _timed_check(worktree, cmd)
        assert result.tests_passed is passed
        record = result.run_evidence["runs"][0]
        assert elapsed < 12, f"took {elapsed:.1f}s"
        assert record["container_events"]["status"] == run_evidence.NOT_RECORDED_TIMED_OUT
        assert record["source"]["after"]["status"] == "recorded"
        assert any("finish" in e for e in record["capture_errors"])

    # Release the blocked discovery: the abandoned phases run on, reach the
    # injected runner, and never start a real docker process.
    quick_phases.set()
    _settle_evidence_threads()
    assert attempts == []
    assert fake_calls and all(c[:2] == ["docker", "events"] for c in fake_calls)


def test_a_blocked_helper_startup_is_left_behind_at_the_phase_bound(worktree, monkeypatch, quick_phases):
    real_popen = run_evidence.subprocess.Popen

    class _BlockingPopen(real_popen):  # type: ignore[misc, valid-type]
        def __init__(self, args, *a, **k):
            if "inventory-marker" in str(args):
                quick_phases.wait()
            super().__init__(args, *a, **k)

    monkeypatch.setattr(run_evidence.subprocess, "Popen", _BlockingPopen)
    toolchain = parse_toolchain_block(
        {"test": "true", "environment_inventory": "echo inventory-marker",
         "environment_inventory_timeout": 1}
    )
    attempts = _forbid_real_docker(monkeypatch)
    for cmd, passed in (("true", True), ("exit 1", False)):
        result, elapsed = _timed_check(worktree, cmd, toolchain=toolchain)
        assert result.tests_passed is passed
        record = result.run_evidence["runs"][0]
        assert elapsed < 12, f"took {elapsed:.1f}s"
        assert record["environment_inventory"]["status"] == run_evidence.NOT_RECORDED_TIMED_OUT
        assert any("begin" in e for e in record["capture_errors"])
    quick_phases.set()
    _settle_evidence_threads()
    assert attempts == []
