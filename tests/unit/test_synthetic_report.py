"""Unit tests for the shared synthetic report builder module.

Tests cover:
- build_synthetic_report(): Synthetic flag, standard fields, recovery metadata,
  scaffolding promise generation, and logging behaviour.
- generate_file_existence_promises(): Regex matching, backtick matching,
  status classification (complete/partial/incomplete), evidence text,
  directory reference checks, and disk-check gating.

Coverage Target: >=90%
Test Count: 18 tests
"""

import logging
from pathlib import Path

import pytest

from guardkit.orchestrator.synthetic_report import (
    build_synthetic_report,
    generate_file_existence_promises,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def base_report_kwargs():
    """Minimal keyword arguments for build_synthetic_report."""
    return {
        "task_id": "TASK-FIX-D1A3",
        "turn": 1,
        "files_modified": ["src/existing.py"],
        "files_created": ["src/new_module.py"],
        "tests_written": ["tests/test_new_module.py"],
        "tests_passed": True,
        "test_count": 5,
        "implementation_notes": "Implemented new module.",
        "concerns": [],
    }


@pytest.fixture
def scaffolding_kwargs(base_report_kwargs):
    """Report kwargs configured as a scaffolding task with acceptance criteria."""
    return {
        **base_report_kwargs,
        "task_type": "scaffolding",
        "acceptance_criteria": [
            "Create src/new_module.py with base classes",
            "Create tests/test_new_module.py with test stubs",
        ],
    }


# ===========================================================================
# Section 1: build_synthetic_report() Tests
# ===========================================================================


class TestBuildSyntheticReport:
    """Tests for build_synthetic_report() function."""

    def test_build_synthetic_report_always_sets_synthetic_flag(
        self, base_report_kwargs
    ):
        """Verify _synthetic: True is always present in the report."""
        report = build_synthetic_report(**base_report_kwargs)
        assert report["_synthetic"] is True

    def test_build_synthetic_report_includes_all_standard_fields(
        self, base_report_kwargs
    ):
        """All Player report schema fields are present in the output."""
        report = build_synthetic_report(**base_report_kwargs)

        expected_keys = {
            "task_id",
            "turn",
            "files_modified",
            "files_created",
            "tests_written",
            "tests_run",
            "tests_passed",
            "test_output_summary",
            "implementation_notes",
            "concerns",
            "requirements_addressed",
            "requirements_remaining",
            "_synthetic",
        }
        assert expected_keys.issubset(report.keys()), (
            f"Missing keys: {expected_keys - report.keys()}"
        )

        # Verify field values map correctly from inputs
        assert report["task_id"] == "TASK-FIX-D1A3"
        assert report["turn"] == 1
        assert report["files_modified"] == ["src/existing.py"]
        assert report["files_created"] == ["src/new_module.py"]
        assert report["tests_written"] == ["tests/test_new_module.py"]
        assert report["tests_run"] is True
        assert report["tests_passed"] is True
        assert report["implementation_notes"] == "Implemented new module."
        assert report["concerns"] == []
        assert report["requirements_addressed"] == []
        assert report["requirements_remaining"] == []

    def test_build_synthetic_report_includes_recovery_metadata_when_provided(
        self, base_report_kwargs
    ):
        """recovery_metadata dict is included under _recovery_metadata key."""
        recovery = {"recovered_from": "crash", "turn_recovered": 2}
        report = build_synthetic_report(
            **base_report_kwargs, recovery_metadata=recovery
        )

        assert "_recovery_metadata" in report
        assert report["_recovery_metadata"]["recovered_from"] == "crash"
        assert report["_recovery_metadata"]["turn_recovered"] == 2

    def test_build_synthetic_report_omits_recovery_metadata_when_none(
        self, base_report_kwargs
    ):
        """No _recovery_metadata key when recovery_metadata is None."""
        report = build_synthetic_report(**base_report_kwargs)
        assert "_recovery_metadata" not in report

        # Explicitly pass None as well
        report_explicit = build_synthetic_report(
            **base_report_kwargs, recovery_metadata=None
        )
        assert "_recovery_metadata" not in report_explicit

    def test_build_synthetic_report_scaffolding_generates_promises(
        self, scaffolding_kwargs
    ):
        """Scaffolding task_type + acceptance_criteria produces completion_promises."""
        report = build_synthetic_report(**scaffolding_kwargs)

        assert "completion_promises" in report
        promises = report["completion_promises"]
        assert len(promises) >= 1

        # Verify at least one promise matched (src/new_module.py appears in
        # both files_created and the acceptance criteria).
        statuses = [p["status"] for p in promises]
        assert "complete" in statuses

    def test_build_synthetic_report_no_promises_without_criteria(
        self, base_report_kwargs
    ):
        """No completion_promises when acceptance_criteria is absent."""
        report = build_synthetic_report(
            **base_report_kwargs, task_type="scaffolding", acceptance_criteria=None
        )
        assert "completion_promises" not in report

    def test_build_synthetic_report_no_promises_for_non_scaffolding(
        self, base_report_kwargs
    ):
        """Feature task_type with criteria does NOT generate completion_promises."""
        report = build_synthetic_report(
            **base_report_kwargs,
            task_type="feature",
            acceptance_criteria=["Create src/new_module.py"],
        )
        assert "completion_promises" not in report

    def test_build_synthetic_report_logs_promise_generation(
        self, scaffolding_kwargs, caplog
    ):
        """INFO log is emitted when file-existence promises are generated."""
        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.synthetic_report"
        ):
            build_synthetic_report(**scaffolding_kwargs)

        promise_logs = [
            r
            for r in caplog.records
            if "file-existence promises" in r.message
        ]
        assert len(promise_logs) == 1
        assert promise_logs[0].levelno == logging.INFO


# ===========================================================================
# Section 2: generate_file_existence_promises() Tests
# ===========================================================================


class TestGenerateFileExistencePromises:
    """Tests for generate_file_existence_promises() function."""

    def test_generate_promises_broad_regex_match(self):
        """Primary regex matches path/to/file.ext patterns without backticks."""
        criteria = ["Create src/models/user.py with user model"]
        promises = generate_file_existence_promises(
            files_created=["src/models/user.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"
        assert "src/models/user.py" in promises[0]["evidence"]

    def test_generate_promises_backtick_match(self):
        """Secondary regex matches backtick-quoted file paths."""
        criteria = ["Ensure `lib/helpers/format.ts` is created"]
        promises = generate_file_existence_promises(
            files_created=["lib/helpers/format.ts"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"
        assert "lib/helpers/format.ts" in promises[0]["evidence"]

    def test_generate_promises_complete_status_for_list_match(self):
        """Files present in created/modified lists yield status 'complete'."""
        criteria = [
            "Create src/api.py and update src/router.py",
        ]
        promises = generate_file_existence_promises(
            files_created=["src/api.py"],
            files_modified=["src/router.py"],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"

    def test_generate_promises_created_vs_modified_evidence(self):
        """Evidence distinguishes between '(created)' and '(modified)' files."""
        criteria = ["Update src/config.py and create src/defaults.py"]
        promises = generate_file_existence_promises(
            files_created=["src/defaults.py"],
            files_modified=["src/config.py"],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        evidence = promises[0]["evidence"]
        assert "(created)" in evidence
        assert "(modified)" in evidence

    def test_generate_promises_partial_status_for_disk_match(self, tmp_path):
        """Files found on disk but not in created/modified yield 'partial'."""
        # Create a real file on disk inside the tmp worktree
        target_file = tmp_path / "src" / "legacy.py"
        target_file.parent.mkdir(parents=True)
        target_file.write_text("# legacy code")

        criteria = ["Verify src/legacy.py exists in the project"]
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=criteria,
            worktree_path=tmp_path,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "partial"
        assert "src/legacy.py" in promises[0]["evidence"]

    def test_generate_promises_incomplete_when_no_match(self):
        """Criterion with no matching file yields 'incomplete'."""
        criteria = ["Create src/missing_module.py with helper functions"]
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "incomplete"
        assert "No file-existence evidence" in promises[0]["evidence"]

    def test_generate_promises_evidence_type_always_present(self):
        """All promises have evidence_type set to 'file_existence'."""
        criteria = [
            "Create src/found.py",
            "Create src/not_found.py",
        ]
        promises = generate_file_existence_promises(
            files_created=["src/found.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 2
        for promise in promises:
            assert promise["evidence_type"] == "file_existence"

    def test_generate_promises_criterion_text_included(self):
        """All promises include the original criterion_text string."""
        criteria = [
            "Add a README.md at the root",
            "Create src/utils.py with helpers",
        ]
        promises = generate_file_existence_promises(
            files_created=["README.md", "src/utils.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 2
        assert promises[0]["criterion_text"] == criteria[0]
        assert promises[1]["criterion_text"] == criteria[1]

    def test_generate_promises_directory_reference_check(self, tmp_path):
        """Backtick-quoted directory paths (e.g. `tests/seam/`) are checked on disk."""
        # Create the directory on disk
        dir_path = tmp_path / "tests" / "seam"
        dir_path.mkdir(parents=True)

        # Criterion references a directory, not a file -- no file extension
        criteria = ["Ensure `tests/seam/` directory exists with test files"]
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=criteria,
            worktree_path=tmp_path,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "partial"
        assert "tests/seam/" in promises[0]["evidence"]

    def test_generate_promises_no_disk_check_without_worktree_path(self, tmp_path):
        """When worktree_path is None, no disk check is attempted -- status is 'incomplete'."""
        # Create a file on disk that would match, but don't pass worktree_path
        target_file = tmp_path / "src" / "on_disk_only.py"
        target_file.parent.mkdir(parents=True)
        target_file.write_text("# exists on disk")

        criteria = ["Verify src/on_disk_only.py exists"]
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=criteria,
            worktree_path=None,
        )

        assert len(promises) == 1
        # Without worktree_path, disk check is skipped; status must be incomplete
        assert promises[0]["status"] == "incomplete"
