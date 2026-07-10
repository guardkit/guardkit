"""Unit tests for the task-audit tool (WS3-S8a).

Covers the declared-vs-inferred status divergences, dangling-reference
detection (the dead-task-id-baseline class), git-completion inference, and the
id-resolution edge cases (lower-case hashes, slug-only names). Fixtures are
self-contained temp repos so the tests are hermetic and deterministic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from guardkit.orchestrator.task_audit import (
    audit_tasks,
    _component_is_id_part,
    _resolve_candidate,
    _status_bucket,
    _trim_candidate,
    OPEN,
    TERMINAL,
    OTHER,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_task(
    repo: Path,
    subtree: str,
    filename: str,
    *,
    task_id: str | None = "__auto__",
    status: str | None = "backlog",
    body: str = "# task",
) -> Path:
    """Write a task markdown file with frontmatter under ``tasks/<subtree>``."""
    d = repo / "tasks" / subtree
    d.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    if task_id == "__auto__":
        task_id = Path(filename).stem
    if task_id is not None:
        lines.append(f"id: {task_id}")
    if status is not None:
        lines.append(f"status: {status}")
    lines.append("---")
    lines.append(body)
    path = d / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git(repo: Path) -> None:
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------


class TestStatusBucket:
    def test_terminal_statuses(self):
        for s in ["completed", "done", "review_complete", "cancelled", "obsolete"]:
            assert _status_bucket(s) == TERMINAL

    def test_open_statuses(self):
        for s in ["backlog", "in_progress", "in-progress", "in_review", "design_approved"]:
            assert _status_bucket(s) == OPEN

    def test_unknown_and_none(self):
        assert _status_bucket(None) == OTHER
        assert _status_bucket("frobnicated") == OTHER


# ---------------------------------------------------------------------------
# Id extraction / resolution
# ---------------------------------------------------------------------------


class TestIdResolution:
    def test_component_qualification(self):
        assert _component_is_id_part("001")  # numeric
        assert _component_is_id_part("REV")  # upper prefix
        assert _component_is_id_part("CB0F")  # upper hash
        assert _component_is_id_part("a3f8")  # lower hex hash w/ digit
        assert _component_is_id_part("6d41")
        assert not _component_is_id_part("feature")  # slug word
        assert not _component_is_id_part("do")

    def test_trim_drops_slug(self):
        assert _trim_candidate("TASK-MP-001-do-thing") == "TASK-MP-001"
        assert _trim_candidate("TASK-FIX-a3f8-fix-the-thing") == "TASK-FIX-a3f8"
        assert _trim_candidate("TASK-FMDR-001") == "TASK-FMDR-001"

    def test_trim_keeps_subtask_suffix(self):
        assert _trim_candidate("TASK-E01-b2c4.1") == "TASK-E01-b2c4.1"

    def test_forward_resolution(self):
        declared = {"TASK-MP-001"}
        assert _resolve_candidate("TASK-MP-001-do-thing", declared) == "TASK-MP-001"
        assert _resolve_candidate("TASK-MP-001", declared) == "TASK-MP-001"

    def test_reverse_resolution_to_full_stem(self):
        # No-frontmatter-id file: declared id is the full slug-bearing stem.
        declared = {"TASK-DOC-api-reference"}
        assert (
            _resolve_candidate("TASK-DOC-api-reference", declared)
            == "TASK-DOC-api-reference"
        )
        assert _resolve_candidate("TASK-DOC", declared) == "TASK-DOC-api-reference"

    def test_unresolved_is_none(self):
        assert _resolve_candidate("TASK-NOPE-999", {"TASK-MP-001"}) is None

    def test_lowercase_hash_resolves(self):
        declared = {"TASK-REV-6d41", "TASK-INT-i9j0"}
        assert _resolve_candidate("TASK-REV-6d41", declared) == "TASK-REV-6d41"
        # non-hex hash (i9j0) is matched by identity against the declared set
        assert _resolve_candidate("TASK-INT-i9j0", declared) == "TASK-INT-i9j0"


# ---------------------------------------------------------------------------
# Clean fixture — zero divergences
# ---------------------------------------------------------------------------


class TestCleanFixture:
    def test_clean_repo_reports_zero(self, tmp_path):
        _init_git(tmp_path)
        _write_task(
            tmp_path,
            "completed",
            "TASK-DEMO-001-demo.md",
            task_id="TASK-DEMO-001",
            status="completed",
        )
        _commit_all(tmp_path, "feat(TASK-DEMO-001): implement demo")

        report = audit_tasks(tmp_path)
        assert report.total_divergences == 0
        assert report.divergent_task_count == 0
        assert report.dangling_count == 0
        assert report.task_file_count == 1
        assert report.git_available is True

    def test_open_task_no_completion_evidence_is_clean(self, tmp_path):
        # A backlog task with no completing commit is NOT a divergence.
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-WIP-001-wip.md",
            task_id="TASK-WIP-001", status="backlog",
        )
        _commit_all(tmp_path, "spec(TASK-WIP-001): draft the plan")
        report = audit_tasks(tmp_path)
        assert report.total_divergences == 0


# ---------------------------------------------------------------------------
# Divergence classes
# ---------------------------------------------------------------------------


class TestDivergenceClasses:
    def _row(self, report, task_id):
        return next(r for r in report.rows if r.task_id == task_id)

    def test_status_location_conflict(self, tmp_path):
        # completed subtree, but frontmatter says backlog.
        _init_git(tmp_path)
        _write_task(
            tmp_path, "completed", "TASK-A-001-a.md",
            task_id="TASK-A-001", status="backlog",
        )
        _commit_all(tmp_path, "chore: add task")
        report = audit_tasks(tmp_path)
        row = self._row(report, "TASK-A-001")
        assert "status_location_conflict" in row.divergences

    def test_inferred_completion_conflict(self, tmp_path):
        # backlog task, but a completion commit references it.
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-B-001-b.md",
            task_id="TASK-B-001", status="backlog",
        )
        _commit_all(tmp_path, "feat(TASK-B-001): complete TASK-B-001 work")
        report = audit_tasks(tmp_path)
        row = self._row(report, "TASK-B-001")
        assert row.inferred_status == "completed"
        assert "inferred_completion_conflict" in row.divergences
        assert any("git:" in e for e in row.inferred_evidence)

    def test_body_only_reference_is_not_completion(self, tmp_path):
        # A commit whose SUBJECT is not completion-shaped and only mentions the
        # id in a non-verb context must NOT infer completion.
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-C-001-c.md",
            task_id="TASK-C-001", status="backlog",
        )
        _commit_all(tmp_path, "docs: notes about the roadmap")  # no id, no verb
        report = audit_tasks(tmp_path)
        row = self._row(report, "TASK-C-001")
        assert row.inferred_status == "unknown"
        assert "inferred_completion_conflict" not in row.divergences

    def test_missing_status(self, tmp_path):
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-D-001-d.md",
            task_id="TASK-D-001", status=None,
        )
        _commit_all(tmp_path, "chore: add task")
        report = audit_tasks(tmp_path)
        row = self._row(report, "TASK-D-001")
        assert "missing_status" in row.divergences

    def test_unparseable_frontmatter(self, tmp_path):
        _init_git(tmp_path)
        d = tmp_path / "tasks" / "backlog"
        d.mkdir(parents=True)
        # A colon in an unquoted title breaks the YAML fence.
        (d / "TASK-E-001-e.md").write_text(
            '---\nid: TASK-E-001\ntitle: Fix "Critical error: None" bug\n---\n# x\n',
            encoding="utf-8",
        )
        _commit_all(tmp_path, "chore: add task")
        report = audit_tasks(tmp_path)
        # The id cannot be read from broken frontmatter, so the row is keyed by
        # the filename stem; it must still carry the unparseable + missing-status
        # divergences.
        row = next(r for r in report.rows if r.file.endswith("TASK-E-001-e.md"))
        assert "unparseable_frontmatter" in row.divergences
        assert "missing_status" in row.divergences

    def test_duplicate_task_file(self, tmp_path):
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-F-001-here.md",
            task_id="TASK-F-001", status="backlog",
        )
        _write_task(
            tmp_path, "design_approved", "TASK-F-001-there.md",
            task_id="TASK-F-001", status="design_approved",
        )
        _commit_all(tmp_path, "chore: add tasks")
        report = audit_tasks(tmp_path)
        rows = [r for r in report.rows if r.task_id == "TASK-F-001"]
        assert len(rows) == 2
        assert all("duplicate_task_file" in r.divergences for r in rows)

    def test_slug_only_names_are_not_false_duplicates(self, tmp_path):
        # Two distinct slug-only tasks (no frontmatter id) sharing a prefix must
        # NOT be reported as duplicates.
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-DOC-api-reference.md",
            task_id=None, status="backlog",
        )
        _write_task(
            tmp_path, "backlog", "TASK-DOC-changelog.md",
            task_id=None, status="backlog",
        )
        _commit_all(tmp_path, "chore: docs tasks")
        report = audit_tasks(tmp_path)
        dup_rows = [r for r in report.rows if "duplicate_task_file" in r.divergences]
        assert dup_rows == []
        # And their ids are the full unique stems.
        ids = {r.task_id for r in report.rows}
        assert "TASK-DOC-api-reference" in ids
        assert "TASK-DOC-changelog" in ids


# ---------------------------------------------------------------------------
# Feature-YAML rollups
# ---------------------------------------------------------------------------


class TestFeatureRollup:
    def test_terminal_feature_infers_task_completion(self, tmp_path):
        _init_git(tmp_path)
        _write_task(
            tmp_path, "backlog", "TASK-G-001-g.md",
            task_id="TASK-G-001", status="backlog",
        )
        feat_dir = tmp_path / ".guardkit" / "features"
        feat_dir.mkdir(parents=True)
        (feat_dir / "FEAT-G.yaml").write_text(
            "id: FEAT-G\nstatus: completed\ntasks:\n  - id: TASK-G-001\n",
            encoding="utf-8",
        )
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        row = next(r for r in report.rows if r.task_id == "TASK-G-001")
        assert row.inferred_status == "completed"
        assert "inferred_completion_conflict" in row.divergences
        assert any("rollup:" in e for e in row.inferred_evidence)


# ---------------------------------------------------------------------------
# Dangling references (the dead-task-id-baseline class)
# ---------------------------------------------------------------------------


class TestDanglingReferences:
    def test_code_reference_to_unfiled_task_is_dangling(self, tmp_path):
        # Reproduces the trio class: source names a task id with no task file.
        _init_git(tmp_path)
        src = tmp_path / "guardkit" / "orchestrator"
        src.mkdir(parents=True)
        (src / "thing.py").write_text(
            "# See TASK-FMDR-001 for the reconciliation-layer rule.\n",
            encoding="utf-8",
        )
        _write_task(
            tmp_path, "completed", "TASK-REAL-001-real.md",
            task_id="TASK-REAL-001", status="completed",
        )
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        dangling_ids = {d.task_id for d in report.dangling}
        assert "TASK-FMDR-001" in dangling_ids
        d = next(d for d in report.dangling if d.task_id == "TASK-FMDR-001")
        assert "guardkit/orchestrator/thing.py" in d.referenced_by

    def test_feature_yaml_pointing_at_missing_task_is_dangling(self, tmp_path):
        _init_git(tmp_path)
        feat_dir = tmp_path / ".guardkit" / "features"
        feat_dir.mkdir(parents=True)
        (feat_dir / "FEAT-H.yaml").write_text(
            "id: FEAT-H\nstatus: planned\ntasks:\n  - id: TASK-GHOST-001\n",
            encoding="utf-8",
        )
        (tmp_path / "tasks" / "backlog").mkdir(parents=True)
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        assert "TASK-GHOST-001" in {d.task_id for d in report.dangling}

    def test_declared_task_is_not_dangling(self, tmp_path):
        # A referenced id that DOES have a task file must not dangle.
        _init_git(tmp_path)
        src = tmp_path / "guardkit"
        src.mkdir(parents=True)
        (src / "x.py").write_text("# ref TASK-KNOWN-001 here\n", encoding="utf-8")
        _write_task(
            tmp_path, "completed", "TASK-KNOWN-001-k.md",
            task_id="TASK-KNOWN-001", status="completed",
        )
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        assert "TASK-KNOWN-001" not in {d.task_id for d in report.dangling}

    def test_state_doc_stub_does_not_count_as_declared(self, tmp_path):
        # docs/state/<id>.md exists but no task file -> still dangling, flagged.
        _init_git(tmp_path)
        src = tmp_path / "guardkit"
        src.mkdir(parents=True)
        (src / "x.py").write_text("# ref TASK-STUB-001 here\n", encoding="utf-8")
        state = tmp_path / "docs" / "state"
        state.mkdir(parents=True)
        (state / "TASK-STUB-001.md").write_text("# state\n", encoding="utf-8")
        (tmp_path / "tasks" / "backlog").mkdir(parents=True)
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        d = next((d for d in report.dangling if d.task_id == "TASK-STUB-001"), None)
        assert d is not None
        assert d.state_doc_exists is True

    def test_placeholder_ids_are_not_dangling(self, tmp_path):
        _init_git(tmp_path)
        src = tmp_path / "guardkit"
        src.mkdir(parents=True)
        (src / "x.py").write_text(
            "# example TASK-XXX-YYYY and TASK-FIX (no digit) placeholders\n",
            encoding="utf-8",
        )
        (tmp_path / "tasks" / "backlog").mkdir(parents=True)
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        assert report.dangling == []

    def test_custom_reference_globs(self, tmp_path):
        _init_git(tmp_path)
        (tmp_path / "weird").mkdir()
        (tmp_path / "weird" / "notes.txt").write_text(
            "TASK-CUSTOM-001 mentioned\n", encoding="utf-8"
        )
        (tmp_path / "tasks" / "backlog").mkdir(parents=True)
        _commit_all(tmp_path, "chore: add")
        # Default globs do not scan weird/ -> no dangling.
        assert audit_tasks(tmp_path).dangling == []
        # Custom glob does.
        report = audit_tasks(tmp_path, reference_globs=["weird/*.txt"])
        assert "TASK-CUSTOM-001" in {d.task_id for d in report.dangling}


# ---------------------------------------------------------------------------
# Report serialisation + no-git degradation
# ---------------------------------------------------------------------------


class TestReport:
    def test_to_dict_divergent_only_and_all(self, tmp_path):
        _init_git(tmp_path)
        _write_task(
            tmp_path, "completed", "TASK-OK-001-ok.md",
            task_id="TASK-OK-001", status="completed",
        )
        _write_task(
            tmp_path, "completed", "TASK-BAD-001-bad.md",
            task_id="TASK-BAD-001", status="backlog",  # conflict
        )
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)

        default = report.to_dict()
        assert default["summary"]["rows_included"] == "divergent_only"
        assert {t["task_id"] for t in default["tasks"]} == {"TASK-BAD-001"}

        full = report.to_dict(include_clean_rows=True)
        assert full["summary"]["rows_included"] == "all"
        assert {"TASK-OK-001", "TASK-BAD-001"} <= {t["task_id"] for t in full["tasks"]}

    def test_breakdown_counts(self, tmp_path):
        _init_git(tmp_path)
        _write_task(
            tmp_path, "completed", "TASK-Z-001-z.md",
            task_id="TASK-Z-001", status="backlog",
        )
        _commit_all(tmp_path, "chore: add")
        report = audit_tasks(tmp_path)
        breakdown = report.divergence_breakdown()
        assert breakdown.get("status_location_conflict") == 1

    def test_no_git_degrades_gracefully(self, tmp_path):
        # No .git -> git_available False, filesystem signals still work.
        _write_task(
            tmp_path, "completed", "TASK-NG-001-ng.md",
            task_id="TASK-NG-001", status="backlog",
        )
        report = audit_tasks(tmp_path)
        assert report.git_available is False
        row = next(r for r in report.rows if r.task_id == "TASK-NG-001")
        # status_location_conflict is filesystem-only, so still detected.
        assert "status_location_conflict" in row.divergences

    def test_no_tasks_dir(self, tmp_path):
        report = audit_tasks(tmp_path)
        assert report.task_file_count == 0
        assert report.total_divergences == 0
