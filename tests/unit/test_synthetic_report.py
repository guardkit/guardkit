"""Unit tests for the shared synthetic report builder module.

Tests cover:
- build_synthetic_report(): Synthetic flag, standard fields, recovery metadata,
  scaffolding promise generation, and logging behaviour.
- generate_file_existence_promises(): Regex matching, backtick matching,
  status classification (complete/partial/incomplete), evidence text,
  directory reference checks, and disk-check gating.
- infer_requirements_from_files(): Content-based keyword matching,
  conservative thresholds, size guards, binary file handling.
- _extract_criterion_keywords(): Stopword filtering, short word removal.

Coverage Target: >=90%
Test Count: 28 tests
"""

import logging
from pathlib import Path

import pytest

from guardkit.orchestrator.synthetic_report import (
    _extract_criterion_keywords,
    build_synthetic_report,
    generate_file_existence_promises,
    infer_requirements_from_files,
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


# ===========================================================================
# Section 3: _extract_criterion_keywords() Tests (TASK-FIX-ASPF-006)
# ===========================================================================


class TestExtractCriterionKeywords:
    """Tests for _extract_criterion_keywords() helper."""

    def test_extracts_meaningful_keywords(self):
        """Keywords longer than 3 chars and not stopwords are returned."""
        keywords = _extract_criterion_keywords(
            "Settings class has log_level field"
        )
        assert "settings" in keywords
        assert "class" in keywords
        assert "log_level" in keywords
        assert "field" in keywords

    def test_filters_stopwords(self):
        """Common stopwords are excluded from keywords."""
        keywords = _extract_criterion_keywords(
            "Create the new file with some implementation"
        )
        # "create", "the", "new", "file", "with", "some" are stopwords
        assert "the" not in keywords
        assert "with" not in keywords
        assert "some" not in keywords
        assert "implementation" in keywords

    def test_filters_short_words(self):
        """Words with 3 or fewer characters are excluded."""
        keywords = _extract_criterion_keywords("Add an API for the UI")
        assert "add" not in keywords
        assert "api" not in keywords  # 3 chars
        assert "for" not in keywords
        assert "the" not in keywords

    def test_returns_empty_for_only_stopwords(self):
        """All-stopword text returns empty set."""
        keywords = _extract_criterion_keywords("create a new file")
        assert len(keywords) == 0


# ===========================================================================
# Section 4: infer_requirements_from_files() Tests (TASK-FIX-ASPF-006)
# ===========================================================================


class TestInferRequirementsFromFiles:
    """Tests for infer_requirements_from_files() function."""

    def test_returns_empty_without_worktree(self):
        """worktree_path=None always returns empty list."""
        result = infer_requirements_from_files(
            acceptance_criteria=["Settings class has log_level field"],
            files_created=["src/settings.py"],
            files_modified=[],
            worktree_path=None,
        )
        assert result == []

    def test_returns_empty_with_no_files(self, tmp_path):
        """No files to check returns empty list."""
        result = infer_requirements_from_files(
            acceptance_criteria=["Settings class has log_level field"],
            files_created=[],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_matches_keywords_in_file_content(self, tmp_path):
        """Criterion keywords found in file contents are matched."""
        # Create a file with matching content
        src = tmp_path / "src" / "settings.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            'class Settings:\n    log_level: str = "INFO"\n'
        )

        result = infer_requirements_from_files(
            acceptance_criteria=[
                "Settings class has log_level field"
            ],
            files_created=["src/settings.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert len(result) == 1
        assert "Settings class has log_level field" in result

    def test_no_match_for_irrelevant_content(self, tmp_path):
        """Criterion keywords not found in any file returns empty."""
        src = tmp_path / "src" / "main.py"
        src.parent.mkdir(parents=True)
        src.write_text("def main():\n    print('hello')\n")

        result = infer_requirements_from_files(
            acceptance_criteria=[
                "Database migration script handles schema version upgrade"
            ],
            files_created=["src/main.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_skips_binary_files(self, tmp_path):
        """Binary (non-UTF-8) files are silently skipped."""
        binfile = tmp_path / "data.bin"
        binfile.write_bytes(b"\x80\x81\x82\x83\x00\xff\xfe")

        result = infer_requirements_from_files(
            acceptance_criteria=[
                "Settings class has log_level field"
            ],
            files_created=["data.bin"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_skips_large_files(self, tmp_path):
        """Files exceeding _MAX_FILE_SIZE are skipped."""
        largefile = tmp_path / "huge.py"
        # Write 150KB of content (exceeds 100KB limit)
        largefile.write_text("x = 'settings log_level class field'\n" * 5000)

        result = infer_requirements_from_files(
            acceptance_criteria=[
                "Settings class has log_level field"
            ],
            files_created=["huge.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_conservative_threshold(self, tmp_path):
        """Criterion with 4 keywords needs at least 2 matches (50%)."""
        src = tmp_path / "src" / "partial.py"
        src.parent.mkdir(parents=True)
        # Only 1 of 4 keywords present (settings) — below 50%
        src.write_text("value = 42\n")

        result = infer_requirements_from_files(
            acceptance_criteria=[
                "Settings class has log_level field"
            ],
            files_created=["src/partial.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_criteria_with_few_keywords_skipped(self, tmp_path):
        """Criteria with <2 meaningful keywords are skipped (too vague)."""
        src = tmp_path / "src" / "app.py"
        src.parent.mkdir(parents=True)
        src.write_text("all the code\n")

        result = infer_requirements_from_files(
            acceptance_criteria=["Create a new file"],  # all stopwords
            files_created=["src/app.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_handles_missing_files_gracefully(self, tmp_path):
        """Missing files (OSError) are silently skipped."""
        result = infer_requirements_from_files(
            acceptance_criteria=[
                "Settings class has log_level field"
            ],
            files_created=["nonexistent/file.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )
        assert result == []

    def test_deterministic_file_reading_order(self, tmp_path):
        """Files are sorted alphabetically for deterministic reading (TASK-VRF-005).

        Without sorting, the 1MB byte cap causes different file subsets to be
        read depending on the order files appear in the input lists, leading to
        non-deterministic keyword matches across turns.
        """
        # Create two files — one with matching keywords, one without.
        # File "aaa.py" alphabetically first, "zzz.py" last.
        aaa = tmp_path / "aaa.py"
        zzz = tmp_path / "zzz.py"
        aaa.write_text("class Settings:\n    log_level: str = 'INFO'\n")
        zzz.write_text("def unrelated():\n    pass\n")

        # Pass files in reverse alphabetical order — sorting should fix order
        result_reversed = infer_requirements_from_files(
            acceptance_criteria=["Settings class has log_level field"],
            files_created=["zzz.py", "aaa.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )

        # Pass files in alphabetical order
        result_sorted = infer_requirements_from_files(
            acceptance_criteria=["Settings class has log_level field"],
            files_created=["aaa.py", "zzz.py"],
            files_modified=[],
            worktree_path=tmp_path,
        )

        # Both orders must produce identical results (deterministic)
        assert result_reversed == result_sorted
        assert len(result_reversed) == 1

    def test_deduplicates_files_across_created_and_modified(self, tmp_path):
        """Files appearing in both created and modified are read only once (TASK-VRF-005)."""
        src = tmp_path / "src" / "settings.py"
        src.parent.mkdir(parents=True)
        src.write_text("class Settings:\n    log_level: str = 'INFO'\n")

        result = infer_requirements_from_files(
            acceptance_criteria=["Settings class has log_level field"],
            files_created=["src/settings.py"],
            files_modified=["src/settings.py"],  # duplicate
            worktree_path=tmp_path,
        )
        # Should still match (no double-counting issues)
        assert len(result) == 1


# ===========================================================================
# Section 5: build_synthetic_report() with worktree_path (TASK-FIX-ASPF-006)
# ===========================================================================


class TestBuildSyntheticReportWithWorktree:
    """Tests for build_synthetic_report() requirements inference integration."""

    def test_populates_requirements_addressed_from_inference(
        self, base_report_kwargs, tmp_path
    ):
        """When worktree_path and criteria provided, requirements_addressed is populated."""
        # Create file with matching content
        src = tmp_path / "src" / "new_module.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "class BaseModule:\n"
            "    def process(self):\n"
            "        return 'processed'\n"
        )

        report = build_synthetic_report(
            **base_report_kwargs,
            acceptance_criteria=[
                "BaseModule class with process method implementation"
            ],
            worktree_path=tmp_path,
        )
        assert len(report["requirements_addressed"]) == 1

    def test_requirements_addressed_empty_without_worktree(
        self, base_report_kwargs
    ):
        """Without worktree_path, requirements_addressed remains []."""
        report = build_synthetic_report(
            **base_report_kwargs,
            acceptance_criteria=["Some criterion text here for testing"],
        )
        assert report["requirements_addressed"] == []

    def test_logs_inferred_requirements(
        self, base_report_kwargs, tmp_path, caplog
    ):
        """INFO log emitted when requirements inferred."""
        src = tmp_path / "src" / "new_module.py"
        src.parent.mkdir(parents=True)
        src.write_text(
            "class BaseModule:\n    process = True\n"
        )

        with caplog.at_level(
            logging.INFO, logger="guardkit.orchestrator.synthetic_report"
        ):
            build_synthetic_report(
                **base_report_kwargs,
                acceptance_criteria=[
                    "BaseModule class with process method implementation"
                ],
                worktree_path=tmp_path,
            )

        inference_logs = [
            r for r in caplog.records
            if "requirements_addressed" in r.message
            and "TASK-FIX-ASPF-006" in r.message
        ]
        assert len(inference_logs) == 1


# ===========================================================================
# Section 6: Enhanced File Matching Tests (TASK-FIX-VL07 Part B)
# ===========================================================================


class TestEnhancedFileExistencePromises:
    """Tests for enhanced regex, directory, and glob matching (TASK-FIX-VL07)."""

    def test_directory_creation_pattern_matching(self):
        """'Create models directory' matches files under models/."""
        criteria = ["Create models directory with base classes"]
        promises = generate_file_existence_promises(
            files_created=["models/__init__.py", "models/user.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"
        assert "models/" in promises[0]["evidence"] or "models" in promises[0]["evidence"]
        assert promises[0]["confidence"] == 0.6

    def test_directory_creation_with_the_article(self):
        """'Create the tests directory' matches files under tests/."""
        criteria = ["Create the tests directory for unit tests"]
        promises = generate_file_existence_promises(
            files_created=["tests/test_main.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"

    def test_directory_structure_pattern(self):
        """'X directory structure' pattern matches files under X/."""
        criteria = ["Set up src directory structure"]
        promises = generate_file_existence_promises(
            files_created=["src/__init__.py", "src/main.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"

    def test_glob_pattern_matching(self):
        """Backtick glob pattern `alembic/versions/*.py` matches files."""
        criteria = ["Create `alembic/versions/*.py` migration files"]
        promises = generate_file_existence_promises(
            files_created=["alembic/versions/001_init.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"
        assert promises[0]["confidence"] == 0.7

    def test_glob_pattern_no_match(self):
        """Glob pattern with no matching files yields incomplete."""
        criteria = ["Create `alembic/versions/*.py` migration files"]
        promises = generate_file_existence_promises(
            files_created=["src/main.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "incomplete"

    def test_double_quoted_path_matching(self):
        """Double-quoted file path extracted and matched."""
        criteria = ['Ensure "src/config.py" is created with defaults']
        promises = generate_file_existence_promises(
            files_created=["src/config.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"

    def test_single_quoted_path_matching(self):
        """Single-quoted file path extracted and matched."""
        criteria = ["Ensure 'src/config.py' is created with defaults"]
        promises = generate_file_existence_promises(
            files_created=["src/config.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "complete"

    def test_confidence_scoring_direct_match(self):
        """Direct file match has confidence 1.0."""
        criteria = ["Create src/models/user.py with user model"]
        promises = generate_file_existence_promises(
            files_created=["src/models/user.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["confidence"] == 1.0

    def test_confidence_scoring_incomplete(self):
        """No match has confidence 0.0."""
        criteria = ["Create src/missing.py with nothing"]
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["confidence"] == 0.0

    def test_confidence_scoring_partial_disk_match(self, tmp_path):
        """Partial disk match has confidence 0.5."""
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
        assert promises[0]["confidence"] == 0.5

    def test_backward_compatibility_no_confidence_breakage(self):
        """Existing callers that don't access 'confidence' key still work."""
        criteria = ["Create src/found.py"]
        promises = generate_file_existence_promises(
            files_created=["src/found.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        # Access only pre-existing keys — these must still work
        assert promises[0]["criterion_id"] == "AC-001"
        assert promises[0]["status"] == "complete"
        assert promises[0]["evidence_type"] == "file_existence"
        # 'confidence' is present but not required by existing callers
        assert "confidence" in promises[0]

    def test_directory_no_match_when_no_files(self):
        """Directory pattern with no files under it yields incomplete."""
        criteria = ["Create models directory with base classes"]
        promises = generate_file_existence_promises(
            files_created=["src/main.py"],
            files_modified=[],
            acceptance_criteria=criteria,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "incomplete"
