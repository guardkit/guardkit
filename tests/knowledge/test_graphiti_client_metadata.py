"""Tests for GraphitiClient metadata integration in add_episode().

This test suite validates that add_episode() correctly handles EpisodeMetadata:
- Backward compatibility (existing callers work)
- Explicit metadata parameter
- Auto-generation when not provided
- Metadata injection into episode_body
- Proper JSON formatting in _metadata block
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig
from guardkit.integrations.graphiti.metadata import EpisodeMetadata
from guardkit.integrations.graphiti.constants import SourceType


@pytest.fixture
def client():
    """Create GraphitiClient instance for testing."""
    config = GraphitiConfig(
        enabled=True,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password123",
        project_id="test-project"
    )
    return GraphitiClient(config)


@pytest.mark.asyncio
async def test_add_episode_backward_compatibility(client):
    """Test backward compatibility - existing callers work without metadata parameter.

    Validates that calling add_episode() with old signature (4 params)
    continues to work without breaking changes.
    """
    # Mock _create_episode to avoid actual Neo4j calls
    client._create_episode = AsyncMock(return_value="episode-uuid-123")

    # Old signature: name, episode_body, group_id, scope
    result = await client.add_episode(
        name="Test Episode",
        episode_body="Original content without metadata",
        group_id="test_group",
        scope="system"
    )

    # Should still return episode UUID
    assert result == "episode-uuid-123"

    # _create_episode should have been called
    client._create_episode.assert_called_once()

    # Verify the episode_body passed to _create_episode contains metadata
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']

    # Should contain original content
    assert "Original content without metadata" in episode_body_arg

    # Should contain auto-generated metadata block
    assert "_metadata" in episode_body_arg


@pytest.mark.asyncio
async def test_add_episode_with_explicit_metadata(client):
    """Test add_episode accepts EpisodeMetadata parameter.

    Validates that explicit metadata is used when provided,
    instead of auto-generating it.
    """
    # Create explicit metadata
    explicit_metadata = EpisodeMetadata.create_now(
        source=SourceType.GUARDKIT_SEEDING,
        entity_type="project_overview",
        version="2.0.0",
        project_id="test-project",
        tags=["important", "seed-data"]
    )

    # Mock _create_episode
    client._create_episode = AsyncMock(return_value="episode-uuid-456")

    # Call with explicit metadata
    result = await client.add_episode(
        name="Project Overview",
        episode_body="This is a project overview",
        group_id="project_overview",
        metadata=explicit_metadata
    )

    # Should return UUID
    assert result == "episode-uuid-456"

    # Verify metadata was injected
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']

    # Extract metadata from episode_body
    assert "_metadata" in episode_body_arg
    metadata_json = episode_body_arg.split("```json")[1].split("```")[0].strip()
    metadata_dict = json.loads(metadata_json)

    # Verify it matches our explicit metadata
    assert metadata_dict["source"] == "guardkit_seeding"
    assert metadata_dict["entity_type"] == "project_overview"
    assert metadata_dict["version"] == "2.0.0"
    assert metadata_dict["project_id"] == "test-project"
    assert metadata_dict["tags"] == ["important", "seed-data"]


@pytest.mark.asyncio
async def test_add_episode_auto_generates_metadata(client):
    """Test metadata is auto-generated when not provided.

    Validates that if metadata parameter is None, the system
    auto-generates metadata using source and entity_type parameters.
    """
    # Mock _create_episode
    client._create_episode = AsyncMock(return_value="episode-uuid-789")

    # Call without metadata parameter
    result = await client.add_episode(
        name="Test Episode",
        episode_body="Content without explicit metadata",
        group_id="test_group",
        source="user_added",
        entity_type="feature_spec"
    )

    # Should return UUID
    assert result == "episode-uuid-789"

    # Verify auto-generated metadata was injected
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']

    # Extract metadata
    assert "_metadata" in episode_body_arg
    metadata_json = episode_body_arg.split("```json")[1].split("```")[0].strip()
    metadata_dict = json.loads(metadata_json)

    # Verify auto-generated fields
    assert metadata_dict["source"] == "user_added"
    assert metadata_dict["entity_type"] == "feature_spec"
    assert metadata_dict["version"] == "1.0.0"  # Default version
    assert "created_at" in metadata_dict

    # Verify timestamp format (ISO 8601 with Z)
    created_at = metadata_dict["created_at"]
    assert created_at.endswith("Z")
    datetime.fromisoformat(created_at.replace('Z', '+00:00'))  # Should not raise


@pytest.mark.asyncio
async def test_add_episode_injects_metadata_block(client):
    """Test metadata appears in episode_body as a structured block.

    Validates that the metadata is injected in a well-formatted
    markdown block that won't interfere with content.
    """
    # Mock _create_episode
    client._create_episode = AsyncMock(return_value="episode-uuid-abc")

    # Create explicit metadata
    metadata = EpisodeMetadata.create_now(
        source="guardkit_seeding",
        entity_type="decision_record",
        entity_id="ADR-001"
    )

    # Call add_episode
    await client.add_episode(
        name="ADR-001",
        episode_body="We decided to use PostgreSQL for storage.",
        group_id="architecture_decisions",
        metadata=metadata
    )

    # Get the injected episode_body
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']

    # Should contain original content
    assert "We decided to use PostgreSQL for storage." in episode_body_arg

    # Should contain metadata block with proper formatting
    assert "---" in episode_body_arg  # Separator
    assert "_metadata:" in episode_body_arg
    assert "```json" in episode_body_arg
    assert "```" in episode_body_arg

    # Should be at the end of the content
    lines = episode_body_arg.strip().split('\n')
    assert lines[-1] == "```"  # Closing fence
    assert "_metadata:" in episode_body_arg.split("---")[-1]


@pytest.mark.asyncio
async def test_add_episode_metadata_format(client):
    """Test _metadata key contains valid JSON with correct structure.

    Validates that the metadata JSON is valid and contains all
    required fields in the correct format.
    """
    # Mock _create_episode
    client._create_episode = AsyncMock(return_value="episode-uuid-def")

    # Create metadata with all fields
    metadata = EpisodeMetadata.create_now(
        source="auto_captured",
        entity_type="constraint",
        version="1.2.3",
        project_id="my-project",
        entity_id="CONST-001",
        source_path="/path/to/source.md",
        tags=["performance", "security"]
    )

    # Call add_episode
    await client.add_episode(
        name="Performance Constraint",
        episode_body="API response time must be <200ms",
        group_id="constraints",
        metadata=metadata
    )

    # Extract and validate metadata JSON
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']

    metadata_section = episode_body_arg.split("_metadata:")[1]
    metadata_json = metadata_section.split("```json")[1].split("```")[0].strip()

    # Should be valid JSON
    metadata_dict = json.loads(metadata_json)

    # Verify all fields
    assert metadata_dict["source"] == "auto_captured"
    assert metadata_dict["entity_type"] == "constraint"
    assert metadata_dict["version"] == "1.2.3"
    assert metadata_dict["project_id"] == "my-project"
    assert metadata_dict["entity_id"] == "CONST-001"
    assert metadata_dict["source_path"] == "/path/to/source.md"
    assert metadata_dict["tags"] == ["performance", "security"]
    assert "created_at" in metadata_dict


@pytest.mark.asyncio
async def test_add_episode_uses_source_parameter(client):
    """Test source parameter creates metadata with correct source value.

    Validates that the source parameter (new) is used when generating
    metadata, instead of requiring explicit EpisodeMetadata.
    """
    # Mock _create_episode
    client._create_episode = AsyncMock(return_value="episode-uuid-ghi")

    # Call with source parameter
    await client.add_episode(
        name="Test Episode",
        episode_body="Some content",
        group_id="test_group",
        source="guardkit_seeding",  # Should be used in metadata
        entity_type="domain_term"
    )

    # Extract metadata
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']
    metadata_json = episode_body_arg.split("```json")[1].split("```")[0].strip()
    metadata_dict = json.loads(metadata_json)

    # Verify source was used
    assert metadata_dict["source"] == "guardkit_seeding"


@pytest.mark.asyncio
async def test_add_episode_uses_entity_type_parameter(client):
    """Test entity_type parameter creates metadata with correct entity_type.

    Validates that the entity_type parameter (new) is used when generating
    metadata.
    """
    # Mock _create_episode
    client._create_episode = AsyncMock(return_value="episode-uuid-jkl")

    # Call with entity_type parameter
    await client.add_episode(
        name="Test Episode",
        episode_body="Some content",
        group_id="test_group",
        source="user_added",
        entity_type="quality_gate_config"  # Should be used in metadata
    )

    # Extract metadata
    call_args = client._create_episode.call_args
    episode_body_arg = call_args.kwargs['episode_body']
    metadata_json = episode_body_arg.split("```json")[1].split("```")[0].strip()
    metadata_dict = json.loads(metadata_json)

    # Verify entity_type was used
    assert metadata_dict["entity_type"] == "quality_gate_config"


@pytest.mark.asyncio
async def test_inject_metadata_creates_valid_json(client):
    """Test _inject_metadata helper creates well-formatted output.

    Validates that the (yet to be implemented) _inject_metadata method
    produces valid JSON and proper markdown formatting.
    """
    # Create metadata
    metadata = EpisodeMetadata.create_now(
        source="user_added",
        entity_type="feature_spec",
        tags=["test"]
    )

    # This should be a helper method on GraphitiClient
    # For now, test will fail as it doesn't exist yet
    result = client._inject_metadata("Original content", metadata)

    # Should contain original content
    assert "Original content" in result

    # Should contain metadata block
    assert "---" in result
    assert "_metadata:" in result
    assert "```json" in result

    # Metadata should be valid JSON
    metadata_section = result.split("_metadata:")[1]
    metadata_json = metadata_section.split("```json")[1].split("```")[0].strip()
    metadata_dict = json.loads(metadata_json)

    # Verify structure
    assert metadata_dict["source"] == "user_added"
    assert metadata_dict["entity_type"] == "feature_spec"
    assert metadata_dict["tags"] == ["test"]
