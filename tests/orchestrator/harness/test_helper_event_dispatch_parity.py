"""Helper-function parity tests for TASK-HMIG-006.2 (AC-006).

The byte-compat-parity suite (``test_byte_compat_parity.py``) proves the
inverted divergence assertion (AC-003) — the verifiable signal that the
helper-migration landed. These tests are the AC-006 surface: they prove
``_track_tool_use`` and ``_extract_partial_from_messages`` work
end-to-end on the LangGraph path by exercising them against synthetic
``ToolUseEvent`` streams (no SDK message required).

The pre-migration LangGraph path returned zero counts because the
helpers walked ``event.raw.content`` (an attribute that exists on SDK
AssistantMessage objects, not on LangChain result dicts). Post-migration
the helpers dispatch on typed ``HarnessEvent`` variants, so the same
LangGraph stream that previously yielded zeros now yields meaningful
counts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    _extract_partial_from_messages,
)
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    HarnessAdapter,
    HarnessEvent,
    ResultMessageEvent,
    ToolUseEvent,
)


# ============================================================================
# Helper-only LangGraph stub (no DeepAgents dependency)
# ============================================================================


class _LangGraphLikeHarness(HarnessAdapter):
    """Yields a LangGraph-shaped event stream without importing DeepAgents.

    Production ``LangGraphHarness`` extracts ``ToolUseEvent`` from
    ``AIMessage.tool_calls`` in ``result["messages"]``. This stub yields
    the same event sequence directly so the helper-parity tests stay
    independent of langchain / langgraph / deepagents installation
    state.
    """

    def __init__(
        self,
        *,
        text: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        self._text = text
        self._tool_calls = tool_calls or []

    async def invoke(  # type: ignore[override]
        self, prompt, role, tools, cwd, *, timeout_seconds
    ):
        # raw=langchain_dict mirrors what production LangGraphHarness
        # populates on AssistantMessageEvent — a dict with no .content
        # attribute, the shape that defeated the old duck-typed walk.
        langchain_dict = {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": self._text},
            ],
        }
        for tc in self._tool_calls:
            yield ToolUseEvent(
                tool_use_id=tc.get("id", ""),
                name=tc["name"],
                input=tc.get("input", tc.get("args", {})),
            )
        yield AssistantMessageEvent(text=self._text, raw=langchain_dict)
        yield ResultMessageEvent(
            session_id=None, stop_reason="end_turn", usage=None
        )

    @property
    def supports_resume(self) -> bool:
        return False


async def _collect_events(harness: HarnessAdapter) -> List[HarnessEvent]:
    """Drive a harness for one turn and collect the typed-event list."""
    from pathlib import Path

    events: List[HarnessEvent] = []
    async for ev in harness.invoke(
        prompt="parity-test",
        role="player",
        tools=[],
        cwd=Path("."),
        timeout_seconds=30,
    ):
        events.append(ev)
        if isinstance(ev, ResultMessageEvent):
            break
    return events


# ============================================================================
# AC-006: _extract_partial_from_messages parity on LangGraph
# ============================================================================


class TestExtractPartialLangGraphParity:
    """Migrated helper produces non-zero counts on the LangGraph path
    for turns that previously returned zeros.
    """

    @pytest.mark.asyncio
    async def test_langgraph_text_only_extracts_one_text_block(self):
        """A text-only LangGraph turn now yields text_block_count=1
        (pre-migration: 0 because raw=langchain_dict has no .content)."""
        harness = _LangGraphLikeHarness(text="some answer text")
        events = await _collect_events(harness)

        partial = _extract_partial_from_messages(events)

        assert partial["text_block_count"] == 1, (
            "AC-006 regression: LangGraph text extraction returned 0 "
            "(pre-migration behaviour). The migrated helper should read "
            "AssistantMessageEvent.text directly."
        )
        assert partial["last_text_blocks"] == ["some answer text"]

    @pytest.mark.asyncio
    async def test_langgraph_single_tool_call_extracts_one(self):
        """A LangGraph turn with one tool call now yields
        tool_call_count=1 (pre-migration: 0 because the LangChain
        result dict has no .content list of ToolUseBlocks)."""
        harness = _LangGraphLikeHarness(
            text="calling Edit",
            tool_calls=[
                {
                    "id": "call-1",
                    "name": "Edit",
                    "input": {
                        "file_path": "src/foo.py",
                        "old_string": "a",
                        "new_string": "b",
                    },
                }
            ],
        )
        events = await _collect_events(harness)

        partial = _extract_partial_from_messages(events)

        assert partial["tool_call_count"] == 1
        assert partial["file_modifications"] == ["src/foo.py"]

    @pytest.mark.asyncio
    async def test_langgraph_multi_tool_call_extracts_all(self):
        """Multiple tool calls in one LangGraph turn each produce a
        ToolUseEvent in arrival order."""
        harness = _LangGraphLikeHarness(
            text="multi-tool",
            tool_calls=[
                {
                    "id": "1",
                    "name": "Write",
                    "input": {"file_path": "a.py", "content": "x"},
                },
                {"id": "2", "name": "Bash", "input": {"command": "ls"}},
                {
                    "id": "3",
                    "name": "Edit",
                    "input": {
                        "file_path": "b.py",
                        "old_string": "x",
                        "new_string": "y",
                    },
                },
            ],
        )
        events = await _collect_events(harness)

        partial = _extract_partial_from_messages(events)

        assert partial["tool_call_count"] == 3
        # Only Write + Edit contribute to file_modifications
        assert sorted(partial["file_modifications"]) == ["a.py", "b.py"]

    @pytest.mark.asyncio
    async def test_langgraph_empty_text_not_counted(self):
        """A LangGraph turn with empty text contributes no text block
        (matches SDK behaviour — text emptiness is checked on the typed
        event)."""
        harness = _LangGraphLikeHarness(text="", tool_calls=[])
        events = await _collect_events(harness)

        partial = _extract_partial_from_messages(events)

        assert partial["text_block_count"] == 0
        assert partial["tool_call_count"] == 0
        assert partial["file_modifications"] == []


# ============================================================================
# AC-006: _track_tool_use parity on LangGraph
# ============================================================================


class _RecordingProgressLogger:
    """Minimal progress-logger stub matching the attribute surface
    ``_track_tool_use`` writes to. Avoids importing the production
    TaskProgressLogger and the file I/O it touches."""

    def __init__(self) -> None:
        self._last_tool: str = ""
        self._files_changed: int = 0


class TestTrackToolUseLangGraphParity:
    """Migrated ``_track_tool_use`` increments progress counters when
    fed ToolUseEvent instances from the LangGraph path.
    """

    @pytest.mark.asyncio
    async def test_langgraph_tool_use_updates_last_tool(self, tmp_path):
        """The progress logger's _last_tool reflects the most recent
        ToolUseEvent the LangGraph stream emitted."""
        invoker = AgentInvoker(
            worktree_path=tmp_path, max_turns_per_agent=5
        )
        progress = _RecordingProgressLogger()
        invoker.set_progress_logger(progress)

        harness = _LangGraphLikeHarness(
            text="text",
            tool_calls=[
                {"id": "1", "name": "Read", "input": {"file_path": "a.py"}},
                {
                    "id": "2",
                    "name": "Write",
                    "input": {"file_path": "b.py", "content": "x"},
                },
            ],
        )

        async for ev in harness.invoke(
            prompt="x", role="player", tools=[], cwd=tmp_path, timeout_seconds=30
        ):
            if isinstance(ev, ToolUseEvent):
                invoker._track_tool_use(ev)
            if isinstance(ev, ResultMessageEvent):
                break

        assert progress._last_tool == "Write", (
            "AC-006 regression: _track_tool_use did not record the "
            "most recent ToolUseEvent.name. Pre-migration this counter "
            "stayed at '' on the LangGraph path because the helper "
            "walked event.raw.content (None for LangChain dicts)."
        )

    @pytest.mark.asyncio
    async def test_langgraph_write_edit_increments_files_changed(
        self, tmp_path
    ):
        """The progress logger's _files_changed counter increments only
        for Write/Edit ToolUseEvents (matches SDK behaviour)."""
        invoker = AgentInvoker(
            worktree_path=tmp_path, max_turns_per_agent=5
        )
        progress = _RecordingProgressLogger()
        invoker.set_progress_logger(progress)

        harness = _LangGraphLikeHarness(
            text="text",
            tool_calls=[
                {"id": "1", "name": "Bash", "input": {"command": "ls"}},
                {
                    "id": "2",
                    "name": "Write",
                    "input": {"file_path": "a.py", "content": "x"},
                },
                {
                    "id": "3",
                    "name": "Edit",
                    "input": {
                        "file_path": "b.py",
                        "old_string": "x",
                        "new_string": "y",
                    },
                },
                {"id": "4", "name": "Read", "input": {"file_path": "c.py"}},
            ],
        )

        async for ev in harness.invoke(
            prompt="x", role="player", tools=[], cwd=tmp_path, timeout_seconds=30
        ):
            if isinstance(ev, ToolUseEvent):
                invoker._track_tool_use(ev)
            if isinstance(ev, ResultMessageEvent):
                break

        # Write + Edit = 2 increments; Bash + Read do not contribute
        assert progress._files_changed == 2

    def test_track_tool_use_handles_no_progress_logger(self, tmp_path):
        """When no progress_logger is set, the helper returns silently
        (no crash)."""
        invoker = AgentInvoker(
            worktree_path=tmp_path, max_turns_per_agent=5
        )
        # No set_progress_logger call

        event = ToolUseEvent(
            tool_use_id="1", name="Write", input={"file_path": "a.py"}
        )

        # Must not raise
        invoker._track_tool_use(event)
