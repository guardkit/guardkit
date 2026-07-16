"""Tests for DCL artifact discovery (Phase D, design §1 / D1).

``find_dcl_files_with_tag`` mirrors the BDD tag scan: a cheap text scan for a
``@task:<TASK-ID>`` marker under ``features/**/*.dcl``.
"""

from __future__ import annotations

from pathlib import Path

from guardkit.qa.dcl.discovery import find_dcl_files_with_tag, task_tag


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_task_tag_format():
    assert task_tag("TASK-STAT-001") == "@task:TASK-STAT-001"


def test_finds_tagged_dcl_in_nested_layout(tmp_path: Path):
    features = tmp_path / "features"
    fp = _write(
        features / "stats-endpoint" / "stats-endpoint.dcl",
        "language dcl 1.0\n// @task:TASK-STAT-001\ncapability C {}\n",
    )
    matches = find_dcl_files_with_tag(features, task_tag("TASK-STAT-001"))
    assert matches == [fp]


def test_no_match_when_tag_absent(tmp_path: Path):
    features = tmp_path / "features"
    _write(
        features / "other" / "other.dcl",
        "language dcl 1.0\n// @task:TASK-OTHER-999\ncapability C {}\n",
    )
    assert find_dcl_files_with_tag(features, task_tag("TASK-STAT-001")) == []


def test_missing_features_dir_returns_empty(tmp_path: Path):
    assert find_dcl_files_with_tag(tmp_path / "features", task_tag("TASK-X")) == []


def test_excludes_dotdirs_and_vendored(tmp_path: Path):
    features = tmp_path / "features"
    _write(
        features / ".venv" / "vendored.dcl",
        "// @task:TASK-STAT-001\n",
    )
    _write(
        features / "node_modules" / "pkg.dcl",
        "// @task:TASK-STAT-001\n",
    )
    real = _write(
        features / "stats" / "stats.dcl",
        "// @task:TASK-STAT-001\ncapability C {}\n",
    )
    assert find_dcl_files_with_tag(features, task_tag("TASK-STAT-001")) == [real]


def test_only_dcl_extension_scanned(tmp_path: Path):
    features = tmp_path / "features"
    _write(features / "s" / "s.feature", "@task:TASK-STAT-001\n")
    _write(features / "s" / "notes.txt", "@task:TASK-STAT-001\n")
    assert find_dcl_files_with_tag(features, task_tag("TASK-STAT-001")) == []


def test_multiple_matches_sorted(tmp_path: Path):
    features = tmp_path / "features"
    a = _write(features / "a" / "a.dcl", "// @task:TASK-1\n")
    b = _write(features / "b" / "b.dcl", "// @task:TASK-1\n")
    matches = find_dcl_files_with_tag(features, task_tag("TASK-1"))
    assert matches == sorted([a, b])
