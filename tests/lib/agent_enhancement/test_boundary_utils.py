"""
Tests for shared boundary utilities.

TASK-UX-6581: Test coverage for boundary_utils.py shared library.
"""

import pytest
import sys
from pathlib import Path

# Add the installer.core.lib.agent_enhancement directory to Python path
_test_dir = Path(__file__).resolve().parent
_lib_dir = _test_dir.parent.parent.parent / "installer" / "core" / "lib" / "agent_enhancement"
sys.path.insert(0, str(_lib_dir))

from boundary_utils import (
    find_boundaries_insertion_point,
    validate_boundaries_format,
    generate_generic_boundaries,
)


class TestFindBoundariesInsertionPoint:
    """Test placement logic for boundaries section."""

    def test_with_quick_start(self):
        """Should insert after Quick Start, before next section."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "## Quick Start",
            "Instructions",
            "## Code Examples",
            "Examples"
        ]

        result = find_boundaries_insertion_point(lines)
        assert result == 6  # Before Code Examples

    def test_no_quick_start(self):
        """Should use fallback placement before Code Examples."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "## Purpose",
            "Description",
            "## Code Examples",
            "Examples"
        ]

        result = find_boundaries_insertion_point(lines)
        assert result == 6  # Before Code Examples

    def test_with_quick_start_no_next_section(self):
        """Should insert 30 lines after Quick Start if no next section."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "## Quick Start",
            "Instructions",
        ] + ["Content line"] * 50

        result = find_boundaries_insertion_point(lines)
        # Should insert at quick_start_idx (4) + 30 = 34, but capped at len(lines) = 56
        assert result == 34

    def test_fallback_before_related_templates(self):
        """Should use fallback to insert before Related Templates."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "## Purpose",
            "Description",
            "## Related Templates",
            "Templates"
        ]

        result = find_boundaries_insertion_point(lines)
        assert result == 6  # Before Related Templates

    def test_absolute_fallback(self):
        """Should use absolute fallback (frontmatter + 50 lines) if nothing else works."""
        lines = [
            "---",
            "name: test",
            "---",
            "# Agent",
            "Content",
        ] + ["More content"] * 100

        result = find_boundaries_insertion_point(lines)
        # Should be at frontmatter_end (3 = after second ---) + 50 = 53
        # (The function finds the next section boundary or uses frontmatter_end + 50)
        assert result == 53


class TestValidateBoundariesFormat:
    """Test validation logic for boundaries sections."""

    def test_valid_boundaries_min_counts(self):
        """Should pass with minimum rule counts (5 ALWAYS, 5 NEVER, 3 ASK)."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5

### NEVER
- ❌ Rule 1
- ❌ Rule 2
- ❌ Rule 3
- ❌ Rule 4
- ❌ Rule 5

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is True
        assert len(issues) == 0

    def test_valid_boundaries_max_counts(self):
        """Should pass with maximum rule counts (7 ALWAYS, 7 NEVER, 5 ASK)."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5
- ✅ Rule 6
- ✅ Rule 7

### NEVER
- ❌ Rule 1
- ❌ Rule 2
- ❌ Rule 3
- ❌ Rule 4
- ❌ Rule 5
- ❌ Rule 6
- ❌ Rule 7

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
- ⚠️ Scenario 4
- ⚠️ Scenario 5
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is True
        assert len(issues) == 0

    def test_invalid_rule_counts_too_few(self):
        """Should fail with too few rules in all sections."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1

### NEVER
- ❌ Rule 1

### ASK
- ⚠️ Scenario 1
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is False
        assert len(issues) == 3  # All sections have wrong counts
        assert any("ALWAYS" in issue for issue in issues)
        assert any("NEVER" in issue for issue in issues)
        assert any("ASK" in issue for issue in issues)

    def test_invalid_rule_counts_too_many(self):
        """Should fail with too many rules."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5
- ✅ Rule 6
- ✅ Rule 7
- ✅ Rule 8

### NEVER
- ❌ Rule 1
- ❌ Rule 2
- ❌ Rule 3
- ❌ Rule 4
- ❌ Rule 5
- ❌ Rule 6
- ❌ Rule 7
- ❌ Rule 8

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
- ⚠️ Scenario 4
- ⚠️ Scenario 5
- ⚠️ Scenario 6
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is False
        assert len(issues) == 3  # All sections have too many rules

    def test_missing_sections(self):
        """Should fail if required subsections are missing."""
        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5
"""

        is_valid, issues = validate_boundaries_format(content)
        assert is_valid is False
        assert any("NEVER" in issue for issue in issues)
        assert any("ASK" in issue for issue in issues)

    def test_empty_content(self):
        """Should fail if boundaries content is empty."""
        is_valid, issues = validate_boundaries_format("")
        assert is_valid is False
        assert len(issues) == 1
        assert "empty" in issues[0].lower()


class TestGenerateGenericBoundaries:
    """Test generic boundary generation."""

    def test_testing_agent(self):
        """Should generate testing-focused boundaries for test-related agents."""
        result = generate_generic_boundaries("test-verifier", "Test execution and verification")

        assert "## Boundaries" in result
        assert "### ALWAYS" in result
        assert "### NEVER" in result
        assert "### ASK" in result
        assert "test" in result.lower()

    def test_architecture_agent(self):
        """Should generate architecture-focused boundaries."""
        result = generate_generic_boundaries("architectural-reviewer", "SOLID principles review")

        assert "## Boundaries" in result
        assert "SOLID" in result or "pattern" in result.lower()

    def test_code_review_agent(self):
        """Should generate code review-focused boundaries."""
        result = generate_generic_boundaries("code-reviewer", "Code quality review")

        assert "## Boundaries" in result
        assert "lint" in result.lower() or "quality" in result.lower()

    def test_orchestration_agent(self):
        """Should generate orchestration-focused boundaries."""
        result = generate_generic_boundaries("task-manager", "Workflow orchestration")

        assert "## Boundaries" in result
        assert "phase" in result.lower() or "workflow" in result.lower()

    def test_default_agent(self):
        """Should generate default boundaries for unknown agent types."""
        result = generate_generic_boundaries("unknown-agent", "Generic description")

        assert "## Boundaries" in result
        assert "### ALWAYS" in result
        assert "### NEVER" in result
        assert "### ASK" in result

    def test_generated_content_validates(self):
        """All generated content should pass validation."""
        agent_types = [
            ("test-verifier", "Test execution"),
            ("architectural-reviewer", "Architecture review"),
            ("code-reviewer", "Code quality"),
            ("task-manager", "Workflow orchestration"),
            ("unknown-agent", "Generic"),
        ]

        for agent_name, agent_description in agent_types:
            result = generate_generic_boundaries(agent_name, agent_description)
            is_valid, issues = validate_boundaries_format(result)
            assert is_valid is True, f"Generated content for {agent_name} failed validation: {issues}"


class TestRoleInference:
    """Test role category inference from agent name/description."""

    def test_infer_testing_role(self):
        """Should infer testing role from keywords."""
        result = generate_generic_boundaries("pytest-runner", "Test coverage analysis")
        assert "test" in result.lower()

    def test_infer_architecture_role(self):
        """Should infer architecture role from keywords."""
        result = generate_generic_boundaries("design-reviewer", "SOLID principle assessment")
        assert "SOLID" in result

    def test_infer_code_review_role(self):
        """Should infer code review role from keywords."""
        result = generate_generic_boundaries("linter", "Code style validation")
        assert "lint" in result.lower()

    def test_infer_orchestration_role(self):
        """Should infer orchestration role from keywords."""
        result = generate_generic_boundaries("phase-manager", "Task workflow phases")
        assert "phase" in result.lower()


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_generate_and_validate_flow(self):
        """Complete flow: generate → validate → should pass."""
        # Generate
        boundaries = generate_generic_boundaries("test-orchestrator", "Test workflow management")

        # Validate
        is_valid, issues = validate_boundaries_format(boundaries)

        # Assert
        assert is_valid is True
        assert len(issues) == 0

    def test_placement_with_generated_content(self):
        """Test that generated boundaries can be placed correctly."""
        # Create agent lines
        lines = [
            "---",
            "name: test-agent",
            "---",
            "# Test Agent",
            "## Quick Start",
            "Instructions",
            "## Code Examples",
            "Examples"
        ]

        # Find insertion point
        insert_line = find_boundaries_insertion_point(lines)

        # Generate boundaries
        boundaries = generate_generic_boundaries("test-agent", "Testing")

        # Insert
        boundary_lines = boundaries.strip().split('\n')
        new_lines = lines[:insert_line] + [''] + boundary_lines + [''] + lines[insert_line:]

        # Verify placement (should be before Code Examples)
        boundaries_start = None
        code_examples_start = None

        for i, line in enumerate(new_lines):
            if "## Boundaries" in line:
                boundaries_start = i
            if "## Code Examples" in line:
                code_examples_start = i

        assert boundaries_start is not None
        assert code_examples_start is not None
        assert boundaries_start < code_examples_start


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_agent_name(self):
        """Should handle empty agent name gracefully."""
        result = generate_generic_boundaries("", "")
        is_valid, issues = validate_boundaries_format(result)
        assert is_valid is True  # Should still generate valid default boundaries

    def test_very_long_description(self):
        """Should handle very long descriptions."""
        long_desc = "test " * 1000
        result = generate_generic_boundaries("agent", long_desc)
        is_valid, issues = validate_boundaries_format(result)
        assert is_valid is True

    def test_special_characters_in_name(self):
        """Should handle special characters in agent name."""
        result = generate_generic_boundaries("test-agent_v2.0", "Testing")
        is_valid, issues = validate_boundaries_format(result)
        assert is_valid is True

    def test_unicode_in_description(self):
        """Should handle unicode characters in description."""
        result = generate_generic_boundaries("agent", "Testing 测试 тест")
        is_valid, issues = validate_boundaries_format(result)
        assert is_valid is True
