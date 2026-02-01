"""
TDD RED Phase Tests for Turn States Retrieval (TASK-GR6-009)

Tests the turn_states retrieval and formatting functionality for cross-turn
learning in feature-build workflows.

Acceptance Criteria:
1. Queries `turn_states` group for feature_id + task_id
2. Returns last 5 turns sorted by turn_number
3. Formats turn summary with decision and progress
4. Emphasizes REJECTED feedback (must address)
5. Increased allocation for later turns (15-20%)

Coverage Target: >=85%
Test Count: 18 tests

References:
- TASK-GR6-009: Add turn_states retrieval for cross-turn learning
- FEAT-GR-006: Job-Specific Context Retrieval
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# 1. Turn States Query Format Tests (3 tests)
# ============================================================================

class TestTurnStatesQueryFormat:
    """Test that turn_states queries use correct format."""

    @pytest.mark.asyncio
    async def test_turn_states_query_includes_feature_id_and_task_id(self):
        """Test that query uses 'turn {feature_id} {task_id}' format."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-GR6-001",
            "description": "Implement feature",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-GR6",
            "turn_number": 3,
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Find the call to turn_states group
        calls = mock_graphiti.search.call_args_list
        turn_state_calls = [
            call for call in calls
            if call[1].get("group_ids") == ["turn_states"]
        ]

        # Should have queried turn_states
        assert len(turn_state_calls) > 0, "Expected at least one query to turn_states group"

        # The query should include feature_id and task_id
        # Format: "turn {feature_id} {task_id}"
        query = turn_state_calls[0][0][0]  # First positional arg
        assert "turn" in query.lower(), f"Query should include 'turn': {query}"
        assert "FEAT-GR6" in query or "feat-gr6" in query.lower(), \
            f"Query should include feature_id: {query}"
        assert "TASK-GR6-001" in query or "task-gr6-001" in query.lower(), \
            f"Query should include task_id: {query}"

    @pytest.mark.asyncio
    async def test_turn_states_query_requests_5_results(self):
        """Test that turn_states query requests num_results=5."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-GR6-001",
            "description": "Implement feature",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-GR6",
            "turn_number": 3,
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Find the call to turn_states group
        calls = mock_graphiti.search.call_args_list
        turn_state_calls = [
            call for call in calls
            if call[1].get("group_ids") == ["turn_states"]
        ]

        assert len(turn_state_calls) > 0, "Expected turn_states query"

        # Should request 5 results (last 5 turns)
        num_results = turn_state_calls[0][1].get("num_results")
        assert num_results == 5, f"Expected num_results=5, got {num_results}"

    @pytest.mark.asyncio
    async def test_turn_states_only_queried_for_autobuild_tasks(self):
        """Test that turn_states is only queried when is_autobuild=True."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        # Non-AutoBuild task
        task = {
            "id": "TASK-001",
            "description": "Implement feature",
            "tech_stack": "python",
            "is_autobuild": False,
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should NOT query turn_states
        calls = mock_graphiti.search.call_args_list
        turn_state_calls = [
            call for call in calls
            if call[1].get("group_ids") == ["turn_states"]
        ]

        assert len(turn_state_calls) == 0, \
            "Should not query turn_states for non-AutoBuild tasks"


# ============================================================================
# 2. Budget Allocation Tests (3 tests)
# ============================================================================

class TestTurnStatesBudgetAllocation:
    """Test increased budget allocation for later turns."""

    @pytest.mark.asyncio
    async def test_later_turns_get_increased_allocation(self):
        """Test that turn_number > 1 gets 15-20% allocation."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        # Task in turn 3 (later turn)
        characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=3,
            feature_id="FEAT-001",
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            turn_number=3,  # Later turn
        )

        budget = calculator.calculate(characteristics)

        # turn_states allocation should be 15-20% (0.15-0.20)
        turn_states_allocation = budget.get_allocation("turn_states")
        total_budget = budget.total_tokens

        # Calculate percentage
        allocation_percent = (turn_states_allocation / total_budget) * 100

        assert 15 <= allocation_percent <= 20, \
            f"Expected 15-20% allocation for later turns, got {allocation_percent:.1f}%"

    @pytest.mark.asyncio
    async def test_turn_1_gets_lower_allocation(self):
        """Test that turn 1 gets lower allocation than later turns."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        # Create characteristics for turn 1
        turn_1_characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=3,
            feature_id="FEAT-001",
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            turn_number=1,  # First turn
        )

        # Create characteristics for turn 3
        turn_3_characteristics = TaskCharacteristics(
            task_id="TASK-001",
            description="Test task",
            tech_stack="python",
            task_type=TaskType.IMPLEMENTATION,
            current_phase=TaskPhase.IMPLEMENT,
            complexity=5,
            is_first_of_type=False,
            similar_task_count=3,
            feature_id="FEAT-001",
            is_refinement=False,
            refinement_attempt=0,
            previous_failure_type=None,
            avg_turns_for_type=3.0,
            success_rate_for_type=0.8,
            is_autobuild=True,
            turn_number=3,  # Later turn
        )

        budget_turn_1 = calculator.calculate(turn_1_characteristics)
        budget_turn_3 = calculator.calculate(turn_3_characteristics)

        allocation_turn_1 = budget_turn_1.get_allocation("turn_states")
        allocation_turn_3 = budget_turn_3.get_allocation("turn_states")

        assert allocation_turn_3 > allocation_turn_1, \
            f"Later turns should get higher allocation: turn_1={allocation_turn_1}, turn_3={allocation_turn_3}"

    @pytest.mark.asyncio
    async def test_allocation_percentage_in_correct_range(self):
        """Test that allocation is within 15-20% for AutoBuild later turns."""
        from guardkit.knowledge.budget_calculator import DynamicBudgetCalculator
        from guardkit.knowledge.task_analyzer import (
            TaskCharacteristics,
            TaskType,
            TaskPhase,
        )

        calculator = DynamicBudgetCalculator()

        # Test various later turn numbers
        for turn_number in [2, 3, 4, 5]:
            characteristics = TaskCharacteristics(
                task_id="TASK-001",
                description="Test task",
                tech_stack="python",
                task_type=TaskType.IMPLEMENTATION,
                current_phase=TaskPhase.IMPLEMENT,
                complexity=5,
                is_first_of_type=False,
                similar_task_count=3,
                feature_id="FEAT-001",
                is_refinement=False,
                refinement_attempt=0,
                previous_failure_type=None,
                avg_turns_for_type=3.0,
                success_rate_for_type=0.8,
                is_autobuild=True,
                turn_number=turn_number,
            )

            budget = calculator.calculate(characteristics)
            allocation = budget.get_allocation("turn_states")
            total = budget.total_tokens
            percent = (allocation / total) * 100

            assert 15 <= percent <= 20, \
                f"Turn {turn_number}: Expected 15-20%, got {percent:.1f}%"


# ============================================================================
# 3. Sorting Tests (3 tests)
# ============================================================================

class TestTurnStatesSorting:
    """Test that turns are sorted by turn_number."""

    @pytest.mark.asyncio
    async def test_turns_sorted_by_turn_number_ascending(self):
        """Test that turns are returned sorted by turn_number ascending."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return unsorted turn states
        mock_turn_states = [
            {"turn_number": 3, "coach_decision": "FEEDBACK", "progress_summary": "Turn 3"},
            {"turn_number": 1, "coach_decision": "APPROVED", "progress_summary": "Turn 1"},
            {"turn_number": 2, "coach_decision": "REJECTED", "progress_summary": "Turn 2"},
        ]

        # Return turn states for turn_states group, empty for others
        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 4,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Verify turns are sorted
        if result.turn_states:
            turn_numbers = [t.get("turn_number") for t in result.turn_states]
            assert turn_numbers == sorted(turn_numbers), \
                f"Turns should be sorted: {turn_numbers}"

    @pytest.mark.asyncio
    async def test_only_last_5_turns_returned(self):
        """Test that only the last 5 turns are returned."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return 7 turn states
        mock_turn_states = [
            {"turn_number": i, "coach_decision": "FEEDBACK", "progress_summary": f"Turn {i}"}
            for i in range(1, 8)  # 7 turns
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 8,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should return at most 5 turns
        assert len(result.turn_states) <= 5, \
            f"Expected at most 5 turns, got {len(result.turn_states)}"

    @pytest.mark.asyncio
    async def test_returns_most_recent_5_turns(self):
        """Test that the most recent 5 turns are returned (highest turn_numbers)."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return 7 turn states
        mock_turn_states = [
            {"turn_number": i, "coach_decision": "FEEDBACK", "progress_summary": f"Turn {i}"}
            for i in range(1, 8)  # Turns 1-7
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 8,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # The returned turns should be the last 5 (turns 3, 4, 5, 6, 7)
        if len(result.turn_states) > 0:
            turn_numbers = [t.get("turn_number") for t in result.turn_states]
            # Should include turns 3-7 (last 5), not turns 1-2
            assert 1 not in turn_numbers and 2 not in turn_numbers, \
                f"Should return last 5 turns, got turns: {turn_numbers}"


# ============================================================================
# 4. Output Format Tests (5 tests)
# ============================================================================

class TestTurnStatesOutputFormat:
    """Test the formatted output matches acceptance criteria."""

    @pytest.mark.asyncio
    async def test_format_includes_header(self):
        """Test that format includes 'Previous Turn Context' header."""
        from guardkit.knowledge.job_context_retriever import (
            JobContextRetriever,
            RetrievedContext,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {"turn_number": 1, "coach_decision": "FEEDBACK", "progress_summary": "Progress 1"},
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 2,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Should include the header
        assert "Previous Turn Context" in prompt, \
            f"Expected 'Previous Turn Context' header in output"

    @pytest.mark.asyncio
    async def test_format_includes_learning_guidance(self):
        """Test that format includes learning guidance text."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {"turn_number": 1, "coach_decision": "FEEDBACK", "progress_summary": "Progress 1"},
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 2,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Should include learning guidance
        assert "don't repeat mistakes" in prompt.lower() or \
               "learn from previous turns" in prompt.lower(), \
            f"Expected learning guidance in output"

    @pytest.mark.asyncio
    async def test_format_includes_turn_number_and_decision(self):
        """Test that each turn shows turn number and coach decision."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {"turn_number": 1, "coach_decision": "FEEDBACK", "progress_summary": "Progress 1"},
            {"turn_number": 2, "coach_decision": "REJECTED", "progress_summary": "Progress 2"},
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 3,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Should include turn number and decision for each turn
        assert "Turn 1" in prompt, "Expected 'Turn 1' in output"
        assert "Turn 2" in prompt, "Expected 'Turn 2' in output"
        assert "FEEDBACK" in prompt, "Expected 'FEEDBACK' decision in output"
        assert "REJECTED" in prompt, "Expected 'REJECTED' decision in output"

    @pytest.mark.asyncio
    async def test_format_includes_progress_summary(self):
        """Test that format includes progress summary for each turn."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {
                "turn_number": 1,
                "coach_decision": "FEEDBACK",
                "progress_summary": "Initial implementation incomplete"
            },
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 2,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Should include progress summary
        assert "Progress:" in prompt or "progress:" in prompt.lower(), \
            "Expected 'Progress:' label in output"
        assert "Initial implementation incomplete" in prompt, \
            "Expected progress summary text in output"

    @pytest.mark.asyncio
    async def test_format_matches_acceptance_criteria_example(self):
        """Test that format matches the exact example from acceptance criteria."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Create turn states matching acceptance criteria example
        mock_turn_states = [
            {
                "turn_number": 1,
                "coach_decision": "FEEDBACK",
                "progress_summary": "Initial implementation incomplete"
            },
            {
                "turn_number": 2,
                "coach_decision": "REJECTED",
                "progress_summary": "Tests failing, coverage at 65%",
                "feedback_summary": "Coverage must be >=80%. Missing tests for error paths."
            },
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 3,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Verify key elements from acceptance criteria format
        assert "Previous Turn Context" in prompt
        assert "Turn 1" in prompt
        assert "FEEDBACK" in prompt
        assert "Initial implementation incomplete" in prompt
        assert "Turn 2" in prompt
        assert "REJECTED" in prompt
        assert "Tests failing, coverage at 65%" in prompt


# ============================================================================
# 5. REJECTED Emphasis Tests (4 tests)
# ============================================================================

class TestRejectedEmphasis:
    """Test that REJECTED turns are emphasized with warning."""

    @pytest.mark.asyncio
    async def test_rejected_turn_has_warning_icon(self):
        """Test that REJECTED turns have warning icon (emoji or text)."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {
                "turn_number": 1,
                "coach_decision": "REJECTED",
                "progress_summary": "Tests failing",
                "feedback_summary": "Coverage must be >=80%"
            },
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 2,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Should have warning indicator for REJECTED
        # Accept either emoji or text warning
        has_warning = (
            "⚠️" in prompt or
            "⚠" in prompt or
            "WARNING" in prompt.upper() or
            "!" in prompt  # Exclamation in context of feedback
        )
        assert has_warning, \
            f"Expected warning indicator for REJECTED turn in output"

    @pytest.mark.asyncio
    async def test_rejected_turn_shows_feedback(self):
        """Test that REJECTED turns display the feedback_summary."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {
                "turn_number": 1,
                "coach_decision": "REJECTED",
                "progress_summary": "Tests failing",
                "feedback_summary": "Coverage must be >=80%. Missing tests for error paths."
            },
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 2,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Should include the feedback for REJECTED turn
        assert "Coverage must be >=80%" in prompt or "coverage" in prompt.lower(), \
            f"Expected feedback content in output"
        assert "Feedback" in prompt or "feedback" in prompt.lower(), \
            f"Expected 'Feedback' label for REJECTED turn"

    @pytest.mark.asyncio
    async def test_approved_turn_no_feedback_emphasis(self):
        """Test that APPROVED turns don't have warning emphasis."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {
                "turn_number": 1,
                "coach_decision": "APPROVED",
                "progress_summary": "All tests passing",
                "feedback_summary": ""  # No feedback for APPROVED
            },
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 2,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Find the APPROVED turn section
        # It should not have warning indicators in the context of feedback
        lines = prompt.split("\n")
        in_approved_section = False
        for line in lines:
            if "Turn 1" in line and "APPROVED" in line:
                in_approved_section = True
            elif in_approved_section and "Turn" in line:
                break
            elif in_approved_section:
                # APPROVED section should not have warning feedback
                assert "⚠️ Feedback" not in line, \
                    f"APPROVED turn should not have warning feedback: {line}"

    @pytest.mark.asyncio
    async def test_feedback_turn_no_strong_warning(self):
        """Test that FEEDBACK turns don't have the same emphasis as REJECTED."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        mock_turn_states = [
            {
                "turn_number": 1,
                "coach_decision": "FEEDBACK",
                "progress_summary": "Partial implementation",
                "feedback_summary": "Consider adding more tests"
            },
            {
                "turn_number": 2,
                "coach_decision": "REJECTED",
                "progress_summary": "Tests failing",
                "feedback_summary": "Coverage below threshold"
            },
        ]

        def mock_search(query, group_ids=None, num_results=None):
            if group_ids == ["turn_states"]:
                return mock_turn_states
            return []

        mock_graphiti.search = AsyncMock(side_effect=mock_search)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "feature_id": "FEAT-001",
            "turn_number": 3,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        prompt = result.to_prompt()

        # Count warning icons - REJECTED should have more emphasis
        # The ⚠️ should appear with REJECTED feedback, not FEEDBACK
        lines = prompt.split("\n")

        # Find REJECTED section - it should have the warning
        rejected_has_warning = False
        for i, line in enumerate(lines):
            if "REJECTED" in line:
                # Check nearby lines for warning
                context = "\n".join(lines[max(0, i-1):min(len(lines), i+3)])
                if "⚠" in context:
                    rejected_has_warning = True
                    break

        assert rejected_has_warning, \
            "REJECTED turn should have warning emphasis"
