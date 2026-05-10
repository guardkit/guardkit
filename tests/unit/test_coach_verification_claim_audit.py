"""Unit tests for CoachVerifier._verify_claims_were_staged.

Covers TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT acceptance criteria AC-001 — AC-007
at the verifier-method layer. Uses real git repos (not mocks) so the
gitignore reproducer actually exercises git's filtering — the FEAT-39E1
class of silent loss is by definition a git-config-vs-Player-claim
disagreement, and a mock would let any of the rules drift without
detection.

The integration wiring through CoachValidator is exercised in
``tests/integration/orchestrator/test_coach_claim_audit.py``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    Discrepancy,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def git_worktree(tmp_path: Path) -> Path:
    """A real git repo with one base commit, ready to host Player edits."""
    repo = tmp_path / "worktree"
    repo.mkdir()
    _git("init", "--initial-branch=main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    # Base commit so HEAD exists.
    (repo / "README.md").write_text("base\n")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-m", "base", cwd=repo)
    return repo


@pytest.fixture
def verifier(git_worktree: Path) -> CoachVerifier:
    return CoachVerifier(git_worktree)


# ---------------------------------------------------------------------------
# AC-005: gitignored file is rejected
# ---------------------------------------------------------------------------


def test_ac005_gitignored_file_produces_claim_audit_discrepancy(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Reproducer for FEAT-39E1: Player creates a file under an unanchored
    ``adapters/`` rule. The file is on disk so ``_verify_files_exist`` is
    silent. ``_verify_claims_were_staged`` must catch it.
    """
    # Set up the unanchored gitignore rule that bit study-tutor.
    (git_worktree / ".gitignore").write_text("adapters/\n")
    # Player creates the source module — exists on disk, but git will
    # silently skip it on `git add -A`.
    src = git_worktree / "src" / "study_tutor" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    report: Dict[str, Any] = {
        "files_created": ["src/study_tutor/adapters/manifest.py"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "claim_audit"
    assert discrepancies[0].severity == "critical"
    assert "src/study_tutor/adapters/manifest.py" in discrepancies[0].player_claim
    # The actual_value must hint at the gitignore root cause so the next
    # turn's Player has actionable feedback.
    assert "gitignore" in discrepancies[0].actual_value.lower()


# ---------------------------------------------------------------------------
# AC-006: zero-cardinality permissive
# ---------------------------------------------------------------------------


def test_ac006_zero_claimed_files_returns_no_discrepancies(
    verifier: CoachVerifier,
) -> None:
    """Documentation-only / zero-attempted turn: gate emits nothing.

    Pair-with-attempted-count semantics from
    ``.claude/rules/absence-of-failure-is-not-success.md`` — the gate
    must be permissive when the Player legitimately has no file claims,
    not raise a no-op critical.
    """
    report: Dict[str, Any] = {
        "files_created": [],
        "files_modified": [],
        "tests_written": [],
        "completion_promises": [],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []


def test_ac006_missing_claim_keys_returns_no_discrepancies(
    verifier: CoachVerifier,
) -> None:
    """Zero-cardinality also fires when the Player omitted the keys
    entirely (not just empty lists)."""
    discrepancies = verifier._verify_claims_were_staged({})

    assert discrepancies == []


# ---------------------------------------------------------------------------
# AC-007: all claimed files staged → approval (no discrepancy)
# ---------------------------------------------------------------------------


def test_ac007_all_claims_staged_produces_no_discrepancies(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Player creates and modifies real files that git happily stages."""
    (git_worktree / "src").mkdir()
    (git_worktree / "src" / "real.py").write_text("def real(): pass\n")
    (git_worktree / "tests").mkdir()
    (git_worktree / "tests" / "test_real.py").write_text(
        "def test_real(): assert True\n"
    )

    report: Dict[str, Any] = {
        "files_created": ["src/real.py", "tests/test_real.py"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []


# ---------------------------------------------------------------------------
# Mixed scenario: N=2 claims, 1 staged, 1 dropped
# ---------------------------------------------------------------------------


def test_mixed_one_staged_one_dropped_surfaces_only_dropped(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """From the task spec §Test cases: 'Player claims tests/foo and src/foo;
    only the test file is staged. Should reject with both dropped paths
    surfaced.' This variant verifies only the dropped path is reported."""
    (git_worktree / ".gitignore").write_text("adapters/\n")
    (git_worktree / "tests").mkdir()
    (git_worktree / "tests" / "test_real.py").write_text(
        "def test_real(): assert True\n"
    )
    src = git_worktree / "src" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    report: Dict[str, Any] = {
        "files_created": ["tests/test_real.py", "src/adapters/manifest.py"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    paths = sorted(
        d.player_claim.split("Player claimed file ", 1)[-1]
        for d in discrepancies
    )
    assert paths == ["src/adapters/manifest.py"]


# ---------------------------------------------------------------------------
# Tracked-but-unchanged file the Player claims to have modified
# ---------------------------------------------------------------------------


def test_tracked_unchanged_modified_claim_rejected(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Player claims to modify ``README.md`` but didn't actually change it.
    ``git add -A`` won't put it in the next commit → should reject.
    """
    report: Dict[str, Any] = {
        "files_modified": ["README.md"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "claim_audit"
    assert "README.md" in discrepancies[0].player_claim


# ---------------------------------------------------------------------------
# completion_promises[*].implementation_files / test_file are also audited
# ---------------------------------------------------------------------------


def test_completion_promise_implementation_files_audited(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Per AC-001, the audit must also pull from
    ``completion_promises[*].implementation_files`` and ``test_file``.
    """
    (git_worktree / ".gitignore").write_text("adapters/\n")
    src = git_worktree / "src" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    report: Dict[str, Any] = {
        # Note: files_created is empty — the only place the path appears is
        # in completion_promises. The audit must still find it.
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": "complete",
                "implementation_files": ["src/adapters/manifest.py"],
                "test_file": "tests/test_manifest.py",
            }
        ],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    paths = sorted(
        d.player_claim.split("Player claimed file ", 1)[-1]
        for d in discrepancies
    )
    # Both manifest.py (gitignored) and the never-created test file are
    # rejected.
    assert paths == [
        "src/adapters/manifest.py",
        "tests/test_manifest.py",
    ]


# ---------------------------------------------------------------------------
# Path-normalization: leading ./ and trailing /
# ---------------------------------------------------------------------------


def test_leading_dot_slash_normalized(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """A Player who reports ``./src/foo.py`` shouldn't false-fail against
    git's ``src/foo.py`` output."""
    (git_worktree / "src").mkdir()
    (git_worktree / "src" / "foo.py").write_text("def foo(): pass\n")

    report: Dict[str, Any] = {
        "files_created": ["./src/foo.py"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []


# ---------------------------------------------------------------------------
# Fail-open: git command failure does not block gates
# ---------------------------------------------------------------------------


def test_non_git_worktree_fails_open(tmp_path: Path) -> None:
    """A worktree that isn't a git repo at all returns no discrepancies —
    the fail-open invariant prevents claim_audit from blocking gates on
    infrastructure errors (mirrors the ``_verify_files_exist`` posture)."""
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    verifier = CoachVerifier(not_a_repo)

    report: Dict[str, Any] = {"files_created": ["whatever.py"]}

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []


# ---------------------------------------------------------------------------
# verify_player_report integration: claim_audit surfaces alongside others
# ---------------------------------------------------------------------------


def test_verify_player_report_emits_claim_audit_alongside_other_checks(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """``CoachVerifier.verify_player_report`` (the public entry point used
    by ``agent_invoker._verify_player_claims``) must return the new
    claim_audit discrepancies in its discrepancy list."""
    (git_worktree / ".gitignore").write_text("adapters/\n")
    src = git_worktree / "src" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    report: Dict[str, Any] = {
        "files_created": ["src/adapters/manifest.py"],
        "tests_run": False,
    }

    verification = verifier.verify_player_report(report)

    audit = [
        d for d in verification.discrepancies if d.claim_type == "claim_audit"
    ]
    assert len(audit) == 1
    assert verification.verified is False
