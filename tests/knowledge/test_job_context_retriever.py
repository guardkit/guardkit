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


# ============================================================================
# 12. Parallel Retrieval Tests (TASK-GR6-012)
# ============================================================================

class TestParallelRetrieval:
    """Test retrieve_parallel() method for concurrent queries."""

    @pytest.mark.asyncio
    async def test_retrieve_parallel_returns_retrieved_context(self):
        """Test that retrieve_parallel() returns RetrievedContext instance."""
        from guardkit.knowledge.job_context_retriever import (
            JobContextRetriever,
            RetrievedContext,
        )
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

        result = await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)

        assert isinstance(result, RetrievedContext)

    @pytest.mark.asyncio
    async def test_retrieve_parallel_queries_all_standard_categories(self):
        """Test that retrieve_parallel() queries all standard categories."""
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

        await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)

        # Should have queried all standard groups
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]

        # Flatten list
        all_groups = [g for groups in group_ids_used for g in groups]

        assert "feature_specs" in all_groups
        assert "task_outcomes" in all_groups
        assert "patterns_python" in all_groups
        assert "project_architecture" in all_groups
        assert "failure_patterns" in all_groups
        assert "domain_knowledge" in all_groups

    @pytest.mark.asyncio
    async def test_retrieve_parallel_autobuild_queries(self):
        """Test that retrieve_parallel() queries AutoBuild categories when applicable."""
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

        await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)

        # Should have queried AutoBuild groups
        calls = mock_graphiti.search.call_args_list
        group_ids_used = [call[1].get("group_ids", []) for call in calls]

        all_groups = [g for groups in group_ids_used for g in groups]

        assert "role_constraints" in all_groups
        assert "quality_gate_configs" in all_groups
        assert "turn_states" in all_groups
        assert "implementation_modes" in all_groups

    @pytest.mark.asyncio
    async def test_retrieve_parallel_tracks_budget(self):
        """Test that retrieve_parallel() tracks budget correctly."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_results = [{"score": 0.9, "content": "test result"}]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve_parallel(task, TaskPhase.IMPLEMENT)

        assert result.budget_used > 0
        assert result.budget_used <= result.budget_total


# ============================================================================
# 13. Cache Tests (TASK-GR6-012)
# ============================================================================

class TestCaching:
    """Test caching functionality for repeated queries."""

    @pytest.mark.asyncio
    async def test_cache_returns_same_result(self):
        """Test that cached result is returned for identical query."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti, cache_ttl=300)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        # First call
        result1 = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Reset mock to verify it's not called again
        mock_graphiti.search.reset_mock()

        # Second call should use cache
        result2 = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Search should not have been called again
        assert mock_graphiti.search.call_count == 0

        # Results should be identical
        assert result1.task_id == result2.task_id
        assert result1.budget_total == result2.budget_total

    @pytest.mark.asyncio
    async def test_cache_disabled_when_ttl_zero(self):
        """Test that caching is disabled when cache_ttl=0."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti, cache_ttl=0)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        # First call
        await retriever.retrieve(task, TaskPhase.IMPLEMENT)
        first_call_count = mock_graphiti.search.call_count

        # Second call should NOT use cache
        await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # Search should have been called again
        assert mock_graphiti.search.call_count > first_call_count

    @pytest.mark.asyncio
    async def test_cache_key_includes_task_and_phase(self):
        """Test that cache key distinguishes between different tasks/phases."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti, cache_ttl=300)

        task1 = {"id": "TASK-001", "description": "Task 1", "tech_stack": "python"}
        task2 = {"id": "TASK-002", "description": "Task 2", "tech_stack": "python"}

        # Query different tasks
        await retriever.retrieve(task1, TaskPhase.IMPLEMENT)
        await retriever.retrieve(task2, TaskPhase.IMPLEMENT)

        # Both should make separate queries (no cache hit)
        assert mock_graphiti.search.call_count > 1


# ============================================================================
# 14. Early Termination Tests (TASK-GR6-012)
# ============================================================================

class TestEarlyTermination:
    """Test early termination when budget is exhausted."""

    @pytest.mark.asyncio
    async def test_early_termination_stops_at_95_percent(self):
        """Test that early termination stops when budget >= 95% full."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        # Return large results that quickly fill budget
        mock_results = [{"score": 0.9, "content": "x" * 1000} for _ in range(50)]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 5,
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT, early_termination=True)

        # Budget used should be at or near the limit
        # Early termination should have kicked in
        assert result is not None
        assert result.budget_used <= result.budget_total

    @pytest.mark.asyncio
    async def test_early_termination_skips_low_priority_categories(self):
        """Test that early termination skips lower priority categories."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        # Return results that will fill the budget
        mock_results = [{"score": 0.9, "content": "x" * 500} for _ in range(30)]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
            "complexity": 3,  # Lower complexity = smaller budget
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT, early_termination=True)

        # Should have some results but may have skipped low priority categories
        assert result is not None


# ============================================================================
# 15. Quality Metrics Tests (TASK-GR6-011)
# ============================================================================

class TestQualityMetrics:
    """Test quality metrics collection functionality."""

    @pytest.mark.asyncio
    async def test_collect_metrics_returns_quality_metrics(self):
        """Test that collect_metrics=True populates quality_metrics."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase

        mock_graphiti = AsyncMock()
        mock_results = [{"score": 0.9, "content": "test result"}]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT, collect_metrics=True)

        assert result.quality_metrics is not None

    @pytest.mark.asyncio
    async def test_no_metrics_when_not_requested(self):
        """Test that quality_metrics is None when collect_metrics=False."""
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

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT, collect_metrics=False)

        assert result.quality_metrics is None


# ============================================================================
# 16. Turn States Formatting Tests
# ============================================================================

class TestTurnStatesFormatting:
    """Test turn states formatting for cross-turn learning."""

    def test_format_turn_states_with_rejected(self):
        """Test that REJECTED turns include warning emphasis."""
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
            turn_states=[
                {
                    "turn_number": 1,
                    "coach_decision": "REJECTED",
                    "progress_summary": "Failed tests",
                    "feedback_summary": "Missing error handling",
                }
            ],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        assert "Turn 1" in prompt
        assert "REJECTED" in prompt
        assert "⚠️" in prompt
        assert "Missing error handling" in prompt

    def test_format_turn_states_with_approved(self):
        """Test that APPROVED turns are formatted correctly."""
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
            turn_states=[
                {
                    "turn_number": 2,
                    "coach_decision": "APPROVED",
                    "progress_summary": "All tests passing",
                }
            ],
            implementation_modes=[],
        )

        prompt = context.to_prompt()

        assert "Turn 2" in prompt
        assert "APPROVED" in prompt
        assert "All tests passing" in prompt

    def test_format_empty_turn_states(self):
        """Test that empty turn_states returns empty string."""
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

        # The _format_turn_states method returns empty string
        result = context._format_turn_states()
        assert result == ""


# ============================================================================
# 17. _query_turn_states Tests
# ============================================================================

class TestQueryTurnStates:
    """Test the _query_turn_states method."""

    @pytest.mark.asyncio
    async def test_query_turn_states_builds_correct_query(self):
        """Test that _query_turn_states uses correct query format."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])

        retriever = JobContextRetriever(mock_graphiti)

        await retriever._query_turn_states(
            feature_id="FEAT-001",
            task_id="TASK-001",
            budget_allocation=500,
            threshold=0.6,
        )

        # Verify the query format
        mock_graphiti.search.assert_called_once()
        call_args = mock_graphiti.search.call_args
        assert "turn FEAT-001 TASK-001" in call_args[0][0]
        assert call_args[1]["group_ids"] == ["turn_states"]
        assert call_args[1]["num_results"] == 5

    @pytest.mark.asyncio
    async def test_query_turn_states_sorts_by_turn_number(self):
        """Test that results are sorted by turn_number ascending."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = AsyncMock()
        mock_results = [
            {"turn_number": 3, "score": 0.9},
            {"turn_number": 1, "score": 0.9},
            {"turn_number": 2, "score": 0.9},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        results, _ = await retriever._query_turn_states(
            feature_id="FEAT-001",
            task_id="TASK-001",
            budget_allocation=1000,
            threshold=0.5,
        )

        # Results should be sorted by turn_number
        assert results[0]["turn_number"] == 1
        assert results[1]["turn_number"] == 2
        assert results[2]["turn_number"] == 3

    @pytest.mark.asyncio
    async def test_query_turn_states_limits_to_5(self):
        """Test that only the last 5 turns are returned."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = AsyncMock()
        mock_results = [
            {"turn_number": i, "score": 0.9, "content": "x"} for i in range(10)
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        retriever = JobContextRetriever(mock_graphiti)

        results, _ = await retriever._query_turn_states(
            feature_id="FEAT-001",
            task_id="TASK-001",
            budget_allocation=5000,  # Large budget
            threshold=0.5,
        )

        # Should only have last 5 turns
        assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_query_turn_states_handles_exception(self):
        """Test that exceptions are handled gracefully."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(side_effect=Exception("Connection error"))

        retriever = JobContextRetriever(mock_graphiti)

        results, tokens = await retriever._query_turn_states(
            feature_id="FEAT-001",
            task_id="TASK-001",
            budget_allocation=500,
            threshold=0.6,
        )

        # Should return empty list on exception
        assert results == []
        assert tokens == 0


# ============================================================================
# 18. _format_item Tests
# ============================================================================

class TestFormatItem:
    """Test the _format_item helper method."""

    def test_format_item_with_name_and_content(self):
        """Test formatting item with name and content fields."""
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

        item = {"name": "Test", "content": "Description"}
        result = context._format_item(item)
        assert "Test: Description" == result

    def test_format_item_with_name_and_description(self):
        """Test formatting item with name and description fields."""
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

        item = {"name": "Test", "description": "A description"}
        result = context._format_item(item)
        assert "Test: A description" == result

    def test_format_item_with_only_name(self):
        """Test formatting item with only name field."""
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

        item = {"name": "Test"}
        result = context._format_item(item)
        assert "Test" == result

    def test_format_item_with_content_only(self):
        """Test formatting item with only content field."""
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

        item = {"content": "Some content"}
        result = context._format_item(item)
        assert "Some content" == result

    def test_format_item_with_pattern(self):
        """Test formatting item with pattern field."""
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

        item = {"pattern": "Repository Pattern"}
        result = context._format_item(item)
        assert "Repository Pattern" == result

    def test_format_item_with_warning(self):
        """Test formatting item with warning field."""
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

        item = {"warning": "Memory leak warning"}
        result = context._format_item(item)
        assert "Memory leak warning" == result

    def test_format_item_with_outcome(self):
        """Test formatting item with outcome field."""
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

        item = {"outcome": "Success"}
        result = context._format_item(item)
        assert "Success" == result

    def test_format_item_with_concept(self):
        """Test formatting item with concept field."""
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

        item = {"concept": "OAuth 2.0"}
        result = context._format_item(item)
        assert "OAuth 2.0" == result

    def test_format_item_with_component(self):
        """Test formatting item with component field."""
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

        item = {"component": "API Gateway"}
        result = context._format_item(item)
        assert "API Gateway" == result

    def test_format_item_fallback_to_json(self):
        """Test formatting item falls back to JSON for unknown structure."""
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

        item = {"foo": "bar", "baz": 123}
        result = context._format_item(item)
        assert "foo" in result
        assert "bar" in result


# ============================================================================
# 19. RelevanceConfig Integration Tests
# ============================================================================

class TestRelevanceConfigIntegration:
    """Test RelevanceConfig integration with JobContextRetriever."""

    @pytest.mark.asyncio
    async def test_custom_relevance_config(self):
        """Test that custom RelevanceConfig is used."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.task_analyzer import TaskPhase
        from guardkit.knowledge.relevance_tuning import RelevanceConfig

        mock_graphiti = AsyncMock()
        mock_results = [
            {"score": 0.75, "content": "high"},
            {"score": 0.55, "content": "medium"},
            {"score": 0.35, "content": "low"},
        ]
        mock_graphiti.search = AsyncMock(return_value=mock_results)

        # Use high threshold
        config = RelevanceConfig(standard_threshold=0.7)
        retriever = JobContextRetriever(mock_graphiti, relevance_config=config)

        task = {
            "id": "TASK-001",
            "description": "Test task",
            "tech_stack": "python",
        }

        result = await retriever.retrieve(task, TaskPhase.IMPLEMENT)

        # With 0.7 threshold, only score >= 0.7 should be included
        all_items = (
            result.feature_context
            + result.similar_outcomes
            + result.relevant_patterns
            + result.architecture_context
            + result.warnings
            + result.domain_knowledge
        )

        for item in all_items:
            if "score" in item:
                assert item["score"] >= 0.7

    @pytest.mark.asyncio
    async def test_default_relevance_config(self):
        """Test that default RelevanceConfig is used when not provided."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever
        from guardkit.knowledge.relevance_tuning import default_config

        mock_graphiti = AsyncMock()
        retriever = JobContextRetriever(mock_graphiti)

        # Should use default config
        expected_config = default_config()
        assert retriever.relevance_config.standard_threshold == expected_config.standard_threshold


# ============================================================================
# 20. _query_category Exception Handling Tests
# ============================================================================

class TestQueryCategoryExceptionHandling:
    """Test exception handling in _query_category method."""

    @pytest.mark.asyncio
    async def test_query_category_handles_exception(self):
        """Test that _query_category handles exceptions gracefully."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(side_effect=Exception("Connection error"))

        retriever = JobContextRetriever(mock_graphiti)

        results, tokens = await retriever._query_category(
            query="test",
            group_ids=["test_group"],
            budget_allocation=1000,
            threshold=0.6,
        )

        # Should return empty results on exception
        assert results == []
        assert tokens == 0

    @pytest.mark.asyncio
    async def test_query_category_handles_none_results(self):
        """Test that _query_category handles None results."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=None)

        retriever = JobContextRetriever(mock_graphiti)

        results, tokens = await retriever._query_category(
            query="test",
            group_ids=["test_group"],
            budget_allocation=1000,
            threshold=0.6,
        )

        # Should return empty results for None
        assert results == []
        assert tokens == 0


# ============================================================================
# 21. _trim_to_budget Edge Cases
# ============================================================================

class TestTrimToBudgetEdgeCases:
    """Test edge cases in _trim_to_budget method."""

    def test_trim_to_budget_empty_items(self):
        """Test _trim_to_budget with empty items list."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        trimmed, tokens = retriever._trim_to_budget([], 1000)

        assert trimmed == []
        assert tokens == 0

    def test_trim_to_budget_zero_budget(self):
        """Test _trim_to_budget with zero budget."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        items = [{"content": "test"}]
        trimmed, tokens = retriever._trim_to_budget(items, 0)

        assert trimmed == []
        assert tokens == 0

    def test_trim_to_budget_large_items(self):
        """Test _trim_to_budget with items larger than budget."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        # Items with large content
        items = [
            {"content": "x" * 1000},  # ~500 tokens
            {"content": "y" * 1000},  # ~500 tokens
        ]

        trimmed, tokens = retriever._trim_to_budget(items, 100)

        # Should only include items that fit
        assert len(trimmed) < len(items) or tokens <= 100


# ============================================================================
# 22. _estimate_tokens Tests
# ============================================================================

class TestEstimateTokens:
    """Test the _estimate_tokens method."""

    def test_estimate_tokens_basic(self):
        """Test basic token estimation."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        item = {"content": "hello"}  # Short content
        tokens = retriever._estimate_tokens(item)

        assert tokens >= 1

    def test_estimate_tokens_large_content(self):
        """Test token estimation with large content."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        item = {"content": "x" * 1000}  # 1000 characters
        tokens = retriever._estimate_tokens(item)

        # With 2 chars per token, expect ~500 tokens
        assert tokens > 400
        assert tokens < 600

    def test_estimate_tokens_minimum(self):
        """Test that token estimation returns at least 1."""
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_graphiti = MagicMock()
        retriever = JobContextRetriever(mock_graphiti)

        item = {}  # Empty item
        tokens = retriever._estimate_tokens(item)

        assert tokens >= 1
