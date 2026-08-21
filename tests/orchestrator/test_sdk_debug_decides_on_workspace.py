"""The capture decision must follow the folder being written to.

WHAT THIS PROTECTS AGAINST, in plain words
------------------------------------------
When AutoBuild records a copy of what it sent to the model, it writes those
files into a specific working folder. Whether it records at all is decided by
a list of project names that have recording switched on by default.

Those two things used to disagree. The write went into the working folder it
was handed, but the decision was made by looking at whatever folder the
program happened to be started from. Two things followed:

  * The safety check that keeps recorded prompts out of version control was
    checking the wrong folder — the one thing it exists to prevent.
  * Behaviour changed with the NAME of the checkout folder. A copy of the
    project checked out as "guardkit" recorded; the identical code checked out
    under any other name did not. The test suite therefore behaved differently
    in a scratch copy than in the main copy.

The fix makes the decision read the folder being written to. These tests pin
that down by moving the program's working folder around and showing it no
longer changes the answer.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator import sdk_debug


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv(sdk_debug.ENV_VAR, raising=False)
    monkeypatch.setattr(sdk_debug, "_unrecognized_env_warned", False, raising=False)


def _make_repo(root: Path, name: str) -> Path:
    """Create a real git repo named `name` that ignores its own capture folder."""
    repo = root / name
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".gitignore").write_text(".guardkit/autobuild/*\n", encoding="utf-8")
    return repo


class TestDecisionFollowsTheWriteTarget:
    def test_working_directory_name_does_not_switch_capture_on(
        self, tmp_path, monkeypatch
    ):
        """Standing in a folder called "guardkit" must not enable capture elsewhere.

        This is the exact shape of the original bug: the process runs inside a
        checkout named "guardkit" (which is on the default-on list) while the
        folder being captured belongs to something else entirely.
        """
        allowlisted_cwd = _make_repo(tmp_path, "guardkit")
        other_workspace = _make_repo(tmp_path, "some-client-project")

        monkeypatch.chdir(allowlisted_cwd)

        result = sdk_debug.preserve_prompt(
            workspace_root=other_workspace,
            task_id="TASK-001",
            turn=1,
            role="player",
            prompt="hello",
            options={"cwd": str(other_workspace)},
        )

        assert result is None, (
            "capture was enabled by the name of the current working directory, "
            "not by the workspace actually being written to"
        )
        assert not (other_workspace / ".guardkit").exists()

    def test_capture_follows_an_allowlisted_workspace_from_any_directory(
        self, tmp_path, monkeypatch
    ):
        """Conversely, an allowlisted workspace records no matter where we stand."""
        neutral_cwd = _make_repo(tmp_path, "somewhere-else")
        workspace = _make_repo(tmp_path, "guardkit")

        monkeypatch.chdir(neutral_cwd)

        debug_dir = sdk_debug.preserve_prompt(
            workspace_root=workspace,
            task_id="TASK-001",
            turn=1,
            role="player",
            prompt="hello",
            options={"cwd": str(workspace)},
        )

        assert debug_dir is not None
        assert (debug_dir / "prompt.txt").read_text(encoding="utf-8") == "hello"
        # It wrote inside the workspace it was given, not inside the cwd.
        assert str(debug_dir).startswith(str(workspace))
        assert not (neutral_cwd / ".guardkit").exists()

    def test_same_answer_from_two_differently_named_checkouts(self, tmp_path, monkeypatch):
        """The identical workspace must give the identical answer from either cwd."""
        workspace = _make_repo(tmp_path, "guardkit")
        cwd_a = _make_repo(tmp_path, "guardkit-copy-a")
        cwd_b = _make_repo(tmp_path, "some-other-name")

        answers = []
        for cwd in (cwd_a, cwd_b):
            monkeypatch.chdir(cwd)
            answers.append(sdk_debug.preservation_enabled_for_repo(workspace))

        assert answers[0] == answers[1], (
            "the same workspace produced different answers depending on which "
            "directory the process was started from"
        )


class TestWorktreesResolveToTheirRepository:
    def test_linked_worktree_is_recognised_as_its_parent_repository(self, tmp_path):
        """A worktree named after a feature ID still counts as its repo.

        AutoBuild works inside folders like ``.guardkit/worktrees/FEAT-1234``.
        Reading the folder name alone would see "FEAT-1234" and miss the
        default-on list, silently switching off capture for exactly the runs
        the feature exists to record.
        """
        repo = _make_repo(tmp_path, "guardkit")
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        }
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True, env=env)

        worktree = repo / ".guardkit" / "worktrees" / "FEAT-1234"
        subprocess.run(
            ["git", "worktree", "add", "-q", "--detach", str(worktree)],
            cwd=repo,
            check=True,
            env=env,
        )

        # The folder is called FEAT-1234, so the name alone misses the list...
        assert sdk_debug._get_repo_name(worktree) == "FEAT-1234"
        # ...but the decision still recognises which project it belongs to.
        assert sdk_debug.preservation_enabled_for_repo(worktree) is True

    def test_a_worktree_of_a_non_allowlisted_project_stays_off(self, tmp_path):
        """The same resolution must not switch capture ON for a client project."""
        repo = _make_repo(tmp_path, "some-client-project")
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        }
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True, env=env)

        worktree = repo / ".guardkit" / "worktrees" / "FEAT-9999"
        subprocess.run(
            ["git", "worktree", "add", "-q", "--detach", str(worktree)],
            cwd=repo,
            check=True,
            env=env,
        )

        assert sdk_debug.preservation_enabled_for_repo(worktree) is False

    def test_a_plain_directory_falls_back_to_its_own_name(self, tmp_path):
        """Outside any repository, the folder name is still the best answer."""
        plain = tmp_path / "not-a-repo"
        plain.mkdir()
        assert sdk_debug._get_repo_name(plain) == "not-a-repo"
