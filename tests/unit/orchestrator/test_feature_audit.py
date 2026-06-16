import yaml
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_audit import (
    FeatureAuditRow,
    audit_features,
    infer_status_for_feature,
)


def write_feature_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def create_completed_task(repo_root: Path, task_id: str, name: str = "example"):
    completed_dir = repo_root / "tasks" / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    file_path = completed_dir / f"{task_id}_{name}.md"
    file_path.write_text(f"# {task_id}\n", encoding="utf-8")
    return file_path


def test_all_tasks_completed_and_stale(tmp_path: Path):
    # Feature declares status planned but all tasks are completed => stale
    repo = tmp_path
    feature_yaml = repo / ".guardkit" / "features" / "feat1.yaml"
    write_feature_yaml(
        feature_yaml,
        {
            "id": "FEAT-001",
            "status": "planned",
            "tasks": ["TASK-001", "TASK-002"],
        },
    )
    create_completed_task(repo, "TASK-001")
    create_completed_task(repo, "TASK-002")
    rows = audit_features(repo)
    assert len(rows) == 1
    row = rows[0]
    assert row.feature_id == "FEAT-001"
    assert row.declared_status == "planned"
    assert row.inferred_status == "completed"
    assert row.is_stale is True
    assert row.tasks_total == 2
    assert row.tasks_completed == 2
    assert row.tasks_pending == 0


def test_none_tasks_completed_not_stale(tmp_path: Path):
    repo = tmp_path
    feature_yaml = repo / ".guardkit" / "features" / "feat2.yaml"
    write_feature_yaml(
        feature_yaml,
        {
            "id": "FEAT-002",
            "status": "planned",
            "tasks": ["TASK-003"],
        },
    )
    # No completed task files created
    rows = audit_features(repo)
    row = rows[0]
    assert row.inferred_status == "planned"
    assert row.is_stale is False
    assert row.tasks_total == 1
    assert row.tasks_completed == 0
    assert row.tasks_pending == 1


def test_mixed_tasks_in_progress(tmp_path: Path):
    repo = tmp_path
    feature_yaml = repo / ".guardkit" / "features" / "feat3.yaml"
    write_feature_yaml(
        feature_yaml,
        {
            "id": "FEAT-003",
            "status": "in_progress",
            "tasks": ["TASK-004", "TASK-005"],
        },
    )
    create_completed_task(repo, "TASK-004")
    # TASK-005 not completed
    rows = audit_features(repo)
    row = rows[0]
    assert row.inferred_status == "in_progress"
    assert row.is_stale is False  # declared matches inferred
    assert row.tasks_total == 2
    assert row.tasks_completed == 1
    assert row.tasks_pending == 1


def test_malformed_yaml_is_skipped(tmp_path: Path):
    repo = tmp_path
    # Write malformed YAML (just a string, not a mapping)
    bad_yaml = repo / ".guardkit" / "features" / "bad.yaml"
    bad_yaml.parent.mkdir(parents=True, exist_ok=True)
    bad_yaml.write_text("just a string not a dict", encoding="utf-8")
    # Valid feature for control
    good_yaml = repo / ".guardkit" / "features" / "good.yaml"
    write_feature_yaml(
        good_yaml,
        {"id": "FEAT-004", "status": "planned", "tasks": []},
    )
    rows = audit_features(repo)
    # Only the good feature should be present
    assert len(rows) == 1
    assert rows[0].feature_id == "FEAT-004"


def test_infer_status_function_directly(tmp_path: Path):
    repo = tmp_path
    # Feature dict with two tasks, one completed
    feature = {"tasks": ["TASK-006", "TASK-007"]}
    create_completed_task(repo, "TASK-006")
    status = infer_status_for_feature(feature, repo)
    assert status == "in_progress"
    # All completed
    create_completed_task(repo, "TASK-007")
    status = infer_status_for_feature(feature, repo)
    assert status == "completed"
    # None completed
    # Remove completed files
    for p in (repo / "tasks" / "completed").glob("*" ):
        p.unlink()
    status = infer_status_for_feature(feature, repo)
    assert status == "planned"


# ---------------------------------------------------------------------------
# Regression: the real feature-YAML schema declares ``tasks`` as a list of
# MAPPINGS ({"id": ..., "name": ..., "file_path": ...}), not bare id strings.
# The original implementation iterated ``for task_id in tasks`` and globbed
# ``f"*{task_id}*.md"``, which stringified each dict and matched nothing — so
# every real feature inferred "planned" (0 completed) regardless of disk state.
# These tests pin the dict-schema path. (FEAT-FAUD deliverable fix, 2026-06-16.)
# ---------------------------------------------------------------------------


def _dict_task(task_id: str) -> dict:
    return {
        "id": task_id,
        "name": f"do {task_id}",
        "file_path": f"tasks/backlog/{task_id}.md",
        "status": "pending",
    }


def test_real_dict_task_schema_detects_completion(tmp_path: Path):
    repo = tmp_path
    feature_yaml = repo / ".guardkit" / "features" / "feat_real.yaml"
    write_feature_yaml(
        feature_yaml,
        {
            "id": "FEAT-REAL",
            "status": "planned",
            "tasks": [_dict_task("TASK-RD-001"), _dict_task("TASK-RD-002")],
        },
    )
    # Completed task files live under nested YYYY-MM dirs in the real repo;
    # rglob must find them recursively.
    nested = repo / "tasks" / "completed" / "2026-06"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "TASK-RD-001-auditor.md").write_text("# done\n", encoding="utf-8")
    (nested / "TASK-RD-002-cli.md").write_text("# done\n", encoding="utf-8")

    rows = audit_features(repo)
    assert len(rows) == 1
    row = rows[0]
    assert row.tasks_total == 2
    assert row.tasks_completed == 2  # would be 0 under the dict-vs-string bug
    assert row.inferred_status == "completed"
    assert row.is_stale is True  # declared planned != inferred completed


def test_infer_status_with_dict_tasks(tmp_path: Path):
    repo = tmp_path
    feature = {"tasks": [_dict_task("TASK-RD-003"), _dict_task("TASK-RD-004")]}
    create_completed_task(repo, "TASK-RD-003")
    # one of two completed => in_progress (the bug produced "planned")
    assert infer_status_for_feature(feature, repo) == "in_progress"
    create_completed_task(repo, "TASK-RD-004")
    assert infer_status_for_feature(feature, repo) == "completed"
