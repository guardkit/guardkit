"""Post-generation normaliser for ``/feature-spec`` Gherkin output.

The official Gherkin parser used downstream by ``/feature-plan`` Step 11
(``feature-plan-bdd-link prepare``) does not accept multi-line step
continuations — every ``Given``/``When``/``Then``/``And``/``But`` step must
fit on a single physical line. Multi-line content is only supported via
doc-strings or data tables.

``/feature-spec`` is an LLM-driven generator and the model occasionally
wraps long step text across lines. This module is the deterministic
backstop that collapses any such continuations before the file lands on
disk, so the next consumer in the chain (the BDD linker) can parse it.

The collapse algorithm walks the file top-to-bottom, tracking whether the
cursor is "inside a step" (i.e. the most-recent non-empty, non-comment,
non-tag line started with a step keyword). While inside a step, any
following line that is more indented than the step and is not a comment,
tag, doc-string delimiter, table row, or another keyword is treated as a
continuation and appended to the step with a single-space separator.

Public surface:

- :func:`collapse_multi_line_steps` — pure, deterministic, idempotent
- :func:`validate_gherkin` — raises :class:`FeatureSpecGherkinError` if the
  text does not parse via ``gherkin.parser.Parser``
- :func:`normalize_feature_file` — collapse then validate; returns text
- ``__main__`` — ``python -m installer.core.commands.lib.feature_spec_normalize <path>``
  rewrites a file in place

Seeded by GuardKit ``TASK-FSGS-001``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

__all__ = [
    "FeatureSpecGherkinError",
    "collapse_multi_line_steps",
    "validate_gherkin",
    "normalize_feature_file",
]


# Gherkin step keywords (case-sensitive — the official parser requires the
# canonical capitalisation).
_STEP_KEYWORD_RE = re.compile(r"^(\s*)(Given|When|Then|And|But)\s+\S")

# Structural keywords end any step block.
_STRUCTURAL_KEYWORD_RE = re.compile(
    r"^\s*(Feature|Background|Scenario Outline|Scenario|Rule|Examples)\s*:"
)

_COMMENT_RE = re.compile(r"^\s*#")
_TAG_RE = re.compile(r"^\s*@")
_TABLE_ROW_RE = re.compile(r"^\s*\|")
_DOCSTRING_DELIMITER_RE = re.compile(r"^\s*(\"\"\"|''')")


class FeatureSpecGherkinError(Exception):
    """Raised when a feature file does not parse via gherkin-official."""


def _line_indent(line: str) -> int:
    """Return the count of leading whitespace characters."""
    return len(line) - len(line.lstrip())


def collapse_multi_line_steps(text: str) -> str:
    """Collapse wrapped step continuations onto their parent step line.

    Pure, deterministic, idempotent. Preserves the original line ending of
    each surviving line (no newline normalisation).

    Args:
        text: Raw ``.feature`` text.

    Returns:
        The same text with every ``Given``/``When``/``Then``/``And``/``But``
        step wrapped onto a single line. Doc-strings, table rows, comments,
        tags, and structural keywords are preserved verbatim.
    """
    lines: List[str] = text.splitlines(keepends=True)
    result: List[str] = []

    in_docstring = False
    docstring_delim = ""

    # Index into ``result`` of the most-recent step line that may still be
    # extended by a continuation. -1 means "not currently inside a step".
    pending_idx = -1
    pending_indent = -1

    for line in lines:
        body = line.rstrip("\r\n")

        # --- Doc-string handling ---------------------------------------
        if in_docstring:
            result.append(line)
            m = _DOCSTRING_DELIMITER_RE.match(body)
            if m and m.group(1) == docstring_delim:
                in_docstring = False
                docstring_delim = ""
                pending_idx = -1
            continue

        m_doc = _DOCSTRING_DELIMITER_RE.match(body)
        if m_doc:
            result.append(line)
            in_docstring = True
            docstring_delim = m_doc.group(1)
            pending_idx = -1
            continue

        # --- Empty line ------------------------------------------------
        if not body.strip():
            result.append(line)
            pending_idx = -1
            continue

        # --- Comment ---------------------------------------------------
        if _COMMENT_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        # --- Tag -------------------------------------------------------
        if _TAG_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        # --- Table row -------------------------------------------------
        if _TABLE_ROW_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        # --- Structural keyword (Feature/Background/Scenario/...) ------
        if _STRUCTURAL_KEYWORD_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        # --- Step keyword (Given/When/Then/And/But) --------------------
        m_step = _STEP_KEYWORD_RE.match(body)
        if m_step:
            result.append(line)
            pending_idx = len(result) - 1
            pending_indent = len(m_step.group(1))
            continue

        # --- Possible continuation of the pending step -----------------
        if pending_idx >= 0 and _line_indent(line) > pending_indent:
            cont = body.strip()
            prior = result[pending_idx]
            prior_body = prior.rstrip("\r\n")
            line_ending = prior[len(prior_body):]
            result[pending_idx] = f"{prior_body} {cont}{line_ending}"
            continue

        # --- Anything else: feature description, etc. -----------------
        result.append(line)
        pending_idx = -1

    return "".join(result)


def validate_gherkin(text: str) -> None:
    """Parse ``text`` with gherkin-official; raise on any parser error.

    Raises:
        FeatureSpecGherkinError: If the parser reports any error. The
            exception message contains the parser's own error text so
            operators can locate the offending line.
    """
    # Local import keeps the cost off cold paths and matches the pattern
    # used in ``bdd_linker.parse_feature_file``.
    from gherkin.errors import CompositeParserException
    from gherkin.parser import Parser

    parser = Parser()
    try:
        parser.parse(text)
    except CompositeParserException as exc:
        raise FeatureSpecGherkinError(
            "Generated feature file does not parse via gherkin-official:\n"
            + str(exc)
        ) from exc
    except Exception as exc:  # pragma: no cover — defensive
        raise FeatureSpecGherkinError(
            f"Unexpected error while parsing feature file: {exc}"
        ) from exc


def normalize_feature_file(text: str) -> str:
    """Collapse continuations and validate. Returns the cleaned text.

    Idempotent: ``normalize_feature_file(normalize_feature_file(x)) == normalize_feature_file(x)``.

    Raises:
        FeatureSpecGherkinError: If the cleaned text still does not parse.
    """
    cleaned = collapse_multi_line_steps(text)
    validate_gherkin(cleaned)
    return cleaned


def _main(argv: List[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write(
            "usage: python -m installer.core.commands.lib.feature_spec_normalize <path>\n"
        )
        return 2

    path = Path(argv[0])
    if not path.exists():
        sys.stderr.write(f"error: file not found: {path}\n")
        return 2

    original = path.read_text(encoding="utf-8")
    try:
        cleaned = normalize_feature_file(original)
    except FeatureSpecGherkinError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    if cleaned != original:
        path.write_text(cleaned, encoding="utf-8")
        sys.stdout.write(f"normalised: {path}\n")
    else:
        sys.stdout.write(f"already clean: {path}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main(sys.argv[1:]))
