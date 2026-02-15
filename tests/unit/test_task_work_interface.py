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
# Test SDK ContentBlock Message Parsing (TASK-FB-FIX-005)
# ============================================================================


class TestSDKContentBlockParsing:
    """Test proper parsing of SDK messages with ContentBlock structure.

    TASK-FB-FIX-005: These tests verify that the fixed _execute_via_sdk()
    properly iterates over ContentBlock objects instead of calling str()
    on the content list, which was causing plan paths to not be extracted.

    Root cause of bug:
        OLD: str(message.content)  # Produces "[TextBlock(text='...'), ...]"
        NEW: Iterate content and extract block.text from TextBlock instances

    These tests use mock ContentBlock classes to simulate real SDK behavior.
    """

    @pytest.mark.asyncio
    async def test_extracts_text_from_textblocks(
        self, interface, mock_contentblock_sdk_module, tmp_worktree
    ):
        """Test that text is properly extracted from TextBlock instances.

        TASK-FB-FIX-005: Verifies block.text is extracted, not str(content).
        """
        # Create plan file so parsing can find it
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-001"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.md"
        plan_file.write_text("# Plan\n\nImplementation plan content")

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_contentblock_sdk_module}):
            result = await interface._execute_via_sdk("/task-work TASK-001 --design-only")

            # Plan path should be found because text content is properly extracted
            assert result["plan_path"] == "docs/state/TASK-001/implementation_plan.md"

    @pytest.mark.asyncio
    async def test_extracts_complexity_score_from_textblocks(
        self, interface, mock_contentblock_sdk_module, tmp_worktree
    ):
        """Test complexity score is extracted from TextBlock text content."""
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_contentblock_sdk_module}):
            result = await interface._execute_via_sdk("/task-work TASK-001 --design-only")

            assert result["complexity"]["score"] == 6

    @pytest.mark.asyncio
    async def test_extracts_architectural_score_from_textblocks(
        self, interface, mock_contentblock_sdk_module, tmp_worktree
    ):
        """Test architectural review score is extracted from TextBlock text content."""
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_contentblock_sdk_module}):
            result = await interface._execute_via_sdk("/task-work TASK-001 --design-only")

            assert result["architectural_review"]["score"] == 85

    @pytest.mark.asyncio
    async def test_checkpoint_approved_detected_from_textblocks(
        self, interface, mock_contentblock_sdk_module, tmp_worktree
    ):
        """Test checkpoint approved status is detected from TextBlock text."""
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_contentblock_sdk_module}):
            result = await interface._execute_via_sdk("/task-work TASK-001 --design-only")

            assert result["checkpoint_result"] == "approved"

    @pytest.mark.asyncio
    async def test_handles_mixed_contentblock_types(
        self, interface, mock_contentblock_sdk_module, tmp_worktree
    ):
        """Test handling of messages with mixed TextBlock and ToolUseBlock content.

        TASK-FB-FIX-005: Verifies ToolUseBlock is logged but not added to output,
        and TextBlock text is still properly collected.
        """
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_contentblock_sdk_module}):
            result = await interface._execute_via_sdk("/task-work TASK-001 --design-only")

            # Should still extract data from TextBlocks despite ToolUseBlocks present
            assert result["architectural_review"]["score"] == 85

    @pytest.mark.asyncio
    async def test_handles_tool_result_block_content(
        self, interface, tmp_worktree
    ):
        """Test that ToolResultBlock content is extracted when present."""
        async def mock_query_with_tool_result(*args, **kwargs):
            messages = [
                MockAssistantMessage(content=[
                    MockTextBlock("Processing..."),
                    MockToolResultBlock(content="Tool result: Plan saved to: docs/state/TASK-002/implementation_plan.md"),
                ]),
                MockResultMessage(num_turns=1),
            ]
            for msg in messages:
                yield msg

        mock_module = MagicMock()
        mock_module.query = mock_query_with_tool_result
        mock_module.ClaudeAgentOptions = MagicMock()
        mock_module.CLINotFoundError = Exception
        mock_module.ProcessError = Exception
        mock_module.CLIJSONDecodeError = Exception
        mock_module.AssistantMessage = MockAssistantMessage
        mock_module.TextBlock = MockTextBlock
        mock_module.ToolUseBlock = MockToolUseBlock
        mock_module.ToolResultBlock = MockToolResultBlock
        mock_module.ResultMessage = MockResultMessage

        # Create plan file
        plan_dir = tmp_worktree / "docs" / "state" / "TASK-002"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "implementation_plan.md"
        plan_file.write_text("# Plan content")

        with patch.dict("sys.modules", {"claude_agent_sdk": mock_module}):
            result = await interface._execute_via_sdk("/task-work TASK-002 --design-only")

            # Plan path should be found from tool result content
            assert result["plan_path"] == "docs/state/TASK-002/implementation_plan.md"

    @pytest.mark.asyncio
    async def test_handles_result_message_gracefully(
        self, interface, mock_contentblock_sdk_module, tmp_worktree
    ):
        """Test that ResultMessage (final message) is handled without errors."""
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_contentblock_sdk_module}):
            # Should not raise any exception
            result = await interface._execute_via_sdk("/task-work TASK-001 --design-only")

            # Result should be valid despite ResultMessage at end
            assert "complexity" in result
            assert "checkpoint_result" in result

    @pytest.mark.asyncio
    async def test_old_str_conversion_bug_produces_invalid_path(self, interface, tmp_worktree):
        """Verify that the old str(message.content) approach produces invalid paths.

        TASK-FB-FIX-005: This test demonstrates why the fix was needed.
        If we stringify the content list, the extracted path includes garbage
        characters like '),' from the string representation.
        """
        # Simulate what str(message.content) would produce
        simulated_old_output = "[TextBlock(text='Plan saved to: docs/state/TASK-001/implementation_plan.md'), ToolUseBlock(name='test')]"

        # This regex matches but extracts an INVALID path with trailing garbage
        import re
        plan_patterns = [
            r"Plan saved to[:\s]+([^\s\n]+)",
            r"(docs/state/[A-Z0-9-]+/implementation_plan\.(?:md|json))",
        ]

        found_path = None
        for pattern in plan_patterns:
            match = re.search(pattern, simulated_old_output, re.IGNORECASE)
            if match:
                found_path = match.group(1) if match.lastindex else match.group(0)
                break

        # The old approach extracts a CORRUPTED path with trailing characters
        # from the TextBlock string representation
        assert found_path is not None, "Pattern should match (but with garbage)"
        assert "')" in found_path or ")," in found_path or found_path.endswith("'"), \
            f"Old approach should produce corrupted path, got: {found_path}"

        # The path is NOT valid - it has extra characters
        assert found_path != "docs/state/TASK-001/implementation_plan.md", \
            "Old approach should NOT produce clean path"

        # Now test with properly extracted text (the fix)
        proper_text_content = "Plan saved to: docs/state/TASK-001/implementation_plan.md"

        found_path = None
        for pattern in plan_patterns:
            match = re.search(pattern, proper_text_content, re.IGNORECASE)
            if match:
                found_path = match.group(1) if match.lastindex else match.group(0)
                break

        # The fixed approach DOES find the CORRECT path
        assert found_path == "docs/state/TASK-001/implementation_plan.md"


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
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
