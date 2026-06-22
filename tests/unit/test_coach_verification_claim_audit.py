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
# AC-005: gitignored file is surfaced as a non-critical advisory
# (TASK-FIX-IGNR demoted this from severity="critical" to "should_fix";
# the discrepancy still surfaces, just under the narrower
# ``claim_audit_gitignored`` claim_type so Coach can route it to
# advisory feedback instead of a turn-rejecting short-circuit.)
# ---------------------------------------------------------------------------


def test_ac005_gitignored_file_produces_claim_audit_discrepancy(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Reproducer for FEAT-39E1: Player creates a file under an unanchored
    ``adapters/`` rule. The file is on disk so ``_verify_files_exist`` is
    silent. ``_verify_claims_were_staged`` must catch it under the
    ``claim_audit_gitignored`` claim_type with ``severity="should_fix"``
    (TASK-FIX-IGNR AC-1 reclassification).
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
    # TASK-FIX-IGNR: gitignored-but-present is now a should_fix advisory
    # under the dedicated claim_audit_gitignored claim_type, so Coach
    # short-circuit logic does not turn-reject the FEAT-39E1 shape.
    assert discrepancies[0].claim_type == "claim_audit_gitignored"
    assert discrepancies[0].severity == "should_fix"
    assert "src/study_tutor/adapters/manifest.py" in discrepancies[0].player_claim
    # The matched rule is exposed verbatim so the operator can fix the
    # .gitignore rather than chase Player honesty across turns.
    assert discrepancies[0].ignore_rule is not None
    assert ".gitignore" in discrepancies[0].ignore_rule
    assert "adapters/" in discrepancies[0].ignore_rule


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


def test_tracked_unchanged_modified_claim_demoted_to_should_fix(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Player claims to modify ``README.md`` but didn't actually change it.

    Pre-TASK-FIX-PCN this fired ``claim_type="claim_audit"`` with
    ``severity="critical"``, which short-circuited the gate. After
    TASK-FIX-PCN AC-6 the path is recognised as tracked-but-unmodified
    and demoted to ``claim_type="claim_audit_unmodified"`` with
    ``severity="should_fix"``: the discrepancy still surfaces (so the
    operator can see the noise), but the gate keeps evaluating the rest
    of the criteria. Defence-in-depth for the agent_invoker-side filter
    at ``_strip_orchestrator_managed_paths`` — see TASK-FIX-PCN.
    """
    report: Dict[str, Any] = {
        "files_modified": ["README.md"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    disc = discrepancies[0]
    assert disc.claim_type == "claim_audit_unmodified"
    assert disc.severity == "should_fix"
    assert "README.md" in disc.player_claim
    # The actual_value text mentions tracked-in-git so the operator can
    # disambiguate from the gitignored / fabricated cases.
    assert "tracked" in disc.actual_value.lower()


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
    by ``agent_invoker._verify_player_claims``) must return the
    claim_audit-family discrepancies in its discrepancy list.

    After TASK-FIX-IGNR the gitignored case now surfaces under
    ``claim_audit_gitignored``; we accept either ``claim_audit`` or
    ``claim_audit_gitignored`` here so the test catches the family.
    """
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
        d for d in verification.discrepancies
        if d.claim_type in {"claim_audit", "claim_audit_gitignored", "claim_audit_unmodified"}
    ]
    assert len(audit) == 1
    # ``verified`` remains False — the discrepancy still surfaces, just
    # at a lower severity than turn-rejecting critical.
    assert verification.verified is False


# ---------------------------------------------------------------------------
# TASK-FIX-IGNR AC-4: gitignored-but-present is should_fix, not critical
# ---------------------------------------------------------------------------


def test_claim_audit_gitignored_is_should_fix_not_critical(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Reproduces the FEAT-39E1 scenario through the public
    ``verify_player_report`` API so the should_fix accounting and
    ignore_rule plumbing are exercised end-to-end.

    Setup: ``.gitignore`` carries an unanchored ``adapters/`` rule and
    the Player authors ``src/pkg/adapters/foo.py`` on disk. Under the
    pre-IGNR contract this fired a critical claim_audit and short-
    circuited the gate (turn-1 → turn-5 adversarial blow-up). Under
    AC-1/AC-2 the discrepancy is should_fix, ``critical_failures`` is
    zero, and the matched rule is preserved on the discrepancy so
    Coach can render it back to the Player.
    """
    (git_worktree / ".gitignore").write_text("adapters/\n")
    src = git_worktree / "src" / "pkg" / "adapters"
    src.mkdir(parents=True)
    (src / "foo.py").write_text("class Foo: pass\n")

    report: Dict[str, Any] = {
        "files_created": ["src/pkg/adapters/foo.py"],
        "tests_run": False,
    }

    verification = verifier.verify_player_report(report)

    # AC-2: critical count is zero — the gitignored case no longer
    # contributes to the honesty critical_failures total.
    critical = [d for d in verification.discrepancies if d.severity == "critical"]
    assert critical == [], (
        f"Expected zero critical discrepancies for a gitignored-but-"
        f"present file; got: {critical}"
    )

    # AC-2: should_fix_count is exactly 1 (the one dropped path).
    assert verification.should_fix_count == 1

    # AC-1 + AC-4: the discrepancy is the new should_fix shape and
    # carries the matched ignore rule verbatim.
    assert len(verification.discrepancies) == 1
    disc = verification.discrepancies[0]
    assert disc.severity == "should_fix"
    assert disc.claim_type == "claim_audit_gitignored"
    assert disc.ignore_rule is not None
    assert ".gitignore" in disc.ignore_rule
    assert "adapters/" in disc.ignore_rule


# ---------------------------------------------------------------------------
# TASK-FIX-IGNR AC-5: actual fabrication (path not on disk) stays critical
# ---------------------------------------------------------------------------


def test_claim_audit_fabricated_path_still_critical(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Regression guard for the AC-1 split: when the Player claims a
    path that does not exist on disk, the discrepancy must remain
    ``severity="critical"`` under ``claim_type="claim_audit"`` so the
    short-circuit in ``coach_validator`` still rejects the turn.

    This is the inverse of AC-4: same gate, different input shape, and
    the contract for genuine fabrication is unchanged.
    """
    # Note: no file created on disk. ``src/study_tutor/adapters/missing.py``
    # is a pure Player invention.
    report: Dict[str, Any] = {
        "files_created": ["src/study_tutor/adapters/missing.py"],
        "tests_run": False,
    }

    verification = verifier.verify_player_report(report)

    # AC-5: the claim_audit-family discrepancy for the fabricated path
    # is critical claim_audit, not the demoted claim_audit_gitignored
    # shape. (verify_player_report also runs _verify_files_exist, which
    # produces its own critical file_existence discrepancy for the
    # missing path — that is orthogonal to AC-5 and is asserted
    # separately below.)
    audit = [
        d for d in verification.discrepancies
        if d.claim_type in {"claim_audit", "claim_audit_gitignored", "claim_audit_unmodified"}
    ]
    assert len(audit) == 1
    disc = audit[0]
    assert disc.severity == "critical"
    assert disc.claim_type == "claim_audit"
    assert disc.ignore_rule is None
    # No path was demoted — should_fix_count is zero.
    assert verification.should_fix_count == 0
    # And the file_existence gate still flags the missing path
    # (defence in depth — both gates remain wired).
    file_existence = [
        d for d in verification.discrepancies if d.claim_type == "file_existence"
    ]
    assert len(file_existence) == 1
    assert file_existence[0].severity == "critical"


# ---------------------------------------------------------------------------
# TASK-FIX-PCN AC-7: tracked-but-unmodified is should_fix, not critical
# ---------------------------------------------------------------------------


def test_claim_audit_tracked_unmodified_is_should_fix(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Reproduces the FEAT-39E1 PH1-005 shape through the public
    ``verify_player_report`` API: the Player report writer swept
    orchestrator-managed paths into ``files_modified`` and the Coach's
    claim audit short-circuited the gate on tracked-but-unchanged paths
    the Player never authored.

    Setup: README.md is committed in the base fixture. The Player
    "claims" to have modified it but didn't actually touch it. Pre-PCN
    this fired ``claim_type="claim_audit"`` with ``severity="critical"``
    and short-circuited the gate via ``_honesty_issues_from``. Under
    AC-6/AC-7 the discrepancy is ``claim_audit_unmodified`` with
    ``severity="should_fix"``: it surfaces in feedback as advisory while
    gate evaluation continues.

    Defence-in-depth: the load-bearing fix is the agent_invoker-side
    filter at ``_strip_orchestrator_managed_paths`` (TASK-FIX-PCN AC-2)
    which prevents the noisy paths from reaching the Coach in the first
    place. This Coach-side demotion guarantees the gate doesn't collapse
    even when the Player-side filter misses a path.
    """
    report: Dict[str, Any] = {
        # README.md was committed in the git_worktree fixture; the
        # Player "claims" to have modified it but didn't actually touch
        # it. ``git status --porcelain`` will show no change for it.
        "files_modified": ["README.md"],
        "tests_run": False,
    }

    verification = verifier.verify_player_report(report)

    # AC-7: critical count is zero — the tracked-but-unmodified case no
    # longer contributes to the honesty critical_failures total, so the
    # short-circuit at coach_validator.py:872 does not fire and the
    # gate keeps evaluating.
    critical = [
        d for d in verification.discrepancies if d.severity == "critical"
    ]
    assert critical == [], (
        f"Expected zero critical discrepancies for a tracked-but-"
        f"unmodified file; got: {critical}"
    )

    # AC-7: should_fix_count is exactly 1 (the one dropped path).
    assert verification.should_fix_count == 1

    # AC-7: the discrepancy is the new should_fix shape and identifies
    # the path as tracked (so the operator can disambiguate from the
    # gitignored / fabricated cases).
    assert len(verification.discrepancies) == 1
    disc = verification.discrepancies[0]
    assert disc.severity == "should_fix"
    assert disc.claim_type == "claim_audit_unmodified"
    assert "README.md" in disc.player_claim
    assert "tracked" in disc.actual_value.lower()
    # claim_audit_unmodified does NOT carry an ignore_rule (that field is
    # exclusive to claim_audit_gitignored).
    assert disc.ignore_rule is None


def test_claim_audit_unmodified_does_not_short_circuit_gate(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Mixed report: one tracked-unmodified path AND one genuine
    fabrication. The fabrication is critical and must short-circuit; the
    tracked-unmodified path rides along as should_fix.

    Confirms that AC-7's demotion is path-scoped — it does not blanket-
    suppress critical discrepancies on the same report.
    """
    report: Dict[str, Any] = {
        "files_modified": ["README.md"],  # tracked, unchanged → should_fix
        "files_created": [
            # Genuine fabrication — path absent from disk.
            "src/never_created.py",
        ],
        "tests_run": False,
    }

    verification = verifier.verify_player_report(report)

    # The fabrication still produces a critical claim_audit discrepancy.
    critical_audit = [
        d for d in verification.discrepancies
        if d.severity == "critical"
        and d.claim_type == "claim_audit"
    ]
    assert len(critical_audit) == 1
    assert "src/never_created.py" in critical_audit[0].player_claim

    # The tracked-but-unmodified path still surfaces as should_fix.
    unmodified = [
        d for d in verification.discrepancies
        if d.claim_type == "claim_audit_unmodified"
    ]
    assert len(unmodified) == 1
    assert unmodified[0].severity == "should_fix"
    assert "README.md" in unmodified[0].player_claim


# ---------------------------------------------------------------------------
# TASK-FIX-CAUD-J6F1 AC-001 / AC-006: absolute-path normalisation
#
# Reproducer for the FEAT-JARVIS-006 fail-run-1 incident: the Player
# report carried the same staged file under both absolute and relative
# form, and the audit's literal-string membership test against
# worktree-relative ``git status --porcelain`` flagged exactly the
# absolute entries (and none of the matching relative entries).
# After AC-001, ``_normalize_claimed_path`` resolves absolute paths to
# the worktree-relative form so both representations dedupe to one
# matching entry and no discrepancy fires.
# ---------------------------------------------------------------------------


def test_absolute_and_relative_duplicate_of_staged_file_no_discrepancy(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """The J6F1 reproducer: Player reports the same staged file under
    both absolute and relative form. Audit must dedupe and pass.

    Pre-AC-001: the absolute entry was kept verbatim, the porcelain set
    only ever contained the relative form, so ``claimed - would_stage``
    contained one entry per absolute claim → ``claim_audit`` discrepancy
    with ``severity="critical"`` (because the Player did not actually
    fabricate; the path resolves to a real, staged file).

    Post-AC-001: ``_normalize_claimed_path`` folds the absolute form to
    the worktree-relative form. Both entries become the same key in the
    ``claimed`` set, the comparison succeeds, and no discrepancy fires.
    """
    (git_worktree / "src" / "jarvis" / "infrastructure").mkdir(parents=True)
    target = git_worktree / "src" / "jarvis" / "infrastructure" / "chat_handler.py"
    target.write_text("class ChatHandler: ...\n")

    abs_path = str(target)
    rel_path = "src/jarvis/infrastructure/chat_handler.py"

    report: Dict[str, Any] = {
        "files_created": [abs_path, rel_path],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == [], (
        f"Expected no discrepancies for an absolute+relative duplicate of "
        f"a real staged file; got: {discrepancies}"
    )


def test_normalize_claimed_path_absolute_to_worktree_relative(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Direct unit test on the normaliser: absolute path under the
    worktree resolves to its relative form; absolute path outside the
    worktree falls through unchanged."""
    src = git_worktree / "src" / "foo.py"
    src.parent.mkdir(parents=True)
    src.write_text("x = 1\n")

    # Absolute under worktree → relative
    assert verifier._normalize_claimed_path(str(src)) == "src/foo.py"

    # Relative is unchanged
    assert verifier._normalize_claimed_path("src/foo.py") == "src/foo.py"

    # ./ prefix and trailing / still stripped (existing contract preserved)
    assert verifier._normalize_claimed_path("./src/foo.py") == "src/foo.py"
    assert verifier._normalize_claimed_path("adapters/") == "adapters"

    # Absolute path outside the worktree → unchanged (downstream
    # classification flags it as fabricated)
    outside = "/tmp/definitely-not-under-the-worktree/foo.py"
    assert verifier._normalize_claimed_path(outside) == outside


# ---------------------------------------------------------------------------
# TASK-FIX-CAUD-J6F1 AC-003b: harness-owned paths are allowlisted
#
# The orchestrator-side filter at
# ``agent_invoker._strip_orchestrator_managed_paths`` is the load-bearing
# fix; the Coach-side allowlist in ``_verify_claims_were_staged`` is
# defence in depth so harness paths can never produce a claim_audit
# discrepancy even if the orchestrator-side strip misses one.
# ---------------------------------------------------------------------------


def test_harness_owned_relative_path_allowlisted(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """A Player report containing only ``.guardkit/autobuild/<TASK>/...``
    paths produces no audit discrepancy — the allowlist filter drops them
    from the claimed set before the porcelain comparison."""
    report: Dict[str, Any] = {
        "files_created": [
            ".guardkit/autobuild/TASK-FOO/player_turn_1.json",
            ".guardkit/autobuild/TASK-FOO/coach_turn_1.json",
        ],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []


def test_harness_owned_absolute_path_allowlisted(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """The J6F1-shape: Player report contains the orchestrator's
    per-turn artefact under its absolute path (because the harness
    itself wrote it that way and it round-trips into ``files_created``).
    AC-001 normalises to relative; AC-003b allowlist then drops it.
    No audit discrepancy fires.
    """
    abs_player_turn = str(
        git_worktree / ".guardkit" / "autobuild" / "TASK-FOO" / "player_turn_1.json"
    )

    report: Dict[str, Any] = {
        "files_created": [abs_player_turn],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == [], (
        f"Expected no discrepancies for a harness-owned path in absolute "
        f"form; got: {discrepancies}"
    )


# ---------------------------------------------------------------------------
# TASK-FIX-CAUD-J6F1 AC-002: diagnostic message surfaces actual checked facts
# ---------------------------------------------------------------------------


def test_fabricated_discrepancy_diagnostic_includes_path_exists_and_no_match(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """When the Player claims a path that is genuinely fabricated (does
    not exist on disk), the discrepancy's ``actual_value`` must report
    the *checked* facts (``path_exists=False``, ``gitignore_match=no rule
    matched``, ``tracked=no``) instead of speculating about an
    unanchored .gitignore rule.

    AC-002 motivation: the previous "Most common cause: an unanchored
    .gitignore rule" wording sent the J6F1 review chasing hypothesis 1
    even though check-ignore had already returned exit 1 (no match).
    """
    report: Dict[str, Any] = {
        "files_created": ["src/never_created.py"],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    disc = discrepancies[0]
    assert disc.claim_type == "claim_audit"
    assert disc.severity == "critical"
    # The new diagnostic surfaces actual checked facts:
    assert "path_exists=False" in disc.actual_value
    assert "no rule matched" in disc.actual_value
    assert "tracked=no" in disc.actual_value
    # And does NOT carry the speculative gitignore-rule guess:
    assert "Most common cause: an unanchored" not in disc.actual_value


# ---------------------------------------------------------------------------
# TASK-FIX-SPECVIOL01: completion_promises[*].test_file is a run-claim,
# not an authored-file claim. Comma-joined lists are split; existing
# tracked-unmodified test files produce zero signal; fabricated test
# paths stay critical (AC-004).
# ---------------------------------------------------------------------------


def test_comma_joined_test_file_run_claims_no_discrepancy(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """FEAT-C332 run-2 turn-1 reproducer at the verifier layer.

    Player promise AC-018 carried
    ``test_file: "tests/a.py, tests/b.py"`` — a comma-joined string of two
    test files the Player *ran* (both committed, tracked, unmodified).
    Pre-fix, the whole string was normalised as ONE path, missed
    ``Path.exists()``, classified "fabricated", and produced a critical
    ``claim_audit`` discrepancy → ``partial_honesty_abort`` on an honest
    turn. Post-fix: the string is split and each existing tracked test
    file is recognised as a legitimate run-claim — zero discrepancies.
    """
    tests_dir = git_worktree / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_evidence.py").write_text("def test_a(): assert True\n")
    (tests_dir / "test_validator.py").write_text("def test_b(): assert True\n")
    _git("add", "-A", cwd=git_worktree)
    _git("commit", "-m", "existing test suites", cwd=git_worktree)

    report: Dict[str, Any] = {
        "completion_promises": [
            {
                "criterion_id": "AC-018",
                "status": "complete",
                "implementation_files": [],
                "test_file": (
                    "tests/test_evidence.py, tests/test_validator.py"
                ),
            }
        ],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []


def test_single_tracked_unmodified_test_file_run_claim_skipped(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """A single existing tracked test file in ``test_file`` produces no
    discrepancy — running a test legitimately stages nothing. Contrast
    with the same path claimed via ``files_modified``, which keeps the
    TASK-FIX-PCN ``claim_audit_unmodified`` should_fix advisory.
    """
    tests_dir = git_worktree / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_existing.py").write_text("def test_x(): assert True\n")
    _git("add", "-A", cwd=git_worktree)
    _git("commit", "-m", "existing test", cwd=git_worktree)

    run_only_report: Dict[str, Any] = {
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": "complete",
                "implementation_files": [],
                "test_file": "tests/test_existing.py",
            }
        ],
    }
    assert verifier._verify_claims_were_staged(run_only_report) == []

    # Same path claimed as authored work: advisory still fires.
    authored_report: Dict[str, Any] = {
        "files_modified": ["tests/test_existing.py"],
    }
    discrepancies = verifier._verify_claims_were_staged(authored_report)
    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "claim_audit_unmodified"
    assert discrepancies[0].severity == "should_fix"


def test_fabricated_test_file_claim_still_critical(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """AC-004: genuine Player test-claim fabrication still short-circuits.

    A ``test_file`` naming a path that does not exist on disk remains a
    critical ``claim_audit`` discrepancy — the run-claim suppression only
    applies to existing tracked files.
    """
    report: Dict[str, Any] = {
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": "complete",
                "implementation_files": [],
                "test_file": "tests/test_never_written.py",
            }
        ],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "claim_audit"
    assert discrepancies[0].severity == "critical"
    assert "tests/test_never_written.py" in discrepancies[0].player_claim


def test_comma_joined_test_file_with_one_fabricated_path_flags_only_it(
    git_worktree: Path, verifier: CoachVerifier
) -> None:
    """Splitting is per-path: one real run-claim + one fabricated path in
    the same comma-joined ``test_file`` flags only the fabricated one.
    """
    tests_dir = git_worktree / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_real.py").write_text("def test_r(): assert True\n")
    _git("add", "-A", cwd=git_worktree)
    _git("commit", "-m", "real test", cwd=git_worktree)

    report: Dict[str, Any] = {
        "completion_promises": [
            {
                "criterion_id": "AC-002",
                "status": "complete",
                "implementation_files": [],
                "test_file": "tests/test_real.py, tests/test_ghost.py",
            }
        ],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "claim_audit"
    assert discrepancies[0].severity == "critical"
    assert "tests/test_ghost.py" in discrepancies[0].player_claim


# ---------------------------------------------------------------------------
# TASK-FIX-XREPO-CAUD: a claimed file authored in a *sibling* git repo must
# not be flagged as a critical fabrication. Worktree ``git status`` /
# ``git check-ignore`` cannot speak to a different repo (check-ignore returns
# exit 128), which the old code mis-bucketed as ``infra_error`` → critical.
# FEAT-RBX / TASK-RBX-002 repro: runbook lifecycle events authored in the
# sibling ``nats-core`` repo false-failed every turn until max_turns.
# ---------------------------------------------------------------------------


@pytest.fixture
def sibling_repo(tmp_path: Path) -> Path:
    """A second, independent git repo next to the worktree (a sibling)."""
    repo = tmp_path / "nats-core"
    repo.mkdir()
    _git("init", "--initial-branch=main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "README.md").write_text("sibling base\n")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-m", "base", cwd=repo)
    return repo


def test_xrepo_undeclared_sibling_file_is_should_fix_not_critical(
    git_worktree: Path, sibling_repo: Path, verifier: CoachVerifier
) -> None:
    """Player authored a file in an undeclared sibling repo and reported it
    by absolute path. The file exists, so it is real work — the audit must
    surface a should_fix advisory under ``claim_audit_cross_repo``, never a
    turn-rejecting critical fabrication.
    """
    src = sibling_repo / "src" / "nats_core"
    src.mkdir(parents=True)
    events = src / "_runbook.py"
    events.write_text("class RunbookStarted: pass\n")

    report: Dict[str, Any] = {
        # Absolute, *unqualified* path into the sibling repo — exactly what
        # the FEAT-RBX player emitted.
        "files_created": [str(events)],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "claim_audit_cross_repo"
    assert discrepancies[0].severity == "should_fix"
    assert str(events) in discrepancies[0].player_claim
    assert "evidence_repos" in discrepancies[0].actual_value


def test_xrepo_declared_evidence_repo_file_is_silent(
    git_worktree: Path, sibling_repo: Path
) -> None:
    """When the sibling repo is declared in ``evidence_repos``, the per-repo
    checkpoint manager and ``_verify_files_exist`` own its verification — the
    worktree claim-audit must stay silent rather than emit an advisory.
    """
    from guardkit.orchestrator.evidence_repos import EvidenceRepo

    verifier = CoachVerifier(
        git_worktree,
        evidence_repos=[EvidenceRepo(name="nats-core", root=sibling_repo)],
    )

    src = sibling_repo / "src" / "nats_core"
    src.mkdir(parents=True)
    events = src / "_runbook.py"
    events.write_text("class RunbookStarted: pass\n")

    report: Dict[str, Any] = {
        "files_created": [str(events)],
    }

    discrepancies = verifier._verify_claims_were_staged(report)

    assert discrepancies == []
