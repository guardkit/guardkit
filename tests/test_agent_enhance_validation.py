"""Unit tests for agent-enhance discovery metadata validation (TASK-ENF-P0-4).

Tests the agent metadata validation feature added in TASK-ENF-P0-4:
- FR1: Validate discovery metadata exists after enhancement
- FR3: Verify agent discoverability post-enhancement
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import importlib.util

# Load agent-enhance module from absolute path
def load_agent_enhance_module():
    """Load agent-enhance module for testing."""
    script_path = Path(__file__).parent.parent / "installer/global/commands/agent-enhance.py"
    spec = importlib.util.spec_from_file_location("agent_enhance", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

agent_enhance_module = load_agent_enhance_module()
validate_discovery_metadata_after_enhancement = agent_enhance_module.validate_discovery_metadata_after_enhancement


@pytest.fixture
def temp_agent_file(tmp_path):
    """Create temporary agent file."""
    agent_file = tmp_path / "test-agent.md"
    return agent_file


class TestValidateDiscoveryMetadataAfterEnhancement:
    """Tests for validate_discovery_metadata_after_enhancement (TASK-ENF-P0-4: FR1, FR3)."""

    def test_validate_metadata_success(self, temp_agent_file):
        """Test validation when agent has complete metadata."""
        # Create agent with valid metadata
        temp_agent_file.write_text("""---
name: test-agent
stack: [python]
phase: implementation
capabilities: [cap1, cap2, cap3]
keywords: [key1, key2, key3]
---

# Test Agent
""")

        # Validate - should not raise any exceptions
        # Success case logs at INFO level which may not be captured
        try:
            validate_discovery_metadata_after_enhancement(temp_agent_file)
            # If we get here, validation passed
            assert True
        except Exception as e:
            pytest.fail(f"Validation failed unexpectedly: {e}")

    def test_validate_metadata_missing_fields(self, temp_agent_file, caplog):
        """Test validation when agent missing required fields."""
        # Create agent with missing metadata
        temp_agent_file.write_text("""---
name: test-agent
phase: implementation
---

# Test Agent
""")

        # Validate
        validate_discovery_metadata_after_enhancement(temp_agent_file)

        # Check log output - warnings should be captured
        assert "Agent metadata incomplete:" in caplog.text
        assert "Missing required field: stack" in caplog.text
        assert "Missing required field: capabilities" in caplog.text
        assert "Missing required field: keywords" in caplog.text

    def test_validate_metadata_unreadable_file(self, tmp_path, caplog):
        """Test validation handles unreadable files gracefully."""
        # File that doesn't exist
        nonexistent = tmp_path / "nonexistent.md"

        # Should not crash
        validate_discovery_metadata_after_enhancement(nonexistent)

        # Check log output includes warning
        assert "Could not read metadata" in caplog.text

    def test_validate_metadata_discovery_unavailable(self, temp_agent_file, caplog):
        """Test validation handles missing agent_discovery module gracefully."""
        # Create agent file
        temp_agent_file.write_text("""---
name: test-agent
---

# Test Agent
""")

        # Mock ImportError for agent_discovery
        with patch('importlib.import_module', side_effect=ImportError("Module not found")):
            # Should not crash
            validate_discovery_metadata_after_enhancement(temp_agent_file)

        # Should silently skip (debug log only)
        # No error output expected (graceful degradation)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
