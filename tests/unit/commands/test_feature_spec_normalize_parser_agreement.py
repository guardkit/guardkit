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
4. a three-backtick line in a description (not straight after a step) is
   ordinary text, as it is to the parser, so it never stops later wrapped
   steps from joining;
5. specs with none of these lines collapse as they did before the fix (the
   expected output is written out in full).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List

import pytest

from installer.core.commands.lib.feature_spec_normalize import (
    collapse_multi_line_steps,
    validate_gherkin,
)


def _parse(text: str) -> Any:
    """Parse with gherkin-official, the parser every downstream reader uses."""
    from gherkin.parser import Parser

    return Parser().parse(text)


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
    # The keywords the collapse uses to decide doc-string eligibility.
    assert set(mod._PARSER_STEP_KEYWORDS) == step_keywords


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
# 4. A backtick line in a description is text, not a doc-string
# ----------------------------------------------------------------------
# The parser opens a doc-string only straight after a step (blank lines and
# comments may sit in between). Anywhere else a three-backtick line is part of
# a description. Each case puts a fence in a description and is followed by a
# wrapped step that must still be joined.

_FENCES = {
    "unclosed": ["```"],
    "closed": ["```json", "fenced text", "```"],
    "opened and closed on one line": ["```code```"],
}


def _indent(lines: List[str], spaces: int) -> List[str]:
    return [" " * spaces + line for line in lines]


def _description_fence_spec(
    where: str,
    fence: List[str],
    joined: bool,
    description: str = "Some description",
) -> str:
    step = (
        ["Given a wrapped step"]
        if joined
        else ["Given a wrapped", "  step"]
    )
    if where == "Feature":
        lines = (
            ["Feature: Demo", "  " + description]
            + _indent(fence, 2)
            + ["  Scenario: x"]
            + _indent(step, 4)
            + ["    Then done"]
        )
    elif where == "Rule":
        lines = (
            ["Feature: Demo", "  Rule: a rule", "    " + description]
            + _indent(fence, 4)
            + ["    Scenario: x"]
            + _indent(step, 6)
            + ["      Then done"]
        )
    elif where == "Scenario":
        lines = (
            ["Feature: Demo", "  Scenario: x", "    " + description]
            + _indent(fence, 4)
            + _indent(step, 4)
            + ["    Then done"]
        )
    elif where == "Background":
        lines = (
            ["Feature: Demo", "  Background:", "    " + description]
            + _indent(fence, 4)
            + _indent(step, 4)
            + ["    Then done"]
        )
    elif where == "Examples":
        lines = (
            [
                "Feature: Demo",
                "  Scenario Outline: x",
                "    Given <v>",
                "    Examples: values",
                "      " + description,
            ]
            + _indent(fence, 6)
            + ["      | v |", "      | 1 |", "  Scenario: y"]
            + _indent(step, 4)
            + ["    Then done"]
        )
    else:  # pragma: no cover - test table error
        raise ValueError(where)
    return "\n".join(lines) + "\n"


@pytest.mark.parametrize("fence_name", sorted(_FENCES))
@pytest.mark.parametrize("where", ["Feature", "Rule", "Scenario", "Examples"])
def test_backtick_line_in_a_description_is_text(where: str, fence_name: str) -> None:
    fence = _FENCES[fence_name]
    text = _description_fence_spec(where, fence, joined=False)
    expected = _description_fence_spec(where, fence, joined=True)
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == expected
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(expected)


# A description line that looks like a step is still description text to
# the parser in a Feature, Rule or Examples description (in a scenario it
# would be a real step), so a fence after it is text too.


@pytest.mark.parametrize("fence_name", sorted(_FENCES))
@pytest.mark.parametrize("where", ["Feature", "Rule", "Examples"])
@pytest.mark.parametrize(
    "description", ["Given some context", "And then more", "But not this"]
)
def test_backtick_line_after_step_looking_description_is_text(
    where: str, fence_name: str, description: str
) -> None:
    fence = _FENCES[fence_name]
    text = _description_fence_spec(where, fence, False, description)
    expected = _description_fence_spec(where, fence, True, description)
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == expected
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(expected)


# In a Scenario or Background description, a keyword followed by a tab is
# not a step to the parser, which needs the keyword's trailing space.


@pytest.mark.parametrize("fence_name", sorted(_FENCES))
@pytest.mark.parametrize("where", ["Scenario", "Background"])
@pytest.mark.parametrize(
    "description", ["Given\tcontext", "When\t\tcontext", "*\tcontext"]
)
def test_backtick_line_after_keyword_and_tab_description_is_text(
    where: str, fence_name: str, description: str
) -> None:
    fence = _FENCES[fence_name]
    text = _description_fence_spec(where, fence, False, description)
    expected = _description_fence_spec(where, fence, True, description)
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == expected
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(expected)
    first = _parse(expected)["feature"]["children"][0]
    section = first.get("scenario") or first["background"]
    assert description in section["description"]
    assert [s["text"] for s in section["steps"]] == ["a wrapped step", "done"]


def test_backtick_line_after_wrapped_keyword_and_tab_description_is_text() -> None:
    """The joining patterns still join a wrapped line onto ``Given<tab>...``
    as they always did; the fence after it stays text."""
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given\tcontext\n"
        "      that wraps\n"
        "    ```\n"
        "    Given a wrapped\n"
        "      step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given\tcontext that wraps\n"
        "    ```\n"
        "    Given a wrapped step\n"
    )
    validate_gherkin(collapsed)


def test_backtick_line_after_wrapped_step_looking_description_is_text() -> None:
    """A wrapped step-looking description line is joined as it always was,
    and the fence after it is still text."""
    text = (
        "Feature: Demo\n"
        "  Given some context\n"
        "    that wraps\n"
        "  ```\n"
        "  Scenario: x\n"
        "    Given a wrapped\n"
        "      step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Given some context that wraps\n"
        "  ```\n"
        "  Scenario: x\n"
        "    Given a wrapped step\n"
    )
    validate_gherkin(collapsed)


# ----------------------------------------------------------------------
# A doc-string after an empty step (keyword, no text)
# ----------------------------------------------------------------------
# The parser accepts ``Given `` or ``* `` with nothing after it as a step, and
# that step may carry a doc-string.

_DELIMITERS = {"backticks": "```", "double quotes": '"""'}


@pytest.mark.parametrize("delimiter_name", sorted(_DELIMITERS))
@pytest.mark.parametrize("keyword", ["Given ", "When  ", "And ", "* "])
@pytest.mark.parametrize("between", ["", "    # a comment\n\n"])
def test_docstring_after_an_empty_step_is_kept(
    keyword: str, delimiter_name: str, between: str
) -> None:
    delimiter = _DELIMITERS[delimiter_name]
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a first step\n"
        f"    {keyword}\n"
        f"{between}"
        f"      {delimiter}\n"
        "      Given payload\n"
        "        wrapped\n"
        "      Scenario: inside\n"
        f"      {delimiter}\n"
        "    Then done\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert steps[1]["text"] == ""
    assert steps[1]["docString"]["content"] == (
        "Given payload\n  wrapped\nScenario: inside"
    )


@pytest.mark.parametrize("delimiter_name", sorted(_DELIMITERS))
@pytest.mark.parametrize("keyword", ["* \t", "*  \t", "Given \t", "And  \t"])
def test_docstring_after_a_step_with_a_tab_before_its_text_is_kept(
    keyword: str, delimiter_name: str
) -> None:
    """``* `` then a tab then text is a step to the parser (the keyword is
    ``* `` and the text is trimmed), and may carry a doc-string."""
    delimiter = _DELIMITERS[delimiter_name]
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        f"    {keyword}body\n"
        f"      {delimiter}\n"
        "      Given payload\n"
        "        wrapped\n"
        f"      {delimiter}\n"
        "    Then done\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert steps[0]["text"] == "body"
    assert steps[0]["docString"]["content"] == "Given payload\n  wrapped"


def test_deeper_empty_step_with_a_docstring_is_not_joined() -> None:
    """An empty step indented under another step is its own step to the
    parser when a doc-string follows, so it is not joined."""
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a first step\n"
        "      And \n"
        "      ```\n"
        "      payload\n"
        "      ```\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    assert _parse(collapsed) == _parse(text)


def test_empty_step_without_a_docstring_is_its_own_step() -> None:
    """An empty step is a step of its own to the parser, so it is never
    joined onto the step above, even when indented under it. (Before, it
    was joined when indented under a step.)"""
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a first step\n"
        "      And \n"
        "      * \n"
        "    Then \n"
        "    And a wrapped\n"
        "      step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a first step\n"
        "      And \n"
        "      * \n"
        "    Then \n"
        "    And a wrapped step\n"
    )
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert [(s["keyword"], s["text"]) for s in steps] == [
        ("Given ", "a first step"),
        ("And ", ""),
        ("* ", ""),
        ("Then ", ""),
        ("And ", "a wrapped step"),
    ]


@pytest.mark.parametrize("line", ["* \tbody", "*  \tbody", "* \u00a0body", "And "])
def test_parser_step_under_a_step_is_not_joined(line: str) -> None:
    """A line the parser reads as a step (here ones the joining patterns do
    not recognise) is never joined onto the step above it."""
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a first step\n"
        f"      {line}\n"
        "    Then done\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert len(steps) == 3


# ----------------------------------------------------------------------
# A stray quote delimiter in a description is text
# ----------------------------------------------------------------------
# The parser opens a doc-string only after a step, whatever the delimiter. A
# stray quote line in a description used to start doc-string mode in the
# collapse; a later real doc-string's opening line then ended it, and the real
# content was read as structure and joined.


@pytest.mark.parametrize("where", ["Feature", "Scenario"])
@pytest.mark.parametrize(
    "stray, delimiter",
    [('"""', '"""'), ('"""json', '"""'), ("'''", "```"), ("```", '"""')],
)
def test_stray_delimiter_in_a_description_does_not_disturb_a_real_docstring(
    where: str, stray: str, delimiter: str
) -> None:
    if where == "Feature":
        head = ["Feature: Demo", "  Some description", f"  {stray}", "  Scenario: x"]
    else:
        head = ["Feature: Demo", "  Scenario: x", "    Some description", f"    {stray}"]
    # A stray three-single-quote line ends at the next such line, so the real
    # doc-string carries one for that case.
    marker = ["      '''"] if stray == "'''" else []
    lines = head + [
        "    Given the body",
        f"      {delimiter}",
        *marker,
        "      Given payload",
        "        wrapped",
        "      Scenario: inside",
        f"      {delimiter}",
        "    Then done",
    ]
    text = "\n".join(lines) + "\n"
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)
    scenario = _parse(collapsed)["feature"]["children"][0]["scenario"]
    content = "Given payload\n  wrapped\nScenario: inside"
    if marker:
        content = "'''\n" + content
    assert scenario["steps"][0]["docString"]["content"] == content


# ----------------------------------------------------------------------
# Lines are split on "\n" only, as the parser splits them
# ----------------------------------------------------------------------

_INLINE_BREAKS = {
    "lone carriage return": "\r",
    "form feed": "\x0c",
    "line separator U+2028": "\u2028",
    "next line U+0085": "\x85",
    "file separator U+001C": "\x1c",
}


@pytest.mark.parametrize("name", sorted(_INLINE_BREAKS))
def test_unicode_line_break_inside_a_docstring_does_not_close_it(name: str) -> None:
    sep = _INLINE_BREAKS[name]
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the body\n"
        "      ```\n"
        f"      text{sep}```\n"
        "      Given payload\n"
        "        wrapped\n"
        "      ```\n"
        "    Then done\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text
    validate_gherkin(collapsed)
    assert _parse(collapsed) == _parse(text)


@pytest.mark.parametrize("name", sorted(_INLINE_BREAKS))
def test_unicode_line_break_inside_a_step_keeps_the_step_whole(name: str) -> None:
    sep = _INLINE_BREAKS[name]
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        f"    Given a{sep}b step that\n"
        "      wraps\n"
        "    Then done\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Scenario: x\n"
        f"    Given a{sep}b step that wraps\n"
        "    Then done\n"
    )
    validate_gherkin(collapsed)


def test_crlf_and_missing_final_newline_are_kept() -> None:
    text = (
        "Feature: Demo\r\n"
        "  Scenario: x\r\n"
        "    Given a step that\r\n"
        "      wraps\r\n"
        "    Then the body\r\n"
        '      """\r\n'
        "      Given payload\r\n"
        "        wrapped\r\n"
        '      """'
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\r\n"
        "  Scenario: x\r\n"
        "    Given a step that wraps\r\n"
        "    Then the body\r\n"
        '      """\r\n'
        "      Given payload\r\n"
        "        wrapped\r\n"
        '      """'
    )
    validate_gherkin(collapsed)
    assert collapse_multi_line_steps("") == ""


def test_empty_step_looking_line_in_a_description_does_not_open_a_docstring() -> None:
    text = (
        "Feature: Demo\n"
        "  Given \n"
        "  ```\n"
        "  Scenario: x\n"
        "    Given a wrapped\n"
        "      step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Given \n"
        "  ```\n"
        "  Scenario: x\n"
        "    Given a wrapped step\n"
    )
    validate_gherkin(collapsed)


def test_backtick_docstring_after_a_comment_and_blank_line_still_opens() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the body\n"
        "    # a comment between the step and its doc-string\n"
        "\n"
        "      ```\n"
        "      Scenario: inside\n"
        "        indented\n"
        "      ```\n"
        "    Then a wrapped\n"
        "      step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == text.replace("Then a wrapped\n      step", "Then a wrapped step")
    validate_gherkin(collapsed)
    steps = _parse(collapsed)["feature"]["children"][0]["scenario"]["steps"]
    assert steps[0]["docString"]["content"] == "Scenario: inside\n  indented"


def test_backtick_line_after_a_data_table_is_not_a_docstring() -> None:
    """A step has a data table or a doc-string, never both; the parser reads
    a fence after a table as an error, and so must the collapsed text. The
    collapse still joins the wrapped step after it, so the only error left is
    the fence itself."""
    from gherkin.errors import CompositeParserException

    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the rows\n"
        "      | a |\n"
        "      ```\n"
        "    Then a wrapped\n"
        "      step\n"
    )
    collapsed = collapse_multi_line_steps(text)
    assert collapsed == (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the rows\n"
        "      | a |\n"
        "      ```\n"
        "    Then a wrapped step\n"
    )

    def error_lines(spec: str) -> List[int]:
        with pytest.raises(CompositeParserException) as raised:
            _parse(spec)
        return [error.location["line"] for error in raised.value.errors]

    # The original is refused at the fence (line 5) and at the wrapped
    # continuation (line 7); the collapsed text only at the fence.
    assert error_lines(text) == [5, 7]
    assert error_lines(collapsed) == [5]


# ----------------------------------------------------------------------
# 5. Specs with none of the newly recognised lines collapse as before
# ----------------------------------------------------------------------
# Each pair is (input, expected output). The expected output is what the
# collapse at commit 7e8844ec produced for the same input.

_UNCHANGED_SAMPLES = {
    "wrapped steps": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a long step that\n"
        "      wraps\n"
        "    # a comment\n"
        "    When another\n"
        "      wraps too\n"
        "    Then done\n",
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a long step that wraps\n"
        "    # a comment\n"
        "    When another wraps too\n"
        "    Then done\n",
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
        "      step\n",
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the text\n"
        '      """json\n'
        "      Scenario: inside\n"
        "        indented\n"
        '      """\n'
        "    Then a wrapped step\n",
    ),
    "single-quote block": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the text\n"
        "      '''\n"
        "      Scenario: inside\n"
        "      '''\n"
        "    Then done\n",
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the text\n"
        "      '''\n"
        "      Scenario: inside\n"
        "      '''\n"
        "    Then done\n",
    ),
    "inline backticks inside a step": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the reply contains ```code``` in the middle of\n"
        "      a wrapped step\n"
        "    Then done\n",
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the reply contains ```code``` in the middle of a wrapped step\n"
        "    Then done\n",
    ),
    "star bullet in a feature description": (
        "Feature: Demo\n"
        "  * a bullet that\n"
        "    wraps\n"
        "  Scenario: x\n"
        "    Given a\n"
        "      wrapped step\n",
        "Feature: Demo\n"
        "  * a bullet that\n"
        "    wraps\n"
        "  Scenario: x\n"
        "    Given a wrapped step\n",
    ),
    "unterminated triple-quote": (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given text\n"
        '      """\n'
        "      never closed\n"
        "    Then x\n"
        "      wraps\n",
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given text\n"
        '      """\n'
        "      never closed\n"
        "    Then x\n"
        "      wraps\n",
    ),
}


@pytest.mark.parametrize("name", sorted(_UNCHANGED_SAMPLES))
def test_sample_without_new_lines_collapses_as_before(name: str) -> None:
    text, expected = _UNCHANGED_SAMPLES[name]
    assert collapse_multi_line_steps(text) == expected
