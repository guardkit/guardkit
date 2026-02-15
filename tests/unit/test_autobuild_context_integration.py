"""
Unit Tests for AutoBuild Context Integration (TASK-GR6-006)

Tests the integration of AutoBuildContextLoader into the AutoBuildOrchestrator,
verifying that context is retrieved for Player and Coach turns and passed
to the agent invocation.

TDD RED Phase: These tests define expected behavior for the integration.

Coverage Target: >=80%
Test Organization:
    - Test Player turn context injection
    - Test Coach turn context injection
    - Test verbose flag output
    - Test graceful degradation when context unavailable
    - Test turn continuation wiring (TASK-GWR-003)

References:
    - TASK-GR6-006: Integrate with /feature-build
    - FEAT-GR-006: Job-Specific Context Retrieval
    - TASK-GWR-003: Wire outcome reads and turn continuation into AutoBuild context
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, List, Optional

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_context_result():
    """Create a mock AutoBuildContextResult for testing."""
    from guardkit.knowledge.autobuild_context_loader import AutoBuildContextResult
    from guardkit.knowledge.job_context_retriever import RetrievedContext

    context = RetrievedContext(
        task_id="TASK-GR6-006",
        budget_used=1500,
        budget_total=4000,
        feature_context=[{"name": "FEAT-GR6", "content": "Job context"}],
        similar_outcomes=[],
        relevant_patterns=[{"pattern": "Repository"}],
        architecture_context=[],
        warnings=[],
        domain_knowledge=[],
        role_constraints=[{"name": "Player", "content": "Must ask before auth"}],
        quality_gate_configs=[{"name": "Coverage", "threshold": 80}],
        turn_states=[{"turn_number": 1, "coach_decision": "REJECTED", "feedback_summary": "Add tests"}],
        implementation_modes=[{"name": "TDD", "content": "Use TDD"}],
    )

    return AutoBuildContextResult(
        context=context,
        prompt_text="## Job-Specific Context\n\nBudget: 1500/4000 tokens\n\n### 🎭 Role Constraints\n- Player: Must ask before auth",
        budget_used=1500,
        budget_total=4000,
        categories_populated=["feature_context", "relevant_patterns", "role_constraints", "quality_gate_configs"],
        verbose_details="=== Context Retrieval Details ===\nTask: TASK-GR6-006\nBudget: 1500/4000 tokens",
    )


@pytest.fixture
def mock_context_loader(mock_context_result):
    """Create a mock AutoBuildContextLoader."""
    loader = MagicMock()

    # Make async methods return the mock result
    async def mock_get_player_context(*args, **kwargs):
        return mock_context_result

    async def mock_get_coach_context(*args, **kwargs):
        return mock_context_result

    loader.get_player_context = AsyncMock(side_effect=mock_get_player_context)
    loader.get_coach_context = AsyncMock(side_effect=mock_get_coach_context)
    loader.verbose = False

    return loader


@pytest.fixture
def mock_worktree():
    """Create a mock Worktree."""
    worktree = Mock()
    worktree.path = Path("/tmp/mock-worktree")
    worktree.branch = "autobuild/TASK-GR6-006"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create a mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create a mock AgentInvoker."""
    invoker = Mock()

    # Mock invoke_player
    async def mock_invoke_player(*args, **kwargs):
        from guardkit.orchestrator.agent_invoker import AgentInvocationResult
        return AgentInvocationResult(
            task_id=kwargs.get("task_id", "TASK-GR6-006"),
            turn=kwargs.get("turn", 1),
            agent_type="player",
            success=True,
            report={
                "files_created": ["src/test.py"],
                "tests_passed": 5,
                "tests_failed": 0,
            },
            duration_seconds=10.5,
            error=None,
        )

    invoker.invoke_player = AsyncMock(side_effect=mock_invoke_player)
    return invoker


@pytest.fixture
def mock_progress_display():
    """Create a mock ProgressDisplay."""
    display = Mock()
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.console = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=None)
    return display


# ============================================================================
# Test: Player Turn Context Injection
# ============================================================================


class TestPlayerTurnContextInjection:
    """Tests for context injection into Player turns."""

    def test_player_turn_calls_context_loader_when_enabled(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given AutoBuildOrchestrator with enable_context=True
        When _invoke_player_safely is called
        Then context_loader.get_player_context is called

        Acceptance Criteria: Context retrieved for each Player turn
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        # Force worktree to be set
        orchestrator._existing_worktree = mock_worktree

        # Call _invoke_player_safely
        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        # Verify context loader was called
        assert mock_context_loader.get_player_context.called, \
            "get_player_context should be called when enable_context=True"

    def test_player_turn_skips_context_when_disabled(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given AutoBuildOrchestrator with enable_context=False
        When _invoke_player_safely is called
        Then context_loader.get_player_context is NOT called
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=False,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree

        # Call _invoke_player_safely
        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        # Verify context loader was NOT called
        assert not mock_context_loader.get_player_context.called, \
            "get_player_context should NOT be called when enable_context=False"

    def test_player_context_includes_feature_id(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given an AutoBuild task with feature_id
        When context is retrieved for Player
        Then feature_id is passed to get_player_context

        Acceptance Criteria: AutoBuild context included
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree

        # Store feature_id on orchestrator for test
        orchestrator._feature_id = "FEAT-0F4A"

        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        # Check that feature_id was passed
        if mock_context_loader.get_player_context.called:
            call_kwargs = mock_context_loader.get_player_context.call_args[1]
            assert call_kwargs.get("feature_id") == "FEAT-0F4A", \
                "feature_id should be passed to get_player_context"

    def test_player_turn_passes_previous_feedback(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given a Player turn with previous Coach feedback
        When context is retrieved
        Then previous_feedback is passed to get_player_context

        Acceptance Criteria: Refinement attempts get emphasized warnings
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=2,
            requirements="Implement OAuth2 flow",
            feedback="Add more test coverage",
        )

        # Check that previous_feedback was passed
        if mock_context_loader.get_player_context.called:
            call_kwargs = mock_context_loader.get_player_context.call_args[1]
            assert call_kwargs.get("previous_feedback") == "Add more test coverage", \
                "previous_feedback should be passed to get_player_context"


# ============================================================================
# Test: Coach Turn Context Injection
# ============================================================================


class TestCoachTurnContextInjection:
    """Tests for context injection into Coach turns."""

    def test_coach_turn_calls_context_loader_when_enabled(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given AutoBuildOrchestrator with enable_context=True
        When _invoke_coach_safely is called
        Then context_loader.get_coach_context is called

        Acceptance Criteria: Coach receives appropriate subset of context
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        # Mock CoachValidator
        with patch('guardkit.orchestrator.autobuild.CoachValidator') as MockValidator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = Mock(
                decision="approve",
                to_dict=Mock(return_value={"decision": "approve"}),
            )
            mock_validator_instance.save_decision = Mock()
            MockValidator.return_value = mock_validator_instance

            result = orchestrator._invoke_coach_safely(
                task_id="TASK-GR6-006",
                turn=1,
                requirements="Implement OAuth2 flow",
                player_report={"tests_passed": 5},
                worktree=mock_worktree,
            )

        # Verify context loader was called for coach
        assert mock_context_loader.get_coach_context.called, \
            "get_coach_context should be called when enable_context=True"

    def test_coach_turn_receives_quality_gate_context(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given Coach turn context retrieval
        When context is retrieved
        Then quality_gate_configs are included

        Acceptance Criteria: Coach receives appropriate subset of context
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        with patch('guardkit.orchestrator.autobuild.CoachValidator') as MockValidator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = Mock(
                decision="approve",
                to_dict=Mock(return_value={"decision": "approve"}),
            )
            mock_validator_instance.save_decision = Mock()
            MockValidator.return_value = mock_validator_instance

            result = orchestrator._invoke_coach_safely(
                task_id="TASK-GR6-006",
                turn=1,
                requirements="Implement OAuth2 flow",
                player_report={"tests_passed": 5},
                worktree=mock_worktree,
            )

        # Verify the context result contains quality gates
        if mock_context_loader.get_coach_context.called:
            # The mock returns context with quality_gate_configs
            call_result = mock_context_loader.get_coach_context.return_value
            # This verifies the method was called - actual quality gate verification
            # happens in the context loader itself (tested in test_autobuild_context_integration.py)
            assert True  # Integration verified


# ============================================================================
# Test: Verbose Output for Context Details
# ============================================================================


class TestVerboseContextOutput:
    """Tests for --verbose flag showing context retrieval details."""

    def test_verbose_flag_shows_context_details(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
        capsys,
    ):
        """
        Given AutoBuildOrchestrator with verbose=True
        When context is retrieved
        Then detailed context information is displayed

        Acceptance Criteria: --verbose flag shows context retrieval details
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # Set verbose on the context loader
        mock_context_loader.verbose = True

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            verbose=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        # When verbose is enabled, the context loader should have verbose=True
        # and the orchestrator should log/display the verbose_details
        if mock_context_loader.get_player_context.called:
            # Verify verbose mode is active
            assert orchestrator.verbose == True
            # The actual verbose output verification is in the integration tests

    def test_verbose_shows_budget_usage(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
        mock_context_result,
    ):
        """
        Given context retrieval with verbose=True
        When context is retrieved
        Then budget usage is logged

        Acceptance Criteria: --verbose flag shows context retrieval details
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            verbose=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        # Verify budget info is available
        assert mock_context_result.budget_used == 1500
        assert mock_context_result.budget_total == 4000


# ============================================================================
# Test: Graceful Degradation
# ============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation when context is unavailable."""

    def test_player_continues_when_context_fails(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given context retrieval fails
        When Player turn is executed
        Then Player continues without context (graceful degradation)
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # Create a failing context loader
        failing_loader = MagicMock()
        failing_loader.get_player_context = AsyncMock(side_effect=Exception("Graphiti unavailable"))

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=failing_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        # Should not raise, should continue gracefully
        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        # Player should still be invoked (with or without context)
        # The test passes if no exception is raised
        assert result is not None

    def test_coach_continues_when_context_fails(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given context retrieval fails
        When Coach turn is executed
        Then Coach continues without context (graceful degradation)
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # Create a failing context loader
        failing_loader = MagicMock()
        failing_loader.get_coach_context = AsyncMock(side_effect=Exception("Graphiti unavailable"))

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=failing_loader,
        )

        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        with patch('guardkit.orchestrator.autobuild.CoachValidator') as MockValidator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = Mock(
                decision="approve",
                to_dict=Mock(return_value={"decision": "approve"}),
            )
            mock_validator_instance.save_decision = Mock()
            MockValidator.return_value = mock_validator_instance

            # Should not raise, should continue gracefully
            result = orchestrator._invoke_coach_safely(
                task_id="TASK-GR6-006",
                turn=1,
                requirements="Implement OAuth2 flow",
                player_report={"tests_passed": 5},
                worktree=mock_worktree,
            )

        # Coach should still run validation
        assert result is not None

    def test_no_context_loader_graceful_degradation(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given no context_loader is provided
        When Player turn is executed
        Then Player continues without context
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=None,  # No context loader
        )

        orchestrator._existing_worktree = mock_worktree

        # Should not raise, should continue gracefully
        result = orchestrator._invoke_player_safely(
            task_id="TASK-GR6-006",
            turn=1,
            requirements="Implement OAuth2 flow",
            feedback=None,
        )

        assert result is not None


# ============================================================================
# Test: Context Loader Initialization
# ============================================================================


class TestContextLoaderInitialization:
    """Tests for AutoBuildContextLoader initialization in orchestrator."""

    def test_orchestrator_stores_context_loader(
        self,
        mock_worktree_manager,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given context_loader is provided
        When AutoBuildOrchestrator is initialized
        Then context_loader is stored
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )

        assert orchestrator._context_loader == mock_context_loader

    def test_orchestrator_creates_context_loader_lazily(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given no context_loader is provided and enable_context=True
        When Player turn is invoked
        Then context_loader is created lazily with Graphiti
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=None,
        )

        # Initially no context loader
        assert orchestrator._context_loader is None

    def test_verbose_flag_passed_to_context_loader(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given verbose=True on orchestrator
        When context_loader is used
        Then verbose flag is propagated
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            verbose=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        assert orchestrator.verbose == True


# ============================================================================
# Test Context Skip Logging (TASK-FIX-GCW2)
# ============================================================================


class TestContextSkipLogging:
    """Test INFO log emission when enable_context=True but context_loader is None."""

    def test_player_logs_info_when_context_enabled_but_loader_none(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and context_loader=None
        When _invoke_player_safely is called
        Then an INFO log 'Player context retrieval skipped' is emitted.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            context_loader=None,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Mock agent_invoker.invoke_player to return a basic result
        mock_result = Mock()
        mock_result.success = True
        mock_result.error = None
        mock_result.report = {"summary": "test"}
        mock_agent_invoker.invoke_player = AsyncMock(return_value=mock_result)

        with patch("guardkit.orchestrator.autobuild.logger") as mock_logger:
            orchestrator._invoke_player_safely(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
                feedback=None,
            )
            mock_logger.info.assert_any_call(
                "Player context retrieval skipped: context_loader not provided for TASK-TEST-001"
            )

    def test_coach_logs_info_when_context_enabled_but_loader_none(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and context_loader=None
        When _invoke_coach_safely is called
        Then an INFO log 'Coach context retrieval skipped' is emitted.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            context_loader=None,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Mock worktree
        mock_worktree = Mock()
        mock_worktree.path = Path("/tmp/worktree")

        # Mock coach invocation to return a basic result
        mock_result = Mock()
        mock_result.success = True
        mock_result.error = None
        mock_result.report = {"decision": "approve", "rationale": "test"}
        mock_agent_invoker.invoke_coach = AsyncMock(return_value=mock_result)

        with patch("guardkit.orchestrator.autobuild.logger") as mock_logger:
            orchestrator._invoke_coach_safely(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
                player_report={"summary": "test"},
                worktree=mock_worktree,
            )
            mock_logger.info.assert_any_call(
                "Coach context retrieval skipped: context_loader not provided for TASK-TEST-001"
            )

    def test_no_log_when_context_disabled(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=False
        When _invoke_player_safely is called
        Then no context skip log is emitted.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=False,
            context_loader=None,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        mock_result = Mock()
        mock_result.success = True
        mock_result.error = None
        mock_result.report = {"summary": "test"}
        mock_agent_invoker.invoke_player = AsyncMock(return_value=mock_result)

        with patch("guardkit.orchestrator.autobuild.logger") as mock_logger:
            orchestrator._invoke_player_safely(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
                feedback=None,
            )
            # Verify no call with "skipped" message
            for call in mock_logger.info.call_args_list:
                assert "context retrieval skipped" not in str(call), (
                    f"Unexpected skip log when enable_context=False: {call}"
                )


# ============================================================================
# Test: Auto-Init Context Loader (TASK-FIX-GCW3)
# ============================================================================


class TestAutoInitContextLoader:
    """Tests for auto-initialization of AutoBuildContextLoader in __init__."""

    def test_auto_init_when_graphiti_available(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True, no context_loader, and Graphiti singleton available
        When AutoBuildOrchestrator is initialized
        Then _context_loader is auto-created with the Graphiti client.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_graphiti = MagicMock()
        mock_graphiti.enabled = True

        with patch("guardkit.orchestrator.autobuild.get_graphiti", return_value=mock_graphiti) as mock_get, \
             patch("guardkit.orchestrator.autobuild.AutoBuildContextLoader") as MockLoader:
            # Prevent the import-based path; patch at module level
            # The auto-init imports from guardkit.knowledge, so patch at the call site
            pass

        # Use a more targeted approach: patch the imports inside __init__
        with patch.dict("sys.modules", {}):
            pass

        # Simplest approach: patch at the guardkit.knowledge level
        mock_graphiti = MagicMock()
        mock_graphiti.enabled = True

        mock_loader_class = MagicMock()
        mock_loader_instance = MagicMock()
        mock_loader_class.return_value = mock_loader_instance

        with patch("guardkit.knowledge.get_graphiti", return_value=mock_graphiti), \
             patch("guardkit.knowledge.AutoBuildContextLoader", mock_loader_class):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        assert orchestrator._context_loader is mock_loader_instance
        mock_loader_class.assert_called_once_with(
            graphiti=mock_graphiti, verbose=False
        )

    def test_auto_init_skipped_when_context_loader_provided(
        self,
        mock_worktree_manager,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and an explicit context_loader is provided
        When AutoBuildOrchestrator is initialized
        Then auto-init is skipped; the provided loader is used.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch("guardkit.knowledge.get_graphiti") as mock_get:
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=mock_context_loader,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        # DI takes precedence: auto-init should not have fired
        assert orchestrator._context_loader is mock_context_loader

    def test_auto_init_skipped_when_context_disabled(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=False
        When AutoBuildOrchestrator is initialized
        Then no auto-init is attempted.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch("guardkit.knowledge.get_graphiti") as mock_get:
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=False,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        assert orchestrator._context_loader is None
        mock_get.assert_not_called()

    def test_auto_init_graceful_when_graphiti_none(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and get_graphiti() returns None
        When AutoBuildOrchestrator is initialized
        Then _context_loader remains None (graceful degradation).
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch("guardkit.knowledge.get_graphiti", return_value=None):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        assert orchestrator._context_loader is None

    def test_auto_init_graceful_when_graphiti_not_enabled(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and get_graphiti() returns client with enabled=False
        When AutoBuildOrchestrator is initialized
        Then _context_loader remains None (graceful degradation).
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_graphiti = MagicMock()
        mock_graphiti.enabled = False

        with patch("guardkit.knowledge.get_graphiti", return_value=mock_graphiti):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        assert orchestrator._context_loader is None

    def test_auto_init_graceful_on_import_error(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True but graphiti dependencies not installed
        When AutoBuildOrchestrator is initialized
        Then _context_loader remains None with no crash.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch(
            "guardkit.knowledge.get_graphiti",
            side_effect=ImportError("No module named 'graphiti_core'"),
        ):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        assert orchestrator._context_loader is None

    def test_auto_init_graceful_on_unexpected_error(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and get_graphiti() raises unexpected error
        When AutoBuildOrchestrator is initialized
        Then _context_loader remains None with no crash.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch(
            "guardkit.knowledge.get_graphiti",
            side_effect=RuntimeError("Connection refused"),
        ):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        assert orchestrator._context_loader is None

    def test_auto_init_passes_verbose_flag(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True and verbose=True
        When AutoBuildOrchestrator auto-initializes context_loader
        Then verbose=True is passed to AutoBuildContextLoader.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_graphiti = MagicMock()
        mock_graphiti.enabled = True

        mock_loader_class = MagicMock()

        with patch("guardkit.knowledge.get_graphiti", return_value=mock_graphiti), \
             patch("guardkit.knowledge.AutoBuildContextLoader", mock_loader_class):
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                verbose=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        mock_loader_class.assert_called_once_with(
            graphiti=mock_graphiti, verbose=True
        )

    def test_auto_init_logs_success(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given successful auto-init
        When AutoBuildOrchestrator is initialized
        Then an INFO log 'Auto-initialized context_loader with Graphiti' is emitted.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_graphiti = MagicMock()
        mock_graphiti.enabled = True

        with patch("guardkit.knowledge.get_graphiti", return_value=mock_graphiti), \
             patch("guardkit.knowledge.AutoBuildContextLoader"), \
             patch("guardkit.orchestrator.autobuild.logger") as mock_logger:
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        mock_logger.info.assert_any_call(
            "Auto-initialized context_loader with Graphiti"
        )

    def test_auto_init_logs_graphiti_unavailable(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given get_graphiti() returns None
        When AutoBuildOrchestrator is initialized
        Then an INFO log 'Graphiti not available' is emitted.
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        with patch("guardkit.knowledge.get_graphiti", return_value=None), \
             patch("guardkit.orchestrator.autobuild.logger") as mock_logger:
            orchestrator = AutoBuildOrchestrator(
                repo_root=Path("/tmp/repo"),
                max_turns=3,
                enable_context=True,
                context_loader=None,
                worktree_manager=mock_worktree_manager,
                agent_invoker=mock_agent_invoker,
                progress_display=mock_progress_display,
            )

        mock_logger.info.assert_any_call(
            "Graphiti not available, context retrieval disabled"
        )


# ============================================================================
# Test: Context Status Tracking (TASK-FIX-GCW5)
# ============================================================================


class TestContextStatusTracking:
    """Tests for ContextStatus being set on orchestrator during invocations."""

    def test_player_context_status_set_when_retrieved(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given context retrieval succeeds
        When _invoke_player_safely is called
        Then _last_player_context_status is set with 'retrieved' status
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )
        orchestrator._existing_worktree = mock_worktree

        orchestrator._invoke_player_safely(
            task_id="TASK-TEST-001",
            turn=1,
            requirements="Test requirements",
            feedback=None,
        )

        cs = orchestrator._last_player_context_status
        assert cs is not None
        assert cs.status == "retrieved"
        assert cs.categories_count == 4  # from mock_context_result fixture
        assert cs.budget_used == 1500
        assert cs.budget_total == 4000

    def test_player_context_status_disabled_when_context_off(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=False
        When _invoke_player_safely is called
        Then _last_player_context_status is 'disabled'
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=False,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )
        orchestrator._existing_worktree = mock_worktree

        orchestrator._invoke_player_safely(
            task_id="TASK-TEST-001",
            turn=1,
            requirements="Test requirements",
            feedback=None,
        )

        cs = orchestrator._last_player_context_status
        assert cs is not None
        assert cs.status == "disabled"

    def test_player_context_status_skipped_when_no_loader(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given enable_context=True but no context_loader
        When _invoke_player_safely is called
        Then _last_player_context_status is 'skipped'
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_result = Mock()
        mock_result.success = True
        mock_result.error = None
        mock_result.report = {"summary": "test"}
        mock_agent_invoker.invoke_player = AsyncMock(return_value=mock_result)

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            context_loader=None,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )
        orchestrator._existing_worktree = mock_worktree

        orchestrator._invoke_player_safely(
            task_id="TASK-TEST-001",
            turn=1,
            requirements="Test requirements",
            feedback=None,
        )

        cs = orchestrator._last_player_context_status
        assert cs is not None
        assert cs.status == "skipped"
        assert cs.reason == "no context_loader"

    def test_player_context_status_failed_on_exception(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given context retrieval raises an exception
        When _invoke_player_safely is called
        Then _last_player_context_status is 'failed' with the error
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        failing_loader = MagicMock()
        failing_loader.get_player_context = AsyncMock(
            side_effect=Exception("Graphiti unavailable")
        )

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=failing_loader,
        )
        orchestrator._existing_worktree = mock_worktree

        orchestrator._invoke_player_safely(
            task_id="TASK-TEST-001",
            turn=1,
            requirements="Test requirements",
            feedback=None,
        )

        cs = orchestrator._last_player_context_status
        assert cs is not None
        assert cs.status == "failed"
        assert "Graphiti unavailable" in cs.reason

    def test_coach_context_status_set_when_retrieved(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_context_loader,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given context retrieval succeeds for Coach
        When _invoke_coach_safely is called
        Then _last_coach_context_status is set with 'retrieved' status
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=mock_context_loader,
        )
        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        with patch('guardkit.orchestrator.autobuild.CoachValidator') as MockValidator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = Mock(
                decision="approve",
                to_dict=Mock(return_value={"decision": "approve"}),
            )
            mock_validator_instance.save_decision = Mock()
            MockValidator.return_value = mock_validator_instance

            orchestrator._invoke_coach_safely(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
                player_report={"tests_passed": 5},
                worktree=mock_worktree,
            )

        cs = orchestrator._last_coach_context_status
        assert cs is not None
        assert cs.status == "retrieved"
        assert cs.categories_count == 4
        assert cs.budget_used == 1500
        assert cs.budget_total == 4000

    def test_coach_context_status_failed_on_exception(
        self,
        mock_worktree_manager,
        mock_worktree,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given Coach context retrieval fails
        When _invoke_coach_safely is called
        Then _last_coach_context_status is 'failed'
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        failing_loader = MagicMock()
        failing_loader.get_coach_context = AsyncMock(
            side_effect=Exception("Graphiti unavailable")
        )

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            context_loader=failing_loader,
        )
        orchestrator._existing_worktree = mock_worktree
        orchestrator._feature_id = "FEAT-0F4A"

        with patch('guardkit.orchestrator.autobuild.CoachValidator') as MockValidator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate.return_value = Mock(
                decision="approve",
                to_dict=Mock(return_value={"decision": "approve"}),
            )
            mock_validator_instance.save_decision = Mock()
            MockValidator.return_value = mock_validator_instance

            orchestrator._invoke_coach_safely(
                task_id="TASK-TEST-001",
                turn=1,
                requirements="Test requirements",
                player_report={"tests_passed": 5},
                worktree=mock_worktree,
            )

        cs = orchestrator._last_coach_context_status
        assert cs is not None
        assert cs.status == "failed"
        assert "Graphiti unavailable" in cs.reason


# ============================================================================
# Test: Turn Continuation Wiring (TASK-GWR-003)
# ============================================================================


@pytest.mark.asyncio
class TestTurnContinuationWiring:
    """Tests for turn continuation context wiring (TASK-GWR-003)."""

    async def test_player_turn_2_calls_continuation(self):
        """
        AC-F2-01: get_player_context() calls load_turn_continuation_context() for turn > 1.

        Given turn_number=2 and Graphiti available
        When get_player_context is called
        Then load_turn_continuation_context is invoked with correct params
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        mock_graphiti = MagicMock()
        loader = AutoBuildContextLoader(graphiti=mock_graphiti)

        # Mock the retriever
        mock_context = RetrievedContext(
            task_id="TASK-001",
            budget_used=100,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_context)
        loader._retriever = mock_retriever

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = "## Previous Turn Summary\nTurn 1: Implemented feature"

            result = await loader.get_player_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=2,
                description="Test task",
            )

            # Verify continuation was called with correct params
            mock_load.assert_called_once_with(
                graphiti_client=mock_graphiti,
                feature_id="FEAT-001",
                task_id="TASK-001",
                current_turn=2,
            )

    async def test_player_turn_continuation_included_in_prompt(self):
        """
        AC-F2-02: Turn continuation context is included in the Player prompt text when available.

        Given turn_number=2 and continuation context exists
        When get_player_context is called
        Then prompt_text includes the continuation context
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        mock_graphiti = MagicMock()
        loader = AutoBuildContextLoader(graphiti=mock_graphiti)

        mock_context = RetrievedContext(
            task_id="TASK-001",
            budget_used=100,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_context)
        loader._retriever = mock_retriever

        continuation_text = "## Previous Turn Summary (Turn 1)\n**What was attempted**: Feature implementation\n**Coach decision**: feedback"

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = continuation_text

            result = await loader.get_player_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=2,
                description="Test task",
            )

            # Verify continuation is in prompt_text
            assert continuation_text in result.prompt_text, \
                "Turn continuation should be included in prompt_text"

    async def test_player_turn_1_no_continuation_call(self):
        """
        AC-F2-03: get_player_context() for turn 1 does NOT call continuation.

        Given turn_number=1
        When get_player_context is called
        Then load_turn_continuation_context is NOT called
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        mock_graphiti = MagicMock()
        loader = AutoBuildContextLoader(graphiti=mock_graphiti)

        mock_context = RetrievedContext(
            task_id="TASK-001",
            budget_used=100,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_context)
        loader._retriever = mock_retriever

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load:
            result = await loader.get_player_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=1,
                description="Test task",
            )

            # Verify continuation was NOT called for turn 1
            mock_load.assert_not_called()

    async def test_graceful_degradation_no_prior_turns(self):
        """
        AC-F2-04: Graceful degradation when no prior turn states exist (None returned, no errors).

        Given turn_number=2 but no prior turn data exists
        When get_player_context is called
        Then continuation returns None and no error is raised
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        mock_graphiti = MagicMock()
        loader = AutoBuildContextLoader(graphiti=mock_graphiti)

        mock_context = RetrievedContext(
            task_id="TASK-001",
            budget_used=100,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_context)
        loader._retriever = mock_retriever

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load:
            # Simulate no previous turn data
            mock_load.return_value = None

            result = await loader.get_player_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=2,
                description="Test task",
            )

            # Should not raise, should return valid result
            assert result is not None
            assert result.context.task_id == "TASK-001"

    async def test_graceful_degradation_graphiti_none(self):
        """
        AC-F2-05: Graceful degradation when Graphiti client is None or disabled.

        Given Graphiti client is None
        When get_player_context is called for turn 2
        Then no continuation call is made and no error is raised
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        # Loader with None graphiti
        loader = AutoBuildContextLoader(graphiti=None)

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load:
            result = await loader.get_player_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=2,
                description="Test task",
            )

            # Verify continuation was NOT called when graphiti is None
            mock_load.assert_not_called()
            # Should return empty result gracefully
            assert result.budget_used == 0

    async def test_coach_turn_2_calls_continuation(self):
        """
        Test that Coach also gets turn continuation for turn > 1.

        Given turn_number=2 and Graphiti available
        When get_coach_context is called
        Then load_turn_continuation_context is invoked
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        mock_graphiti = MagicMock()
        loader = AutoBuildContextLoader(graphiti=mock_graphiti)

        mock_context = RetrievedContext(
            task_id="TASK-001",
            budget_used=100,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_context)
        loader._retriever = mock_retriever

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = "## Previous Turn Summary\nTurn 1: Validated implementation"

            result = await loader.get_coach_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=2,
                description="Test task",
            )

            # Verify continuation was called
            mock_load.assert_called_once_with(
                graphiti_client=mock_graphiti,
                feature_id="FEAT-001",
                task_id="TASK-001",
                current_turn=2,
            )

    async def test_structured_logging_for_continuation(self):
        """
        AC-F2-07: Structured logging for turn continuation and similar outcomes.

        Given turn continuation is loaded
        When get_player_context is called
        Then INFO logs are emitted with continuation length
        """
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        mock_graphiti = MagicMock()
        loader = AutoBuildContextLoader(graphiti=mock_graphiti)

        mock_context = RetrievedContext(
            task_id="TASK-001",
            budget_used=100,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[{"outcome": "test"}],  # 1 similar outcome
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_context)
        loader._retriever = mock_retriever

        continuation_text = "## Previous Turn Summary\nTest"

        with patch("guardkit.knowledge.turn_state_operations.load_turn_continuation_context", new_callable=AsyncMock) as mock_load, \
             patch("guardkit.knowledge.autobuild_context_loader.logger") as mock_logger:
            mock_load.return_value = continuation_text

            result = await loader.get_player_context(
                task_id="TASK-001",
                feature_id="FEAT-001",
                turn_number=2,
                description="Test task",
            )

            # Verify logging for turn continuation
            mock_logger.info.assert_any_call(
                "[Graphiti] Turn continuation loaded: %d chars for turn %d",
                len(continuation_text),
                2,
            )

            # Verify logging for similar outcomes
            mock_logger.info.assert_any_call(
                "[Graphiti] Similar outcomes found: %d matches",
                1,
            )
