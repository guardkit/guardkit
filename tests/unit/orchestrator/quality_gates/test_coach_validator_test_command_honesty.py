"""AC-006 tests: independent test-command must surface AC-cited missing tests.

Background: when an AC names a specific test file (e.g. "all tests in
``tests/test_login.py`` pass") and that file does not exist on disk,
``CoachValidator._detect_test_command`` silently falls back to running the
existing-test set and reports green. AC-006 requires emitting a
``must_fix`` issue (category ``acceptance_criteria``) instead.

This test exercises the helper directly. Tests for the wire-in into
``run_independent_tests`` live in
``tests/integration/orchestrator/test_coach_honesty_restoration.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


def _detect_missing(
    validator: CoachValidator, acceptance_criteria: List[str]
) -> List[str]:
    """Helper: invoke the AC-cited-test-file existence check directly."""
    return validator._detect_ac_cited_missing_test_files(acceptance_criteria)


def test_ac006_python_test_path_detected_when_missing(tmp_worktree: Path):
    """AC text names tests/test_login.py and file is absent → reported."""
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: tests in tests/test_login.py pass"],
    )
    assert "tests/test_login.py" in missing


def test_ac006_python_test_path_existing_not_reported(tmp_worktree: Path):
    """AC names tests/test_login.py and file exists → not reported."""
    target = tmp_worktree / "tests" / "test_login.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def test_x(): assert True\n")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: tests in tests/test_login.py pass"],
    )
    assert missing == []


def test_ac006_underscore_test_suffix_detected(tmp_worktree: Path):
    """AC names `tests/login_test.py` (underscore suffix) and file is absent."""
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: see tests/login_test.py"],
    )
    assert "tests/login_test.py" in missing


def test_ac006_no_test_path_in_ac_returns_empty(tmp_worktree: Path):
    """AC text mentions no test paths → empty list."""
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: ensure helpful logging on error"],
    )
    assert missing == []


def test_ac006_non_test_python_file_path_not_reported(tmp_worktree: Path):
    """AC names src/login.py — not a test path → not reported by this helper."""
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: implement src/login.py"],
    )
    # The helper only flags test-file paths; source-file existence is the
    # plan_audit gate's concern (AC-005), not AC-006.
    assert missing == []


def test_ac006_multiple_test_paths_detected(tmp_worktree: Path):
    """Multiple AC-cited test files: only the missing ones are reported."""
    existing = tmp_worktree / "tests" / "test_a.py"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("def test_a(): assert True\n")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        [
            "AC-001: tests/test_a.py passes",
            "AC-002: tests/test_b.py also passes",
        ],
    )
    assert "tests/test_b.py" in missing
    assert "tests/test_a.py" not in missing
