"""Say out loud, at the end of every run, which checks did not run.

WHY THIS EXISTS, in plain words
-------------------------------
A green tick is supposed to mean "everything was checked and everything was
fine". In this suite it did not. On 2026-08-23, 1,390 of the 17,077 checks this
suite collects stepped aside and the run still ended with a clean summary line and exit
code 0-for-the-parts-that-ran. Nothing in the output said what had stood down,
so nobody could tell the difference between "this works" and "nobody looked".

That gap hid a real defect. ``select_harness`` grew a required ``cwd=``
argument; its test was never updated; the test file stands down whenever the
``guardkitfactory`` package is absent, which is exactly the state of the CI
runner. The test failed on every developer machine and CI could never see it.
It was fixed on 2026-08-23 (guardkit ``e96d41dc``) after living in that gap for
roughly eleven weeks.

Rich's words, which are the brief for this module: "I don't like skipping
things and leaving them for later because they get forgotten."

WHAT THIS MODULE DOES, AND WHAT IT DELIBERATELY DOES NOT DO
------------------------------------------------------------
It DOES: collect every skip in the session, sort it into categories that were
established by measuring this suite (not invented), and print a report at the
very end of the output.

It does NOT gate. **The exit code is never touched.** There is no
``pytest_sessionfinish`` here and nothing anywhere in this file assigns to
``session.exitstatus``. A run that skips 1,390 checks and passes the rest still
exits 0, exactly as before.

That is a deliberate difference from the sibling rule in fleet-evals
(``fleet-evals/harness/could_not_measure.py``), where a skip makes the run FAIL
with exit code 40. That rule is right THERE, because there a skip means a
graded exam axis could not be measured and the grade is not a result. It would
be wrong HERE. This suite skips legitimately and in bulk: a documented
quarantine of 345 known-red tests, a whole integration tree behind an opt-in
command-line flag, platform and optional-dependency gates. Turning those into
failures would make the merge gate permanently red, and a permanently red gate
teaches everyone to ignore it. Rich asked for things not to be FORGOTTEN. Here
that is a reporting problem, not a gating one.

If a subset of these should one day gate, that is a decision for Rich to take
explicitly, not something this module should do quietly. The recommendation is
recorded in the lane report, not implemented here.

THE CATEGORIES, AND HOW EACH IS RECOGNISED
-------------------------------------------
The four categories below are the ones that ACTUALLY OCCUR in this suite,
measured on a full run on 2026-08-23 (1,390 skips). No category was invented
for a case that does not happen here.

1. A WHOLE TEST FILE STOOD DOWN BECAUSE A PACKAGE IS NOT INSTALLED.
   Recognised by: pytest reported the skip during COLLECTION (so it is the
   whole file, not one test) and the reason begins with pytest's own
   ``importorskip`` wording, "could not import ...".
   Measured on this box: 5 files — 4 waiting on ``claude_agent_sdk``, 1 on
   ``fastapi``. Twenty test files in this suite carry a module-level
   ``importorskip``; the other fifteen found what they wanted here. On a CI
   runner, which installs only the ``dev`` extra, more of the twenty stand
   down — that is INFERRED from the extras CI installs, not measured, because
   this lane cannot run CI.
   THIS IS THE DANGEROUS KIND. The file is never read, so nothing in it can
   fail, so a green tick says nothing whatsoever about it. This is the category
   that hid the ``cwd=`` defect, and it is printed first and in full.

2. A WHOLE TEST FILE STOOD DOWN FOR A RECORDED DECISION.
   Recognised by: skipped during collection, any other reason. In practice this
   is ``pytest.skip(..., allow_module_level=True)`` with a written explanation.
   Measured here: 6 files, all carrying the "R1 de-wire (Rich 08-14)" note.

3. A TEST WAS QUARANTINED AS A KNOWN FAILURE.
   Recognised by: the skip reason names ``quarantine.txt``, which is the reason
   string ``tests/conftest.py`` attaches when it applies the quarantine list.
   Measured here: 345 tests — exactly the 345 entries in
   ``tests/quarantine.txt``, which is how that rule was checked.
   These are a recorded decision with a burn-down list, so the report gives the
   count and points at the file rather than reprinting 345 node ids.

4. AN ORDINARY SKIP INSIDE A SINGLE TEST.
   Everything else: ``skipif`` markers, ``pytest.skip()`` in a test body or a
   fixture, an opt-in command-line flag that was not passed, a sibling checkout
   that is not on this machine, an optional import inside a test.
   Measured here: 1,034 tests across 21 distinct reasons. The largest single
   reason is 933 tests behind the ``--run-integration`` flag.

A NOTE ON HOW FRAGILE THAT CLASSIFICATION IS, said honestly
------------------------------------------------------------
pytest does not record WHY something was skipped in any structured form — only
a free-text reason. Categories 1 and 3 are therefore matched on the text of
that reason. If pytest reworded ``importorskip``, or if the quarantine reason
string were rewritten, an item would land in a different bucket.

The failure mode is deliberately safe: a misclassified skip is still COUNTED
and still PRINTED. It moves between headings; it never disappears. Both text
rules are pinned by tests in ``tests/unit/test_skip_report.py`` so a reword
fails a test instead of silently degrading the report.

WHY IT PRINTS FROM ``pytest_unconfigure``
------------------------------------------
Because that is the only hook whose output is genuinely last, and being last is
the whole point.

The obvious hook, ``pytest_terminal_summary``, is NOT last: pytest's own
terminal reporter prints the ``FAILED ...`` short summary lines and then the
final ``N failed, N passed`` stats line AFTER every plugin's terminal-summary
hook has run. Measured on a small run: a line written from
``pytest_terminal_summary`` landed 202 characters from the end of stdout, while
the same line written from ``pytest_unconfigure`` landed 19 characters from the
end. On a run with many failures the short-summary block grows without limit
and pushes a terminal-summary block further and further from the end.

That matters because tools in this estate keep only the TAIL of a run's output
— both fleet-evals runners save ``proc.stdout[-4000:]`` into the receipt. The
earlier version of this same idea printed from ``pytest_sessionfinish``, landed
at character 153 of stdout, and was truncated out of every saved receipt: a
guard that was invisible in exactly the artefact people read. This block is
kept under 4,000 characters and printed from ``pytest_unconfigure``, which was
measured to fire and reach real stdout from a conftest under all four capture
modes (fd, sys, tee-sys, and -s).

TURNING IT OFF, AND TURNING IT ALL THE WAY UP
----------------------------------------------
``GUARDKIT_SKIP_REPORT=off`` prints nothing at all. ``GUARDKIT_SKIP_REPORT=full``
prints every file and every reason with no budget trimming, for when someone is
actually working through the list. Nothing else switches it off, and it is
silent anyway on a run with no skips — silence when there is nothing to say.

``pytest -rs`` remains the way to see the individual test names behind a count;
this report deliberately does not reprint 1,390 node ids.
"""
from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Categories. The order here is the order they print: most dangerous first.
# ---------------------------------------------------------------------------
FILE_PACKAGE_ABSENT = "file_package_absent"
FILE_DECISION = "file_decision"
QUARANTINED = "quarantined"
ORDINARY = "ordinary"

CATEGORY_ORDER = (FILE_PACKAGE_ABSENT, FILE_DECISION, QUARANTINED, ORDINARY)

#: What to call each category, and what to call one of its members.
CATEGORY_HEADINGS = {
    FILE_PACKAGE_ABSENT: "WHOLE FILES SKIPPED — a package they need is not installed",
    FILE_DECISION: "WHOLE FILES SKIPPED — by a decision written into the file",
    QUARANTINED: "TESTS HELD BACK as known failures (the quarantine list)",
    ORDINARY: "SINGLE TESTS THAT STEPPED ASIDE, grouped by the reason given",
}

CATEGORY_NOUNS = {
    FILE_PACKAGE_ABSENT: ("file", "files"),
    FILE_DECISION: ("file", "files"),
    QUARANTINED: ("test", "tests"),
    ORDINARY: ("test", "tests"),
}

#: pytest's own wording when ``pytest.importorskip("x")`` cannot import "x".
#: Pinned by ``tests/unit/test_skip_report.py::TestTheTextRulesAreStillTrue``,
#: which asks pytest itself rather than trusting this copy of the wording.
IMPORTORSKIP_PREFIX = "could not import"

#: The file ``tests/conftest.py`` names in the reason it attaches to every
#: quarantined test. Pinned by the same test module.
QUARANTINE_MARKER = "quarantine.txt"

# ---------------------------------------------------------------------------
# How big the printed block is allowed to be, and why there is a limit at all
# ---------------------------------------------------------------------------
# This estate's runners keep only the TAIL of a run's output — both fleet-evals
# runners save ``proc.stdout[-4000:]`` into the receipt. A report longer than
# that window is half-truncated in the artefact people actually read, which is
# exactly how the previous attempt at this idea was lost.
#
# Measured on the full guardkit suite (1,390 skips, 2026-08-23): the first draft
# of this block was 4,716 characters, so its headline and its most important
# section fell outside the window. So the block is now FITTED to a budget rather
# than hoped to be short enough: `build_report_lines` retries with progressively
# shorter lists until it fits. The detail dropped is always the least important
# first — the tail of the "ordinary skips" list before anything else, and the
# list of whole skipped FILES last of all.
#
# The final two lines are a one-line restatement of every count, so even a brutal
# truncation leaves a reader the totals.
TAIL_BUDGET_CHARS = 3800

#: (whole files listed, distinct ordinary reasons listed), tried in order until
#: the block fits the budget. Reasons are given up before files, because a file
#: that never ran at all is the category that hid a real defect for weeks.
_SIZE_LADDER = (
    (40, 40), (40, 22), (30, 16), (20, 12), (14, 8), (10, 5), (6, 2), (0, 0),
)

_REASON_CHARS = 88
_RULE = "=" * 78


class _Skip:
    """One skipped thing: what it was, and the reason it gave."""

    __slots__ = ("nodeid", "reason", "category")

    def __init__(self, nodeid: str, reason: str, category: str) -> None:
        self.nodeid = nodeid
        self.reason = reason
        self.category = category


#: nodeid -> _Skip, for the session in progress. Module state, so it is cleared
#: at the start of every session: two ``pytest.main()`` calls in one process
#: would otherwise let session one's skips be reported against session two.
_skips: "dict[str, _Skip]" = {}


def _reason_of(report) -> str:
    """Pull the human reason out of a report, whatever shape it arrived in.

    A skip's ``longrepr`` is a ``(path, lineno, reason)`` tuple for a skip
    raised in a test, and a plain string in other cases. The reason itself
    usually arrives with pytest's ``"Skipped: "`` prefix already on it, which is
    noise in a report that is entirely about skips.
    """
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        reason = str(longrepr[2])
    elif longrepr is None:
        reason = ""
    else:
        reason = str(longrepr)
    reason = reason.strip()
    if reason.startswith("Skipped: "):
        reason = reason[len("Skipped: ") :]
    return " ".join(reason.split())


def _is_xfail(report) -> bool:
    """True for a test that was EXPECTED to fail and did.

    pytest gives an xfailed test a report whose outcome is "skipped" with a
    ``wasxfail`` attribute, and then counts it as "xfailed", not "skipped", in
    its own summary. Counting it here made this report disagree with the line
    printed directly above it — measured on the full suite as 1,391 against
    pytest's 1,390.
    """
    return hasattr(report, "wasxfail")


def _record(nodeid: str, reason: str, category: str) -> None:
    """First report for a node wins, so nothing is counted twice."""
    if nodeid not in _skips:
        _skips[nodeid] = _Skip(nodeid, reason, category)


# ---------------------------------------------------------------------------
# Collecting. Two hooks, because skips arrive by two different roads.
# ---------------------------------------------------------------------------


def pytest_sessionstart(session):
    """Forget the previous session's skips."""
    _skips.clear()


def pytest_collectreport(report):
    """Catch a WHOLE FILE standing down, which the runtest hook never sees.

    ``pytest.importorskip(...)`` and ``pytest.skip(..., allow_module_level=True)``
    at the top of a file stop the file being imported at all. pytest reports that
    as a COLLECTION result, so no test in the file ever produces a runtest report
    and the obvious hook below never fires once. This is precisely the category
    that hid a real defect for eleven weeks, so it is the one that most needs
    catching, and it is the one an author would most easily miss.
    """
    if not report.skipped:
        return
    reason = _reason_of(report)
    if reason.lower().startswith(IMPORTORSKIP_PREFIX):
        category = FILE_PACKAGE_ABSENT
    else:
        category = FILE_DECISION
    _record(report.nodeid, reason, category)


def pytest_runtest_logreport(report):
    """Catch a single test stepping aside, in setup, call or teardown."""
    if not report.skipped or _is_xfail(report):
        return
    reason = _reason_of(report)
    category = QUARANTINED if QUARANTINE_MARKER in reason else ORDINARY
    _record(report.nodeid, reason, category)


# ---------------------------------------------------------------------------
# Reporting.
# ---------------------------------------------------------------------------


def _short(text: str, limit: int = _REASON_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _count(n: int, singular: str, plural: str) -> str:
    """"1 file" / "14 files", so the report reads like English, not a dump."""
    return f"{n:,} {singular if n == 1 else plural}"


def _package_name(reason: str) -> str:
    """Pull the module name out of pytest's "could not import 'x': ..." wording.

    Falls back to the whole reason if the wording ever changes, so the files are
    still grouped under something a reader can act on rather than disappearing.
    """
    for quote in ("'", '"'):
        start = reason.find(quote)
        if start != -1:
            end = reason.find(quote, start + 1)
            if end != -1:
                return reason[start + 1 : end]
    return reason


def _by_category() -> "dict[str, list[_Skip]]":
    grouped: "dict[str, list[_Skip]]" = {name: [] for name in CATEGORY_ORDER}
    for skip in _skips.values():
        grouped.setdefault(skip.category, []).append(skip)
    return grouped


def build_report_lines() -> "list[str]":
    """Return the report as lines, fitted to the tail budget.

    Returns an empty list when nothing was skipped — silence when there is
    nothing to say.

    Separated from the printing so the tests can read it directly, and so a
    caller who wants these facts somewhere other than a terminal can have them.
    """
    if not _skips:
        return []
    if os.environ.get("GUARDKIT_SKIP_REPORT", "").lower() == "full":
        # GENUINELY unbounded. This used to return _compose(*_SIZE_LADDER[0]),
        # which is (40, 40) — hard caps — while the docstring promised "every
        # file and every reason with no budget trimming". Measured with 200
        # package-absent files and 400 reasons: 40 named, "... and 360 more
        # reasons" silently dropped. It looked correct only because today's
        # suite (11 whole files, 24 reasons) fits under both caps. `full` exists
        # for the person actually working through the list, which is exactly
        # when a silent cap is worst.
        return _compose(len(_skips) or 1, len(_skips) or 1)
    for max_files, max_reasons in _SIZE_LADDER:
        lines = _compose(max_files, max_reasons)
        if len("\n".join(lines)) <= TAIL_BUDGET_CHARS:
            return lines
    # Nothing on the ladder fitted. Return the smallest form anyway: the last
    # two lines are the totals, so a truncated receipt still carries them.
    return lines


def _compose(max_files: int, max_reasons: int) -> "list[str]":
    grouped = _by_category()
    total = len(_skips)
    out = [
        _RULE,
        f"WHAT DID NOT RUN — {_count(total, 'skip', 'skips')}, "
        + ("the one" if total == 1 else "the same ones")
        + " pytest counted above",
        "None of these failed. None of them was looked at either, so this run says",
        "nothing about whether they work. THIS IS A REPORT ONLY: it does not change",
        "the exit code, and nothing listed below turns the run red.",
    ]

    for category in CATEGORY_ORDER:
        items = grouped[category]
        if not items:
            continue
        singular, plural = CATEGORY_NOUNS[category]
        out.append("")
        out.append(
            f"{CATEGORY_HEADINGS[category]} — {_count(len(items), singular, plural)}"
        )
        out.extend(_section_lines(category, items, max_files, max_reasons))

    out.append("")
    out.append(
        "IN ONE LINE: "
        + _count(len(grouped[FILE_PACKAGE_ABSENT]), "whole file", "whole files")
        + " skipped for a missing package, "
        + f"{len(grouped[FILE_DECISION]):,} by decision,"
    )
    out.append(
        f"{len(grouped[QUARANTINED]):,} quarantined, "
        + _count(len(grouped[ORDINARY]), "single test", "single tests")
        + f" — {_count(total, 'skip', 'skips')} in total. Exit code unchanged."
    )
    out.append(_RULE)
    return out


def _section_lines(category, items, max_files, max_reasons) -> "list[str]":
    if category == FILE_PACKAGE_ABSENT:
        out = [
            "  Nothing in these files was read, so nothing in them could fail and a",
            "  green run says nothing at all about them. Install what they ask for,",
            "  or delete them.",
        ]
        out.extend(_package_group_lines(items, max_files))
        return out

    if category == FILE_DECISION:
        out = []
        listed = sorted(items, key=lambda skip: skip.nodeid)[: max(max_files, 0)]
        for item in listed:
            out.append(f"    {item.nodeid}")
            out.append(f"        {_short(item.reason or '(no reason given)')}")
        hidden = len(items) - len(listed)
        if hidden:
            out.append(
                f"    ... and {_count(hidden, 'more file', 'more files')} — "
                "pytest -rs prints them all."
            )
        return out

    if category == QUARANTINED:
        return [
            "  A recorded decision, not a surprise: every one is named in",
            "  tests/quarantine.txt and tracked for burn-down. Delete a line there to",
            "  put that test back into the gate.",
        ]

    # ORDINARY
    counts: "dict[str, int]" = {}
    for item in items:
        counts[item.reason] = counts.get(item.reason, 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    out = []
    for reason, count in ranked[:max_reasons]:
        out.append(f"  {count:>5,}  {_short(reason or '(no reason given)')}")
    hidden = len(ranked) - min(len(ranked), max_reasons)
    if hidden:
        out.append(
            f"  ... and {_count(hidden, 'more reason', 'more reasons')} — "
            "pytest -rs prints them all."
        )
    else:
        out.append("  (pytest -rs names every one of these tests individually.)")
    return out


def _package_group_lines(items, max_files) -> "list[str]":
    """Group the skipped files under the package each of them was waiting for.

    Biggest group first, because "eleven files are waiting on guardkitfactory"
    is the sentence worth reading. When the budget runs out the remainder is
    still COUNTED on one line — trimming this report never makes a skipped file
    disappear, only makes it anonymous.
    """
    groups: "dict[str, list[str]]" = {}
    for item in items:
        groups.setdefault(_package_name(item.reason), []).append(item.nodeid)
    ordered = sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))

    out: "list[str]" = []
    budget = max(max_files, 0)
    shown_files = 0
    shown_groups = 0
    for package, paths in ordered:
        if budget <= 0:
            break
        paths = sorted(paths)
        out.append(
            f"    {package} is not installed — "
            f"{_count(len(paths), 'file did not run', 'files did not run')}:"
        )
        for path in paths[:budget]:
            out.append(f"        {path}")
        listed = min(len(paths), budget)
        if len(paths) > listed:
            out.append(f"        ... and {len(paths) - listed} more.")
        budget -= listed
        shown_files += len(paths)
        shown_groups += 1

    remaining_files = len(items) - shown_files
    remaining_groups = len(ordered) - shown_groups
    if remaining_groups:
        out.append(
            f"    ... and {_count(remaining_files, 'more file', 'more files')} "
            f"waiting on {_count(remaining_groups, 'other package', 'other packages')}"
            " — pytest -rs prints them all."
        )
    return out


def pytest_unconfigure(config):
    """Print the report, LAST, and change nothing else.

    Deliberately NOT ``pytest_terminal_summary``: pytest prints its ``FAILED``
    short-summary lines and its final ``N passed`` stats line after every
    terminal-summary hook, so a block written there is not last and gets cut out
    of any tail-truncated receipt. See the module docstring for the measured
    character offsets.

    THIS FUNCTION DOES NOT TOUCH THE EXIT CODE. It cannot: ``pytest_unconfigure``
    is handed the config, not the session, and there is no ``pytest_sessionfinish``
    anywhere in this module. That is the intended design, not an oversight — see
    the module docstring for why gating would be wrong here.
    """
    if os.environ.get("GUARDKIT_SKIP_REPORT", "").lower() == "off":
        return
    lines = build_report_lines()
    if not lines:
        # Silence when there is nothing to say.
        return
    _write_without_ever_raising("\n".join(lines) + "\n")


def _write_without_ever_raising(text: str) -> None:
    """Print the block, and swallow anything that goes wrong doing it.

    This is not defensive habit, it is the exit-code promise. An exception
    raised out of ``pytest_unconfigure`` becomes an INTERNALERROR and pytest
    exits 3 — so a bug in a REPORT could turn a passing run red, which is the
    one thing this module must never do.

    The realistic failure is encoding: the block contains em dashes and an
    ellipsis, and a terminal or CI log whose encoding cannot carry them raises
    ``UnicodeEncodeError`` on write. That case is worth a second attempt in
    plain ASCII rather than losing the report; anything else is given up on.
    """
    stream = sys.stdout
    try:
        stream.write(text)
        stream.flush()
        return
    except UnicodeEncodeError:
        pass
    except Exception:
        return
    try:
        stream.write(text.encode("ascii", "replace").decode("ascii"))
        stream.flush()
    except Exception:
        return
