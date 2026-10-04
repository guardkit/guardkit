"""complete_task derives the task ID, not the whole file name (Pi-commands change, 4 October 2026).

Descriptive task file names (TASK-045-add-login.md) carry a slug. Using the whole stem as the ID
made plan archival, the docs/state/ commit and the tier-1 pass-bar lookup
(qa/pass-bar-<TASK-ID>.yaml) miss.
"""
from __future__ import annotations

from pathlib import Path

from installer.core.commands.lib.task_completion_helper import _task_id_for


def _write(path: Path, frontmatter: str) -> Path:
    path.write_text(f"---\n{frontmatter}---\n\n# Task\n", encoding="utf-8")
    return path


def test_frontmatter_id_wins(tmp_path: Path) -> None:
    task = _write(tmp_path / "TASK-TOP-D6C8-process-launch-path.md", "id: TASK-TOP-D6C8\ntitle: x\n")
    assert _task_id_for(task) == "TASK-TOP-D6C8"


def test_descriptive_name_without_id_uses_prefix(tmp_path: Path) -> None:
    task = _write(tmp_path / "TASK-045-add-login.md", "title: x\n")
    assert _task_id_for(task) == "TASK-045"


def test_multi_segment_id_prefix(tmp_path: Path) -> None:
    task = _write(tmp_path / "TASK-TEST-001-some-slug.md", "title: x\n")
    assert _task_id_for(task) == "TASK-TEST-001"


def test_plain_id_file_name_unchanged(tmp_path: Path) -> None:
    task = _write(tmp_path / "TASK-001.md", "title: x\n")
    assert _task_id_for(task) == "TASK-001"


def test_frontmatter_id_is_read_not_guessed(tmp_path: Path) -> None:
    task = _write(tmp_path / "TASK-045-renamed-file.md", "id: TASK-099\ntitle: x\n")
    assert _task_id_for(task) == "TASK-099"


def test_slug_starting_with_digits_is_not_absorbed(tmp_path: Path) -> None:
    task = _write(tmp_path / "TASK-045-2fa-setup.md", "title: x\n")
    assert _task_id_for(task) == "TASK-045"


def test_lowercase_hash_id(tmp_path: Path) -> None:
    assert _task_id_for(_write(tmp_path / "TASK-FIX-a3f8.md", "title: x\n")) == "TASK-FIX-a3f8"
    assert _task_id_for(_write(tmp_path / "TASK-a3f2-add-login.md", "title: x\n")) == "TASK-a3f2"


def test_subtask_id_with_and_without_slug(tmp_path: Path) -> None:
    assert _task_id_for(_write(tmp_path / "TASK-E01-A3F2.1.md", "title: x\n")) == "TASK-E01-A3F2.1"
    assert _task_id_for(_write(tmp_path / "TASK-E01-a3f2.1-split-parser.md", "title: x\n")) == "TASK-E01-a3f2.1"


def test_prefixed_hash_with_slug(tmp_path: Path) -> None:
    assert _task_id_for(_write(tmp_path / "TASK-TOP-D6C8-process-launch.md", "title: x\n")) == "TASK-TOP-D6C8"


def test_capture_reports_not_published(monkeypatch, tmp_path: Path) -> None:
    """capture-outcome exits 0 when it could not publish; the routine must not say "recorded"."""
    import subprocess

    from installer.core.commands.lib import task_completion_helper as helper

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="Memory client unavailable - outcome NOT published\n", stderr="")

    monkeypatch.setattr(helper.subprocess, "run", fake_run)
    assert helper._capture_outcome_best_effort(tmp_path / "TASK-001.md") == "not published"

    def fake_ok(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="Outcome published: OUT-1\n", stderr="")

    monkeypatch.setattr(helper.subprocess, "run", fake_ok)
    assert helper._capture_outcome_best_effort(tmp_path / "TASK-001.md") == "recorded"
