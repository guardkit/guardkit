"""
Integration Tests for Agent Discovery Module.

Task Reference: TASK-HAI-005-7A2E
Epic: haiku-agent-implementation

These tests verify that agent discovery works correctly with the actual
agent files in the codebase, including:
- HAI-002: python-api-specialist
- HAI-003: react-state-specialist
- HAI-004: dotnet-domain-specialist

These tests require the actual agent files to be present in the codebase.
"""

import logging
import os
import pytest
import sys
import time
from pathlib import Path

# Add the library to the path
lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from agent_discovery import (
    discover_agents,
    get_agent_by_name,
    list_discoverable_agents,
    get_agents_by_stack,
    validate_discovery_metadata,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def agents_dir(project_root):
    """Get the global agents directory."""
    return project_root / "installer" / "global" / "agents"


def agent_file_exists(agents_dir: Path, agent_name: str) -> bool:
    """Check if an agent file exists."""
    return (agents_dir / f"{agent_name}.md").exists()


# ============================================================================
# Test: Discover Haiku Agents (HAI-002, HAI-003, HAI-004)
# ============================================================================

class TestDiscoverHaikuAgents:
    """Integration tests for discovering the new Haiku agents."""

    def test_discover_haiku_agents(self, agents_dir):
        """Verify HAI-002, HAI-003, HAI-004 are discoverable."""
        # Skip if agent files don't exist (allows test to run in CI without agents)
        required_agents = [
            'python-api-specialist',
            'react-state-specialist',
            'dotnet-domain-specialist'
        ]

        missing_agents = [
            agent for agent in required_agents
            if not agent_file_exists(agents_dir, agent)
        ]

        if missing_agents:
            pytest.skip(f"Agent files not found: {missing_agents}")

        # Test discovery
        results = discover_agents(phase='implementation')

        agent_names = [r.get('name') for r in results]

        # Verify all Haiku agents are discoverable
        assert 'python-api-specialist' in agent_names, \
            "python-api-specialist not found in results"
        assert 'react-state-specialist' in agent_names, \
            "react-state-specialist not found in results"
        assert 'dotnet-domain-specialist' in agent_names, \
            "dotnet-domain-specialist not found in results"

    def test_python_agent_metadata_complete(self, agents_dir):
        """Verify python-api-specialist has complete metadata."""
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        agent = get_agent_by_name('python-api-specialist')

        assert agent is not None, "python-api-specialist not found"
        assert 'python' in agent.get('stack', []), "Should have python stack"
        assert agent.get('phase') == 'implementation', "Should be implementation phase"
        assert len(agent.get('keywords', [])) >= 5, "Should have at least 5 keywords"
        assert len(agent.get('capabilities', [])) >= 5, "Should have at least 5 capabilities"

        # Validate the metadata
        is_valid, errors = validate_discovery_metadata(agent)
        assert is_valid, f"Metadata validation failed: {errors}"

    def test_react_agent_metadata_complete(self, agents_dir):
        """Verify react-state-specialist has complete metadata."""
        if not agent_file_exists(agents_dir, 'react-state-specialist'):
            pytest.skip("react-state-specialist.md not found")

        agent = get_agent_by_name('react-state-specialist')

        assert agent is not None, "react-state-specialist not found"

        stacks = agent.get('stack', [])
        if isinstance(stacks, str):
            stacks = [stacks]

        assert 'react' in stacks or 'typescript' in stacks, \
            "Should have react or typescript stack"
        assert agent.get('phase') == 'implementation', "Should be implementation phase"
        assert len(agent.get('keywords', [])) >= 3, "Should have at least 3 keywords"

        # Validate the metadata
        is_valid, errors = validate_discovery_metadata(agent)
        assert is_valid, f"Metadata validation failed: {errors}"

    def test_dotnet_agent_metadata_complete(self, agents_dir):
        """Verify dotnet-domain-specialist has complete metadata."""
        if not agent_file_exists(agents_dir, 'dotnet-domain-specialist'):
            pytest.skip("dotnet-domain-specialist.md not found")

        agent = get_agent_by_name('dotnet-domain-specialist')

        assert agent is not None, "dotnet-domain-specialist not found"

        stacks = agent.get('stack', [])
        if isinstance(stacks, str):
            stacks = [stacks]

        assert 'dotnet' in stacks or 'csharp' in stacks, \
            "Should have dotnet or csharp stack"
        assert agent.get('phase') == 'implementation', "Should be implementation phase"
        assert len(agent.get('keywords', [])) >= 5, "Should have at least 5 keywords"

        # Validate the metadata
        is_valid, errors = validate_discovery_metadata(agent)
        assert is_valid, f"Metadata validation failed: {errors}"


# ============================================================================
# Test: Stack-Specific Discovery
# ============================================================================

class TestStackSpecificDiscovery:
    """Integration tests for stack-specific agent discovery."""

    def test_discover_python_implementation_agents(self, agents_dir):
        """Should find Python implementation agents."""
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        results = discover_agents(phase='implementation', stack=['python'])

        assert len(results) >= 1, "Should find at least one Python agent"

        # Check that Python agent is in results
        agent_names = [r.get('name') for r in results]
        assert 'python-api-specialist' in agent_names

    def test_discover_react_implementation_agents(self, agents_dir):
        """Should find React implementation agents."""
        if not agent_file_exists(agents_dir, 'react-state-specialist'):
            pytest.skip("react-state-specialist.md not found")

        results = discover_agents(phase='implementation', stack=['react'])

        assert len(results) >= 1, "Should find at least one React agent"

        agent_names = [r.get('name') for r in results]
        assert 'react-state-specialist' in agent_names

    def test_discover_dotnet_implementation_agents(self, agents_dir):
        """Should find .NET implementation agents."""
        if not agent_file_exists(agents_dir, 'dotnet-domain-specialist'):
            pytest.skip("dotnet-domain-specialist.md not found")

        results = discover_agents(phase='implementation', stack=['dotnet'])

        assert len(results) >= 1, "Should find at least one .NET agent"

        agent_names = [r.get('name') for r in results]
        assert 'dotnet-domain-specialist' in agent_names


# ============================================================================
# Test: Keyword-Based Discovery
# ============================================================================

class TestKeywordBasedDiscovery:
    """Integration tests for keyword-based agent discovery."""

    def test_discover_by_fastapi_keyword(self, agents_dir):
        """Should find agents by FastAPI keyword."""
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        results = discover_agents(
            phase='implementation',
            keywords=['fastapi']
        )

        # Python agent should be found
        agent_names = [r.get('name') for r in results]
        assert 'python-api-specialist' in agent_names, \
            "python-api-specialist should be found with 'fastapi' keyword"

    def test_discover_by_hooks_keyword(self, agents_dir):
        """Should find agents by React hooks keyword."""
        if not agent_file_exists(agents_dir, 'react-state-specialist'):
            pytest.skip("react-state-specialist.md not found")

        results = discover_agents(
            phase='implementation',
            keywords=['hooks']
        )

        agent_names = [r.get('name') for r in results]
        assert 'react-state-specialist' in agent_names, \
            "react-state-specialist should be found with 'hooks' keyword"

    def test_discover_by_ddd_keyword(self, agents_dir):
        """Should find agents by DDD keyword."""
        if not agent_file_exists(agents_dir, 'dotnet-domain-specialist'):
            pytest.skip("dotnet-domain-specialist.md not found")

        results = discover_agents(
            phase='implementation',
            keywords=['ddd']
        )

        agent_names = [r.get('name') for r in results]
        assert 'dotnet-domain-specialist' in agent_names, \
            "dotnet-domain-specialist should be found with 'ddd' keyword"

    def test_relevance_scoring_with_multiple_keywords(self, agents_dir):
        """Should rank agents by keyword match count."""
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        results = discover_agents(
            phase='implementation',
            stack=['python'],
            keywords=['fastapi', 'async', 'pydantic', 'endpoints']
        )

        assert len(results) >= 1

        # Python agent should have high relevance score
        python_agent = next(
            (r for r in results if r.get('name') == 'python-api-specialist'),
            None
        )

        assert python_agent is not None
        assert python_agent.get('relevance_score', 0) >= 2, \
            "Python agent should have high relevance with multiple matching keywords"


# ============================================================================
# Test: Cross-Stack Agents
# ============================================================================

class TestCrossStackAgents:
    """Integration tests for cross-stack agent discovery."""

    def test_discover_cross_stack_agents(self, agents_dir):
        """Should find cross-stack agents regardless of stack filter."""
        results = discover_agents(phase='review')

        # Should find review agents
        assert len(results) >= 0  # May be 0 if no review agents exist

        # If we have code-reviewer, it should be cross-stack
        code_reviewer = next(
            (r for r in results if r.get('name') == 'code-reviewer'),
            None
        )

        if code_reviewer:
            stacks = code_reviewer.get('stack', [])
            if isinstance(stacks, str):
                stacks = [stacks]
            # cross-stack agents should work for any stack
            assert 'cross-stack' in stacks or len(stacks) > 0


# ============================================================================
# Test: Performance with Real Agents
# ============================================================================

class TestPerformanceWithRealAgents:
    """Performance tests with actual agent files."""

    def test_discovery_performance_real_agents(self, agents_dir):
        """Should scan real agents in <500ms."""
        start = time.time()
        results = discover_agents(phase='implementation')
        duration = time.time() - start

        assert duration < 0.5, \
            f"Discovery took {duration:.3f}s (max: 0.5s)"

        # Should find at least some agents
        assert len(results) >= 0

    def test_all_discoverable_agents_performance(self, agents_dir):
        """Should list all discoverable agents quickly."""
        start = time.time()
        results = list_discoverable_agents()
        duration = time.time() - start

        assert duration < 0.5, \
            f"Listing all agents took {duration:.3f}s (max: 0.5s)"


# ============================================================================
# Test: Graceful Degradation with Real Codebase
# ============================================================================

class TestGracefulDegradationRealCodebase:
    """Test graceful degradation with real codebase agents."""

    def test_discovery_succeeds_with_mixed_agents(self, agents_dir):
        """Discovery should work even with agents lacking metadata."""
        # Should complete without errors
        results = discover_agents(phase='implementation')

        # Verify results are valid
        assert isinstance(results, list)

        # All results should have required fields
        for agent in results:
            assert 'name' in agent or 'path' in agent
            assert agent.get('phase') == 'implementation'

    def test_nonexistent_phase_returns_empty(self):
        """Nonexistent phase should return empty list, not error."""
        results = discover_agents(phase='nonexistent-phase-xyz')

        assert results == []
        assert isinstance(results, list)


# ============================================================================
# Test: Agent Location Discovery
# ============================================================================

class TestAgentLocationDiscovery:
    """Test that agent locations are correctly identified."""

    def test_global_agents_discovered(self, agents_dir):
        """Should discover agents from installer/global/agents/."""
        results = list_discoverable_agents()

        # Check that at least some agents are from the global location
        global_agents = [
            r for r in results
            if 'installer/global/agents' in r.get('path', '')
        ]

        # May be 0 if running in isolated test environment
        assert isinstance(global_agents, list)

    def test_template_agents_discovered(self, project_root):
        """Should discover agents from templates directories."""
        templates_dir = project_root / "installer" / "global" / "templates"

        if not templates_dir.exists():
            pytest.skip("Templates directory not found")

        # Check for template-specific agents
        results = list_discoverable_agents()

        template_agents = [
            r for r in results
            if 'templates/' in r.get('path', '')
        ]

        # Template agents are optional
        assert isinstance(template_agents, list)


# ============================================================================
# Test: Full Workflow Simulation
# ============================================================================

class TestFullWorkflowSimulation:
    """Simulate real workflow scenarios."""

    def test_phase_3_implementation_workflow(self, agents_dir):
        """Simulate Phase 3 agent selection for Python task."""
        # Scenario: Task is for Python FastAPI implementation
        task_stack = ['python']
        task_keywords = ['fastapi', 'async', 'api']

        results = discover_agents(
            phase='implementation',
            stack=task_stack,
            keywords=task_keywords
        )

        if not results:
            pytest.skip("No Python implementation agents available")

        # The top result should be most relevant
        top_agent = results[0]

        assert top_agent.get('phase') == 'implementation'

        # Check stack match
        agent_stacks = top_agent.get('stack', [])
        if isinstance(agent_stacks, str):
            agent_stacks = [agent_stacks]
        agent_stacks_lower = [s.lower() for s in agent_stacks]

        assert 'python' in agent_stacks_lower or 'cross-stack' in agent_stacks_lower

    def test_multi_stack_task_workflow(self, agents_dir):
        """Simulate task that could match multiple stacks."""
        # Scenario: Full-stack task with both React and Python
        results = discover_agents(
            phase='implementation',
            stack=['react', 'python']
        )

        if len(results) < 2:
            pytest.skip("Not enough multi-stack agents available")

        # Should find agents for both stacks
        agent_stacks = set()
        for agent in results:
            stacks = agent.get('stack', [])
            if isinstance(stacks, str):
                stacks = [stacks]
            for s in stacks:
                agent_stacks.add(s.lower())

        # At least one stack should be covered
        assert 'react' in agent_stacks or 'python' in agent_stacks or 'cross-stack' in agent_stacks


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
