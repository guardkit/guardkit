"""
TDD RED Phase: Tests for guardkit.knowledge.template_sync

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- Graceful degradation when Graphiti disabled
- Handling missing manifest files
- Template metadata sync (happy path)
- Agent metadata sync
- Rule metadata sync
- Metadata extraction from markdown frontmatter

Coverage Target: >=85%
Test Count: 18+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List, Dict
from pathlib import Path
import json
import tempfile

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.template_sync import (
        sync_template_to_graphiti,
        sync_agent_to_graphiti,
        sync_rule_to_graphiti,
        extract_agent_metadata,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


# ============================================================================
# 1. Graceful Degradation Tests (4 tests)
# ============================================================================

class TestGracefulDegradation:
    """Test graceful degradation when Graphiti is disabled."""

    @pytest.mark.asyncio
    async def test_sync_template_disabled_client(self, tmp_path):
        """Test sync_template_to_graphiti degrades gracefully when client disabled."""
        # Create a minimal template structure
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        # Mock get_graphiti to return disabled client
        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

            # Should return False (not synced) but not raise exception
            assert result is False

            # Should not attempt to add episodes
            mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_template_no_client(self, tmp_path):
        """Test sync_template_to_graphiti handles None client gracefully."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=None):
            result = await sync_template_to_graphiti(template_path)
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_agent_disabled_client(self, tmp_path):
        """Test sync_agent_to_graphiti degrades gracefully when client disabled."""
        agent_path = tmp_path / "test-agent.md"
        agent_path.write_text("---\nname: test\n---\n# Test Agent")

        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_agent_to_graphiti(agent_path, "test-template")
            assert result is False
            mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_rule_disabled_client(self, tmp_path):
        """Test sync_rule_to_graphiti degrades gracefully when client disabled."""
        rule_path = tmp_path / "test-rule.md"
        rule_path.write_text("---\npaths: src/**/*.py\n---\n# Test Rule")

        mock_client = AsyncMock()
        mock_client.enabled = False

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_rule_to_graphiti(rule_path, "test-template")
            assert result is False
            mock_client.add_episode.assert_not_called()


# ============================================================================
# 2. Missing File Handling Tests (3 tests)
# ============================================================================

class TestMissingFileHandling:
    """Test handling of missing files."""

    @pytest.mark.asyncio
    async def test_sync_template_missing_manifest(self, tmp_path):
        """Test sync_template_to_graphiti handles missing manifest gracefully."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        # No manifest.json created

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_agent_missing_file(self, tmp_path):
        """Test sync_agent_to_graphiti handles missing agent file gracefully."""
        agent_path = tmp_path / "nonexistent-agent.md"

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_agent_to_graphiti(agent_path, "test-template")
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_rule_missing_file(self, tmp_path):
        """Test sync_rule_to_graphiti handles missing rule file gracefully."""
        rule_path = tmp_path / "nonexistent-rule.md"

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_rule_to_graphiti(rule_path, "test-template")
            assert result is False


# ============================================================================
# 3. Template Sync Tests (4 tests)
# ============================================================================

class TestTemplateSync:
    """Test template metadata sync to Graphiti."""

    @pytest.mark.asyncio
    async def test_sync_template_with_manifest(self, tmp_path):
        """Test sync_template_to_graphiti syncs template metadata correctly."""
        # Create a complete template structure
        template_path = tmp_path / "fastapi-python"
        template_path.mkdir()

        manifest = {
            "name": "fastapi-python",
            "display_name": "Python FastAPI Backend",
            "description": "Production-ready FastAPI template",
            "language": "Python",
            "frameworks": [
                {"name": "FastAPI", "version": ">=0.104.0", "purpose": "web_framework"}
            ],
            "patterns": ["Dependency Injection", "Repository Pattern"],
            "tags": ["python", "fastapi", "api"],
            "complexity": 7
        }
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

            assert result is True
            mock_client.add_episode.assert_called()

            # Verify episode content
            call_args = mock_client.add_episode.call_args
            assert call_args.kwargs['group_id'] == 'templates'
            assert 'fastapi-python' in call_args.kwargs['name']

    @pytest.mark.asyncio
    async def test_sync_template_includes_agents(self, tmp_path):
        """Test sync_template_to_graphiti also syncs agents in template."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()

        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        # Create agents directory with an agent
        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        agent_content = """---
name: test-specialist
description: Test specialist agent
capabilities:
  - Testing
  - Validation
technologies:
  - pytest
  - Python
---

# Test Specialist

Test content.
"""
        (agents_dir / "test-specialist.md").write_text(agent_content)

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            assert result is True

            # Should have called add_episode at least twice (template + agent)
            assert mock_client.add_episode.call_count >= 2

    @pytest.mark.asyncio
    async def test_sync_template_uses_correct_group_id(self, tmp_path):
        """Test sync_template_to_graphiti uses 'templates' group_id."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_template_to_graphiti(template_path)

            # First call should be for template with 'templates' group_id
            call_args = mock_client.add_episode.call_args_list[0]
            assert call_args.kwargs['group_id'] == 'templates'

    @pytest.mark.asyncio
    async def test_sync_template_episode_body_contains_metadata(self, tmp_path):
        """Test that synced template episode contains key metadata fields."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()

        manifest = {
            "name": "test-template",
            "language": "Python",
            "frameworks": [{"name": "FastAPI", "purpose": "web"}],
            "patterns": ["DI", "Repository"],
            "tags": ["python", "api"]
        }
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        captured_body = None

        async def capture_episode(name, episode_body, group_id, **kwargs):
            nonlocal captured_body
            if group_id == 'templates':
                captured_body = episode_body
            return "episode_id"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = capture_episode

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_template_to_graphiti(template_path)

            # Verify episode body contains expected fields
            assert captured_body is not None
            # episode_body is still a string in graphiti_client.add_episode
            body_data = json.loads(captured_body)
            assert body_data['entity_type'] == 'template'
            assert body_data['name'] == 'test-template'
            assert body_data['language'] == 'Python'


# ============================================================================
# 4. Agent Sync Tests (3 tests)
# ============================================================================

class TestAgentSync:
    """Test agent metadata sync to Graphiti."""

    @pytest.mark.asyncio
    async def test_sync_agent_to_graphiti(self, tmp_path):
        """Test sync_agent_to_graphiti syncs agent metadata correctly."""
        agent_path = tmp_path / "fastapi-specialist.md"
        agent_content = """---
name: fastapi-specialist
description: FastAPI framework specialist for API development
stack: [python, fastapi]
phase: implementation
capabilities:
  - FastAPI router organization
  - Dependency injection patterns
  - Middleware implementation
technologies:
  - FastAPI
  - Python
  - Pydantic
priority: 8
---

# FastAPI Specialist

You are a FastAPI specialist.
"""
        agent_path.write_text(agent_content)

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_agent_to_graphiti(agent_path, "fastapi-python")

            assert result is True
            mock_client.add_episode.assert_called_once()

            call_args = mock_client.add_episode.call_args
            assert call_args.kwargs['group_id'] == 'agents'
            assert 'fastapi-specialist' in call_args.kwargs['name']

    @pytest.mark.asyncio
    async def test_sync_agent_includes_capabilities(self, tmp_path):
        """Test that synced agent includes capabilities in episode body."""
        agent_path = tmp_path / "test-agent.md"
        agent_content = """---
name: test-agent
capabilities:
  - Code review
  - Testing
  - Documentation
---

# Test Agent
"""
        agent_path.write_text(agent_content)

        captured_body = None

        async def capture_episode(name, episode_body, group_id, **kwargs):
            nonlocal captured_body
            captured_body = episode_body
            return "episode_id"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = capture_episode

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_agent_to_graphiti(agent_path, "test-template")

            body_data = json.loads(captured_body)
            assert 'capabilities' in body_data
            assert 'Code review' in body_data['capabilities']

    @pytest.mark.asyncio
    async def test_sync_agent_links_to_template(self, tmp_path):
        """Test that synced agent is linked to its template."""
        agent_path = tmp_path / "test-agent.md"
        agent_content = """---
name: test-agent
description: Test agent
---

# Test Agent
"""
        agent_path.write_text(agent_content)

        captured_body = None

        async def capture_episode(name, episode_body, group_id, **kwargs):
            nonlocal captured_body
            captured_body = episode_body
            return "episode_id"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = capture_episode

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_agent_to_graphiti(agent_path, "my-template")

            body_data = json.loads(captured_body)
            assert body_data['template_id'] == 'my-template'


# ============================================================================
# 5. Rule Sync Tests (2 tests)
# ============================================================================

class TestRuleSync:
    """Test rule metadata sync to Graphiti."""

    @pytest.mark.asyncio
    async def test_sync_rule_to_graphiti(self, tmp_path):
        """Test sync_rule_to_graphiti syncs rule metadata correctly."""
        rule_path = tmp_path / "code-style.md"
        rule_content = """---
paths: src/**/*.py, lib/**/*.py
---

# Python Code Style

Use snake_case for functions and variables.
Use PascalCase for classes.
"""
        rule_path.write_text(rule_content)

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_rule_to_graphiti(rule_path, "fastapi-python")

            assert result is True
            mock_client.add_episode.assert_called_once()

            call_args = mock_client.add_episode.call_args
            assert call_args.kwargs['group_id'] == 'rules'

    @pytest.mark.asyncio
    async def test_sync_rule_includes_path_patterns(self, tmp_path):
        """Test that synced rule includes path patterns in episode body."""
        rule_path = tmp_path / "testing.md"
        rule_content = """---
paths: tests/**/*.py, **/test_*.py
---

# Testing Rules

Write tests for all public functions.
"""
        rule_path.write_text(rule_content)

        captured_body = None

        async def capture_episode(name, episode_body, group_id, **kwargs):
            nonlocal captured_body
            captured_body = episode_body
            return "episode_id"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = capture_episode

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_rule_to_graphiti(rule_path, "test-template")

            body_data = json.loads(captured_body)
            assert 'path_patterns' in body_data
            assert 'tests/**/*.py' in body_data['path_patterns']


# ============================================================================
# 6. Metadata Extraction Tests (4 tests)
# ============================================================================

class TestMetadataExtraction:
    """Test metadata extraction from markdown frontmatter."""

    def test_extract_agent_metadata_basic(self):
        """Test extracting basic agent metadata from frontmatter."""
        content = """---
name: test-agent
description: A test agent
priority: 5
---

# Test Agent

Body content here.
"""
        metadata = extract_agent_metadata(content)

        assert metadata['name'] == 'test-agent'
        assert metadata['description'] == 'A test agent'
        assert metadata['priority'] == 5

    def test_extract_agent_metadata_with_lists(self):
        """Test extracting list fields from frontmatter."""
        content = """---
name: specialist-agent
capabilities:
  - Code review
  - Testing
  - Documentation
technologies:
  - Python
  - pytest
stack: [python, fastapi]
---

# Specialist Agent
"""
        metadata = extract_agent_metadata(content)

        assert 'capabilities' in metadata
        assert len(metadata['capabilities']) == 3
        assert 'Code review' in metadata['capabilities']

        assert 'technologies' in metadata
        assert 'Python' in metadata['technologies']

        assert 'stack' in metadata
        assert 'python' in metadata['stack']

    def test_extract_agent_metadata_empty_content(self):
        """Test extracting metadata from content without frontmatter."""
        content = """# No Frontmatter

Just plain content.
"""
        metadata = extract_agent_metadata(content)
        assert metadata == {}

    def test_extract_agent_metadata_malformed_frontmatter(self):
        """Test handling of malformed frontmatter."""
        content = """---
name: test
invalid yaml: [unclosed
---

# Content
"""
        # Should not raise exception, return empty or partial
        metadata = extract_agent_metadata(content)
        # At minimum, should not crash
        assert isinstance(metadata, dict)


# ============================================================================
# 7. Error Handling Tests (2 tests)
# ============================================================================

class TestErrorHandling:
    """Test error handling in sync operations."""

    @pytest.mark.asyncio
    async def test_sync_template_handles_add_episode_failure(self, tmp_path):
        """Test sync_template_to_graphiti handles add_episode failure gracefully."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("API Error"))

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            # Should handle exception gracefully
            result = await sync_template_to_graphiti(template_path)
            # May return False due to error, but should not raise
            assert result is False or result is True

    @pytest.mark.asyncio
    async def test_sync_template_handles_invalid_json_manifest(self, tmp_path):
        """Test sync_template_to_graphiti handles invalid JSON in manifest."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        (template_path / "manifest.json").write_text("{ invalid json }")

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_agent_handles_read_failure(self, tmp_path):
        """Test sync_agent_to_graphiti handles file read errors."""
        agent_path = tmp_path / "test-agent.md"
        # Create file then make it unreadable (skip if permissions not supported)
        agent_path.write_text("---\nname: test\n---\n")

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            # Patch Path.read_text to raise an exception
            with patch.object(Path, 'read_text', side_effect=PermissionError("Cannot read")):
                result = await sync_agent_to_graphiti(agent_path, "test-template")
                assert result is False

    @pytest.mark.asyncio
    async def test_sync_agent_no_metadata(self, tmp_path):
        """Test sync_agent_to_graphiti handles agent with no metadata."""
        agent_path = tmp_path / "empty-agent.md"
        agent_path.write_text("# Just content\n\nNo frontmatter here.")

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_agent_to_graphiti(agent_path, "test-template")
            assert result is False
            mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_agent_add_episode_failure(self, tmp_path):
        """Test sync_agent_to_graphiti handles add_episode failure."""
        agent_path = tmp_path / "test-agent.md"
        agent_path.write_text("---\nname: test\ndescription: Test\n---\n# Test")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("API Error"))

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_agent_to_graphiti(agent_path, "test-template")
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_rule_no_client(self, tmp_path):
        """Test sync_rule_to_graphiti handles None client."""
        rule_path = tmp_path / "test-rule.md"
        rule_path.write_text("---\npaths: src/**\n---\n# Rule")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=None):
            result = await sync_rule_to_graphiti(rule_path, "test-template")
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_rule_handles_read_failure(self, tmp_path):
        """Test sync_rule_to_graphiti handles file read errors."""
        rule_path = tmp_path / "test-rule.md"
        rule_path.write_text("---\npaths: src/**\n---\n")

        mock_client = AsyncMock()
        mock_client.enabled = True

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            with patch.object(Path, 'read_text', side_effect=IOError("Cannot read")):
                result = await sync_rule_to_graphiti(rule_path, "test-template")
                assert result is False

    @pytest.mark.asyncio
    async def test_sync_rule_add_episode_failure(self, tmp_path):
        """Test sync_rule_to_graphiti handles add_episode failure."""
        rule_path = tmp_path / "test-rule.md"
        rule_path.write_text("---\npaths: src/**\n---\n# Rule Content")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("API Error"))

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_rule_to_graphiti(rule_path, "test-template")
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_rule_with_list_paths(self, tmp_path):
        """Test sync_rule_to_graphiti handles paths as list."""
        rule_path = tmp_path / "test-rule.md"
        rule_content = """---
paths:
  - src/**/*.py
  - lib/**/*.py
---

# Rule With List Paths

Content here.
"""
        rule_path.write_text(rule_content)

        captured_body = None

        async def capture_episode(name, episode_body, group_id, **kwargs):
            nonlocal captured_body
            captured_body = episode_body
            return "episode_id"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = capture_episode

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_rule_to_graphiti(rule_path, "test-template")
            assert result is True
            body_data = json.loads(captured_body)
            assert 'src/**/*.py' in body_data['path_patterns']

    @pytest.mark.asyncio
    async def test_sync_template_skips_ext_agents(self, tmp_path):
        """Test sync_template_to_graphiti skips extended agent files."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()

        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent-ext.md").write_text("---\nname: extended\n---\n# Extended")
        (agents_dir / "main-agent.md").write_text("---\nname: main\n---\n# Main Agent")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            assert result is True

            # Check that extended agent was not synced
            call_names = [call.kwargs.get('name', '') for call in mock_client.add_episode.call_args_list]
            assert not any('extended' in name for name in call_names)

    @pytest.mark.asyncio
    async def test_sync_template_includes_rules(self, tmp_path):
        """Test sync_template_to_graphiti syncs rules in .claude/rules/."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()

        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        rules_dir = template_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "code-style.md").write_text("---\npaths: src/**\n---\n# Code Style")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            assert result is True

            # Check that rule was synced (should have at least 2 calls: template + rule)
            assert mock_client.add_episode.call_count >= 2

    @pytest.mark.asyncio
    async def test_sync_template_handles_agent_sync_failure(self, tmp_path):
        """Test sync_template_to_graphiti continues after agent sync failure."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()

        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        # Create agent with invalid content to cause parsing failure
        (agents_dir / "bad-agent.md").write_text("---\n invalid: [yaml\n---\n")
        (agents_dir / "good-agent.md").write_text("---\nname: good\n---\n# Good")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            # Should succeed overall even if one agent fails
            assert result is True


# ============================================================================
# 8. Integration Tests (2 tests - marked for selective running)
# ============================================================================

@pytest.mark.integration
class TestTemplateSyncIntegration:
    """
    Integration tests for template sync with real GraphitiClient.

    These tests require Graphiti to be running.
    Mark with @pytest.mark.integration to run selectively.
    """

    @pytest.mark.asyncio
    async def test_full_template_sync_workflow(self, tmp_path):
        """Test complete template sync workflow with real Graphiti instance."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

        # Create test template
        template_path = tmp_path / "integration-test-template"
        template_path.mkdir()
        manifest = {
            "name": "integration-test-template",
            "language": "Python",
            "frameworks": [],
            "patterns": [],
            "tags": ["test"]
        }
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=client):
            result = await sync_template_to_graphiti(template_path)
            assert result is True

    @pytest.mark.asyncio
    async def test_agent_sync_workflow(self, tmp_path):
        """Test agent sync workflow with real Graphiti instance."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

        # Create test agent
        agent_path = tmp_path / "integration-test-agent.md"
        agent_content = """---
name: integration-test-agent
description: Test agent for integration
capabilities:
  - Testing
---

# Integration Test Agent
"""
        agent_path.write_text(agent_content)

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=client):
            result = await sync_agent_to_graphiti(agent_path, "test-template")
            assert result is True
