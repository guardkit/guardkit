"""Fleet-memory client adapter with graphiti-client-shaped interface.

This module provides a fleet-memory client whose public surface matches
the subset of the (now-removed) graphiti_client.py that call-sites were
written against — retained as intentional compat naming so existing
call-sites did not have to change during the FEAT-MEM-09 cutover.

Architecture:
- Reads: `memory_search` MCP tool (fleet-memory stdio server)
- Writes: `nats_core.publish_episode(MemoryEpisodeV1(...))` via NATS
- Mapping: group_id → (project, payload_type, domain_tags) via fleet_memory_mapping

Contract:
- search() returns same [{"fact": str, "uuid": str, "score": float}] shape
- add_episode() with unmapped/retired group_id is no-op returning None
- Factory returns the fleet-memory client unconditionally (FEAT-MEM-09 WS-2c
  retired the graphiti/dual routing + the `.guardkit/graphiti.yaml` reader)

See: TASK-MEM08-002
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Sequence
from uuid import uuid4

from guardkit.knowledge.memory_project import (
    MemoryProjectResolution,
    log_resolution,
    resolve_memory_project,
)

logger = logging.getLogger(__name__)

_SOURCE_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_HEADING_RE = re.compile(
    r"^[ \t]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*(?:\r?\n)?$"
)
_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})([^\r\n]*)")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_MAX_DOCUMENT_SOURCE_TAGS = 8
_MAX_DECLARED_DOCUMENT_BYTES = 256 * 1024
_MAX_SECTIONS_PER_DOCUMENT = 32
_MAX_SECTION_CANDIDATES = 64


def _query_terms(query: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(query)
        if len(token) >= 3
    }


def _split_markdown_heading_sections(body: str) -> list[dict[str, Any]]:
    """Return complete ATX-heading sections without splitting fenced code."""
    if len(body.encode("utf-8")) > _MAX_DECLARED_DOCUMENT_BYTES:
        return []
    lines = body.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []
    char_offset = 0
    fence_char: str | None = None
    fence_len = 0
    for line in lines:
        fence = _FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            suffix = fence.group(2)
            if fence_char is None:
                if marker[0] != "`" or "`" not in suffix:
                    fence_char, fence_len = marker[0], len(marker)
                    char_offset += len(line)
                    continue
            elif (
                marker[0] == fence_char
                and len(marker) >= fence_len
                and not suffix.strip()
            ):
                fence_char, fence_len = None, 0
                char_offset += len(line)
                continue
            elif fence_char is not None:
                char_offset += len(line)
                continue
        if fence_char is None:
            heading = _HEADING_RE.match(line)
            if heading:
                headings.append(
                    (char_offset, len(heading.group(1)), heading.group(2).strip())
                )
        char_offset += len(line)
    if fence_char is not None or not headings or len(headings) > _MAX_SECTIONS_PER_DOCUMENT:
        return []

    body_bytes = body.encode("utf-8")
    char_to_byte = [0]
    for char in body:
        char_to_byte.append(char_to_byte[-1] + len(char.encode("utf-8")))
    sections: list[dict[str, Any]] = []
    ancestry: list[tuple[int, str]] = []
    for index, (start_char, level, title) in enumerate(headings):
        end_char = headings[index + 1][0] if index + 1 < len(headings) else len(body)
        text = body[start_char:end_char]
        first_newline = text.find("\n")
        remainder = text[first_newline + 1 :] if first_newline >= 0 else ""
        while ancestry and ancestry[-1][0] >= level:
            ancestry.pop()
        ancestry.append((level, title))
        if not remainder.strip():
            continue
        start_byte, end_byte = char_to_byte[start_char], char_to_byte[end_char]
        assert body_bytes[start_byte:end_byte].decode("utf-8") == text
        sections.append(
            {
                "text": text,
                "start_byte": start_byte,
                "end_byte": end_byte,
                "heading_path": [name for _, name in ancestry],
            }
        )
    return sections


def _decode_declared_rule_document(raw: str, declared_tags: set[str]) -> dict[str, Any] | None:
    """Decode the canonical legacy rule envelope, failing closed."""
    if len(raw.encode("utf-8")) > _MAX_DECLARED_DOCUMENT_BYTES:
        return None
    try:
        outer = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(outer, dict):
        return None
    source_ref, domain_tags = outer.get("source_ref"), outer.get("domain_tags")
    if (
        not isinstance(source_ref, str)
        or source_ref not in declared_tags
        or not isinstance(domain_tags, list)
        or source_ref not in domain_tags
    ):
        return None
    inner_raw = outer.get("content")
    if not isinstance(inner_raw, str) or len(inner_raw.encode("utf-8")) > _MAX_DECLARED_DOCUMENT_BYTES:
        return None
    try:
        inner, end = json.JSONDecoder().raw_decode(inner_raw)
    except (json.JSONDecodeError, TypeError):
        return None
    metadata_match = re.fullmatch(
        r"\s*---\r?\n_metadata:\r?\n```json\r?\n(.*?)\r?\n```\s*",
        inner_raw[end:],
        flags=re.DOTALL,
    )
    if metadata_match is None:
        return None
    try:
        metadata = json.loads(metadata_match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(inner, dict) or not isinstance(metadata, dict):
        return None
    body = inner.get("content")
    if inner.get("entity_type") != "rule" or not isinstance(body, str) or not body.strip():
        return None
    return {
        "body": body,
        "source_ref": source_ref,
        "outer_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def _declared_rule_section_hits(
    results: Sequence[Any], query: str, declared_tags: Sequence[str], limit: int
) -> list[dict[str, Any]]:
    """Adapt declared rule documents into bounded provenance-bound sections."""
    query_terms, tags = _query_terms(query), set(declared_tags)
    candidates: list[tuple[float, int, int, int, dict[str, Any]]] = []
    for source_rank, item in enumerate(results[:10]):
        if not isinstance(item.value, dict):
            continue
        raw, natural_key = item.value.get("content"), item.value.get("natural_key")
        if not isinstance(raw, str) or not isinstance(natural_key, str) or not natural_key:
            continue
        decoded = _decode_declared_rule_document(raw, tags)
        if decoded is None:
            continue
        score = _safe_relevance_score(item.score)
        for section in _split_markdown_heading_sections(decoded["body"]):
            overlap = len(query_terms & _query_terms(section["text"]))
            hit = {
                "fact": section["text"],
                "uuid": natural_key,
                "score": score,
                "source_ref": decoded["source_ref"],
                "score_kind": "document",
                "outer_sha256": decoded["outer_sha256"],
                "body_sha256": decoded["body_sha256"],
                "section_sha256": hashlib.sha256(section["text"].encode("utf-8")).hexdigest(),
                "section_start_byte": section["start_byte"],
                "section_end_byte": section["end_byte"],
                "heading_path": section["heading_path"],
            }
            candidates.append((-score, -overlap, source_rank, section["start_byte"], hit))
            if len(candidates) >= _MAX_SECTION_CANDIDATES:
                break
        if len(candidates) >= _MAX_SECTION_CANDIDATES:
            break
    candidates.sort(key=lambda candidate: candidate[:4])
    return [candidate[4] for candidate in candidates[: min(10, limit)]]


def _safe_relevance_score(value: Any) -> float:
    """Return a finite source relevance score, or honest zero if malformed."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return score if math.isfinite(score) else 0.0


@dataclass
class FleetMemoryConfig:
    """Configuration for fleet-memory backend.

    Attributes:
        enabled: Whether fleet-memory backend is enabled
        postgres_dsn: PostgreSQL connection string for memory storage
        embed_url: Embedding service URL
        embed_model: Embedding model identifier
        embed_dims: Embedding vector dimensions
        nats_url: NATS server URL for episode writes
        project: The memory this build reads and writes — the middle segment of
            the store prefix ``fleet_memory.{project}.{payload_type}`` and the
            ``project`` component of every natural key. **There is no default**
            (2026-09-21): ``None`` means this build has no memory, so nothing is
            read and nothing is written, under any name. It used to default to
            ``"guardkit"``, which is why every project's build outcomes were
            filed under GuardKit's own name. The name comes from
            :func:`guardkit.knowledge.memory_project.resolve_memory_project`.
    """

    enabled: bool = False
    postgres_dsn: str = "postgresql://postgres:test@localhost:5433/memory"
    embed_url: str = "http://promaxgb10-41b1:9000/v1"
    embed_model: str = "nomic-embed"
    embed_dims: int = 768
    nats_url: str = "nats://localhost:4222"
    project: Optional[str] = None
    # New retrieval arm configuration (FEAT-ABL-001)
    retrieval_arm: Optional[str] = None
    fixture_id: Optional[str] = None


def _running_loop() -> "asyncio.AbstractEventLoop | None":
    """The event loop this call is running on, or None outside one.

    Used to keep the fleet-memory store with the loop it was opened on: the
    store is loop-affine and a cross-loop use fails in a way the search
    swallows, which reads downstream as an empty memory.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


#: The memory door: FastMCP over streamable HTTP, the same surface the seats
#: use when their native backend is missing. Named by the variable they already
#: read, so nobody has to learn a second one.
DOOR_URL_ENV = "FLEET_MEMORY_MCP_URL"
DEFAULT_DOOR_URL = "http://host.docker.internal:8005/mcp"

#: How long the door may take before the write is given up on. Well inside the
#: caller's own ceiling: a build's last line must not be held open.
DOOR_WRITE_TIMEOUT_SECONDS = 10.0


def _typed_door_payload(episode: Any) -> dict[str, Any]:
    """Return a fresh MCP payload carrying the episode's outer type identity.

    MemoryEpisodeV1.body contains the registered model fields while
    payload_type lives on the envelope. The MCP write boundary accepts one
    flat typed payload, so the HTTP fallback must join those two layers without
    mutating either. A body-supplied conflicting type is rejected rather than
    silently overwritten.
    """
    payload_type = getattr(episode, "payload_type", None)
    if (
        not isinstance(payload_type, str)
        or not payload_type
        or payload_type != payload_type.strip()
    ):
        raise ValueError("typed memory episode has no valid outer payload_type")

    try:
        body = json.loads(episode.body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("typed memory episode body is not valid JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("typed memory episode body is not a JSON object")

    body_type = body.get("payload_type")
    if "payload_type" in body and body_type != payload_type:
        raise ValueError("typed memory episode body conflicts with outer payload_type")

    payload = dict(body)
    payload["payload_type"] = payload_type
    return payload


async def write_through_the_door(payload: dict, *, url: str | None = None) -> bool:
    """Write one typed payload to fleet-memory over HTTP. True when it landed.

    WHY THIS EXISTS (2026-09-13). Builds run inside each repository's sandbox,
    and that sandbox enforces its network policy through an HTTP proxy: HTTP
    reaches the host, raw TCP does not. NATS is raw TCP, so the episode
    publisher's socket reaches the proxy and the broker's greeting never
    arrives — every build outcome since the sandbox-first move on 2026-09-07
    was published into a closed port, which is why the corpus stopped growing
    and why builders found nothing to read.

    The door is HTTP, is already allow-listed, and is already how the seats
    reach memory when their native backend is absent. So a write that cannot
    take the bus takes the door instead, and the payload is the SAME typed
    payload the relay would have written — this maps nothing and invents
    nothing.

    Never raises: a memory write must not be able to fail a build.
    """
    where = url or (os.getenv(DOOR_URL_ENV, "").strip() or DEFAULT_DOOR_URL)
    try:
        # Imported lazily, exactly as the seats do it, so this module still
        # loads where `mcp` is absent.
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def _send() -> bool:
            async with streamable_http_client(where) as streams:
                read, write = streams[0], streams[1]
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    # The tool's argument is ``payload``. Sending
                    # ``payload_dict`` (the underlying function's parameter
                    # name) returns a pydantic validation error as PLAIN TEXT
                    # with isError unset — which the first cut of this read as
                    # a successful write. Proven against the live door.
                    result = await session.call_tool(
                        "memory_write_payload", {"payload": payload}
                    )
            # POSITIVE EVIDENCE ONLY. A write is claimed when the door says
            # so, never when it says nothing or says something this cannot
            # read: the door reports an argument mismatch as plain text with
            # isError unset, and the first cut of this treated that as a
            # success and reported a write that never happened.
            if getattr(result, "isError", False):
                logger.warning("memory: the door refused the write")
                return False
            text = "".join(getattr(c, "text", "") for c in (result.content or []))
            if not text.strip():
                logger.warning(
                    "memory: the door answered the write with nothing at all, "
                    "so there is no evidence it landed; not claiming a write"
                )
                return False
            try:
                envelope = json.loads(text)
            except ValueError:
                logger.warning(
                    "memory: the door's answer could not be read as JSON, so "
                    "there is no evidence the write landed: %s",
                    text[:200],
                )
                return False
            if envelope.get("is_error") or envelope.get("error"):
                logger.warning(
                    "memory: the door refused the write: %s",
                    str(envelope.get("message") or envelope.get("error"))[:200],
                )
                return False
            return True

        return await asyncio.wait_for(_send(), timeout=DOOR_WRITE_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 — a write never costs a build
        logger.warning(
            "memory: could not write through the door at %s (%s); this "
            "build teaches future builds nothing",
            where,
            _what_actually_failed(exc),
        )
        return False


def _what_actually_failed(exc: BaseException) -> str:
    """The innermost reason, in words a person can act on.

    The MCP client runs inside an anyio task group, so every failure reaches
    the caller as ``ExceptionGroup: unhandled errors in a TaskGroup (1
    sub-exception)`` — which is true and says nothing. On 2026-09-13 the real
    reason was an HTTP 403 from the sandbox's network proxy, visible only in
    an httpx INFO line nobody reads. This walks to the leaves and names them,
    with the HTTP status when there is one.
    """
    leaves: list[str] = []

    def walk(e: BaseException) -> None:
        subs = getattr(e, "exceptions", None)
        if subs:
            for sub in subs:
                walk(sub)
            return
        text = f"{type(e).__name__}: {str(e)[:160]}"
        response = getattr(e, "response", None)
        status = getattr(response, "status_code", None)
        if status is not None:
            text = f"HTTP {status} — {text}"
        leaves.append(text)

    walk(exc)
    return "; ".join(leaves) if leaves else f"{type(exc).__name__}: {str(exc)[:160]}"


class FleetMemoryClient:
    supports_document_source_tags = True

    """Fleet-memory client with graphiti-client-shaped interface.

    Provides search() and add_episode() methods matching the subset
    of graphiti_client.GraphitiClient that existing call-sites use.

    Args:
        config: Fleet-memory configuration

    Example:
        >>> client = FleetMemoryClient(config)
        >>> hits = await client.search("task outcomes", group_ids=["task_outcomes"])
        >>> for hit in hits:
        ...     print(hit["fact"])
    """

    supports_substantive_search = True

    def __init__(self, config: FleetMemoryConfig):
        """Initialize fleet-memory client.

        Args:
            config: Fleet-memory configuration
        """
        self.config = config
        # Read path reuses fleet_memory.retrieval directly (the exact functions
        # the memory_search MCP tool wraps — single source of truth, no drift).
        # Installed via the guardkit `memory` extra. TASK-MEM08-011.
        self._store_loop = None  # the loop the store was opened on
        self._read_available = self._check_read_backend_available()
        self._mcp_available = self._read_available  # back-compat alias
        self._nats_available = self._check_nats_available()
        self._store: Any = None
        self._store_cm: Any = None
        self._initialized = False
        # Said once per client when something asks for memory without a name.
        self._said_no_memory_name: bool = False
        # TASK-FIX-GTP2/GLF-003 parity: the per-thread FleetMemoryClientFactory sets
        # this True when it creates a client inside a running loop, deferring the
        # asyncpg store connection to the consumer's event loop (loop-affinity). The
        # autobuild per-thread block (autobuild.py:5265-5267) initializes it there.
        self._pending_init: bool = False

    @property
    def enabled(self) -> bool:
        """Whether reads are enabled (FLEET_MEMORY_ENABLED)."""
        return bool(self.config.enabled)

    def _memory_named(self, about_to: str) -> bool:
        """Whether this build has a memory name, said once per client if not.

        WITHOUT A NAME NOTHING HAPPENS (2026-09-21). There is deliberately no
        fallback name: a build whose project said nothing reads nothing and
        writes nothing, rather than reading and writing under somebody else's
        records. The loud sentence naming the line to add is emitted where the
        name is resolved; this is the last gate before the store or the bus.
        """
        if self.config.project:
            return True
        if not self._said_no_memory_name:
            self._said_no_memory_name = True
            logger.warning(
                "memory: refusing to %s — this build has no memory name, so "
                "nothing is read and nothing is written. The project declares "
                "one with a `memory:` block carrying `project:` in its "
                ".guardkit/config.yaml.",
                about_to,
            )
        return False

    @property
    def is_initialized(self) -> bool:
        """Whether the store connection is open (graphiti-client parity).

        Mirrors ``GraphitiClient.is_initialized`` (``_connected and not
        _pending_init``) so the autobuild per-thread factory machinery
        (``autobuild.py:5265-5278``) can treat a FleetMemoryClient
        interchangeably with a GraphitiClient.
        """
        return self._initialized and not self._pending_init

    def reset_circuit_breaker(self) -> None:
        """No-op circuit-breaker reset (graphiti-client interface parity).

        GraphitiClient wraps FalkorDB access in a circuit breaker;
        fleet-memory reads hit Postgres directly with no breaker, so this is
        a documented no-op. ``JobContextRetriever`` calls this (hasattr-guarded)
        between queries; providing it explicitly future-proofs any non-guarded
        caller.
        """
        return None

    def _check_read_backend_available(self) -> bool:
        """Check the READ dependency: fleet_memory.retrieval importable.

        Reads reuse fleet-memory's retrieval surface (search + assemble_context),
        installed via the guardkit `memory` extra (editable ../fleet-memory
        sibling) — NOT nats_core, which is the write path. TASK-MEM08-011 / AC-3.

        Returns:
            True if fleet_memory.retrieval is importable, False otherwise.
        """
        try:
            import fleet_memory.retrieval  # noqa: F401

            return True
        except Exception:
            return False

    async def initialize(self) -> bool:
        """Open the fleet-memory store connection for reads.

        Builds a fleet_memory ``Settings`` from this client's config and enters
        ``async_store_context`` (connects to Postgres + configures embed-on-read).
        Idempotent; returns False (graceful) when disabled or the read backend is
        unavailable/unreachable.

        Returns:
            True if the store is ready, False otherwise.
        """
        if not self.config.enabled:
            return False
        if not self._memory_named("open the store"):
            return False
        if self._store is not None:
            # THE STORE IS AFFINE TO THE LOOP IT WAS OPENED ON (2026-09-13).
            # The line further down says so already — and until today nothing
            # checked it again. A store opened on one event loop and used from
            # another raises inside the batched store ("got Future attached to
            # a different loop", or "Event loop is closed" once the first loop
            # has gone), the search swallows it and returns [], and the build
            # reads that as an empty memory. Every build on 2026-09-12 and
            # 2026-09-13 ran with the builder and the reviewer having NO
            # memory for exactly this reason, while the store was reachable
            # and full the whole time.
            if self._store_loop is _running_loop():
                return True
            logger.info(
                "memory: the store was opened on a different event loop; "
                "opening it again for this one (the store is loop-affine)"
            )
            # The old context manager belongs to a loop that may be closed, so
            # it cannot be exited from here. Dropping the reference is the
            # honest thing available; the connection goes with its loop.
            self._store = None
            self._store_cm = None
        if not self._read_available:
            logger.warning(
                "fleet_memory.retrieval not importable; install the guardkit "
                "`memory` extra (editable ../fleet-memory). Reads disabled."
            )
            return False
        try:
            from fleet_memory.settings import Settings
            from fleet_memory.store import async_store_context

            settings = Settings(
                pg_dsn=self.config.postgres_dsn,
                embed_url=self.config.embed_url,
                embed_model=self.config.embed_model,
                embed_dims=self.config.embed_dims,
                nats_url=self.config.nats_url,
            )
            self._store_cm = async_store_context(settings)
            self._store = await self._store_cm.__aenter__()
            self._store_loop = _running_loop()  # remembered, and checked above
            self._initialized = True
            self._pending_init = False  # store now affine to the calling loop
            return True
        except Exception as e:
            logger.warning(f"Fleet-memory initialize failed: {e}", exc_info=True)
            self._store = None
            self._store_cm = None
            self._store_loop = None
            return False

    async def health_check(self) -> bool:
        """Confirm the live store is reachable via a trivial real read.

        Returns:
            True if a store read completes (connection healthy), False otherwise.
        """
        # Not just "is there a store" but "is it THIS loop's store" — a
        # stale one from another loop never reaches initialize() otherwise,
        # and every read through it comes back empty (2026-09-13).
        if (
            self._store is None
            # A store whose loop was never recorded is one we cannot JUDGE,
            # and re-opening on that would churn the connection on every
            # call. The defect this guard exists for always records the loop
            # — initialize() sets both together — so "unknown" is left alone
            # and only a KNOWN foreign loop forces a re-open (2026-09-14:
            # the first form failed eleven tests that hand the client a
            # store directly, and would have re-opened on every call in any
            # code that did the same).
            or (
                self._store_loop is not None
                and self._store_loop is not _running_loop()
            )
        ) and not await self.initialize():
            return False
        try:
            await self._store.aget(
                ("fleet_memory", self.config.project, "chunk"), "__healthcheck__"
            )
            return True
        except Exception as e:
            logger.debug(f"Fleet-memory health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close the fleet-memory store connection (idempotent)."""
        if self._store_cm is not None:
            try:
                await self._store_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._store_cm = None
        self._store = None
        self._initialized = False

    def _check_nats_available(self) -> bool:
        """Check if nats_core module is available for writes.

        Returns:
            True if nats_core is importable, False otherwise
        """
        try:
            import nats_core  # noqa: F401

            return True
        except ImportError:
            return False

    async def search(
        self,
        query: str,
        group_ids: Optional[list[str]] = None,
        num_results: int = 10,
        scope: Optional[str] = None,
        require_substantive: bool = False,
        document_source_tags: Optional[Sequence[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search fleet-memory for relevant knowledge.

        Calls fleet-memory search(project, query, payload_types, domain_tags,
        token_budget) and adapts each result into the graphiti-shaped
        {"fact": str, "uuid": str, "score": float} hits that readers expect.

        Args:
            query: Search query string
            group_ids: Optional list of group IDs to search. Maps to payload_types
                      and domain_tags via fleet_memory_mapping.
            num_results: Requested number of results (used for token_budget)
            scope: Optional scope filter (not used by fleet-memory)

        Returns:
            List of dicts with keys: fact, uuid, score. Empty list on error
            or when fleet-memory is not available.

        Example:
            >>> hits = await client.search("autobuild outcomes",
            ...                            group_ids=["task_outcomes"])
            >>> hits[0]["fact"]
            "TASK-X completed with 80% coverage..."
        """
        if not self.config.enabled:
            return []
        if not self._memory_named("search memory"):
            return []
        if self.config.retrieval_arm == "off":
            # Retrieval ablation arm gate (FEAT-ABL-001 / TASK-ABL1-003): mirror
            # the enabled=false gate exactly — no store access, no initialize(),
            # no retrieval-log entry — so the context loader, turn-continuation
            # and template-pattern paths run byte-identical code on every arm.
            logger.debug("Fleet-memory retrieval arm 'off': returning empty")
            return []
        if not self._read_available:
            logger.debug("fleet_memory.retrieval unavailable, returning empty")
            return []

        from guardkit.knowledge.fleet_memory_mapping import resolve

        declared_scope = document_source_tags is not None
        if declared_scope and (
            isinstance(document_source_tags, (str, bytes))
            or not isinstance(document_source_tags, Sequence)
        ):
            logger.warning(
                "Fleet-memory invalid document source tag scope; returning empty"
            )
            return []
        declared_tags = tuple(document_source_tags or ())
        invalid_declared_tags = any(
            not isinstance(tag, str) or not _SOURCE_TAG_RE.fullmatch(tag)
            for tag in declared_tags
        )
        if declared_scope and (
            group_ids
            or not 1 <= len(declared_tags) <= _MAX_DOCUMENT_SOURCE_TAGS
            or invalid_declared_tags
            or len(set(declared_tags)) != len(declared_tags)
        ):
            logger.warning(
                "Fleet-memory invalid document source tag scope; returning empty"
            )
            return []

        # An explicitly scoped read must never degrade into a whole-corpus
        # search. Retired and unknown Graphiti groups have no Fleet identity;
        # treating their empty mapping as an unscoped request let unrelated
        # build outcomes populate policy-specific context sections. A genuinely
        # unscoped call (None or []) still intentionally searches the corpus.
        migrated_mappings = []
        if group_ids and not declared_tags:
            migrated_mappings = [
                mapping
                for gid in group_ids
                if (mapping := resolve(gid)) is not None
                and mapping.disposition == "migrate"
            ]
            if not migrated_mappings:
                logger.debug(
                    "Fleet-memory scoped search has no migrated groups: returning empty"
                )
                return []

        # Lazy-open the store on first read (GROI readers do not call initialize()).
        # Not just "is there a store" but "is it THIS loop's store" — a
        # stale one from another loop never reaches initialize() otherwise,
        # and every read through it comes back empty (2026-09-13).
        if (
            self._store is None
            # A store whose loop was never recorded is one we cannot JUDGE,
            # and re-opening on that would churn the connection on every
            # call. The defect this guard exists for always records the loop
            # — initialize() sets both together — so "unknown" is left alone
            # and only a KNOWN foreign loop forces a re-open (2026-09-14:
            # the first form failed eleven tests that hand the client a
            # store directly, and would have re-opened on every call in any
            # code that did the same).
            or (
                self._store_loop is not None
                and self._store_loop is not _running_loop()
            )
        ) and not await self.initialize():
            return []

        try:
            from fleet_memory.retrieval import SearchRequest, search as fm_search

            # Resolve group_ids -> payload_types / domain_tags (migrate only).
            # Explicit retired/unknown-only scopes returned above. Mixed scopes use
            # only their migrated mappings; only None/[] remains an unscoped search.
            payload_types: set[str] = set()
            domain_tags: set[str] = set()
            for mapping in migrated_mappings:
                payload_types.add(mapping.payload_type)
                # Migrated Graphiti prose (FEAT-MEM-09 graph_export) lands as typed
                # `document` records carrying the group's domain_tags. Include
                # "document" so a group-scoped read matches BOTH the live typed
                # records (build_outcome/adr/warning) AND the migrated documents;
                # the domain_tags filter below does the precise per-group scoping.
                payload_types.add("document")
                domain_tags.update(mapping.domain_tags)

            if declared_tags:
                payload_types = {"document"}
                domain_tags = set(declared_tags)

            token_budget = max(2000, num_results * 200)

            # Reuse fleet-memory's REAL retrieval surface — the exact functions the
            # memory_search MCP tool wraps (single source of truth, no drift).
            request = SearchRequest(
                project=self.config.project,
                query=query,
                payload_types=sorted(payload_types),
                domain_tags=sorted(domain_tags),
                token_budget=token_budget,
                include_superseded=False,
                require_substantive=require_substantive,
            )
            results = await fm_search(request, self._store)

            # Per-item retrieval log (FEAT-ABL-001 / TASK-ABL1-003). Emitted HERE
            # where the source natural_key and semantic relevance score are intact.
            # Written on EVERY successful
            # fm_search return, including empty results (items=[]), so the run
            # guardrail can distinguish "retrieval attempted, nothing found"
            # (entry with empty items) from "no retrieval" (no entry). A failed
            # fm_search raises into the except below and writes nothing.
            # log_query never raises by contract.
            from guardkit.knowledge.query_logger import log_query

            first_preview: Optional[str] = None
            if results:
                first_content = results[0].value.get("content")
                if isinstance(first_content, str) and first_content:
                    first_preview = first_content
            log_query(
                operation="search",
                query=query,
                group_ids=group_ids or [],
                result_count=len(results),
                first_result_preview=first_preview,
                source="fleet_memory_client",
                items=[
                    {
                        "id": item.value.get("natural_key", ""),
                        "score": _safe_relevance_score(item.score),
                    }
                    for item in results
                ],
            )

            # Preserve the graphiti-shaped *per-result* contract expected by
            # JobContextRetriever.  Fleet's assembly.coverage_score is a budget-fill
            # fraction, not semantic relevance; using it as ``score`` caused valid
            # results to fail the retriever's relevance threshold.  Returning the
            # actual result granularity also lets the caller enforce each category's
            # own token allocation instead of accepting or dropping one large block.
            limit = max(0, num_results)
            if limit == 0:
                return []
            if declared_tags:
                return _declared_rule_section_hits(
                    results, query, declared_tags, limit
                )

            hits: list[dict[str, Any]] = []
            for item in results:
                if not isinstance(item.value, dict):
                    continue
                content = item.value.get("content")
                if not isinstance(content, str) or not content:
                    continue

                score = _safe_relevance_score(item.score)

                natural_key = item.value.get("natural_key")
                hits.append(
                    {
                        "fact": content,
                        "uuid": (
                            natural_key
                            if isinstance(natural_key, str) and natural_key
                            else str(uuid4())
                        ),
                        "score": score,
                    }
                )
                if len(hits) >= limit:
                    break

            return hits

        except Exception as e:
            # Loud, and named for what it costs: a swallowed search reads
            # downstream as "the memory is empty", which is how every build
            # this week ran blind without anybody being told.
            logger.error(
                "memory: the search FAILED and this turn will therefore see no "
                "memory at all — this is not an empty memory, it is a broken "
                "read (%s: %s)",
                type(e).__name__,
                e,
                exc_info=True,
            )
            return []

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        source: str = "user_added",
        entity_type: str = "generic",
        scope: Optional[str] = None,
        metadata: Optional[Any] = None,
        timeout_override: Optional[float] = None,
        dedup_token: Optional[str] = None,
    ) -> Optional[str]:
        """Publish an episode to fleet-memory via NATS (typed payload, fail-open).

        Resolves ``group_id`` via ``fleet_memory_mapping``, builds a typed
        ``MemoryEpisodeV1`` whose JSON body matches the relay's payload registry
        (``fleet_memory_payloads.build_memory_episode``), and publishes it as the
        provisioned ``guardkit`` NATS user — reusing the harvest publisher's
        connect + 900KB-guard + idempotent path (single source of truth for guardkit's
        NATS writes).

        Graceful degradation: returns ``None`` (never raises into the caller's task flow)
        when the group is unmapped/retired, ``nats_core`` is unavailable, the episode
        cannot be built, or the publish fails (e.g. ``GUARDKIT_NATS_PASSWORD`` unset).

        Args:
            name: Episode name (carries the task/ADR id, e.g. "OUT-..: TASK-1234 - title").
            episode_body: Episode content — a ``json.dumps(dict)`` string from the call sites.
            group_id: Graphiti group identifier to resolve to a fleet-memory payload type.
            source: Episode source label (default: "user_added").
            entity_type: Accepted for interface parity (unused by fleet-memory).
            scope: Accepted for interface parity (unused).
            metadata: Accepted for interface parity (unused).
            timeout_override: Accepted for interface parity (unused).
            dedup_token: Per-WRITE uniquifier for the broker's duplicate window.
                When given, the published copy carries
                ``Nats-Msg-Id = "{natural_key}.{dedup_token}"`` so a second write
                for the same task is not silently swallowed by JetStream's
                duplicate window (the natural key alone is per-task, so it was).
                The payload — and therefore the store's upsert key — is
                untouched, so latest-write-wins in the store is unchanged; see
                ``fleet_memory_payloads.with_broker_dedup_scope``. Callers must
                compute it ONCE per write so a retry inside that write still
                dedupes. Omit it for writes that SHOULD collapse by natural key
                (the harvest re-runs).

        Returns:
            The natural key (``"{payload_type}:{project}:{identifier}"``) on a successful
            publish, else ``None`` — the unscoped key, not the scoped message id.

            THIS IS NOT A STORE RECEIPT. The key is computed LOCALLY by
            ``build_memory_episode`` (which sets ``episode.episode_id`` to it)
            before anything is sent, and the send itself is core NATS with no
            JetStream ack — ``NATSClient.publish_episode`` calls
            ``nc.publish(...)`` and returns. So a non-``None`` return means the
            bytes left this process, and a dark relay, an unmapped or full
            stream, and a relay-side validation refusal all return it too.
            Callers must say "published", never "stored"; store-side landing is
            fleet-memory's liveness fence's question.

        Example:
            >>> key = await client.add_episode(
            ...     name="OUT-1A2B: TASK-1234 - Implement OAuth2",
            ...     episode_body=json.dumps(outcome.to_episode_body()),
            ...     group_id="task_outcomes",
            ... )  # -> "build_outcome:guardkit:TASK_1234"
        """
        if not self._memory_named("write to memory"):
            return None
        try:
            # Resolve group_id to fleet-memory identity
            from guardkit.knowledge.fleet_memory_mapping import resolve

            mapping = resolve(group_id)

            # Unmapped or retired group → fail-open no-op
            if mapping is None or mapping.disposition == "retire":
                logger.debug(f"Group {group_id!r} unmapped or retired, skipping write")
                return None

            if not self._nats_available:
                logger.warning(
                    f"nats_core not available, cannot write {group_id!r} episode"
                )
                return None

            # Build the typed MemoryEpisodeV1 (body shaped for the relay's registry).
            from guardkit.knowledge.fleet_memory_payloads import build_memory_episode

            episode = build_memory_episode(
                mapping,
                name=name,
                episode_body=episode_body,
                source=source,
                project=self.config.project,
            )
            if episode is None:
                logger.warning(
                    f"Could not build fleet-memory episode for {group_id!r} ({name!r})"
                )
                return None

            # Publish as the guardkit NATS user (reuses the harvest connect + guard path).
            from guardkit.knowledge.fleet_memory_payloads import (
                with_broker_dedup_scope,
            )
            from guardkit.memory.harvest_publisher import publish_episodes

            # The natural key is what the caller gets back and what the store
            # upserts on. The PUBLISHED copy may carry a per-write message id so
            # a rebuild inside the broker's duplicate window is not dropped —
            # the two ids are deliberately different things.
            natural_key = episode.episode_id
            published_episode = with_broker_dedup_scope(episode, dedup_token or "")

            try:
                summary = await publish_episodes([published_episode])
            except Exception as bus_refused:  # noqa: BLE001
                # THE BUS IS NOT ALWAYS REACHABLE (2026-09-13). Inside a
                # repository's sandbox the network policy is an HTTP proxy, and
                # NATS is raw TCP, so this is the ordinary case there rather
                # than an exceptional one. Say so once and take the door.
                logger.info(
                    "memory: the bus did not carry episode %s (%s) — trying "
                    "the door",
                    natural_key,
                    type(bus_refused).__name__,
                )
                if await write_through_the_door(_typed_door_payload(episode)):
                    logger.info(
                        "[Memory] Wrote %s episode %s through the door",
                        mapping.payload_type,
                        natural_key,
                    )
                    return natural_key
                return None

            if summary.published >= 1:
                logger.info(
                    "[Memory] Published %s episode %s to fleet-memory",
                    mapping.payload_type,
                    natural_key,
                )
                return natural_key

            logger.warning(
                "[Memory] Episode %s not published "
                "(published=%d, skipped_oversized=%d) — trying the door",
                natural_key,
                summary.published,
                summary.skipped_oversized,
            )
            if await write_through_the_door(_typed_door_payload(episode)):
                logger.info(
                    "[Memory] Wrote %s episode %s through the door",
                    mapping.payload_type,
                    natural_key,
                )
                return natural_key
            return None

        except Exception as e:
            # Fail-open: a memory write must never break the caller's task flow.
            logger.warning(
                f"Fleet-memory add_episode failed for {group_id!r}: {e}", exc_info=True
            )
            return None


class FleetMemoryClientFactory:
    """Thread-safe factory for per-thread FleetMemoryClient instances.

    Mirrors ``graphiti_client.GraphitiClientFactory``: stores one shared config
    and hands out a distinct client per thread via ``threading.local()``. This
    is REQUIRED (not merely convenient) for parallel autobuild waves — the
    fleet-memory store is a Postgres/asyncpg connection opened by
    ``FleetMemoryClient.initialize()`` and is bound to the event loop that opens
    it, exactly like the FalkorDB locks the graphiti factory was built for
    (TASK-FIX-GTP2 / TASK-GLF-003). A single shared client cannot be reused
    across the per-thread loops that ``FeatureOrchestrator`` creates.

    The client's store connection is always deferred (``_pending_init = True``)
    so the consumer initializes it on its own event loop
    (``autobuild.py:5265-5278``), keeping the asyncpg connection loop-affine.

    Attributes:
        config: FleetMemoryConfig instance (shared across threads).
    """

    def __init__(self, config: FleetMemoryConfig):
        self._config = config
        self._thread_local = threading.local()

    @property
    def config(self) -> FleetMemoryConfig:
        """Get the shared configuration."""
        return self._config

    def create_client(self) -> FleetMemoryClient:
        """Create a new uninitialized FleetMemoryClient.

        The caller is responsible for calling ``await client.initialize()`` in
        the appropriate async context.
        """
        return FleetMemoryClient(self._config)

    def get_thread_client(self) -> Optional[FleetMemoryClient]:
        """Get or lazily create a client for the current thread.

        Uses ``threading.local()`` for automatic per-thread storage. On first
        access in a thread, creates a client with a deferred store connection
        (``_pending_init = True``) so the consumer initializes it on its own
        event loop. Returns None when the backend is disabled.
        """
        client = getattr(self._thread_local, "client", None)
        if client is not None:
            return client

        if getattr(self._thread_local, "init_attempted", False):
            return None
        self._thread_local.init_attempted = True

        if not self._config.enabled:
            # LOUD by design (2026-08-03 reconnection): the info-level version
            # of this line hid a month of memory-dark factory builds. A run
            # without memory is acceptable; a run that hides it is not.
            logger.warning(
                "memory: OFF — FLEET_MEMORY_ENABLED is unset/false; this run "
                "reads no prior decisions and writes no outcomes. Set "
                "FLEET_MEMORY_ENABLED=true and FLEET_MEMORY_PG_DSN to enable."
            )
            return None

        if not self._config.project:
            # NO NAME, NO CLIENT (2026-09-21). Every thread of this build asks
            # here, so refusing here is what makes "nothing is read and nothing
            # is written" true for the whole build rather than one code path.
            # The sentence saying which line to add to which file was already
            # emitted once, where the name was resolved.
            logger.warning(
                "memory: OFF — this build has no memory name, so no thread gets "
                "a memory client: this run reads no prior decisions and writes "
                "no outcomes, and nothing is read or written under any other "
                "name. The project declares its name with a `memory:` block "
                "carrying `project:` in its .guardkit/config.yaml."
            )
            return None

        client = self.create_client()
        # Always defer the asyncpg store connection to the consumer's event loop
        # (the store is loop-affine — TASK-GLF-003). Never connect on the
        # factory-calling thread's loop.
        client._pending_init = True
        self._thread_local.client = client
        logger.info(
            "memory: ON (project=%s) — thread client created (pending init — "
            "will initialize lazily on the consumer's event loop)",
            self._config.project,
        )
        return client

    def set_thread_client(self, client: Optional[FleetMemoryClient]) -> None:
        """Explicitly set the client for the current thread (testing / DI parity)."""
        self._thread_local.client = client
        self._thread_local.init_attempted = True


# Module-level factory state
_memory_client: Optional[FleetMemoryClient | Any] = None
_memory_factory: Optional[FleetMemoryClientFactory] = None
# FEAT-MEM-09 WS-2c: fleet-memory is the only backend. The graphiti/dual routing
# and the .guardkit/graphiti.yaml ``backend:`` flag reader were retired.
_backend: Literal["fleet_memory"] = "fleet_memory"
# Whether the backend has been initialized (explicitly via init_memory_client, or
# lazily on first get_memory_client). Guards the one-time auto-init so an explicit
# init always wins and tests that set state directly are not disrupted.
_backend_initialized: bool = False
# THE ONE SHARED NAME FOR THIS PROCESS (2026-09-21). Resolved once — by
# ``configure_memory_project`` at the start of a build, or lazily from the
# current folder when GuardKit is used by hand — and then handed to every
# config, so the builder thread and the reviewer thread cannot end up reading
# and writing under different names.
_memory_project_resolution: Optional[MemoryProjectResolution] = None
# Settling the name, and discarding what was built under an older one, is one
# step. A parallel wave builds its orchestrators in threads, each of which calls
# ``configure_memory_project`` on the way up, so without this lock two of them
# can be half-way through that step at once and leave a torn factory behind.
_memory_project_lock = threading.Lock()


def configure_memory_project(
    project_root: Optional[Path],
) -> MemoryProjectResolution:
    """Settle which memory this build uses, before any thread gets a client.

    Called at the start of a build with the folder the build works in. Says the
    answer out loud — including, when there is no name, the two lines to add and
    the file to add them to.

    When the answer is the one already settled, nothing else is touched: a
    parallel wave builds every orchestrator against the same folder, so every
    call after the first is a restatement, and throwing away the shared client
    and factory each time would only rebuild them under the same name. When the
    answer really is different, anything built under the earlier one is dropped
    so nothing can keep using a stale name.

    Returns the resolution, so the caller can record what was decided.
    """
    global _memory_project_resolution, _memory_client, _memory_factory
    global _backend_initialized

    resolution = resolve_memory_project(project_root)
    log_resolution(resolution)
    with _memory_project_lock:
        if _memory_project_resolution == resolution:
            # Same answer as the one already settled: change nothing.
            return resolution
        _memory_project_resolution = resolution
        # Anything built under an earlier answer is discarded, config and all.
        _memory_client = None
        _memory_factory = None
        _backend_initialized = False
    return resolution


def memory_project_resolution() -> MemoryProjectResolution:
    """The settled answer for this process, resolving it now if nothing has.

    The lazy path is GuardKit used by hand, with nobody to hand a name over: it
    reads the declaration in the current folder. It is said out loud once.
    """
    global _memory_project_resolution
    if _memory_project_resolution is None:
        resolution = resolve_memory_project(Path.cwd())
        log_resolution(resolution)
        _memory_project_resolution = resolution
    return _memory_project_resolution


def reset_memory_project() -> None:
    """Forget the settled answer (tests, and a process that changes projects)."""
    global _memory_project_resolution
    _memory_project_resolution = None


def _ensure_backend_initialized() -> None:
    """Lazily initialize the fleet-memory backend on first use (idempotent).

    Called by ``get_memory_client`` / ``get_memory_factory`` so every call site honours
    the fleet-memory backend without each needing to call ``init_memory_client``
    explicitly. A prior explicit ``init_memory_client`` sets ``_backend_initialized``
    and short-circuits.
    """
    global _backend_initialized
    if _backend_initialized:
        return
    init_memory_client()  # sets _backend_initialized = True


def init_memory_client(
    backend: str = "fleet_memory",
    fleet_config: Optional[FleetMemoryConfig] = None,
    graphiti_config: Optional[Any] = None,
) -> bool:
    """Initialize the fleet-memory client factory.

    FEAT-MEM-09 WS-2c: fleet-memory is the only backend. The ``backend`` and
    ``graphiti_config`` parameters are retained for backwards compatibility and
    are ignored.

    Args:
        backend: Deprecated / ignored (fleet-memory is always used).
        fleet_config: Fleet-memory configuration; loaded from env when None.
        graphiti_config: Deprecated / ignored.

    Returns:
        True if initialization succeeded, False otherwise.

    Example:
        >>> init_memory_client(fleet_config=FleetMemoryConfig())
        True
    """
    global _memory_client, _memory_factory, _backend, _backend_initialized

    _backend = "fleet_memory"
    # An explicit init wins over (and disables) lazy auto-init.
    _backend_initialized = True
    # Drop any per-thread factory built for a prior config.
    _memory_factory = None

    try:
        if fleet_config is None:
            fleet_config = _load_fleet_config_from_env()
        _memory_client = FleetMemoryClient(fleet_config)
        return True
    except Exception as e:
        logger.error(f"Memory client initialization failed: {e}", exc_info=True)
        return False


def get_memory_client() -> Optional[FleetMemoryClient | Any]:
    """Get the fleet-memory client.

    Fleet-memory is the only backend post-cutover (FEAT-MEM-09); returns the
    singleton ``FleetMemoryClient`` (lazily initialized on first use).

    Returns:
        FleetMemoryClient instance, or None if not initialized

    Example:
        >>> client = get_memory_client()
        >>> if client:
        ...     hits = await client.search("query")
    """
    global _memory_client

    # First call (no explicit init): lazily initialize the fleet-memory backend.
    _ensure_backend_initialized()

    return _memory_client


def get_memory_factory() -> Optional[FleetMemoryClientFactory]:
    """Get a per-thread fleet-memory client factory.

    Hands out per-thread clients so parallel autobuild waves don't share a
    loop-affine store. Encapsulates the one-time backend initialization (via
    ``_ensure_backend_initialized``). Fleet-memory is the only backend
    post-cutover (FEAT-MEM-09).

    Returns:
        FleetMemoryClientFactory.
    """
    global _memory_factory

    _ensure_backend_initialized()

    if _memory_factory is None:
        # Reuse the singleton client's config (single source of truth) when the
        # fleet backend is active; else load from env.
        config = getattr(_memory_client, "config", None)
        if config is None:
            config = _load_fleet_config_from_env()
        _memory_factory = FleetMemoryClientFactory(config)
    return _memory_factory


def _load_fleet_config_from_env() -> FleetMemoryConfig:
    """Load fleet-memory config from environment variables.

    Returns:
        FleetMemoryConfig loaded from environment
    """
    # Default postgres DSN (live)
    enabled = os.getenv("FLEET_MEMORY_ENABLED", "false").lower() == "true"
    if enabled and not os.getenv("FLEET_MEMORY_PG_DSN"):
        # The code default below is a trap on this estate: localhost:5433 is a
        # TEST Postgres with no "memory" database, so an enabled-but-DSN-less
        # run times out and degrades to empty context looking exactly like
        # memory working with nothing to say (2026-08-03 audit, live-fired).
        logger.warning(
            "memory: FLEET_MEMORY_ENABLED is true but FLEET_MEMORY_PG_DSN is "
            "unset — falling back to the localhost:5433 code default, which is "
            "almost certainly NOT the fleet store. Set FLEET_MEMORY_PG_DSN."
        )
    default_postgres_dsn = os.getenv(
        "FLEET_MEMORY_PG_DSN",
        "postgresql://postgres:test@localhost:5433/memory",
    )
    # Parse retrieval arm
    raw_retrieval = os.getenv("FLEET_MEMORY_RETRIEVAL")
    retrieval_arm: Optional[str] = None
    fixture_id: Optional[str] = None
    if raw_retrieval is None or raw_retrieval.strip() == "":
        retrieval_arm = None
    else:
        val = raw_retrieval.strip().lower()
        if val == "off":
            retrieval_arm = "off"
        elif val.startswith("fixture:"):
            fid = raw_retrieval.strip()[len("fixture:"):]
            if fid:
                retrieval_arm = f"fixture:{fid}"
                fixture_id = fid
            else:
                logger.warning(f"Invalid FLEET_MEMORY_RETRIEVAL value: {raw_retrieval!r}")
                retrieval_arm = "off"
        else:
            logger.warning(f"Invalid FLEET_MEMORY_RETRIEVAL value: {raw_retrieval!r}")
            retrieval_arm = "off"
    # Resolve fixture DSN if needed
    if retrieval_arm and retrieval_arm.startswith("fixture:"):
        # Uppercase id, map non-alnum to _
        import re
        norm_id = re.sub(r"[^0-9A-Za-z]", "_", fixture_id.upper()) if fixture_id else ""
        env_var_specific = f"FLEET_MEMORY_FIXTURE_DSN_{norm_id}"
        dsn = os.getenv(env_var_specific) or os.getenv("FLEET_MEMORY_FIXTURE_DSN")
        if dsn:
            postgres_dsn = dsn
        else:
            logger.warning(f"Fixture DSN not set for retrieval arm {retrieval_arm!r}")
            retrieval_arm = "off"
            postgres_dsn = default_postgres_dsn
    else:
        postgres_dsn = default_postgres_dsn
    return FleetMemoryConfig(
        enabled=os.getenv("FLEET_MEMORY_ENABLED", "false").lower() == "true",
        postgres_dsn=postgres_dsn,
        embed_url=os.getenv(
            "FLEET_MEMORY_EMBED_URL",
            "http://promaxgb10-41b1:9000",
        ),
        # Defaults match the live deployment (Qwen3-Embedding-0.6B @ 1024 dims).
        # A wrong default silently mis-embeds against the rebuilt corpus and
        # corrupts retrieval (TASK-MEM08-011 / AC-4).
        embed_model=os.getenv("FLEET_MEMORY_EMBED_MODEL", "embed"),
        embed_dims=int(os.getenv("FLEET_MEMORY_EMBED_DIMS", "1024")),
        nats_url=os.getenv("FLEET_MEMORY_NATS_URL", "nats://localhost:4222"),
        # WHICH MEMORY THIS BUILD USES (2026-09-21). One answer for the whole
        # process: a name handed over on purpose, else the project's own
        # declaration, else None — which means memory is off and nothing is read
        # or written. There is no default name here any more; the old
        # "guardkit" default is why every project's outcomes were filed under
        # GuardKit's name.
        project=memory_project_resolution().project,
        retrieval_arm=retrieval_arm,
        fixture_id=fixture_id,
    )
