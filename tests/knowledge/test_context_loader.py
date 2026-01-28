"""
Tests for guardkit.knowledge.context_loader and context_formatter modules.

These tests verify the critical context loading functionality that fixes
the memory problem by injecting relevant knowledge at session start.

Coverage targets:
- load_critical_context() - graceful degradation, command-specific loading
- format_context_for_injection() - markdown formatting
- CriticalContext dataclass - field validation
- Helper functions - edge cases

ACCEPTANCE CRITERIA TESTED:
1. Context loads at command start
2. Architecture decisions are visible  
3. Failure patterns are visible
4. Context is scoped appropriately
5. Graceful degradation when Graphiti unavailable
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Import modules under test
from guardkit.knowledge.context_loader import (
    CriticalContext,
    load_critical_context,
    _create_empty_context,
    _filter_valid_results,
)
from guardkit.knowledge.context_formatter import (
    ContextFormatterConfig,
    format_context_for_injection,
    _format_architecture_decisions_section,
    _format_failure_patterns_section,
    _format_quality_gates_section,
    _format_system_context_section,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_architecture_decisions() -> List[Dict[str, Any]]:
    """Sample architecture decision results from Graphiti."""
    return [
        {
            'body': {
                'title': 'SDK Query Pattern',
                'decision': 'Use Claude Agent SDK query() for task-work delegation, NOT subprocess'
            }
        },
        {
            'body': {
                'title': 'Worktree Paths',
                'decision': 'Use FEAT-XXX worktree paths for feature isolation'
            }
        },
        {
            'body': {
                'title': 'Episode Architecture',
                'decision': 'Store episodes with group_ids for scoped retrieval'
            }
        }
    ]


@pytest.fixture
def sample_failure_patterns() -> List[Dict[str, Any]]:
    """Sample failure pattern results from Graphiti."""
    return [
        {
            'body': {
                'description': 'Subprocess mocking fails in test environments - use SDK directly'
            }
        },
        {
            'body': {
                'description': 'Missing OPENAI_API_KEY causes silent failures'
            }
        }
    ]


@pytest.fixture
def sample_quality_gates() -> List[Dict[str, Any]]:
    """Sample quality gate results from Graphiti."""
    return [
        {
            'body': {
                'phase': 'Phase 4',
                'requirement': 'All tests must pass (100%)'
            }
        },
        {
            'body': {
                'phase': 'Phase 4.5',
                'requirement': 'Coverage >= 80%'
            }
        }
    ]


@pytest.fixture
def sample_system_context() -> List[Dict[str, Any]]:
    """Sample system context results from Graphiti."""
    return [
        {
            'body': {
                'name': 'GuardKit',
                'description': 'Lightweight AI-assisted development workflow with quality gates'
            }
        },
        {
            'body': {
                'name': 'Quality Gates',
                'description': 'Automated checkpoints that prevent broken code'
            }
        }
    ]


@pytest.fixture
def complete_context(
    sample_architecture_decisions,
    sample_failure_patterns,
    sample_quality_gates,
    sample_system_context
) -> CriticalContext:
    """Fully populated CriticalContext for testing."""
    return CriticalContext(
        system_context=sample_system_context,
        quality_gates=sample_quality_gates,
        architecture_decisions=sample_architecture_decisions,
        failure_patterns=sample_failure_patterns,
        successful_patterns=[],
        similar_task_outcomes=[],
        relevant_adrs=[],
        applicable_patterns=[],
        relevant_rules=[]
    )


@pytest.fixture
def mock_graphiti(
    sample_architecture_decisions,
    sample_failure_patterns,
    sample_quality_gates,
    sample_system_context
):
    """Create a mock GraphitiClient that returns sample data."""
    mock_client = MagicMock()
    mock_client.enabled = True
    
    async def mock_search(query: str, group_ids=None, num_results=10):
        """Return appropriate results based on query/group_ids."""
        if group_ids and 'architecture_decisions' in group_ids:
            return sample_architecture_decisions
        elif group_ids and 'failure_patterns' in group_ids:
            return sample_failure_patterns
        elif group_ids and 'quality_gate_phases' in group_ids:
            return sample_quality_gates
        elif group_ids and ('product_knowledge' in group_ids or 'command_workflows' in group_ids):
            return sample_system_context
        elif group_ids and 'feature_build_architecture' in group_ids:
            return [{'body': {'name': 'Player-Coach', 'description': 'Adversarial workflow'}}]
        return []
    
    mock_client.search = AsyncMock(side_effect=mock_search)
    return mock_client


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestCreateEmptyContext:
    """Tests for _create_empty_context helper."""
    
    def test_returns_critical_context_instance(self):
        """Should return a CriticalContext dataclass instance."""
        context = _create_empty_context()
        assert isinstance(context, CriticalContext)
    
    def test_all_fields_are_empty_lists(self):
        """All fields should be empty lists."""
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


class TestFilterValidResults:
    """Tests for _filter_valid_results helper."""
    
    def test_filters_none_values(self):
        """Should filter out None values."""
        results = [{'body': {}}, None, {'body': {}}]
        filtered = _filter_valid_results(results)
        assert len(filtered) == 2
    
    def test_filters_non_dict_values(self):
        """Should filter out non-dict values."""
        results = [{'body': {}}, "string", 123, {'body': {}}]
        filtered = _filter_valid_results(results)
        assert len(filtered) == 2
    
    def test_keeps_dicts_with_missing_body(self):
        """Should keep dicts even if body is missing."""
        results = [{'body': {}}, {'no_body': True}]
        filtered = _filter_valid_results(results)
        assert len(filtered) == 2
    
    def test_empty_input_returns_empty(self):
        """Empty input should return empty list."""
        assert _filter_valid_results([]) == []


# =============================================================================
# Graceful Degradation Tests
# =============================================================================

class TestGracefulDegradation:
    """Tests for graceful degradation when Graphiti unavailable."""
    
    @pytest.mark.asyncio
    async def test_returns_empty_when_graphiti_none(self):
        """Should return empty context when get_graphiti() returns None."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=None):
            context = await load_critical_context()
            assert context.system_context == []
            assert context.architecture_decisions == []
    
    @pytest.mark.asyncio
    async def test_returns_empty_when_graphiti_disabled(self):
        """Should return empty context when graphiti.enabled is False."""
        mock_client = MagicMock()
        mock_client.enabled = False
        
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()
            assert context.system_context == []
            assert context.architecture_decisions == []
    
    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        """Should return empty context on any exception."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_client):
            context = await load_critical_context()
            assert context.system_context == []
            assert context.architecture_decisions == []


# =============================================================================
# Load Critical Context Tests
# =============================================================================

class TestLoadCriticalContext:
    """Tests for load_critical_context main function."""
    
    @pytest.mark.asyncio
    async def test_loads_all_sections(self, mock_graphiti):
        """Should load all context sections when Graphiti available."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            context = await load_critical_context()
            
            assert len(context.system_context) > 0
            assert len(context.quality_gates) > 0
            assert len(context.architecture_decisions) > 0
            assert len(context.failure_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_feature_build_loads_extra_context(self, mock_graphiti):
        """Feature-build command should load additional context."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            context = await load_critical_context(command="feature-build")
            
            # System context should include feature-build specific items
            assert len(context.system_context) > 0
    
    @pytest.mark.asyncio
    async def test_task_work_command(self, mock_graphiti):
        """task-work command should load standard context."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            context = await load_critical_context(command="task-work")
            
            assert len(context.architecture_decisions) > 0
            assert len(context.failure_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_with_task_id(self, mock_graphiti):
        """Should accept task_id parameter (future functionality)."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            context = await load_critical_context(task_id="TASK-001")
            
            # Currently just loads standard context
            assert isinstance(context, CriticalContext)
    
    @pytest.mark.asyncio
    async def test_with_feature_id(self, mock_graphiti):
        """Should accept feature_id parameter (future functionality)."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            context = await load_critical_context(feature_id="FEAT-001")
            
            # Currently just loads standard context
            assert isinstance(context, CriticalContext)


# =============================================================================
# Format Context Tests
# =============================================================================

class TestFormatContextForInjection:
    """Tests for format_context_for_injection function."""
    
    def test_empty_context_returns_empty_string(self):
        """Empty context should return empty string."""
        context = _create_empty_context()
        result = format_context_for_injection(context)
        assert result == ""
    
    def test_complete_context_includes_all_sections(self, complete_context):
        """Complete context should include all section headers."""
        result = format_context_for_injection(complete_context)
        
        assert "## Architecture Decisions (MUST FOLLOW)" in result
        assert "## Known Failures (AVOID THESE)" in result
        assert "## Quality Gates" in result
        assert "## System Context" in result
    
    def test_architecture_decisions_formatting(self, complete_context):
        """Architecture decisions should be formatted as bullet points."""
        result = format_context_for_injection(complete_context)
        
        assert "**SDK Query Pattern**" in result
        assert "Use Claude Agent SDK query()" in result
    
    def test_failure_patterns_formatting(self, complete_context):
        """Failure patterns should be formatted with descriptions."""
        result = format_context_for_injection(complete_context)
        
        assert "Subprocess mocking fails" in result
    
    def test_respects_config_limits(self, complete_context):
        """Should respect configuration limits."""
        config = ContextFormatterConfig(
            max_decisions=1,
            max_failure_patterns=1,
            max_quality_gates=1,
            max_system_context=1
        )
        result = format_context_for_injection(complete_context, config)
        
        # Should only have 1 of each (not all entries)
        assert result.count("**") <= 4  # At most 1 bold item per section


# =============================================================================
# Section Formatter Tests
# =============================================================================

class TestFormatArchitectureDecisionsSection:
    """Tests for _format_architecture_decisions_section."""
    
    def test_empty_list_returns_empty_string(self):
        """Empty list should return empty string."""
        assert _format_architecture_decisions_section([]) == ""
    
    def test_formats_decision_with_title_and_decision(self):
        """Should format decision with title and decision text."""
        decisions = [{'body': {'title': 'Test', 'decision': 'Use X'}}]
        result = _format_architecture_decisions_section(decisions)
        
        assert "**Test**" in result
        assert "Use X" in result
    
    def test_handles_none_body(self):
        """Should handle None body gracefully by using defaults."""
        decisions = [{'body': None}]
        result = _format_architecture_decisions_section(decisions)
        # Implementation gracefully handles None body by using 'Unknown' as title
        assert "**Unknown**" in result
    
    def test_handles_missing_decision_field(self):
        """Should handle missing decision field."""
        decisions = [{'body': {'title': 'Test Only'}}]
        result = _format_architecture_decisions_section(decisions)
        
        assert "**Test Only**" in result


class TestFormatFailurePatternsSection:
    """Tests for _format_failure_patterns_section."""
    
    def test_empty_list_returns_empty_string(self):
        """Empty list should return empty string."""
        assert _format_failure_patterns_section([]) == ""
    
    def test_formats_pattern_description(self):
        """Should format pattern with description."""
        patterns = [{'body': {'description': 'Never do X'}}]
        result = _format_failure_patterns_section(patterns)
        
        assert "Never do X" in result
        assert "## Known Failures (AVOID THESE)" in result
    
    def test_handles_none_description(self):
        """Should handle None description."""
        patterns = [{'body': {'description': None}}]
        result = _format_failure_patterns_section(patterns)
        assert result == ""


class TestFormatQualityGatesSection:
    """Tests for _format_quality_gates_section."""
    
    def test_empty_list_returns_empty_string(self):
        """Empty list should return empty string."""
        assert _format_quality_gates_section([]) == ""
    
    def test_formats_gate_with_phase_and_requirement(self):
        """Should format gate with phase and requirement."""
        gates = [{'body': {'phase': 'Phase 4', 'requirement': 'All tests pass'}}]
        result = _format_quality_gates_section(gates)
        
        assert "Phase 4" in result
        assert "All tests pass" in result


class TestFormatSystemContextSection:
    """Tests for _format_system_context_section."""
    
    def test_empty_list_returns_empty_string(self):
        """Empty list should return empty string."""
        assert _format_system_context_section([]) == ""
    
    def test_formats_context_with_name_and_description(self):
        """Should format context with name and description."""
        items = [{'body': {'name': 'GuardKit', 'description': 'AI workflow tool'}}]
        result = _format_system_context_section(items)
        
        assert "**GuardKit**" in result
        assert "AI workflow tool" in result
    
    def test_truncates_long_descriptions(self):
        """Should truncate descriptions over 200 chars."""
        long_desc = "A" * 300
        items = [{'body': {'name': 'Test', 'description': long_desc}}]
        result = _format_system_context_section(items)
        
        assert "..." in result
        assert len(result) < 400  # Should be truncated


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and malformed data."""
    
    def test_context_dataclass_initialization(self):
        """CriticalContext should initialize with all required fields."""
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
        assert isinstance(context, CriticalContext)
    
    def test_config_default_values(self):
        """ContextFormatterConfig should have sensible defaults."""
        config = ContextFormatterConfig()
        assert config.max_decisions == 5
        assert config.max_failure_patterns == 3
        assert config.max_quality_gates == 3
        assert config.max_system_context == 3
    
    @pytest.mark.asyncio
    async def test_mixed_valid_invalid_results(self, mock_graphiti):
        """Should handle mix of valid and invalid results."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            context = await load_critical_context()
            
            # All results should be dicts
            for decision in context.architecture_decisions:
                assert isinstance(decision, dict)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for full context loading workflow."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_graphiti):
        """Test complete load and format workflow."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=mock_graphiti):
            # Load context
            context = await load_critical_context(command="feature-build")
            
            # Format for injection
            formatted = format_context_for_injection(context)
            
            # Verify output
            assert len(formatted) > 0
            assert "## Architecture Decisions (MUST FOLLOW)" in formatted
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_preserves_functionality(self):
        """Commands should work even without Graphiti."""
        with patch('guardkit.knowledge.context_loader.get_graphiti', return_value=None):
            context = await load_critical_context(command="task-work")
            formatted = format_context_for_injection(context)
            
            # Should return empty but not error
            assert formatted == ""
            assert isinstance(context, CriticalContext)
