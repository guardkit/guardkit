"""
Additional validation error tests for complete coverage.

Covers validation error paths in parser.py that weren't hit by other tests.
"""

import pytest
import sys
from pathlib import Path

# Add agent_enhancement module to path
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from parser import EnhancementParser


class TestParserValidationErrors:
    """Tests for parser.py validation error paths."""

    def test_validate_basic_structure_not_dict(self):
        """Test validation fails when enhancement is not a dict (line 141)."""
        parser = EnhancementParser()

        # Parse will return a list instead of dict
        response = '["not", "a", "dict"]'

        with pytest.raises(ValueError, match="Enhancement must be a dictionary"):
            parser.parse(response)

    def test_validate_basic_structure_missing_sections_key(self):
        """Test validation fails when 'sections' key is missing (line 144)."""
        parser = EnhancementParser()

        # Valid JSON but missing 'sections' key
        response = '{"other_key": "value"}'

        with pytest.raises(ValueError, match="Enhancement must contain 'sections' key"):
            parser.parse(response)

    def test_validate_basic_structure_sections_not_list(self):
        """Test validation fails when 'sections' is not a list (line 147)."""
        parser = EnhancementParser()

        # 'sections' is a string instead of list
        response = '{"sections": "not_a_list"}'

        with pytest.raises(ValueError, match="'sections' must be a list"):
            parser.parse(response)

    def test_validate_boundaries_empty_string(self):
        """Test validation fails when boundaries content is empty (line 169)."""
        parser = EnhancementParser()

        # Boundaries section included but empty
        response = '{"sections": ["boundaries"], "boundaries": ""}'

        with pytest.raises(ValueError, match="Boundaries section is empty"):
            parser.parse(response)

    def test_validate_boundaries_whitespace_only(self):
        """Test validation fails when boundaries is only whitespace (line 169)."""
        parser = EnhancementParser()

        # Boundaries with only whitespace
        response = '{"sections": ["boundaries"], "boundaries": "   \\n\\n   "}'

        with pytest.raises(ValueError, match="Boundaries section is empty"):
            parser.parse(response)

    def test_validate_boundaries_missing_always_section(self):
        """Test validation fails when ALWAYS subsection missing (line 173)."""
        parser = EnhancementParser()

        # Missing ALWAYS section
        boundaries_content = """## Boundaries

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

        response = f'{{"sections": ["boundaries"], "boundaries": "{boundaries_content.replace(chr(10), "\\n")}"}}'

        with pytest.raises(ValueError, match="Boundaries section missing '### ALWAYS' subsection"):
            parser.parse(response)

    def test_validate_boundaries_missing_never_section(self):
        """Test validation fails when NEVER subsection missing (line 175)."""
        parser = EnhancementParser()

        # Missing NEVER section
        boundaries_content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
- ✅ Rule 3
- ✅ Rule 4
- ✅ Rule 5

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
- ⚠️ Scenario 3
"""

        response = f'{{"sections": ["boundaries"], "boundaries": "{boundaries_content.replace(chr(10), "\\n")}"}}'

        with pytest.raises(ValueError, match="Boundaries section missing '### NEVER' subsection"):
            parser.parse(response)

    def test_extract_subsection_start_marker_not_found(self):
        """Test _extract_subsection when start marker not found (line 227)."""
        parser = EnhancementParser()

        content = """## Boundaries

### ALWAYS
- ✅ Rule 1

### NEVER
- ❌ Rule 1
"""

        # Try to extract a section that doesn't exist
        result = parser._extract_subsection(content, "### DOES_NOT_EXIST", "### NEVER")
        assert result == ""

    def test_extract_subsection_no_end_marker(self):
        """Test _extract_subsection when end marker is None (line 237)."""
        parser = EnhancementParser()

        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2

### NEVER
- ❌ Rule 1
- ❌ Rule 2

### ASK
- ⚠️ Scenario 1
- ⚠️ Scenario 2
"""

        # Extract ASK section to end (no end marker)
        result = parser._extract_subsection(content, "### ASK", None)
        assert "⚠️ Scenario 1" in result
        assert "⚠️ Scenario 2" in result

    def test_extract_subsection_end_marker_not_found(self):
        """Test _extract_subsection when end marker not found (line 237)."""
        parser = EnhancementParser()

        content = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2
"""

        # Try to extract with end marker that doesn't exist
        result = parser._extract_subsection(content, "### ALWAYS", "### NEVER")
        # Should return from ALWAYS to end of content
        assert "✅ Rule 1" in result
        assert "✅ Rule 2" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
