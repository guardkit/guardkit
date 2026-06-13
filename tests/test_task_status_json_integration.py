"""Integration tests for the task-status-json producer script.

Hermetic: each test builds its own minimal ``tasks/`` tree under ``tmp_path``
and runs the producer with ``--base-path`` so the assertions never depend on
the live repo's task set (the original version depended on a committed
``TEST-001`` fixture — removed as repo cruft — which made it environment-fragile).
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "installer/core/commands/lib/task_status_json.py"

_FIXTURE = (
    "---\n"
    "id: TEST-001\n"
    "title: Test Task\n"
    "status: backlog\n"
    "priority: high\n"
    "task_type: feature\n"
    "complexity: 4\n"
    "---\n\n"
    "# Test Task\n\n"
    "Hermetic fixture for the task-status-json integration tests.\n"
)


def _make_tasks(tmp_path: Path) -> Path:
    """Build a minimal hermetic tasks/ tree with one known task (TEST-001)."""
    backlog = tmp_path / "tasks" / "backlog"
    backlog.mkdir(parents=True)
    (backlog / "TEST-001.md").write_text(_FIXTURE)
    return tmp_path


def _run(*args: str, base: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--base-path", str(base)],
        capture_output=True,
        text=True,
        cwd=str(base),
    )


def test_full_dashboard(tmp_path):
    """No task-id arg → full dashboard JSON with the expected schema keys."""
    base = _make_tasks(tmp_path)
    result = _run(base=base)

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    for key in ("schema_version", "generated_at", "base_path", "summary", "tasks"):
        assert key in data, f"missing {key}"
    assert data["summary"]["backlog"] == 1
    assert data["summary"]["total"] == 1
    assert any(t.get("id") == "TEST-001" for t in data["tasks"])


def test_single_task_lookup(tmp_path):
    """A known task-id → single-task object carrying that id (AC-007)."""
    base = _make_tasks(tmp_path)
    result = _run("TEST-001", base=base)

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data.get("id") == "TEST-001"
    assert data.get("status") == "backlog"


def test_nonexistent_task_errors(tmp_path):
    """An unknown task-id → exit 1 + 'not found' on stderr (error handling)."""
    base = _make_tasks(tmp_path)
    result = _run("NON-EXISTENT", base=base)

    assert result.returncode == 1, f"expected exit 1, got {result.returncode}"
    assert "not found" in result.stderr.lower()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        _make_tasks(p)
        for fn in (test_full_dashboard, test_single_task_lookup, test_nonexistent_task_errors):
            fn(Path(tempfile.mkdtemp()))
    print("✓ All integration tests passed!")
