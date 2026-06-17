"""Real-git integration: WorktreeManager.create installs the BDD bridge.

TASK-AB-BDDNEUTRAL01 Half 2 — the autobuild worktree bootstrap auto-installs
``features/conftest.py`` when the checked-out worktree carries tagged
``.feature`` files but no bridge. This exercises the wire end-to-end against a
real git repo + a real ``git worktree add`` (no mocks), which is the only honest
way to verify the fix actually reaches the FEAT-MEM-07 scenario (a pre-existing
repo with committed feature files but no bridge).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from guardkit.worktrees import WorktreeManager


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git not available"
)


_FEATURE = """\
@task:TASK-AB-BDDNEUTRAL01
Feature: Sample
  Scenario: One
    Given a thing
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    return r


class TestWorktreeCreateInstallsBridge:
    def test_create_installs_bridge_when_feature_committed(self, repo: Path):
        # Commit a tagged .feature but NO conftest bridge (the FEAT-MEM-07 shape).
        (repo / "features").mkdir()
        (repo / "features" / "login.feature").write_text(_FEATURE, encoding="utf-8")
        (repo / "README.md").write_text("seed\n", encoding="utf-8")
        _commit_all(repo, "seed with feature, no bridge")

        manager = WorktreeManager(repo)
        worktree = manager.create("TASK-AB-001", base_branch="main")

        bridge = worktree.path / "features" / "conftest.py"
        assert bridge.is_file(), "WorktreeManager.create must install the bridge"
        assert "pytest_collect_file" in bridge.read_text(encoding="utf-8")

    def test_create_without_features_is_noop(self, repo: Path):
        (repo / "README.md").write_text("seed\n", encoding="utf-8")
        _commit_all(repo, "seed, no features dir")

        manager = WorktreeManager(repo)
        worktree = manager.create("TASK-AB-002", base_branch="main")

        assert not (worktree.path / "features").exists()

    def test_create_does_not_clobber_committed_conftest(self, repo: Path):
        (repo / "features").mkdir()
        (repo / "features" / "login.feature").write_text(_FEATURE, encoding="utf-8")
        (repo / "features" / "conftest.py").write_text(
            "# project's own bridge\n", encoding="utf-8"
        )
        _commit_all(repo, "seed with feature AND own bridge")

        manager = WorktreeManager(repo)
        worktree = manager.create("TASK-AB-003", base_branch="main")

        assert (worktree.path / "features" / "conftest.py").read_text(
            encoding="utf-8"
        ) == "# project's own bridge\n"
