"""Tests for the /task-review ad-hoc entry (description form).

Scope: ai-transition docs/task-review-adhoc-entry-scope-2026-07-08.md.
Two halves:

  * ``create_task(task_type=...)`` — the deterministic Phase 0 mechanism
    (``guardkit task create "..." --prefix REV --task-type review``) must emit a
    review-shaped task file that /task-review's Execution Protocol accepts
    without editing (``task_type: review`` frontmatter + a "Review Scope"
    section), while the default remains byte-compatible ``task_type: feature``.

  * Doc grep-able signatures — the command markdowns are LLM-executed prose, so
    these assertions are the loud-fail guard (test_command_anchor_hygiene.py
    precedent) that (a) Phase 0 and its no-silent-fallback guard stay in
    task-review.md, and (b) the ID-form invocation contract /feature-plan pins
    (scope §4) survives any future edit.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.cli.task import VALID_TASK_TYPES, create_task

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMANDS = _REPO_ROOT / "installer" / "core" / "commands"


class TestCreateTaskTaskType:
    """create_task grows a task_type parameter for the Phase 0 ad-hoc entry."""

    def test_default_task_type_remains_feature(self, tmp_path: Path) -> None:
        task_path = create_task("Add user authentication", repo_root=tmp_path)
        content = task_path.read_text(encoding="utf-8")
        assert "task_type: feature" in content
        assert task_path.parent == tmp_path / "tasks" / "backlog"
        # Default body shape unchanged (regression guard for existing callers).
        assert "## Implementation Notes" in content
        assert "## Review Scope" not in content

    def test_review_task_type_emits_review_shaped_body(self, tmp_path: Path) -> None:
        description = "auth redirect loops after logout"
        task_path = create_task(
            description, prefix="REV", task_type="review", repo_root=tmp_path
        )
        content = task_path.read_text(encoding="utf-8")
        assert "task_type: review" in content
        # /task-review errors on a missing "Review Scope" section; Phase 0
        # relies on the description being seeded there (scope §7 AC-1).
        assert "## Review Scope" in content
        assert description in content
        assert task_path.name.startswith("TASK-REV-")
        assert task_path.parent == tmp_path / "tasks" / "backlog"

    def test_review_body_carries_no_implementation_section(self, tmp_path: Path) -> None:
        task_path = create_task(
            "should the exporter batch or stream?",
            task_type="review",
            repo_root=tmp_path,
        )
        content = task_path.read_text(encoding="utf-8")
        assert "## Implementation Notes" not in content
        assert "no implementation" in content

    def test_task_type_is_case_insensitive(self, tmp_path: Path) -> None:
        task_path = create_task("Review the cache layer", task_type="REVIEW", repo_root=tmp_path)
        assert "task_type: review" in task_path.read_text(encoding="utf-8")

    def test_invalid_task_type_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid task_type"):
            create_task("Some task", task_type="not-a-type", repo_root=tmp_path)

    def test_valid_task_types_mirror_task_create_doc(self) -> None:
        """VALID_TASK_TYPES must stay in sync with task-create.md's documented set."""
        doc = (_COMMANDS / "task-create.md").read_text(encoding="utf-8")
        for task_type in VALID_TASK_TYPES:
            assert f"`{task_type}`" in doc, (
                f"task_type '{task_type}' not documented in task-create.md"
            )


class TestAdhocEntryDocSignatures:
    """Grep-able-signature guards over the LLM-executed command specs."""

    @pytest.fixture(scope="class")
    def task_review_doc(self) -> str:
        return (_COMMANDS / "task-review.md").read_text(encoding="utf-8")

    def test_phase_0_exists(self, task_review_doc: str) -> None:
        assert "### Phase 0: Ad-Hoc Task Creation (Description Form Only)" in task_review_doc

    def test_phase_0_uses_deterministic_cli_creation(self, task_review_doc: str) -> None:
        assert (
            'guardkit task create "{description}" --prefix REV --task-type review'
            in task_review_doc
        )

    def test_no_silent_fallback_guard_present(self, task_review_doc: str) -> None:
        assert "Never reinterpret a missing ID as a description" in task_review_doc

    def test_id_form_invocation_still_documented(self, task_review_doc: str) -> None:
        """The ID form is the contract /feature-plan pins (scope §4) — must survive."""
        assert "/task-review TASK-XXX" in task_review_doc

    def test_feature_plan_pinned_invocation_untouched(self) -> None:
        """feature-plan's internal invocation shape must keep resolving (scope §4).

        feature-plan.md is sha256-pinned; this asserts the *other* side of the
        seam — that the invocation form it hard-codes still exists there.
        """
        doc = (_COMMANDS / "feature-plan.md").read_text(encoding="utf-8")
        assert "--mode=decision --depth=standard" in doc

    def test_task_create_banner_mentions_shortcut(self) -> None:
        doc = (_COMMANDS / "task-create.md").read_text(encoding="utf-8")
        assert '/task-review "description"' in doc
