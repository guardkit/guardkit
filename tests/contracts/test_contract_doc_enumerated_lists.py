"""Check FOUR enumerated lists in the written contract document against the code.

WHAT THIS CHECKS — and nothing else
===================================
The specialist-agent repository holds a written contract document,
``docs/design/contracts/CONTRACT-feature-spec-plan-outputs.md``, which describes
what the ``/feature-spec`` and ``/feature-plan`` commands are supposed to emit. A
frozen exam cites that document as the authority it grades against, so when the
document drifts away from the code, the exam grades against a falsehood.

Most of that document is prose, and prose cannot be machine-checked. FOUR things
in it *are* lists of fixed values that also exist in guardkit's own source, and
this module checks exactly those four, at five places in the document:

  1. ``Feature.status``      — the allowed statuses of a feature   (6 values)
  2. ``FeatureTask.status``  — the allowed statuses of a task      (6 values)
  3. ``TaskType``            — the allowed task-type values       (11 values),
     checked at BOTH places the document states them: the canonical bullet list
     in section B.4, and the fenced block in the same section that claims to
     reproduce the validator's error message word for word.
  4. ``Feature.model_fields`` — the field names of the feature model (19 names)

The values are IMPORTED from guardkit at run time. This module deliberately
contains no second copy of any of the four lists: a hardcoded copy here would be
one more place to drift, which is the very problem being guarded against.

WHAT THIS DOES **NOT** CHECK — read this before trusting a green run
====================================================================
This is a four-list check, NOT a contract check. A green run here means those
four lists agree with the code. It means nothing whatsoever about the rest of
the document, and the document is mostly not lists.

Specifically, this check is blind to:

  * **Prose that is simply wrong.** The document described the validation
    pipeline as "two-layer" when the code runs three passes. That claim is not a
    list of values, so no version of this check could ever see it. Wrong prose
    is the largest category of defect found in this document and it remains
    entirely uncovered.
  * **Whether the values are described correctly.** The check confirms that the
    value ``awaiting_merge`` is present. It cannot tell whether the sentence
    explaining what ``awaiting_merge`` means is true.
  * **Everything in Part A** (the four-file ``/feature-spec`` output contract).
    Part A once claimed a three-file output for seven days after the code began
    enforcing four files. Nothing here would have caught that.
  * **The other enumerable lists in the document** that are not among the four —
    for example the task-type *aliases*, the ``implementation_mode`` values, and
    the ``FeatureTask`` field names. They are checkable in principle; they are
    not checked here.
  * **Whether the document exists at all**, in any environment that has not
    declared it required. See "WHERE THIS RUNS" below.

If you are reading a green light from this check and concluding "the contract
document is accurate", you are making exactly the over-reading that put eleven
stale claims into this document in the first place.

WHERE THIS RUNS
===============
The document lives in the specialist-agent repository; this code lives in
guardkit. The two are only ever side by side in one continuous-integration job:
``.github/workflows/seam-tests.yml``, whose established purpose is running checks
that need a sibling repository checked out. That job checks out specialist-agent
and sets ``GUARDKIT_CONTRACT_DOC_REQUIRED=1``.

The distinction between "checked, fine" and "could not check" is deliberate and
load-bearing:

  * ``GUARDKIT_CONTRACT_DOC_REQUIRED=1`` set (the seam job): if the document
    cannot be found, every test in this module FAILS loudly. A check that
    silently skips in the one job built to run it is invisible, and invisible
    checks are the defect this whole exercise exists to remove.
  * The variable unset (a developer's laptop, or guardkit's main ``tests.yml``
    job, which does not check out specialist-agent): the tests SKIP, with a skip
    reason naming the paths searched and the variable to set.

Set ``SPECIALIST_AGENT_PATH`` to point at a specialist-agent checkout in any
other location.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

import pytest

from guardkit.models.task_types import TaskType
from guardkit.orchestrator.feature_loader import Feature, FeatureTask

# --------------------------------------------------------------------------
# Locating the document
# --------------------------------------------------------------------------

#: Path of the contract document *inside* a specialist-agent checkout.
DOC_RELATIVE_PATH = Path("docs/design/contracts/CONTRACT-feature-spec-plan-outputs.md")

#: Human name used in every failure message, so a reader knows what to open.
DOC_DISPLAY_NAME = f"specialist-agent/{DOC_RELATIVE_PATH.as_posix()}"

#: Set to "1" by the seam-tests CI job. When set, a missing document is a
#: FAILURE rather than a skip. See the module docstring.
REQUIRED_ENV_VAR = "GUARDKIT_CONTRACT_DOC_REQUIRED"

#: Explicit override for a specialist-agent checkout in a non-standard place.
PATH_ENV_VAR = "SPECIALIST_AGENT_PATH"

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _candidate_doc_paths() -> List[Path]:
    """Every place a specialist-agent checkout is looked for, in order."""
    candidates: List[Path] = []
    override = os.environ.get(PATH_ENV_VAR)
    if override:
        candidates.append(Path(override) / DOC_RELATIVE_PATH)
    # CI layout: the sibling repo is checked out into a directory under the
    # workspace root, mirroring how seam-tests.yml checks out guardkitfactory.
    candidates.append(_REPO_ROOT / "specialist-agent" / DOC_RELATIVE_PATH)
    # Local developer layout: the two repos are siblings on disk.
    candidates.append(_REPO_ROOT.parent / "specialist-agent" / DOC_RELATIVE_PATH)
    return candidates


def _resolve_doc() -> Optional[Path]:
    for candidate in _candidate_doc_paths():
        if candidate.is_file():
            return candidate
    return None


def _searched_paths_text() -> str:
    return "\n".join(f"    {p}" for p in _candidate_doc_paths())


@pytest.fixture(scope="module")
def contract_doc_text() -> str:
    """The document's text, or a loud skip/failure explaining why there is none.

    Skips when no specialist-agent checkout is present AND no environment has
    declared the document required. Fails when it is declared required and
    still cannot be found.
    """
    doc = _resolve_doc()
    if doc is not None:
        return doc.read_text(encoding="utf-8")

    message = (
        f"The contract document {DOC_DISPLAY_NAME} was not found.\n"
        f"Searched:\n{_searched_paths_text()}\n"
        f"Point {PATH_ENV_VAR} at a specialist-agent checkout to check it here."
    )
    if os.environ.get(REQUIRED_ENV_VAR) == "1":
        pytest.fail(
            "COULD NOT CHECK — and this job declared the check MANDATORY.\n\n"
            f"{message}\n\n"
            f"{REQUIRED_ENV_VAR}=1 is set, which means this job is supposed to "
            "have specialist-agent checked out. It does not. This is a broken "
            "CI job, not a passing check: fix the checkout step in "
            ".github/workflows/seam-tests.yml."
        )
    pytest.skip(
        f"COULD NOT CHECK (not a pass): {message} "
        f"Set {REQUIRED_ENV_VAR}=1 to make this absence a failure instead."
    )
    raise AssertionError("unreachable")  # pragma: no cover


# --------------------------------------------------------------------------
# Parsing the document
#
# Every locator below anchors on text — a heading, a bold label, a row's field
# name — never on a line number, so inserting or deleting text elsewhere in the
# document cannot silently point a check at the wrong place.
# --------------------------------------------------------------------------

_BACKTICKED = re.compile(r"`([^`]+)`")
#: A markdown table splits on "|", but a cell may contain an escaped "\|".
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


class DocumentShapeError(AssertionError):
    """The document could not be parsed where a checked list was expected.

    Raised instead of returning nothing, so that a document restructure
    produces a loud failure rather than a check that quietly stops checking.
    """


def _fail_shape(what: str, anchor: str) -> "DocumentShapeError":
    return DocumentShapeError(
        f"CONTRACT DOCUMENT SHAPE CHANGED — could not find {what}.\n\n"
        f"  File:    {DOC_DISPLAY_NAME}\n"
        f"  Looked for the anchor: {anchor!r}\n\n"
        "This check locates each list by its surrounding text, not by line "
        "number. The anchor above is gone or reworded, so the list underneath "
        "it is NO LONGER BEING CHECKED. Either restore the anchor text or "
        "update the locator in "
        "guardkit/tests/contracts/test_contract_doc_enumerated_lists.py."
    )


def _find_unique(text: str, anchor: str, what: str) -> int:
    """Index of ``anchor``, requiring it to occur exactly once.

    Ambiguity is a hard failure rather than a silent "use the first one": this
    document discusses its own tables in prose, so a second occurrence usually
    means the check is about to read a sentence *about* a list instead of the
    list itself — and would then happily pass while checking nothing.
    """
    count = text.count(anchor)
    if count == 0:
        raise _fail_shape(what, anchor)
    if count > 1:
        raise DocumentShapeError(
            f"CONTRACT DOCUMENT ANCHOR IS AMBIGUOUS — {what}.\n\n"
            f"  File:   {DOC_DISPLAY_NAME}\n"
            f"  Anchor: {anchor!r}\n"
            f"  Occurs: {count} times (expected exactly 1)\n\n"
            "This check locates the list by the text above. More than one "
            "match means it cannot tell which occurrence is the real list, so "
            "it refuses to guess. Reword the other occurrence — prose that "
            "merely REFERS to this list must not reproduce its introduction "
            "line verbatim."
        )
    return text.index(anchor)


def _table_rows_after(text: str, anchor: str) -> List[List[str]]:
    """Return the cells of each markdown table row following ``anchor``."""
    start = _find_unique(text, anchor, f"the table introduced by {anchor!r}")

    rows: List[List[str]] = []
    started = False
    for line in text[start:].splitlines()[1:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if started:
                break
            continue
        started = True
        cells = [c.strip() for c in _UNESCAPED_PIPE.split(stripped)]
        # Drop the empty strings produced by the leading/trailing pipes.
        cells = [c for c in cells[1:-1]] if len(cells) >= 2 else cells
        if not cells:
            continue
        # Skip the header separator row (|---|---|).
        if set(cells[0]) <= set("-: "):
            continue
        rows.append(cells)
    if not rows:
        raise _fail_shape(f"any table rows under {anchor!r}", anchor)
    return rows


def _row_by_field_name(rows: List[List[str]], field: str, anchor: str) -> List[str]:
    for cells in rows:
        names = _BACKTICKED.findall(cells[0])
        if field in names:
            return cells
    raise _fail_shape(f"the {field!r} row of the table under {anchor!r}", anchor)


def _leading_alternation(cell: str) -> List[str]:
    """Read a leading run of backticked values joined by an escaped pipe.

    ``"`a` \\| `b` \\| `c` (default `a`)"`` yields ``["a", "b", "c"]`` — the
    trailing parenthetical prose is not part of the alternation and is ignored.
    """
    values: List[str] = []
    rest = cell.strip()
    token = re.compile(r"^`([^`]+)`")
    separator = re.compile(r"^\s*\\\|\s*")
    match = token.match(rest)
    while match:
        values.append(match.group(1))
        rest = rest[match.end():]
        sep = separator.match(rest)
        if not sep:
            break
        rest = rest[sep.end():]
        match = token.match(rest)
    return values


# Anchors are the FULL introduction text of each list, not a short phrase, and
# each is required to occur exactly once (see `_find_unique`). The document
# discusses its own tables in prose, so a short anchor such as
# "**Feature (top level)**" also matches a sentence *about* the table and would
# silently bind a check to the wrong place.
FEATURE_TABLE_ANCHOR = (
    '**Feature (top level)** — `extra="ignore"` (unknown keys tolerated):'
)
TASK_TABLE_ANCHOR = '**Task** — `extra="ignore"`:'
TASK_TYPE_LIST_ANCHOR = "**Valid `task_type` values** (guardkit/models/task_types.py)"
TASK_TYPE_VERBATIM_ANCHOR = "**Verbatim from the live validator"


def _documented_feature_statuses(text: str) -> List[str]:
    rows = _table_rows_after(text, FEATURE_TABLE_ANCHOR)
    row = _row_by_field_name(rows, "status", FEATURE_TABLE_ANCHOR)
    return _leading_alternation(row[-1])


def _documented_task_statuses(text: str) -> List[str]:
    rows = _table_rows_after(text, TASK_TABLE_ANCHOR)
    row = _row_by_field_name(rows, "status", TASK_TABLE_ANCHOR)
    return _leading_alternation(row[-1])


def _documented_feature_fields(text: str) -> List[str]:
    rows = _table_rows_after(text, FEATURE_TABLE_ANCHOR)
    names: List[str] = []
    for cells in rows:
        names.extend(_BACKTICKED.findall(cells[0]))
    return names


def _documented_task_types_canonical(text: str) -> List[str]:
    """Parse the "·"-separated list of task-type values in section B.4.

    The list runs from the colon that introduces it to a terminating full stop,
    and the values may be emphasised (``**`glue`**``). It is consumed entry by
    entry rather than split on a delimiter, because the paragraph that follows
    the list ("**Aliases (normalised):** ...") also contains colons and
    backticked values, and a split-based reader silently picks that up instead.
    """
    start = _find_unique(
        text, TASK_TYPE_LIST_ANCHOR, "the canonical task-type list"
    )
    after_anchor = start + len(TASK_TYPE_LIST_ANCHOR)
    colon = text.find(":", after_anchor)
    if colon == -1:
        raise _fail_shape(
            "the ':' introducing the canonical task-type list",
            TASK_TYPE_LIST_ANCHOR,
        )

    rest = text[colon + 1:]
    # One entry: optional bold markers around a single backticked value.
    entry = re.compile(r"^\s*(?:\*\*)?`([^`]+)`(?:\*\*)?")
    separator = re.compile(r"^\s*·\s*")

    values: List[str] = []
    match = entry.match(rest)
    while match:
        values.append(match.group(1))
        rest = rest[match.end():]
        sep = separator.match(rest)
        if not sep:
            break
        rest = rest[sep.end():]
        match = entry.match(rest)

    if not values:
        raise DocumentShapeError(
            "CONTRACT DOCUMENT SHAPE CHANGED — the canonical task-type list in "
            f"{DOC_DISPLAY_NAME} could not be read.\n\n"
            f"  Expected, after {TASK_TYPE_LIST_ANCHOR!r} and its ':', a list "
            "of `backticked` values separated by '·'.\n"
            f"  Found instead: {rest[:120].strip()!r}\n\n"
            "The list is NO LONGER BEING CHECKED until this is restored."
        )
    return values


def _documented_task_types_verbatim(text: str) -> str:
    """Return the 'Valid values: ...' run from the quoted validator message."""
    start = _find_unique(
        text, TASK_TYPE_VERBATIM_ANCHOR, "the quoted validator error message"
    )
    fence = text.find("```", start)
    if fence == -1:
        raise _fail_shape(
            "the fenced block after the quoted validator message",
            TASK_TYPE_VERBATIM_ANCHOR,
        )
    body_start = text.index("\n", fence) + 1
    end = text.find("```", body_start)
    if end == -1:
        raise _fail_shape(
            "the closing fence of the quoted validator message",
            TASK_TYPE_VERBATIM_ANCHOR,
        )
    # The message is hard-wrapped in the document; unwrap it before matching.
    unwrapped = " ".join(text[body_start:end].split())
    match = re.search(r"Valid values:\s*(.*?)\.\s*Valid aliases:", unwrapped)
    if not match:
        raise DocumentShapeError(
            "CONTRACT DOCUMENT SHAPE CHANGED — the quoted validator error "
            f"message in {DOC_DISPLAY_NAME} no longer contains a "
            "'Valid values: ... . Valid aliases:' run, so the task-type list "
            "inside it is NO LONGER BEING CHECKED."
        )
    return match.group(1)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def _mismatch(
    *,
    list_name: str,
    code_location: str,
    doc_section: str,
    code_values: List[str],
    doc_values: List[str],
) -> str:
    """Build a failure a reader can act on without opening anything else."""
    missing = [v for v in code_values if v not in doc_values]
    extra = [v for v in doc_values if v not in code_values]

    lines = [
        f"CONTRACT DOCUMENT ENUMERATED-LIST MISMATCH — {list_name}",
        "",
        "The written contract states a different set of values than the code "
        "actually accepts.",
        "",
        f"  List:            {list_name}",
        f"  Code says  ({len(code_values):>2}): {', '.join(code_values) or '(none)'}",
        f"  Document says ({len(doc_values):>2}): {', '.join(doc_values) or '(none)'}",
        "",
    ]
    if missing:
        lines.append(
            "  IN THE CODE BUT NOT IN THE DOCUMENT (the document is stale): "
            + ", ".join(missing)
        )
    if extra:
        lines.append(
            "  IN THE DOCUMENT BUT NOT IN THE CODE (the document is wrong): "
            + ", ".join(extra)
        )
    lines += [
        "",
        "  To fix:",
        f"    Source of truth : guardkit repo — {code_location}",
        f"    File to edit    : {DOC_DISPLAY_NAME}",
        f"    Section to edit : {doc_section}",
        "",
        "  If the CODE is what changed, update the document to match it and add "
        "a dated note to section '0.1 · Dated correction notes'. If the "
        "DOCUMENT is right and the code is wrong, that is a code defect — do "
        "not edit the document to hide it.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------


class TestContractDocEnumeratedLists:
    """Four enumerated lists, checked at five places in the document.

    NOT a check of the contract document as a whole — see the module docstring
    for the (large) uncovered surface.
    """

    def test_feature_status_values_match_code(self, contract_doc_text: str) -> None:
        code_values = list(Feature.model_fields["status"].annotation.__args__)
        doc_values = _documented_feature_statuses(contract_doc_text)
        assert doc_values == code_values, _mismatch(
            list_name="Feature.status — the allowed statuses of a feature",
            code_location="guardkit/orchestrator/feature_loader.py "
            "(class Feature, the `status` Literal)",
            doc_section="'B.2 · Schema layer' — the **Feature (top level)** "
            "table, the `status` row, 'Constraint / default' column",
            code_values=code_values,
            doc_values=doc_values,
        )

    def test_task_status_values_match_code(self, contract_doc_text: str) -> None:
        code_values = list(FeatureTask.model_fields["status"].annotation.__args__)
        doc_values = _documented_task_statuses(contract_doc_text)
        assert doc_values == code_values, _mismatch(
            list_name="FeatureTask.status — the allowed statuses of a task",
            code_location="guardkit/orchestrator/feature_loader.py "
            "(class FeatureTask, the `status` Literal)",
            doc_section="'B.2 · Schema layer' — the **Task** table, the "
            "`status` row, 'Constraint / default' column",
            code_values=code_values,
            doc_values=doc_values,
        )

    def test_task_type_values_match_code(self, contract_doc_text: str) -> None:
        code_values = [t.value for t in TaskType]
        doc_values = _documented_task_types_canonical(contract_doc_text)
        assert doc_values == code_values, _mismatch(
            list_name="TaskType — the allowed task-type values (canonical list)",
            code_location="guardkit/models/task_types.py (class TaskType)",
            doc_section="'B.4 · Task markdown frontmatter contract' — the "
            "**Valid `task_type` values** list",
            code_values=code_values,
            doc_values=doc_values,
        )

    def test_task_type_values_match_code_in_the_quoted_error_message(
        self, contract_doc_text: str
    ) -> None:
        """The same list again, where the document quotes the validator.

        The document states the task-type values twice. On 2026-08-15 a
        correction pass fixed one statement of this list and left the other
        wrong, in the same pass. Checking only one place would not have caught
        that, so both are checked.
        """
        code_text = ", ".join(t.value for t in TaskType)
        doc_text = _documented_task_types_verbatim(contract_doc_text)
        assert doc_text == code_text, _mismatch(
            list_name="TaskType — as quoted in the validator's error message",
            code_location="guardkit/orchestrator/feature_loader.py "
            "(_validate_task_type_in_file, the 'Valid values:' string)",
            doc_section="'B.4 · Task markdown frontmatter contract' — the "
            "fenced block headed **Verbatim from the live validator**",
            code_values=code_text.split(", "),
            doc_values=doc_text.split(", "),
        )

    def test_feature_field_names_match_code(self, contract_doc_text: str) -> None:
        code_values = list(Feature.model_fields)
        doc_values = _documented_feature_fields(contract_doc_text)
        assert sorted(doc_values) == sorted(code_values), _mismatch(
            list_name="Feature.model_fields — the field names of the feature model",
            code_location="guardkit/orchestrator/feature_loader.py (class Feature)",
            doc_section="'B.2 · Schema layer' — the **Feature (top level)** "
            "table, one row per field, field name in the first column",
            code_values=code_values,
            doc_values=doc_values,
        )


def test_contract_document_is_present_when_declared_required() -> None:
    """Absence must be loud in the job that exists to run this check.

    This test carries no fixture on purpose: it runs even when the document is
    missing, so that a seam job with a broken specialist-agent checkout reports
    a failure instead of a silent pass made of skips.
    """
    if os.environ.get(REQUIRED_ENV_VAR) != "1":
        pytest.skip(
            f"{REQUIRED_ENV_VAR} is not set — this environment has not declared "
            "the contract document required. In CI it is set by "
            ".github/workflows/seam-tests.yml."
        )
    doc = _resolve_doc()
    assert doc is not None, (
        f"COULD NOT CHECK — {REQUIRED_ENV_VAR}=1 but {DOC_DISPLAY_NAME} was not "
        f"found.\nSearched:\n{_searched_paths_text()}\n\n"
        "The four enumerated-list checks in this module all skipped, which "
        "looks like success and is not. Fix the specialist-agent checkout step "
        "in .github/workflows/seam-tests.yml."
    )
