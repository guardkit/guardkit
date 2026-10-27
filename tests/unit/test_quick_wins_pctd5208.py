"""
Unit tests for TASK-PCTD-5208 quick wins:
  R1 - Enhanced _summarize_test_output() with error context
  R2 - (normalized feedback text for stall detection: deleted with the
       stall detectors, 27 October 2026)
  R3 - Fixed duplicate path deduplication in test detection

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates import CoachValidator


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-PCTD-5208"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def validator(tmp_worktree):
    """Create a CoachValidator with a temporary worktree."""
    return CoachValidator(worktree_path=str(tmp_worktree))


# ============================================================================
# R1: _summarize_test_output tests
# ============================================================================


class TestSummarizeTestOutput:
    """Tests for enhanced _summarize_test_output with error context."""

    def test_connection_refused_error_included(self, validator):
        """ConnectionRefusedError output includes Error detail section."""
        output = (
            "collected 3 items\n"
            "\n"
            "tests/test_db.py::TestDB::test_connect FAILED\n"
            "E   ConnectionRefusedError: [Errno 111] Connection refused\n"
            "E   localhost:5432\n"
            "\n"
            "short test summary info\n"
            "FAILED tests/test_db.py::TestDB::test_connect\n"
            "1 failed in 0.45s\n"
        )
        result = validator._summarize_test_output(output)
        assert "Error detail:" in result
        assert "ConnectionRefusedError" in result

    def test_import_error_captured(self, validator):
        """ImportError/ModuleNotFoundError output captures error type."""
        output = (
            "collected 0 items / 1 error\n"
            "\n"
            "ImportError: cannot import name 'missing_func' from 'mymodule'\n"
            "ModuleNotFoundError: No module named 'nonexistent'\n"
            "\n"
            "1 error in 0.12s\n"
        )
        result = validator._summarize_test_output(output)
        assert "Error detail:" in result
        assert "ImportError" in result

    def test_normal_passing_output_backward_compatible(self, validator):
        """Normal passing output still includes Result section."""
        output = (
            "collected 5 items\n"
            "\n"
            "tests/test_auth.py::test_login PASSED\n"
            "tests/test_auth.py::test_logout PASSED\n"
            "tests/test_auth.py::test_token PASSED\n"
            "tests/test_auth.py::test_refresh PASSED\n"
            "tests/test_auth.py::test_revoke PASSED\n"
            "\n"
            "5 passed in 0.23s\n"
        )
        result = validator._summarize_test_output(output)
        # No error context — just result summary
        assert "Error detail:" not in result
        assert "Result:" in result
        assert "passed" in result

    def test_truncation_at_max_length(self, validator):
        """Output exceeding max_length is truncated with ellipsis."""
        # Build output that will produce a long summary
        long_error = "E   " + "x" * 2000
        output = "\n".join([long_error, "1 failed in 1.0s"])
        result = validator._summarize_test_output(output, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_no_keyword_matches_fallback_to_last_lines(self, validator):
        """When no keyword matches, falls back to last 3 lines."""
        output = (
            "Line one\n"
            "Line two\n"
            "Line three\n"
            "Line four\n"
            "Line five\n"
        )
        result = validator._summarize_test_output(output)
        # Should include last 3 lines and no Error detail or Result
        assert "Error detail:" not in result
        assert "Result:" not in result
        assert "Line three" in result or "Line four" in result or "Line five" in result

    def test_default_max_length_is_1000(self, validator):
        """Default max_length is 1000, not 500."""
        import inspect
        sig = inspect.signature(validator._summarize_test_output)
        assert sig.parameters["max_length"].default == 1000

    def test_error_context_window_lines_around_error(self, validator):
        """Error context captures 1 line before and 3 after the error line."""
        output = (
            "context before error\n"
            "E   ValueError: bad value\n"
            "  after line 1\n"
            "  after line 2\n"
            "  after line 3\n"
            "1 failed in 0.1s\n"
        )
        result = validator._summarize_test_output(output)
        assert "Error detail:" in result
        assert "context before error" in result
        assert "ValueError" in result

    def test_operational_error_db_connection_captured(self, validator):
        """The exact TASK-DB-003 failure pattern includes error context."""
        output = (
            "collected 3 items\n"
            "\n"
            "tests/users/test_users.py::TestUserCreate::test_create_user FAILED\n"
            "\n"
            "ERRORS\n"
            "E   sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)\n"
            "E   could not connect to server: Connection refused\n"
            'E       Is the server running on host "localhost" (127.0.0.1)\n'
            "E       and accepting TCP/IP connections on port 5432?\n"
            "\n"
            "1 failed in 1.7s\n"
        )
        result = validator._summarize_test_output(output)
        assert "Error detail:" in result
        assert "OperationalError" in result


# ============================================================================
# R3: _normalize_to_relative and _detect_tests_from_results tests
# ============================================================================


class TestNormalizeToRelative:
    """Tests for _normalize_to_relative method."""

    def test_absolute_path_under_worktree_returns_relative(self, tmp_worktree):
        """Absolute path that is under worktree is converted to relative."""
        validator = CoachValidator(worktree_path=str(tmp_worktree))
        abs_path = str(tmp_worktree / "tests" / "unit" / "test_foo.py")
        result = validator._normalize_to_relative(abs_path)
        assert result == "tests/unit/test_foo.py"
        assert not Path(result).is_absolute()

    def test_relative_path_returned_unchanged(self, tmp_worktree):
        """Relative path is returned as-is."""
        validator = CoachValidator(worktree_path=str(tmp_worktree))
        rel_path = "tests/unit/test_foo.py"
        result = validator._normalize_to_relative(rel_path)
        assert result == rel_path

    def test_absolute_path_outside_worktree_returned_unchanged(self, tmp_worktree):
        """Absolute path NOT under worktree is returned unchanged."""
        validator = CoachValidator(worktree_path=str(tmp_worktree))
        outside_path = "/some/other/path/test_foo.py"
        result = validator._normalize_to_relative(outside_path)
        assert result == outside_path


class TestDetectTestsFromResultsDeduplication:
    """
    Tests for _detect_tests_from_results with mixed abs/rel duplicate paths.
    """

    def test_mixed_abs_rel_duplicates_deduplicated(self, tmp_worktree):
        """
        When files_created has the same test file listed as both an absolute path
        and a relative path, the result should contain only a single entry.
        """
        validator = CoachValidator(worktree_path=str(tmp_worktree))

        # Create the actual test file so full_path.exists() passes
        test_file_rel = "tests/unit/test_dedup.py"
        test_file_abs = str(tmp_worktree / test_file_rel)
        test_file_path = tmp_worktree / test_file_rel
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text("# test file\n")

        task_work_results = {
            "files_created": [
                test_file_abs,   # absolute path
                test_file_rel,   # relative path (same file)
            ],
            "files_modified": [],
        }

        cmd = validator._detect_tests_from_results(task_work_results)

        assert cmd is not None
        # The pytest command should list the file exactly once
        parts = cmd.split()
        test_files_in_cmd = [p for p in parts if "test_dedup.py" in p]
        assert len(test_files_in_cmd) == 1, (
            f"Expected exactly 1 entry for test_dedup.py but got {test_files_in_cmd}"
        )

    def test_relative_path_only_works(self, tmp_worktree):
        """Relative-only path still works correctly after normalization."""
        validator = CoachValidator(worktree_path=str(tmp_worktree))

        test_file_rel = "tests/unit/test_relative.py"
        test_file_path = tmp_worktree / test_file_rel
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text("# test file\n")

        task_work_results = {
            "files_created": [test_file_rel],
            "files_modified": [],
        }

        cmd = validator._detect_tests_from_results(task_work_results)
        assert cmd is not None
        assert "test_relative.py" in cmd
