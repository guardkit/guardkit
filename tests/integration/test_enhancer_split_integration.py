"""
Integration Tests for Enhancer Split Output

TASK-PD-003: Integration tests for full enhancement workflow with split output
"""

import pytest
from pathlib import Path
import sys
import os

# Add lib directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../installer/core/lib/agent_enhancement'))

from enhancer import SingleAgentEnhancer


@pytest.fixture
def sample_agent_file(tmp_path):
    """Create a sample agent file for testing."""
    agent_file = tmp_path / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent for integration testing
stack: [python]
phase: implementation
priority: 5
---

# Test Agent

This is a test agent for integration testing.
""")
    return agent_file


@pytest.fixture
def sample_template_dir(tmp_path):
    """Create a sample template directory."""
    template_dir = tmp_path / "template"
    template_dir.mkdir()

    # Create templates subdirectory
    templates_subdir = template_dir / "templates"
    templates_subdir.mkdir()

    # Create a sample template file
    template_file = templates_subdir / "sample.template"
    template_file.write_text("""# Sample Template

This is a sample template for testing.

```python
def example():
    pass
```
""")

    return template_dir


class TestEnhancerSplitIntegration:
    """Integration tests for enhancer with split output."""

    def test_full_enhancement_with_split_output(self, sample_agent_file, sample_template_dir):
        """Test complete enhancement workflow with split output."""
        enhancer = SingleAgentEnhancer(strategy="static", verbose=False)

        result = enhancer.enhance(
            sample_agent_file,
            sample_template_dir,
            split_output=True
        )

        # Verify success
        assert result.success is True
        assert result.agent_name == "test-agent"
        assert result.split_output is True

        # Verify file paths
        assert result.core_file is not None
        assert result.extended_file is not None

        # Verify files property
        assert len(result.files) == 2

        # Verify files exist
        assert result.core_file.exists()
        # Note: Extended file may or may not exist depending on whether
        # there are extended sections in the enhancement

    def test_full_enhancement_with_single_file(self, sample_agent_file, sample_template_dir):
        """Test complete enhancement workflow with single-file output."""
        enhancer = SingleAgentEnhancer(strategy="static", verbose=False)

        result = enhancer.enhance(
            sample_agent_file,
            sample_template_dir,
            split_output=False
        )

        # Verify success
        assert result.success is True
        assert result.agent_name == "test-agent"
        assert result.split_output is False

        # Verify file paths
        assert result.core_file is not None
        assert result.extended_file is None

        # Verify files property
        assert len(result.files) == 1

        # Verify file exists
        assert result.core_file.exists()

    def test_enhancement_with_ai_strategy_fallback(self, sample_agent_file, sample_template_dir):
        """Test enhancement with hybrid strategy (AI with static fallback)."""
        # Hybrid strategy will try AI first, then fall back to static
        enhancer = SingleAgentEnhancer(strategy="hybrid", verbose=False)

        result = enhancer.enhance(
            sample_agent_file,
            sample_template_dir,
            split_output=True
        )

        # Verify success (should work via static fallback)
        assert result.success is True
        assert result.strategy_used == "hybrid"
        assert result.split_output is True

    def test_enhancement_preserves_agent_metadata(self, sample_agent_file, sample_template_dir):
        """Test that enhancement preserves agent frontmatter metadata."""
        enhancer = SingleAgentEnhancer(strategy="static", verbose=False)

        # Read original content
        original_content = sample_agent_file.read_text()
        assert "name: test-agent" in original_content

        result = enhancer.enhance(
            sample_agent_file,
            sample_template_dir,
            split_output=False
        )

        # Verify enhancement succeeded
        assert result.success is True

        # Verify original metadata is preserved
        enhanced_content = result.core_file.read_text()
        assert "name: test-agent" in enhanced_content
        assert "description: Test agent for integration testing" in enhanced_content

    def test_enhancement_generates_diff(self, sample_agent_file, sample_template_dir):
        """Test that enhancement generates a useful diff."""
        enhancer = SingleAgentEnhancer(strategy="static", verbose=False)

        result = enhancer.enhance(
            sample_agent_file,
            sample_template_dir,
            split_output=True
        )

        # Verify diff is generated
        assert result.success is True
        assert result.diff is not None
        assert len(result.diff) > 0
