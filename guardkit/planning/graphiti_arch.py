"""
SystemPlanGraphiti: Graphiti read/write operations for /system-plan.

This module provides the persistence layer that bridges entity definitions
(Wave 1) with the interactive /system-plan command (Wave 3).

All operations use upsert_episode() (NOT add_episode()) for idempotent writes.
All operations use client.get_group_id() for correct project namespace prefixing.
All operations have graceful degradation (return None/[]/False on failure).
All log messages use [Graphiti] prefix for easy filtering.

Public API:
    SystemPlanGraphiti: Main class for Graphiti architecture operations

Example:
    from guardkit.planning.graphiti_arch import SystemPlanGraphiti
    from guardkit.knowledge.graphiti_client import get_graphiti

    client = get_graphiti()
    service = SystemPlanGraphiti(client=client, project_id="my-project")

    # Write operations
    uuid = await service.upsert_component(component)
    uuid = await service.upsert_adr(adr)
    uuid = await service.upsert_system_context(system_context)
    uuid = await service.upsert_crosscutting(concern)

    # Read operations
    has_context = await service.has_architecture_context()
    summary = await service.get_architecture_summary()
    facts = await service.get_relevant_context_for_topic("order processing", 10)
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.knowledge.graphiti_client import GraphitiClient
    from guardkit.knowledge.entities.component import ComponentDef
    from guardkit.knowledge.entities.system_context import SystemContextDef
    from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
    from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

logger = logging.getLogger(__name__)


class SystemPlanGraphiti:
    """Encapsulates all Graphiti read/write operations for /system-plan.

    This class provides the persistence layer for architecture entities,
    bridging entity definitions (Wave 1) with the interactive command (Wave 3).

    All write operations use upsert_episode() with stable entity_id values
    to enable idempotent updates. Group IDs are correctly prefixed using
    client.get_group_id() for project namespace isolation.

    Attributes:
        _client: GraphitiClient instance (may be None)
        _project_id: Project ID for namespace prefixing

    Example:
        client = get_graphiti()
        service = SystemPlanGraphiti(client=client, project_id="my-project")

        # Upsert a component
        uuid = await service.upsert_component(component)

        # Check if architecture context exists
        has_context = await service.has_architecture_context()

        # Search for relevant context
        facts = await service.get_relevant_context_for_topic("orders", 10)
    """

    # Group names for architecture entities
    ARCHITECTURE_GROUP = "project_architecture"
    DECISIONS_GROUP = "project_decisions"

    def __init__(
        self,
        client: Optional["GraphitiClient"],
        project_id: str,
    ) -> None:
        """Initialize SystemPlanGraphiti.

        Args:
            client: GraphitiClient instance. May be None for graceful degradation.
            project_id: Project ID for namespace prefixing in group IDs.
        """
        self._client = client
        self._project_id = project_id

    @property
    def _available(self) -> bool:
        """Check if Graphiti operations are available.

        Returns True only if client exists AND is enabled.

        Returns:
            True if client is available and enabled, False otherwise.
        """
        return self._client is not None and self._client.enabled

    async def upsert_component(
        self,
        component: "ComponentDef",
    ) -> Optional[str]:
        """Upsert a component definition to Graphiti.

        Uses upsert_episode() with the component's stable entity_id
        (format: COMP-{slug}) for idempotent updates.

        Args:
            component: ComponentDef instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.ARCHITECTURE_GROUP)
            episode_body = json.dumps(component.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"component_{component.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=component.entity_id,
                source="system_plan",
                entity_type=component.entity_type,
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert component {component.name}: {e}")
            return None

    async def upsert_adr(
        self,
        adr: "ArchitectureDecision",
    ) -> Optional[str]:
        """Upsert an Architecture Decision Record to Graphiti.

        Uses upsert_episode() with the ADR's stable entity_id
        (format: ADR-SP-NNN) for idempotent updates.

        Args:
            adr: ArchitectureDecision instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.DECISIONS_GROUP)
            episode_body = json.dumps(adr.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"adr_{adr.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=adr.entity_id,
                source="system_plan",
                entity_type="architecture_decision",
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert ADR {adr.entity_id}: {e}")
            return None

    async def upsert_system_context(
        self,
        system: "SystemContextDef",
    ) -> Optional[str]:
        """Upsert a system context definition to Graphiti.

        Uses upsert_episode() with the system's stable entity_id
        (format: SYS-{slug}) for idempotent updates.

        Args:
            system: SystemContextDef instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.ARCHITECTURE_GROUP)
            episode_body = json.dumps(system.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"system_{system.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=system.entity_id,
                source="system_plan",
                entity_type="system_context",
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert system context {system.name}: {e}")
            return None

    async def upsert_crosscutting(
        self,
        concern: "CrosscuttingConcernDef",
    ) -> Optional[str]:
        """Upsert a crosscutting concern definition to Graphiti.

        Uses upsert_episode() with the concern's stable entity_id
        (format: XC-{slug}) for idempotent updates.

        Args:
            concern: CrosscuttingConcernDef instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.ARCHITECTURE_GROUP)
            episode_body = json.dumps(concern.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"crosscutting_{concern.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=concern.entity_id,
                source="system_plan",
                entity_type="crosscutting_concern",
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert crosscutting concern {concern.name}: {e}")
            return None

    async def has_architecture_context(self) -> bool:
        """Quick check for whether architecture context exists.

        Used for mode detection in /system-plan command to determine
        whether to start in document mode or discovery mode.

        Returns:
            True if architecture context exists, False otherwise.
        """
        if not self._available:
            return False

        try:
            group_id = self._client.get_group_id(self.ARCHITECTURE_GROUP)

            results = await self._client.search(
                query="system context component architecture",
                group_ids=[group_id],
                num_results=1,
            )

            return len(results) > 0

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to check architecture context: {e}")
            return False

    async def get_architecture_summary(self) -> Optional[Dict[str, Any]]:
        """Retrieve architecture and decision facts summary.

        Searches for all architecture knowledge (components, system context,
        crosscutting concerns, and decisions) and returns a summary dict.

        Returns:
            Dict with 'facts' key containing list of facts, or None if
            no data found, disabled, or on error.
        """
        if not self._available:
            return None

        try:
            arch_group_id = self._client.get_group_id(self.ARCHITECTURE_GROUP)
            decisions_group_id = self._client.get_group_id(self.DECISIONS_GROUP)

            # Search for architecture facts and decisions
            results = await self._client.search(
                query="architecture component system context decision ADR",
                group_ids=[arch_group_id, decisions_group_id],
                num_results=20,
            )

            if not results:
                return None

            return {
                "facts": results,
            }

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to get architecture summary: {e}")
            return None

    async def get_relevant_context_for_topic(
        self,
        topic: str,
        num_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Semantic search for architecture context related to a topic.

        Searches both architecture and decisions groups for relevant
        facts based on the provided topic.

        Args:
            topic: Search topic/query string.
            num_results: Maximum number of results to return.

        Returns:
            List of dicts with 'fact', 'uuid', 'score' keys.
            Empty list if disabled, not found, or on error.
        """
        if not self._available:
            return []

        try:
            arch_group_id = self._client.get_group_id(self.ARCHITECTURE_GROUP)
            decisions_group_id = self._client.get_group_id(self.DECISIONS_GROUP)

            results = await self._client.search(
                query=topic,
                group_ids=[arch_group_id, decisions_group_id],
                num_results=num_results,
            )

            return results

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to get context for topic '{topic}': {e}")
            return []
