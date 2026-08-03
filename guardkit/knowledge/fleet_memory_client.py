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
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any, Literal, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


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
        project: Fleet-memory project namespace for reads/writes. The middle segment
            of the store prefix ``fleet_memory.{project}.{payload_type}`` and the
            ``project`` component of every natural key. Defaults to ``"guardkit"``
            (single-project back-compat); FEAT-MEM-09 WS-0 makes it per-project.
    """

    enabled: bool = False
    postgres_dsn: str = "postgresql://postgres:test@localhost:5433/memory"
    embed_url: str = "http://promaxgb10-41b1:9000/v1"
    embed_model: str = "nomic-embed"
    embed_dims: int = 768
    nats_url: str = "nats://localhost:4222"
    project: str = "guardkit"
    # New retrieval arm configuration (FEAT-ABL-001)
    retrieval_arm: Optional[str] = None
    fixture_id: Optional[str] = None


class FleetMemoryClient:
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

    def __init__(self, config: FleetMemoryConfig):
        """Initialize fleet-memory client.

        Args:
            config: Fleet-memory configuration
        """
        self.config = config
        # Read path reuses fleet_memory.retrieval directly (the exact functions
        # the memory_search MCP tool wraps — single source of truth, no drift).
        # Installed via the guardkit `memory` extra. TASK-MEM08-011.
        self._read_available = self._check_read_backend_available()
        self._mcp_available = self._read_available  # back-compat alias
        self._nats_available = self._check_nats_available()
        self._store: Any = None
        self._store_cm: Any = None
        self._initialized = False
        # TASK-FIX-GTP2/GLF-003 parity: the per-thread FleetMemoryClientFactory sets
        # this True when it creates a client inside a running loop, deferring the
        # asyncpg store connection to the consumer's event loop (loop-affinity). The
        # autobuild per-thread block (autobuild.py:5265-5267) initializes it there.
        self._pending_init: bool = False

    @property
    def enabled(self) -> bool:
        """Whether reads are enabled (FLEET_MEMORY_ENABLED)."""
        return bool(self.config.enabled)

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
        if self._store is not None:
            return True
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
            self._initialized = True
            self._pending_init = False  # store now affine to the calling loop
            return True
        except Exception as e:
            logger.warning(f"Fleet-memory initialize failed: {e}", exc_info=True)
            self._store = None
            self._store_cm = None
            return False

    async def health_check(self) -> bool:
        """Confirm the live store is reachable via a trivial real read.

        Returns:
            True if a store read completes (connection healthy), False otherwise.
        """
        if self._store is None and not await self.initialize():
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
    ) -> list[dict[str, Any]]:
        """Search fleet-memory for relevant knowledge.

        Calls memory_search(project, query, payload_types, domain_tags, token_budget)
        and adapts the single context_block response into the graphiti-shaped
        [{"fact": str, "uuid": str, "score": float}] list that readers expect.

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

        # Lazy-open the store on first read (GROI readers do not call initialize()).
        if self._store is None and not await self.initialize():
            return []

        try:
            from fleet_memory.retrieval import (
                SearchRequest,
                assemble_context,
                search as fm_search,
            )
            from guardkit.knowledge.fleet_memory_mapping import resolve

            # Resolve group_ids -> payload_types / domain_tags (migrate only).
            # Unmapped / retired group_ids leave the filters empty, which searches
            # ALL payload types (e.g. the harvested `chunk` corpus).
            payload_types: set[str] = set()
            domain_tags: set[str] = set()
            for gid in group_ids or []:
                mapping = resolve(gid)
                if mapping and mapping.disposition == "migrate":
                    payload_types.add(mapping.payload_type)
                    # Migrated Graphiti prose (FEAT-MEM-09 graph_export) lands as typed
                    # `document` records carrying the group's domain_tags. Include
                    # "document" so a group-scoped read matches BOTH the live typed
                    # records (build_outcome/adr/warning) AND the migrated documents;
                    # the domain_tags filter below does the precise per-group scoping.
                    payload_types.add("document")
                    domain_tags.update(mapping.domain_tags)

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
            )
            results = await fm_search(request, self._store)

            # Per-item retrieval log (FEAT-ABL-001 / TASK-ABL1-003). Emitted HERE
            # because per-item identity (natural_key + score) only exists between
            # fm_search() and assemble_context() — assembly collapses everything
            # into the one synthetic uuid4 hit below. Written on EVERY successful
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
                        "score": float(item.score or 0.0),
                    }
                    for item in results
                ],
            )

            assembly = assemble_context(results, token_budget)

            if not assembly.context_block:
                return []

            # Adapt the assembled context block to the graphiti-shaped hit the GROI
            # readers expect: [{fact, uuid, score}].
            return [
                {
                    "fact": assembly.context_block,
                    "uuid": str(uuid4()),
                    "score": float(assembly.coverage_score),
                }
            ]

        except Exception as e:
            logger.error(f"Fleet-memory search failed: {e}", exc_info=True)
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

        Returns:
            The natural key (``"{payload_type}:{project}:{identifier}"``) on a successful
            publish, else ``None``.

        Example:
            >>> key = await client.add_episode(
            ...     name="OUT-1A2B: TASK-1234 - Implement OAuth2",
            ...     episode_body=json.dumps(outcome.to_episode_body()),
            ...     group_id="task_outcomes",
            ... )  # -> "build_outcome:guardkit:TASK_1234"
        """
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
            from guardkit.memory.harvest_publisher import publish_episodes

            summary = await publish_episodes([episode])
            if summary.published >= 1:
                logger.info(
                    "[Memory] Published %s episode %s to fleet-memory",
                    mapping.payload_type,
                    episode.episode_id,
                )
                return episode.episode_id

            logger.warning(
                "[Memory] Episode %s not published "
                "(published=%d, skipped_oversized=%d)",
                episode.episode_id,
                summary.published,
                summary.skipped_oversized,
            )
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
        # Per-project scoping (FEAT-MEM-09 WS-0): the fleet-memory namespace this
        # guardkit instance reads/writes. Defaults to "guardkit" (back-compat).
        project=os.getenv("GUARDKIT_MEMORY_PROJECT", "guardkit"),
        retrieval_arm=retrieval_arm,
        fixture_id=fixture_id,
    )
