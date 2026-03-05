"""
Tests for guardkit.knowledge.seed_rules

Covers:
- Per-template batching behavior
- Circuit breaker reset between templates
- Per-template logging (created/skipped)
- Disabled/None client early return
- Empty templates directory handling
- Return type (total_created, total_skipped) tuple

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

from guardkit.knowledge.seed_rules import (
    seed_rules,
    _get_templates_dir,
    _discover_rule_files,
    _read_rule_content,
    _extract_title,
    _chunk_by_sections,
    _build_rule_episodes,
)


class TestSeedRulesPerTemplateBatching:
    """Test that seed_rules batches by template and resets circuit breaker."""

    @pytest.mark.asyncio
    async def test_returns_zero_tuple_when_client_none(self):
        """None client returns (0, 0)."""
        result = await seed_rules(None)
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_returns_zero_tuple_when_client_disabled(self):
        """Disabled client returns (0, 0)."""
        client = MagicMock()
        client.enabled = False
        result = await seed_rules(client)
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_returns_zero_tuple_when_no_templates_dir(self, tmp_path):
        """Missing templates directory returns (0, 0)."""
        client = AsyncMock()
        client.enabled = True

        with patch(
            "guardkit.knowledge.seed_rules._get_templates_dir",
            return_value=tmp_path / "nonexistent",
        ):
            result = await seed_rules(client)
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_returns_zero_tuple_when_no_rule_files(self, tmp_path):
        """Templates dir with no rule files returns (0, 0)."""
        client = AsyncMock()
        client.enabled = True

        # Create template dirs without rules
        (tmp_path / "template-a").mkdir()
        (tmp_path / "template-b").mkdir()

        with patch(
            "guardkit.knowledge.seed_rules._get_templates_dir",
            return_value=tmp_path,
        ):
            result = await seed_rules(client)
        assert result == (0, 0)

    @pytest.mark.asyncio
    async def test_batches_by_template(self, tmp_path):
        """Rules are grouped by template and _add_episodes called per template."""
        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        # Create two templates with rule files
        for tpl in ["default", "fastapi-python"]:
            rules_dir = tmp_path / tpl / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "rule1.md").write_text("# Rule 1\nContent for rule 1")
            (rules_dir / "rule2.md").write_text("# Rule 2\nContent for rule 2")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(2, 0),
            ) as mock_add,
        ):
            result = await seed_rules(client)

        # Should be called once per template
        assert mock_add.call_count == 2

        # Check group_ids are per-template
        call_group_ids = [c.kwargs.get("group_id", c.args[2]) for c in mock_add.call_args_list]
        assert "rules_default" in call_group_ids
        assert "rules_fastapi-python" in call_group_ids

        # Total: 2 templates * 2 created = 4 created
        assert result == (4, 0)

    @pytest.mark.asyncio
    async def test_resets_circuit_breaker_between_templates(self, tmp_path):
        """Circuit breaker is reset before each template batch."""
        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        # Create three templates
        for tpl in ["alpha", "beta", "gamma"]:
            rules_dir = tmp_path / tpl / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "rule.md").write_text("# Rule\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ),
        ):
            await seed_rules(client)

        # Circuit breaker should be reset once per template
        assert client.reset_circuit_breaker.call_count == 3

    @pytest.mark.asyncio
    async def test_failure_in_one_template_doesnt_block_others(self, tmp_path):
        """Failures in one template don't prevent other templates from seeding."""
        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        # Create two templates
        for tpl in ["failing", "succeeding"]:
            rules_dir = tmp_path / tpl / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "rule.md").write_text("# Rule\nContent")

        # First template fails (all skipped), second succeeds
        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                side_effect=[(0, 1), (1, 0)],
            ),
        ):
            result = await seed_rules(client)

        # First template: 0 created, 1 skipped
        # Second template: 1 created, 0 skipped
        assert result == (1, 1)

    @pytest.mark.asyncio
    async def test_per_template_category_names(self, tmp_path):
        """Each template batch uses per-template category_name."""
        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        rules_dir = tmp_path / "react-typescript" / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule.md").write_text("# Rule\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ) as mock_add,
        ):
            await seed_rules(client)

        # Check category_name is per-template
        call_args = mock_add.call_args
        assert call_args.args[3] == "rules/react-typescript" or call_args.kwargs.get("category_name") == "rules/react-typescript"

    @pytest.mark.asyncio
    async def test_works_without_reset_circuit_breaker_method(self, tmp_path):
        """Gracefully handles clients without reset_circuit_breaker."""
        client = AsyncMock()
        client.enabled = True
        # Explicitly remove the method
        del client.reset_circuit_breaker

        rules_dir = tmp_path / "default" / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule.md").write_text("# Rule\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ),
        ):
            # Should not raise even without reset_circuit_breaker
            result = await seed_rules(client)

        assert result == (1, 0)

    @pytest.mark.asyncio
    async def test_skips_hidden_directories(self, tmp_path):
        """Hidden directories (starting with .) are skipped."""
        client = AsyncMock()
        client.enabled = True
        client.reset_circuit_breaker = MagicMock()

        # Create a hidden template dir and a normal one
        hidden_dir = tmp_path / ".hidden" / ".claude" / "rules"
        hidden_dir.mkdir(parents=True)
        (hidden_dir / "rule.md").write_text("# Hidden Rule\nContent")

        visible_dir = tmp_path / "visible" / ".claude" / "rules"
        visible_dir.mkdir(parents=True)
        (visible_dir / "rule.md").write_text("# Visible Rule\nContent")

        with (
            patch(
                "guardkit.knowledge.seed_rules._get_templates_dir",
                return_value=tmp_path,
            ),
            patch(
                "guardkit.knowledge.seed_rules._add_episodes",
                new_callable=AsyncMock,
                return_value=(1, 0),
            ) as mock_add,
        ):
            result = await seed_rules(client)

        # Only visible template processed
        assert mock_add.call_count == 1
        assert result == (1, 0)


class TestDiscoverRuleFiles:
    """Test _discover_rule_files helper."""

    def test_discovers_md_files(self, tmp_path):
        """Finds all .md files in .claude/rules/."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "a.md").write_text("content")
        (rules_dir / "b.md").write_text("content")
        (rules_dir / "not_md.txt").write_text("content")

        result = _discover_rule_files(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".md" for p in result)

    def test_returns_empty_when_no_rules_dir(self, tmp_path):
        """Returns empty list when .claude/rules/ doesn't exist."""
        result = _discover_rule_files(tmp_path)
        assert result == []

    def test_discovers_nested_md_files(self, tmp_path):
        """Recursively finds .md files in subdirectories."""
        rules_dir = tmp_path / ".claude" / "rules"
        sub_dir = rules_dir / "patterns"
        sub_dir.mkdir(parents=True)
        (rules_dir / "top.md").write_text("content")
        (sub_dir / "nested.md").write_text("content")

        result = _discover_rule_files(tmp_path)
        assert len(result) == 2


class TestReadRuleContent:
    """Test _read_rule_content helper."""

    def test_reads_file_content(self, tmp_path):
        """Returns file content as string."""
        f = tmp_path / "rule.md"
        f.write_text("# Test Rule\nSome content")
        assert _read_rule_content(f) == "# Test Rule\nSome content"

    def test_returns_none_for_empty_file(self, tmp_path):
        """Returns None for empty files."""
        f = tmp_path / "empty.md"
        f.write_text("")
        assert _read_rule_content(f) is None

    def test_returns_none_for_whitespace_only(self, tmp_path):
        """Returns None for whitespace-only files."""
        f = tmp_path / "ws.md"
        f.write_text("   \n\n  ")
        assert _read_rule_content(f) is None

    def test_returns_none_for_missing_file(self, tmp_path):
        """Returns None for non-existent files."""
        assert _read_rule_content(tmp_path / "missing.md") is None


class TestExtractTitle:
    """Test _extract_title helper."""

    def test_extracts_h1_title(self):
        assert _extract_title("# My Title\nContent") == "My Title"

    def test_extracts_h2_title(self):
        assert _extract_title("## Section Title\nContent") == "Section Title"

    def test_returns_none_for_no_heading(self):
        assert _extract_title("No heading here") is None

    def test_strips_whitespace(self):
        assert _extract_title("#  Spaced Title  \n") == "Spaced Title"


class TestChunkBySections:
    """Test _chunk_by_sections helper."""

    def test_single_chunk_when_no_h2(self):
        """Content without h2 headers returns single chunk."""
        result = _chunk_by_sections("# Title\nJust content", "Doc")
        assert len(result) == 1
        assert result[0]["title"] == "Doc"

    def test_splits_by_h2(self):
        """Content with h2 headers splits into chunks."""
        content = "# Title\nIntro\n## Section A\nContent A\n## Section B\nContent B"
        result = _chunk_by_sections(content, "Doc")
        assert len(result) == 3  # intro + 2 sections
        assert result[0]["title"] == "Doc - Introduction"
        assert result[1]["title"] == "Doc - Section A"
        assert result[2]["title"] == "Doc - Section B"


class TestBuildRuleEpisodes:
    """Test _build_rule_episodes helper."""

    def test_single_episode_for_small_file(self, tmp_path):
        """Small files produce a single episode."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        rule_file = rules_dir / "test.md"
        rule_file.write_text("# Test Rule\nSmall content")

        result = _build_rule_episodes("default", rule_file, "# Test Rule\nSmall content")
        assert len(result) == 1
        name, body = result[0]
        assert body["entity_type"] == "rule"
        assert body["template_id"] == "default"

    def test_chunks_large_files(self, tmp_path):
        """Files over 10KB are chunked by sections."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        rule_file = rules_dir / "big.md"

        # Create content > 10KB with multiple sections
        sections = []
        for i in range(5):
            sections.append(f"## Section {i}\n{'x' * 3000}")
        content = "# Big Rule\n" + "\n".join(sections)
        rule_file.write_text(content)

        result = _build_rule_episodes("default", rule_file, content)
        # Should have intro + 5 sections = 6 chunks
        assert len(result) > 1
        for name, body in result:
            assert "chunk_index" in body
            assert "chunk_total" in body
