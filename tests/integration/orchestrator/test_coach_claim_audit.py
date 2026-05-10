"""Integration tests for the claim_audit gate on the deterministic Coach path.

Proves TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT acceptance criteria
AC-003 / AC-005 / AC-006 / AC-007 are wired through CoachValidator:

- AC-003: dropped paths produce a Coach ``must_fix`` issue with
  ``category: "claim_audit"`` and ``decision: "feedback"``.
- AC-005: synthetic Player report claims a ``.gitignore``-d path → reject.
- AC-006: zero claimed files → no claim_audit issue (gate stays out of
  the way of legitimately documentation-only turns).
- AC-007: every claimed file is stage-able → no claim_audit issue.

These tests use a real git repo to exercise actual gitignore filtering —
the FEAT-39E1 silent-loss class is by definition a Player-vs-git-config
disagreement, and a mock would hide rule drift.
"""

from __future__ import annotations

import json
import subprocess
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
# Selective subprocess mock
# ---------------------------------------------------------------------------
#
# CoachValidator runs both ``run_independent_tests`` (pytest) and
# ``_verify_claims_were_staged`` (``git status --porcelain=v1``). The
# existing test pattern in ``test_coach_honesty_restoration.py`` mocks
# subprocess.run uniformly — that would also intercept the git call and
# force every claimed path into the dropped set, masking real behaviour.
#
# Instead we capture the real ``subprocess.run`` before patching and
# delegate ``git`` invocations to the real binary while continuing to
# stub pytest.

_REAL_RUN = subprocess.run


def _selective_run(*args: Any, **kwargs: Any) -> Any:
    """side_effect that lets git through and mocks everything else."""
    if args:
        cmd = args[0]
    else:
        cmd = kwargs.get("args") or []
    if cmd and isinstance(cmd, (list, tuple)) and cmd[0] == "git":
        return _REAL_RUN(*args, **kwargs)
    # Stub pytest / coverage / anything else as a clean pass.
    return MagicMock(returncode=0, stdout="5 passed in 0.1s", stderr="")


# ---------------------------------------------------------------------------
# Real git worktree fixture
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return _REAL_RUN(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def git_worktree(tmp_path: Path) -> Path:
    """A real git repo with one base commit."""
    repo = tmp_path / "worktree"
    repo.mkdir()
    _git("init", "--initial-branch=main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "README.md").write_text("base\n")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-m", "base", cwd=repo)
    return repo


@pytest.fixture
def task_work_results_dir(git_worktree: Path) -> Path:
    results_dir = git_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _passing_baseline(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A task_work_results that would otherwise approve."""
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
        "tests_run": False,
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
# AC-003 / AC-005: gitignored Player file → must_fix claim_audit issue
# ---------------------------------------------------------------------------


def test_ac005_gitignored_file_triggers_claim_audit_feedback(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """The FEAT-39E1 reproducer end-to-end: file on disk, gitignored,
    Coach must reject the turn with a claim_audit issue."""
    # Unanchored .gitignore rule (the same shape that bit study-tutor).
    (git_worktree / ".gitignore").write_text("adapters/\n")
    # Player creates the source module in the worktree.
    src = git_worktree / "src" / "study_tutor" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    results = _passing_baseline({
        "files_created": ["src/study_tutor/adapters/manifest.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    assert result.decision == "feedback", (
        f"Expected feedback when Player claims a gitignored file, got "
        f"{result.decision}. Issues: {result.issues}"
    )
    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert len(audit_issues) == 1, (
        f"Expected exactly one claim_audit issue, got: {result.issues}"
    )
    issue = audit_issues[0]
    assert issue["severity"] == "must_fix"
    assert issue["details"]["claim_type"] == "claim_audit"
    assert "src/study_tutor/adapters/manifest.py" in issue["description"]


# ---------------------------------------------------------------------------
# AC-006: zero-cardinality permissive
# ---------------------------------------------------------------------------


def test_ac006_zero_claimed_files_does_not_trigger_claim_audit(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """Documentation-only turn: zero file claims must not emit claim_audit
    feedback. (Other gates may still produce decisions; what matters here
    is that the claim_audit category is absent.)"""
    results = _passing_baseline()  # all file lists empty
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert audit_issues == [], (
        f"Zero-cardinality turn yielded spurious claim_audit issues: "
        f"{audit_issues}"
    )


# ---------------------------------------------------------------------------
# AC-007: all claimed files staged → no claim_audit issue
# ---------------------------------------------------------------------------


def test_ac007_all_files_stageable_does_not_trigger_claim_audit(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """Player creates real source + test files, no gitignore filter →
    claim_audit must remain silent."""
    (git_worktree / "src").mkdir()
    (git_worktree / "src" / "real.py").write_text("def real(): pass\n")
    (git_worktree / "tests").mkdir()
    (git_worktree / "tests" / "test_real.py").write_text(
        "def test_real(): assert True\n"
    )

    results = _passing_baseline({
        "files_created": ["src/real.py", "tests/test_real.py"],
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": "complete",
                "implementation_files": ["src/real.py"],
                "test_file": "tests/test_real.py",
            }
        ],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert audit_issues == [], (
        f"All-staged turn yielded spurious claim_audit issues: "
        f"{audit_issues}"
    )


# ---------------------------------------------------------------------------
# claim_audit must_fix short-circuits gate evaluation
# ---------------------------------------------------------------------------


def test_claim_audit_short_circuits_gate_evaluation(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """A claim_audit must_fix issue must short-circuit before the
    independent-test gate runs (mirroring the must_fix honesty path).
    The signal is: ``result.quality_gates`` and ``result.independent_tests``
    are both None when claim_audit fires alone."""
    (git_worktree / ".gitignore").write_text("adapters/\n")
    src = git_worktree / "src" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    results = _passing_baseline({
        "files_created": ["src/adapters/manifest.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    assert result.decision == "feedback"
    assert result.quality_gates is None
    assert result.independent_tests is None


# ---------------------------------------------------------------------------
# claim_audit issues retain must_fix even when only one discrepancy fires
# (i.e. the FEAT-FFC3 single-discrepancy demotion does NOT apply to claim_audit)
# ---------------------------------------------------------------------------


def test_single_claim_audit_not_demoted_to_should_fix(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """The FEAT-FFC3 demotion (single ``file_existence`` → should_fix) must
    not apply to ``claim_audit``: even one dropped path is enough signal
    to reject the turn."""
    (git_worktree / ".gitignore").write_text("adapters/\n")
    src = git_worktree / "src" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    results = _passing_baseline({
        "files_created": ["src/adapters/manifest.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert len(audit_issues) == 1
    assert audit_issues[0]["severity"] == "must_fix"
