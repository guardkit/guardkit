"""How a dcode Player turn's graph reaches the debug record: an empty or
cut-off answer ends the turn as usual, and a failed graph's record keeps
credentials out."""
from __future__ import annotations

import json
import socket

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("guardkitfactory")

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent
from tests.orchestrator.test_agent_invoker_langgraph import (
    _DcodePlayerChat,
    _assert_dcode_http_evidence,
    _assert_owned_clients_closed,
    _enable_dcode_player,
    _install_factory_owned_mock_transport,
    _make_invoker,
)


@pytest.fixture(autouse=True)
def _routine_fleet_route(m0_routine_fleet_route):
    """Declare the routine local-fleet route, as the module these helpers come
    from does for its own tests (an imported helper does not bring that
    module's autouse fixtures with it). Without it the M0 seat fence refuses
    the named local seat before the graph runs, so there is no failed graph to
    inspect."""


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["role", "direct"])
@pytest.mark.parametrize("text,reason", [("", "stop"), ("", "length"), ("partial", "length")])
async def test_empty_or_cut_off_answer_ends_the_turn_as_usual(monkeypatch, tmp_path, text, reason, route):
    """26 October 2026 (step 2, guardkitfactory d8fcbdb): an empty or cut-off
    final Player answer is logged by the harness and the turn ends as usual.
    No graph failure is recorded; the turn's own result (for the direct route,
    the receipt built from the files) is what the reviewer reads, and the
    skill read the graph streamed is still in the debug record."""
    def deny(*args, **kwargs):
        raise AssertionError("real network forbidden")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")
    monkeypatch.setenv("DEEPAGENTS_CODE_OFFLINE", "1")
    emitter = NullEmitter(capture=True)
    invoker = _make_invoker(tmp_path, emitter=emitter)
    skill = _enable_dcode_player(monkeypatch, invoker.worktree_path)
    script = _DcodePlayerChat(skill, final_text=text, finish_reason=reason)
    clients = _install_factory_owned_mock_transport(monkeypatch, script)
    if route == "role":
        await invoker._invoke_with_role(
            prompt="TASK-FAILED-GRAPH read the selected workflow", agent_type="player",
            allowed_tools=["Read"], permission_mode="acceptEdits",
        )
    else:
        result = await invoker._invoke_player_direct(
            task_id="TASK-FAILED-GRAPH", turn=1, requirements="Read the selected workflow",
        )
        assert result.success is True
        receipt = invoker.worktree_path / ".guardkit/autobuild/TASK-FAILED-GRAPH/task_work_results.json"
        assert json.loads(receipt.read_text())["success"] is True
    _assert_dcode_http_evidence(script)
    _assert_owned_clients_closed(clients)
    calls = [event for event in emitter.events if isinstance(event, LLMCallEvent)]
    assert all(call.status == "ok" for call in calls)
    if route == "direct":
        assert len(calls) == 1
    paths = list(invoker.worktree_path.rglob("messages.jsonl"))
    assert len(paths) == 1
    records = [json.loads(line) for line in paths[0].read_text().splitlines()]
    assert not any(record.get("type") == "GraphFailure" for record in records)
    reads = [
        record for record in records
        if record.get("type") == "NativeToolEvent" and record.get("phase") == "end"
    ]
    assert len(reads) == 1
    assert "ACTUAL_CWD_SKILL_MARKER" in reads[0]["payload"]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("break_writer", [False, True])
async def test_internal_graph_failure_does_not_invent_activity(monkeypatch, tmp_path, break_writer):
    from guardkitfactory.harness.langgraph_harness import LangGraphHarness
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import AIMessage
    from guardkit.orchestrator import sdk_debug

    monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")
    emitter = NullEmitter(capture=True)
    invoker = _make_invoker(tmp_path, emitter=emitter)
    model = FakeMessagesListChatModel(responses=[AIMessage(content="never delivered")])
    harness = LangGraphHarness(model=model)
    # The graph actually raises before returning, so Factory has no raw_result.
    from unittest.mock import AsyncMock, Mock
    graph = Mock(ainvoke=AsyncMock(side_effect=RuntimeError("original graph failure")))
    monkeypatch.setattr("guardkitfactory.harness.langgraph_harness.create_deep_agent", lambda **kw: graph)
    monkeypatch.setattr("guardkit.orchestrator.agent_invoker.select_harness", lambda **kw: harness)
    if break_writer:
        monkeypatch.setattr(sdk_debug, "preserve_failure", Mock(side_effect=RuntimeError("writer failed")))
    with pytest.raises(AgentInvocationError, match="original graph failure") as caught:
        await invoker._invoke_with_role(prompt="TASK-FAILED-GRAPH crash", agent_type="coach",
                                        allowed_tools=[], permission_mode="acceptEdits")
    assert caught.value.__cause__.__cause__.args == ("original graph failure",)
    if not break_writer:
        path = next(invoker.worktree_path.rglob("messages.jsonl"))
        records = [json.loads(line) for line in path.read_text().splitlines()]
        assert records[0]["graph_result_available"] is False
        assert records[0]["terminal_graph_index"] is None
        assert records[0]["finish_reason"] is None
        assert records[0]["usage"] is None
        assert all("graph_index" not in record for record in records)


def _failed_skill_read(tmp_path, skill_text):
    """Write the failure record for a graph that returned after reading a
    skill, through the real writer, and return the recorded tool output.

    The harness no longer fails a turn for its final answer (step 2), so these
    tests hand the writer a returned graph directly: whatever failure carries
    the graph's messages, a credential in a tool's output never reaches disk.
    """
    from guardkitfactory.harness.langgraph_harness import LangGraphHarnessError
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from guardkit.orchestrator import sdk_debug

    call = {"id": "call-read-selected-skill", "name": "read_file",
            "args": {"file_path": "skills/planning/SKILL.md"}}
    raw = {"messages": [
        HumanMessage(content="TASK-FAILED-GRAPH read the selected workflow"),
        AIMessage(content="", tool_calls=[call]),
        ToolMessage(content=skill_text, tool_call_id=call["id"], status="success"),
        AIMessage(content=""),
    ]}
    debug_dir = tmp_path / "sdk_debug" / "turn_1"
    debug_dir.mkdir(parents=True)
    sdk_debug.preserve_failure(debug_dir, LangGraphHarnessError("graph failed", raw_result=raw))
    written = (debug_dir / "messages.jsonl").read_text()
    for planted in ("opaque-header-secret", "opaque-password-secret", "opaque-actual-value"):
        assert planted not in written
    records = [json.loads(line) for line in written.splitlines()]
    return next(record["content"] for record in records if record["type"] == "ToolMessage")


_SKILL_TEXT = "# Planning\n\nACTUAL_CWD_SKILL_MARKER\n"


@pytest.mark.parametrize("embedded", [
    '{"Authorization": "opaque-header-secret", "password": "opaque-password-secret", "safe": "KEEP_JSON"}',
    'Example: {"Authorization": "opaque-header-secret", "password": "opaque-password-secret"} KEEP_SUFFIX',
    '{"Authorization": "opaque-header-secret"}\n{"password": "opaque-password-secret", "safe": "KEEP_JSONL"}',
])
def test_failed_skill_read_redacts_embedded_credentials(tmp_path, embedded):
    content = _failed_skill_read(tmp_path, _SKILL_TEXT + embedded + "\nKEEP_AFTER_CREDENTIALS\n")
    assert "ACTUAL_CWD_SKILL_MARKER" in content
    assert "KEEP_AFTER_CREDENTIALS" in content
    assert "[REDACTED]" in content
    for marker in ("KEEP_JSON", "KEEP_SUFFIX", "KEEP_JSONL"):
        if marker in embedded:
            assert marker in content


@pytest.mark.parametrize("credential_case", [
    ("password: 'can''t-opaque-actual-value'", "password: "),
    ('password = """opaque-actual-value"""', "password = "),
])
def test_failed_skill_read_discards_uncertain_quoted_value(tmp_path, credential_case):
    credential, safe_prefix = credential_case
    content = _failed_skill_read(tmp_path, _SKILL_TEXT + credential + "\nSAFE_AFTER_CREDENTIAL\n")
    assert content == _SKILL_TEXT + safe_prefix + "[REDACTED]"
