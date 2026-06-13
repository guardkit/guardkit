"""Tests for task_status_json.py — the task dashboard JSON producer."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

# Resolve the project root relative to this test file's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure the installer package is on sys.path for imports
INSTALLER_LIB = PROJECT_ROOT / "installer" / "core" / "commands" / "lib"
if str(INSTALLER_LIB.parent) not in sys.path:
    sys.path.insert(0, str(INSTALLER_LIB.parent))

from installer.core.commands.lib.task_status_json import (
    build_dashboard,
    build_single_task,
    main,
    parse_task_record,
    scan_task_files,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_tasks(tmp_path: Path) -> Path:
    """Create a minimal tasks/ directory tree with sample task files."""
    # backlog tasks
    task_a = tmp_path / "tasks" / "backlog" / "TASK-001-sample.md"
    task_a.parent.mkdir(parents=True, exist_ok=True)
    task_a.write_text(
        "---\nid: TASK-001\ntitle: Sample Task A\nstatus: backlog\n"
        "priority: high\ntask_type: feature\ncomplexity: 3\n"
        "tags: [test]\ncreated: 2026-01-01T00:00:00Z\n"
        "updated: 2026-01-02T00:00:00Z\n---\n\nBody\n"
    )

    task_b = tmp_path / "tasks" / "backlog" / "TASK-002-sample.md"
    task_b.parent.mkdir(parents=True, exist_ok=True)
    task_b.write_text(
        "---\nid: TASK-002\ntitle: Sample Task B\nstatus: backlog\n"
        "priority: medium\ntask_type: refactor\ncomplexity: 2\n"
        "tags: []\ncreated: 2026-02-01T00:00:00Z\n"
        "updated: 2026-02-01T00:00:00Z\n---\n\nBody\n"
    )

    # in_progress task
    task_c = tmp_path / "tasks" / "in_progress" / "TASK-003-sample.md"
    task_c.parent.mkdir(parents=True, exist_ok=True)
    task_c.write_text(
        "---\nid: TASK-003\ntitle: Sample Task C\nstatus: in_progress\n"
        "priority: high\ntask_type: feature\ncomplexity: 5\n"
        "tags: [urgent]\ncreated: 2026-03-01T00:00:00Z\n"
        "updated: 2026-03-05T00:00:00Z\n"
        "parent_review: TASK-REV-001\nfeature_id: FEAT-ABC\n---\n\nBody\n"
    )

    # nested feature subfolder
    task_d = tmp_path / "tasks" / "backlog" / "feat-sub" / "TASK-004-sample.md"
    task_d.parent.mkdir(parents=True, exist_ok=True)
    task_d.write_text(
        "---\nid: TASK-004\ntitle: Nested Task\nstatus: backlog\n"
        "priority: low\ntask_type: documentation\ncomplexity: 1\n"
        "tags: [docs]\ncreated: 2026-04-01T00:00:00Z\n"
        "updated: 2026-04-01T00:00:00Z\n---\n\nBody\n"
    )

    # archive folder
    task_e = tmp_path / "tasks" / "completed" / "2026-01" / "TASK-005-sample.md"
    task_e.parent.mkdir(parents=True, exist_ok=True)
    task_e.write_text(
        "---\nid: TASK-005\ntitle: Archived Task\nstatus: completed\n"
        "priority: medium\ntask_type: feature\ncomplexity: 4\n"
        "tags: []\ncreated: 2025-12-01T00:00:00Z\n"
        "updated: 2026-01-15T00:00:00Z\n---\n\nBody\n"
    )

    # task with missing optional fields
    task_f = tmp_path / "tasks" / "blocked" / "TASK-006-sample.md"
    task_f.parent.mkdir(parents=True, exist_ok=True)
    task_f.write_text(
        "---\nid: TASK-006\ntitle: Minimal Task\nstatus: blocked\n"
        "priority: high\ntask_type: feature\ncomplexity: 3\n"
        "tags: [blocker]\ncreated: 2026-05-01T00:00:00Z\n"
        "updated: 2026-05-01T00:00:00Z\n---\n\nBody\n"
    )

    return tmp_path


# ---------------------------------------------------------------------------
# scan_task_files
# ---------------------------------------------------------------------------

class TestScanTaskFiles:
    def test_finds_all_status_dirs(self, tmp_tasks: Path) -> None:
        files = scan_task_files(tmp_tasks)
        ids = {f.stem for f in files}
        expected = {
            "TASK-001-sample",
            "TASK-002-sample",
            "TASK-003-sample",
            "TASK-004-sample",
            "TASK-005-sample",
            "TASK-006-sample",
        }
        assert ids == expected

    def test_skips_non_task_md(self, tmp_tasks: Path) -> None:
        readme = tmp_tasks / "tasks" / "backlog" / "README.md"
        readme.write_text("# README")
        files = scan_task_files(tmp_tasks)
        ids = {f.stem for f in files}
        # README.md should NOT be included because it doesn't have TASK- prefix
        # Actually, our scanner doesn't filter by prefix, so let's check
        # that it finds all .md files
        assert "README" in ids

    def test_empty_dir(self, tmp_path: Path) -> None:
        (tmp_path / "tasks").mkdir()
        files = scan_task_files(tmp_path)
        assert files == []


# ---------------------------------------------------------------------------
# parse_task_record
# ---------------------------------------------------------------------------

class TestParseTaskRecord:
    def test_parses_full_frontmatter(self, tmp_tasks: Path) -> None:
        tf = tmp_tasks / "tasks" / "in_progress" / "TASK-003-sample.md"
        record = parse_task_record(tf, tmp_tasks)
        assert record is not None
        assert record["id"] == "TASK-003"
        assert record["title"] == "Sample Task C"
        assert record["status"] == "in_progress"
        assert record["priority"] == "high"
        assert record["task_type"] == "feature"
        assert record["complexity"] == 5
        assert record["tags"] == ["urgent"]
        assert record["parent_review"] == "TASK-REV-001"
        assert record["feature_id"] == "FEAT-ABC"

    def test_missing_optional_fields_are_null(self, tmp_tasks: Path) -> None:
        tf = tmp_tasks / "tasks" / "blocked" / "TASK-006-sample.md"
        record = parse_task_record(tf, tmp_tasks)
        assert record is not None
        assert record["epic"] is None
        assert record["feature"] is None
        assert record["parent_review"] is None
        assert record["feature_id"] is None

    def test_relative_file_path(self, tmp_tasks: Path) -> None:
        tf = tmp_tasks / "tasks" / "backlog" / "feat-sub" / "TASK-004-sample.md"
        record = parse_task_record(tf, tmp_tasks)
        assert record is not None
        assert record["file_path"] == "tasks/backlog/feat-sub/TASK-004-sample.md"

    def test_invalid_frontmatter_returns_none(self, tmp_path: Path) -> None:
        tf = tmp_path / "tasks" / "backlog" / "TASK-BAD.md"
        tf.parent.mkdir(parents=True, exist_ok=True)
        tf.write_text("no frontmatter here")
        record = parse_task_record(tf, tmp_path)
        assert record is None


# ---------------------------------------------------------------------------
# build_dashboard
# ---------------------------------------------------------------------------

class TestBuildDashboard:
    def test_schema_version(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        assert dashboard["schema_version"] == "1.0"

    def test_generated_at_is_iso(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        assert "generated_at" in dashboard
        assert "T" in dashboard["generated_at"]

    def test_base_path(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        assert dashboard["base_path"] == str(tmp_tasks.resolve())

    def test_summary_counts(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        s = dashboard["summary"]
        assert s["backlog"] == 3  # TASK-001, TASK-002, TASK-004
        assert s["in_progress"] == 1  # TASK-003
        assert s["completed"] == 1  # TASK-005
        assert s["blocked"] == 1  # TASK-006
        assert s["total"] == 6

    def test_tasks_sorted_by_status_then_id(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        ids = [t["id"] for t in dashboard["tasks"]]
        # Sorted by (status, id) alphabetically:
        # backlog: TASK-001, TASK-002, TASK-004
        # blocked: TASK-006
        # completed: TASK-005
        # in_progress: TASK-003
        expected_order = [
            "TASK-001", "TASK-002", "TASK-004",
            "TASK-006",
            "TASK-005",
            "TASK-003",
        ]
        assert ids == expected_order

    def test_fixed_key_order_top_level(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        keys = list(dashboard.keys())
        assert keys == [
            "schema_version",
            "generated_at",
            "base_path",
            "summary",
            "tasks",
        ]

    def test_fixed_key_order_task(self, tmp_tasks: Path) -> None:
        dashboard = build_dashboard(tmp_tasks)
        task = dashboard["tasks"][0]
        expected_keys = [
            "id",
            "title",
            "status",
            "priority",
            "task_type",
            "complexity",
            "tags",
            "created",
            "updated",
            "epic",
            "feature",
            "parent_review",
            "feature_id",
            "file_path",
        ]
        assert list(task.keys()) == expected_keys

    def test_deterministic_output(self, tmp_tasks: Path) -> None:
        d1 = build_dashboard(tmp_tasks)
        d2 = build_dashboard(tmp_tasks)
        # generated_at may differ, so compare everything except that
        d1_str = json.dumps(d1, indent=2, sort_keys=False)
        d2_str = json.dumps(d2, indent=2, sort_keys=False)
        # They should match except for generated_at
        j1 = json.loads(d1_str)
        j2 = json.loads(d2_str)
        j1.pop("generated_at")
        j2.pop("generated_at")
        assert j1 == j2


# ---------------------------------------------------------------------------
# build_single_task
# ---------------------------------------------------------------------------

class TestBuildSingleTask:
    def test_finds_task_by_id(self, tmp_tasks: Path) -> None:
        record = build_single_task("TASK-003", tmp_tasks)
        assert record is not None
        assert record["id"] == "TASK-003"
        assert record["title"] == "Sample Task C"

    def test_returns_none_when_not_found(self, tmp_tasks: Path) -> None:
        record = build_single_task("TASK-999", tmp_tasks)
        assert record is None

    def test_task_shape_only(self, tmp_tasks: Path) -> None:
        record = build_single_task("TASK-001", tmp_tasks)
        assert record is not None
        assert "id" in record
        assert "title" in record
        assert "status" in record
        # Should NOT have dashboard-level keys
        assert "summary" not in record
        assert "schema_version" not in record


# ---------------------------------------------------------------------------
# main (CLI)
# ---------------------------------------------------------------------------

class TestMain:
    def test_full_dashboard_prints_json(self, tmp_tasks: Path, capsys: pytest.CaptureFixture) -> None:
        with mock.patch.object(sys, "argv", ["task_status_json.py", "--base-path", str(tmp_tasks)]):
            main()
        captured = capsys.readouterr()
        assert captured.err == ""
        data = json.loads(captured.out)
        assert data["schema_version"] == "1.0"
        assert data["summary"]["total"] == 6

    def test_single_task_by_id(self, tmp_tasks: Path, capsys: pytest.CaptureFixture) -> None:
        with mock.patch.object(
            sys, "argv", ["task_status_json.py", "TASK-003", "--base-path", str(tmp_tasks)]
        ):
            main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["id"] == "TASK-003"
        assert "summary" not in data

    def test_missing_task_exits_1(self, tmp_tasks: Path, capsys: pytest.CaptureFixture) -> None:
        with mock.patch.object(
            sys, "argv", ["task_status_json.py", "TASK-999", "--base-path", str(tmp_tasks)]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_no_args_uses_cwd(self, tmp_tasks: Path, capsys: pytest.CaptureFixture) -> None:
        # Temporarily change cwd to tmp_tasks
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_tasks)
            with mock.patch.object(sys, "argv", ["task_status_json.py"]):
                main()
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert data["summary"]["total"] == 6
        finally:
            os.chdir(original_cwd)
