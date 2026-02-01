"""
Comprehensive validation tests for TASK-GR5-010: Update GR-005 documentation.

Validates that all acceptance criteria are met:
1. CLI usage in CLAUDE.md
2. All query commands documented with examples
3. Turn state capture behavior documented
4. Troubleshooting for query issues
5. FEAT-GR-005 marked as implemented
"""

import re
from pathlib import Path

import pytest


@pytest.fixture
def claude_md_path():
    """Path to root CLAUDE.md file."""
    return Path(__file__).parent.parent.parent / "CLAUDE.md"


@pytest.fixture
def feat_gr005_path():
    """Path to FEAT-GR-005 specification."""
    return (
        Path(__file__).parent.parent.parent
        / "docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md"
    )


@pytest.fixture
def claude_md_content(claude_md_path):
    """Content of CLAUDE.md."""
    return claude_md_path.read_text()


@pytest.fixture
def feat_gr005_content(feat_gr005_path):
    """Content of FEAT-GR-005."""
    return feat_gr005_path.read_text()


class TestAcceptanceCriteria:
    """Test all acceptance criteria for TASK-GR5-010."""

    def test_ac001_cli_usage_in_claude_md(self, claude_md_content):
        """AC-001: CLI usage documented in CLAUDE.md."""
        # Should have the "Knowledge Query Commands" section
        assert "### Knowledge Query Commands" in claude_md_content

        # Should document all four CLI commands
        assert "guardkit graphiti show" in claude_md_content
        assert "guardkit graphiti search" in claude_md_content
        assert "guardkit graphiti list" in claude_md_content
        assert "guardkit graphiti status" in claude_md_content

    def test_ac002_all_query_commands_documented_with_examples(self, claude_md_content):
        """AC-002: All query commands documented with examples."""
        # show command
        assert "guardkit graphiti show FEAT-SKEL-001" in claude_md_content
        assert "guardkit graphiti show ADR-001" in claude_md_content

        # search command
        assert 'guardkit graphiti search "authentication patterns"' in claude_md_content
        assert 'guardkit graphiti search "error handling" --group patterns' in claude_md_content

        # list command
        assert "guardkit graphiti list features" in claude_md_content
        assert "guardkit graphiti list adrs" in claude_md_content
        assert "guardkit graphiti list patterns" in claude_md_content

        # status command
        assert "guardkit graphiti status" in claude_md_content
        assert "guardkit graphiti status --verbose" in claude_md_content

    def test_ac003_turn_state_capture_documented(self, claude_md_content):
        """AC-003: Turn state capture behavior documented."""
        # Should have turn state tracking section
        assert "### Turn State Tracking (AutoBuild)" in claude_md_content

        # Should document what gets captured
        assert "Player decisions and actions" in claude_md_content
        assert "Coach feedback and approval status" in claude_md_content
        assert "Files modified during turn" in claude_md_content
        assert "Acceptance criteria status" in claude_md_content

        # Should document querying turn states
        assert 'guardkit graphiti search "turn FEAT-XXX" --group turn_states' in claude_md_content
        assert 'guardkit graphiti search "turn TASK-XXX" --group turn_states' in claude_md_content

        # Should document turn state schema
        assert "Turn State Schema:" in claude_md_content
        assert "feature_id" in claude_md_content
        assert "task_id" in claude_md_content
        assert "turn_number" in claude_md_content
        assert "player_decision" in claude_md_content
        assert "coach_decision" in claude_md_content

    def test_ac004_troubleshooting_for_query_issues(self, claude_md_content):
        """AC-004: Troubleshooting guide for query issues."""
        # Should have troubleshooting section
        assert "### Troubleshooting Graphiti" in claude_md_content

        # Should document common issues
        assert "Command not found" in claude_md_content
        assert "Connection errors" in claude_md_content
        assert "No results from queries" in claude_md_content
        assert "Empty turn states" in claude_md_content
        assert "Slow queries" in claude_md_content
        assert "Stale knowledge" in claude_md_content

        # Should provide actionable solutions
        assert "guardkit graphiti status" in claude_md_content
        assert "guardkit graphiti seed" in claude_md_content
        assert "docker ps | grep neo4j" in claude_md_content

    def test_ac005_feat_gr005_marked_as_implemented(self, feat_gr005_content):
        """AC-005: FEAT-GR-005 marked as implemented."""
        # Should have IMPLEMENTED status
        assert "**Status**: ✅ **IMPLEMENTED**" in feat_gr005_content

        # Should have implementation date
        assert "**Implementation Date**: 2026-02-01" in feat_gr005_content

        # Should have implementation notes section
        assert "## Implementation Notes" in feat_gr005_content

        # Should document completed tasks
        assert "TASK-GR5-001" in feat_gr005_content
        assert "TASK-GR5-002" in feat_gr005_content
        assert "TASK-GR5-003" in feat_gr005_content
        assert "TASK-GR5-004" in feat_gr005_content
        assert "TASK-GR5-005" in feat_gr005_content
        assert "TASK-GR5-006" in feat_gr005_content
        assert "TASK-GR5-007" in feat_gr005_content
        assert "TASK-GR5-008" in feat_gr005_content
        assert "TASK-GR5-009" in feat_gr005_content
        assert "TASK-GR5-010" in feat_gr005_content


class TestCommandDetails:
    """Test detailed command documentation."""

    def test_show_command_documented(self, claude_md_content):
        """Test show command documentation."""
        # Should describe functionality
        assert "Display detailed information about specific knowledge" in claude_md_content
        assert "Auto-detects knowledge type from ID" in claude_md_content

        # Should have example
        assert "guardkit graphiti show FEAT-GR-005" in claude_md_content

    def test_search_command_documented(self, claude_md_content):
        """Test search command documentation."""
        # Should describe functionality
        assert "Search across all knowledge" in claude_md_content
        assert "Full-text search with relevance scoring" in claude_md_content

        # Should document options
        assert "--group" in claude_md_content
        assert "--limit" in claude_md_content

        # Should describe color coding
        assert "green >0.8" in claude_md_content
        assert "yellow >0.5" in claude_md_content

    def test_list_command_documented(self, claude_md_content):
        """Test list command documentation."""
        # Should describe functionality
        assert "List all items in a category" in claude_md_content

        # Should document categories
        assert "features" in claude_md_content
        assert "adrs" in claude_md_content
        assert "patterns" in claude_md_content
        assert "constraints" in claude_md_content

    def test_status_command_documented(self, claude_md_content):
        """Test status command documentation."""
        # Should describe functionality
        assert "Show knowledge graph health and statistics" in claude_md_content
        assert "Connection status" in claude_md_content
        assert "Episode counts by category" in claude_md_content

        # Should document verbose option
        assert "--verbose" in claude_md_content


class TestKnowledgeGroups:
    """Test knowledge group documentation."""

    def test_knowledge_groups_documented(self, claude_md_content):
        """Test that all knowledge groups are documented."""
        # Should have knowledge groups section
        assert "**Knowledge Groups:**" in claude_md_content

        # Should document all groups
        assert "System Knowledge" in claude_md_content
        assert "product_knowledge" in claude_md_content
        assert "command_workflows" in claude_md_content
        assert "patterns" in claude_md_content
        assert "agents" in claude_md_content

        assert "Project Knowledge" in claude_md_content
        assert "project_overview" in claude_md_content
        assert "project_architecture" in claude_md_content
        assert "feature_specs" in claude_md_content

        assert "Decisions" in claude_md_content
        assert "project_decisions" in claude_md_content
        assert "architecture_decisions" in claude_md_content

        assert "Learning" in claude_md_content
        assert "task_outcomes" in claude_md_content
        assert "failure_patterns" in claude_md_content
        assert "successful_fixes" in claude_md_content

        assert "Turn States" in claude_md_content
        assert "turn_states" in claude_md_content


class TestTurnStateDocumentation:
    """Test turn state tracking documentation."""

    def test_turn_state_benefits_documented(self, claude_md_content):
        """Test that turn state benefits are documented."""
        # Should document cross-turn learning
        assert "Turn N+1 knows what Turn N learned" in claude_md_content
        assert "Prevents repeated mistakes" in claude_md_content
        assert "Tracks progress across autonomous sessions" in claude_md_content
        assert "Provides audit trail for feature development" in claude_md_content

    def test_turn_state_schema_complete(self, claude_md_content):
        """Test that turn state schema is completely documented."""
        # All key fields should be documented
        required_fields = [
            "feature_id",
            "task_id",
            "turn_number",
            "player_decision",
            "coach_decision",
            "feedback_summary",
            "blockers_found",
            "files_modified",
            "acceptance_criteria_status",
            "mode",
        ]

        for field in required_fields:
            assert field in claude_md_content

        # Should document mode values
        assert "FRESH_START" in claude_md_content
        assert "RECOVERING_STATE" in claude_md_content
        assert "CONTINUING_WORK" in claude_md_content


class TestTroubleshooting:
    """Test troubleshooting documentation."""

    def test_all_troubleshooting_scenarios_covered(self, claude_md_content):
        """Test that all troubleshooting scenarios are documented."""
        scenarios = [
            "Command not found",
            "Connection errors",
            "No results from queries",
            "Empty turn states",
            "Slow queries",
            "Stale knowledge",
        ]

        for scenario in scenarios:
            assert scenario in claude_md_content

    def test_troubleshooting_provides_solutions(self, claude_md_content):
        """Test that troubleshooting provides actionable solutions."""
        # Each scenario should have a solution
        assert "guardkit graphiti status" in claude_md_content
        assert "cat config/graphiti.yaml" in claude_md_content
        assert "docker ps | grep neo4j" in claude_md_content
        assert "guardkit graphiti seed" in claude_md_content
        assert "guardkit autobuild task TASK-XXX" in claude_md_content
        assert "guardkit graphiti seed --force" in claude_md_content


class TestCrossReferences:
    """Test cross-references in documentation."""

    def test_feat_gr005_reference(self, claude_md_content):
        """Test that FEAT-GR-005 is referenced."""
        assert "FEAT-GR-005" in claude_md_content
        assert "docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md" in claude_md_content

    def test_implementation_completeness(self, feat_gr005_content):
        """Test that FEAT-GR-005 documents implementation completeness."""
        # Should mark all tasks as complete
        assert "✅ Complete" in feat_gr005_content or "✅ complete" in feat_gr005_content.lower()

        # Should have key implementation details
        assert "CLI Commands" in feat_gr005_content
        assert "Output Formatting" in feat_gr005_content
        assert "Turn State Tracking" in feat_gr005_content
        assert "Testing" in feat_gr005_content
        assert "Documentation Updates" in feat_gr005_content
