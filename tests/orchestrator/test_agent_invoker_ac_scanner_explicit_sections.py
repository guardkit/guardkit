"""Tests for ``AgentInvoker._read_declared_file_sections``: the task
document's ``## Files to Create`` / ``## Files to Modify`` sections.

(27 October 2026 cull: ``_scan_ac_for_missing_paths``,
``_extract_explicit_planned_files`` and the ``_compute_plan_audit_verdict``
escalation they fed are deleted, with their tests and the FEAT-PEBR run-2
fixture worktree that only they used.)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker


# ==================== Fixtures ====================


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Empty worktree with the standard ``tasks/in_progress`` directory."""
    (tmp_path / "tasks" / "in_progress").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=1,
        sdk_timeout_seconds=10,
    )


def _write_task(
    worktree: Path,
    task_id: str,
    body: str,
    *,
    state: str = "in_progress",
) -> Path:
    """Write a task file with a hand-crafted body (no AC list templating)."""
    content = (
        "---\n"
        f"id: {task_id}\n"
        "title: Test task\n"
        f"status: {state}\n"
        "---\n\n"
        f"{body}\n"
    )
    task_path = worktree / "tasks" / state / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(content)
    return task_path


# ==================== The reader that keeps the two sections apart ============


class TestReadDeclaredFileSections:
    """The reader keeps the two sections apart, and tells a section that
    says "nothing" from a section that is not there."""

    def test_the_two_sections_are_kept_apart(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- `src/users/router.py`\n\n"
            "## Files to Modify\n\n"
            "- `src/users/crud.py`\n"
            "- `src/users/schemas.py`\n"
        )
        _write_task(worktree, "TASK-READ-001", body)

        declared = invoker._read_declared_file_sections("TASK-READ-001")

        assert declared["create"] == ["src/users/router.py"]
        assert declared["modify"] == [
            "src/users/crud.py",
            "src/users/schemas.py",
        ]

    def test_creates_nothing_and_changes_two_files_can_be_said(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- _none_\n\n"
            "## Files to Modify\n\n"
            "- `src/a.py`\n"
            "- `src/b.py`\n"
        )
        _write_task(worktree, "TASK-READ-002", body)

        declared = invoker._read_declared_file_sections("TASK-READ-002")

        assert declared["create"] == [], (
            "the section is there and says nothing: that is a claim, not a "
            "missing section"
        )
        assert declared["modify"] == ["src/a.py", "src/b.py"]

    def test_a_section_that_is_not_there_is_not_a_claim(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- `src/a.py`\n"
        )
        _write_task(worktree, "TASK-READ-003", body)

        declared = invoker._read_declared_file_sections("TASK-READ-003")

        assert declared["create"] == ["src/a.py"]
        assert declared["modify"] is None

    def test_a_heading_with_nothing_under_it_is_not_a_claim(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """An unfinished task document is not a declaration of nothing."""
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "## Implementation notes\n\n"
            "- some prose.\n"
        )
        _write_task(worktree, "TASK-READ-004", body)

        declared = invoker._read_declared_file_sections("TASK-READ-004")

        assert declared["create"] is None
        assert declared["modify"] is None

    def test_descriptions_and_subsections_are_handled(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "### The endpoint\n\n"
            "- `src/users/router.py` \u2014 the route itself\n"
            "- `src/users/schemas.py` - the shape of the answer\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] AC-1: it answers.\n"
        )
        _write_task(worktree, "TASK-READ-005", body)

        declared = invoker._read_declared_file_sections("TASK-READ-005")

        assert declared["create"] == [
            "src/users/router.py",
            "src/users/schemas.py",
        ], "a subsection is part of the section, and a description is not a path"
        assert declared["modify"] is None

    def test_an_unknown_task_makes_no_claim(
        self, invoker: AgentInvoker
    ) -> None:
        declared = invoker._read_declared_file_sections("TASK-DOES-NOT-EXIST")

        assert declared == {"create": None, "modify": None}

    def test_a_none_marker_is_a_section_that_says_nothing(
        self, worktree: Path, invoker: AgentInvoker
    ) -> None:
        """``- _none_`` under a heading is an explicit empty section."""
        body = (
            "# Task: Demo\n\n"
            "## Files to Create\n\n"
            "- _none_\n\n"
            "## Files to Modify\n\n"
            "- `src/a.py`\n"
        )
        _write_task(worktree, "TASK-READ-006", body)

        assert invoker._read_declared_file_sections("TASK-READ-006") == {
            "create": [],
            "modify": ["src/a.py"],
        }
