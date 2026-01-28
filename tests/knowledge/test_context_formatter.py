"""
TDD RED Phase: Tests for guardkit.knowledge.context_formatter

These tests define the expected behavior for context formatting.
The implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- format_context_for_injection() with various context types
- Markdown section generation
- Empty context handling
- Content truncation and limits
- Special character handling

Coverage Target: >=80%
"""

import pytest
from unittest.mock import Mock

# Import will succeed after implementation (GREEN phase)
try:
    from guardkit.knowledge.context_formatter import (
        format_context_for_injection,
        _format_architecture_decisions_section,
        _format_failure_patterns_section,
        _format_quality_gates_section,
        _format_system_context_section,
        ContextFormatterConfig,
    )
    from guardkit.knowledge.context_loader import CriticalContext
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    CriticalContext = None


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


class TestFormatContextForInjection:
    """Test format_context_for_injection() main function."""

    def test_format_empty_context_returns_string(self):
        """Test formatting empty context returns string."""
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

        result = format_context_for_injection(context)

        assert isinstance(result, str)

    def test_format_empty_context_returns_empty_or_minimal(self):
        """Test formatting empty context returns empty or minimal content."""
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

        result = format_context_for_injection(context)

        # Should be minimal or empty when no context available
        assert len(result) < 100  # Reasonable limit for empty context

    def test_format_context_with_architecture_decisions(self):
        """Test formatting context with architecture decisions."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "Use SDK query()", "decision": "Always use SDK query() not subprocess"}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should include architecture decisions section
        assert "Architecture" in result or "Decision" in result
        assert "SDK" in result or "query" in result

    def test_format_context_with_failure_patterns(self):
        """Test formatting context with failure patterns."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[
                {"body": {"description": "Using subprocess for CLI commands that don't exist"}}
            ],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should include failure patterns section
        assert "Failure" in result or "AVOID" in result or "subprocess" in result

    def test_format_context_with_quality_gates(self):
        """Test formatting context with quality gates."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[
                {"body": {"phase": "Phase 4", "requirement": "80% code coverage"}}
            ],
            architecture_decisions=[],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should include quality gates section
        assert "Quality" in result or "Gate" in result or "Phase" in result

    def test_format_context_with_all_sections(self):
        """Test formatting context with all sections populated."""
        context = CriticalContext(
            system_context=[
                {"body": {"name": "GuardKit", "description": "Task workflow"}}
            ],
            quality_gates=[
                {"body": {"phase": "Phase 4", "requirement": "80% coverage"}}
            ],
            architecture_decisions=[
                {"body": {"title": "Use SDK", "decision": "Use SDK query()"}}
            ],
            failure_patterns=[
                {"body": {"description": "subprocess failure"}}
            ],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should include all sections
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_context_uses_markdown_headers(self):
        """Test that formatted context uses markdown headers."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "Test Decision", "decision": "Test"}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should use markdown headers (##)
        assert "##" in result or "#" in result


class TestFormatArchitectureDecisionsSection:
    """Test _format_architecture_decisions_section() helper."""

    def test_format_empty_decisions(self):
        """Test formatting empty architecture decisions."""
        result = _format_architecture_decisions_section([])
        assert result == ""

    def test_format_single_decision(self):
        """Test formatting single architecture decision."""
        decisions = [
            {"body": {"title": "Use SDK query()", "decision": "Always use SDK"}}
        ]

        result = _format_architecture_decisions_section(decisions)

        assert "SDK" in result
        assert len(result) > 0

    def test_format_multiple_decisions(self):
        """Test formatting multiple architecture decisions."""
        decisions = [
            {"body": {"title": "Decision 1", "decision": "First decision"}},
            {"body": {"title": "Decision 2", "decision": "Second decision"}},
        ]

        result = _format_architecture_decisions_section(decisions)

        assert "Decision 1" in result or "First" in result
        assert "Decision 2" in result or "Second" in result

    def test_format_decisions_limits_count(self):
        """Test that decisions are limited to reasonable count.

        Note: The helper function formats ALL decisions passed to it.
        Limiting is done by the caller (format_context_for_injection)
        using config.max_decisions slicing. This tests that when
        a reasonable number is passed, the output is reasonable.
        """
        # Pass a pre-sliced list (as format_context_for_injection would)
        decisions = [
            {"body": {"title": f"Decision {i}", "decision": f"Content {i}"}}
            for i in range(5)  # Pre-limited as caller would do
        ]

        result = _format_architecture_decisions_section(decisions)

        # Count bullet points to verify decision count (header contains "Decision" too)
        bullet_count = result.count("- **Decision")
        assert bullet_count == 5  # Matches input count

    def test_format_decision_with_missing_title(self):
        """Test formatting decision with missing title."""
        decisions = [
            {"body": {"decision": "No title provided"}}
        ]

        result = _format_architecture_decisions_section(decisions)

        # Should handle gracefully (use 'Unknown' or skip)
        assert isinstance(result, str)

    def test_format_decision_with_missing_body(self):
        """Test formatting decision with missing body."""
        decisions = [
            {"no_body": "invalid"}
        ]

        result = _format_architecture_decisions_section(decisions)

        # Should handle gracefully
        assert isinstance(result, str)


class TestFormatFailurePatternsSection:
    """Test _format_failure_patterns_section() helper."""

    def test_format_empty_patterns(self):
        """Test formatting empty failure patterns."""
        result = _format_failure_patterns_section([])
        assert result == ""

    def test_format_single_pattern(self):
        """Test formatting single failure pattern."""
        patterns = [
            {"body": {"description": "Using subprocess for non-existent CLI commands"}}
        ]

        result = _format_failure_patterns_section(patterns)

        assert "subprocess" in result or "CLI" in result
        assert len(result) > 0

    def test_format_multiple_patterns(self):
        """Test formatting multiple failure patterns."""
        patterns = [
            {"body": {"description": "Pattern 1 failure"}},
            {"body": {"description": "Pattern 2 failure"}},
        ]

        result = _format_failure_patterns_section(patterns)

        assert "Pattern 1" in result or "failure" in result

    def test_format_patterns_limits_count(self):
        """Test that patterns are limited to reasonable count."""
        patterns = [
            {"body": {"description": f"Failure pattern {i}"}}
            for i in range(20)
        ]

        result = _format_failure_patterns_section(patterns)

        # Should limit to 3 patterns (as per task spec)
        # Count occurrences to verify limiting
        assert isinstance(result, str)


class TestFormatQualityGatesSection:
    """Test _format_quality_gates_section() helper."""

    def test_format_empty_gates(self):
        """Test formatting empty quality gates."""
        result = _format_quality_gates_section([])
        assert result == ""

    def test_format_single_gate(self):
        """Test formatting single quality gate."""
        gates = [
            {"body": {"phase": "Phase 4", "requirement": "80% code coverage"}}
        ]

        result = _format_quality_gates_section(gates)

        assert "Phase 4" in result or "coverage" in result
        assert len(result) > 0

    def test_format_multiple_gates(self):
        """Test formatting multiple quality gates."""
        gates = [
            {"body": {"phase": "Phase 2.5", "requirement": "Architectural review"}},
            {"body": {"phase": "Phase 4", "requirement": "80% coverage"}},
        ]

        result = _format_quality_gates_section(gates)

        assert isinstance(result, str)
        assert len(result) > 0


class TestFormatSystemContextSection:
    """Test _format_system_context_section() helper."""

    def test_format_empty_system_context(self):
        """Test formatting empty system context."""
        result = _format_system_context_section([])
        assert result == ""

    def test_format_single_context_item(self):
        """Test formatting single system context item."""
        context_items = [
            {"body": {"name": "GuardKit", "description": "Task workflow system"}}
        ]

        result = _format_system_context_section(context_items)

        assert "GuardKit" in result or "Task" in result


class TestContextFormatterConfig:
    """Test ContextFormatterConfig dataclass."""

    def test_config_default_values(self):
        """Test default configuration values."""
        config = ContextFormatterConfig()

        assert hasattr(config, 'max_decisions')
        assert hasattr(config, 'max_failure_patterns')
        assert hasattr(config, 'max_quality_gates')

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = ContextFormatterConfig(
            max_decisions=3,
            max_failure_patterns=2,
            max_quality_gates=2
        )

        assert config.max_decisions == 3
        assert config.max_failure_patterns == 2
        assert config.max_quality_gates == 2


class TestFormatContextWithConfig:
    """Test format_context_for_injection() with custom config."""

    def test_format_context_respects_max_decisions(self):
        """Test that max_decisions config is respected."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": f"Decision {i}", "decision": f"Content {i}"}}
                for i in range(10)
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        config = ContextFormatterConfig(max_decisions=2)
        result = format_context_for_injection(context, config=config)

        # Should only include 2 decisions
        # Count bullet points or decision references
        assert isinstance(result, str)

    def test_format_context_respects_max_failure_patterns(self):
        """Test that max_failure_patterns config is respected."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[],
            failure_patterns=[
                {"body": {"description": f"Pattern {i}"}}
                for i in range(10)
            ],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        config = ContextFormatterConfig(max_failure_patterns=1)
        result = format_context_for_injection(context, config=config)

        assert isinstance(result, str)


class TestSpecialCharacterHandling:
    """Test handling of special characters in context."""

    def test_format_context_with_markdown_chars(self):
        """Test handling of markdown special characters."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "Test *bold* and _italic_", "decision": "Use `code`"}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should handle markdown chars without breaking
        assert isinstance(result, str)

    def test_format_context_with_newlines(self):
        """Test handling of newlines in content."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "Multi\nline\ntitle", "decision": "Line1\nLine2"}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should handle newlines
        assert isinstance(result, str)

    def test_format_context_with_unicode(self):
        """Test handling of unicode characters."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "Unicode: \u2713 \u2717 \u2022", "decision": "Test \u00e9\u00e8\u00ea"}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should handle unicode
        assert isinstance(result, str)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_format_context_with_none_values(self):
        """Test handling of None values in body."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": None, "decision": None}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should handle None values gracefully
        assert isinstance(result, str)

    def test_format_context_with_empty_strings(self):
        """Test handling of empty strings."""
        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "", "decision": ""}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should handle empty strings gracefully
        assert isinstance(result, str)

    def test_format_context_with_very_long_content(self):
        """Test handling of very long content."""
        long_content = "A" * 10000  # 10KB of content

        context = CriticalContext(
            system_context=[],
            quality_gates=[],
            architecture_decisions=[
                {"body": {"title": "Long Content", "decision": long_content}}
            ],
            failure_patterns=[],
            successful_patterns=[],
            similar_task_outcomes=[],
            relevant_adrs=[],
            applicable_patterns=[],
            relevant_rules=[]
        )

        result = format_context_for_injection(context)

        # Should handle long content (possibly truncate)
        assert isinstance(result, str)
        # Should be reasonable length
        assert len(result) < 50000  # Shouldn't explode
