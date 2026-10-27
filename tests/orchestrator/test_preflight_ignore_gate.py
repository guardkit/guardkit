"""Tests for ``load_planned_targets``: a task's planned files, from its plan or
front matter. (The git check-ignore advice these tests also covered was removed
with the other checks on 27 October 2026.)"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.preflight_ignore_gate import load_planned_targets


# ---------- fixtures ----------------------------------------------------


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A fresh ``git init`` worktree with no .gitignore yet."""
    subprocess.run(
        ["git", "init", "-q"], cwd=str(tmp_path), check=True
    )
    # Quiet "please tell me who you are" warnings on minimal CI envs.
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(tmp_path),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        check=True,
    )
    return tmp_path


def _write_gitignore(worktree: Path, content: str) -> None:
    (worktree / ".gitignore").write_text(content + "\n", encoding="utf-8")


def _write_plan_json(worktree: Path, task_id: str, plan: dict) -> Path:
    state_dir = worktree / "docs" / "state" / task_id
    state_dir.mkdir(parents=True)
    json_path = state_dir / "implementation_plan.json"
    json_path.write_text(json.dumps(plan), encoding="utf-8")
    return json_path


def _write_task_file(
    worktree: Path,
    task_id: str,
    *,
    files_to_create: list[str] | None = None,
    files_to_modify: list[str] | None = None,
) -> Path:
    """Drop a minimal task markdown into ``tasks/in_progress/``."""
    task_dir = worktree / "tasks" / "in_progress"
    task_dir.mkdir(parents=True)
    frontmatter_lines = [
        "---",
        f"id: {task_id}",
        f'title: "test task for {task_id}"',
        "status: in_progress",
    ]
    if files_to_create is not None:
        frontmatter_lines.append("files_to_create:")
        for path in files_to_create:
            frontmatter_lines.append(f"  - {path}")
    if files_to_modify is not None:
        frontmatter_lines.append("files_to_modify:")
        for path in files_to_modify:
            frontmatter_lines.append(f"  - {path}")
    frontmatter_lines.append("---")
    body = "\n".join(frontmatter_lines) + "\n\n# body\n"
    task_path = task_dir / f"{task_id}-stub.md"
    task_path.write_text(body, encoding="utf-8")
    return task_path


# ---------- unit tests: helpers ----------------------------------------


# ---------- integration tests: full gate ------------------------------


class TestLoadPlannedTargets:
    """Direct coverage of the source-resolver."""

    def test_prefers_plan_over_frontmatter(self, worktree: Path) -> None:
        _write_plan_json(
            worktree,
            "TASK-T13",
            {"plan": {"files_to_create": ["from_plan.py"], "files_to_modify": []}},
        )
        _write_task_file(
            worktree, "TASK-T13", files_to_create=["from_frontmatter.py"]
        )

        targets = load_planned_targets("TASK-T13", worktree)

        assert targets == ["from_plan.py"]

    def test_falls_back_to_frontmatter_when_no_plan(
        self, worktree: Path
    ) -> None:
        _write_task_file(
            worktree, "TASK-T14", files_to_create=["from_frontmatter.py"]
        )

        targets = load_planned_targets("TASK-T14", worktree)

        assert targets == ["from_frontmatter.py"]

    def test_returns_none_when_no_source(self, worktree: Path) -> None:
        assert load_planned_targets("TASK-T15", worktree) is None


# ---------- message formatting ----------------------------------------


