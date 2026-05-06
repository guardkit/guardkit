"""Hybrid-fallback regression tests for AC-004 / AC-011 of TASK-AB-FIX-INVAB1.

Background: ``CoachValidator._hybrid_fallback`` was upgrading rejected
criteria back to ``verified`` whenever the Player's text in
``requirements_addressed`` had ≥70% keyword overlap with the AC text. Two
upgrade branches existed:

1. ``"No completion promise"`` branch — for the case where Player wrote
   no completion_promises at all (TASK-REV-E719 Fix 2). Legitimate, but
   needs tightening so it can't upgrade based on Player text that names
   a file path that doesn't exist on disk.

2. ``"Promise status: incomplete"`` branch — used to forgive a
   Player-self-reported incomplete promise via Player-self-reported text.
   This was identified by TASK-INV-AB1 as the second-order corruption
   path: it allowed text fallback to overrule the deterministic verifier.
   Removed as part of AC-004.

These tests establish the post-fix invariants:

- AC-011a (this file): the ``Promise status: incomplete`` branch must NOT
  upgrade rejected criteria, even when ``requirements_addressed`` keyword
  overlap exceeds 70%.
- AC-011b (this file): the ``"No completion promise"`` branch still
  upgrades correctly when no file path is named in the AC text.
- AC-011c (this file): the ``"No completion promise"`` branch must NOT
  upgrade when the AC names a file path that does not exist on disk.
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
from guardkit.orchestrator.quality_gates.coach_validator import (
    CriterionResult,
    RequirementsValidation,
)


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


def _make_promise_validation(
    acceptance_criteria: List[str],
    promise_evidence: str,
) -> RequirementsValidation:
    """Build a RequirementsValidation where every criterion is rejected with
    the supplied evidence text — simulating the output of ``_match_by_promises``."""
    results = []
    for i, ac_text in enumerate(acceptance_criteria, start=1):
        results.append(
            CriterionResult(
                criterion_id=f"AC-{i:03d}",
                criterion_text=ac_text,
                result="rejected",
                status="rejected",
                evidence=promise_evidence,
            )
        )
    return RequirementsValidation(
        criteria_total=len(acceptance_criteria),
        criteria_met=0,
        all_criteria_met=False,
        missing=list(acceptance_criteria),
        criteria_results=results,
    )


# ---------------------------------------------------------------------------
# AC-011a: Promise status: incomplete branch removed
# ---------------------------------------------------------------------------


def test_ac011a_promise_status_incomplete_does_not_upgrade(tmp_worktree: Path):
    """AC-011a: ``Promise status: incomplete`` evidence must NOT upgrade via text fallback."""
    validator = CoachValidator(str(tmp_worktree))

    acceptance_criteria = [
        "implement authentication module with login and logout",
    ]
    requirements_addressed = [
        "implement authentication module with login and logout",
    ]

    promise_validation = _make_promise_validation(
        acceptance_criteria, "Promise status: incomplete"
    )

    merged = validator._hybrid_fallback(
        promise_validation, acceptance_criteria, requirements_addressed
    )

    # Post-fix: incomplete-status promises must NOT be upgraded by text.
    assert merged.all_criteria_met is False
    assert merged.criteria_results[0].result == "rejected"


# ---------------------------------------------------------------------------
# AC-011b: No completion promise branch still upgrades when AC has no file path
# ---------------------------------------------------------------------------


def test_ac011b_no_completion_promise_branch_still_upgrades_when_safe(
    tmp_worktree: Path,
):
    """AC-011b: ``No completion promise`` upgrade still works for path-free ACs."""
    validator = CoachValidator(str(tmp_worktree))

    acceptance_criteria = [
        "implement authentication module with login and logout",
    ]
    requirements_addressed = [
        "implement authentication module with login and logout",
    ]

    promise_validation = _make_promise_validation(
        acceptance_criteria, "No completion promise"
    )

    merged = validator._hybrid_fallback(
        promise_validation, acceptance_criteria, requirements_addressed
    )

    # AC text has no file path → branch still upgrades when text matches.
    assert merged.all_criteria_met is True
    assert merged.criteria_results[0].result == "verified"


# ---------------------------------------------------------------------------
# AC-011c: No completion promise branch must NOT upgrade when AC names a missing file
# ---------------------------------------------------------------------------


def test_ac011c_no_completion_promise_branch_blocks_upgrade_when_path_missing(
    tmp_worktree: Path,
):
    """AC-011c: AC names a file path that doesn't exist → no upgrade."""
    validator = CoachValidator(str(tmp_worktree))

    acceptance_criteria = [
        "src/auth/login.py implements authentication module login logout",
    ]
    requirements_addressed = [
        "src/auth/login.py implements authentication module login logout",
    ]

    promise_validation = _make_promise_validation(
        acceptance_criteria, "No completion promise"
    )

    merged = validator._hybrid_fallback(
        promise_validation, acceptance_criteria, requirements_addressed
    )

    # File doesn't exist on disk → upgrade must be blocked.
    assert merged.all_criteria_met is False
    assert merged.criteria_results[0].result == "rejected"


def test_ac011c_no_completion_promise_branch_upgrades_when_path_exists(
    tmp_worktree: Path,
):
    """AC-011c-paired: AC names a file path that DOES exist → upgrade still works."""
    validator = CoachValidator(str(tmp_worktree))

    # Pre-create the file the AC names.
    target = tmp_worktree / "src" / "auth" / "login.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# real")

    acceptance_criteria = [
        "src/auth/login.py implements authentication module login logout",
    ]
    requirements_addressed = [
        "src/auth/login.py implements authentication module login logout",
    ]

    promise_validation = _make_promise_validation(
        acceptance_criteria, "No completion promise"
    )

    merged = validator._hybrid_fallback(
        promise_validation, acceptance_criteria, requirements_addressed
    )

    # Path exists → branch behaves as today (upgrade allowed).
    assert merged.all_criteria_met is True
    assert merged.criteria_results[0].result == "verified"
