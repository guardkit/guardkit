"""
Additional tests to achieve ≥80% line and ≥75% branch coverage.

This module adds tests for error handling paths and edge cases
not covered by test_boundaries_implementation.py.

Coverage targets:
- parser.py: Error paths in JSON parsing
- applier.py: File I/O errors, diff generation, remove_sections
- prompt_builder.py: Template overflow handling, build_minimal
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add agent_enhancement module to path
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from prompt_builder import EnhancementPromptBuilder
from parser import EnhancementParser
from applier import EnhancementApplier


# ============================================================================
# PROMPT BUILDER TESTS - Additional Coverage
# ============================================================================

class TestPromptBuilderCoverage:
    """Tests for prompt_builder.py uncovered paths."""

    def test_build_with_many_templates(self, tmp_path):
        """Test template limiting when >20 templates (line 67)."""
        builder = EnhancementPromptBuilder()

        # Create 25 template files
        templates = []
        for i in range(25):
            template_file = tmp_path / f"template{i}.template"
            template_file.write_text("content")
            templates.append(template_file)

        prompt = builder.build(
            agent_metadata={"name": "test-agent", "description": "Test"},
            templates=templates,
            template_dir=tmp_path
        )

        # Should show first 20 templates and "... and 5 more"
        assert "... and 5 more templates" in prompt
        assert "**Available Templates** (25 total):" in prompt

    def test_build_minimal(self):
        """Test build_minimal method (line 121)."""
        builder = EnhancementPromptBuilder()

        prompt = builder.build_minimal("test-agent", 10)

        assert "Enhance agent 'test-agent' with 10 templates" in prompt
        assert "Return JSON:" in prompt
        assert '"sections": ["related_templates"]' in prompt


# ============================================================================
# PARSER TESTS - Error Handling and Edge Cases
# ============================================================================

class TestParserCoverage:
    """Tests for parser.py uncovered paths."""

    def test_parse_markdown_wrapped_json_error(self):
        """Test JSON decode error in markdown block (lines 55-60)."""
        parser = EnhancementParser()

        # Markdown block with invalid JSON
        response = """```json
{
    "sections": ["test",  // Invalid JSON comment
}
```"""

        # Should fall through to try parsing entire response
        with pytest.raises(ValueError, match="Could not parse enhancement response"):
            parser.parse(response)

    def test_parse_entire_response_as_json_fallback(self):
        """Test parsing entire response when markdown extraction fails (line 70)."""
        parser = EnhancementParser()

        # Valid JSON without markdown wrapper
        response = '{"sections": ["test"], "test": "content"}'

        enhancement = parser.parse(response)
        assert enhancement["sections"] == ["test"]

    def test_parse_json_pattern_matching_fallback(self):
        """Test JSON pattern matching as last resort (lines 74-82)."""
        parser = EnhancementParser()

        # JSON embedded in text without proper code blocks
        response = """
Here's the enhancement:
{"sections": ["related_templates"], "related_templates": "## Related Templates"}
Hope this helps!
"""

        enhancement = parser.parse(response)
        assert "related_templates" in enhancement["sections"]

    def test_parse_json_pattern_matching_with_invalid_json(self):
        """Test JSON pattern matching with multiple invalid attempts (lines 76-82)."""
        parser = EnhancementParser()

        # Multiple JSON-like patterns, but invalid
        response = """
{"sections": invalid json}
{"sections" more invalid}
No valid JSON here
"""

        with pytest.raises(ValueError, match="Could not parse enhancement response"):
            parser.parse(response)

    def test_extract_json_from_generic_code_block(self):
        """Test extracting JSON from generic code blocks (lines 123-126)."""
        parser = EnhancementParser()

        # Generic code block (without 'json' tag) containing valid JSON
        response = """```
{"sections": ["test"], "test": "content"}
```"""

        enhancement = parser.parse(response)
        assert enhancement["sections"] == ["test"]

    def test_extract_json_no_match_in_code_block(self):
        """Test code block without JSON (line 116 return None path)."""
        parser = EnhancementParser()

        # Code block without JSON content
        response = """```
This is not JSON
Just plain text
```"""

        # Should fall back to other parsing methods
        with pytest.raises(ValueError, match="Could not parse enhancement response"):
            parser.parse(response)

    def test_parse_simple(self):
        """Test parse_simple method for well-formatted responses (line 273)."""
        parser = EnhancementParser()

        response = '{"sections": ["test"], "test": "content"}'
        enhancement = parser.parse_simple(response)

        assert enhancement["sections"] == ["test"]
        assert enhancement["test"] == "content"


# ============================================================================
# APPLIER TESTS - File I/O and Error Handling
# ============================================================================

class TestApplierCoverage:
    """Tests for applier.py uncovered paths."""

    def test_apply_file_not_found(self, tmp_path):
        """Test FileNotFoundError when file doesn't exist (line 42)."""
        applier = EnhancementApplier()

        non_existent = tmp_path / "does-not-exist.md"
        enhancement = {"sections": ["test"], "test": "content"}

        with pytest.raises(FileNotFoundError, match="Agent file not found"):
            applier.apply(non_existent, enhancement)

    def test_apply_path_is_directory(self, tmp_path):
        """Test ValueError when path is a directory (line 45)."""
        applier = EnhancementApplier()

        directory = tmp_path / "test_dir"
        directory.mkdir()
        enhancement = {"sections": ["test"], "test": "content"}

        with pytest.raises(ValueError, match="Path is not a file"):
            applier.apply(directory, enhancement)

    def test_apply_read_permission_error(self, tmp_path):
        """Test PermissionError when file is not readable (line 51)."""
        applier = EnhancementApplier()

        agent_file = tmp_path / "test.md"
        agent_file.write_text("content")
        enhancement = {"sections": ["test"], "test": "content"}

        # Mock safe_read_file to simulate read error
        with patch('applier.safe_read_file', return_value=(False, "Permission denied")):
            with pytest.raises(PermissionError, match="Cannot read agent file"):
                applier.apply(agent_file, enhancement)

    def test_apply_write_permission_error(self, tmp_path):
        """Test PermissionError when file is not writable (line 59)."""
        applier = EnhancementApplier()

        agent_file = tmp_path / "test.md"
        agent_file.write_text("---\nname: test\n---\n\n# Test")
        enhancement = {"sections": ["test"], "test": "## Test\n\nContent"}

        # Mock safe_write_file to simulate write error
        with patch('applier.safe_write_file', return_value=(False, "Permission denied")):
            with pytest.raises(PermissionError, match="Cannot write to agent file"):
                applier.apply(agent_file, enhancement)

    def test_generate_diff_file_not_found(self, tmp_path):
        """Test diff generation when file doesn't exist (line 87-88)."""
        applier = EnhancementApplier()

        non_existent = tmp_path / "does-not-exist.md"
        enhancement = {"sections": ["test"], "test": "content"}

        diff = applier.generate_diff(non_existent, enhancement)
        assert "Error: File not found" in diff

    def test_generate_diff_read_error(self, tmp_path):
        """Test diff generation with read error (lines 90-93)."""
        applier = EnhancementApplier()

        agent_file = tmp_path / "test.md"
        agent_file.write_text("content")
        enhancement = {"sections": ["test"], "test": "content"}

        # Mock read_text to simulate error
        with patch.object(Path, 'read_text', side_effect=PermissionError("Access denied")):
            diff = applier.generate_diff(agent_file, enhancement)
            assert "Error reading file" in diff

    def test_generate_diff_success(self, tmp_path):
        """Test successful diff generation (lines 96-110)."""
        applier = EnhancementApplier()

        agent_file = tmp_path / "test.md"
        original_content = """---
name: test
---

# Test Agent

Existing content.
"""
        agent_file.write_text(original_content)

        enhancement = {
            "sections": ["related_templates"],
            "related_templates": "## Related Templates\n\n- template1.template"
        }

        diff = applier.generate_diff(agent_file, enhancement)

        # Verify diff format
        assert "---" in diff  # From file
        assert "+++" in diff  # To file (enhanced)
        assert "+## Related Templates" in diff

    def test_remove_sections(self, tmp_path):
        """Test remove_sections utility method (lines 254-281)."""
        applier = EnhancementApplier()

        agent_file = tmp_path / "test.md"
        agent_file.write_text("""---
name: test
---

# Test Agent

## Quick Start

Use this agent.

## Related Templates

- template1.template
- template2.template

## Capabilities

Does things.
""")

        # Remove related_templates section
        applier.remove_sections(agent_file, ["related_templates"])

        result = agent_file.read_text()

        # Should have removed the section
        assert "## Related Templates" not in result
        assert "template1.template" not in result
        # But preserved other sections
        assert "## Quick Start" in result
        assert "## Capabilities" in result

    def test_remove_sections_file_not_found(self, tmp_path):
        """Test remove_sections with non-existent file."""
        applier = EnhancementApplier()

        non_existent = tmp_path / "does-not-exist.md"

        with pytest.raises(FileNotFoundError, match="Agent file not found"):
            applier.remove_sections(non_existent, ["test"])

    def test_merge_content_empty_boundaries(self):
        """Test merge with empty boundaries content (line 166)."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent

Some content.
"""

        # Empty boundaries should not be inserted
        enhancement = {
            "sections": ["boundaries"],
            "boundaries": ""
        }

        merged = applier._merge_content(original, enhancement)

        # Boundaries should not be added
        assert "## Boundaries" not in merged

    def test_merge_content_boundaries_no_blank_line_before(self):
        """Test boundaries insertion when previous line is not blank (line 172)."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent
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

        # Should have inserted blank line before boundaries
        lines = merged.split('\n')
        boundaries_idx = None
        for i, line in enumerate(lines):
            if line.strip() == "## Boundaries":
                boundaries_idx = i
                break

        assert boundaries_idx is not None
        # Check that there's blank line before boundaries
        assert lines[boundaries_idx - 1].strip() == ""

    def test_merge_content_fallback_no_blank_line(self):
        """Test fallback append when no blank line at end (line 177-178)."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent
Some content without trailing blank line"""

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

        # Should have added blank line before boundaries
        assert "\n\n## Boundaries" in merged

    def test_merge_content_other_sections_with_content(self):
        """Test appending other sections when content exists (lines 188-198)."""
        applier = EnhancementApplier()

        original = """---
name: test
---

# Test Agent

Content."""

        enhancement = {
            "sections": ["related_templates", "examples"],
            "related_templates": "## Related Templates\n\n- template1.template",
            "examples": "## Code Examples\n\n```python\ncode\n```"
        }

        merged = applier._merge_content(original, enhancement)

        assert "## Related Templates" in merged
        assert "## Code Examples" in merged
        assert "template1.template" in merged


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
