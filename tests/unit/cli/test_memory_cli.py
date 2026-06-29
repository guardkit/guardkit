"""Tests for guardkit memory CLI commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from click.testing import CliRunner

from guardkit.cli.memory import memory
from guardkit.cli.graphiti import graphiti


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_memory_client():
    """Mock memory client."""
    client = MagicMock()
    client.enabled = True
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.search = AsyncMock(return_value=[
        {"fact": "test fact", "uuid": "test-uuid", "score": 0.9}
    ])
    client.health_check = AsyncMock(return_value=True)
    return client


class TestMemorySearch:
    """Tests for guardkit memory search command."""

    @patch("guardkit.cli.memory.get_memory_client")
    def test_search_basic(self, mock_get_client, runner, mock_memory_client):
        """Test basic search returns results."""
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["search", "test query"])

        assert result.exit_code == 0
        assert "test fact" in result.output
        mock_memory_client.search.assert_called_once()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_search_with_token_budget(self, mock_get_client, runner, mock_memory_client):
        """Test search with --token-budget flag."""
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["search", "test query", "--token-budget", "500"])

        assert result.exit_code == 0
        mock_memory_client.search.assert_called_once()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_search_unreachable_store(self, mock_get_client, runner):
        """Test search shows graceful message when store is unreachable."""
        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        mock_get_client.return_value = mock_client

        result = runner.invoke(memory, ["search", "test query"])

        assert result.exit_code == 0
        assert "unavailable" in result.output.lower() or "unreachable" in result.output.lower()


class TestMemoryStatus:
    """Tests for guardkit memory status command."""

    @patch("guardkit.cli.memory.get_memory_client")
    def test_status_shows_reachability(self, mock_get_client, runner, mock_memory_client):
        """Test status shows store reachability."""
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["status"])

        assert result.exit_code == 0
        assert "reachable" in result.output.lower() or "connected" in result.output.lower()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_status_shows_payload_counts(self, mock_get_client, runner, mock_memory_client):
        """Test status shows per-payload_type counts."""
        # Mock search to return different payload types
        mock_memory_client.search = AsyncMock(side_effect=[
            [{"fact": "fact1"}],  # build_outcome
            [{"fact": "fact2"}, {"fact": "fact3"}],  # feature_spec
        ])
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["status"])

        assert result.exit_code == 0
        # Should show some form of counts/stats

    @patch("guardkit.cli.memory.get_memory_client")
    def test_status_unreachable_store(self, mock_get_client, runner):
        """Test status shows graceful message when store is unreachable."""
        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        mock_get_client.return_value = mock_client

        result = runner.invoke(memory, ["status"])

        assert result.exit_code == 0
        assert any(word in result.output.lower() for word in ["unavailable", "unreachable", "disabled"])


class TestMemoryCaptureOutcome:
    """Tests for guardkit memory capture-outcome command."""

    @patch("guardkit.cli.memory.get_memory_client")
    @patch("guardkit.cli.memory.capture_task_outcome")
    def test_capture_outcome_from_task_file(
        self, mock_capture, mock_get_client, runner, mock_memory_client, tmp_path
    ):
        """Test capture-outcome from task file."""
        # Create a mock task file
        task_file = tmp_path / "TASK-XXX.md"
        task_file.write_text("""---
id: TASK-XXX
title: Test Task
complexity: 5
---

## Description
Test task description

## Implementation Notes
Test implementation notes
""")

        mock_get_client.return_value = mock_memory_client
        mock_capture.return_value = "OUT-12345"

        result = runner.invoke(
            memory, ["capture-outcome", "--from-task-file", str(task_file)]
        )

        assert result.exit_code == 0
        assert "captured" in result.output.lower()
        mock_capture.assert_called_once()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_capture_outcome_unreachable_store(self, mock_get_client, runner, tmp_path):
        """Test capture-outcome shows graceful message when store is unreachable."""
        task_file = tmp_path / "TASK-XXX.md"
        task_file.write_text("""---
id: TASK-XXX
title: Test Task
---

## Description
Test description
""")

        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        mock_get_client.return_value = mock_client

        result = runner.invoke(
            memory, ["capture-outcome", "--from-task-file", str(task_file)]
        )

        # Should not fail but warn
        assert "unavailable" in result.output.lower() or "not captured" in result.output.lower()


class TestGraphitiDeprecation:
    """Tests for guardkit graphiti deprecation warnings."""

    def test_graphiti_search_warns_and_delegates(self, runner):
        """Test graphiti search emits deprecation warning and delegates."""
        with patch("guardkit.cli.graphiti._get_client_and_config") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=[])

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_get.return_value = (mock_client, mock_settings)

            result = runner.invoke(graphiti, ["search", "test query"])

            assert "deprecat" in result.output.lower()
            # Should still work
            assert result.exit_code == 0

    def test_graphiti_status_warns_and_delegates(self, runner):
        """Test graphiti status emits deprecation warning."""
        with patch("guardkit.cli.graphiti._get_client_and_config") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.search = AsyncMock(return_value=[])

            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_get.return_value = (mock_client, mock_settings)

            result = runner.invoke(graphiti, ["status"])

            assert "deprecat" in result.output.lower()

    def test_graphiti_capture_outcome_warns_and_delegates(self, runner, tmp_path):
        """Test graphiti capture-outcome emits deprecation warning."""
        task_file = tmp_path / "TASK-XXX.md"
        task_file.write_text("""---
id: TASK-XXX
title: Test Task
---

## Description
Test description
""")

        with patch("guardkit.cli.graphiti.get_graphiti") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.initialize = AsyncMock(return_value=True)
            mock_client.close = AsyncMock()
            mock_client.default_timeout_override = None
            mock_get.return_value = mock_client

            with patch("guardkit.knowledge.outcome_manager.capture_task_outcome") as mock_capture:
                mock_capture.return_value = AsyncMock(return_value="OUT-12345")

                result = runner.invoke(
                    graphiti, ["capture-outcome", "--from-task-file", str(task_file)]
                )

                assert "deprecat" in result.output.lower()
