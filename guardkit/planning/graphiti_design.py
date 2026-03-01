"""
SystemDesignGraphiti: Graphiti read/write operations for /system-design.

This module provides the persistence layer for design entities
(DesignDecision, ApiContract, DataModel) used by the /system-design
and /design-refine commands.

All operations use upsert_episode() (NOT add_episode()) for idempotent writes.
All operations use client.get_group_id() for correct project namespace prefixing.
All operations have graceful degradation (return None/[]/False on failure).
All log messages use [Graphiti] prefix for easy filtering.

Public API:
    SystemDesignGraphiti: Main class for Graphiti design operations

Example:
    from guardkit.planning.graphiti_design import SystemDesignGraphiti
    from guardkit.knowledge.graphiti_client import get_graphiti

    client = get_graphiti()
    service = SystemDesignGraphiti(client=client, project_id="my-project")

    # Write operations
    uuid = await service.upsert_design_decision(decision)
    uuid = await service.upsert_api_contract(contract)
    uuid = await service.upsert_data_model(model)

    # Read operations
    has_context = await service.has_design_context()
    results = await service.search_design_context("order processing", 5)
    decisions = await service.get_design_decisions()
    contracts = await service.get_api_contracts()
"""

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from guardkit.knowledge.graphiti_client import GraphitiClient
    from guardkit.knowledge.entities.design_decision import DesignDecision
    from guardkit.knowledge.entities.api_contract import ApiContract
    from guardkit.knowledge.entities.data_model import DataModel

logger = logging.getLogger(__name__)


class SystemDesignGraphiti:
    """Encapsulates all Graphiti read/write operations for /system-design.

    This class provides the persistence layer for design entities,
    bridging entity definitions (Wave 1) with the interactive
    /system-design and /design-refine commands (Wave 3+).

    All write operations use upsert_episode() with stable entity_id values
    to enable idempotent updates. Group IDs are correctly prefixed using
    client.get_group_id() for project namespace isolation.

    Attributes:
        _client: GraphitiClient instance (may be None)
        _project_id: Project ID for namespace prefixing

    Example:
        client = get_graphiti()
        service = SystemDesignGraphiti(client=client, project_id="my-project")

        # Upsert a design decision
        uuid = await service.upsert_design_decision(decision)

        # Check if design context exists
        has_context = await service.has_design_context()

        # Search for relevant context
        facts = await service.search_design_context("CQRS pattern", 10)
    """

    # Group names for design entities
    DESIGN_GROUP = "project_design"
    CONTRACTS_GROUP = "api_contracts"

    def __init__(
        self,
        client: Optional["GraphitiClient"],
        project_id: str,
    ) -> None:
        """Initialize SystemDesignGraphiti.

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

    async def upsert_design_decision(
        self,
        decision: "DesignDecision",
    ) -> Optional[str]:
        """Upsert a Design Decision Record (DDR) to Graphiti.

        Uses upsert_episode() with the decision's stable entity_id
        (format: DDR-{NNN}) for idempotent updates.

        Args:
            decision: DesignDecision instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.DESIGN_GROUP)
            episode_body = json.dumps(decision.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"ddr_{decision.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=decision.entity_id,
                source="system_design",
                entity_type="design_decision",
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert design decision {decision.entity_id}: {e}")
            return None

    async def upsert_api_contract(
        self,
        contract: "ApiContract",
    ) -> Optional[str]:
        """Upsert an API contract definition to Graphiti.

        Uses upsert_episode() with the contract's stable entity_id
        (format: API-{bounded_context_slug}) for idempotent updates.

        Args:
            contract: ApiContract instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.CONTRACTS_GROUP)
            episode_body = json.dumps(contract.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"api_{contract.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=contract.entity_id,
                source="system_design",
                entity_type="api_contract",
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert API contract {contract.entity_id}: {e}")
            return None

    async def upsert_data_model(
        self,
        model: "DataModel",
    ) -> Optional[str]:
        """Upsert a data model definition to Graphiti.

        Uses upsert_episode() with the model's stable entity_id
        (format: DM-{bounded_context_slug}) for idempotent updates.

        Args:
            model: DataModel instance to upsert.

        Returns:
            Episode UUID if successful, None on failure or if disabled.
        """
        if not self._available:
            return None

        try:
            group_id = self._client.get_group_id(self.DESIGN_GROUP)
            episode_body = json.dumps(model.to_episode_body())

            result = await self._client.upsert_episode(
                name=f"dm_{model.entity_id}",
                episode_body=episode_body,
                group_id=group_id,
                entity_id=model.entity_id,
                source="system_design",
                entity_type="data_model",
            )

            if result is not None:
                return result.uuid
            return None

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to upsert data model {model.entity_id}: {e}")
            return None

    async def search_design_context(
        self,
        query: str,
        num_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic search for design context related to a query.

        Searches both design and contracts groups for relevant
        facts based on the provided query.

        Args:
            query: Search query string.
            num_results: Maximum number of results to return.

        Returns:
            List of dicts with 'fact', 'uuid', 'score' keys.
            Empty list if disabled, not found, or on error.
        """
        if not self._available:
            return []

        try:
            design_group_id = self._client.get_group_id(self.DESIGN_GROUP)
            contracts_group_id = self._client.get_group_id(self.CONTRACTS_GROUP)

            results = await self._client.search(
                query=query,
                group_ids=[design_group_id, contracts_group_id],
                num_results=num_results,
            )

            return results

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to search design context for '{query}': {e}")
            return []

    async def has_design_context(self) -> bool:
        """Quick check for whether design context exists.

        Used for mode detection in /system-design command to determine
        whether to start in document mode or discovery mode.

        Returns:
            True if design context exists, False otherwise.
        """
        if not self._available:
            return False

        try:
            group_id = self._client.get_group_id(self.DESIGN_GROUP)

            results = await self._client.search(
                query="design decision API contract data model",
                group_ids=[group_id],
                num_results=1,
            )

            return len(results) > 0

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to check design context: {e}")
            return False

    async def get_design_decisions(self) -> List[Dict[str, Any]]:
        """Retrieve all design decision facts.

        Searches the project_design group for design decision
        related knowledge.

        Returns:
            List of dicts with design decision facts.
            Empty list if disabled, not found, or on error.
        """
        if not self._available:
            return []

        try:
            group_id = self._client.get_group_id(self.DESIGN_GROUP)

            results = await self._client.search(
                query="design decision DDR rationale alternatives",
                group_ids=[group_id],
                num_results=20,
            )

            return results

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to get design decisions: {e}")
            return []

    async def get_api_contracts(self) -> List[Dict[str, Any]]:
        """Retrieve all API contract facts.

        Searches the api_contracts group for API contract
        related knowledge.

        Returns:
            List of dicts with API contract facts.
            Empty list if disabled, not found, or on error.
        """
        if not self._available:
            return []

        try:
            group_id = self._client.get_group_id(self.CONTRACTS_GROUP)

            results = await self._client.search(
                query="API contract endpoint protocol consumer",
                group_ids=[group_id],
                num_results=20,
            )

            return results

        except Exception as e:
            logger.warning(f"[Graphiti] Failed to get API contracts: {e}")
            return []
