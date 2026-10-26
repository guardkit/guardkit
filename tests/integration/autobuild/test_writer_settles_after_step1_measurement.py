"""The two writer-marker refusals the step 1 measurement found (26 October 2026).

FEAT-CC77: a task the tree already satisfied was recorded as unapproved, so the
writer marker refused every later task. FEAT-3BA8: a feature check's coverage run
deleted a committed ``.coverage.<host>.pid…`` file and wrote ``.coverage``; the
boundary refusal that followed refused every later task. No model, broker,
remote repository or fixture product is used.
"""

from pathlib import Path
import subprocess
from types import MethodType, SimpleNamespace

import pytest

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.task_work_scope import (
    ScopeUnavailable,
    checkout_lease,
    register_fresh_checkout,
)


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def repository(root):
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "user.email", "fixture@example.invalid")
    (root / "base").write_text("baseline\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "immutable source")
    register_fresh_checkout(root, git(root, "rev-parse", "HEAD"))
    return root


def _run_tasks(tmp_path, decisions):
    """Each task as the feature orchestrator runs it: its own writer lease, with
    AutoBuild's ``orchestrate`` nested inside on the feature's worktree."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    root = repository(tmp_path / "checkout")
    runner = AutoBuildOrchestrator(
        repo_root=root,
        existing_worktree=SimpleNamespace(path=root),
        enable_context=False,
        enable_pre_loop=False,
    )
    answers = iter(decisions)
    runner._orchestrate_owned = MethodType(
        lambda self, *a, **k: SimpleNamespace(final_decision=next(answers)), runner
    )
    for number in range(1, len(decisions) + 1):
        with checkout_lease(root) as lease:
            lease.admit(f"TASK-{number}")
            runner.orchestrate(f"TASK-{number}", "r", [])


def test_an_already_satisfied_task_lets_the_next_task_in(tmp_path):
    # Before the fix: ScopeUnavailable "Prior writer is unapproved or its termination is unknown".
    _run_tasks(tmp_path, ["already_satisfied", "approved"])


def test_a_task_that_was_not_approved_still_refuses_the_next_task(tmp_path):
    with pytest.raises(ScopeUnavailable, match="Prior writer"):
        _run_tasks(tmp_path, ["max_turns_exceeded", "approved"])


def _feature(root):
    feature = FeatureOrchestrator.__new__(FeatureOrchestrator)
    feature._evidence_repos_resolved = []
    return feature, SimpleNamespace(path=root)


def test_a_checks_coverage_leftovers_are_put_back_and_the_next_writer_is_admitted(tmp_path, caplog):
    root = repository(tmp_path / "checkout")
    parallel = root / ".coverage.host.pid8634.XVIC"
    parallel.write_text("committed by an earlier checkpoint")
    git(root, "add", ".")
    git(root, "commit", "-m", "checkpoint that carried a coverage part file")
    register_fresh_checkout(root, git(root, "rev-parse", "HEAD"))
    feature, worktree = _feature(root)

    def coverage_run():
        parallel.unlink()  # coverage combine
        (root / ".coverage").write_text("combined")
        return "gate result"

    assert feature._checked_writer(worktree, coverage_run) == "gate result"
    assert parallel.read_text() == "committed by an earlier checkpoint"
    assert not (root / ".coverage").exists()
    assert "were put back" in caplog.text
    with checkout_lease(root) as lease:  # the next writer is admitted
        lease.admit("TASK-NEXT")


def test_a_check_that_commits_or_rewrites_changed_work_is_still_refused(tmp_path):
    root = repository(tmp_path / "checkout")
    feature, worktree = _feature(root)
    with checkout_lease(root) as lease:
        lease.admit("TASK-A")
        (root / "base").write_text("the task's own unsaved change\n")

        def rewrite():
            (root / "base").write_text("the check rewrote it\n")

        with pytest.raises(ScopeUnavailable, match="changed product files"):
            feature._checked_writer(worktree, rewrite)
        assert (root / "base").read_text() == "the check rewrote it\n"
