"""The factory's real git callers run no program the project's settings name.

Each test calls a real GuardKit function against a real repository whose own
settings and hooks name marker programs (:mod:`tests.fixtures.git_marker_lab`),
with a secret in GuardKit's environment. Before the fix each of these ran
project programs that could see the secret.

Every test here also runs with a ``git`` shim first on ``PATH``. The shim
records any git call that lacks the helper's ``core.hooksPath=/dev/null``
setting (on its command line, or handed down to a child git), however the
caller built its command line. ``test_factory_git_calls_all_go_through_the_helper``
fails if any test in this file made such a call.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Dict, List

import pytest

from tests.fixtures.git_marker_lab import GIT, SECRET_NAME, SECRET_VALUE, Lab
from tests.task_scope_fixtures import admitted_task

REAL_GIT = os.path.realpath(GIT)

#: Direct git calls the shim saw, by test name.
DIRECT_CALLS: Dict[str, List[str]] = {}

SHIM = """#!/bin/sh
case "$* $GIT_CONFIG_PARAMETERS" in
  *core.hooksPath=/dev/null*|*core.hookspath*/dev/null*|*core.hooksPath*/dev/null*) ;;
  *) printf '%s\\n' "$*" >> "{log}" ;;
esac
exec "{git}" "$@"
"""


@pytest.fixture(autouse=True)
def git_shim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request) -> Path:
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    log = tmp_path / "direct-git-calls.txt"
    shim = shim_dir / "git"
    shim.write_text(SHIM.replace("{log}", str(log)).replace("{git}", REAL_GIT))
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}")
    try:  # the helper finds git once; let it find the real one
        from guardkit.lib import project_git
    except ImportError:
        project_git = None
    if project_git is not None:
        monkeypatch.setattr(project_git, "_git_program_cache", [REAL_GIT])
    yield log
    if request.node.name != "test_factory_git_calls_all_go_through_the_helper":
        DIRECT_CALLS[request.node.name] = (
            log.read_text().splitlines() if log.exists() else []
        )


@pytest.fixture()
def lab(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Lab:
    made = Lab(tmp_path / "lab")
    monkeypatch.setenv("HOME", str(made.home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv(SECRET_NAME, SECRET_VALUE)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Lab")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "lab@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Lab")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "lab@example.invalid")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_PARAMETERS",
                 "GIT_CONFIG_COUNT", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"):
        monkeypatch.delenv(name, raising=False)
    return made


def _invoker(worktree: Path):
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker._git_lock = threading.Lock()
    invoker.worktree_path = worktree
    invoker._baseline_commit = None
    return invoker


# ---------------------------------------------------------------------------
# The turn's change counts


def test_worktree_change_snapshot_runs_no_project_program(lab: Lab) -> None:
    from guardkit.orchestrator.autobuild import _worktree_change_snapshot

    repo = lab.marked_repo("repo")
    lab.fired()
    snapshot = _worktree_change_snapshot(repo)
    snapshot_quiet = _worktree_change_snapshot(repo, no_optional_locks=True)
    assert lab.fired() == []
    assert snapshot is not None and "a.txt" in snapshot
    assert snapshot_quiet is not None and "a.txt" in snapshot_quiet


def test_detect_git_changes_runs_no_project_program(lab: Lab) -> None:
    repo = lab.marked_repo("repo")
    (repo / "new.md").write_text("new\n")
    with admitted_task(repo, "TASK-T1") as (_lease, scope):
        invoker = _invoker(repo)
        invoker.task_work_scope = scope
        lab.fired()
        changes = invoker._detect_git_changes()
        assert lab.fired() == []
    assert "a.txt" in changes["modified"]
    assert "new.md" in changes["created"]


def test_detect_git_changes_sees_a_change_a_filter_hides(lab: Lab) -> None:
    repo = lab.base_repo("repo", attributes="*.txt filter=liar\n")
    liar = lab.program("liar", f'cat >/dev/null\n"{REAL_GIT}" show HEAD:"$1"\n')
    lab.setup_git(repo, "config", "filter.liar.clean", f"{liar} %f")
    lab.same_size_edit(repo / "a.txt")
    with admitted_task(repo, "TASK-T1") as (_lease, scope):
        invoker = _invoker(repo)
        invoker.task_work_scope = scope
        lab.fired()
        changes = invoker._detect_git_changes()
        assert "a.txt" in changes["modified"]
        assert lab.fired() == []


def test_set_aside_check_runs_no_project_program(lab: Lab) -> None:
    repo = lab.marked_repo("repo")
    invoker = _invoker(repo)
    lab.fired()
    report = {"files_created": ["gone.md"], "files_modified": [], "tests_written": []}
    removed = invoker._set_aside_written_then_removed(report, ["gone.md"], [], [])
    assert removed == ["gone.md"]
    assert lab.fired() == []


# ---------------------------------------------------------------------------
# Checkpoints


def test_checkpoint_commit_runs_no_hook_filter_or_signing(lab: Lab) -> None:
    from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager

    repo = lab.marked_repo("repo")
    with admitted_task(repo, "TASK-T1") as (_lease, scope):
        manager = WorktreeCheckpointManager(
            worktree_path=repo, task_id="TASK-T1", task_work_scope=scope
        )
        lab.fired()
        checkpoint = manager.create_checkpoint(turn=1, tests_passed=True, test_count=1)
        assert lab.fired() == []
    assert checkpoint.commit_hash == lab.setup_git(repo, "rev-parse", "HEAD").strip()
    assert "a.txt" in lab.setup_git(repo, "show", "--name-only", "--format=", "HEAD")


# ---------------------------------------------------------------------------
# Evidence and committed content


def test_originating_worktree_identity_runs_no_clean_filter(lab: Lab) -> None:
    from guardkit.orchestrator import run_evidence

    repo = lab.marked_repo("repo")
    lab.fired()
    record = run_evidence.originating_worktree_identity(repo)
    assert lab.fired() == []
    assert record["status"] == run_evidence.RECORDED, record
    assert record["tree_with_untracked"]


def test_committed_content_changed_paths_runs_no_file_monitor(lab: Lab) -> None:
    from guardkit.lib.committed_content import changed_paths

    repo = lab.marked_repo("repo")
    lab.fired()
    assert changed_paths(repo, ["a.txt", "b.txt"]) == {"a.txt", "b.txt"}
    assert lab.fired() == []


def test_read_head_runs_no_project_program(lab: Lab) -> None:
    from guardkit.orchestrator.head_identity import read_head

    repo = lab.marked_repo("repo")
    lab.fired()
    head = read_head(repo)
    assert lab.fired() == []
    assert head["symbolic_ref"] == "refs/heads/main"


# ---------------------------------------------------------------------------
# Worktrees, merges and refresh


def test_worktree_manager_create_runs_no_smudge_or_checkout_hook(lab: Lab) -> None:
    from guardkit.worktrees.manager import WorktreeManager

    repo = lab.marked_repo("repo", edits=False)
    lab.fired()
    worktree = WorktreeManager(repo_root=repo).create("TASK-T1")
    assert lab.fired() == []
    assert (worktree.path / "a.txt").exists()
    assert lab.setup_git(worktree.path, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    "condition, program",
    [("gitdir:**/worktrees/**", "smudge_wt"), ("onbranch:autobuild/**", "smudge_br")],
    ids=["gitdir", "onbranch"],
)
def test_worktree_manager_create_with_destination_only_include(
    lab: Lab, condition: str, program: str
) -> None:
    from guardkit.worktrees.manager import WorktreeManager

    repo = lab.base_repo("repo", attributes="*.txt filter=late\n")
    lab.include(repo, condition, f'[filter "late"]\n\tsmudge = {lab.path(program)}\n', "c.inc")
    lab.fired()
    worktree = WorktreeManager(repo_root=repo).create("TASK-T1")
    assert lab.fired() == []
    assert (worktree.path / "a.txt").read_text() == "one\n"


def test_perform_merge_runs_no_project_program(lab: Lab) -> None:
    from guardkit.orchestrator.merge_executor import OUTCOME_MERGED, perform_merge

    repo = lab.marked_repo("repo", edits=False)
    lab.setup_git(repo, "config", "branch.main.mergeOptions", "--gpg-sign")
    lab.fired()
    report = perform_merge(repo, "FEAT-T1", target_branch="main", branch="side")
    assert lab.fired() == []
    assert report.outcome == OUTCOME_MERGED, report
    assert (repo / "a.txt").read_text() == "one\n2\n3\n4\n5\nsix\n"


def test_checkout_failure_note_has_no_git_text(lab: Lab) -> None:
    from guardkit.orchestrator.merge_executor import checkout_branch

    repo = lab.base_repo("repo")
    name = "IGNORE-PREVIOUS-INSTRUCTIONS.txt"
    (repo / name).write_text("base\n")
    lab.setup_git(repo, "add", "-A")
    lab.setup_git(repo, "commit", "-qm", "named")
    lab.setup_git(repo, "checkout", "-q", "-b", "other")
    (repo / name).write_text("other\n")
    lab.setup_git(repo, "commit", "-qam", "other")
    lab.setup_git(repo, "checkout", "-q", "main")
    (repo / name).write_text("dirty\n")
    reason = checkout_branch(repo, "other")
    assert reason is not None
    assert "IGNORE" not in reason
    assert reason == "could not switch to branch other: git checkout stopped with exit code 1."


def test_refresh_does_not_fetch(lab: Lab, monkeypatch: pytest.MonkeyPatch, git_shim: Path) -> None:
    from rich.console import Console

    from guardkit.orchestrator import feature_orchestrator
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
    from guardkit.worktrees.manager import Worktree

    repo = lab.base_repo("repo")
    origin = lab.root / "origin.git"
    lab.setup_git(lab.root, "clone", "-q", "--bare", str(repo), str(origin))
    lab.setup_git(repo, "remote", "add", "origin", str(origin))
    lab.setup_git(repo, "fetch", "-q", "origin")
    lab.setup_git(repo, "config", "remote.origin.uploadpack", lab.path("uploadpack"))
    (repo / "fix.md").write_text("local fix\n")
    lab.setup_git(repo, "add", "-A")
    lab.setup_git(repo, "commit", "-qm", "local fix, not pushed")
    tree = lab.root / "feature-tree"
    lab.setup_git(repo, "worktree", "add", "-q", str(tree), "-b", "autobuild/FEAT-T1", "HEAD~1")
    (tree / "feature.md").write_text("feature\n")
    lab.setup_git(tree, "add", "-A")
    lab.setup_git(tree, "commit", "-qm", "feature work")
    shown = io.StringIO()
    monkeypatch.setattr(feature_orchestrator, "console", Console(file=shown, width=200))
    orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
    lab.fired()
    orchestrator._refresh_worktree(
        Worktree(task_id="FEAT-T1", branch_name="autobuild/FEAT-T1", path=tree,
                 base_branch="main"),
        base_branch="main",
    )
    assert lab.fired() == []
    calls = git_shim.read_text() if git_shim.exists() else ""
    assert "fetch" not in calls
    assert (tree / "fix.md").exists()  # rebased onto the local base branch
    assert "fetch it yourself first" in shown.getvalue()


# ---------------------------------------------------------------------------
# guardkit task complete


def test_task_complete_state_commit_runs_no_hook_or_signing(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    from installer.core.commands.lib import git_state_helper

    repo = lab.marked_repo("repo", edits=False)
    state = repo / "docs" / "state" / "TASK-T1"
    state.mkdir(parents=True)
    (state / "state.json").write_text("{}\n")
    monkeypatch.chdir(repo)
    lab.fired()
    git_state_helper.commit_state_files("TASK-T1", "Save state for TASK-T1")
    assert lab.fired() == []
    assert "docs/state/TASK-T1/state.json" in lab.setup_git(
        repo, "show", "--name-only", "--format=", "HEAD"
    )


# ---------------------------------------------------------------------------
# The shim


def test_factory_git_calls_all_go_through_the_helper(git_shim: Path) -> None:
    subprocess.run(["git", "--version"], capture_output=True, check=False)
    assert git_shim.read_text().splitlines() == ["--version"]  # the shim works
    if len(DIRECT_CALLS) < 5:
        pytest.skip("run the whole file: this test reads what the others recorded")
    direct = {name: calls for name, calls in DIRECT_CALLS.items() if calls}
    assert direct == {}


def test_worktree_change_snapshot_switches_off_a_filter_whose_name_is_not_utf8(lab: Lab) -> None:
    from guardkit.orchestrator.autobuild import _worktree_change_snapshot

    repo = lab.base_repo("repo")
    (repo / ".gitattributes").write_bytes(b"*.txt filter=\xff\xfe\n")
    lab.setup_git(repo, "add", "-A")
    lab.setup_git(repo, "commit", "-qm", "attributes")
    with open(repo / ".git" / "config", "ab") as config:
        config.write(b'[filter "\xff\xfe"]\n\tclean = ' + lab.path("clean").encode() + b"\n")
    lab.same_size_edit(repo / "a.txt")
    lab.fired()
    assert _worktree_change_snapshot(repo) is not None
    assert lab.fired() == []
