"""Unit tests for the stale-test attribution helpers (TASK-AB-STALEATTRIB01).

Covers the pure helpers wired into ``agent_invoker._apply_runtime_parity_guard``
and ``feature_orchestrator._build_smoke_feedback``: the test-runner command
heuristic, the pytest failing-line parser, and the fail-OPEN authorship join
over per-task ``task_work_results.json`` records
(``path-string-mismatch-is-not-dishonesty.md``).

Coverage Target: >=85%
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from guardkit.orchestrator.stale_test_attribution import (
    build_stale_test_note,
    extract_failing_test_lines,
    failing_test_files,
    find_authoring_task,
    is_test_runner_command,
    stale_test_notes,
)


# ============================================================================
# 1. is_test_runner_command
# ============================================================================


@pytest.mark.parametrize(
    "command",
    [
        "pytest tests/unit -q",
        "python -m pytest tests/",
        ".venv/bin/python -m pytest -q",
        "npm test",
        "dotnet test MySln.sln",
        "go test ./...",
    ],
)
def test_test_runner_commands_recognised(command):
    assert is_test_runner_command(command) is True


@pytest.mark.parametrize(
    "command",
    ["python3 mod.py", "python -m guardkit.cli.main --dry-run", "", None],
)
def test_non_test_runner_commands_rejected(command):
    assert is_test_runner_command(command) is False


# ============================================================================
# 2. extract_failing_test_lines / failing_test_files
# ============================================================================


def test_extracts_failed_and_error_lines_deduped():
    output = (
        "=== short test summary info ===\n"
        "FAILED tests/unit/test_a.py::test_x - AssertionError: boom\n"
        "FAILED tests/unit/test_a.py::test_x - AssertionError: boom\n"
        "ERROR tests/unit/test_b.py - ImportError: nope\n"
        "2 failed in 0.10s"
    )
    lines = extract_failing_test_lines(output)
    assert lines == [
        "FAILED tests/unit/test_a.py::test_x",
        "ERROR tests/unit/test_b.py",
    ]


def test_unparseable_or_empty_output_yields_nothing():
    assert extract_failing_test_lines("") == []
    assert extract_failing_test_lines(None) == []
    assert extract_failing_test_lines("ModuleNotFoundError: no 'x'") == []


def test_extraction_failure_warns_once_and_fails_open(monkeypatch, caplog):
    """A bug in the extraction loop must be LOUD (one WARNING per process)
    while still failing open — the previous silent blanket except would
    blank every failing-test name across the parity/smoke/stall surfaces
    with no trace (2026-07-04 review, FIX 3a)."""
    import guardkit.orchestrator.stale_test_attribution as sta

    class _Boom:
        def finditer(self, output):
            raise RuntimeError("regex exploded")

    monkeypatch.setattr(sta, "_FAILING_LINE_RE", _Boom())
    monkeypatch.setattr(sta, "_extract_warn_emitted", False)
    with caplog.at_level(logging.WARNING):
        assert extract_failing_test_lines("FAILED tests/t.py::x") == []
        assert extract_failing_test_lines("FAILED tests/t.py::y") == []
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1  # once per process, not per call
    assert "regex exploded" in warnings[0].getMessage()
    assert "fail open" in warnings[0].getMessage()


def test_failing_test_files_maps_node_ids_to_distinct_paths():
    lines = [
        "FAILED tests/unit/test_a.py::TestC::test_x",
        "FAILED tests/unit/test_a.py::test_y",
        "ERROR tests/unit/test_b.py",
    ]
    assert failing_test_files(lines) == [
        "tests/unit/test_a.py",
        "tests/unit/test_b.py",
    ]


# ============================================================================
# 3. find_authoring_task (fail-OPEN authorship join)
# ============================================================================


def _write_record(worktree_root, task_id, payload) -> None:
    task_dir = worktree_root / ".guardkit" / "autobuild" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "task_work_results.json").write_text(
        payload if isinstance(payload, str) else json.dumps(payload)
    )


def test_single_other_author_resolves(tmp_path):
    _write_record(
        tmp_path, "TASK-TSJ-000",
        {"files_authored": ["tests/unit/test_a.py"]},
    )
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        == "TASK-TSJ-000"
    )


def test_created_fallback_when_no_files_authored(tmp_path):
    _write_record(
        tmp_path, "TASK-TSJ-000",
        {"files_created": ["tests/unit/test_a.py"], "files_modified": []},
    )
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        == "TASK-TSJ-000"
    )


def test_files_modified_alone_never_attributes(tmp_path):
    """``files_modified`` is TOUCHED, not authored (it carries union-merged
    git-diff paths): a pre-existing regression test trivially edited by an
    earlier task must never be attributed to it — a false attribution would
    license a later task to delete a genuine regression guard
    (2026-07-04 review, FIX 1a). Fail-open: no match → no note."""
    _write_record(
        tmp_path, "TASK-TSJ-000",
        {"files_created": [], "files_modified": ["tests/unit/test_a.py"]},
    )
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        is None
    )
    # And the batch surface emits no note either.
    assert (
        stale_test_notes(
            ["FAILED tests/unit/test_a.py::test_x"], tmp_path, {"TASK-TSJ-001"}
        )
        == []
    )


def test_files_modified_never_widens_files_authored(tmp_path):
    """When ``files_authored`` is present it is authoritative — a file that
    appears only in ``files_modified`` does not attribute."""
    _write_record(
        tmp_path, "TASK-TSJ-000",
        {
            "files_authored": ["src/mod.py"],
            "files_modified": ["tests/unit/test_a.py"],
        },
    )
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        is None
    )


def test_path_normalisation_matches_dot_prefix_and_absolute(tmp_path):
    _write_record(
        tmp_path, "TASK-TSJ-000",
        {"files_authored": ["./tests/unit/test_a.py"]},
    )
    # Worktree-absolute failing path resolves to the same relative target.
    absolute = str(tmp_path / "tests" / "unit" / "test_a.py")
    assert (
        find_authoring_task(absolute, tmp_path, {"TASK-TSJ-001"})
        == "TASK-TSJ-000"
    )


def test_current_task_author_fails_open(tmp_path):
    _write_record(
        tmp_path, "TASK-TSJ-001",
        {"files_authored": ["tests/unit/test_a.py"]},
    )
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        is None
    )


def test_ambiguous_authors_fail_open(tmp_path):
    _write_record(tmp_path, "TASK-TSJ-000", {"files_authored": ["tests/unit/test_a.py"]})
    _write_record(tmp_path, "TASK-TSJ-002", {"files_authored": ["tests/unit/test_a.py"]})
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        is None
    )


def test_missing_or_unreadable_records_fail_open(tmp_path):
    # No .guardkit/autobuild dir at all.
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        is None
    )
    # Corrupt JSON contributes nothing (and never raises).
    _write_record(tmp_path, "TASK-TSJ-000", "{not json")
    assert (
        find_authoring_task("tests/unit/test_a.py", tmp_path, {"TASK-TSJ-001"})
        is None
    )


# ============================================================================
# 4. stale_test_notes / build_stale_test_note
# ============================================================================


def test_stale_test_notes_none_worktree_fails_open():
    assert stale_test_notes(["FAILED tests/t.py::x"], None, {"TASK-TSJ-001"}) == []


def test_stale_test_note_names_test_task_and_permission(tmp_path):
    _write_record(
        tmp_path, "TASK-TSJ-000",
        {"files_authored": ["tests/unit/test_a.py"]},
    )
    notes = stale_test_notes(
        ["FAILED tests/unit/test_a.py::test_x"], tmp_path, {"TASK-TSJ-001"}
    )
    assert len(notes) == 1
    note = notes[0]
    assert "FAILED tests/unit/test_a.py::test_x" in note
    assert "TASK-TSJ-000" in note
    # The permission is conditional on the assertion pinning transient
    # scaffold state from the named task (2026-07-04 review, FIX 1b) …
    assert (
        "You may amend or delete that specific stale assertion in "
        "tests/unit/test_a.py ONLY if it pins transient point-in-time "
        "scaffold state from TASK-TSJ-000" in note
    )
    assert "change nothing else in that file" in note
    # … and never licenses deleting a genuine regression guard.
    assert (
        "genuine regression guard for behaviour your change broke, fix "
        "your implementation instead — do not delete it" in note
    )


def test_build_stale_test_note_without_lines_names_the_file():
    note = build_stale_test_note("tests/unit/test_a.py", "TASK-TSJ-000")
    assert "tests/unit/test_a.py" in note
    assert "change nothing else in that file" in note
    assert "do not delete it" in note


def test_stale_test_notes_reads_each_record_once(tmp_path, monkeypatch):
    """The authorship map is built with ONE scan per stale_test_notes call —
    records are not re-read per failing file (was O(files × tasks) JSON
    loads inside the per-turn verdict seam; 2026-07-04 review, FIX 2)."""
    _write_record(
        tmp_path, "TASK-TSJ-000", {"files_authored": ["tests/unit/test_a.py"]}
    )
    _write_record(
        tmp_path, "TASK-TSJ-002", {"files_authored": ["tests/unit/test_b.py"]}
    )
    _write_record(
        tmp_path, "TASK-TSJ-003", {"files_authored": ["tests/unit/test_c.py"]}
    )

    reads: list = []
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        if self.name == "task_work_results.json":
            reads.append(str(self))
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    notes = stale_test_notes(
        [
            "FAILED tests/unit/test_a.py::test_x",
            "FAILED tests/unit/test_b.py::test_y",
        ],
        tmp_path,
        {"TASK-TSJ-001"},
    )
    assert len(notes) == 2
    # ONE scan: 3 records on disk → exactly 3 reads, not 3 records × 2 files.
    assert len(reads) == 3
    assert len(set(reads)) == 3
