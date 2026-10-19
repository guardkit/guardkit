"""The project commands' private folders are owner-only (19 October 2026).

``launch_declaration._private_directory`` made a missing folder with mode 0700
but took an existing one as it found it. It now makes an existing folder of
this user's owner-only too, and refuses another user's. These are the project
commands' ``HOME`` and ``TMPDIR`` (``project_command_env``) and the declared
``launch.scratch`` folders, so the same tests as the factory's shell folders.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.launch_declaration import (
    LaunchDeclaration,
    LaunchEnvironmentError,
    _private_directory,
    apply_launch_environment,
)
from guardkit.orchestrator.paths import prepare_builder_scratch_dir
from guardkit.orchestrator.project_command_env import project_command_environment


def _checkout(tmp_path: Path) -> Path:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    subprocess.run(["git", "init", "-q", str(worktree)], check=True)
    return worktree


def _toolchain(worktree: Path) -> Path:
    scratch = prepare_builder_scratch_dir(worktree)
    assert scratch is not None
    return scratch / "toolchain"


def _mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_existing_open_home_and_tmpdir_are_made_owner_only(tmp_path: Path) -> None:
    worktree = _checkout(tmp_path)
    toolchain = _toolchain(worktree)
    for name in ("HOME", "TMPDIR"):
        (toolchain / name).mkdir(parents=True, exist_ok=True)
        (toolchain / name / "kept").write_text("kept\n")
        (toolchain / name).chmod(0o777)
    toolchain.chmod(0o777)

    env = project_command_environment(worktree, None)

    assert env["HOME"] == str(toolchain / "HOME")
    assert env["TMPDIR"] == str(toolchain / "TMPDIR")
    for folder in (toolchain, toolchain / "HOME", toolchain / "TMPDIR"):
        assert _mode(folder) == 0o700, folder
    assert (toolchain / "HOME" / "kept").read_text() == "kept\n"


def test_new_folders_are_owner_only(tmp_path: Path) -> None:
    worktree = _checkout(tmp_path)

    env = project_command_environment(worktree, None)

    assert _mode(Path(env["HOME"])) == 0o700
    assert _mode(Path(env["TMPDIR"])) == 0o700


def test_an_existing_open_declared_scratch_folder_is_made_owner_only(
    tmp_path: Path,
) -> None:
    worktree = _checkout(tmp_path)
    folder = _toolchain(worktree) / "TOOL_CACHE"
    folder.mkdir(parents=True)
    folder.chmod(0o777)

    env = apply_launch_environment({}, LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree)

    assert env["TOOL_CACHE"] == str(folder)
    assert _mode(folder) == 0o700


def test_a_folder_owned_by_another_user_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _checkout(tmp_path)
    (_toolchain(worktree) / "HOME").mkdir(parents=True)
    real_uid = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: real_uid + 1)

    with pytest.raises(LaunchEnvironmentError, match="another user"):
        project_command_environment(worktree, None)


def test_a_symlink_is_still_refused(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    elsewhere.chmod(0o755)
    link = tmp_path / "link"
    link.symlink_to(elsewhere, target_is_directory=True)

    with pytest.raises(LaunchEnvironmentError, match="not a real folder"):
        _private_directory(link)
    assert _mode(elsewhere) == 0o755  # the target is never touched


def test_a_folder_made_by_another_caller_first_is_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "raced"
    original = Path.mkdir

    def made_first(self: Path, *args, **kwargs):
        if self == folder:
            original(self, mode=0o755)
            raise FileExistsError(str(self))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", made_first)

    assert _private_directory(folder) == folder
    assert _mode(folder) == 0o700
