"""Tests for [Graphiti] structured logging in write-path files.

Verifies TASK-FIX-GG03: consistent [Graphiti] prefixed log messages in
turn_state_operations.py, outcome_manager.py, failed_approach_manager.py,
and template_sync.py.

Coverage Target: >=85%
Test Count: 8 tests
"""

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# turn_state_operations.py logging
# ---------------------------------------------------------------------------


class TestTurnStateOperationsLogging:
    """Tests for [Graphiti] logging in turn_state_operations."""

    @pytest.fixture
    def mock_entity(self):
        from guardkit.knowledge.entities.turn_state import TurnStateEntity, TurnMode
        from datetime import datetime

        return TurnStateEntity(
            id="TURN-FEAT-1",
            feature_id="FEAT-1",
            task_id="TASK-001",
            turn_number=1,
            player_summary="Implemented feature",
            player_decision="implemented",
            coach_decision="approved",
            coach_feedback=None,
            mode=TurnMode.FRESH_START,
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    async def test_capture_logs_graphiti_prefix_on_success(self, mock_entity, caplog):
        from guardkit.knowledge.turn_state_operations import capture_turn_state

        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock()

        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.turn_state_operations"):
            await capture_turn_state(client, mock_entity)

        assert any(
            "[Graphiti] Captured turn state:" in r.message
            for r in caplog.records
        )

    async def test_capture_logs_graphiti_prefix_on_client_none(self, mock_entity, caplog):
        from guardkit.knowledge.turn_state_operations import capture_turn_state

        with caplog.at_level(logging.DEBUG, logger="guardkit.knowledge.turn_state_operations"):
            await capture_turn_state(None, mock_entity)

        assert any(
            "[Graphiti] Client unavailable" in r.message
            for r in caplog.records
        )

    async def test_capture_logs_graphiti_prefix_on_error(self, mock_entity, caplog):
        from guardkit.knowledge.turn_state_operations import capture_turn_state

        client = AsyncMock()
        client.enabled = True
        client.add_episode = AsyncMock(side_effect=Exception("connection lost"))

        with caplog.at_level(logging.WARNING, logger="guardkit.knowledge.turn_state_operations"):
            await capture_turn_state(client, mock_entity)

        assert any(
            "[Graphiti] Failed to capture turn state" in r.message
            for r in caplog.records
        )

    async def test_load_context_logs_graphiti_prefix_on_error(self, caplog):
        from guardkit.knowledge.turn_state_operations import load_turn_continuation_context

        client = AsyncMock()
        client.enabled = True
        client.search = AsyncMock(side_effect=Exception("timeout"))

        with caplog.at_level(logging.WARNING, logger="guardkit.knowledge.turn_state_operations"):
            await load_turn_continuation_context(client, "FEAT-1", "TASK-001", 2)

        assert any(
            "[Graphiti] Failed to load turn continuation context" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# outcome_manager.py logging
# ---------------------------------------------------------------------------


class TestOutcomeManagerLogging:
    """Tests for [Graphiti] logging in outcome_manager."""

    async def test_capture_logs_graphiti_prefix_on_success(self, caplog):
        from guardkit.knowledge.outcome_manager import capture_task_outcome
        from guardkit.knowledge.entities.outcome import OutcomeType

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        with patch("guardkit.knowledge.outcome_manager.get_graphiti", return_value=mock_client):
            with caplog.at_level(logging.INFO, logger="guardkit.knowledge.outcome_manager"):
                await capture_task_outcome(
                    outcome_type=OutcomeType.TASK_COMPLETED,
                    task_id="TASK-001",
                    task_title="Test",
                    task_requirements="Test req",
                    success=True,
                    summary="Done",
                )

        assert any(
            "[Graphiti] Captured task outcome" in r.message
            for r in caplog.records
        )

    async def test_capture_logs_graphiti_prefix_on_failure(self, caplog):
        from guardkit.knowledge.outcome_manager import capture_task_outcome
        from guardkit.knowledge.entities.outcome import OutcomeType

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("fail"))

        with patch("guardkit.knowledge.outcome_manager.get_graphiti", return_value=mock_client):
            with caplog.at_level(logging.WARNING, logger="guardkit.knowledge.outcome_manager"):
                await capture_task_outcome(
                    outcome_type=OutcomeType.TASK_COMPLETED,
                    task_id="TASK-001",
                    task_title="Test",
                    task_requirements="Test req",
                    success=True,
                    summary="Done",
                )

        assert any(
            "[Graphiti] Failed to store outcome" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# failed_approach_manager.py logging
# ---------------------------------------------------------------------------


class TestFailedApproachManagerLogging:
    """Tests for [Graphiti] logging in failed_approach_manager."""

    async def test_capture_logs_graphiti_prefix_on_success(self, caplog):
        from guardkit.knowledge.failed_approach_manager import capture_failed_approach
        from guardkit.knowledge.entities.failed_approach import Severity

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        with patch("guardkit.knowledge.failed_approach_manager.get_graphiti", return_value=mock_client):
            with caplog.at_level(logging.INFO, logger="guardkit.knowledge.failed_approach_manager"):
                await capture_failed_approach(
                    approach="bad approach",
                    symptom="error",
                    root_cause="reason",
                    fix_applied="fix",
                    prevention="prevent",
                    context="test",
                )

        assert any(
            "[Graphiti] Captured failed approach" in r.message
            for r in caplog.records
        )

    async def test_capture_logs_graphiti_prefix_on_failure(self, caplog):
        from guardkit.knowledge.failed_approach_manager import capture_failed_approach

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock(side_effect=Exception("fail"))

        with patch("guardkit.knowledge.failed_approach_manager.get_graphiti", return_value=mock_client):
            with caplog.at_level(logging.WARNING, logger="guardkit.knowledge.failed_approach_manager"):
                await capture_failed_approach(
                    approach="bad approach",
                    symptom="error",
                    root_cause="reason",
                    fix_applied="fix",
                    prevention="prevent",
                    context="test",
                )

        assert any(
            "[Graphiti] Failed to store failed approach" in r.message
            for r in caplog.records
        )


# ---------------------------------------------------------------------------
# template_sync.py logging
# ---------------------------------------------------------------------------


class TestTemplateSyncLogging:
    """Tests for [Graphiti] logging in template_sync."""

    async def test_sync_template_logs_graphiti_prefix_on_success(self, tmp_path, caplog):
        from guardkit.knowledge.template_sync import sync_template_to_graphiti

        manifest = {"name": "test-template", "display_name": "Test", "language": "python"}
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.add_episode = AsyncMock()

        with patch("guardkit.knowledge.template_sync.get_graphiti", return_value=mock_client):
            with caplog.at_level(logging.INFO, logger="guardkit.knowledge.template_sync"):
                await sync_template_to_graphiti(tmp_path)

        assert any(
            "[Graphiti] Synced template" in r.message
            for r in caplog.records
        )

    async def test_sync_template_logs_graphiti_prefix_on_client_none(self, tmp_path, caplog):
        from guardkit.knowledge.template_sync import sync_template_to_graphiti

        with patch("guardkit.knowledge.template_sync.get_graphiti", return_value=None):
            with caplog.at_level(logging.WARNING, logger="guardkit.knowledge.template_sync"):
                result = await sync_template_to_graphiti(tmp_path)

        assert result is False
        assert any(
            "[Graphiti] Template sync skipped" in r.message
            for r in caplog.records
        )
