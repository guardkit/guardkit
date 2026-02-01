"""UpsertResult dataclass for upsert_episode operations.

Provides a structured result format for upsert operations,
indicating whether an episode was created, updated, or skipped.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal


@dataclass
class UpsertResult:
    """Result of upsert_episode operation.

    Attributes:
        action: The action taken - "created", "updated", or "skipped"
        episode: Episode data dictionary with uuid, content, metadata
        uuid: Episode UUID (shortcut to episode["uuid"])
        previous_uuid: For updates, the UUID of the previous episode (if different)
    """

    action: Literal["created", "updated", "skipped"]
    episode: Optional[Dict[str, Any]] = None
    uuid: Optional[str] = None
    previous_uuid: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate result state and extract uuid if needed."""
        # Validate action is valid
        if self.action not in ("created", "updated", "skipped"):
            raise ValueError(f"action must be 'created', 'updated', or 'skipped', got '{self.action}'")

        # Extract uuid from episode if not provided
        if self.uuid is None and self.episode is not None:
            self.uuid = self.episode.get("uuid")

    @classmethod
    def created(cls, episode: Dict[str, Any], uuid: Optional[str] = None) -> "UpsertResult":
        """Create a result for newly created episode.

        Args:
            episode: Episode data dictionary
            uuid: Episode UUID (extracted from episode if not provided)

        Returns:
            UpsertResult with action="created"
        """
        return cls(action="created", episode=episode, uuid=uuid)

    @classmethod
    def updated(
        cls,
        episode: Dict[str, Any],
        uuid: Optional[str] = None,
        previous_uuid: Optional[str] = None
    ) -> "UpsertResult":
        """Create a result for updated episode.

        Args:
            episode: Updated episode data dictionary
            uuid: New episode UUID
            previous_uuid: UUID of the episode that was replaced

        Returns:
            UpsertResult with action="updated"
        """
        return cls(action="updated", episode=episode, uuid=uuid, previous_uuid=previous_uuid)

    @classmethod
    def skipped(cls, episode: Dict[str, Any], uuid: Optional[str] = None) -> "UpsertResult":
        """Create a result for skipped operation (content unchanged).

        Args:
            episode: Existing episode data dictionary
            uuid: Episode UUID

        Returns:
            UpsertResult with action="skipped"
        """
        return cls(action="skipped", episode=episode, uuid=uuid)

    @property
    def was_created(self) -> bool:
        """Check if episode was created."""
        return self.action == "created"

    @property
    def was_updated(self) -> bool:
        """Check if episode was updated."""
        return self.action == "updated"

    @property
    def was_skipped(self) -> bool:
        """Check if operation was skipped."""
        return self.action == "skipped"
