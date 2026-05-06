"""Integration tests proving CoachVerifier is wired into CoachValidator.

Tests for AC-007 / AC-008 / AC-009 / AC-010 of TASK-AB-FIX-INVAB1:

- AC-007: Honesty restoration test — Player lying about ``files_created``
  must trigger a ``honesty`` issue with ``claim_type == 'file_existence'``.
  This proves CoachVerifier is being invoked from CoachValidator.

- AC-008: FEAT-6CC5 reproducer — sophisticated Player keeps
  ``files_created`` honest (autobuild metadata that does exist) but lies in
  ``completion_promises[*].implementation_files``. The new
  ``promise_file_existence`` discrepancy must surface.

- AC-009: Backwards-compatibility — when the Player report is fully honest
  (all claimed files exist, all promises true), behaviour matches today's
  approve path with no spurious ``honesty`` issues.

- AC-010: Idempotency — running ``CoachValidator.validate`` twice on the
  same inputs yields identical decisions / issue payloads.

These tests run filesystem-only — no SDK invocations, no live pytest
runs against the host repo. CoachValidator's ``run_independent_tests`` is
patched out via subprocess.run mock so the focus is honesty wiring.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree: Path) -> Path:
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _passing_baseline(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Baseline task_work_results that would otherwise approve."""
    base: Dict[str, Any] = {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 5,
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"status": "skipped", "violations": 0},
        "files_created": [],
        "files_modified": [],
        "tests_written": [],
        "tests_run": False,  # avoid CoachVerifier running pytest
        "test_output_summary": "",
        "completion_promises": [],
        "requirements_addressed": [],
        "requirements_met": ["AC-001"],
    }
    if extra:
        base.update(extra)
    return base


def _write_results(results_dir: Path, results: Dict[str, Any]) -> Path:
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    return results_path


def _task() -> Dict[str, Any]:
    return {"acceptance_criteria": ["AC-001"]}


# ---------------------------------------------------------------------------
# AC-007: Honesty wiring proof — file_existence
# ---------------------------------------------------------------------------


def test_ac007_player_claims_missing_file_triggers_honesty_feedback(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-007: Player claims a file exists; verifier disagrees → feedback."""
    results = _passing_baseline({
        "files_created": ["src/repro/never_created.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="5 passed in 0.1s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _task())

    assert result.decision == "feedback", (
        f"Expected feedback when Player lies about file existence, got "
        f"{result.decision}. Issues: {result.issues}"
    )
    honesty_issues = [
        i for i in result.issues if i.get("category") == "honesty"
    ]
    assert len(honesty_issues) >= 1, (
        f"Expected at least one honesty issue, got issues: {result.issues}"
    )
    # The discrepancy must specifically reference file_existence (the
    # claim_type CoachVerifier produces for files_created lies).
    file_existence_issues = [
        i for i in honesty_issues
        if i.get("details", {}).get("claim_type") == "file_existence"
    ]
    assert len(file_existence_issues) >= 1, (
        f"Expected file_existence claim_type, got: {honesty_issues}"
    )


# ---------------------------------------------------------------------------
# AC-008: FEAT-6CC5 reproducer — sophisticated promise lie
# ---------------------------------------------------------------------------


def test_ac008_feat_6cc5_reproducer_promise_implementation_file_missing(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-008: Player keeps files_created honest but lies in completion_promises."""
    # Pre-create the metadata file (Player honestly lists this) but NOT
    # the source file that Player promises is "complete".
    metadata_file = tmp_worktree / ".guardkit" / "autobuild" / "some_metadata.json"
    metadata_file.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.write_text("{}")

    results = _passing_baseline({
        "files_created": [".guardkit/autobuild/some_metadata.json"],
        "tests_run": True,
        "test_output_summary": "29 passed in 0.26s",
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 29,
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "criterion_text": "src/repro/missing.py exists",
                "status": "complete",
                "evidence": "Module created and tested.",
                "implementation_files": ["src/repro/missing.py"],
            }
        ],
        "requirements_addressed": ["AC-001 implemented"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="29 passed in 0.26s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _task())

    assert result.decision == "feedback", (
        f"FEAT-6CC5 reproducer: expected feedback; got {result.decision}. "
        f"Issues: {result.issues}"
    )
    honesty_issues = [
        i for i in result.issues if i.get("category") == "honesty"
    ]
    promise_lies = [
        i for i in honesty_issues
        if i.get("details", {}).get("claim_type") == "promise_file_existence"
    ]
    assert len(promise_lies) >= 1, (
        f"Expected promise_file_existence claim_type, got: {honesty_issues}"
    )
    assert "src/repro/missing.py" in promise_lies[0].get("details", {}).get(
        "player_claim", ""
    )


# ---------------------------------------------------------------------------
# AC-009: Backwards compatibility — honest report behaves as today
# ---------------------------------------------------------------------------


def test_ac009_honest_report_no_spurious_honesty_issues(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-009: Honest player report → no honesty issues; gates evaluated normally."""
    # Pre-create every file the Player will claim.
    src_file = tmp_worktree / "src" / "real.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("def real(): pass\n")

    results = _passing_baseline({
        "files_created": ["src/real.py"],
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": "complete",
                "implementation_files": ["src/real.py"],
            }
        ],
        "requirements_addressed": ["AC-001 implemented in src/real.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="5 passed in 0.1s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _task())

    honesty_issues = [
        i for i in result.issues if i.get("category") == "honesty"
    ]
    assert honesty_issues == [], (
        f"Honest report yielded spurious honesty issues: {honesty_issues}"
    )


# ---------------------------------------------------------------------------
# AC-010: Idempotency — repeated validate() calls match
# ---------------------------------------------------------------------------


def test_ac010_idempotent_validation_on_dishonest_report(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-010: Validate() twice on the same input yields equivalent decisions."""
    results = _passing_baseline({
        "files_created": ["src/missing.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="5 passed in 0.1s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        first = validator.validate("TASK-001", 1, _task())
        second = validator.validate("TASK-001", 1, _task())

    assert first.decision == second.decision

    def _categories(issues):
        return sorted(i.get("category") for i in issues if i.get("category"))

    assert _categories(first.issues) == _categories(second.issues)


# ---------------------------------------------------------------------------
# AC-003: honesty_verification surfaces in to_dict()
# ---------------------------------------------------------------------------


def test_ac003_to_dict_includes_honesty_verification_block(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-003: ``to_dict()`` of the result must expose honesty_verification fields."""
    results = _passing_baseline({"files_created": ["src/missing.py"]})
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="5 passed in 0.1s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _task())

    payload = result.to_dict()
    assert "honesty_verification" in payload
    honesty = payload["honesty_verification"]
    assert "verified" in honesty
    assert "honesty_score" in honesty
    assert "discrepancy_count" in honesty
    assert honesty["verified"] is False
    assert honesty["discrepancy_count"] >= 1


# ---------------------------------------------------------------------------
# AC-006: AC-cited missing test files short-circuit the independent-test gate
# ---------------------------------------------------------------------------


def test_ac006_ac_cited_missing_test_short_circuits_to_feedback(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-006 wire-in proof: AC names a missing test file → feedback before pytest.

    The unit test for ``_detect_ac_cited_missing_test_files`` exercises the
    helper in isolation. This test proves the helper is wired into
    ``CoachValidator.validate()`` and actually fails the gate — i.e. the
    helper is not dead code.
    """
    # Honest baseline so the AC-002 honesty gate doesn't fire first; we
    # want to isolate the AC-006 short-circuit. Player has produced a real
    # source file and reports nothing about test files (because they
    # weren't created — that's the AC-006 case).
    src_file = tmp_worktree / "src" / "real.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("def real(): pass\n")

    results = _passing_baseline({
        "files_created": ["src/real.py"],
    })
    _write_results(task_work_results_dir, results)

    task_with_test_path = {
        "acceptance_criteria": [
            "AC-001: tests in tests/test_real.py pass"
        ]
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="29 passed in 0.26s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task_with_test_path)

    assert result.decision == "feedback", (
        f"Expected feedback when AC names missing test file; got "
        f"{result.decision}. Issues: {result.issues}"
    )
    ac_issues = [
        i for i in result.issues
        if i.get("category") == "acceptance_criteria"
    ]
    assert len(ac_issues) >= 1, (
        f"Expected acceptance_criteria issue; got: {result.issues}"
    )
    missing = ac_issues[0].get("details", {}).get("missing_test_files", [])
    assert "tests/test_real.py" in missing, (
        f"Expected tests/test_real.py in missing_test_files; got: {missing}"
    )
    # Quality gates must NOT have been consulted — short-circuit semantics.
    assert result.quality_gates is None
    assert result.independent_tests is None


def test_ac006_existing_test_file_does_not_short_circuit(
    tmp_worktree: Path, task_work_results_dir: Path
):
    """AC-006 negative case: when the AC-cited test file exists, no AC-006 short-circuit fires.

    Decision is whatever the downstream gates produce — what matters here
    is that no ``acceptance_criteria`` / ``missing_test_files`` issue
    appears (i.e. AC-006 itself didn't trigger).
    """
    test_file = tmp_worktree / "tests" / "test_real.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_real(): assert True\n")
    src_file = tmp_worktree / "src" / "real.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("def real(): pass\n")

    results = _passing_baseline({
        "files_created": ["src/real.py", "tests/test_real.py"],
    })
    _write_results(task_work_results_dir, results)

    task_with_test_path = {
        "acceptance_criteria": [
            "AC-001: tests in tests/test_real.py pass"
        ]
    }

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0, stdout="5 passed in 0.1s", stderr=""
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, task_with_test_path)

    ac006_issues = [
        i for i in result.issues
        if i.get("category") == "acceptance_criteria"
        and "missing_test_files" in (i.get("details") or {})
    ]
    assert ac006_issues == [], (
        f"AC-006 fired spuriously when test file exists: {ac006_issues}"
    )
