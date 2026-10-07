"""``collapse_multi_line_steps`` must read a spec the way the gherkin parser does.

Two gaps are covered here.

Backtick doc-strings. Gherkin accepts two doc-string delimiters: three double
quotes and three backticks. The opening delimiter may carry a content type
(three backticks followed by ``json``), and the doc-string ends at the next
line that starts with the same delimiter. Before this fix the collapse only
knew the double-quote form (plus three single quotes, which Gherkin itself does
not treat as a delimiter). Inside a backtick doc-string it therefore joined the
opening line and the content onto the step above, and read content lines such
as ``Rule: not a rule`` or ``Scenario: fake`` as structure, so the parser then
read the collapsed spec differently from what was written (later steps became a
Rule description; phantom scenarios appeared).

Missing keywords. The collapse's list of headers lacked ``Example:``,
``Scenario Template:``, ``Scenarios:``, ``Business Need:`` and ``Ability:``,
and it did not know the ``* `` step keyword. An indented header (or ``* `` step)
under a step was joined onto that step, while the parser of the original text
starts a new scenario, examples block or step there.

These tests pin that:

1. backtick doc-strings, with and without a content type, come out of the
   collapse byte-identical, and the gherkin parse after collapse equals the
   parse of the original;
2. every English header keyword in gherkin-official's own list, and the
   ``* `` step, is left alone by the collapse, with the same parse before and
   after;
3. wrapped steps outside doc-strings still join;
4. a spec with none of these lines collapses exactly as it did before the fix
   (a verbatim copy of the collapse at commit 7e8844ec is kept below as the
   reference).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, List

import pytest

from installer.core.commands.lib.feature_spec_normalize import (
    collapse_multi_line_steps,
    validate_gherkin,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "feature_specs"


def _parse(text: str) -> Any:
    """Parse with gherkin-official, the parser every downstream reader uses."""
    from gherkin.parser import Parser

    return Parser().parse(text)


# ----------------------------------------------------------------------
# Reference: the collapse exactly as it was at commit 7e8844ec
# ----------------------------------------------------------------------
# Copied verbatim (names prefixed) so the "no backtick doc-string means no
# change" tests compare against the real earlier behaviour, not a re-statement
# of it.

_OLD_STEP_KEYWORD_RE = re.compile(r"^(\s*)(Given|When|Then|And|But)\s+\S")
_OLD_STRUCTURAL_KEYWORD_RE = re.compile(
    r"^\s*(Feature|Background|Scenario Outline|Scenario|Rule|Examples)\s*:"
)
_OLD_COMMENT_RE = re.compile(r"^\s*#")
_OLD_TAG_RE = re.compile(r"^\s*@")
_OLD_TABLE_ROW_RE = re.compile(r"^\s*\|")
_OLD_DOCSTRING_DELIMITER_RE = re.compile(r"^\s*(\"\"\"|''')")


def _old_line_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _collapse_as_of_7e8844ec(text: str) -> str:
    lines: List[str] = text.splitlines(keepends=True)
    result: List[str] = []

    in_docstring = False
    docstring_delim = ""

    pending_idx = -1
    pending_indent = -1

    for line in lines:
        body = line.rstrip("\r\n")

        if in_docstring:
            result.append(line)
            m = _OLD_DOCSTRING_DELIMITER_RE.match(body)
            if m and m.group(1) == docstring_delim:
                in_docstring = False
                docstring_delim = ""
                pending_idx = -1
            continue

        m_doc = _OLD_DOCSTRING_DELIMITER_RE.match(body)
        if m_doc:
            result.append(line)
            in_docstring = True
            docstring_delim = m_doc.group(1)
            pending_idx = -1
            continue

        if not body.strip():
            result.append(line)
            pending_idx = -1
            continue

        if _OLD_COMMENT_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        if _OLD_TAG_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        if _OLD_TABLE_ROW_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        if _OLD_STRUCTURAL_KEYWORD_RE.match(body):
            result.append(line)
            pending_idx = -1
            continue

        m_step = _OLD_STEP_KEYWORD_RE.match(body)
        if m_step:
            result.append(line)
            pending_idx = len(result) - 1
            pending_indent = len(m_step.group(1))
            continue

        if pending_idx >= 0 and _old_line_indent(line) > pending_indent:
            cont = body.strip()
            prior = result[pending_idx]
            prior_body = prior.rstrip("\r\n")
            line_ending = prior[len(prior_body):]
            result[pending_idx] = f"{prior_body} {cont}{line_ending}"
            continue

        result.append(line)
        pending_idx = -1

    return "".join(result)


# ----------------------------------------------------------------------
# 1. Backtick doc-strings are kept verbatim
# ----------------------------------------------------------------------


def _backtick_spec(content_type: str, eol: str = "\n") -> str:
    lines = [
        "@payloads",
        "Feature: Webhook payloads",
        "  Background:",
        "    Given the receiver is running",
        "",
        "  Scenario: Posting a payload",
        "    When a client posts the body",
        f"      ```{content_type}",
        "      {",
        "      Rule: not a rule",
        "      Scenario: fake",
        "      Feature: x",
        "      Background: not a background",
        "      Examples: not examples",
        "      # not a comment",
        "      @not-a-tag",
        "      | not | a table |",
        "      Given not a step",
        '        "key": "a long value that looks like',
        '          a wrapped continuation"',
        '      """',
        "      '''",
        "      }",
        "      ```",
        "    Then the response says it was received",
        "    And the stored body matches",
        "",
        "  Scenario: A second, real scenario",
        "    Given nothing special",
        "    Then nothing happens",
    ]
    return eol.join(lines) + eol


@pytest.mark.parametrize("content_type", ["", "json", "text/plain"])
def test_backtick_docstring_is_byte_identical_after_collapse(
    content_type: str,
) -> None:
    text = _backtick_spec(content_type)
    assert collapse_multi_line_steps(text) == text


@pytest.mark.parametrize("content_type", ["", "json"])
def test_backtick_docstring_parse_after_collapse_equals_original(
    content_type: str,
) -> None:
    text = _backtick_spec(content_type)
    collapsed = collapse_multi_line_steps(text)
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)

    # Spell out what the reader must see: two scenarios, no rule, and the
    # doc-string content (including the keyword-looking lines) as one block.
    feature = _parse(collapsed)["feature"]
    children = feature["children"]
    assert [list(c)[0] for c in children] == ["background", "scenario", "scenario"]
    scenarios = [c["scenario"]["name"] for c in children if "scenario" in c]
    assert scenarios == ["Posting a payload", "A second, real scenario"]
    posting = children[1]["scenario"]
    assert [s["text"] for s in posting["steps"]] == [
        "a client posts the body",
        "the response says it was received",
        "the stored body matches",
    ]
    doc = posting["steps"][0]["docString"]
    assert doc["delimiter"] == "```"
    if content_type:
        assert doc["mediaType"] == content_type
    assert "Rule: not a rule" in doc["content"]
    assert "Scenario: fake" in doc["content"]


def test_backtick_docstring_survives_crlf_line_endings() -> None:
    text = _backtick_spec("json", eol="\r\n")
    assert collapse_multi_line_steps(text) == text


def test_backtick_docstring_collapse_is_idempotent() -> None:
    text = _backtick_spec("json")
    once = collapse_multi_line_steps(text)
    assert collapse_multi_line_steps(once) == once


def test_triple_quote_line_does_not_close_a_backtick_docstring() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the body\n"
        "      ```\n"
        '      """\n'
        "      Scenario: still inside the backtick doc-string\n"
        "      ```\n"
        "    Then it is stored\n"
    )
    assert collapse_multi_line_steps(text) == text
    assert _parse(collapse_multi_line_steps(text)) == _parse(text)


def test_backtick_line_does_not_close_a_triple_quote_docstring() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the body\n"
        '      """markdown\n'
        "      ```json\n"
        "      Rule: still inside the triple-quote doc-string\n"
        "      ```\n"
        '      """\n'
        "    Then it is stored\n"
    )
    assert collapse_multi_line_steps(text) == text
    assert _parse(collapse_multi_line_steps(text)) == _parse(text)


# ----------------------------------------------------------------------
# 2. Every header keyword, and the ``* `` step, is left alone
# ----------------------------------------------------------------------


def test_structural_keyword_list_matches_gherkin_official() -> None:
    """The collapse knows every English header keyword the parser knows."""
    import json

    import gherkin

    from installer.core.commands.lib import feature_spec_normalize as mod

    languages = Path(gherkin.__file__).with_name("gherkin-languages.json")
    english = json.loads(languages.read_text(encoding="utf-8"))["en"]
    headers = {
        keyword
        for kind in ("feature", "rule", "background", "scenario",
                     "scenarioOutline", "examples")
        for keyword in english[kind]
    }
    for keyword in headers:
        assert mod._STRUCTURAL_KEYWORD_RE.match(f"    {keyword}: x"), keyword
    step_keywords = {
        keyword
        for kind in ("given", "when", "then", "and", "but")
        for keyword in english[kind]
    }
    assert step_keywords == {"Given ", "When ", "Then ", "And ", "But ", "* "}


# Each spec has an indented header straight under a step, at a deeper indent
# than the step, which is the shape the collapse used to join. All of them
# parse; the parser reads the indented line as a new header.
_HEADER_UNDER_STEP = {
    "Example": (
        "Feature: Demo\n"
        "  Scenario: first\n"
        "    Given a value\n"
        "      Example: second\n"
        "    Given another value\n"
    ),
    "Scenario": (
        "Feature: Demo\n"
        "  Example: first\n"
        "    Given a value\n"
        "      Scenario: second\n"
        "    Given another value\n"
    ),
    "Scenario Template": (
        "Feature: Demo\n"
        "  Scenario: first\n"
        "    Given a value\n"
        "      Scenario Template: second\n"
        "    Given <v>\n"
        "    Examples:\n"
        "      | v |\n"
        "      | 1 |\n"
    ),
    "Scenario Outline": (
        "Feature: Demo\n"
        "  Scenario: first\n"
        "    Given a value\n"
        "      Scenario Outline: second\n"
        "    Given <v>\n"
        "    Examples:\n"
        "      | v |\n"
        "      | 1 |\n"
    ),
    "Scenarios": (
        "Feature: Demo\n"
        "  Scenario Outline: first\n"
        "    Given <v>\n"
        "      Scenarios: the values\n"
        "      | v |\n"
        "      | 1 |\n"
    ),
    "Examples": (
        "Feature: Demo\n"
        "  Scenario Template: first\n"
        "    Given <v>\n"
        "      Examples: the values\n"
        "      | v |\n"
        "      | 1 |\n"
    ),
    "Rule": (
        "Feature: Demo\n"
        "  Scenario: first\n"
        "    Given a value\n"
        "      Rule: a rule\n"
        "  Scenario: inside the rule\n"
        "    Given another value\n"
    ),
}


@pytest.mark.parametrize("keyword", sorted(_HEADER_UNDER_STEP))
def test_header_under_a_step_is_left_alone(keyword: str) -> None:
    text = _HEADER_UNDER_STEP[keyword]
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)


# These headers cannot follow a step in a valid spec; the parser refuses the
# original. The collapse must not "repair" that by joining the header onto the
# step: the original and the collapsed text must be refused the same way.
_INVALID_HEADER_UNDER_STEP = {
    "Background": "Background:",
    "Feature": "Feature: another",
    "Business Need": "Business Need: another",
    "Ability": "Ability: another",
}


@pytest.mark.parametrize("keyword", sorted(_INVALID_HEADER_UNDER_STEP))
def test_misplaced_header_under_a_step_is_not_joined(keyword: str) -> None:
    from gherkin.errors import CompositeParserException

    text = (
        "Feature: Demo\n"
        "  Scenario: first\n"
        "    Given a value\n"
        f"      {_INVALID_HEADER_UNDER_STEP[keyword]}\n"
        "    Given another value\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    with pytest.raises(CompositeParserException) as original_error:
        _parse(text)
    with pytest.raises(CompositeParserException) as collapsed_error:
        _parse(collapsed)
    assert str(collapsed_error.value) == str(original_error.value)


@pytest.mark.parametrize("keyword", ["Business Need", "Ability"])
def test_feature_header_synonyms_start_a_feature(keyword: str) -> None:
    text = (
        f"{keyword}: Demo\n"
        "  Some description\n"
        "  Scenario: first\n"
        "    Given a value that wraps\n"
        "      onto a second line\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        f"{keyword}: Demo\n"
        "  Some description\n"
        "  Scenario: first\n"
        "    Given a value that wraps onto a second line\n"
    )
    validate_gherkin(collapsed)


def test_star_step_under_a_step_is_not_joined() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: first\n"
        "    Given a value\n"
        "      * another value\n"
        "    Then done\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    assert _parse(collapsed) == _parse(text)
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert [s["keyword"] + s["text"] for s in steps] == [
        "Given a value",
        "* another value",
        "Then done",
    ]


def test_wrapped_star_step_joins_like_any_other_step() -> None:
    text = (
        "Feature: Demo\n"
        "  Background:\n"
        "    * a background step that\n"
        "      wraps\n"
        "  Example: first\n"
        "    * a step that\n"
        "      wraps\n"
        "    * a second step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Background:\n"
        "    * a background step that wraps\n"
        "  Example: first\n"
        "    * a step that wraps\n"
        "    * a second step\n"
    )
    validate_gherkin(collapsed)


def test_star_bullets_in_descriptions_are_left_as_text() -> None:
    """In Feature, Rule and Examples descriptions the parser reads ``* `` as
    ordinary text, so the collapse must not treat it as a step there."""
    text = (
        "Feature: Demo\n"
        "  The feature does:\n"
        "  * one thing that\n"
        "    wraps\n"
        "  Rule: a rule\n"
        "    * a rule bullet that\n"
        "      wraps\n"
        "    Scenario Outline: first\n"
        "      Given <v>\n"
        "      Examples: values\n"
        "        * an examples bullet that\n"
        "          wraps\n"
        "        | v |\n"
        "        | 1 |\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    assert collapsed == _collapse_as_of_7e8844ec(text)
    assert _parse(collapsed) == _parse(text)


# ----------------------------------------------------------------------
# 3. Wrapped steps outside doc-strings still join
# ----------------------------------------------------------------------


def test_wrapped_steps_around_a_backtick_docstring_still_join() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a client that sends a body with a fairly long\n"
        "      description that the writer wrapped\n"
        "      ```json\n"
        "      {\n"
        '        "a": 1,\n'
        "          Rule: content\n"
        "      }\n"
        "      ```\n"
        "    Then the receiver stores it under a key that is also\n"
        "      wrapped onto a second line\n"
        "    And replies\n"
    )
    expected = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a client that sends a body with a fairly long "
        "description that the writer wrapped\n"
        "      ```json\n"
        "      {\n"
        '        "a": 1,\n'
        "          Rule: content\n"
        "      }\n"
        "      ```\n"
        "    Then the receiver stores it under a key that is also "
        "wrapped onto a second line\n"
        "    And replies\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == expected
    validate_gherkin(collapsed)
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert steps[0]["docString"]["content"] == (
        '{\n  "a": 1,\n    Rule: content\n}'
    )


# ----------------------------------------------------------------------
# 4. Specs with none of the newly recognised lines are unchanged from 7e8844ec
# ----------------------------------------------------------------------

_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox"}


def _feature_corpus() -> List[Path]:
    found: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name.endswith(".feature"):
                found.append(Path(dirpath) / name)
    return sorted(found)


_CORPUS = _feature_corpus()


_NEWLY_RECOGNISED_RE = re.compile(
    r"^\s*(```|\* |(Business Need|Ability|Scenario Template|Example|Scenarios)\s*:)"
)


def _has_newly_recognised_line(text: str) -> bool:
    """A line the fix reads differently: a backtick delimiter, a ``* `` step,
    or one of the header keywords that were missing."""
    return any(_NEWLY_RECOGNISED_RE.match(line) for line in text.splitlines())


def test_corpus_is_not_empty() -> None:
    # Guards the comparison below against silently checking nothing.
    assert (FIXTURES / "mcp-llm-player-coach-adapters_pre.feature") in _CORPUS
    assert len(_CORPUS) >= 2


@pytest.mark.parametrize(
    "path", _CORPUS, ids=[str(p.relative_to(REPO_ROOT)) for p in _CORPUS]
)
def test_spec_without_new_lines_collapses_as_before(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if _has_newly_recognised_line(text):
        pytest.skip("has a line the fix reads differently; covered above")
    assert collapse_multi_line_steps(text) == _collapse_as_of_7e8844ec(text)


_INLINE_SAMPLES = {
    "wrapped steps": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a long step that\n"
        "      wraps\n"
        "    # a comment\n"
        "    When another\n"
        "      wraps too\n"
        "    Then done\n"
    ),
    "triple-quote doc-string": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the text\n"
        '      """json\n'
        "      Scenario: inside\n"
        "        indented\n"
        '      """\n'
        "    Then a wrapped\n"
        "      step\n"
    ),
    "single-quote block": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the text\n"
        "      '''\n"
        "      Scenario: inside\n"
        "      '''\n"
        "    Then done\n"
    ),
    "inline backticks inside a step": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the reply contains ```code``` in the middle of\n"
        "      a wrapped step\n"
        "    Then done\n"
    ),
    "star bullet in a feature description": (
        "Feature: Demo\n"
        "  * a bullet that\n"
        "    wraps\n"
        "  Scenario: x\n"
        "    Given a\n"
        "      wrapped step\n"
    ),
    "unterminated triple-quote": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given text\n"
        '      """\n'
        "      never closed\n"
        "    Then x\n"
        "      wraps\n"
    ),
}


@pytest.mark.parametrize("name", sorted(_INLINE_SAMPLES))
def test_inline_sample_without_new_lines_collapses_as_before(
    name: str,
) -> None:
    text = _INLINE_SAMPLES[name]
    assert collapse_multi_line_steps(text) == _collapse_as_of_7e8844ec(text)
