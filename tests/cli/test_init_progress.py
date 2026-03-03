"""
Tests for episode progress indicator during Graphiti seeding.

TASK-IGR-005: Add episode progress indicator during seeding.

Tests:
- _ProgressClient wraps add_episode with progress display
- _ProgressClient shows warning on failure
- estimate_episode_count returns correct counts
- Total seeding time is displayed

Coverage Target: >=85%
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call

try:
    from guardkit.cli.init import _ProgressClient
    from guardkit.knowledge.project_seeding import estimate_episode_count

    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Progress indicator modules not available",
)


# ============================================================================
# 1. _ProgressClient Tests
# ============================================================================


class TestProgressClient:
    """Test the _ProgressClient proxy used during seeding."""

    @pytest.mark.asyncio
    async def test_progress_client_prints_episode_counter(self):
        """Test that add_episode prints N/M progress."""
        mock_client = MagicMock()
        mock_client.add_episode = AsyncMock(return_value="ep-id")
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=3, console_obj=mock_console)

        await proxy.add_episode(name="ep_1", episode_body="{}", group_id="g")
        await proxy.add_episode(name="ep_2", episode_body="{}", group_id="g")
        await proxy.add_episode(name="ep_3", episode_body="{}", group_id="g")

        # Should have called print for each episode (start + done = 2 calls each)
        assert mock_console.print.call_count == 6

        # Verify N/M pattern in the "start" prints (calls at index 0, 2, 4)
        start_calls = [mock_console.print.call_args_list[i] for i in (0, 2, 4)]
        assert "1/3" in start_calls[0].args[0]
        assert "2/3" in start_calls[1].args[0]
        assert "3/3" in start_calls[2].args[0]

    @pytest.mark.asyncio
    async def test_progress_client_shows_done_with_elapsed(self):
        """Test that successful episodes show 'done' with elapsed time."""
        mock_client = MagicMock()
        mock_client.add_episode = AsyncMock(return_value="ep-id")
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=1, console_obj=mock_console)
        await proxy.add_episode(name="ep_1", episode_body="{}", group_id="g")

        # Second print call should contain "done" and a time
        done_call = mock_console.print.call_args_list[1]
        assert "done" in done_call.args[0]
        assert "s)" in done_call.args[0]

    @pytest.mark.asyncio
    async def test_progress_client_shows_warning_on_failure(self):
        """Test that failed episodes show warning instead of done."""
        mock_client = MagicMock()
        mock_client.add_episode = AsyncMock(side_effect=RuntimeError("connection lost"))
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=1, console_obj=mock_console)

        with pytest.raises(RuntimeError, match="connection lost"):
            await proxy.add_episode(name="ep_1", episode_body="{}", group_id="g")

        # Second print call should contain "warning"
        warn_call = mock_console.print.call_args_list[1]
        assert "warning" in warn_call.args[0]
        assert "connection lost" in warn_call.args[0]

    @pytest.mark.asyncio
    async def test_progress_client_delegates_add_episode_args(self):
        """Test that add_episode args are forwarded to the real client."""
        mock_client = MagicMock()
        mock_client.add_episode = AsyncMock(return_value="ep-id")
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=1, console_obj=mock_console)
        await proxy.add_episode(
            name="test_ep",
            episode_body='{"key": "val"}',
            group_id="test_group",
            source="test_source",
        )

        mock_client.add_episode.assert_called_once_with(
            name="test_ep",
            episode_body='{"key": "val"}',
            group_id="test_group",
            source="test_source",
        )

    @pytest.mark.asyncio
    async def test_progress_client_returns_add_episode_result(self):
        """Test that add_episode return value is forwarded."""
        mock_client = MagicMock()
        mock_client.add_episode = AsyncMock(return_value="ep-123")
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=1, console_obj=mock_console)
        result = await proxy.add_episode(name="ep", episode_body="{}", group_id="g")

        assert result == "ep-123"

    def test_progress_client_delegates_enabled(self):
        """Test that .enabled delegates to the wrapped client."""
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=1, console_obj=mock_console)
        assert proxy.enabled is True

        mock_client.enabled = False
        proxy2 = _ProgressClient(mock_client, total=1, console_obj=mock_console)
        assert proxy2.enabled is False

    def test_progress_client_delegates_unknown_attributes(self):
        """Test that unknown attributes delegate to the wrapped client."""
        mock_client = MagicMock()
        mock_client.some_method.return_value = "hello"
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=1, console_obj=mock_console)
        assert proxy.some_method() == "hello"


# ============================================================================
# 2. estimate_episode_count Tests
# ============================================================================


class TestEstimateEpisodeCount:
    """Test the episode count estimator used for N/M display."""

    def test_count_with_skip_overview(self):
        """Test count when overview is skipped (constraints + modes only)."""
        # 2 role constraints + 3 implementation modes = 5
        count = estimate_episode_count(skip_overview=True)
        assert count == 5

    def test_count_with_interactive_episode(self):
        """Test count when a project_overview_episode is provided."""
        mock_episode = MagicMock()
        # 1 overview + 2 constraints + 3 modes = 6
        count = estimate_episode_count(
            skip_overview=False,
            project_overview_episode=mock_episode,
        )
        assert count == 6

    def test_count_with_no_doc_file(self, tmp_path):
        """Test count when no CLAUDE.md or README.md exists."""
        # 0 overview + 2 constraints + 3 modes = 5
        count = estimate_episode_count(
            skip_overview=False,
            project_dir=tmp_path,
        )
        assert count == 5

    def test_count_with_unparseable_doc(self, tmp_path):
        """Test count when doc exists but cannot be parsed."""
        (tmp_path / "CLAUDE.md").write_text("not a valid project doc")
        # Parser may return 0 episodes for unstructured content
        count = estimate_episode_count(
            skip_overview=False,
            project_dir=tmp_path,
        )
        # At minimum: 2 constraints + 3 modes = 5
        assert count >= 5


# ============================================================================
# 3. Integration: Progress during seed_project_knowledge
# ============================================================================


class TestSeedingWithProgress:
    """Test that _ProgressClient integrates with seed_project_knowledge."""

    @pytest.mark.asyncio
    async def test_seeding_calls_add_episode_through_proxy(self):
        """Test that seed_project_knowledge works with _ProgressClient."""
        from guardkit.knowledge.project_seeding import seed_project_knowledge

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(return_value="ep-id")
        mock_console = MagicMock()

        proxy = _ProgressClient(mock_client, total=5, console_obj=mock_console)

        result = await seed_project_knowledge(
            project_name="test-project",
            client=proxy,
        )

        assert result.success is True
        # The proxy should have intercepted add_episode calls
        # At minimum: 2 role constraints + 3 implementation modes = 5
        assert mock_client.add_episode.call_count >= 5
        # Each episode produces 2 prints (start + done)
        assert mock_console.print.call_count >= 10

    @pytest.mark.asyncio
    async def test_seeding_progress_with_none_client(self):
        """Test that seed_project_knowledge still works with None client."""
        from guardkit.knowledge.project_seeding import seed_project_knowledge

        # None client should still succeed (graceful degradation)
        result = await seed_project_knowledge(
            project_name="test-project",
            client=None,
        )
        assert result.success is True
