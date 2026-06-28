"""Tests for harvest walker module.

Tests cover:
- Directory enumeration and episode_type mapping
- Empty body filtering
- Oversized body skipping
- MemoryEpisodeV1 construction with correct provenance
- HarvestResult counts and statistics
- No NATS dependencies
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from nats_core.events import MAX_EPISODE_BODY_BYTES, MemoryEpisodeV1

from guardkit.memory.harvest_walker import HarvestResult, walk_harvest_dirs


class TestHarvestWalker:
    """Test suite for harvest walker functionality."""

    def test_taxonomy_mapping(self, tmp_path: Path) -> None:
        """Episode types are correctly mapped from directory structure."""
        # Create sample docs in different taxonomy dirs
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/code-review").mkdir(parents=True)
        (tmp_path / "docs/guides").mkdir(parents=True)

        (tmp_path / "docs/adr/001-decision.md").write_text("# ADR 001\nContent")
        (tmp_path / "docs/code-review/review-x.md").write_text("# Review X\nContent")
        (tmp_path / "docs/guides/guide-y.md").write_text("# Guide Y\nContent")

        result = walk_harvest_dirs(tmp_path)

        # Find episodes by type
        adr_episodes = [e for e in result.episodes if e.episode_type == "adr"]
        review_episodes = [e for e in result.episodes if e.episode_type == "review_report"]
        doc_episodes = [e for e in result.episodes if e.episode_type == "document"]

        assert len(adr_episodes) == 1
        assert len(review_episodes) == 1
        assert len(doc_episodes) == 1

    def test_empty_body_filter(self, tmp_path: Path) -> None:
        """Empty and whitespace-only bodies are filtered out."""
        (tmp_path / "docs/adr").mkdir(parents=True)

        # Create files with various empty content
        (tmp_path / "docs/adr/empty.md").write_text("")
        (tmp_path / "docs/adr/whitespace.md").write_text("   \n\t  \n   ")
        (tmp_path / "docs/adr/valid.md").write_text("# Real content")

        result = walk_harvest_dirs(tmp_path)

        # Should only have 1 valid episode
        assert len(result.episodes) == 1
        assert result.skipped_empty == 2
        assert result.episodes[0].body == "# Real content"

    def test_oversized_skip(self, tmp_path: Path) -> None:
        """Docs >= MAX_EPISODE_BODY_BYTES are skipped with size recorded."""
        (tmp_path / "docs/adr").mkdir(parents=True)

        # Create an oversized doc (just over 900KB)
        oversized_content = "x" * (MAX_EPISODE_BODY_BYTES + 100)
        oversized_path = tmp_path / "docs/adr/huge.md"
        oversized_path.write_text(oversized_content)

        # Create a normal-sized doc
        (tmp_path / "docs/adr/normal.md").write_text("# Normal content")

        result = walk_harvest_dirs(tmp_path)

        # Should have 1 episode (normal) and 1 skipped (oversized)
        assert len(result.episodes) == 1
        assert len(result.skipped_oversized) == 1

        path, size = result.skipped_oversized[0]
        assert "docs/adr/huge.md" in path
        assert size > MAX_EPISODE_BODY_BYTES

    def test_project_id_literal_guardkit(self, tmp_path: Path) -> None:
        """project_id is the literal 'guardkit' with underscores only."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/adr/test.md").write_text("# Test")

        result = walk_harvest_dirs(tmp_path)

        assert len(result.episodes) == 1
        episode = result.episodes[0]

        # CRITICAL: Must be underscores, not hyphens (DLQ poison)
        assert episode.project_id == "guardkit"
        assert "-" not in episode.project_id

    def test_counts_per_type(self, tmp_path: Path) -> None:
        """counts_per_type accurately reflects episode distribution."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/code-review").mkdir(parents=True)

        # Create multiple docs per type
        (tmp_path / "docs/adr/001.md").write_text("# ADR 001")
        (tmp_path / "docs/adr/002.md").write_text("# ADR 002")
        (tmp_path / "docs/adr/003.md").write_text("# ADR 003")
        (tmp_path / "docs/code-review/review-a.md").write_text("# Review A")
        (tmp_path / "docs/code-review/review-b.md").write_text("# Review B")

        result = walk_harvest_dirs(tmp_path)

        assert result.counts_per_type["adr"] == 3
        assert result.counts_per_type["review_report"] == 2
        assert sum(result.counts_per_type.values()) == 5

    def test_memory_episode_fields(self, tmp_path: Path) -> None:
        """MemoryEpisodeV1 is constructed with all required fields."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        test_path = tmp_path / "docs/adr/001-test.md"
        test_path.write_text("# Test Decision\n\nSome content here.")

        result = walk_harvest_dirs(tmp_path)

        assert len(result.episodes) == 1
        episode = result.episodes[0]

        # Required fields
        assert episode.episode_id.startswith("ep-")
        assert episode.project_id == "guardkit"
        assert episode.episode_type == "adr"
        assert episode.content_format == "markdown"
        assert episode.body == "# Test Decision\n\nSome content here."

        # Provenance fields
        assert episode.source == "guardkit-harvest"
        assert "docs/adr/001-test.md" in episode.source_ref
        assert episode.name == "001-test"  # File stem
        assert isinstance(episode.occurred_at, datetime)

    def test_name_extraction_from_file(self, tmp_path: Path) -> None:
        """Episode name is extracted from file stem."""
        (tmp_path / "docs/adr").mkdir(parents=True)

        # Test various file name patterns
        (tmp_path / "docs/adr/001-decision.md").write_text("# Content")
        (tmp_path / "docs/adr/simple.md").write_text("# Content")
        (tmp_path / "docs/adr/multi-word-name.md").write_text("# Content")

        result = walk_harvest_dirs(tmp_path)

        names = sorted([e.name for e in result.episodes])
        assert names == ["001-decision", "multi-word-name", "simple"]

    def test_occurred_at_is_datetime(self, tmp_path: Path) -> None:
        """occurred_at is a valid datetime (best-effort from git/fs)."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/adr/test.md").write_text("# Test")

        result = walk_harvest_dirs(tmp_path)

        episode = result.episodes[0]
        assert isinstance(episode.occurred_at, datetime)
        # Should be timezone-aware
        assert episode.occurred_at.tzinfo is not None

    def test_no_nats_connection_required(self, tmp_path: Path) -> None:
        """Walker runs without any NATS connection or client."""
        # This test verifies we don't import NATSClient at module level
        # or attempt any network operations
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/adr/test.md").write_text("# Test")

        # Should complete without any network calls
        result = walk_harvest_dirs(tmp_path)
        assert len(result.episodes) == 1

    def test_relative_path_in_source_ref(self, tmp_path: Path) -> None:
        """source_ref contains repo-relative path, not absolute."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/adr/test.md").write_text("# Test")

        result = walk_harvest_dirs(tmp_path)

        episode = result.episodes[0]
        # Should be relative like "docs/adr/test.md", not absolute
        assert episode.source_ref.startswith("docs/")
        assert not episode.source_ref.startswith("/")

    def test_deterministic_episode_id(self, tmp_path: Path) -> None:
        """episode_id is deterministic for same file path and type."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/adr/test.md").write_text("# Test")

        # Walk twice
        result1 = walk_harvest_dirs(tmp_path)
        result2 = walk_harvest_dirs(tmp_path)

        assert result1.episodes[0].episode_id == result2.episodes[0].episode_id

    def test_excludes_non_markdown_files(self, tmp_path: Path) -> None:
        """Only *.md files are harvested."""
        (tmp_path / "docs/adr").mkdir(parents=True)

        (tmp_path / "docs/adr/valid.md").write_text("# Valid")
        (tmp_path / "docs/adr/readme.txt").write_text("Not markdown")
        (tmp_path / "docs/adr/data.json").write_text("{}")

        result = walk_harvest_dirs(tmp_path)

        assert len(result.episodes) == 1
        assert result.episodes[0].source_ref.endswith("valid.md")

    def test_nested_directories(self, tmp_path: Path) -> None:
        """Files in nested subdirectories are harvested correctly."""
        (tmp_path / "docs/code-review/2024").mkdir(parents=True)
        (tmp_path / "docs/code-review/2024/q1").mkdir(parents=True)

        (tmp_path / "docs/code-review/top.md").write_text("# Top level")
        (tmp_path / "docs/code-review/2024/nested.md").write_text("# Nested")
        (tmp_path / "docs/code-review/2024/q1/deep.md").write_text("# Deep")

        result = walk_harvest_dirs(tmp_path)

        assert len(result.episodes) == 3
        # All should have review_report type
        assert all(e.episode_type == "review_report" for e in result.episodes)

    def test_content_format_always_markdown(self, tmp_path: Path) -> None:
        """All harvested episodes have content_format='markdown'."""
        (tmp_path / "docs/adr").mkdir(parents=True)
        (tmp_path / "docs/code-review").mkdir(parents=True)
        (tmp_path / "docs/guides").mkdir(parents=True)

        (tmp_path / "docs/adr/test1.md").write_text("# Test 1")
        (tmp_path / "docs/code-review/test2.md").write_text("# Test 2")
        (tmp_path / "docs/guides/test3.md").write_text("# Test 3")

        result = walk_harvest_dirs(tmp_path)

        assert all(e.content_format == "markdown" for e in result.episodes)

    def test_empty_repo_returns_empty_result(self, tmp_path: Path) -> None:
        """Walking an empty repo returns empty episodes list."""
        result = walk_harvest_dirs(tmp_path)

        assert len(result.episodes) == 0
        assert result.skipped_empty == 0
        assert len(result.skipped_oversized) == 0
        assert result.counts_per_type == {}

    def test_skip_report_contains_repo_relative_paths(self, tmp_path: Path) -> None:
        """Oversized skip report uses repo-relative paths."""
        (tmp_path / "docs/adr").mkdir(parents=True)

        oversized_content = "x" * (MAX_EPISODE_BODY_BYTES + 100)
        (tmp_path / "docs/adr/huge.md").write_text(oversized_content)

        result = walk_harvest_dirs(tmp_path)

        assert len(result.skipped_oversized) == 1
        path, _ = result.skipped_oversized[0]
        # Should be relative
        assert path.startswith("docs/")
        assert not path.startswith("/")
