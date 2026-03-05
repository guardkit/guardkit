"""
Tests for guardkit.knowledge.system_seeding

Coverage Target: >=85%
Test Count: 18 tests
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

try:
    from guardkit.knowledge.system_seeding import (
        SystemSeedComponentResult,
        SystemSeedResult,
        is_system_seeded,
        mark_system_seeded,
        clear_system_seed_marker,
        resolve_template_path,
        _seed_role_constraints_upsert,
        seed_system_content,
        SYSTEM_SEED_VERSION,
    )

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="system_seeding module not available",
)


# ============================================================================
# Helper: mock client factory
# ============================================================================


def _make_mock_client(enabled: bool = True):
    """Create a mock GraphitiClient for testing."""
    client = MagicMock()
    client.enabled = enabled
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.upsert_episode = AsyncMock(return_value=MagicMock(was_skipped=False))
    return client


# ============================================================================
# 1. SystemSeedResult dataclass tests (2 tests)
# ============================================================================


class TestSystemSeedResult:
    """Test SystemSeedResult dataclass."""

    def test_add_result_updates_totals(self):
        """Test that add_result accumulates episode counts."""
        result = SystemSeedResult(success=True)
        result.add_result(
            SystemSeedComponentResult(
                component="a", success=True, episodes_created=3, episodes_skipped=1
            )
        )
        result.add_result(
            SystemSeedComponentResult(
                component="b", success=True, episodes_created=2, episodes_skipped=0
            )
        )
        assert result.total_episodes == 5
        assert result.total_skipped == 1
        assert len(result.results) == 2

    def test_initial_state(self):
        """Test default field values."""
        result = SystemSeedResult(success=True)
        assert result.total_episodes == 0
        assert result.total_skipped == 0
        assert result.results == []
        assert result.template_name == ""


# ============================================================================
# 2. Seeding marker tests (4 tests)
# ============================================================================


class TestSystemSeedMarker:
    """Test marker file management."""

    def test_is_system_seeded_false_when_no_marker(self, tmp_path, monkeypatch):
        """Test returns False when marker does not exist."""
        monkeypatch.chdir(tmp_path)
        assert is_system_seeded() is False

    def test_mark_system_seeded_creates_file(self, tmp_path, monkeypatch):
        """Test that mark_system_seeded creates marker JSON."""
        monkeypatch.chdir(tmp_path)
        seed_result = SystemSeedResult(success=True, total_episodes=5)
        mark_system_seeded("fastapi-python", seed_result)

        marker_path = tmp_path / ".guardkit" / "seeding" / ".system_seeded.json"
        assert marker_path.exists()

        data = json.loads(marker_path.read_text())
        assert data["seeded"] is True
        assert data["version"] == SYSTEM_SEED_VERSION
        assert data["template"] == "fastapi-python"
        assert data["episodes_created"] == 5

    def test_is_system_seeded_true_after_marking(self, tmp_path, monkeypatch):
        """Test returns True after marking."""
        monkeypatch.chdir(tmp_path)
        seed_result = SystemSeedResult(success=True)
        mark_system_seeded("default", seed_result)
        assert is_system_seeded() is True

    def test_clear_system_seed_marker_removes_file(self, tmp_path, monkeypatch):
        """Test clearing removes the marker file."""
        monkeypatch.chdir(tmp_path)
        seed_result = SystemSeedResult(success=True)
        mark_system_seeded("default", seed_result)
        assert is_system_seeded() is True

        clear_system_seed_marker()
        assert is_system_seeded() is False

    def test_clear_system_seed_marker_noop_when_missing(self, tmp_path, monkeypatch):
        """Test clearing when no marker exists does not raise."""
        monkeypatch.chdir(tmp_path)
        clear_system_seed_marker()  # should not raise


# ============================================================================
# 3. Template resolution tests (4 tests)
# ============================================================================


class TestResolveTemplatePath:
    """Test template path resolution logic."""

    def test_explicit_template_name(self, tmp_path):
        """Test resolution with explicit template name."""
        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=tmp_path / "fastapi-python",
        ) as mock_resolve:
            result = resolve_template_path("fastapi-python")
            mock_resolve.assert_called_once_with("fastapi-python")
            assert result == tmp_path / "fastapi-python"

    def test_auto_detect_from_manifest(self, tmp_path, monkeypatch):
        """Test auto-detection from manifest.json in cwd."""
        monkeypatch.chdir(tmp_path)
        manifest = {"name": "react-typescript"}
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))

        expected_path = tmp_path / "react-typescript"
        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=expected_path,
        ):
            result = resolve_template_path(None)
            assert result == expected_path

    def test_fallback_to_default(self, tmp_path, monkeypatch):
        """Test fallback to 'default' when no manifest exists."""
        monkeypatch.chdir(tmp_path)
        expected_path = tmp_path / "default"
        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=expected_path,
        ):
            result = resolve_template_path(None)
            assert result == expected_path

    def test_returns_none_when_template_not_found(self):
        """Test returns None when template cannot be resolved."""
        with patch(
            "guardkit.cli.init._resolve_template_source_dir",
            return_value=None,
        ):
            result = resolve_template_path("nonexistent")
            assert result is None


# ============================================================================
# 4. Role constraints upsert tests (3 tests)
# ============================================================================


class TestSeedRoleConstraintsUpsert:
    """Test role constraints seeding via upsert."""

    @pytest.mark.asyncio
    async def test_seeds_player_and_coach(self):
        """Test that both player and coach constraints are seeded."""
        client = _make_mock_client()
        result = await _seed_role_constraints_upsert(client)

        assert result.success is True
        assert result.component == "role_constraints"
        assert result.episodes_created == 2
        assert client.upsert_episode.call_count == 2

        # Verify episode names
        call_args_list = client.upsert_episode.call_args_list
        names = [call.kwargs["name"] for call in call_args_list]
        assert any("player" in name for name in names)
        assert any("coach" in name for name in names)

    @pytest.mark.asyncio
    async def test_skips_when_client_disabled(self):
        """Test graceful skip when client is disabled."""
        client = _make_mock_client(enabled=False)
        result = await _seed_role_constraints_upsert(client)

        assert result.success is True
        assert "Skipped" in result.message
        assert result.episodes_created == 0
        client.upsert_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_client_is_none(self):
        """Test graceful skip when client is None."""
        result = await _seed_role_constraints_upsert(None)

        assert result.success is True
        assert "Skipped" in result.message
        assert result.episodes_created == 0

    @pytest.mark.asyncio
    async def test_handles_upsert_failure_gracefully(self):
        """Test that individual upsert failures don't crash."""
        client = _make_mock_client()
        client.upsert_episode = AsyncMock(side_effect=Exception("timeout"))

        result = await _seed_role_constraints_upsert(client)
        assert result.success is True
        assert result.episodes_created == 0

    @pytest.mark.asyncio
    async def test_counts_skipped_episodes(self):
        """Test that unchanged episodes are counted as skipped."""
        client = _make_mock_client()
        skipped_result = MagicMock(was_skipped=True)
        client.upsert_episode = AsyncMock(return_value=skipped_result)

        result = await _seed_role_constraints_upsert(client)
        assert result.episodes_skipped == 2
        assert result.episodes_created == 0


# ============================================================================
# 5. Main orchestrator tests (6 tests)
# ============================================================================


class TestSeedSystemContent:
    """Test the main seed_system_content orchestrator."""

    @pytest.mark.asyncio
    async def test_seeds_all_components(self, tmp_path, monkeypatch):
        """Test that all components are seeded sequentially."""
        monkeypatch.chdir(tmp_path)
        client = _make_mock_client()

        with patch(
            "guardkit.knowledge.system_seeding.resolve_template_path",
            return_value=tmp_path / "test-template",
        ), patch(
            "guardkit.knowledge.template_sync.sync_template_to_graphiti",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_sync, patch(
            "guardkit.knowledge.project_seeding.seed_implementation_modes_from_defaults",
            new_callable=AsyncMock,
        ) as mock_modes:
            from guardkit.knowledge.project_seeding import SeedComponentResult

            mock_modes.return_value = SeedComponentResult(
                component="implementation_modes",
                success=True,
                message="Seeded 3 modes",
                episodes_created=3,
            )

            result = await seed_system_content(client=client, force=True)

            assert result.success is True
            assert len(result.results) == 3  # template + constraints + modes
            mock_sync.assert_called_once()
            mock_modes.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_already_seeded(self, tmp_path, monkeypatch):
        """Test early return when marker exists and force=False."""
        monkeypatch.chdir(tmp_path)
        seed_result = SystemSeedResult(success=True)
        mark_system_seeded("default", seed_result)

        client = _make_mock_client()
        result = await seed_system_content(client=client, force=False)

        assert result.success is True
        assert len(result.results) == 1
        assert "Already seeded" in result.results[0].message

    @pytest.mark.asyncio
    async def test_force_reseeds_when_already_seeded(self, tmp_path, monkeypatch):
        """Test that force=True bypasses marker."""
        monkeypatch.chdir(tmp_path)
        seed_result = SystemSeedResult(success=True)
        mark_system_seeded("default", seed_result)

        client = _make_mock_client()

        with patch(
            "guardkit.knowledge.system_seeding.resolve_template_path",
            return_value=None,
        ), patch(
            "guardkit.knowledge.project_seeding.seed_implementation_modes_from_defaults",
            new_callable=AsyncMock,
        ) as mock_modes:
            from guardkit.knowledge.project_seeding import SeedComponentResult

            mock_modes.return_value = SeedComponentResult(
                component="implementation_modes",
                success=True,
                message="Seeded",
                episodes_created=3,
            )

            result = await seed_system_content(client=client, force=True)

            # Should proceed past marker check
            assert len(result.results) >= 2  # at least constraints + modes

    @pytest.mark.asyncio
    async def test_handles_no_template_found(self, tmp_path, monkeypatch):
        """Test graceful handling when no template is resolved."""
        monkeypatch.chdir(tmp_path)
        client = _make_mock_client()

        with patch(
            "guardkit.knowledge.system_seeding.resolve_template_path",
            return_value=None,
        ), patch(
            "guardkit.knowledge.project_seeding.seed_implementation_modes_from_defaults",
            new_callable=AsyncMock,
        ) as mock_modes:
            from guardkit.knowledge.project_seeding import SeedComponentResult

            mock_modes.return_value = SeedComponentResult(
                component="implementation_modes",
                success=True,
                message="Seeded",
                episodes_created=3,
            )

            result = await seed_system_content(client=client, force=True)

            # template_content should be skipped
            template_comp = next(
                r for r in result.results if r.component == "template_content"
            )
            assert "Skipped" in template_comp.message

    @pytest.mark.asyncio
    async def test_disabled_client_returns_failure(self, tmp_path, monkeypatch):
        """Test that a disabled client returns success=False."""
        monkeypatch.chdir(tmp_path)
        client = _make_mock_client(enabled=False)

        result = await seed_system_content(client=client, force=True)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_none_client_returns_failure(self, tmp_path, monkeypatch):
        """Test that None client returns success=False."""
        monkeypatch.chdir(tmp_path)

        result = await seed_system_content(client=None, force=True)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_template_sync_exception_handled(self, tmp_path, monkeypatch):
        """Test that template sync exceptions don't crash the orchestrator."""
        monkeypatch.chdir(tmp_path)
        client = _make_mock_client()

        with patch(
            "guardkit.knowledge.system_seeding.resolve_template_path",
            return_value=tmp_path / "bad-template",
        ), patch(
            "guardkit.knowledge.template_sync.sync_template_to_graphiti",
            new_callable=AsyncMock,
            side_effect=Exception("sync failed"),
        ), patch(
            "guardkit.knowledge.project_seeding.seed_implementation_modes_from_defaults",
            new_callable=AsyncMock,
        ) as mock_modes:
            from guardkit.knowledge.project_seeding import SeedComponentResult

            mock_modes.return_value = SeedComponentResult(
                component="implementation_modes",
                success=True,
                message="Seeded",
                episodes_created=3,
            )

            result = await seed_system_content(client=client, force=True)

            # Should still complete (graceful degradation) but report partial failure
            assert result.success is False  # component failure propagates
            template_comp = next(
                r for r in result.results if r.component == "template_content"
            )
            assert template_comp.success is False
            assert "Error" in template_comp.message
