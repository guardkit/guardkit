"""Returned failed native/dcode graphs reach disk through the real consumer."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import socket
import sys
from pathlib import Path

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("guardkitfactory")

from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent
from tests.orchestrator.test_agent_invoker_langgraph import (
    _NativeExperimentChat,
    _assert_native_http_evidence,
    _assert_owned_clients_closed,
    _enable_native_experiment,
    _install_factory_owned_mock_transport,
    _make_invoker,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["role", "direct"])
@pytest.mark.parametrize("engine", ["native", "dcode"])
@pytest.mark.parametrize("text,reason", [("", "stop"), ("", "length"), ("partial", "length")])
async def test_failed_graph_retains_actual_skill_read(monkeypatch, tmp_path, engine, text, reason, route, credential_case=None):
    if engine == "dcode" and (sys.version_info < (3, 12) or importlib.util.find_spec("deepagents_code") is None):
        pytest.skip("optional dcode extra requires Python 3.12+")

    def deny(*args, **kwargs):
        raise AssertionError("real network forbidden")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")
    monkeypatch.setenv("DEEPAGENTS_CODE_OFFLINE", "1")
    emitter = NullEmitter(capture=True)
    invoker = _make_invoker(tmp_path, emitter=emitter)
    skill = _enable_native_experiment(monkeypatch, invoker.worktree_path)
    if credential_case is not None:
        with skill.open("a") as out:
            out.write("\n" + credential_case[0] + "\nSAFE_AFTER_CREDENTIAL\n")
    if engine == "dcode":
        (invoker.worktree_path / ".agents").mkdir()
        (invoker.worktree_path / ".agents/skills").symlink_to("../skills", target_is_directory=True)
        profile = os.environ.get("DEEPAGENTS_HOME")
        assert profile and Path(profile).is_absolute()
        monkeypatch.setenv("GUARDKIT_PLAYER_EXPERIMENT", json.dumps({
            "engine": engine, "skills": ["skills"], "memory": ["AGENTS.md"],
            "dcode_home": profile,
        }))
    script = _NativeExperimentChat(skill, final_text=text, finish_reason=reason)
    clients = _install_factory_owned_mock_transport(monkeypatch, script)
    errors = []
    invoke = invoker._invoke_with_role

    async def observe(**kwargs):
        try:
            return await invoke(**kwargs)
        except AgentInvocationError as error:
            errors.append(error)
            raise

    monkeypatch.setattr(invoker, "_invoke_with_role", observe)
    if route == "role":
        with pytest.raises(AgentInvocationError):
            await invoker._invoke_with_role(
                prompt="TASK-FAILED-GRAPH read the selected workflow", agent_type="player",
                allowed_tools=["Read"], permission_mode="acceptEdits",
            )
    else:
        result = await invoker._invoke_player_direct(
            task_id="TASK-FAILED-GRAPH", turn=1, requirements="Read the selected workflow",
        )
        assert result.success is False
        receipt = invoker.worktree_path / ".guardkit/autobuild/TASK-FAILED-GRAPH/task_work_results.json"
        assert json.loads(receipt.read_text())["success"] is False
    await asyncio.sleep(0.05)
    assert len(errors) == 1
    original = errors[0].__cause__
    assert type(original).__name__ == "LangGraphHarnessError"
    assert ("empty" if not text else "truncated") in str(original)
    raw = original.raw_result
    _assert_native_http_evidence(script)
    _assert_owned_clients_closed(clients)
    calls = [event for event in emitter.events if isinstance(event, LLMCallEvent)]
    assert len(calls) == 1 and calls[0].status == "error"
    assert invoker._last_session_id is None
    paths = list(invoker.worktree_path.rglob("messages.jsonl"))
    assert len(paths) == 1
    records = [json.loads(line) for line in paths[0].read_text().splitlines()]
    summary = records[0]
    assert summary["type"] == "GraphFailure"
    assert summary["outcome"] == "failed"
    assert summary["graph_result_available"] is True
    assert summary["finish_reason"] == reason
    assert summary["text_empty"] is (not text)
    assert summary["text_length"] == len(text)
    assert summary["usage"]["input_tokens"] == 7
    assert summary["usage"]["output_tokens"] == 3
    assert summary["terminal_graph_index"] == len(raw["messages"]) - 1
    messages = [record for record in records if "graph_index" in record]
    assert [record["graph_index"] for record in messages] == [1, 2, 3]
    call, result, terminal = messages
    actual_call = raw["messages"][1].tool_calls[0]
    assert call["tool_calls"] == [{key: actual_call[key] for key in ("id", "name", "args")}]
    assert call["tool_calls"][0]["args"]["file_path"] == str(skill)
    assert result["tool_call_id"] == actual_call["id"]
    assert result["status"] == "success"
    # Preserve exact output except these explicit planted regression values.
    # The independent credential probe also reuses this consumer assertion.
    expected = raw["messages"][2].content
    for planted in ("opaque-header-secret", "opaque-password-secret"):
        expected = expected.replace(planted, "[REDACTED]")
    if credential_case is not None:
        credential, safe_prefix = credential_case
        assert credential in expected
        expected = expected.split(credential, 1)[0] + safe_prefix + "[REDACTED]"
    assert result["content"] == expected
    assert "ACTUAL_CWD_SKILL_MARKER" in result["content"]
    assert terminal["content"] == text
    assert terminal["finish_reason"] == reason
    assert not any(record["type"] in {"ResultMessageEvent", "AssistantMessageEvent"} for record in records)
    evidence = os.environ.get("FAILED_GRAPH_EVIDENCE")
    if evidence:
        target = Path(evidence) / f"{engine}-{route}-{reason}-{'partial' if text else 'empty'}.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(paths[0].read_bytes())


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
        await invoker._invoke_with_role(prompt="TASK-FAILED-GRAPH crash", agent_type="player",
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


@pytest.mark.asyncio
@pytest.mark.parametrize("engine", ["native", "dcode"])
@pytest.mark.parametrize("embedded", [
    '{"Authorization": "opaque-header-secret", "password": "opaque-password-secret", "safe": "KEEP_JSON"}',
    'Example: {"Authorization": "opaque-header-secret", "password": "opaque-password-secret"} KEEP_SUFFIX',
    '{"Authorization": "opaque-header-secret"}\n{"password": "opaque-password-secret", "safe": "KEEP_JSONL"}',
])
async def test_failed_skill_read_redacts_embedded_credentials(monkeypatch, tmp_path, engine, embedded):
    original = _enable_native_experiment

    def enable(monkeypatch, worktree):
        skill = original(monkeypatch, worktree)
        with skill.open("a") as out:
            out.write("\n" + embedded + "\nKEEP_AFTER_CREDENTIALS\n")
        return skill

    monkeypatch.setattr(sys.modules[__name__], "_enable_native_experiment", enable)
    await test_failed_graph_retains_actual_skill_read(monkeypatch, tmp_path, engine, "", "length", "role")
    records = [json.loads(line) for line in next(tmp_path.rglob("messages.jsonl")).read_text().splitlines()]
    content = next(record["content"] for record in records if record["type"] == "ToolMessage")
    assert "KEEP_AFTER_CREDENTIALS" in content
    assert "[REDACTED]" in content
    for marker in ("KEEP_JSON", "KEEP_SUFFIX", "KEEP_JSONL"):
        if marker in embedded:
            assert marker in content


@pytest.mark.asyncio
@pytest.mark.parametrize("engine", ["native", "dcode"])
@pytest.mark.parametrize("credential_case", [
    ("password: 'can''t-opaque-actual-value'", "password: "),
    ('password = """opaque-actual-value"""', "password = "),
])
async def test_failed_skill_read_discards_uncertain_quoted_value(monkeypatch, tmp_path, engine, credential_case):
    await test_failed_graph_retains_actual_skill_read(
        monkeypatch, tmp_path, engine, "", "length", "role", credential_case,
    )
