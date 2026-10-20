"""
Integration Tests for SDK Delegation in AutoBuild Orchestration

Tests the SDK delegation flow through AgentInvoker, verifying that task-work
delegation correctly invokes the Claude Agent SDK and handles stream parsing,
timeout scenarios, and Coach validation.

Test Scenarios:
    1. Happy Path: SDK query succeeds, stream parser extracts quality gates,
       task_work_results.json is written, Coach validates successfully
    2. Timeout Handling: SDK query exceeds timeout, SDKTimeoutError raised,
       result.success=False with appropriate error message
    3. Stream Parsing: TaskWorkStreamParser correctly parses phase markers,
       test results, and coverage metrics
    4. Coach Validation: Coach reads task_work_results.json and validates
       quality gate results independently

Coverage Target: >=85%
Test Count: 20+ tests

Architecture:
    - Mocks claude_agent_sdk.query() to avoid actual SDK invocations
    - Uses TaskWorkStreamParser for stream processing validation
    - Tests AgentInvoker._invoke_task_work_implement() directly
    - Verifies task_work_results.json creation and format

Run with:
    pytest tests/integration/test_sdk_delegation.py -v
    pytest tests/integration/test_sdk_delegation.py -v --cov=guardkit/orchestrator

Note: Async tests use asyncio.run() wrapper for compatibility across environments.
"""

import asyncio
import json
import pytest
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from dataclasses import dataclass


def run_async(coro):
    """Helper to run async coroutines in sync test functions."""
    return asyncio.run(coro)

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

# Import components under test
from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
    TaskWorkStreamParser,
)
from guardkit.orchestrator.exceptions import (
    SDKTimeoutError,
    TaskWorkResult,
)


# ============================================================================
# Typed stand-ins for the SDK's message classes
# ============================================================================
#
# The code under test has checked ``isinstance(message, AssistantMessage)``
# and read the text out of each message's ``TextBlock`` content since
# TASK-FB-FIX-013 (in b7f0472ac, the commit that added this file); today the
# sdk harness does the same (``sdk_harness.py``) and duck-types blocks on
# ``type(block).__name__``. A bare ``MagicMock`` message is not an instance of
# anything and a ``MagicMock`` attribute is not a type, so the stand-ins carry
# the real SDK's class names, as the unit tests' fake SDK does
# (``tests/unit/test_agent_invoker.py``, ``_create_mock_sdk``).


class TextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class AssistantMessage:
    def __init__(self, content: list):
        self.content = content


class ResultMessage:
    def __init__(self, num_turns: int = 1, session_id: Any = None):
        self.num_turns = num_turns
        self.session_id = session_id


def _assistant(text: str) -> AssistantMessage:
    """One assistant message saying ``text``, as the SDK streams it."""
    return AssistantMessage([TextBlock(text)])


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _routine_seat(monkeypatch: pytest.MonkeyPatch, m0_routine_fleet_route: str) -> str:
    """The seat and the harness these tests were written for, stated outright.

    Two things changed under this file after it was written (merged 25 January 2026):

    * TASK-HMIG-011 (16 June 2026) flipped the default harness from ``sdk`` to
      ``langgraph``. These tests drive ``_invoke_task_work_implement`` through
      a patched ``claude_agent_sdk`` module (``sys.modules``), which only the
      ``sdk`` harness calls, so they name it — the SDK path stays an opt-in
      fallback, exactly as the cutover left it.
    * The effective-seat M0 fence at ``select_harness`` (``m0_fence.py``,
      2 August 2026) refuses a construction with no model: an unnamed seat falls
      to a frontier default. These tests declare the routine local-fleet route
      with the suite's sanctioned fixture (``tests/conftest.py``), and every
      ``AgentInvoker`` here is handed that seat as ``model_name`` — never
      ``GUARDKIT_ALLOW_FRONTIER``, which would switch the fence off.

    Nothing here reaches a network: every SDK call goes to the patched module.
    """
    monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
    return m0_routine_fleet_route


@pytest.fixture
def mock_worktree(tmp_path):
    """
    Create a mock worktree structure for SDK delegation testing.

    Returns:
        Path: Path to worktree root
    """
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    # Create task directories
    task_dir = worktree / "tasks" / "design_approved"
    task_dir.mkdir(parents=True)

    # Also create in_progress for state transition tests
    in_progress_dir = worktree / "tasks" / "in_progress"
    in_progress_dir.mkdir(parents=True)

    # Create task file in design_approved state
    task_file = task_dir / "TASK-SDK-001-test-task.md"
    task_file.write_text("""---
id: TASK-SDK-001
title: SDK Test Task
status: design_approved
created: 2025-12-31T10:00:00Z
priority: medium
complexity: 4
---

# SDK Test Task

## Description

Test task for SDK delegation integration testing.

## Requirements

- Implement SDK integration
- Add comprehensive tests
- Verify stream parsing

## Acceptance Criteria

- [ ] SDK query invoked correctly
- [ ] Stream parsing works
- [ ] Results file created
""", encoding='utf-8')

    # Create implementation plan
    plan_dir = worktree / ".claude" / "task-plans"
    plan_dir.mkdir(parents=True)
    plan_file = plan_dir / "TASK-SDK-001-implementation-plan.md"
    plan_file.write_text("""# Implementation Plan: TASK-SDK-001

## Overview

SDK delegation implementation plan.

## Steps

1. Implement SDK query wrapper
2. Add stream parsing
3. Write results to JSON
4. Verify Coach can read results

## Files to Create

- guardkit/orchestrator/sdk_wrapper.py
- tests/test_sdk_wrapper.py

## Estimated Complexity: 4/10
""", encoding='utf-8')

    # Create .guardkit/autobuild directory for results
    autobuild_dir = worktree / ".guardkit" / "autobuild" / "TASK-SDK-001"
    autobuild_dir.mkdir(parents=True)

    return worktree


@pytest.fixture
def agent_invoker(mock_worktree, _routine_seat):
    """Create AgentInvoker instance with task-work delegation enabled, on the routine local seat."""
    return AgentInvoker(
        worktree_path=mock_worktree,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
        use_task_work_delegation=True,
        development_mode="tdd",
        model_name=_routine_seat,
    )


@pytest.fixture
def stream_parser():
    """Create TaskWorkStreamParser instance for testing."""
    return TaskWorkStreamParser()


@pytest.fixture
def sample_sdk_messages():
    """Sample SDK stream messages for testing."""
    return [
        "Phase 2: Implementation Planning...",
        "  Planning implementation approach...",
        "Phase 3: Implementation...",
        "  Creating files...",
        "  Modified: src/feature.py",
        "  Created: tests/test_feature.py",
        "✓ Phase 3 complete",
        "Phase 4: Testing...",
        "  Running tests...",
        "  12 tests passed, 0 tests failed",
        "  Coverage: 85.5%",
        "✓ Phase 4 complete",
        "All quality gates passed",
        "✓ Phase 5 complete",
    ]


@pytest.fixture
def mock_sdk_query():
    """Mock claude_agent_sdk.query() for testing."""
    async def _create_mock_query(messages: List[str], should_timeout: bool = False, should_fail: bool = False):
        """Create a mock query function that yields messages."""
        async def mock_query(prompt: str, options: Any) -> AsyncGenerator:
            if should_timeout:
                await asyncio.sleep(1000)  # Will be cancelled by timeout

            if should_fail:
                raise Exception("SDK query failed")

            for msg in messages:
                yield _assistant(msg)
            yield ResultMessage()

        return mock_query

    return _create_mock_query


# ============================================================================
# TestTaskWorkStreamParser - Stream Parsing Tests
# ============================================================================


@pytest.mark.integration
class TestTaskWorkStreamParser:
    """Test TaskWorkStreamParser for SDK stream processing."""

    def test_parser_initialization(self):
        """Parser initializes with empty state."""
        parser = TaskWorkStreamParser()
        result = parser.to_result()

        assert result == {}

    def test_parse_phase_markers(self, stream_parser):
        """Parser extracts phase markers from stream."""
        stream_parser.parse_message("Phase 2: Implementation Planning")
        stream_parser.parse_message("Phase 3: Implementation")

        result = stream_parser.to_result()

        assert "phases" in result
        assert "phase_2" in result["phases"]
        assert "phase_3" in result["phases"]
        assert result["phases"]["phase_2"]["detected"] is True

    def test_parse_phase_completion(self, stream_parser):
        """Parser detects phase completion markers."""
        stream_parser.parse_message("Phase 3: Implementation")
        stream_parser.parse_message("✓ Phase 3 complete")

        result = stream_parser.to_result()

        assert result["phases"]["phase_3"]["completed"] is True

    def test_parse_test_results(self, stream_parser):
        """Parser extracts test pass/fail counts."""
        stream_parser.parse_message("12 tests passed, 0 tests failed")

        result = stream_parser.to_result()

        assert result["tests_passed"] == 12
        assert result["tests_failed"] == 0

    def test_parse_coverage(self, stream_parser):
        """Parser extracts coverage percentage."""
        stream_parser.parse_message("Coverage: 85.5%")

        result = stream_parser.to_result()

        assert result["coverage"] == 85.5

    def test_parse_quality_gates_passed(self, stream_parser):
        """Parser detects quality gates passed."""
        stream_parser.parse_message("All quality gates passed")

        result = stream_parser.to_result()

        assert result["quality_gates_passed"] is True

    def test_parse_quality_gates_failed(self, stream_parser):
        """Parser detects quality gates failed."""
        stream_parser.parse_message("Quality gates: FAILED")

        result = stream_parser.to_result()

        assert result["quality_gates_passed"] is False

    def test_parse_files_modified(self, stream_parser):
        """Parser extracts modified file paths."""
        stream_parser.parse_message("Modified: src/feature.py")
        stream_parser.parse_message("Changed: src/utils.py")

        result = stream_parser.to_result()

        assert "files_modified" in result
        assert "src/feature.py" in result["files_modified"]
        assert "src/utils.py" in result["files_modified"]

    def test_parse_files_created(self, stream_parser):
        """Parser extracts created file paths."""
        stream_parser.parse_message("Created: tests/test_feature.py")
        stream_parser.parse_message("Added: tests/test_utils.py")

        result = stream_parser.to_result()

        assert "files_created" in result
        assert "tests/test_feature.py" in result["files_created"]
        assert "tests/test_utils.py" in result["files_created"]

    def test_parse_full_stream(self, stream_parser, sample_sdk_messages):
        """Parser correctly processes complete stream."""
        for msg in sample_sdk_messages:
            stream_parser.parse_message(msg)

        result = stream_parser.to_result()

        assert result["tests_passed"] == 12
        assert result["tests_failed"] == 0
        assert result["coverage"] == 85.5
        assert result["quality_gates_passed"] is True
        assert "phases" in result

    def test_parser_reset(self, stream_parser):
        """Parser can be reset for reuse."""
        stream_parser.parse_message("12 tests passed")
        stream_parser.parse_message("Coverage: 90%")

        stream_parser.reset()
        result = stream_parser.to_result()

        assert result == {}

    def test_parser_handles_empty_message(self, stream_parser):
        """Parser handles empty messages gracefully."""
        stream_parser.parse_message("")
        stream_parser.parse_message(None)  # type: ignore

        result = stream_parser.to_result()
        assert result == {}

    def test_parser_deduplicates_files(self, stream_parser):
        """Parser deduplicates file lists."""
        stream_parser.parse_message("Modified: src/feature.py")
        stream_parser.parse_message("Modified: src/feature.py")  # Duplicate
        stream_parser.parse_message("Modified: src/utils.py")

        result = stream_parser.to_result()

        # Should have only 2 unique files
        assert len(result["files_modified"]) == 2


# ============================================================================
# TestSDKDelegationHappyPath - Happy Path Tests
# ============================================================================


def _create_mock_sdk(query_gen):
    """Create mock SDK module with given query generator."""
    mock_sdk = MagicMock()
    mock_sdk.query = query_gen
    mock_sdk.ClaudeAgentOptions = MagicMock()
    mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
    mock_sdk.ProcessError = type("ProcessError", (Exception,), {"exit_code": 1, "stderr": ""})
    mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})
    mock_sdk.AssistantMessage = AssistantMessage
    mock_sdk.TextBlock = TextBlock
    mock_sdk.ResultMessage = ResultMessage
    return mock_sdk


@pytest.mark.integration
class TestSDKDelegationHappyPath:
    """Test happy path for SDK delegation flow."""

    @pytest.mark.personal_run
    def test_invoke_task_work_implement_success(self, agent_invoker, mock_worktree, sample_sdk_messages):
        """SDK invocation succeeds and returns TaskWorkResult."""
        # Create mock SDK response
        async def mock_query_gen(*args, **kwargs):
            for msg in sample_sdk_messages:
                yield _assistant(msg)
            yield ResultMessage()

        mock_sdk = _create_mock_sdk(mock_query_gen)

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                return await agent_invoker._invoke_task_work_implement(
                    task_id="TASK-SDK-001",
                    mode="tdd",
                )

        result = run_async(run_test())

        assert result.success is True
        assert result.error is None
        assert "tests_passed" in result.output or "raw_output" in result.output

    def test_task_work_results_file_written(self, agent_invoker, mock_worktree):
        """task_work_results.json is created after successful invocation."""
        # Parse some messages first
        parser = TaskWorkStreamParser()
        parser.parse_message("12 tests passed, 0 tests failed")
        parser.parse_message("Coverage: 85.5%")
        parser.parse_message("All quality gates passed")
        result_data = parser.to_result()

        # Write results
        results_path = agent_invoker._write_task_work_results("TASK-SDK-001", result_data)

        assert results_path.exists()

        # Verify file content
        with open(results_path) as f:
            results = json.load(f)

        assert results["task_id"] == "TASK-SDK-001"
        assert "quality_gates" in results
        assert results["quality_gates"]["tests_passed"] == 12
        assert results["quality_gates"]["tests_failed"] == 0
        assert results["quality_gates"]["coverage"] == 85.5

    def test_task_work_results_summary_generated(self, agent_invoker):
        """Summary is correctly generated from result data."""
        result_data = {
            "tests_passed": 12,
            "tests_failed": 0,
            "coverage": 85.5,
            "quality_gates_passed": True,
        }

        summary = agent_invoker._generate_summary(result_data)

        assert "12 tests passed" in summary
        assert "85.5% coverage" in summary
        assert "all quality gates passed" in summary

    def test_invoke_player_with_delegation(self, agent_invoker, mock_worktree, sample_sdk_messages):
        """invoke_player delegates to task-work when enabled."""
        # Create mock SDK response
        async def mock_query_gen(*args, **kwargs):
            for msg in sample_sdk_messages:
                yield _assistant(msg)
            yield ResultMessage()

        mock_sdk = _create_mock_sdk(mock_query_gen)

        # Create task_work_results.json that would be written by task-work
        results_dir = mock_worktree / ".guardkit" / "autobuild" / "TASK-SDK-001"
        results_file = results_dir / "task_work_results.json"
        results_file.write_text(json.dumps({
            "task_id": "TASK-SDK-001",
            "completed": True,
            "tests_info": {
                "tests_run": True,
                "tests_passed": True,
                "output_summary": "12 tests passed",
            },
            "files_modified": ["src/feature.py"],
            "files_created": ["tests/test_feature.py"],
        }))

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                with patch.object(agent_invoker, "_ensure_design_approved_state"):
                    return await agent_invoker.invoke_player(
                        task_id="TASK-SDK-001",
                        turn=1,
                        requirements="Implement SDK integration",
                    )

        result = run_async(run_test())

        assert result.agent_type == "player"
        assert result.task_id == "TASK-SDK-001"


# ============================================================================
# TestSDKTimeoutHandling - Timeout Tests
# ============================================================================


@pytest.mark.integration
class TestSDKTimeoutHandling:
    """Test SDK timeout handling."""

    @pytest.mark.personal_run
    def test_sdk_timeout_raises_error(self, mock_worktree, _routine_seat):
        """SDK timeout raises SDKTimeoutError."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            sdk_timeout_seconds=1,  # Very short timeout
            use_task_work_delegation=True,
            model_name=_routine_seat,
        )

        # Create mock that simulates slow response
        async def slow_query(*args, **kwargs):
            await asyncio.sleep(10)  # Will be cancelled
            yield MagicMock(content="Never reached")

        mock_sdk = _create_mock_sdk(slow_query)

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                return await invoker._invoke_task_work_implement(
                    task_id="TASK-SDK-001",
                    mode="tdd",
                )

        with pytest.raises(SDKTimeoutError) as exc_info:
            run_async(run_test())

        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.personal_run
    def test_invoke_player_timeout_returns_failure(self, mock_worktree, _routine_seat):
        """invoke_player returns failure result on timeout."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            sdk_timeout_seconds=1,
            use_task_work_delegation=True,
            model_name=_routine_seat,
        )

        async def slow_query(*args, **kwargs):
            await asyncio.sleep(10)
            yield MagicMock(content="Never reached")

        mock_sdk = _create_mock_sdk(slow_query)

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                with patch.object(invoker, "_ensure_design_approved_state"):
                    return await invoker.invoke_player(
                        task_id="TASK-SDK-001",
                        turn=1,
                        requirements="Test task",
                    )

        result = run_async(run_test())

        assert result.success is False
        assert "timeout" in result.error.lower()
        assert result.report == {}


# ============================================================================
# TestSDKErrorHandling - Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestSDKErrorHandling:
    """Test SDK error handling scenarios."""

    @pytest.mark.personal_run
    def test_sdk_import_error_handled(self, mock_worktree, _routine_seat):
        """Missing SDK import is handled gracefully."""
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
            model_name=_routine_seat,
        )

        async def run_test():
            # Patch sys.modules to simulate missing SDK
            with patch.dict(sys.modules, {"claude_agent_sdk": None}):
                return await invoker._invoke_task_work_implement(
                    task_id="TASK-SDK-001",
                    mode="tdd",
                )

        result = run_async(run_test())

        assert result.success is False
        assert "Claude Agent SDK" in result.error or "import" in result.error.lower()

    @pytest.mark.personal_run
    def test_sdk_process_error_handled(self, agent_invoker):
        """SDK ProcessError is handled gracefully."""
        ProcessError = type("ProcessError", (Exception,), {"exit_code": 1, "stderr": "Command failed"})

        async def failing_query(*args, **kwargs):
            raise ProcessError("Process failed")
            yield  # Make it a generator

        mock_sdk = _create_mock_sdk(failing_query)
        mock_sdk.ProcessError = ProcessError

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                return await agent_invoker._invoke_task_work_implement(
                    task_id="TASK-SDK-001",
                    mode="tdd",
                )

        result = run_async(run_test())

        assert result.success is False
        # THE STUB'S OWN FAILURE, not any failure: the configured ProcessError's
        # stderr reaches the result. A run refused before the SDK is called (a
        # fence refusal, a harness that cannot be built) also fails, but does
        # not carry these words, and fails here.
        assert "Command failed" in result.error

    @pytest.mark.personal_run
    def test_sdk_generic_error_handled(self, agent_invoker):
        """Generic SDK errors are handled gracefully."""
        async def failing_query(*args, **kwargs):
            raise Exception("Unexpected SDK error")
            yield  # Make it a generator

        mock_sdk = _create_mock_sdk(failing_query)

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                return await agent_invoker._invoke_task_work_implement(
                    task_id="TASK-SDK-001",
                    mode="tdd",
                )

        result = run_async(run_test())

        assert result.success is False
        assert "Unexpected SDK error" in result.error


# ============================================================================
# TestCoachValidation - Coach Validation Tests
# ============================================================================


@pytest.mark.integration
class TestCoachValidation:
    """Test Coach validation of task-work results."""

    def test_coach_can_read_task_work_results(self, agent_invoker, mock_worktree):
        """Coach can read and validate task_work_results.json."""
        # Write task-work results
        result_data = {
            "tests_passed": 12,
            "tests_failed": 0,
            "coverage": 85.5,
            "quality_gates_passed": True,
            "files_modified": ["src/feature.py"],
            "files_created": ["tests/test_feature.py"],
        }

        results_path = agent_invoker._write_task_work_results("TASK-SDK-001", result_data)

        # Verify Coach can read the file
        with open(results_path) as f:
            results = json.load(f)

        assert results["completed"] is True
        assert results["quality_gates"]["tests_passed"] == 12
        assert results["quality_gates"]["all_passed"] is True

    def test_task_work_results_schema(self, agent_invoker, mock_worktree):
        """task_work_results.json follows expected schema."""
        result_data = {
            "tests_passed": 10,
            "tests_failed": 2,
            "coverage": 75.0,
            "quality_gates_passed": False,
        }

        results_path = agent_invoker._write_task_work_results("TASK-SDK-001", result_data)

        with open(results_path) as f:
            results = json.load(f)

        # Verify schema
        assert "task_id" in results
        assert "timestamp" in results
        assert "completed" in results
        assert "phases" in results
        assert "quality_gates" in results
        assert "files_modified" in results
        assert "files_created" in results
        assert "summary" in results

        # Verify quality_gates sub-schema
        qg = results["quality_gates"]
        assert "tests_passing" in qg
        assert "tests_passed" in qg
        assert "tests_failed" in qg
        assert "coverage" in qg
        assert "coverage_met" in qg
        assert "all_passed" in qg

    def test_results_file_deduplicates_files(self, agent_invoker, mock_worktree):
        """Results file deduplicates file lists."""
        result_data = {
            "files_modified": ["src/a.py", "src/a.py", "src/b.py"],
            "files_created": ["tests/test_a.py", "tests/test_a.py"],
        }

        results_path = agent_invoker._write_task_work_results("TASK-SDK-001", result_data)

        with open(results_path) as f:
            results = json.load(f)

        assert len(results["files_modified"]) == 2
        assert len(results["files_created"]) == 1


# ============================================================================
# TestParseTaskWorkStream - Stream Integration Tests
# ============================================================================


@pytest.mark.integration
class TestParseTaskWorkStream:
    """Test _parse_task_work_stream integration."""

    def test_parse_stream_accumulates_results(self, agent_invoker):
        """Stream parsing accumulates results across messages."""
        parser = TaskWorkStreamParser()

        messages = [
            "Phase 2: Planning",
            "Phase 3: Implementation",
            "5 tests passed",
            "Coverage: 80%",
        ]

        for msg in messages:
            result = agent_invoker._parse_task_work_stream(msg, parser)

        # Final result should have accumulated data
        assert "phases" in result
        assert result.get("tests_passed") == 5
        assert result.get("coverage") == 80

    def test_parse_stream_returns_current_state(self, agent_invoker):
        """Each parse call returns current accumulated state."""
        parser = TaskWorkStreamParser()

        result1 = agent_invoker._parse_task_work_stream("5 tests passed", parser)
        assert result1.get("tests_passed") == 5
        assert result1.get("coverage") is None

        result2 = agent_invoker._parse_task_work_stream("Coverage: 90%", parser)
        assert result2.get("tests_passed") == 5  # Still has previous
        assert result2.get("coverage") == 90  # Added new


# ============================================================================
# TestDevelopmentModeHandling - Mode Parameter Tests
# ============================================================================


@pytest.mark.integration
class TestDevelopmentModeHandling:
    """Test development mode parameter handling in SDK delegation."""

    @pytest.mark.personal_run
    @pytest.mark.parametrize("mode", ["tdd", "standard", "bdd"])
    def test_mode_included_in_sdk_prompt(self, mock_worktree, mode, _routine_seat):
        """Development mode is included in SDK prompt."""
        # The invoker's own mode differs from the call's, so the prompt must
        # carry the mode passed to this call, not the instance default.
        invoker = AgentInvoker(
            worktree_path=mock_worktree,
            use_task_work_delegation=True,
            development_mode="tdd" if mode != "tdd" else "standard",
            model_name=_routine_seat,
        )

        captured_prompt = None

        async def capture_query(prompt: str, options: Any):
            nonlocal captured_prompt
            captured_prompt = prompt
            # Yield a single message then stop
            yield MagicMock(content="Done")

        mock_sdk = _create_mock_sdk(capture_query)

        async def run_test():
            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                try:
                    return await invoker._invoke_task_work_implement(
                        task_id="TASK-SDK-001",
                        mode=mode,
                    )
                except StopIteration:
                    pass  # Expected when query yields nothing

        run_async(run_test())

        assert captured_prompt is not None
        # The prompt states the mode in its Context block. It used to be the
        # slash command "/task-work <id> --implement-only --mode=<mode>"; that
        # was replaced by an inline protocol on 15 February 2026 (42a07adda,
        # TASK-POF-004) and the line now comes from
        # _build_autobuild_implementation_prompt (TASK-ACO-002, 28534d78b).
        assert f"- Mode: {mode}\n" in captured_prompt

    def test_mode_defaults_to_instance_mode(self, agent_invoker):
        """Mode defaults to instance development_mode when not specified."""
        assert agent_invoker.development_mode == "tdd"

        # The mode parameter in invoke_player should use instance mode when None
        effective_mode = "bdd" if None is not None else agent_invoker.development_mode
        assert effective_mode == "tdd"


# ============================================================================
# TestTaskWorkOutputParsing - Output Parsing Tests
# ============================================================================


@pytest.mark.integration
class TestTaskWorkOutputParsing:
    """Test _parse_task_work_output for batch parsing."""

    def test_parse_output_detects_tests_passed(self, agent_invoker):
        """Output parser detects passing tests."""
        stdout = "All tests passing ✅"

        output = agent_invoker._parse_task_work_output(stdout)

        assert output["tests_passed"] is True

    def test_parse_output_extracts_coverage(self, agent_invoker):
        """Output parser extracts coverage percentage."""
        stdout = "Line Coverage: 85.5%"

        output = agent_invoker._parse_task_work_output(stdout)

        assert output["coverage_line"] == 85.5

    def test_parse_output_extracts_branch_coverage(self, agent_invoker):
        """Output parser extracts branch coverage."""
        stdout = "Branch Coverage: 78.2%"

        output = agent_invoker._parse_task_work_output(stdout)

        assert output["coverage_branch"] == 78.2

    def test_parse_output_detects_quality_gates(self, agent_invoker):
        """Output parser detects quality gates status."""
        stdout = "All quality gates passed\nTask State: IN_REVIEW"

        output = agent_invoker._parse_task_work_output(stdout)

        assert output["quality_gates_passed"] is True

    def test_parse_output_includes_raw(self, agent_invoker):
        """Output parser includes raw output."""
        stdout = "Some task output here"

        output = agent_invoker._parse_task_work_output(stdout)

        assert output["raw_output"] == stdout


# ============================================================================
# TestCoachResultsValidation - Coach can read task_work_results.json
# ============================================================================


@pytest.mark.integration
class TestCoachResultsValidation:
    """Test that Coach can validate results written by _invoke_task_work_implement."""

    @pytest.mark.personal_run
    def test_full_flow_creates_results_for_coach(
        self, agent_invoker, mock_worktree, sample_sdk_messages, mock_sdk_query
    ):
        """Full delegation flow creates results file that Coach can validate."""

        async def run_test():
            # Create mock SDK that yields sample messages
            mock_query = await mock_sdk_query(sample_sdk_messages)

            # Create mock SDK module
            mock_sdk = _create_mock_sdk(mock_query)

            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                result = await agent_invoker._invoke_task_work_implement(
                    task_id="TASK-SDK-001",
                    mode="tdd",
                )

            assert result.success is True

            # Verify results file was created
            results_path = mock_worktree / ".guardkit" / "autobuild" / "TASK-SDK-001" / "task_work_results.json"
            assert results_path.exists(), "task_work_results.json should exist after invocation"

            # Verify Coach can read and parse the results
            results = json.loads(results_path.read_text())
            assert results["task_id"] == "TASK-SDK-001"
            assert "quality_gates" in results
            assert "timestamp" in results

            # Verify quality gates have expected structure
            quality_gates = results["quality_gates"]
            assert "tests_passing" in quality_gates
            assert "coverage" in quality_gates
            assert "all_passed" in quality_gates
            # ... and carry what the stream said ("12 tests passed",
            # "Coverage: 85.5%"), so the file is built from the output.
            assert quality_gates["tests_passed"] == 12
            assert quality_gates["coverage"] == 85.5

        run_async(run_test())

    @pytest.mark.personal_run
    def test_results_file_has_coach_expected_structure(
        self, agent_invoker, mock_worktree, mock_sdk_query
    ):
        """Results file matches Coach's expected schema for validation."""

        async def run_test():
            # Create mock SDK with comprehensive output
            messages = [
                "Phase 2: Implementation Planning",
                "Phase 3: Implementation",
                "Modified: src/auth.py",
                "Created: tests/test_auth.py",
                "Phase 4: Testing",
                "15 tests passed, 0 tests failed",
                "Coverage: 92.5%",
                "All quality gates passed",
                "IN_REVIEW",
            ]
            mock_query = await mock_sdk_query(messages)

            mock_sdk = _create_mock_sdk(mock_query)

            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                result = await agent_invoker._invoke_task_work_implement(
                    task_id="TASK-COACH-001",
                    mode="standard",
                )

            assert result.success is True

            # Verify Coach-expected fields
            results_path = mock_worktree / ".guardkit" / "autobuild" / "TASK-COACH-001" / "task_work_results.json"
            results = json.loads(results_path.read_text())

            # Coach validates these specific fields
            assert results["task_id"] == "TASK-COACH-001"
            assert results["completed"] is True  # No test failures
            assert results["quality_gates"]["tests_passed"] == 15
            assert results["quality_gates"]["tests_failed"] == 0
            assert results["quality_gates"]["coverage"] == 92.5
            # Recorded, not judged: the Coach decides coverage from the
            # project's declared command, or leaves it UNKNOWN.
            assert results["quality_gates"]["coverage_met"] is None
            assert results["quality_gates"]["tests_passing"] is True

        run_async(run_test())

    @pytest.mark.personal_run
    def test_failure_results_file_written_on_sdk_failure(
        self, agent_invoker, mock_worktree
    ):
        """A failed SDK invocation still leaves a results file, marked failed.

        ``_write_failure_results`` has run on every error path since this file
        was added (b7f0472ac): "Called on ALL error paths to ensure Coach
        receives actionable information instead of 'results not found'". So
        the Coach reads a failure record naming the cause, never a missing
        file and never a success.
        """

        async def run_test():
            # Create mock SDK that raises ProcessError
            ProcessError = type("ProcessError", (Exception,), {})

            async def mock_query_error(*args, **kwargs):
                error = ProcessError("Process failed")
                error.exit_code = 1
                error.stderr = "Error: tests failed"
                raise error
                yield  # Make it a generator

            mock_sdk = MagicMock()
            mock_sdk.query = mock_query_error
            mock_sdk.ClaudeAgentOptions = MagicMock()
            mock_sdk.CLINotFoundError = type("CLINotFoundError", (Exception,), {})
            mock_sdk.ProcessError = ProcessError
            mock_sdk.CLIJSONDecodeError = type("CLIJSONDecodeError", (Exception,), {})

            with patch.dict(sys.modules, {"claude_agent_sdk": mock_sdk}):
                result = await agent_invoker._invoke_task_work_implement(
                    task_id="TASK-FAIL-001",
                    mode="tdd",
                )

            assert result.success is False
            assert "Error: tests failed" in result.error

            # The Coach gets a failure record, not a missing file.
            results_path = mock_worktree / ".guardkit" / "autobuild" / "TASK-FAIL-001" / "task_work_results.json"
            assert results_path.exists(), "task_work_results.json should record the failure"
            results = json.loads(results_path.read_text())
            assert results["task_id"] == "TASK-FAIL-001"
            assert results["completed"] is False
            assert results["success"] is False
            assert results["quality_gates"]["all_passed"] is False
            assert "Error: tests failed" in results["error"]

        run_async(run_test())


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
