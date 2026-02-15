"""
Unit tests for AutoBuild prompt builders.

Tests both implementation and design prompt builders to verify
correct protocol loading, context injection, and phase encoding.

Coverage Target: >=85%
Test Count: 30+ tests
"""

import sys
from pathlib import Path

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface
from guardkit.orchestrator.prompts import clear_cache


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear protocol cache before each test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def invoker(worktree_path):
    """Create AgentInvoker instance with temporary worktree."""
    return AgentInvoker(worktree_path=worktree_path)


@pytest.fixture
def interface(tmp_path):
    """Create TaskWorkInterface instance with temporary worktree."""
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return TaskWorkInterface(worktree)


# ============================================================================
# Implementation Prompt Builder Tests
# ============================================================================


class TestImplementationPromptBuilder:
    """Tests for _build_autobuild_implementation_prompt()."""

    def test_prompt_contains_task_id(self, invoker):
        """Verify prompt includes task ID in context section."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-ABC",
            requirements="Test requirements"
        )

        assert "TASK-ABC" in prompt
        assert "Task ID: TASK-ABC" in prompt

    def test_prompt_contains_requirements_section(self, invoker):
        """Verify prompt contains task requirements section."""
        requirements = "Implement OAuth2 authentication flow"
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements=requirements
        )

        assert "## Task Requirements" in prompt
        assert requirements in prompt

    def test_prompt_contains_execution_protocol(self, invoker):
        """Verify prompt contains execution protocol (phases 3-5)."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements"
        )

        # Must contain key phases
        assert "Phase 3" in prompt
        assert "Phase 4" in prompt
        assert "Phase 5" in prompt
        # Implementation phase is Phase 3
        assert "Implementation" in prompt

    def test_prompt_contains_player_report_schema(self, invoker):
        """Verify prompt contains PLAYER_REPORT_SCHEMA."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements"
        )

        assert "PLAYER_REPORT_SCHEMA" in prompt
        # Key fields should appear in schema
        assert "task_id" in prompt
        assert "turn" in prompt
        assert "files_modified" in prompt
        assert "tests_passed" in prompt

    def test_prompt_includes_coach_feedback_when_available(self, invoker):
        """Verify prompt includes Coach feedback when provided."""
        feedback = {
            "must_fix": ["Fix test failure in test_auth.py"],
            "should_fix": ["Add error handling"]
        }

        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=2,
            requirements="Test requirements",
            feedback=feedback
        )

        assert "## Coach Feedback from Turn 1" in prompt
        assert "must_fix" in prompt.lower() or "Fix test failure" in prompt

    def test_prompt_excludes_coach_feedback_on_turn_1(self, invoker):
        """Verify prompt excludes Coach feedback on first turn."""
        feedback = {"must_fix": ["Some feedback"]}

        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=1,
            requirements="Test requirements",
            feedback=feedback
        )

        # Should not include feedback section on turn 1
        assert "## Coach Feedback" not in prompt

    def test_prompt_includes_graphiti_context_when_available(self, invoker):
        """Verify prompt includes Graphiti context when provided."""
        context = "Previous work on authentication shows pattern X is preferred"

        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements",
            context=context
        )

        assert "## Job-Specific Context" in prompt
        assert context in prompt

    def test_prompt_excludes_graphiti_context_when_empty(self, invoker):
        """Verify prompt excludes Graphiti context when not provided."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements",
            context=""
        )

        assert "## Job-Specific Context" not in prompt

    def test_prompt_includes_turn_context(self, invoker):
        """Verify prompt includes turn context with current/max turns."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=3,
            max_turns=5,
            requirements="Test requirements"
        )

        assert "## Turn Context" in prompt
        assert "Current turn: 3" in prompt
        assert "Max turns: 5" in prompt
        assert "Turns remaining: 2" in prompt

    def test_prompt_shows_approaching_limit_warning(self, invoker):
        """Verify prompt shows warning when approaching turn limit."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=4,
            max_turns=5,
            requirements="Test requirements"
        )

        assert "Approaching limit: True" in prompt
        assert "WARNING" in prompt or "blocked_report" in prompt

    def test_prompt_respects_documentation_level(self, invoker):
        """Verify prompt includes documentation level in context."""
        for level in ["minimal", "standard", "comprehensive"]:
            prompt = invoker._build_autobuild_implementation_prompt(
                task_id="TASK-001",
                documentation_level=level,
                requirements="Test requirements"
            )

            assert f"Documentation Level: {level}" in prompt

    def test_prompt_respects_development_mode(self, invoker):
        """Verify prompt includes development mode (TDD/BDD/standard)."""
        for mode in ["standard", "tdd", "bdd"]:
            prompt = invoker._build_autobuild_implementation_prompt(
                task_id="TASK-001",
                mode=mode,
                requirements="Test requirements"
            )

            assert f"Mode: {mode}" in prompt

    def test_prompt_includes_worktree_path(self, invoker, worktree_path):
        """Verify prompt includes working directory path."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements"
        )

        assert "Working directory:" in prompt
        assert str(worktree_path) in prompt

    def test_prompt_substitutes_task_id_placeholder(self, invoker):
        """Verify {task_id} placeholder is substituted in protocol."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-XYZ",
            requirements="Test requirements"
        )

        # Placeholder should be replaced
        assert "{task_id}" not in prompt
        # Task ID should appear multiple times (context + protocol)
        assert prompt.count("TASK-XYZ") >= 2

    def test_prompt_substitutes_turn_placeholder(self, invoker):
        """Verify {turn} placeholder is substituted in protocol."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=3,
            requirements="Test requirements"
        )

        # Placeholder should be replaced
        assert "{turn}" not in prompt

    def test_prompt_includes_implementation_plan_locations(self, invoker):
        """Verify prompt includes implementation plan paths."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements"
        )

        assert "## Implementation Plan Locations" in prompt
        assert ".claude/task-plans/" in prompt or "implementation-plan" in prompt

    def test_prompt_string_feedback_handled(self, invoker):
        """Verify string feedback is handled correctly."""
        feedback = "Fix the authentication bug in login handler"

        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=2,
            requirements="Test requirements",
            feedback=feedback
        )

        assert "## Coach Feedback from Turn 1" in prompt
        assert feedback in prompt


# ============================================================================
# Implementation Prompt Edge Cases
# ============================================================================


class TestImplementationPromptEdgeCases:
    """Edge case tests for implementation prompt builder."""

    def test_empty_requirements_section_omitted(self, invoker):
        """Verify empty requirements section is omitted from prompt."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements=""
        )

        # Empty requirements should not create section
        assert "## Task Requirements" not in prompt

    def test_turn_1_with_max_turns_1_shows_approaching_limit(self, invoker):
        """Verify turn 1/1 shows approaching limit warning."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=1,
            max_turns=1,
            requirements="Test"
        )

        # Turn 1 with max 1 means turn >= max_turns - 1 (1 >= 0)
        assert "Approaching limit: True" in prompt

    def test_multiline_requirements_preserved(self, invoker):
        """Verify multiline requirements are preserved in prompt."""
        requirements = """Implement OAuth2 flow:
- Authorization code exchange
- Token refresh
- PKCE support"""

        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements=requirements
        )

        assert "Authorization code exchange" in prompt
        assert "Token refresh" in prompt
        assert "PKCE support" in prompt

    def test_none_feedback_handled_gracefully(self, invoker):
        """Verify None feedback is handled without errors."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=2,
            requirements="Test",
            feedback=None
        )

        # Should not crash, no feedback section
        assert "## Coach Feedback" not in prompt

    def test_dict_feedback_with_empty_values(self, invoker):
        """Verify dict feedback with empty lists is handled."""
        feedback = {"must_fix": [], "should_fix": []}

        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            turn=2,
            requirements="Test",
            feedback=feedback
        )

        # Should not crash (feedback formatting handles empty dicts)
        assert isinstance(prompt, str)


# ============================================================================
# Design Prompt Builder Tests
# ============================================================================


class TestDesignPromptBuilder:
    """Tests for _build_autobuild_design_prompt()."""

    def test_prompt_contains_task_id(self, interface):
        """Verify prompt includes task ID in header."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-ABC",
            options={}
        )

        assert "TASK-ABC" in prompt
        assert "AutoBuild design phase for task TASK-ABC" in prompt

    def test_prompt_contains_design_protocol(self, interface):
        """Verify prompt contains design protocol (phases 1.5-2.8)."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        # Must contain key phases
        assert "Phase 1.5" in prompt or "1.5" in prompt
        assert "Phase 2" in prompt
        assert "Phase 2.7" in prompt or "2.7" in prompt
        assert "Phase 2.8" in prompt or "2.8" in prompt

    def test_prompt_encodes_phase_skipping(self, interface):
        """Verify prompt encodes skipped phases (1.6, 2.1, 2.5A)."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        assert "Phase 1.6" in prompt and "SKIP" in prompt
        assert "Phase 2.1" in prompt and "SKIP" in prompt
        assert "Phase 2.5A" in prompt and "SKIP" in prompt

    def test_prompt_specifies_lightweight_2_5b(self, interface):
        """Verify prompt specifies lightweight 2.5B (no subagent)."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={"skip_arch_review": False}
        )

        assert "Phase 2.5B" in prompt
        assert "LIGHTWEIGHT" in prompt or "inline" in prompt.lower()
        assert "no subagent" in prompt.lower() or "NOT invoke a subagent" in prompt

    def test_prompt_specifies_auto_approve_2_8(self, interface):
        """Verify prompt specifies auto-approve for 2.8."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        assert "Phase 2.8" in prompt
        assert "AUTO-APPROVE" in prompt or "auto-approve" in prompt.lower()

    def test_prompt_includes_complexity_evaluation_criteria(self, interface):
        """Verify prompt includes complexity evaluation criteria."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        # Should contain Phase 2.7 with complexity
        assert "Complexity" in prompt
        # Should mention complexity scale
        assert "/10" in prompt or "1-10" in prompt or "complexity score" in prompt.lower()

    def test_prompt_includes_architectural_review_criteria(self, interface):
        """Verify prompt includes architectural review criteria."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={"skip_arch_review": False}
        )

        # Should contain architectural review section
        assert "Architectural" in prompt or "architectural" in prompt
        # Should mention SOLID or design principles
        assert "SOLID" in prompt or "Single Responsibility" in prompt or "architectural" in prompt.lower()

    def test_skip_arch_review_removes_phase_2_5b(self, interface):
        """Verify skip_arch_review option removes Phase 2.5B section."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={"skip_arch_review": True}
        )

        # Should document that 2.5B is skipped
        assert "Phase 2.5B" in prompt
        assert "SKIP" in prompt

        # Should not contain the full 2.5B section
        # The _strip_arch_review_section removes the ## Phase 2.5B section
        # But the header lists it as skipped
        # Count occurrences - should appear once in skip list, not as full section
        assert prompt.count("## Phase 2.5B") == 0

    def test_skip_arch_review_flag_in_header(self, interface):
        """Verify skip_arch_review flag is documented in header."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={"skip_arch_review": True}
        )

        assert "Phase 2.5B (Architectural Review): SKIP" in prompt

    def test_documentation_level_included_in_header(self, interface):
        """Verify documentation level appears in header."""
        for level in ["minimal", "standard", "comprehensive"]:
            prompt = interface._build_autobuild_design_prompt(
                task_id="TASK-001",
                options={"docs": level}
            )

            assert f"Documentation Level: {level}" in prompt

    def test_working_directory_included_in_header(self, interface):
        """Verify working directory appears in header."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        assert "Working Directory:" in prompt
        assert str(interface.worktree_path) in prompt

    def test_prompt_substitutes_task_id_placeholder(self, interface):
        """Verify {task_id} placeholder is substituted in protocol."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-XYZ",
            options={}
        )

        # Placeholder should be replaced
        assert "{task_id}" not in prompt
        # Task ID should appear in header and protocol
        assert "TASK-XYZ" in prompt

    def test_default_documentation_level_is_minimal(self, interface):
        """Verify default documentation level is minimal."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        assert "Documentation Level: minimal" in prompt

    def test_phase_execution_instructions_included(self, interface):
        """Verify prompt includes instructions to execute only non-skipped phases."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        assert "Execute ONLY the phases" in prompt or "execute" in prompt.lower()
        assert "not skipped" in prompt.lower() or "skip" in prompt.lower()


# ============================================================================
# Design Prompt Edge Cases
# ============================================================================


class TestDesignPromptEdgeCases:
    """Edge case tests for design prompt builder."""

    def test_empty_options_dict_handled(self, interface):
        """Verify empty options dict uses defaults."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        # Should use defaults: docs=minimal, skip_arch_review=False
        assert "Documentation Level: minimal" in prompt
        assert "Phase 2.5B (Architectural Review): LIGHTWEIGHT" in prompt

    def test_missing_docs_key_uses_default(self, interface):
        """Verify missing 'docs' key uses minimal default."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={"other_key": "value"}
        )

        assert "Documentation Level: minimal" in prompt

    def test_missing_skip_arch_review_uses_false(self, interface):
        """Verify missing 'skip_arch_review' key defaults to False."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        # Should show LIGHTWEIGHT, not SKIP
        assert "Phase 2.5B (Architectural Review): LIGHTWEIGHT" in prompt

    def test_strip_arch_review_section_removes_only_2_5b(self, interface):
        """Verify _strip_arch_review_section removes only Phase 2.5B."""
        test_protocol = """## Phase 2: Planning

Content here

## Phase 2.5B: Architectural Review

This should be removed
Including multiple lines
Until the next section

## Phase 2.7: Complexity

This should remain
"""

        result = interface._strip_arch_review_section(test_protocol)

        assert "## Phase 2: Planning" in result
        assert "## Phase 2.5B" not in result
        assert "This should be removed" not in result
        assert "## Phase 2.7: Complexity" in result
        assert "This should remain" in result

    def test_strip_arch_review_at_end_of_protocol(self, interface):
        """Verify _strip_arch_review_section handles 2.5B at end."""
        test_protocol = """## Phase 2: Planning

Content

## Phase 2.5B: Architectural Review

Last section content
No section after this
"""

        result = interface._strip_arch_review_section(test_protocol)

        assert "## Phase 2: Planning" in result
        assert "## Phase 2.5B" not in result
        assert "Last section content" not in result

    def test_strip_arch_review_no_2_5b_returns_unchanged(self, interface):
        """Verify _strip_arch_review_section returns protocol unchanged if no 2.5B."""
        test_protocol = """## Phase 2: Planning

Content

## Phase 2.7: Complexity

Content
"""

        result = interface._strip_arch_review_section(test_protocol)

        assert result == test_protocol


# ============================================================================
# Integration Tests
# ============================================================================


class TestPromptBuilderIntegration:
    """Integration tests verifying prompt builders work with real protocol files."""

    def test_implementation_prompt_loads_real_protocol(self, invoker):
        """Verify implementation builder loads real execution protocol file."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            requirements="Test requirements"
        )

        # Should contain content from actual protocol file
        assert "Phase 3: Implementation" in prompt
        assert "Phase 4: Testing" in prompt
        assert "PLAYER_REPORT_SCHEMA" in prompt
        assert len(prompt) > 1000  # Real protocol is substantial

    def test_design_prompt_loads_real_protocol(self, interface):
        """Verify design builder loads real design protocol file."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={}
        )

        # Should contain content from actual protocol file
        assert "Phase 1.5" in prompt or "Load Task Context" in prompt
        assert "Phase 2" in prompt
        assert "Implementation Planning" in prompt or "planning" in prompt.lower()
        assert len(prompt) > 1000  # Real protocol is substantial

    def test_implementation_prompt_complete_assembly(self, invoker):
        """Verify all sections assemble correctly in implementation prompt."""
        prompt = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-001",
            mode="tdd",
            documentation_level="standard",
            turn=2,
            requirements="Implement OAuth2 flow",
            feedback={"must_fix": ["Fix auth test"]},
            max_turns=5,
            context="Previous OAuth work used library X"
        )

        # All sections present
        assert "Task ID: TASK-001" in prompt
        assert "Mode: tdd" in prompt
        assert "Documentation Level: standard" in prompt
        assert "Current turn: 2" in prompt
        assert "## Task Requirements" in prompt
        assert "Implement OAuth2 flow" in prompt
        assert "## Coach Feedback from Turn 1" in prompt
        assert "## Job-Specific Context" in prompt
        assert "Previous OAuth work" in prompt
        assert "Phase 3" in prompt
        assert "## Implementation Plan Locations" in prompt

    def test_design_prompt_complete_assembly(self, interface):
        """Verify all sections assemble correctly in design prompt."""
        prompt = interface._build_autobuild_design_prompt(
            task_id="TASK-001",
            options={"docs": "comprehensive", "skip_arch_review": False}
        )

        # All sections present
        assert "AutoBuild design phase for task TASK-001" in prompt
        assert "Documentation Level: comprehensive" in prompt
        assert "Working Directory:" in prompt
        assert "AutoBuild Phase Decisions" in prompt
        assert "Phase 1.6" in prompt and "SKIP" in prompt
        assert "Phase 2.5B" in prompt and "LIGHTWEIGHT" in prompt
        assert "Phase 2.8" in prompt and "AUTO-APPROVE" in prompt
        assert "Phase 1.5" in prompt
        assert "Phase 2:" in prompt


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
