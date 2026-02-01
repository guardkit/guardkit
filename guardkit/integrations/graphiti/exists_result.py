"""ExistsResult dataclass for episode existence checks.

Provides a structured result format for episode_exists() operations,
indicating whether an episode was found and providing episode details.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ExistsResult:
    """Result of episode existence check.

    Attributes:
        exists: True if an episode with matching entity_id was found
        episode: Episode data dictionary if found, None otherwise
        exact_match: True if source_hash matched (content-based deduplication)
        uuid: Episode UUID if found, None otherwise
    """

    exists: bool
    episode: Optional[Dict[str, Any]] = None
    exact_match: bool = False
    uuid: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate result state consistency."""
        # If exists is False, other fields should be empty/default
        if not self.exists:
            if self.episode is not None:
                raise ValueError("episode must be None when exists is False")
            if self.exact_match:
                raise ValueError("exact_match must be False when exists is False")
            if self.uuid is not None:
                raise ValueError("uuid must be None when exists is False")

        # If exists is True, uuid should be present
        if self.exists and self.uuid is None and self.episode is not None:
            # Try to extract uuid from episode if available
            if "uuid" in self.episode:
                object.__setattr__(self, "uuid", self.episode["uuid"])

    @classmethod
    def not_found(cls) -> "ExistsResult":
        """Create a not-found result.

        Returns:
            ExistsResult with exists=False.
        """
        return cls(exists=False)

    @classmethod
    def found(
        cls,
        episode: Dict[str, Any],
        exact_match: bool = False,
        uuid: Optional[str] = None
    ) -> "ExistsResult":
        """Create a found result.

        Args:
            episode: Episode data dictionary.
            exact_match: True if source_hash matched.
            uuid: Episode UUID. If not provided, attempts to extract from episode.

        Returns:
            ExistsResult with exists=True.
        """
        # Extract uuid from episode if not provided
        if uuid is None and episode:
            uuid = episode.get("uuid")

        return cls(
            exists=True,
            episode=episode,
            exact_match=exact_match,
            uuid=uuid
        )
