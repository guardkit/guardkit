"""Records what was observed when the zero-test rule fired. It interprets nothing.

PLAIN-LANGUAGE SUMMARY
----------------------
GuardKit builds software in a loop with two halves. A **Player** writes the
code. A **Coach** then reviews what the Player did and decides one of three
things: approve, send feedback, or reject.

There are two Coach implementations in this repository:

* The **legacy** Coach is a set of hard-coded rules
  (``CoachValidator.validate``). One of those rules,
  ``CoachValidator._check_zero_test_anomaly``, refuses to approve certain
  turns.
* The **live** Coach — the default since 2026-05-21 — is a language model.
  The rule-based validator was demoted to gathering evidence for it
  (``CoachValidator.gather_evidence``), and on that path the rule was never
  run at all.

This module runs **the same rule** — ``_check_zero_test_anomaly``, not a
second copy of it — on the live path, and writes down what it saw. That is
the whole of what it does.

WHAT THIS MODULE DOES NOT DO — read this before adding anything to it
---------------------------------------------------------------------
It states no conclusion. Four earlier versions tried to word a sentence
saying what a build had or had not done — "no test file was written", then
"no test was recognised", then two more attempts — and a reviewer refuted
each one, because the check cannot see enough to say any of them. So the
sentences were removed rather than reworded.

What is left is a list of observations, each one established by a specific,
named thing:

* what the Player's own report listed under ``tests_written``;
* which names in that report the recogniser
  ``CoachValidator._is_test_file_path`` accepted, and which of the naming
  conventions in :data:`KNOWN_TEST_CONVENTIONS` each accepted name fits;
* which names the recogniser was never run on, kept **separate** from the
  names it was run on and did not accept — "not looked at" and "looked at and
  not accepted" are different facts;
* which accepted names were found on disk, and whether disk was looked at at
  all;
* what the Coach's own independent test run recorded as its command (that run
  is pytest, so Python only);
* what the Player's report recorded under ``quality_gates``;
* what the Coach decided.

A person reads those and draws the conclusion. Nothing here draws it for
them, and no field is named in a way that draws it either.

ADVISORY — it blocks nothing
-----------------------------
By default this records and changes nothing: the turn is approved if the
Coach approves it. Setting the environment variable::

    GUARDKIT_ZERO_TEST_BLOCKING=1

makes a fired rule turn an ``approve`` verdict into ``feedback``. Accepted
values are ``1``, ``true``, ``yes`` and ``on`` (case-insensitive); anything
else, including the variable being absent, leaves the verdict alone. This
mirrors ``guardkit.orchestrator.boot_smoke_gate`` exactly, on purpose — one
shape for every advisory-first instrument here.

WHEN THE RULE IS REACHED — it differs between the two Coach paths
------------------------------------------------------------------
The *detection* is identical: the same method, the same arguments. What
differs is **how often it is reached**.

The legacy ``validate()`` runs the rule as step 5, after the acceptance
criteria have been confirmed met; a turn that fails its acceptance criteria
returns feedback earlier and the rule never runs. ``gather_evidence`` has no
such early return, so the rule is run at the complete-gathering path whether
or not the acceptance criteria were met. The record therefore stores what the
acceptance-criteria verdict was, so a reader can tell the two apart.

Both paths share two earlier exits: a dishonest report and a failed quality
gate both stop gathering before the rule, on both paths.

WHERE THE RECORD GOES
---------------------
Every fired rule writes two things:

* a per-turn record beside the Coach's own verdict, at
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
the other side.

An earlier version wrote the ledger to ``<repo root>/.guardkit/zero-test/
queue.jsonl``. That path is in-tree and untracked, so ``git clean -fdx``
deletes it. It now lives under :data:`ZERO_TEST_HOME`, overridable with
``GUARDKIT_ZERO_TEST_ROOT`` (chiefly so tests need no home directory). Any
ledger still sitting at the old in-tree path is still **read**; nothing is
ever written there again.

CONCURRENT BUILDS — the append is serialised
---------------------------------------------
This estate runs many autobuild worktrees against one repository at once
(eleven were live when this was written), and they all append to the one
ledger for that repository. Two builds finishing a turn at the same moment
must not produce one spliced, unparseable line — a dropped row is a silently
wrong record.

Appending in text mode with ``open(path, "a")`` already sets ``O_APPEND``,
and for a small record that is usually enough on a local Linux filesystem. It
stops being enough when a record is large enough to be flushed in several
pieces, when the kernel returns a short write, or when the ledger sits on a
network filesystem, where ``O_APPEND`` carries no atomicity guarantee at all.

So this does not rely on that. Every append opens the ledger ``O_APPEND``,
takes an exclusive ``fcntl.flock`` (the estate's existing cross-process
pattern — see ``guardkit/orchestrator/worktree_checkpoints.py``), and writes
the whole line with ``os.write``, looping until every byte is out. On a
platform without ``fcntl`` the append still happens, unlocked.

READING IT
----------
::

    guardkit autobuild zero-test-report

Both the writing side and the reading side resolve the repository through
:func:`resolve_repo_root`, so a report run from a subdirectory reads the file
a build wrote rather than looking somewhere nothing was ever written.

Neither write can ever break a build: every failure swallows to a warning.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

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
    "RECOGNISER",
    "KNOWN_TEST_CONVENTIONS",
    "CONVENTION_LABELS",
    "FIELD_PROVENANCE",
    "OBSERVATION_COUNTS",
    "NOT_RECORDED",
    "conventions_matching",
    "blocking_requested",
    "resolve_repo_root",
    "ledger_path_for",
    "legacy_ledger_path_for",
    "evaluate_zero_test",
    "build_record",
    "write_record",
    "observation_lines",
    "render_observation",
    "LedgerRead",
    "read_ledger",
    "read_rows",
]

#: Environment variable that turns a fired rule from a record into a block.
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

#: The per-turn record, written beside ``coach_turn_{turn}.json`` inside the
#: build's own worktree.
ZERO_TEST_RECEIPT = ".guardkit/autobuild/{task_id}/zero_test_turn_{turn}.json"

#: The issue category the legacy rule already uses. Kept identical so the two
#: paths are greppable as one thing.
ANOMALY_CATEGORY = "zero_test_anomaly"

#: The name of the thing that decides whether a file name is accepted. Stored
#: on every row, so a reader is never left guessing what "matched" meant.
RECOGNISER = "CoachValidator._is_test_file_path"


def _name_of(path: str) -> str:
    return Path(path).name


#: The file-naming conventions ``CoachValidator._is_test_file_path`` accepts,
#: each as (label, example file name, predicate over (name, path parts)).
#:
#: The **decision** about a file is always taken by the recogniser itself, never
#: by these predicates. They exist only to say WHICH convention an accepted
#: name fits, so a row can record that rather than a bare "matched". When they
#: disagree with the recogniser — a name it accepts that none of them explains —
#: the row says the convention was not identified, which is still a fact.
#:
#: ``tests/orchestrator/test_zero_test_gate.py`` runs every example below
#: through the real recogniser, so this table cannot drift into claiming the
#: recogniser accepts something it does not.
KNOWN_TEST_CONVENTIONS: Tuple[Tuple[str, str, Callable[[str, Tuple[str, ...]], bool]], ...] = (
    (
        "test_*.py",
        "tests/test_widget.py",
        lambda name, parts: name.startswith("test_") and name.endswith(".py"),
    ),
    ("*_test.py", "tests/widget_test.py", lambda name, parts: name.endswith("_test.py")),
    ("*_test.go", "widget_test.go", lambda name, parts: name.endswith("_test.go")),
    (
        "*.test.ts / *.test.js",
        "src/widget.test.ts",
        lambda name, parts: name.endswith(".test.ts") or name.endswith(".test.js"),
    ),
    (
        "*.spec.ts / *.spec.js",
        "src/widget.spec.js",
        lambda name, parts: name.endswith(".spec.ts") or name.endswith(".spec.js"),
    ),
    (
        "*.cs under a Tests/ directory",
        "Tests/WidgetTests.cs",
        lambda name, parts: name.endswith(".cs") and "Tests" in parts,
    ),
)

#: Just the labels from :data:`KNOWN_TEST_CONVENTIONS`, in order.
CONVENTION_LABELS: Tuple[str, ...] = tuple(
    label for label, _example, _predicate in KNOWN_TEST_CONVENTIONS
)

#: What a row says when the recogniser accepted a name but no convention in
#: the table above explains it.
CONVENTION_UNIDENTIFIED = "(convention not identified)"


def conventions_matching(path: str) -> List[str]:
    """Which of :data:`CONVENTION_LABELS` the given file name fits.

    Attribution only. It never decides whether a file is a test — that is the
    recogniser's job — and an empty list from a name the recogniser accepted
    is recorded as :data:`CONVENTION_UNIDENTIFIED`, not as a rejection.
    """
    try:
        parts = Path(path).parts
        name = _name_of(path)
    except Exception:  # noqa: BLE001 — an odd path must not break recording
        return []
    matched: List[str] = []
    for label, _example, predicate in KNOWN_TEST_CONVENTIONS:
        try:
            if predicate(name, parts):
                matched.append(label)
        except Exception:  # noqa: BLE001
            continue
    return matched


def blocking_requested(env: Optional[Mapping[str, str]] = None) -> bool:
    """Has the operator asked a fired rule to change the verdict?

    Reads :data:`BLOCKING_ENV_VAR`. Absent or unrecognised means no. Same
    contract as ``boot_smoke_gate.blocking_requested``.
    """
    source = os.environ if env is None else env
    return str(source.get(BLOCKING_ENV_VAR, "")).strip().lower() in _TRUTHY


def _main_worktree_of(git_link: Path) -> Optional[Path]:
    """The main checkout behind a linked git worktree, or ``None``.

    A linked worktree (anything made by ``git worktree add``) has a ``.git``
    **file**, not a directory, holding one line::

        gitdir: /path/to/main-checkout/.git/worktrees/<name>

    The main checkout is the part before ``/.git/worktrees/``.
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
    while the report keyed its lookup by whatever directory the person
    happened to be standing in. Run the report one level down and it looked in
    a directory that had never been written to and found nothing.

    The answer, in order:

    1. **An autobuild worktree** lives at
       ``<repo>/.guardkit/worktrees/<task or feature id>/...``. Its rows
       belong to ``<repo>``. This is the same strip
       ``AgentInvoker._resolve_repo_root`` performs.
    2. **Any other checkout**: the nearest enclosing directory holding a
       ``.git``. When that ``.git`` is a *file* — a linked ``git worktree`` —
       the main checkout behind it is used.
    3. **Nothing git-like above it**: the path itself, unchanged.

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


def ledger_path_for(repo_root: Any, env: Optional[Mapping[str, str]] = None) -> Path:
    """The durable ledger file for one repository. Outside every worktree.

    ``~/.guardkit/zero-test/<repo name>/queue.jsonl`` by default;
    ``$GUARDKIT_ZERO_TEST_ROOT/<repo name>/queue.jsonl`` when that variable is
    set. ``repo_root`` may be any path inside the repository: it is put
    through :func:`resolve_repo_root` first, so a reader standing in a
    subdirectory and a build writing from its worktree land on the same file
    **by construction** rather than by both remembering to resolve.
    """
    source = os.environ if env is None else env
    configured = str(source.get(ZERO_TEST_ROOT_ENV_VAR, "") or "").strip()
    home = Path(configured) if configured else ZERO_TEST_HOME
    return home / resolve_repo_root(repo_root).name / ZERO_TEST_QUEUE_FILENAME


def legacy_ledger_path_for(repo_root: Any) -> Path:
    """The old in-tree ledger path. Read for continuity; never written."""
    return resolve_repo_root(repo_root) / LEGACY_IN_TREE_QUEUE


def _string_list(value: Any) -> List[str]:
    """Coerce a Player-reported file list to a list of strings; never raise."""
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, (str, Path))]


def evaluate_zero_test(
    validator: Any,
    *,
    task_work_results: Dict[str, Any],
    profile: Any,
    independent_tests: Any = None,
    task_id: Optional[str] = None,
    requirements: Any = None,
) -> Dict[str, Any]:
    """Run the legacy zero-test rule and write down what was observed.

    The detection itself is **not** implemented here. It is delegated to
    ``validator._check_zero_test_anomaly(...)`` — the same method the legacy
    Coach calls, with the same arguments — so the two paths cannot drift.

    Everything else in the returned dict is an observation. The ones a reader
    is shown are listed in :data:`FIELD_PROVENANCE`, each paired with a
    statement of how it was established, and the report prints those
    statements alongside the values. Nothing here concludes anything from the
    observations.

    Never raises. If the rule itself blows up, the result records that fact
    with ``rule_fired`` false and ``rule_error`` set — an instrument that
    cannot report must not manufacture one.

    Returns
    -------
    dict
        Always a dict, never ``None``. ``rule_fired`` is the only key a caller
        must branch on.
    """
    files_created = _string_list(task_work_results.get("files_created"))
    files_modified = _string_list(task_work_results.get("files_modified"))
    tests_written = _string_list(task_work_results.get("tests_written"))

    is_test_path = getattr(validator, "_is_test_file_path", None)
    worktree_path = getattr(validator, "worktree_path", None)

    # THE RECOGNITION PASS. Three outcomes per file name, kept apart, because
    # collapsing the third into the second is exactly how this instrument came
    # to state a falsehood: "the recogniser did not accept it" and "the
    # recogniser never looked at it" are different facts.
    matching: List[Dict[str, Any]] = []
    examined: List[str] = []
    not_examined: List[str] = []
    recogniser_available = callable(is_test_path)
    seen: List[str] = []
    for candidate in [*tests_written, *files_created, *files_modified]:
        if candidate in seen:
            continue
        seen.append(candidate)
        if not recogniser_available:
            not_examined.append(candidate)
            continue
        try:
            accepted = bool(is_test_path(candidate))
        except Exception:  # noqa: BLE001 — a heuristic must never break gathering
            not_examined.append(candidate)
            continue
        examined.append(candidate)
        if accepted:
            matching.append(
                {
                    "name": candidate,
                    "conventions": conventions_matching(candidate)
                    or [CONVENTION_UNIDENTIFIED],
                }
            )

    # Whether an accepted name is actually THERE. Only answerable when the
    # validator carries a worktree path; when it does not, the record says the
    # lookup did not happen rather than saying the file is absent.
    disk_lookup_performed = worktree_path is not None
    on_disk: List[str] = []
    if disk_lookup_performed:
        for entry in matching:
            try:
                if (Path(worktree_path) / entry["name"]).exists():
                    on_disk.append(entry["name"])
            except Exception:  # noqa: BLE001 — an odd path must not break gathering
                continue

    quality_gates = task_work_results.get("quality_gates")
    if not isinstance(quality_gates, dict):
        quality_gates = {}

    observation: Dict[str, Any] = {
        "rule": "CoachValidator._check_zero_test_anomaly",
        "rule_fired": False,
        "rule_severity": None,
        "rule_error": None,
        "category": ANOMALY_CATEGORY,
        "report_tests_written": tests_written,
        "report_files_created": files_created,
        "report_files_modified": files_modified,
        "recogniser": RECOGNISER,
        "recogniser_available": recogniser_available,
        "recogniser_conventions": list(CONVENTION_LABELS),
        "names_matching_a_convention": matching,
        "names_examined_by_recogniser": examined,
        "names_not_examined_by_recogniser": not_examined,
        "disk_lookup_performed": disk_lookup_performed,
        "matching_names_found_on_disk": on_disk,
        "independent_test_run_command": getattr(
            independent_tests, "test_command", None
        ),
        "report_quality_gates_all_passed": quality_gates.get("all_passed"),
        "report_quality_gates_tests_passed": quality_gates.get("tests_passed"),
        "report_quality_gates_coverage": quality_gates.get("coverage"),
        "report_requirements_all_criteria_met": _criteria_met(requirements),
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
            "zero_test_gate: %s raised %s for %s — recorded as not fired.",
            observation["rule"],
            exc.__class__.__name__,
            task_id,
        )
        observation["rule_error"] = f"{exc.__class__.__name__}: {exc}"
        return observation

    if not issues:
        return observation

    first = issues[0] if isinstance(issues[0], dict) else {}
    observation["rule_fired"] = True
    observation["rule_severity"] = first.get("severity")
    return observation


def _criteria_met(requirements: Any) -> Optional[bool]:
    """``True``/``False`` when the acceptance-criteria verdict is known, else None."""
    if requirements is None:
        return None
    value = getattr(requirements, "all_criteria_met", None)
    return bool(value) if isinstance(value, bool) else None


# ===========================================================================
# Rendering — one label set, used by the report AND by the record itself
# ===========================================================================

LABEL_TESTS_WRITTEN = "report: tests_written"
LABEL_FILES_CREATED = "report: files_created"
LABEL_FILES_MODIFIED = "report: files_modified"
LABEL_MATCHING = "names matching a convention"
LABEL_EXAMINED = "names put to the recogniser"
LABEL_NOT_EXAMINED = "names not put to the recogniser"
LABEL_ON_DISK = "matching names found on disk"
LABEL_INDEPENDENT_RUN = "independent test run"
LABEL_QUALITY_GATES = "report: quality_gates"
LABEL_CRITERIA = "report: acceptance criteria"
LABEL_SEVERITY = "severity returned by the rule"
LABEL_DECISION = "Coach decision recorded"

#: For every field a row shows, **how that field was established**. Printed by
#: ``guardkit autobuild zero-test-report`` above the rows, so a reader never
#: has to guess what a value means or how far it reaches.
FIELD_PROVENANCE: Tuple[Tuple[str, str], ...] = (
    (
        LABEL_TESTS_WRITTEN,
        "copied from the Player's own report for the turn "
        "(task_work_results.json, key \"tests_written\"). It is what the "
        "Player listed, not a scan of the working tree.",
    ),
    (
        LABEL_FILES_CREATED,
        "copied from the same report, key \"files_created\".",
    ),
    (
        LABEL_FILES_MODIFIED,
        "copied from the same report, key \"files_modified\".",
    ),
    (
        LABEL_MATCHING,
        "every name in the three lists above was passed to "
        f"{RECOGNISER}; these are the names it accepted. The bracketed label "
        "is which of the conventions it knows the name fits: "
        + ", ".join(CONVENTION_LABELS)
        + ".",
    ),
    (
        LABEL_EXAMINED,
        f"the names {RECOGNISER} was actually run on and returned an answer "
        "for.",
    ),
    (
        LABEL_NOT_EXAMINED,
        "names the recogniser was not run on, or raised on: nothing is "
        "recorded about them either way. Kept apart from the names above on "
        "purpose.",
    ),
    (
        LABEL_ON_DISK,
        "each matching name was looked for at <worktree>/<name>. Shows "
        "\"not looked for\" when the record was written without a worktree "
        "path to look in.",
    ),
    (
        LABEL_INDEPENDENT_RUN,
        "the test_command field of the Coach's own independent test run for "
        "the turn. That run is pytest, so it reports on Python tests it is "
        "able to collect and on nothing else.",
    ),
    (
        LABEL_QUALITY_GATES,
        "copied from the Player's report, key \"quality_gates\" — the "
        "Player's claim about its own run, as recorded.",
    ),
    (
        LABEL_CRITERIA,
        "the all_criteria_met field of the Coach's acceptance-criteria "
        "validation for the turn, where one was recorded.",
    ),
    (
        LABEL_SEVERITY,
        "the severity string on the issue CoachValidator."
        "_check_zero_test_anomaly returned. It is \"error\" or \"warning\" "
        "according to the task type's profile.",
    ),
    (
        LABEL_DECISION,
        "the decision field of the Coach's verdict for the turn, read at the "
        "moment the row was written.",
    ),
)


def _render_list(names: Sequence[Any], limit: int = 8) -> str:
    """``a, b, c`` — or ``(none)``, or a bounded listing naming what it cut."""
    items = [str(name) for name in names]
    if not items:
        return "(none)"
    if len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f", +{len(items) - limit} more (--json shows all)"


def _render_matching(entries: Any) -> str:
    """``path [convention]`` per accepted name."""
    if not isinstance(entries, (list, tuple)) or not entries:
        return "(none)"
    rendered = []
    for entry in entries:
        if isinstance(entry, Mapping):
            conventions = entry.get("conventions") or []
            label = ", ".join(str(c) for c in conventions) or CONVENTION_UNIDENTIFIED
            rendered.append(f"{entry.get('name')} [{label}]")
        else:  # a row written by something that stored bare names
            rendered.append(str(entry))
    return _render_list(rendered)


#: What a line shows when the row does not carry that field at all. It is a
#: different thing from ``(none)``, which means the field IS there and is
#: empty — the row observed something, and what it observed was nothing.
#: Printing a row written under an older shape as ``(none)`` would state an
#: observation nothing ever made.
NOT_RECORDED = "(not recorded)"


def _render_value(value: Any) -> str:
    return NOT_RECORDED if value is None else repr(value)


def _list_field(row: Mapping[str, Any], key: str) -> str:
    """A recorded list, or :data:`NOT_RECORDED` when the row has no such key."""
    if key not in row:
        return NOT_RECORDED
    return _render_list(row.get(key) or [])


def observation_lines(row: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """One ``(label, value)`` pair per observed field, in reading order.

    The labels are exactly the ones :data:`FIELD_PROVENANCE` explains, so a
    reader can put any line of a row against the statement of how it was
    established.

    A field the row does not carry renders as :data:`NOT_RECORDED`, kept
    distinct from ``(none)``. The two say different things — "nothing was
    written down here" against "this was looked at and came back empty" — and
    a row written under an older shape must not be read as the second.
    """
    if row.get("disk_lookup_performed") is False:
        on_disk = "not looked for (no worktree path was recorded)"
    else:
        on_disk = _list_field(row, "matching_names_found_on_disk")
    gate_keys = (
        "report_quality_gates_all_passed",
        "report_quality_gates_tests_passed",
        "report_quality_gates_coverage",
    )
    if any(key in row for key in gate_keys):
        gates = (
            f"all_passed={row.get(gate_keys[0])!r}, "
            f"tests_passed={row.get(gate_keys[1])!r}, "
            f"coverage={row.get(gate_keys[2])!r}"
        )
    else:
        gates = NOT_RECORDED
    if "names_matching_a_convention" not in row:
        matching = NOT_RECORDED
    else:
        matching = _render_matching(row.get("names_matching_a_convention"))
    return [
        (LABEL_TESTS_WRITTEN, _list_field(row, "report_tests_written")),
        (LABEL_FILES_CREATED, _list_field(row, "report_files_created")),
        (LABEL_FILES_MODIFIED, _list_field(row, "report_files_modified")),
        (LABEL_MATCHING, matching),
        (LABEL_EXAMINED, _list_field(row, "names_examined_by_recogniser")),
        (LABEL_NOT_EXAMINED, _list_field(row, "names_not_examined_by_recogniser")),
        (LABEL_ON_DISK, on_disk),
        (
            LABEL_INDEPENDENT_RUN,
            _render_value(row.get("independent_test_run_command")),
        ),
        (LABEL_QUALITY_GATES, gates),
        (
            LABEL_CRITERIA,
            _render_value(row.get("report_requirements_all_criteria_met")),
        ),
        (LABEL_SEVERITY, _render_value(row.get("rule_severity"))),
        (LABEL_DECISION, _render_value(row.get("coach_decision"))),
    ]


def render_observation(row: Mapping[str, Any]) -> str:
    """The ``(label, value)`` pairs as plain text, one per line.

    Used where there is no console to draw with — the message handed back to
    the Player when :data:`BLOCKING_ENV_VAR` is set.
    """
    return "\n".join(f"  {label}: {value}" for label, value in observation_lines(row))


def _recorded_and_empty(row: Mapping[str, Any], key: str) -> bool:
    """The row carries ``key`` AND what it carries is empty.

    The two halves are both required. A row written under an older shape has
    no such key, and counting it as "empty" would put it in a total that
    claims something was looked at and came back with nothing. Nothing was
    looked at; there is no row here to count either way.
    """
    return key in row and not row[key]


#: Counts the report prints. Each heading names the observation counted, in
#: terms of what was looked at — never in terms of what a build did. A count
#: of facts is a fact; a count called "turns with no test" would not be.
#:
#: Every predicate is FALSE for a row that does not carry the field it asks
#: about, so an old or partial row is left out of that total rather than
#: guessed into it.
OBSERVATION_COUNTS: Tuple[Tuple[str, Callable[[Mapping[str, Any]], bool]], ...] = (
    (
        "the report's tests_written list was recorded and was empty",
        lambda row: _recorded_and_empty(row, "report_tests_written"),
    ),
    (
        f"no name in the report was accepted by {RECOGNISER}",
        lambda row: _recorded_and_empty(row, "names_matching_a_convention"),
    ),
    (
        f"at least one name in the report was accepted by {RECOGNISER}",
        lambda row: bool(row.get("names_matching_a_convention")),
    ),
    (
        f"at least one name accepted by {RECOGNISER} was found on disk",
        lambda row: bool(row.get("matching_names_found_on_disk")),
    ),
    (
        "at least one name was not put to the recogniser at all",
        lambda row: bool(row.get("names_not_examined_by_recogniser")),
    ),
    (
        'the independent test run recorded test_command "skipped"',
        lambda row: row.get("independent_test_run_command") == "skipped",
    ),
    (
        "the report recorded quality_gates.all_passed true with a "
        "tests_passed value the rule reads as zero",
        lambda row: row.get("report_quality_gates_all_passed") is True
        and _recorded_and_empty(row, "report_quality_gates_tests_passed"),
    ),
    (
        'the Coach decision recorded was "approve"',
        lambda row: row.get("coach_decision") == "approve",
    ),
    (
        f"the recorded decision was changed by this instrument "
        f"({BLOCKING_ENV_VAR} was set)",
        lambda row: bool(row.get("decision_changed_by_this_instrument")),
    ),
)


def build_record(
    *,
    observation: Mapping[str, Any],
    task_id: str,
    turn: int,
    worktree_dir: Optional[str],
    repo: Optional[str],
    repo_path: Optional[str],
    coach_decision: Optional[str],
    blocking_env_var_set: bool,
    decision_changed: bool,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the durable row for one fired rule.

    Everything from the observation, plus which build it came from, when, what
    the Coach decided, and whether this instrument changed that decision. No
    field summarises, labels or scores the row: a reader gets the observations
    and draws their own conclusion.
    """
    # The observation goes down first and the identity on top of it, so a
    # malformed observation carrying a key like "task_id" cannot rewrite which
    # build the row belongs to.
    record = dict(observation)
    record.update(
        {
            "schema": "zero_test_observation/1",
            "recorded_at": now or datetime.now(timezone.utc).isoformat(),
            "repo": repo,
            "repo_path": repo_path,
            "worktree_dir": worktree_dir,
            "task_id": task_id,
            "turn": turn,
            "coach_decision": coach_decision,
            "blocking_env_var": BLOCKING_ENV_VAR,
            "blocking_env_var_set": bool(blocking_env_var_set),
            "decision_changed_by_this_instrument": bool(decision_changed),
        }
    )
    return record


def _append_line_atomically(path: Path, line: str) -> None:
    """Append one whole line to a JSON-lines file without interleaving.

    Many autobuild worktrees append to one ledger concurrently. Two builds
    that finish a turn together must not splice their lines together, so the
    file is opened ``O_APPEND``, an exclusive ``fcntl.flock`` serialises the
    writers, and the whole line goes out in one looping ``os.write``. A
    platform with no ``fcntl`` still appends, unlocked.
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


def write_record(
    record: Dict[str, Any],
    *,
    worktree_path: Path,
    repo_root: Optional[Path] = None,
    task_id: str,
    turn: int,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Write the per-turn record and append the durable ledger line.

    Mirrors ``qav_shadow._write_receipt``: the two writes are independent, and
    **neither can ever break a build** — a failure swallows to a warning.

    ``repo_root`` names the repository the ledger belongs to. When it is
    ``None`` (the build is running directly in the repository rather than in a
    worktree) the worktree path is the repository. The ledger itself is
    written OUTSIDE that repository — see the module docstring and D-OBS-4.

    Returns the per-turn record path, or ``None`` when that write failed.
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
            "zero_test_gate: unwritable record %s (%r) — dropped", receipt_path, exc
        )
        receipt_path = None

    ledger_owner = Path(repo_root) if repo_root is not None else Path(worktree_path)
    ledger_path = ledger_path_for(ledger_owner, env)
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        _append_line_atomically(ledger_path, json.dumps(record, sort_keys=True) + "\n")
    except OSError as exc:
        logger.warning(
            "zero_test_gate: unwritable ledger %s (%r) — row dropped", ledger_path, exc
        )
    return receipt_path


def _read_jsonl(ledger_path: Path) -> List[Dict[str, Any]]:
    """Every JSON object in one ledger file, oldest first. Missing file → []."""
    if not ledger_path.is_file():
        return []

    rows: List[Dict[str, Any]] = []
    try:
        raw_lines: Sequence[str] = ledger_path.read_text(encoding="utf-8").splitlines()
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


@dataclass(frozen=True)
class LedgerRead:
    """One repository's rows, **and where they were looked for**.

    The second half is not decoration. ``rows == []`` has two completely
    different causes — no ledger file exists at the resolved location, or a
    ledger exists and is empty — and the caller is handed both so it never
    prints one as the other.
    """

    repo_root: Path
    ledger_path: Path
    legacy_path: Path
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


def read_ledger(repo_root: Any, env: Optional[Mapping[str, str]] = None) -> LedgerRead:
    """Read one repository's rows and report where they were read from.

    ``repo_root`` may be any path inside the repository — it goes through
    :func:`resolve_repo_root`, the same function the writing side goes
    through, so a report run from a subdirectory reads the file a build wrote.

    Reads the durable ledger, then any rows still sitting at the old in-tree
    path so that nothing recorded before the move is dropped. A malformed line
    is skipped with a warning rather than aborting the read.
    """
    resolved = resolve_repo_root(repo_root)
    ledger = ledger_path_for(resolved, env)
    legacy = legacy_ledger_path_for(resolved)

    rows = _read_jsonl(ledger)
    rows.extend(_read_jsonl(legacy))

    return LedgerRead(
        repo_root=resolved,
        ledger_path=ledger,
        legacy_path=legacy,
        ledger_exists=ledger.is_file(),
        legacy_exists=legacy.is_file(),
        rows=rows,
    )


def read_rows(repo_root: Any, env: Optional[Mapping[str, str]] = None) -> List[Dict[str, Any]]:
    """One repository's rows, in the order they were read.

    Thin wrapper over :func:`read_ledger` for callers that only want the rows.
    Anything that prints must use :func:`read_ledger` instead and check
    :attr:`LedgerRead.any_ledger_file`, so that "found nothing" is never
    printed as "nothing to find".
    """
    return read_ledger(repo_root, env).rows
