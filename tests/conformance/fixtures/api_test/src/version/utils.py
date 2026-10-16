"""Utility functions for version information."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_git_commit_hash() -> str:
    """
    Get the current git commit hash (40 characters, full SHA-1).

    Returns the full 40-character git commit hash.
    Falls back to "unknown" if not in a git repository or if git is unavailable.

    Returns:
        str: 40-character git commit hash or "unknown"
    """
    try:
        # Find the git repository root by looking for .git directory
        current_dir = Path(__file__).resolve().parent
        while current_dir != current_dir.parent:
            if (current_dir / ".git").exists():
                break
            current_dir = current_dir.parent
        else:
            # No .git directory found
            return "unknown"

        # Run git command to get the full commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=current_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ):
        return "unknown"
