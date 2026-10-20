"""A model call's record names where it went and the model that answered.

20 October 2026. Every factory Player and Coach turn was recorded as
``"provider": "anthropic"`` with the CLI's default model name (on 19 October
``claude-sonnet-4-5-20250929``, on 20 October ``claude-opus-5-5``), although
the turn ran on a local model through an OpenAI-compatible client: the
configured name won over anything the server said, and the provider was read
from ``ANTHROPIC_BASE_URL`` alone, with "anthropic" as the fallback.

Checked here, through the real ``_invoke_with_role`` where a turn is made:

* a LangGraph turn on a local seat, asked for a frontier-looking alias,
  records provider ``local-vllm``, the model the server reported, and the
  alias as ``requested_model``; with nothing reported, ``"unknown"``;
* an SDK turn to Anthropic's own API records the model the API reported;
* the route rules, harness by harness.

Invented seats and model names only; nothing reaches a network.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, List, Optional
from unittest.mock import patch

import pytest
from claude_agent_sdk import AssistantMessage as SdkAssistantMessage
from claude_agent_sdk import ResultMessage as SdkResultMessage
from langchain_core.messages import AIMessage

from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.harness.selector import seat_for_record
from guardkit.orchestrator.instrumentation.emitter import NullEmitter
from guardkit.orchestrator.instrumentation.llm_instrumentation import (
    provider_for_route,
)
from guardkit.orchestrator.instrumentation.schemas import LLMCallEvent
from guardkit.orchestrator.m0_fence import LANGGRAPH_DEFAULT_SEAT

LOCAL_SEAT = "http://10.20.30.40:31823/v1"
ALIAS = "claude-opus-5-5"  # the name the CLI asks for by default


class _StubHarness:
    """Yields what a harness yields; nothing is constructed or called."""

    supports_resume = False

    def __init__(self, raw: Any, result_raw: Any = None) -> None:
        self.raw = raw
        self.result_raw = result_raw

    async def invoke(self, **kwargs: Any):
        yield AssistantMessageEvent(text="done", raw=self.raw)
        yield ResultMessageEvent(
            session_id=None, stop_reason="end_turn", usage=None, raw=self.result_raw
        )

    async def cancel(self) -> None:  # pragma: no cover - not reached
        return None


def _sdk_assistant(model: str) -> SdkAssistantMessage:
    """A real Claude SDK AssistantMessage (it has no ``.type``)."""
    message = SdkAssistantMessage(content=[], model=model)
    assert not hasattr(message, "type")
    return message


def _sdk_result(model_usage: Optional[dict]) -> SdkResultMessage:
    """A real Claude SDK ResultMessage (it has no ``.type``)."""
    message = SdkResultMessage(
        subtype="success", duration_ms=10, duration_api_ms=8, is_error=False,
        num_turns=1, session_id="session-1", model_usage=model_usage,
    )
    assert not hasattr(message, "type")
    return message


def _invoker(tmp_path: Path, emitter: NullEmitter, model_name: Optional[str]):
    from guardkit.orchestrator.agent_invoker import AgentInvoker

    worktree = tmp_path / "worktree"
    worktree.mkdir(exist_ok=True)
    return AgentInvoker(
        worktree_path=worktree,
        max_turns_per_agent=30,
        sdk_timeout_seconds=60,
        emitter=emitter,
        model_name=model_name,
    )


async def _one_turn(
    tmp_path: Path, raw: Any, model_name: Optional[str], result_raw: Any = None
) -> LLMCallEvent:
    emitter = NullEmitter(capture=True)
    invoker = _invoker(tmp_path, emitter, model_name)
    with patch(
        "guardkit.orchestrator.agent_invoker.select_harness",
        return_value=_StubHarness(raw, result_raw),
    ):
        await invoker._invoke_with_role(
            prompt="TASK-SEAT-001 one turn",
            agent_type="player",
            allowed_tools=["Read"],
            permission_mode="acceptEdits",
        )
        await asyncio.sleep(0.05)
    events = [e for e in emitter.events if isinstance(e, LLMCallEvent)]
    assert len(events) == 1
    return events[0]


@pytest.fixture
def local_langgraph_seat(monkeypatch):
    monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
    monkeypatch.setenv("OPENAI_BASE_URL", LOCAL_SEAT)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_URL", raising=False)


class TestATurnRecordsItsRealSeat:
    @pytest.mark.asyncio
    async def test_local_seat_records_the_served_model_not_the_alias(
        self, tmp_path: Path, local_langgraph_seat
    ) -> None:
        state = {
            "messages": [
                AIMessage(content="thinking", response_metadata={"model_name": "early"}),
                AIMessage(
                    content="done",
                    response_metadata={"model_name": "local-coder-27b"},
                ),
            ]
        }
        event = await _one_turn(tmp_path, state, ALIAS)
        assert event.provider == "local-vllm"
        assert event.model == "local-coder-27b"
        assert event.requested_model == f"openai:{ALIAS}"

    @pytest.mark.asyncio
    async def test_local_seat_with_nothing_reported_is_unknown(
        self, tmp_path: Path, local_langgraph_seat
    ) -> None:
        event = await _one_turn(
            tmp_path, {"messages": [AIMessage(content="done")]}, ALIAS
        )
        assert event.provider == "local-vllm"
        assert event.model == "unknown"
        assert event.model != ALIAS
        assert event.requested_model == f"openai:{ALIAS}"

    @pytest.mark.asyncio
    async def test_a_synthesis_reply_message_is_read_too(
        self, tmp_path: Path, local_langgraph_seat
    ) -> None:
        """The Coach's toolless call hands back one message, not a state."""
        reply = AIMessage(content="{}", response_metadata={"model": "local-judge-9b"})
        event = await _one_turn(tmp_path, reply, ALIAS)
        assert event.model == "local-judge-9b"

    @pytest.mark.asyncio
    async def test_sdk_turn_records_the_model_the_api_reported(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        event = await _one_turn(
            tmp_path, _sdk_assistant("claude-test-model-20261001"), "claude-test-model"
        )
        assert event.provider == "anthropic"
        assert event.model == "claude-test-model-20261001"
        assert event.requested_model == "claude-test-model"

    @pytest.mark.asyncio
    async def test_real_sdk_messages_on_a_local_route_record_the_served_model(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Review round 1: the SDK's real AssistantMessage carries no
        ``.type``; the served model it names is recorded, not the alias."""
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://10.9.8.7:4000")
        event = await _one_turn(
            tmp_path, _sdk_assistant("local-coder-27b"), ALIAS,
            result_raw=_sdk_result({"local-coder-27b": {"inputTokens": 5}}),
        )
        assert event.provider == "local-vllm"
        assert event.model == "local-coder-27b"
        assert event.model != ALIAS
        assert event.requested_model == ALIAS

    @pytest.mark.asyncio
    async def test_real_sdk_result_message_model_usage_is_read(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """With no assistant message naming a model, the real ResultMessage's
        ``model_usage`` names the model that answered."""
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://10.9.8.7:4000")
        event = await _one_turn(
            tmp_path, {"messages": []}, ALIAS,
            result_raw=_sdk_result({"local-judge-9b": {"outputTokens": 3}}),
        )
        assert event.provider == "local-vllm"
        assert event.model == "local-judge-9b"
        assert event.requested_model == ALIAS

    @pytest.mark.asyncio
    async def test_real_sdk_result_without_usage_is_unknown(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://10.9.8.7:4000")
        event = await _one_turn(
            tmp_path, {"messages": []}, ALIAS, result_raw=_sdk_result(None)
        )
        assert event.model == "unknown"

    @pytest.mark.asyncio
    async def test_sdk_turn_on_a_local_seat_is_not_called_anthropic(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://workhorse:4000")
        event = await _one_turn(tmp_path, {"messages": []}, ALIAS)
        assert event.provider == "local-vllm"
        assert event.model == "unknown"
        assert event.requested_model == ALIAS

    @pytest.mark.asyncio
    async def test_vendor_api_without_a_report_records_the_named_model(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A vendor's own API serves exactly the model named."""
        monkeypatch.setenv("GUARDKIT_HARNESS", "langgraph")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_URL", raising=False)
        event = await _one_turn(tmp_path, {"messages": []}, "anthropic:claude-test-model")
        assert event.provider == "anthropic"
        assert event.model == "claude-test-model"
        assert event.requested_model == "anthropic:claude-test-model"


class TestSeatForRecord:
    def test_langgraph_bare_alias_goes_to_the_openai_route(self) -> None:
        env = {"GUARDKIT_HARNESS": "langgraph", "OPENAI_BASE_URL": LOCAL_SEAT}
        seat = seat_for_record(ALIAS, env)
        assert (seat.harness, seat.requested_model, seat.provider) == (
            "langgraph", f"openai:{ALIAS}", "local-vllm",
        )

    def test_langgraph_without_a_model_names_deepagents_default(self) -> None:
        seat = seat_for_record(None, {"GUARDKIT_HARNESS": "langgraph"})
        assert seat.requested_model == LANGGRAPH_DEFAULT_SEAT
        assert seat.provider == "anthropic"

    def test_langgraph_anthropic_prefix_reads_the_anthropic_urls(self) -> None:
        seat = seat_for_record(
            "anthropic:x",
            {"GUARDKIT_HARNESS": "langgraph", "ANTHROPIC_API_URL": "http://127.0.0.1:8"},
        )
        assert seat.provider == "local-vllm"

    def test_the_default_harness_is_langgraph(self) -> None:
        seat = seat_for_record(ALIAS, {"OPENAI_BASE_URL": LOCAL_SEAT})
        assert seat.harness == "langgraph"
        assert seat.provider == "local-vllm"

    @pytest.mark.parametrize(
        "model,env,expected",
        [
            ("ollama:x", {"GUARDKIT_HARNESS": "langgraph"}, "unknown"),
            (object(), {"GUARDKIT_HARNESS": "langgraph"}, "unknown"),
            (ALIAS, {"GUARDKIT_HARNESS": "something-else"}, "unknown"),
            (None, {"GUARDKIT_HARNESS": "sdk"}, "anthropic"),
        ],
    )
    def test_what_cannot_be_told_is_unknown(self, model, env, expected) -> None:
        assert seat_for_record(model, env).provider == expected

    def test_sdk_without_a_model_requests_nothing_nameable(self) -> None:
        assert seat_for_record(None, {"GUARDKIT_HARNESS": "sdk"}).requested_model is None


class TestProviderForRoute:
    @pytest.mark.parametrize(
        "client,base_url,expected",
        [
            ("anthropic", None, "anthropic"),
            ("anthropic", "", "anthropic"),
            ("anthropic", "https://api.anthropic.com", "anthropic"),
            ("anthropic", "http://localhost:4000", "local-vllm"),
            ("anthropic", "http://10.1.2.3:31823", "local-vllm"),
            ("anthropic", "https://proxy.example.com", "unknown"),
            ("anthropic", "api.anthropic.com", "unknown"),
            ("openai", None, "openai"),
            ("openai", "https://api.openai.com/v1", "openai"),
            ("openai", "http://192.168.1.5:8000/v1", "local-vllm"),
            ("openai", "http://workhorse:9000/v1", "local-vllm"),
            ("openai", "https://openrouter.ai/api/v1", "unknown"),
            ("openai", "https://api.anthropic.com", "unknown"),
            ("ollama", None, "unknown"),
            (None, None, "unknown"),
        ],
    )
    def test_route(self, client, base_url, expected) -> None:
        assert provider_for_route(client, base_url) == expected
