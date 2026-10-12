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
    monkeypatch.setattr(run_evidence, "originating_worktree_identity", _broken)
    monkeypatch.setattr(
        run_evidence, "docker_events_between", _broken
    )
    broken = _validator(worktree, cmd, wave_size=wave_size).run_independent_tests()

    assert broken.tests_passed is baseline.tests_passed is passed
    assert broken.signal_absent == baseline.signal_absent
    assert broken.test_output_summary == baseline.test_output_summary
    assert broken.run_evidence["runs"][0]["capture_errors"]


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
