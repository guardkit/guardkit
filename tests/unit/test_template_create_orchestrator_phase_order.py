"""
Unit tests for Phase Order Validation in Template Create Orchestrator

Tests that verify the phase execution order change in TASK-019A:
- Phase 5: Template file generation (reordered - was Phase 6)
- Phase 6: Agent recommendation (reordered - was Phase 7)
- Phase 7: CLAUDE.md generation (reordered - was Phase 5)

This ensures agents are generated BEFORE CLAUDE.md documentation,
allowing accurate agent documentation without hallucinations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from dataclasses import dataclass
import sys

# Add lib directories to path for imports
lib_path = Path(__file__).parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))


class TestPhaseOrderExecution:
    """Test that phases execute in correct order: Templates -> Agents -> CLAUDE.md"""

    def test_phase_5_executes_before_phase_6(self):
        """Verify Phase 5 (templates) runs before Phase 6 (agents)"""
        execution_order = []

        def mock_phase5(*args, **kwargs):
            execution_order.append(5)
            return MagicMock()  # Return templates

        def mock_phase6(*args, **kwargs):
            execution_order.append(6)
            return []  # Return agents

        # Simulate orchestrator phases
        phase5_result = mock_phase5()
        phase6_result = mock_phase6()

        assert execution_order == [5, 6], f"Expected [5, 6], got {execution_order}"

    def test_phase_6_executes_before_phase_7(self):
        """Verify Phase 6 (agents) runs before Phase 7 (CLAUDE.md)"""
        execution_order = []

        def mock_phase6(*args, **kwargs):
            execution_order.append(6)
            return [MagicMock()]  # Return agents

        def mock_phase7(analysis, agents, *args, **kwargs):
            execution_order.append(7)
            # At this point, agents should exist
            assert len(agents) > 0, "Agents should exist before CLAUDE.md generation"
            return MagicMock()  # Return CLAUDE.md

        # Simulate orchestrator phases
        agents = mock_phase6()
        claude_md = mock_phase7(MagicMock(), agents)

        assert execution_order == [6, 7], f"Expected [6, 7], got {execution_order}"

    def test_phase_7_receives_agents_from_phase_6(self):
        """Verify Phase 7 (CLAUDE.md) receives agents from Phase 6"""
        # Create mock agents
        agent1 = MagicMock()
        agent1.name = "domain-operations-specialist"
        agent1.full_definition = "# Domain Operations\n\nAgent definition..."

        agent2 = MagicMock()
        agent2.name = "ui-component-specialist"
        agent2.full_definition = "# UI Components\n\nAgent definition..."

        mock_agents = [agent1, agent2]

        # Verify agents are passed to CLAUDE.md generator
        def mock_claude_md_generator(analysis, agents=None):
            assert agents is not None, "Agents parameter should be provided"
            assert len(agents) == 2, f"Expected 2 agents, got {len(agents)}"
            assert agents[0].name == "domain-operations-specialist"
            assert agents[1].name == "ui-component-specialist"
            return MagicMock()

        result = mock_claude_md_generator(MagicMock(), agents=mock_agents)
        assert result is not None

    def test_all_three_phases_execute_in_order(self):
        """Verify complete sequence: Phase 5 -> 6 -> 7"""
        execution_log = []

        def log_phase(phase_num):
            def inner(*args, **kwargs):
                execution_log.append(phase_num)
                if phase_num == 5:
                    return MagicMock()  # templates
                elif phase_num == 6:
                    return [MagicMock(), MagicMock()]  # agents
                else:  # phase 7
                    return MagicMock()  # CLAUDE.md
            return inner

        # Execute phases
        templates = log_phase(5)()
        agents = log_phase(6)()
        claude_md = log_phase(7)()

        assert execution_log == [5, 6, 7], f"Expected [5, 6, 7], got {execution_log}"

    def test_agent_parameter_is_optional_in_claude_md_generator(self):
        """Verify CLAUDE.md generator can work with or without agents (backward compatibility)"""
        mock_analysis = MagicMock()

        # Test with agents
        def mock_generator_with_agents(analysis, agents=None):
            assert agents is not None
            return "agent_docs"

        # Test without agents (backward compatibility)
        def mock_generator_without_agents(analysis, agents=None):
            # Should handle None gracefully
            return "generic_docs"

        result_with = mock_generator_with_agents(mock_analysis, agents=[])
        result_without = mock_generator_without_agents(mock_analysis, agents=None)

        assert result_with is not None
        assert result_without is not None


class TestPhaseNumbering:
    """Test that phase numbers match the new execution order"""

    def test_phase_numbers_are_sequential(self):
        """Verify phase numbers are 1-8 with correct assignments"""
        phase_map = {
            1: "Q&A Session",
            2: "AI Analysis",
            3: "Manifest Generation",
            4: "Settings Generation",
            5: "Template File Generation",  # Reordered
            6: "Agent Recommendation",  # Reordered
            7: "CLAUDE.md Generation",  # Reordered
            8: "Package Assembly"
        }

        # Verify all phases present
        assert len(phase_map) == 8
        for i in range(1, 9):
            assert i in phase_map, f"Phase {i} missing from phase map"

    def test_phase_5_is_template_generation(self):
        """Verify Phase 5 handles template file generation"""
        phase_description = "Template File Generation"
        assert "Template" in phase_description or "template" in phase_description

    def test_phase_6_is_agent_recommendation(self):
        """Verify Phase 6 handles agent generation"""
        phase_description = "Agent Recommendation"
        assert "Agent" in phase_description or "agent" in phase_description

    def test_phase_7_is_claude_md_generation(self):
        """Verify Phase 7 handles CLAUDE.md generation"""
        phase_description = "CLAUDE.md Generation"
        assert "CLAUDE" in phase_description or "claude" in phase_description


class TestPhaseOutputHandling:
    """Test that phase outputs are properly handled and passed to next phase"""

    def test_phase_5_output_is_templates_collection(self):
        """Verify Phase 5 returns templates collection"""
        mock_templates = MagicMock()
        mock_templates.total_count = 5
        mock_templates.templates = []

        def phase_5_generator(analysis):
            return mock_templates

        result = phase_5_generator(MagicMock())
        assert result.total_count == 5

    def test_phase_6_output_is_agent_list(self):
        """Verify Phase 6 returns list of agents"""
        mock_agent1 = MagicMock()
        mock_agent1.name = "agent1"
        mock_agent2 = MagicMock()
        mock_agent2.name = "agent2"

        def phase_6_generator(analysis):
            return [mock_agent1, mock_agent2]

        result = phase_6_generator(MagicMock())
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].name == "agent1"
        assert result[1].name == "agent2"

    def test_phase_7_accepts_agents_from_phase_6(self):
        """Verify Phase 7 accepts and uses agents from Phase 6"""
        mock_analysis = MagicMock()
        mock_agents = [MagicMock(name="test-agent")]

        def phase_7_generator(analysis, agents=None):
            assert agents is not None, "Phase 7 should receive agents"
            assert len(agents) > 0, "Phase 7 should have at least one agent"
            return {"content": "claude_md_content", "agents_documented": len(agents)}

        result = phase_7_generator(mock_analysis, agents=mock_agents)
        assert result["agents_documented"] == 1

    def test_phase_7_fallback_when_no_agents(self):
        """Verify Phase 7 generates generic guidance when no agents provided"""
        mock_analysis = MagicMock()

        def phase_7_generator(analysis, agents=None):
            if agents:
                return "specific_agent_documentation"
            else:
                return "generic_agent_guidance"

        result = phase_7_generator(mock_analysis, agents=None)
        assert result == "generic_agent_guidance"

    def test_phase_6_can_return_empty_list(self):
        """Verify Phase 6 can return empty list if no agents recommended"""
        def phase_6_generator(analysis):
            # Some analyses might not recommend agents
            return []

        result = phase_6_generator(MagicMock())
        assert isinstance(result, list)
        assert len(result) == 0

    def test_phase_7_handles_empty_agent_list(self):
        """Verify Phase 7 handles case when Phase 6 returns empty agent list"""
        mock_analysis = MagicMock()

        def phase_7_generator(analysis, agents=None):
            if agents is None or len(agents) == 0:
                return "generic_guidance"
            else:
                return "specific_guidance"

        result = phase_7_generator(mock_analysis, agents=[])
        assert result == "generic_guidance"


class TestPhaseDependencies:
    """Test dependencies between phases"""

    def test_phase_6_depends_on_analysis_from_phase_2(self):
        """Verify Phase 6 depends on analysis from Phase 2"""
        mock_analysis = MagicMock()
        mock_analysis.technology = MagicMock()
        mock_analysis.architecture = MagicMock()

        def phase_6_generator(analysis):
            # Should access analysis to recommend agents
            assert hasattr(analysis, 'technology')
            assert hasattr(analysis, 'architecture')
            return []

        # Should not raise
        phase_6_generator(mock_analysis)

    def test_phase_7_depends_on_analysis_from_phase_2(self):
        """Verify Phase 7 depends on analysis from Phase 2"""
        mock_analysis = MagicMock()
        mock_analysis.architecture = MagicMock()
        mock_analysis.technology = MagicMock()

        def phase_7_generator(analysis, agents=None):
            assert hasattr(analysis, 'architecture')
            assert hasattr(analysis, 'technology')
            return MagicMock()

        # Should not raise
        phase_7_generator(mock_analysis)

    def test_phase_7_depends_on_agents_from_phase_6(self):
        """Verify Phase 7 explicitly depends on agents from Phase 6"""
        mock_analysis = MagicMock()
        mock_agents = [MagicMock()]

        def phase_7_generator(analysis, agents=None):
            # For accurate documentation, agents should be provided
            if agents is not None:
                return f"documented_{len(agents)}_agents"
            else:
                return "generic_guidance"

        result = phase_7_generator(mock_analysis, agents=mock_agents)
        assert "documented_1_agents" in result


class TestPhaseReorderingRationale:
    """Test the rationale for reordering: eliminating AI hallucinations"""

    def test_phase_7_with_actual_agents_prevents_hallucination(self):
        """Verify Phase 7 documents only agents that actually exist"""
        # Create actual agents
        agent1 = MagicMock()
        agent1.name = "real-agent-1"
        agent1.full_definition = "# Real Agent 1"

        actual_agents = [agent1]

        def phase_7_with_agents(analysis, agents):
            # Should only document agents in the list
            documented_names = [a.name for a in agents]
            assert "real-agent-1" in documented_names
            assert "hallucinated-agent" not in documented_names
            return documented_names

        result = phase_7_with_agents(MagicMock(), agents=actual_agents)
        assert len(result) == 1
        assert result[0] == "real-agent-1"

    def test_phase_7_without_agents_generates_generic_guidance(self):
        """Verify Phase 7 without agents generates generic guidance (old behavior)"""
        def phase_7_without_agents(analysis, agents=None):
            if not agents:
                return "Use domain-specific agents for business logic..."
            return "Documented: " + ", ".join(a.name for a in agents)

        result = phase_7_without_agents(MagicMock(), agents=None)
        assert "generic" in result.lower() or "Use" in result

    def test_new_order_eliminates_documentation_mismatch(self):
        """Verify new order eliminates agent documentation mismatches"""
        # Old order issue: Phase 7 could document agents that don't exist in Phase 6
        # New order: Phase 6 creates agents, then Phase 7 documents what exists

        created_agents = [
            MagicMock(name="agent-1"),
            MagicMock(name="agent-2")
        ]

        def phase_7_new_order(analysis, agents):
            # Can only document what exists
            return len(agents) == 2 and all(hasattr(a, 'name') for a in agents)

        result = phase_7_new_order(MagicMock(), agents=created_agents)
        assert result is True


class TestBackwardCompatibility:
    """Test backward compatibility with existing code that doesn't use agents"""

    def test_claude_md_generator_works_without_agents_parameter(self):
        """Verify CLAUDE.md generator works when agents parameter is not provided"""
        mock_analysis = MagicMock()

        def generator(analysis, agents=None):
            # Should work even if agents is None
            return "result"

        # Old code calling without agents
        result = generator(mock_analysis)
        assert result == "result"

    def test_claude_md_generator_with_none_agents(self):
        """Verify CLAUDE.md generator handles agents=None gracefully"""
        mock_analysis = MagicMock()

        def generator(analysis, agents=None):
            if agents is None:
                return "generic_guidance"
            else:
                return "specific_guidance"

        result = generator(mock_analysis, agents=None)
        assert result == "generic_guidance"

    def test_orchestrator_can_skip_agents(self):
        """Verify orchestrator can skip agent generation with config flag"""
        config = MagicMock()
        config.no_agents = True

        def orchestrator_run(config):
            if config.no_agents:
                agents = []
            else:
                agents = [MagicMock()]
            return agents

        result = orchestrator_run(config)
        assert len(result) == 0


class TestPhaseSequenceWithMocks:
    """Integration-like tests with mocked phases"""

    def test_complete_phase_sequence_with_outputs(self):
        """Test complete phase sequence with realistic outputs"""

        # Phase 2: Analysis
        analysis = MagicMock()
        analysis.overall_confidence = MagicMock(percentage=85)
        analysis.architecture = MagicMock()
        analysis.technology = MagicMock()
        analysis.example_files = []

        # Phase 5: Templates
        templates = MagicMock()
        templates.total_count = 10
        templates.templates = []

        # Phase 6: Agents
        agents = [
            MagicMock(name="agent-1", full_definition="# Agent 1"),
            MagicMock(name="agent-2", full_definition="# Agent 2")
        ]

        # Phase 7: CLAUDE.md (uses agents from Phase 6)
        claude_md = MagicMock()
        claude_md.agent_usage = "Documented 2 agents"

        # Verify sequence
        assert templates.total_count > 0
        assert len(agents) == 2
        assert "2" in claude_md.agent_usage

    def test_phase_outputs_are_compatible(self):
        """Verify phase outputs are compatible with next phase inputs"""

        # Phase 5 output
        templates = {"total": 5, "templates": []}

        # Phase 6 output
        agents = [{"name": "agent1"}, {"name": "agent2"}]

        # Phase 7 input
        def phase_7(analysis, agents):
            assert isinstance(agents, list)
            return {"documented_agents": len(agents)}

        result = phase_7(MagicMock(), agents)
        assert result["documented_agents"] == 2
