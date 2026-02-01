"""
Comprehensive Test Suite for JobContextRetriever

Tests the job-specific context retrieval functionality including:
- RetrievedContext dataclass
- JobContextRetriever class with retrieve() method
- Integration with TaskAnalyzer and DynamicBudgetCalculator
- Graphiti queries for each context category
- Relevance filtering and budget trimming
- AutoBuild context loading
- Prompt formatting

Coverage Target: >=85%
Test Count: 30+ tests

References:
- TASK-GR6-003: Implement JobContextRetriever
- FEAT-GR-006: Job-Specific Context Retrieval

TDD RED PHASE: These tests are designed to FAIL initially because
the implementation doesn't exist yet. This is intentional.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
from typing import Dict, List, Any


# ============================================================================
# 1. RetrievedContext Dataclass Tests (8 tests)
# ============================================================================

class TestRetrievedContextDataclass:
    """Test RetrievedContext dataclass definition."""

    def test_dataclass_exists(self):
        """Test that RetrievedContext dataclass exists."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        assert RetrievedContext is not None

    def test_dataclass_has_required_fields(self):
        """Test that dataclass has all required fields."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext
        from dataclasses import is_dataclass, fields

        assert is_dataclass(RetrievedContext)

        field_names = {f.name for f in fields(RetrievedContext)}
        expected_fields = {
            "task_id",
            "budget_used",
            "budget_total",
            "feature_context",
            "similar_outcomes",
            "relevant_patterns",
            "architecture_context",
            "warnings",
            "domain_knowledge",
            "role_constraints",
            "quality_gate_configs",
            "turn_states",
            "implementation_modes",
        }

        assert expected_fields.issubset(field_names)

    def test_dataclass_can_be_instantiated(self):
        """Test that dataclass can be created with required fields."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=2000,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        assert context.task_id == "TASK-001"
        assert context.budget_used == 2000
        assert context.budget_total == 4000

    def test_dataclass_context_categories_are_lists(self):
        """Test that all context categories are list types."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[{"test": "data"}],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        assert isinstance(context.feature_context, list)
        assert isinstance(context.similar_outcomes, list)
        assert isinstance(context.relevant_patterns, list)
        assert isinstance(context.architecture_context, list)
        assert isinstance(context.warnings, list)
        assert isinstance(context.domain_knowledge, list)
        assert isinstance(context.role_constraints, list)
        assert isinstance(context.quality_gate_configs, list)
        assert isinstance(context.turn_states, list)
        assert isinstance(context.implementation_modes, list)

    def test_dataclass_has_to_prompt_method(self):
        """Test that dataclass has to_prompt() method."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        assert hasattr(context, "to_prompt")
        assert callable(context.to_prompt)

    def test_to_prompt_returns_string(self):
        """Test that to_prompt() returns a formatted string."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=500,
            budget_total=4000,
            feature_context=[{"name": "Feature A", "description": "Test feature"}],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        result = context.to_prompt()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_to_prompt_includes_budget_info(self):
        """Test that to_prompt() includes budget information."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=1500,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        result = context.to_prompt()
        assert "1500" in result or "1,500" in result
        assert "4000" in result or "4,000" in result

    def test_to_prompt_includes_context_categories(self):
        """Test that to_prompt() formats all context categories."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[{"name": "Feature A"}],
            similar_outcomes=[{"outcome": "Success"}],
            relevant_patterns=[{"pattern": "Singleton"}],
            architecture_context=[{"component": "API"}],
            warnings=[{"warning": "Memory leak"}],
            domain_knowledge=[{"concept": "OAuth"}],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        result = context.to_prompt()
        # Should include section headers or category names
        assert "feature" in result.lower() or "Feature" in result
        assert "outcome" in result.lower() or "similar" in result.lower()
        assert "pattern" in result.lower() or "Pattern" in result


# ============================================================================
# 2. JobContextRetriever Class Tests (5 tests)
# ============================================================================

class TestJobContextRetrieverClass:
    """Test JobContextRetriever class definition."""

    def test_class_exists(self):
        """Test that JobContextRetriever class exists."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        assert JobContextRetriever is not None

    def test_class_can_be_instantiated(self):
        """Test that class can be instantiated with dependencies."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        assert retriever is not None
        assert hasattr(retriever, "graphiti")

    def test_class_has_retrieve_method(self):
        """Test that class has retrieve() method."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        assert hasattr(retriever, "retrieve")
        assert callable(retriever.retrieve)

    def test_retrieve_is_async(self):
        """Test that retrieve() is an async method."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        import inspect

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        assert inspect.iscoroutinefunction(retriever.retrieve)

    def test_class_stores_graphiti_client(self):
        """Test that class stores graphiti client reference."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        assert retriever.graphiti is mock_graphiti


# ============================================================================
# 3. Basic Retrieve Method Tests (5 tests)
# ============================================================================

class TestRetrieveBasics:
    """Test basic retrieve() functionality."""

    @pytest.mark.asyncio
    async def test_retrieve_returns_retrieved_context(self):
        """Test that retrieve() returns RetrievedContext instance."""
        from guardkit.knowledge.job_context_retriever import (
            JobContextRetriever,
            RetrievedContext,
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 5,
        }

        from guardkit.knowledge.task_analyzer import TaskPhase

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        assert isinstance(result, RetrievedContext)

    @pytest.mark.asyncio
    async def test_retrieve_uses_task_analyzer(self):
        """Test that retrieve() uses TaskAnalyzer to analyze task."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        with patch(
            "guardkit.knowledge.job_context_retriever.TaskAnalyzer"
        ) as mock_analyzer_class:
            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer

            await retriever.retrieve(task, TaskPhase.IMPLEMENT)

            # Verify TaskAnalyzer was instantiated with graphiti
            mock_analyzer_class.assert_called_once_with(mock_graphiti)
            # Verify analyze was called with task and phase
            mock_analyzer.analyze.assert_called_once_with(task, TaskPhase.IMPLEMENT)

    @pytest.mark.asyncio
    async def test_retrieve_uses_budget_calculator(self):
        """Test that retrieve() uses DynamicBudgetCalculator."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        with patch(
            "guardkit.knowledge.job_context_retriever.DynamicBudgetCalculator"
        ) as mock_calc_class:
            mock_calc = MagicMock()
            mock_calc_class.return_value = mock_calc

            await retriever.retrieve(task, TaskPhase.IMPLEMENT)

            # Verify calculator was instantiated
            mock_calc_class.assert_called_once()
            # Verify calculate was called
            assert mock_calc.calculate.called

    @pytest.mark.asyncio
    async def test_retrieve_sets_task_id_in_result(self):
        """Test that retrieve() sets task_id in result."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        assert result.task_id == "TASK-001"

    @pytest.mark.asyncio
    async def test_retrieve_sets_budget_total(self):
        """Test that retrieve() sets budget_total from calculator."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 5,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Budget total should be set (4000 for complexity 5)
        assert result.budget_total > 0


# ============================================================================
# 4. Context Category Query Tests (6 tests)
# ============================================================================

class TestContextCategoryQueries:
    """Test Graphiti queries for each context category."""

    @pytest.mark.asyncio
    async def test_queries_feature_context(self):
        """Test that retrieve() queries feature_specs group."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
            "feature_id": "FEAT-AUTH",
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have queried feature_specs group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("feature_specs" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_queries_similar_outcomes(self):
        """Test that retrieve() queries task_outcomes group."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have queried task_outcomes group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("task_outcomes" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_queries_relevant_patterns(self):
        """Test that retrieve() queries patterns_{stack} group."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have queried patterns_python group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("patterns_python" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_queries_architecture_context(self):
        """Test that retrieve() queries project_architecture group."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have queried project_architecture group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("project_architecture" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_queries_warnings(self):
        """Test that retrieve() queries failure_patterns group."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have queried failure_patterns group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("failure_patterns" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_queries_domain_knowledge(self):
        """Test that retrieve() queries domain_knowledge group."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should have queried domain_knowledge group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("domain_knowledge" in groups for groups in group_ids_used)


# ============================================================================
# 5. AutoBuild Context Tests (4 tests)
# ============================================================================

class TestAutoBuildContext:
    """Test AutoBuild-specific context loading."""

    @pytest.mark.asyncio
    async def test_loads_autobuild_context_when_applicable(self):
        """Test that AutoBuild context is loaded when is_autobuild=True."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # AutoBuild categories should be populated (even if empty lists)
        assert isinstance(result.role_constraints, list)
        assert isinstance(result.quality_gate_configs, list)
        assert isinstance(result.turn_states, list)
        assert isinstance(result.implementation_modes, list)

    @pytest.mark.asyncio
    async def test_queries_role_constraints_for_autobuild(self):
        """Test that role_constraints group is queried for AutoBuild."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should query role_constraints group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("role_constraints" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_queries_turn_states_for_autobuild(self):
        """Test that turn_states group is queried for AutoBuild."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": True,
            "turn_number": 2,
        }

        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should query turn_states group
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]
        assert any("turn_states" in groups for groups in group_ids_used)

    @pytest.mark.asyncio
    async def test_autobuild_context_empty_when_not_applicable(self):
        """Test that AutoBuild context is empty when is_autobuild=False."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "is_autobuild": False,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # AutoBuild categories should be empty
        assert result.role_constraints == []
        assert result.quality_gate_configs == []
        assert result.turn_states == []
        assert result.implementation_modes == []


# ============================================================================
# 6. Relevance Filtering Tests (3 tests)
# ============================================================================

class TestRelevanceFiltering:
    """Test relevance threshold filtering."""

    @pytest.mark.asyncio
    async def test_filters_by_relevance_threshold_first_of_type(self):
        """Test that results are filtered by 0.5 threshold for first-of-type."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Mock search results with varying scores
        mock_results = [
            {"score": 0.8, "content": "high relevance"},
            {"score": 0.6, "content": "medium relevance"},
            {"score": 0.4, "content": "low relevance"},  # Should be filtered out
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        # Task with is_first_of_type=True (will need to mock TaskAnalyzer)
        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        with patch(
            "guardkit.knowledge.job_context_retriever.TaskAnalyzer"
        ) as mock_analyzer_class:
            from guardkit.knowledge.task_analyzer import (
                TaskCharacteristics,
                TaskType,
            )

            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer

            # Mock characteristics with is_first_of_type=True
            characteristics = TaskCharacteristics(
                task_id="TASK-001",
                description="Test task",
                tech_stack="python",
                task_type=TaskType.IMPLEMENTATION,
                current_phase=TaskPhase.IMPLEMENT,
                complexity=5,
                is_first_of_type=True,  # Should use 0.5 threshold
                similar_task_count=0,
                feature_id=None,
                is_refinement=False,
                refinement_attempt=0,
                previous_failure_type=None,
                avg_turns_for_type=3.0,
                success_rate_for_type=0.8,
            )
            mock_analyzer.analyze = AsyncMock(return_value=characteristics)

            result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

            # At least one category should have filtered results (>= 0.5 threshold)
            # Should not include items with score < 0.5
            all_results = (
                result.feature_context
                + result.similar_outcomes
                + result.relevant_patterns
                + result.architecture_context
                + result.warnings
                + result.domain_knowledge
            )

            for item in all_results:
                if "score" in item:
                    assert item["score"] >= 0.5

    @pytest.mark.asyncio
    async def test_filters_by_relevance_threshold_standard(self):
        """Test that results are filtered by 0.6 threshold for standard tasks."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Mock search results with varying scores
        mock_results = [
            {"score": 0.8, "content": "high relevance"},
            {"score": 0.5, "content": "low relevance"},  # Should be filtered out
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        with patch(
            "guardkit.knowledge.job_context_retriever.TaskAnalyzer"
        ) as mock_analyzer_class:
            from guardkit.knowledge.task_analyzer import (
                TaskCharacteristics,
                TaskType,
            )

            mock_analyzer = AsyncMock()
            mock_analyzer_class.return_value = mock_analyzer

            # Mock characteristics with is_first_of_type=False
            characteristics = TaskCharacteristics(
                task_id="TASK-001",
                description="Test task",
                tech_stack="python",
                task_type=TaskType.IMPLEMENTATION,
                current_phase=TaskPhase.IMPLEMENT,
                complexity=5,
                is_first_of_type=False,  # Should use 0.6 threshold
                similar_task_count=5,
                feature_id=None,
                is_refinement=False,
                refinement_attempt=0,
                previous_failure_type=None,
                avg_turns_for_type=3.0,
                success_rate_for_type=0.8,
            )
            mock_analyzer.analyze = AsyncMock(return_value=characteristics)

            result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

            # Should filter by >= 0.6 threshold
            all_results = (
                result.feature_context
                + result.similar_outcomes
                + result.relevant_patterns
                + result.architecture_context
                + result.warnings
                + result.domain_knowledge
            )

            for item in all_results:
                if "score" in item:
                    assert item["score"] >= 0.6

    @pytest.mark.asyncio
    async def test_handles_results_without_score(self):
        """Test that results without score field are kept."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Mock results without score field
        mock_results = [
            {"content": "result without score"},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        # Should not raise exception
        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        assert result is not None


# ============================================================================
# 7. Budget Trimming Tests (3 tests)
# ============================================================================

class TestBudgetTrimming:
    """Test that results are trimmed to fit budget allocation."""

    @pytest.mark.asyncio
    async def test_trims_results_to_fit_budget(self):
        """Test that results are trimmed when exceeding budget."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return many results that would exceed budget
        mock_results = [
            {"score": 0.9, "content": "result " + str(i)} for i in range(100)
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 5,  # 4000 token budget
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Budget should not be exceeded
        assert result.budget_used <= result.budget_total

    @pytest.mark.asyncio
    async def test_respects_category_allocations(self):
        """Test that each category respects its budget allocation."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return many results for each category
        mock_results = [
            {"score": 0.9, "content": "result " + str(i)} for i in range(50)
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 5,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Each category should be limited (not all 50 results)
        assert len(result.feature_context) < 50
        assert len(result.similar_outcomes) < 50

    @pytest.mark.asyncio
    async def test_tracks_budget_used(self):
        """Test that budget_used is calculated correctly."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return some results
        mock_results = [
            {"score": 0.9, "content": "test result"},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Budget used should be tracked
        assert result.budget_used >= 0
        assert result.budget_used <= result.budget_total


# ============================================================================
# 8. Empty Results Tests (2 tests)
# ============================================================================

class TestEmptyResults:
    """Test handling of empty Graphiti results."""

    @pytest.mark.asyncio
    async def test_handles_empty_graphiti_results(self):
        """Test that empty Graphiti results are handled gracefully."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Should return empty lists for all categories
        assert result.feature_context == []
        assert result.similar_outcomes == []
        assert result.relevant_patterns == []
        assert result.architecture_context == []
        assert result.warnings == []
        assert result.domain_knowledge == []

    @pytest.mark.asyncio
    async def test_handles_none_graphiti_results(self):
        """Test that None results from Graphiti are handled."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=None)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        # Should not raise exception
        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        assert result is not None


# ============================================================================
# 9. Token Estimation Tests (2 tests)
# ============================================================================

class TestTokenEstimation:
    """Test token estimation for budget tracking."""

    @pytest.mark.asyncio
    async def test_estimates_tokens_for_results(self):
        """Test that token estimation is used for budget tracking."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return results with content
        mock_results = [
            {"score": 0.9, "content": "This is a test result with some content"},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Budget used should reflect token estimation
        assert result.budget_used > 0

    @pytest.mark.asyncio
    async def test_token_estimation_accounts_for_all_categories(self):
        """Test that token estimation includes all loaded categories."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Return results for multiple categories
        mock_results = [
            {"score": 0.9, "content": "Category result"},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Total categories with content
        total_items = (
            len(result.feature_context)
            + len(result.similar_outcomes)
            + len(result.relevant_patterns)
            + len(result.architecture_context)
            + len(result.warnings)
            + len(result.domain_knowledge)
        )

        # Budget used should scale with number of items
        if total_items > 0:
            assert result.budget_used > 0


# ============================================================================
# 10. Integration Tests (2 tests)
# ============================================================================

class TestIntegration:
    """Test integration between components."""

    @pytest.mark.asyncio
    async def test_end_to_end_retrieval(self):
        """Test complete end-to-end retrieval flow."""
        from guardkit.knowledge.job_context_retriever import (
            JobContextRetriever,
            RetrievedContext,
        )
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()

        # Mock realistic search results
        mock_results = [
            {
                "score": 0.85,
                "name": "Feature Overview",
                "content": "Authentication feature",
            },
            {
                "score": 0.75,
                "name": "Similar Task",
                "content": "Implemented OAuth2",
            },
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement authentication",
            "tech_stack": "python",
            "complexity": 6,
            "feature_id": "FEAT-AUTH",
            "is_autobuild": False,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Verify complete result structure
        assert isinstance(result, RetrievedContext)
        assert result.task_id == "TASK-001"
        assert result.budget_total > 0
        assert result.budget_used >= 0
        assert result.budget_used <= result.budget_total

        # Verify to_prompt works
        prompt = result.to_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    @pytest.mark.asyncio
    async def test_autobuild_end_to_end(self):
        """Test complete AutoBuild retrieval flow."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Implement feature",
            "tech_stack": "python",
            "complexity": 5,
            "is_autobuild": True,
            "turn_number": 2,
            "current_actor": "player",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Verify AutoBuild categories are available
        assert isinstance(result.role_constraints, list)
        assert isinstance(result.quality_gate_configs, list)
        assert isinstance(result.turn_states, list)
        assert isinstance(result.implementation_modes, list)

        # Verify prompt includes AutoBuild context
        prompt = result.to_prompt()
        assert isinstance(prompt, str)


# ============================================================================
# 11. Emoji Markers Tests (NEW - TDD RED PHASE for TASK-GR6-004)
# ============================================================================

class TestEmojiMarkers:
    """Test emoji markers in prompt output.

    These tests verify that section headers include emoji markers to
    visually differentiate section types as per TASK-GR6-004 acceptance criteria.

    Expected emojis:
    - 📋 Feature Context
    - ✅ Similar Outcomes
    - 🎨 Relevant Patterns
    - 🏗️ Architecture Context
    - ⚠️ Warnings
    - 📚 Domain Knowledge
    - 🎭 Role Constraints (AutoBuild)
    - 🎯 Quality Gate Configs (AutoBuild)
    - 🔄 Turn States (AutoBuild)
    - 🛠️ Implementation Modes (AutoBuild)

    TDD RED PHASE: These tests will FAIL initially because the current
    implementation doesn't include emoji markers in section headers.
    """

    def test_feature_context_has_emoji(self):
        """Test that Feature Context section header includes 📋 emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[{"name": "Feature A", "content": "Test feature"}],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "📋" in prompt, "Feature Context section missing 📋 emoji"
        assert "### 📋 Feature Context" in prompt or "📋 Feature Context" in prompt

    def test_similar_outcomes_has_emoji(self):
        """Test that Similar Outcomes section header includes ✅ emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[{"outcome": "Success", "content": "Implemented OAuth2"}],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "✅" in prompt, "Similar Outcomes section missing ✅ emoji"
        assert "### ✅" in prompt or "✅ Similar" in prompt or "✅ What Worked" in prompt

    def test_relevant_patterns_has_emoji(self):
        """Test that Relevant Patterns section header includes 🎨 emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[{"pattern": "Repository", "content": "Repository pattern"}],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "🎨" in prompt, "Relevant Patterns section missing 🎨 emoji"
        assert "### 🎨" in prompt or "🎨 Patterns" in prompt or "🎨 Relevant" in prompt

    def test_architecture_context_has_emoji(self):
        """Test that Architecture Context section header includes 🏗️ emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[{"component": "API", "content": "REST API"}],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "🏗️" in prompt, "Architecture Context section missing 🏗️ emoji"
        assert "### 🏗️" in prompt or "🏗️ Architecture" in prompt

    def test_warnings_has_emoji(self):
        """Test that Warnings section header includes ⚠️ emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[{"warning": "Memory leak", "content": "Watch for memory leaks"}],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "⚠️" in prompt, "Warnings section missing ⚠️ emoji"
        assert "### ⚠️" in prompt or "⚠️ Warnings" in prompt

    def test_domain_knowledge_has_emoji(self):
        """Test that Domain Knowledge section header includes 📚 emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[{"concept": "OAuth", "content": "OAuth 2.0 protocol"}],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "📚" in prompt, "Domain Knowledge section missing 📚 emoji"
        assert "### 📚" in prompt or "📚 Domain" in prompt

    def test_role_constraints_has_emoji(self):
        """Test that Role Constraints section header includes 🎭 emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[{"role": "player", "constraint": "Must ask before schema changes"}],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "🎭" in prompt, "Role Constraints section missing 🎭 emoji"
        assert "### 🎭" in prompt or "🎭 Role" in prompt

    def test_quality_gate_configs_has_emoji(self):
        """Test that Quality Gate Configs section header includes 🎯 emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[{"gate": "coverage", "threshold": "85%"}],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "🎯" in prompt, "Quality Gate Configs section missing 🎯 emoji"
        assert "### 🎯" in prompt or "🎯 Quality" in prompt

    def test_turn_states_has_emoji(self):
        """Test that Turn States section header includes 🔄 emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[{"turn": 1, "status": "APPROVED"}],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "🔄" in prompt, "Turn States section missing 🔄 emoji"
        assert "### 🔄" in prompt or "🔄 Turn" in prompt

    def test_implementation_modes_has_emoji(self):
        """Test that Implementation Modes section header includes 🛠️ emoji."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[{"mode": "tdd", "preference": "use for business logic"}],
        )

        prompt = context.to_prompt()

        # Should have emoji in section header
        assert "🛠️" in prompt, "Implementation Modes section missing 🛠️ emoji"
        assert "### 🛠️" in prompt or "🛠️ Implementation" in prompt

    def test_all_emojis_present_in_full_context(self):
        """Test that all emoji markers appear when all sections populated."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[{"name": "Feature A"}],
            similar_outcomes=[{"outcome": "Success"}],
            relevant_patterns=[{"pattern": "Repository"}],
            architecture_context=[{"component": "API"}],
            warnings=[{"warning": "Memory leak"}],
            domain_knowledge=[{"concept": "OAuth"}],
            role_constraints=[{"role": "player"}],
            quality_gate_configs=[{"gate": "coverage"}],
            turn_states=[{"turn": 1}],
            implementation_modes=[{"mode": "tdd"}],
        )

        prompt = context.to_prompt()

        # All emojis should be present
        assert "📋" in prompt, "Missing 📋 emoji"
        assert "✅" in prompt, "Missing ✅ emoji"
        assert "🎨" in prompt, "Missing 🎨 emoji"
        assert "🏗️" in prompt, "Missing 🏗️ emoji"
        assert "⚠️" in prompt, "Missing ⚠️ emoji"
        assert "📚" in prompt, "Missing 📚 emoji"
        assert "🎭" in prompt, "Missing 🎭 emoji"
        assert "🎯" in prompt, "Missing 🎯 emoji"
        assert "🔄" in prompt, "Missing 🔄 emoji"
        assert "🛠️" in prompt, "Missing 🛠️ emoji"

    def test_emojis_only_in_headers_not_content(self):
        """Test that emojis appear in section headers, not in item content."""
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=0,
            budget_total=4000,
            feature_context=[{"name": "Feature A", "content": "Test feature"}],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        # Emoji should appear before "Feature Context" header
        lines = prompt.split("\n")

        found_emoji_header = False
        for line in lines:
            if "Feature Context" in line and "###" in line:
                # This should be the header line
                assert "📋" in line, "Emoji should be in header line"
                found_emoji_header = True
                break

        assert found_emoji_header, "Could not find Feature Context header line"
