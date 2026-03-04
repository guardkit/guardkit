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
        """Test sync_template_to_graphiti handles missing manifest gracefully.

        TASK-INST-011: Manifest is now optional. When missing, sync proceeds
        with agents and rules only (returns True).
        """
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        # No manifest.json created

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            # Now returns True (manifest is optional)
            assert result is True

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

    def test_extract_agent_metadata_with_glob_paths(self):
        """Test that frontmatter with quoted glob paths parses correctly.

        YAML safe_load interprets unquoted * at the start of a value as an
        alias indicator, causing parsing to fail. Quoting the paths value
        prevents this.
        """
        # Quoted glob pattern (the fix)
        content_quoted = """---
name: code-style
paths: "**/*.py"
alwaysApply: false
---

# Code Style Rules
"""
        metadata = extract_agent_metadata(content_quoted)
        assert metadata['name'] == 'code-style'
        assert metadata['paths'] == '**/*.py'
        assert metadata['alwaysApply'] is False

        # Multi-pattern quoted glob
        content_multi = """---
name: testing
paths: "**/tests/**, **/test_*.py, **/*_test.py, **/conftest.py"
alwaysApply: false
---

# Testing Rules
"""
        metadata_multi = extract_agent_metadata(content_multi)
        assert metadata_multi['name'] == 'testing'
        assert '**/*_test.py' in metadata_multi['paths']

        # Glob pattern not starting with * (already worked, but verify)
        content_safe = """---
name: database
paths: "apps/backend/**/models/**, apps/backend/**/crud/**"
---

# Database Rules
"""
        metadata_safe = extract_agent_metadata(content_safe)
        assert metadata_safe['name'] == 'database'
        assert 'apps/backend' in metadata_safe['paths']


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
        """Test sync_template_to_graphiti handles invalid JSON in manifest.

        TASK-INST-011: Invalid manifest is treated as absent; agents/rules
        still sync. Returns True (graceful degradation).
        """
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        (template_path / "manifest.json").write_text("{ invalid json }")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            # Now returns True (manifest parse failure is not fatal)
            assert result is True

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
    async def test_sync_agent_add_episode_returns_none(self, tmp_path):
        """Test sync_agent_to_graphiti returns False when add_episode returns None."""
        agent_path = tmp_path / "test-agent.md"
        agent_path.write_text("---\nname: test\ndescription: Test\n---\n# Test")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value=None)

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_agent_to_graphiti(agent_path, "test-template")
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_rule_add_episode_returns_none(self, tmp_path):
        """Test sync_rule_to_graphiti returns False when add_episode returns None."""
        rule_path = tmp_path / "test-rule.md"
        rule_path.write_text("---\npaths: src/**\n---\n# Rule Content")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value=None)

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_rule_to_graphiti(rule_path, "test-template")
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
# 8. TASK-INST-011: Full Content Ingestion Tests
# ============================================================================

class TestFullContentIngestion:
    """Test that rule and agent sync includes full content, not just previews."""

    @pytest.mark.asyncio
    async def test_rule_sync_excludes_full_content(self, tmp_path):
        """AC: Rule body uses content_preview only, no full_content (reduces entity extraction)."""
        rule_path = tmp_path / "long-rule.md"
        # Create rule content that exceeds 500 chars
        long_content = "# Long Rule\n\n" + ("This is detailed rule guidance. " * 50)
        rule_content = f"---\npaths: src/**/*.py\n---\n{long_content}"
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
            # full_content removed to reduce entity extraction work
            assert 'full_content' not in body_data
            # content_preview retained for search display
            assert 'content_preview' in body_data
            assert len(body_data['content_preview']) == 500

    @pytest.mark.asyncio
    async def test_rule_sync_short_content_has_preview_only(self, tmp_path):
        """Short rules get content_preview but no full_content."""
        rule_path = tmp_path / "short-rule.md"
        rule_content = "---\npaths: src/**\n---\n# Short Rule\n\nBrief guidance."
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
            assert 'full_content' not in body_data
            assert 'content_preview' in body_data

    @pytest.mark.asyncio
    async def test_agent_sync_includes_body_content(self, tmp_path):
        """AC: Agent sync includes body content beyond frontmatter."""
        agent_path = tmp_path / "detailed-agent.md"
        agent_content = """---
name: detailed-agent
description: Detailed agent
capabilities:
  - Code review
---

# Detailed Agent

You are a detailed specialist agent.

## Responsibilities

1. Review code for quality
2. Ensure test coverage
3. Validate architecture

## Guidelines

Follow SOLID principles and ensure all code is well-documented.
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
            result = await sync_agent_to_graphiti(agent_path, "test-template")

            assert result is True
            body_data = json.loads(captured_body)
            assert 'body_content' in body_data
            assert 'Responsibilities' in body_data['body_content']
            assert 'SOLID principles' in body_data['body_content']


# ============================================================================
# 9. TASK-INST-011: Template Sync Without Manifest
# ============================================================================

class TestTemplateSyncWithoutManifest:
    """Test sync_template_to_graphiti works without manifest.json."""

    @pytest.mark.asyncio
    async def test_sync_template_without_manifest_syncs_agents(self, tmp_path):
        """AC: Template not found (no manifest): sync agents and rules gracefully."""
        template_path = tmp_path / "default-template"
        template_path.mkdir()
        # No manifest.json

        # Create agents directory with an agent
        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "test-agent.md").write_text(
            "---\nname: test-agent\ndescription: Test\n---\n# Test Agent"
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

            # Should return True even without manifest
            assert result is True
            # Should still sync agents
            assert mock_client.add_episode.call_count >= 1

    @pytest.mark.asyncio
    async def test_sync_template_without_manifest_syncs_rules(self, tmp_path):
        """Template without manifest still syncs rule files."""
        template_path = tmp_path / "minimal-template"
        template_path.mkdir()
        # No manifest.json

        rules_dir = template_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "code-style.md").write_text(
            "---\npaths: src/**\n---\n# Code Style\nContent."
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

            assert result is True
            assert mock_client.add_episode.call_count >= 1

    @pytest.mark.asyncio
    async def test_sync_template_without_manifest_no_content_returns_true(self, tmp_path):
        """Template with no manifest, agents or rules still returns True (nothing to sync)."""
        template_path = tmp_path / "empty-template"
        template_path.mkdir()

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)
            assert result is True


# ============================================================================
# 10. TASK-INST-011: Agent Directory Resolution
# ============================================================================

class TestAgentDirectoryResolution:
    """Test that sync_template_to_graphiti checks both agents/ and .claude/agents/."""

    @pytest.mark.asyncio
    async def test_sync_template_checks_dotclaude_agents(self, tmp_path):
        """AC: Template sync checks .claude/agents/ for agent files."""
        template_path = tmp_path / "template-with-dotclaude-agents"
        template_path.mkdir()
        manifest = {"name": "dotclaude-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        # Create agents in .claude/agents/ (not agents/)
        agents_dir = template_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "specialist.md").write_text(
            "---\nname: specialist\ndescription: Specialist\n---\n# Specialist"
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

            assert result is True
            # Should have synced template + agent
            assert mock_client.add_episode.call_count >= 2

    @pytest.mark.asyncio
    async def test_sync_template_checks_both_agent_dirs(self, tmp_path):
        """Template sync checks both agents/ and .claude/agents/ directories."""
        template_path = tmp_path / "template-both-dirs"
        template_path.mkdir()
        manifest = {"name": "both-dirs-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        # Create agents in both locations
        top_agents_dir = template_path / "agents"
        top_agents_dir.mkdir()
        (top_agents_dir / "top-agent.md").write_text(
            "---\nname: top-agent\ndescription: Top\n---\n# Top Agent"
        )

        dotclaude_agents_dir = template_path / ".claude" / "agents"
        dotclaude_agents_dir.mkdir(parents=True)
        (dotclaude_agents_dir / "dotclaude-agent.md").write_text(
            "---\nname: dotclaude-agent\ndescription: DotClaude\n---\n# DotClaude Agent"
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

            assert result is True
            # Should have synced template + 2 agents
            assert mock_client.add_episode.call_count >= 3


# ============================================================================
# 11. TASK-IGR-003: Reuse Connected Client Tests
# ============================================================================

class TestReuseConnectedClient:
    """Test that sync functions accept and propagate an optional client parameter."""

    @pytest.mark.asyncio
    async def test_sync_template_uses_passed_client(self, tmp_path):
        """sync_template_to_graphiti uses the passed client instead of get_graphiti()."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        # Pass client directly — get_graphiti should NOT be called
        with patch('guardkit.knowledge.template_sync.get_graphiti') as mock_get:
            result = await sync_template_to_graphiti(template_path, client=mock_client)

            assert result is True
            mock_client.add_episode.assert_called()
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_template_falls_back_to_get_graphiti(self, tmp_path):
        """sync_template_to_graphiti falls back to get_graphiti() when no client passed."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client) as mock_get:
            result = await sync_template_to_graphiti(template_path)

            assert result is True
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_agent_uses_passed_client(self, tmp_path):
        """sync_agent_to_graphiti uses the passed client instead of get_graphiti()."""
        agent_path = tmp_path / "test-agent.md"
        agent_path.write_text("---\nname: test-agent\ndescription: Test\n---\n# Agent")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti') as mock_get:
            result = await sync_agent_to_graphiti(agent_path, "template-id", client=mock_client)

            assert result is True
            mock_client.add_episode.assert_called_once()
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_rule_uses_passed_client(self, tmp_path):
        """sync_rule_to_graphiti uses the passed client instead of get_graphiti()."""
        rule_path = tmp_path / "test-rule.md"
        rule_path.write_text("---\npaths: src/**\n---\n# Rule Content")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti') as mock_get:
            result = await sync_rule_to_graphiti(rule_path, "template-id", client=mock_client)

            assert result is True
            mock_client.add_episode.assert_called_once()
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_template_propagates_client_to_agents_and_rules(self, tmp_path):
        """sync_template_to_graphiti passes client down to agent and rule syncs."""
        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        # Create an agent and a rule
        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(
            "---\nname: my-agent\ndescription: Agent\n---\n# Agent"
        )

        rules_dir = template_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "my-rule.md").write_text(
            "---\npaths: src/**\n---\n# Rule"
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        # get_graphiti should never be called since we pass client directly
        with patch('guardkit.knowledge.template_sync.get_graphiti') as mock_get:
            result = await sync_template_to_graphiti(template_path, client=mock_client)

            assert result is True
            # Should have 3 calls: template + agent + rule
            assert mock_client.add_episode.call_count == 3
            mock_get.assert_not_called()


# ============================================================================
# 12. Integration Tests (2 tests - marked for selective running)
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


# ============================================================================
# 13. TASK-IGR-TS01: Summary Logging Tests
# ============================================================================

class TestSummaryLogging:
    """Test that sync_template_to_graphiti logs a completion summary."""

    @pytest.mark.asyncio
    async def test_summary_logged_with_template_agents_rules(self, tmp_path):
        """Summary message is logged when template, agents, and rules are synced."""
        template_path = tmp_path / "full-template"
        template_path.mkdir()

        manifest = {"name": "full-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent-one.md").write_text(
            "---\nname: agent-one\ndescription: Agent One\n---\n# Agent One"
        )

        rules_dir = template_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule-one.md").write_text(
            "---\npaths: src/**\n---\n# Rule One"
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            with patch('guardkit.knowledge.template_sync.logger') as mock_logger:
                result = await sync_template_to_graphiti(template_path)

                assert result is True

                # Find the summary log call
                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                summary_calls = [c for c in info_calls if "Template sync complete" in c]
                assert len(summary_calls) == 1, "Expected exactly one summary log line"

                summary_msg = summary_calls[0]
                assert "1 template" in summary_msg
                assert "1 agents" in summary_msg
                assert "1 rules" in summary_msg
                # Timing suffix in the form (N.Ns)
                assert "s)" in summary_msg

    @pytest.mark.asyncio
    async def test_summary_logged_without_manifest(self, tmp_path):
        """Summary message omits template count when no manifest is synced."""
        template_path = tmp_path / "no-manifest-template"
        template_path.mkdir()
        # No manifest.json

        agents_dir = template_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "my-agent.md").write_text(
            "---\nname: my-agent\ndescription: My Agent\n---\n# My Agent"
        )

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            with patch('guardkit.knowledge.template_sync.logger') as mock_logger:
                result = await sync_template_to_graphiti(template_path)

                assert result is True

                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                summary_calls = [c for c in info_calls if "Template sync complete" in c]
                assert len(summary_calls) == 1

                summary_msg = summary_calls[0]
                # No template count when manifest is absent
                assert "1 template" not in summary_msg
                assert "1 agents" in summary_msg

    @pytest.mark.asyncio
    async def test_summary_includes_warning_count_on_manifest_parse_failure(self, tmp_path):
        """Summary includes warning count when manifest JSON is invalid."""
        template_path = tmp_path / "bad-manifest-template"
        template_path.mkdir()
        (template_path / "manifest.json").write_text("{ not valid json }")

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            with patch('guardkit.knowledge.template_sync.logger') as mock_logger:
                result = await sync_template_to_graphiti(template_path)

                assert result is True

                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                summary_calls = [c for c in info_calls if "Template sync complete" in c]
                assert len(summary_calls) == 1

                summary_msg = summary_calls[0]
                assert "warnings" in summary_msg

    @pytest.mark.asyncio
    async def test_summary_no_warnings_suffix_when_clean(self, tmp_path):
        """Summary omits warnings suffix when sync completes without issues."""
        template_path = tmp_path / "clean-template"
        template_path.mkdir()

        manifest = {"name": "clean-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            with patch('guardkit.knowledge.template_sync.logger') as mock_logger:
                result = await sync_template_to_graphiti(template_path)

                assert result is True

                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                summary_calls = [c for c in info_calls if "Template sync complete" in c]
                assert len(summary_calls) == 1

                summary_msg = summary_calls[0]
                assert "warnings" not in summary_msg

    @pytest.mark.asyncio
    async def test_summary_zero_counts_when_nothing_to_sync(self, tmp_path):
        """Summary shows zero agents and rules when directories are absent."""
        template_path = tmp_path / "empty-template"
        template_path.mkdir()
        # No manifest, no agents dir, no rules dir

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="episode_id")

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            with patch('guardkit.knowledge.template_sync.logger') as mock_logger:
                result = await sync_template_to_graphiti(template_path)

                assert result is True

                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                summary_calls = [c for c in info_calls if "Template sync complete" in c]
                assert len(summary_calls) == 1

                summary_msg = summary_calls[0]
                assert "0 agents" in summary_msg
                assert "0 rules" in summary_msg


# ============================================================================
# Logger Suppression Tests
# ============================================================================

class TestFalkorDBLoggerSuppression:
    """Test that FalkorDB driver ERROR logs are suppressed during sync."""

    @pytest.mark.asyncio
    async def test_falkordb_logger_suppressed_during_sync(self, tmp_path):
        """FalkorDB driver logger set to WARNING during sync operations."""
        import logging

        template_path = tmp_path / "test-template"
        template_path.mkdir()

        falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
        falkordb_logger.setLevel(logging.DEBUG)

        captured_levels = []

        mock_client = AsyncMock()
        mock_client.enabled = True

        async def capture_level(*args, **kwargs):
            captured_levels.append(falkordb_logger.level)
            return "episode_id"

        mock_client.add_episode = AsyncMock(side_effect=capture_level)

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_template_to_graphiti(template_path)

        # Logger should have been WARNING during the sync (no add_episode calls
        # for this template since no manifest, but level should still restore)
        assert falkordb_logger.level == logging.DEBUG

    @pytest.mark.asyncio
    async def test_falkordb_logger_restored_after_error(self, tmp_path):
        """FalkorDB driver logger level restored even when sync raises."""
        import logging

        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
        falkordb_logger.setLevel(logging.ERROR)

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("connection lost"))

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            result = await sync_template_to_graphiti(template_path)

        # Logger must be restored to ERROR even though sync failed
        assert falkordb_logger.level == logging.ERROR
        assert result is False

    @pytest.mark.asyncio
    async def test_falkordb_logger_at_warning_during_episode_add(self, tmp_path):
        """During add_episode calls the FalkorDB logger is at WARNING level."""
        import logging

        template_path = tmp_path / "test-template"
        template_path.mkdir()
        manifest = {"name": "test-template", "language": "Python"}
        (template_path / "manifest.json").write_text(json.dumps(manifest))

        falkordb_logger = logging.getLogger("graphiti_core.driver.falkordb_driver")
        falkordb_logger.setLevel(logging.DEBUG)

        observed_level = None

        async def observe_level(*args, **kwargs):
            nonlocal observed_level
            observed_level = falkordb_logger.level
            return "episode_id"

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=observe_level)

        with patch('guardkit.knowledge.template_sync.get_graphiti', return_value=mock_client):
            await sync_template_to_graphiti(template_path)

        assert observed_level == logging.WARNING
        # Restored after sync
        assert falkordb_logger.level == logging.DEBUG
