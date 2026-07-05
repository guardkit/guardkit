"""TASK-AB-HERMETICTEST01 — hermetic-environment test guidance.

Pins the prompt/doc text requiring env-reading config tests to pin the FULL
relevant env-var surface with ``monkeypatch.setenv``/``delenv`` (ABL-001
run-3 lesson 4: the non-hermetic test was both flaky across hosts AND the
leak channel that printed a live DSN). Per
``.claude/rules/player-prompt-reinforce-coach-constraint-in-three-locations.md``
the constraint lands in THREE Player-prompt locations:

1. The test-writing workflow step in ``AgentInvoker._build_player_prompt``.
2. The anti-patterns entry in ``installer/core/agents/autobuild-player.md``
   (quoting the Coach's detection wording VERBATIM).
3. A grounding-principle paragraph in the same agent definition's
   test-discipline section.

Plus a Coach-side ADVISORY detection (guard #10 in
``AgentInvoker._render_absence_of_failure_guards``, category
``non_hermetic_env_test``, ``should_fix`` — never turn-rejecting on its
own), ``/feature-plan`` spec guidance to name the env surface, and the
operational note in the instrumentation guide (never run agent loops with
live credentials in the ambient environment).

Prompt-only by necessity (``structural-defence-beats-prompt-instruction``):
the structural halves are TASK-AB-SECRETSCRUB01 (the leak channel) and the
basetemp/venv isolation work; the SECRETSCRUB01 lint is the paired monitor.
This file asserts the text is wired in; it does NOT assert an LLM follows it.
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    HERMETIC_ENV_DETECTION_PHRASE,
)
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYER_AGENT_MD = (
    REPO_ROOT / "installer" / "core" / "agents" / "autobuild-player.md"
)
FEATURE_PLAN_MD = (
    REPO_ROOT / "installer" / "core" / "commands" / "feature-plan.md"
)
INSTRUMENTATION_GUIDE = (
    REPO_ROOT / "docs" / "guides" / "autobuild-instrumentation-guide.md"
)


def _build_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


def _minimal_bundle() -> CoachEvidenceBundle:
    return CoachEvidenceBundle(honesty=HonestyVerification(verified=True))


def _render_coach_prompt(tmp_path: Path) -> str:
    return _build_invoker(tmp_path)._build_coach_prompt(
        task_id="TASK-001",
        turn=1,
        requirements="Implement env-read configuration",
        player_report={"files_modified": []},
        evidence_bundle=_minimal_bundle(),
    )


# ---------------------------------------------------------------------------
# Location 1 — test-writing workflow step in _build_player_prompt
# ---------------------------------------------------------------------------


class TestPlayerPromptHermeticEnvConstraint:
    def test_player_prompt_contains_hermetic_env_constraint(
        self, tmp_path: Path
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement env-read configuration",
            feedback=None,
        )

        assert "hermetic-env" in prompt
        assert "monkeypatch.setenv/delenv" in prompt
        assert "FULL relevant env-var surface" in prompt
        assert "host environment" in prompt

    def test_constraint_lives_in_the_test_writing_step(
        self, tmp_path: Path
    ) -> None:
        """Same placement rule as INVARIANTTEST01: the constraint extends
        responsibility 2 (write tests), the section the Player re-reads."""
        prompt = _build_invoker(tmp_path)._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement env-read configuration",
            feedback=None,
        )

        responsibilities = prompt.split("## Your Responsibilities")[1]
        step_two = responsibilities.split("2. ")[1].split("3. ")[0]
        assert "hermetic-env" in step_two
        assert "comprehensive tests" in step_two


# ---------------------------------------------------------------------------
# Locations 2 + 3 — anti-patterns entry and grounding paragraph
# ---------------------------------------------------------------------------


class TestPlayerAgentDefinitionLocations:
    def test_anti_pattern_entry_quotes_coach_detection_wording_verbatim(
        self,
    ) -> None:
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        assert "## Anti-Patterns" in content
        assert HERMETIC_ENV_DETECTION_PHRASE in content
        assert "non_hermetic_env_test" in content
        assert "never turn-rejecting on its own" in content

    def test_grounding_paragraph_explains_why(self) -> None:
        """Location 3: non-hermetic tests are host-dependent AND a leak
        channel; the SECRETSCRUB01 lint is the named monitor."""
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        assert "Pin the environment surface (hermetic-env)" in content
        assert "not a test of the code" in content
        assert "ABL-001" in content
        # structural-defence rule: prompt-only levers name their monitor.
        assert "TASK-AB-SECRETSCRUB01" in content

    def test_localhost_fixture_pattern_stays_legitimate(self) -> None:
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")
        grounding_start = content.index("Pin the environment surface")
        grounding = content[grounding_start : grounding_start + 1200]
        assert "localhost/127.0.0.1" in grounding

    def test_shared_token_present_in_both_locations(self) -> None:
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")
        assert content.count("hermetic-env") >= 2


# ---------------------------------------------------------------------------
# Coach-side detection — guard #10 in _render_absence_of_failure_guards
# ---------------------------------------------------------------------------


class TestCoachPromptHermeticEnvGuard:
    def test_coach_prompt_contains_hermetic_env_guard(
        self, tmp_path: Path
    ) -> None:
        prompt = _render_coach_prompt(tmp_path)

        assert "HERMETIC-ENV ADVISORY GUARD" in prompt
        assert HERMETIC_ENV_DETECTION_PHRASE in prompt

    def test_guard_is_advisory_should_fix_never_turn_rejecting(
        self, tmp_path: Path
    ) -> None:
        prompt = _render_coach_prompt(tmp_path)
        guard_start = prompt.index("HERMETIC-ENV ADVISORY GUARD")
        guard_block = prompt[
            guard_start : prompt.index("</absence_of_failure_guards>")
        ]

        assert "should_fix" in guard_block
        assert '"non_hermetic_env_test"' in guard_block
        assert "NEVER reject the turn on this finding alone" in guard_block

    def test_guard_preserves_localhost_fixture_pattern(
        self, tmp_path: Path
    ) -> None:
        prompt = _render_coach_prompt(tmp_path)
        guard_start = prompt.index("HERMETIC-ENV ADVISORY GUARD")
        guard_block = prompt[
            guard_start : prompt.index("</absence_of_failure_guards>")
        ]
        assert "localhost/127.0.0.1" in guard_block

    def test_prior_guards_unchanged(self, tmp_path: Path) -> None:
        """Adding guard #10 must not disturb the existing guards — NO
        verdict-logic changes anywhere in this task."""
        prompt = _render_coach_prompt(tmp_path)

        for needle in (
            "1. ZERO-CARDINALITY BDD GUARD",
            "2. ZERO-CARDINALITY TEST GUARD",
            "3. SOPHISTICATED-LIE GUARD",
            "4. LAYER-1 PATH DEMOTION GUARD",
            "5. GATHERING-STATUS GUARD",
            "6. INDEPENDENT-TEST ABSENT GUARD",
            "7. WIRING-EVIDENCE ADVISORY GUARD",
            "8. TRANSIENT-ASSERTION ADVISORY GUARD",
            "9. STUB-SCAN ADVISORY GUARD",
        ):
            assert needle in prompt, f"pre-existing guard missing: {needle}"


# ---------------------------------------------------------------------------
# Cross-check — detection phrase byte-identical between Coach and Player
# ---------------------------------------------------------------------------


class TestDetectionPhraseByteIdentical:
    def test_phrase_is_single_line(self) -> None:
        assert "\n" not in HERMETIC_ENV_DETECTION_PHRASE

    def test_phrase_byte_identical_between_coach_guard_and_player_entry(
        self, tmp_path: Path
    ) -> None:
        coach_guards = _build_invoker(
            tmp_path
        )._render_absence_of_failure_guards()
        player_doc = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        assert HERMETIC_ENV_DETECTION_PHRASE in coach_guards
        assert HERMETIC_ENV_DETECTION_PHRASE in player_doc


# ---------------------------------------------------------------------------
# Planner guidance (AC-003) + operational note (AC-004)
# ---------------------------------------------------------------------------


class TestPlannerGuidance:
    def test_feature_plan_requires_naming_the_env_surface(self) -> None:
        content = FEATURE_PLAN_MD.read_text(encoding="utf-8")

        assert "hermetic-env" in content
        assert "name the full env-var surface" in content
        assert "monkeypatch.setenv" in content
        assert "TASK-AB-HERMETICTEST01" in content


class TestOperationalNote:
    def test_instrumentation_guide_forbids_live_creds_in_loop_env(
        self,
    ) -> None:
        content = INSTRUMENTATION_GUIDE.read_text(encoding="utf-8")

        assert (
            "Never Run Agent Loops With Live Credentials in the Ambient "
            "Environment" in content
        )
        assert "fixture" in content
        assert "TASK-AB-HERMETICTEST01" in content
        assert "TASK-AB-SECRETSCRUB01" in content
