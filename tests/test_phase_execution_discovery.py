"""
Unit Tests for Phase 3 Discovery Integration.

Task Reference: TASK-HAI-006-C391
Epic: haiku-agent-implementation

Tests cover:
- analyze_task_context() function
- execute_phase_3() with specialist selection
- Fallback to task-manager when no specialist found
- Edge cases (empty plans, missing files, etc.)
"""

import json
import os
import pytest
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Add lib to path
lib_path = Path(__file__).parent.parent / "installer" / "global" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

from phase_execution import (
    analyze_task_context,
    execute_phase_3,
    _fallback_phase_3_result,
)

# Patch targets for phase_execution module
# phase_execution.py does: from .agent_discovery import discover_agents as _discover_agents
# We need to patch both the function and the DISCOVERY_AVAILABLE flag
DISCOVER_AGENTS_PATCH = 'phase_execution._discover_agents'
DISCOVERY_AVAILABLE_PATCH = 'phase_execution.DISCOVERY_AVAILABLE'


@pytest.fixture
def mock_discovery_available():
    """Fixture to enable discovery in tests (patches DISCOVERY_AVAILABLE to True)."""
    with patch(DISCOVERY_AVAILABLE_PATCH, True):
        yield


# ============================================================================
# Test Fixtures
# ============================================================================

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
                'src/components/UserCard.tsx'
            ]
        }
    }


@pytest.fixture
def dotnet_plan():
    """Plan with .NET files."""
    return {
        'implementation_plan': {
            'files': [
                'src/Domain/Entities/User.cs',
                'src/Domain/ValueObjects/Email.cs',
                'src/Infrastructure/Repositories/UserRepository.cs'
            ]
        }
    }


@pytest.fixture
def mixed_plan():
    """Plan with mixed file types."""
    return {
        'implementation_plan': {
            'files': [
                'src/api/users.py',
                'frontend/UserList.tsx',
                'docs/README.md'
            ]
        }
    }


@pytest.fixture
def empty_plan():
    """Empty plan with no files."""
    return {}


@pytest.fixture
def ruby_plan():
    """Plan with Ruby files (no specialist available)."""
    return {
        'implementation_plan': {
            'files': [
                'app/controllers/users_controller.rb',
                'app/models/user.rb'
            ]
        }
    }


@pytest.fixture
def fastapi_task_context():
    """Task context with FastAPI keywords."""
    return {
        'title': 'Add FastAPI endpoint for user registration',
        'description': 'Implement REST API endpoint with async handlers and Pydantic validation'
    }


@pytest.fixture
def react_task_context():
    """Task context with React keywords."""
    return {
        'title': 'Create user list component',
        'description': 'Build React component with hooks for state management'
    }


@pytest.fixture
def domain_task_context():
    """Task context with DDD keywords."""
    return {
        'title': 'Implement Order aggregate',
        'description': 'Create domain entity with value objects following DDD patterns'
    }


# ============================================================================
# Test: analyze_task_context() - File Extension Detection
# ============================================================================

class TestAnalyzeTaskContextFileExtensions:
    """Tests for file extension-based stack detection."""

    def test_detects_python_from_py_files(self, python_plan):
        """Should detect Python stack from .py files."""
        context = analyze_task_context('TASK-001', python_plan)

        assert 'python' in context['stack']

    def test_detects_react_from_tsx_files(self, react_plan):
        """Should detect React from .tsx files."""
        context = analyze_task_context('TASK-002', react_plan)

        assert 'react' in context['stack']
        assert 'typescript' in context['stack']

    def test_detects_dotnet_from_cs_files(self, dotnet_plan):
        """Should detect .NET from .cs files."""
        context = analyze_task_context('TASK-003', dotnet_plan)

        assert 'dotnet' in context['stack']
        assert 'csharp' in context['stack']

    def test_detects_mixed_stacks(self, mixed_plan):
        """Should detect multiple stacks from mixed files."""
        context = analyze_task_context('TASK-004', mixed_plan)

        assert 'python' in context['stack']
        assert 'react' in context['stack']

    def test_handles_empty_plan(self, empty_plan):
        """Should handle empty plan gracefully."""
        context = analyze_task_context('TASK-005', empty_plan)

        assert context['stack'] == [] or isinstance(context['stack'], list)
        assert context['keywords'] == [] or isinstance(context['keywords'], list)

    def test_detects_ruby_stack(self, ruby_plan):
        """Should detect Ruby from .rb files."""
        context = analyze_task_context('TASK-006', ruby_plan)

        assert 'ruby' in context['stack']

    def test_alternative_plan_structures(self):
        """Should handle alternative plan structures."""
        # files key directly
        plan1 = {'files': ['src/api.py']}
        context1 = analyze_task_context('TASK-007', plan1)
        assert 'python' in context1['stack']

        # files_to_create key
        plan2 = {'files_to_create': ['src/app.ts']}
        context2 = analyze_task_context('TASK-008', plan2)
        assert 'typescript' in context2['stack']


# ============================================================================
# Test: analyze_task_context() - Keyword Extraction
# ============================================================================

class TestAnalyzeTaskContextKeywords:
    """Tests for keyword extraction from task context."""

    def test_extracts_fastapi_keywords(self, python_plan, fastapi_task_context):
        """Should extract FastAPI-related keywords."""
        context = analyze_task_context('TASK-001', python_plan, fastapi_task_context)

        assert 'fastapi' in context['keywords']
        assert 'api' in context['keywords']

    def test_extracts_react_keywords(self, react_plan, react_task_context):
        """Should extract React-related keywords."""
        context = analyze_task_context('TASK-002', react_plan, react_task_context)

        assert 'react' in context['keywords']
        assert 'hooks' in context['keywords'] or 'state' in context['keywords']

    def test_extracts_domain_keywords(self, dotnet_plan, domain_task_context):
        """Should extract DDD-related keywords."""
        context = analyze_task_context('TASK-003', dotnet_plan, domain_task_context)

        assert 'domain' in context['keywords']

    def test_handles_no_task_context(self, python_plan):
        """Should handle missing task context."""
        context = analyze_task_context('TASK-004', python_plan, None)

        assert isinstance(context['keywords'], list)

    def test_keywords_are_case_insensitive(self, empty_plan):
        """Should detect keywords regardless of case."""
        task = {
            'title': 'FASTAPI Endpoint',
            'description': 'Using REACT hooks'
        }
        context = analyze_task_context('TASK-005', empty_plan, task)

        assert 'fastapi' in context['keywords']
        assert 'react' in context['keywords']


# ============================================================================
# Test: analyze_task_context() - Project Structure Detection
# ============================================================================

class TestAnalyzeTaskContextProjectStructure:
    """Tests for project structure detection."""

    def test_detects_package_json_react(self, empty_plan):
        """Should detect React from package.json."""
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp()
        try:
            os.chdir(tmpdir)
            pkg = {'dependencies': {'react': '^18.0.0', 'typescript': '^5.0.0'}}
            with open('package.json', 'w') as f:
                json.dump(pkg, f)

            context = analyze_task_context('TASK-001', empty_plan)

            assert 'react' in context['stack']
            assert 'typescript' in context['stack']
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_detects_requirements_txt_fastapi(self, empty_plan):
        """Should detect FastAPI from requirements.txt."""
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp()
        try:
            os.chdir(tmpdir)
            with open('requirements.txt', 'w') as f:
                f.write('fastapi==0.100.0\nuvicorn==0.23.0\n')

            context = analyze_task_context('TASK-002', empty_plan)

            assert 'python' in context['stack']
            assert 'fastapi' in context['keywords']
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_detects_pyproject_toml(self, empty_plan):
        """Should detect Python from pyproject.toml."""
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp()
        try:
            os.chdir(tmpdir)
            with open('pyproject.toml', 'w') as f:
                f.write('[project]\nname = "test"\n')

            context = analyze_task_context('TASK-003', empty_plan)

            assert 'python' in context['stack']
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_handles_missing_project_files(self, python_plan):
        """Should work when project files don't exist."""
        original_cwd = os.getcwd()
        tmpdir = tempfile.mkdtemp()
        try:
            os.chdir(tmpdir)
            # No project files present

            context = analyze_task_context('TASK-004', python_plan)

            # Should still detect from plan files
            assert 'python' in context['stack']
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================================
# Test: execute_phase_3() - Specialist Selection
# ============================================================================

class TestExecutePhase3SpecialistSelection:
    """Tests for Phase 3 specialist agent selection."""

    def test_selects_python_specialist(self, python_plan, fastapi_task_context):
        """Should select python-api-specialist for Python tasks."""
        mock_specialists = [{
            'name': 'python-api-specialist',
            'stack': ['python'],
            'phase': 'implementation',
            'relevance_score': 5,
            'capabilities': ['FastAPI endpoints', 'Async handlers', 'Pydantic'],
            'model': 'haiku',
            'path': '/path/to/agent.md'
        }]

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-001', python_plan, fastapi_task_context)

        assert result['agent_used'] == 'python-api-specialist'
        assert result['discovery_method'] == 'ai-metadata'
        assert result['relevance_score'] == 5

    def test_selects_react_specialist(self, react_plan, react_task_context):
        """Should select react-state-specialist for React tasks."""
        mock_specialists = [{
            'name': 'react-state-specialist',
            'stack': ['react', 'typescript'],
            'phase': 'implementation',
            'relevance_score': 4,
            'capabilities': ['React hooks', 'State management', 'TanStack Query'],
            'model': 'haiku',
            'path': '/path/to/agent.md'
        }]

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-002', react_plan, react_task_context)

        assert result['agent_used'] == 'react-state-specialist'
        assert result['discovery_method'] == 'ai-metadata'

    def test_selects_dotnet_specialist(self, dotnet_plan, domain_task_context):
        """Should select dotnet-domain-specialist for .NET tasks."""
        mock_specialists = [{
            'name': 'dotnet-domain-specialist',
            'stack': ['dotnet', 'csharp'],
            'phase': 'implementation',
            'relevance_score': 6,
            'capabilities': ['Entity design', 'Value objects', 'DDD patterns'],
            'model': 'haiku',
            'path': '/path/to/agent.md'
        }]

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-003', dotnet_plan, domain_task_context)

        assert result['agent_used'] == 'dotnet-domain-specialist'
        assert result['discovery_method'] == 'ai-metadata'

    def test_fallback_to_task_manager(self, ruby_plan):
        """Should fallback to task-manager when no specialist found."""
        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=[]):
                result = execute_phase_3('TASK-004', ruby_plan)

        assert result['agent_used'] == 'task-manager'
        assert result['discovery_method'] == 'fallback'
        assert result['specialists_found'] == 0

    def test_selects_highest_relevance(self, python_plan):
        """Should select specialist with highest relevance score."""
        mock_specialists = [
            {'name': 'high-relevance', 'relevance_score': 10, 'capabilities': ['a'], 'model': 'haiku', 'path': '/a.md'},
            {'name': 'low-relevance', 'relevance_score': 2, 'capabilities': ['b'], 'model': 'haiku', 'path': '/b.md'},
        ]

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-005', python_plan)

        # First in list is highest relevance (pre-sorted by discover_agents)
        assert result['agent_used'] == 'high-relevance'

    def test_includes_context_in_result(self, python_plan, fastapi_task_context):
        """Should include detected context in result."""
        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=[]):
                result = execute_phase_3('TASK-006', python_plan, fastapi_task_context)

        assert 'context_detected' in result
        assert 'stack' in result['context_detected']
        assert 'keywords' in result['context_detected']


# ============================================================================
# Test: execute_phase_3() - Error Handling
# ============================================================================

class TestExecutePhase3ErrorHandling:
    """Tests for Phase 3 error handling."""

    def test_handles_discovery_import_error(self, python_plan):
        """Should fallback when discovery module unavailable."""
        # Test the fallback function directly (it's used when import fails)
        result = _fallback_phase_3_result('TASK-001')

        assert result['agent_used'] == 'task-manager'
        assert result['discovery_method'] == 'fallback'
        assert 'note' in result

    def test_handles_discovery_exception(self, python_plan):
        """Should fallback when discovery throws exception."""
        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, side_effect=Exception("Discovery error")):
                result = execute_phase_3('TASK-002', python_plan)

        assert result['agent_used'] == 'task-manager'
        assert result['discovery_method'] == 'fallback'

    def test_handles_malformed_specialist_data(self, python_plan):
        """Should handle specialists with missing fields."""
        mock_specialists = [{'name': 'incomplete-agent'}]  # Missing many fields

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-003', python_plan)

        assert result['success'] is True
        # Should still select the agent, using defaults for missing fields

    def test_handles_empty_agent_list(self, empty_plan):
        """Should handle empty specialist list."""
        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=[]):
                result = execute_phase_3('TASK-004', empty_plan)

        assert result['agent_used'] == 'task-manager'
        assert result['discovery_method'] == 'fallback'


# ============================================================================
# Test: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_deduplicates_stacks(self):
        """Should deduplicate detected stacks."""
        plan = {
            'implementation_plan': {
                'files': ['a.py', 'b.py', 'c.py', 'd.py']  # Multiple Python files
            }
        }
        context = analyze_task_context('TASK-001', plan)

        # Should only have one 'python' entry
        assert context['stack'].count('python') == 1

    def test_deduplicates_keywords(self):
        """Should deduplicate detected keywords."""
        plan = {'implementation_plan': {'files': ['api.py']}}
        task = {
            'title': 'API endpoint API handler',
            'description': 'REST API with API clients'
        }
        context = analyze_task_context('TASK-002', plan, task)

        # Should only have one 'api' entry
        assert context['keywords'].count('api') == 1

    def test_handles_non_string_files(self):
        """Should handle non-string file entries."""
        plan = {
            'implementation_plan': {
                'files': ['valid.py', None, 123, {'path': 'ignored.ts'}]
            }
        }
        context = analyze_task_context('TASK-003', plan)

        # Should only detect from valid string file
        assert 'python' in context['stack']

    def test_preserves_order(self):
        """Should preserve order of detected items."""
        plan = {
            'implementation_plan': {
                'files': ['first.py', 'second.tsx', 'third.cs']
            }
        }
        context = analyze_task_context('TASK-004', plan)

        # Python should come before React (based on file order)
        if 'python' in context['stack'] and 'react' in context['stack']:
            python_idx = context['stack'].index('python')
            react_idx = context['stack'].index('react')
            assert python_idx < react_idx


# ============================================================================
# Test: Result Structure
# ============================================================================

class TestResultStructure:
    """Tests for result structure compliance."""

    def test_specialist_result_has_required_fields(self, python_plan):
        """Specialist result should have all required fields."""
        mock_specialists = [{
            'name': 'test-specialist',
            'stack': ['python'],
            'phase': 'implementation',
            'relevance_score': 5,
            'capabilities': ['Test'],
            'model': 'haiku',
            'path': '/path/to/agent.md'
        }]

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-001', python_plan)

        assert 'success' in result
        assert 'agent_used' in result
        assert 'agent_path' in result
        assert 'discovery_method' in result
        assert 'context_detected' in result
        assert 'specialists_found' in result
        assert 'relevance_score' in result

    def test_fallback_result_has_required_fields(self, ruby_plan):
        """Fallback result should have all required fields."""
        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=[]):
                result = execute_phase_3('TASK-002', ruby_plan)

        assert 'success' in result
        assert 'agent_used' in result
        assert 'agent_path' in result
        assert 'discovery_method' in result
        assert 'context_detected' in result
        assert 'specialists_found' in result
        assert 'relevance_score' in result

    def test_result_includes_model_info(self, python_plan):
        """Result should include model information."""
        mock_specialists = [{
            'name': 'test-specialist',
            'model': 'haiku',
            'capabilities': ['Test'],
            'path': '/path/to/agent.md'
        }]

        with patch(DISCOVERY_AVAILABLE_PATCH, True):
            with patch(DISCOVER_AGENTS_PATCH, return_value=mock_specialists):
                result = execute_phase_3('TASK-003', python_plan)

        assert 'agent_model' in result
        assert result['agent_model'] == 'haiku'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
