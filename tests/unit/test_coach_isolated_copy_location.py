"""Where the Coach's isolated copy of the worktree lives.

When a wave holds two or more tasks, the Coach runs the declared test command
in a copy of the worktree. It used to make that copy in the system temp folder.
On 3 October 2026 (FEAT-FFEC, FEAT-78F7) a test bind-mounted a file from the
copy into a container; the container engine ran on another machine that could
not see the runner's ``/tmp``, so it mounted an empty folder and the test
failed before reaching the code. The copy now lives beside the worktree, in
its parent directory, so anything that can see the worktree can see the copy.

These tests run the real code with real commands (no mocked subprocess):

* the copy is made beside the worktree, not in the system temp folder;
* the test command runs inside the copy, which carries the worktree's files;
* the copy never shows up in ``git status`` of the worktree, nor of a checkout
  that holds the worktree's parent, and git inside the copy finds no
  repository (as it did in the system temp folder);
* the copy is removed afterwards — after a pass, a failure and a timeout;
* a plain directory (not a git worktree) works the same;
* if the parent cannot take a new folder, the copy falls back to the system
  temp folder and says so.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


PREFIX = "guardkit-coach-iso-"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.fixture
def system_temp(tmp_path, monkeypatch) -> Path:
    """Point the system temp folder somewhere we can watch.

    pytest's own ``tmp_path`` lives under the real system temp folder, so
    "not under /tmp" cannot be asserted directly; instead the module-level
    temp folder is redirected and must stay empty.
    """
    d = tmp_path / "system-temp"
    d.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(d))
    return d


@pytest.fixture
def git_layout(tmp_path):
    """A build clone with a feature worktree at ``.guardkit/worktrees/FEAT-X``.

    Mirrors the live runner layout
    ``<build clone>/.guardkit/worktrees/<FEAT>``. The clone deliberately does
    NOT ignore ``.guardkit/`` in its own .gitignore, so the copy staying out
    of ``git status`` is the copy's own doing, not the project's.
    """
    clone = tmp_path / "build-clone"
    clone.mkdir()
    _git(clone, "init", "-q", "-b", "main")
    _git(clone, "config", "user.email", "t@example.invalid")
    _git(clone, "config", "user.name", "t")
    (clone / "README").write_text("clone\n")
    _git(clone, "add", "README")
    _git(clone, "commit", "-q", "-m", "init")

    worktrees = clone / ".guardkit" / "worktrees"
    worktrees.mkdir(parents=True)
    worktree = worktrees / "FEAT-X"
    _git(clone, "worktree", "add", "-q", "-b", "feat", str(worktree))
    (worktree / ".gitignore").write_text("only-the-worktrees-own-rules\n")
    (worktree / "qa").mkdir()
    (worktree / "qa" / "probe.py").write_text("print('probe')\n")
    _git(worktree, "add", ".gitignore", "qa/probe.py")
    _git(worktree, "commit", "-q", "-m", "worktree files")
    return clone, worktree


def _validator(worktree: Path, test_cmd: str, wave_size: int = 2) -> CoachValidator:
    v = CoachValidator(
        worktree_path=str(worktree),
        task_id="TASK-COPYLOC-001",
        test_command=test_cmd,
        wave_size=wave_size,
    )
    v._coach_test_execution = "subprocess"
    return v


def _recording_command(out: Path, worktree: Path, clone: Path | None) -> str:
    """A shell command that records what it saw while running in the copy."""
    q = shlex.quote
    lines = [
        f"pwd > {q(str(out / 'pwd'))}",
        f"cat qa/probe.py > {q(str(out / 'probe'))}",
        f"cat .gitignore > {q(str(out / 'gitignore'))}",
        f"ls -a .. > {q(str(out / 'holder_listing'))}",
        f"cat ../.gitignore > {q(str(out / 'holder_gitignore'))}",
        f"(git rev-parse --show-toplevel > {q(str(out / 'toplevel'))} 2>&1;"
        f" echo $? > {q(str(out / 'toplevel_rc'))})",
    ]
    if (worktree / ".git").exists():
        lines.append(
            f"git -C {q(str(worktree))} status --porcelain --untracked-files=all"
            f" > {q(str(out / 'worktree_status'))}"
        )
    if clone is not None:
        lines.append(
            f"git -C {q(str(clone))} status --porcelain --untracked-files=all"
            f" > {q(str(out / 'clone_status'))}"
        )
    return "; ".join(lines)


def _leftovers(parent: Path) -> list[str]:
    return sorted(p.name for p in parent.iterdir() if PREFIX in p.name)


class TestTheCopyLivesBesideTheWorktree:
    def test_copy_is_made_beside_the_worktree_and_the_command_runs_in_it(
        self, tmp_path, git_layout, system_temp
    ):
        clone, worktree = git_layout
        out = tmp_path / "out"
        out.mkdir()

        v = _validator(worktree, _recording_command(out, worktree, clone))
        result = v._run_isolated_tests(v.test_command)

        assert result.tests_passed, result.test_output_summary
        assert not result.check_could_not_run

        # The command ran in the copy: <worktree parent>/.<name>/<name>.
        ran_in = Path((out / "pwd").read_text().strip())
        assert ran_in.name.startswith(PREFIX)
        assert ran_in.parent.name == "." + ran_in.name
        assert ran_in.parent.parent == worktree.parent
        assert ran_in != worktree
        assert worktree not in ran_in.parents  # never inside the worktree

        # ...and carried the worktree's own files, its own .gitignore intact.
        assert (out / "probe").read_text() == "print('probe')\n"
        assert (out / "gitignore").read_text() == "only-the-worktrees-own-rules\n"
        # The holder holds only the copy and the ignore-everything file.
        listing = set((out / "holder_listing").read_text().split())
        assert listing == {".", "..", ".gitignore", ran_in.name}
        assert (out / "holder_gitignore").read_text() == "*\n"

        # Not in the system temp folder.
        assert list(system_temp.iterdir()) == []

    def test_copy_never_shows_in_git_status(self, tmp_path, git_layout, system_temp):
        clone, worktree = git_layout
        out = tmp_path / "out"
        out.mkdir()
        clone_status_before = _git(
            clone, "status", "--porcelain", "--untracked-files=all"
        )

        v = _validator(worktree, _recording_command(out, worktree, clone))
        result = v._run_isolated_tests(v.test_command)
        assert result.tests_passed, result.test_output_summary

        # Taken WHILE the copy existed, by the command itself.
        assert (out / "worktree_status").read_text() == ""
        clone_status_during = (out / "clone_status").read_text()
        assert PREFIX not in clone_status_during
        assert clone_status_during == clone_status_before

    def test_git_inside_the_copy_finds_no_repository(
        self, tmp_path, git_layout, system_temp
    ):
        """The copy has no .git; git must not climb out and find the clone."""
        clone, worktree = git_layout
        out = tmp_path / "out"
        out.mkdir()

        v = _validator(worktree, _recording_command(out, worktree, clone))
        assert v._run_isolated_tests(v.test_command).tests_passed

        assert (out / "toplevel_rc").read_text().strip() != "0"
        assert str(clone) not in (out / "toplevel").read_text()


class TestTheCopyIsRemoved:
    def test_removed_after_a_pass(self, tmp_path, git_layout, system_temp):
        _, worktree = git_layout
        v = _validator(worktree, "true")
        assert v._run_isolated_tests("true").tests_passed
        assert _leftovers(worktree.parent) == []
        assert sorted(p.name for p in worktree.parent.iterdir()) == ["FEAT-X"]

    def test_removed_after_a_failure(self, tmp_path, git_layout, system_temp):
        _, worktree = git_layout
        v = _validator(worktree, "echo 1 failed; exit 1")
        result = v._run_isolated_tests(v.test_command)
        assert not result.tests_passed
        assert _leftovers(worktree.parent) == []

    def test_removed_after_a_timeout(self, tmp_path, git_layout, system_temp):
        _, worktree = git_layout
        v = _validator(worktree, "sleep 5")
        v.test_timeout = 1
        result = v._run_isolated_tests(v.test_command)
        assert not result.tests_passed
        assert _leftovers(worktree.parent) == []

    def test_removed_even_when_the_command_leaves_read_only_files(
        self, tmp_path, git_layout, system_temp
    ):
        _, worktree = git_layout
        v = _validator(
            worktree,
            "mkdir -p made locked && touch made/f locked/g"
            " && chmod 555 made && chmod 000 locked",
        )
        assert v._run_isolated_tests(v.test_command).tests_passed
        assert _leftovers(worktree.parent) == []

    def test_removed_with_nested_read_only_and_unreadable_folders(
        self, tmp_path, git_layout, system_temp, caplog
    ):
        """Review round 1, R2: the outer folder cannot even be listed and the
        inner one is read-only; both belong to this process, so all of it
        must go, without a single cleanup warning."""
        _, worktree = git_layout
        v = _validator(
            worktree,
            "mkdir -p outer/inner && touch outer/inner/f"
            " && chmod 555 outer/inner && chmod 000 outer",
        )
        with caplog.at_level(logging.WARNING):
            assert v._run_isolated_tests(v.test_command).tests_passed
        assert _leftovers(worktree.parent) == []
        assert not [
            r for r in caplog.records if "cleaning up the isolated copy" in r.getMessage()
        ]

    def test_cleanup_never_changes_permissions_through_a_link_back_to_the_worktree(
        self, tmp_path, git_layout, system_temp
    ):
        """The copy links skipped folders (a bootstrap environment, say) back
        to the real ones in the worktree. Opening up permissions for cleanup
        must not follow those links into the worktree."""
        _, worktree = git_layout
        venv = worktree / ".venv"
        (venv / "bin").mkdir(parents=True)
        (venv / "bin" / "python").write_text("")
        venv.chmod(0o555)
        try:
            v = _validator(worktree, "test -L .venv")
            assert v._run_isolated_tests(v.test_command).tests_passed
            assert _leftovers(worktree.parent) == []
            assert (venv.stat().st_mode & 0o777) == 0o555
            assert (venv / "bin" / "python").exists()
        finally:
            venv.chmod(0o755)


class TestLeftoversStayHiddenFromGit:
    """Review round 1, R1: if part of the copy cannot be removed (a folder a
    container wrote into as root), the holder's ignore-everything file must
    stay, so the containing checkout stays clean and ``git add -A`` stages
    nothing from it.

    A non-root test cannot make a folder it owns undeletable, so ownership is
    simulated: ``os.chmod`` refuses for the one folder, exactly as it refuses
    for a root-owned folder. The failure to delete is then real — the folder
    is genuinely read-only and the file in it genuinely cannot be unlinked.
    """

    def test_undeletable_leftovers_keep_the_ignore_file_and_the_clone_clean(
        self, tmp_path, git_layout, system_temp, monkeypatch, caplog
    ):
        clone, worktree = git_layout
        status_before = _git(clone, "status", "--porcelain", "--untracked-files=all")

        real_chmod = os.chmod

        def chmod_as_if_root_owned(path, mode, *args, **kwargs):
            if os.path.basename(os.fspath(path)) == "written-by-a-container":
                raise PermissionError(1, "Operation not permitted", os.fspath(path))
            return real_chmod(path, mode, *args, **kwargs)

        monkeypatch.setattr(os, "chmod", chmod_as_if_root_owned)
        v = _validator(
            worktree,
            "mkdir written-by-a-container && echo data > written-by-a-container/out"
            " && chmod 555 written-by-a-container",
        )
        with caplog.at_level(logging.WARNING):
            assert v._run_isolated_tests(v.test_command).tests_passed
        monkeypatch.setattr(os, "chmod", real_chmod)

        holders = [p for p in worktree.parent.iterdir() if p.name.startswith("." + PREFIX)]
        try:
            assert len(holders) == 1
            holder = holders[0]
            stuck = holder / holder.name.lstrip(".") / "written-by-a-container"
            assert (stuck / "out").read_text() == "data\n"  # really left behind
            assert (holder / ".gitignore").read_text() == "*\n"  # protection kept
            assert any("could not be removed completely" in r.getMessage()
                       for r in caplog.records)

            # The containing clone does not ignore this location itself: only
            # the holder's own .gitignore keeps the leftovers out of git.
            assert ".guardkit" not in (clone / ".git" / "info" / "exclude").read_text()
            assert not (clone / ".gitignore").exists()
            assert (
                _git(clone, "status", "--porcelain", "--untracked-files=all")
                == status_before
            )
            subprocess.run(
                ["git", "add", "-A"], cwd=str(clone), check=True, capture_output=True
            )
            staged = _git(clone, "diff", "--cached", "--name-only")
            assert PREFIX not in staged
        finally:
            for h in holders:
                for dirpath, dirnames, _ in os.walk(h):
                    for d in dirnames:
                        os.chmod(os.path.join(dirpath, d), 0o755)

    def test_the_holder_is_removed_once_the_copy_is_gone(
        self, tmp_path, git_layout, system_temp
    ):
        _, worktree = git_layout
        v = _validator(worktree, "true")
        assert v._run_isolated_tests("true").tests_passed
        assert [p.name for p in worktree.parent.iterdir()] == ["FEAT-X"]


class TestPlainDirectory:
    def test_a_plain_directory_works_the_same(self, tmp_path, system_temp):
        parent = tmp_path / "workspace"
        worktree = parent / "project"
        (worktree / "qa").mkdir(parents=True)
        (worktree / "qa" / "probe.py").write_text("print('probe')\n")
        (worktree / ".gitignore").write_text("only-the-worktrees-own-rules\n")
        out = tmp_path / "out"
        out.mkdir()

        v = _validator(worktree, _recording_command(out, worktree, None))
        result = v._run_isolated_tests(v.test_command)

        assert result.tests_passed, result.test_output_summary
        ran_in = Path((out / "pwd").read_text().strip())
        assert ran_in.parent.parent == parent
        assert (out / "probe").read_text() == "print('probe')\n"
        assert _leftovers(parent) == []
        assert list(system_temp.iterdir()) == []


class TestFallback:
    @pytest.mark.skipif(
        hasattr(os, "geteuid") and os.geteuid() == 0,
        reason="root can write into a read-only folder",
    )
    def test_falls_back_to_system_temp_when_the_parent_is_read_only(
        self, tmp_path, system_temp, caplog
    ):
        parent = tmp_path / "read-only"
        worktree = parent / "project"
        worktree.mkdir(parents=True)
        (worktree / "f").write_text("x\n")
        out = tmp_path / "out"
        out.mkdir()
        parent.chmod(0o555)
        try:
            v = _validator(worktree, f"pwd > {shlex.quote(str(out / 'pwd'))}; cat f")
            with caplog.at_level(logging.WARNING):
                result = v._run_isolated_tests(v.test_command)
        finally:
            parent.chmod(0o755)

        assert result.tests_passed, result.test_output_summary
        ran_in = Path((out / "pwd").read_text().strip())
        assert ran_in.parent.parent == system_temp
        assert list(system_temp.iterdir()) == []  # cleaned up
        assert any(
            "system temp folder instead" in r.getMessage() for r in caplog.records
        )


class TestRoutedFromAParallelWave:
    def test_a_wave_of_two_runs_the_declared_command_in_the_copy_beside_the_worktree(
        self, tmp_path, git_layout, system_temp
    ):
        _, worktree = git_layout
        out = tmp_path / "out"
        out.mkdir()
        v = _validator(
            worktree, f"pwd > {shlex.quote(str(out / 'pwd'))}", wave_size=2
        )
        result = v.run_independent_tests()

        assert result.tests_passed, result.test_output_summary
        ran_in = Path((out / "pwd").read_text().strip())
        assert ran_in.parent.parent == worktree.parent
        assert ran_in.name.startswith(PREFIX)
        assert _leftovers(worktree.parent) == []

    def test_a_wave_of_one_still_runs_in_the_worktree_itself(
        self, tmp_path, git_layout, system_temp
    ):
        _, worktree = git_layout
        out = tmp_path / "out"
        out.mkdir()
        v = _validator(
            worktree, f"pwd > {shlex.quote(str(out / 'pwd'))}", wave_size=1
        )
        assert v.run_independent_tests().tests_passed
        assert Path((out / "pwd").read_text().strip()) == worktree


class TestGitCeiling:
    def test_sets_the_ceiling_to_the_holder(self, tmp_path):
        env = CoachValidator._with_git_ceiling({"A": "1"}, tmp_path)
        assert env == {"A": "1", "GIT_CEILING_DIRECTORIES": str(tmp_path)}

    def test_keeps_an_existing_ceiling_and_does_not_mutate_the_input(self, tmp_path):
        original = {"GIT_CEILING_DIRECTORIES": "/elsewhere"}
        env = CoachValidator._with_git_ceiling(original, tmp_path)
        assert env["GIT_CEILING_DIRECTORIES"] == f"{tmp_path}{os.pathsep}/elsewhere"
        assert original == {"GIT_CEILING_DIRECTORIES": "/elsewhere"}
