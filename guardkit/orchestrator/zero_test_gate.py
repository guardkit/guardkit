"""Notices — and records — when an automated build's tests are missing or unrun.

PLAIN-LANGUAGE SUMMARY
----------------------
GuardKit builds software in a loop with two halves. A **Player** writes the
code. A **Coach** then reviews what the Player did and decides one of three
things: approve, send feedback, or reject.

There are two Coach implementations in this repository:

* The **legacy** Coach is a set of hard-coded rules
  (``CoachValidator.validate``). One of those rules,
  ``CoachValidator._check_zero_test_anomaly``, refuses to approve a turn whose
  tests are missing or were never run.
* The **live** Coach — the default since 2026-05-21 — is a language model.
  The rule-based validator was demoted to gathering evidence for it
  (``CoachValidator.gather_evidence``). On that path the rule was never run,
  and the model's written instructions never mentioned the case, so nothing
  put the fact in front of it.

This module closes that gap on the live path. It runs **the same rule** —
``_check_zero_test_anomaly``, not a second copy of it — over the same evidence,
puts the answer in front of the language model in plain words, and writes a
durable record every time it fires.

THE RULE HAS TWO BRANCHES, AND THEY ARE DIFFERENT SITUATIONS
------------------------------------------------------------
This matters more than anything else in this module, because the whole point
of the instrument is to produce **one honest number** and a blended claim
makes that number wrong.

``_check_zero_test_anomaly`` can fire for either of two entirely different
reasons. It returns the same ``category`` for both, so nothing downstream
could previously tell them apart. This module names them:

``no_test_file`` — **no test exists for this turn.**
    Fires when the Player's report names no test file at all
    (``tests_written`` is empty) *and* the Coach's own independent test run
    searched the worktree for task-specific tests and found none to execute
    (it reports its command as ``"skipped"``). Both halves must hold.

    This is the situation the promotion question is about: a turn produced
    code and no test, and a person must judge whether that was legitimate
    (a documentation edit, a rename, deleting dead code, a configuration
    change) or whether it was unverified work.

``tests_not_executed`` — **tests may well exist; the Player's own report says
none ran.**
    Fires when the first branch did *not* apply, and the Player's report
    claims ``quality_gates.all_passed`` is true while reporting
    ``tests_passed`` as zero.

    Nothing in this branch says a test file is missing. Test files may be
    listed in ``tests_written``, may exist on disk, and may have been written
    this very turn. What is wrong here is the **report**: it asserts every
    quality gate passed while simultaneously reporting that no test executed.
    That is a claim-versus-evidence problem, not a missing-test problem.

Everything the older version of this module asserted about a fired check —
"none of the files is a test file that exists on disk", "the independent test
run found no task-specific tests" — is true of ``no_test_file`` and can be
flatly **false** of ``tests_not_executed``. So the sentence shown to the
Coach, the field written into the receipt, and the report a person reads are
all branch-specific from here on.

WHICH BRANCH FEEDS THE PROMOTION MEASUREMENT — only the first
--------------------------------------------------------------
Only ``no_test_file`` rows count toward the promotion decision
(:data:`COUNTS_TOWARD_PROMOTION`). ``tests_not_executed`` rows are recorded
and reported, but deliberately kept out of the rate, for three reasons:

1. The promotion question is "how often does a turn legitimately need no
   test?". A ``tests_not_executed`` turn has not been shown to lack a test, so
   it cannot answer that question either way.
2. The adjudication a person performs — marking a row
   ``legitimately_test_free`` — is meaningless for the second branch. The
   useful follow-up there is "why did the report claim a pass with no test
   run?", which is a different question with a different owner.
3. Blending them inflates the numerator with turns that are not test-free at
   all, and the resulting rate would be acted on.

HOW THE BRANCH IS DETERMINED — from the rule's own control flow
----------------------------------------------------------------
The rule tests the ``no_test_file`` condition first and returns immediately if
it holds. So: given that the rule fired, if that first condition holds the
branch is ``no_test_file``; otherwise it is ``tests_not_executed``. That is
exact, not a guess at the wording of a message.

``tests/orchestrator/test_zero_test_gate.py`` pins the labels against the
descriptions the real rule produces for each branch, so reordering the rule
turns those tests red rather than silently mislabelling rows.

ADVISORY FIRST — deliberate, and the whole point
------------------------------------------------
By default this **reports and blocks nothing**. The turn is still approved if
the Coach approves it. Only the record is written.

That is not timidity, it is the estate's own lesson. Whether a test file was
written is a **fact**, so detecting it deterministically is right. But a hard
rule would also stop changes that legitimately need no test, and **nobody
knows yet how often that happens**. That number is the whole promotion
decision, and it does not exist. A previous check in this estate was promoted
without being measured first and turned out to raise a false alarm 97% of the
time; it would have stopped real builds roughly thirty times for nothing.

To make a fired check actually stop a turn, set the environment variable::

    GUARDKIT_ZERO_TEST_BLOCKING=1

Accepted values are ``1``, ``true``, ``yes`` and ``on`` (case-insensitive);
anything else, including the variable being absent, means advisory. This
mirrors ``guardkit.orchestrator.boot_smoke_gate.GUARDKIT_BOOT_SMOKE_BLOCKING``
exactly, on purpose — one shape for every advisory-first instrument here.

WHAT THE RULE ALREADY DECIDES, INHERITED WITHOUT RESTATING
-----------------------------------------------------------
* A task type whose profile does not require tests never fires.
* A Coach-run independent test suite that genuinely PASSED suppresses the
  anomaly entirely — the zero count was then a bookkeeping error in the
  Player's report, not missing tests.
* A test file the Player *claims* but never wrote is a different finding
  entirely — a dishonest report. The honesty verifier catches it first and
  evidence gathering stops there, so this check is never reached. That is
  the same order the legacy rule ran in.

WHAT DIFFERS BETWEEN THE TWO COACH PATHS — stated plainly, because it matters
------------------------------------------------------------------------------
The *detection* is identical: the same method, the same arguments. What
differs is **how often it is reached**.

The legacy ``validate()`` runs the check as step 5, after the acceptance
criteria have been confirmed met; a turn that fails its acceptance criteria
returns feedback earlier and the rule never runs. ``gather_evidence`` has no
such early return — the language model is given every piece of evidence at
once and decides — so this check is computed at the complete-gathering path
whether or not the acceptance criteria were met. The receipt therefore records
``requirements_met`` so a person adjudicating the measurement can filter the
turns the legacy path would never have reached.

Both paths still share the two earlier exits: a dishonest report and a failed
quality gate both stop gathering before this check, on both paths.

THE RECEIPT — durable, and where it lives
-----------------------------------------
Every fired check writes two things:

* a per-turn receipt beside the Coach's own verdict, at
  ``<worktree>/.guardkit/autobuild/<task_id>/zero_test_turn_<turn>.json``;
* one appended line in the durable ledger, at
  ``~/.guardkit/zero-test/<repo name>/queue.jsonl``.

**The ledger is outside every repository working tree, and that is a
Decision of Record, not a preference.** D-OBS-4 (filed 2026-07-09,
``ai-transition/docs/observability-analysis-production-and-continual-
learning-2026-07-09.md`` §7) settled the durable home for ``.guardkit``
artifacts as one archive tree under the user's home directory, rsynced to the
NAS — precisely because in-tree artifacts are "one copy on one machine with no
git recovery". ``guardkit/worktrees/archive.py`` enforces the same rule from
the other side: it refuses an archive root that resolves inside the repository
tree and falls back to ``~/.guardkit/archive/<repo name>/``.

An earlier version of this module wrote the ledger to
``<repo root>/.guardkit/zero-test/queue.jsonl``. That path is in-tree and
untracked, so ``git clean -fdx`` deletes it — and this measurement is the
deliverable. It now lives under :data:`ZERO_TEST_HOME`, overridable with
``GUARDKIT_ZERO_TEST_ROOT`` (chiefly so tests need no home directory). Any
ledger still sitting at the old in-tree path is still **read**, so no already-
recorded row is lost; nothing is ever written there again.

CONCURRENT BUILDS — the append is serialised
---------------------------------------------
This estate runs many autobuild worktrees against one repository at once
(eleven were live when this was written), and they all append to the one
ledger for that repository. Two builds finishing a turn at the same moment
must not produce one spliced, unparseable line — a dropped row is a silently
wrong measurement, which is the exact failure mode this instrument exists to
avoid.

Stated precisely, because the difference matters: appending in text mode with
``open(path, "a")`` already sets ``O_APPEND``, and for a record small enough
to leave the writer's buffer in one piece that is usually enough on a local
Linux filesystem. It stops being enough when a record is large enough to be
flushed in several pieces, when the kernel returns a short write, or when the
ledger sits on a network filesystem, where ``O_APPEND`` carries no atomicity
guarantee at all. None of those is exotic for a file this one is meant to
accumulate in for months.

So this does not rely on that. Every append:

* opens the ledger ``O_APPEND``, so each write lands at the current end of
  file even as other writers grow it;
* takes an exclusive ``fcntl.flock``, which serialises the writers outright —
  this is the guarantee, and it is the estate's existing cross-process
  pattern (see ``guardkit/orchestrator/worktree_checkpoints.py``);
* writes the whole line with ``os.write``, looping until every byte is out,
  so a short write cannot truncate a row.

On a platform without ``fcntl`` the append still happens, unlocked, rather
than failing.

Read the ledger with::

    guardkit autobuild zero-test-report

Neither write can ever break a build: every failure swallows to a warning.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:  # pragma: no cover - exercised implicitly on POSIX, absent on Windows
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = [
    "BLOCKING_ENV_VAR",
    "ZERO_TEST_ROOT_ENV_VAR",
    "ZERO_TEST_HOME",
    "ZERO_TEST_QUEUE_FILENAME",
    "LEGACY_IN_TREE_QUEUE",
    "ZERO_TEST_RECEIPT",
    "ANOMALY_CATEGORY",
    "BRANCH_NO_TEST_FILE",
    "BRANCH_TESTS_NOT_EXECUTED",
    "BRANCH_LABELS",
    "BRANCH_MEANINGS",
    "COUNTS_TOWARD_PROMOTION",
    "blocking_requested",
    "ledger_path_for",
    "legacy_ledger_path_for",
    "evaluate_zero_test",
    "build_receipt",
    "write_receipt",
    "coach_advisory_text",
    "read_receipts",
    "counts_toward_promotion",
]

#: Environment variable that promotes this check from advisory to blocking.
#: Named and shaped after ``boot_smoke_gate.BLOCKING_ENV_VAR``.
BLOCKING_ENV_VAR = "GUARDKIT_ZERO_TEST_BLOCKING"

_TRUTHY = {"1", "true", "yes", "on"}

#: Overrides where the durable ledger tree lives. Mainly so tests do not have
#: to write into a real home directory.
ZERO_TEST_ROOT_ENV_VAR = "GUARDKIT_ZERO_TEST_ROOT"

#: The durable ledger tree, OUTSIDE every repository working tree, per D-OBS-4
#: (see the module docstring). One sub-directory per repository.
ZERO_TEST_HOME = Path.home() / ".guardkit" / "zero-test"

#: The ledger file inside a repository's durable directory. One JSON object
#: per line.
ZERO_TEST_QUEUE_FILENAME = "queue.jsonl"

#: Where the ledger used to be written, in-tree and therefore destroyed by
#: ``git clean -fdx``. Still READ so no recorded row is lost; never written.
LEGACY_IN_TREE_QUEUE = ".guardkit/zero-test/queue.jsonl"

#: The per-turn receipt, written beside ``coach_turn_{turn}.json`` inside the
#: build's own worktree.
ZERO_TEST_RECEIPT = ".guardkit/autobuild/{task_id}/zero_test_turn_{turn}.json"

#: The issue category the legacy rule already uses. Kept identical so the two
#: paths are greppable as one thing. NOTE: the rule uses this single category
#: for BOTH branches below — which is exactly why this module labels them.
ANOMALY_CATEGORY = "zero_test_anomaly"

#: Branch 1: the Player named no test file AND the Coach's own search found no
#: task-specific test to run. No test exists for this turn.
BRANCH_NO_TEST_FILE = "no_test_file"

#: Branch 2: tests may exist, but the Player's report claims every quality
#: gate passed while reporting that zero tests executed.
BRANCH_TESTS_NOT_EXECUTED = "tests_not_executed"

#: Short human labels, for tables and one-line summaries.
BRANCH_LABELS = {
    BRANCH_NO_TEST_FILE: "no test file",
    BRANCH_TESTS_NOT_EXECUTED: "0 tests ran",
}

#: One sentence per branch, for a person who has never read this module.
BRANCH_MEANINGS = {
    BRANCH_NO_TEST_FILE: (
        "No test exists for this turn: the Player named no test file, and the "
        "Coach's own test run searched the worktree and found no "
        "task-specific test to execute."
    ),
    BRANCH_TESTS_NOT_EXECUTED: (
        "Tests may well exist. The Player's report claims every quality gate "
        "passed while also reporting that zero tests ran — a claim-versus-"
        "evidence problem, not a missing-test problem."
    ),
}

#: The only branch that feeds the promotion measurement. See the module
#: docstring for why the other one is deliberately excluded.
COUNTS_TOWARD_PROMOTION = BRANCH_NO_TEST_FILE


def blocking_requested(env: Optional[Mapping[str, str]] = None) -> bool:
    """Has the operator asked a fired zero-test check to stop the turn?

    Reads :data:`BLOCKING_ENV_VAR`. Absent or unrecognised means no — the
    check stays advisory. Same contract as
    ``boot_smoke_gate.blocking_requested``.
    """
    source = os.environ if env is None else env
    return str(source.get(BLOCKING_ENV_VAR, "")).strip().lower() in _TRUTHY


def counts_toward_promotion(row: Mapping[str, Any]) -> bool:
    """Does this receipt belong in the promotion measurement?

    Only ``no_test_file`` rows do. A row written before branches were recorded
    carries no ``branch`` at all; those are treated as NOT counting, because
    guessing would put unverified rows into the one number this instrument
    exists to produce.
    """
    return row.get("branch") == COUNTS_TOWARD_PROMOTION


def ledger_path_for(
    repo_root: Any, env: Optional[Mapping[str, str]] = None
) -> Path:
    """The durable ledger file for one repository. Outside every worktree.

    ``~/.guardkit/zero-test/<repo name>/queue.jsonl`` by default;
    ``$GUARDKIT_ZERO_TEST_ROOT/<repo name>/queue.jsonl`` when that variable is
    set. See the module docstring for the Decision of Record behind this.
    """
    source = os.environ if env is None else env
    configured = str(source.get(ZERO_TEST_ROOT_ENV_VAR, "") or "").strip()
    home = Path(configured) if configured else ZERO_TEST_HOME
    return home / Path(repo_root).resolve().name / ZERO_TEST_QUEUE_FILENAME


def legacy_ledger_path_for(repo_root: Any) -> Path:
    """The old in-tree ledger path. Read for continuity; never written."""
    return Path(repo_root) / LEGACY_IN_TREE_QUEUE


def _string_list(value: Any) -> List[str]:
    """Coerce a Player-reported file list to a list of strings; never raise."""
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, (str, Path))]


def _fired_branch(
    task_work_results: Mapping[str, Any], independent_tests: Any
) -> str:
    """Which of the rule's two branches produced the finding.

    Derived from the rule's own control flow, not from the wording of its
    message: ``_check_zero_test_anomaly`` evaluates the ``no_test_file``
    condition first and returns immediately when it holds. So, GIVEN that the
    rule fired, that condition holding means branch one; anything else means
    the rule fell through to branch two.
    """
    raw_tests_written = task_work_results.get("tests_written", [])
    try:
        named_no_test_file = len(raw_tests_written) == 0
    except TypeError:  # a report with a non-sequence there; the rule would
        named_no_test_file = False  # have raised, and we record honestly.

    search_found_nothing = (
        bool(independent_tests)
        and getattr(independent_tests, "test_command", None) == "skipped"
    )
    if named_no_test_file and search_found_nothing:
        return BRANCH_NO_TEST_FILE
    return BRANCH_TESTS_NOT_EXECUTED


def evaluate_zero_test(
    validator: Any,
    *,
    task_work_results: Dict[str, Any],
    profile: Any,
    independent_tests: Any = None,
    task_id: Optional[str] = None,
    requirements: Any = None,
) -> Dict[str, Any]:
    """Run the legacy zero-test rule and package what it found as evidence.

    The detection itself is **not** implemented here. It is delegated to
    ``validator._check_zero_test_anomaly(...)`` — the same method the legacy
    Coach calls, with the same arguments — so the two paths cannot drift.

    When it fires, the result records **which of the rule's two branches**
    fired (``branch``), what that means in one sentence
    (``branch_meaning``), and whether the row belongs in the promotion
    measurement (``counts_toward_promotion``). Everything else is context for
    the person who will later adjudicate the row: what the Player said it
    created, modified and claimed, which of those look like test files, and
    which of THOSE are actually present on disk.

    Never raises. If the rule itself blows up, the result records that fact
    with ``fired`` false — an instrument that cannot report must not
    manufacture a verdict.

    Returns
    -------
    dict
        Always a dict, never ``None``. ``fired`` is the only key a caller
        must branch on.
    """
    files_created = _string_list(task_work_results.get("files_created"))
    files_modified = _string_list(task_work_results.get("files_modified"))
    tests_written = _string_list(task_work_results.get("tests_written"))

    is_test_path = getattr(validator, "_is_test_file_path", None)
    worktree_path = getattr(validator, "worktree_path", None)

    claimed_test_files: List[str] = []
    for candidate in [*tests_written, *files_created, *files_modified]:
        if candidate in claimed_test_files:
            continue
        try:
            looks_like_a_test = bool(is_test_path and is_test_path(candidate))
        except Exception:  # noqa: BLE001 — a heuristic must never break gathering
            looks_like_a_test = False
        if looks_like_a_test:
            claimed_test_files.append(candidate)

    test_files_on_disk: List[str] = []
    if worktree_path is not None:
        for candidate in claimed_test_files:
            try:
                if (Path(worktree_path) / candidate).exists():
                    test_files_on_disk.append(candidate)
            except Exception:  # noqa: BLE001 — an odd path must not break gathering
                continue

    independent_command = getattr(independent_tests, "test_command", None)
    quality_gates = task_work_results.get("quality_gates")
    if not isinstance(quality_gates, dict):
        quality_gates = {}

    evidence: Dict[str, Any] = {
        "fired": False,
        "branch": None,
        "branch_meaning": None,
        "counts_toward_promotion": False,
        "severity": None,
        "category": ANOMALY_CATEGORY,
        "description": None,
        "detector": "CoachValidator._check_zero_test_anomaly",
        "tests_required": bool(getattr(profile, "tests_required", False)),
        "profile_blocks_on_zero_tests": bool(
            getattr(profile, "zero_test_blocking", False)
        ),
        "files_created": files_created,
        "files_modified": files_modified,
        "tests_written": tests_written,
        "claimed_test_files": claimed_test_files,
        "test_files_on_disk": test_files_on_disk,
        "any_test_file_on_disk": bool(test_files_on_disk),
        # What the Player CLAIMED about its own quality gates. Recorded
        # because it is the entire substance of the tests_not_executed
        # branch, and a person cannot adjudicate that branch without it.
        "claimed_all_passed": quality_gates.get("all_passed"),
        "claimed_tests_passed": quality_gates.get("tests_passed"),
        "claimed_coverage": quality_gates.get("coverage"),
        "independent_test_command": independent_command,
        "requirements_met": _requirements_met(requirements),
        "evaluation_error": None,
    }

    try:
        issues = validator._check_zero_test_anomaly(
            task_work_results,
            profile,
            independent_tests=independent_tests,
            task_id=task_id,
        )
    except Exception as exc:  # noqa: BLE001 — the instrument must never break a build
        logger.warning(
            "zero_test_gate: the zero-test rule raised %s for %s — recorded "
            "as not fired (an instrument that cannot report must not "
            "manufacture a verdict).",
            exc.__class__.__name__,
            task_id,
        )
        evidence["evaluation_error"] = f"{exc.__class__.__name__}: {exc}"
        return evidence

    if not issues:
        return evidence

    first = issues[0] if isinstance(issues[0], dict) else {}
    branch = _fired_branch(task_work_results, independent_tests)
    evidence["fired"] = True
    evidence["branch"] = branch
    evidence["branch_meaning"] = BRANCH_MEANINGS[branch]
    evidence["counts_toward_promotion"] = branch == COUNTS_TOWARD_PROMOTION
    evidence["severity"] = first.get("severity")
    evidence["description"] = first.get("description")
    return evidence


def _requirements_met(requirements: Any) -> Optional[bool]:
    """``True``/``False`` when the acceptance criteria verdict is known, else None."""
    if requirements is None:
        return None
    value = getattr(requirements, "all_criteria_met", None)
    return bool(value) if isinstance(value, bool) else None


def _no_test_file_advisory(evidence: Dict[str, Any]) -> str:
    """The sentence for branch one. Every claim in it is true of that branch."""
    created = evidence.get("files_created") or []
    modified = evidence.get("files_modified") or []
    return (
        "\nADVISORY — NO TEST FILE WAS WRITTEN: the Player's report for this "
        f"turn names no test file, lists {len(created)} file(s) created and "
        f"{len(modified)} file(s) modified, and the Coach's own independent "
        "test run searched the worktree and found no task-specific test to "
        "execute.\n"
        "Some changes legitimately need no test — a documentation edit, a "
        "rename, deleting dead code, a configuration change. Others do not: a "
        "new behaviour with no test is unverified work.\n"
        "Weigh this. It is ADVISORY and does NOT block the turn on its own, "
        "and you must not reject solely because this line is present — say in "
        "your rationale which of the two cases you judge this to be.\n"
    )


def _tests_not_executed_advisory(evidence: Dict[str, Any]) -> str:
    """The sentence for branch two.

    Deliberately says nothing about test files being absent. They may be
    present; the finding is about the Player's report contradicting itself.
    """
    on_disk = evidence.get("test_files_on_disk") or []
    named = evidence.get("tests_written") or []
    if on_disk:
        presence = (
            f"{len(on_disk)} test file(s) named by this turn DO exist on "
            "disk, so this is not a report of missing tests"
        )
    elif named:
        presence = (
            f"{len(named)} test file(s) are named in the report but none was "
            "confirmed on disk by this check"
        )
    else:
        presence = "this check did not confirm any test file for this turn"
    coverage = evidence.get("claimed_coverage")
    return (
        "\nADVISORY — THE REPORT SAYS NO TEST RAN: the Player's report claims "
        "every quality gate passed while also reporting that zero tests "
        f"executed (tests_passed=0, coverage={coverage}). Note that "
        f"{presence}.\n"
        "This is a claim-versus-evidence problem, not a missing-test "
        "problem: a quality gate cannot honestly be reported as passed on the "
        "strength of a test run that did not happen. A reported coverage "
        "figure with no test run behind it is not evidence either.\n"
        "Weigh this. It is ADVISORY and does NOT block the turn on its own, "
        "and you must not reject solely because this line is present — say in "
        "your rationale whether you accept the reported pass and why.\n"
    )


def coach_advisory_text(evidence: Optional[Dict[str, Any]]) -> str:
    """The plain sentence the language-model Coach is shown. Empty when clean.

    This is the behaviour change that costs nothing and helps immediately:
    before this, the Coach was never told, in words, that its tests were
    missing or unrun. The numbers were buried among dozens of sibling keys in
    the evidence JSON and nothing named them.

    **The sentence is branch-specific**, because the two branches assert
    different facts and a blended sentence is false for one of them. See the
    module docstring.

    The wording deliberately states that the check does not block, so the
    Coach neither treats it as a rule it must obey nor as a fact it may
    ignore — it is one more piece of evidence to weigh, and it says so.
    """
    if not isinstance(evidence, dict) or not evidence.get("fired"):
        return ""
    if evidence.get("branch") == BRANCH_TESTS_NOT_EXECUTED:
        return _tests_not_executed_advisory(evidence)
    return _no_test_file_advisory(evidence)


def build_receipt(
    *,
    evidence: Dict[str, Any],
    task_id: str,
    turn: int,
    feature_id: Optional[str],
    repo: Optional[str],
    repo_path: Optional[str],
    coach_decision: Optional[str],
    blocking: bool,
    overridden: bool,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the durable record for one fired check.

    Carries everything a person needs, months later, to adjudicate the row
    without re-running anything or opening another file: **which branch
    fired**, which feature and task, when, what the Player created, modified
    and claimed, whether any test file exists on disk, what the Coach decided
    anyway, and which repository it happened in.
    """
    branch = evidence.get("branch")
    return {
        "schema": "zero_test_receipt/2",
        "recorded_at": now or datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "repo_path": repo_path,
        "feature_id": feature_id,
        "task_id": task_id,
        "turn": turn,
        # WHICH OF THE TWO SITUATIONS THIS IS. Never conflate them downstream.
        "branch": branch,
        "branch_meaning": evidence.get("branch_meaning"),
        "counts_toward_promotion": bool(evidence.get("counts_toward_promotion")),
        "coach_decision": coach_decision,
        "severity": evidence.get("severity"),
        "blocking_requested": blocking,
        "decision_overridden": overridden,
        "files_created": evidence.get("files_created") or [],
        "files_modified": evidence.get("files_modified") or [],
        "tests_written": evidence.get("tests_written") or [],
        "claimed_test_files": evidence.get("claimed_test_files") or [],
        "test_files_on_disk": evidence.get("test_files_on_disk") or [],
        "any_test_file_on_disk": bool(evidence.get("any_test_file_on_disk")),
        "claimed_all_passed": evidence.get("claimed_all_passed"),
        "claimed_tests_passed": evidence.get("claimed_tests_passed"),
        "claimed_coverage": evidence.get("claimed_coverage"),
        "independent_test_command": evidence.get("independent_test_command"),
        "requirements_met": evidence.get("requirements_met"),
        "tests_required": bool(evidence.get("tests_required")),
        "profile_blocks_on_zero_tests": bool(
            evidence.get("profile_blocks_on_zero_tests")
        ),
        "description": evidence.get("description"),
        # Left for a person to fill in later, by hand or by a follow-up tool.
        # This is the half of the promotion question a machine cannot answer,
        # and it is only meaningful for a ``no_test_file`` row.
        "legitimately_test_free": None,
    }


def _append_line_atomically(path: Path, line: str) -> None:
    """Append one whole line to a JSON-lines file without interleaving.

    Many autobuild worktrees append to one ledger concurrently. Two guards
    that finish a turn together must not splice their lines together, so:

    * the file is opened ``O_APPEND``, which makes every write land at the
      current end of file even as others grow it;
    * an exclusive ``fcntl.flock`` serialises the writers;
    * the whole line, newline included, goes out in one ``os.write``.

    A platform with no ``fcntl`` still appends, unlocked — a measurement that
    might interleave beats no measurement.
    """
    payload = line.encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            written = 0
            while written < len(payload):
                written += os.write(fd, payload[written:])
        finally:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def write_receipt(
    record: Dict[str, Any],
    *,
    worktree_path: Path,
    repo_root: Optional[Path] = None,
    task_id: str,
    turn: int,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Write the per-turn receipt and append the durable ledger line.

    Mirrors ``qav_shadow._write_receipt``: the two writes are independent, and
    **neither can ever break a build** — a failure swallows to a warning.

    ``repo_root`` names the repository the ledger belongs to. When it is
    ``None`` (the build is running directly in the repository rather than in
    a worktree) the worktree path is the repository. The ledger itself is
    written OUTSIDE that repository — see the module docstring and D-OBS-4.

    Returns the per-turn receipt path, or ``None`` when that write failed.
    """
    receipt_path: Optional[Path] = Path(worktree_path) / ZERO_TEST_RECEIPT.format(
        task_id=task_id, turn=turn
    )
    try:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unwritable receipt %s (%r) — record dropped",
            receipt_path,
            exc,
        )
        receipt_path = None

    ledger_owner = Path(repo_root) if repo_root is not None else Path(worktree_path)
    ledger_path = ledger_path_for(ledger_owner, env)
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        _append_line_atomically(ledger_path, json.dumps(record, sort_keys=True) + "\n")
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unwritable ledger %s (%r) — row dropped",
            ledger_path,
            exc,
        )
    return receipt_path


def _read_jsonl(ledger_path: Path) -> List[Dict[str, Any]]:
    """Every JSON object in one ledger file, oldest first. Missing file → []."""
    if not ledger_path.is_file():
        return []

    rows: List[Dict[str, Any]] = []
    try:
        raw_lines: Sequence[str] = ledger_path.read_text(
            encoding="utf-8"
        ).splitlines()
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unreadable ledger %s (%r) — reporting nothing",
            ledger_path,
            exc,
        )
        return []

    for number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            logger.warning(
                "zero_test_gate: ledger %s line %d is not valid JSON — skipped",
                ledger_path,
                number,
            )
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def read_receipts(
    repo_root: Path, env: Optional[Mapping[str, str]] = None
) -> List[Dict[str, Any]]:
    """Read one repository's recorded rows, oldest first.

    Reads the durable ledger, and then any rows still sitting at the old
    in-tree path so that nothing recorded before the move is dropped. A
    malformed line is skipped with a warning rather than aborting the read —
    a measurement instrument that refuses to report because one row is corrupt
    is worse than one that reports the rest.
    """
    rows = _read_jsonl(ledger_path_for(repo_root, env))
    rows.extend(_read_jsonl(legacy_ledger_path_for(repo_root)))
    return rows
