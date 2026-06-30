"""Fleet-memory client adapter with graphiti-client-shaped interface.

This module provides a fleet-memory client whose public surface matches
the subset of graphiti_client.py that call-sites use, enabling swapable
backends via config flag.

Architecture:
- Reads: `memory_search` MCP tool (fleet-memory stdio server)
- Writes: `nats_core.publish_episode(MemoryEpisodeV1(...))` via NATS
- Mapping: group_id → (project, payload_type, domain_tags) via fleet_memory_mapping

Contract:
- search() returns same [{"fact": str, "uuid": str, "score": float}] shape
- add_episode() with unmapped/retired group_id is no-op returning None
- Factory routes graphiti vs fleet_memory vs dual purely from config

See: TASK-MEM08-002
"""

from __future__ import annotations

import asyncio
import logging
import os
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
    """

    enabled: bool = False
    postgres_dsn: str = "postgresql://postgres:test@localhost:5433/memory"
    embed_url: str = "http://promaxgb10-41b1:9000/v1"
    embed_model: str = "nomic-embed"
    embed_dims: int = 768
    nats_url: str = "nats://localhost:4222"


class DualWriteClient:
    """Dual-write client that writes to both Graphiti and fleet-memory.

    Under `backend=dual`, writes go to both Graphiti (authoritative) and
    fleet-memory. Graphiti failures propagate; fleet-memory failures are
    logged but do not fail the operation (graceful degradation).

    Args:
        graphiti_client: GraphitiClient instance
        fleet_client: FleetMemoryClient instance

    Example:
        >>> from guardkit.knowledge.graphiti_client import get_graphiti
        >>> dual = DualWriteClient(get_graphiti(), FleetMemoryClient(config))
        >>> await dual.add_episode(name="...", episode_body="...", group_id="task_outcomes")
    """

    def __init__(self, graphiti_client: Any, fleet_client: "FleetMemoryClient"):
        """Initialize dual-write client.

        Args:
            graphiti_client: GraphitiClient instance (authoritative)
            fleet_client: FleetMemoryClient instance (secondary)
        """
        self.graphiti_client = graphiti_client
        self.fleet_client = fleet_client

    @property
    def enabled(self) -> bool:
        """Check if client is enabled (delegates to Graphiti)."""
        return self.graphiti_client.enabled if self.graphiti_client else False

    async def search(
        self,
        query: str,
        group_ids: Optional[list[str]] = None,
        num_results: int = 10,
        scope: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search for knowledge (delegates to Graphiti for now).

        Reads are not yet migrated to fleet-memory, so this delegates
        to Graphiti.

        Args:
            query: Search query string
            group_ids: Optional list of group IDs to search
            num_results: Maximum number of results
            scope: Optional scope filter

        Returns:
            List of search results from Graphiti
        """
        if self.graphiti_client is None:
            return []
        return await self.graphiti_client.search(
            query=query,
            group_ids=group_ids,
            num_results=num_results,
            scope=scope,
        )

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
        """Add episode to both Graphiti and fleet-memory.

        Writes to Graphiti first (authoritative). If successful, also
        writes to fleet-memory (fail-open). Retired groups skip
        fleet-memory write.

        Args:
            name: Episode name
            episode_body: Episode content
            group_id: Graphiti group identifier
            source: Episode source
            entity_type: Entity type
            scope: Optional scope
            metadata: Optional metadata
            timeout_override: Optional timeout

        Returns:
            Graphiti UUID if successful, None if Graphiti write failed

        Raises:
            Exception: If Graphiti write fails (it's authoritative)
        """
        # Write to Graphiti first (authoritative)
        graphiti_uuid = await self.graphiti_client.add_episode(
            name=name,
            episode_body=episode_body,
            group_id=group_id,
            source=source,
            entity_type=entity_type,
            scope=scope,
            metadata=metadata,
            timeout_override=timeout_override,
        )

        # Check if group should be written to fleet-memory
        from guardkit.knowledge.fleet_memory_mapping import resolve

        mapping = resolve(group_id)

        # Skip fleet-memory for retired or unmapped groups
        if mapping is None or mapping.disposition == "retire":
            logger.debug(
                f"Group {group_id!r} retired/unmapped, skipping fleet-memory write"
            )
            return graphiti_uuid

        # Write to fleet-memory (fail-open - don't propagate errors)
        try:
            await self.fleet_client.add_episode(
                name=name,
                episode_body=episode_body,
                group_id=group_id,
                source=source,
                entity_type=entity_type,
                scope=scope,
                metadata=metadata,
                timeout_override=timeout_override,
            )
            logger.info(f"Dual-write to fleet-memory succeeded for {group_id!r}")
        except Exception as e:
            # Log but don't fail - Graphiti is authoritative
            logger.warning(
                f"Fleet-memory write failed for {group_id!r}: {e} "
                "(Graphiti write succeeded, continuing)"
            )

        return graphiti_uuid


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

    @property
    def enabled(self) -> bool:
        """Whether reads are enabled (FLEET_MEMORY_ENABLED)."""
        return bool(self.config.enabled)

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
            await self._store.aget(("fleet_memory", "guardkit", "chunk"), "__healthcheck__")
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
                    domain_tags.update(mapping.domain_tags)

            token_budget = max(2000, num_results * 200)

            # Reuse fleet-memory's REAL retrieval surface — the exact functions the
            # memory_search MCP tool wraps (single source of truth, no drift).
            request = SearchRequest(
                project="guardkit",
                query=query,
                payload_types=sorted(payload_types),
                domain_tags=sorted(domain_tags),
                token_budget=token_budget,
                include_superseded=False,
            )
            results = await fm_search(request, self._store)
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
                mapping, name=name, episode_body=episode_body, source=source
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


# Module-level factory state
_memory_client: Optional[FleetMemoryClient | Any] = None
_backend: Literal["graphiti", "fleet_memory", "dual"] = "graphiti"
# Whether the backend has been initialized (explicitly via init_memory_client, or
# lazily from config on first get_memory_client). Guards the one-time auto-init so an
# explicit init always wins and tests that set _backend directly are not disrupted.
_backend_initialized: bool = False


def _resolve_backend_from_config() -> Literal["graphiti", "fleet_memory", "dual"]:
    """Resolve the memory backend from configuration.

    Precedence: ``GUARDKIT_MEMORY_BACKEND`` env var → ``.guardkit/graphiti.yaml``
    ``backend:`` key → ``"graphiti"`` (back-compat default). This is the producer the
    FEAT-MEM-08 cutover needs: 009 flipped ``backend: fleet_memory`` in the YAML, but
    without something reading it the flag is inert and every call routes to graphiti.
    """
    env = os.getenv("GUARDKIT_MEMORY_BACKEND")
    if env:
        env = env.strip().lower()
        if env in ("graphiti", "fleet_memory", "dual"):
            return env  # type: ignore[return-value]
        logger.warning("Ignoring invalid GUARDKIT_MEMORY_BACKEND=%r", env)
    try:
        from guardkit.knowledge.config import get_config_path
        import yaml

        config_path = get_config_path()
        if config_path.exists():
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}
            backend = str(data.get("backend", "graphiti")).strip().lower()
            if backend in ("graphiti", "fleet_memory", "dual"):
                return backend  # type: ignore[return-value]
            logger.warning("Ignoring invalid backend %r in %s", backend, config_path)
    except Exception as e:  # pragma: no cover - config read is best-effort
        logger.debug("Could not resolve backend from config: %s", e)
    return "graphiti"


def _ensure_backend_initialized() -> None:
    """Lazily initialize the backend from config on first use (idempotent).

    Called by ``get_memory_client`` so every call site (readers and writers) honours the
    configured backend without each needing to call ``init_memory_client`` explicitly.
    A prior explicit ``init_memory_client`` sets ``_backend_initialized`` and short-circuits.
    """
    global _backend_initialized
    if _backend_initialized:
        return
    backend = _resolve_backend_from_config()
    init_memory_client(backend=backend)  # sets _backend_initialized = True


def init_memory_client(
    backend: Literal["graphiti", "fleet_memory", "dual"] = "graphiti",
    fleet_config: Optional[FleetMemoryConfig] = None,
    graphiti_config: Optional[Any] = None,
) -> bool:
    """Initialize memory client factory.

    Sets the global backend routing and initializes the appropriate
    client(s) based on configuration.

    Args:
        backend: Backend to use (graphiti | fleet_memory | dual)
        fleet_config: Fleet-memory configuration (required if backend != graphiti)
        graphiti_config: Graphiti configuration (required if backend != fleet_memory)

    Returns:
        True if initialization succeeded, False otherwise

    Example:
        >>> init_memory_client(backend="fleet_memory",
        ...                    fleet_config=FleetMemoryConfig())
        True
    """
    global _memory_client, _backend, _backend_initialized

    _backend = backend
    # An explicit init wins over (and disables) lazy config-driven auto-init.
    _backend_initialized = True

    try:
        if backend == "graphiti":
            # Use existing graphiti client
            from guardkit.knowledge.graphiti_client import (
                init_graphiti,
            )

            # Note: init_graphiti is async, would need to handle that
            _memory_client = None  # Lazy init via get_memory_client()
            return True

        elif backend == "fleet_memory":
            # Initialize fleet-memory client
            if fleet_config is None:
                fleet_config = _load_fleet_config_from_env()
            _memory_client = FleetMemoryClient(fleet_config)
            return True

        elif backend == "dual":
            # Initialize both clients (dual-write mode)
            from guardkit.knowledge.graphiti_client import get_graphiti

            graphiti_client = get_graphiti()
            if graphiti_client is None:
                logger.error("Cannot initialize dual mode: Graphiti client unavailable")
                return False

            if fleet_config is None:
                fleet_config = _load_fleet_config_from_env()

            fleet_client = FleetMemoryClient(fleet_config)
            _memory_client = DualWriteClient(graphiti_client, fleet_client)
            logger.info("Dual-write mode initialized (Graphiti + fleet-memory)")
            return True

        else:
            logger.error(f"Unknown backend: {backend!r}")
            return False

    except Exception as e:
        logger.error(f"Memory client initialization failed: {e}", exc_info=True)
        return False


def get_memory_client() -> Optional[FleetMemoryClient | Any]:
    """Get memory client for current backend.

    Returns the appropriate client based on the configured backend:
    - graphiti: Returns GraphitiClient
    - fleet_memory: Returns FleetMemoryClient
    - dual: Returns DualWriteClient (future)

    Returns:
        Memory client instance, or None if not initialized

    Example:
        >>> client = get_memory_client()
        >>> if client:
        ...     hits = await client.search("query")
    """
    global _memory_client, _backend

    # First call (no explicit init): select the backend from config (the cutover flag).
    _ensure_backend_initialized()

    if _backend == "graphiti":
        # Lazy init graphiti if needed
        if _memory_client is None:
            from guardkit.knowledge.graphiti_client import get_graphiti

            _memory_client = get_graphiti()
        return _memory_client

    elif _backend == "fleet_memory":
        return _memory_client

    elif _backend == "dual":
        return _memory_client

    return None


def _load_fleet_config_from_env() -> FleetMemoryConfig:
    """Load fleet-memory config from environment variables.

    Returns:
        FleetMemoryConfig loaded from environment
    """
    return FleetMemoryConfig(
        enabled=os.getenv("FLEET_MEMORY_ENABLED", "false").lower() == "true",
        postgres_dsn=os.getenv(
            "FLEET_MEMORY_PG_DSN",
            "postgresql://postgres:test@localhost:5433/memory",
        ),
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
    )
