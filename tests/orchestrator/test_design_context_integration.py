"""
Comprehensive Test Suite for Design Context Integration in Player-Coach Prompts

Tests integration of DesignContext into:
- Player prompt generation (_build_player_prompt)
- Coach prompt generation (_build_coach_prompt)
- TurnRecord dataclass extension for visual verification tracking

Coverage Target: >=85%
Test Count: 11 tests
Phase: TDD RED (tests will FAIL until implementation exists)
"""

import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.autobuild import DesignContext, TurnRecord


# ============================================================================
# 1. Fixtures
# ============================================================================


@pytest.fixture
def sample_design_context():
    """
    Create sample DesignContext for testing prompt injection.

    Represents a typical Figma design export with:
    - Component elements (Button, Input)
    - Design tokens (colors, spacing)
    - Prohibition checklist constraints
    - Visual reference URL
    """
    return DesignContext(
        elements=[
            {
                "name": "Button",
                "type": "component",
                "props": ["variant", "size"],
                "variants": ["primary", "secondary"],
            },
            {
                "name": "Input",
                "type": "component",
                "props": ["placeholder", "type"],
            },
        ],
        tokens={
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#10B981",
                "background": "#FFFFFF",
            },
            "spacing": {"sm": "8px", "md": "16px", "lg": "24px"},
            "typography": {"fontFamily": "Inter", "fontSize": {"base": "16px"}},
        },
        constraints={
            "no_shadcn_icons": True,
            "exact_colors_only": True,
            "no_additional_components": True,
            "strict_spacing": True,
        },
        visual_reference="https://figma.com/api/v1/images/abc123",
        summary="Button and Input components with blue/green color palette. Uses Inter font family.",
        source="figma",
        metadata={
            "file_key": "abc123",
            "node_id": "2:2",
            "extracted_at": "2026-02-08T12:00:00Z",
        },
    )


@pytest.fixture
def mock_agent_invoker():
    """
    Mock AgentInvoker instance for testing prompt methods.

    Returns a minimal mock that allows testing _build_player_prompt
    and _build_coach_prompt methods in isolation.
    """
    # Import here to avoid circular dependency
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    # Create mock with minimal required attributes
    invoker = Mock(spec=AgentInvoker)

    # Make _build_player_prompt and _build_coach_prompt real methods
    # bound to the mock instance
    invoker._build_player_prompt = AgentInvoker._build_player_prompt.__get__(
        invoker, AgentInvoker
    )
    invoker._build_coach_prompt = AgentInvoker._build_coach_prompt.__get__(
        invoker, AgentInvoker
    )

    # Make helper methods real as well (needed for design context formatting)
    invoker._format_design_elements = AgentInvoker._format_design_elements.__get__(
        invoker, AgentInvoker
    )
    invoker._format_design_tokens = AgentInvoker._format_design_tokens.__get__(
        invoker, AgentInvoker
    )
    invoker._format_design_constraints = AgentInvoker._format_design_constraints.__get__(
        invoker, AgentInvoker
    )

    return invoker


@pytest.fixture
def sample_player_report():
    """Sample Player report for Coach prompt testing."""
    return {
        "task_id": "TASK-DM-007",
        "turn": 1,
        "files_modified": ["src/components/Button.tsx"],
        "files_created": ["src/components/Input.tsx"],
        "tests_written": ["tests/components/Button.test.tsx"],
        "tests_run": True,
        "tests_passed": True,
        "test_output_summary": "All tests passed (3/3)",
        "implementation_notes": "Implemented Button and Input per design spec",
        "concerns": [],
        "requirements_addressed": ["REQ-001: Button component"],
        "requirements_remaining": [],
    }


# ============================================================================
# 2. Player Prompt Design Context Tests (5 tests)
# ============================================================================


def test_player_prompt_includes_design_context_when_available(
    mock_agent_invoker, sample_design_context
):
    """
    Test that Player prompt includes design_context section when DesignContext provided.

    EXPECTED BEHAVIOR (not yet implemented):
    - _build_player_prompt accepts optional design_context parameter
    - When design_context is provided, prompt includes "## Design Context" section
    - Section appears before requirements
    - Includes source attribution

    RED PHASE: This test will FAIL because:
    - _build_player_prompt doesn't have design_context parameter yet
    - No design context injection logic exists
    """
    prompt = mock_agent_invoker._build_player_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        feedback=None,
        acceptance_criteria=None,
        context="",
        design_context=sample_design_context,  # NEW PARAMETER - will cause failure
    )

    # Verify design context section exists
    assert "## Design Context" in prompt
    assert "**Source**: figma" in prompt

    # Verify section appears before requirements (context positioning)
    design_idx = prompt.index("## Design Context")
    req_idx = prompt.index("## Requirements")
    assert design_idx < req_idx, "Design context should appear before requirements"


def test_player_prompt_includes_design_elements_in_context(
    mock_agent_invoker, sample_design_context
):
    """
    Test that Player prompt includes formatted list of design elements.

    EXPECTED BEHAVIOR (not yet implemented):
    - Elements section lists all components from design
    - Each element shows: name, type, props
    - Formatted as readable markdown list

    RED PHASE: This test will FAIL because:
    - Element formatting logic doesn't exist
    - No "### Elements in Design" section
    """
    prompt = mock_agent_invoker._build_player_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        feedback=None,
        design_context=sample_design_context,
    )

    # Verify elements section exists
    assert "### Elements in Design" in prompt

    # Verify specific elements are listed
    assert "Button" in prompt
    assert "Input" in prompt
    assert "component" in prompt

    # Verify element details are included (props, variants)
    assert "variant" in prompt or "size" in prompt  # Button props
    assert "placeholder" in prompt or "type" in prompt  # Input props


def test_player_prompt_includes_design_tokens_in_context(
    mock_agent_invoker, sample_design_context
):
    """
    Test that Player prompt includes formatted design tokens.

    EXPECTED BEHAVIOR (not yet implemented):
    - Tokens section shows colors, spacing, typography
    - Formatted as structured data (JSON or markdown)
    - Exact values visible (no approximation)

    RED PHASE: This test will FAIL because:
    - Token formatting logic doesn't exist
    - No "### Design Tokens" section
    """
    prompt = mock_agent_invoker._build_player_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        feedback=None,
        design_context=sample_design_context,
    )

    # Verify tokens section exists
    assert "### Design Tokens" in prompt

    # Verify specific token categories
    assert "colors" in prompt.lower() or "Colors" in prompt
    assert "spacing" in prompt.lower() or "Spacing" in prompt

    # Verify exact token values are present (critical for exact match)
    assert "#3B82F6" in prompt  # primary color
    assert "#10B981" in prompt  # secondary color
    assert "8px" in prompt or "16px" in prompt  # spacing values


def test_player_prompt_includes_prohibition_checklist(
    mock_agent_invoker, sample_design_context
):
    """
    Test that Player prompt includes prohibition checklist as design boundaries.

    EXPECTED BEHAVIOR (not yet implemented):
    - Constraints formatted as "Design Boundaries" or "Prohibition Checklist"
    - Each constraint shown as a boundary rule
    - Clear instructions: DON'T add what's not in design

    RED PHASE: This test will FAIL because:
    - Constraint formatting doesn't exist
    - No prohibition checklist section
    """
    prompt = mock_agent_invoker._build_player_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        feedback=None,
        design_context=sample_design_context,
    )

    # Verify boundaries section exists
    assert (
        "### Design Boundaries" in prompt
        or "### Prohibition Checklist" in prompt
    )

    # Verify specific constraints are mentioned
    assert "no_shadcn_icons" in prompt or "shadcn" in prompt.lower()
    assert "exact_colors_only" in prompt or "exact" in prompt.lower()

    # Verify instructions emphasize boundaries
    assert "DO NOT" in prompt or "Don't" in prompt or "MUST NOT" in prompt

    # Verify instruction to not add unlisted components
    prompt_lower = prompt.lower()
    assert (
        "not shown in the design" in prompt_lower
        or "not in the design" in prompt_lower
        or "exactly" in prompt_lower
    )


def test_player_prompt_unchanged_when_no_design_context(
    mock_agent_invoker,
):
    """
    Test backward compatibility: prompt unchanged when design_context=None.

    EXPECTED BEHAVIOR (not yet implemented):
    - When design_context=None, prompt is identical to current behavior
    - No design context sections appear
    - No errors or placeholder text

    RED PHASE: This test will PASS initially but verifies regression prevention.
    """
    # Generate prompt without design context
    prompt_without = mock_agent_invoker._build_player_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        feedback=None,
        design_context=None,  # Explicitly no design context
    )

    # Verify no design context sections
    assert "## Design Context" not in prompt_without
    assert "### Elements in Design" not in prompt_without
    assert "### Design Tokens" not in prompt_without
    assert "### Design Boundaries" not in prompt_without
    assert "### Prohibition Checklist" not in prompt_without

    # Verify standard sections still exist
    assert "## Requirements" in prompt_without
    assert "## Your Responsibilities" in prompt_without


# ============================================================================
# 3. Coach Prompt Visual Verification Tests (3 tests)
# ============================================================================


def test_coach_prompt_includes_visual_verification_when_design_context(
    mock_agent_invoker, sample_design_context, sample_player_report
):
    """
    Test that Coach prompt includes visual verification section when design context present.

    EXPECTED BEHAVIOR (not yet implemented):
    - _build_coach_prompt accepts optional design_context parameter
    - When design_context provided, includes "## Visual Verification (Design Mode)"
    - Instructions to render, screenshot, compare with SSIM
    - Quality gates: >=95% SSIM, zero violations

    RED PHASE: This test will FAIL because:
    - _build_coach_prompt doesn't have design_context parameter
    - No visual verification section exists
    """
    prompt = mock_agent_invoker._build_coach_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        player_report=sample_player_report,
        honesty_verification=None,
        acceptance_criteria=None,
        design_context=sample_design_context,  # NEW PARAMETER - will cause failure
    )

    # Verify visual verification section exists
    assert "## Visual Verification" in prompt or "Visual Verification" in prompt
    assert "Design Mode" in prompt or "design context" in prompt.lower()

    # Verify instructions include key steps
    prompt_lower = prompt.lower()
    assert "render" in prompt_lower or "screenshot" in prompt_lower
    assert "compare" in prompt_lower or "ssim" in prompt_lower

    # Verify visual reference mentioned
    assert (
        "design reference" in prompt_lower
        or "visual reference" in prompt_lower
        or sample_design_context.visual_reference in prompt
    )


def test_coach_prompt_includes_quality_gates_for_design(
    mock_agent_invoker, sample_design_context, sample_player_report
):
    """
    Test that Coach prompt includes specific quality gates for design verification.

    EXPECTED BEHAVIOR (not yet implemented):
    - Visual fidelity gate: >=95% SSIM match
    - Constraint violations: Zero tolerance
    - Design token application: 100% exact match
    - Clear pass/fail thresholds

    RED PHASE: This test will FAIL because:
    - Quality gates section doesn't exist
    - No SSIM threshold mentioned
    """
    prompt = mock_agent_invoker._build_coach_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        player_report=sample_player_report,
        design_context=sample_design_context,
    )

    # Verify quality gates section
    assert "Quality Gates" in prompt or "quality gate" in prompt.lower()

    # Verify SSIM threshold
    assert "95%" in prompt or "95" in prompt  # SSIM threshold
    assert "SSIM" in prompt or "similarity" in prompt.lower()

    # Verify constraint violation threshold
    assert "zero" in prompt.lower() or "Zero" in prompt
    assert "violation" in prompt.lower() or "Violation" in prompt

    # Verify design token exactness requirement
    assert "100%" in prompt or "exact" in prompt.lower()
    assert "token" in prompt.lower()


def test_coach_prompt_unchanged_when_no_design_context(
    mock_agent_invoker, sample_player_report
):
    """
    Test backward compatibility: Coach prompt unchanged when design_context=None.

    EXPECTED BEHAVIOR (not yet implemented):
    - When design_context=None, prompt identical to current behavior
    - No visual verification sections
    - Standard validation only

    RED PHASE: This test will PASS initially but verifies regression prevention.
    """
    prompt = mock_agent_invoker._build_coach_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        player_report=sample_player_report,
        honesty_verification=None,
        acceptance_criteria=None,
        design_context=None,  # Explicitly no design context
    )

    # Verify no visual verification sections
    assert "Visual Verification" not in prompt
    assert "SSIM" not in prompt
    assert "screenshot" not in prompt.lower()

    # Verify standard sections still exist
    assert "## Your Responsibilities" in prompt
    assert "## Decision Format" in prompt


# ============================================================================
# 4. TurnRecord Extension Tests (3 tests)
# ============================================================================


def test_turn_record_has_visual_verification_field():
    """
    Test that TurnRecord has optional visual_verification field.

    EXPECTED BEHAVIOR (not yet implemented):
    - TurnRecord dataclass has visual_verification: Optional[Dict[str, Any]]
    - Field accepts visual comparison results
    - Field is optional (None if no design context)

    RED PHASE: This test will FAIL because:
    - visual_verification field doesn't exist on TurnRecord
    - Will raise AttributeError when accessed
    """
    from guardkit.orchestrator.autobuild import AgentInvocationResult

    # Create mock invocation results
    player_result = Mock(spec=AgentInvocationResult)
    coach_result = Mock(spec=AgentInvocationResult)

    # Create TurnRecord with visual verification data
    visual_verification = {
        "ssim_score": 0.97,
        "visual_reference": "https://figma.com/api/v1/images/abc123",
        "screenshot_path": "/tmp/screenshot.png",
        "passed": True,
    }

    turn = TurnRecord(
        turn=1,
        player_result=player_result,
        coach_result=coach_result,
        decision="approve",
        feedback=None,
        timestamp="2026-02-08T12:00:00Z",
        visual_verification=visual_verification,  # NEW FIELD - will cause failure
    )

    # Verify field is accessible and stored correctly
    assert hasattr(turn, "visual_verification")
    assert turn.visual_verification == visual_verification
    assert turn.visual_verification["ssim_score"] == 0.97


def test_turn_record_has_design_compliance_field():
    """
    Test that TurnRecord has optional design_compliance field.

    EXPECTED BEHAVIOR (not yet implemented):
    - TurnRecord has design_compliance: Optional[Dict[str, Any]]
    - Field stores prohibition checklist compliance results
    - Field is optional (None if no design context)

    RED PHASE: This test will FAIL because:
    - design_compliance field doesn't exist on TurnRecord
    - Will raise AttributeError
    """
    from guardkit.orchestrator.autobuild import AgentInvocationResult

    player_result = Mock(spec=AgentInvocationResult)
    coach_result = Mock(spec=AgentInvocationResult)

    # Create TurnRecord with design compliance data
    design_compliance = {
        "violations": [],
        "constraints_checked": ["no_shadcn_icons", "exact_colors_only"],
        "all_passed": True,
    }

    turn = TurnRecord(
        turn=1,
        player_result=player_result,
        coach_result=coach_result,
        decision="approve",
        feedback=None,
        timestamp="2026-02-08T12:00:00Z",
        design_compliance=design_compliance,  # NEW FIELD - will cause failure
    )

    # Verify field is accessible
    assert hasattr(turn, "design_compliance")
    assert turn.design_compliance == design_compliance
    assert turn.design_compliance["all_passed"] is True


def test_turn_record_defaults_none_for_design_fields():
    """
    Test that TurnRecord defaults visual_verification and design_compliance to None.

    EXPECTED BEHAVIOR (not yet implemented):
    - visual_verification defaults to None when not provided
    - design_compliance defaults to None when not provided
    - Backward compatible with existing TurnRecord creation

    RED PHASE: This test will FAIL because:
    - Fields don't exist yet, so can't default to None
    - TypeError when checking non-existent attributes
    """
    from guardkit.orchestrator.autobuild import AgentInvocationResult

    player_result = Mock(spec=AgentInvocationResult)
    coach_result = Mock(spec=AgentInvocationResult)

    # Create TurnRecord WITHOUT design fields (backward compatibility test)
    turn = TurnRecord(
        turn=1,
        player_result=player_result,
        coach_result=coach_result,
        decision="approve",
        feedback=None,
        timestamp="2026-02-08T12:00:00Z",
        # visual_verification NOT provided
        # design_compliance NOT provided
    )

    # Verify fields exist but default to None
    assert hasattr(turn, "visual_verification")
    assert hasattr(turn, "design_compliance")
    assert turn.visual_verification is None
    assert turn.design_compliance is None


# ============================================================================
# 5. Edge Cases and Integration
# ============================================================================


def test_player_prompt_with_design_context_and_feedback(
    mock_agent_invoker, sample_design_context
):
    """
    Test that design context and feedback coexist in Player prompt.

    EXPECTED BEHAVIOR (not yet implemented):
    - Both design context and coach feedback appear in prompt
    - Sections don't conflict or overlap
    - Clear separation between design constraints and iteration feedback

    RED PHASE: This test will FAIL because design context injection doesn't exist.
    """
    prompt = mock_agent_invoker._build_player_prompt(
        task_id="TASK-DM-007",
        turn=2,
        requirements="Implement Button and Input components",
        feedback="Adjust button padding to match design tokens exactly",
        design_context=sample_design_context,
    )

    # Verify both sections exist
    assert "## Design Context" in prompt
    assert "## Coach Feedback" in prompt

    # Verify design context appears before feedback (logical order)
    design_idx = prompt.index("## Design Context")
    feedback_idx = prompt.index("## Coach Feedback")
    assert design_idx < feedback_idx


def test_coach_prompt_references_design_context_in_validation(
    mock_agent_invoker, sample_design_context, sample_player_report
):
    """
    Test that Coach prompt instructs validation against design context.

    EXPECTED BEHAVIOR (not yet implemented):
    - Coach instructions mention checking against design
    - Visual reference URL included for comparison
    - Clear criteria for design approval

    RED PHASE: This test will FAIL because validation instructions don't exist.
    """
    prompt = mock_agent_invoker._build_coach_prompt(
        task_id="TASK-DM-007",
        turn=1,
        requirements="Implement Button and Input components",
        player_report=sample_player_report,
        design_context=sample_design_context,
    )

    # Verify design validation instructions
    prompt_lower = prompt.lower()
    assert "design" in prompt_lower
    assert "verify" in prompt_lower or "check" in prompt_lower

    # Verify visual reference is accessible
    assert sample_design_context.visual_reference in prompt
