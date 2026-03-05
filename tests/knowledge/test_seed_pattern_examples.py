"""Tests for seed_pattern_examples module."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.knowledge.seed_pattern_examples import (
    _get_patterns_dir,
    extract_dataclass_patterns,
    extract_orchestrator_patterns,
    extract_pydantic_patterns,
    seed_pattern_examples,
)


class TestGetPatternsDir:
    """Tests for _get_patterns_dir path resolution."""

    def test_resolves_to_guardkit_patterns_dir(self):
        """_get_patterns_dir() should find .claude/rules/patterns/ in the guardkit repo."""
        result = _get_patterns_dir()
        assert result.is_dir(), f"Expected directory to exist: {result}"
        assert result.name == "patterns"
        assert result.parent.name == "rules"

    def test_contains_expected_pattern_files(self):
        """The resolved directory should contain the expected pattern files."""
        result = _get_patterns_dir()
        expected_files = ["dataclasses.md", "pydantic-models.md", "orchestrators.md"]
        for filename in expected_files:
            assert (result / filename).exists(), f"Missing pattern file: {filename}"

    def test_works_when_cwd_is_different(self, tmp_path, monkeypatch):
        """_get_patterns_dir() should work even when CWD is a different directory."""
        monkeypatch.chdir(tmp_path)
        result = _get_patterns_dir()
        # Should still resolve via __file__ walk-up, not CWD
        assert result.is_dir(), f"Expected directory to exist: {result}"
        assert (result / "dataclasses.md").exists()

    def test_does_not_use_cwd(self, tmp_path, monkeypatch):
        """_get_patterns_dir() should NOT return a CWD-relative path when __file__ walk-up succeeds."""
        monkeypatch.chdir(tmp_path)
        result = _get_patterns_dir()
        # The result should NOT be under tmp_path (CWD)
        assert not str(result).startswith(str(tmp_path))


class TestExtractPatterns:
    """Tests for pattern extraction functions."""

    def test_extract_dataclass_patterns_returns_episodes(self):
        episodes = extract_dataclass_patterns("dummy content")
        assert len(episodes) > 0
        for ep in episodes:
            assert "name" in ep
            assert "body" in ep
            assert ep["name"].startswith("Dataclass Pattern:")

    def test_extract_pydantic_patterns_returns_episodes(self):
        episodes = extract_pydantic_patterns("dummy content")
        assert len(episodes) > 0
        for ep in episodes:
            assert "name" in ep
            assert "body" in ep
            assert ep["name"].startswith("Pydantic Pattern:")

    def test_extract_orchestrator_patterns_returns_episodes(self):
        episodes = extract_orchestrator_patterns("dummy content")
        assert len(episodes) > 0
        for ep in episodes:
            assert "name" in ep
            assert "body" in ep
            assert ep["name"].startswith("Orchestrator Pattern:")


class TestSeedPatternExamples:
    """Tests for the main seed_pattern_examples function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_client_disabled(self):
        client = MagicMock()
        client.enabled = False
        result = await seed_pattern_examples(client)
        assert result["success"] is False
        assert result["error"] == "Graphiti not enabled"

    @pytest.mark.asyncio
    async def test_seeds_all_patterns_when_enabled(self):
        client = MagicMock()
        client.enabled = True
        client.add_episode = AsyncMock(return_value="episode-id-123")

        result = await seed_pattern_examples(client)

        assert result["success"] is True
        assert result["episodes_created"] > 0
        assert "dataclasses" in result["patterns_seeded"]
        assert "pydantic-models" in result["patterns_seeded"]
        assert "orchestrators" in result["patterns_seeded"]
        assert result["error"] is None
