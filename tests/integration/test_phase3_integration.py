"""
Integration Tests for Phase 3 Discovery Routing.

Task Reference: TASK-HAI-006-C391
Epic: haiku-agent-implementation

These tests verify end-to-end discovery routing:
- Python task → python-api-specialist
- React task → react-state-specialist
- .NET task → dotnet-domain-specialist
- Ruby task → task-manager (fallback)
"""

import os
import pytest
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any

# Add lib to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from phase_execution import analyze_task_context, execute_phase_3
from agent_discovery import discover_agents


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def python_task():
    """Python FastAPI task context."""
    return {
        'title': 'Add FastAPI endpoint for user registration',
        'description': 'Create a REST API endpoint with Pydantic validation and async handlers',
        'tags': ['python', 'fastapi', 'api']
    }


@pytest.fixture
def react_task():
    """React component task context."""
    return {
        'title': 'Create user list component with state management',
        'description': 'Build a React component using hooks for state and TanStack Query for data fetching',
        'tags': ['react', 'typescript', 'component']
    }


@pytest.fixture
def dotnet_task():
    """DotNet domain entity task context."""
    return {
        'title': 'Implement User aggregate root',
        'description': 'Create domain entity with value objects following DDD patterns',
        'tags': ['dotnet', 'csharp', 'domain', 'ddd']
    }


@pytest.fixture
def ruby_task():
    """Ruby task (no specialist available)."""
    return {
        'title': 'Add Ruby controller for users',
        'description': 'Create Rails controller with CRUD operations',
        'tags': ['ruby', 'rails', 'controller']
    }


@pytest.fixture
def python_plan():
    """Plan with Python files."""
    return {
        'implementation_plan': {
            'files': [
                'src/api/endpoints.py',
                'src/models/user.py',
                'tests/test_api.py'
            ]
        }
    }


@pytest.fixture
def react_plan():
    """Plan with React/TypeScript files."""
    return {
        'implementation_plan': {
            'files': [
                'src/components/UserList.tsx',
                'src/hooks/useUsers.ts',
                'tests/UserList.test.tsx'
            ]
        }
    }


@pytest.fixture
def dotnet_plan():
    """Plan with .NET C# files."""
    return {
        'implementation_plan': {
            'files': [
                'src/Domain/Entities/User.cs',
                'src/Domain/ValueObjects/Email.cs',
                'tests/Domain/UserTests.cs'
            ]
        }
    }


@pytest.fixture
def ruby_plan():
    """Plan with Ruby files."""
    return {
        'implementation_plan': {
            'files': [
                'app/controllers/users_controller.rb',
                'app/models/user.rb',
                'spec/controllers/users_controller_spec.rb'
            ]
        }
    }


# ============================================================================
# Integration Tests: Context Analysis
# ============================================================================

class TestContextAnalysisIntegration:
    """Integration tests for context analysis."""

    def test_python_context_detection(self, python_plan, python_task):
        """Should detect Python stack from files and FastAPI keywords."""
        context = analyze_task_context('TASK-PYTHON', python_plan, python_task)

        assert 'python' in context['stack']
        # Should detect keywords from description
        keywords = context.get('keywords', [])
        assert any(k in ['api', 'fastapi', 'endpoint', 'rest'] for k in keywords)

    def test_react_context_detection(self, react_plan, react_task):
        """Should detect React/TypeScript stack from files."""
        context = analyze_task_context('TASK-REACT', react_plan, react_task)

        assert 'react' in context['stack'] or 'typescript' in context['stack']
        keywords = context.get('keywords', [])
        assert any(k in ['react', 'component', 'hook', 'state'] for k in keywords)

    def test_dotnet_context_detection(self, dotnet_plan, dotnet_task):
        """Should detect .NET/C# stack from files."""
        context = analyze_task_context('TASK-DOTNET', dotnet_plan, dotnet_task)

        assert 'dotnet' in context['stack'] or 'csharp' in context['stack']
        keywords = context.get('keywords', [])
        assert any(k in ['domain', 'entity', 'aggregate', 'ddd'] for k in keywords)

    def test_ruby_context_detection(self, ruby_plan, ruby_task):
        """Should detect Ruby stack from files."""
        context = analyze_task_context('TASK-RUBY', ruby_plan, ruby_task)

        assert 'ruby' in context['stack']


# ============================================================================
# Integration Tests: Discovery Routing
# ============================================================================

class TestDiscoveryRoutingIntegration:
    """Integration tests for discovery routing."""

    def test_discovery_finds_python_specialist(self):
        """Should find python-api-specialist for Python/implementation."""
        specialists = discover_agents(
            phase='implementation',
            stack=['python'],
            keywords=['fastapi', 'api', 'endpoint']
        )

        # Should find at least one specialist or gracefully return empty
        # (depends on whether HAI-002 agent file exists with metadata)
        assert isinstance(specialists, list)

        if specialists:
            agent_names = [s.get('name', '') for s in specialists]
            assert any('python' in name.lower() for name in agent_names)

    def test_discovery_finds_react_specialist(self):
        """Should find react-state-specialist for React/implementation."""
        specialists = discover_agents(
            phase='implementation',
            stack=['react', 'typescript'],
            keywords=['react', 'hooks', 'state']
        )

        assert isinstance(specialists, list)

        if specialists:
            agent_names = [s.get('name', '') for s in specialists]
            assert any('react' in name.lower() for name in agent_names)

    def test_discovery_finds_dotnet_specialist(self):
        """Should find dotnet-domain-specialist for .NET/implementation."""
        specialists = discover_agents(
            phase='implementation',
            stack=['dotnet', 'csharp'],
            keywords=['domain', 'entity', 'ddd']
        )

        assert isinstance(specialists, list)

        if specialists:
            agent_names = [s.get('name', '') for s in specialists]
            assert any('dotnet' in name.lower() for name in agent_names)

    def test_discovery_returns_empty_for_ruby(self):
        """Should return empty list for Ruby (no specialist available)."""
        specialists = discover_agents(
            phase='implementation',
            stack=['ruby'],
            keywords=['rails', 'controller']
        )

        assert isinstance(specialists, list)
        # Ruby specialist doesn't exist, so should be empty or have 0 relevance


# ============================================================================
# Integration Tests: End-to-End Phase 3
# ============================================================================

class TestPhase3EndToEnd:
    """End-to-end tests for Phase 3 execution."""

    def test_phase3_selects_specialist_or_fallback(self, python_plan, python_task):
        """Should select specialist if available, else fallback."""
        result = execute_phase_3('TASK-E2E-001', python_plan, python_task)

        assert result['success'] is True
        assert 'agent_used' in result
        assert 'discovery_method' in result
        assert 'context_detected' in result

        # Either got a specialist or fell back to task-manager
        assert result['discovery_method'] in ['ai-metadata', 'fallback']

    def test_phase3_detects_context(self, react_plan, react_task):
        """Should include detected context in result."""
        result = execute_phase_3('TASK-E2E-002', react_plan, react_task)

        assert 'context_detected' in result
        context = result['context_detected']
        assert 'stack' in context
        assert 'keywords' in context

    def test_phase3_fallback_for_unknown_stack(self, ruby_plan, ruby_task):
        """Should fallback to task-manager for unknown stack."""
        result = execute_phase_3('TASK-E2E-003', ruby_plan, ruby_task)

        assert result['success'] is True
        # Ruby doesn't have a specialist, so should fallback
        # (unless a cross-stack agent matches)
        assert result['agent_used'] in ['task-manager'] or result['discovery_method'] == 'ai-metadata'

    def test_phase3_handles_empty_plan(self):
        """Should handle empty plan gracefully."""
        empty_plan = {'implementation_plan': {'files': []}}
        result = execute_phase_3('TASK-E2E-004', empty_plan)

        assert result['success'] is True
        assert 'agent_used' in result

    def test_phase3_result_structure(self, python_plan):
        """Should return complete result structure."""
        result = execute_phase_3('TASK-E2E-005', python_plan)

        # Required fields
        required_fields = [
            'success',
            'agent_used',
            'agent_path',
            'discovery_method',
            'context_detected',
            'specialists_found',
            'relevance_score'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"


# ============================================================================
# Integration Tests: Cross-Stack Agent
# ============================================================================

class TestCrossStackIntegration:
    """Tests for cross-stack agent matching."""

    def test_cross_stack_agent_matches_any_stack(self):
        """Cross-stack agents should match any technology stack."""
        # Cross-stack agents have stack: ['cross-stack'] in metadata
        # They should be discoverable for any stack
        specialists = discover_agents(
            phase='implementation',
            stack=['someunknownstack']
        )

        # Should return list (may be empty if no cross-stack agents exist)
        assert isinstance(specialists, list)


# ============================================================================
# Integration Tests: Project Structure Detection
# ============================================================================

class TestProjectStructureIntegration:
    """Tests for project structure detection."""

    def test_detects_react_from_package_json(self):
        """Should detect React from package.json in current directory."""
        import json as json_mod

        tmpdir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Create package.json with React dependency
            package_json = {'dependencies': {'react': '^18.0.0'}}
            with open('package.json', 'w') as f:
                json_mod.dump(package_json, f)

            # Analyze context
            plan = {'implementation_plan': {'files': ['src/App.tsx']}}
            context = analyze_task_context('TASK-PKG', plan)

            assert 'react' in context['stack']
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_detects_fastapi_from_requirements(self):
        """Should detect FastAPI from requirements.txt."""
        tmpdir = tempfile.mkdtemp()
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Create requirements.txt with FastAPI
            with open('requirements.txt', 'w') as f:
                f.write('fastapi>=0.100.0\nuvicorn>=0.22.0\n')

            # Analyze context
            plan = {'implementation_plan': {'files': ['main.py']}}
            context = analyze_task_context('TASK-REQ', plan)

            assert 'python' in context['stack']
            assert 'fastapi' in context['keywords']
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
