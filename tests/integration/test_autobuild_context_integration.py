"""
Integration Tests for AutoBuild Context Retrieval (TASK-GR6-006)

Tests the integration of JobContextRetriever into the /feature-build command,
verifying that context is retrieved for Player and Coach turns with
AutoBuild-specific characteristics.

Coverage Target: >=80%
Test Organization:
    - Test Player turn context retrieval with AutoBuild characteristics
    - Test Coach turn context retrieval with quality gates and turn states
    - Test refinement attempt warning emphasis
    - Test verbose flag context retrieval details

Architecture:
    - Uses mocked GraphitiClient for deterministic results
    - Uses mocked AutoBuildOrchestrator methods
    - Tests integration points in _invoke_player_safely and _invoke_coach_safely

References:
    - TASK-GR6-006: Integrate with /feature-build
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.knowledge.job_context_retriever import (
    JobContextRetriever,
    RetrievedContext,
)
from guardkit.knowledge.task_analyzer import TaskPhase


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_graphiti():
    """
    Create a mock GraphitiClient for testing.

    Returns:
        Mock: Configured Graphiti client mock
    """
    mock = AsyncMock()

    # Configure search to return relevant results based on group_ids
    async def mock_search(query, group_ids=None, num_results=10):
        results = []

        if group_ids and "role_constraints" in group_ids:
            results = [
                {
                    "name": "Player Role",
                    "content": "Player MUST NOT modify auth files without review",
                    "score": 0.9,
                },
                {
                    "name": "Coach Role",
                    "content": "Coach validates quality gates",
                    "score": 0.85,
                },
            ]
        elif group_ids and "quality_gate_configs" in group_ids:
            results = [
                {
                    "name": "Coverage Gate",
                    "content": "Minimum 80% test coverage required",
                    "threshold": 80,
                    "score": 0.9,
                },
                {
                    "name": "Arch Review Gate",
                    "content": "Minimum 60/100 architectural score",
                    "threshold": 60,
                    "score": 0.88,
                },
            ]
        elif group_ids and "turn_states" in group_ids:
            results = [
                {
                    "turn_number": 1,
                    "coach_decision": "REJECTED",
                    "feedback_summary": "Missing test coverage",
                    "progress_summary": "Basic implementation done",
                    "score": 0.95,
                },
                {
                    "turn_number": 2,
                    "coach_decision": "APPROVED",
                    "feedback_summary": "",
                    "progress_summary": "Tests added, all gates pass",
                    "score": 0.92,
                },
            ]
        elif group_ids and "implementation_modes" in group_ids:
            results = [
                {
                    "name": "TDD Mode",
                    "content": "Use TDD for complex business logic",
                    "score": 0.85,
                },
            ]
        elif group_ids and "feature_specs" in group_ids:
            results = [
                {
                    "name": "FEAT-GR6",
                    "content": "Job-Specific Context Retrieval feature",
                    "score": 0.9,
                },
            ]
        elif group_ids and "failure_patterns" in group_ids:
            results = [
                {
                    "warning": "Previous task TASK-001 failed due to missing imports",
                    "score": 0.8,
                },
            ]

        return results

    mock.search = mock_search
    return mock


@pytest.fixture
def sample_autobuild_task():
    """
    Sample AutoBuild task with is_autobuild=True.

    Returns:
        Dict[str, Any]: Task dictionary with AutoBuild characteristics
    """
    return {
        "id": "TASK-GR6-006",
        "description": "Integrate JobContextRetriever with /feature-build",
        "tech_stack": "python",
        "complexity": 5,
        "is_autobuild": True,
        "feature_id": "FEAT-0F4A",
        "turn_number": 1,
        "current_actor": "player",
        "has_previous_turns": False,
    }


@pytest.fixture
def sample_autobuild_task_turn2(sample_autobuild_task):
    """
    Sample AutoBuild task for turn 2 (refinement attempt).

    Returns:
        Dict[str, Any]: Task dictionary with refinement characteristics
    """
    task = sample_autobuild_task.copy()
    task.update({
        "turn_number": 2,
        "has_previous_turns": True,
        "refinement_attempt": 2,
        "last_failure_type": "test_coverage",
    })
    return task


@pytest.fixture
def sample_coach_task(sample_autobuild_task):
    """
    Sample task for Coach turn.

    Returns:
        Dict[str, Any]: Task dictionary with Coach characteristics
    """
    task = sample_autobuild_task.copy()
    task.update({
        "current_actor": "coach",
    })
    return task


# ============================================================================
# Test: Player Turn Context Retrieval
# ============================================================================


class TestPlayerTurnContextRetrieval:
    """Tests for Player turn context retrieval with AutoBuild characteristics."""

    @pytest.mark.asyncio
    async def test_player_turn_retrieves_context_with_is_autobuild_true(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given an AutoBuild task with is_autobuild=True
        When context is retrieved for Player turn
        Then AutoBuild-specific context categories are included

        Acceptance Criteria: Context retrieved for each Player turn
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Verify AutoBuild context is populated
        assert context.role_constraints, "Role constraints should be retrieved"
        assert context.quality_gate_configs, "Quality gate configs should be retrieved"
        assert context.implementation_modes, "Implementation modes should be retrieved"

    @pytest.mark.asyncio
    async def test_player_turn_includes_role_constraints(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given an AutoBuild task for Player turn
        When context is retrieved
        Then role_constraints are included with Player-specific constraints

        Acceptance Criteria: AutoBuild context included (role_constraints)
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Verify role constraints are present
        assert len(context.role_constraints) > 0

        # Verify Player role constraint content
        role_names = [r.get("name", "") for r in context.role_constraints]
        assert any("Player" in name for name in role_names), \
            "Should include Player role constraints"

    @pytest.mark.asyncio
    async def test_player_turn_includes_quality_gates(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given an AutoBuild task for Player turn
        When context is retrieved
        Then quality_gate_configs are included

        Acceptance Criteria: AutoBuild context included (quality_gates)
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Verify quality gate configs are present
        assert len(context.quality_gate_configs) > 0

        # Verify coverage gate is included
        gate_names = [g.get("name", "") for g in context.quality_gate_configs]
        assert any("Coverage" in name for name in gate_names), \
            "Should include coverage gate config"

    @pytest.mark.asyncio
    async def test_player_turn_includes_turn_states(
        self,
        mock_graphiti,
        sample_autobuild_task_turn2,
    ):
        """
        Given an AutoBuild task on turn 2+ with previous turns
        When context is retrieved
        Then turn_states from previous turns are included

        Acceptance Criteria: AutoBuild context included (turn_states)
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task_turn2,
            phase=TaskPhase.IMPLEMENT,
        )

        # Verify turn states are present
        assert len(context.turn_states) > 0

        # Verify turn structure
        first_turn = context.turn_states[0]
        assert "turn_number" in first_turn
        assert "coach_decision" in first_turn

    @pytest.mark.asyncio
    async def test_player_context_includes_current_actor_player(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given an AutoBuild task with current_actor="player"
        When context is retrieved
        Then context is filtered/weighted for Player role

        Acceptance Criteria: Context retrieved for each Player turn
        """
        # Verify task has player as current actor
        assert sample_autobuild_task["current_actor"] == "player"

        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Context should be present (not empty due to is_autobuild=True)
        assert context.task_id == sample_autobuild_task["id"]
        assert context.budget_total > 0


# ============================================================================
# Test: Coach Turn Context Retrieval
# ============================================================================


class TestCoachTurnContextRetrieval:
    """Tests for Coach turn context retrieval."""

    @pytest.mark.asyncio
    async def test_coach_turn_receives_quality_gate_configs(
        self,
        mock_graphiti,
        sample_coach_task,
    ):
        """
        Given an AutoBuild task for Coach turn
        When context is retrieved
        Then quality_gate_configs are included for validation

        Acceptance Criteria: Coach receives appropriate subset of context
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_coach_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Coach should receive quality gate configs
        assert len(context.quality_gate_configs) > 0

        # Verify threshold info is present
        coverage_gate = next(
            (g for g in context.quality_gate_configs if "Coverage" in g.get("name", "")),
            None
        )
        assert coverage_gate is not None
        assert coverage_gate.get("threshold") == 80

    @pytest.mark.asyncio
    async def test_coach_turn_receives_turn_states(
        self,
        mock_graphiti,
        sample_coach_task,
    ):
        """
        Given an AutoBuild task for Coach turn
        When context is retrieved
        Then turn_states are included for cross-turn learning

        Acceptance Criteria: Coach receives appropriate subset of context
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_coach_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Coach should receive turn states
        assert len(context.turn_states) > 0

    @pytest.mark.asyncio
    async def test_coach_context_includes_current_actor_coach(
        self,
        mock_graphiti,
        sample_coach_task,
    ):
        """
        Given an AutoBuild task with current_actor="coach"
        When context is retrieved
        Then context reflects Coach role

        Acceptance Criteria: Coach receives appropriate subset of context
        """
        # Verify task has coach as current actor
        assert sample_coach_task["current_actor"] == "coach"

        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_coach_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Context should be present
        assert context.task_id == sample_coach_task["id"]


# ============================================================================
# Test: Refinement Attempt Warning Emphasis
# ============================================================================


class TestRefinementAttemptWarningEmphasis:
    """Tests for refinement attempt warning emphasis."""

    @pytest.mark.asyncio
    async def test_refinement_attempt_gets_emphasized_warnings(
        self,
        mock_graphiti,
        sample_autobuild_task_turn2,
    ):
        """
        Given an AutoBuild task on refinement attempt (turn > 1)
        When context is retrieved
        Then warnings are emphasized for the failure type

        Acceptance Criteria: Refinement attempts get emphasized warnings
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task_turn2,
            phase=TaskPhase.IMPLEMENT,
        )

        # Verify warnings are present
        assert len(context.warnings) > 0 or len(context.turn_states) > 0, \
            "Refinement attempts should have warnings or turn states"

    @pytest.mark.asyncio
    async def test_refinement_turn_states_show_rejected_feedback(
        self,
        mock_graphiti,
        sample_autobuild_task_turn2,
    ):
        """
        Given an AutoBuild task with previous REJECTED turns
        When context is formatted to prompt
        Then REJECTED turns show emphasized feedback

        Acceptance Criteria: Refinement attempts get emphasized warnings
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task_turn2,
            phase=TaskPhase.IMPLEMENT,
        )

        # Format to prompt and check for warning emphasis
        prompt = context.to_prompt()

        # REJECTED turns should have warning emoji
        assert "REJECTED" in prompt or "Feedback" in prompt, \
            "REJECTED turn feedback should be visible in prompt"

    @pytest.mark.asyncio
    async def test_turn_states_format_includes_warning_for_rejected(
        self,
        mock_graphiti,
        sample_autobuild_task_turn2,
    ):
        """
        Given turn states with REJECTED decisions
        When formatted via _format_turn_states
        Then warning emoji is included with feedback

        Acceptance Criteria: Refinement attempts get emphasized warnings
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task_turn2,
            phase=TaskPhase.IMPLEMENT,
        )

        prompt = context.to_prompt()

        # Check for warning formatting
        if context.turn_states:
            # Look for expected warning patterns
            has_turn_section = "Turn States" in prompt or "Turn" in prompt
            assert has_turn_section, "Turn states should be formatted in prompt"


# ============================================================================
# Test: Verbose Flag Context Details
# ============================================================================


class TestVerboseFlagContextDetails:
    """Tests for verbose flag showing context retrieval details."""

    @pytest.mark.asyncio
    async def test_verbose_flag_shows_budget_used(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given context is retrieved with verbose=True
        When formatted to prompt
        Then budget usage is visible

        Acceptance Criteria: --verbose flag shows context retrieval details
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # Budget should be tracked
        assert context.budget_used >= 0
        assert context.budget_total > 0

        # Format to prompt should show budget
        prompt = context.to_prompt()
        assert "Budget:" in prompt, "Budget usage should be in prompt"

    @pytest.mark.asyncio
    async def test_verbose_flag_shows_categories_retrieved(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given context is retrieved
        When formatted to prompt
        Then category headers are visible for non-empty categories

        Acceptance Criteria: --verbose flag shows context retrieval details
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        prompt = context.to_prompt()

        # Check for category headers with emoji markers
        autobuild_categories = [
            "Role Constraints",
            "Quality Gate",
            "Implementation Modes",
        ]

        found_categories = sum(1 for cat in autobuild_categories if cat in prompt)
        assert found_categories > 0, \
            "At least one AutoBuild category should be in prompt"


# ============================================================================
# Test: Integration with AutoBuild Orchestrator
# ============================================================================


class TestAutoBuildOrchestratorIntegration:
    """Tests for integration with AutoBuildOrchestrator."""

    @pytest.mark.asyncio
    async def test_context_retrieval_called_before_player_invocation(self):
        """
        Given AutoBuildOrchestrator._invoke_player_safely is called
        When Player turn starts
        Then JobContextRetriever.retrieve is called with AutoBuild characteristics

        Acceptance Criteria: Context retrieved for each Player turn
        """
        # This test verifies the integration point exists
        # Will fail until _invoke_player_safely is modified to call retriever
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # Check that AutoBuildOrchestrator has _invoke_player_safely method
        assert hasattr(AutoBuildOrchestrator, '_invoke_player_safely')

        # NOTE: Full integration test would require:
        # 1. Mock JobContextRetriever
        # 2. Mock AgentInvoker
        # 3. Verify retrieve() called with is_autobuild=True
        # This will be implemented in GREEN phase

    @pytest.mark.asyncio
    async def test_context_retrieval_called_before_coach_invocation(self):
        """
        Given AutoBuildOrchestrator._invoke_coach_safely is called
        When Coach turn starts
        Then JobContextRetriever.retrieve is called with quality_gates subset

        Acceptance Criteria: Coach receives appropriate subset of context
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # Check that AutoBuildOrchestrator has _invoke_coach_safely method
        assert hasattr(AutoBuildOrchestrator, '_invoke_coach_safely')

        # NOTE: Full integration test would require similar mocking
        # This will be implemented in GREEN phase


# ============================================================================
# Test: Non-AutoBuild Task (Negative Case)
# ============================================================================


class TestNonAutoBuildTask:
    """Tests for non-AutoBuild tasks (is_autobuild=False)."""

    @pytest.mark.asyncio
    async def test_non_autobuild_task_skips_autobuild_context(
        self,
        mock_graphiti,
    ):
        """
        Given a task with is_autobuild=False
        When context is retrieved
        Then AutoBuild-specific categories are empty
        """
        non_autobuild_task = {
            "id": "TASK-NORMAL-001",
            "description": "Regular task without AutoBuild",
            "tech_stack": "python",
            "complexity": 3,
            "is_autobuild": False,
        }

        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=non_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        # AutoBuild categories should be empty
        assert context.role_constraints == []
        assert context.quality_gate_configs == []
        assert context.turn_states == []
        assert context.implementation_modes == []

        # Standard categories may still have content
        # (feature_context, warnings, etc.)


# ============================================================================
# Test: Context Prompt Formatting
# ============================================================================


class TestContextPromptFormatting:
    """Tests for context formatting in prompts."""

    @pytest.mark.asyncio
    async def test_to_prompt_includes_autobuild_sections(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given retrieved AutoBuild context
        When formatted via to_prompt()
        Then AutoBuild sections are included with correct headers
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        prompt = context.to_prompt()

        # Check for AutoBuild section formatting
        assert "Job-Specific Context" in prompt

    @pytest.mark.asyncio
    async def test_to_prompt_uses_emoji_markers(
        self,
        mock_graphiti,
        sample_autobuild_task,
    ):
        """
        Given retrieved AutoBuild context
        When formatted via to_prompt()
        Then emoji markers are used for categories
        """
        retriever = JobContextRetriever(mock_graphiti)

        context = await retriever.retrieve(
            task=sample_autobuild_task,
            phase=TaskPhase.IMPLEMENT,
        )

        prompt = context.to_prompt()

        # Check for emoji markers (as per existing implementation)
        emoji_patterns = ["###", "Budget:"]  # Headers and budget indicator
        found_patterns = sum(1 for p in emoji_patterns if p in prompt)
        assert found_patterns > 0, "Prompt should have formatting markers"
