"""TASK-AB-INVARIANTTEST01 — transient-assertion ("invariant-not-snapshot") guidance.

Pins the prompt/doc text that discourages self-defeating snapshot tests
(e.g. asserting a method raises NotImplementedError when a later task in
the SAME feature implements it — the FEAT-SMP-001 SMP-03/SMP-04 failure
shape). Per
``.claude/rules/player-prompt-reinforce-coach-constraint-in-three-locations.md``
the constraint must land in THREE Player-prompt locations:

1. The test-writing workflow step in ``AgentInvoker._build_player_prompt``.
2. The anti-patterns entry in ``installer/core/agents/autobuild-player.md``
   (quoting the Coach's detection wording VERBATIM).
3. A grounding-principle paragraph in the same agent definition's
   test-discipline section.

Plus a Coach-side ADVISORY detection (guard #8 in
``AgentInvoker._render_absence_of_failure_guards``, category
``transient_assertion``, ``should_fix`` — never turn-rejecting on its own)
and ``/feature-plan`` spec guidance to name boundaries negatively.

This file asserts the text is *wired into the prompts/docs*; it does NOT
assert an LLM follows it (the TASK-AB-STALEATTRIB01 authorship join is the
runtime monitor for non-compliance).
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    TRANSIENT_ASSERTION_DETECTION_PHRASE,
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
CLASSIFICATION_GUIDE = (
    REPO_ROOT / "docs" / "guides" / "feature-plan-task-classification.md"
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _build_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


def _minimal_bundle() -> CoachEvidenceBundle:
    """Smallest bundle that makes _build_coach_prompt render the guards."""
    return CoachEvidenceBundle(honesty=HonestyVerification(verified=True))


def _render_coach_prompt(tmp_path: Path) -> str:
    return _build_invoker(tmp_path)._build_coach_prompt(
        task_id="TASK-001",
        turn=1,
        requirements="Implement the scaffold",
        player_report={"files_modified": []},
        evidence_bundle=_minimal_bundle(),
    )


# ---------------------------------------------------------------------------
# Location 1 — test-writing workflow step in _build_player_prompt
# ---------------------------------------------------------------------------


class TestPlayerPromptInvariantConstraint:
    """The Player's focused prompt must carry the invariant-not-snapshot
    constraint in the test-writing responsibility (location 1 of the
    three-locations rule)."""

    def test_player_prompt_contains_invariant_not_snapshot_constraint(
        self, tmp_path: Path,
    ) -> None:
        prompt = _build_invoker(tmp_path)._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement the scaffold",
            feedback=None,
        )

        assert "invariant-not-snapshot" in prompt
        assert "LASTING INVARIANTS" in prompt
        assert "NotImplementedError" in prompt
        assert "later task in THIS feature" in prompt
        # The escape hatch: a boundary pin must be scoped to what NO task in
        # the feature will implement, naming the owning task.
        assert "NO task in this feature will implement" in prompt

    def test_constraint_lives_in_the_test_writing_step(
        self, tmp_path: Path,
    ) -> None:
        """The constraint extends responsibility 2 (write tests), not some
        unrelated section the Player may never re-read."""
        prompt = _build_invoker(tmp_path)._build_player_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Implement the scaffold",
            feedback=None,
        )

        responsibilities = prompt.split("## Your Responsibilities")[1]
        step_two = responsibilities.split("2. ")[1].split("3. ")[0]
        assert "invariant-not-snapshot" in step_two
        assert "comprehensive tests" in step_two


# ---------------------------------------------------------------------------
# Locations 2 + 3 — anti-patterns entry and grounding paragraph in
# installer/core/agents/autobuild-player.md
# ---------------------------------------------------------------------------


class TestPlayerAgentDefinitionLocations:
    """The agent definition must carry the anti-patterns entry (location 2,
    quoting the Coach's detection wording verbatim) and the grounding
    paragraph (location 3)."""

    def test_agent_definition_exists(self) -> None:
        assert PLAYER_AGENT_MD.exists(), (
            f"Player agent definition not found at {PLAYER_AGENT_MD}"
        )

    def test_anti_pattern_entry_quotes_coach_detection_wording_verbatim(
        self,
    ) -> None:
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        assert "## Anti-Patterns" in content
        # The load-bearing requirement of the three-locations rule: the
        # anti-patterns entry names the EXACT detection pattern the Coach
        # uses, so the Player recognises the failure in the Coach's terms.
        assert TRANSIENT_ASSERTION_DETECTION_PHRASE in content
        assert "transient_assertion" in content
        assert "should_fix" in content
        # Advisory posture must be stated (never turn-rejecting on its own).
        assert "never turn-rejecting on its own" in content

    def test_anti_pattern_entry_preserves_anti_stub_compatibility(
        self,
    ) -> None:
        """The wording targets TESTS that pin stubs, not the stubs
        themselves (stub implementations in scaffold tasks stay legitimate
        per .claude/rules/anti-stub.md)."""
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        assert "anti-stub.md" in content
        assert "not the\nstubs themselves" in content or (
            "not the stubs themselves" in content.replace("\n", " ")
        )

    def test_grounding_paragraph_explains_why(self) -> None:
        """Location 3: the grounding-principle paragraph in the testing
        guidelines — later tasks exist to make snapshot assertions false,
        and a snapshot test burns the WRONG task's turn budget."""
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        assert "Test invariants, not snapshots (invariant-not-snapshot)" in content
        assert "burns the WRONG task's" in content
        # Prompt-only levers need monitoring (structural-defence rule):
        # the authorship join is the named monitor.
        assert "TASK-AB-STALEATTRIB01" in content

    def test_shared_token_present_in_locations_two_and_three(self) -> None:
        """AC-006: the grep-able ``invariant-not-snapshot`` token appears in
        both agent-definition locations (the workflow-step location is
        covered by the prompt-builder tests above)."""
        content = PLAYER_AGENT_MD.read_text(encoding="utf-8")
        assert content.count("invariant-not-snapshot") >= 2


# ---------------------------------------------------------------------------
# Coach-side detection — guard #8 in _render_absence_of_failure_guards
# ---------------------------------------------------------------------------


class TestCoachPromptTransientAssertionGuard:
    """The Coach prompt must carry the advisory transient-assertion guard
    with the same detection wording the Player anti-pattern quotes."""

    def test_coach_prompt_contains_transient_assertion_guard(
        self, tmp_path: Path,
    ) -> None:
        prompt = _render_coach_prompt(tmp_path)

        assert "TRANSIENT-ASSERTION ADVISORY GUARD" in prompt
        assert "invariant-not-snapshot" in prompt
        assert TRANSIENT_ASSERTION_DETECTION_PHRASE in prompt

    def test_guard_is_advisory_should_fix_never_turn_rejecting(
        self, tmp_path: Path,
    ) -> None:
        prompt = _render_coach_prompt(tmp_path)
        guard_start = prompt.index("TRANSIENT-ASSERTION ADVISORY GUARD")
        guard_block = prompt[guard_start:prompt.index(
            "</absence_of_failure_guards>"
        )]

        assert "should_fix" in guard_block
        assert '"transient_assertion"' in guard_block
        assert "NEVER reject the turn on this finding alone" in guard_block

    def test_guard_scopes_later_task_judgement_to_visible_context(
        self, tmp_path: Path,
    ) -> None:
        """The Coach prompt has no feature task list, so the guard must be
        scoped to what the Coach can see: the task's own scope statement,
        requirements, and acceptance criteria."""
        prompt = _render_coach_prompt(tmp_path)
        guard_start = prompt.index("TRANSIENT-ASSERTION ADVISORY GUARD")
        guard_block = prompt[guard_start:prompt.index(
            "</absence_of_failure_guards>"
        )]

        assert "scope statement" in guard_block
        assert "acceptance" in guard_block

    def test_guard_preserves_anti_stub_compatibility(
        self, tmp_path: Path,
    ) -> None:
        prompt = _render_coach_prompt(tmp_path)
        guard_start = prompt.index("TRANSIENT-ASSERTION ADVISORY GUARD")
        guard_block = prompt[guard_start:]

        assert "anti-stub.md" in guard_block
        assert "not the stubs themselves" in guard_block

    def test_prior_guards_unchanged(self, tmp_path: Path) -> None:
        """Adding guard #8 must not disturb the existing seven guards —
        NO verdict-logic changes anywhere in this task."""
        prompt = _render_coach_prompt(tmp_path)

        for needle in (
            "1. ZERO-CARDINALITY BDD GUARD",
            "2. ZERO-CARDINALITY TEST GUARD",
            "3. SOPHISTICATED-LIE GUARD",
            "4. LAYER-1 PATH DEMOTION GUARD",
            "5. GATHERING-STATUS GUARD",
            "6. INDEPENDENT-TEST ABSENT GUARD",
            "7. WIRING-EVIDENCE ADVISORY GUARD",
        ):
            assert needle in prompt, f"pre-existing guard missing: {needle}"


# ---------------------------------------------------------------------------
# Cross-check — detection phrase byte-identical between Coach and Player
# ---------------------------------------------------------------------------


class TestDetectionPhraseByteIdentical:
    """Per the three-locations rule, the anti-patterns entry must quote the
    Coach's detection wording VERBATIM — byte-identical, not paraphrased."""

    def test_phrase_is_single_line(self) -> None:
        """A newline inside the phrase would defeat single-line grep audits
        and the markdown-table quoting below."""
        assert "\n" not in TRANSIENT_ASSERTION_DETECTION_PHRASE

    def test_phrase_byte_identical_between_coach_guard_and_player_entry(
        self, tmp_path: Path,
    ) -> None:
        coach_guards = _build_invoker(
            tmp_path
        )._render_absence_of_failure_guards()
        player_doc = PLAYER_AGENT_MD.read_text(encoding="utf-8")

        # Both surfaces carry the exact same bytes (via the shared
        # TRANSIENT_ASSERTION_DETECTION_PHRASE constant on the Coach side).
        assert TRANSIENT_ASSERTION_DETECTION_PHRASE in coach_guards
        assert TRANSIENT_ASSERTION_DETECTION_PHRASE in player_doc


# ---------------------------------------------------------------------------
# Planner guidance — feature-plan.md + classification guide (AC-003)
# ---------------------------------------------------------------------------


class TestPlannerGuidance:
    """/feature-plan task-spec authoring must instruct specs to name
    boundaries NEGATIVELY, and the classification guide gains Class D."""

    def test_feature_plan_names_boundaries_negatively(self) -> None:
        content = FEATURE_PLAN_MD.read_text(encoding="utf-8")

        assert "invariant-not-snapshot" in content
        assert (
            "assert NotImplementedError ONLY for methods out of scope for "
            "the WHOLE feature" in content
        )
        assert "never for methods a later task in this feature implements" in content
        # anti-stub compatibility on the planner side too.
        assert "anti-stub.md" in content

    def test_classification_guide_gains_class_d(self) -> None:
        content = CLASSIFICATION_GUIDE.read_text(encoding="utf-8")

        assert "Class D" in content
        assert "invariant-not-snapshot" in content
        assert "TASK-AB-STALEATTRIB01" in content
        assert "TASK-AB-INVARIANTTEST01" in content
