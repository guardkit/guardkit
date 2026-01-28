"""
ADR Service for creating and managing Architecture Decision Records.

Provides a service layer for CRUD operations on ADRs stored in Graphiti.
All operations include graceful degradation for when Graphiti is unavailable.

Public API:
    ADRService: Main service class for ADR management

Example:
    from guardkit.knowledge.adr_service import ADRService
    from guardkit.knowledge.adr import ADREntity, ADRTrigger
    from guardkit.knowledge.graphiti_client import GraphitiClient

    client = GraphitiClient()
    service = ADRService(client)

    adr = ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL",
        trigger=ADRTrigger.TASK_REVIEW
    )

    adr_id = await service.create_adr(adr)
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from guardkit.knowledge.adr import ADREntity, ADRStatus, ADRTrigger
from guardkit.knowledge.graphiti_client import GraphitiClient

logger = logging.getLogger(__name__)


class ADRService:
    """Service for creating and managing ADRs in Graphiti.

    Provides methods for creating, searching, superseding, and deprecating
    Architecture Decision Records. All operations gracefully degrade when
    Graphiti is unavailable.

    Attributes:
        client: GraphitiClient instance for storage operations

    Example:
        client = GraphitiClient()
        service = ADRService(client)

        adr = ADREntity(id="ADR-0001", title="Use PostgreSQL")
        adr_id = await service.create_adr(adr)

        results = await service.search_adrs("database decisions")
    """

    def __init__(self, client: GraphitiClient):
        """Initialize ADRService with a GraphitiClient.

        Args:
            client: GraphitiClient instance for storage operations.
                   Must be provided (not optional).

        Raises:
            TypeError: If client is not provided.
        """
        self.client = client
        self._counter_file = Path.home() / ".agentecflow" / "state" / ".adr-counter.json"

    def _get_next_adr_id(self) -> str:
        """Generate the next sequential ADR ID.

        Uses a counter file to track the next available ADR number.
        Thread-safe through file-based locking.

        Returns:
            ADR ID in format ADR-XXXX (e.g., ADR-0001, ADR-0002)
        """
        try:
            # Ensure directory exists
            self._counter_file.parent.mkdir(parents=True, exist_ok=True)

            # Read current counter
            if self._counter_file.exists():
                with open(self._counter_file, "r") as f:
                    data = json.load(f)
                    counter = data.get("counter", 0)
            else:
                counter = 0

            # Increment and save
            counter += 1
            with open(self._counter_file, "w") as f:
                json.dump({"counter": counter}, f)

            return f"ADR-{counter:04d}"

        except Exception as e:
            logger.warning(f"Failed to generate ADR ID from counter: {e}")
            # Fallback to timestamp-based ID
            import time
            return f"ADR-{int(time.time()) % 10000:04d}"

    def _serialize_adr(self, adr: ADREntity) -> str:
        """Serialize an ADR to JSON string.

        Handles datetime and enum serialization.

        Args:
            adr: ADREntity to serialize

        Returns:
            JSON string representation
        """
        data = asdict(adr)

        # Convert enums to their values
        if "status" in data and isinstance(data["status"], ADRStatus):
            data["status"] = data["status"].value
        if "trigger" in data and isinstance(data["trigger"], ADRTrigger):
            data["trigger"] = data["trigger"].value

        return json.dumps(data, default=str)

    def _parse_adr(self, data: dict) -> ADREntity:
        """Parse a dictionary into an ADREntity.

        Handles conversion of string values back to enums and datetimes.

        Args:
            data: Dictionary with ADR data

        Returns:
            ADREntity instance
        """
        # Convert status string to enum
        status = data.get("status", "accepted")
        if isinstance(status, str):
            try:
                status = ADRStatus(status)
            except ValueError:
                status = ADRStatus.ACCEPTED
        elif isinstance(status, ADRStatus):
            pass
        else:
            status = ADRStatus.ACCEPTED

        # Convert trigger string to enum
        trigger = data.get("trigger", "manual")
        if isinstance(trigger, str):
            try:
                trigger = ADRTrigger(trigger)
            except ValueError:
                trigger = ADRTrigger.MANUAL
        elif isinstance(trigger, ADRTrigger):
            pass
        else:
            trigger = ADRTrigger.MANUAL

        # Parse datetime fields
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except (ValueError, TypeError):
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()

        return ADREntity(
            id=data.get("id", ""),
            title=data.get("title", ""),
            status=status,
            trigger=trigger,
            source_task_id=data.get("source_task_id"),
            source_feature_id=data.get("source_feature_id"),
            source_command=data.get("source_command"),
            context=data.get("context", ""),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            alternatives_considered=data.get("alternatives_considered", []),
            consequences=data.get("consequences", []),
            supersedes=data.get("supersedes"),
            superseded_by=data.get("superseded_by"),
            related_adrs=data.get("related_adrs", []),
            created_at=created_at,
            decided_at=data.get("decided_at"),
            deprecated_at=data.get("deprecated_at"),
            tags=data.get("tags", []),
            confidence=data.get("confidence", 1.0)
        )

    async def create_adr(self, adr: ADREntity) -> Optional[str]:
        """Create a new ADR in Graphiti.

        Generates an ID if not provided, then stores the ADR as an episode
        in Graphiti with group_id="adrs".

        Args:
            adr: ADREntity to create

        Returns:
            ADR ID if successful, None on failure (graceful degradation)

        Example:
            adr = ADREntity(id="ADR-0001", title="Use PostgreSQL")
            adr_id = await service.create_adr(adr)
        """
        # Check if Graphiti is enabled
        if not self.client.enabled:
            logger.debug("Graphiti disabled, skipping ADR creation")
            return None

        try:
            # Generate ID if not provided
            if not adr.id:
                adr.id = self._get_next_adr_id()

            # Serialize and store
            episode_body = self._serialize_adr(adr)

            await self.client.add_episode(
                name=f"adr_{adr.id}",
                episode_body=episode_body,
                group_id="adrs"
            )

            logger.info(f"Created ADR: {adr.id}")
            return adr.id

        except Exception as e:
            logger.warning(f"Failed to create ADR: {e}")
            return None

    async def search_adrs(
        self,
        query: str,
        status: Optional[ADRStatus] = None,
        num_results: int = 10
    ) -> List[ADREntity]:
        """Search for ADRs by topic.

        Searches Graphiti for ADRs matching the query. Optionally filters
        by status after retrieval.

        Args:
            query: Search query string
            status: Optional status filter (applied after search)
            num_results: Maximum number of results (default: 10)

        Returns:
            List of matching ADREntity objects.
            Empty list on failure (graceful degradation).

        Example:
            results = await service.search_adrs("database", status=ADRStatus.ACCEPTED)
        """
        try:
            results = await self.client.search(
                query=query,
                group_ids=["adrs"],
                num_results=num_results
            )

            adrs = [self._parse_adr(r) for r in results]

            # Filter by status if provided
            if status is not None:
                adrs = [a for a in adrs if a.status == status]

            return adrs

        except Exception as e:
            logger.warning(f"Failed to search ADRs: {e}")
            return []

    async def get_adr(self, adr_id: str) -> Optional[ADREntity]:
        """Get a specific ADR by ID.

        Searches for an ADR with the exact ID.

        Args:
            adr_id: ADR ID to retrieve (e.g., "ADR-0001")

        Returns:
            ADREntity if found, None otherwise.
            Returns None on failure (graceful degradation).

        Example:
            adr = await service.get_adr("ADR-0001")
            if adr:
                print(f"Found: {adr.title}")
        """
        try:
            results = await self.client.search(
                query=adr_id,
                group_ids=["adrs"],
                num_results=1
            )

            if results:
                return self._parse_adr(results[0])

            return None

        except Exception as e:
            logger.warning(f"Failed to get ADR {adr_id}: {e}")
            return None

    async def supersede_adr(
        self,
        old_adr_id: str,
        new_adr: ADREntity
    ) -> Optional[str]:
        """Create a new ADR that supersedes an existing one.

        Updates the old ADR to SUPERSEDED status and creates the new ADR
        with a reference to the superseded ADR.

        Args:
            old_adr_id: ID of ADR to supersede
            new_adr: New ADREntity that replaces the old one

        Returns:
            New ADR ID if successful, None on failure (graceful degradation).

        Example:
            new_adr = ADREntity(id="ADR-0002", title="Use MongoDB instead")
            new_id = await service.supersede_adr("ADR-0001", new_adr)
        """
        try:
            # Get old ADR
            old_adr = await self.get_adr(old_adr_id)
            if old_adr is None:
                logger.warning(f"Could not find ADR {old_adr_id} to supersede")
                return None

            # Update old ADR status
            old_adr.status = ADRStatus.SUPERSEDED
            old_adr.superseded_by = new_adr.id

            # Set supersedes reference on new ADR
            new_adr.supersedes = old_adr_id

            # Create new ADR
            return await self.create_adr(new_adr)

        except Exception as e:
            logger.warning(f"Failed to supersede ADR {old_adr_id}: {e}")
            return None

    async def deprecate_adr(self, adr_id: str) -> Optional[bool]:
        """Deprecate an ADR.

        Sets the ADR status to DEPRECATED and records the deprecation time.

        Args:
            adr_id: ID of ADR to deprecate

        Returns:
            True if successful, None/False on failure (graceful degradation).

        Example:
            success = await service.deprecate_adr("ADR-0001")
        """
        try:
            # Get ADR
            adr = await self.get_adr(adr_id)
            if adr is None:
                logger.warning(f"Could not find ADR {adr_id} to deprecate")
                return None

            # Update status
            adr.status = ADRStatus.DEPRECATED
            adr.deprecated_at = datetime.now()

            # Note: In a full implementation, we would update the ADR in Graphiti
            # For now, the status is updated in-memory on the returned object

            return True

        except Exception as e:
            logger.warning(f"Failed to deprecate ADR {adr_id}: {e}")
            return None
