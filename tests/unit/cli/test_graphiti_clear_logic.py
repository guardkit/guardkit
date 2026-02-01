"""
Unit tests for graphiti clear command logic.

Test Coverage:
- Clear marker file removal
- Clear command validation logic
- Error handling in clear operations
- Flag validation and mutual exclusivity

AC-002: Unit tests for clear command logic
"""

import pytest
from pathlib import Path
import json
from unittest.mock import MagicMock, AsyncMock, patch

from guardkit.knowledge.seeding import (
    clear_seeding_marker,
    get_state_dir,
    is_seeded,
    mark_seeded,
)


class TestClearSeedingMarker:
    """Test clear_seeding_marker function."""

    def test_clear_seeding_marker_removes_file(self, tmp_path, monkeypatch):
        """Test that clear_seeding_marker removes the marker file."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        # Create marker file
        from guardkit.knowledge.seeding import mark_seeded, clear_seeding_marker, is_seeded

        mark_seeded()
        assert is_seeded()

        # Clear it
        clear_seeding_marker()

        # Verify removed
        assert not is_seeded()

    def test_clear_seeding_marker_safe_if_not_exists(self, tmp_path, monkeypatch):
        """Test that clear_seeding_marker is safe to call even if marker doesn't exist."""
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: tmp_path
        )

        from guardkit.knowledge.seeding import clear_seeding_marker, is_seeded

        # Verify no marker exists
        assert not is_seeded()

        # Should not raise exception
        clear_seeding_marker()

        # Still no marker
        assert not is_seeded()

    def test_clear_seeding_marker_creates_dir_if_needed(self, tmp_path, monkeypatch):
        """Test that clear_seeding_marker handles missing directory gracefully."""
        test_dir = tmp_path / "nonexistent" / "seeding"
        monkeypatch.setattr(
            "guardkit.knowledge.seeding.get_state_dir",
            lambda: test_dir
        )

        from guardkit.knowledge.seeding import clear_seeding_marker

        # Should not raise exception even if directory doesn't exist
        clear_seeding_marker()


class TestClearCommandValidation:
    """Test clear command validation logic."""

    @pytest.mark.asyncio
    async def test_system_and_project_only_are_mutually_exclusive(self):
        """Test that system_only and project_only cannot both be True."""
        from guardkit.cli.graphiti import _cmd_clear

        # This should raise SystemExit when both flags are set
        with pytest.raises(SystemExit):
            await _cmd_clear(
                confirm=True,
                system_only=True,
                project_only=True,
                dry_run=False,
                force=False
            )

    @pytest.mark.asyncio
    async def test_confirm_required_for_non_dry_run(self):
        """Test that confirm flag is required for non-dry-run operations."""
        from guardkit.cli.graphiti import _cmd_clear

        # This should raise SystemExit when confirm=False and dry_run=False
        with pytest.raises(SystemExit):
            await _cmd_clear(
                confirm=False,
                system_only=False,
                project_only=False,
                dry_run=False,
                force=False
            )

    @pytest.mark.asyncio
    async def test_dry_run_allows_no_confirm(self):
        """Test that dry-run mode doesn't require confirm flag."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": [],
                "project_groups": [],
                "total_groups": 0,
                "estimated_episodes": 0
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            # Should not raise exception
            await _cmd_clear(
                confirm=False,
                system_only=False,
                project_only=False,
                dry_run=True,
                force=False
            )


class TestClearErrorHandling:
    """Test error handling in clear operations."""

    @pytest.mark.asyncio
    async def test_clear_handles_disabled_client_gracefully(self):
        """Test that clear handles disabled client gracefully."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = False

            mock_settings = MagicMock()
            mock_settings.enabled = False
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            # Should not raise exception
            await _cmd_clear(
                confirm=True,
                system_only=False,
                project_only=False,
                dry_run=False,
                force=False
            )

    @pytest.mark.asyncio
    async def test_clear_handles_connection_failure(self):
        """Test that clear handles connection failures gracefully."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.initialize = AsyncMock(side_effect=Exception("Connection failed"))

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            # Should raise SystemExit due to connection failure
            with pytest.raises(SystemExit):
                await _cmd_clear(
                    confirm=True,
                    system_only=False,
                    project_only=False,
                    dry_run=False,
                    force=False
                )

    @pytest.mark.asyncio
    async def test_clear_handles_uninitialized_client(self):
        """Test that clear handles uninitialized client gracefully."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=False)
            mock_client.close = AsyncMock()

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            # Should handle gracefully
            await _cmd_clear(
                confirm=True,
                system_only=False,
                project_only=False,
                dry_run=False,
                force=False
            )


class TestClearPreviewGeneration:
    """Test clear preview generation."""

    @pytest.mark.asyncio
    async def test_preview_called_before_clear(self):
        """Test that get_clear_preview is called before clearing."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["test_group"],
                "project_groups": [],
                "total_groups": 1,
                "estimated_episodes": 10
            })
            mock_client.clear_all = AsyncMock(return_value={
                "system_groups_cleared": 1,
                "project_groups_cleared": 0,
                "total_episodes_deleted": 10
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            await _cmd_clear(
                confirm=True,
                system_only=False,
                project_only=False,
                dry_run=False,
                force=False
            )

            # Verify preview was called
            mock_client.get_clear_preview.assert_called_once()

            # Verify clear was called after preview
            mock_client.clear_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_preview_respects_system_only_flag(self):
        """Test that preview respects system_only flag."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": ["test_group"],
                "project_groups": [],
                "total_groups": 1,
                "estimated_episodes": 10
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            await _cmd_clear(
                confirm=False,
                system_only=True,
                project_only=False,
                dry_run=True,
                force=False
            )

            # Verify preview was called with system_only=True
            call_kwargs = mock_client.get_clear_preview.call_args.kwargs
            assert call_kwargs.get('system_only') is True

    @pytest.mark.asyncio
    async def test_preview_respects_project_only_flag(self):
        """Test that preview respects project_only flag."""
        with patch('guardkit.cli.graphiti._get_client_and_config') as mock_get_client:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.get_clear_preview = AsyncMock(return_value={
                "system_groups": [],
                "project_groups": ["test_project__overview"],
                "total_groups": 1,
                "estimated_episodes": 5
            })

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_get_client.return_value = (mock_client, mock_settings)

            from guardkit.cli.graphiti import _cmd_clear

            await _cmd_clear(
                confirm=False,
                system_only=False,
                project_only=True,
                dry_run=True,
                force=False
            )

            # Verify preview was called with project_only=True
            call_kwargs = mock_client.get_clear_preview.call_args.kwargs
            assert call_kwargs.get('project_only') is True
