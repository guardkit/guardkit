"""The merge primitive behind the merge word (make-merge-work, 2026-08-24).

Spec: ``docs/make-merge-work-build-spec-2026-08-24.md`` (ai-transition). Today
"merge" is a phrase — the build-complete message says the merge word is Rich's,
but nothing listens. This module is the mechanism: code — never an AI session —
merges ``autobuild/<FEATURE_ID>`` into the target branch, refuses loudly when
anything is off, and re-checks the merged result.

Since 2026-09-07 (Part M of the rewrite-on-refusal lane, rule 53) the merge
takes the branch to merge: a repair build's commits live on the branch that
build made, not on ``autobuild/<FEATURE_ID>``. When no branch is named, the
feature's own ``autobuild/<FEATURE_ID>`` is merged exactly as before; either
way the report's ``branch`` field names the branch that was merged. The
branch is the ONLY thing that changes with it — the target pin, the verify
run and the exit codes are untouched.

House pattern: pure functions, explicit inputs, one frozen dataclass report
with ``to_dict()`` and ``receipt_lines()``.

The three laws this module enforces:

* **Refuse, never half-do.** A dirty tree, a missing branch, or a target that
  has moved since the checks ran each refuse the merge before anything is
  touched.
* **The branch survives EVERY path.** The branch merged
  (``autobuild/<FEATURE_ID>`` for a feature build) is the rollback path.
  This module never calls ``manager.cleanup()``, never deletes
  a branch, and on conflict aborts the merge and leaves the tree exactly as it
  found it.
* **Only a check that ran and passed is ok (31 October 2026).** The full
  check the project declares runs on the joined result, once, every part in
  its own folder. ``verify_ok`` is true only when it passed: a check that
  could not run is not a pass (FEAT-8BB4 was published unchecked that way).
  There is no known-failure baseline: a failure fails the merge.
* **A branch never chooses the command that judges it.** The check is
  resolved on the TARGET branch, before the merge, and that resolution runs
  on the joined result (2026-09-06 spec, rule 11). See
  :func:`resolve_verify_command_on_target` for why.
"""

from __future__ import annotations

import logging
import os
import stat
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from guardkit.orchestrator.completion_verification import (
    DEFAULT_VERIFY_TIMEOUT,
    VerificationResult,
    check_command_texts,
    part_install_texts,
    resolve_verify_command,
    resolve_verify_command_with_declaration,
    run_completion_verification,
)
from guardkit.orchestrator.merge_environment import (
    JUDGE_FILES_CHANGED,
    JUDGE_IS_A_LINK,
    MergeEnvironment,
    judge_files,
    judge_links,
    judges_kept_from_target,
    pin_merge_environment,
    read_merge_declarations,
    shown_path,
    tree_entries,
)
from guardkit.orchestrator.launch_declaration import LaunchEnvironmentError
from guardkit.orchestrator.process_group import run_in_own_group
from guardkit.orchestrator.project_command_env import (
    project_command_environment,
)
from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration
from guardkit.worktrees.manager import (
    Worktree,
    WorktreeManager,
    WorktreeMergeError,
)
from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)

# --- outcome constants (module-level so callers compare without the dataclass)
OUTCOME_MERGED = "merged"
OUTCOME_REFUSED = "refused"
OUTCOME_CONFLICT = "conflict"

_GIT_TIMEOUT_SECONDS = 60


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MergeReport:
    """The one receipt-bearing report the merge primitive emits."""

    outcome: str  # OUTCOME_MERGED | OUTCOME_REFUSED | OUTCOME_CONFLICT
    feature_id: str
    target_branch: str
    # The branch that was merged: autobuild/<FEATURE_ID> unless one was named.
    # Retained on every path.
    branch: str
    refusal_reason: Optional[str] = None
    pre_sha: Optional[str] = None
    post_sha: Optional[str] = None
    conflict_files: Tuple[str, ...] = ()
    # True only when the check ran on the joined result and gave a verdict
    # ("passed" or "failed"). False when verification was turned off and when
    # the check could not run (2026-09-06 spec, rule 12). ``verify_status``
    # tells the two apart: None when verification was off, "unverified" when
    # it could not run.
    verify_ran: bool = False
    # The full check's verdict on the joined result: "passed", "failed", or
    # "unverified" (it could not run).
    verify_status: Optional[str] = None  # "passed" | "failed" | "unverified"
    verify_detail: str = ""
    verify_command: Optional[str] = None
    verify_source: Optional[str] = None
    notes: Tuple[str, ...] = ()
    # The judge files whose joined version differed from the target's, so the
    # checks after the join used the target's copy and not the joined one
    # (15 October 2026). Empty when nothing was put in place. Set whenever
    # the target's copies were put in place, whatever happened next.
    judged_with_main_copies: Tuple[str, ...] = ()
    # Those of them the joined-onto commit does not have: they were left out
    # of the folder for the install and the check.
    judge_files_not_on_target: Tuple[str, ...] = ()
    # The judge files whose joined version differed from the target's and
    # are not under the project's protected paths, so the joined (the
    # build's) version was kept for the checks after the join (28 October
    # 2026). Like ``judged_with_main_copies``, it says what was in place,
    # not what ran.
    judged_with_build_copies: Tuple[str, ...] = ()
    # The last part of what the check after the join printed, when it did not
    # pass (28 October 2026). Step 2 request 9 (FEAT-0A55) failed with "exit
    # 1, no failing tests named" and nothing else, so the cause could not be
    # read without running the check again.
    verify_output_tail: str = ""

    @property
    def verify_ok(self) -> bool:
        """True only when the project's full check ran on the joined result
        and passed (31 October 2026). A check that could not run
        (``unverified``) or was turned off is not ok."""
        return self.verify_status == "passed"

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
            "verify_ok": self.verify_ok,
            "verify_command": self.verify_command,
            "verify_source": self.verify_source,
            "notes": list(self.notes),
            "judged_with_main_copies": list(self.judged_with_main_copies),
            "judge_files_not_on_target": list(self.judge_files_not_on_target),
            "judged_with_build_copies": list(self.judged_with_build_copies),
            "verify_output_tail": self.verify_output_tail,
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
                lines.extend(f"  - {shown_path(p)}" for p in self.conflict_files)
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
            if self.verify_status is None:
                # Verification was turned off. A check that was ATTEMPTED and
                # could not run says "unverified" instead, and is reported
                # below in full — it must never be mistaken for a run nobody
                # asked for.
                lines.append(
                    "The merged result was NOT verified (verification was "
                    "turned off for this run)."
                )
            else:
                if self.verify_command:
                    # "would have been" on the unverified path: there the
                    # report itself says the run was never made, and a
                    # receipt must never imply tests ran that did not.
                    ran_words = (
                        "The tests would have been run with"
                        if self.verify_status == "unverified"
                        else "The tests were run with"
                    )
                    lines.append(
                        f"{ran_words}: {self.verify_command} "
                        f"(that command came from the {self.verify_source})."
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
                        f"The tests were not run on the merged result "
                        f"({self.verify_detail})."
                    )
                # What was put in place for the install and checks after the
                # join: nothing about what ran, or where else the build's
                # changes did or did not run.
                at = (self.pre_sha or "?")[:10]
                absent = set(self.judge_files_not_on_target)
                kept = [
                    shown_path(p)
                    for p in self.judged_with_main_copies
                    if p not in absent
                ]
                left_out = [
                    shown_path(p) for p in self.judged_with_main_copies if p in absent
                ]
                if kept:
                    one = len(kept) == 1
                    lines.append(
                        f"For the install and checks after the join, "
                        f"{', '.join(kept)} {'was' if one else 'were'} put back "
                        f"to {'its' if one else 'their'} version at {at}, the "
                        f"commit the build was joined onto, so this build's "
                        f"changes to {'it were' if one else 'them were'} not used."
                    )
                if left_out:
                    one = len(left_out) == 1
                    lines.append(
                        f"{', '.join(left_out)} {'is' if one else 'are'} not on "
                        f"the commit the build was joined onto ({at}), so "
                        f"{'it was' if one else 'they were'} left out for the "
                        f"install and checks after the join."
                    )
                ran_own = [shown_path(p) for p in self.judged_with_build_copies]
                if ran_own:
                    one = len(ran_own) == 1
                    lines.append(
                        f"This build changed {', '.join(ran_own)}, which "
                        f"{'is' if one else 'are'} not under the project's "
                        f"protected paths, so this build's "
                        f"{'version was' if one else 'versions were'} kept for "
                        f"the install and checks after the join."
                    )
        for note in self.notes:
            lines.append(f"Note: {note}")
        return lines


# ---------------------------------------------------------------------------
# git plumbing (explicit, timeout-bounded, never raises past the boundary)
# ---------------------------------------------------------------------------


def _run_git(
    repo_root: Path, *args: str
) -> subprocess.CompletedProcess:
    """Run one git command in ``repo_root``; never raises on non-zero exit.

    Output naming a file in bytes that are not UTF-8 (``git status`` under
    ``core.quotePath=false``, for one) is kept as ``os.fsdecode`` keeps it,
    so reading it never fails; any such name shown in a sentence goes
    through :func:`shown_path`."""
    return run_git(
        [*args],
        cwd=str(repo_root),
        timeout=_GIT_TIMEOUT_SECONDS,
        errors="surrogateescape",
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


def current_branch(repo_root: Path) -> Optional[str]:
    """The branch HEAD is on, or ``None`` when HEAD is detached/unreadable."""
    proc = _run_git(repo_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if proc.returncode != 0:
        return None
    name = proc.stdout.strip()
    return name or None


def checkout_branch(repo_root: Path, branch: str) -> Optional[str]:
    """Put HEAD on ``branch``. Returns a plain reason on failure, else None.

    A no-op when HEAD is already there. The caller has already refused a
    dirty tree, so this moves nothing a person had not committed.
    """
    try:
        return _checkout_branch(repo_root, branch)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"could not switch to branch {branch}: {_failure_words(exc)}"


def _checkout_branch(repo_root: Path, branch: str) -> Optional[str]:
    """:func:`checkout_branch` itself; may raise a git timeout or failure."""
    if current_branch(repo_root) == branch:
        return None
    # Said in a build worktree's HEAD record when this folder is one (build
    # 0D7C, 12 October 2026); nothing is written anywhere else.
    from guardkit.orchestrator.head_identity import record_git_operation

    record_git_operation(
        repo_root,
        actor="guardkit merge_executor.checkout_branch",
        operation=f"checkout {branch}",
        only_if_recorded=True,
    )
    proc = _run_git(repo_root, "checkout", branch)
    if proc.returncode != 0:
        # The helper's fixed sentence; git's own output is never repeated.
        detail = (proc.stderr or "").strip() or f"git checkout exited {proc.returncode}"
        return f"could not switch to branch {branch}: {detail}"
    return None


# ---------------------------------------------------------------------------
# Which branch
# ---------------------------------------------------------------------------


def branch_to_merge(feature_id: str, branch: Optional[str] = None) -> str:
    """The branch the merge word merges.

    ``branch`` when one was named (a repair build's own branch, say);
    otherwise the feature's own ``autobuild/<FEATURE_ID>``, exactly as every
    feature build has always been merged. An empty name counts as none.
    This is the ONE place the default is written down.
    """
    if branch is not None and branch.strip():
        return branch.strip()
    return f"autobuild/{feature_id}"


# ---------------------------------------------------------------------------
# Refusal preflight
# ---------------------------------------------------------------------------


def preflight_refusal(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    expect_target_sha: Optional[str] = None,
    branch: Optional[str] = None,
) -> Optional[str]:
    """Return the refusal reason, or None when the merge may proceed
    (:func:`_preflight_refusal`). A git command that times out or fails here
    is a refusal with its plain reason, never an error."""
    try:
        return _preflight_refusal(
            repo_root, feature_id, target_branch, expect_target_sha, branch
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"git could not be read before the merge: {_failure_words(exc)}"


def _preflight_refusal(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    expect_target_sha: Optional[str] = None,
    branch: Optional[str] = None,
) -> Optional[str]:
    """Return the refusal reason, or None when the merge may proceed.

    Refusals (each checked before anything is touched):

    * ``repo_root`` is not a git repository;
    * the working tree is dirty (``git status --porcelain`` non-empty);
    * the branch to merge (``branch``, else ``autobuild/<FEATURE_ID>``)
      does not exist — the reason names it;
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

    branch = branch_to_merge(feature_id, branch)
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
    feature_id: str,
    pre_sha: str,
    branch_sha: str,
    branch: Optional[str] = None,
) -> str:
    """The template message, filled ONLY from the build's own records.

    ``pre_sha`` is the target branch head before the merge; ``branch_sha`` is
    the tip of the branch being merged (``branch``, else
    ``autobuild/<FEATURE_ID>``; the merge commit cannot carry its own sha, so
    the range in the message is target-before..branch-tip). No model writes
    this.
    """
    branch = branch_to_merge(feature_id, branch)
    return (
        f"merge({feature_id}): merged on the merge word\n\n"
        f"{pre_sha[:12]}..{branch_sha[:12]} — branch {branch} "
        f"retained as the rollback path"
    )


def perform_merge(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    manager: Optional[WorktreeManager] = None,
    branch: Optional[str] = None,
    working_folder: Optional[Path] = None,
    merge_commit: Optional[str] = None,
) -> MergeReport:
    """Merge the build's branch into ``target_branch``.

    The branch is ``branch`` when one was named, else
    ``autobuild/<FEATURE_ID>`` (:func:`branch_to_merge`).

    On :class:`WorktreeMergeError`: capture the conflicted files, run
    ``git merge --abort`` (its own failure is ignored), re-verify the tree is
    clean, and report outcome ``conflict``. The branch is NEVER deleted on any
    path — no ``cleanup()``, no ``auto_merge_if_graduated``, no
    preserve-then-delete.

    ``working_folder`` is the folder the merge happens in. ``None`` is the
    repository's main copy, exactly as before. A caller that hands one in —
    a working folder of its own, made at the commit being joined onto — gets
    the checkout, the merge, the conflict reading and the abort all run
    THERE, and the repository's main copy is never switched or merged into.
    The commits, the refs and the objects are the same either way: a working
    folder of a repository shares all three.

    ``merge_commit`` (13 October 2026) is the commit to join, already
    resolved from ``branch`` by the caller. Given it, that exact commit is
    merged, so what was checked before the merge is what lands even if the
    branch moves meanwhile; the report still names ``branch``. ``None``
    merges ``branch`` as before.
    """
    branch = branch_to_merge(feature_id, branch)
    notes: List[str] = []
    # Where the tree is. Every read of a tree below goes here; every read of
    # a ref may go here too, because a working folder shares the repository's
    # refs.
    tree_root = Path(working_folder) if working_folder is not None else Path(repo_root)

    unreadable = ""
    try:
        pre_sha = _rev_parse(tree_root, target_branch)
        branch_sha = (
            _rev_parse(tree_root, f"{merge_commit}^{{commit}}")
            if merge_commit
            else _rev_parse(tree_root, branch)
        )
    except (OSError, subprocess.SubprocessError) as exc:
        pre_sha = branch_sha = None
        unreadable = f" ({_failure_words(exc)})"
    if pre_sha is None or branch_sha is None:
        return MergeReport(
            outcome=OUTCOME_REFUSED,
            feature_id=feature_id,
            target_branch=target_branch,
            branch=branch,
            refusal_reason=(
                f"could not resolve {target_branch} and {branch} to commits"
                f"{unreadable}"
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
        # The ref ``git merge`` is given: the resolved commit when there is
        # one, so the commit checked is the commit joined.
        branch_name=branch_sha if merge_commit else branch,
        path=Path(repo_root) / ".guardkit" / "worktrees" / feature_id,
        base_branch=target_branch,
    )

    message = merge_commit_message(
        feature_id, pre_sha, branch_sha, branch=branch
    )

    try:
        manager.merge(
            worktree,
            target_branch=target_branch,
            message=message,
            working_folder=working_folder,
        )
    except WorktreeMergeError as exc:
        # Conflict path: capture the UU rows BEFORE aborting (the abort wipes
        # them), then abort and re-verify the tree is clean.
        # A git command that times out or fails here is recorded, never
        # raised: the report is still made.
        try:
            status_before_abort = _porcelain_status(tree_root) or ""
        except (OSError, subprocess.SubprocessError) as exc:
            status_before_abort = ""
            notes.append(
                f"the files in conflict could not be read: {_failure_words(exc)}"
            )
        conflict_files = conflicted_files_from_status(status_before_abort)

        try:
            abort = _run_git(tree_root, "merge", "--abort")
            if abort.returncode != 0:
                # Ignored by design (there may be nothing to abort), but
                # recorded.
                notes.append(
                    f"git merge --abort exited {abort.returncode}: "
                    f"{abort.stderr.strip() or '(no stderr)'}"
                )
        except (OSError, subprocess.SubprocessError) as exc:
            notes.append(f"git merge --abort did not finish: {_failure_words(exc)}")

        try:
            status_after = _porcelain_status(tree_root)
        except (OSError, subprocess.SubprocessError):
            status_after = None
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

    try:
        post_sha = _rev_parse(tree_root, target_branch)
    except (OSError, subprocess.SubprocessError) as exc:
        # Joined, but the new commit could not be read: nothing after this
        # can be checked against it, and the report says so.
        post_sha = None
        notes.append(
            f"the joined commit on {target_branch} could not be read: "
            f"{_failure_words(exc)}"
        )
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
# Choosing the check on the target
# ---------------------------------------------------------------------------


def resolve_verify_command_on_target(
    repo_root: Path,
    target_branch: str = "main",
    smoke_command: Optional[str] = None,
) -> Tuple[
    Tuple[Optional[str], str, Optional[ToolchainDeclaration]], Optional[str]
]:
    """Choose the test command on the TARGET branch, before any merge.

    Returns ``(resolution, problem)``: the ``(command, source, profile)``
    triple :func:`resolve_verify_command` gives, and a plain reason when HEAD
    could not be put on the target branch first — in which case the
    resolution was made against whatever tree was in front of us and the
    caller must not trust it.

    Why the target branch, and why before the merge (2026-09-06 spec, rule
    11). ``resolve_verify_command`` reads the repository's declared test
    command out of ``.guardkit/config.yaml`` in the WORKING TREE, and that
    file lives inside the very repository being merged. Resolve it after the
    merge and the branch under judgement has just written the command that
    judges it: a branch that sets ``toolchain.test`` to ``true`` and adds any
    number of failing tests would merge green, its own new red never run.

    ``toolchain_declaration.py`` names this danger in its second law — "the
    declaration is snapshotted before the model's first turn ... without a
    snapshot, a Player turn could rewrite ``toolchain.test`` to ``true`` and
    green itself" — and answers it by pinning a copy of the declaration
    outside the worktree before turn 1. This function is that same law at the
    merge's own scale. The merge's snapshot is the resolution made here, on
    the target branch, before anything lands; handed on unchanged, it is what
    verifies the merged tree, so the merge is judged by a check the branch
    could not touch.
    """
    repo_root = Path(repo_root)
    problem = checkout_branch(repo_root, target_branch)
    resolution = resolve_verify_command(
        repo_root, smoke_command=smoke_command
    )
    return resolution, problem


# ---------------------------------------------------------------------------
# Post-merge verification
# ---------------------------------------------------------------------------


def verify_merged(
    repo_root: Path,
    timeout: int = DEFAULT_VERIFY_TIMEOUT,
    resolved_command: Optional[
        Tuple[Optional[str], str, Optional[ToolchainDeclaration]]
    ] = None,
    env: Optional[Dict[str, str]] = None,
) -> VerificationResult:
    """The post-merge check: the project's full check on the merged tree.

    ``resolved_command`` is the resolution made on the target branch before
    the merge (:func:`resolve_verify_command_on_target`), so the merged
    branch cannot have chosen it (2026-09-06 spec, rule 11).
    :func:`execute_merge` always passes it. Omit it — a direct caller
    verifying a tree it already trusts — and it is resolved here.

    ``env`` goes to the run unchanged; :func:`execute_merge` passes the
    minimal environment and the run then has a process group of its own.
    """
    command, source, declaration = resolved_command or resolve_verify_command(
        Path(repo_root)
    )
    return run_completion_verification(
        Path(repo_root),
        command,
        source,
        declaration=declaration,
        timeout=timeout,
        env=env,
        own_process_group=env is not None,
    )


# ---------------------------------------------------------------------------
# What judges the merge, pinned on the target; and preparing each tree
# (the merge design of 13 October 2026)
# ---------------------------------------------------------------------------


def files_the_branch_changed(
    tree_root: Path, target_branch: str, branch: str
) -> Tuple[Optional[List[str]], Optional[str]]:
    """The repository paths ``branch`` changed since it left ``target_branch``.

    ``git diff --name-only --no-renames --ignore-submodules=none -z
    <merge-base> <branch> --``. ``branch`` is best given as the commit the
    merge will join, so the files compared are the files merged. A
    submodule pointer the build moved is listed whatever the repository's
    ``diff.ignoreSubmodules`` setting says, and the ``--`` keeps git from
    reading either commit as a path. Returns ``(paths, None)`` or
    ``(None, reason)`` when git cannot say.
    """
    base = _run_git(tree_root, "merge-base", target_branch, branch)
    base_sha = base.stdout.strip() if base.returncode == 0 else ""
    if not base_sha:
        return None, (
            f"the files the build changed could not be listed (no common "
            f"commit of {target_branch} and {branch}), so the commands that "
            f"judge it could not be checked"
        )
    changed = _git_names(
        tree_root,
        "diff",
        "--name-only",
        "--no-renames",
        "--ignore-submodules=none",
        "-z",
        base_sha,
        branch,
        "--",
    )
    if changed is None:
        return None, (
            "the files the build changed could not be listed (git diff "
            "failed), so the commands that judge it could not be checked"
        )
    return changed, None


def pin_the_judge_on_target(
    tree_root: Path,
    target_branch: str,
    branch: str,
    verify_timeout: int = DEFAULT_VERIFY_TIMEOUT,
    branch_commit: Optional[str] = None,
) -> Tuple[
    Optional[Tuple[Optional[str], str, Optional[ToolchainDeclaration]]],
    Optional[str],
    Optional[MergeEnvironment],
]:
    """:func:`_pin_the_judge_on_target`, where a git command that times out or
    fails is the plain reason nothing may run, before or after the merge,
    never an error."""
    try:
        return _pin_the_judge_on_target(
            tree_root, target_branch, branch, verify_timeout, branch_commit
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, (
            f"could not verify — git could not be read on {target_branch} "
            f"before the merge, so nothing that judges it could be settled: "
            f"{_failure_words(exc)}"
        ), None


def _pin_the_judge_on_target(
    tree_root: Path,
    target_branch: str,
    branch: str,
    verify_timeout: int = DEFAULT_VERIFY_TIMEOUT,
    branch_commit: Optional[str] = None,
) -> Tuple[
    Optional[Tuple[Optional[str], str, Optional[ToolchainDeclaration]]],
    Optional[str],
    Optional[MergeEnvironment],
]:
    """Choose everything that judges this merge, on the TARGET, before it.

    Returns ``(resolution, problem, pinned)``. Rule 11, extended on 13
    October 2026 from the test command to the install and the launch block:

    * HEAD is put on the target branch;
    * ``.guardkit/config.yaml`` is read ONCE, fail-closed
      (:func:`read_merge_declarations`): an invalid file or block means no
      command is looked for anywhere else, so ``resolution`` is ``None``;
    * the full check comes from that reading (nothing declared means no
      check: GuardKit never chooses a command), and the plain words of every
      command it can run with the install's and every component's and
      part's install are the judge words (:func:`judge_words`);
    * a file those commands name directly (a judge file) that is a symbolic
      link, or sits under one, in the target's tree or the build's, means no
      automatic verdict (:data:`JUDGE_IS_A_LINK`);
    * the judge files the build changed are recorded on ``pinned``
      (``judge_files_changed``) for the card and the receipt, when git can
      list them. Since 15 October 2026 they no longer stop the check: the
      join is checked with the target's copy of every judge file under the
      project's protected paths (:func:`put_main_judges_in_place`), and with
      the build's copy of the others (28 October 2026).

    ``problem`` is the plain reason nothing may run, before or after the
    merge. ``pinned`` is what runs both installs and both checks otherwise.
    The merged branch's own ``config.yaml`` is never read for any of them.

    ``branch_commit`` is the commit the merge will join (resolved once by
    :func:`execute_merge`); the changed files are read from it rather than
    from wherever ``branch`` points by the time git is asked.
    """
    tree_root = Path(tree_root)
    switch_problem = checkout_branch(tree_root, target_branch)
    if switch_problem is not None:
        return None, switch_problem, None

    declarations, problem = read_merge_declarations(tree_root)
    if problem is not None or declarations is None:
        return None, problem or "the declarations could not be read", None

    resolution = resolve_verify_command_with_declaration(
        tree_root, declarations.toolchain
    )
    pinned, _ = pin_merge_environment(
        declarations,
        " ; ".join(check_command_texts(declarations.toolchain)) or None,
        verify_timeout,
        part_installs=part_install_texts(declarations.toolchain),
    )

    if pinned.judge_words:
        changed, _ = files_the_branch_changed(
            tree_root, target_branch, branch_commit or branch
        )
        if changed is not None:
            hits = judge_files(changed, pinned.judge_words)
            pinned = replace(pinned, judge_files_changed=tuple(hits))
        target_commit = _rev_parse(tree_root, "HEAD")
        for commit in (target_commit, branch_commit or _rev_parse(tree_root, branch)):
            problem = judge_link_problem(tree_root, commit, pinned.judge_words)
            if problem is not None:
                return resolution, problem, None

    return resolution, None, pinned


def judge_link_problem(
    tree_root: Path, commit: Optional[str], words: Sequence[str]
) -> Optional[str]:
    """The link rule for one commit's tree: ``None`` when no judge file and no
    folder on its path is a symbolic link there, otherwise the plain reason
    nothing may run. A tree that cannot be read fails closed."""
    unreadable = ""
    try:
        links = judge_links(tree_root, commit, words) if commit else None
    except (OSError, subprocess.SubprocessError) as exc:
        links = None
        unreadable = f" ({_failure_words(exc)})"
    if links is None:
        return (
            f"could not verify — whether a file the declared commands name is "
            f"a symbolic link could not be read at {(commit or '?')[:10]}"
            f"{unreadable}"
        )
    if links:
        return JUDGE_IS_A_LINK.format(path=shown_path(links[0]))
    return None


# ---------------------------------------------------------------------------
# The target's judge files in the join's folder (15 October 2026)
# ---------------------------------------------------------------------------


def _git_names(tree_root: Path, *args: str) -> Optional[List[str]]:
    """The NUL-separated names one git listing prints, or ``None``. Read as
    bytes and decoded byte-exact (``os.fsdecode``), so a name that is not
    valid UTF-8 is still one path, never an error."""
    done = run_git(
        [*args], cwd=str(tree_root), timeout=_GIT_TIMEOUT_SECONDS, text=False
    )
    if done.returncode != 0:
        return None
    return [os.fsdecode(name) for name in (done.stdout or b"").split(b"\0") if name]


def _link_on_the_way(tree_root: Path, path: str) -> Optional[str]:
    """The first part of ``path`` (itself or a folder on its way) that is a
    symbolic link in the folder, or ``None``."""
    current = Path(tree_root)
    walked: List[str] = []
    for part in path.split("/"):
        current = current / part
        walked.append(part)
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                return "/".join(walked)
        except OSError:
            return None
    return None


#: The git modes of an ordinary file, and whether each is executable.
_FILE_MODES = {"100644": False, "100755": True}


def _blob_bytes(tree_root: Path, oid: str) -> Optional[bytes]:
    """A stored blob's exact bytes (``git cat-file blob``: no filter, no
    line-ending or keyword conversion), or ``None`` when git cannot say."""
    done = run_git(
        ["cat-file", "blob", oid],
        cwd=str(tree_root),
        timeout=_GIT_TIMEOUT_SECONDS,
        text=False,
    )
    if done.returncode != 0:
        return None
    return done.stdout or b""


def _parent_link(tree_root: Path, path: str) -> Optional[str]:
    """The first folder on the way to ``path`` that is a symbolic link in the
    folder, or ``None``."""
    parts = path.split("/")[:-1]
    return _link_on_the_way(tree_root, "/".join(parts)) if parts else None


def judges_match_commit(
    tree_root: Path, commit: str, paths: Sequence[str]
) -> Optional[str]:
    """``None`` when every path in the folder is exactly as stored in
    ``commit``: the same raw bytes as its blob (read with no filter and no
    conversion), an ordinary file with the same executable bit, and no
    symbolic link on the way; and absent where ``commit`` lacks it.
    Otherwise a plain reason naming the paths. The index is not consulted:
    what runs is the file in the folder."""
    if not paths:
        return None
    entries = tree_entries(tree_root, commit)
    if entries is None:
        return f"the tree of {commit[:10]} could not be read"
    differing: List[str] = []
    for path in paths:
        target = Path(tree_root) / path
        link = _link_on_the_way(tree_root, path)
        if link is not None:
            return f"{shown_path(link)} is a symbolic link in the folder"
        if path not in entries:
            if os.path.lexists(target):
                differing.append(path)
            continue
        mode, oid = entries[path]
        if mode not in _FILE_MODES:
            return f"{shown_path(path)} is not an ordinary file at {commit[:10]}"
        expected = _blob_bytes(tree_root, oid)
        if expected is None:
            return (
                f"the stored copy of {shown_path(path)} at {commit[:10]} "
                f"could not be read"
            )
        try:
            info = os.lstat(target)
            if not stat.S_ISREG(info.st_mode):
                differing.append(path)
                continue
            with open(target, "rb") as handle:
                actual = handle.read()
        except OSError:
            differing.append(path)
            continue
        executable = bool(info.st_mode & stat.S_IXUSR)
        if actual != expected or executable != _FILE_MODES[mode]:
            differing.append(path)
    if differing:
        shown = ", ".join(shown_path(p) for p in sorted(set(differing)))
        return f"{shown} does not match {commit[:10]}"
    return None


def _put_tree_paths_in_place(
    tree_root: Path, commit: str, paths: Sequence[str]
) -> Optional[str]:
    """Make each path in the folder exactly as stored in ``commit``: written
    from its blob's raw bytes with its mode where ``commit`` has it, removed
    where it does not. Nothing goes through git's checkout, so no attribute
    in the folder (line endings, keywords, filters) can change a byte. The
    index is left as it is. Then compared exactly
    (:func:`judges_match_commit`)."""
    entries = tree_entries(tree_root, commit)
    if entries is None:
        return f"the tree of {commit[:10]} could not be read"
    root = Path(tree_root)
    for path in paths:
        link = _parent_link(root, path)
        if link is not None:
            return f"{shown_path(link)} is a symbolic link in the folder"
        target = root / path
        # The stored copy is read BEFORE anything in the folder is removed,
        # so a read that fails (or times out) leaves the folder's copy where
        # it was.
        data: Optional[bytes] = None
        permissions = 0o644
        if path in entries:
            mode, oid = entries[path]
            if mode not in _FILE_MODES:
                return f"{shown_path(path)} is not an ordinary file at {commit[:10]}"
            data = _blob_bytes(root, oid)
            if data is None:
                return (
                    f"the stored copy of {shown_path(path)} at {commit[:10]} "
                    f"could not be read"
                )
            permissions = 0o755 if _FILE_MODES[mode] else 0o644
        try:
            if target.is_symlink() or (target.exists() and not target.is_dir()):
                target.unlink()
            elif target.is_dir():
                return f"{shown_path(path)} is a folder in the working folder"
            if data is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            handle = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                permissions,
            )
            try:
                os.write(handle, data)
            finally:
                os.close(handle)
            os.chmod(target, permissions)
        except OSError as exc:
            return (
                f"{shown_path(path)} could not be written "
                f"({exc.strerror or type(exc).__name__})"
            )
    return judges_match_commit(tree_root, commit, paths)


def put_main_judges_in_place(
    tree_root: Path, main_sha: str, paths: Sequence[str]
) -> Optional[str]:
    """Put the target's copy of every judge file in place for the check.

    A path the target commit has is written from its stored blob, byte for
    byte with its mode, with no filter or conversion; a path it lacks is
    removed from the folder. The result is then compared with ``main_sha``
    exactly. Returns ``None`` or the plain reason it could not be done.
    """
    return _put_tree_paths_in_place(tree_root, main_sha, paths)


def put_joined_files_back(
    tree_root: Path, post_sha: str, paths: Sequence[str]
) -> Optional[str]:
    """Put the joined commit's version of every path back after the check,
    and confirm those paths are clean. Returns ``None`` or the reason.

    Nothing runs after this, so the files are put back the way git itself
    checks them out (through the folder's attributes), which is what makes
    ``git status`` agree that the folder is the joined commit: raw bytes
    would read as changed under a line-ending attribute. The index was never
    changed by :func:`put_main_judges_in_place`. A path the joined commit
    lacks is removed.
    """
    entries = tree_entries(tree_root, post_sha)
    if entries is None:
        return f"the tree of {post_sha[:10]} could not be read"
    root = Path(tree_root)
    present = [p for p in paths if p in entries]
    for path in paths:
        link = _parent_link(root, path)
        if link is not None:
            return f"{shown_path(link)} is a symbolic link in the folder"
        target = root / path
        try:
            if target.is_symlink() or (target.exists() and not target.is_dir()):
                target.unlink()
            elif target.is_dir():
                return f"{shown_path(path)} is a folder in the working folder"
        except OSError as exc:
            return (
                f"{shown_path(path)} could not be removed "
                f"({exc.strerror or type(exc).__name__})"
            )
    if present:
        done = _run_git(tree_root, "checkout", post_sha, "--", *present)
        if done.returncode != 0:
            return f"git checkout from {post_sha[:10]} failed ({done.stderr.strip()})"
    rows = _git_names(
        tree_root, "status", "--porcelain", "-z", "--untracked-files=all", "--", *paths
    )
    if rows is None:
        return "git status could not be read"
    if rows:
        return "; ".join(shown_path(row) for row in rows[:5])
    return None


class TreePreparation(NamedTuple):
    """What :func:`prepare_tree` produced for one tree."""

    env: Optional[Dict[str, str]]
    problem: Optional[str]
    note: Optional[str] = None


_INSTALL_TAIL_LINES = 5
_INSTALL_TAIL_CHARS = 600


def _last_lines(text: str) -> str:
    lines = [ln.rstrip() for ln in (text or "").splitlines() if ln.strip()]
    tail = " | ".join(lines[-_INSTALL_TAIL_LINES:])
    if len(tail) > _INSTALL_TAIL_CHARS:
        tail = "..." + tail[-_INSTALL_TAIL_CHARS:]
    return tail or "(no output)"


def prepare_tree(
    tree_root: Path,
    pinned: MergeEnvironment,
    where: str,
) -> TreePreparation:
    """Build the check's environment for ``tree_root`` and run the install.

    The environment is built from nothing
    (``project_command_env.project_command_environment``). A
    declared install runs as an argument list with no shell, in
    ``tree_root``, with that environment and the pinned time limit. What the
    install writes into the folder is left there (the cull, 27 October
    2026). Never raises.
    """
    try:
        env = project_command_environment(Path(tree_root), pinned.launch)
    except LaunchEnvironmentError as exc:
        return TreePreparation(None, str(exc))
    if not pinned.install_argv:
        return TreePreparation(env, None)

    text = pinned.install_text
    try:
        # In a process group of its own: a timeout ends everything the
        # install started, not only its first process.
        proc = run_in_own_group(
            pinned.install_argv,
            cwd=tree_root,
            env=env,
            timeout=pinned.install_timeout,
        )
    except OSError as exc:
        return TreePreparation(
            None,
            f"the declared install (`{text}`) could not start on {where}: "
            f"{exc.strerror or type(exc).__name__}",
        )
    if proc.timed_out:
        return TreePreparation(
            None,
            f"the declared install (`{text}`) ran out of its "
            f"{pinned.install_timeout} seconds on {where}",
        )
    if proc.returncode != 0:
        return TreePreparation(
            None,
            f"the declared install (`{text}`) failed on {where} (exit "
            f"{proc.returncode}): {_last_lines(proc.stderr or proc.stdout)}",
        )

    return TreePreparation(
        env, None, note=f"the declared install (`{text}`) ran on {where} before the check"
    )


# ---------------------------------------------------------------------------
# Assembly — preflight, merge, verify, one report
# ---------------------------------------------------------------------------


def execute_merge(
    repo_root: Path,
    feature_id: str,
    target_branch: str = "main",
    expect_target_sha: Optional[str] = None,
    verify: bool = True,
    verify_timeout: int = DEFAULT_VERIFY_TIMEOUT,
    manager: Optional[WorktreeManager] = None,
    branch: Optional[str] = None,
    working_folder: Optional[Path] = None,
) -> MergeReport:
    """Refusal preflight, the merge, the full check on the joined result.

    Every outcome is a :class:`MergeReport`. The branch merged is ``branch``
    when one is named, else ``autobuild/<FEATURE_ID>`` (the default every
    feature build has always had); it survives every path, and the report's
    ``branch`` field names it. Naming a branch changes nothing else here.

    With verification on, the project's full check is resolved on the TARGET
    branch before the merge, and that resolution is what checks the merged
    tree. A branch cannot choose the check that judges it (2026-09-06 spec,
    rule 11; see :func:`pin_the_judge_on_target`, and
    :func:`resolve_verify_command_on_target` for why). ``verify_command`` and
    ``verify_source`` in the report are that resolution.

    The full check runs once, on the joined result (31 October 2026). There
    is no run on the target first and no known-failure baseline: a check
    that failed fails the merge (``verify_ok`` False), and a check that could
    not run is reported as not run, which is not ok either.

    The target's declared install and ``launch:`` block are pinned with the
    check (13 October 2026). Before the check the joined tree is prepared
    once (:func:`prepare_tree`): a minimal environment built from nothing,
    then the declared install. An install that fails, or settings that
    cannot be passed safely, mean the check is reported as not run. A file
    the commands name that is a symbolic link (or sits under one) in the
    target's, the build's or the joined tree gets no automatic verdict: the
    join still happens and nothing is installed or run. Before the install,
    the target's copy of every file the commands name under the project's
    protected paths is put in place, checked to match exactly, and the
    joined files are put back after the check (15 and 28 October 2026).

    ``working_folder`` (22 September 2026) is a working folder of this same
    repository, made at the commit being joined onto. Handed one, EVERYTHING
    that touches a tree happens in there: the refusal preflight, the choice of
    the check on the target branch, the merge itself and the post-merge
    check. The repository's main copy is
    never switched, reset or merged into. Handed none — every caller that
    existed before this — the whole function runs exactly where it always ran.

    ``repo_root`` itself is NOT moved: it stays the repository, so a
    worktree's administrative paths are still the repository's own.
    """
    repo_root = Path(repo_root)
    branch = branch_to_merge(feature_id, branch)
    # The tree everything is done to. A working folder shares the
    # repository's refs and objects, so every ref read below answers the same
    # thing in either place; what differs is which branch is checked out and
    # which files the checks see, and those are exactly what must move.
    tree_root = Path(working_folder) if working_folder is not None else repo_root

    reason = preflight_refusal(
        tree_root, feature_id, target_branch, expect_target_sha, branch=branch
    )
    if reason is not None:
        return MergeReport(
            outcome=OUTCOME_REFUSED,
            feature_id=feature_id,
            target_branch=target_branch,
            branch=branch,
            refusal_reason=reason,
        )

    # Resolve both ends of the merge before anything moves. ``perform_merge``
    # checks this too, but only after HEAD has been put on the target branch;
    # refusing here leaves HEAD exactly where the caller had it.
    # The branch is resolved to a commit ONCE, here. That commit is what the
    # changed files are read from and what the merge joins, so a branch that
    # moves while the checks run cannot slip anything past them.
    unreadable = ""
    try:
        branch_commit = _rev_parse(tree_root, branch)
        target_commit = _rev_parse(tree_root, target_branch)
    except (OSError, subprocess.SubprocessError) as exc:
        branch_commit = target_commit = None
        unreadable = f" ({_failure_words(exc)})"
    if target_commit is None or branch_commit is None:
        return MergeReport(
            outcome=OUTCOME_REFUSED,
            feature_id=feature_id,
            target_branch=target_branch,
            branch=branch,
            refusal_reason=(
                f"could not resolve {target_branch} and {branch} to commits"
                f"{unreadable}"
            ),
        )

    # Rule 11. Everything that judges this merge is chosen HERE: on the
    # target branch, before anything lands — the full check, the declared
    # install and the launch block, read once from the target's
    # .guardkit/config.yaml by a reader that fails closed. A judge file
    # reached through a symbolic link gets no automatic verdict.
    resolution: Optional[
        Tuple[Optional[str], str, Optional[ToolchainDeclaration]]
    ] = None
    resolution_problem: Optional[str] = None
    pinned: Optional[MergeEnvironment] = None
    if verify:
        resolution, resolution_problem, pinned = pin_the_judge_on_target(
            tree_root,
            target_branch,
            branch,
            verify_timeout=verify_timeout,
            branch_commit=branch_commit,
        )
    verify_command = (resolution[0] or None) if resolution else None
    verify_source = (resolution[1] or None) if resolution else None

    pre_merge_notes: List[str] = []
    if resolution_problem is not None:
        # No trustworthy check could be chosen, so none may be run: falling
        # back to whatever the merged tree declares is exactly the hole rule
        # 11 closes.
        pre_merge_notes.append(
            f"nothing that judges this merge could be settled on "
            f"{target_branch} before the merge, so no install and no test "
            f"run was attempted: {resolution_problem}"
        )

    report = perform_merge(
        repo_root,
        feature_id,
        target_branch,
        manager=manager,
        branch=branch,
        working_folder=working_folder,
        merge_commit=branch_commit,
    )
    if report.outcome != OUTCOME_MERGED or not verify:
        return replace(
            report,
            verify_command=verify_command,
            verify_source=verify_source,
            notes=tuple(list(report.notes) + pre_merge_notes),
        )

    def could_not_run(detail: str, more_notes: Sequence[str] = ()) -> MergeReport:
        """The merged report when no post-merge run was attempted.

        Say "not run" once, in the run's own words. ``verify_ran`` is False
        (2026-09-06 spec, rule 12), and an "unverified" result is not ok.
        """
        return MergeReport(
            outcome=report.outcome,
            feature_id=report.feature_id,
            target_branch=report.target_branch,
            branch=report.branch,
            pre_sha=report.pre_sha,
            post_sha=report.post_sha,
            verify_ran=False,
            verify_status="unverified",
            verify_detail=detail,
            verify_command=verify_command,
            verify_source=verify_source,
            notes=tuple(
                list(report.notes) + pre_merge_notes + list(more_notes)
            ),
        )

    # Nothing that judges the merge could be settled on the target branch,
    # so nothing is run after it.
    if resolution_problem is not None:
        return could_not_run(resolution_problem)

    # The target's judge files in the join's folder (15 October 2026). Every
    # file the target's commands name under the project's protected paths
    # (28 October 2026) is put back from the target commit, whether or not
    # the build changed it, so the check never runs the build's copy of one
    # (a rename on the target cannot carry the build's edits past this
    # either); the build's copy of any other is kept. A link on a judge's
    # path in the joined tree is
    # refused first. Putting them in place, the install and the check all sit
    # inside one cleanup: the joined files are put back afterwards on every
    # path, and a git command that times out or fails on the way ends in the
    # ordinary "could not verify" report, never an unexpected error.
    assert pinned is not None
    pre_sha, post_sha = report.pre_sha, report.post_sha
    judges = _JudgeRestore()
    restore_problem: Optional[str] = None
    put_back_problem: Optional[str] = None
    result: object = None
    try:
        if pinned.judge_words:
            try:
                restore_problem = _put_target_judges_in_place(
                    tree_root, pinned, pre_sha, post_sha, judges
                )
            except (OSError, subprocess.SubprocessError) as exc:
                restore_problem = _restore_failed(pinned, _failure_words(exc))

        # Install the merged tree again (a dependency the branch adds must be
        # there) with the TARGET's pinned install and launch block, then
        # check it.
        if restore_problem is None:
            env = None
            post_merge_notes: List[str] = []
            prepared_problem: Optional[str] = None
            if verify_command:
                prepared = prepare_tree(tree_root, pinned, "the merged result")
                if prepared.problem is not None:
                    prepared_problem = prepared.problem
                else:
                    env = prepared.env
                    if prepared.note:
                        post_merge_notes.append(prepared.note)
            if prepared_problem is not None:
                result = could_not_run(
                    prepared_problem,
                    [
                        f"the post-merge test run was not attempted: "
                        f"{prepared_problem}"
                    ],
                )
            else:
                verification = verify_merged(
                    tree_root,
                    timeout=verify_timeout,
                    resolved_command=resolution,
                    env=env,
                )
                result = _CheckRun(verification, post_merge_notes)
    finally:
        if judges.restored:
            try:
                put_back_problem = put_joined_files_back(
                    tree_root, post_sha, judges.restored
                )
            except (OSError, subprocess.SubprocessError) as exc:
                put_back_problem = _failure_words(exc)

    if restore_problem is not None:
        detail = restore_problem
        if put_back_problem is not None:
            detail += (
                f"; the join's folder could not be put back to the "
                f"joined commit afterwards ({put_back_problem}), so it may "
                f"still hold some of main's copies, or be missing some of the "
                f"joined files"
            )
        final = could_not_run(detail)
    elif isinstance(result, MergeReport):
        final = result
    else:
        assert isinstance(result, _CheckRun)
        final = _report_from_the_check(
            report, result, pre_merge_notes, verify_command, verify_source,
        )
    # Said whenever the target's copies were in place, whatever happened
    # next (an install that then failed, or a restore that stopped part way,
    # included).
    final = replace(
        final,
        judged_with_main_copies=judges.judged_with_main_copies,
        judged_with_build_copies=judges.judged_with_build_copies,
        judge_files_not_on_target=tuple(
            p for p in judges.judged_with_main_copies
            if p not in judges.target_paths
        ),
    )
    if put_back_problem is not None and restore_problem is None:
        final = replace(
            final,
            notes=tuple(
                list(final.notes)
                + [
                    f"the join's folder could not be put back to the joined "
                    f"commit after the check ({put_back_problem})"
                ]
            ),
        )
    return final


@dataclass
class _JudgeRestore:
    """What was, or was about to be, put in place from the target commit.

    ``restored`` is filled BEFORE any file in the folder is touched, so the
    cleanup puts back every path a restore that stopped part way may have
    changed."""

    restored: List[str] = field(default_factory=list)
    judged_with_main_copies: Tuple[str, ...] = ()
    judged_with_build_copies: Tuple[str, ...] = ()
    target_paths: frozenset = frozenset()


def _failure_words(exc: BaseException) -> str:
    """Plain words for a git command or file step that raised."""
    if isinstance(exc, subprocess.TimeoutExpired):
        said = exc.stderr
        if isinstance(said, bytes):
            said = said.decode("utf-8", "replace")
        return (said or "").strip().rstrip(".") or (
            f"{exc.cmd} did not finish within {exc.timeout} seconds"
        )
    if isinstance(exc, subprocess.CalledProcessError):
        said = exc.stderr
        if isinstance(said, bytes):
            said = said.decode("utf-8", "replace")
        shown = exc.cmd if isinstance(exc.cmd, str) else " ".join(map(str, exc.cmd))
        return (said or "").strip().rstrip(".") or f"{shown} failed"
    if isinstance(exc, OSError):
        return exc.strerror or type(exc).__name__
    return type(exc).__name__


def _restore_failed(pinned: MergeEnvironment, problem: str) -> str:
    lead = (
        JUDGE_FILES_CHANGED
        if pinned.judge_files_changed
        else "could not verify — the commands that judge it"
    )
    return f"{lead}, and main's copies could not be put in place: {problem}"


def _put_target_judges_in_place(
    tree_root: Path,
    pinned: MergeEnvironment,
    pre_sha: Optional[str],
    post_sha: Optional[str],
    judges: _JudgeRestore,
) -> Optional[str]:
    """Put the target's copy of every judge file in the join's folder.

    Returns ``None`` or the plain reason the check cannot run. May raise a
    git timeout or failure; the caller turns that into a reason and puts
    back every path recorded in ``judges.restored``."""
    if not pre_sha or not post_sha:
        return (
            "could not verify — the commit joined onto, or the joined commit, "
            "could not be read, so the target's copies of the files the "
            "declared commands name could not be put in place"
        )
    link_problem = judge_link_problem(tree_root, post_sha, pinned.judge_words)
    if link_problem is not None:
        return link_problem
    target_entries = tree_entries(tree_root, pre_sha) if pre_sha else None
    joined_entries = tree_entries(tree_root, post_sha) if post_sha else None
    if target_entries is None or joined_entries is None:
        return (
            "could not verify — the trees of the join could not be read, so "
            "the target's copies of the files the declared commands name "
            "could not be put in place"
        )
    named = judge_files(
        sorted(set(target_entries) | set(joined_entries)), pinned.judge_words
    )
    restored = judges_kept_from_target(named, pinned.protected_paths)
    judges.judged_with_main_copies = tuple(
        p for p in restored if target_entries.get(p) != joined_entries.get(p)
    )
    judges.judged_with_build_copies = tuple(
        p
        for p in named
        if p not in restored and target_entries.get(p) != joined_entries.get(p)
    )
    judges.target_paths = frozenset(target_entries)
    judges.restored = restored
    if not restored:
        return None
    problem = put_main_judges_in_place(tree_root, pre_sha, restored)
    if problem is not None:
        return _restore_failed(pinned, problem)
    return None


class _CheckRun(NamedTuple):
    """What the post-join install and check produced."""

    verification: VerificationResult
    notes: List[str]


def _report_from_the_check(
    report: MergeReport,
    run: _CheckRun,
    pre_merge_notes: Sequence[str],
    verify_command: Optional[str],
    verify_source: Optional[str],
) -> MergeReport:
    """The merged report from a post-join check: its own verdict, unchanged."""
    verification = run.verification
    status = verification.status
    return MergeReport(
        outcome=report.outcome,
        feature_id=report.feature_id,
        target_branch=report.target_branch,
        branch=report.branch,
        pre_sha=report.pre_sha,
        post_sha=report.post_sha,
        verify_ran=status in ("passed", "failed"),
        verify_status=status,
        verify_detail=verification.detail,
        # The pre-merge resolution, not whatever the merged tree would say
        # now: this is the check that actually ran.
        verify_command=verify_command,
        verify_source=verify_source,
        verify_output_tail=(
            verification.output_tail if status != "passed" else ""
        ),
        notes=tuple(list(report.notes) + list(pre_merge_notes) + list(run.notes)),
    )


__all__ = [
    "OUTCOME_MERGED",
    "OUTCOME_REFUSED",
    "OUTCOME_CONFLICT",
    "MergeReport",
    "conflicted_files_from_status",
    "current_branch",
    "checkout_branch",
    "branch_to_merge",
    "preflight_refusal",
    "merge_commit_message",
    "perform_merge",
    "resolve_verify_command_on_target",
    "verify_merged",
    "files_the_branch_changed",
    "pin_the_judge_on_target",
    "judge_link_problem",
    "judges_match_commit",
    "put_main_judges_in_place",
    "put_joined_files_back",
    "prepare_tree",
    "TreePreparation",
    "execute_merge",
]
