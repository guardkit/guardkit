"""
End-to-End Integration Tests for Haiku Agent Discovery System.

Task Reference: TASK-HAI-008-D5C2
Epic: haiku-agent-implementation

This test suite validates the complete Haiku agent implementation and discovery
system through comprehensive end-to-end tests. It ensures all components work
together: schema validation, agent discovery, Phase 3 integration, and specialist routing.

Test Scenarios (the numbering of the original suite is kept):
4. Unsupported stack (Ruby) → task-manager fallback
5. Partial metadata coverage → graceful degradation
7. Cost validation

Scenarios 1-3 and 6 routed tasks to the global python-api-specialist,
react-state-specialist and dotnet-domain-specialist agents. Those global agents
were removed in a875bb73c (stack agents now ship with templates; see
tests/integration/lib/test_discovery_integration.py) and task-work's Phase 3
discovery routing was removed in 5d04b391c, so those tests were deleted.

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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

# Add the library to the path
lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
sys.path.insert(0, str(lib_path))

# Import helpers
from tests.integration.helpers import (
    create_ruby_task,
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


# Scenarios 1-3 and 6 (Python, React, .NET and multi-stack tasks routed to the
# global python-api-specialist, react-state-specialist and
# dotnet-domain-specialist) were deleted: those global agents were removed in
# a875bb73c (stack agents now ship with templates; discovery of the template
# agents is covered in tests/integration/lib/test_discovery_integration.py),
# and task-work's Phase 3 discovery routing (execute_phase_3 /
# analyze_task_context) was removed in 5d04b391c. The Haiku speed and quality
# checks for the python agent went for the same reasons.

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
    def test_discovery_graceful_with_missing_agents(self):
        """Test that discovery handles missing agent files gracefully."""
        # This should complete without errors
        results = discover_agents(phase='implementation')
        assert isinstance(results, list)

        # All returned agents should have valid phase field
        for agent in results:
            assert agent.get('phase') == 'implementation'


# ============================================================================
# Scenario 7: Cost/Speed Validation
# ============================================================================

class TestCostSpeedValidationE2E:
    """E2E tests for cost and speed improvement validation."""


    @pytest.mark.e2e
    def test_haiku_cheaper_than_sonnet(self, agents_dir):
        """Test that Haiku is cheaper than Sonnet."""
        haiku_cost = estimate_cost('haiku', 1000)
        sonnet_cost = estimate_cost('sonnet', 1000)

        cost_savings = calculate_cost_savings(haiku_cost, sonnet_cost)

        # Haiku should be significantly cheaper (>75% savings)
        assert cost_savings >= 75, \
            f"Expected >75% cost savings, got {cost_savings:.1f}%"



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
