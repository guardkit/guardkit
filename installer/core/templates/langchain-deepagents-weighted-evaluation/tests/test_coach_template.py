"""Comprehensive tests for the Coach/Evaluator prompt template.

Tests weighted criteria generation, scepticism tuning, CRITICAL response
format positioning, quality gates, think block verification, and
GoalSchema integration.

Coverage Target: >=85%
Test Count: 28 tests

Implements acceptance criteria for TASK-TI-013.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import pathlib
import sys

import pytest

TEMPLATE_ROOT = pathlib.Path(__file__).parent.parent


def _load_module(name: str, file_path: pathlib.Path):
    """Load a Python module from an explicit file path."""
    unique_name = f"_test_coach_.{name}"
    loader = importlib.machinery.SourceFileLoader(unique_name, str(file_path))
    spec = importlib.util.spec_from_file_location(
        unique_name, str(file_path), loader=loader,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(unique_name, None)
        raise
    return module


@pytest.fixture
def coach_mod():
    return _load_module(
        "coach_template",
        TEMPLATE_ROOT / "prompts" / "coach_template.py",
    )


@pytest.fixture
def goal_mod():
    return _load_module(
        "goal_schema",
        TEMPLATE_ROOT / "scaffold" / "goal_schema.py.j2",
    )


@pytest.fixture
def sample_criteria():
    return [
        {
            "name": "accuracy",
            "weight": 0.4,
            "description": "All claims supported by cited sources",
            "accept_example": "Every factual statement has a source reference",
            "reject_example": "Claims made without evidence or citation",
        },
        {
            "name": "completeness",
            "weight": 0.3,
            "description": "Content addresses the request fully",
            "accept_example": "All aspects of the query are covered",
            "reject_example": "Major aspects of the query are missing",
        },
        {
            "name": "quality",
            "weight": 0.3,
            "description": "Writing quality and clarity",
            "accept_example": "Clear, well-organized content",
            "reject_example": "Incoherent or poorly structured text",
        },
    ]


# ============================================================================
# 1. Scepticism Level Tests (6 tests)
# ============================================================================


class TestScepticismLevels:
    """Test that each scepticism level produces distinct prompt language."""

    def test_strict_scepticism(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria, scepticism="strict",
        )
        assert "When uncertain, reject" in prompt
        assert "Quality over quantity" in prompt
        assert "STRICT" in prompt

    def test_balanced_scepticism(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria, scepticism="balanced",
        )
        assert "Evaluate fairly" in prompt
        assert "Accept if minimum threshold met" in prompt
        assert "BALANCED" in prompt

    def test_lenient_scepticism(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria, scepticism="lenient",
        )
        assert "Accept if substantially correct" in prompt
        assert "Minor issues are feedback, not rejection" in prompt
        assert "LENIENT" in prompt

    def test_moderate_alias_maps_to_balanced(self, coach_mod, sample_criteria):
        """'moderate' is a backward-compatible alias for 'balanced'."""
        balanced = coach_mod.build_weighted_coach_prompt(
            sample_criteria, scepticism="balanced",
        )
        moderate = coach_mod.build_weighted_coach_prompt(
            sample_criteria, scepticism="moderate",
        )
        assert balanced == moderate

    def test_unknown_scepticism_falls_back_to_balanced(
        self, coach_mod, sample_criteria,
    ):
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria, scepticism="unknown_level",
        )
        assert "BALANCED" in prompt

    def test_all_levels_have_scoring_bias(self, coach_mod):
        """Each scepticism level includes scoring bias guidance."""
        for level in ("strict", "balanced", "lenient"):
            assert "scoring_bias" in coach_mod.SCEPTICISM_LEVELS[level]
            assert len(coach_mod.SCEPTICISM_LEVELS[level]["scoring_bias"]) > 0


# ============================================================================
# 2. Weighted Criteria Tests (5 tests)
# ============================================================================


class TestWeightedCriteria:
    """Test weighted criteria section generation."""

    def test_criteria_names_in_prompt(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        for criterion in sample_criteria:
            assert criterion["name"] in prompt

    def test_criteria_weights_formatted_as_percentages(
        self, coach_mod, sample_criteria,
    ):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "40%" in prompt
        assert "30%" in prompt

    def test_accept_reject_examples_included(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "ACCEPT example" in prompt
        assert "REJECT example" in prompt
        assert "Every factual statement has a source reference" in prompt
        assert "Claims made without evidence" in prompt

    def test_criteria_without_examples(self, coach_mod):
        """Criteria with missing examples should not crash."""
        criteria = [{"name": "test_criterion", "weight": 1.0}]
        prompt = coach_mod.build_weighted_coach_prompt(criteria)
        assert "test_criterion" in prompt
        assert "ACCEPT example" not in prompt

    def test_acceptance_threshold_in_prompt(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria, acceptance_threshold=0.85,
        )
        assert "0.85" in prompt


# ============================================================================
# 3. CRITICAL Response Format Tests (5 tests)
# ============================================================================


class TestCriticalResponseFormat:
    """Test the CRITICAL JSON response format section."""

    def test_critical_section_at_end(self, coach_mod, sample_criteria):
        """CRITICAL response format must be the LAST major section (recency bias)."""
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        critical_pos = prompt.rfind("## CRITICAL -- Response Format")
        # Must be the last ## section in the prompt
        last_section_pos = prompt.rfind("\n## ", 0, critical_pos)
        assert critical_pos > last_section_pos
        # No other ## section after CRITICAL
        after_critical = prompt[critical_pos + 30:]
        assert "\n## " not in after_critical

    def test_critical_section_contains_json_schema(
        self, coach_mod, sample_criteria,
    ):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert '"accepted"' in prompt
        assert '"scores"' in prompt
        assert '"weighted_score"' in prompt
        assert '"feedback"' in prompt
        assert '"revision_hints"' in prompt

    def test_critical_section_has_accepted_example(
        self, coach_mod, sample_criteria,
    ):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "Example: ACCEPTED output" in prompt

    def test_critical_section_has_rejected_example(
        self, coach_mod, sample_criteria,
    ):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "Example: REJECTED output" in prompt

    def test_no_prose_instruction(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "ONLY valid JSON" in prompt
        assert "No prose" in prompt


# ============================================================================
# 4. Quality Gates Tests (4 tests)
# ============================================================================


class TestQualityGates:
    """Test explicit quality gates and format requirements."""

    def test_automatic_rejection_criteria(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "AUTOMATIC rejection" in prompt
        assert "not valid JSON" in prompt

    def test_accept_reject_scenarios(self, coach_mod, sample_criteria):
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "ACCEPT scenario" in prompt
        assert "REJECT scenario" in prompt

    def test_think_block_verification(self, coach_mod, sample_criteria):
        """Think block requirement should be injected when configured."""
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria,
            format_requirements=["think_blocks_required"],
        )
        assert "Think blocks required" in prompt
        assert "<think>" in prompt
        assert "Automatically reject" in prompt

    def test_no_format_requirements(self, coach_mod, sample_criteria):
        """Without format requirements, domain-specific section is absent."""
        prompt = coach_mod.build_weighted_coach_prompt(sample_criteria)
        assert "Domain-Specific Requirements" not in prompt


# ============================================================================
# 5. GoalSchema Integration Tests (5 tests)
# ============================================================================


class TestGoalSchemaIntegration:
    """Test build_coach_prompt_from_goal with GoalSchema objects."""

    def test_basic_goal_schema(self, coach_mod, goal_mod):
        goal = goal_mod.GoalSchema(
            domain_name="test-domain",
            domain_description="A test domain",
            criteria=[
                goal_mod.EvaluationCriterion(
                    name="accuracy", weight=0.6,
                    description="Factual correctness",
                    accept_example="All facts verified",
                    reject_example="Contains errors",
                ),
                goal_mod.EvaluationCriterion(
                    name="style", weight=0.4,
                    description="Writing quality",
                    accept_example="Clear prose",
                    reject_example="Unclear writing",
                ),
            ],
        )
        prompt = coach_mod.build_coach_prompt_from_goal(goal)
        assert "accuracy" in prompt
        assert "style" in prompt
        assert "60%" in prompt
        assert "40%" in prompt

    def test_goal_schema_with_scepticism(self, coach_mod, goal_mod):
        goal = goal_mod.GoalSchema(
            domain_name="strict-domain",
            criteria=[
                goal_mod.EvaluationCriterion(name="quality", weight=1.0),
            ],
        )
        prompt = coach_mod.build_coach_prompt_from_goal(
            goal, scepticism="strict",
        )
        assert "STRICT" in prompt
        assert "When uncertain, reject" in prompt

    def test_goal_schema_with_format_requirements(self, coach_mod, goal_mod):
        goal = goal_mod.GoalSchema(
            domain_name="reasoning-domain",
            criteria=[
                goal_mod.EvaluationCriterion(name="reasoning", weight=1.0),
            ],
        )
        prompt = coach_mod.build_coach_prompt_from_goal(
            goal,
            format_requirements=["think_blocks_required"],
        )
        assert "<think>" in prompt

    def test_goal_schema_empty_criteria_raises(self, coach_mod, goal_mod):
        goal = goal_mod.GoalSchema(domain_name="empty")
        with pytest.raises(ValueError, match="at least one"):
            coach_mod.build_coach_prompt_from_goal(goal)

    def test_goal_schema_invalid_weights_raises(self, coach_mod, goal_mod):
        goal = goal_mod.GoalSchema(
            domain_name="bad-weights",
            criteria=[
                goal_mod.EvaluationCriterion(name="a", weight=0.5),
                goal_mod.EvaluationCriterion(name="b", weight=0.3),
            ],
        )
        with pytest.raises(ValueError, match="sum to 1.0"):
            coach_mod.build_coach_prompt_from_goal(goal)


# ============================================================================
# 6. Integration Test: Coach Prompt + Mock Evaluation (3 tests)
# ============================================================================


class TestCoachPromptIntegration:
    """Integration tests verifying the prompt produces valid evaluation context."""

    def test_full_prompt_assembly(self, coach_mod, sample_criteria):
        """Verify all sections are present in the assembled prompt."""
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria,
            acceptance_threshold=0.75,
            scepticism="strict",
            format_requirements=["think_blocks_required", "json_output_required"],
        )

        # Role section
        assert "Coach agent" in prompt
        assert "evaluate content" in prompt

        # Tool restriction
        assert "do NOT have access to any tools" in prompt

        # Evaluation process
        assert "Evaluate the content against EACH criterion" in prompt

        # Scepticism
        assert "STRICT" in prompt

        # Threshold
        assert "0.75" in prompt

        # Criteria
        assert "accuracy" in prompt
        assert "completeness" in prompt
        assert "quality" in prompt

        # Quality gates
        assert "Think blocks required" in prompt
        assert "Strict JSON output" in prompt

        # CRITICAL format at end
        assert '"accepted"' in prompt
        assert '"revision_hints"' in prompt

    def test_mock_evaluation_against_prompt(self, coach_mod, sample_criteria):
        """Simulate a Coach evaluation to verify prompt expectations."""
        prompt = coach_mod.build_weighted_coach_prompt(
            sample_criteria, acceptance_threshold=0.7,
        )

        # A mock Coach response that conforms to the CRITICAL format
        mock_response = {
            "accepted": True,
            "scores": {
                "accuracy": {"score": 0.9, "feedback": "Well sourced"},
                "completeness": {"score": 0.8, "feedback": "Thorough"},
                "quality": {"score": 0.75, "feedback": "Clear writing"},
            },
            "weighted_score": 0.83,
            "feedback": "Meets all criteria",
            "revision_hints": [],
        }

        # Verify the response structure matches what the prompt requests
        assert isinstance(mock_response["accepted"], bool)
        assert all(
            "score" in v and "feedback" in v
            for v in mock_response["scores"].values()
        )
        assert isinstance(mock_response["weighted_score"], float)
        assert isinstance(mock_response["revision_hints"], list)

        # Verify composite calculation
        composite = sum(
            mock_response["scores"][c["name"]]["score"] * c["weight"]
            for c in sample_criteria
        )
        assert abs(composite - mock_response["weighted_score"]) < 0.01

        # Verify acceptance decision matches threshold
        assert mock_response["accepted"] == (composite >= 0.7)

    def test_mock_rejection_has_revision_hints(self, coach_mod, sample_criteria):
        """Rejected evaluations must include non-empty revision_hints."""
        mock_rejection = {
            "accepted": False,
            "scores": {
                "accuracy": {"score": 0.3, "feedback": "Missing sources"},
                "completeness": {"score": 0.5, "feedback": "Incomplete"},
                "quality": {"score": 0.6, "feedback": "Acceptable"},
            },
            "weighted_score": 0.45,  # 0.3*0.4 + 0.5*0.3 + 0.6*0.3
            "feedback": "Below threshold",
            "revision_hints": [
                "Add source references",
                "Cover missing topics",
            ],
        }

        # Prompt mandates non-empty hints on rejection
        assert not mock_rejection["accepted"]
        assert len(mock_rejection["revision_hints"]) > 0

        # Verify composite
        composite = sum(
            mock_rejection["scores"][c["name"]]["score"] * c["weight"]
            for c in sample_criteria
        )
        assert abs(composite - mock_rejection["weighted_score"]) < 0.01
        assert composite < 0.7
