"""
Unit tests for TASK-PCTD-5208 quick wins:
  R1 - Enhanced _summarize_test_output() with error context
  R2 - Normalized feedback text for stall detection
  R3 - Fixed duplicate path deduplication in test detection

Coverage Target: >=85%
Test Count: 25 tests
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
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


@pytest.fixture
def orchestrator():
    """Create an AutoBuildOrchestrator for stall detection tests."""
    return AutoBuildOrchestrator(
        repo_root=Path.cwd(),
        max_turns=5,
    )


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
# R2: _normalize_feedback_for_stall and _is_feedback_stalled tests
# ============================================================================


class TestNormalizeFeedbackForStall:
    """Tests for _normalize_feedback_for_stall method."""

    def test_strips_test_paths(self, orchestrator):
        """Test paths like tests/users/test_users.py::TestClass::test_method become FILE::TEST."""
        raw = "tests/users/test_users.py::TestUserCreate::test_create_user failed"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "FILE::TEST" in normalized
        assert "test_users.py" not in normalized
        assert "TestUserCreate" not in normalized

    def test_strips_root_level_test_paths(self, orchestrator):
        """Root-level test files without tests/ prefix are also normalized."""
        raw = "test_main.py::TestApp::test_startup failed"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "FILE::TEST" in normalized
        assert "test_main.py" not in normalized
        assert "TestApp" not in normalized

    def test_strips_line_numbers(self, orchestrator):
        """Line numbers like 'line 45' become 'line N'."""
        raw = "AssertionError at line 45 in test_auth.py"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "line N" in normalized
        assert "line 45" not in normalized

    def test_strips_percentages(self, orchestrator):
        """Percentages like '85.5%' become 'N%'."""
        raw = "Coverage is only 85.5%, needs to be at least 80%"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "N%" in normalized
        assert "85.5%" not in normalized

    def test_strips_durations(self, orchestrator):
        """Durations like 'in 1.7s' become 'in Ns'."""
        raw = "3 failed in 1.7s"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "in Ns" in normalized
        assert "in 1.7s" not in normalized

    def test_strips_test_counts(self, orchestrator):
        """Test counts like '5 passed' become 'N passed'."""
        raw = "5 passed, 2 failed, 1 error"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "N passed" in normalized
        assert "N failed" in normalized
        assert "N error" in normalized
        assert "5 passed" not in normalized

    def test_strips_worktree_paths(self, orchestrator):
        """Worktree absolute paths are normalized."""
        raw = "File not found: /home/user/.guardkit/worktrees/TASK-001/src/app.py"
        normalized = orchestrator._normalize_feedback_for_stall(raw)
        assert "/WORKTREE/" in normalized
        assert "/home/user/.guardkit/worktrees/TASK-001/" not in normalized


class TestIsFeedbackStalledWithNormalization:
    """Tests for _is_feedback_stalled using normalized feedback (R2 regression)."""

    def test_stall_fires_on_same_category_different_detail(self):
        """
        Key regression test: feedback with same category but different test
        class names / tracebacks should trigger stall after threshold turns.

        This is the TASK-DB-003 pattern: Coach keeps saying "test X failed"
        where X changes each turn, but it's the same underlying issue.
        """
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        # Three turns of same-category feedback but with different test details
        # After normalization, these should all hash the same.
        base_feedback = (
            "The following tests failed:\n"
            "tests/{test_file}::TestClass::test_method failed\n"
            "line {line} in test body\n"
            "3 failed in 1.5s\n"
        )

        fb1 = base_feedback.format(test_file="test_users.py", line=42)
        fb2 = base_feedback.format(test_file="test_orders.py", line=99)
        fb3 = base_feedback.format(test_file="test_products.py", line=17)

        r1 = orchestrator._is_feedback_stalled(fb1, 0)
        r2 = orchestrator._is_feedback_stalled(fb2, 0)
        r3 = orchestrator._is_feedback_stalled(fb3, 0)

        assert r1 is False
        assert r2 is False
        assert r3 is True, (
            "Stall should fire: after normalization all three feedback strings "
            "are identical in category"
        )

    def test_no_false_positive_genuinely_different_feedback(self):
        """Different feedback categories should NOT trigger false-positive stall."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        fb1 = "Missing docstrings in src/auth.py — add module-level docstring"
        fb2 = "Coverage is below threshold — add tests for edge cases"
        fb3 = "Type hints missing on get_user() function in models.py"

        r1 = orchestrator._is_feedback_stalled(fb1, 0)
        r2 = orchestrator._is_feedback_stalled(fb2, 0)
        r3 = orchestrator._is_feedback_stalled(fb3, 0)

        assert r1 is False
        assert r2 is False
        assert r3 is False, "Genuinely different feedback must not trigger stall"


class TestStallDetectionRegressionDB003:
    """
    Replay the TASK-DB-003 turn sequence pattern.

    The real failure: Player gets stuck and Coach repeatedly reports
    test failures in different test files each turn but with the same
    underlying category.  After normalization, turns 3-5 should be
    identical and fire stall at Turn 5 (after 3 consecutive matches).
    """

    def test_db003_pattern_stall_fires_at_turn_5(self):
        """
        TASK-DB-003 regression: Stall fires after 3 consecutive
        normalized-identical turns even if raw feedback differs.

        Turn 1-2: different feedback (different categories)
        Turn 3-5: same-category feedback (connection error, different details)
        -> stall fires at Turn 5
        """
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )

        # Turns 1-2: genuinely different feedback
        r1 = orchestrator._is_feedback_stalled(
            "Missing authentication middleware in middleware.py",
            0,
        )
        r2 = orchestrator._is_feedback_stalled(
            "Add unit tests for the UserRepository class",
            0,
        )

        # Turns 3-5: same error category but different test file details
        connection_template = (
            "Database connection failed in tests/{f}::TestDB::test_query\n"
            "E   OperationalError: could not connect to server\n"
            "1 failed in {t}s\n"
        )
        r3 = orchestrator._is_feedback_stalled(
            connection_template.format(f="test_users.py", t="0.12"),
            0,
        )
        r4 = orchestrator._is_feedback_stalled(
            connection_template.format(f="test_orders.py", t="0.34"),
            0,
        )
        r5 = orchestrator._is_feedback_stalled(
            connection_template.format(f="test_products.py", t="0.27"),
            0,
        )

        assert r1 is False
        assert r2 is False
        assert r3 is False
        assert r4 is False
        assert r5 is True, (
            "Stall must fire at turn 5 when turns 3-5 have same normalized signature"
        )


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
