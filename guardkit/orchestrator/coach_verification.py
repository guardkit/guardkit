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

logger = logging.getLogger(__name__)


def _resolve_venv_python(
    worktree_path: Path,
    explicit: Optional[Union[str, Path]],
) -> Optional[Path]:
    """Resolve the Python interpreter Coach should use for pytest.

    Resolution order (AC-TASK-FIX-7A05):
      1. Explicit path passed by the orchestrator (typically from
         BootstrapResult.venv_python).
      2. ``<worktree>/.guardkit/venv/bin/python`` when it exists on disk
         (recovery path when the explicit param wasn't threaded through).
      3. None — caller falls back to PATH ``pytest`` / ``sys.executable``
         behaviour for non-Python projects.
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

    filesystem = worktree_path / ".guardkit" / "venv" / "bin" / "python"
    if filesystem.exists():
        return filesystem

    return None


@dataclass
class Discrepancy:
    """A discrepancy between Player claim and reality.

    Attributes:
        claim_type: Type of claim ("test_result", "file_existence",
            "test_count", "claim_audit", "claim_audit_gitignored").
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
        """
        self.worktree_path = Path(worktree_path)
        self._cached_test_result: Optional[TestResult] = None
        self._venv_python: Optional[Path] = _resolve_venv_python(
            self.worktree_path, venv_python
        )
        if self._venv_python is not None:
            logger.debug(
                "CoachVerifier using interpreter %s for pytest", self._venv_python
            )
        self.task_id: Optional[str] = task_id
        self.state_bridge: Optional["TaskStateBridge"] = state_bridge
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
        claimed: set[str] = set()
        for key in ("files_created", "files_modified", "tests_written"):
            for entry in report.get(key) or []:
                if entry:
                    claimed.add(self._normalize_claimed_path(str(entry)))
        for promise in report.get("completion_promises") or []:
            if not isinstance(promise, dict):
                continue
            for entry in promise.get("implementation_files") or []:
                if entry:
                    claimed.add(self._normalize_claimed_path(str(entry)))
            test_file = promise.get("test_file")
            if test_file:
                claimed.add(self._normalize_claimed_path(str(test_file)))

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

        # TASK-FIX-IGNR: split the dropped set into "fabricated" (path is
        # absent from disk OR present but git would refuse to stage for a
        # non-ignore reason — e.g. tracked-but-unchanged) and "gitignored"
        # (path is on disk and ``git check-ignore -v --no-index`` matches
        # an ignore rule). The first stays ``severity="critical"`` because
        # the Player is claiming work that did not land. The second drops
        # to ``severity="should_fix"``: the Player-authored file exists,
        # the .gitignore is the bug, and short-circuiting the gate
        # produces the FEAT-39E1 turn-1 → turn-5 adversarial blow-up
        # documented in TASK-REV-F30A.
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
            else:
                # "fabricated" or "infra_error" — keep the critical
                # behaviour. infra_error here means ``git check-ignore``
                # itself broke (exit 128); we already logged a warning
                # in ``_classify_dropped_path``. Falling back to critical
                # preserves the FEAT-39E1 detection floor when the
                # gitignore probe is unavailable for any reason.
                discrepancies.append(
                    Discrepancy(
                        claim_type="claim_audit",
                        player_claim=f"Player claimed file {path}",
                        actual_value=(
                            "Path would not be staged by 'git add -A' "
                            "(absent from 'git status --porcelain'). Most "
                            "common cause: an unanchored .gitignore rule "
                            "silently filters the file. Other causes: "
                            "sparse-checkout, assume-unchanged, pathspec "
                            "attribute filters, or the file is tracked but "
                            "unchanged (Player claimed modified but didn't)."
                        ),
                        severity="critical",
                    )
                )
        return discrepancies

    def _classify_dropped_path(self, path: str) -> str:
        """Classify why ``path`` was absent from ``git status --porcelain``.

        Returns one of:
          * ``"fabricated"`` — path does not exist on disk (Player lied),
            or path exists but ``git check-ignore`` reports it as not
            ignored (tracked-but-unchanged, sparse-filter, etc.).
          * ``"gitignored"`` — path exists on disk and ``git check-ignore -v
            --no-index`` matches an ignore rule.
          * ``"infra_error"`` — ``git check-ignore`` itself failed (exit
            128 or a subprocess crash). Caller falls back to critical to
            preserve the detection floor.

        ``--no-index`` makes ``git check-ignore`` evaluate ignore rules
        against the path string regardless of whether the path is tracked,
        which is what we want here (the path was just dropped from
        porcelain, so it is, by definition, untracked-or-modified).
        """
        abs_path = self.worktree_path / path
        if not abs_path.exists():
            return "fabricated"

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
            return "gitignored"
        if result.returncode == 1:
            return "fabricated"
        # 128 or any other non-{0,1} exit: log + fall back.
        logger.warning(
            "claim_audit: 'git check-ignore' returned %d for path %s "
            "in %s; stderr=%s. Falling back to critical classification.",
            result.returncode, path, self.worktree_path,
            result.stderr.strip(),
        )
        return "infra_error"

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

    @staticmethod
    def _normalize_claimed_path(path: str) -> str:
        """Strip leading ``./`` so claimed paths match porcelain output.

        Player reports occasionally prefix paths with ``./``; ``git status``
        never does. Normalising both sides avoids false-fail mismatches on
        cosmetic differences. Trailing slashes (directory markers) are also
        stripped so ``adapters/`` matches ``adapters``.
        """
        cleaned = path
        while cleaned.startswith("./"):
            cleaned = cleaned[2:]
        return cleaned.rstrip("/")

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
                if not (self.worktree_path / impl_file).exists():
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
    "ResolvedPath",
    "TestResult",
    "_resolve_venv_python",
    "format_verification_context",
]
