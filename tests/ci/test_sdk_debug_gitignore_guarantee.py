"""CI test for sdk_debug keep-out-of-git guarantee (TASK-OBS-396E AC-3).

Ensures that:
1. git check-ignore confirms sdk_debug paths (worktree and archive forms) are ignored
2. The narrow `!` allow-patterns in .gitignore (TASK-HMIG-009/010 audit exceptions)
   do NOT un-ignore any sdk_debug/ path

This is a structural defence, not a convention — the guarantee is a test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    """Get repository root directory."""
    # Walk up from this file to find .git
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    pytest.fail("Could not find repository root (no .git)")


class TestSdkDebugKeepOutOfGit:
    """Test sdk_debug paths are properly ignored by git (AC-3)."""

    def test_worktree_sdk_debug_is_ignored(self, repo_root: Path) -> None:
        """Worktree form: .guardkit/autobuild/<task>/sdk_debug/ is ignored."""
        # ARRANGE: representative worktree sdk_debug path
        test_path = repo_root / ".guardkit" / "autobuild" / "TASK-TEST" / "sdk_debug" / "turn_1"

        # ACT: check if git would ignore this path
        result = subprocess.run(
            ["git", "check-ignore", str(test_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # ASSERT: git check-ignore returns 0 (path is ignored)
        assert result.returncode == 0, (
            f"sdk_debug worktree path NOT ignored by git:\n"
            f"  Path: {test_path}\n"
            f"  Expected: ignored (returncode 0)\n"
            f"  Got: returncode {result.returncode}\n"
            f"  This violates the keep-out-of-git guarantee (TASK-OBS-396E AC-3).\n"
            f"  Ensure .guardkit/autobuild/* pattern is in .gitignore."
        )

    def test_archive_sdk_debug_is_ignored(self, repo_root: Path) -> None:
        """Archive form: .guardkit/archive/<run>/sdk_debug/ is ignored."""
        # ARRANGE: representative archive sdk_debug path (per TASK-OBS-80FE)
        test_path = repo_root / ".guardkit" / "archive" / "run_001" / "TASK-TEST" / "sdk_debug"

        # ACT
        result = subprocess.run(
            ["git", "check-ignore", str(test_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # ASSERT: ignored
        assert result.returncode == 0, (
            f"sdk_debug archive path NOT ignored by git:\n"
            f"  Path: {test_path}\n"
            f"  This violates the keep-out-of-git guarantee.\n"
            f"  Ensure .guardkit/archive/ pattern is in .gitignore."
        )

    def test_allow_patterns_do_not_unignore_sdk_debug(self, repo_root: Path) -> None:
        """The `!` allow-patterns in .gitignore must NOT un-ignore sdk_debug/ paths.

        TASK-HMIG-009/010 added narrow `!.guardkit/autobuild/TASK-REV-HMIG-*` patterns.
        This test ensures those patterns don't accidentally un-ignore sdk_debug/.
        """
        # ARRANGE: paths that are close to the allow-patterns
        test_paths = [
            # Under a TASK-REV-HMIG-canary task
            repo_root / ".guardkit" / "autobuild" / "TASK-REV-HMIG-001" / "sdk_debug" / "turn_1",
            # Under the canary results file location
            repo_root / ".guardkit" / "autobuild" / "sdk_debug",
            # Nested under allowed location
            repo_root / ".guardkit" / "autobuild" / "TASK-REV-HMIG-canary" / "default" / "TASK-X" / "sdk_debug",
        ]

        for test_path in test_paths:
            # ACT
            result = subprocess.run(
                ["git", "check-ignore", str(test_path)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # ASSERT: still ignored (not un-ignored by ! patterns)
            assert result.returncode == 0, (
                f"sdk_debug path ACCIDENTALLY UN-IGNORED by .gitignore ! pattern:\n"
                f"  Path: {test_path}\n"
                f"  The narrow `!` allow-patterns in .gitignore must NOT un-ignore sdk_debug/.\n"
                f"  Review .gitignore and ensure sdk_debug/ stays ignored everywhere."
            )

    def test_nested_sdk_debug_files_are_ignored(self, repo_root: Path) -> None:
        """Files inside sdk_debug/ are ignored, not just the directory."""
        # ARRANGE: representative files inside sdk_debug/
        test_paths = [
            repo_root / ".guardkit" / "autobuild" / "TASK-TEST" / "sdk_debug" / "turn_1" / "prompt.txt",
            repo_root / ".guardkit" / "autobuild" / "TASK-TEST" / "sdk_debug" / "turn_1" / "messages.jsonl",
            repo_root / ".guardkit" / "autobuild" / "TASK-TEST" / "sdk_debug" / "turn_1" / "coach" / "prompt.txt",
        ]

        for test_path in test_paths:
            # ACT
            result = subprocess.run(
                ["git", "check-ignore", str(test_path)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # ASSERT: ignored
            assert result.returncode == 0, (
                f"sdk_debug file NOT ignored by git:\n"
                f"  File: {test_path}\n"
                f"  All files under sdk_debug/ must be ignored."
            )
