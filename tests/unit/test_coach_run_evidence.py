"""Repair 7, connected: the Coach's independent check records what it ran on.

Real commands, real git, real isolated copies; only Docker is faked (and the
suite-wide fence keeps any real daemon out of reach).

* PARALLEL PATH: the check runs in an isolated copy that has no ``.git``. The
  command itself changes the ORIGINAL worktree after the copy was made. The
  record must still name the copy as the execution root, identify the copied
  bytes (not the changed original), and carry the originating worktree's
  identity from the moment of copying.
* FALLBACK: when the isolated copy cannot start the check and it falls back to
  the worktree, both runs are recorded, in order.
* WORKTREE PATH: a write during the command is "source changed during the
  command".
* A declared inventory is saved; an undeclared one says "not declared".
* Recording never changes the outcome, even when capture itself breaks.
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator import run_evidence
from guardkit.orchestrator.quality_gates.coach_validator import (
    EVIDENCE_ISOLATED,
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


def _validator(wt: Path, cmd: str, *, wave_size: int = 2, toolchain=None) -> CoachValidator:
    v = CoachValidator(
        worktree_path=str(wt),
        task_id="TASK-R7-001",
        test_command=cmd,
        wave_size=wave_size,
        toolchain=toolchain,
    )
    v._coach_test_execution = "subprocess"
    return v


def test_parallel_path_records_the_copy_and_the_origin_at_copy_time(worktree, tmp_path):
    expected_origin_tree = _temp_index_tree(worktree, tmp_path)
    head = _git(worktree, "rev-parse", "HEAD").strip()
    q = shlex.quote
    # The command runs in the copy, and changes the ORIGINAL worktree after
    # the copy was made — exactly the hazard the copy exists to avoid.
    cmd = (
        f"printf 'changed after copying\\n' > {q(str(worktree / 'untracked.txt'))}; "
        f"printf 'new\\n' > {q(str(worktree / 'late.txt'))}; "
        "test -f src.txt"
    )

    result = _validator(worktree, cmd).run_independent_tests(turn=4)

    assert result.tests_passed, result.test_output_summary
    runs = result.run_evidence["runs"]
    assert len(runs) == 1
    record = runs[0]
    assert record["command_kind"] == EVIDENCE_ISOLATED
    root = Path(record["execution_root"])
    assert root != worktree and root.name.startswith("guardkit-coach-iso-")
    assert "without Git metadata" in record["execution_root_is"]

    # The copy is identified by the bytes it held, not the changed original.
    source = record["source"]
    assert source["verdict"] == run_evidence.SOURCE_UNCHANGED
    assert "plain directory" in source["before"]["file_set"]
    entries = {e[0]: e for e in source["manifest"]["entries"]}
    assert entries["untracked.txt"][2] == hashlib.sha256(b"copied untracked bytes\n").hexdigest()
    assert "late.txt" not in entries
    assert ".git" not in entries

    # The origin as it was when copied, not as it is now.
    origin = record["originating_worktree"]
    assert origin["status"] == "recorded"
    assert origin["worktree"] == str(worktree)
    assert origin["head"] == head
    assert origin["tree_with_untracked"] == expected_origin_tree
    now_scratch = tmp_path / "now"
    now_scratch.mkdir()
    assert _temp_index_tree(worktree, now_scratch) != expected_origin_tree

    assert record["observer"]["task"] == "TASK-R7-001"
    assert record["observer"]["turn"] == 4
    assert record["environment_inventory"] == {"status": run_evidence.NOT_DECLARED}
    assert record["container_events"]["status"].startswith("not recorded: switched off")

    # The Coach's turn receipt carries it, as plain JSON.
    v = _validator(worktree, cmd)
    v_result = v.run_independent_tests()
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidationResult

    payload = CoachValidationResult(
        task_id="TASK-R7-001", turn=1, decision="feedback", independent_tests=v_result
    ).to_dict()
    json.dumps(payload)
    assert payload["validation_results"]["independent_tests"]["run_evidence"]["runs"]


def test_fallback_to_the_worktree_records_both_runs_in_order(worktree):
    # In the copy (no .git) the command cannot run: exit 127, the shell's
    # "could not execute" — so the check falls back to the worktree.
    cmd = "if [ -e .git ]; then echo ok; else echo 'probe: command not found' >&2; exit 127; fi"
    result = _validator(worktree, cmd).run_independent_tests()

    assert result.tests_passed, result.test_output_summary
    assert result.isolation_fallback_reason
    kinds = [r["command_kind"] for r in result.run_evidence["runs"]]
    assert kinds == [EVIDENCE_ISOLATED, EVIDENCE_WORKTREE]
    worktree_run = result.run_evidence["runs"][1]
    assert worktree_run["execution_root"] == str(worktree)
    assert worktree_run["originating_worktree"] is None
    assert "Git worktree" in worktree_run["source"]["before"]["file_set"]
    assert worktree_run["source"]["before"]["head"] == _git(worktree, "rev-parse", "HEAD").strip()


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


@pytest.mark.parametrize("wave_size", [1, 2])
@pytest.mark.parametrize("cmd,passed", [("true", True), ("echo 1 failed; exit 1", False)])
def test_a_capture_failure_never_changes_the_outcome(worktree, monkeypatch, wave_size, cmd, passed):
    baseline = _validator(worktree, cmd, wave_size=wave_size).run_independent_tests()

    def _broken(*_a, **_k):
        raise RuntimeError("manifest exploded")

    monkeypatch.setattr(run_evidence, "source_manifest", _broken)
    # The name the Coach imported is the one it calls.
    monkeypatch.setattr(
        "guardkit.orchestrator.quality_gates.coach_validator.originating_worktree_identity",
        _broken,
    )
    monkeypatch.setattr(
        run_evidence, "docker_events_between", _broken
    )
    broken = _validator(worktree, cmd, wave_size=wave_size).run_independent_tests()

    assert broken.tests_passed is baseline.tests_passed is passed
    assert broken.signal_absent == baseline.signal_absent
    assert broken.test_output_summary == baseline.test_output_summary
    assert broken.run_evidence["runs"][0]["capture_errors"]
    if wave_size > 1:
        origin = broken.run_evidence["runs"][0]["originating_worktree"]
        assert origin["status"].startswith("not recorded: capture error")
        assert origin["stable_during_copy"].startswith("not known")


def test_the_record_stays_out_of_the_coach_prompt_but_in_the_bundle(worktree):
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    result = _validator(worktree, "true", wave_size=1).run_independent_tests()
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0),
        independent_tests=result,
    )

    text = AgentInvoker._render_evidence_bundle_section(AgentInvoker.__new__(AgentInvoker), bundle)
    payload = json.loads(text.split("<evidence_bundle>")[1].split("</evidence_bundle>")[0])
    assert "run_evidence" not in payload["independent_tests"]
    assert payload["independent_tests"]["tests_passed"] is True
    # The bundle itself (what coach_turn_N.json is written from) keeps it.
    assert bundle.to_dict()["independent_tests"]["run_evidence"]["runs"]


def test_python_run_inside_the_copy_keeps_the_verdict_and_lists_what_it_made(worktree):
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


def test_a_worktree_change_while_copying_is_recorded(worktree, monkeypatch):
    from guardkit.orchestrator import run_evidence as rem

    real = CoachValidator._originating_identity_for_copy
    calls = {"n": 0}

    def _identity(self):
        calls["n"] += 1
        if calls["n"] == 2:  # just after the copy: somebody wrote meanwhile
            (worktree / "written-while-copying.txt").write_text("x\n")
        return real(self)

    monkeypatch.setattr(CoachValidator, "_originating_identity_for_copy", _identity)
    result = _validator(worktree, "true").run_independent_tests()
    origin = result.run_evidence["runs"][0]["originating_worktree"]
    assert origin["stable_during_copy"] == rem.COPY_UNSTABLE

    calls["n"] = 10  # no write this time
    result = _validator(worktree, "true").run_independent_tests()
    origin = result.run_evidence["runs"][0]["originating_worktree"]
    assert origin["stable_during_copy"] == rem.COPY_STABLE
    assert origin["after_copy"]["tree_with_untracked"] == origin["tree_with_untracked"]


@pytest.mark.parametrize(
    "route", ["pytest in the isolated copy", "pytest in the worktree", "through the SDK"]
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
        wave = 2 if "isolated" in route else 1
        v = _validator(worktree, "pytest -q -p no:cacheprovider test_red.py", wave_size=wave)
        monkeypatch.setattr(v, "_pytest_interpreter", lambda: sys.executable)

    result = v.run_independent_tests()

    assert made and result is made[-1]
    runs = result.run_evidence["runs"]
    assert len(runs) == 1
    expected_kind = {
        "pytest in the isolated copy": EVIDENCE_ISOLATED,
        "pytest in the worktree": EVIDENCE_WORKTREE,
        "through the SDK": EVIDENCE_SDK,
    }[route]
    assert runs[0]["command_kind"] == expected_kind
    if route != "through the SDK":
        assert result.tests_passed is False
        assert result.exit_code == 1
        assert result.failure_receipt()["exit_code"] == 1
        assert isinstance(runs[0]["command"], list)  # the pytest argv itself


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

    result = v._produce_behavioural_oracle(authored_files=[], task=task)

    assert result["status"] == "ran"
    assert result["passed"] is passed and result["timed_out"] is timed_out
    record = result["run_evidence"]
    assert record["command_kind"] == "behavioural oracle"
    assert record["execution_root"] == str(worktree)
    assert record["source"]["verdict"] == run_evidence.SOURCE_UNCHANGED
    json.dumps(result)
    # The oracle's record goes on the oracle's receipt, not the suite's runs.
    assert not v._run_evidence_log


def test_a_python_oracle_carries_its_run_record(worktree):
    import sys
    import textwrap

    oracle = worktree / "tests" / "acceptance" / "x_roundtrip.py"
    oracle.parent.mkdir(parents=True)
    oracle.write_text(textwrap.dedent("""
        def test_roundtrip():
            assert True
    """))
    v = CoachValidator(worktree_path=worktree, task_id="TASK-R7-001")
    v._pytest_interpreter = lambda: sys.executable  # type: ignore[method-assign]

    result = v._produce_behavioural_oracle(authored_files=[], task={"id": "TASK-R7-001"})

    assert result["oracle_path"] == "tests/acceptance/x_roundtrip.py"
    assert result["run_evidence"]["command_kind"] == "behavioural oracle"
    assert isinstance(result["run_evidence"]["command"], list)


def test_a_required_oracle_carries_its_run_record_and_keeps_its_verdict(worktree, tmp_path):
    import hashlib
    import sys

    checker = tmp_path / "checker.py"
    checker.write_text(
        "from pathlib import Path\nimport json, os\n"
        "Path(os.environ['GUARDKIT_BEHAVIOURAL_ORACLE_RECEIPT']).write_text("
        "json.dumps({'run': 1, 'failures': 0, 'errors': 0, 'skipped': 0}))\n"
    )
    task = {
        "behavioural_oracle": {
            "command": f"{sys.executable} -B {checker}",
            "expected_exit": 0,
            "timeout": 20,
            "required": True,
            "expected_checks": 1,
            "checker_path": str(checker),
            "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
            "source_paths": ["src.txt"],
        }
    }
    v = CoachValidator(worktree_path=worktree, task_id="TASK-REQ")

    result = v._produce_behavioural_oracle(
        authored_files=[], task=task, task_id="TASK-REQ", turn=2
    )

    assert result["passed"] is True and result["receipt_validation"]["valid"] is True
    assert result["run_evidence"]["command_kind"] == "behavioural oracle"
    assert result["run_evidence"]["source"]["before"]["status"] == "recorded"


def test_the_oracle_record_stays_out_of_the_prompt(worktree):
    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.coach_verification import HonestyVerification
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    v = CoachValidator(worktree_path=worktree, task_id="TASK-R7-001")
    oracle = v._produce_behavioural_oracle(
        authored_files=[], task={"behavioural_oracle": {"command": "true"}}
    )
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0),
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
