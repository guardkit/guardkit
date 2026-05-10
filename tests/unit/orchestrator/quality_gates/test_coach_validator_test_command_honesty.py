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


# ---------------------------------------------------------------------------
# TASK-AB-006: AC-linter must not parse pytest commands as literal paths.
#
# Regression coverage for the FG-004 stall pattern: when an AC body wraps a
# pytest invocation in backticks (e.g. ``pytest tests/test_openwebui_pipe.py``),
# the over-captured command-line string was failing disk-existence under
# ``_detect_ac_cited_missing_test_files`` and short-circuiting the
# independent-test gate even when the cited file was on disk.
# ---------------------------------------------------------------------------


def _make_existing_test(tmp_worktree: Path, relpath: str) -> Path:
    target = tmp_worktree / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("def test_x(): assert True\n")
    return target


def test_ab006_backtick_pytest_command_does_not_smuggle_runner_into_path(
    tmp_worktree: Path,
):
    """`pytest tests/foo.py` in AC must check tests/foo.py, not the whole command."""
    _make_existing_test(tmp_worktree, "tests/test_openwebui_pipe.py")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        [
            "AC-001: `pytest tests/test_openwebui_pipe.py` exits 0 with all tests passing",
        ],
    )
    # The exact FG-004 reproducer: literal command must not appear as a
    # missing path, and the bare path resolves on disk so no missing entry.
    assert "pytest tests/test_openwebui_pipe.py" not in missing
    assert missing == []


def test_ab006_backtick_pytest_command_with_missing_file_still_flagged(
    tmp_worktree: Path,
):
    """Tokenisation must not mask a genuinely missing AC-cited test file."""
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        [
            "AC-001: `pytest tests/test_missing.py` passes",
        ],
    )
    # The bare file path is still extracted and disk-checked.
    assert "tests/test_missing.py" in missing
    # The runner-prefixed form must not be reported.
    assert "pytest tests/test_missing.py" not in missing


def test_ab006_pytest_command_with_flags_extracts_path_only(tmp_worktree: Path):
    """`pytest -v tests/foo.py`: flags drop, file path is what's checked."""
    _make_existing_test(tmp_worktree, "tests/test_with_flags.py")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: `pytest -v tests/test_with_flags.py` passes"],
    )
    assert missing == []


def test_ab006_pytest_node_id_suffix_stripped_from_backtick(tmp_worktree: Path):
    """`pytest tests/foo.py::test_bar` strips ::test_bar before disk-check."""
    _make_existing_test(tmp_worktree, "tests/test_node_id.py")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: `pytest tests/test_node_id.py::test_specific` passes"],
    )
    assert missing == []
    # Composite node-ID must not be reported as a missing path.
    assert "tests/test_node_id.py::test_specific" not in missing


def test_ab006_pytest_node_id_suffix_stripped_without_runner(tmp_worktree: Path):
    """Bare backtick `tests/foo.py::test_bar` (no `pytest` prefix) also stripped."""
    _make_existing_test(tmp_worktree, "tests/test_bare_node_id.py")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: `tests/test_bare_node_id.py::test_x` passes"],
    )
    assert missing == []


def test_ab006_python_module_pytest_prefix_recognised(tmp_worktree: Path):
    """`python -m pytest tests/foo.py` extracts tests/foo.py."""
    _make_existing_test(tmp_worktree, "tests/test_python_m.py")

    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: `python -m pytest tests/test_python_m.py` passes"],
    )
    assert missing == []


def test_ab006_non_pytest_runner_no_path_yields_no_findings(tmp_worktree: Path):
    """`npm test` / `dotnet test --filter Category=Unit` yield no AC-006 finding.

    Documented behaviour (per the helper's docstring): non-pytest runners with
    no path-shaped argument produce no AC-cited-missing-test-files findings.
    Stacks needing disk-existence verification for non-pytest runners must
    cite the test file path explicitly in the AC text.
    """
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        [
            "AC-001: `npm test` passes",
            "AC-002: `dotnet test --filter Category=Unit` passes",
        ],
    )
    assert missing == []


def test_ab006_bare_backtick_path_still_extracted(tmp_worktree: Path):
    """No regression: backtick-quoted bare paths (no whitespace) still work."""
    validator = CoachValidator(str(tmp_worktree))
    missing = _detect_missing(
        validator,
        ["AC-001: see `tests/test_bare_backtick.py`"],
    )
    assert "tests/test_bare_backtick.py" in missing


def test_ab006_extract_paths_from_ac_text_directly(tmp_worktree: Path):
    """Helper-level: command-line content yields just the path token."""
    validator = CoachValidator(str(tmp_worktree))
    paths = validator._extract_paths_from_ac_text(
        "Run `pytest tests/test_openwebui_pipe.py` and assert exit 0"
    )
    # The bare file path must be present; the command-line string must not.
    assert "tests/test_openwebui_pipe.py" in paths
    assert "pytest tests/test_openwebui_pipe.py" not in paths
    # `pytest` alone must not be captured as a path either.
    assert "pytest" not in paths
