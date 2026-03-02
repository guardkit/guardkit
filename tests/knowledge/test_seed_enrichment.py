"""
Tests for enriched system seeding with actual template markdown content.

TASK-INST-012: Tests verify that seed_templates, seed_agents, and seed_rules
read actual content from installer/core/templates/ instead of hardcoded metadata.

Covers:
- Template discovery (all 7 templates)
- Content extraction (manifest.json, agent .md, rule .md)
- Content chunking for large files (>10KB)
- Missing file handling (graceful warnings)
- group_id convention preservation
- SEEDING_VERSION bump to 1.2.0

Coverage Target: >=80%
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


# ============================================================================
# Helpers
# ============================================================================

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "installer" / "core" / "templates"

EXPECTED_TEMPLATES = {
    "default",
    "fastapi-python",
    "fastmcp-python",
    "mcp-typescript",
    "nextjs-fullstack",
    "react-fastapi-monorepo",
    "react-typescript",
}


def _make_mock_client() -> AsyncMock:
    """Create a mock client that captures add_episode calls."""
    client = AsyncMock()
    client.enabled = True
    client.add_episode = AsyncMock(return_value="episode_id")
    return client


def _captured_episodes(client: AsyncMock) -> list[dict[str, Any]]:
    """Extract call kwargs from a mock client's add_episode calls."""
    return [call_obj.kwargs for call_obj in client.add_episode.call_args_list]


# ============================================================================
# 1. SEEDING_VERSION Tests
# ============================================================================

class TestSeedingVersion:
    """Test SEEDING_VERSION is bumped to 1.2.0."""

    def test_seeding_version_is_1_2_0(self):
        """AC: SEEDING_VERSION bumped to '1.2.0'."""
        from guardkit.knowledge.seed_helpers import SEEDING_VERSION
        assert SEEDING_VERSION == "1.2.0"


# ============================================================================
# 2. Template Discovery Tests
# ============================================================================

class TestTemplateDiscovery:
    """Test that all 7 templates are discovered from the filesystem."""

    @pytest.mark.asyncio
    async def test_seed_templates_discovers_all_seven_templates(self):
        """AC: seed_templates reads actual manifest.json from each template dir."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = _make_mock_client()
        await seed_templates(client)

        episodes = _captured_episodes(client)
        # Should have at least 7 episodes (one per template)
        assert len(episodes) >= 7, f"Expected >=7 episodes, got {len(episodes)}"

    @pytest.mark.asyncio
    async def test_seed_templates_reads_manifest_json(self):
        """AC: seed_templates reads actual manifest.json content."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = _make_mock_client()
        await seed_templates(client)

        episodes = _captured_episodes(client)
        # Find episode for fastapi-python (has manifest.json)
        bodies = [json.loads(ep["episode_body"]) for ep in episodes]
        fastapi_found = False
        for body in bodies:
            body_str = json.dumps(body)
            if "fastapi-python" in body_str and "FastAPI" in body_str:
                fastapi_found = True
                # Should contain actual manifest content, not just a summary
                assert "frameworks" in body_str or "architecture" in body_str or "patterns" in body_str, \
                    "Template episode should contain actual manifest data"
                break
        assert fastapi_found, "Should find fastapi-python template episode with manifest data"

    @pytest.mark.asyncio
    async def test_seed_templates_includes_default_without_manifest(self):
        """AC: Templates without manifest.json (e.g., default) use dir name as ID."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = _make_mock_client()
        await seed_templates(client)

        episodes = _captured_episodes(client)
        bodies = [json.loads(ep["episode_body"]) for ep in episodes]
        default_found = any(
            "default" in json.dumps(b) for b in bodies
        )
        assert default_found, "Should discover 'default' template even without manifest.json"

    @pytest.mark.asyncio
    async def test_seed_templates_preserves_group_id(self):
        """AC: Existing group_id convention 'templates' maintained."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = _make_mock_client()
        await seed_templates(client)

        for ep in _captured_episodes(client):
            assert ep["group_id"] == "templates"


# ============================================================================
# 3. Agent Content Tests
# ============================================================================

class TestAgentContent:
    """Test that seed_agents reads actual agent .md files."""

    @pytest.mark.asyncio
    async def test_seed_agents_reads_actual_md_files(self):
        """AC: seed_agents reads actual agent .md files from each template."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)

        episodes = _captured_episodes(client)
        # 18 non-ext agent files across all templates
        assert len(episodes) >= 7, f"Expected >=7 agent episodes, got {len(episodes)}"

    @pytest.mark.asyncio
    async def test_seed_agents_includes_full_body_text(self):
        """AC: Agent content includes full body text (not just frontmatter)."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)

        episodes = _captured_episodes(client)
        # Find a fastapi-specialist episode and verify it has body content
        bodies = [json.loads(ep["episode_body"]) for ep in episodes]
        found_with_body = False
        for body in bodies:
            body_str = json.dumps(body)
            # Should contain actual markdown content, not just metadata
            if "fastapi-specialist" in body_str:
                # The actual file contains "## Role" section with real content
                assert "Role" in body_str or "Boundaries" in body_str or "specialist" in body_str.lower(), \
                    "Agent episode should contain actual body text from the .md file"
                found_with_body = True
                break
        assert found_with_body, "Should find fastapi-specialist agent with body content"

    @pytest.mark.asyncio
    async def test_seed_agents_skips_ext_files(self):
        """AC: -ext.md files should be skipped (supplementary content)."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)

        episodes = _captured_episodes(client)
        for ep in episodes:
            name = ep.get("name", "")
            body_str = ep.get("episode_body", "")
            # Should not have -ext in episode names
            assert "-ext" not in name, f"Should skip -ext files, found: {name}"

    @pytest.mark.asyncio
    async def test_seed_agents_checks_both_agent_directories(self):
        """AC: Check both agents/ and .claude/agents/ for agent files."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)

        episodes = _captured_episodes(client)
        bodies = [json.loads(ep["episode_body"]) for ep in episodes]

        # fastmcp-python uses .claude/agents/ directory
        fastmcp_found = any(
            "fastmcp" in json.dumps(b).lower() for b in bodies
        )
        assert fastmcp_found, "Should discover agents from .claude/agents/ (fastmcp-python)"

    @pytest.mark.asyncio
    async def test_seed_agents_preserves_group_id(self):
        """AC: Existing group_id convention 'agents' maintained."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)

        for ep in _captured_episodes(client):
            assert ep["group_id"] == "agents"


# ============================================================================
# 4. Rule Content Tests
# ============================================================================

class TestRuleContent:
    """Test that seed_rules reads actual rule .md files."""

    @pytest.mark.asyncio
    async def test_seed_rules_reads_actual_md_files(self):
        """AC: seed_rules reads actual rule .md files from each template."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)

        episodes = _captured_episodes(client)
        # Many rule files across templates
        assert len(episodes) >= 4, f"Expected >=4 rule episodes, got {len(episodes)}"

    @pytest.mark.asyncio
    async def test_seed_rules_includes_full_text(self):
        """AC: Rule content includes full text (not just topic headings)."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)

        episodes = _captured_episodes(client)
        bodies = [json.loads(ep["episode_body"]) for ep in episodes]

        # Find a code-style rule and check it has actual content
        found_with_content = False
        for body in bodies:
            body_str = json.dumps(body)
            if "code-style" in body_str.lower() or "naming" in body_str.lower():
                # Should have actual rule content, not just headings
                assert len(body_str) > 100, \
                    "Rule episode should contain full text, not just headings"
                found_with_content = True
                break
        assert found_with_content, "Should find rule episode with full content"

    @pytest.mark.asyncio
    async def test_seed_rules_organises_by_template(self):
        """AC: Rules organized by template for queryability."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)

        episodes = _captured_episodes(client)
        bodies = [json.loads(ep["episode_body"]) for ep in episodes]

        # Each rule episode should reference its template
        templates_found = set()
        for body in bodies:
            body_str = json.dumps(body)
            for tmpl in EXPECTED_TEMPLATES:
                if tmpl in body_str:
                    templates_found.add(tmpl)

        # Should have rules from multiple templates
        assert len(templates_found) >= 3, \
            f"Rules should span multiple templates, found: {templates_found}"

    @pytest.mark.asyncio
    async def test_seed_rules_preserves_group_id(self):
        """AC: Existing group_id convention 'rules' maintained."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)

        for ep in _captured_episodes(client):
            assert ep["group_id"] == "rules"


# ============================================================================
# 5. Content Chunking Tests
# ============================================================================

class TestContentChunking:
    """Test content chunking for files over 10KB."""

    @pytest.mark.asyncio
    async def test_large_rule_files_are_chunked(self):
        """AC: Content chunking applied for files over 10KB."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)

        episodes = _captured_episodes(client)
        # There are rule files >10KB (e.g., fastmcp security.md at ~11KB,
        # react-fastapi-monorepo backend/fastapi.md at ~11KB).
        # These should be chunked into multiple episodes.
        # Total episode count should be > number of rule files
        # because some files get chunked
        assert len(episodes) > 10, \
            f"Expected chunked rules to produce >10 episodes, got {len(episodes)}"

    @pytest.mark.asyncio
    async def test_small_files_are_single_episodes(self):
        """Files under 10KB should be single episodes."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)

        episodes = _captured_episodes(client)
        # All non-ext agent files are <10KB, so episode count should equal file count
        # 18 non-ext agent files
        assert len(episodes) == 18, \
            f"Expected 18 agent episodes (1 per file), got {len(episodes)}"


# ============================================================================
# 6. Missing File Handling Tests
# ============================================================================

class TestMissingFileHandling:
    """Test graceful handling of missing template files."""

    @pytest.mark.asyncio
    async def test_missing_manifest_handled_gracefully(self, tmp_path):
        """AC: Missing template files handled gracefully (warning, not error)."""
        from guardkit.knowledge.seed_templates import seed_templates, _discover_templates

        # Create a template dir without manifest.json
        fake_template = tmp_path / "test-template"
        fake_template.mkdir()

        # Should not raise, should return some result
        templates = _discover_templates(tmp_path)
        found = [t for t in templates if t["template_id"] == "test-template"]
        assert len(found) == 1, "Should discover template even without manifest"
        assert found[0].get("manifest") is None or found[0].get("manifest") == {}

    @pytest.mark.asyncio
    async def test_missing_agents_dir_handled_gracefully(self, tmp_path):
        """Templates without agents/ dir should not error."""
        from guardkit.knowledge.seed_agents import _discover_agent_files

        # Create a template dir without agents/ subfolder
        fake_template = tmp_path / "no-agents"
        fake_template.mkdir()

        # Should return empty list, not raise
        files = _discover_agent_files(fake_template)
        assert files == []

    @pytest.mark.asyncio
    async def test_missing_rules_dir_handled_gracefully(self, tmp_path):
        """Templates without rules/ dir should not error."""
        from guardkit.knowledge.seed_rules import _discover_rule_files

        # Create a template dir without rules
        fake_template = tmp_path / "no-rules"
        fake_template.mkdir()

        files = _discover_rule_files(fake_template)
        assert files == []

    @pytest.mark.asyncio
    async def test_unreadable_file_handled_gracefully(self, tmp_path):
        """Unreadable files should produce warnings, not crash."""
        from guardkit.knowledge.seed_agents import _read_agent_content

        # Non-existent file
        result = _read_agent_content(tmp_path / "nonexistent.md")
        assert result is None


# ============================================================================
# 7. Backward Compatibility Tests
# ============================================================================

class TestBackwardCompatibility:
    """Verify existing test expectations still hold."""

    @pytest.mark.asyncio
    async def test_seed_templates_creates_at_least_4_episodes(self):
        """Existing test expects >= 4 episodes."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = _make_mock_client()
        await seed_templates(client)
        assert client.add_episode.call_count >= 4

    @pytest.mark.asyncio
    async def test_seed_agents_creates_at_least_7_episodes(self):
        """Existing test expects >= 7 episodes."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)
        assert client.add_episode.call_count >= 7

    @pytest.mark.asyncio
    async def test_seed_rules_creates_at_least_4_episodes(self):
        """Existing test expects >= 4 episodes."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)
        assert client.add_episode.call_count >= 4

    @pytest.mark.asyncio
    async def test_seed_templates_disabled_client_skips(self):
        """Disabled client should skip seeding."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = AsyncMock()
        client.enabled = False
        await seed_templates(client)
        client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_agents_disabled_client_skips(self):
        """Disabled client should skip seeding."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = AsyncMock()
        client.enabled = False
        await seed_agents(client)
        client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_rules_disabled_client_skips(self):
        """Disabled client should skip seeding."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = AsyncMock()
        client.enabled = False
        await seed_rules(client)
        client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_templates_uses_correct_source(self):
        """Verify source kwarg is 'guardkit_seeding'."""
        from guardkit.knowledge.seed_templates import seed_templates

        client = _make_mock_client()
        await seed_templates(client)
        for ep in _captured_episodes(client):
            assert ep.get("source") == "guardkit_seeding"

    @pytest.mark.asyncio
    async def test_seed_agents_uses_correct_entity_type(self):
        """Verify entity_type kwarg is 'agent'."""
        from guardkit.knowledge.seed_agents import seed_agents

        client = _make_mock_client()
        await seed_agents(client)
        for ep in _captured_episodes(client):
            assert ep.get("entity_type") == "agent"

    @pytest.mark.asyncio
    async def test_seed_rules_uses_correct_entity_type(self):
        """Verify entity_type kwarg is 'rule'."""
        from guardkit.knowledge.seed_rules import seed_rules

        client = _make_mock_client()
        await seed_rules(client)
        for ep in _captured_episodes(client):
            assert ep.get("entity_type") == "rule"
