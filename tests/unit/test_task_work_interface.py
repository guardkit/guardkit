"""
Unit tests for TaskWorkInterface SDK integration.

Tests cover:
    - SDK-based execute_design_phase() method
    - Prompt construction for /task-work --design-only
    - Result parsing from SDK output
    - Error handling and fallback behavior

Coverage Target: >=85%
Test Count: 25+ tests
"""

import asyncio
import json
import pytest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import sys
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates.task_work_interface import (
    DEFAULT_SDK_TIMEOUT,
    DesignPhaseResult,
    TaskWorkInterface,
)
from guardkit.orchestrator.quality_gates.exceptions import (
    DesignPhaseError,
    QualityGateBlocked,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def interface(tmp_worktree):
    """Create a TaskWorkInterface instance."""
    return TaskWorkInterface(tmp_worktree)


@pytest.fixture
def mock_sdk_query():
    """Create a mock for claude_agent_sdk.query()."""
    async def mock_query(*args, **kwargs):
        # Yield mock messages simulating SDK output
        messages = [
            Mock(content="Phase 2: Implementation Planning..."),
            Mock(content="Phase 2.5B: Architectural Review..."),
            Mock(content="Architectural Score: 85/100"),
            Mock(content="SOLID: 88, DRY: 82, YAGNI: 85"),
            Mock(content="Complexity Score: 6/10"),
            Mock(content="Plan saved to: docs/state/TASK-001/implementation_plan.md"),
            Mock(content="Phase 2.8: checkpoint approved"),
            Mock(content="State: DESIGN_APPROVED"),
        ]
        for msg in messages:
            yield msg

    return mock_query


@pytest.fixture
def mock_sdk_module(mock_sdk_query):
    """Create a complete mock SDK module."""
    mock_module = MagicMock()
    mock_module.query = mock_sdk_query
    mock_module.ClaudeAgentOptions = MagicMock()
    mock_module.CLINotFoundError = Exception
    mock_module.ProcessError = Exception
    mock_module.CLIJSONDecodeError = Exception
    return mock_module


# ============================================================================
# Mock ContentBlock Classes for TASK-FB-FIX-005 Tests
# ============================================================================


class MockTextBlock:
    """Mock TextBlock with text attribute."""

    def __init__(self, text: str):
        self.text = text


class MockToolUseBlock:
    """Mock ToolUseBlock with name attribute."""

    def __init__(self, name: str):
        self.name = name


class MockToolResultBlock:
    """Mock ToolResultBlock with content attribute."""

    def __init__(self, content: Any = None):
        self.content = content


class MockAssistantMessage:
    """Mock AssistantMessage with content list."""

    def __init__(self, content: list):
        self.content = content


class MockResultMessage:
    """Mock ResultMessage with num_turns attribute."""

    def __init__(self, num_turns: int):
        self.num_turns = num_turns


@pytest.fixture
def mock_contentblock_sdk_query():
    """Create a mock SDK query that yields proper ContentBlock-based messages.

    TASK-FB-FIX-005: This fixture tests the correct parsing of SDK messages
    where message.content is a list of ContentBlock objects, not a string.
    """
    async def mock_query(*args, **kwargs):
        # Yield mock messages with proper ContentBlock structure
        messages = [
            MockAssistantMessage(content=[
                MockTextBlock("Phase 2: Implementation Planning..."),
            ]),
            MockAssistantMessage(content=[
                MockTextBlock("Phase 2.5B: Architectural Review..."),
                MockToolUseBlock("architectural-reviewer"),
            ]),
            MockAssistantMessage(content=[
                MockTextBlock("Architectural Score: 85/100"),
                MockTextBlock("SOLID: 88, DRY: 82, YAGNI: 85"),
            ]),
            MockAssistantMessage(content=[
                MockTextBlock("Complexity Score: 6/10"),
            ]),
            MockAssistantMessage(content=[
                MockTextBlock("Plan saved to: docs/state/TASK-001/implementation_plan.md"),
            ]),
            MockAssistantMessage(content=[
                MockTextBlock("Phase 2.8: checkpoint approved"),
                MockTextBlock("State: DESIGN_APPROVED"),
            ]),
            MockResultMessage(num_turns=5),
        ]
        for msg in messages:
            yield msg

    return mock_query


@pytest.fixture
def mock_contentblock_sdk_module(mock_contentblock_sdk_query):
    """Create a complete mock SDK module with ContentBlock types.

    TASK-FB-FIX-005: This module includes the ContentBlock types needed
    for proper isinstance() checks in the fixed _execute_via_sdk().
    """
    mock_module = MagicMock()
    mock_module.query = mock_contentblock_sdk_query
    mock_module.ClaudeAgentOptions = MagicMock()
    mock_module.CLINotFoundError = Exception
    mock_module.ProcessError = Exception
    mock_module.CLIJSONDecodeError = Exception
    # Add ContentBlock types for isinstance() checks
    mock_module.AssistantMessage = MockAssistantMessage
    mock_module.TextBlock = MockTextBlock
    mock_module.ToolUseBlock = MockToolUseBlock
    mock_module.ToolResultBlock = MockToolResultBlock
    mock_module.ResultMessage = MockResultMessage
    return mock_module


# ============================================================================
# Test Initialization
# ============================================================================


class TestTaskWorkInterfaceInit:
    """Test TaskWorkInterface initialization."""

    def test_init_sets_worktree_path(self, tmp_worktree):
        """Test worktree path is set correctly."""
        interface = TaskWorkInterface(tmp_worktree)
        assert interface.worktree_path == tmp_worktree

    def test_init_sets_default_timeout(self, tmp_worktree):
        """Test default SDK timeout is set."""
        interface = TaskWorkInterface(tmp_worktree)
        assert interface.sdk_timeout_seconds == DEFAULT_SDK_TIMEOUT

    def test_init_accepts_custom_timeout(self, tmp_worktree):
        """Test custom SDK timeout can be specified."""
        interface = TaskWorkInterface(tmp_worktree, sdk_timeout_seconds=300)
        assert interface.sdk_timeout_seconds == 300

    def test_init_converts_string_path(self, tmp_worktree):
        """Test string path is converted to Path."""
        interface = TaskWorkInterface(str(tmp_worktree))
        assert isinstance(interface.worktree_path, Path)
        assert interface.worktree_path == tmp_worktree


# ============================================================================
# Test Prompt Construction
# ============================================================================


class TestBuildDesignPrompt:
    """Test _build_design_prompt() returns inline protocol (TASK-POF-003)."""

    def test_inline_protocol_includes_task_id(self, interface):
        """Test inline protocol contains the task ID."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "TASK-001" in prompt

    def test_inline_protocol_not_skill_invocation(self, interface):
        """Test prompt is NOT a /task-work skill invocation."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert not prompt.startswith("/task-work")

    def test_inline_protocol_includes_phase_instructions(self, interface):
        """Test protocol includes instructions for all design phases."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "Phase 1.5" in prompt
        assert "Phase 2:" in prompt or "Phase 2 " in prompt or "Implementation Planning" in prompt
        assert "Phase 2.7" in prompt or "Complexity" in prompt
        assert "Phase 2.8" in prompt or "checkpoint" in prompt.lower()

    def test_inline_protocol_includes_plan_save_path(self, interface):
        """Test protocol specifies the plan save path."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert ".claude/task-plans/TASK-001-implementation-plan.md" in prompt

    def test_inline_protocol_includes_output_markers(self, interface):
        """Test protocol instructs agent to output parseable markers."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "Plan saved to:" in prompt
        assert "Complexity:" in prompt
        assert "checkpoint approved" in prompt

    def test_inline_protocol_with_docs_level(self, interface):
        """Test docs level is embedded in protocol."""
        prompt = interface._build_design_prompt("TASK-001", {"docs": "comprehensive"})

        assert "comprehensive" in prompt

    def test_inline_protocol_default_docs_minimal(self, interface):
        """Test default docs level is minimal."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "minimal" in prompt

    def test_inline_protocol_skip_arch_review(self, interface):
        """Test Phase 2.5B is omitted when skip_arch_review is set."""
        prompt = interface._build_design_prompt("TASK-001", {"skip_arch_review": True})

        assert "Phase 2.5B" not in prompt
        assert "Architectural Review" not in prompt
        assert "SOLID" not in prompt

    def test_inline_protocol_includes_arch_review_by_default(self, interface):
        """Test Phase 2.5B is included by default."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "Phase 2.5B" in prompt or "Architectural Review" in prompt
        assert "SOLID" in prompt
        assert "DRY" in prompt
        assert "YAGNI" in prompt

    def test_inline_protocol_size_within_limit(self, interface):
        """Test inline protocol is within 20KB limit."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert len(prompt.encode("utf-8")) <= 20480, (
            f"Protocol size {len(prompt.encode('utf-8'))} exceeds 20KB limit"
        )


# ============================================================================
# Test SDK Output Parsing
# ============================================================================


class TestParseSDKOutput:
    """Test _parse_sdk_output() method."""

    def test_parses_plan_path_from_saved_message(self, interface):
        """Test plan path is extracted from 'Plan saved to:' message."""
        output = "Phase 2 complete\nPlan saved to: docs/state/TASK-001/implementation_plan.md\nDone"

        result = interface._parse_sdk_output(output)

        assert result["plan_path"] == "docs/state/TASK-001/implementation_plan.md"

    def test_parses_complexity_score(self, interface):
        """Test complexity score is extracted."""
        output = "Phase 2.7: Complexity Score: 7/10"

        result = interface._parse_sdk_output(output)

        assert result["complexity"]["score"] == 7

    def test_parses_architectural_score(self, interface):
        """Test architectural review score is extracted."""
        output = "Phase 2.5B: Architectural Score: 92/100"

        result = interface._parse_sdk_output(output)

        assert result["architectural_review"]["score"] == 92

    def test_parses_solid_score(self, interface):
        """Test SOLID score is extracted."""
        output = "SOLID: 88/100"

        result = interface._parse_sdk_output(output)

        assert result["architectural_review"]["solid"] == 88

    def test_parses_dry_score(self, interface):
        """Test DRY score is extracted."""
        output = "DRY: 75/100"

        result = interface._parse_sdk_output(output)

        assert result["architectural_review"]["dry"] == 75

    def test_parses_yagni_score(self, interface):
        """Test YAGNI score is extracted."""
        output = "YAGNI: 90/100"

        result = interface._parse_sdk_output(output)

        assert result["architectural_review"]["yagni"] == 90

    def test_parses_approved_checkpoint(self, interface):
        """Test checkpoint approved is detected."""
        output = "Phase 2.8: checkpoint approved\nState: DESIGN_APPROVED"

        result = interface._parse_sdk_output(output)

        assert result["checkpoint_result"] == "approved"

    def test_parses_rejected_checkpoint(self, interface):
        """Test checkpoint rejected is detected."""
        output = "Phase 2.8: checkpoint rejected - complexity too high"

        result = interface._parse_sdk_output(output)

        assert result["checkpoint_result"] == "rejected"

    def test_parses_skipped_checkpoint(self, interface):
        """Test auto-proceed/skipped checkpoint is detected."""
        output = "Low complexity - auto-proceed to Phase 3"

        result = interface._parse_sdk_output(output)

        assert result["checkpoint_result"] == "skipped"

    def test_returns_defaults_for_empty_output(self, interface):
        """Test sensible defaults are returned for empty output."""
        result = interface._parse_sdk_output("")

        assert result["complexity"]["score"] == 5
        assert result["checkpoint_result"] == "approved"
        assert result["architectural_review"]["score"] == 80

    def test_loads_plan_content_from_file(self, interface, tmp_worktree):
        """Test implementation plan content is loaded from file."""
        # Create plan file
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.json"
        plan_content = {"steps": ["Step 1", "Step 2"]}
        plan_file.write_text(json.dumps(plan_content))

        output = f"Plan saved to: {plan_file}"

        result = interface._parse_sdk_output(output)

        assert result["implementation_plan"] == plan_content


# ============================================================================
# Test Execute Design Phase
# ============================================================================


class TestExecuteDesignPhase:
    """Test execute_design_phase() method."""

    @pytest.mark.asyncio
    async def test_invokes_sdk_with_inline_protocol(
        self, interface, mock_sdk_module, tmp_worktree
    ):
        """Test SDK is invoked with inline protocol containing task ID."""
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk_module}):
            with patch.object(interface, "_execute_via_sdk") as mock_execute:
                mock_execute.return_value = {
                    "implementation_plan": {},
                    "plan_path": "/path/to/plan.md",
                    "complexity": {"score": 5},
                    "checkpoint_result": "approved",
                    "architectural_review": {"score": 80},
                    "clarifications": {},
                }

                await interface.execute_design_phase("TASK-001", {"no_questions": True})

                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0][0]
                # TASK-POF-003: Prompt is now inline protocol, not skill invocation
                assert "TASK-001" in call_args
                assert not call_args.startswith("/task-work")

    @pytest.mark.asyncio
    async def test_returns_design_phase_result(self, interface):
        """Test execute_design_phase returns DesignPhaseResult."""
        with patch.object(interface, "_execute_via_sdk") as mock_execute:
            mock_execute.return_value = {
                "implementation_plan": {"steps": ["Step 1"]},
                "plan_path": "/path/to/plan.md",
                "complexity": {"score": 6},
                "checkpoint_result": "approved",
                "architectural_review": {"score": 85},
                "clarifications": {"scope": "standard"},
            }

            result = await interface.execute_design_phase("TASK-001", {})

            assert isinstance(result, DesignPhaseResult)
            assert result.implementation_plan == {"steps": ["Step 1"]}
            assert result.plan_path == "/path/to/plan.md"
            assert result.complexity == {"score": 6}
            assert result.checkpoint_result == "approved"

    @pytest.mark.asyncio
    async def test_falls_back_to_subprocess_on_import_error(self, interface):
        """Test subprocess fallback when SDK import fails."""
        with patch.object(interface, "_execute_via_sdk") as mock_sdk:
            mock_sdk.side_effect = ImportError("SDK not available")

            with patch.object(interface, "_execute_via_subprocess") as mock_subprocess:
                mock_subprocess.return_value = {
                    "implementation_plan": {},
                    "plan_path": None,
                    "complexity": {"score": 5},
                    "checkpoint_result": "approved",
                    "architectural_review": {"score": 80},
                    "clarifications": {},
                }

                result = await interface.execute_design_phase("TASK-001", {})

                mock_subprocess.assert_called_once()
                assert isinstance(result, DesignPhaseResult)

    @pytest.mark.asyncio
    async def test_raises_quality_gate_blocked_for_low_arch_score(self, interface):
        """Test QualityGateBlocked raised for low architectural score."""
        with patch.object(interface, "_execute_via_sdk") as mock_execute:
            mock_execute.return_value = {
                "implementation_plan": {},
                "plan_path": None,
                "complexity": {"score": 5},
                "checkpoint_result": "approved",
                "architectural_review": {"score": 45},  # Below 60 threshold
                "clarifications": {},
            }

            with pytest.raises(QualityGateBlocked) as exc_info:
                await interface.execute_design_phase("TASK-001", {})

            assert "architectural_review" in exc_info.value.gate_name


# ============================================================================
# Test Harness Dispatch (TASK-HMIG-006.4)
# ============================================================================


from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)


class _FakeHarness:
    """Minimal HarnessAdapter double yielding scripted HarnessEvents.

    TASK-HMIG-006.4: ``_execute_via_sdk`` now dispatches through
    ``select_harness()`` and consumes the substrate-agnostic
    ``HarnessEvent`` stream. These tests mock at that seam (the
    architecturally correct boundary) instead of the now-internal
    ``claude_agent_sdk`` import. Records the ``invoke()`` call kwargs so
    tests can assert prompt / role / cwd / timeout forwarding.
    """

    def __init__(self, events):
        self._events = list(events)
        self.invoke_calls = []

    async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
        self.invoke_calls.append(
            {
                "prompt": prompt,
                "role": role,
                "tools": tools,
                "cwd": cwd,
                "timeout_seconds": timeout_seconds,
            }
        )
        for event in self._events:
            yield event

    @property
    def supports_resume(self):
        return False


def _design_phase_events():
    """Scripted harness events mirroring a successful design-phase run."""
    return [
        AssistantMessageEvent(text="Phase 2: Implementation Planning..."),
        AssistantMessageEvent(
            text="Architectural Score: 85/100\nSOLID: 88, DRY: 82, YAGNI: 85"
        ),
        AssistantMessageEvent(text="Complexity Score: 6/10"),
        AssistantMessageEvent(
            text="Plan saved to: docs/state/TASK-001/implementation_plan.md"
        ),
        AssistantMessageEvent(
            text="Phase 2.8: checkpoint approved\nState: DESIGN_APPROVED"
        ),
        ResultMessageEvent(session_id="sess-design-1"),
    ]


_SELECT_HARNESS = "guardkit.orchestrator.harness.select_harness"


class TestHarnessDispatch:
    """TASK-HMIG-006.4 AC-001: design phase routes through select_harness().

    The pre-loop design phase no longer imports claude_agent_sdk directly;
    it dispatches through the GUARDKIT_HARNESS-driven harness seam, the
    same boundary agent_invoker._invoke_with_role crosses.
    """

    @pytest.mark.asyncio
    async def test_routes_through_select_harness(self, interface):
        """AC-001/AC-004: select_harness() is invoked (no direct SDK import)."""
        fake = _FakeHarness(_design_phase_events())

        with patch(_SELECT_HARNESS, return_value=fake) as mock_select:
            await interface._execute_via_sdk("design prompt for TASK-001")

        mock_select.assert_called_once()

    @pytest.mark.asyncio
    async def test_forwards_pre_loop_sdk_kwargs(self, interface):
        """AC-002: the four pre-loop SDK kwargs are forwarded to select_harness()."""
        fake = _FakeHarness(_design_phase_events())

        with patch(_SELECT_HARNESS, return_value=fake) as mock_select:
            await interface._execute_via_sdk("design prompt for TASK-001")

        kwargs = mock_select.call_args.kwargs
        assert kwargs["setting_sources"] == ["project"]
        assert kwargs["max_turns"] == 25
        assert kwargs["permission_mode"] == "acceptEdits"
        assert "Skill" not in kwargs["allowed_tools"]
        assert "Task" not in kwargs["allowed_tools"]
        assert "Read" in kwargs["allowed_tools"]
        assert kwargs["sdk_timeout_seconds"] == interface.sdk_timeout_seconds

    @pytest.mark.asyncio
    async def test_invoke_receives_prompt_and_cwd(self, interface, tmp_worktree):
        """harness.invoke() receives the prompt and the worktree cwd."""
        fake = _FakeHarness(_design_phase_events())

        with patch(_SELECT_HARNESS, return_value=fake):
            await interface._execute_via_sdk("design prompt for TASK-001")

        assert len(fake.invoke_calls) == 1
        call = fake.invoke_calls[0]
        assert call["prompt"] == "design prompt for TASK-001"
        assert call["cwd"] == tmp_worktree
        assert call["timeout_seconds"] == interface.sdk_timeout_seconds

    @pytest.mark.asyncio
    async def test_extracts_plan_path_from_event_text(self, interface, tmp_worktree):
        """Assistant event text is collected and parsed for the plan path."""
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        (plan_dir / "implementation_plan.md").write_text("# Plan")

        fake = _FakeHarness(_design_phase_events())
        with patch(_SELECT_HARNESS, return_value=fake):
            result = await interface._execute_via_sdk("design prompt for TASK-001")

        assert result["plan_path"] == "docs/state/TASK-001/implementation_plan.md"

    @pytest.mark.asyncio
    async def test_extracts_complexity_and_arch_scores(self, interface):
        """Complexity + SOLID/DRY/YAGNI scores parsed from collected event text."""
        fake = _FakeHarness(_design_phase_events())
        with patch(_SELECT_HARNESS, return_value=fake):
            result = await interface._execute_via_sdk("design prompt for TASK-001")

        assert result["complexity"]["score"] == 6
        assert result["architectural_review"]["score"] == 85
        assert result["architectural_review"]["solid"] == 88

    @pytest.mark.asyncio
    async def test_checkpoint_approved_detected(self, interface):
        """Checkpoint approval is detected from collected event text."""
        fake = _FakeHarness(_design_phase_events())
        with patch(_SELECT_HARNESS, return_value=fake):
            result = await interface._execute_via_sdk("design prompt for TASK-001")

        assert result["checkpoint_result"] == "approved"

    @pytest.mark.asyncio
    async def test_result_message_event_terminates_loop(self, interface):
        """Events after the terminal ResultMessageEvent are not consumed."""
        events = [
            AssistantMessageEvent(text="Complexity: 5/10"),
            ResultMessageEvent(session_id=None),
            AssistantMessageEvent(text="Plan saved to: should/not/be/parsed.md"),
        ]
        fake = _FakeHarness(events)
        with patch(_SELECT_HARNESS, return_value=fake):
            result = await interface._execute_via_sdk("design prompt for TASK-001")

        # The post-terminal event must not contribute to the parsed output.
        assert result["plan_path"] != "should/not/be/parsed.md"

    @pytest.mark.asyncio
    async def test_api_error_in_raw_raises_design_phase_error(self, interface):
        """A bug-#472 API error on event.raw surfaces as DesignPhaseError."""

        class _ErrMsg:
            error = "rate limit exceeded"
            content = []

        events = [AssistantMessageEvent(text="", raw=_ErrMsg())]
        fake = _FakeHarness(events)
        with patch(_SELECT_HARNESS, return_value=fake):
            with pytest.raises(DesignPhaseError):
                await interface._execute_via_sdk("design prompt for TASK-001")

    @pytest.mark.asyncio
    async def test_handles_result_message_gracefully(self, interface):
        """ResultMessageEvent terminal is handled without errors."""
        fake = _FakeHarness(_design_phase_events())
        with patch(_SELECT_HARNESS, return_value=fake):
            result = await interface._execute_via_sdk("design prompt for TASK-001")

        assert "complexity" in result
        assert "checkpoint_result" in result

    @pytest.mark.asyncio
    async def test_debug_logging_short_output(self, interface, caplog):
        """DEBUG output-length logging runs for short collected output (<500)."""
        import logging as _logging

        fake = _FakeHarness(
            [
                AssistantMessageEvent(text="Complexity: 5/10"),
                ResultMessageEvent(session_id=None),
            ]
        )
        with caplog.at_level(
            _logging.DEBUG,
            logger="guardkit.orchestrator.quality_gates.task_work_interface",
        ):
            with patch(_SELECT_HARNESS, return_value=fake):
                await interface._execute_via_sdk("design prompt for TASK-001")

        assert any("Collected output length" in r.message for r in caplog.records)
        assert any("Full output" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_debug_logging_long_output(self, interface, caplog):
        """DEBUG output-length logging takes the preview branch for long output (>500)."""
        import logging as _logging

        long_text = "Complexity: 5/10\n" + ("x" * 600)
        fake = _FakeHarness(
            [
                AssistantMessageEvent(text=long_text),
                ResultMessageEvent(session_id=None),
            ]
        )
        with caplog.at_level(
            _logging.DEBUG,
            logger="guardkit.orchestrator.quality_gates.task_work_interface",
        ):
            with patch(_SELECT_HARNESS, return_value=fake):
                await interface._execute_via_sdk("design prompt for TASK-001")

        assert any("Output preview" in r.message for r in caplog.records)


class TestHarnessExceptionHandling:
    """TASK-HMIG-006.4 AC-003: harness failures map to the right exceptions."""

    @pytest.mark.asyncio
    async def test_sdk_import_failure_reraised_as_import_error(self, interface):
        """SDK-missing (AgentInvocationError caused by ImportError) → ImportError.

        Preserves execute_design_phase's subprocess fallback: the harness
        normalises a missing claude_agent_sdk to AgentInvocationError, and
        _execute_via_sdk re-raises ImportError when that is the root cause.
        """

        async def _import_failing_invoke(*args, **kwargs):
            err = AgentInvocationError("Claude Agent SDK import failed")
            err.__cause__ = ImportError("No module named 'claude_agent_sdk'")
            raise err
            yield  # pragma: no cover  (marks this an async-generator)

        fake = MagicMock()
        fake.invoke = _import_failing_invoke

        with patch(_SELECT_HARNESS, return_value=fake):
            with pytest.raises(ImportError):
                await interface._execute_via_sdk("design prompt for TASK-001")

    @pytest.mark.asyncio
    async def test_other_invocation_failure_raises_design_phase_error(self, interface):
        """A non-import AgentInvocationError surfaces as DesignPhaseError."""

        async def _failing_invoke(*args, **kwargs):
            raise AgentInvocationError("SDK process failed (exit 1)")
            yield  # pragma: no cover

        fake = MagicMock()
        fake.invoke = _failing_invoke

        with patch(_SELECT_HARNESS, return_value=fake):
            with pytest.raises(DesignPhaseError):
                await interface._execute_via_sdk("design prompt for TASK-001")

    @pytest.mark.asyncio
    async def test_harness_selection_failure_raises_design_phase_error(self, interface):
        """langgraph unavailable / unknown value at construction → DesignPhaseError.

        select_harness() raising AgentInvocationError must NOT fall back to
        the SDK subprocess path (that would defeat GUARDKIT_HARNESS=langgraph).
        """

        def _failing_select(*args, **kwargs):
            raise AgentInvocationError(
                "GUARDKIT_HARNESS=langgraph but guardkitfactory is not importable"
            )

        with patch(_SELECT_HARNESS, side_effect=_failing_select):
            with pytest.raises(DesignPhaseError):
                await interface._execute_via_sdk("design prompt for TASK-001")

    @pytest.mark.asyncio
    async def test_timeout_raises_design_phase_error(self, interface):
        """A harness timeout (orchestrator-side asyncio.timeout) → DesignPhaseError."""

        async def _timeout_invoke(*args, **kwargs):
            raise asyncio.TimeoutError()
            yield  # pragma: no cover

        fake = MagicMock()
        fake.invoke = _timeout_invoke

        with patch(_SELECT_HARNESS, return_value=fake):
            with pytest.raises(DesignPhaseError):
                await interface._execute_via_sdk("design prompt for TASK-001")

    @pytest.mark.asyncio
    async def test_unexpected_error_raises_design_phase_error(self, interface):
        """An unexpected exception leaking from the harness → DesignPhaseError."""

        async def _boom_invoke(*args, **kwargs):
            raise RuntimeError("unexpected harness explosion")
            yield  # pragma: no cover

        fake = MagicMock()
        fake.invoke = _boom_invoke

        with patch(_SELECT_HARNESS, return_value=fake):
            with pytest.raises(DesignPhaseError):
                await interface._execute_via_sdk("design prompt for TASK-001")


class TestSubstrateParity:
    """TASK-HMIG-006.4 AC-004: identical event streams → identical results.

    The design-phase glue (_execute_via_sdk + _parse_sdk_output) is
    substrate-agnostic: whether the HarnessEvents came from
    ClaudeSDKHarness (raw populated) or LangGraphHarness (raw is None),
    the same stream yields an identical raw DesignPhaseResult dict.
    """

    @pytest.mark.asyncio
    async def test_identical_events_yield_identical_result(self, interface):
        class _Raw:
            error = None
            content = []

        # SDK path: events carry a raw SDK-shape object per Design Decision D-1.
        sdk_events = [
            AssistantMessageEvent(text=e.text, raw=_Raw())
            for e in _design_phase_events()
            if isinstance(e, AssistantMessageEvent)
        ] + [ResultMessageEvent(session_id="sess-1", raw=_Raw())]

        # LangGraph path: raw is None (no SDK shape downstream).
        lg_events = [
            AssistantMessageEvent(text=e.text)
            for e in _design_phase_events()
            if isinstance(e, AssistantMessageEvent)
        ] + [ResultMessageEvent(session_id=None)]

        with patch(_SELECT_HARNESS, return_value=_FakeHarness(sdk_events)):
            sdk_result = await interface._execute_via_sdk("design prompt for TASK-001")

        with patch(_SELECT_HARNESS, return_value=_FakeHarness(lg_events)):
            lg_result = await interface._execute_via_sdk("design prompt for TASK-001")

        assert sdk_result == lg_result


class TestFalsifierNoSdkOnLangGraph:
    """TASK-HMIG-006.4 AC-005 falsifier (cheap, CI-able form).

    The frontmatter falsifier runs ``guardkit autobuild task TASK-X
    --pre-loop`` with ``GUARDKIT_HARNESS=langgraph`` and greps stderr for
    zero ``claude_agent_sdk.subprocess_cli`` lines. That full run needs a
    live LLM, so this test proves the same claim deterministically: with
    ``GUARDKIT_HARNESS=langgraph`` the design phase dispatches through the
    REAL LangGraphHarness (via the unpatched ``select_harness``) and NEVER
    calls ``claude_agent_sdk.query``. Only ``LangGraphHarness.invoke`` is
    stubbed so no real LLM call happens.
    """

    @pytest.mark.asyncio
    async def test_langgraph_design_phase_never_calls_sdk(self, interface, monkeypatch):
        import claude_agent_sdk
        from guardkitfactory.harness import LangGraphHarness

        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")

        async def _fake_lg_invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            yield AssistantMessageEvent(text="Complexity: 6/10")
            yield AssistantMessageEvent(text="Phase 2.8: checkpoint approved")
            yield ResultMessageEvent(session_id=None)

        sdk_query = MagicMock(name="claude_agent_sdk.query")

        # NOTE: select_harness is NOT patched here — the real langgraph
        # dispatch runs, exercising _translate_kwargs_for_langgraph against
        # the four pre-loop SDK kwargs (including setting_sources).
        with patch.object(LangGraphHarness, "invoke", _fake_lg_invoke), patch.object(
            claude_agent_sdk, "query", sdk_query
        ):
            result = await interface._execute_via_sdk("design prompt for TASK-001")

        # Falsifier assertion: zero SDK invocations on the langgraph design path.
        assert sdk_query.call_count == 0
        # The langgraph path still produces a valid design result.
        assert result["complexity"]["score"] == 6
        assert result["checkpoint_result"] == "approved"


class TestParseSDKOutputRobustness:
    """Regression coverage for _parse_sdk_output plan-path extraction.

    TASK-FB-FIX-005 origin: the old str(message.content) approach produced
    corrupted paths. The harness now hands clean joined text to
    _parse_sdk_output; this test pins the parser's clean-vs-corrupted
    behaviour independently of the harness seam.
    """

    def test_clean_text_yields_clean_path_corrupted_does_not(self, interface):
        import re

        plan_patterns = [
            r"Plan saved to[:\s]+([^\s\n]+)",
            r"(docs/state/[A-Z0-9-]+/implementation_plan\.(?:md|json))",
        ]

        # Stringified content list (the old bug) → corrupted path.
        corrupted_source = (
            "[TextBlock(text='Plan saved to: "
            "docs/state/TASK-001/implementation_plan.md'), ToolUseBlock(name='test')]"
        )
        found = None
        for pattern in plan_patterns:
            match = re.search(pattern, corrupted_source, re.IGNORECASE)
            if match:
                found = match.group(1) if match.lastindex else match.group(0)
                break
        assert found is not None
        assert found != "docs/state/TASK-001/implementation_plan.md"

        # Clean joined text (what the harness now provides) → clean path.
        clean_source = "Plan saved to: docs/state/TASK-001/implementation_plan.md"
        result = interface._parse_sdk_output(clean_source)
        assert result["plan_path"] == "docs/state/TASK-001/implementation_plan.md"


# ============================================================================
# Test Build Task Work Args (Legacy)
# ============================================================================


class TestBuildTaskWorkArgs:
    """Test _build_task_work_args() for subprocess fallback."""

    def test_basic_args_include_task_id_and_design_only(self, interface):
        """Test basic args include task_id and --design-only."""
        args = interface._build_task_work_args("TASK-001", {})

        assert "TASK-001" in args
        assert "--design-only" in args

    def test_args_include_no_questions(self, interface):
        """Test --no-questions is included."""
        args = interface._build_task_work_args("TASK-001", {"no_questions": True})

        assert "--no-questions" in args

    def test_args_include_with_questions(self, interface):
        """Test --with-questions is included."""
        args = interface._build_task_work_args("TASK-001", {"with_questions": True})

        assert "--with-questions" in args

    def test_args_include_answers(self, interface):
        """Test --answers is included with value."""
        args = interface._build_task_work_args("TASK-001", {"answers": "1:Y 2:N"})

        assert "--answers" in args
        assert "1:Y 2:N" in args

    def test_args_include_docs(self, interface):
        """Test --docs flag is included."""
        args = interface._build_task_work_args("TASK-001", {"docs": "minimal"})

        assert "--docs=minimal" in args

    def test_args_include_defaults(self, interface):
        """Test --defaults is included."""
        args = interface._build_task_work_args("TASK-001", {"defaults": True})

        assert "--defaults" in args


# ============================================================================
# Test Parse Design Result
# ============================================================================


class TestParseDesignResult:
    """Test _parse_design_result() method."""

    def test_extracts_all_fields(self, interface):
        """Test all fields are extracted correctly."""
        raw_result = {
            "implementation_plan": {"steps": ["Step 1"]},
            "plan_path": "/path/to/plan.md",
            "complexity": {"score": 6},
            "checkpoint_result": "approved",
            "architectural_review": {"score": 88},
            "clarifications": {"q1": "answer1"},
        }

        result = interface._parse_design_result(raw_result)

        assert result.implementation_plan == {"steps": ["Step 1"]}
        assert result.plan_path == "/path/to/plan.md"
        assert result.complexity == {"score": 6}
        assert result.checkpoint_result == "approved"
        assert result.architectural_review == {"score": 88}
        assert result.clarifications == {"q1": "answer1"}

    def test_provides_defaults_for_missing_fields(self, interface):
        """Test defaults are provided for missing fields."""
        result = interface._parse_design_result({})

        assert result.implementation_plan == {}
        assert result.complexity == {"score": 5}
        assert result.checkpoint_result == "approved"

    def test_raises_quality_gate_blocked_for_low_score(self, interface):
        """Test QualityGateBlocked raised for score < 60."""
        raw_result = {"architectural_review": {"score": 55}}

        with pytest.raises(QualityGateBlocked) as exc_info:
            interface._parse_design_result(raw_result)

        assert exc_info.value.gate_name == "architectural_review"
        assert exc_info.value.details["score"] == 55

    @pytest.mark.parametrize("score", [60, 70, 80, 90, 100])
    def test_accepts_scores_at_or_above_threshold(self, interface, score):
        """Test scores >= 60 pass validation."""
        raw_result = {"architectural_review": {"score": score}}

        result = interface._parse_design_result(raw_result)

        assert result.architectural_review["score"] == score


# ============================================================================
# Test Plan Path Helpers
# ============================================================================


class TestPlanPathHelpers:
    """Test plan path helper methods."""

    def test_get_plan_path_prefers_claude_directory(self, interface, tmp_worktree):
        """Test .claude/task-plans/ is checked first (priority 1)."""
        # Create plan in .claude/task-plans/ (highest priority)
        claude_dir = tmp_worktree / ".claude" / "task-plans"
        claude_dir.mkdir(parents=True)
        claude_plan = claude_dir / "TASK-001-implementation-plan.md"
        claude_plan.write_text("# Implementation Plan\n\nThis is a detailed plan with sufficient content to pass validation.")

        # Also create plan in docs/state/ (lower priority)
        docs_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        docs_dir.mkdir(parents=True)
        docs_plan = docs_dir / "implementation_plan.json"
        docs_plan.write_text('{"files": ["src/main.py"], "phases": ["planning", "implementation"]}')

        result = interface._get_plan_path("TASK-001")

        # Should return .claude path (higher priority)
        assert result == claude_plan

    def test_get_plan_path_falls_back_to_docs_state(self, interface, tmp_worktree):
        """Test falls back to docs/state/ if .claude/ doesn't have valid plan."""
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)

        md_plan = plan_dir / "implementation_plan.md"
        md_plan.write_text("# Implementation Plan\n\nThis is a detailed plan with sufficient content to pass validation.")

        result = interface._get_plan_path("TASK-001")

        assert result == md_plan

    def test_get_plan_path_returns_preferred_when_none_exist(self, interface, tmp_worktree):
        """Test returns preferred path when no valid plan exists."""
        result = interface._get_plan_path("TASK-001")

        # When no plan exists, should return preferred path (for writing)
        expected = tmp_worktree / ".claude" / "task-plans" / "TASK-001-implementation-plan.md"
        assert result == expected

    def test_get_complexity_path(self, interface, tmp_worktree):
        """Test complexity path is correct."""
        result = interface._get_complexity_path("TASK-001")

        expected = tmp_worktree / "docs" / "state" / "TASK-001" / "complexity_score.json"
        assert result == expected


# ============================================================================
# Test TASK-FB-FIX-019: Plan Path Regex and Auto-Approve Flag
# ============================================================================


class TestCreatedImplementationPlanPattern:
    """Test parsing of 'Created implementation plan:' output format.

    TASK-FB-FIX-019: These tests verify the new regex pattern that matches
    task-work's actual output format for plan path extraction.
    """

    def test_parses_created_implementation_plan_format(self, interface):
        """Test 'Created implementation plan:' pattern is recognized."""
        output = """
        Phase 2: Implementation Planning
        Created implementation plan: .claude/task-plans/TASK-WKT-b2c4-implementation-plan.md
        Phase 2.5A: Pattern Suggestions
        """

        result = interface._parse_sdk_output(output)

        assert result["plan_path"] == ".claude/task-plans/TASK-WKT-b2c4-implementation-plan.md"

    def test_parses_created_implementation_plan_with_docs_state_path(self, interface):
        """Test 'Created implementation plan:' with docs/state path."""
        output = "Created implementation plan: docs/state/TASK-001/implementation_plan.md"

        result = interface._parse_sdk_output(output)

        assert result["plan_path"] == "docs/state/TASK-001/implementation_plan.md"

    def test_parses_created_implementation_plan_colon_no_space(self, interface):
        """Test 'Created implementation plan:path' without space after colon."""
        output = "Created implementation plan:.claude/task-plans/TASK-001-implementation-plan.md"

        result = interface._parse_sdk_output(output)

        assert result["plan_path"] == ".claude/task-plans/TASK-001-implementation-plan.md"


class TestAutoApproveInInlineProtocol:
    """Test that inline protocol includes auto-approve checkpoint behavior.

    TASK-POF-003: The inline protocol always auto-approves the checkpoint
    (no human present in autobuild context). These tests verify this behavior
    replaces the previous --auto-approve-checkpoint flag.
    """

    def test_checkpoint_auto_approved_in_protocol(self, interface):
        """Test that the inline protocol includes auto-approve checkpoint."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "checkpoint approved" in prompt.lower() or "auto-approved" in prompt.lower()

    def test_design_approved_state_in_protocol(self, interface):
        """Test that protocol includes DESIGN_APPROVED state output."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "DESIGN_APPROVED" in prompt

    def test_auto_approve_with_all_option_combinations(self, interface):
        """Test auto-approve is present regardless of other options."""
        for opts in [{}, {"docs": "minimal"}, {"skip_arch_review": True}]:
            prompt = interface._build_design_prompt("TASK-001", opts)
            assert "checkpoint approved" in prompt.lower()

    def test_no_skill_flags_in_inline_protocol(self, interface):
        """Test inline protocol does not contain /task-work flags."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "--auto-approve-checkpoint" not in prompt
        assert "--design-only" not in prompt
        assert "/task-work" not in prompt


# ============================================================================
# Test TASK-POF-001: --autobuild-mode Composite Flag
# ============================================================================


class TestAutobuildModeInlineProtocol:
    """Test autobuild_mode option in inline protocol and subprocess args.

    TASK-POF-001: autobuild_mode bundles autonomous execution optimizations.
    TASK-POF-003: Design prompt is now inline protocol, not /task-work skill invocation.
    Subprocess args (_build_task_work_args) still use the flag-based approach.
    """

    def test_autobuild_mode_produces_inline_protocol(self, interface):
        """Test autobuild_mode produces inline protocol, not skill invocation."""
        prompt = interface._build_design_prompt("TASK-001", {"autobuild_mode": True})

        assert "TASK-001" in prompt
        assert not prompt.startswith("/task-work")

    def test_autobuild_mode_protocol_includes_all_phases(self, interface):
        """Test autobuild protocol includes required design phases."""
        prompt = interface._build_design_prompt("TASK-001", {"autobuild_mode": True})

        assert "Phase 1.5" in prompt
        assert "Implementation Planning" in prompt
        assert "Complexity" in prompt
        assert "checkpoint approved" in prompt.lower()

    def test_autobuild_mode_skip_arch_review_omits_phase(self, interface):
        """Test skip_arch_review omits Phase 2.5B from protocol."""
        prompt = interface._build_design_prompt(
            "TASK-001",
            {"autobuild_mode": True, "skip_arch_review": True},
        )

        assert "Phase 2.5B" not in prompt
        assert "SOLID" not in prompt

    def test_non_autobuild_protocol_includes_arch_review(self, interface):
        """Test non-autobuild protocol includes Phase 2.5B by default."""
        prompt = interface._build_design_prompt("TASK-001", {})

        assert "SOLID" in prompt
        assert "DRY" in prompt
        assert "YAGNI" in prompt

    def test_autobuild_mode_in_task_work_args(self, interface):
        """Test --autobuild-mode is added to subprocess args (unchanged)."""
        args = interface._build_task_work_args("TASK-001", {"autobuild_mode": True})

        assert "--autobuild-mode" in args
        assert "TASK-001" in args
        assert "--design-only" in args

    def test_autobuild_mode_replaces_individual_flags_in_args(self, interface):
        """Test --autobuild-mode replaces individual sub-flags in args."""
        args = interface._build_task_work_args("TASK-001", {"autobuild_mode": True})

        assert "--no-questions" not in args
        assert "--skip-arch-review" not in args
        assert "--defaults" not in args

    def test_without_autobuild_mode_uses_individual_flags_in_args(self, interface):
        """Test individual flags still work in args when autobuild_mode is not set."""
        args = interface._build_task_work_args(
            "TASK-001",
            {"no_questions": True, "docs": "minimal", "skip_arch_review": True},
        )

        assert "--autobuild-mode" not in args
        assert "--no-questions" in args
        assert "--docs=minimal" in args
        assert "--skip-arch-review" in args


# ============================================================================
# Test TASK-POF-003: SDK Options for Inline Protocol
# ============================================================================


class TestSDKOptionsForInlineProtocol:
    """Test that SDK options are configured for inline protocol execution.

    TASK-POF-003: The SDK options should use setting_sources=["project"]
    (not ["user", "project"]) and exclude Skill/Task tools since the
    inline protocol does not invoke skills or subagents.
    """

    @pytest.mark.asyncio
    async def test_sdk_uses_project_only_setting_sources(self, interface, tmp_worktree):
        """Test setting_sources is ["project"], not ["user", "project"]."""
        captured_options = {}

        mock_module = MagicMock()
        mock_module.CLINotFoundError = Exception
        mock_module.ProcessError = Exception
        mock_module.CLIJSONDecodeError = Exception
        mock_module.AssistantMessage = MockAssistantMessage
        mock_module.TextBlock = MockTextBlock
        mock_module.ToolUseBlock = MockToolUseBlock
        mock_module.ToolResultBlock = MockToolResultBlock
        mock_module.ResultMessage = MockResultMessage

        def capture_options(**kwargs):
            captured_options.update(kwargs)
            return MagicMock()

        mock_module.ClaudeAgentOptions = capture_options

        async def mock_query(*args, **kwargs):
            yield MockAssistantMessage(content=[MockTextBlock("Complexity: 5/10")])
            yield MockAssistantMessage(content=[MockTextBlock("Phase 2.8: checkpoint approved")])
            yield MockResultMessage(num_turns=2)

        mock_module.query = mock_query

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_module}):
            await interface._execute_via_sdk("test prompt")

        assert captured_options.get("setting_sources") == ["project"]

    @pytest.mark.asyncio
    async def test_sdk_excludes_skill_tool(self, interface, tmp_worktree):
        """Test Skill tool is not in allowed_tools."""
        captured_options = {}

        mock_module = MagicMock()
        mock_module.CLINotFoundError = Exception
        mock_module.ProcessError = Exception
        mock_module.CLIJSONDecodeError = Exception
        mock_module.AssistantMessage = MockAssistantMessage
        mock_module.TextBlock = MockTextBlock
        mock_module.ToolUseBlock = MockToolUseBlock
        mock_module.ToolResultBlock = MockToolResultBlock
        mock_module.ResultMessage = MockResultMessage

        def capture_options(**kwargs):
            captured_options.update(kwargs)
            return MagicMock()

        mock_module.ClaudeAgentOptions = capture_options

        async def mock_query(*args, **kwargs):
            yield MockAssistantMessage(content=[MockTextBlock("Done")])
            yield MockResultMessage(num_turns=1)

        mock_module.query = mock_query

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_module}):
            await interface._execute_via_sdk("test prompt")

        allowed_tools = captured_options.get("allowed_tools", [])
        assert "Skill" not in allowed_tools
        assert "Task" not in allowed_tools
        # Core tools should still be present
        assert "Read" in allowed_tools
        assert "Write" in allowed_tools
        assert "Glob" in allowed_tools

    @pytest.mark.asyncio
    async def test_sdk_max_turns_reduced(self, interface, tmp_worktree):
        """Test max_turns is reduced for simpler inline protocol."""
        captured_options = {}

        mock_module = MagicMock()
        mock_module.CLINotFoundError = Exception
        mock_module.ProcessError = Exception
        mock_module.CLIJSONDecodeError = Exception
        mock_module.AssistantMessage = MockAssistantMessage
        mock_module.TextBlock = MockTextBlock
        mock_module.ToolUseBlock = MockToolUseBlock
        mock_module.ToolResultBlock = MockToolResultBlock
        mock_module.ResultMessage = MockResultMessage

        def capture_options(**kwargs):
            captured_options.update(kwargs)
            return MagicMock()

        mock_module.ClaudeAgentOptions = capture_options

        async def mock_query(*args, **kwargs):
            yield MockAssistantMessage(content=[MockTextBlock("Done")])
            yield MockResultMessage(num_turns=1)

        mock_module.query = mock_query

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_module}):
            await interface._execute_via_sdk("test prompt")

        assert captured_options.get("max_turns") == 25


# ============================================================================
# Test TASK-ACO-003: AutoBuild Design Prompt Builder
# ============================================================================


class TestBuildAutobuildDesignPrompt:
    """Test _build_autobuild_design_prompt() method.

    TASK-ACO-003: Tests the protocol-based prompt builder that loads
    autobuild_design_protocol.md via load_protocol() and injects
    task-specific context.
    """

    def test_loads_protocol_from_md_file(self, interface):
        """Test prompt loads content from autobuild_design_protocol.md."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        # Protocol content should include Phase 1.5 and Phase 2 from .md file
        assert "Phase 1.5" in prompt
        assert "Phase 2:" in prompt or "Implementation Planning" in prompt
        assert "Phase 2.7" in prompt or "Complexity Evaluation" in prompt

    def test_substitutes_task_id_in_protocol(self, interface):
        """Test {task_id} placeholders are replaced with actual task ID."""
        prompt = interface._build_autobuild_design_prompt("TASK-ABC-999", {})

        assert "TASK-ABC-999" in prompt
        # Should NOT contain unresolved {task_id} placeholders
        assert "{task_id}" not in prompt

    def test_includes_phase_skipping_instructions(self, interface):
        """Test AutoBuild phase skipping is encoded in the prompt."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert "Phase 1.6" in prompt
        assert "SKIP" in prompt
        assert "Phase 2.1" in prompt
        assert "Phase 2.5A" in prompt

    def test_includes_docs_level(self, interface):
        """Test documentation level is included in prompt."""
        prompt = interface._build_autobuild_design_prompt(
            "TASK-001", {"docs": "comprehensive"}
        )

        assert "comprehensive" in prompt

    def test_default_docs_level_is_minimal(self, interface):
        """Test default documentation level is minimal."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert "minimal" in prompt

    def test_includes_arch_review_by_default(self, interface):
        """Test Phase 2.5B is included by default (lightweight mode)."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert "LIGHTWEIGHT" in prompt
        assert "SOLID" in prompt
        assert "DRY" in prompt
        assert "YAGNI" in prompt

    def test_skips_arch_review_with_flag(self, interface):
        """Test Phase 2.5B is removed when skip_arch_review is set."""
        prompt = interface._build_autobuild_design_prompt(
            "TASK-001", {"skip_arch_review": True}
        )

        # Phase 2.5B section should be stripped from protocol
        assert "## Phase 2.5B" not in prompt

    def test_checkpoint_auto_approved(self, interface):
        """Test Phase 2.8 auto-approve is in the prompt."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert "AUTO-APPROVE" in prompt or "auto-approve" in prompt.lower()

    def test_output_markers_preserved(self, interface):
        """Test output markers from protocol are preserved for parsing."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert "Plan saved to:" in prompt
        assert "Complexity:" in prompt
        assert "DESIGN_APPROVED" in prompt

    def test_plan_path_uses_correct_convention(self, interface):
        """Test plan save path uses .claude/task-plans/ convention."""
        prompt = interface._build_autobuild_design_prompt("TASK-XYZ-001", {})

        assert ".claude/task-plans/TASK-XYZ-001-implementation-plan.md" in prompt

    def test_not_a_skill_invocation(self, interface):
        """Test prompt is NOT a /task-work skill invocation."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert not prompt.strip().startswith("/task-work")
        assert "--design-only" not in prompt

    def test_includes_working_directory(self, interface):
        """Test working directory is included in prompt context."""
        prompt = interface._build_autobuild_design_prompt("TASK-001", {})

        assert str(interface.worktree_path) in prompt

    def test_parseable_by_parse_sdk_output(self, interface):
        """Test prompt output markers can be parsed by _parse_sdk_output().

        Simulates the expected output from an SDK agent that followed the
        protocol, verifying it is parseable by the existing parser.
        """
        # This is the format the protocol instructs the agent to output
        simulated_output = (
            "Plan saved to: .claude/task-plans/TASK-001-implementation-plan.md\n"
            "Architectural Score: 85/100\n"
            "SOLID: 88, DRY: 82, YAGNI: 85\n"
            "Complexity: 6/10\n"
            "Phase 2.8: checkpoint approved\n"
            "State: DESIGN_APPROVED\n"
        )

        result = interface._parse_sdk_output(simulated_output)

        assert result["plan_path"] == ".claude/task-plans/TASK-001-implementation-plan.md"
        assert result["complexity"]["score"] == 6
        assert result["architectural_review"]["score"] == 85
        assert result["checkpoint_result"] == "approved"


class TestStripArchReviewSection:
    """Test _strip_arch_review_section() static method."""

    def test_removes_phase_25b_section(self):
        """Test Phase 2.5B section is removed from protocol."""
        protocol = (
            "## Phase 2: Planning\n"
            "Some planning content.\n"
            "\n"
            "## Phase 2.5B: Architectural Review\n"
            "SOLID content here.\n"
            "DRY content here.\n"
            "\n"
            "## Phase 2.7: Complexity\n"
            "Complexity content.\n"
        )

        result = TaskWorkInterface._strip_arch_review_section(protocol)

        assert "## Phase 2: Planning" in result
        assert "## Phase 2.5B" not in result
        assert "SOLID content" not in result
        assert "## Phase 2.7: Complexity" in result

    def test_preserves_content_before_and_after(self):
        """Test content before and after 2.5B is preserved."""
        protocol = (
            "Header content\n"
            "## Phase 2.5B: Architectural Review\n"
            "Review content\n"
            "## Phase 2.7: Complexity\n"
            "Footer content\n"
        )

        result = TaskWorkInterface._strip_arch_review_section(protocol)

        assert "Header content" in result
        assert "Footer content" in result

    def test_noop_when_no_phase_25b(self):
        """Test no change when Phase 2.5B is not in protocol."""
        protocol = "## Phase 2: Planning\nContent\n## Phase 2.7: Complexity\n"

        result = TaskWorkInterface._strip_arch_review_section(protocol)

        assert result == protocol


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
