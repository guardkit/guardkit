"""
Tests for UpsertResult dataclass.

Tests cover the structured result format for upsert_episode operations.

Coverage Target: >=85%
Test Count: 10+ tests
"""

import pytest

from guardkit.integrations.graphiti.upsert_result import UpsertResult


class TestUpsertResultCreation:
    """Test UpsertResult creation and factory methods."""

    def test_create_result_created(self):
        """Test creating a result with 'created' action via factory method."""
        episode = {"uuid": "test-uuid", "content": "Test content"}
        result = UpsertResult.created(episode=episode)

        assert result.action == "created"
        assert result.episode == episode
        assert result.uuid == "test-uuid"
        assert result.previous_uuid is None

    def test_create_result_updated(self):
        """Test creating a result with 'updated' action via factory method."""
        episode = {"uuid": "new-uuid", "content": "Updated content"}
        result = UpsertResult.updated(
            episode=episode,
            uuid="new-uuid",
            previous_uuid="old-uuid"
        )

        assert result.action == "updated"
        assert result.episode == episode
        assert result.uuid == "new-uuid"
        assert result.previous_uuid == "old-uuid"

    def test_create_result_skipped(self):
        """Test creating a result with 'skipped' action via factory method."""
        episode = {"uuid": "existing-uuid", "content": "Existing content"}
        result = UpsertResult.skipped(episode=episode)

        assert result.action == "skipped"
        assert result.episode == episode
        assert result.uuid == "existing-uuid"
        assert result.previous_uuid is None


class TestUpsertResultUuidExtraction:
    """Test UUID extraction behavior."""

    def test_uuid_extracted_from_episode(self):
        """Test that uuid is automatically extracted from episode if not provided."""
        episode = {"uuid": "auto-extracted-uuid", "other": "data"}
        result = UpsertResult.created(episode=episode)

        assert result.uuid == "auto-extracted-uuid"

    def test_explicit_uuid_overrides_episode_uuid(self):
        """Test that explicit uuid takes precedence over episode uuid."""
        episode = {"uuid": "episode-uuid", "content": "data"}
        result = UpsertResult.created(episode=episode, uuid="explicit-uuid")

        assert result.uuid == "explicit-uuid"

    def test_no_uuid_when_episode_has_no_uuid(self):
        """Test result when episode has no uuid key."""
        episode = {"content": "content only"}
        result = UpsertResult.created(episode=episode)

        assert result.uuid is None

    def test_uuid_none_when_episode_is_none(self):
        """Test uuid is None when episode is None."""
        result = UpsertResult(action="created", episode=None)

        assert result.uuid is None


class TestUpsertResultValidation:
    """Test UpsertResult validation rules."""

    def test_invalid_action_raises_value_error(self):
        """Test that invalid action raises ValueError."""
        with pytest.raises(ValueError, match="action must be 'created', 'updated', or 'skipped'"):
            UpsertResult(action="invalid")

    def test_valid_actions_accepted(self):
        """Test that all valid actions are accepted."""
        for action in ("created", "updated", "skipped"):
            result = UpsertResult(action=action)
            assert result.action == action


class TestUpsertResultBooleanHelpers:
    """Test boolean helper properties."""

    def test_was_created_property(self):
        """Test was_created returns True only for created action."""
        created = UpsertResult.created(episode={"uuid": "1"})
        updated = UpsertResult.updated(episode={"uuid": "2"})
        skipped = UpsertResult.skipped(episode={"uuid": "3"})

        assert created.was_created is True
        assert updated.was_created is False
        assert skipped.was_created is False

    def test_was_updated_property(self):
        """Test was_updated returns True only for updated action."""
        created = UpsertResult.created(episode={"uuid": "1"})
        updated = UpsertResult.updated(episode={"uuid": "2"})
        skipped = UpsertResult.skipped(episode={"uuid": "3"})

        assert created.was_updated is False
        assert updated.was_updated is True
        assert skipped.was_updated is False

    def test_was_skipped_property(self):
        """Test was_skipped returns True only for skipped action."""
        created = UpsertResult.created(episode={"uuid": "1"})
        updated = UpsertResult.updated(episode={"uuid": "2"})
        skipped = UpsertResult.skipped(episode={"uuid": "3"})

        assert created.was_skipped is False
        assert updated.was_skipped is False
        assert skipped.was_skipped is True


class TestUpsertResultPreviousUuid:
    """Test previous_uuid tracking for updates."""

    def test_previous_uuid_for_updates(self):
        """Test that previous_uuid is tracked for update operations."""
        episode = {"uuid": "new-uuid"}
        result = UpsertResult.updated(
            episode=episode,
            previous_uuid="old-uuid-123"
        )

        assert result.previous_uuid == "old-uuid-123"
        assert result.uuid == "new-uuid"

    def test_previous_uuid_none_for_created(self):
        """Test that previous_uuid is None for created operations."""
        result = UpsertResult.created(episode={"uuid": "new"})

        assert result.previous_uuid is None

    def test_previous_uuid_none_for_skipped(self):
        """Test that previous_uuid is None for skipped operations."""
        result = UpsertResult.skipped(episode={"uuid": "existing"})

        assert result.previous_uuid is None


class TestUpsertResultEdgeCases:
    """Test edge cases for UpsertResult."""

    def test_created_with_empty_episode(self):
        """Test created with empty episode dict."""
        result = UpsertResult.created(episode={})

        assert result.action == "created"
        assert result.episode == {}
        assert result.uuid is None

    def test_updated_with_same_uuid(self):
        """Test updated where uuid remains the same."""
        result = UpsertResult.updated(
            episode={"uuid": "same-uuid"},
            previous_uuid="same-uuid"
        )

        assert result.uuid == "same-uuid"
        assert result.previous_uuid == "same-uuid"

    def test_direct_constructor_with_all_fields(self):
        """Test direct constructor with all fields specified."""
        episode = {"uuid": "ep-uuid", "content": "data"}
        result = UpsertResult(
            action="updated",
            episode=episode,
            uuid="override-uuid",
            previous_uuid="prev-uuid"
        )

        assert result.action == "updated"
        assert result.episode == episode
        assert result.uuid == "override-uuid"
        assert result.previous_uuid == "prev-uuid"
