"""
Unit tests for TASK-PCTD-5208 quick wins:
  R1 - Enhanced _summarize_test_output() with error context
  R2 - (normalized feedback text for stall detection: deleted with the
       stall detectors, 27 October 2026)
  R3 - (path deduplication in test detection: deleted with the guessed
       test commands, 31 October 2026)

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
