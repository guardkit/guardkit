"""
Unit tests for TASK-BDRY-316A - Schema validation enforcement for boundaries.

Tests the parser's enforcement of JSON schema requirement that boundaries
are REQUIRED in AI responses. When AI omits boundaries, parser should raise
ValueError to trigger the workaround in enhancer.py.
"""

import pytest
import sys
from pathlib import Path

# Add agent_enhancement module to path
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from parser import EnhancementParser


class TestBoundarySchemaValidation:
    """Tests for TASK-BDRY-316A - Boundary schema enforcement."""

    def test_boundaries_completely_omitted(self):
        """
        Test Case 1: AI omits boundaries entirely (schema violation).

        Expected behavior:
        - Parser raises ValueError with "missing required 'boundaries' field"
        - This triggers workaround in enhancer._ensure_boundaries()
        - Workaround adds generic boundaries
        """
        parser = EnhancementParser()

        # AI response without boundaries at all
        response = """{
            "sections": ["related_templates", "examples"],
            "related_templates": "Some content",
            "examples": "Example content"
        }"""

        with pytest.raises(ValueError, match="missing required 'boundaries' field"):
            parser.parse(response)

    def test_boundaries_in_sections_but_field_missing(self):
        """
        Test Case 2: AI includes boundaries in sections list but not the field.

        Expected behavior:
        - Parser raises ValueError about field being missing
        - This is a different error than Case 1 (more specific)
        """
        parser = EnhancementParser()

        # AI response with boundaries in sections list but missing field
        response = """{
            "sections": ["related_templates", "boundaries", "examples"],
            "related_templates": "Some content",
            "examples": "Example content"
        }"""

        with pytest.raises(ValueError, match="'boundaries' field is missing"):
            parser.parse(response)

    def test_valid_boundaries(self):
        """
        Test Case 3: AI includes valid boundaries (should pass).

        Expected behavior:
        - Parser accepts the response
        - No ValueError raised
        - Boundaries content validated for format
        """
        parser = EnhancementParser()

        # AI response with valid boundaries - use proper JSON formatting
        import json

        valid_boundaries = """## Boundaries

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

        response_dict = {
            "sections": ["related_templates", "boundaries", "examples"],
            "related_templates": "Some content",
            "boundaries": valid_boundaries,
            "examples": "Example content"
        }

        response = json.dumps(response_dict)

        # Should not raise any exception
        result = parser.parse(response)
        assert result is not None
        assert "boundaries" in result
        assert "boundaries" in result["sections"]

    def test_malformed_boundaries(self):
        """
        Test Case 4: AI includes malformed boundaries (format validation fails).

        Expected behavior:
        - Parser raises ValueError from _validate_boundaries()
        - Error indicates format issues (missing subsections, wrong counts, etc.)
        """
        parser = EnhancementParser()

        # AI response with malformed boundaries (missing NEVER section)
        import json

        malformed_boundaries = """## Boundaries

### ALWAYS
- ✅ Rule 1
- ✅ Rule 2

### ASK
- ⚠️ Scenario 1
"""

        response_dict = {
            "sections": ["related_templates", "boundaries", "examples"],
            "related_templates": "Some content",
            "boundaries": malformed_boundaries,
            "examples": "Example content"
        }

        response = json.dumps(response_dict)

        with pytest.raises(ValueError, match="Boundaries section missing '### NEVER' subsection"):
            parser.parse(response)

    def test_boundaries_only_in_sections(self):
        """
        Test Case 5: Boundaries only in sections list, not as field (partial omission).

        This is a variation of Case 2 - helps verify the validation logic.
        """
        parser = EnhancementParser()

        response = """{
            "sections": ["boundaries"],
            "other_field": "content"
        }"""

        with pytest.raises(ValueError, match="'boundaries' field is missing"):
            parser.parse(response)

    def test_boundaries_only_as_field(self):
        """
        Test Case 6: Boundaries field exists but not in sections list.

        Expected behavior:
        - Parser raises ValueError about schema violation
        - Both must be present for valid response
        """
        parser = EnhancementParser()

        import json

        valid_boundaries = """## Boundaries

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

        response_dict = {
            "sections": ["related_templates"],
            "related_templates": "Some content",
            "boundaries": valid_boundaries
        }

        response = json.dumps(response_dict)

        with pytest.raises(ValueError, match="missing required 'boundaries' field"):
            parser.parse(response)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
