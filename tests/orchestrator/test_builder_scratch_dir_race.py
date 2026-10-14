"""Two builds preparing one worktree's scratch folder at once both get it.

``prepare_builder_scratch_dir`` checks the folder is missing and then makes
it. A second build doing the same at the same moment used to lose the race,
get "file exists", and report no scratch folder; the factory then put the
coding model's working files in a temporary folder instead (14 October 2026).
"""

from __future__ import annotations

import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from guardkit.orchestrator import paths
from guardkit.orchestrator.paths import builder_scratch_dir, prepare_builder_scratch_dir


def _checkout(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def test_losing_the_mkdir_race_still_returns_the_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _checkout(tmp_path / "wt")
    scratch = builder_scratch_dir(worktree)
    scratch.mkdir(mode=0o700)
    # The check ran before the other build made the folder.
    monkeypatch.setattr(paths.os.path, "lexists", lambda _p: False)

    assert prepare_builder_scratch_dir(worktree) == Path(os.path.realpath(scratch))


def test_a_symlink_made_by_the_race_winner_is_still_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _checkout(tmp_path / "wt")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    builder_scratch_dir(worktree).symlink_to(elsewhere, target_is_directory=True)
    monkeypatch.setattr(paths.os.path, "lexists", lambda _p: False)

    assert prepare_builder_scratch_dir(worktree) is None


def test_eight_builds_at_once_all_get_the_same_folder(tmp_path: Path) -> None:
    for round_number in range(10):
        worktree = _checkout(tmp_path / f"wt{round_number}")
        start = threading.Barrier(8)

        def prepare() -> Path | None:
            start.wait()
            return prepare_builder_scratch_dir(worktree)

        with ThreadPoolExecutor(max_workers=8) as pool:
            folders = list(pool.map(lambda _: prepare(), range(8)))
        assert set(folders) == {
            Path(os.path.realpath(builder_scratch_dir(worktree)))
        }, folders
