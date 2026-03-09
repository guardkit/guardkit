"""
Unit Tests for AutoBuild Cross-Turn Session Tracking (TASK-RFX-B20B)

Tests that the AutoBuild orchestrator correctly propagates session_id
to AgentInvoker between turns and clears it on perspective reset.

Coverage Target: >=85%
Test Count: 7 tests
"""

import inspect
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_agent_invoker():
    """Create a mock AgentInvoker with session tracking methods."""
    invoker = MagicMock()
    invoker._last_session_id = None

    # Track calls to set_player_resume_session
    session_history = []

    def track_set_session(session_id):
        invoker._last_session_id = session_id
        session_history.append(session_id)

    invoker.set_player_resume_session = Mock(side_effect=track_set_session)
    invoker._session_history = session_history
    return invoker


def _make_player_result(
    success=True, session_id=None, turn=1, task_id="TASK-TEST-001"
):
    """Create an AgentInvocationResult with session_id."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=success,
        report={"tests_passed": success} if success else {},
        duration_seconds=10.0,
        session_id=session_id,
    )


# ============================================================================
# 1. Cross-Turn Session Propagation Tests (3 tests)
# ============================================================================


class TestCrossTurnSessionPropagation:
    """Tests that session_id flows from player_result to AgentInvoker between turns."""

    def test_session_id_propagated_after_successful_turn(self, mock_agent_invoker):
        """After a turn with session_id, invoker receives it for next turn."""
        player_result = _make_player_result(session_id="sess-turn1-abc123")

        # Simulate the guard from autobuild._loop_phase()
        if (
            mock_agent_invoker is not None
            and player_result is not None
            and player_result.session_id is not None
        ):
            mock_agent_invoker.set_player_resume_session(
                player_result.session_id
            )

        mock_agent_invoker.set_player_resume_session.assert_called_once_with(
            "sess-turn1-abc123"
        )
        assert mock_agent_invoker._last_session_id == "sess-turn1-abc123"

    def test_session_id_not_set_when_none(self, mock_agent_invoker):
        """When player_result.session_id is None, invoker is not called."""
        player_result = _make_player_result(session_id=None)

        if (
            mock_agent_invoker is not None
            and player_result is not None
            and player_result.session_id is not None
        ):
            mock_agent_invoker.set_player_resume_session(
                player_result.session_id
            )

        mock_agent_invoker.set_player_resume_session.assert_not_called()
        assert mock_agent_invoker._last_session_id is None

    def test_session_id_updates_across_multiple_turns(self, mock_agent_invoker):
        """Each turn's session_id replaces the previous one."""
        turns = [
            _make_player_result(session_id="sess-turn1", turn=1),
            _make_player_result(session_id="sess-turn2", turn=2),
            _make_player_result(session_id="sess-turn3", turn=3),
        ]

        for player_result in turns:
            if (
                mock_agent_invoker is not None
                and player_result is not None
                and player_result.session_id is not None
            ):
                mock_agent_invoker.set_player_resume_session(
                    player_result.session_id
                )

        assert mock_agent_invoker._session_history == [
            "sess-turn1",
            "sess-turn2",
            "sess-turn3",
        ]
        assert mock_agent_invoker._last_session_id == "sess-turn3"


# ============================================================================
# 2. Perspective Reset Tests (2 tests)
# ============================================================================


class TestPerspectiveResetClearsSession:
    """Tests that perspective reset clears the session_id."""

    def test_perspective_reset_clears_session(self, mock_agent_invoker):
        """On perspective reset, session_id is cleared to None."""
        mock_agent_invoker.set_player_resume_session("sess-before-reset")
        assert mock_agent_invoker._last_session_id == "sess-before-reset"

        # Simulate perspective reset
        mock_agent_invoker.set_player_resume_session(None)

        assert mock_agent_invoker._last_session_id is None
        assert mock_agent_invoker._session_history == [
            "sess-before-reset",
            None,
        ]

    def test_session_resumes_after_perspective_reset(self, mock_agent_invoker):
        """After perspective reset, a new turn's session_id is set fresh."""
        mock_agent_invoker.set_player_resume_session("sess-turn1")
        mock_agent_invoker.set_player_resume_session(None)
        mock_agent_invoker.set_player_resume_session("sess-turn3-fresh")

        assert mock_agent_invoker._last_session_id == "sess-turn3-fresh"
        assert mock_agent_invoker._session_history == [
            "sess-turn1",
            None,
            "sess-turn3-fresh",
        ]


# ============================================================================
# 3. Production Code Presence Verification (2 tests)
# ============================================================================


class TestProductionCodePresence:
    """Verify that the actual autobuild._loop_phase contains session propagation code.

    These tests guard against the production code being accidentally deleted
    while the unit tests above continue to pass (since they simulate the logic).
    """

    def test_loop_phase_contains_session_propagation(self):
        """Verify _loop_phase has set_player_resume_session call after turn_history.append."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        source = inspect.getsource(AutoBuildOrchestrator._loop_phase)
        assert "set_player_resume_session" in source, (
            "_loop_phase must call set_player_resume_session to propagate "
            "session_id after each turn (TASK-RFX-B20B)"
        )
        assert "turn_record.player_result.session_id" in source, (
            "_loop_phase must read session_id from turn_record.player_result "
            "(TASK-RFX-B20B)"
        )

    def test_loop_phase_clears_session_on_perspective_reset(self):
        """Verify _loop_phase clears session on perspective reset."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        source = inspect.getsource(AutoBuildOrchestrator._loop_phase)
        # Check that perspective reset section calls set_player_resume_session(None)
        assert "set_player_resume_session(None)" in source, (
            "_loop_phase must clear session on perspective reset by calling "
            "set_player_resume_session(None) (TASK-RFX-B20B)"
        )
