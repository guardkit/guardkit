"""Regression tests for typed Fleet Memory writes through the HTTP door."""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClient,
    FleetMemoryConfig,
    _typed_door_payload,
    write_through_the_door,
)

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("nats_core") is None,
    reason="nats_core memory extra is required for the real typed episode builder",
)


@pytest.fixture(autouse=True)
def _deny_network(monkeypatch):
    attempts: list[str] = []

    def denied(*_args, **_kwargs):
        attempts.append("socket")
        raise AssertionError("network access is forbidden in typed-door tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    yield attempts
    assert attempts == []


@pytest.fixture
def client() -> FleetMemoryClient:
    value = FleetMemoryClient(
        FleetMemoryConfig(
            enabled=True,
            postgres_dsn="postgresql://fake:fake@localhost:5433/fake",
            embed_url="http://localhost:9000/v1",
            embed_model="fake",
            embed_dims=768,
            nats_url="nats://localhost:4222",
            project="guardkit",
        )
    )
    value._nats_available = True
    return value


def outcome_body() -> str:
    return json.dumps(
        {
            "task_id": "TASK-DBE3-001",
            "success": True,
            "duration_minutes": 3,
            "approach_used": "async SQLAlchemy aggregation",
            "lessons_learned": ["preserve typed identity"],
            "feature_id": "FEAT-DBE3",
        }
    )


def expected_door_payload() -> dict:
    return {
        "payload_type": "build_outcome",
        "project": "guardkit",
        "identifier": "TASK_DBE3_001",
        "source_ref": "FEAT-DBE3",
        "domain_tags": ["task"],
        "status": "success",
        "duration_seconds": 180,
        "task_id": "TASK-DBE3-001",
        "lessons": "preserve typed identity",
        "approach": "async SQLAlchemy aggregation",
    }


async def test_bus_exception_sends_complete_typed_outcome_to_door_without_mutation(client):
    """Reproduce B9's empty-INFO branch and assert the missing type is restored."""
    captured_episodes = []

    async def bus_refused(episodes):
        captured_episodes.extend(episodes)
        raise RuntimeError("empty response when expecting INFO")

    door = AsyncMock(return_value=True)
    with (
        patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(side_effect=bus_refused),
        ),
        patch(
            "guardkit.knowledge.fleet_memory_client.write_through_the_door",
            new=door,
        ),
    ):
        result = await client.add_episode(
            name="OUT-D2C9FDA3: TASK-DBE3-001 - Add daily user counts",
            episode_body=outcome_body(),
            group_id="task_outcomes",
        )

    assert result == "build_outcome:guardkit:TASK_DBE3_001"
    door.assert_awaited_once_with(expected_door_payload())
    assert len(captured_episodes) == 1
    episode = captured_episodes[0]
    assert episode.payload_type == "build_outcome"
    assert json.loads(episode.body) == {
        key: value for key, value in expected_door_payload().items()
        if key != "payload_type"
    }
    assert "payload_type" not in json.loads(episode.body)


async def test_zero_publish_summary_uses_same_complete_typed_door_payload(client):
    from guardkit.memory.harvest_publisher import PublishSummary

    door = AsyncMock(return_value=True)
    summary = PublishSummary(published=0, skipped_oversized=1, counts_per_type={})
    with (
        patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(return_value=summary),
        ),
        patch(
            "guardkit.knowledge.fleet_memory_client.write_through_the_door",
            new=door,
        ),
    ):
        result = await client.add_episode(
            name="OUT-D2C9FDA3: TASK-DBE3-001 - Add daily user counts",
            episode_body=outcome_body(),
            group_id="task_outcomes",
        )

    assert result == "build_outcome:guardkit:TASK_DBE3_001"
    door.assert_awaited_once_with(expected_door_payload())


async def test_successful_bus_does_not_construct_or_call_door(client):
    from guardkit.memory.harvest_publisher import PublishSummary

    door = AsyncMock(return_value=True)
    summary = PublishSummary(published=1, skipped_oversized=0, counts_per_type={})
    with (
        patch(
            "guardkit.memory.harvest_publisher.publish_episodes",
            new=AsyncMock(return_value=summary),
        ),
        patch(
            "guardkit.knowledge.fleet_memory_client.write_through_the_door",
            new=door,
        ),
    ):
        result = await client.add_episode(
            name="OUT-D2C9FDA3: TASK-DBE3-001 - Add daily user counts",
            episode_body=outcome_body(),
            group_id="task_outcomes",
        )

    assert result == "build_outcome:guardkit:TASK_DBE3_001"
    door.assert_not_awaited()


@pytest.mark.parametrize(
    "episode",
    [
        SimpleNamespace(body="{}"),
        SimpleNamespace(payload_type=None, body="{}"),
        SimpleNamespace(payload_type=7, body="{}"),
        SimpleNamespace(payload_type="", body="{}"),
        SimpleNamespace(payload_type=" build_outcome", body="{}"),
        SimpleNamespace(payload_type="build_outcome", body="not-json"),
        SimpleNamespace(payload_type="build_outcome", body="[]"),
        SimpleNamespace(
            payload_type="build_outcome",
            body='{"payload_type": "adr", "status": "success"}',
        ),
    ],
)
def test_invalid_or_conflicting_typed_episode_fails_closed(episode):
    with pytest.raises(ValueError):
        _typed_door_payload(episode)


def test_typed_payload_is_fresh_and_does_not_mutate_episode_body():
    raw = '{"payload_type": "build_outcome", "status": "success"}'
    episode = SimpleNamespace(payload_type="build_outcome", body=raw)

    payload = _typed_door_payload(episode)
    payload["status"] = "changed"

    assert episode.body == raw
    assert json.loads(episode.body)["status"] == "success"


async def test_fake_mcp_receives_exact_typed_payload(monkeypatch):
    captured = {}
    mcp = ModuleType("mcp")
    mcp.__path__ = []
    mcp_client = ModuleType("mcp.client")
    mcp_client.__path__ = []
    stream_module = ModuleType("mcp.client.streamable_http")

    class Stream:
        async def __aenter__(self):
            return (object(), object())

        async def __aexit__(self, *_args):
            return False

    class Session:
        def __init__(self, _read, _write):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def initialize(self):
            return None

        async def call_tool(self, name, arguments):
            captured.update({"name": name, "arguments": arguments})
            return SimpleNamespace(
                isError=False,
                content=[SimpleNamespace(text=json.dumps({"natural_key": "ok"}))],
            )

    mcp.ClientSession = Session
    stream_module.streamable_http_client = lambda _url: Stream()
    monkeypatch.setitem(sys.modules, "mcp", mcp)
    monkeypatch.setitem(sys.modules, "mcp.client", mcp_client)
    monkeypatch.setitem(sys.modules, "mcp.client.streamable_http", stream_module)

    payload = expected_door_payload()
    assert await write_through_the_door(payload, url="http://unit.invalid/mcp") is True
    assert captured == {
        "name": "memory_write_payload",
        "arguments": {"payload": payload},
    }
