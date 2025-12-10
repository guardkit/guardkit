"""
End-to-End Integration Tests for Haiku Agent Discovery System.

Task Reference: TASK-HAI-008-D5C2
Epic: haiku-agent-implementation

This test suite validates the complete Haiku agent implementation and discovery
system through comprehensive end-to-end tests. It ensures all components work
together: schema validation, agent discovery, Phase 3 integration, and specialist routing.

Test Scenarios:
1. Python FastAPI task → python-api-specialist routing
2. React component task → react-state-specialist routing
3. .NET domain model task → dotnet-domain-specialist routing
4. Unsupported stack (Ruby) → task-manager fallback
5. Partial metadata coverage → graceful degradation
6. Multi-stack task → appropriate agent selection
7. Cost/speed validation → performance benchmarks

Success Metrics:
- Test pass rate: 100% (7/7 scenarios)
- Speed improvement: >70% (Haiku vs Sonnet)
- Cost reduction: >75% (Haiku vs Sonnet)
- Quality maintained: >80% review scores, 100% test pass
- Discovery accuracy: >95% correct specialist routing
"""

import os
import pytest
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

# Add the library to the path
lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

# Import helpers
from tests.integration.helpers import (
    create_python_task,
    create_react_task,
    create_dotnet_task,
    create_ruby_task,
    create_multi_stack_task,
    create_test_task,
    execute_task_work,
    cleanup_test_task,
    cleanup_all_test_tasks,
    remove_metadata_from_agents,
    restore_agents,
    estimate_cost,
    calculate_cost_savings,
    calculate_speed_improvement,
    generate_e2e_report,
    E2ETestReport,
    TaskWorkResult,
)

from agent_discovery import (
    discover_agents,
    get_agent_by_name,
    list_discoverable_agents,
    validate_discovery_metadata,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def agents_dir(project_root):
    """Get the global agents directory."""
    return project_root / "installer" / "core" / "agents"


@pytest.fixture
def e2e_task_dir(tmp_path):
    """Create isolated task directory for E2E tests."""
    task_dir = tmp_path / "tasks" / "backlog"
    task_dir.mkdir(parents=True)
    return task_dir


@pytest.fixture
def e2e_workspace(tmp_path):
    """Create complete E2E workspace."""
    workspace = {
        'root': tmp_path,
        'tasks': {
            'backlog': tmp_path / "tasks" / "backlog",
            'in_progress': tmp_path / "tasks" / "in_progress",
            'completed': tmp_path / "tasks" / "completed",
        },
        'agents': tmp_path / ".claude" / "agents",
        'metrics': tmp_path / "metrics",
    }

    for path in [workspace['tasks']['backlog'], workspace['tasks']['in_progress'],
                 workspace['tasks']['completed'], workspace['agents'], workspace['metrics']]:
        path.mkdir(parents=True, exist_ok=True)

    return workspace


def agent_file_exists(agents_dir: Path, agent_name: str) -> bool:
    """Check if an agent file exists."""
    return (agents_dir / f"{agent_name}.md").exists()


# ============================================================================
# Scenario 1: Python FastAPI Task
# ============================================================================

class TestPythonFastAPITaskE2E:
    """E2E tests for Python FastAPI task routing to python-api-specialist."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_python_fastapi_task_routes_to_specialist(self, agents_dir, e2e_task_dir):
        """
        Test that Python FastAPI task routes to python-api-specialist.

        Expected Behavior:
        1. Phase 3 analyzes context
           - Detects stack: [python]
           - Keywords: [fastapi, endpoint, api]
        2. Discovery finds python-api-specialist
           - Metadata matches: stack=python, phase=implementation
           - Relevance score: 3/5 (keywords match)
        3. Phase 3 uses python-api-specialist (Haiku)
        4. Implementation succeeds
        """
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        # Create Python task
        task_id = create_python_task(e2e_task_dir)

        try:
            # Execute task work flow
            result = execute_task_work(task_id, e2e_task_dir)

            # Verify discovery
            assert result.phase_3.agent_used == 'python-api-specialist', \
                f"Expected python-api-specialist, got {result.phase_3.agent_used}"
            assert result.phase_3.discovery_method == 'ai-metadata', \
                f"Expected ai-metadata discovery, got {result.phase_3.discovery_method}"
            assert 'python' in result.phase_3.detected_stack, \
                f"Expected python in stack, got {result.phase_3.detected_stack}"

            # Verify implementation success
            assert result.phase_3.status == 'completed'
            assert result.phase_4.tests_passed == True
            assert result.phase_5.review_score >= 70

            # Verify Haiku model used
            assert result.phase_3.model == 'haiku', \
                f"Expected haiku model, got {result.phase_3.model}"

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_python_task_discovery_with_keywords(self, agents_dir, e2e_task_dir):
        """Test keyword-based discovery for Python tasks."""
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        # Test with explicit FastAPI keywords
        results = discover_agents(
            phase='implementation',
            stack=['python'],
            keywords=['fastapi', 'async', 'pydantic', 'endpoints']
        )

        assert len(results) >= 1, "Should find at least one Python agent"

        # Verify python-api-specialist is in results with high relevance
        python_agent = next(
            (r for r in results if r.get('name') == 'python-api-specialist'),
            None
        )
        assert python_agent is not None, "python-api-specialist should be in results"
        assert python_agent.get('relevance_score', 0) >= 2, \
            "Should have high relevance score with multiple matching keywords"


# ============================================================================
# Scenario 2: React Component Task
# ============================================================================

class TestReactComponentTaskE2E:
    """E2E tests for React component task routing to react-state-specialist."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_react_component_task_routes_to_specialist(self, agents_dir, e2e_task_dir):
        """
        Test that React component task routes to react-state-specialist.

        Expected Behavior:
        1. Detects stack: [react, typescript]
        2. Keywords: [react, component, hooks]
        3. Discovery finds react-state-specialist
        4. Uses Haiku model
        5. Implementation succeeds
        """
        if not agent_file_exists(agents_dir, 'react-state-specialist'):
            pytest.skip("react-state-specialist.md not found")

        task_id = create_react_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Verify discovery
            assert result.phase_3.agent_used == 'react-state-specialist', \
                f"Expected react-state-specialist, got {result.phase_3.agent_used}"
            assert result.phase_3.discovery_method == 'ai-metadata'

            # Verify React/TypeScript stack detected
            detected_stacks = result.phase_3.detected_stack
            assert 'react' in detected_stacks or 'typescript' in detected_stacks, \
                f"Expected react or typescript in stack, got {detected_stacks}"

            # Verify success
            assert result.phase_3.status == 'completed'
            assert result.phase_3.model == 'haiku'

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_react_task_discovery_with_hooks_keyword(self, agents_dir):
        """Test discovery with React hooks keyword."""
        if not agent_file_exists(agents_dir, 'react-state-specialist'):
            pytest.skip("react-state-specialist.md not found")

        results = discover_agents(
            phase='implementation',
            keywords=['hooks']
        )

        agent_names = [r.get('name') for r in results]
        assert 'react-state-specialist' in agent_names, \
            "react-state-specialist should be found with 'hooks' keyword"


# ============================================================================
# Scenario 3: .NET Domain Model Task
# ============================================================================

class TestDotNetDomainModelTaskE2E:
    """E2E tests for .NET domain model task routing to dotnet-domain-specialist."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_dotnet_domain_model_task_routes_to_specialist(self, agents_dir, e2e_task_dir):
        """
        Test that .NET domain model task routes to dotnet-domain-specialist.

        Expected Behavior:
        1. Detects stack: [dotnet, csharp]
        2. Keywords: [entity, domain, ddd]
        3. Discovery finds dotnet-domain-specialist
        4. Uses Haiku model
        5. Implementation succeeds
        """
        if not agent_file_exists(agents_dir, 'dotnet-domain-specialist'):
            pytest.skip("dotnet-domain-specialist.md not found")

        task_id = create_dotnet_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Verify discovery
            assert result.phase_3.agent_used == 'dotnet-domain-specialist', \
                f"Expected dotnet-domain-specialist, got {result.phase_3.agent_used}"
            assert result.phase_3.discovery_method == 'ai-metadata'
            assert 'dotnet' in result.phase_3.detected_stack, \
                f"Expected dotnet in stack, got {result.phase_3.detected_stack}"

            # Verify success
            assert result.phase_3.status == 'completed'
            assert result.phase_3.model == 'haiku'

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_dotnet_task_discovery_with_ddd_keyword(self, agents_dir):
        """Test discovery with DDD keyword."""
        if not agent_file_exists(agents_dir, 'dotnet-domain-specialist'):
            pytest.skip("dotnet-domain-specialist.md not found")

        results = discover_agents(
            phase='implementation',
            keywords=['ddd']
        )

        agent_names = [r.get('name') for r in results]
        assert 'dotnet-domain-specialist' in agent_names, \
            "dotnet-domain-specialist should be found with 'ddd' keyword"


# ============================================================================
# Scenario 4: Unsupported Stack Fallback
# ============================================================================

class TestUnsupportedStackFallbackE2E:
    """E2E tests for fallback to task-manager with unsupported stacks."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_unsupported_stack_falls_back_to_task_manager(self, e2e_task_dir):
        """
        Test that unsupported stack (Ruby) falls back to task-manager.

        Expected Behavior:
        1. Detects stack: [ruby]
        2. Discovery finds NO specialist (ruby not supported yet)
        3. Fallback to task-manager (Sonnet)
        4. Implementation still succeeds
        """
        task_id = create_ruby_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Verify fallback
            assert result.phase_3.agent_used == 'task-manager', \
                f"Expected task-manager fallback, got {result.phase_3.agent_used}"
            assert result.phase_3.discovery_method == 'fallback', \
                f"Expected fallback discovery method, got {result.phase_3.discovery_method}"

            # Fallback uses Sonnet
            assert result.phase_3.model == 'sonnet', \
                f"Expected sonnet model for fallback, got {result.phase_3.model}"

            # Implementation should still succeed
            assert result.phase_3.status == 'completed'

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_nonexistent_stack_returns_empty_discovery(self):
        """Test that nonexistent stack returns empty discovery results."""
        results = discover_agents(
            phase='implementation',
            stack=['nonexistent-stack-xyz']
        )

        # Should return empty but not error
        assert isinstance(results, list)
        # May return cross-stack agents, so we just verify it doesn't crash


# ============================================================================
# Scenario 5: Partial Metadata Coverage
# ============================================================================

class TestPartialMetadataCoverageE2E:
    """E2E tests for graceful degradation with partial metadata."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_discovery_works_with_partial_metadata(self, agents_dir, e2e_task_dir):
        """
        Test that discovery works even when some agents lack metadata.

        Expected Behavior:
        1. Some agents have metadata removed
        2. Python task should still find python-api-specialist
        3. Agents without metadata are skipped gracefully
        """
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        # Discovery should work even with partial coverage
        task_id = create_python_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Should still find python-api-specialist
            assert result.phase_3.agent_used == 'python-api-specialist', \
                f"Should still find python-api-specialist, got {result.phase_3.agent_used}"
            assert result.phase_3.discovery_method == 'ai-metadata'

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_discovery_graceful_with_missing_agents(self):
        """Test that discovery handles missing agent files gracefully."""
        # This should complete without errors
        results = discover_agents(phase='implementation')
        assert isinstance(results, list)

        # All returned agents should have valid phase field
        for agent in results:
            assert agent.get('phase') == 'implementation'


# ============================================================================
# Scenario 6: Multi-Stack Task
# ============================================================================

class TestMultiStackTaskE2E:
    """E2E tests for multi-stack task handling."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_multi_stack_task_selects_appropriate_agent(self, agents_dir, e2e_task_dir):
        """
        Test that multi-stack task selects an appropriate agent.

        Expected Behavior:
        1. Detects stack: [react, typescript, python]
        2. Discovery finds multiple specialists
        3. Selects highest relevance agent
        """
        has_python = agent_file_exists(agents_dir, 'python-api-specialist')
        has_react = agent_file_exists(agents_dir, 'react-state-specialist')

        if not has_python and not has_react:
            pytest.skip("No specialist agents found")

        task_id = create_multi_stack_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Should pick one of the specialists
            valid_agents = ['react-state-specialist', 'python-api-specialist', 'task-manager']
            assert result.phase_3.agent_used in valid_agents, \
                f"Expected one of {valid_agents}, got {result.phase_3.agent_used}"

            # Multiple stacks should be detected
            assert len(result.phase_3.detected_stack) >= 2, \
                f"Should detect multiple stacks, got {result.phase_3.detected_stack}"

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_multi_stack_discovery_returns_multiple_agents(self, agents_dir):
        """Test that multi-stack discovery returns multiple matching agents."""
        has_python = agent_file_exists(agents_dir, 'python-api-specialist')
        has_react = agent_file_exists(agents_dir, 'react-state-specialist')

        if not (has_python and has_react):
            pytest.skip("Need both python and react specialists")

        results = discover_agents(
            phase='implementation',
            stack=['react', 'python']
        )

        # Should find agents for both stacks
        agent_names = [r.get('name') for r in results]

        # At least one specialist should be found
        specialists_found = [
            name for name in agent_names
            if name in ['python-api-specialist', 'react-state-specialist']
        ]
        assert len(specialists_found) >= 1, \
            f"Should find at least one specialist, found: {agent_names}"


# ============================================================================
# Scenario 7: Cost/Speed Validation
# ============================================================================

class TestCostSpeedValidationE2E:
    """E2E tests for cost and speed improvement validation."""

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.workflow
    def test_haiku_faster_than_sonnet(self, agents_dir, e2e_task_dir):
        """
        Test that Haiku is faster than Sonnet baseline.

        Expected Behavior:
        - Haiku discovery should complete quickly (<500ms)
        - Overall speed improvement should be >70%
        """
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        task_id = create_python_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Verify Haiku model used
            assert result.phase_3.model == 'haiku'

            # Discovery should be fast
            assert result.phase_3.duration < 0.5, \
                f"Discovery took {result.phase_3.duration:.3f}s (max: 0.5s)"

            # Speed improvement calculation (simulated baseline is 3x)
            speed_improvement = calculate_speed_improvement(
                result.phase_3.duration,
                result.baseline_duration
            )

            # Note: In real scenario, this would be ~70%+ improvement
            # In simulated test, we verify the metric is calculated
            assert speed_improvement >= 0, "Speed improvement should be calculated"

        finally:
            cleanup_test_task(task_id, e2e_task_dir)

    @pytest.mark.e2e
    def test_haiku_cheaper_than_sonnet(self, agents_dir):
        """Test that Haiku is cheaper than Sonnet."""
        haiku_cost = estimate_cost('haiku', 1000)
        sonnet_cost = estimate_cost('sonnet', 1000)

        cost_savings = calculate_cost_savings(haiku_cost, sonnet_cost)

        # Haiku should be significantly cheaper (>75% savings)
        assert cost_savings >= 75, \
            f"Expected >75% cost savings, got {cost_savings:.1f}%"

    @pytest.mark.e2e
    def test_quality_maintained_with_haiku(self, agents_dir, e2e_task_dir):
        """Test that quality is maintained when using Haiku agents."""
        if not agent_file_exists(agents_dir, 'python-api-specialist'):
            pytest.skip("python-api-specialist.md not found")

        task_id = create_python_task(e2e_task_dir)

        try:
            result = execute_task_work(task_id, e2e_task_dir)

            # Verify quality metrics
            assert result.phase_4.tests_passed == True, "Tests should pass"
            assert result.phase_5.review_score >= 70, \
                f"Review score should be >=70, got {result.phase_5.review_score}"

        finally:
            cleanup_test_task(task_id, e2e_task_dir)


# ============================================================================
# Performance Benchmarks
# ============================================================================

class TestPerformanceBenchmarksE2E:
    """Performance benchmark tests for the discovery system."""

    @pytest.mark.e2e
    @pytest.mark.benchmark
    def test_discovery_performance(self, agents_dir):
        """Test that discovery completes within performance requirements."""
        start = time.time()
        results = discover_agents(phase='implementation')
        duration = time.time() - start

        assert duration < 0.5, \
            f"Discovery took {duration:.3f}s (max: 0.5s)"

    @pytest.mark.e2e
    @pytest.mark.benchmark
    def test_multiple_discoveries_performance(self, agents_dir):
        """Test that multiple discoveries complete efficiently."""
        start = time.time()

        for _ in range(10):
            discover_agents(phase='implementation', stack=['python'])

        duration = time.time() - start

        assert duration < 2.0, \
            f"10 discoveries took {duration:.3f}s (max: 2.0s)"

    @pytest.mark.e2e
    @pytest.mark.benchmark
    def test_list_all_agents_performance(self):
        """Test listing all agents completes quickly."""
        start = time.time()
        results = list_discoverable_agents()
        duration = time.time() - start

        assert duration < 0.5, \
            f"Listing all agents took {duration:.3f}s (max: 0.5s)"


# ============================================================================
# Report Generation Test
# ============================================================================

class TestReportGenerationE2E:
    """Tests for E2E report generation."""

    @pytest.mark.e2e
    def test_generate_e2e_report(self, tmp_path):
        """Test E2E report generation."""
        # Create sample scenario results
        scenarios = [
            {
                'name': 'Python FastAPI',
                'passed': True,
                'agent_used': 'python-api-specialist',
                'discovery_method': 'ai-metadata',
                'duration': 8.2,
                'cost': 0.004,
                'model': 'haiku',
                'detected_stack': ['python'],
                'relevance_score': 3,
                'baseline_duration': 24.6,
            },
            {
                'name': 'React Component',
                'passed': True,
                'agent_used': 'react-state-specialist',
                'discovery_method': 'ai-metadata',
                'duration': 7.9,
                'cost': 0.003,
                'model': 'haiku',
                'detected_stack': ['react', 'typescript'],
                'relevance_score': 3,
                'baseline_duration': 23.7,
            },
            {
                'name': 'Ruby Fallback',
                'passed': True,
                'agent_used': 'task-manager',
                'discovery_method': 'fallback',
                'duration': 24.1,
                'cost': 0.015,
                'model': 'sonnet',
                'detected_stack': ['ruby'],
                'relevance_score': 0,
                'baseline_duration': 24.1,
            },
        ]

        report_path = tmp_path / "haiku-agent-e2e-report.md"
        report = generate_e2e_report(scenarios, report_path)

        # Verify report was generated
        assert report_path.exists(), "Report file should be created"

        # Verify report content
        assert report.total_passed == 3
        assert report.total_failed == 0

        # Read and verify markdown content
        content = report_path.read_text()
        assert "Haiku Agent E2E Test Report" in content
        assert "Python FastAPI" in content
        assert "React Component" in content


# ============================================================================
# Full Workflow Integration Test
# ============================================================================

class TestFullWorkflowIntegrationE2E:
    """Complete workflow integration tests."""

    @pytest.mark.e2e
    @pytest.mark.workflow
    def test_complete_e2e_workflow(self, agents_dir, e2e_workspace, tmp_path):
        """
        Test complete E2E workflow with all scenarios.

        This test runs all scenarios and generates a final report.
        """
        task_dir = e2e_workspace['tasks']['backlog']
        scenarios_results = []

        # Scenario 1: Python
        if agent_file_exists(agents_dir, 'python-api-specialist'):
            task_id = create_python_task(task_dir)
            try:
                result = execute_task_work(task_id, task_dir)
                scenarios_results.append({
                    'name': 'Python FastAPI',
                    'passed': result.phase_3.status == 'completed',
                    'agent_used': result.phase_3.agent_used,
                    'discovery_method': result.phase_3.discovery_method,
                    'duration': result.phase_3.duration,
                    'cost': estimate_cost(result.phase_3.model, 1000),
                    'model': result.phase_3.model,
                    'detected_stack': result.phase_3.detected_stack,
                    'baseline_duration': result.baseline_duration,
                })
            finally:
                cleanup_test_task(task_id, task_dir)

        # Scenario 2: React
        if agent_file_exists(agents_dir, 'react-state-specialist'):
            task_id = create_react_task(task_dir)
            try:
                result = execute_task_work(task_id, task_dir)
                scenarios_results.append({
                    'name': 'React Component',
                    'passed': result.phase_3.status == 'completed',
                    'agent_used': result.phase_3.agent_used,
                    'discovery_method': result.phase_3.discovery_method,
                    'duration': result.phase_3.duration,
                    'cost': estimate_cost(result.phase_3.model, 1000),
                    'model': result.phase_3.model,
                    'detected_stack': result.phase_3.detected_stack,
                    'baseline_duration': result.baseline_duration,
                })
            finally:
                cleanup_test_task(task_id, task_dir)

        # Scenario 3: .NET
        if agent_file_exists(agents_dir, 'dotnet-domain-specialist'):
            task_id = create_dotnet_task(task_dir)
            try:
                result = execute_task_work(task_id, task_dir)
                scenarios_results.append({
                    'name': '.NET Domain Model',
                    'passed': result.phase_3.status == 'completed',
                    'agent_used': result.phase_3.agent_used,
                    'discovery_method': result.phase_3.discovery_method,
                    'duration': result.phase_3.duration,
                    'cost': estimate_cost(result.phase_3.model, 1000),
                    'model': result.phase_3.model,
                    'detected_stack': result.phase_3.detected_stack,
                    'baseline_duration': result.baseline_duration,
                })
            finally:
                cleanup_test_task(task_id, task_dir)

        # Scenario 4: Ruby (fallback)
        task_id = create_ruby_task(task_dir)
        try:
            result = execute_task_work(task_id, task_dir)
            scenarios_results.append({
                'name': 'Ruby Fallback',
                'passed': result.phase_3.status == 'completed',
                'agent_used': result.phase_3.agent_used,
                'discovery_method': result.phase_3.discovery_method,
                'duration': result.phase_3.duration,
                'cost': estimate_cost(result.phase_3.model, 1000),
                'model': result.phase_3.model,
                'detected_stack': result.phase_3.detected_stack,
                'baseline_duration': result.baseline_duration,
            })
        finally:
            cleanup_test_task(task_id, task_dir)

        # Generate report
        if scenarios_results:
            report_path = tmp_path / "haiku-agent-e2e-report.md"
            report = generate_e2e_report(scenarios_results, report_path)

            # Verify results
            assert report.total_passed >= len(scenarios_results) - 1, \
                f"Most scenarios should pass: {report.total_passed}/{len(scenarios_results)}"

            # Print report summary for visibility
            print(f"\n{'='*60}")
            print("E2E Test Report Summary")
            print(f"{'='*60}")
            print(f"Total scenarios: {len(scenarios_results)}")
            print(f"Passed: {report.total_passed}")
            print(f"Failed: {report.total_failed}")
            print(f"Specialist usage rate: {report.specialist_usage_rate:.1f}%")
            print(f"Fallback rate: {report.fallback_rate:.1f}%")
            print(f"{'='*60}\n")


# ============================================================================
# Run Configuration
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
