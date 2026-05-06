"""End-to-end regression guard for ``/feature-spec`` Gherkin output (TASK-FSGS-001).

``/feature-spec`` is an LLM-driven prompt command — it has no Python entry
point we can call directly — so this integration test exercises the
*post-generation pipeline* the prompt now wires up: take a representative
LLM-emitted ``.feature`` body that includes wrapped step lines (the failure
shape from the study-tutor MCP-LCA feature on 2026-05-06), feed it through
``normalize_feature_file`` (the same call the prompt instructs Claude to
make immediately after writing the file in Phase 6), and assert the cleaned
output parses cleanly via the official ``gherkin`` parser used downstream
by ``/feature-plan`` Step 11.

If this regression guard ever fails, the pipeline cannot deliver a
parseable spec to the BDD linker and the next operator will hit the same
hard parser stop the user reported. Treat any failure here as a release
blocker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from installer.core.commands.lib.feature_spec_normalize import (
    FeatureSpecGherkinError,
    normalize_feature_file,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "feature_specs"


def _parse(text: str) -> None:
    """Parse via gherkin-official the same way bdd_linker does."""
    from gherkin.parser import Parser

    Parser().parse(text)


def test_e2e_normaliser_makes_studytutor_pre_fixture_parseable() -> None:
    """Real-world regression: the pre-fix study-tutor MCP-LCA feature
    parses cleanly *only* after passing through normalize_feature_file."""
    pre = (FIXTURES / "mcp-llm-player-coach-adapters_pre.feature").read_text(
        encoding="utf-8"
    )

    # Sanity: parser rejects the raw LLM output (otherwise the fixture
    # has drifted and this test proves nothing).
    with pytest.raises(Exception):
        _parse(pre)

    cleaned = normalize_feature_file(pre)

    # The wired-in normaliser must produce a parseable spec.
    _parse(cleaned)


def test_e2e_normaliser_handles_synthetic_long_step_brief() -> None:
    """Synthetic regression: a brief that always produces long step text
    (``As the platform team, I want a guarantee that ...``) ends up with
    every step on a single line after the wired-in normaliser runs."""
    # Shape mirrors what an LLM emits when the step text overflows ~70
    # chars and the model wraps to "stay readable". Includes a doc-string
    # and a Scenario Outline Examples table — both must survive verbatim.
    raw = (
        "@feat\n"
        "Feature: Long-step regression brief\n"
        "  As the platform team\n"
        "  I want every Given/When/Then to stay on a single physical line\n"
        "  So that /feature-plan Step 11 can parse the output\n"
        "\n"
        "  Background:\n"
        "    Given the orchestrator surfaces (PlayerLike, CoachLike,\n"
        "      PlayerCoachOrchestrator, validate_coach_config,\n"
        "      parse_coach_output) are unchanged from Phase-0\n"
        "    And the AGENT_MODELS__REASONING_MODEL env var configures the\n"
        "      Player provider via the standard pydantic-settings binding\n"
        "\n"
        "  @key-example @smoke\n"
        "  Scenario: A learner turn returns the Phase-1 metadata shape\n"
        "    Given the MCP server has booted with a working\n"
        "      orchestrator_factory exposed at module import time\n"
        "    When the learner sends a turn message via the MCP tutor_turn tool\n"
        "    Then the response should include a tutor_response, a decision,\n"
        "      a number of revision attempts, and a duration field\n"
        "\n"
        "  @docstring\n"
        "  Scenario: Doc-string survives normalisation\n"
        "    Given the operator submits the following payload:\n"
        '      """\n'
        "      first line of the doc\n"
        "        deeper indent inside the doc-string is fine\n"
        '      """\n'
        "    Then it is stored verbatim\n"
        "\n"
        "  @outline\n"
        "  Scenario Outline: Examples table survives normalisation\n"
        "    Given a request with parameter <p> and a really long\n"
        "      tail that wraps onto a second line\n"
        "    Then the result is <r>\n"
        "    Examples:\n"
        "      | p | r |\n"
        "      | 1 | a |\n"
        "      | 2 | b |\n"
    )

    # Sanity: the raw LLM output is not parseable.
    with pytest.raises(FeatureSpecGherkinError):
        from installer.core.commands.lib.feature_spec_normalize import validate_gherkin

        validate_gherkin(raw)

    cleaned = normalize_feature_file(raw)

    # Every step keyword must end up on one physical line.
    for line in cleaned.splitlines():
        stripped = line.lstrip()
        if any(
            stripped.startswith(kw + " ")
            for kw in ("Given", "When", "Then", "And", "But")
        ):
            # Step text contains no embedded newline — already implicit
            # from splitlines, but assert no empty step bodies either.
            assert stripped.split(None, 1)[1].strip()

    # Doc-string and Examples block survive verbatim.
    assert '      """\n' in cleaned
    assert "      | p | r |\n" in cleaned
    assert "      | 1 | a |\n" in cleaned

    # Result parses via the official parser.
    _parse(cleaned)
