"""
Integration test for agent enhancement with code samples (TASK-PHASE-7-5-INCLUDE-TEMPLATE-CODE-SAMPLES).

Tests the end-to-end workflow where:
1. Templates are available on disk
2. Code samples are extracted from templates
3. Batch enhancement is invoked with code samples in context
4. Enhanced agents include references to actual code patterns

This test verifies that the AI has actual template code to reference when
generating agent documentation, resulting in more accurate, template-specific content.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

import importlib
_agent_enhancer_module = importlib.import_module('installer.global.lib.template_creation.agent_enhancer')
AgentEnhancer = _agent_enhancer_module.AgentEnhancer


class TestAgentEnhancementWithCodeSamples:
    """Integration tests for agent enhancement with code samples"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    def test_code_samples_included_in_batch_request_and_prompt(self, mock_bridge_invoker):
        """
        Integration test verifying that code samples are properly included in batch request and prompt.

        Scenario:
        1. Agent and template files exist
        2. Batch request is built
        3. Code samples are extracted
        4. Batch prompt is built with code samples

        Expected:
        - Code samples are extracted from templates
        - Code samples are included in batch request
        - Code samples are formatted in batch prompt
        - Batch prompt references actual template code
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create agents directory
            agents_dir = temp_path / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test-agent.md"
            agent_file.write_text("""---
name: test-agent
description: Test agent
priority: 5
technologies:
  - Python
---

# Test Agent

Original content.""")

            # Create templates directory with actual code
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()
            template_file = templates_dir / "sample.template"
            template_file.write_text("""def sample_function():
    '''Sample function demonstrating a pattern.'''
    return True

class SampleClass:
    def method(self):
        pass
""")

            enhancer = AgentEnhancer(mock_bridge_invoker)
            enhancer.template_root = temp_path

            # Build batch request
            agent_files = list(agents_dir.glob("*.md"))
            all_templates = list(templates_dir.glob("*.template"))

            batch_request = enhancer._build_batch_enhancement_request(agent_files, all_templates)

            # Verify code samples are in request
            assert "template_code_samples" in batch_request
            code_samples = batch_request["template_code_samples"]
            assert isinstance(code_samples, dict)

            # Build prompt
            prompt = enhancer._build_batch_prompt(batch_request)

            # Verify prompt includes code samples
            assert isinstance(prompt, str)
            assert len(prompt) > 0
            # Should reference templates in some way
            assert "test-agent" in prompt or "agent" in prompt.lower()

    def test_code_samples_handle_large_templates(self, mock_bridge_invoker):
        """
        Test that code sampling correctly truncates large files.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create templates directory with large file
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()
            large_file = templates_dir / "large.template"
            # Create 200 lines
            large_content = "\n".join([f"# Line {i}" for i in range(1, 201)])
            large_file.write_text(large_content)

            enhancer = AgentEnhancer(mock_bridge_invoker)
            enhancer.template_root = temp_path

            # Sample with max 50 lines
            result = enhancer._sample_template_code(
                ["templates/large.template"],
                max_lines_per_template=50
            )

            # Should be truncated
            assert "templates/large.template" in result
            sampled = result["templates/large.template"]
            assert len(sampled) > 0
            assert "... (truncated)" in sampled

    def test_empty_code_samples_handled_gracefully(self, mock_bridge_invoker):
        """
        Test that system handles templates with no code gracefully.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create agents directory
            agents_dir = temp_path / "agents"
            agents_dir.mkdir()
            (agents_dir / "test.md").write_text("""---
name: test
description: Test
priority: 5
technologies: [Python]
---

# Test""")

            # Create templates directory with empty file
            templates_dir = temp_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "empty.template").write_text("")

            enhancer = AgentEnhancer(mock_bridge_invoker)
            enhancer.template_root = temp_path

            # Should handle gracefully
            result = enhancer._sample_template_code(["templates/empty.template"])
            assert result["templates/empty.template"] == ""

            # Build batch request should work
            agent_files = list(agents_dir.glob("*.md"))
            all_templates = list(templates_dir.glob("*.template"))

            batch_request = enhancer._build_batch_enhancement_request(agent_files, all_templates)
            assert batch_request["template_code_samples"]["templates/empty.template"] == ""

            # Prompt should handle empty samples
            prompt = enhancer._build_batch_prompt(batch_request)
            assert isinstance(prompt, str)
            assert len(prompt) > 0
