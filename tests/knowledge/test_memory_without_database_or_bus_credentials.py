"""Memory without a database address or a bus password (14 October 2026).

The build sandbox is to hold no factory credential. Memory then has one route
in and out: the memory door, the memory service's MCP endpoint, which needs no
key. These tests pin what GuardKit does in that setting:

1. With memory on and neither a database address nor a door, nothing falls
   back to a database address written in the code. Reads are off, said once.
2. With a door and no database address, reads go through the door's
   ``memory_search_items`` tool and give the same hits as the store route.
3. With no bus password, writes go straight to the door, and say so once.
4. A door that answers 500 is a failed read, and the error names the door.
5. The autobuild's real per-thread loader lifecycle works through the door.
6. A door that is down skips the loader with "connection failed", and the
   build carries on.
7. The stamp check reaches the model door at the shared model address with
   the fixed placeholder key (a positive control).

STAND-INS, AND NOTHING LIVE. The door is a real FastMCP server (the same
library the memory service uses) on a loopback port, run by uvicorn in a
thread. The failing door is a plain HTTP server that answers 500. The model
door is a plain HTTP server that records one request. The database and the
bus are never reached: every connection to port 5433 (the database address
the old code default named) or 4222 (the bus) is refused and recorded at the
socket, and fleet-memory's ``async_store_context`` is replaced by one that
records the call and refuses. The tests assert that neither was touched.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge import fleet_memory_client as fmc
from guardkit.knowledge.fleet_memory_client import (
    FleetMemoryClient,
    FleetMemoryClientFactory,
    FleetMemoryConfig,
    MemoryReadUnavailable,
)
from guardkit.knowledge.memory_project import MemoryProjectResolution

CLIENT_LOGGER = "guardkit.knowledge.fleet_memory_client"
AUTOBUILD = "guardkit.orchestrator.autobuild"
PROJECT = "demo"
GUARDED_PORTS = (5433, 4222)
PLACEHOLDER_MODEL_KEY = "no-key-the-model-door-adds-it"


# ---------------------------------------------------------------------------
# Guards: nothing reaches a database or a bus
# ---------------------------------------------------------------------------


@pytest.fixture
def refused_connections(monkeypatch) -> list:
    """Refuse and record every connection to the database or bus ports."""
    attempts: list = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _check(address: Any) -> None:
        if isinstance(address, tuple) and len(address) >= 2 and address[1] in GUARDED_PORTS:
            attempts.append(address[1])
            raise ConnectionRefusedError(f"test guard: port {address[1]} is not to be used")

    def connect(self, address):
        _check(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        _check(address)
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    return attempts


@pytest.fixture
def store_never_opened(monkeypatch) -> list:
    """fleet-memory's database store, replaced by one that refuses and records."""
    import fleet_memory.store as fleet_memory_store

    calls: list = []

    def refuse(*args, **kwargs):
        calls.append("async_store_context")
        raise AssertionError("the database store must not be opened here")

    monkeypatch.setattr(fleet_memory_store, "async_store_context", refuse)
    return calls


@pytest.fixture
def memory_env(monkeypatch):
    """Memory on, a memory name, and none of the credentials or addresses set."""
    for name in (
        "FLEET_MEMORY_PG_DSN",
        "FLEET_MEMORY_MCP_URL",
        "FLEET_MEMORY_NATS_URL",
        "FLEET_MEMORY_RETRIEVAL",
        "GUARDKIT_NATS_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FLEET_MEMORY_ENABLED", "true")
    monkeypatch.setattr(
        fmc,
        "_memory_project_resolution",
        MemoryProjectResolution(project=PROJECT, source="handover", message="test"),
    )
    return monkeypatch


@pytest.fixture
def query_log(monkeypatch) -> list:
    entries: list = []
    monkeypatch.setattr(
        "guardkit.knowledge.query_logger.log_query",
        lambda **kwargs: entries.append(kwargs),
    )
    return entries


# ---------------------------------------------------------------------------
# Stand-ins
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class StandInDoor:
    """A real FastMCP server on loopback offering the memory door's two tools."""

    def __init__(self, items: list[dict]) -> None:
        import uvicorn
        from fastmcp import FastMCP

        self.items = items
        self.searches: list[dict] = []
        self.writes: list[dict] = []
        door = FastMCP("memory-door-stand-in")

        @door.tool(name="memory_search_items")
        async def memory_search_items(
            project: str,
            query: Optional[str] = None,
            payload_types: Optional[list[str]] = None,
            domain_tags: Optional[list[str]] = None,
            token_budget: Optional[int] = None,
            include_superseded: bool = False,
            require_substantive: bool = False,
        ) -> dict:
            self.searches.append(
                {
                    "project": project,
                    "query": query,
                    "payload_types": payload_types,
                    "domain_tags": domain_tags,
                    "include_superseded": include_superseded,
                    "require_substantive": require_substantive,
                }
            )
            # The memory service's shared tool envelope.
            return {
                "is_error": False,
                "error_type": None,
                "message": "",
                "value": {"items": self.items},
            }

        @door.tool(name="memory_write_payload")
        async def memory_write_payload(payload: dict) -> dict:
            self.writes.append(payload)
            key = f"{payload['payload_type']}:{payload['project']}:{payload['identifier']}"
            return {"is_error": False, "error_type": None, "message": "", "value": key}

        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}/mcp"
        self._server = uvicorn.Server(
            uvicorn.Config(
                door.http_app(path="/mcp"),
                host="127.0.0.1",
                port=self.port,
                log_level="warning",
                lifespan="on",
            )
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self) -> "StandInDoor":
        self._thread.start()
        deadline = time.monotonic() + 15
        while not self._server.started:
            if time.monotonic() > deadline or not self._thread.is_alive():
                raise RuntimeError("the stand-in door did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


class _RecordingHandler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # quiet
        return None


class StandInHttp:
    """A plain loopback HTTP server: answers every request with one response."""

    def __init__(self, status: int, body: dict) -> None:
        self.requests: list[dict] = []
        outer = self

        class Handler(_RecordingHandler):
            def _answer(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                outer.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "authorization": self.headers.get("Authorization"),
                        "body": raw,
                    }
                )
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_DELETE = _answer

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "StandInHttp":
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()


def _rule_document(body: str, tag: str = "rules_example") -> str:
    inner = json.dumps(
        {
            "entity_type": "rule",
            "id": "example/guidance/database",
            "template_id": "example",
            "name": "Database guidance",
            "content": body,
        }
    )
    inner += "\n\n---\n_metadata:\n```json\n{}\n```"
    return json.dumps({"content": inner, "domain_tags": [tag], "source_ref": tag})


RULE_BODY = (
    "# Database guidance\n\n"
    "## Boundaries\n\n"
    "### ALWAYS\n"
    "- Use one grouped query to count users per day.\n\n"
    "## Indexes\n"
    "- Index the created-at column before counting.\n"
)

THREE_ITEMS = [
    {
        "value": {
            "natural_key": "build_outcome:demo:TASK_1",
            "content": "Counting users per day worked with one grouped query.",
        },
        "score": 0.91,
    },
    {
        "value": {
            "natural_key": "document:demo:rule-1",
            "content": _rule_document(RULE_BODY),
        },
        "score": 0.83,
    },
    {
        "value": {
            "natural_key": "build_outcome:demo:TASK_2",
            "content": "Retry the database call with a short back-off.",
        },
        "score": 0.62,
    },
]


def _store_route_hits(monkeypatch, items: list[dict], call) -> list[dict]:
    """The hits the database route gives for the same ranked items."""
    import sys
    import types

    class SearchRequest:
        def __init__(self, **fields):
            self.fields = fields

    async def search(request, store):
        return [SimpleNamespace(value=dict(i["value"]), score=i["score"]) for i in items]

    retrieval = types.ModuleType("fleet_memory.retrieval")
    retrieval.SearchRequest = SearchRequest
    retrieval.search = search
    with monkeypatch.context() as scoped:
        scoped.setitem(sys.modules, "fleet_memory.retrieval", retrieval)
        client = FleetMemoryClient(
            FleetMemoryConfig(
                enabled=True,
                postgres_dsn="postgresql://unused@invalid/none",
                project=PROJECT,
            )
        )
        client._read_available = True
        client._store = object()
        return asyncio.run(call(client))


def _door_client(door_url: str) -> FleetMemoryClient:
    return FleetMemoryClient(
        FleetMemoryConfig(enabled=True, postgres_dsn=None, door_url=door_url, project=PROJECT)
    )


# ---------------------------------------------------------------------------
# 1. No database address never falls back to a code default
# ---------------------------------------------------------------------------


def test_no_database_address_never_falls_back_to_a_code_default(
    memory_env, refused_connections, store_never_opened, query_log, caplog
):
    config = fmc._load_fleet_config_from_env()

    assert config.enabled is True
    assert config.postgres_dsn is None
    assert config.door_url is None
    assert FleetMemoryConfig().postgres_dsn is None

    client = FleetMemoryClient(config)
    caplog.clear()  # loading the config says it once too; count the client's own
    with caplog.at_level(logging.WARNING, logger=CLIENT_LOGGER):
        first = asyncio.run(client.search("count users per day"))
        second = asyncio.run(client.search("count users per day"))

    assert first == [] and second == []
    off = [r for r in caplog.records if "reads are off" in r.getMessage()]
    assert len(off) == 1, [r.getMessage() for r in caplog.records]
    assert store_never_opened == []
    assert refused_connections == []
    assert query_log == []


# ---------------------------------------------------------------------------
# 2. Reads go through the door without a database address
# ---------------------------------------------------------------------------


def test_reads_go_through_the_door_without_a_database_address(
    memory_env, monkeypatch, refused_connections, store_never_opened, query_log
):
    async def plain(client):
        return await client.search("count users per day", num_results=10)

    async def declared(client):
        return await client.search(
            "count users per day", group_ids=[], document_source_tags=["rules_example"]
        )

    expected_plain = _store_route_hits(monkeypatch, THREE_ITEMS, plain)
    expected_declared = _store_route_hits(monkeypatch, THREE_ITEMS, declared)
    assert len(expected_plain) == 3
    assert expected_declared and all("section_sha256" in hit for hit in expected_declared)
    query_log.clear()

    with StandInDoor(THREE_ITEMS) as door:
        memory_env.setenv("FLEET_MEMORY_MCP_URL", door.url)
        config = fmc._load_fleet_config_from_env()
        assert config.postgres_dsn is None
        assert config.door_url == door.url
        client = FleetMemoryClient(config)

        got_plain = asyncio.run(plain(client))
        assert len(query_log) == 1
        got_declared = asyncio.run(declared(client))

    assert [(h["fact"], h["uuid"], h["score"]) for h in got_plain] == [
        (h["fact"], h["uuid"], h["score"]) for h in expected_plain
    ]
    assert got_declared == expected_declared
    assert client.reads == {"completed": 2, "failed": 0}

    # The query log has one entry per search, carrying the items' natural keys.
    assert len(query_log) == 2
    assert [entry["id"] for entry in query_log[0]["items"]] == [
        item["value"]["natural_key"] for item in THREE_ITEMS
    ]
    assert [entry["score"] for entry in query_log[0]["items"]] == [0.91, 0.83, 0.62]

    # The door was asked for the same scope the store route would have used.
    assert door.searches[0]["project"] == PROJECT
    assert door.searches[0]["query"] == "count users per day"
    assert door.searches[1]["payload_types"] == ["document"]
    assert door.searches[1]["domain_tags"] == ["rules_example"]
    assert store_never_opened == []
    assert refused_connections == []


def test_door_mode_set_up_health_check_close_and_read_back(
    memory_env, refused_connections, store_never_opened
):
    with StandInDoor(THREE_ITEMS) as door:
        client = _door_client(door.url)

        async def lifecycle():
            started = await client.initialize()
            healthy = await client.health_check()
            await client.close()
            return started, healthy

        started, healthy = asyncio.run(lifecycle())

    assert started is True and healthy is True
    assert client._store is None and client._store_loop is None
    assert client._initialized is False  # close() leaves it closed, as today
    with pytest.raises(MemoryReadUnavailable, match="memory door, which has no read-back"):
        asyncio.run(client.read_record("adr", "ADR_1"))
    assert store_never_opened == []
    assert refused_connections == []


# ---------------------------------------------------------------------------
# 3. Writes go straight to the door without a bus password
# ---------------------------------------------------------------------------

OUTCOME_BODY = json.dumps(
    {
        "task_id": "TASK-DBE3-001",
        "success": True,
        "duration_minutes": 3,
        "approach_used": "one grouped query",
        "lessons_learned": ["count with one query"],
        "feature_id": "FEAT-DBE3",
    }
)


@pytest.mark.skipif(
    importlib.util.find_spec("nats_core") is None,
    reason="the typed episode builder needs the nats_core memory extra",
)
def test_writes_go_straight_to_the_door_without_a_bus_password(
    memory_env, monkeypatch, refused_connections, store_never_opened, caplog
):
    import guardkit.memory.harvest_publisher as harvest_publisher

    bus = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    bus.bind(("127.0.0.1", 0))
    bus.listen(1)
    bus.setblocking(False)
    memory_env.setenv("FLEET_MEMORY_NATS_URL", f"nats://127.0.0.1:{bus.getsockname()[1]}")

    bus_calls: list = []
    real_publish = harvest_publisher.publish_episodes

    async def recording_publish(*args, **kwargs):
        bus_calls.append(args)
        return await real_publish(*args, **kwargs)

    monkeypatch.setattr(harvest_publisher, "publish_episodes", recording_publish)

    try:
        with StandInDoor([]) as door:
            memory_env.setenv("FLEET_MEMORY_MCP_URL", door.url)
            client = FleetMemoryClient(fmc._load_fleet_config_from_env())
            with caplog.at_level(logging.INFO, logger=CLIENT_LOGGER):
                keys = [
                    asyncio.run(
                        client.add_episode(
                            name=f"OUT-1: TASK-DBE3-00{n} - Count users per day",
                            episode_body=OUTCOME_BODY.replace("001", f"00{n}"),
                            group_id="task_outcomes",
                        )
                    )
                    for n in (1, 2)
                ]
        try:
            bus.accept()
            bus_connected = True
        except BlockingIOError:
            bus_connected = False
    finally:
        bus.close()

    assert keys == ["build_outcome:demo:TASK_DBE3_001", "build_outcome:demo:TASK_DBE3_002"]
    # Positive control: the door recorded both typed payloads.
    assert [w["identifier"] for w in door.writes] == ["TASK_DBE3_001", "TASK_DBE3_002"]
    assert all(w["payload_type"] == "build_outcome" for w in door.writes)
    assert all(w["project"] == PROJECT for w in door.writes)

    messages = [r.getMessage() for r in caplog.records]
    chosen = [m for m in messages if "no bus account here; writing through the memory door" in m]
    assert len(chosen) == 1, messages
    assert not any("the bus did not carry" in m for m in messages), messages
    assert sum("through the door" in m and m.startswith("[Memory] Wrote") for m in messages) == 2

    # The bus was never tried.
    assert bus_calls == []
    assert bus_connected is False
    assert refused_connections == []
    assert store_never_opened == []


# ---------------------------------------------------------------------------
# 4. A door failure is said plainly
# ---------------------------------------------------------------------------


def test_a_door_failure_is_said_plainly(
    memory_env, monkeypatch, refused_connections, store_never_opened, query_log, caplog
):
    monkeypatch.setattr(fmc, "DOOR_READ_TIMEOUT_SECONDS", 10.0, raising=False)
    with StandInHttp(500, {"error": "the door is broken"}) as broken:
        door_url = f"http://127.0.0.1:{broken.port}/mcp"
        client = _door_client(door_url)
        with caplog.at_level(logging.WARNING, logger=CLIENT_LOGGER):
            hits = asyncio.run(client.search("count users per day"))

    assert hits == []
    assert client.reads == {"completed": 0, "failed": 1}
    assert broken.requests, "the read must have gone to the door"
    errors = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any(
        "memory door" in m and f"127.0.0.1:{broken.port}" in m and "500" in m for m in errors
    ), errors
    assert query_log == []
    assert store_never_opened == []
    assert refused_connections == []


# ---------------------------------------------------------------------------
# 5 and 6. The autobuild's real per-thread loader lifecycle
# ---------------------------------------------------------------------------


def _orchestrator(tmp_path: Path, factory: FleetMemoryClientFactory):
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    invoker = MagicMock()
    invoker.invoke_player = AsyncMock(
        return_value=MagicMock(success=True, error=None, report={"summary": "done"})
    )
    with patch(f"{AUTOBUILD}.get_memory_factory", return_value=factory):
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            max_turns=3,
            enable_context=True,
            context_loader=None,
            worktree_manager=MagicMock(),
            agent_invoker=invoker,
            progress_display=MagicMock(),
            enable_checkpoints=False,
        )
    orchestrator._factory = factory
    return orchestrator, invoker


def _on_a_fresh_thread(work):
    """Run ``work(loop)`` on a new thread with its own new event loop."""
    outcome: dict = {}

    def run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            outcome["value"] = work(loop)
        except BaseException as exc:  # handed back to the test
            outcome["error"] = exc
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=60)
    assert not thread.is_alive(), "the loader thread did not finish"
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def test_the_autobuild_loader_reads_through_the_door(
    memory_env, tmp_path, refused_connections, store_never_opened, query_log
):
    with StandInDoor(THREE_ITEMS) as door:
        memory_env.setenv("FLEET_MEMORY_MCP_URL", door.url)
        factory = FleetMemoryClientFactory(fmc._load_fleet_config_from_env())
        orchestrator, _ = _orchestrator(tmp_path, factory)

        def work(loop):
            client = factory.get_thread_client()
            pending_before = client._pending_init
            loader = orchestrator._get_thread_local_loader(loop)
            result = None
            if loader is not None:
                result = loop.run_until_complete(
                    loader.get_player_context(
                        task_id="TASK-DOOR-001",
                        feature_id="FEAT-DOOR",
                        turn_number=1,
                        description="Count users per day",
                    )
                )
            healthy = loop.run_until_complete(client.health_check())
            loop.run_until_complete(client.close())
            return client, pending_before, loader, result, healthy

        client, pending_before, loader, result, healthy = _on_a_fresh_thread(work)

    assert pending_before is True
    assert loader is not None, orchestrator._thread_loader_skips
    assert client._pending_init is False
    assert result is not None and result.memory is not None
    assert result.memory.completed > 0 and result.memory.failed == 0
    assert result.memory.delivered > 0
    assert "Counting users per day worked with one grouped query." in result.prompt_text
    assert door.searches, "the loader's reads must have reached the door"
    assert healthy is True
    assert client._initialized is False
    assert store_never_opened == []
    assert refused_connections == []


def test_a_door_that_is_down_skips_the_loader(
    memory_env, tmp_path, refused_connections, store_never_opened, caplog
):
    memory_env.setenv("FLEET_MEMORY_MCP_URL", f"http://127.0.0.1:{_free_port()}/mcp")
    factory = FleetMemoryClientFactory(fmc._load_fleet_config_from_env())
    orchestrator, invoker = _orchestrator(tmp_path, factory)

    def work(loop):
        loader = orchestrator._get_thread_local_loader(loop)
        skip = orchestrator._thread_loader_skips.get(threading.get_ident())
        return loader, skip

    loader, skip = _on_a_fresh_thread(work)

    assert loader is None
    assert skip is not None and "connection failed" in skip[1]

    # The build carries on: a builder turn on this thread still runs.
    with caplog.at_level(logging.INFO, logger=AUTOBUILD):
        result = orchestrator._invoke_player_safely("TASK-DOOR-002", 1, "Count users.", None)
    assert result.success is True
    assert invoker.invoke_player.await_count == 1
    assert store_never_opened == []
    assert refused_connections == []


# ---------------------------------------------------------------------------
# 7. The stamp check reaches the model door with the placeholder
# ---------------------------------------------------------------------------


def test_the_stamp_check_goes_through_the_door_with_the_placeholder(monkeypatch):
    import guardkit.orchestrator.stamp_model_fallback as smf
    from guardkit.lib.client_env import API_KEY_ENV, BASE_URL_ENV

    answer = {"choices": [{"message": {"content": "toolchain"}}]}
    with StandInHttp(200, answer) as model_door:
        # The shared model address is the only one; the stamp check's own
        # setting is absent, not empty (empty would switch the check off).
        monkeypatch.delenv(smf.MODEL_URL_ENV, raising=False)
        monkeypatch.setenv(BASE_URL_ENV, f"http://127.0.0.1:{model_door.port}")
        monkeypatch.setenv(API_KEY_ENV, PLACEHOLDER_MODEL_KEY)
        monkeypatch.setenv(smf.MODEL_NAME_ENV, "a-stamp-model")

        asker = smf.build_default_asker()
        assert asker is not None
        reply = asker("Answer with one word.")

    assert reply == "toolchain"
    assert len(model_door.requests) == 1
    request = model_door.requests[0]
    assert request["method"] == "POST"
    assert request["path"].endswith("/chat/completions")
    assert request["authorization"] == f"Bearer {PLACEHOLDER_MODEL_KEY}"
