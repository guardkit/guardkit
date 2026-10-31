"""The project commands' private folders are owner-only (19 October 2026).

``launch_declaration._private_directory`` made a missing folder with mode 0700
but took an existing one as it found it. It now makes an existing folder
owner-only too. These are the project
commands' ``HOME`` and ``TMPDIR`` (``project_command_env``) and the declared
``launch.scratch`` folders, so the same tests as the factory's shell folders.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.launch_declaration import (
    LaunchDeclaration,
    _private_directory,
    apply_launch_environment,
)
from guardkit.orchestrator.paths import prepare_builder_scratch_dir
from guardkit.orchestrator.project_command_env import (
    project_command_environment,
    remove_short_tmpdir,
    short_tmpdir_path,
)


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
    tmpdir = short_tmpdir_path(toolchain.parent)
    for folder in (toolchain / "HOME", tmpdir):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "kept").write_text("kept\n")
        folder.chmod(0o777)
    toolchain.chmod(0o777)

    env = project_command_environment(worktree, None)

    assert env["HOME"] == str(toolchain / "HOME")
    assert env["TMPDIR"] == str(tmpdir)
    for folder in (toolchain, toolchain / "HOME", tmpdir):
        assert _mode(folder) == 0o700, folder
    assert (toolchain / "HOME" / "kept").read_text() == "kept\n"
    assert (tmpdir / "kept").read_text() == "kept\n"


# The short TMPDIR (1 November 2026). The project's commands had TMPDIR at
# <repo>/.git/worktrees/<FEAT>/guardkit-scratch/toolchain/TMPDIR; `dotnet
# test` (Microsoft.Testing.Platform) opens a named pipe there with a name of
# about 32 characters, and .NET refuses a socket path over 103 bytes, so every
# test project of a .NET copy aborted ("Zero tests ran", exit 134).

DOTNET_SOCKET_LIMIT = 103
PIPE_NAME = "0123456789abcdef0123456789abcdef"  # 32 characters


@pytest.mark.real_project_scratch
def test_a_socket_in_the_tmpdir_fits_with_a_deep_repo_and_a_long_feature(
    tmp_path: Path,
) -> None:
    deep = tmp_path / ("very-long-folder-name-" * 4) / "Projects" / "work"
    deep.mkdir(parents=True)
    repo = deep / "career-assistant-dotnet"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    for args in (
        ["config", "user.email", "t@t.t"],
        ["config", "user.name", "t"],
        ["commit", "-q", "--allow-empty", "-m", "start"],
    ):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    worktree = repo / ".guardkit" / "worktrees" / "FEAT-ASSESSMENT-AND-SHORTLIST-0A1B2C3D"
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(worktree)],
        check=True,
    )
    try:
        env = project_command_environment(worktree, None)
        socket = f"{env['TMPDIR']}/{PIPE_NAME}"
        assert len(socket.encode()) <= DOTNET_SOCKET_LIMIT, socket
        assert env["TMPDIR"].startswith("/tmp/gk-")
        assert _mode(Path(env["TMPDIR"])) == 0o700
        old_place = prepare_builder_scratch_dir(worktree) / "toolchain" / "TMPDIR"
        assert len(f"{old_place}/{PIPE_NAME}".encode()) > DOTNET_SOCKET_LIMIT
    finally:
        remove_short_tmpdir(worktree)
    assert not Path(env["TMPDIR"]).exists()


def test_each_worktree_has_its_own_tmpdir(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    first = _checkout(tmp_path / "a")
    one = project_command_environment(first, None)["TMPDIR"]
    two = project_command_environment(_checkout(tmp_path / "b"), None)["TMPDIR"]
    assert one != two
    assert project_command_environment(first, None)["TMPDIR"] == one


def test_a_tmpdir_name_taken_by_a_link_is_refused(tmp_path: Path) -> None:
    from guardkit.orchestrator.launch_declaration import LaunchEnvironmentError

    worktree = _checkout(tmp_path)
    target = short_tmpdir_path(_toolchain(worktree).parent)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(elsewhere)

    with pytest.raises(LaunchEnvironmentError):
        project_command_environment(worktree, None)


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
