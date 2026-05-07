"""Tests for `guardkit.orchestrator.preflight` (TASK-GK-PR-001).

Coverage Target: >=85% line, >=75% branch.

The fixtures here are **synthetic and target-repo agnostic** — no forge
paths, no FEAT-PEBR-shaped acceptance criteria. The discovery happened
in a forge feature run but the bug class fires on any guardkit-managed
feature in any target repo, so the regression suite mirrors that
generality.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List

import pytest

from guardkit.orchestrator.feature_loader import (
    Feature,
    FeatureOrchestration,
    FeatureTask,
)
from guardkit.orchestrator.preflight import (
    PreflightTypo,
    PreflightTypoError,
    preflight_validate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_task(
    repo_root: Path,
    task_id: str,
    modify_paths: List[str] | None = None,
    create_paths: List[str] | None = None,
) -> Path:
    """Write a synthetic guardkit task markdown file under
    ``repo_root/tasks/backlog/{task_id}.md`` and return its repo-relative
    path (suitable for ``FeatureTask.file_path``)."""
    backlog = repo_root / "tasks" / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    body_lines = [
        "---",
        f"id: {task_id}",
        "title: Synthetic task for preflight tests",
        "status: backlog",
        "---",
        "",
        f"# Task: {task_id}",
        "",
        "## Description",
        "",
        "Synthetic.",
        "",
    ]
    if create_paths:
        body_lines.append("## Files to Create")
        body_lines.append("")
        for p in create_paths:
            body_lines.append(f"- `{p}`")
        body_lines.append("")
    if modify_paths:
        body_lines.append("## Files to Modify")
        body_lines.append("")
        for p in modify_paths:
            body_lines.append(f"- `{p}`")
        body_lines.append("")
    file_path = backlog / f"{task_id}.md"
    file_path.write_text("\n".join(body_lines), encoding="utf-8")
    return Path("tasks/backlog") / f"{task_id}.md"


def _make_task(task_id: str, file_path: Path) -> FeatureTask:
    return FeatureTask(
        id=task_id,
        name=task_id,
        file_path=file_path,
        complexity=3,
    )


def _make_feature(tasks: List[FeatureTask], preflight_strict: bool = False) -> Feature:
    return Feature(
        id="FEAT-PR-TEST",
        name="Preflight Test Feature",
        description="synthetic preflight regression",
        tasks=tasks,
        orchestration=FeatureOrchestration(
            parallel_groups=[[t.id for t in tasks]],
        ),
        preflight_strict=preflight_strict,
    )


def _seed_real_source(repo_root: Path, rel_path: str) -> Path:
    """Write an empty source file at ``repo_root/rel_path``."""
    target = repo_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# real source\n", encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# AC-5: Modify-axis typo with fuzzy suggestions
# ---------------------------------------------------------------------------


class TestModifyPathExistenceCheck:
    """AC-5: synthetic single-typo regression with strict + non-strict modes."""

    def test_strict_raises_with_suggestion(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """preflight_strict=True raises PreflightTypoError; the exception
        carries one PreflightTypo whose declared_path is the typo and
        whose suggestions list includes the real on-disk file."""
        repo_root = tmp_path
        # On-disk: src/sample/real.py exists
        _seed_real_source(repo_root, "src/sample/real.py")
        # Task declares src/sample/typo.py (note different basename)
        rel = _write_task(
            repo_root,
            "TASK-PR-A",
            modify_paths=["src/sample/typo.py"],
        )
        feature = _make_feature([_make_task("TASK-PR-A", rel)], preflight_strict=True)

        with pytest.raises(PreflightTypoError) as excinfo:
            preflight_validate(
                feature, repo_root=repo_root, worktree_path=None, strict=True
            )

        assert len(excinfo.value.typos) == 1
        typo = excinfo.value.typos[0]
        assert typo.task_id == "TASK-PR-A"
        assert typo.declared_path == "src/sample/typo.py"
        assert typo.kind == "modify"
        assert "src/sample/real.py" in typo.suggestions
        # Line number is 1-indexed and points at the body bullet
        assert typo.line >= 1

    def test_nonstrict_logs_warning_and_returns_typos(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """preflight_strict=False emits one WARNING line naming the task
        and at least one suggestion; returns the typo list; does NOT
        raise — so wave-1 dispatch can proceed."""
        repo_root = tmp_path
        _seed_real_source(repo_root, "src/sample/real.py")
        rel = _write_task(
            repo_root,
            "TASK-PR-B",
            modify_paths=["src/sample/typo.py"],
        )
        feature = _make_feature(
            [_make_task("TASK-PR-B", rel)], preflight_strict=False
        )

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.preflight")
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )

        assert len(typos) == 1
        assert typos[0].declared_path == "src/sample/typo.py"
        # At least one warning record names the task and a suggestion
        warning_records = [
            rec for rec in caplog.records if rec.levelno == logging.WARNING
        ]
        assert any("TASK-PR-B" in rec.getMessage() for rec in warning_records)
        assert any(
            "src/sample/real.py" in rec.getMessage() for rec in warning_records
        )

    def test_modify_path_that_exists_under_repo_root_passes(
        self, tmp_path: Path
    ) -> None:
        """A declared modify path that exists under repo_root produces
        no typo entry."""
        repo_root = tmp_path
        _seed_real_source(repo_root, "src/sample/real.py")
        rel = _write_task(
            repo_root,
            "TASK-PR-C",
            modify_paths=["src/sample/real.py"],
        )
        feature = _make_feature([_make_task("TASK-PR-C", rel)])
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )
        assert typos == []

    def test_modify_path_only_in_worktree_passes(self, tmp_path: Path) -> None:
        """A declared modify path that exists only under worktree_path
        (not under repo_root) is accepted — the worktree fallback is
        intentional for tasks that target files created by an earlier
        wave."""
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "wt"
        repo_root.mkdir()
        _seed_real_source(worktree, "src/sample/wave1_artifact.py")
        rel = _write_task(
            repo_root,
            "TASK-PR-D",
            modify_paths=["src/sample/wave1_artifact.py"],
        )
        feature = _make_feature([_make_task("TASK-PR-D", rel)])
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=worktree, strict=False
        )
        assert typos == []


# ---------------------------------------------------------------------------
# AC-3: Create-axis warnings, not errors
# ---------------------------------------------------------------------------


class TestCreateAxisWarning:
    """AC-3: a declared create path that already exists logs a WARNING
    but never adds to the typo list and never raises."""

    def test_create_path_that_already_exists_warns_does_not_fail(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo_root = tmp_path
        # File already exists on disk (preserved-worktree re-run scenario)
        _seed_real_source(repo_root, "src/sample/already_there.py")
        rel = _write_task(
            repo_root,
            "TASK-PR-E",
            create_paths=["src/sample/already_there.py"],
        )
        feature = _make_feature(
            [_make_task("TASK-PR-E", rel)], preflight_strict=True
        )

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.preflight")
        # Strict mode is irrelevant for create-axis — should still not raise
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=True
        )
        assert typos == []
        warnings = [rec for rec in caplog.records if rec.levelno == logging.WARNING]
        assert any(
            "TASK-PR-E" in rec.getMessage() and "already_there.py" in rec.getMessage()
            for rec in warnings
        )

    def test_create_path_that_does_not_exist_is_silent(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo_root = tmp_path
        rel = _write_task(
            repo_root,
            "TASK-PR-F",
            create_paths=["src/sample/will_be_created.py"],
        )
        feature = _make_feature([_make_task("TASK-PR-F", rel)])

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.preflight")
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )
        assert typos == []
        # No WARNING records for this task
        warnings = [
            rec
            for rec in caplog.records
            if rec.levelno == logging.WARNING and "TASK-PR-F" in rec.getMessage()
        ]
        assert warnings == []


# ---------------------------------------------------------------------------
# AC-7: Multi-typo, multi-task integration
# ---------------------------------------------------------------------------


class TestMultiTypoMultiTask:
    """AC-7: synthetic feature with three tasks (A: 2 typos, B: 1 typo,
    C: clean) emits 3 distinct WARNINGs in non-strict mode and returns
    a typo list of length 3. Task C produces no output."""

    def test_three_tasks_two_with_typos(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo_root = tmp_path
        _seed_real_source(repo_root, "src/a/real_one.py")
        _seed_real_source(repo_root, "src/a/real_two.py")
        _seed_real_source(repo_root, "src/b/real.py")
        _seed_real_source(repo_root, "src/c/real.py")

        rel_a = _write_task(
            repo_root,
            "TASK-PR-A",
            modify_paths=["src/a/typo_one.py", "src/a/typo_two.py"],
        )
        rel_b = _write_task(
            repo_root,
            "TASK-PR-B",
            modify_paths=["src/b/typo.py"],
        )
        rel_c = _write_task(
            repo_root,
            "TASK-PR-C",
            modify_paths=["src/c/real.py"],
        )
        feature = _make_feature(
            [
                _make_task("TASK-PR-A", rel_a),
                _make_task("TASK-PR-B", rel_b),
                _make_task("TASK-PR-C", rel_c),
            ]
        )

        caplog.set_level(logging.WARNING, logger="guardkit.orchestrator.preflight")
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )

        assert len(typos) == 3
        task_ids = {t.task_id for t in typos}
        assert task_ids == {"TASK-PR-A", "TASK-PR-B"}
        a_typos = [t for t in typos if t.task_id == "TASK-PR-A"]
        b_typos = [t for t in typos if t.task_id == "TASK-PR-B"]
        assert len(a_typos) == 2
        assert len(b_typos) == 1

        # Three distinct WARNING lines (one per typo); none for task C
        warning_msgs = [
            rec.getMessage()
            for rec in caplog.records
            if rec.levelno == logging.WARNING
            and "Files to Modify" in rec.getMessage()
        ]
        assert len(warning_msgs) == 3
        assert not any("TASK-PR-C" in msg for msg in warning_msgs)


# ---------------------------------------------------------------------------
# AC-6: Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    """AC-6: preflight completes in <1s for ≤50 tasks against a synthetic
    on-disk tree of ~500 .py files."""

    def test_fifty_tasks_under_one_second(self, tmp_path: Path) -> None:
        repo_root = tmp_path
        # Seed ~500 .py files across 50 directories
        for d in range(50):
            for f in range(10):
                _seed_real_source(repo_root, f"src/pkg{d}/mod{f}.py")

        # 50 tasks, each declares 1 modify path against a real file and
        # 1 against a typo (so we exercise both lookup branches and
        # difflib for half the declarations).
        tasks: List[FeatureTask] = []
        for i in range(50):
            rel = _write_task(
                repo_root,
                f"TASK-PERF-{i:03d}",
                modify_paths=[f"src/pkg{i}/mod0.py", f"src/pkg{i}/typo.py"],
            )
            tasks.append(_make_task(f"TASK-PERF-{i:03d}", rel))
        feature = _make_feature(tasks)

        start = time.perf_counter()
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )
        elapsed = time.perf_counter() - start
        # 50 typos (one per task), all detected
        assert len(typos) == 50
        assert elapsed < 1.0, f"preflight took {elapsed:.3f}s; budget 1.0s"


# ---------------------------------------------------------------------------
# Direct construction / formatting
# ---------------------------------------------------------------------------


class TestPreflightTypoErrorFormat:
    """Smoke test for PreflightTypoError formatting."""

    def test_format_with_suggestions(self) -> None:
        typo = PreflightTypo(
            task_id="TASK-X",
            line=42,
            declared_path="src/x/typo.py",
            suggestions=["src/x/real.py"],
            kind="modify",
        )
        err = PreflightTypoError([typo])
        msg = str(err)
        assert "TASK-X" in msg
        assert "src/x/typo.py" in msg
        assert "src/x/real.py" in msg
        assert "line 42" in msg

    def test_format_without_suggestions(self) -> None:
        typo = PreflightTypo(
            task_id="TASK-Y",
            line=7,
            declared_path="src/y/orphan.py",
            suggestions=[],
            kind="modify",
        )
        err = PreflightTypoError([typo])
        msg = str(err)
        assert "no close matches found on disk" in msg


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Defensive / edge-case behaviour."""

    def test_missing_task_file_is_skipped(self, tmp_path: Path) -> None:
        """If a task's file_path doesn't exist on disk, skip silently —
        feature validation already enforces task-file existence; we
        don't double-report."""
        repo_root = tmp_path
        feature = _make_feature(
            [
                FeatureTask(
                    id="TASK-MISSING",
                    name="missing",
                    file_path=Path("tasks/backlog/does-not-exist.md"),
                    complexity=3,
                )
            ]
        )
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )
        assert typos == []

    def test_no_files_to_modify_section(self, tmp_path: Path) -> None:
        """Tasks without a `## Files to Modify` section produce no typos."""
        repo_root = tmp_path
        backlog = repo_root / "tasks" / "backlog"
        backlog.mkdir(parents=True)
        (backlog / "TASK-NO-MOD.md").write_text(
            "---\nid: TASK-NO-MOD\n---\n# Task\n## Description\nNo modify section.\n",
            encoding="utf-8",
        )
        feature = _make_feature(
            [_make_task("TASK-NO-MOD", Path("tasks/backlog/TASK-NO-MOD.md"))]
        )
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )
        assert typos == []

    def test_path_with_unindexed_extension_is_skipped(self, tmp_path: Path) -> None:
        """Bullets pointing at files whose extension we don't index
        (e.g. `.md`, `.yaml`) are skipped — we only validate code
        files via this preflight."""
        repo_root = tmp_path
        rel = _write_task(
            repo_root,
            "TASK-MD",
            modify_paths=["docs/some-non-existent.md"],
        )
        feature = _make_feature([_make_task("TASK-MD", rel)])
        typos = preflight_validate(
            feature, repo_root=repo_root, worktree_path=None, strict=False
        )
        assert typos == []

    def test_default_preflight_strict_is_false(self, tmp_path: Path) -> None:
        """Adding a feature yaml without ``preflight_strict`` defaults
        to False — backward compatibility for existing yamls."""
        feature = Feature(id="FEAT-DEF", name="default")
        assert feature.preflight_strict is False
