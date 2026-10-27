"""Recovered state names the files a task created, not the folders.

Build FEAT-D31F (19 October 2026): the recovery path listed new folders as
created files because git folds a new folder into one line. The claim-audit
tests that used to live here asserted the deleted honesty check (cull, 27
October 2026) and went with it.

Real git repositories under ``tmp_path``; invented names; no network, no model.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from guardkit.orchestrator.state_detection import detect_git_changes
from tests.task_scope_fixtures import admitted_task


TASK_ID = "TASK-SHELF-002"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


def _write(root: Path, rel: str, text: str = "invented\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class TestRecoveredStateNamesFilesNotFolders:
    def test_a_new_folder_is_listed_file_by_file(self, tmp_path: Path) -> None:
        """Turn 2 of the same build was refused over folder "claims".

        The recovery path listed ``.claude/task-plans/`` and ``.local/`` as
        created files because git folds a new folder into one line.
        """
        root = tmp_path / "repo"
        root.mkdir()
        _git("init", "--initial-branch=main", cwd=root)
        _git("config", "user.email", "test@example.com", cwd=root)
        _git("config", "user.name", "Test", cwd=root)
        _write(root, "README.md", "base\n")
        _git("add", "-A", cwd=root)
        _git("commit", "-m", "base", cwd=root)
        with admitted_task(root, TASK_ID, register=True) as (_, scope):
            _write(root, "drafts/plans/plan-1.md", "plan\n")
            _write(root, "drafts/plans/plan-2.md", "plan\n")
            changes = detect_git_changes(root, task_work_scope=scope)

        assert changes is not None
        assert sorted(changes.files_added) == [
            "drafts/plans/plan-1.md",
            "drafts/plans/plan-2.md",
        ]
