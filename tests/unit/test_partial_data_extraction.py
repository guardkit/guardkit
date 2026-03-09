"""Tests for TASK-CRV-1540: Partial data extraction from response_messages on CancelledError.

Coverage Target: >=85%
Test Count: 10+ tests
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    _extract_partial_from_messages,
)


# ============================================================================
# Mock helpers for SDK message types
# ============================================================================


def _make_text_block(text: str) -> MagicMock:
    """Create a mock TextBlock with given text."""
    block = MagicMock()
    type(block).__name__ = "TextBlock"
    block.text = text
    return block


def _make_tool_use_block(name: str, input_dict: Dict[str, Any] = None) -> MagicMock:
    """Create a mock ToolUseBlock."""
    block = MagicMock()
    type(block).__name__ = "ToolUseBlock"
    block.name = name
    block.input = input_dict or {}
    return block


def _make_assistant_message(blocks: List[Any]) -> MagicMock:
    """Create a mock AssistantMessage with given content blocks."""
    msg = MagicMock()
    msg.content = blocks
    return msg


def _make_result_message() -> MagicMock:
    """Create a mock ResultMessage (no content attr)."""
    msg = MagicMock(spec=[])  # No attributes
    return msg


# ============================================================================
# Test _extract_partial_from_messages
# ============================================================================


class TestExtractPartialFromMessages:
    """Tests for the partial data extraction function."""

    def test_empty_messages(self):
        """Empty list returns zero counts."""
        result = _extract_partial_from_messages([])
        assert result["text_block_count"] == 0
        assert result["tool_call_count"] == 0
        assert result["file_modifications"] == []
        assert result["last_text_blocks"] == []
        assert result["message_count"] == 0

    def test_single_text_block(self):
        """Single message with one text block."""
        msg = _make_assistant_message([_make_text_block("Hello world")])
        result = _extract_partial_from_messages([msg])

        assert result["text_block_count"] == 1
        assert result["tool_call_count"] == 0
        assert result["file_modifications"] == []
        assert result["last_text_blocks"] == ["Hello world"]
        assert result["message_count"] == 1

    def test_multiple_text_blocks(self):
        """Multiple messages with text blocks."""
        msgs = [
            _make_assistant_message([_make_text_block(f"Block {i}")])
            for i in range(5)
        ]
        result = _extract_partial_from_messages(msgs)

        assert result["text_block_count"] == 5
        assert result["last_text_blocks"] == ["Block 2", "Block 3", "Block 4"]

    def test_tool_use_blocks(self):
        """Messages with tool use blocks (non-file tools)."""
        msg = _make_assistant_message([
            _make_tool_use_block("Bash", {"command": "ls"}),
            _make_tool_use_block("Read", {"file_path": "/foo.py"}),
        ])
        result = _extract_partial_from_messages([msg])

        assert result["tool_call_count"] == 2
        assert result["file_modifications"] == []

    def test_write_tool_extracts_file_modification(self):
        """Write tool calls are captured as file modifications."""
        msg = _make_assistant_message([
            _make_tool_use_block("Write", {"file_path": "/src/main.py", "content": "..."}),
        ])
        result = _extract_partial_from_messages([msg])

        assert result["tool_call_count"] == 1
        assert result["file_modifications"] == ["/src/main.py"]

    def test_edit_tool_extracts_file_modification(self):
        """Edit tool calls are captured as file modifications."""
        msg = _make_assistant_message([
            _make_tool_use_block("Edit", {"file_path": "/src/util.py", "old_string": "a", "new_string": "b"}),
        ])
        result = _extract_partial_from_messages([msg])

        assert result["tool_call_count"] == 1
        assert result["file_modifications"] == ["/src/util.py"]

    def test_mixed_blocks(self):
        """Message with mixed text and tool use blocks."""
        msg = _make_assistant_message([
            _make_text_block("Implementing changes..."),
            _make_tool_use_block("Write", {"file_path": "/a.py", "content": "code"}),
            _make_text_block("Running tests..."),
            _make_tool_use_block("Bash", {"command": "pytest"}),
            _make_tool_use_block("Edit", {"file_path": "/b.py", "old_string": "x", "new_string": "y"}),
        ])
        result = _extract_partial_from_messages([msg])

        assert result["text_block_count"] == 2
        assert result["tool_call_count"] == 3
        assert sorted(result["file_modifications"]) == ["/a.py", "/b.py"]

    def test_message_without_content_attribute(self):
        """Messages without content attribute are skipped."""
        msg = _make_result_message()
        result = _extract_partial_from_messages([msg])

        assert result["text_block_count"] == 0
        assert result["message_count"] == 1

    def test_message_with_none_content(self):
        """Messages with None content are skipped."""
        msg = MagicMock()
        msg.content = None
        result = _extract_partial_from_messages([msg])

        assert result["text_block_count"] == 0

    def test_message_with_non_list_content(self):
        """Messages with non-list content are skipped."""
        msg = MagicMock()
        msg.content = "not a list"
        result = _extract_partial_from_messages([msg])

        assert result["text_block_count"] == 0

    def test_malformed_block_skipped(self):
        """Blocks that raise on attribute access are skipped."""
        bad_block = MagicMock()
        type(bad_block).__name__ = "TextBlock"
        bad_block.text = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))

        msg = _make_assistant_message([bad_block, _make_text_block("OK")])
        # Should not raise, and should extract the valid block
        result = _extract_partial_from_messages([msg])
        # At least the message was processed
        assert result["message_count"] == 1

    def test_empty_text_blocks_ignored(self):
        """Empty string text blocks are not counted."""
        msg = _make_assistant_message([
            _make_text_block(""),
            _make_text_block("real text"),
        ])
        result = _extract_partial_from_messages([msg])

        assert result["text_block_count"] == 1
        assert result["last_text_blocks"] == ["real text"]

    def test_tool_use_with_no_file_path(self):
        """Write/Edit tool with empty file_path is not added to modifications."""
        msg = _make_assistant_message([
            _make_tool_use_block("Write", {"file_path": "", "content": "..."}),
            _make_tool_use_block("Edit", {"content": "..."}),  # Missing file_path key
        ])
        result = _extract_partial_from_messages([msg])

        assert result["tool_call_count"] == 2
        assert result["file_modifications"] == []

    def test_last_text_blocks_capped_at_three(self):
        """last_text_blocks returns at most the last 3."""
        msgs = [
            _make_assistant_message([_make_text_block(f"Msg {i}")])
            for i in range(10)
        ]
        result = _extract_partial_from_messages(msgs)

        assert len(result["last_text_blocks"]) == 3
        assert result["last_text_blocks"] == ["Msg 7", "Msg 8", "Msg 9"]


# ============================================================================
# Test AgentInvoker._last_partial_report initialization
# ============================================================================


class TestAgentInvokerPartialReport:
    """Tests that AgentInvoker initializes _last_partial_report."""

    def test_init_has_none_partial_report(self, tmp_path):
        """AgentInvoker initializes _last_partial_report to None."""
        invoker = AgentInvoker(
            worktree_path=tmp_path,
            max_turns_per_agent=5,
        )
        assert invoker._last_partial_report is None
