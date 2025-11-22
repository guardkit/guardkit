"""
Unit tests for boundaries implementation in agent enhancement pipeline.

Tests the complete boundaries feature across all three modules:
1. prompt_builder.py - Boundaries format in prompts
2. parser.py - Validation logic for boundaries content
3. applier.py - Smart placement of boundaries in agent files

Test Coverage:
- Prompt generation with boundaries requirements
- Validation of boundaries structure (ALWAYS/NEVER/ASK)
- Rule count validation (5-7, 5-7, 3-5)
- Emoji validation (✅, ❌, ⚠️)
- Smart placement logic (after Quick Start, before Capabilities)
- Backward compatibility with best_practices format
- Integration tests for end-to-end flow
"""

import pytest
import sys
from pathlib import Path

# Add agent_enhancement module to path
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from prompt_builder import EnhancementPromptBuilder
from parser import EnhancementParser
from applier import EnhancementApplier


# ============================================================================
# PROMPT BUILDER TESTS - Boundaries Format in Prompts
# ============================================================================

class TestPromptBuilderBoundaries:
    """Test boundaries requirements in prompt generation."""

    def test_prompt_includes_boundaries_section(self, tmp_path):
        """Test prompt includes boundaries in sections list."""
        builder = EnhancementPromptBuilder()

        # Create actual template file in tmp_path
        template_file = tmp_path / "test.template"
        template_file.write_text("content")

        prompt = builder.build(
            agent_metadata={"name": "test-agent", "description": "Test description"},
            templates=[template_file],
            template_dir=tmp_path
        )

        assert '"sections": ["related_templates", "examples", "boundaries"]' in prompt

    def test_prompt_includes_boundaries_requirements(self, tmp_path):
        """Test prompt includes ALWAYS/NEVER/ASK requirements."""
        builder = EnhancementPromptBuilder()

        # Create actual template file
        template_file = tmp_path / "test.template"
        template_file.write_text("content")

        prompt = builder.build(
            agent_metadata={"name": "test-agent", "description": "Test"},
            templates=[template_file],
            template_dir=tmp_path
        )

        assert "**Boundaries Requirements**" in prompt
        assert "**ALWAYS section**: 5-7 rules with ✅ prefix" in prompt
        assert "**NEVER section**: 5-7 rules with ❌ prefix" in prompt
        assert "**ASK section**: 3-5 scenarios with ⚠️ prefix" in prompt

    def test_prompt_includes_boundaries_format_example(self, tmp_path):
        """Test prompt includes boundaries format example."""
        builder = EnhancementPromptBuilder()

        template_file = tmp_path / "test.template"
        template_file.write_text("content")

        prompt = builder.build(
            agent_metadata={"name": "test-agent", "description": "Test"},
            templates=[template_file],
            template_dir=tmp_path
        )

        assert '✅ Validate schemas (prevent invalid data processing)' in prompt

    def test_prompt_includes_boundaries_in_json_structure(self, tmp_path):
        """Test prompt shows boundaries in output JSON structure."""
        builder = EnhancementPromptBuilder()

        template_file = tmp_path / "test.template"
        template_file.write_text("content")

        prompt = builder.build(
            agent_metadata={"name": "test-agent", "description": "Test"},
            templates=[template_file],
            template_dir=tmp_path
        )

        assert '"boundaries": "## Boundaries\\n\\n### ALWAYS\\n' in prompt


# ============================================================================
# PARSER TESTS - Boundaries Validation Logic
# ============================================================================

class TestParserBoundariesValidation:
    """Test boundaries validation in parser."""

    def test_validate_boundaries_complete_structure(self):
        """Test validation passes for complete boundaries structure."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)
"""

        # Should not raise
        parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_missing_subsection(self):
        """Test validation fails when subsection missing."""
        parser = EnhancementParser()

        # Missing ASK section
        boundaries_content = """## Boundaries

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
"""

        with pytest.raises(ValueError, match="missing '### ASK' subsection"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_wrong_always_count_too_few(self):
        """Test validation fails when ALWAYS has too few rules."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3

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

        with pytest.raises(ValueError, match="ALWAYS section must have 5-7 rules, found 3"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_wrong_always_count_too_many(self):
        """Test validation fails when ALWAYS has too many rules."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

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

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
"""

        with pytest.raises(ValueError, match="ALWAYS section must have 5-7 rules, found 8"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_wrong_never_count(self):
        """Test validation fails when NEVER has wrong count."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5

### NEVER
- ❌ Rule 1
- ❌ Rule 2

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
"""

        with pytest.raises(ValueError, match="NEVER section must have 5-7 rules, found 2"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_wrong_ask_count_too_few(self):
        """Test validation fails when ASK has too few scenarios."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

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
"""

        with pytest.raises(ValueError, match="ASK section must have 3-5 scenarios, found 1"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_wrong_ask_count_too_many(self):
        """Test validation fails when ASK has too many scenarios."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

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
- ⚠️ Scenario 4
- ⚠️ Scenario 5
- ⚠️ Scenario 6
"""

        with pytest.raises(ValueError, match="ASK section must have 3-5 scenarios, found 6"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_missing_emoji(self):
        """Test validation fails when rules missing emoji prefix."""
        parser = EnhancementParser()

        # Rules without emoji prefix
        boundaries_content = """## Boundaries

### ALWAYS
- Rule 1 (no emoji)
- Rule 2 (no emoji)
- Rule 3 (no emoji)
- Rule 4 (no emoji)
- Rule 5 (no emoji)

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

        with pytest.raises(ValueError, match="ALWAYS section must have 5-7 rules, found 0"):
            parser._validate_boundaries(boundaries_content)

    def test_validate_boundaries_max_limits(self):
        """Test validation passes at maximum rule counts (7-7-5)."""
        parser = EnhancementParser()

        boundaries_content = """## Boundaries

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

        # Should not raise
        parser._validate_boundaries(boundaries_content)

    def test_count_rules_with_spacing_variations(self):
        """Test rule counting handles spacing variations."""
        parser = EnhancementParser()

        # Test with different spacing formats
        section1 = "- ✅ Rule 1\n- ✅ Rule 2"  # Standard spacing
        section2 = "-✅ Rule 1\n-✅ Rule 2"    # No space after dash

        count1 = parser._count_rules(section1, "✅")
        count2 = parser._count_rules(section2, "✅")

        assert count1 == 2
        assert count2 == 2

    def test_parse_with_boundaries_validation_called(self):
        """Test parse() calls boundaries validation when section present."""
        parser = EnhancementParser()

        # Invalid boundaries (too few rules)
        response = """{
    "sections": ["boundaries"],
    "boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule 1\\n\\n### NEVER\\n- ❌ Rule 1\\n\\n### ASK\\n- ⚠️ Scenario 1"
}"""

        with pytest.raises(ValueError, match="ALWAYS section must have 5-7 rules"):
            parser.parse(response)


# ============================================================================
# APPLIER TESTS - Smart Placement Logic
# ============================================================================

class TestApplierBoundariesPlacement:
    """Test boundaries placement logic in applier."""

    def test_find_boundaries_insertion_point_before_capabilities(self):
        """Test insertion point found before Capabilities section."""
        applier = EnhancementApplier()

        lines = [
            "---",
            "name: test",
            "---",
            "",
            "# Test Agent",
            "",
            "## Quick Start",
            "",
            "Content here",
            "",
            "## Capabilities",
            "",
            "More content"
        ]

        insertion_point = applier._find_boundaries_insertion_point(lines)
        assert insertion_point == 10  # Before "## Capabilities"
        assert lines[insertion_point].startswith("## Capabilities")

    def test_find_boundaries_insertion_point_after_quick_start(self):
        """Test insertion point after Quick Start when no Capabilities."""
        applier = EnhancementApplier()

        lines = [
            "---",
            "name: test",
            "---",
            "",
            "# Test Agent",
            "",
            "## Quick Start",
            "",
            "Content here",
            "",
            "## Examples",
            "",
            "More content"
        ]

        insertion_point = applier._find_boundaries_insertion_point(lines)
        assert insertion_point == 10  # Before "## Examples"

    def test_find_boundaries_insertion_point_no_markers(self):
        """Test returns None when no suitable insertion point."""
        applier = EnhancementApplier()

        lines = [
            "---",
            "name: test",
            "---",
            "",
            "# Test Agent",
            "",
            "Some content"
        ]

        insertion_point = applier._find_boundaries_insertion_point(lines)
        assert insertion_point is None

    def test_merge_content_boundaries_placement(self, tmp_path):
        """Test boundaries inserted at correct location in merged content."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent

## Quick Start

Use this agent.

## Capabilities

Does things.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        merged = applier._merge_content(original, enhancement)

        # Verify boundaries appears before Capabilities
        assert "## Boundaries" in merged
        boundaries_idx = merged.find("## Boundaries")
        capabilities_idx = merged.find("## Capabilities")
        assert boundaries_idx < capabilities_idx
        assert boundaries_idx > 0

    def test_merge_content_boundaries_after_quick_start(self):
        """Test boundaries placed after Quick Start section."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent

## Quick Start

Use this agent.

## Capabilities

Does things.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        merged = applier._merge_content(original, enhancement)

        # Verify boundaries appears after Quick Start
        quick_start_idx = merged.find("## Quick Start")
        boundaries_idx = merged.find("## Boundaries")
        assert boundaries_idx > quick_start_idx

    def test_merge_content_boundaries_no_duplicate(self):
        """Test boundaries not duplicated if already exists."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent

## Quick Start

Use this agent.

## Boundaries

### ALWAYS
- ✅ Existing rule

### NEVER
- ❌ Existing rule

### ASK
- ⚠️ Existing scenario

## Capabilities

Does things.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ New rule 1
- ✅ New rule 2
- ✅ New rule 3
- ✅ New rule 4
- ✅ New rule 5

### NEVER
- ❌ New rule 1
- ❌ New rule 2
- ❌ New rule 3
- ❌ New rule 4
- ❌ New rule 5

### ASK
- ⚠️ New scenario 1
- ⚠️ New scenario 2
- ⚠️ New scenario 3"""
        }

        merged = applier._merge_content(original, enhancement)

        # Count occurrences of "## Boundaries"
        count = merged.count("## Boundaries")
        assert count == 1

    def test_merge_content_fallback_to_end(self):
        """Test boundaries appended at end if no insertion point found."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent

Some content here.
"""

        enhancement = {
            "sections": ["boundaries"],
            "boundaries": """## Boundaries

### ALWAYS
- ✅ Rule 1 (rationale)
- ✅ Rule 2 (rationale)
- ✅ Rule 3 (rationale)
- ✅ Rule 4 (rationale)
- ✅ Rule 5 (rationale)

### NEVER
- ❌ Rule 1 (rationale)
- ❌ Rule 2 (rationale)
- ❌ Rule 3 (rationale)
- ❌ Rule 4 (rationale)
- ❌ Rule 5 (rationale)

### ASK
- ⚠️ Scenario 1 (rationale)
- ⚠️ Scenario 2 (rationale)
- ⚠️ Scenario 3 (rationale)"""
        }

        merged = applier._merge_content(original, enhancement)

        # Boundaries should be at end
        assert merged.strip().endswith("- ⚠️ Scenario 3 (rationale)")


# ============================================================================
# INTEGRATION TESTS - End-to-End Boundaries Flow
# ============================================================================

class TestBoundariesIntegration:
    """Integration tests for complete boundaries workflow."""

    def test_end_to_end_boundaries_generation(self, tmp_path):
        """Test complete flow: build prompt → parse response → apply to file."""
        # 1. Build prompt
        builder = EnhancementPromptBuilder()

        template_file = tmp_path / "test.template"
        template_file.write_text("content")

        prompt = builder.build(
            agent_metadata={"name": "test-agent", "description": "Test agent"},
            templates=[template_file],
            template_dir=tmp_path
        )

        assert "boundaries" in prompt

        # 2. Simulate AI response with valid boundaries
        ai_response = """{
    "sections": ["boundaries"],
    "boundaries": "## Boundaries\\n\\n### ALWAYS\\n- ✅ Rule 1 (rationale)\\n- ✅ Rule 2 (rationale)\\n- ✅ Rule 3 (rationale)\\n- ✅ Rule 4 (rationale)\\n- ✅ Rule 5 (rationale)\\n\\n### NEVER\\n- ❌ Rule 1 (rationale)\\n- ❌ Rule 2 (rationale)\\n- ❌ Rule 3 (rationale)\\n- ❌ Rule 4 (rationale)\\n- ❌ Rule 5 (rationale)\\n\\n### ASK\\n- ⚠️ Scenario 1 (rationale)\\n- ⚠️ Scenario 2 (rationale)\\n- ⚠️ Scenario 3 (rationale)"
}"""

        # 3. Parse response
        parser = EnhancementParser()
        enhancement = parser.parse(ai_response)

        assert "boundaries" in enhancement["sections"]
        assert "## Boundaries" in enhancement["boundaries"]

        # 4. Apply to file
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text("""---
name: test-agent
---

# Test Agent

## Quick Start

Use this.

## Capabilities

Does things.
""")

        applier = EnhancementApplier()
        applier.apply(agent_file, enhancement)

        # 5. Verify result
        result = agent_file.read_text()
        assert "## Boundaries" in result
        assert "### ALWAYS" in result
        assert "### NEVER" in result
        assert "### ASK" in result
        assert result.index("## Boundaries") < result.index("## Capabilities")

    def test_backward_compatibility_best_practices(self):
        """Test system handles old best_practices format gracefully."""
        parser = EnhancementParser()

        # Old format response (no boundaries, just best_practices)
        old_response = """{
    "sections": ["best_practices"],
    "best_practices": "## Best Practices\\n\\n- Practice 1\\n- Practice 2"
}"""

        # Should parse without validation errors
        enhancement = parser.parse(old_response)
        assert "best_practices" in enhancement["sections"]
        assert "boundaries" not in enhancement["sections"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
