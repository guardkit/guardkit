"""Coach Verification module for validating Player claims.

This module provides the CoachVerifier class that cross-references Player's
self-reported claims against actual test results and filesystem state.

The verification process detects discrepancies between:
- Claimed test results vs actual test execution
- Claimed files vs filesystem reality
- Claimed test counts vs parsed output

This pattern is inspired by the "intellectual honesty" design principle,
ensuring the Coach can trust Player reports.
"""

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from guardkit.tasks.state_bridge import TaskStateBridge

from guardkit.orchestrator.environment_bootstrap import probe_worktree_venv
from guardkit.orchestrator.evidence_repos import (
    EvidenceRepo,
    resolve_qualified_path,
    split_qualified,
)

logger = logging.getLogger(__name__)


# Manifest names that mark a worktree as a Python project for the loud
# no-venv fallback WARNING (TASK-AB-RESUMEVENV01 AC-003). Deliberately the
# same root-level names ProjectEnvironmentDetector treats as Python stack
# manifests — a match means "pytest against sys.executable will almost
# certainly miss the project's deps".
_PYTHON_PROJECT_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
)


class InterpreterResolutionError(RuntimeError):
    """No worktree venv interpreter resolved for a Python-project worktree
    *inside an autobuild run*.

    Q1 SPLIT posture (WS3-S1, decided by Rich 2026-07-09 — see WS3 §7): the
    shipped behaviour logged one WARNING and fell back to ``sys.executable``,
    which kept runs alive but is exactly the soft-fail shape that hid DD4F's
    TypeError. A wrong interpreter poisons **every** downstream Coach verdict
    (pytest collects 0 tests -> an absent signal that reads like a quality
    rejection, FEAT-ABL-005 run 4). So resolution failure is now a HARD-ABORT
    when ``in_autobuild_context=True`` — the run fails loud and the operator
    fixes the environment rather than the orchestrator silently mis-verdicting.

    The split is EXPLICIT (the ``in_autobuild_context`` flag), not a heuristic:
    interactive CLI use (the default, ``False``) keeps the WARNING +
    ``sys.executable`` fallback so a developer's ad-hoc invocation is not
    aborted.
    """


def _check_ignore_match_is_negation(check_ignore_stdout: str) -> bool:
    """Whether ``git check-ignore -v --no-index`` matched a ``!``-negation.

    The ``-v`` line format is ``<source>:<linenum>:<pattern>\\t<path>``. A
    pattern beginning with ``!`` RE-INCLUDES the path (the opposite of a
    drop): git reports it with exit 0 under ``--no-index`` even for tracked,
    re-included trees (e.g. ``!app/lib/**``). This helper lets the claim-audit
    classifier tell "silently dropped by gitignore" from "explicitly
    re-included" so it stops manufacturing ``claim_audit_gitignored`` false
    positives (red-baseline retro, L12 item 6). Returns ``False`` on empty or
    unparseable output (fail toward the pre-existing behaviour).
    """
    for line in check_ignore_stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Everything before the tab is ``<source>:<linenum>:<pattern>``.
        rule_field = line.split("\t", 1)[0]
        parts = rule_field.split(":", 2)
        if len(parts) < 3:
            continue
        pattern = parts[2].strip()
        return pattern.startswith("!")
    return False


def _resolve_venv_python(
    worktree_path: Path,
    explicit: Optional[Union[str, Path]],
    *,
    in_autobuild_context: bool = False,
) -> Optional[Path]:
    """Resolve the Python interpreter Coach should use for pytest.

    Resolution order (AC-TASK-FIX-7A05, extended by TASK-AB-RESUMEVENV01):
      1. Explicit path passed by the orchestrator (typically from
         BootstrapResult.venv_python).
      2. ``<worktree>/.venv/bin/python`` when it exists on disk — the
         current bootstrap layout (FFC6 eager worktree venv; recovery path
         when the explicit param wasn't threaded through, e.g. the
         ``--resume`` hash-match skip).
      3. ``<worktree>/.guardkit/venv/bin/python`` when it exists on disk —
         the legacy PEP 668 fallback layout (old worktrees exist).
      4. For a PYTHON project worktree that resolved nothing, the split
         posture (Q1, WS3-S1) applies:
           * ``in_autobuild_context=True`` -> raise
             :class:`InterpreterResolutionError` (HARD-ABORT — a wrong
             interpreter poisons every downstream Coach verdict; the
             DD4F-shaped soft-fail closes).
           * ``in_autobuild_context=False`` (interactive CLI, the default) ->
             log ONE WARNING naming the probed locations and the interpreter
             the caller will fall back to, then return None (warn-and-fallback
             preserved).
      5. For a non-Python project, return None either way (the caller's
         PATH ``pytest`` / ``sys.executable`` behaviour is correct — there is
         no project venv to miss).

    Args:
        worktree_path: The worktree whose venv is being resolved.
        explicit: An explicit interpreter path (typically
            ``BootstrapResult.venv_python``); wins when it exists on disk.
        in_autobuild_context: When True, a Python-project resolution failure
            is a HARD-ABORT (raises :class:`InterpreterResolutionError`)
            instead of warn-and-fallback. Set True ONLY by autobuild
            orchestrator call sites (Coach verdict paths). The interactive
            default (False) keeps the shipped warn-and-fallback behaviour.

    Raises:
        InterpreterResolutionError: Python-project worktree, no interpreter
            resolved, and ``in_autobuild_context=True``.
    """
    if explicit:
        candidate = Path(explicit)
        if candidate.exists():
            return candidate
        logger.debug(
            "CoachVerifier: explicit venv_python %s does not exist — "
            "falling through to filesystem discovery",
            candidate,
        )

    filesystem = probe_worktree_venv(worktree_path)
    if filesystem is not None:
        return filesystem

    # TASK-AB-RESUMEVENV01 (AC-003): no silent sys.executable fallback for a
    # Python project. The caller will run pytest under the ORCHESTRATOR'S own
    # interpreter, which almost certainly lacks the target project's deps —
    # pytest then collects 0 tests and every turn records an absent signal
    # that looks exactly like a quality rejection (FEAT-ABL-005 run 4).
    is_python_project = any(
        (worktree_path / marker).exists() for marker in _PYTHON_PROJECT_MARKERS
    )
    if is_python_project:
        probed_venv = worktree_path / ".venv" / "bin" / "python"
        probed_legacy = worktree_path / ".guardkit" / "venv" / "bin" / "python"
        if in_autobuild_context:
            # Q1 SPLIT (WS3-S1, Rich 2026-07-09): HARD-ABORT inside autobuild.
            # The remediation is named so the operator fixes the environment,
            # not the (poisoned) verdict.
            raise InterpreterResolutionError(
                "Autobuild interpreter-resolution FAILED for Python project at "
                f"{worktree_path}: no worktree venv interpreter resolved "
                f"(explicit={explicit}; probed {probed_venv} and "
                f"{probed_legacy}). Inside an autobuild run this is a "
                "HARD-ABORT (Q1 SPLIT, WS3-S1) — falling back to the "
                "orchestrator's own interpreter would poison every downstream "
                "Coach verdict (pytest collects 0 tests, the DD4F-shaped "
                "soft-fail). Remediation: re-run environment bootstrap so the "
                f"worktree venv exists (verify {probed_venv} was created, or "
                "delete the worktree and re-run the autobuild), or thread an "
                "explicit venv_python through. Interactive CLI use keeps the "
                "warn-and-fallback behaviour."
            )
        logger.warning(
            "TASK-AB-RESUMEVENV01: no worktree venv interpreter resolved for "
            "Python project at %s — probed %s and %s (explicit=%s). Callers "
            "will fall back to %s (the orchestrator's own interpreter), which "
            "likely lacks the project's deps; check the worktree venv or "
            "re-run environment bootstrap.",
            worktree_path,
            probed_venv,
            probed_legacy,
            explicit,
            sys.executable,
        )

    return None


@dataclass
class Discrepancy:
    """A discrepancy between Player claim and reality.

    Attributes:
        claim_type: Type of claim ("test_result", "file_existence",
            "test_count", "claim_audit", "claim_audit_gitignored",
            "claim_audit_unmodified").
        player_claim: What the Player reported
        actual_value: What was actually found
        severity: Severity level ("critical", "should_fix", "warning", "info")
        ignore_rule: For ``claim_audit_gitignored`` discrepancies, the
            ``<source>:<linenum>:<pattern>`` line from
            ``git check-ignore -v --no-index`` that matched the path.
            ``None`` for every other claim_type. Used by the Coach
            feedback path to surface the matched rule to the Player and,
            when the source is the project-root ``.gitignore``, to
            append a "rebase the worktree onto main" hint
            (TASK-FIX-IGNR AC-6).

    The ``claim_audit_unmodified`` shape (TASK-FIX-PCN AC-6) is the
    sibling of ``claim_audit_gitignored``: where the latter says
    "Player-authored file is on disk but .gitignore filtered it", this
    one says "claimed path is tracked in git AND porcelain shows no
    change for it". The most common cause is the Player report writer
    sweeping an orchestrator-managed path (e.g.
    ``.guardkit/autobuild/<TASK-ID>/coach_turn_N.json`` or
    ``tasks/backlog/<TASK-ID>-*.md``) into ``files_modified`` —
    defence-in-depth for the agent_invoker-side filter at
    ``_strip_orchestrator_managed_paths``. Demoted to ``should_fix``
    so the gate surfaces a warning rather than collapsing on the
    FEAT-39E1 PH1-005 shape.
    """

    claim_type: str
    player_claim: str
    actual_value: str
    severity: str  # "critical", "should_fix", "warning", "info"
    ignore_rule: Optional[str] = None


@dataclass
class ResolvedPath:
    """A Player-reported path resolved through state_bridge identity lookup.

    Recorded on :py:class:`HonestyVerification` when ``CoachVerifier`` chose
    not to emit a ``file_existence`` discrepancy because the claimed path was
    missing on disk but the task's current canonical path (per state_bridge)
    does exist. Provides an audit trail for why a discrepancy was suppressed.

    Attributes:
        claimed: The path the Player (or post-turn enrichment) reported.
        resolved_to: The canonical task file path on disk (relative to worktree
            when possible, absolute otherwise).
        task_id: The task ID whose canonical path was consulted.
    """

    claimed: str
    resolved_to: str
    task_id: str


@dataclass
class TestResult:
    """Result of running tests.

    Attributes:
        passed: Whether all tests passed
        test_count: Number of tests that passed
        output: Raw test output
    """

    passed: bool
    test_count: int
    output: str


@dataclass
class HonestyVerification:
    """Result of verifying Player claims.

    Attributes:
        verified: True if all claims were verified successfully
        discrepancies: List of found discrepancies
        honesty_score: Score from 0.0 to 1.0 (1.0 = fully honest)
        resolved_paths: Player-reported paths that would have triggered a
            ``file_existence`` discrepancy but were resolved through
            state_bridge identity lookup (TASK-FIX-1B4A). Empty list when
            no resolutions occurred or state_bridge wiring is absent.
        should_fix_count: Count of ``severity == "should_fix"`` discrepancies
            (TASK-FIX-IGNR). These are advisory — they do not contribute to
            ``honesty_score`` and do not short-circuit gate evaluation, but
            they ride along to Coach feedback so the Player can act on them.
            The motivating case is ``claim_audit_gitignored``: a Player-
            authored file that is on disk but silently filtered by
            ``.gitignore`` deserves an actionable warning, not a
            turn-rejecting fabrication verdict.
    """

    verified: bool
    discrepancies: List[Discrepancy] = field(default_factory=list)
    honesty_score: float = 1.0
    resolved_paths: List[ResolvedPath] = field(default_factory=list)
    should_fix_count: int = 0


class CoachVerifier:
    """Verifies Player claims against reality.

    This class provides verification logic to cross-reference Player's
    self-reported claims against actual test results and filesystem state.

    Attributes:
        worktree_path: Path to the isolated git worktree

    Example:
        >>> verifier = CoachVerifier(Path(".guardkit/worktrees/TASK-001"))
        >>> result = verifier.verify_player_report(player_report)
        >>> if not result.verified:
        ...     print(f"Discrepancies found: {result.discrepancies}")
    """

    def __init__(
        self,
        worktree_path: Path,
        venv_python: Optional[Union[str, Path]] = None,
        task_id: Optional[str] = None,
        state_bridge: Optional["TaskStateBridge"] = None,
        evidence_repos: Optional[List["EvidenceRepo"]] = None,
        in_autobuild_context: bool = False,
    ):
        """Initialize CoachVerifier.

        Args:
            worktree_path: Path to the isolated git worktree
            venv_python: Optional explicit Python interpreter to run pytest
                with. Typically sourced from
                ``BootstrapResult.venv_python`` so Coach verifies against
                the same interpreter the Player's bootstrap produced.
                Resolution follows :func:`_resolve_venv_python`.
            task_id: Optional task identifier. When paired with ``state_bridge``,
                enables identity-based path resolution in
                :py:meth:`_verify_files_exist` so a Player-reported pre-move
                task path can be resolved to the task's current canonical
                location instead of triggering a false-fail file_existence
                discrepancy (TASK-FIX-1B4A, Layer 1 of FEAT-FFC3 fix).
            state_bridge: Optional :py:class:`TaskStateBridge` instance for
                the same worktree. When either ``task_id`` or ``state_bridge``
                is None, identity resolution is disabled and exact-match
                behaviour is preserved (fail-open).
            evidence_repos: Optional declared sibling repos
                (TASK-AB-XREPOEV01). When a claimed file is repo-qualified
                (``<repo>:<path>``) and names one of these, file-existence is
                checked against ``repo.root / path`` instead of the worktree.
                A qualified claim naming an *undeclared* repo is fail-open
                (skipped, never a new false-red) per
                ``path-string-mismatch-is-not-dishonesty``. Default None ->
                exact worktree-only behaviour preserved.
            in_autobuild_context: When True, an unresolved interpreter for a
                Python-project worktree is a HARD-ABORT
                (:class:`InterpreterResolutionError`) instead of
                warn-and-fallback (Q1 SPLIT, WS3-S1). Autobuild orchestrator
                call sites pass True; interactive / recovery callers keep the
                default False.
        """
        self.worktree_path = Path(worktree_path)
        self._cached_test_result: Optional[TestResult] = None
        self._in_autobuild_context = in_autobuild_context
        self._venv_python: Optional[Path] = _resolve_venv_python(
            self.worktree_path,
            venv_python,
            in_autobuild_context=in_autobuild_context,
        )
        if self._venv_python is not None:
            logger.debug(
                "CoachVerifier using interpreter %s for pytest", self._venv_python
            )
        self.task_id: Optional[str] = task_id
        self.state_bridge: Optional["TaskStateBridge"] = state_bridge
        self.evidence_repos: List["EvidenceRepo"] = list(evidence_repos or [])
        self._resolved_paths: List[ResolvedPath] = []

    def verify_player_report(self, player_report: Dict[str, Any]) -> HonestyVerification:
        """Verify all verifiable claims in Player report.

        Performs three types of verification:
        1. Test results - Run tests and compare with claimed results
        2. File existence - Check claimed files exist on filesystem
        3. Test count - Verify test count matches claimed summary

        Args:
            player_report: Player's report dictionary containing claims

        Returns:
            HonestyVerification with verification results
        """
        discrepancies: List[Discrepancy] = []

        # Clear cached test result for fresh verification
        self._cached_test_result = None

        # Verify test results
        test_disc = self._verify_test_results(player_report)
        if test_disc:
            discrepancies.extend(test_disc)

        # Verify file existence
        file_disc = self._verify_files_exist(player_report)
        if file_disc:
            discrepancies.extend(file_disc)

        # Verify completion_promises (TASK-AB-FIX-INVAB1 AC-001).
        # Catches the FEAT-6CC5 class of sophisticated dishonesty: Player
        # keeps files_created/files_modified honest while lying in
        # completion_promises[*].implementation_files.
        promise_disc = self._verify_completion_promises_files_exist(player_report)
        if promise_disc:
            discrepancies.extend(promise_disc)

        # Verify Player claims would be staged (TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT).
        # Catches the FEAT-39E1 class of silent loss: Player created a file
        # that exists on disk but is gitignored (or sparse-filtered, etc.),
        # so the per-turn checkpoint commits without it. ``_verify_files_exist``
        # passes because the file is on disk; this check fails because git
        # would refuse to stage it.
        claim_audit_disc = self._verify_claims_were_staged(player_report)
        if claim_audit_disc:
            discrepancies.extend(claim_audit_disc)

        # Verify test count
        count_disc = self._verify_test_count(player_report)
        if count_disc:
            discrepancies.extend(count_disc)

        # Calculate honesty score
        total_claims = self._count_verifiable_claims(player_report)
        critical_failures = len([d for d in discrepancies if d.severity == "critical"])
        # TASK-FIX-IGNR AC-2: should_fix discrepancies (e.g.
        # claim_audit_gitignored) do NOT contribute to honesty_score —
        # they ride along as advisory feedback only.
        should_fix_count = len(
            [d for d in discrepancies if d.severity == "should_fix"]
        )
        honesty_score = 1.0 - (critical_failures / max(total_claims, 1))

        return HonestyVerification(
            verified=len(discrepancies) == 0,
            discrepancies=discrepancies,
            honesty_score=honesty_score,
            resolved_paths=list(self._resolved_paths),
            should_fix_count=should_fix_count,
        )

    def _verify_test_results(self, report: Dict[str, Any]) -> List[Discrepancy]:
        """Verify tests_passed claim against actual test run.

        Args:
            report: Player report dictionary

        Returns:
            List of discrepancies found (empty if verified)
        """
        discrepancies: List[Discrepancy] = []

        claimed_passed = report.get("tests_passed", False)
        claimed_run = report.get("tests_run", False)

        if not claimed_run:
            # Player claims tests weren't run - nothing to verify
            return discrepancies

        # Run tests independently
        actual_result = self._run_tests()

        if claimed_passed != actual_result.passed:
            discrepancies.append(
                Discrepancy(
                    claim_type="test_result",
                    player_claim=f"tests_passed: {claimed_passed}",
                    actual_value=f"tests_passed: {actual_result.passed}",
                    severity="critical",
                )
            )

        return discrepancies

    def _verify_files_exist(self, report: Dict[str, Any]) -> List[Discrepancy]:
        """Verify claimed files actually exist.

        When a claimed path is missing on disk and identity-resolution is wired
        (``task_id`` and ``state_bridge`` both supplied at construction time),
        consult :py:meth:`TaskStateBridge.canonical_path_for` once per call.
        If that returns a path that exists on disk, suppress the discrepancy
        and append a :py:class:`ResolvedPath` audit record to
        ``self._resolved_paths`` instead. This closes the FEAT-FFC3 false-fail
        where the orchestrator's post-turn enrichment attributes a pre-move
        task path to the Player after state_bridge has moved the file
        (TASK-FIX-1B4A, Layer 1).

        Args:
            report: Player report dictionary

        Returns:
            List of discrepancies for missing files (after identity resolution)
        """
        discrepancies: List[Discrepancy] = []
        self._resolved_paths = []

        canonical_path: Optional[Path] = None
        canonical_resolved: bool = False

        for file_list_key in ["files_created", "files_modified", "tests_written"]:
            claimed_files = report.get(file_list_key, [])

            for file_path in claimed_files:
                # TASK-AB-XREPOEV01: repo-qualified claim (``<repo>:<path>``).
                # Resolve against the declared sibling repo root, not the
                # worktree. An unknown repo name resolves to None -> fail-open
                # (skip, never a new false-red) per
                # path-string-mismatch-is-not-dishonesty.
                if split_qualified(file_path) is not None:
                    sibling_path = resolve_qualified_path(
                        file_path, self.evidence_repos
                    )
                    if sibling_path is None:
                        logger.debug(
                            "CoachVerifier: repo-qualified claim %s names an "
                            "undeclared evidence repo; skipping existence check "
                            "(fail-open)",
                            file_path,
                        )
                        continue
                    if sibling_path.exists():
                        continue
                    discrepancies.append(
                        Discrepancy(
                            claim_type="file_existence",
                            player_claim=f"{file_list_key}: {file_path}",
                            actual_value=(
                                f"File does not exist in sibling repo "
                                f"({sibling_path})"
                            ),
                            severity="critical",
                        )
                    )
                    continue

                full_path = self.worktree_path / file_path
                if full_path.exists():
                    continue

                if (
                    self.task_id is not None
                    and self.state_bridge is not None
                ):
                    if not canonical_resolved:
                        canonical_path = self.state_bridge.canonical_path_for()
                        canonical_resolved = True

                    if canonical_path is not None and canonical_path.exists():
                        try:
                            resolved_to = str(
                                canonical_path.relative_to(self.worktree_path)
                            )
                        except ValueError:
                            resolved_to = str(canonical_path)
                        self._resolved_paths.append(
                            ResolvedPath(
                                claimed=str(file_path),
                                resolved_to=resolved_to,
                                task_id=self.task_id,
                            )
                        )
                        logger.debug(
                            "CoachVerifier suppressed file_existence "
                            "discrepancy for %s via state_bridge canonical "
                            "path %s (task %s)",
                            file_path,
                            resolved_to,
                            self.task_id,
                        )
                        continue

                discrepancies.append(
                    Discrepancy(
                        claim_type="file_existence",
                        player_claim=f"{file_list_key}: {file_path}",
                        actual_value="File does not exist",
                        severity="critical",
                    )
                )

        return discrepancies

    def _verify_claims_were_staged(
        self, report: Dict[str, Any]
    ) -> List[Discrepancy]:
        """Verify Player-claimed files would be picked up by ``git add -A``.

        Sibling of :py:meth:`_verify_files_exist`. Where ``_verify_files_exist``
        asks "is the file on disk?", this asks "would git stage it into the
        next checkpoint commit?". Both signals are needed: a file the Player
        created can pass the on-disk check yet be silently filtered by
        ``.gitignore`` (or sparse-checkout, ``assume-unchanged``, or pathspec
        attribute filters), so the per-turn checkpoint commits without it and
        the file is later lost when the worktree is cleaned up.

        Catches the FEAT-39E1 class of silent loss
        (TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT, 2026-05-08): Player created
        ``src/study_tutor/adapters/manifest.py``; the worktree's ``.gitignore``
        carried an unanchored ``adapters/`` rule; ``git add -A`` silently
        skipped the file; the Coach approved the turn at honesty score 1.0
        (the file *did* exist on disk); the file never reached the merged
        branch.

        Pair-with-attempted-count semantics from
        ``.claude/rules/absence-of-failure-is-not-success.md``: when the
        Player populated zero claim keys (zero-cardinality input), this
        method emits no discrepancy and lets other gates decide. The implicit
        "git add error count == 0" gate becomes pair-with-attempted-count
        only when the attempted count is > 0.

        Detection oracle. The task spec
        (``TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT`` AC-002) names
        ``git show --name-only --format= HEAD`` as the staged-set source.
        That command is correct only *after* the checkpoint commit lands.
        In the current ``autobuild.py`` flow the checkpoint commit happens
        *after* Coach decides
        (``autobuild.py:2257-2266`` for the approve path,
        ``autobuild.py:2306-2316`` for the feedback path), so at honesty-
        verification time HEAD is still the previous turn's checkpoint.
        Using ``git status --porcelain=v1`` here gives the same signal
        ("paths git would stage on the next ``git add -A``") at the right
        moment in the flow — modified-tracked, untracked-not-ignored,
        and deletions all surface, while gitignored files do not. The
        behaviour matches AC-005/006/007.

        Args:
            report: Player report dictionary.

        Returns:
            Critical ``claim_audit`` discrepancies for files claimed but
            not in the would-be-staged set. Empty list when:
              * The claimed set is empty (zero-cardinality permitted).
              * The git invocation failed (fail-open; never block gates on
                infrastructure errors).
              * Every claimed path is in the would-be-staged set.
        """
        # TASK-FIX-SPECVIOL01: partition claims by provenance.
        #   * authored_claims — files the Player says it wrote
        #     (files_created / files_modified / tests_written /
        #     completion_promises[*].implementation_files). These must show
        #     up in the would-be-staged set or something is wrong.
        #   * run_claims — completion_promises[*].test_file names tests the
        #     Player *ran*, not files it authored. An existing, tracked,
        #     unmodified test file legitimately produces no staged change,
        #     so auditing run-claims against the would-be-staged set
        #     misattributes protocol noise as Player dishonesty (the
        #     path-string-mismatch-is-not-dishonesty meta-class; FEAT-C332
        #     run-2 turn-1 false-red).
        authored_claims: set[str] = set()
        run_claims: set[str] = set()
        for key in ("files_created", "files_modified", "tests_written"):
            for entry in report.get(key) or []:
                if entry:
                    authored_claims.add(self._normalize_claimed_path(str(entry)))
        for promise in report.get("completion_promises") or []:
            if not isinstance(promise, dict):
                continue
            for entry in promise.get("implementation_files") or []:
                if entry:
                    authored_claims.add(self._normalize_claimed_path(str(entry)))
            test_file = promise.get("test_file")
            if test_file:
                # Players routinely emit a comma-joined list in this
                # free-text field (FEAT-C332 run 2, promise AC-018:
                # "a.py, b.py"). Split it, or the whole string is audited
                # as one path and false-fails Path.exists() — a guaranteed
                # "fabricated" critical on an honest report.
                for part in str(test_file).split(","):
                    part = part.strip()
                    if part:
                        run_claims.add(self._normalize_claimed_path(part))
        claimed: set[str] = authored_claims | run_claims

        # TASK-AB-XREPOEV01: drop repo-qualified claims (``<repo>:<path>``).
        # This audit runs ``git status`` in the WORKTREE to learn what the
        # next ``git add -A`` checkpoint would stage; the worktree knows
        # nothing about sibling repos, so auditing a qualified path here would
        # manufacture a false-red (the path-string-mismatch meta-class).
        # Sibling-repo existence is verified by ``_verify_files_exist`` against
        # the right root, and sibling-repo staging is the per-repo checkpoint
        # manager's job (AC-004).
        claimed = {c for c in claimed if split_qualified(c) is None}

        # TASK-FIX-XREPOPROM01: also drop UNQUALIFIED claims that are absent
        # from the worktree but exist under a declared sibling evidence repo
        # (the Player reported sibling-relative paths without the ``<repo>:``
        # qualifier — FEAT-10AC run 1). Same rationale as the qualified drop
        # above: this audit's ``git status`` runs in the WORKTREE and knows
        # nothing about sibling files; sibling staging is the per-repo
        # checkpoint manager's job. A claim that exists nowhere is untouched
        # and still classifies as fabricated below.
        if self.evidence_repos:
            claimed = {
                c
                for c in claimed
                if (self.worktree_path / c).exists()
                or self._resolve_against_evidence_repos(c) is None
            }

        # TASK-FIX-CAUD-J6F1 AC-003b — defence-in-depth allowlist.
        # The orchestrator-side filter at
        # ``agent_invoker._strip_orchestrator_managed_paths`` is the
        # load-bearing fix; this strip here makes sure that even if a
        # harness-owned path slips past it (e.g. a future refactor that
        # introduces a new write site, or a synthetic-promise generator
        # that injects after the strip), the Coach's claim audit never
        # raises a discrepancy on a path the Player had no control over.
        # Late import to avoid the agent_invoker → coach_verification
        # → agent_invoker circular at module-load time.
        try:
            from guardkit.orchestrator.agent_invoker import (
                _is_orchestrator_managed_path,
            )
        except ImportError:
            # Filter unavailable (e.g. partial install / namespace
            # re-arrangement). Fail-open: leave ``claimed`` unchanged
            # and let the existing audit logic run.
            pass
        else:
            claimed = {
                p for p in claimed
                if not _is_orchestrator_managed_path(
                    p, worktree_path=self.worktree_path
                )
            }

        # AC-004: zero-cardinality permitted — no oracle ran, don't block.
        if not claimed:
            return []

        # Fail-open guard: skip the audit when the worktree is not a git
        # repo. The audit oracle (``git status --porcelain``) is meaningful
        # only inside a git tree, and many of the existing fixture-based
        # tests instantiate ``CoachVerifier`` against a plain ``tmp_path``
        # so that ``_verify_files_exist`` can be exercised in isolation.
        # ``.git`` is a directory in a normal repo and a file in linked
        # worktrees — ``Path.exists()`` covers both.
        if not (self.worktree_path / ".git").exists():
            logger.debug(
                "claim_audit: %s is not a git worktree; skipping audit "
                "(fail-open).",
                self.worktree_path,
            )
            return []

        try:
            # ``--untracked-files=all`` expands new untracked directories
            # into their individual files. Without it, git collapses
            # ``src/new_module/`` to a single ``?? src/new_module/`` line
            # and we'd false-fail every claimed file under it.
            result = subprocess.run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all"],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning(
                "claim_audit: 'git status --porcelain=v1' failed (%s) in %s; "
                "fail-open to avoid blocking gate evaluation on infra error.",
                exc,
                self.worktree_path,
            )
            return []
        if result.returncode != 0:
            logger.warning(
                "claim_audit: 'git status --porcelain=v1' returned %d in %s; "
                "fail-open. stderr=%s",
                result.returncode,
                self.worktree_path,
                result.stderr.strip(),
            )
            return []

        would_stage: set[str] = set()
        for line in result.stdout.splitlines():
            # Porcelain v1 line: ``XY <path>`` or ``XY <oldpath> -> <newpath>``
            # where X/Y are status codes. Anything reported here would be
            # staged by ``git add -A`` — gitignored paths are excluded by
            # default (no ``--ignored`` flag).
            if len(line) < 4:
                continue
            path_part = line[3:]
            if " -> " in path_part:
                old, _, new = path_part.partition(" -> ")
                would_stage.add(self._normalize_claimed_path(old.strip().strip('"')))
                would_stage.add(self._normalize_claimed_path(new.strip().strip('"')))
            else:
                would_stage.add(
                    self._normalize_claimed_path(path_part.strip().strip('"'))
                )

        dropped = sorted(claimed - would_stage)
        if not dropped:
            return []

        # TASK-FIX-IGNR + TASK-FIX-PCN: split the dropped set into:
        #   * "fabricated"          — path absent from disk, OR present
        #                              but neither gitignored nor tracked.
        #                              Stays ``severity="critical"``: the
        #                              Player is claiming work that did
        #                              not land.
        #   * "gitignored"          — path on disk, matches a .gitignore
        #                              rule (TASK-FIX-IGNR). Demoted to
        #                              ``severity="should_fix"`` so the
        #                              FEAT-39E1 turn-1→turn-5 adversarial
        #                              blow-up does not recur.
        #   * "tracked_unmodified"  — path on disk, tracked in git, but
        #                              porcelain shows no change for it
        #                              (TASK-FIX-PCN). Most common cause:
        #                              the Player report writer swept an
        #                              orchestrator-managed path into
        #                              files_modified (defence-in-depth
        #                              for the agent_invoker-side filter
        #                              at ``_strip_orchestrator_managed_paths``).
        #                              Demoted to ``severity="should_fix"``
        #                              so the gate surfaces a warning
        #                              rather than rejecting the turn on
        #                              what is almost always a noise path.
        discrepancies: List[Discrepancy] = []
        for path in dropped:
            classification = self._classify_dropped_path(path)
            if classification == "gitignored":
                ignore_rule = self._git_check_ignore_rule(path)
                discrepancies.append(
                    Discrepancy(
                        claim_type="claim_audit_gitignored",
                        player_claim=f"Player claimed file {path}",
                        actual_value=(
                            f"Path is on disk but matched a .gitignore "
                            f"rule ({ignore_rule}); 'git add -A' silently "
                            f"skipped it. Fix the ignore rule (or rebase "
                            f"the worktree onto a branch where the rule "
                            f"is fixed) and re-run the turn."
                        ),
                        severity="should_fix",
                        ignore_rule=ignore_rule,
                    )
                )
            elif classification == "tracked_unmodified":
                if path in run_claims and path not in authored_claims:
                    # TASK-FIX-SPECVIOL01: a run-claim (test_file) on an
                    # existing tracked test file. No staged change is the
                    # *expected* outcome of running a test — zero signal,
                    # not a Player-honesty observation. Emit nothing.
                    continue
                discrepancies.append(
                    Discrepancy(
                        claim_type="claim_audit_unmodified",
                        player_claim=f"Player claimed file {path}",
                        actual_value=(
                            "Path is tracked in git but 'git status "
                            "--porcelain' shows no change for it — the "
                            "Player claimed work on a file it did not "
                            "actually modify this turn. Most likely "
                            "cause: the report writer swept an "
                            "orchestrator-managed path (e.g. a file "
                            "under .guardkit/autobuild/ or tasks/<state>/) "
                            "into files_modified. Defence-in-depth for "
                            "the agent_invoker-side filter; this is a "
                            "warning, not a turn-rejecting fabrication."
                        ),
                        severity="should_fix",
                    )
                )
            elif classification == "cross_repo":
                # TASK-FIX-XREPO-CAUD: the claimed path exists on disk but
                # inside a *different* git repo than the worktree (the
                # FEAT-RBX / TASK-RBX-002 repro: runbook lifecycle events
                # authored in the sibling ``nats-core`` repo). Worktree
                # ``git add -A`` cannot stage it and worktree
                # ``git check-ignore`` returns exit 128, so the old code
                # mis-bucketed it as ``infra_error`` → a turn-rejecting
                # critical false-red. When the owning repo is a declared
                # evidence repo, sibling verification (``_verify_files_exist``)
                # and the per-repo checkpoint manager own it — stay silent.
                # Otherwise surface a should_fix advisory: the work is real
                # but the feature never declared the sibling repo, so it
                # cannot be staged or independently verified. Never critical:
                # the file is on disk.
                repo_name = self._path_under_declared_repo(
                    self.worktree_path / path
                )
                if repo_name is not None:
                    continue
                discrepancies.append(
                    Discrepancy(
                        claim_type="claim_audit_cross_repo",
                        player_claim=f"Player claimed file {path}",
                        actual_value=(
                            "Path is on disk inside a different git "
                            "repository than the worktree, so worktree "
                            "'git add -A' cannot stage it and the worktree "
                            "claim-audit cannot verify it. Declare the "
                            "sibling repo in the feature's evidence_repos "
                            "and report the path repo-qualified "
                            "('<repo>:<relpath>') to enable cross-repo "
                            "checkpointing and verification."
                        ),
                        severity="should_fix",
                    )
                )
            else:
                # "fabricated" or "infra_error" — keep the critical
                # behaviour. infra_error here means ``git check-ignore``
                # itself broke (exit 128); we already logged a warning
                # in ``_classify_dropped_path``. Falling back to critical
                # preserves the FEAT-39E1 detection floor when the
                # gitignore probe is unavailable for any reason.
                #
                # TASK-FIX-CAUD-J6F1 AC-002: the actual_value text now
                # surfaces the *checked* facts (path_exists, ignore-probe
                # result, tracked status) rather than speculating about
                # an unanchored .gitignore rule. The previous text
                # ("Most common cause: an unanchored .gitignore rule
                # silently filters the file") sent the J6F1 review chasing
                # a wrong hypothesis for non-trivial time, even though
                # ``_classify_dropped_path`` had *already* run check-ignore
                # and obtained exit 1 (no match) on every flagged path.
                abs_path = self.worktree_path / path
                path_exists = abs_path.exists()
                if classification == "fabricated":
                    # Reaching this branch means ``_classify_dropped_path``
                    # observed: check-ignore exit 1 (no rule matched) AND
                    # — if path exists — ls-files exit != 0 (not tracked).
                    diagnosis = (
                        f"path_exists={path_exists}; "
                        f"gitignore_match=no rule matched; tracked=no"
                    )
                    if not path_exists:
                        cause = (
                            "Most likely cause: the Player claimed work "
                            "on a file that does not exist on disk."
                        )
                    else:
                        cause = (
                            "Path exists on disk but is neither "
                            "gitignored nor tracked — investigate "
                            "sparse-checkout, assume-unchanged, or "
                            "pathspec attribute filters as the next step."
                        )
                else:  # "infra_error"
                    diagnosis = (
                        f"path_exists={path_exists}; "
                        f"gitignore_match=probe failed; tracked=unknown"
                    )
                    cause = (
                        "The 'git check-ignore' probe itself failed "
                        "(logged separately); falling back to critical "
                        "classification to preserve the FEAT-39E1 "
                        "detection floor."
                    )
                discrepancies.append(
                    Discrepancy(
                        claim_type="claim_audit",
                        player_claim=f"Player claimed file {path}",
                        actual_value=(
                            f"Path absent from 'git status --porcelain' "
                            f"so 'git add -A' would not stage it. Probes: "
                            f"{diagnosis}. {cause}"
                        ),
                        severity="critical",
                    )
                )
        return discrepancies

    def _classify_dropped_path(self, path: str) -> str:
        """Classify why ``path`` was absent from ``git status --porcelain``.

        Returns one of:
          * ``"fabricated"`` — path does not exist on disk (Player lied),
            or path exists but is neither gitignored nor tracked
            (genuinely unaccounted for).
          * ``"gitignored"`` — path exists on disk and ``git check-ignore -v
            --no-index`` matches an ignore rule.
          * ``"tracked_unmodified"`` — path exists on disk, is NOT
            gitignored, and ``git ls-files --error-unmatch`` confirms it
            is tracked. Porcelain showed no change for it because there
            *is* no change. Most common cause: the Player report writer
            swept an orchestrator-managed path into ``files_modified``
            (TASK-FIX-PCN). Caller demotes to ``should_fix`` so the gate
            surfaces a warning rather than rejecting the turn.
          * ``"cross_repo"`` — path exists on disk but resolves into a
            *different* git working tree than the worktree (a sibling
            repo). The worktree audit cannot speak to it; the caller
            either stays silent (declared evidence repo) or emits a
            should_fix advisory (undeclared). Never critical.
          * ``"infra_error"`` — ``git check-ignore`` (or the
            ``ls-files`` follow-up) itself failed (exit 128 or a
            subprocess crash). Caller falls back to critical to preserve
            the detection floor.

        ``--no-index`` makes ``git check-ignore`` evaluate ignore rules
        against the path string regardless of whether the path is tracked,
        which is what we want here (the path was just dropped from
        porcelain, so it is, by definition, untracked-or-modified).
        """
        abs_path = self.worktree_path / path
        if not abs_path.exists():
            return "fabricated"

        # TASK-FIX-XREPO-CAUD: an absolute claim that exists but lives in a
        # *different* git repo than the worktree must not be probed with
        # worktree-cwd git — ``git check-ignore`` against an out-of-worktree
        # path returns exit 128, which the logic below mis-buckets as
        # ``infra_error`` → a critical false-red on real sibling-repo work
        # (FEAT-RBX / TASK-RBX-002). Only absolute paths can point outside
        # the worktree; relative claims always resolve under it, so gate the
        # (two-subprocess) repo probe on ``is_absolute()`` to keep the common
        # path zero-cost.
        if Path(path).is_absolute():
            owning_top = self._git_toplevel(abs_path)
            if (
                owning_top is not None
                and owning_top != self._git_toplevel(self.worktree_path)
            ):
                return "cross_repo"

        # Red-baseline retro (2026-07-08, L12 item 6): a TRACKED file is
        # never silently skipped by ``git add -A`` — so tracking state is the
        # authority on "was this dropped", and it must be consulted BEFORE
        # trusting ``git check-ignore --no-index``. The ``--no-index`` probe
        # reports the *last matching* pattern regardless of tracking, and for
        # a re-included tree (``!app/lib/**``) that last pattern is a
        # **negation** returned with exit 0 — which the old exit-0→"gitignored"
        # shortcut mis-read for demonstrably tracked, committed files
        # (FEAT-VOICE-003: 3 phantom ``claim_audit_gitignored`` should_fix
        # items every turn, steering the Player off the one real red test).
        # ``git ls-files --error-unmatch`` short-circuits the whole class.
        tracked = self._git_path_is_tracked(path)
        if tracked is None:
            # ls-files probe itself failed (git missing / timeout) — preserve
            # the detection floor rather than guess. Consistent with the
            # check-ignore infra_error posture below.
            return "infra_error"
        if tracked:
            return "tracked_unmodified"

        # Untracked and on disk. Distinguish a genuinely-gitignored file
        # (``git add -A`` would silently skip it — a real honesty signal)
        # from an unaccounted / fabricated one.
        try:
            result = subprocess.run(
                ["git", "check-ignore", "-v", "--no-index", "--", path],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning(
                "claim_audit: 'git check-ignore' failed (%s) for path %s "
                "in %s; falling back to critical classification.",
                exc, path, self.worktree_path,
            )
            return "infra_error"

        if result.returncode == 0:
            # ``check-ignore -v --no-index`` matched a rule. Honour negations:
            # a ``!pattern`` match RE-INCLUDES the path, so ``git add -A``
            # would stage it — it is NOT silently dropped by gitignore. An
            # untracked, re-included path absent from porcelain is unaccounted
            # → fabricated, not ``gitignored``.
            if _check_ignore_match_is_negation(result.stdout):
                return "fabricated"
            return "gitignored"
        if result.returncode == 1:
            # Not ignored and (from the short-circuit above) not tracked, yet
            # on disk and absent from porcelain → genuinely unaccounted.
            return "fabricated"
        # 128 or any other non-{0,1} exit: log + fall back.
        logger.warning(
            "claim_audit: 'git check-ignore' returned %d for path %s "
            "in %s; stderr=%s. Falling back to critical classification.",
            result.returncode, path, self.worktree_path,
            result.stderr.strip(),
        )
        return "infra_error"

    def _git_path_is_tracked(self, path: str) -> Optional[bool]:
        """Return whether ``path`` is tracked in the worktree's git index.

        ``True`` when ``git ls-files --error-unmatch`` reports the path
        tracked (exit 0), ``False`` when it is untracked (exit 1), and
        ``None`` when the probe itself failed (git missing / timeout) — the
        caller treats ``None`` as ``infra_error`` to preserve the detection
        floor. A tracked file is never silently dropped by ``git add -A``,
        so this is the authoritative short-circuit for the check-ignore
        ``!``-negation false-positive (red-baseline retro, L12 item 6).
        """
        try:
            ls_result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", path],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning(
                "claim_audit: 'git ls-files --error-unmatch' failed "
                "(%s) for path %s in %s.",
                exc, path, self.worktree_path,
            )
            return None
        return ls_result.returncode == 0

    def _git_toplevel(self, start: Path) -> Optional[Path]:
        """Return the git working-tree root that owns ``start``, or None.

        ``start`` may be a file or directory; the probe runs from the
        nearest existing directory. Returns the resolved toplevel Path, or
        None when ``start`` is not inside any git repo, git is unavailable,
        or the probe fails. Used by :py:meth:`_classify_dropped_path` to
        detect cross-repo claims (TASK-FIX-XREPO-CAUD).
        """
        probe_dir = start if start.is_dir() else start.parent
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=probe_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return None
        if result.returncode != 0 or not result.stdout.strip():
            return None
        try:
            return Path(result.stdout.strip()).resolve()
        except OSError:
            return None

    def _path_under_declared_repo(self, abs_path: Path) -> Optional[str]:
        """Return the name of the declared evidence repo containing ``abs_path``.

        Returns None when no ``evidence_repos`` are declared or the path is
        outside every declared repo root. Lets the claim-audit ``cross_repo``
        branch stay silent on sibling-repo work the feature has opted into
        (verified by ``_verify_files_exist`` and staged by the per-repo
        checkpoint manager) rather than emitting an advisory
        (TASK-FIX-XREPO-CAUD).
        """
        if not self.evidence_repos:
            return None
        try:
            resolved = abs_path.resolve()
        except OSError:
            return None
        for repo in self.evidence_repos:
            try:
                resolved.relative_to(Path(repo.root).resolve())
            except (ValueError, OSError):
                continue
            return repo.name
        return None

    def _git_check_ignore_rule(self, path: str) -> str:
        """Return the matched ``<source>:<line>:<pattern>`` for ``path``.

        Should only be called after ``_classify_dropped_path`` returned
        ``"gitignored"``; on any anomaly returns the literal string
        ``"unknown"`` rather than raising, so the discrepancy still
        surfaces with a usable (if degraded) message.
        """
        try:
            result = subprocess.run(
                ["git", "check-ignore", "-v", "--no-index", "--", path],
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "unknown"
        if result.returncode != 0 or not result.stdout:
            return "unknown"
        # Output: ``<source>:<line>:<pattern><HT><pathname>`` — split on
        # the first tab to recover the rule prefix.
        first_line = result.stdout.splitlines()[0]
        if "\t" in first_line:
            return first_line.split("\t", 1)[0]
        return first_line

    def _normalize_claimed_path(self, path: str) -> str:
        """Normalise a claimed path so it can be compared with porcelain output.

        Three normalisation steps, applied in order:

        1. Strip leading ``./`` (Player reports sometimes prefix paths with
           it; ``git status`` never does).
        2. Strip trailing ``/`` (so ``adapters/`` matches ``adapters``).
        3. **Convert absolute paths to worktree-relative** (TASK-FIX-CAUD-J6F1):
           when the Player reports
           ``/Users/.../FEAT-X/src/foo.py`` and ``git status --porcelain``
           reports ``src/foo.py``, the literal-string membership test in
           :py:meth:`_verify_claims_were_staged` would otherwise produce a
           guaranteed false-positive ``claim_audit`` discrepancy.
           ``Path.resolve().relative_to(worktree_path.resolve())`` brings
           both sides to the same canonical form. Falls through unchanged
           when the path lives outside the worktree, when ``resolve()``
           fails (broken symlink, permission denied), or when the input
           is already relative — so genuinely-fabricated absolute paths
           outside the worktree still surface as discrepancies via the
           downstream classification.

        Backslashes are normalised to forward slashes so Windows-style
        paths in Player reports compare cleanly with porcelain (porcelain
        always emits forward slashes).
        """
        cleaned = path
        while cleaned.startswith("./"):
            cleaned = cleaned[2:]
        cleaned = cleaned.rstrip("/")

        # AC-001: absolute → worktree-relative. The membership-test in
        # _verify_claims_were_staged compares this output against
        # ``git status --porcelain`` which is always worktree-relative,
        # so absolute claims can never match without this step. See
        # TASK-FIX-CAUD-J6F1 / TASK-REV-J6F1 for the FEAT-JARVIS-006
        # repro that motivated this fix.
        candidate = Path(cleaned)
        if candidate.is_absolute():
            try:
                resolved = candidate.resolve()
                worktree_resolved = self.worktree_path.resolve()
                cleaned = str(
                    resolved.relative_to(worktree_resolved)
                ).replace("\\", "/")
            except (ValueError, OSError):
                # ValueError: path is absolute but lies outside the
                # worktree — leave as-is so the downstream
                # ``_classify_dropped_path`` flags it as fabricated.
                # OSError: resolve() failed (broken symlink, perm
                # denied). Same fallback: keep the original string so
                # the gate fails open rather than silently swallowing
                # the claim.
                pass
        return cleaned

    def _resolve_against_evidence_repos(self, rel_path: str) -> Optional[Path]:
        """Resolve an UNQUALIFIED claim against declared sibling evidence repos.

        TASK-FIX-XREPOPROM01 (FEAT-10AC run 1, 2026-07-04): a Player writing
        a declared sibling repo reports promise/claim paths RELATIVE TO THE
        SIBLING ROOT (``src/guardkitfactory/wiring/analyzer.py``) without the
        ``<repo>:`` qualifier the orchestrator injects for ``files_modified``.
        Resolving those Player-authored strings against the worktree root
        manufactured critical ``promise_file_existence`` + ``claim_audit``
        discrepancies three turns running (honesty collapse) while the work
        sat committed in the sibling's checkpoint commits — the
        ``evidence-boundary-narrower-than-write-surface`` false-red, at the
        two Player-authored-claim verifiers TASK-AB-XREPOEV01 did not widen.

        Declaration-bounded and permissive only on POSITIVE evidence: returns
        the resolved path ONLY when the file actually exists under a declared
        evidence repo root. A path that exists nowhere stays a critical
        discrepancy (the FEAT-6CC5 fabrication class is untouched), and with
        no declared repos the prior worktree-only behaviour is exact.
        """
        for repo in self.evidence_repos:
            candidate = repo.root / rel_path
            if candidate.exists():
                return candidate
        return None

    def _verify_completion_promises_files_exist(
        self, report: Dict[str, Any]
    ) -> List[Discrepancy]:
        """Verify files claimed in completion_promises[*].implementation_files exist.

        Catches the FEAT-6CC5 class of sophisticated dishonesty: Player keeps
        ``files_created`` / ``files_modified`` honest (containing only metadata
        that does exist) but lies in ``completion_promises`` with
        ``status: "complete"`` and ``implementation_files`` referencing source
        files that don't exist.

        Only ``status: "complete"`` promises are inspected; incomplete and
        rejected statuses are explicitly the Player flagging "not yet done"
        and require no honesty challenge.

        Args:
            report: Player report dictionary

        Returns:
            List of critical discrepancies for promised-but-missing files.
        """
        discrepancies: List[Discrepancy] = []
        promises = report.get("completion_promises") or []
        for promise in promises:
            if not isinstance(promise, dict):
                continue
            if promise.get("status") != "complete":
                continue
            impl_files = promise.get("implementation_files") or []
            criterion_id = promise.get("criterion_id", "?")
            for impl_file in impl_files:
                if not impl_file:
                    continue
                # TASK-AB-XREPOEV01: resolve a repo-qualified promise file
                # against the declared sibling repo root. Unknown repo ->
                # fail-open skip (path-string-mismatch rule); known + missing
                # -> critical, same rigor as a worktree promise.
                if split_qualified(impl_file) is not None:
                    sibling_path = resolve_qualified_path(
                        impl_file, self.evidence_repos
                    )
                    if sibling_path is None:
                        continue
                    if not sibling_path.exists():
                        discrepancies.append(
                            Discrepancy(
                                claim_type="promise_file_existence",
                                player_claim=(
                                    f"completion_promises[{criterion_id}]"
                                    f".status=complete with implementation_files "
                                    f"including {impl_file}"
                                ),
                                actual_value=(
                                    f"File does not exist in sibling repo "
                                    f"({sibling_path})"
                                ),
                                severity="critical",
                            )
                        )
                    continue
                if not (self.worktree_path / impl_file).exists():
                    # TASK-FIX-XREPOPROM01: before calling an unqualified
                    # promise path fabricated, try it as sibling-relative
                    # against each declared evidence repo. Positive hit ->
                    # resolved (recorded for audit), never a discrepancy;
                    # miss everywhere -> critical, exactly as before.
                    sibling_hit = self._resolve_against_evidence_repos(impl_file)
                    if sibling_hit is not None:
                        self._resolved_paths.append(
                            ResolvedPath(
                                claimed=str(impl_file),
                                resolved_to=str(sibling_hit),
                                task_id=self.task_id,
                            )
                        )
                        logger.debug(
                            "CoachVerifier suppressed promise_file_existence "
                            "discrepancy for %s via declared evidence repo "
                            "(%s)",
                            impl_file,
                            sibling_hit,
                        )
                        continue
                    discrepancies.append(
                        Discrepancy(
                            claim_type="promise_file_existence",
                            player_claim=(
                                f"completion_promises[{criterion_id}]"
                                f".status=complete with implementation_files "
                                f"including {impl_file}"
                            ),
                            actual_value=f"File does not exist at {impl_file}",
                            severity="critical",
                        )
                    )
        return discrepancies

    def _verify_test_count(self, report: Dict[str, Any]) -> List[Discrepancy]:
        """Verify test count in summary matches actual.

        Args:
            report: Player report dictionary

        Returns:
            List of discrepancies for mismatched counts
        """
        discrepancies: List[Discrepancy] = []

        summary = report.get("test_output_summary", "")
        if not summary:
            return discrepancies

        # Extract claimed count from summary (e.g., "5 passed in 0.23s")
        claimed_count = self._extract_test_count(summary)
        if claimed_count is None:
            return discrepancies

        # Run tests and get actual count (use cached result if available)
        actual_result = self._run_tests()
        actual_count = actual_result.test_count

        if claimed_count != actual_count:
            discrepancies.append(
                Discrepancy(
                    claim_type="test_count",
                    player_claim=f"{claimed_count} tests",
                    actual_value=f"{actual_count} tests",
                    severity="warning",
                )
            )

        return discrepancies

    def _run_tests(self, test_paths: list[str] | None = None, timeout: int = 120) -> TestResult:
        """Run tests in worktree and return result.

        Uses caching to avoid running tests multiple times in the same
        verification session. Caching is only used for unscoped runs.

        Args:
            test_paths: Optional list of test file/directory paths to scope
                the test run. When provided, pytest runs only against these
                paths instead of the entire worktree.
            timeout: Timeout in seconds for test execution. Default 120.
                Use higher values (e.g. 300) for state recovery contexts
                where parallel load may cause slower execution.

        Returns:
            TestResult with execution results
        """
        # Return cached result if available (only for unscoped runs)
        if test_paths is None and self._cached_test_result is not None:
            return self._cached_test_result

        # Build base pytest command. When a venv interpreter is known
        # (explicit param or discovered via _resolve_venv_python), invoke
        # pytest through it so Coach verifies against the same interpreter
        # the bootstrap produced (AC-TASK-FIX-7A05).
        if self._venv_python is not None:
            cmd = [str(self._venv_python), "-m", "pytest", "--tb=no", "-q"]
        else:
            cmd = ["pytest", "--tb=no", "-q"]
        if test_paths:
            cmd.extend(test_paths)

        # Detect test framework and run appropriate command
        try:
            result = subprocess.run(
                cmd,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            test_result = TestResult(
                passed=result.returncode == 0,
                test_count=self._parse_pytest_count(result.stdout),
                output=result.stdout,
            )
        except FileNotFoundError:
            logger.warning("pytest not found, trying python -m pytest")
            test_result = None
            # When a venv interpreter was resolved but missing at run time,
            # skip the PATH fallback — it would silently validate against
            # the wrong interpreter (the exact bug TASK-FIX-7A05 closes).
            fallback_interpreters: List[str] = (
                [str(self._venv_python)] if self._venv_python is not None
                else [sys.executable, "python3", "python"]
            )
            for python_cmd in fallback_interpreters:
                try:
                    fallback_cmd = [python_cmd, "-m", "pytest", "--tb=no", "-q"]
                    if test_paths:
                        fallback_cmd.extend(test_paths)
                    result = subprocess.run(
                        fallback_cmd,
                        cwd=self.worktree_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    test_result = TestResult(
                        passed=result.returncode == 0,
                        test_count=self._parse_pytest_count(result.stdout),
                        output=result.stdout,
                    )
                    break
                except FileNotFoundError:
                    continue
            if test_result is None:
                logger.error(
                    "Failed to run tests: no usable Python interpreter found "
                    "(tried: %s)",
                    ", ".join(fallback_interpreters),
                )
                test_result = TestResult(passed=False, test_count=0, output="")
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {timeout}s")
            test_result = TestResult(
                passed=False, test_count=0, output="Test execution timed out"
            )
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            test_result = TestResult(
                passed=False, test_count=0, output=str(e)
            )

        # Only cache unscoped runs
        if test_paths is None:
            self._cached_test_result = test_result

        return test_result

    def _extract_test_count(self, summary: str) -> Optional[int]:
        """Extract test count from summary string.

        Args:
            summary: Test output summary string (e.g., "5 passed in 0.23s")

        Returns:
            Number of passed tests, or None if not parseable
        """
        match = re.search(r"(\d+)\s+passed", summary)
        return int(match.group(1)) if match else None

    def _parse_pytest_count(self, output: str) -> int:
        """Parse test count from pytest output.

        Args:
            output: Raw pytest output

        Returns:
            Number of passed tests
        """
        match = re.search(r"(\d+)\s+passed", output)
        return int(match.group(1)) if match else 0

    def _count_verifiable_claims(self, report: Dict[str, Any]) -> int:
        """Count total verifiable claims in report.

        Args:
            report: Player report dictionary

        Returns:
            Number of verifiable claims
        """
        count = 0
        if report.get("tests_run"):
            count += 2  # tests_passed + test_count
        count += len(report.get("files_created", []))
        count += len(report.get("files_modified", []))
        count += len(report.get("tests_written", []))
        # TASK-AB-FIX-INVAB1 AC-001: count complete-promise files so the
        # honesty score arithmetic stays accurate when the new check fires.
        for promise in report.get("completion_promises") or []:
            if isinstance(promise, dict) and promise.get("status") == "complete":
                count += len(promise.get("implementation_files") or [])
        return max(count, 1)  # Avoid division by zero


def format_verification_context(verification: HonestyVerification) -> str:
    """Format verification results for inclusion in Coach prompt.

    Args:
        verification: HonestyVerification result

    Returns:
        Formatted string for prompt injection
    """
    lines = [
        "HONESTY VERIFICATION RESULTS:",
        "━" * 30,
        f"Honesty Score: {verification.honesty_score:.2f}",
        "",
    ]

    if verification.discrepancies:
        lines.append("DISCREPANCIES FOUND:")
        for disc in verification.discrepancies:
            severity_icon = "✗" if disc.severity == "critical" else "⚠"
            lines.append(f"  {severity_icon} [{disc.severity.upper()}] {disc.claim_type}")
            lines.append(f"    Player claimed: {disc.player_claim}")
            lines.append(f"    Actual value: {disc.actual_value}")
            lines.append("")
    else:
        lines.append("✓ All claims verified successfully")

    return "\n".join(lines)


__all__ = [
    "CoachVerifier",
    "Discrepancy",
    "HonestyVerification",
    "InterpreterResolutionError",
    "ResolvedPath",
    "TestResult",
    "_resolve_venv_python",
    "format_verification_context",
]
