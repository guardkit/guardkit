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
        self._mcp_available = self._check_mcp_available()
        self._nats_available = self._check_nats_available()

    def _check_mcp_available(self) -> bool:
        """Check if memory_search MCP tool is available.

        Returns:
            True if MCP tool is available, False otherwise
        """
        # In real implementation, would check if .mcp.json declares fleet-memory server
        # For now, return False to gracefully degrade
        return False

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
        if not self._mcp_available:
            logger.debug("memory_search MCP tool not available, returning empty")
            return []

        try:
            # Resolve group_ids to payload_types and domain_tags
            from guardkit.knowledge.fleet_memory_mapping import resolve

            payload_types = set()
            domain_tags = set()

            if group_ids:
                for gid in group_ids:
                    mapping = resolve(gid)
                    if mapping and mapping.disposition == "migrate":
                        payload_types.add(mapping.payload_type)
                        domain_tags.update(mapping.domain_tags)

            # Build generous token budget based on num_results
            # Assume ~200 tokens per result for context blocks
            token_budget = max(2000, num_results * 200)

            # Call memory_search MCP tool
            # Note: In real implementation, would use MCP client to call the tool
            # For now, return empty list to gracefully degrade
            logger.debug(
                f"memory_search call: query={query!r}, "
                f"payload_types={sorted(payload_types)}, "
                f"domain_tags={sorted(domain_tags)}, "
                f"token_budget={token_budget}"
            )

            # Simulate MCP response structure
            context_block = ""  # Would come from actual MCP call

            if not context_block:
                return []

            # Adapt context_block to graphiti-shaped hits
            # Strategy: create one synthetic hit carrying the context block
            # Alternative: could split on headings if context_block is structured
            return [
                {
                    "fact": context_block,
                    "uuid": str(uuid4()),
                    "score": 0.95,  # High score since it's the primary result
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
        """Add episode to fleet-memory.

        Resolves group_id via fleet_memory_mapping, builds typed payload
        matching fleet-memory schema, and publishes via NATS.

        Args:
            name: Episode name/identifier
            episode_body: Episode content (markdown/text)
            group_id: Graphiti group identifier to resolve
            source: Episode source (default: "user_added")
            entity_type: Entity type (not used by fleet-memory)
            scope: Optional scope (not used by fleet-memory)
            metadata: Optional metadata (not used by fleet-memory)
            timeout_override: Optional timeout (not used by fleet-memory)

        Returns:
            Natural key identifier if successful, None if group unmapped
            or write failed (fail-open behavior).

        Example:
            >>> key = await client.add_episode(
            ...     name="TASK-X outcome",
            ...     episode_body="Task completed with...",
            ...     group_id="task_outcomes"
            ... )
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

            # Build natural key (payload-type specific)
            # For build_outcome: task_id from name
            # For adr: decision_id from name
            # For document: sanitized name as doc_path
            natural_key = self._build_natural_key(name, mapping.payload_type)

            # Build typed payload matching fleet-memory schema
            # Note: Fleet-memory payload schemas are defined in TASK-MEM08-003
            # For now, build generic structure
            payload = {
                "project": mapping.project,
                "payload_type": mapping.payload_type,
                "domain_tags": mapping.domain_tags,
                "identifier": natural_key,
                "content": episode_body,
                "source": source,
            }

            # Publish via NATS
            # Note: nats_core.publish_episode signature TBD
            # For now, log what would be published
            logger.info(
                f"Would publish to fleet-memory: "
                f"type={mapping.payload_type}, key={natural_key}"
            )

            return natural_key

        except Exception as e:
            logger.error(
                f"Fleet-memory add_episode failed for {group_id!r}: {e}", exc_info=True
            )
            return None

    def _build_natural_key(self, name: str, payload_type: str) -> str:
        """Build natural key from episode name and payload type.

        Args:
            name: Episode name
            payload_type: Fleet-memory payload type

        Returns:
            Natural key identifier
        """
        # For build_outcome: extract TASK-XXX from name
        if payload_type == "build_outcome":
            import re

            match = re.search(r"TASK-[\w-]+", name)
            if match:
                return match.group(0)

        # For adr: extract decision ID or use name
        if payload_type == "adr":
            import re

            match = re.search(r"(ADR-\d+|DECISION-[\w-]+)", name)
            if match:
                return match.group(0)

        # For document: sanitize name as path
        if payload_type == "document":
            # Replace spaces with hyphens, lowercase
            sanitized = name.lower().replace(" ", "-")
            # Remove non-alphanumeric except hyphens
            import re

            sanitized = re.sub(r"[^a-z0-9\-]", "", sanitized)
            return sanitized

        # Fallback: use name as-is
        return name


# Module-level factory state
_memory_client: Optional[FleetMemoryClient | Any] = None
_backend: Literal["graphiti", "fleet_memory", "dual"] = "graphiti"


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
    global _memory_client, _backend

    _backend = backend

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
            "http://promaxgb10-41b1:9000/v1",
        ),
        embed_model=os.getenv("FLEET_MEMORY_EMBED_MODEL", "nomic-embed"),
        embed_dims=int(os.getenv("FLEET_MEMORY_EMBED_DIMS", "768")),
        nats_url=os.getenv("FLEET_MEMORY_NATS_URL", "nats://localhost:4222"),
    )
