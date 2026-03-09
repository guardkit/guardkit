"""
Unit tests for local file-based turn state capture and loading (TASK-RFX-5FED).

Tests:
- Local file write from _capture_turn_state
- Local file read from load_turn_continuation_context
- Fallback to Graphiti when local files missing
- _format_turn_state_body formatting

Coverage Target: >=85%
Test Count: 15 tests
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from guardkit.knowledge.turn_state_operations import (
    load_turn_continuation_context,
    _load_from_local_file,
    _format_turn_state_body,
)


# ============================================================================
# Test Data
# ============================================================================

SAMPLE_TURN_STATE = {
    "id": "TURN-FEAT-TEST-1",
    "feature_id": "FEAT-TEST",
    "task_id": "TASK-TEST-001",
    "turn_number": 1,
    "player_summary": "Implemented authentication endpoint",
    "player_decision": "implemented",
    "coach_decision": "feedback",
    "coach_feedback": "Add session caching",
    "mode": "fresh_start",
    "blockers_found": ["Missing Redis"],
    "progress_summary": "Turn 1: feedback",
    "acceptance_criteria_status": {
        "AC-001": "completed",
        "AC-002": "in_progress",
        "AC-003": "not_started",
    },
    "files_modified": ["src/auth.py", "tests/test_auth.py"],
    "tests_passed": 5,
    "tests_failed": 0,
    "coverage": 85.5,
    "arch_score": 78,
    "started_at": "2026-03-09T10:00:00",
    "completed_at": "2026-03-09T10:15:00",
    "duration_seconds": 900,
    "lessons_from_turn": ["Redis needed for sessions", "Use bcrypt for passwords"],
    "what_to_try_next": "Add Redis session caching",
}


# ============================================================================
# 1. _format_turn_state_body() Tests (4 tests)
# ============================================================================


class TestFormatTurnStateBody:
    """Test _format_turn_state_body() formatting function."""

    def test_basic_formatting(self):
        """Test basic turn state body formatting."""
        result = _format_turn_state_body(SAMPLE_TURN_STATE, 1)

        assert "## Previous Turn Summary (Turn 1)" in result
        assert "**What was attempted**: Implemented authentication endpoint" in result
        assert "**Player decision**: implemented" in result
        assert "**Coach decision**: feedback" in result

    def test_includes_coach_feedback(self):
        """Test that coach feedback is included when present."""
        result = _format_turn_state_body(SAMPLE_TURN_STATE, 1)
        assert "**Coach feedback**: Add session caching" in result

    def test_includes_blockers_and_lessons(self):
        """Test blockers and lessons are included."""
        result = _format_turn_state_body(SAMPLE_TURN_STATE, 1)
        assert "**Blockers found**: Missing Redis" in result
        assert "**Lessons learned**: Redis needed for sessions; Use bcrypt for passwords" in result
        assert "**Suggested focus for this turn**: Add Redis session caching" in result

    def test_includes_acceptance_criteria_status(self):
        """Test acceptance criteria status with correct icons."""
        result = _format_turn_state_body(SAMPLE_TURN_STATE, 1)
        assert "**Acceptance Criteria Status**:" in result
        assert "✓ AC-001: completed" in result
        assert "○ AC-002: in_progress" in result
        assert "○ AC-003: not_started" in result

    def test_minimal_body(self):
        """Test formatting with minimal fields."""
        body = {
            "player_summary": "Did something",
            "player_decision": "implemented",
            "coach_decision": "approved",
        }
        result = _format_turn_state_body(body, 2)
        assert "## Previous Turn Summary (Turn 2)" in result
        assert "**What was attempted**: Did something" in result
        # No optional fields
        assert "**Coach feedback**" not in result
        assert "**Blockers found**" not in result

    def test_empty_body_uses_defaults(self):
        """Test formatting with empty body uses 'Unknown' defaults."""
        result = _format_turn_state_body({}, 1)
        assert "**What was attempted**: Unknown" in result
        assert "**Player decision**: Unknown" in result


# ============================================================================
# 2. _load_from_local_file() Tests (4 tests)
# ============================================================================


class TestLoadFromLocalFile:
    """Test _load_from_local_file() function."""

    def test_loads_existing_file(self, tmp_path):
        """Test loading from an existing local turn state file."""
        state_file = tmp_path / "turn_state_turn_1.json"
        state_file.write_text(json.dumps(SAMPLE_TURN_STATE))

        result = _load_from_local_file(tmp_path, 1, "TASK-TEST-001")

        assert result is not None
        assert "Implemented authentication endpoint" in result
        assert "Turn 1" in result

    def test_returns_none_for_missing_file(self, tmp_path):
        """Test returns None when file doesn't exist."""
        result = _load_from_local_file(tmp_path, 1, "TASK-TEST-001")
        assert result is None

    def test_returns_none_for_invalid_json(self, tmp_path):
        """Test returns None for malformed JSON."""
        state_file = tmp_path / "turn_state_turn_1.json"
        state_file.write_text("not valid json{{{")

        result = _load_from_local_file(tmp_path, 1, "TASK-TEST-001")
        assert result is None

    def test_returns_none_for_empty_body(self, tmp_path):
        """Test returns None for empty/null body."""
        state_file = tmp_path / "turn_state_turn_1.json"
        state_file.write_text("null")

        result = _load_from_local_file(tmp_path, 1, "TASK-TEST-001")
        assert result is None


# ============================================================================
# 3. load_turn_continuation_context() Integration Tests (6 tests)
# ============================================================================


class TestLoadTurnContinuationContextLocal:
    """Test load_turn_continuation_context() with local file support."""

    @pytest.mark.asyncio
    async def test_turn_1_returns_none(self):
        """Test turn 1 always returns None regardless of autobuild_dir."""
        result = await load_turn_continuation_context(
            graphiti_client=None,
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            current_turn=1,
            autobuild_dir=Path("/tmp/fake"),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_local_file_preferred_over_graphiti(self, tmp_path):
        """Test local file is used when available, Graphiti not called."""
        # Write local file
        state_file = tmp_path / "turn_state_turn_1.json"
        state_file.write_text(json.dumps(SAMPLE_TURN_STATE))

        # Create mock Graphiti client that should NOT be called
        mock_client = AsyncMock()
        mock_client.enabled = True

        result = await load_turn_continuation_context(
            graphiti_client=mock_client,
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            current_turn=2,
            autobuild_dir=tmp_path,
        )

        assert result is not None
        assert "Implemented authentication endpoint" in result
        # Graphiti should NOT be called when local file exists
        mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_graphiti_when_no_local_file(self, tmp_path):
        """Test falls back to Graphiti when local file not found."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": SAMPLE_TURN_STATE}])

        result = await load_turn_continuation_context(
            graphiti_client=mock_client,
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            current_turn=2,
            autobuild_dir=tmp_path,  # Empty dir - no local file
        )

        assert result is not None
        # Graphiti should be called as fallback
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_autobuild_dir_uses_graphiti(self):
        """Test without autobuild_dir goes directly to Graphiti."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[{"body": SAMPLE_TURN_STATE}])

        result = await load_turn_continuation_context(
            graphiti_client=mock_client,
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            current_turn=2,
            # No autobuild_dir
        )

        assert result is not None
        mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_local_file_no_graphiti_returns_none(self, tmp_path):
        """Test returns None when no local file and no Graphiti."""
        result = await load_turn_continuation_context(
            graphiti_client=None,
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            current_turn=2,
            autobuild_dir=tmp_path,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_backward_compatible_without_autobuild_dir(self):
        """Test backward compatibility - works without autobuild_dir parameter."""
        mock_client = AsyncMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        # Call without autobuild_dir (old call signature)
        result = await load_turn_continuation_context(
            graphiti_client=mock_client,
            feature_id="FEAT-TEST",
            task_id="TASK-TEST-001",
            current_turn=2,
        )

        assert result is None  # No results from Graphiti
        mock_client.search.assert_called_once()


# ============================================================================
# 4. _capture_turn_state Local File Write Tests (4 tests)
# ============================================================================


class TestCaptureTurnStateLocalFile:
    """Test _capture_turn_state() local file writing."""

    def _make_orchestrator(self):
        """Create a minimal AutoBuildOrchestrator for testing."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch.object(AutoBuildOrchestrator, '__init__', lambda self, **kw: None):
            orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
            orch.enable_context = False
            orch._factory = None
            orch._thread_loaders = {}
            orch._shutting_down = False
            orch.recovery_count = 0
            return orch

    def _make_turn_record(self, turn=1, decision="feedback"):
        """Create a mock TurnRecord."""
        record = Mock()
        record.turn = turn
        record.decision = decision
        record.feedback = "Add more tests"
        record.player_result = Mock()
        record.player_result.report = {
            "summary": "Implemented feature X",
            "blockers": [],
            "files_modified": ["src/main.py"],
            "files_created": ["tests/test_main.py"],
        }
        record.player_result.error = None
        record.coach_result = Mock()
        record.coach_result.report = {
            "lessons": ["Use dependency injection"],
            "focus_for_next_turn": "Refactor service layer",
            "acceptance_criteria_verification": {
                "criteria_results": [
                    {"criterion_id": "AC-001", "status": "verified"},
                    {"criterion_id": "AC-002", "status": "not_started"},
                ]
            },
            "validation_results": {"tests_passed": True},
            "architecture_review": {},
        }
        return record

    def test_writes_local_file(self, tmp_path):
        """Test that _capture_turn_state writes a local JSON file."""
        orch = self._make_orchestrator()
        turn_record = self._make_turn_record(turn=1)

        orch._capture_turn_state(
            turn_record=turn_record,
            acceptance_criteria=["AC-001", "AC-002"],
            task_id="TASK-TEST-001",
            worktree_path=tmp_path,
        )

        state_file = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST-001" / "turn_state_turn_1.json"
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["task_id"] == "TASK-TEST-001"
        assert data["turn_number"] == 1
        assert data["player_summary"] == "Implemented feature X"
        assert data["coach_decision"] == "feedback"

    def test_writes_multiple_turns(self, tmp_path):
        """Test writing multiple turn state files."""
        orch = self._make_orchestrator()

        for turn_num in [1, 2, 3]:
            turn_record = self._make_turn_record(turn=turn_num)
            orch._capture_turn_state(
                turn_record=turn_record,
                acceptance_criteria=["AC-001"],
                task_id="TASK-TEST-001",
                worktree_path=tmp_path,
            )

        autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST-001"
        assert (autobuild_dir / "turn_state_turn_1.json").exists()
        assert (autobuild_dir / "turn_state_turn_2.json").exists()
        assert (autobuild_dir / "turn_state_turn_3.json").exists()

    def test_no_file_when_no_worktree_path(self, tmp_path):
        """Test no file written when worktree_path is None."""
        orch = self._make_orchestrator()
        turn_record = self._make_turn_record(turn=1)

        orch._capture_turn_state(
            turn_record=turn_record,
            acceptance_criteria=["AC-001"],
            task_id="TASK-TEST-001",
            worktree_path=None,  # No worktree path
        )

        # No file should be created
        autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST-001"
        assert not autobuild_dir.exists()

    def test_roundtrip_write_then_read(self, tmp_path):
        """Test that data written by _capture_turn_state can be read by load_turn_continuation_context."""
        orch = self._make_orchestrator()
        turn_record = self._make_turn_record(turn=1)

        # Write
        orch._capture_turn_state(
            turn_record=turn_record,
            acceptance_criteria=["AC-001", "AC-002"],
            task_id="TASK-TEST-001",
            worktree_path=tmp_path,
        )

        # Read
        autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST-001"
        result = _load_from_local_file(autobuild_dir, 1, "TASK-TEST-001")

        assert result is not None
        assert "Implemented feature X" in result
        assert "feedback" in result
        assert "AC-001" in result
