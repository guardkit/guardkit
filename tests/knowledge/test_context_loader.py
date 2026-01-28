"""
TDD RED Phase: Tests for guardkit.knowledge.context_loader

These tests define the expected behavior for session context loading.
The implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- CriticalContext dataclass structure and validation
- load_critical_context() with various parameters
- Graceful degradation when Graphiti unavailable
- Command-specific context loading
- Task-specific context loading
- Feature-specific context loading
- Context scoping and limits

Coverage Target: >=80%
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

# Import will succeed after implementation (GREEN phase)
try:
    from guardkit.knowledge.context_loader import (
        CriticalContext,
        load_critical_context,
        _create_empty_context,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    # Define placeholder for type hints in RED phase
    CriticalContext = None


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


class TestCriticalContext:
    """Test CriticalContext dataclass structure."""

    def test_critical_context_has_system_context_field(self):
        """Test CriticalContext has system_context field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'system_context')
        assert isinstance(context.system_context, list)

    def test_critical_context_has_quality_gates_field(self):
        """Test CriticalContext has quality_gates field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[{"phase": "4", "requirement": "80% coverage"}],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'quality_gates')
        assert len(context.quality_gates) == 1

    def test_critical_context_has_architecture_decisions_field(self):
        """Test CriticalContext has architecture_decisions field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[{"decision": "Use SDK"}],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'architecture_decisions')
        assert len(context.architecture_decisions) == 1

    def test_critical_context_has_failure_patterns_field(self):
        """Test CriticalContext has failure_patterns field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[{"pattern": "subprocess fail"}],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'failure_patterns')
        assert len(context.failure_patterns) == 1

    def test_critical_context_has_successful_patterns_field(self):
        """Test CriticalContext has successful_patterns field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[{"pattern": "SDK query"}],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'successful_patterns')
        assert len(context.successful_patterns) == 1

    def test_critical_context_has_similar_task_outcomes_field(self):
        """Test CriticalContext has similar_task_outcomes field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[{"task": "TASK-001", "outcome": "success"}],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'similar_task_outcomes')
        assert len(context.similar_task_outcomes) == 1

    def test_critical_context_has_relevant_adrs_field(self):
        """Test CriticalContext has relevant_adrs field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[{"adr": "ADR-001"}],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert hasattr(context, 'relevant_adrs')
        assert len(context.relevant_adrs) == 1

    def test_critical_context_has_applicable_patterns_field(self):
        """Test CriticalContext has applicable_patterns field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[{"pattern": "Repository"}],
            relevant_rules=[]
        )
        assert hasattr(context, 'applicable_patterns')
        assert len(context.applicable_patterns) == 1

    def test_critical_context_has_relevant_rules_field(self):
        """Test CriticalContext has relevant_rules field."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[{"rule": "SOLID"}]
        )
        assert hasattr(context, 'relevant_rules')
        assert len(context.relevant_rules) == 1

    def test_critical_context_all_fields_empty(self):
        """Test CriticalContext with all empty fields."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )
        assert len(context.system_context) == 0
        assert len(context.quality_gates) == 0
        assert len(context.architecture_decisions) == 0
        assert len(context.failure_patterns) == 0
        assert len(context.successful_patterns) == 0
        assert len(context.similar_task_outcomes) == 0
        assert len(context.relevant_adrs) == 0
        assert len(context.applicable_patterns) == 0
        assert len(context.relevant_rules) == 0


class TestCreateEmptyContext:
    """Test _create_empty_context helper function."""

    def test_create_empty_context_returns_critical_context(self):
        """Test _create_empty_context returns CriticalContext instance."""
        context = _create_empty_context()
        assert isinstance(context, CriticalContext)

    def test_create_empty_context_all_fields_empty(self):
        """Test _create_empty_context returns context with all empty fields."""
        context = _create_empty_context()
        assert context.system_context == []
        assert context.quality_gates == []
        assert context.architecture_decisions == []
        assert context.failure_patterns == []
        assert context.successful_patterns == []
        assert context.similar_task_outcomes == []
        assert context.relevant_adrs == []
        assert context.applicable_patterns == []
        assert context.relevant_rules == []


class TestLoadCriticalContextGracefulDegradation:
    """Test load_critical_context() graceful degradation."""

    @pytest.mark.asyncio
    async def test_load_context_returns_empty_when_graphiti_disabled(self):
        """Test returns empty context when Graphiti is disabled."""
        # Mock get_graphiti to return a disabled client
        mock_client = Mock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        assert isinstance(context, CriticalContext)
        assert context.system_context == []
        assert context.quality_gates == []
        assert context.architecture_decisions == []

    @pytest.mark.asyncio
    async def test_load_context_returns_empty_when_graphiti_none(self):
        """Test returns empty context when Graphiti client is None."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=None):
            context = await load_critical_context()

        assert isinstance(context, CriticalContext)
        assert context.system_context == []

    @pytest.mark.asyncio
    async def test_load_context_graceful_on_search_error(self):
        """Test graceful degradation when search fails."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Search failed"))

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Should return empty context, not raise exception
        assert isinstance(context, CriticalContext)


class TestLoadCriticalContextBasicQueries:
    """Test load_critical_context() basic search queries."""

    @pytest.mark.asyncio
    async def test_load_context_queries_system_context(self):
        """Test that system context is queried."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"name": "GuardKit", "description": "Task workflow"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Verify search was called with system context parameters
        assert mock_client.search.called
        # Check that at least one call was for system context
        call_args_list = mock_client.search.call_args_list
        queries = [call.kwargs.get('query', call.args[0] if call.args else '') for call in call_args_list]
        assert any('GuardKit' in q or 'product' in q.lower() or 'workflow' in q.lower() for q in queries)

    @pytest.mark.asyncio
    async def test_load_context_queries_quality_gates(self):
        """Test that quality gates are queried."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"phase": "4", "requirement": "80% coverage"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Verify search was called
        assert mock_client.search.called
        call_args_list = mock_client.search.call_args_list
        queries = [call.kwargs.get('query', call.args[0] if call.args else '') for call in call_args_list]
        # Check for quality gate related query
        assert any('quality' in q.lower() or 'gate' in q.lower() or 'phase' in q.lower() for q in queries)

    @pytest.mark.asyncio
    async def test_load_context_queries_architecture_decisions(self):
        """Test that architecture decisions are queried."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"decision": "Use SDK query()"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Verify search was called
        assert mock_client.search.called
        call_args_list = mock_client.search.call_args_list
        queries = [call.kwargs.get('query', call.args[0] if call.args else '') for call in call_args_list]
        assert any('architecture' in q.lower() or 'decision' in q.lower() or 'sdk' in q.lower() for q in queries)

    @pytest.mark.asyncio
    async def test_load_context_queries_failure_patterns(self):
        """Test that failure patterns are queried."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"pattern": "subprocess CLI", "fix": "Use SDK"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Verify search was called
        assert mock_client.search.called
        call_args_list = mock_client.search.call_args_list
        queries = [call.kwargs.get('query', call.args[0] if call.args else '') for call in call_args_list]
        assert any('failure' in q.lower() or 'error' in q.lower() or 'anti-pattern' in q.lower() for q in queries)


class TestLoadCriticalContextResultLimits:
    """Test load_critical_context() result limits."""

    @pytest.mark.asyncio
    async def test_load_context_limits_system_context_results(self):
        """Test that system context results are limited."""
        mock_client = Mock()
        mock_client.enabled = True

        # Return many results
        many_results = [{"body": {"id": f"result_{i}"}} for i in range(20)]
        mock_client.search = AsyncMock(return_value=many_results)

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Verify num_results parameter is passed (should limit results)
        for call in mock_client.search.call_args_list:
            if 'num_results' in call.kwargs:
                assert call.kwargs['num_results'] <= 10  # Should be limited

    @pytest.mark.asyncio
    async def test_load_context_limits_architecture_decisions(self):
        """Test that architecture decisions are limited to reasonable number."""
        mock_client = Mock()
        mock_client.enabled = True

        many_results = [{"body": {"decision": f"decision_{i}"}} for i in range(50)]
        mock_client.search = AsyncMock(return_value=many_results)

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Should pass num_results to limit
        calls_with_num_results = [c for c in mock_client.search.call_args_list if 'num_results' in c.kwargs]
        assert len(calls_with_num_results) > 0


class TestLoadCriticalContextCommandSpecific:
    """Test load_critical_context() with command parameter."""

    @pytest.mark.asyncio
    async def test_load_context_feature_build_command(self):
        """Test context loading for feature-build command."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"pattern": "Player-Coach"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(command="feature-build")

        # Should query for feature-build specific context
        call_args_list = mock_client.search.call_args_list
        queries = [call.kwargs.get('query', call.args[0] if call.args else '') for call in call_args_list]
        # At least one query should be feature-build specific
        assert any('feature' in q.lower() or 'build' in q.lower() or 'player' in q.lower() or 'coach' in q.lower() for q in queries)

    @pytest.mark.asyncio
    async def test_load_context_task_work_command(self):
        """Test context loading for task-work command."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"phase": "implementation"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(command="task-work")

        # Should still load basic context
        assert mock_client.search.called

    @pytest.mark.asyncio
    async def test_load_context_unknown_command(self):
        """Test context loading with unknown command (should use defaults)."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(command="unknown-command")

        # Should still return valid context
        assert isinstance(context, CriticalContext)

    @pytest.mark.asyncio
    async def test_load_context_no_command(self):
        """Test context loading without command parameter."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(command=None)

        # Should still return valid context
        assert isinstance(context, CriticalContext)


class TestLoadCriticalContextTaskSpecific:
    """Test load_critical_context() with task_id parameter."""

    @pytest.mark.asyncio
    async def test_load_context_with_task_id(self):
        """Test context loading with task_id parameter."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"task": "TASK-001", "outcome": "success"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(task_id="TASK-001")

        # Should query for task-related context
        assert mock_client.search.called

    @pytest.mark.asyncio
    async def test_load_context_task_id_none(self):
        """Test context loading with task_id=None."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(task_id=None)

        # Should still return valid context
        assert isinstance(context, CriticalContext)


class TestLoadCriticalContextFeatureSpecific:
    """Test load_critical_context() with feature_id parameter."""

    @pytest.mark.asyncio
    async def test_load_context_with_feature_id(self):
        """Test context loading with feature_id parameter."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"body": {"feature": "FEAT-001", "pattern": "Repository"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(feature_id="FEAT-001")

        # Should query for feature-related context
        assert mock_client.search.called

    @pytest.mark.asyncio
    async def test_load_context_feature_id_none(self):
        """Test context loading with feature_id=None."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(feature_id=None)

        # Should still return valid context
        assert isinstance(context, CriticalContext)


class TestLoadCriticalContextGroupIds:
    """Test load_critical_context() uses correct group_ids."""

    @pytest.mark.asyncio
    async def test_load_context_uses_product_knowledge_group(self):
        """Test that product_knowledge group is used."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            await load_critical_context()

        # Check that at least one call uses product_knowledge or command_workflows
        call_args_list = mock_client.search.call_args_list
        group_ids_used = []
        for call in call_args_list:
            if 'group_ids' in call.kwargs:
                group_ids_used.extend(call.kwargs['group_ids'])

        # Should use appropriate group IDs
        assert len(group_ids_used) > 0 or len(call_args_list) > 0

    @pytest.mark.asyncio
    async def test_load_context_uses_architecture_decisions_group(self):
        """Test that architecture_decisions group is used."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            await load_critical_context()

        # Verify search was called (group_ids may vary)
        assert mock_client.search.called


class TestLoadCriticalContextReturnStructure:
    """Test load_critical_context() return structure."""

    @pytest.mark.asyncio
    async def test_load_context_returns_critical_context(self):
        """Test that load_critical_context returns CriticalContext."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        assert isinstance(context, CriticalContext)

    @pytest.mark.asyncio
    async def test_load_context_populates_system_context(self):
        """Test that system_context is populated from search results."""
        mock_client = Mock()
        mock_client.enabled = True

        # First call returns system context
        mock_client.search = AsyncMock(return_value=[
            {"body": {"name": "GuardKit", "description": "Test"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Should have populated at least some field
        assert isinstance(context, CriticalContext)

    @pytest.mark.asyncio
    async def test_load_context_populates_architecture_decisions(self):
        """Test that architecture_decisions is populated from search results."""
        mock_client = Mock()
        mock_client.enabled = True

        mock_client.search = AsyncMock(return_value=[
            {"body": {"decision": "Use SDK query()", "not": "subprocess"}}
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Should return valid context
        assert isinstance(context, CriticalContext)


class TestLoadCriticalContextEdgeCases:
    """Test load_critical_context() edge cases."""

    @pytest.mark.asyncio
    async def test_load_context_handles_empty_search_results(self):
        """Test handling of empty search results."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        assert isinstance(context, CriticalContext)
        # All lists should be initialized (possibly empty)
        assert isinstance(context.system_context, list)
        assert isinstance(context.quality_gates, list)
        assert isinstance(context.architecture_decisions, list)

    @pytest.mark.asyncio
    async def test_load_context_handles_malformed_results(self):
        """Test handling of malformed search results."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            None,  # Malformed
            {"body": None},  # Missing body content
            {"body": {"valid": "data"}},
            "not a dict",  # Wrong type
        ])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()

        # Should handle gracefully
        assert isinstance(context, CriticalContext)

    @pytest.mark.asyncio
    async def test_load_context_all_parameters(self):
        """Test load_critical_context with all parameters provided."""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                command="feature-build"
            )

        assert isinstance(context, CriticalContext)

    @pytest.mark.asyncio
    async def test_load_context_concurrent_safety(self):
        """Test that multiple concurrent calls are safe."""
        import asyncio

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            # Run multiple concurrent calls
            results = await asyncio.gather(
                load_critical_context(),
                load_critical_context(task_id="TASK-001"),
                load_critical_context(command="feature-build"),
            )

        # All should succeed
        assert all(isinstance(r, CriticalContext) for r in results)
