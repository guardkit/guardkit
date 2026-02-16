"""
Unit Tests for AutoBuild Shutdown Suppression (TASK-GLF-002)

Tests the _shutting_down flag that suppresses Graphiti operations during
process shutdown, eliminating ~20 noisy error lines from _cleanup_thread_loaders().

Coverage Target: >=80%
Test Organization:
    - Test _shutting_down initialized to False
    - Test _cleanup_thread_loaders sets _shutting_down to True
    - Test _capture_turn_state skips when _shutting_down is True
    - Test _capture_turn_state runs normally when _shutting_down is False

References:
    - TASK-GLF-002: Add shutting_down flag to suppress shutdown errors
    - TASK-REV-50E1: AutoBuild Run 4 Error Analysis (Finding 4)
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_manager():
    """Create a mock WorktreeManager."""
    manager = Mock()
    worktree = Mock()
    worktree.path = Path("/tmp/mock-worktree")
    worktree.branch = "autobuild/TASK-GLF-002"
    manager.create.return_value = worktree
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create a mock AgentInvoker."""
    return Mock()


@pytest.fixture
def mock_progress_display():
    """Create a mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=None)
    return display


@pytest.fixture
def orchestrator(mock_worktree_manager, mock_agent_invoker, mock_progress_display):
    """Create an AutoBuildOrchestrator with context disabled (no Graphiti needed)."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    return AutoBuildOrchestrator(
        repo_root=Path("/tmp/repo"),
        max_turns=3,
        enable_context=False,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
    )


@pytest.fixture
def mock_turn_record():
    """Create a mock TurnRecord for _capture_turn_state tests."""
    record = Mock()
    record.turn = 1
    record.player_result = Mock()
    record.player_result.report = {"summary": "Test implementation"}
    return record


# ============================================================================
# Test: _shutting_down Initialization (AC-003)
# ============================================================================


class TestShuttingDownInitialization:
    """Tests that _shutting_down is initialized to False."""

    def test_shutting_down_initialized_to_false(self, orchestrator):
        """
        Given a new AutoBuildOrchestrator
        When initialized
        Then _shutting_down should be False

        Acceptance Criteria: AC-003
        """
        assert orchestrator._shutting_down is False

    def test_shutting_down_is_bool(self, orchestrator):
        """
        Given a new AutoBuildOrchestrator
        When initialized
        Then _shutting_down should be a boolean

        Acceptance Criteria: AC-003
        """
        assert isinstance(orchestrator._shutting_down, bool)


# ============================================================================
# Test: _cleanup_thread_loaders Sets Flag (AC-001)
# ============================================================================


class TestCleanupSetsShuttingDown:
    """Tests that _cleanup_thread_loaders sets _shutting_down to True."""

    def test_cleanup_sets_shutting_down_true(self, orchestrator):
        """
        Given an AutoBuildOrchestrator with _shutting_down=False
        When _cleanup_thread_loaders() is called
        Then _shutting_down should be True

        Acceptance Criteria: AC-001
        """
        assert orchestrator._shutting_down is False
        orchestrator._cleanup_thread_loaders()
        assert orchestrator._shutting_down is True

    def test_cleanup_sets_flag_before_iterating_loaders(
        self, mock_worktree_manager, mock_agent_invoker, mock_progress_display
    ):
        """
        Given an AutoBuildOrchestrator with a loader that checks _shutting_down
        When _cleanup_thread_loaders() is called
        Then _shutting_down is True before any loader cleanup runs

        Acceptance Criteria: AC-001
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
        import asyncio

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=False,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Track flag state when cleanup iterates
        flag_during_cleanup = []

        mock_loader = MagicMock()
        mock_loader.graphiti = MagicMock()

        loop = asyncio.new_event_loop()

        # Patch close to capture _shutting_down state during cleanup
        original_close = mock_loader.graphiti.close

        async def spy_close():
            flag_during_cleanup.append(orchestrator._shutting_down)

        mock_loader.graphiti.close = spy_close

        try:
            # Manually inject a loader entry
            import threading
            tid = threading.get_ident()
            orchestrator._thread_loaders[tid] = (mock_loader, loop)

            orchestrator._cleanup_thread_loaders()

            assert len(flag_during_cleanup) == 1
            assert flag_during_cleanup[0] is True, \
                "_shutting_down should be True when loader cleanup runs"
        finally:
            loop.close()


# ============================================================================
# Test: _capture_turn_state Skips During Shutdown (AC-002, AC-005)
# ============================================================================


class TestCaptureSkipsDuringShutdown:
    """Tests that _capture_turn_state returns early when shutting down."""

    def test_capture_returns_early_when_shutting_down(
        self, orchestrator, mock_turn_record
    ):
        """
        Given an AutoBuildOrchestrator with _shutting_down=True
        When _capture_turn_state() is called
        Then it returns immediately without attempting Graphiti operations

        Acceptance Criteria: AC-002, AC-005
        """
        orchestrator._shutting_down = True

        # Should not raise, should return immediately
        orchestrator._capture_turn_state(
            turn_record=mock_turn_record,
            acceptance_criteria=["AC-001: Test criterion"],
            task_id="TASK-GLF-002",
        )

    def test_capture_does_not_call_extract_feature_id_when_shutting_down(
        self, orchestrator, mock_turn_record
    ):
        """
        Given an AutoBuildOrchestrator with _shutting_down=True
        When _capture_turn_state() is called
        Then _extract_feature_id is never called

        Acceptance Criteria: AC-002
        """
        orchestrator._shutting_down = True

        with patch.object(orchestrator, '_extract_feature_id') as mock_extract:
            orchestrator._capture_turn_state(
                turn_record=mock_turn_record,
                acceptance_criteria=["AC-001"],
                task_id="TASK-GLF-002",
            )
            mock_extract.assert_not_called()

    def test_capture_logs_debug_when_shutting_down(
        self, orchestrator, mock_turn_record
    ):
        """
        Given an AutoBuildOrchestrator with _shutting_down=True
        When _capture_turn_state() is called
        Then a debug message is logged

        Acceptance Criteria: AC-002
        """
        orchestrator._shutting_down = True

        with patch("guardkit.orchestrator.autobuild.logger") as mock_logger:
            orchestrator._capture_turn_state(
                turn_record=mock_turn_record,
                acceptance_criteria=["AC-001"],
                task_id="TASK-GLF-002",
            )
            mock_logger.debug.assert_called_once_with(
                "Skipping turn state capture (shutting down)"
            )

    def test_capture_proceeds_when_not_shutting_down(
        self, orchestrator, mock_turn_record
    ):
        """
        Given an AutoBuildOrchestrator with _shutting_down=False
        When _capture_turn_state() is called
        Then it proceeds past the shutting_down guard (may fail later due to
        missing Graphiti, but the guard itself does not block)

        Acceptance Criteria: AC-002 (negative case)
        """
        orchestrator._shutting_down = False

        # With enable_context=False and no Graphiti, the method will proceed
        # past the guard and likely hit a graceful failure in the try block.
        # We just verify it doesn't return at the guard.
        with patch.object(orchestrator, '_extract_feature_id', return_value="FEAT-GLF") as mock_extract:
            orchestrator._capture_turn_state(
                turn_record=mock_turn_record,
                acceptance_criteria=["AC-001"],
                task_id="TASK-GLF-002",
            )
            # _extract_feature_id is called, proving we passed the guard
            mock_extract.assert_called_once()
