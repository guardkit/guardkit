"""WorktreeManager.cleanup removes guardkitfactory's short shell TMPDIRs too.

guardkitfactory's builder and checker shells keep their TMPDIRs in /tmp, outside the
worktree, so removing the worktree no longer removes them (31 October 2026).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from guardkit.worktrees.manager import Worktree, WorktreeManager

backend_config = pytest.importorskip("guardkitfactory.harness.backend_config")


def test_cleanup_removes_the_shells_tmpdirs(tmp_path):
    worktree_path = tmp_path / "repo" / ".guardkit" / "worktrees" / "TASK-TEST-001"
    worktree_path.mkdir(parents=True)
    executor = Mock()
    executor.run.return_value = Mock(returncode=0, stdout="", stderr="")

    with patch("guardkit.worktrees.manager.get_archive_root_from_env", return_value=tmp_path / "archive"), \
            patch.object(backend_config, "remove_shell_tmpdirs", create=True) as remove:
        manager = WorktreeManager(repo_root=tmp_path / "repo", executor=executor)
        manager.cleanup(
            Worktree(task_id="TASK-TEST-001", path=worktree_path,
                     branch_name="autobuild/TASK-TEST-001", base_branch="main"),
            force=True,
        )

    remove.assert_called_once_with(worktree_path)
