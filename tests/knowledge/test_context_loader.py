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
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=None):
            context = await load_critical_context()
            assert context.system_context == []
            assert context.architecture_decisions == []
    
    @pytest.mark.asyncio
    async def test_returns_empty_when_graphiti_disabled(self):
        """Should return empty context when graphiti.enabled is False."""
        mock_client = MagicMock()
        mock_client.enabled = False
        
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_client):
            context = await load_critical_context()
            assert context.system_context == []
            assert context.architecture_decisions == []
    
    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self):
        """Should return empty context on any exception."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_client):
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
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
            context = await load_critical_context()
            
            assert len(context.system_context) > 0
            assert len(context.quality_gates) > 0
            assert len(context.architecture_decisions) > 0
            assert len(context.failure_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_feature_build_loads_extra_context(self, mock_graphiti):
        """Feature-build command should load additional context."""
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
            context = await load_critical_context(command="feature-build")
            
            # System context should include feature-build specific items
            assert len(context.system_context) > 0
    
    @pytest.mark.asyncio
    async def test_task_work_command(self, mock_graphiti):
        """task-work command should load standard context."""
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
            context = await load_critical_context(command="task-work")
            
            assert len(context.architecture_decisions) > 0
            assert len(context.failure_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_with_task_id(self, mock_graphiti):
        """Should accept task_id parameter (future functionality)."""
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
            context = await load_critical_context(task_id="TASK-001")
            
            # Currently just loads standard context
            assert isinstance(context, CriticalContext)
    
    @pytest.mark.asyncio
    async def test_with_feature_id(self, mock_graphiti):
        """Should accept feature_id parameter (future functionality)."""
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
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
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
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
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=mock_graphiti):
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
        with patch('guardkit.knowledge.context_loader.get_memory_client', return_value=None):
            context = await load_critical_context(command="task-work")
            formatted = format_context_for_injection(context)
            
            # Should return empty but not error
            assert formatted == ""
            assert isinstance(context, CriticalContext)


# ============================================================================
# Real-seam tests (FEAT-MEM-09 W1 / TASK-MEM09-CTXLOAD)
#
# The tests above MagicMock the fleet-memory client — the primary first-party
# seam. Per .claude/rules/per-task-green-is-not-feature-green.md that is absent
# integration evidence. The tests below exercise the REAL
# get_memory_client() -> FleetMemoryClient.search() -> fleet_memory_mapping
# path, stubbing ONLY the external fleet_memory.retrieval edge, and prove each
# _load_* resolves its group_ids to the correct payload_types/domain_tags.
# ============================================================================


def _install_fake_fleet_memory_retrieval(monkeypatch, *, context_block, coverage, captured):
    """Fake ONLY the external fleet_memory.retrieval edge, capturing the real
    SearchRequest the shim builds. Mirrors the helper in
    tests/unit/knowledge/test_fleet_memory_client.py (TASK-MEM08-011)."""
    import sys
    import types

    class _FakeSearchRequest:
        def __init__(self, **kw):
            captured["request"] = kw

    async def _fake_search(request, store):
        captured["store"] = store
        # Contract-shaped items: search() reads .score and .value dict
        # (natural_key/content) for per-item retrieval logging (FEAT-ABL-001).
        return [
            types.SimpleNamespace(
                score=0.9, value={"natural_key": "r1", "content": "result one"}
            ),
            types.SimpleNamespace(
                score=0.8, value={"natural_key": "r2", "content": "result two"}
            ),
        ]

    class _FakeAssembly:
        pass

    def _fake_assemble(results, token_budget):
        a = _FakeAssembly()
        a.context_block = context_block
        a.coverage_score = coverage
        return a

    retrieval = types.ModuleType("fleet_memory.retrieval")
    retrieval.SearchRequest = _FakeSearchRequest
    retrieval.search = _fake_search
    retrieval.assemble_context = _fake_assemble
    fm = types.ModuleType("fleet_memory")
    fm.retrieval = retrieval
    monkeypatch.setitem(sys.modules, "fleet_memory", fm)
    monkeypatch.setitem(sys.modules, "fleet_memory.retrieval", retrieval)


def _enabled_fleet_client():
    """A REAL FleetMemoryClient (NOT a mock) with reads enabled + store
    pre-opened so initialize() is skipped. Exercises the real shim + mapping."""
    from guardkit.knowledge.fleet_memory_client import (
        FleetMemoryClient,
        FleetMemoryConfig,
    )

    client = FleetMemoryClient(
        FleetMemoryConfig(
            enabled=True,
            postgres_dsn="postgresql://t:t@localhost:5433/t",
            embed_url="http://localhost:9000/v1",
            embed_model="nomic-embed",
            embed_dims=768,
            nats_url="nats://localhost:4222",
        )
    )
    client._read_available = True
    client._store = object()
    return client


class TestContextLoaderRealSeam:
    """Exercise the REAL fleet-memory read seam (not a MagicMock)."""

    @pytest.mark.asyncio
    async def test_load_architecture_decisions_resolves_migrate_group(self, monkeypatch):
        """_load_architecture_decisions -> real mapping -> adr + document / [system]."""
        from guardkit.knowledge.context_loader import _load_architecture_decisions

        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="ADR: SDK subprocess delegation",
            coverage=0.8,
            captured=captured,
        )
        client = _enabled_fleet_client()

        results = await _load_architecture_decisions(client)

        req = captured["request"]
        # migrate group -> payload_types {adr, document}, domain_tags [system]
        # computed by the REAL fleet_memory_mapping.resolve (not a mock).
        assert sorted(req["payload_types"]) == ["adr", "document"]
        assert req["domain_tags"] == ["system"]
        assert req["query"] == "architecture decision SDK subprocess worktree delegation"
        # the real search() adaptation ran end-to-end
        assert results and results[0]["fact"] == "ADR: SDK subprocess delegation"

    @pytest.mark.asyncio
    async def test_load_system_context_retire_groups_search_whole_store(self, monkeypatch):
        """_load_system_context reads only RETIRE groups -> empty filters -> whole-store."""
        from guardkit.knowledge.context_loader import _load_system_context

        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="GuardKit is a task workflow system",
            coverage=0.5,
            captured=captured,
        )
        client = _enabled_fleet_client()

        await _load_system_context(client)

        req = captured["request"]
        # product_knowledge + command_workflows are RETIRE -> no typed filter
        # (whole-store semantic search over the harvest corpus).
        assert req["payload_types"] == []
        assert req["domain_tags"] == []
        assert req["query"] == "GuardKit product workflow quality gate"

    @pytest.mark.asyncio
    async def test_load_failure_patterns_resolves_migrate_warning(self, monkeypatch):
        """_load_failure_patterns -> real mapping -> warning + document / [failure, pattern]."""
        from guardkit.knowledge.context_loader import _load_failure_patterns

        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch,
            context_block="Do not mock the primary seam",
            coverage=0.6,
            captured=captured,
        )
        client = _enabled_fleet_client()

        await _load_failure_patterns(client)

        req = captured["request"]
        assert sorted(req["payload_types"]) == ["document", "warning"]
        assert req["domain_tags"] == ["failure", "pattern"]

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_load_critical_context_returns_real_hits_live(self):
        """Operator-run proof: with the store ENABLED, load_critical_context returns
        real hits. Skips cleanly when the store is disabled (autobuild / CI)."""
        from guardkit.knowledge.fleet_memory_client import get_memory_client

        client = get_memory_client()
        if client is None or not getattr(client, "enabled", False):
            pytest.skip("fleet-memory store not enabled (Status: DISABLED)")

        ctx = await load_critical_context(command="feature-build")
        assert (
            ctx.system_context
            or ctx.quality_gates
            or ctx.architecture_decisions
            or ctx.failure_patterns
        ), "expected at least one enrichment field populated from the live store"
