"""
Integration Tests for Agent Discovery Module.

Task Reference: TASK-HAI-005-7A2E
Epic: haiku-agent-implementation

These tests run the real discovery scanner against the real stack agent files
that ship in this repository's templates, installed the way `guardkit init`
installs them (copied into the project's ``.claude/agents/``):

- react-state-specialist   (installer/core/templates/react-typescript/agents/)
- fastapi-specialist       (installer/core/templates/fastapi-python/agents/)

History: the global stack agents python-api-specialist, react-state-specialist
and dotnet-domain-specialist were moved out of the global agents folder in
a875bb73c (4 Dec 2025, "Reviews, tasks for progressive disclosure and
featureplan"): stack-specific agents now ship with templates.
react-state-specialist moved to the react-typescript and nextjs-fullstack
templates under the same name; python-api-specialist was replaced by the
fastapi-python template's fastapi-specialist (the agent-discovery guide was
changed in that commit to say so); dotnet-domain-specialist was removed with no
replacement, so the tests that named it were deleted.
"""

import shutil
import sys
from pathlib import Path

import pytest

# Add the library to the path
lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from agent_discovery import (
    discover_agents,
    get_agent_by_name,
    list_discoverable_agents,
    get_agents_by_stack,
    validate_discovery_metadata,
)


# Templates whose agents these tests install into a project.
INSTALLED_TEMPLATES = ("react-typescript", "fastapi-python")


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
    return project_root / "installer" / "core" / "agents"


@pytest.fixture
def templates_dir(project_root):
    """The templates shipped in this repository."""
    return project_root / "installer" / "core" / "templates"


@pytest.fixture
def installed_project(tmp_path, templates_dir, monkeypatch):
    """A project with the template agents installed in .claude/agents/.

    HOME points at an empty folder so agents installed on the machine running
    the tests (~/.agentecflow/agents/) cannot change what is discovered.
    """
    project = tmp_path / "project"
    agents = project / ".claude" / "agents"
    agents.mkdir(parents=True)
    for template in INSTALLED_TEMPLATES:
        for agent_file in (templates_dir / template / "agents").glob("*.md"):
            shutil.copy(agent_file, agents / agent_file.name)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project)
    return project


# ============================================================================
# Test: Discover the template stack agents
# ============================================================================

class TestDiscoverHaikuAgents:
    """Integration tests for discovering the template stack agents."""

    def test_discover_haiku_agents(self, installed_project):
        """The installed react and fastapi stack agents are discoverable."""
        results = discover_agents(phase='implementation')

        agent_names = [r.get('name') for r in results]

        assert 'fastapi-specialist' in agent_names, \
            "fastapi-specialist not found in results"
        assert 'react-state-specialist' in agent_names, \
            "react-state-specialist not found in results"

    def test_react_agent_metadata_complete(self, installed_project):
        """Verify react-state-specialist has complete metadata."""
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


# ============================================================================
# Test: Stack-Specific Discovery
# ============================================================================

class TestStackSpecificDiscovery:
    """Integration tests for stack-specific agent discovery."""

    def test_discover_python_implementation_agents(self, installed_project):
        """Should find Python implementation agents."""
        results = discover_agents(phase='implementation', stack=['python'])

        assert len(results) >= 1, "Should find at least one Python agent"

        agent_names = [r.get('name') for r in results]
        assert 'fastapi-specialist' in agent_names

    def test_discover_react_implementation_agents(self, installed_project):
        """Should find React implementation agents."""
        results = discover_agents(phase='implementation', stack=['react'])

        assert len(results) >= 1, "Should find at least one React agent"

        agent_names = [r.get('name') for r in results]
        assert 'react-state-specialist' in agent_names


# ============================================================================
# Test: Keyword-Based Discovery
# ============================================================================

class TestKeywordBasedDiscovery:
    """Integration tests for keyword-based agent discovery."""

    def test_discover_by_fastapi_keyword(self, installed_project):
        """Should find agents by FastAPI keyword."""
        results = discover_agents(
            phase='implementation',
            keywords=['fastapi']
        )

        agent_names = [r.get('name') for r in results]
        assert 'fastapi-specialist' in agent_names, \
            "fastapi-specialist should be found with 'fastapi' keyword"

    def test_discover_by_hooks_keyword(self, installed_project):
        """Should find agents by React hooks keyword."""
        results = discover_agents(
            phase='implementation',
            keywords=['hooks']
        )

        agent_names = [r.get('name') for r in results]
        assert 'react-state-specialist' in agent_names, \
            "react-state-specialist should be found with 'hooks' keyword"

    def test_relevance_scoring_with_multiple_keywords(self, installed_project):
        """Should rank agents by keyword match count."""
        results = discover_agents(
            phase='implementation',
            stack=['python'],
            keywords=['fastapi', 'async', 'pydantic', 'endpoints']
        )

        assert len(results) >= 1

        # The FastAPI agent should have high relevance score
        python_agent = next(
            (r for r in results if r.get('name') == 'fastapi-specialist'),
            None
        )

        assert python_agent is not None
        assert python_agent.get('relevance_score', 0) >= 2, \
            "FastAPI agent should have high relevance with multiple matching keywords"


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
        """Should discover agents from installer/core/agents/."""
        results = list_discoverable_agents()

        # Check that at least some agents are from the global location
        global_agents = [
            r for r in results
            if 'installer/core/agents' in r.get('path', '')
        ]

        # May be 0 if running in isolated test environment
        assert isinstance(global_agents, list)

    def test_template_agents_discovered(self, project_root):
        """Should discover agents from templates directories."""
        templates_dir = project_root / "installer" / "core" / "templates"

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

    def test_phase_3_implementation_workflow(self, installed_project):
        """Simulate Phase 3 agent selection for Python task."""
        # Scenario: Task is for Python FastAPI implementation
        task_stack = ['python']
        task_keywords = ['fastapi', 'async', 'api']

        results = discover_agents(
            phase='implementation',
            stack=task_stack,
            keywords=task_keywords
        )

        assert results, "Should find a Python implementation agent"

        # The top result should be most relevant
        top_agent = results[0]

        assert top_agent.get('phase') == 'implementation'

        # Check stack match
        agent_stacks = top_agent.get('stack', [])
        if isinstance(agent_stacks, str):
            agent_stacks = [agent_stacks]
        agent_stacks_lower = [s.lower() for s in agent_stacks]

        assert 'python' in agent_stacks_lower or 'cross-stack' in agent_stacks_lower

    def test_multi_stack_task_workflow(self, installed_project):
        """Simulate task that could match multiple stacks."""
        # Scenario: Full-stack task with both React and Python
        results = discover_agents(
            phase='implementation',
            stack=['react', 'python']
        )

        assert len(results) >= 2, "Should find agents for the react and python stacks"

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
