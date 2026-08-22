"""Notices — and records — when a build's tests cannot be found, or never ran.

PLAIN-LANGUAGE SUMMARY
----------------------
GuardKit builds software in a loop with two halves. A **Player** writes the
code. A **Coach** then reviews what the Player did and decides one of three
things: approve, send feedback, or reject.

There are two Coach implementations in this repository:

* The **legacy** Coach is a set of hard-coded rules
  (``CoachValidator.validate``). One of those rules,
  ``CoachValidator._check_zero_test_anomaly``, refuses to approve a turn
  whose tests it cannot find, or whose own report says none ran.
* The **live** Coach — the default since 2026-05-21 — is a language model.
  The rule-based validator was demoted to gathering evidence for it
  (``CoachValidator.gather_evidence``). On that path the rule was never run,
  and the model's written instructions never mentioned the case, so nothing
  put the fact in front of it.

This module closes that gap on the live path. It runs **the same rule** —
``_check_zero_test_anomaly``, not a second copy of it — over the same evidence,
puts the answer in front of the language model in plain words, and writes a
durable record every time it fires.

THE CHECK REPORTS WHAT IT RECOGNISED — NEVER WHAT EXISTS
---------------------------------------------------------
This is the single most important paragraph in the module, and three earlier
versions of it were wrong.

The check has no way of knowing whether the builder wrote a test. It knows
three much smaller things, and only these three:

1. what the builder's own report listed under ``tests_written``;
2. whether any file name the report mentions matches one of a **fixed, short
   list of test-file naming conventions** (see :data:`KNOWN_TEST_CONVENTIONS`)
   — that recogniser is ``CoachValidator._is_test_file_path``, and it knows
   Python, Go, TypeScript, JavaScript and .NET and nothing else;
3. whether the Coach's own independent test run — a **pytest** run, so
   Python only — found a task-specific test it could execute.

A test written in Java, Ruby, Rust, C, C++, Elixir, Kotlin, Swift, a shell
script, a ``.feature`` file, or in any Python file whose name does not match
those conventions, is invisible to all three. So is a perfectly ordinary
``test_*.py`` that ``collect_ignore_glob`` excludes from collection.

Earlier rounds tried to fix this by teaching the recogniser one more
language. That is the losing move: there is always one more language. **What
changed instead is the claim.** Nothing this module writes — to the Coach, to
the Player, to the ledger, or to a person reading the report — says a test
does not exist. Every sentence is scoped to recognition, and where the check
has evidence that a test file *is* named, it says that — and says how strong
that evidence is — instead of guessing.

THE RULE HAS TWO BRANCHES, AND THEY ARE DIFFERENT SITUATIONS
------------------------------------------------------------
``_check_zero_test_anomaly`` can fire for either of two entirely different
reasons. It returns the same ``category`` for both, so nothing downstream
could previously tell them apart. This module names them:

``no_test_recognised`` — **no test was RECOGNISED for this turn.**
    Fires when the Player's ``tests_written`` list is empty *and* the Coach's
    own independent test run reported that it found no task-specific test to
    execute (its command reads ``"skipped"``). Both halves must hold.

    The branch says nothing about whether a test exists. It arrives in two
    shapes, and the wording shown to the Coach, written into the receipt and
    printed in the report says which shape a row is, read from
    ``recognised_test_files``:

    * ``recognised_test_files`` empty — nothing the report names matches a
      convention the recogniser knows. **This** is the shape the promotion
      question is about: a person must judge whether the turn legitimately
      needed no test (a documentation edit, a rename, deleting dead code, a
      configuration change), whether it is unverified work, or whether it
      wrote a test in a form nothing here can see.
    * ``recognised_test_files`` non-empty — the report names test files that
      the rule did not look at (it reads ``tests_written`` and nothing else)
      and the pytest run could not execute. That is **positive evidence a
      test exists**, and the wording says so. The row is still recorded under
      this branch, because the branch is defined by the rule's control flow
      and nothing else, but the report flags it so nobody rules it test-free
      by mistake.

    A third possibility is recorded rather than assumed away: if the
    recogniser is unavailable or raises on a file name, that file goes into
    ``files_not_examined`` and the sentence says so — it does not quietly
    count as "not a test".

``report_says_no_test_ran`` — **tests may well exist; the Player's own report
says none ran.**
    Fires when the first branch did *not* apply, and the Player's report
    claims ``quality_gates.all_passed`` is true while reporting
    ``tests_passed`` as zero (or as a value this check reads as zero).

    Nothing in this branch says a test file is missing. Test files may be
    listed in ``tests_written``, may exist on disk, and may have been written
    this very turn. What is wrong here is the **report**: it asserts every
    quality gate passed while simultaneously reporting that no test executed.
    That is a claim-versus-evidence problem, not a missing-test problem.

THE BRANCH IDENTIFIERS WERE RENAMED; THE ENV VARS AND FILE NAMES WERE NOT
--------------------------------------------------------------------------
The two identifiers used to be ``no_test_file`` and ``tests_not_executed``.
Both named a fact about the world that the check cannot establish, so both
were renamed — they appear in ``--json`` output and in every receipt, which
makes them user-facing. Nothing had recorded a row under the old names
anywhere in this estate when the rename happened, and :data:`LEGACY_BRANCH_IDS`
maps them forward anyway, so no already-recorded row is lost or reclassified.

What was deliberately **not** renamed, and why:

* ``GUARDKIT_ZERO_TEST_BLOCKING`` and ``GUARDKIT_ZERO_TEST_ROOT`` — an
  environment variable is an operator's interface. Renaming it would silently
  turn blocking off for anyone who had set it.
* the module, the receipt file name, ``queue.jsonl``, and the
  ``guardkit autobuild zero-test-report`` / ``zero-test-rule`` commands — the
  command names are installed on people's machines and written into runbooks,
  and the file names are pinned by the wiring tests that prove the instrument
  is still connected.

"Zero-test" as a *file and command* name is a neutral label for the
instrument. It is the *claims* that had to change.

WHICH BRANCH FEEDS THE PROMOTION MEASUREMENT — only the first
--------------------------------------------------------------
Only ``no_test_recognised`` rows count toward the promotion decision
(:data:`COUNTS_TOWARD_PROMOTION`). ``report_says_no_test_ran`` rows are
recorded and reported, but deliberately kept out of the rate, for three
reasons:

1. The promotion question is "how often does a turn legitimately need no
   test?". A ``report_says_no_test_ran`` turn has not been shown to lack a
   test, so it cannot answer that question either way.
   (A ``no_test_recognised`` row whose ``recognised_test_files`` is non-empty
   has not been shown to lack one either. It still counts, because the branch
   follows the rule's control flow rather than a second opinion about it, but
   the report marks it so a person does not rule it test-free by mistake. If
   that proves common in the accumulated rows, excluding it is a decision for
   whoever reads the measurement, not for this module to take quietly.)
2. The adjudication a person performs — marking a row
   ``legitimately_test_free`` — is meaningless for the second branch. The
   useful follow-up there is "why did the report claim a pass with no test
   run?", which is a different question with a different owner.
3. Blending them inflates the numerator with turns that are not test-free at
   all, and the resulting rate would be acted on.

HOW THE BRANCH IS DETERMINED — from the rule's own control flow
----------------------------------------------------------------
The rule tests the ``no_test_recognised`` condition first and returns
immediately if it holds. So: given that the rule fired, if that first
condition holds the branch is ``no_test_recognised``; otherwise it is
``report_says_no_test_ran``. That is exact, not a guess at the wording of a
message.

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

ADJUDICATION GOES IN ITS OWN FILE — never in the ledger
--------------------------------------------------------
A person rules on a row by marking it ``legitimately_test_free``. That ruling
is appended to ``rulings.jsonl`` beside the ledger, and the report joins the
two on ``(repo, task_id, turn)``. It is a separate file because the ``flock``
above serialises builds against **builds**; nothing serialises a build's
append against a **person with the ledger open in an editor**, and whoever
saves last would silently destroy the other's work. Rows already carrying an
inline ``legitimately_test_free``, written by hand before this file existed,
are still honoured.

Read the ledger, and rule on a row, with::

    guardkit autobuild zero-test-report
    guardkit autobuild zero-test-rule --task TASK-X --turn 1 --test-free

Both resolve the repository through :func:`resolve_repo_root`, the same
function the writing side goes through — so neither can be run from a
directory that quietly looks in the wrong place.

Neither write can ever break a build: every failure swallows to a warning.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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
    "ZERO_TEST_RULINGS_FILENAME",
    "LEGACY_IN_TREE_QUEUE",
    "ZERO_TEST_RECEIPT",
    "ANOMALY_CATEGORY",
    "BRANCH_NO_TEST_RECOGNISED",
    "BRANCH_REPORT_SAYS_NO_TEST_RAN",
    "LEGACY_BRANCH_IDS",
    "BRANCH_LABELS",
    "BRANCH_MEANINGS",
    "KNOWN_TEST_CONVENTIONS",
    "RECOGNISED_CONVENTIONS_PHRASE",
    "UNRECOGNISED_EXAMPLES",
    "HEADLINE_NONE_RECOGNISED",
    "HEADLINE_TEST_NAMED_NONE_RAN",
    "HEADLINE_REPORT_SAYS_NO_TEST_RAN",
    "ADVISORY_HEADLINES",
    "COUNTS_TOWARD_PROMOTION",
    "normalise_branch",
    "blocking_requested",
    "resolve_repo_root",
    "ledger_path_for",
    "rulings_path_for",
    "legacy_ledger_path_for",
    "evaluate_zero_test",
    "build_receipt",
    "write_receipt",
    "coach_advisory_text",
    "LedgerRead",
    "read_ledger",
    "read_receipts",
    "ruling_key",
    "record_ruling",
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
#: per line. **Builds write this; a person never edits it.**
ZERO_TEST_QUEUE_FILENAME = "queue.jsonl"

#: A person's rulings on recorded rows, beside the ledger and separate from
#: it. **A person writes this; a build never touches it.** See
#: :func:`rulings_path_for` for why the two must not be the same file.
ZERO_TEST_RULINGS_FILENAME = "rulings.jsonl"

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

#: Branch 1: the Player's ``tests_written`` list is empty AND the Coach's own
#: pytest run reported that it found no task-specific test to execute. Note
#: what this does NOT say — see :data:`BRANCH_MEANINGS`. Renamed from
#: ``no_test_file`` (which asserted a fact about the world the check cannot
#: establish); :data:`LEGACY_BRANCH_IDS` maps the old value forward.
BRANCH_NO_TEST_RECOGNISED = "no_test_recognised"

#: Branch 2: tests may exist, but the Player's report claims every quality
#: gate passed while reporting that zero tests executed. Renamed from
#: ``tests_not_executed`` for the same reason: the check knows what the report
#: SAYS, not what ran.
BRANCH_REPORT_SAYS_NO_TEST_RAN = "report_says_no_test_ran"

#: Branch identifiers written by earlier versions of this module, mapped to
#: the ones in use. Nothing in this estate had recorded a row under the old
#: names when they were renamed, but a row from anywhere else still classifies
#: rather than falling into the report's "unlabelled" bucket.
LEGACY_BRANCH_IDS = {
    "no_test_file": BRANCH_NO_TEST_RECOGNISED,
    "tests_not_executed": BRANCH_REPORT_SAYS_NO_TEST_RAN,
}

#: Short human labels, for tables and one-line summaries. Both are scoped to
#: what the check saw: it recognises, and it reads a report.
BRANCH_LABELS = {
    BRANCH_NO_TEST_RECOGNISED: "no test recognised",
    BRANCH_REPORT_SAYS_NO_TEST_RAN: "report says 0 tests ran",
}

#: The test-file naming conventions the recogniser
#: (``CoachValidator._is_test_file_path``) actually knows, each paired with a
#: file name it accepts. **This list is the whole of what "recognised" means**,
#: and it is quoted verbatim to the Coach and to a person reading the report,
#: so that neither mistakes silence for absence.
#:
#: ``tests/orchestrator/test_zero_test_gate.py`` runs every example below
#: through the real recogniser, so this list cannot drift into claiming more
#: than the code does.
KNOWN_TEST_CONVENTIONS = (
    ("test_*.py", "tests/test_widget.py"),
    ("*_test.py", "tests/widget_test.py"),
    ("*_test.go", "widget_test.go"),
    ("*.test.ts / *.test.js", "src/widget.test.ts"),
    ("*.spec.ts / *.spec.js", "src/widget.spec.js"),
    ("*.cs under Tests/", "Tests/WidgetTests.cs"),
)

#: The conventions above as one parenthetical phrase, for prose.
RECOGNISED_CONVENTIONS_PHRASE = ", ".join(
    pattern for pattern, _example in KNOWN_TEST_CONVENTIONS
)

#: Languages and forms the recogniser and the pytest run are both blind to.
#: Named explicitly, because "no test was recognised" is only honest if the
#: reader is told how narrow the recogniser is.
UNRECOGNISED_EXAMPLES = (
    "in Java, Ruby, Rust, C, C++, Kotlin, Swift or Elixir, as a shell "
    "script, as a .feature file, or as a Python file whose name matches none "
    "of those patterns or that collect_ignore_glob excludes from collection"
)

#: The headline of every advisory sentence this module can produce, keyed by
#: the situation it describes. Exported so the Coach's standing instructions
#: can be checked against the code rather than against a copy of the wording:
#: if a headline changes here and not in ``installer/core/agents/
#: autobuild-coach.md``, the guard test goes red.
HEADLINE_NONE_RECOGNISED = "ADVISORY — NO TEST FILE WAS RECOGNISED FOR THIS TURN"
HEADLINE_TEST_NAMED_NONE_RAN = "ADVISORY — A TEST FILE IS NAMED, BUT NONE RAN"
HEADLINE_REPORT_SAYS_NO_TEST_RAN = "ADVISORY — THE REPORT SAYS NO TEST RAN"

#: Every headline above, as one set.
ADVISORY_HEADLINES = (
    HEADLINE_NONE_RECOGNISED,
    HEADLINE_TEST_NAMED_NONE_RAN,
    HEADLINE_REPORT_SAYS_NO_TEST_RAN,
)

#: One sentence per branch, for a person who has never read this module.
#: Every clause is scoped to what the check looked at.
BRANCH_MEANINGS = {
    BRANCH_NO_TEST_RECOGNISED: (
        "No test was RECOGNISED for this turn: the Player's tests-written "
        "list is empty, and the Coach's own pytest run reported that it found "
        "no task-specific test to execute. This is not evidence that no test "
        "exists — the rule never reads the report's created/modified lists, "
        "and the recogniser knows only "
        f"{RECOGNISED_CONVENTIONS_PHRASE}. Check recognised_test_files and "
        "the created/modified lists before ruling on the row."
    ),
    BRANCH_REPORT_SAYS_NO_TEST_RAN: (
        "Tests may well exist. The Player's report claims every quality gate "
        "passed while also reporting that zero tests ran — a claim-versus-"
        "evidence problem, not a missing-test problem."
    ),
}

#: The only branch that feeds the promotion measurement. See the module
#: docstring for why the other one is deliberately excluded.
COUNTS_TOWARD_PROMOTION = BRANCH_NO_TEST_RECOGNISED


def normalise_branch(value: Any) -> Optional[str]:
    """The branch identifier in use, given whatever a row carries.

    Maps the identifiers earlier versions wrote (:data:`LEGACY_BRANCH_IDS`)
    onto the current ones and passes the current ones through. Anything else —
    including a row recorded before branches existed at all — comes back
    ``None``, which every caller treats as "cannot be attributed", never as a
    guess.
    """
    if not isinstance(value, str):
        return None
    if value in BRANCH_LABELS:
        return value
    return LEGACY_BRANCH_IDS.get(value)


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

    Only ``no_test_recognised`` rows do. A row written before branches were
    recorded carries no ``branch`` at all; those are treated as NOT counting,
    because guessing would put unverified rows into the one number this
    instrument exists to produce. A row carrying one of the identifiers an
    earlier version wrote is mapped forward by :func:`normalise_branch` rather
    than dropped.
    """
    return normalise_branch(row.get("branch")) == COUNTS_TOWARD_PROMOTION


def _main_worktree_of(git_link: Path) -> Optional[Path]:
    """The main checkout behind a linked git worktree, or ``None``.

    A linked worktree (anything made by ``git worktree add``) has a ``.git``
    **file**, not a directory, holding one line::

        gitdir: /path/to/main-checkout/.git/worktrees/<name>

    The main checkout is the part before ``/.git/worktrees/``. Reading that
    line is cheaper and more predictable than shelling out to git on a path
    that only ever reports a measurement.
    """
    try:
        text = git_link.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("gitdir:"):
            continue
        gitdir = Path(line.split(":", 1)[1].strip())
        parts = gitdir.parts
        for index in range(len(parts) - 1):
            if parts[index] == ".git" and parts[index + 1] == "worktrees":
                return Path(*parts[:index]) if index else None
        return None
    return None


def resolve_repo_root(start: Any) -> Path:
    """The repository a row belongs to, given ANY path inside it.

    **Both the writing side and the reading side go through this one
    function, and that is the point.** They used to answer the question
    separately: a build keyed its rows by the repository it was building,
    while ``guardkit autobuild zero-test-report`` keyed its lookup by whatever
    directory the person happened to be standing in. Run the report one level
    down and it looked in a directory that had never been written to, found
    nothing, and said so — which reads as "no build skipped its tests". A
    check whose answer is narrower than it reads is the exact fault this
    instrument exists to catch, so it must not have one.

    The answer, in order:

    1. **An autobuild worktree** lives at
       ``<repo>/.guardkit/worktrees/<task or feature id>/...``. Its rows
       belong to ``<repo>``. This is the same strip
       ``AgentInvoker._resolve_repo_root`` performs, kept first so the two
       agree on the case that actually occurs in a build.
    2. **Any other checkout**: the nearest enclosing directory holding a
       ``.git``. When that ``.git`` is a *file* — a linked ``git worktree`` —
       the main checkout behind it is used, so a lane worktree reports the
       repository's rows rather than its own empty ones.
    3. **Nothing git-like above it**: the path itself, unchanged. A temporary
       directory in a test is its own repository, which is what a test wants.

    The result is idempotent: resolving an already-resolved root returns it.
    """
    path = Path(start).resolve()

    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index] == ".guardkit" and parts[index + 1] == "worktrees":
            if index:
                return Path(*parts[:index])

    for candidate in (path, *path.parents):
        git = candidate / ".git"
        if git.is_file():
            return _main_worktree_of(git) or candidate
        if git.is_dir():
            return candidate

    return path


def ledger_path_for(
    repo_root: Any, env: Optional[Mapping[str, str]] = None
) -> Path:
    """The durable ledger file for one repository. Outside every worktree.

    ``~/.guardkit/zero-test/<repo name>/queue.jsonl`` by default;
    ``$GUARDKIT_ZERO_TEST_ROOT/<repo name>/queue.jsonl`` when that variable is
    set. See the module docstring for the Decision of Record behind this.

    ``repo_root`` may be any path inside the repository: it is put through
    :func:`resolve_repo_root` first, so a reader standing in a subdirectory
    and a build writing from its worktree land on the same file **by
    construction** rather than by both remembering to resolve.
    """
    source = os.environ if env is None else env
    configured = str(source.get(ZERO_TEST_ROOT_ENV_VAR, "") or "").strip()
    home = Path(configured) if configured else ZERO_TEST_HOME
    return home / resolve_repo_root(repo_root).name / ZERO_TEST_QUEUE_FILENAME


def rulings_path_for(
    repo_root: Any, env: Optional[Mapping[str, str]] = None
) -> Path:
    """Where a person's rulings on this repository's rows are kept.

    **A separate file from the ledger, deliberately.** Builds append to
    ``queue.jsonl`` continuously and concurrently; the append is serialised
    against other *builds* by an ``flock`` (see
    :func:`_append_line_atomically`), but nothing serialises it against a
    **person with the file open in an editor**. Whoever saves last wins, and
    what gets lost is either a build's row or a person's ruling — silently,
    in the one file this instrument exists to accumulate.

    So rulings go in their own append-only journal beside the ledger, and the
    report joins the two on ``(repo, task_id, turn)``. Nothing a person edits
    is ever a file a build writes.
    """
    return ledger_path_for(repo_root, env).with_name(ZERO_TEST_RULINGS_FILENAME)


def legacy_ledger_path_for(repo_root: Any) -> Path:
    """The old in-tree ledger path. Read for continuity; never written."""
    return resolve_repo_root(repo_root) / LEGACY_IN_TREE_QUEUE


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
    message: ``_check_zero_test_anomaly`` evaluates the
    ``no_test_recognised`` condition first and returns immediately when it holds. So, GIVEN that the
    rule fired, that condition holding means branch one; anything else means
    the rule fell through to branch two.
    """
    raw_tests_written = task_work_results.get("tests_written", [])
    try:
        listed_no_test = len(raw_tests_written) == 0
    except TypeError:  # a report with a non-sequence there; the rule would
        listed_no_test = False  # have raised, and we record honestly.

    search_found_nothing = (
        bool(independent_tests)
        and getattr(independent_tests, "test_command", None) == "skipped"
    )
    if listed_no_test and search_found_nothing:
        return BRANCH_NO_TEST_RECOGNISED
    return BRANCH_REPORT_SAYS_NO_TEST_RAN


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
    created, modified and claimed, which of those names the recogniser
    MATCHED (``recognised_test_files``), which it never got to examine
    (``files_not_examined``), and which of the matched names are actually
    present on disk.

    Nothing here decides that a file is not a test. A name the recogniser
    could not examine is recorded as unexamined, not as a non-test, so no
    sentence built from this evidence can claim more than was looked at.

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

    # THE RECOGNITION PASS. Three outcomes per file name, kept apart, because
    # collapsing the third into the second is exactly how this instrument came
    # to state a falsehood: "the recogniser did not match it" and "the
    # recogniser never looked at it" are different facts, and only the first
    # one licenses saying anything at all about the file.
    recognised_test_files: List[str] = []
    files_examined: List[str] = []
    files_not_examined: List[str] = []
    recogniser_available = callable(is_test_path)
    seen: List[str] = []
    for candidate in [*tests_written, *files_created, *files_modified]:
        if candidate in seen:
            continue
        seen.append(candidate)
        if not recogniser_available:
            files_not_examined.append(candidate)
            continue
        try:
            looks_like_a_test = bool(is_test_path(candidate))
        except Exception:  # noqa: BLE001 — a heuristic must never break gathering
            files_not_examined.append(candidate)
            continue
        files_examined.append(candidate)
        if looks_like_a_test:
            recognised_test_files.append(candidate)

    # Whether a recognised file is actually THERE. Only knowable when the
    # validator carries a worktree path; when it does not, the answer is
    # "not checked", never "no".
    disk_checked = worktree_path is not None
    test_files_on_disk: List[str] = []
    if disk_checked:
        for candidate in recognised_test_files:
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
        # WHAT THE RECOGNISER SAW. Named for what it is: files whose NAME
        # matches one of KNOWN_TEST_CONVENTIONS. Never read as "the tests".
        "recognised_test_files": recognised_test_files,
        "files_examined": files_examined,
        "files_not_examined": files_not_examined,
        "recogniser_available": recogniser_available,
        "recognised_conventions": [
            pattern for pattern, _example in KNOWN_TEST_CONVENTIONS
        ],
        "disk_checked": disk_checked,
        "test_files_on_disk": test_files_on_disk,
        "any_test_file_on_disk": bool(test_files_on_disk),
        # What the Player CLAIMED about its own quality gates. Recorded
        # because it is the entire substance of the report_says_no_test_ran
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


_WEIGH_THIS = (
    "Weigh this. It is ADVISORY and does NOT block the turn on its own, "
    "and you must not reject solely because this line is present — say in "
    "your rationale which of the cases above you judge this to be.\n"
)

#: The one paragraph that keeps every "nothing was recognised" sentence
#: honest. It is appended to that sentence and nowhere else, and it is what
#: separates a statement about this check from a statement about the world.
_RECOGNITION_IS_NOT_EXISTENCE = (
    "That is the WHOLE of what is known, and all of it is about recognition, "
    "not about what exists. A test written "
    f"{UNRECOGNISED_EXAMPLES} is invisible to every one of those checks. Do "
    "not conclude from this line that the turn produced no test — look at the "
    "changed files yourself and say what you found.\n"
)


def _plural_files(count: int) -> str:
    return "1 file" if count == 1 else f"{count} files"


def _listing(names: Sequence[Any], limit: int = 3) -> str:
    """``a, b, c, +2 more`` — a bounded, readable file listing."""
    shown = ", ".join(str(name) for name in names[:limit])
    if len(names) > limit:
        shown += f", +{len(names) - limit} more"
    return shown


def _pytest_run_clause() -> str:
    """What the Coach's own test run reported. Scoped to the report of a run.

    Branch one is reached only when that run's command reads ``"skipped"``,
    which ``run_independent_tests`` sets in exactly one place: it looked for a
    task-specific test to execute and found none. The clause says that, and
    names the run's one blind spot — it is pytest, so it can only ever find
    Python tests it is able to collect.
    """
    return (
        "the Coach's own independent test run reported that it found no "
        "task-specific test to execute (that run is pytest, so it can only "
        "find Python tests it is able to collect)"
    )


def _recognition_clauses(evidence: Dict[str, Any]) -> List[str]:
    """What the recogniser did and did not look at, as true clauses.

    Three separate facts, each stated only when it holds:

    * files that were examined and matched nothing;
    * files that could not be examined at all (the recogniser was missing or
      raised on the name) — these are never reported as "not a test";
    * what "matched" even means, quoted from :data:`KNOWN_TEST_CONVENTIONS`.
    """
    examined = evidence.get("files_examined") or []
    not_examined = evidence.get("files_not_examined") or []
    clauses: List[str] = []
    if len(examined) == 1:
        clauses.append(
            f"the one file it names ({examined[0]}) does not match a "
            "test-file naming convention this check knows "
            f"({RECOGNISED_CONVENTIONS_PHRASE})"
        )
    elif examined:
        clauses.append(
            f"none of the {len(examined)} files it names matches a "
            "test-file naming convention this check knows "
            f"({RECOGNISED_CONVENTIONS_PHRASE})"
        )
    if not_examined:
        clauses.append(
            f"{_plural_files(len(not_examined))} it names could not be "
            "examined by this check at all, so nothing is known about "
            f"{'it' if len(not_examined) == 1 else 'them'} "
            f"({_listing(not_examined)})"
        )
    return clauses


def _on_disk_clause(evidence: Dict[str, Any]) -> str:
    """How many recognised files are present — or that presence was not checked."""
    if not evidence.get("disk_checked"):
        return "this check could not look on disk to see whether they are there"
    on_disk = evidence.get("test_files_on_disk") or []
    if not on_disk:
        return "none of them was found on disk at the path the report gives"
    if len(on_disk) == 1:
        return "1 of them is present on disk"
    return f"{len(on_disk)} of them are present on disk"


def _no_test_recognised_advisory(evidence: Dict[str, Any]) -> str:
    """The sentence for branch one — in the two shapes that branch really has.

    **Branch one establishes exactly two things**, and this wording must not
    exceed them:

    * the Player's ``tests_written`` list is empty, and
    * the Coach's own independent test run reported that it found no
      task-specific test it could execute.

    It does **not** establish that no test file exists, and it does not even
    establish that the report names none. The rule reads ``tests_written`` and
    nothing else, while a Player is free to list a test under
    ``files_created`` / ``files_modified`` — the rule's own remediation text
    tells it to. The recogniser that inspects those lists knows six naming
    conventions across five languages and nothing else. And the run behind the
    second bullet is pytest, so it comes up empty for a test in any other
    language, for a test excluded from collection by ``collect_ignore_glob``,
    and for pytest-bdd glue.

    So the branch has two shapes and gets two sentences, chosen by whether
    anything was recognised. Neither sentence says a test does not exist;
    the second one says, positively, that one is named.
    """
    named = evidence.get("recognised_test_files") or []

    if named:
        # The strength of the claim follows the evidence. A recognised name
        # that is ALSO on disk is positive evidence; a recognised name with
        # nothing at that path is not, and must not be reported as if it were.
        on_disk = evidence.get("test_files_on_disk") or []
        if on_disk:
            reading = (
                "So there is positive evidence a test for this turn exists; "
                "what is missing is a run of it and an entry in tests_written."
            )
        elif evidence.get("disk_checked"):
            reading = (
                "So the report names a test, but nothing was found at "
                "the path(s) it gives — either the path is wrong or the file "
                "was not written. This check cannot tell which."
            )
        else:
            reading = (
                "So the report names a test that this check could neither run "
                "nor look for on disk."
            )
        return (
            f"\n{HEADLINE_TEST_NAMED_NONE_RAN}: the Player's report for this "
            "turn lists nothing under tests_written, and "
            f"{_pytest_run_clause()} — but the report DOES name "
            f"{_plural_files(len(named))} matching a test-file naming "
            f"convention ({_listing(named)}), and "
            f"{_on_disk_clause(evidence)}.\n"
            f"{reading} Open "
            f"the named file{'' if len(named) == 1 else 's'} and say what you "
            "found. If a real test is there, say so — that is what stops this "
            "turn being counted as one that needed no test. If the Player "
            "wrote a test but left tests_written empty, ask it to list the "
            "file there: a bookkeeping fix, not a missing test.\n"
            + _WEIGH_THIS
        )

    clauses = [
        "the Player's report for this turn lists nothing under tests_written",
        *_recognition_clauses(evidence),
        _pytest_run_clause(),
    ]
    if len(clauses) == 2:
        body = f"{clauses[0]}, and {clauses[1]}"
    else:
        body = "; ".join(clauses[:-1]) + f"; and {clauses[-1]}"
    return (
        f"\n{HEADLINE_NONE_RECOGNISED}: {body}.\n"
        + _RECOGNITION_IS_NOT_EXISTENCE
        + "If the turn really did produce no test, some changes legitimately "
        "need none — a documentation edit, a rename, deleting dead code, a "
        "configuration change. Others do not: a new behaviour with no test is "
        "unverified work.\n"
        + _WEIGH_THIS
    )


def _reported_zero_clause(evidence: Dict[str, Any]) -> str:
    """How the report expressed "no tests ran" — quoted, not paraphrased.

    The rule reads ``quality_gates.tests_passed`` through ``... or 0``, so it
    treats a missing key, ``null``, ``false`` and ``""`` as zero just as it
    treats ``0``. Printing ``tests_passed=0`` for all of them would put a
    number in the report that the Player never wrote.
    """
    reported = evidence.get("claimed_tests_passed")
    if reported == 0 and not isinstance(reported, bool):
        return "reporting tests_passed=0"
    if reported is None:
        return "reporting no tests_passed count at all"
    return f"reporting tests_passed as {reported!r}, which this check reads as zero"


def _report_says_no_test_ran_advisory(evidence: Dict[str, Any]) -> str:
    """The sentence for branch two.

    Deliberately says nothing about test files being absent. They may be
    present; the finding is about the Player's report contradicting itself.
    """
    on_disk = evidence.get("test_files_on_disk") or []
    named = evidence.get("tests_written") or []
    if on_disk:
        presence = (
            f"{_plural_files(len(on_disk))} named by this turn "
            f"{'is' if len(on_disk) == 1 else 'are'} present on disk, so this "
            "is not a report of missing tests"
        )
    elif named:
        presence = (
            f"{_plural_files(len(named))} named in the report as written, none "
            "of which this check confirmed on disk"
        )
    else:
        presence = "this check recognised no test file for this turn"
    coverage = evidence.get("claimed_coverage")
    return (
        f"\n{HEADLINE_REPORT_SAYS_NO_TEST_RAN}: the Player's report claims "
        "every quality gate passed while also "
        f"{_reported_zero_clause(evidence)} (coverage={coverage}). Note that "
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
    before this, the Coach was never told, in words, that its tests could not
    be found or were never run. The numbers were buried among dozens of
    sibling keys in the evidence JSON and nothing named them.

    **The sentence is branch-specific**, because the two branches assert
    different facts and a blended sentence is false for one of them. Within
    branch one it is specific again, to whether anything was recognised. See
    the module docstring.

    **Every sentence it can produce is scoped to what this check looked at.**
    None of them asserts that a test does not exist, because no reachable turn
    entitles it to. Its headline is always one of
    :data:`ADVISORY_HEADLINES`, and the Coach's standing instructions are
    checked against that tuple rather than against a copy of the wording.

    The wording deliberately states that the check does not block, so the
    Coach neither treats it as a rule it must obey nor as a fact it may
    ignore — it is one more piece of evidence to weigh, and it says so.
    """
    if not isinstance(evidence, dict) or not evidence.get("fired"):
        return ""
    if normalise_branch(evidence.get("branch")) == BRANCH_REPORT_SAYS_NO_TEST_RAN:
        return _report_says_no_test_ran_advisory(evidence)
    return _no_test_recognised_advisory(evidence)


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
    and claimed, **which names the recogniser matched and which it never
    examined**, whether any recognised file was found on disk, what the Coach
    decided anyway, and which repository it happened in.

    The recognition fields are stored separately from the file lists on
    purpose. A row that says only "no test" cannot be adjudicated: a person
    reading it two years from now has to be able to see that the check knew
    six naming conventions and ran pytest, and nothing more.
    """
    branch = normalise_branch(evidence.get("branch"))
    return {
        "schema": "zero_test_receipt/3",
        "recorded_at": now or datetime.now(timezone.utc).isoformat(),
        "repo": repo,
        "repo_path": repo_path,
        "feature_id": feature_id,
        "task_id": task_id,
        "turn": turn,
        # WHICH OF THE TWO SITUATIONS THIS IS. Never conflate them downstream.
        "branch": branch,
        # The short human label AND the full sentence, both stored, so a
        # person reading a two-year-old row needs nothing but the row.
        "branch_label": BRANCH_LABELS.get(branch),
        "branch_meaning": evidence.get("branch_meaning"),
        "counts_toward_promotion": bool(evidence.get("counts_toward_promotion")),
        "coach_decision": coach_decision,
        "severity": evidence.get("severity"),
        "blocking_requested": blocking,
        "decision_overridden": overridden,
        "files_created": evidence.get("files_created") or [],
        "files_modified": evidence.get("files_modified") or [],
        "tests_written": evidence.get("tests_written") or [],
        # RECOGNITION, not existence. ``recognised_test_files`` is the set of
        # names matching one of ``recognised_conventions``; ``files_not_
        # examined`` is the set the recogniser never got to look at, kept
        # apart from the ones it looked at and rejected.
        "recognised_test_files": evidence.get("recognised_test_files") or [],
        "recognised_conventions": evidence.get("recognised_conventions") or [],
        "files_examined": evidence.get("files_examined") or [],
        "files_not_examined": evidence.get("files_not_examined") or [],
        "recogniser_available": bool(evidence.get("recogniser_available")),
        "disk_checked": bool(evidence.get("disk_checked")),
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
        # and it is only meaningful for a ``no_test_recognised`` row.
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


def ruling_key(row: Mapping[str, Any]) -> Tuple[str, str]:
    """The identity a ruling and the row it rules on are joined by.

    ``(task, turn)``. The repository is deliberately NOT part of the key:
    a ledger and its rulings journal are already two files inside one
    repository's directory, so adding the repository could only ever make a
    row and its ruling fail to meet — which is how a person's decision goes
    missing. Rows recorded before the ``repo`` field existed still join.

    Both halves are coerced to strings so a turn recorded as ``1`` and one
    written as ``"1"`` still meet.
    """
    return (str(row.get("task_id") or ""), str(row.get("turn")))


def record_ruling(
    *,
    repo_root: Any,
    task_id: str,
    turn: int,
    legitimately_test_free: bool,
    note: Optional[str] = None,
    repo: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    now: Optional[str] = None,
) -> Path:
    """Append one person's ruling on one recorded turn. Returns the file.

    Appended, never rewritten, and to a file **no build ever opens** — so a
    ruling cannot lose a race with a build finishing a turn, in either
    direction. Ruling the same turn twice is allowed and the later line wins;
    that is how a person changes their mind without editing anything.
    """
    resolved = resolve_repo_root(repo_root)
    record = {
        "schema": "zero_test_ruling/1",
        "ruled_at": now or datetime.now(timezone.utc).isoformat(),
        "repo": repo or resolved.name,
        "task_id": task_id,
        "turn": turn,
        "legitimately_test_free": bool(legitimately_test_free),
        "note": note,
    }
    path = rulings_path_for(repo_root, env)
    path.parent.mkdir(parents=True, exist_ok=True)
    _append_line_atomically(path, json.dumps(record, sort_keys=True) + "\n")
    return path


def _apply_rulings(
    rows: List[Dict[str, Any]], rulings: Sequence[Mapping[str, Any]]
) -> None:
    """Fold the rulings journal onto the rows it rules on, in place.

    Later rulings overwrite earlier ones for the same turn. A row already
    carrying an inline ``legitimately_test_free`` — written by hand into the
    ledger before rulings had their own file — keeps its value unless a
    ruling names it, so nothing anybody has already decided is lost.
    """
    verdicts: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for ruling in rulings:
        if not isinstance(ruling, Mapping):
            continue
        if not isinstance(ruling.get("legitimately_test_free"), bool):
            continue
        verdicts[ruling_key(ruling)] = ruling

    for row in rows:
        ruling = verdicts.get(ruling_key(row))
        if ruling is None:
            continue
        row["legitimately_test_free"] = ruling["legitimately_test_free"]
        row["ruled_at"] = ruling.get("ruled_at")
        row["ruling_note"] = ruling.get("note")


@dataclass(frozen=True)
class LedgerRead:
    """One repository's rows, **and where they were looked for**.

    The second half is not decoration. ``rows == []`` has two completely
    different causes — no ledger file exists at the resolved location, or a
    ledger exists and is empty — and only the second is a clean bill of
    health. Reporting them as one is how a check comes to answer a narrower
    question than it appears to, so the caller is handed both.
    """

    repo_root: Path
    ledger_path: Path
    legacy_path: Path
    rulings_path: Path
    ledger_exists: bool
    legacy_exists: bool
    rows: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def any_ledger_file(self) -> bool:
        """Was there anything to read at all? ``False`` means: never looked."""
        return self.ledger_exists or self.legacy_exists

    @property
    def paths_read(self) -> List[Path]:
        """The files that actually exist, for naming in a report."""
        return [
            path
            for path, exists in (
                (self.ledger_path, self.ledger_exists),
                (self.legacy_path, self.legacy_exists),
            )
            if exists
        ]


def read_ledger(
    repo_root: Any, env: Optional[Mapping[str, str]] = None
) -> LedgerRead:
    """Read one repository's rows and report where they were read from.

    ``repo_root`` may be any path inside the repository — it goes through
    :func:`resolve_repo_root`, the same function the writing side goes
    through, so a report run from a subdirectory reads the file a build
    wrote.

    Reads the durable ledger, then any rows still sitting at the old in-tree
    path so that nothing recorded before the move is dropped, then folds on
    the separate rulings journal. A malformed line is skipped with a warning
    rather than aborting the read — a measurement instrument that refuses to
    report because one row is corrupt is worse than one that reports the rest.
    """
    resolved = resolve_repo_root(repo_root)
    ledger = ledger_path_for(resolved, env)
    legacy = legacy_ledger_path_for(resolved)
    rulings = rulings_path_for(resolved, env)

    rows = _read_jsonl(ledger)
    rows.extend(_read_jsonl(legacy))
    _apply_rulings(rows, _read_jsonl(rulings))

    return LedgerRead(
        repo_root=resolved,
        ledger_path=ledger,
        legacy_path=legacy,
        rulings_path=rulings,
        ledger_exists=ledger.is_file(),
        legacy_exists=legacy.is_file(),
        rows=rows,
    )


def read_receipts(
    repo_root: Path, env: Optional[Mapping[str, str]] = None
) -> List[Dict[str, Any]]:
    """One repository's recorded rows, oldest first, rulings folded in.

    Thin wrapper over :func:`read_ledger` for callers that only want the
    rows. Anything that prints a verdict should use :func:`read_ledger`
    instead and check :attr:`LedgerRead.any_ledger_file`, so that "found
    nothing" is never printed as "nothing to find".
    """
    return read_ledger(repo_root, env).rows
