"""CLI tests for ``guardkit task audit`` (WS3-S8a)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from guardkit.cli.main import cli


def _init_git(repo: Path) -> None:
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "Test"],
    ):
        subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True)


def _write_task(repo: Path, subtree: str, name: str, task_id: str, status: str) -> None:
    d = repo / "tasks" / subtree
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(
        f"---\nid: {task_id}\nstatus: {status}\n---\n# task\n", encoding="utf-8"
    )


def _commit(repo: Path, msg: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", msg], cwd=str(repo), check=True, capture_output=True
    )


def test_clean_repo_exits_zero(tmp_path):
    _init_git(tmp_path)
    _write_task(tmp_path, "completed", "TASK-A-001-a.md", "TASK-A-001", "completed")
    _commit(tmp_path, "feat(TASK-A-001): done")

    result = CliRunner().invoke(cli, ["task", "audit", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert "No tracker divergences" in result.output


def test_divergent_repo_exits_one(tmp_path):
    _init_git(tmp_path)
    # completed subtree but backlog status -> conflict.
    _write_task(tmp_path, "completed", "TASK-B-001-b.md", "TASK-B-001", "backlog")
    _commit(tmp_path, "chore: add")

    result = CliRunner().invoke(cli, ["task", "audit", "--root", str(tmp_path)])
    assert result.exit_code == 1
    assert "TASK-B-001" in result.output


def test_json_report_written(tmp_path):
    _init_git(tmp_path)
    _write_task(tmp_path, "completed", "TASK-C-001-c.md", "TASK-C-001", "backlog")
    _commit(tmp_path, "chore: add")
    out = tmp_path / "report.json"

    result = CliRunner().invoke(
        cli, ["task", "audit", "--root", str(tmp_path), "--json", str(out)]
    )
    assert result.exit_code == 1
    data = json.loads(out.read_text())
    assert data["generated_by"] == "guardkit task audit"
    assert data["summary"]["total_divergences"] >= 1
    assert {t["task_id"] for t in data["tasks"]} == {"TASK-C-001"}


def test_format_json_to_stdout(tmp_path):
    _init_git(tmp_path)
    _write_task(tmp_path, "completed", "TASK-D-001-d.md", "TASK-D-001", "completed")
    _commit(tmp_path, "feat(TASK-D-001): done")

    result = CliRunner().invoke(
        cli, ["task", "audit", "--root", str(tmp_path), "--format", "json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["summary"]["total_divergences"] == 0


def test_read_only_does_not_modify_repo(tmp_path):
    _init_git(tmp_path)
    _write_task(tmp_path, "completed", "TASK-E-001-e.md", "TASK-E-001", "backlog")
    _commit(tmp_path, "chore: add")
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(tmp_path),
        capture_output=True, text=True,
    ).stdout

    CliRunner().invoke(cli, ["task", "audit", "--root", str(tmp_path)])

    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(tmp_path),
        capture_output=True, text=True,
    ).stdout
    assert before == after == ""  # audit is read-only
