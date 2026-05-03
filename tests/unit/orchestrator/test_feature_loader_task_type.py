"""FeatureLoader awareness of the OPERATOR_HANDOFF task_type (TASK-FPTC-002).

Pins AC-FPTC-002-04 and AC-FPTC-002-05: a fixture task file with
``task_type: operator_handoff`` in its YAML frontmatter must pass
``FeatureLoader._validate_task_type_in_file`` and surface no
task_type-related error from ``FeatureLoader.validate_feature``.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureLoader,
    FeatureOrchestration,
    FeatureTask,
)


def _write_task_md(
    repo_root: Path,
    rel_path: str,
    task_id: str,
    task_type: str,
) -> Path:
    """Write a minimal task markdown file with the given ``task_type`` frontmatter."""
    task_file = repo_root / rel_path
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        dedent(
            f"""\
            ---
            id: {task_id}
            title: "Operator handoff fixture"
            status: backlog
            task_type: {task_type}
            ---

            # Task: Operator handoff fixture
            """
        )
    )
    return task_file


class TestValidateTaskTypeInFileOperatorHandoff:
    """AC-FPTC-002-04: ``_validate_task_type_in_file`` accepts operator_handoff."""

    def test_operator_handoff_returns_none(self, tmp_path: Path) -> None:
        """A task file with ``task_type: operator_handoff`` returns None (no error)."""
        task_file = _write_task_md(
            tmp_path,
            "tasks/in_progress/TASK-FPTC-OP1.md",
            "TASK-FPTC-OP1",
            "operator_handoff",
        )

        result = FeatureLoader._validate_task_type_in_file(
            "TASK-FPTC-OP1", task_file
        )

        assert result is None

    def test_unknown_task_type_still_errors(self, tmp_path: Path) -> None:
        """Sanity: the validator still rejects truly unknown values.

        Pins that adding OPERATOR_HANDOFF didn't accidentally relax the
        validator into accepting arbitrary strings.
        """
        task_file = _write_task_md(
            tmp_path,
            "tasks/in_progress/TASK-FPTC-OP2.md",
            "TASK-FPTC-OP2",
            "banana",
        )

        result = FeatureLoader._validate_task_type_in_file(
            "TASK-FPTC-OP2", task_file
        )

        assert result is not None
        assert "banana" in result
        assert "operator_handoff" in result  # listed in valid values


class TestValidateFeatureOperatorHandoff:
    """AC-FPTC-002-05: ``validate_feature`` surfaces no task_type error."""

    def test_validate_feature_accepts_operator_handoff_task(
        self, tmp_path: Path
    ) -> None:
        """End-to-end: a Feature whose only task carries ``task_type: operator_handoff``
        validates without producing a task_type error."""
        rel_path = "tasks/in_progress/TASK-FPTC-OP3.md"
        _write_task_md(
            tmp_path, rel_path, "TASK-FPTC-OP3", "operator_handoff"
        )

        feature = Feature(
            id="FEAT-FPTC-OP",
            name="Operator handoff fixture feature",
            description="Pins TASK-FPTC-002 AC-05.",
            created="2026-05-03T12:00:00Z",
            complexity=3,
            estimated_tasks=1,
            tasks=[
                FeatureTask(
                    id="TASK-FPTC-OP3",
                    name="Operator handoff fixture task",
                    file_path=Path(rel_path),
                    complexity=3,
                    estimated_minutes=30,
                )
            ],
            orchestration=FeatureOrchestration(
                parallel_groups=[["TASK-FPTC-OP3"]],
                estimated_duration_minutes=30,
                recommended_parallel=1,
            ),
        )

        errors = FeatureLoader.validate_feature(feature, repo_root=tmp_path)

        # The only relevant assertion is the absence of any task_type
        # error for our task; other unrelated errors (none expected here)
        # would not invalidate the AC.
        task_type_errors = [
            e for e in errors if "TASK-FPTC-OP3" in e and "task_type" in e
        ]
        assert task_type_errors == [], (
            f"Unexpected task_type errors for operator_handoff: {task_type_errors}"
        )
