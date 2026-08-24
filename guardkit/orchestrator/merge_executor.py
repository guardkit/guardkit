"""The merge primitive behind the merge word (make-merge-work, 2026-08-24).

Spec: ``docs/make-merge-work-build-spec-2026-08-24.md`` (ai-transition). Today
"merge" is a phrase — the build-complete message says the merge word is Rich's,
but nothing listens. This module is the mechanism: code — never an AI session —
merges ``autobuild/<FEATURE_ID>`` into the target branch, refuses loudly when
anything is off, and re-checks the merged result.

House pattern: ``machine_verify.py`` — pure functions, explicit inputs, one
frozen dataclass report with ``to_dict()`` and ``receipt_lines()``.

The three laws this module enforces:

* **Refuse, never half-do.** A dirty tree, a missing branch, or a target that
  has moved since the checks ran each refuse the merge before anything is
  touched.
* **The branch survives EVERY path.** ``autobuild/<FEATURE_ID>`` is the
  rollback path. This module never calls ``manager.cleanup()``, never deletes
  a branch, and on conflict aborts the merge and leaves the tree exactly as it
  found it.
* **Never invent a clean.** Post-merge verification only ever reports what it
  observed; with no pre-merge baseline the full observed failure set is
  reported with a note saying the diff is unavailable.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from guardkit.orchestrator.baseline import (
    compute_charged_failures,
    failing_node_ids,
    load_known_failure_ids,
)
from guardkit.orchestrator.completion_verification import (
    DEFAULT_VERIFY_TIMEOUT,
    VerificationResult,
    resolve_verify_command,
    run_completion_verification,
)
from guardkit.worktrees.manager import (
    Worktree,
    WorktreeManager,
    WorktreeMergeError,
)

logger = logging.getLogger(__name__)

# --- outcome constants (module-level so callers compare without the dataclass)
OUTCOME_MERGED = "merged"
OUTCOME_REFUSED = "refused"
OUTCOME_CONFLICT = "conflict"

_GIT_TIMEOUT_SECONDS = 60
_VALIDATE_TIMEOUT_SECONDS = 120


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeReport:
    """The one receipt-bearing report the merge primitive emits."""

    outcome: str  # OUTCOME_MERGED | OUTCOME_REFUSED | OUTCOME_CONFLICT
    feature_id: str
    target_branch: str
    branch: str  # autobuild/<FEATURE_ID> — retained on every path
    refusal_reason: Optional[str] = None
    pre_sha: Optional[str] = None
    post_sha: Optional[str] = None
    conflict_files: Tuple[str, ...] = ()
    verify_ran: bool = False
    verify_status: Optional[str] = None  # "passed" | "failed" | "unverified"
    verify_detail: str = ""
    validate_valid: Optional[bool] = None
    charged_failures: Tuple[str, ...] = ()
    notes: Tuple[str, ...] = ()

    @property
    def verify_ok(self) -> bool:
        """True only when every post-merge check positively passed.

        Requires the suite verification to be ``passed``, the feature YAML to
        validate, and zero charged failures. Absence of evidence is never a
        pass (absence-of-failure-is-not-success).
        """
        return (
            self.verify_ran
            and self.verify_status == "passed"
            and self.validate_valid is True
            and not self.charged_failures
        )

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "feature_id": self.feature_id,
            "target_branch": self.target_branch,
            "branch": self.branch,
            "refusal_reason": self.refusal_reason,
            "pre_sha": self.pre_sha,
            "post_sha": self.post_sha,
            "conflict_files": list(self.conflict_files),
            "verify_ran": self.verify_ran,
            "verify_status": self.verify_status,
            "verify_detail": self.verify_detail,
            "validate_valid": self.validate_valid,
            "charged_failures": list(self.charged_failures),
            "verify_ok": self.verify_ok,
            "notes": list(self.notes),
        }

    def receipt_lines(self) -> List[str]:
        """Plain sentences describing what happened — no jargon, no colour."""
        lines: List[str] = []
        if self.outcome == OUTCOME_REFUSED:
            lines.append(
                f"The merge of {self.feature_id} was refused before anything "
                f"was touched."
            )
            if self.refusal_reason:
                lines.append(f"Reason: {self.refusal_reason}")
        elif self.outcome == OUTCOME_CONFLICT:
            lines.append(
                f"The merge of branch {self.branch} into {self.target_branch} "
                f"hit conflicts, so it was aborted and the tree was left clean."
            )
            if self.conflict_files:
                lines.append("Files in conflict:")
                lines.extend(f"  - {p}" for p in self.conflict_files)
            lines.append(
                f"Branch {self.branch} is untouched and remains the rollback "
                f"path."
            )
        else:
            lines.append(
                f"{self.feature_id} merged into {self.target_branch}: "
                f"{(self.pre_sha or '?')[:12]} -> {(self.post_sha or '?')[:12]}."
            )
            lines.append(
                f"Branch {self.branch} is kept as the rollback path."
            )
            if not self.verify_ran:
                lines.append(
                    "The merged result was NOT verified (verification was "
                    "turned off for this run)."
                )
            else:
                if self.validate_valid is True:
                    lines.append("The feature file validates.")
                elif self.validate_valid is False:
                    lines.append("The feature file does NOT validate.")
                else:
                    lines.append(
                        "The feature file validation gave no usable answer."
                    )
                if self.verify_status == "passed":
                    lines.append(
                        f"The test suite passed on the merged result "
                        f"({self.verify_detail})."
                    )
                elif self.verify_status == "failed":
                    lines.append(
                        f"The test suite FAILED on the merged result "
                        f"({self.verify_detail})."
                    )
                else:
                    lines.append(
                        f"The test suite could not be verified "
                        f"({self.verify_detail}). This is not a pass."
                    )
                if self.charged_failures:
                    lines.append(
                        f"{len(self.charged_failures)} failing test(s) are "
                        f"charged to this merge (not excused by the baseline "
                        f"or the known-failures ledger):"
                    )
                    lines.extend(f"  - {n}" for n in self.charged_failures)
        for note in self.notes:
            lines.append(f"Note: {note}")
        return lines


# ---------------------------------------------------------------------------
# git plumbing (explicit, timeout-bounded, never raises past the boundary)
# ---------------------------------------------------------------------------


def _run_git(
    repo_root: Path, *args: str
) -> subprocess.CompletedProcess:
    """Run one git command in ``repo_root``; never raises on non-zero exit."""
    return subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=_GIT_TIMEOUT_SECONDS,
    )


def _rev_parse(repo_root: Path, ref: str) -> Optional[str]:
    proc = _run_git(repo_root, "rev-parse", "--verify", "--quiet", ref)
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


def _porcelain_status(repo_root: Path) -> Optional[str]:
    """``git status --porcelain`` output, or None when git itself failed."""
    proc = _run_git(repo_root, "status", "--porcelain")
    if proc.returncode != 0:
        return None
    return proc.stdout


def conflicted_files_from_status(porcelain: str) -> List[str]:
    """Paths from the ``UU`` rows of ``git status --porcelain`` output."""
    files: List[str] = []
    for line in porcelain.splitlines():
        if line.startswith("UU "):
            files.append(line[3:].strip())
    return files


# ---------------------------------------------------------------------------
# Refusal preflight
# ---------------------------------------------------------------------------


def preflight_refusal(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    expect_target_sha: Optional[str] = None,
) -> Optional[str]:
    """Return the refusal reason, or None when the merge may proceed.

    Refusals (each checked before anything is touched):

    * ``repo_root`` is not a git repository;
    * the working tree is dirty (``git status --porcelain`` non-empty);
    * branch ``autobuild/<FEATURE_ID>`` does not exist;
    * ``expect_target_sha`` is given and the target branch no longer resolves
      to it — the checks were run against a target that has since moved.
    """
    proc = _run_git(repo_root, "rev-parse", "--git-dir")
    if proc.returncode != 0:
        return f"{repo_root} is not a git repository"

    porcelain = _porcelain_status(repo_root)
    if porcelain is None:
        return "git status could not be read"
    if porcelain.strip():
        dirty = [ln for ln in porcelain.splitlines() if ln.strip()]
        shown = "; ".join(dirty[:5])
        more = f" (and {len(dirty) - 5} more)" if len(dirty) > 5 else ""
        return (
            f"the working tree is dirty — refuse to merge over uncommitted "
            f"changes: {shown}{more}"
        )

    branch = f"autobuild/{feature_id}"
    if _rev_parse(repo_root, f"refs/heads/{branch}") is None:
        return f"branch {branch} does not exist"

    if expect_target_sha:
        actual = _rev_parse(repo_root, target_branch)
        if actual is None:
            return f"branch {target_branch} does not exist"
        expected = expect_target_sha.strip()
        matches = actual == expected or (
            len(expected) >= 7 and actual.startswith(expected)
        )
        if not matches:
            return (
                f"{target_branch} has moved since the checks ran "
                f"(expected {expected}, found {actual})"
            )

    return None


# ---------------------------------------------------------------------------
# The merge itself
# ---------------------------------------------------------------------------


def merge_commit_message(
    feature_id: str, pre_sha: str, branch_sha: str
) -> str:
    """The template message, filled ONLY from the build's own records.

    ``pre_sha`` is the target branch head before the merge; ``branch_sha`` is
    the tip of ``autobuild/<FEATURE_ID>`` being merged (the merge commit
    cannot carry its own sha, so the range in the message is
    target-before..branch-tip). No model writes this.
    """
    return (
        f"merge({feature_id}): merged on the merge word\n\n"
        f"{pre_sha[:12]}..{branch_sha[:12]} — branch autobuild/{feature_id} "
        f"retained as the rollback path"
    )


def perform_merge(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    manager: Optional[WorktreeManager] = None,
) -> MergeReport:
    """Merge ``autobuild/<FEATURE_ID>`` into ``target_branch``.

    On :class:`WorktreeMergeError`: capture the conflicted files, run
    ``git merge --abort`` (its own failure is ignored), re-verify the tree is
    clean, and report outcome ``conflict``. The branch is NEVER deleted on any
    path — no ``cleanup()``, no ``auto_merge_if_graduated``, no
    preserve-then-delete.
    """
    branch = f"autobuild/{feature_id}"
    notes: List[str] = []

    pre_sha = _rev_parse(repo_root, target_branch)
    branch_sha = _rev_parse(repo_root, branch)
    if pre_sha is None or branch_sha is None:
        return MergeReport(
            outcome=OUTCOME_REFUSED,
            feature_id=feature_id,
            target_branch=target_branch,
            branch=branch,
            refusal_reason=(
                f"could not resolve {target_branch} and {branch} to commits"
            ),
        )

    if manager is None:
        manager = WorktreeManager(repo_root=Path(repo_root))

    # Only task_id and branch_name are read by ``manager.merge``; the path
    # need not exist (the ``_find_worktree`` reconstruction pattern —
    # cli/autobuild.py). The feature file may already be archived, so nothing
    # here reads the feature YAML either.
    worktree = Worktree(
        task_id=feature_id,
        branch_name=branch,
        path=Path(repo_root) / ".guardkit" / "worktrees" / feature_id,
        base_branch=target_branch,
    )

    message = merge_commit_message(feature_id, pre_sha, branch_sha)

    try:
        manager.merge(worktree, target_branch=target_branch, message=message)
    except WorktreeMergeError as exc:
        # Conflict path: capture the UU rows BEFORE aborting (the abort wipes
        # them), then abort and re-verify the tree is clean.
        status_before_abort = _porcelain_status(repo_root) or ""
        conflict_files = conflicted_files_from_status(status_before_abort)

        abort = _run_git(repo_root, "merge", "--abort")
        if abort.returncode != 0:
            # Ignored by design (there may be nothing to abort), but recorded.
            notes.append(
                f"git merge --abort exited {abort.returncode}: "
                f"{abort.stderr.strip() or '(no stderr)'}"
            )

        status_after = _porcelain_status(repo_root)
        if status_after is None or status_after.strip():
            notes.append(
                "the working tree is NOT clean after the abort — "
                "look before touching anything"
            )
        notes.append(f"merge error: {exc}")

        return MergeReport(
            outcome=OUTCOME_CONFLICT,
            feature_id=feature_id,
            target_branch=target_branch,
            branch=branch,
            pre_sha=pre_sha,
            conflict_files=tuple(conflict_files),
            notes=tuple(notes),
        )

    post_sha = _rev_parse(repo_root, target_branch)
    return MergeReport(
        outcome=OUTCOME_MERGED,
        feature_id=feature_id,
        target_branch=target_branch,
        branch=branch,
        pre_sha=pre_sha,
        post_sha=post_sha,
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Post-merge verification
# ---------------------------------------------------------------------------


def default_validate_command(feature_id: str) -> List[str]:
    """The ``guardkit feature validate <fid> --json`` argv.

    Prefers the installed ``guardkit`` console script; falls back to
    ``python -m guardkit.cli.main`` (the documented module entry point) so the
    validation runs in exactly the environment running this executor.
    """
    exe = shutil.which("guardkit")
    if exe:
        return [exe, "feature", "validate", feature_id, "--json"]
    return [
        sys.executable,
        "-m",
        "guardkit.cli.main",
        "feature",
        "validate",
        feature_id,
        "--json",
    ]


def parse_validate_stdout(stdout: str) -> Tuple[Optional[bool], str]:
    """Parse the ``feature validate --json`` STDOUT into ``(valid, detail)``.

    STDOUT ONLY — an INFO line rides stderr and must never reach this parser.
    Returns ``(None, reason)`` when no verdict could be read (never a pass).
    """
    text = stdout.strip()
    if not text:
        return None, "feature validate printed nothing on stdout"
    try:
        data = json.loads(text)
    except ValueError:
        return None, "feature validate stdout was not JSON"
    if not isinstance(data, dict) or "valid" not in data:
        return None, "feature validate JSON carried no 'valid' field"
    detail = ""
    errors = data.get("errors") or []
    if errors:
        detail = "; ".join(str(e) for e in errors[:5])
    return bool(data["valid"]), detail


def run_feature_validate(
    repo_root: Path,
    feature_id: str,
    validate_command: Optional[Sequence[str]] = None,
) -> Tuple[Optional[bool], str]:
    """Run ``guardkit feature validate <fid> --json`` and parse STDOUT only."""
    argv = list(validate_command or default_validate_command(feature_id))
    try:
        proc = subprocess.run(
            argv,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=_VALIDATE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"feature validate could not run: {exc}"
    return parse_validate_stdout(proc.stdout)


def charged_failures_from_output(
    repo_root: Path,
    verification_output: Optional[str],
    baseline_failing: Optional[Sequence[str]],
) -> Tuple[List[str], List[str]]:
    """``(charged, notes)`` from the post-merge suite output.

    ``observed - (baseline ∪ ledger)`` via the same primitives the Coach loop
    uses. ``baseline_failing=None`` means no pre-merge baseline exists: the
    FULL observed set is reported (minus only the human-triaged ledger) with a
    note that the diff is unavailable — never an invented clean.
    """
    notes: List[str] = []
    observed = failing_node_ids(verification_output)
    ledger = load_known_failure_ids(Path(repo_root))
    charged = compute_charged_failures(
        observed_node_ids=observed,
        baseline_node_ids=list(baseline_failing or []),
        ledger_ids=ledger,
    )
    if baseline_failing is None and observed:
        notes.append(
            "no pre-merge baseline — diff unavailable; the full observed "
            "failure set is reported"
        )
    return charged, notes


def verify_merged(
    repo_root: Path,
    feature_id: str,
    baseline_failing: Optional[Sequence[str]] = None,
    timeout: int = DEFAULT_VERIFY_TIMEOUT,
    validate_command: Optional[Sequence[str]] = None,
) -> Tuple[Optional[bool], VerificationResult, List[str], List[str]]:
    """The three post-merge checks, in order.

    Returns ``(validate_valid, verification, charged_failures, notes)``:

    * (a) ``guardkit feature validate <fid> --json`` as a subprocess with
      ``cwd=repo_root``, STDOUT parsed exclusively;
    * (b) the resolved verification command run in the merged repo — only
      ``status == "passed"`` is ever success (venv-pinned precedence lives in
      ``resolve_verify_command``);
    * (c) the failing node ids charged to this merge, diffed against the
      pre-merge baseline and the known-failures ledger.
    """
    notes: List[str] = []

    validate_valid, validate_detail = run_feature_validate(
        repo_root, feature_id, validate_command=validate_command
    )
    if validate_valid is None:
        notes.append(f"feature validation gave no verdict: {validate_detail}")
    elif validate_valid is False and validate_detail:
        notes.append(f"feature validation errors: {validate_detail}")

    command, source, profile = resolve_verify_command(Path(repo_root))
    verification = run_completion_verification(
        Path(repo_root),
        command,
        source,
        stack_profile=profile,
        timeout=timeout,
    )

    # The runner output available here is the recorded tail (capped at 2000
    # characters by run_completion_verification); a very long failure list may
    # be under-reported — the status verdict above is unaffected.
    charged, charge_notes = charged_failures_from_output(
        repo_root, verification.output_tail, baseline_failing
    )
    notes.extend(charge_notes)

    return validate_valid, verification, charged, notes


# ---------------------------------------------------------------------------
# Assembly — preflight, merge, verify, one report
# ---------------------------------------------------------------------------


def execute_merge(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    expect_target_sha: Optional[str] = None,
    verify: bool = True,
    baseline_failing: Optional[Sequence[str]] = None,
    verify_timeout: int = DEFAULT_VERIFY_TIMEOUT,
    manager: Optional[WorktreeManager] = None,
    validate_command: Optional[Sequence[str]] = None,
) -> MergeReport:
    """Refusal preflight, then the merge, then post-merge verification.

    Every outcome is a :class:`MergeReport`. The ``autobuild/<FEATURE_ID>``
    branch survives every path.
    """
    repo_root = Path(repo_root)
    branch = f"autobuild/{feature_id}"

    reason = preflight_refusal(
        repo_root, feature_id, target_branch, expect_target_sha
    )
    if reason is not None:
        return MergeReport(
            outcome=OUTCOME_REFUSED,
            feature_id=feature_id,
            target_branch=target_branch,
            branch=branch,
            refusal_reason=reason,
        )

    report = perform_merge(
        repo_root, feature_id, target_branch, manager=manager
    )
    if report.outcome != OUTCOME_MERGED or not verify:
        return report

    validate_valid, verification, charged, notes = verify_merged(
        repo_root,
        feature_id,
        baseline_failing=baseline_failing,
        timeout=verify_timeout,
        validate_command=validate_command,
    )

    return MergeReport(
        outcome=report.outcome,
        feature_id=report.feature_id,
        target_branch=report.target_branch,
        branch=report.branch,
        pre_sha=report.pre_sha,
        post_sha=report.post_sha,
        verify_ran=True,
        verify_status=verification.status,
        verify_detail=verification.detail,
        validate_valid=validate_valid,
        charged_failures=tuple(charged),
        notes=tuple(list(report.notes) + notes),
    )


__all__ = [
    "OUTCOME_MERGED",
    "OUTCOME_REFUSED",
    "OUTCOME_CONFLICT",
    "MergeReport",
    "conflicted_files_from_status",
    "preflight_refusal",
    "merge_commit_message",
    "perform_merge",
    "default_validate_command",
    "parse_validate_stdout",
    "run_feature_validate",
    "charged_failures_from_output",
    "verify_merged",
    "execute_merge",
]
