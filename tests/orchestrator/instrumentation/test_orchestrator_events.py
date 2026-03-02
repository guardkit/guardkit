"""Tests for AutoBuild orchestrator lifecycle event instrumentation.

Covers:
- EventEmitter injection into AutoBuildOrchestrator via constructor
- task.started emission at orchestration begin with attempt field
- task.completed emission on success with turn_count, diff_stats, verification_status
- task.failed emission on failure with valid failure_category
- wave.completed emission after each wave with independent wave_id
- rate_limit_count of 0 reported for waves with no rate limits
- emitter.flush() called in finalize phase
- NullEmitter used as default when no emitter provided
- Seam test for EVENT_EMITTER contract from TASK-INST-002
- Failure category mapping for all exit conditions
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import (
    BaseEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    WaveCompletedEvent,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def capturing_emitter() -> NullEmitter:
    """NullEmitter that captures events for assertions."""
    return NullEmitter(capture=True)


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """Create a minimal repo root for testing."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".guardkit").mkdir()
    return tmp_path


# ============================================================================
# Seam Test: EVENT_EMITTER contract from TASK-INST-002
# ============================================================================


@pytest.mark.seam
@pytest.mark.integration_contract("EVENT_EMITTER")
def test_event_emitter_protocol_contract():
    """Verify EventEmitter can be injected and called.

    Contract: EventEmitter injected via constructor; call await emitter.emit(event)
    Producer: TASK-INST-002
    """
    from guardkit.orchestrator.instrumentation.emitter import NullEmitter
    from guardkit.orchestrator.instrumentation.schemas import TaskStartedEvent

    emitter = NullEmitter(capture=True)
    event = TaskStartedEvent(
        run_id="test",
        task_id="TASK-001",
        agent_role="player",
        attempt=1,
        timestamp="2026-03-01T00:00:00Z",
    )
    # Verify the emitter accepts BaseEvent subclasses
    asyncio.run(emitter.emit(event))
    assert len(emitter.events) == 1


# ============================================================================
# AC-001: EventEmitter injected into AutoBuildOrchestrator via constructor
# ============================================================================


class TestAutoBuildOrchestratorEmitterInjection:
    """Tests for EventEmitter constructor injection."""

    def test_accepts_emitter_parameter(self, repo_root: Path, capturing_emitter: NullEmitter):
        """AutoBuildOrchestrator accepts emitter via constructor."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=3,
            emitter=capturing_emitter,
        )
        assert orchestrator._emitter is capturing_emitter

    def test_default_emitter_is_null_emitter(self, repo_root: Path):
        """When no emitter provided, NullEmitter is used as default."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=3,
        )
        assert isinstance(orchestrator._emitter, NullEmitter)


# ============================================================================
# AC-002: task.started emitted at orchestration begin with attempt field
# ============================================================================


class TestTaskStartedEvent:
    """Tests for task.started emission."""

    def test_task_started_emitted_on_orchestrate(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """task.started is emitted when orchestrate() begins."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        # Create orchestrator with capturing emitter and mock dependencies
        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"
        mock_wm.create_worktree.return_value = mock_worktree
        mock_wm.preserve_on_failure.return_value = None

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=1,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        # Mock internal methods to prevent actual execution
        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([], "max_turns_exceeded")), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test requirements",
                acceptance_criteria=["criterion 1"],
            )

        # Find TaskStartedEvent in captured events
        started_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskStartedEvent)
        ]
        assert len(started_events) == 1
        event = started_events[0]
        assert event.task_id == "TASK-001"
        assert event.attempt == 1
        assert event.agent_role == "player"

    def test_task_started_includes_attempt_field(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """task.started includes attempt=1 for first run."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-002"
        mock_worktree.path = repo_root / "worktree"

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=1,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([], "max_turns_exceeded")), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-002",
                requirements="test",
                acceptance_criteria=["test"],
            )

        started_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskStartedEvent)
        ]
        assert len(started_events) == 1
        assert started_events[0].attempt == 1


# ============================================================================
# AC-003: task.completed emitted on success with turn_count, diff_stats,
#          verification_status
# ============================================================================


class TestTaskCompletedEvent:
    """Tests for task.completed emission."""

    def test_task_completed_on_approved(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """task.completed emitted when orchestration succeeds (approved)."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=3,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        # Simulate approved outcome
        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([MagicMock()], "approved")), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test",
                acceptance_criteria=["test"],
            )

        completed_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskCompletedEvent)
        ]
        assert len(completed_events) == 1
        event = completed_events[0]
        assert event.task_id == "TASK-001"
        assert event.turn_count >= 0
        assert isinstance(event.diff_stats, str)
        assert isinstance(event.verification_status, str)
        assert event.prompt_profile in (
            "digest_only", "digest+graphiti",
            "digest+rules_bundle", "digest+graphiti+rules_bundle",
        )

    def test_no_completed_event_on_failure(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """task.completed NOT emitted when orchestration fails."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=1,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([], "max_turns_exceeded")), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test",
                acceptance_criteria=["test"],
            )

        completed_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskCompletedEvent)
        ]
        assert len(completed_events) == 0


# ============================================================================
# AC-004: task.failed emitted on failure with valid failure_category
# ============================================================================


class TestTaskFailedEvent:
    """Tests for task.failed emission."""

    @pytest.mark.parametrize(
        "final_decision,expected_category",
        [
            ("max_turns_exceeded", "other"),
            ("error", "other"),
            ("timeout", "timeout"),
            ("cancelled", "other"),
            ("configuration_error", "env_failure"),
            ("pre_loop_blocked", "other"),
            ("unrecoverable_stall", "other"),
        ],
    )
    def test_task_failed_emitted_with_correct_category(
        self,
        repo_root: Path,
        capturing_emitter: NullEmitter,
        final_decision: str,
        expected_category: str,
    ):
        """task.failed emitted on failure with mapped failure_category."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=1,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([], final_decision)), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test",
                acceptance_criteria=["test"],
            )

        failed_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskFailedEvent)
        ]
        assert len(failed_events) == 1
        assert failed_events[0].failure_category == expected_category

    def test_rate_limit_failure_category(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """Rate limit exception maps to rate_limit failure_category."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
        from guardkit.orchestrator.exceptions import RateLimitExceededError

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=1,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', side_effect=RateLimitExceededError("rate limited")), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test",
                acceptance_criteria=["test"],
            )

        failed_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskFailedEvent)
        ]
        assert len(failed_events) == 1
        assert failed_events[0].failure_category == "rate_limit"

    def test_no_failed_event_on_success(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """task.failed NOT emitted when orchestration succeeds."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=3,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([MagicMock()], "approved")), \
             patch.object(orchestrator, '_finalize_phase'), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test",
                acceptance_criteria=["test"],
            )

        failed_events = [
            e for e in capturing_emitter.events
            if isinstance(e, TaskFailedEvent)
        ]
        assert len(failed_events) == 0


# ============================================================================
# AC-005: wave.completed emitted after each wave with independent wave_id
# ============================================================================


class TestWaveCompletedEvent:
    """Tests for wave.completed emission in FeatureOrchestrator."""

    def test_wave_completed_emitted(self):
        """wave.completed is emitted after each wave finishes."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        emitter = NullEmitter(capture=True)
        repo_root = Path("/tmp/test-repo")

        # We test via the _emit_wave_completed helper directly
        orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
        orchestrator._emitter = emitter
        orchestrator.repo_root = repo_root

        # Call helper to emit wave.completed event
        asyncio.run(
            orchestrator._emit_wave_completed(
                feature_id="FEAT-001",
                wave_id="wave-1",
                wave_number=1,
                worker_count=3,
                queue_depth_start=5,
                queue_depth_end=2,
                tasks_completed=3,
                task_failures=0,
                rate_limit_count=0,
                p95_task_latency_ms=1234.5,
                run_id="run-test",
                task_id="FEAT-001",
            )
        )

        wave_events = [
            e for e in emitter.events
            if isinstance(e, WaveCompletedEvent)
        ]
        assert len(wave_events) == 1
        event = wave_events[0]
        assert event.wave_id == "wave-1"
        assert event.worker_count == 3
        assert event.tasks_completed == 3
        assert event.task_failures == 0

    def test_each_wave_has_distinct_wave_id(self):
        """Each wave event has a distinct wave_id."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        emitter = NullEmitter(capture=True)

        orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
        orchestrator._emitter = emitter

        for i in range(1, 4):
            asyncio.run(
                orchestrator._emit_wave_completed(
                    feature_id="FEAT-001",
                    wave_id=f"wave-{i}",
                    wave_number=i,
                    worker_count=2,
                    queue_depth_start=3,
                    queue_depth_end=1,
                    tasks_completed=2,
                    task_failures=0,
                    rate_limit_count=0,
                    p95_task_latency_ms=None,
                    run_id="run-test",
                    task_id="FEAT-001",
                )
            )

        wave_events = [
            e for e in emitter.events
            if isinstance(e, WaveCompletedEvent)
        ]
        assert len(wave_events) == 3
        wave_ids = [e.wave_id for e in wave_events]
        assert len(set(wave_ids)) == 3  # All distinct


# ============================================================================
# AC-006: rate_limit_count of 0 reported for waves with no rate limits
# ============================================================================


class TestWaveRateLimitCount:
    """Tests for rate_limit_count in wave events."""

    def test_zero_rate_limit_count(self):
        """rate_limit_count is 0 when no rate limits occurred."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        emitter = NullEmitter(capture=True)

        orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
        orchestrator._emitter = emitter

        asyncio.run(
            orchestrator._emit_wave_completed(
                feature_id="FEAT-001",
                wave_id="wave-1",
                wave_number=1,
                worker_count=2,
                queue_depth_start=2,
                queue_depth_end=0,
                tasks_completed=2,
                task_failures=0,
                rate_limit_count=0,
                p95_task_latency_ms=500.0,
                run_id="run-test",
                task_id="FEAT-001",
            )
        )

        wave_events = [
            e for e in emitter.events
            if isinstance(e, WaveCompletedEvent)
        ]
        assert len(wave_events) == 1
        assert wave_events[0].rate_limit_count == 0


# ============================================================================
# AC-007: emitter.flush() called in finalize phase
# ============================================================================


class TestEmitterFlush:
    """Tests for emitter.flush() in finalize phase."""

    def test_flush_called_in_finalize(
        self, repo_root: Path, capturing_emitter: NullEmitter
    ):
        """emitter.flush() is called during finalize phase."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        mock_wm = MagicMock()
        mock_worktree = MagicMock()
        mock_worktree.task_id = "TASK-001"
        mock_worktree.path = repo_root / "worktree"

        # Track flush calls
        flush_called = False
        original_flush = capturing_emitter.flush

        async def tracking_flush():
            nonlocal flush_called
            flush_called = True
            await original_flush()

        capturing_emitter.flush = tracking_flush

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=1,
            emitter=capturing_emitter,
            worktree_manager=mock_wm,
            enable_pre_loop=False,
        )

        with patch.object(orchestrator, '_setup_phase', return_value=mock_worktree), \
             patch.object(orchestrator, '_loop_phase', return_value=([], "max_turns_exceeded")), \
             patch.object(orchestrator, '_finalize_phase', wraps=orchestrator._finalize_phase), \
             patch('guardkit.orchestrator.autobuild.TaskLoader') as mock_tl:
            mock_tl.load_task.return_value = {
                "frontmatter": {},
                "requirements": "test",
                "acceptance_criteria": ["test"],
            }

            orchestrator.orchestrate(
                task_id="TASK-001",
                requirements="test",
                acceptance_criteria=["test"],
            )

        assert flush_called, "emitter.flush() was not called in finalize phase"


# ============================================================================
# AC-008: NullEmitter used as default when no emitter provided
# ============================================================================


class TestNullEmitterDefault:
    """Tests for NullEmitter as default."""

    def test_null_emitter_default(self, repo_root: Path):
        """NullEmitter used when no emitter provided."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=repo_root,
            max_turns=3,
        )
        assert isinstance(orchestrator._emitter, NullEmitter)


# ============================================================================
# AC-009: Unit tests verify all lifecycle events and failure categories
# ============================================================================


class TestFailureCategoryMapping:
    """Tests for failure category mapping from exit conditions."""

    def test_mapping_coverage(self):
        """All documented exit conditions map to a failure category."""
        from guardkit.orchestrator.autobuild import FAILURE_CATEGORY_MAP

        # Documented mappings from the task spec
        expected_mappings = {
            "max_turns_exceeded": "other",
            "error": "other",
            "timeout": "timeout",
            "timeout_budget_exhausted": "timeout",
            "rate_limited": "rate_limit",
            "cancelled": "other",
            "configuration_error": "env_failure",
            "pre_loop_blocked": "other",
            "unrecoverable_stall": "other",
            "design_extraction_failed": "other",
        }

        for decision, expected_category in expected_mappings.items():
            assert decision in FAILURE_CATEGORY_MAP, (
                f"Missing mapping for decision '{decision}'"
            )
            assert FAILURE_CATEGORY_MAP[decision] == expected_category, (
                f"Expected {decision} -> {expected_category}, "
                f"got {FAILURE_CATEGORY_MAP[decision]}"
            )

    def test_all_failure_categories_are_valid(self):
        """All mapped categories are valid FailureCategory literals."""
        from guardkit.orchestrator.autobuild import FAILURE_CATEGORY_MAP
        from guardkit.orchestrator.instrumentation.schemas import FailureCategory

        # Extract valid categories from the Literal type
        import typing
        valid_categories = set(typing.get_args(FailureCategory))

        for decision, category in FAILURE_CATEGORY_MAP.items():
            assert category in valid_categories, (
                f"Invalid category '{category}' for decision '{decision}'"
            )


# ============================================================================
# AC-005 (FeatureOrchestrator): Constructor injection
# ============================================================================


class TestFeatureOrchestratorEmitterInjection:
    """Tests for EventEmitter constructor injection in FeatureOrchestrator."""

    def test_accepts_emitter_parameter(self, repo_root: Path, capturing_emitter: NullEmitter):
        """FeatureOrchestrator accepts emitter via constructor."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        orchestrator = FeatureOrchestrator(
            repo_root=repo_root,
            emitter=capturing_emitter,
        )
        assert orchestrator._emitter is capturing_emitter

    def test_default_emitter_is_null_emitter(self, repo_root: Path):
        """When no emitter provided, NullEmitter is used as default."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        orchestrator = FeatureOrchestrator(
            repo_root=repo_root,
        )
        assert isinstance(orchestrator._emitter, NullEmitter)
