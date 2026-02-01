"""
Tests for ExistsResult dataclass.

Tests cover the structured result format for episode existence checks.

Coverage Target: >=85%
Test Count: 10+ tests
"""

import pytest

from guardkit.integrations.graphiti.exists_result import ExistsResult


class TestExistsResultCreation:
    """Test ExistsResult creation and validation."""

    def test_create_not_found(self):
        """Test creating a not-found result with factory method."""
        result = ExistsResult.not_found()

        assert result.exists is False
        assert result.episode is None
        assert result.exact_match is False
        assert result.uuid is None

    def test_create_found_with_episode(self):
        """Test creating a found result with episode data."""
        episode = {"uuid": "test-uuid", "fact": "Test content"}
        result = ExistsResult.found(episode=episode)

        assert result.exists is True
        assert result.episode == episode
        assert result.exact_match is False
        assert result.uuid == "test-uuid"

    def test_create_found_with_exact_match(self):
        """Test creating a found result with exact_match flag."""
        episode = {"uuid": "test-uuid-2"}
        result = ExistsResult.found(episode=episode, exact_match=True)

        assert result.exists is True
        assert result.exact_match is True

    def test_create_found_extracts_uuid_from_episode(self):
        """Test that uuid is automatically extracted from episode."""
        episode = {"uuid": "auto-extracted-uuid", "other": "data"}
        result = ExistsResult.found(episode=episode)

        assert result.uuid == "auto-extracted-uuid"

    def test_create_found_explicit_uuid_overrides(self):
        """Test that explicit uuid overrides episode uuid."""
        episode = {"uuid": "episode-uuid"}
        result = ExistsResult.found(episode=episode, uuid="explicit-uuid")

        assert result.uuid == "explicit-uuid"

    def test_create_found_no_uuid_in_episode(self):
        """Test found result when episode has no uuid."""
        episode = {"fact": "content only"}
        result = ExistsResult.found(episode=episode)

        assert result.exists is True
        assert result.uuid is None


class TestExistsResultValidation:
    """Test ExistsResult validation rules."""

    def test_not_found_with_episode_raises(self):
        """Test that not-found with episode raises ValueError."""
        with pytest.raises(ValueError, match="episode must be None"):
            ExistsResult(exists=False, episode={"uuid": "test"})

    def test_not_found_with_exact_match_raises(self):
        """Test that not-found with exact_match=True raises ValueError."""
        with pytest.raises(ValueError, match="exact_match must be False"):
            ExistsResult(exists=False, exact_match=True)

    def test_not_found_with_uuid_raises(self):
        """Test that not-found with uuid raises ValueError."""
        with pytest.raises(ValueError, match="uuid must be None"):
            ExistsResult(exists=False, uuid="some-uuid")

    def test_found_without_uuid_but_with_episode_extracts_uuid(self):
        """Test that found with episode but no uuid extracts from episode."""
        # Direct constructor with exists=True and episode with uuid
        result = ExistsResult(
            exists=True,
            episode={"uuid": "extracted", "fact": "content"},
            exact_match=False,
            uuid=None  # Not provided
        )

        # Post-init should extract uuid from episode
        assert result.uuid == "extracted"


class TestExistsResultBooleanBehavior:
    """Test ExistsResult boolean evaluation."""

    def test_not_found_is_falsy_via_exists(self):
        """Test that not_found result has exists=False."""
        result = ExistsResult.not_found()
        assert not result.exists

    def test_found_is_truthy_via_exists(self):
        """Test that found result has exists=True."""
        result = ExistsResult.found(episode={"uuid": "test"})
        assert result.exists


class TestExistsResultDataAccess:
    """Test accessing data from ExistsResult."""

    def test_access_episode_data(self):
        """Test accessing episode data from result."""
        episode = {
            "uuid": "ep-123",
            "fact": "Test content",
            "metadata": {"source": "test"}
        }
        result = ExistsResult.found(episode=episode)

        assert result.episode["uuid"] == "ep-123"
        assert result.episode["fact"] == "Test content"
        assert result.episode["metadata"]["source"] == "test"

    def test_access_uuid_directly(self):
        """Test accessing uuid directly."""
        result = ExistsResult.found(
            episode={"uuid": "direct-access"},
            uuid="direct-access"
        )

        assert result.uuid == "direct-access"

    def test_exact_match_indicates_hash_match(self):
        """Test that exact_match indicates source_hash matched."""
        result = ExistsResult.found(
            episode={"uuid": "test"},
            exact_match=True
        )

        assert result.exact_match is True


class TestExistsResultEdgeCases:
    """Test edge cases for ExistsResult."""

    def test_found_with_empty_episode(self):
        """Test found with empty episode dict."""
        result = ExistsResult.found(episode={})

        assert result.exists is True
        assert result.episode == {}
        assert result.uuid is None

    def test_found_with_none_values_in_episode(self):
        """Test found with None values in episode dict."""
        episode = {"uuid": None, "fact": None}
        result = ExistsResult.found(episode=episode)

        assert result.exists is True
        assert result.uuid is None  # None in episode

    def test_multiple_not_found_results_are_equal(self):
        """Test that multiple not_found results have same attributes."""
        result1 = ExistsResult.not_found()
        result2 = ExistsResult.not_found()

        assert result1.exists == result2.exists
        assert result1.episode == result2.episode
        assert result1.uuid == result2.uuid
        assert result1.exact_match == result2.exact_match
