"""One writer at a time, and nothing else refuses the next writer (26 October 2026).

FEAT-CC77: a task the tree already satisfied was recorded as unapproved, so the
writer marker refused every later task. FEAT-3BA8: a feature check's coverage run
deleted a committed ``.coverage.<host>.pid…`` file and wrote ``.coverage``; the
boundary refusal that followed refused every later task. Step 2 deleted the
marker and boundary refusals: the real lease and the real AutoBuild
``orchestrate`` run here. No model, broker, remote repository or fixture
product is used.
"""

import subprocess
from types import MethodType, SimpleNamespace

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
from guardkit.orchestrator.task_work_scope import (
    approved_head,
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
    AutoBuild's ``orchestrate`` nested inside on the feature's worktree. Each
    task commits one file, so every task leaves a different HEAD. Returns the
    checkout, the tasks that ran and the HEAD each one left."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    root = repository(tmp_path / "checkout")
    runner = AutoBuildOrchestrator(
        repo_root=root,
        existing_worktree=SimpleNamespace(path=root),
        enable_context=False,
        enable_pre_loop=False,
    )
    answers = iter(decisions)
    ran, heads = [], []

    def owned(self, task_id, *a, **k):
        ran.append(task_id)
        (root / f"{task_id}.txt").write_text(task_id)
        git(root, "add", ".")
        git(root, "commit", "-m", task_id)
        heads.append(git(root, "rev-parse", "HEAD"))
        return SimpleNamespace(final_decision=next(answers))

    runner._orchestrate_owned = MethodType(owned, runner)
    for number in range(1, len(decisions) + 1):
        with checkout_lease(root) as lease:
            lease.admit(f"TASK-{number}")
            runner.orchestrate(f"TASK-{number}", "r", [])
            # The checkpoint writer records the task's own commit.
            lease.checkpoint_completed()
    return root, ran, heads


def test_an_already_satisfied_task_lets_the_next_task_in(tmp_path):
    # Before the fix: ScopeUnavailable "Prior writer is unapproved or its termination is unknown".
    _, ran, _ = _run_tasks(tmp_path, ["already_satisfied", "approved"])
    assert ran == ["TASK-1", "TASK-2"]


def test_a_task_after_an_unapproved_task_is_admitted_and_runs(tmp_path):
    """Step 2 (26 October 2026): task A approved, task B not approved, task C
    is admitted and runs on top of what B left. The approved part offered
    stays A's commit, the work before the first unapproved task."""
    root, ran, heads = _run_tasks(
        tmp_path, ["approved", "max_turns_exceeded", "approved"]
    )
    assert ran == ["TASK-1", "TASK-2", "TASK-3"]
    assert (root / "TASK-2.txt").exists()  # B's work stays for the next task
    assert approved_head(root) == heads[0]


def test_every_task_approved_offers_the_last_one(tmp_path):
    root, _, heads = _run_tasks(tmp_path, ["approved", "approved"])
    assert approved_head(root) == heads[-1]


def test_uncommitted_work_a_task_left_is_the_next_tasks_starting_point(tmp_path):
    root = repository(tmp_path / "checkout")
    with checkout_lease(root) as lease:
        lease.admit("TASK-A")
        (root / "half-done.py").write_text("left by a task that was not approved\n")
        lease.poison("TASK-A was not approved")
    with checkout_lease(root) as lease:  # no refusal: the next writer is admitted
        scope = lease.admit("TASK-B")
        assert scope.task_id == "TASK-B"
        assert any("half-done.py" in note for note in lease.notes)
    assert (root / "half-done.py").exists()


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


def test_a_check_that_rewrites_already_changed_work_is_left_and_the_build_goes_on(tmp_path, caplog):
    root = repository(tmp_path / "checkout")
    feature, worktree = _feature(root)
    with checkout_lease(root) as lease:
        lease.admit("TASK-A")
        (root / "base").write_text("the task's own unsaved change\n")

    def rewrite():
        (root / "base").write_text("the check rewrote it\n")
        return "gate result"

    assert feature._checked_writer(worktree, rewrite) == "gate result"
    assert (root / "base").read_text() == "the check rewrote it\n"
    assert "left as it is" in caplog.text
    with checkout_lease(root) as lease:  # the next writer is admitted
        lease.admit("TASK-NEXT")


def test_a_check_that_stages_a_change_does_not_refuse_the_next_writer(tmp_path):
    root = repository(tmp_path / "checkout")
    feature, worktree = _feature(root)

    def stage():
        (root / "staged").write_text("the check staged this")
        git(root, "add", "staged")
        return "gate result"

    assert feature._checked_writer(worktree, stage) == "gate result"
    assert git(root, "diff", "--cached", "--name-only") == "staged"
    with checkout_lease(root) as lease:
        lease.admit("TASK-NEXT")


def test_a_check_that_commits_does_not_refuse_the_next_writer(tmp_path):
    root = repository(tmp_path / "checkout")
    feature, worktree = _feature(root)

    def commit():
        (root / "committed").write_text("the check committed this")
        git(root, "add", "committed")
        git(root, "commit", "-m", "a check must never commit")
        return "gate result"

    assert feature._checked_writer(worktree, commit) == "gate result"
    assert (root / "committed").exists()
    with checkout_lease(root) as lease:
        lease.admit("TASK-NEXT")
