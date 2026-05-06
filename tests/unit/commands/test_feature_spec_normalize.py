"""Tests for installer/core/commands/lib/feature_spec_normalize.py (TASK-FSGS-001).

Covers the acceptance criteria from
``tasks/in_progress/feature-spec-gherkin-syntax/TASK-FSGS-001-...``:

- Single-line input is a no-op (idempotence base case)
- 2-line continuation (Background ``Given``)
- 3-line continuation with embedded quote
- Continuation followed by a comment (comment preserved at the right place)
- Continuation followed by another step (second step is not absorbed)
- Doc-string content is preserved verbatim, even when wrapped
- Table rows are preserved verbatim
- ``Scenario Outline`` ``Examples:`` block is preserved verbatim
- Real-world fixture: study-tutor ``mcp-llm-player-coach-adapters.feature``
- Idempotence (property test): collapse(collapse(x)) == collapse(x)
- ``validate_gherkin`` raises ``FeatureSpecGherkinError`` on bad input
- ``normalize_feature_file`` round-trip
- ``__main__`` CLI rewrites in place / no-ops on already-clean files

Coverage Target: >=85%
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from installer.core.commands.lib.feature_spec_normalize import (
    FeatureSpecGherkinError,
    collapse_multi_line_steps,
    normalize_feature_file,
    validate_gherkin,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "feature_specs"


# ----------------------------------------------------------------------
# 1. Idempotence base case — single-line input is a no-op
# ----------------------------------------------------------------------


def test_single_line_input_is_noop() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: Trivial\n"
        "    Given a registered user\n"
        "    When they sign in\n"
        "    Then a session is created\n"
    )
    assert collapse_multi_line_steps(text) == text


# ----------------------------------------------------------------------
# 2. Two-line continuation (Background Given)
# ----------------------------------------------------------------------


def test_two_line_background_given_collapses() -> None:
    text = (
        "Feature: Demo\n"
        "  Background:\n"
        "    Given the orchestrator surfaces (PlayerLike, CoachLike,\n"
        "      PlayerCoachOrchestrator) are unchanged from Phase-0\n"
        "  Scenario: x\n"
        "    Given y\n"
    )
    expected = (
        "Feature: Demo\n"
        "  Background:\n"
        "    Given the orchestrator surfaces (PlayerLike, CoachLike, "
        "PlayerCoachOrchestrator) are unchanged from Phase-0\n"
        "  Scenario: x\n"
        "    Given y\n"
    )
    assert collapse_multi_line_steps(text) == expected


# ----------------------------------------------------------------------
# 3. Three-line continuation with embedded quote
# ----------------------------------------------------------------------


def test_three_line_continuation_with_embedded_quote() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: emits message\n"
        "    Given the system is ready\n"
        '    When the operator types "the quick brown fox\n'
        "      jumps over\n"
        '      the lazy dog" into the prompt\n'
        "    Then it is echoed verbatim\n"
    )
    out = collapse_multi_line_steps(text)
    # The When line should now be a single line containing the full quoted
    # phrase joined with single spaces — punctuation preserved.
    assert (
        '    When the operator types "the quick brown fox jumps over '
        'the lazy dog" into the prompt\n'
    ) in out
    # And the surrounding steps survive untouched.
    assert "    Given the system is ready\n" in out
    assert "    Then it is echoed verbatim\n" in out


# ----------------------------------------------------------------------
# 4. Continuation followed by a comment line
# ----------------------------------------------------------------------


def test_continuation_followed_by_comment_preserves_comment() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a really long step that wraps onto\n"
        "      a second line for readability\n"
        "    # important domain note\n"
        "    When y happens\n"
        "    Then z holds\n"
    )
    out = collapse_multi_line_steps(text)
    lines = out.splitlines()
    # The collapsed step is one line, then the comment, then When.
    assert lines[2] == (
        "    Given a really long step that wraps onto a second line for readability"
    )
    assert lines[3] == "    # important domain note"
    assert lines[4] == "    When y happens"


# ----------------------------------------------------------------------
# 5. Continuation followed by another step is not absorbed
# ----------------------------------------------------------------------


def test_following_step_is_not_absorbed_into_prior() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a user signs in\n"
        "      with valid credentials\n"
        "    And another step on its own\n"
        "    Then they see the dashboard\n"
    )
    out = collapse_multi_line_steps(text)
    lines = out.splitlines()
    assert lines[2] == "    Given a user signs in with valid credentials"
    # The And step is preserved as its own step.
    assert "    And another step on its own" in lines
    assert "    Then they see the dashboard" in lines


def test_following_step_at_deeper_indent_is_not_absorbed() -> None:
    """A step keyword at the start of a line is always a new step, even
    if it happens to be more indented than the prior step."""
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given step one\n"
        "      And step two oddly indented\n"
    )
    out = collapse_multi_line_steps(text)
    # "And ..." line is treated as a new step, NOT absorbed into "Given".
    assert "    Given step one\n" in out
    assert "      And step two oddly indented\n" in out


# ----------------------------------------------------------------------
# 6. Doc-string content is preserved verbatim
# ----------------------------------------------------------------------


def test_docstring_content_is_not_collapsed() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given the operator submits the following:\n"
        '      """\n'
        "      first line of the doc\n"
        "        indented continuation that LOOKS like a step continuation\n"
        '      """\n'
        "    Then it is stored\n"
    )
    # collapse() must not touch anything inside the """ block.
    assert collapse_multi_line_steps(text) == text


# ----------------------------------------------------------------------
# 7. Table rows are preserved verbatim
# ----------------------------------------------------------------------


def test_table_rows_are_not_collapsed() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario Outline: x\n"
        "    Given <a> and <b>\n"
        "    Examples:\n"
        "      | a | b |\n"
        "      | 1 | 2 |\n"
        "      | 3 | 4 |\n"
    )
    assert collapse_multi_line_steps(text) == text


# ----------------------------------------------------------------------
# 8. Scenario Outline Examples block is preserved verbatim
# ----------------------------------------------------------------------


def test_scenario_outline_with_wrapped_step_collapses_only_the_step() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario Outline: long step still collapses\n"
        "    Given a request with parameter <p> and a really long\n"
        "      tail that wraps to a second line\n"
        "    Then the result is <r>\n"
        "    Examples:\n"
        "      | p | r |\n"
        "      | 1 | a |\n"
        "      | 2 | b |\n"
    )
    out = collapse_multi_line_steps(text)
    assert (
        "    Given a request with parameter <p> and a really long "
        "tail that wraps to a second line\n"
    ) in out
    # Examples table rows untouched
    assert "      | p | r |\n" in out
    assert "      | 1 | a |\n" in out


# ----------------------------------------------------------------------
# 9. Real-world fixture round-trip
# ----------------------------------------------------------------------


def test_studytutor_fixture_collapses_to_post_fix_form() -> None:
    """The pre-fix shape of the study-tutor MCP-LCA feature collapses to
    the post-fix Gherkin-valid form, exactly.

    Fixture provenance: ``mcp-llm-player-coach-adapters_post.feature`` is a
    verbatim copy of the file from
    ``study-tutor/features/mcp-llm-player-coach-adapters/`` after the user
    manually collapsed wrapped steps on 2026-05-06 to satisfy the parser
    used by ``/feature-plan`` Step 11. The pre-fix file was never
    committed to study-tutor (the directory was untracked when the user
    fixed it), so ``mcp-llm-player-coach-adapters_pre.feature`` is a
    deterministic re-wrapped reconstruction generated from the post-fix
    file by re-applying ~80-char word-boundary wrapping to every long
    step — i.e. the same shape an LLM emits when it wraps to "stay
    readable". This makes the fixture exercise the exact failure mode the
    normaliser exists to fix without depending on study-tutor's git
    history.
    """
    pre = (FIXTURES / "mcp-llm-player-coach-adapters_pre.feature").read_text(
        encoding="utf-8"
    )
    post = (FIXTURES / "mcp-llm-player-coach-adapters_post.feature").read_text(
        encoding="utf-8"
    )
    assert collapse_multi_line_steps(pre) == post


def test_studytutor_pre_fixture_is_not_parseable_until_collapsed() -> None:
    """Sanity guard: the pre-fix fixture must currently fail the official
    parser; otherwise the fixture has drifted and the test above proves
    nothing."""
    pre = (FIXTURES / "mcp-llm-player-coach-adapters_pre.feature").read_text(
        encoding="utf-8"
    )
    with pytest.raises(FeatureSpecGherkinError):
        validate_gherkin(pre)


# ----------------------------------------------------------------------
# 10. Idempotence (property test)
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "mcp-llm-player-coach-adapters_pre.feature",
        "mcp-llm-player-coach-adapters_post.feature",
    ],
)
def test_collapse_is_idempotent_on_fixtures(fixture_name: str) -> None:
    raw = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    once = collapse_multi_line_steps(raw)
    twice = collapse_multi_line_steps(once)
    assert once == twice


# ----------------------------------------------------------------------
# 11. validate_gherkin behaviour
# ----------------------------------------------------------------------


def test_validate_gherkin_passes_on_clean_text() -> None:
    text = (
        "Feature: Clean\n"
        "  Scenario: works\n"
        "    Given a thing\n"
        "    Then it works\n"
    )
    validate_gherkin(text)  # must not raise


def test_validate_gherkin_raises_on_wrapped_step() -> None:
    text = (
        "Feature: Bad\n"
        "  Scenario: wraps\n"
        "    Given a long step that wraps,\n"
        "      across two lines\n"
        "    Then it fails\n"
    )
    with pytest.raises(FeatureSpecGherkinError) as exc_info:
        validate_gherkin(text)
    # Error message must include the parser's location so an operator
    # can find the offending line.
    assert ":" in str(exc_info.value)


def test_normalize_feature_file_collapses_then_validates() -> None:
    text = (
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a long step that wraps,\n"
        "      across two lines\n"
        "    Then it works\n"
    )
    cleaned = normalize_feature_file(text)
    assert "wraps, across two lines\n" in cleaned
    # Result must now parse cleanly via the official parser.
    validate_gherkin(cleaned)


def test_normalize_feature_file_raises_when_collapse_cannot_save_it() -> None:
    """If the input has malformed Gherkin that wrapping doesn't explain
    (e.g. a stray top-level keyword), normalize_feature_file should still
    surface the parser failure rather than silently shipping garbage."""
    text = "Garbage Feature: not a feature\n"
    with pytest.raises(FeatureSpecGherkinError):
        normalize_feature_file(text)


# ----------------------------------------------------------------------
# 12. Line-ending preservation
# ----------------------------------------------------------------------


def test_crlf_line_endings_are_preserved() -> None:
    text = (
        "Feature: Demo\r\n"
        "  Scenario: x\r\n"
        "    Given a long step that wraps,\r\n"
        "      across two lines\r\n"
        "    Then it works\r\n"
    )
    out = collapse_multi_line_steps(text)
    assert "\r\n" in out
    # The collapsed step keeps the prior line's CRLF ending.
    assert (
        "    Given a long step that wraps, across two lines\r\n" in out
    )


# ----------------------------------------------------------------------
# 13. CLI entry point
# ----------------------------------------------------------------------


def test_cli_rewrites_wrapped_file_in_place(tmp_path: Path) -> None:
    f = tmp_path / "demo.feature"
    f.write_text(
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a long step that wraps,\n"
        "      across two lines\n"
        "    Then it works\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.core.commands.lib.feature_spec_normalize",
            str(f),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2].parent),
    )
    assert proc.returncode == 0, proc.stderr
    assert "normalised" in proc.stdout
    assert (
        "    Given a long step that wraps, across two lines\n"
        in f.read_text(encoding="utf-8")
    )


def test_cli_no_op_on_already_clean_file(tmp_path: Path) -> None:
    f = tmp_path / "clean.feature"
    f.write_text(
        "Feature: Demo\n"
        "  Scenario: x\n"
        "    Given a clean step\n"
        "    Then it works\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.core.commands.lib.feature_spec_normalize",
            str(f),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2].parent),
    )
    assert proc.returncode == 0
    assert "already clean" in proc.stdout


def test_cli_returns_2_on_missing_path(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.core.commands.lib.feature_spec_normalize",
            str(tmp_path / "does-not-exist.feature"),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2].parent),
    )
    assert proc.returncode == 2
    assert "file not found" in proc.stderr


def test_cli_returns_2_on_no_args() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.core.commands.lib.feature_spec_normalize",
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2].parent),
    )
    assert proc.returncode == 2
    assert "usage" in proc.stderr


def test_cli_returns_1_on_unparseable_input(tmp_path: Path) -> None:
    f = tmp_path / "bad.feature"
    f.write_text("Garbage Feature: not a feature\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "installer.core.commands.lib.feature_spec_normalize",
            str(f),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2].parent),
    )
    assert proc.returncode == 1
    assert "does not parse" in proc.stderr or "expected" in proc.stderr
