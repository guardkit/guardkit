"""
Integration tests for TASK-BDRY-316A - Boundary workaround triggering.

Tests the complete flow:
1. Parser raises ValueError when boundaries missing
2. Enhancer catches the error
3. Enhancer triggers _ensure_boundaries() workaround
4. Enhancement proceeds with generic boundaries
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add agent_enhancement module to path
lib_path = Path(__file__).parent.parent.parent.parent / 'installer' / 'global' / 'lib' / 'agent_enhancement'
sys.path.insert(0, str(lib_path))

from enhancer import SingleAgentEnhancer
from parser import EnhancementParser


class TestBoundaryWorkaroundIntegration:
    """Integration tests for boundary workaround flow."""

    def test_workaround_triggered_when_ai_omits_boundaries(self):
        """
        Test complete flow when AI omits boundaries.

        Flow:
        1. Mock AI returns response without boundaries
        2. Parser._validate_basic_structure() raises ValueError
        3. Enhancer catches ValueError
        4. Enhancer adds generic boundaries
        5. Enhancement succeeds with boundaries present
        """
        # Setup
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=True)

        # Mock agent metadata
        agent_metadata = {
            "name": "test-agent",
            "description": "Test agent for validation"
        }

        # Mock AI response WITHOUT boundaries (schema violation)
        ai_response_without_boundaries = """{
            "sections": ["related_templates", "examples"],
            "related_templates": "Some template content",
            "examples": "Some example content"
        }"""

        # Mock the AI client to return response without boundaries
        with patch.object(enhancer, '_call_ai_api') as mock_ai:
            mock_ai.return_value = ai_response_without_boundaries

            # Mock template files
            mock_templates = [Path("/fake/template.md")]
            mock_template_dir = Path("/fake")

            # Execute enhancement (should trigger workaround)
            result = enhancer._ai_enhancement(
                agent_metadata,
                mock_templates,
                mock_template_dir
            )

            # Verify boundaries were added by workaround
            assert "boundaries" in result
            assert "boundaries" in result["sections"]
            assert "## Boundaries" in result["boundaries"]
            assert "### ALWAYS" in result["boundaries"]
            assert "### NEVER" in result["boundaries"]
            assert "### ASK" in result["boundaries"]

    def test_no_workaround_when_boundaries_present(self):
        """
        Test that workaround is NOT triggered when boundaries are present.

        Flow:
        1. Mock AI returns response WITH valid boundaries
        2. Parser validates successfully
        3. No workaround triggered
        4. Enhancement uses AI-generated boundaries
        """
        # Setup
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=True)

        # Mock agent metadata
        agent_metadata = {
            "name": "test-agent",
            "description": "Test agent for validation"
        }

        # Mock AI response WITH valid boundaries
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

        ai_response_with_boundaries = f"""{{
            "sections": ["related_templates", "boundaries", "examples"],
            "related_templates": "Some template content",
            "boundaries": {repr(valid_boundaries)},
            "examples": "Some example content"
        }}"""

        # Mock the AI client to return response with boundaries
        with patch.object(enhancer, '_call_ai_api') as mock_ai:
            mock_ai.return_value = ai_response_with_boundaries

            # Mock template files
            mock_templates = [Path("/fake/template.md")]
            mock_template_dir = Path("/fake")

            # Execute enhancement (should NOT trigger workaround)
            result = enhancer._ai_enhancement(
                agent_metadata,
                mock_templates,
                mock_template_dir
            )

            # Verify AI-generated boundaries were used
            assert "boundaries" in result
            assert "boundaries" in result["sections"]
            assert result["boundaries"] == valid_boundaries

    def test_parser_validation_catches_missing_boundaries(self):
        """
        Test that parser validation detects missing boundaries.

        This is a unit-level check of the parser validation,
        separate from the full enhancer flow.
        """
        parser = EnhancementParser()

        # Response without boundaries
        response = """{
            "sections": ["related_templates", "examples"],
            "related_templates": "Content",
            "examples": "Content"
        }"""

        # Parser should raise ValueError
        with pytest.raises(ValueError, match="missing required 'boundaries' field"):
            parser.parse(response)

    def test_workaround_adds_all_boundary_sections(self):
        """
        Test that workaround-generated boundaries contain all required sections.

        Ensures generic boundaries meet the same quality standards:
        - ALWAYS subsection (5-7 rules)
        - NEVER subsection (5-7 rules)
        - ASK subsection (3-5 scenarios)
        """
        # Setup
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=True)

        # Mock agent metadata
        agent_metadata = {
            "name": "test-agent",
            "description": "Test agent for validation"
        }

        # Mock AI response without boundaries
        ai_response = """{
            "sections": ["related_templates"],
            "related_templates": "Content"
        }"""

        # Mock the AI client
        with patch.object(enhancer, '_call_ai_api') as mock_ai:
            mock_ai.return_value = ai_response

            # Mock template files
            mock_templates = [Path("/fake/template.md")]
            mock_template_dir = Path("/fake")

            # Execute enhancement
            result = enhancer._ai_enhancement(
                agent_metadata,
                mock_templates,
                mock_template_dir
            )

            # Verify workaround-generated boundaries structure
            boundaries = result["boundaries"]

            # Check all required subsections present
            assert "### ALWAYS" in boundaries
            assert "### NEVER" in boundaries
            assert "### ASK" in boundaries

            # Check emoji prefixes present
            assert "✅" in boundaries  # ALWAYS rules
            assert "❌" in boundaries  # NEVER rules
            assert "⚠️" in boundaries  # ASK scenarios

    def test_workaround_logging(self, caplog):
        """
        Test that workaround triggers appropriate logging.

        Verifies that when boundaries are missing:
        - Warning logged about schema violation
        - Info logged about workaround being triggered
        - Info logged about workaround success
        """
        import logging
        caplog.set_level(logging.INFO)

        # Setup
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=True)

        # Mock agent metadata
        agent_metadata = {
            "name": "test-agent",
            "description": "Test agent"
        }

        # Mock AI response without boundaries
        ai_response = """{
            "sections": ["related_templates"],
            "related_templates": "Content"
        }"""

        # Mock the AI client
        with patch.object(enhancer, '_call_ai_api') as mock_ai:
            mock_ai.return_value = ai_response

            # Mock template files
            mock_templates = [Path("/fake/template.md")]
            mock_template_dir = Path("/fake")

            # Execute enhancement
            enhancer._ai_enhancement(
                agent_metadata,
                mock_templates,
                mock_template_dir
            )

            # Verify logging messages
            log_messages = [record.message for record in caplog.records]

            # Check for schema violation warning
            assert any("schema violation" in msg.lower() for msg in log_messages)

            # Check for workaround trigger info
            assert any("triggering workaround" in msg.lower() for msg in log_messages)

            # Check for workaround success info
            assert any("workaround applied" in msg.lower() for msg in log_messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
