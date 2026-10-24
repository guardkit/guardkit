"""Explicit task-writer admission helpers for legacy test fixtures.

These helpers deliberately do not participate in pytest discovery and do not
auto-admit anything.  A test must identify the exact clean Git boundary and
keep the returned lease alive for every scope-aware operation it exercises.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import subprocess

from guardkit.orchestrator.task_work_scope import (
    checkout_lease,
    register_fresh_checkout,
)


def git(root: Path, *args: str) -> str:
    """Run Git in an invented local fixture repository."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def register_clean_fresh_checkout(root: Path) -> str:
    """Register one genuinely fresh, clean fixture checkout at its real HEAD."""
    root = Path(root)
    head = git(root, "rev-parse", "HEAD")
    status = git(root, "status", "--porcelain")
    assert status == "", f"fresh fixture registration requires a clean tree: {status}"
    register_fresh_checkout(root, head)
    return head


class RetainedTaskAdmission:
    """An explicitly opened fixture admission, closed by the owning test."""

    def __init__(
        self,
        root: Path,
        task_id: str,
        *,
        feature_id: str = "",
        round_id: str = "initial",
        evidence_repos=(),
        register: bool = False,
    ) -> None:
        if register:
            register_clean_fresh_checkout(root)
        self._context = checkout_lease(root, evidence_repos)
        self.lease = self._context.__enter__()
        self.scope = self.lease.admit(task_id, feature_id, round_id)

    def close(self) -> None:
        self._context.__exit__(None, None, None)


@contextmanager
def admitted_task(
    root: Path,
    task_id: str,
    *,
    feature_id: str = "",
    round_id: str = "initial",
    evidence_repos=(),
    register: bool = False,
):
    """Retain one real checkout lease and its immutable admitted task scope."""
    if register:
        register_clean_fresh_checkout(root)
    with checkout_lease(root, evidence_repos) as lease:
        scope = lease.admit(task_id, feature_id, round_id)
        yield lease, scope
