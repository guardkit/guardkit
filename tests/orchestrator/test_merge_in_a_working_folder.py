"""The merge happens in a working folder of its own, and the main copy is not touched.

One-true-copy design pass, 21 September 2026 ("Every step happens in a working
folder of its own"): the merge used to switch the branch checked out in the
repository's main copy, underneath whoever else was using it. It can now be
told a working folder — an ordinary ``git worktree`` of the same repository,
made at the commit being joined onto — and everything that touches a tree
happens there instead.

Real git in ``tmp_path``. No mocks of git, no network, no model seats, and
nothing here knows what the repository contains.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.merge_executor import (
    OUTCOME_CONFLICT,
    OUTCOME_MERGED,
    execute_merge,
    perform_merge,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "app.txt").write_text("x\n", encoding="utf-8")
    (repo / "shared.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


@pytest.fixture
def repo_with_branch(tmp_path: Path) -> Path:
    """main, a build branch, and main left checked out with work of its own."""
    repo = _init_repo(tmp_path)
    _git(repo, "checkout", "-q", "-b", "autobuild/FEAT-W")
    (repo / "feature.txt").write_text("built by the factory\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-q", "-m", "feature work")
    _git(repo, "checkout", "-q", "main")
    # main moves on, so a join is a real join and not a fast-forward.
    (repo / "someone-else.txt").write_text("another hand\n", encoding="utf-8")
    _git(repo, "add", "someone-else.txt")
    _git(repo, "commit", "-q", "-m", "someone else's work")
    return repo


def _integration_folder(repo: Path, branch: str, at: str) -> Path:
    """A working folder of its own, on a new branch, at exactly ``at``."""
    folder = repo / ".forge" / "worktrees" / "integration"
    _git(repo, "worktree", "add", "-q", "-b", branch, str(folder), at)
    return folder


class TestTheMainCopyIsNeverSwitched:
    def test_the_join_happens_in_the_folder_and_main_stays_put(
        self, repo_with_branch: Path
    ):
        repo = repo_with_branch
        g = _git(repo, "rev-parse", "main")
        branch_before = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        folder = _integration_folder(repo, "factory-integration/FEAT-W", g)

        report = perform_merge(
            repo,
            "FEAT-W",
            target_branch="factory-integration/FEAT-W",
            working_folder=folder,
        )

        assert report.outcome == OUTCOME_MERGED
        # The main copy: same branch, same commit, nothing merged into it.
        assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == branch_before
        assert _git(repo, "rev-parse", "main") == g
        assert not (repo / "feature.txt").exists()
        # The joined commit J is a real merge of G and the build's tip.
        j = _git(repo, "rev-parse", "factory-integration/FEAT-W")
        parents = _git(repo, "rev-list", "--parents", "-1", j).split()
        assert parents[1] == g
        assert parents[2] == _git(repo, "rev-parse", "autobuild/FEAT-W")
        # And the folder has both sides of the join in it.
        assert (folder / "feature.txt").exists()
        assert (folder / "someone-else.txt").exists()

    def test_without_a_folder_the_merge_is_exactly_what_it_was(
        self, repo_with_branch: Path
    ):
        repo = repo_with_branch
        pre = _git(repo, "rev-parse", "main")

        report = perform_merge(repo, "FEAT-W")

        assert report.outcome == OUTCOME_MERGED
        assert report.pre_sha == pre
        assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
        assert (repo / "feature.txt").exists()


class TestTheWholeCommandInTheFolder:
    def test_execute_merge_pins_the_target_and_joins_in_the_folder(
        self, repo_with_branch: Path
    ):
        repo = repo_with_branch
        g = _git(repo, "rev-parse", "main")
        folder = _integration_folder(repo, "factory-integration/FEAT-W", g)

        report = execute_merge(
            repo_root=repo,
            feature_id="FEAT-W",
            target_branch="factory-integration/FEAT-W",
            expect_target_sha=g,
            verify=False,
            working_folder=folder,
        )

        assert report.outcome == OUTCOME_MERGED
        assert report.target_branch == "factory-integration/FEAT-W"
        assert _git(repo, "rev-parse", "main") == g
        assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"

    def test_a_dirty_main_copy_does_not_refuse_a_join_in_its_own_folder(
        self, repo_with_branch: Path
    ):
        """The preflight looks at the folder's tree, which is the tree being merged."""
        repo = repo_with_branch
        g = _git(repo, "rev-parse", "main")
        folder = _integration_folder(repo, "factory-integration/FEAT-W", g)
        (repo / "someone-is-editing.txt").write_text("in progress\n", encoding="utf-8")

        report = execute_merge(
            repo_root=repo,
            feature_id="FEAT-W",
            target_branch="factory-integration/FEAT-W",
            expect_target_sha=g,
            verify=False,
            working_folder=folder,
        )

        assert report.outcome == OUTCOME_MERGED
        # The person's uncommitted file is still there, untouched.
        assert (repo / "someone-is-editing.txt").read_text() == "in progress\n"


class TestAConflictIsReportedAndNothingElseHappens:
    def test_conflict_in_the_folder_leaves_both_trees_clean(self, tmp_path: Path):
        repo = _init_repo(tmp_path)
        _git(repo, "checkout", "-q", "-b", "autobuild/FEAT-C")
        (repo / "shared.txt").write_text("branch side\n", encoding="utf-8")
        _git(repo, "commit", "-aqm", "branch edit")
        _git(repo, "checkout", "-q", "main")
        (repo / "shared.txt").write_text("main side\n", encoding="utf-8")
        _git(repo, "commit", "-aqm", "main edit")

        g = _git(repo, "rev-parse", "main")
        folder = _integration_folder(repo, "factory-integration/FEAT-C", g)

        report = perform_merge(
            repo,
            "FEAT-C",
            target_branch="factory-integration/FEAT-C",
            working_folder=folder,
        )

        assert report.outcome == OUTCOME_CONFLICT
        assert "shared.txt" in report.conflict_files
        # Nothing landed anywhere, and both trees are clean.
        assert _git(repo, "rev-parse", "factory-integration/FEAT-C") == g
        assert _git(repo, "rev-parse", "main") == g
        # (the working folders' own directory is the only untracked thing)
        assert _git(repo, "status", "--porcelain") == "?? .forge/"
        assert _git(folder, "status", "--porcelain") == ""
        # The branch that was merged survives, as it does on every path.
        assert _git(repo, "rev-parse", "--verify", "--quiet", "autobuild/FEAT-C")
