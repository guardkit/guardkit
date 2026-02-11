"""
Graphiti client wrapper with graceful degradation.

Provides a wrapper around the graphiti-core library that gracefully degrades
when Neo4j is not available, not configured, or encounters errors.
All operations return empty/None values on failure instead of raising exceptions.

This module uses the graphiti-core Python library for direct Neo4j communication,
bypassing the Docker REST API for better control and error handling.

Example Usage:
    config = GraphitiConfig(enabled=True, neo4j_uri="bolt://localhost:7687")
    client = GraphitiClient(config)
    await client.initialize()

    if client.enabled:
        results = await client.search("query", group_ids=["product_knowledge"])
        episode_id = await client.add_episode("name", "content", "group_id")

    await client.close()

Thread-Safe Factory Pattern:
    await init_graphiti(config)  # Initialize factory + thread client
    client = get_graphiti()       # Get per-thread client anywhere
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
import os
import re
import json
import threading

logger = logging.getLogger(__name__)

# Lazy import graphiti-core to allow graceful degradation
_graphiti_core_available = None


def _check_graphiti_core() -> bool:
    """Check if graphiti-core is available."""
    global _graphiti_core_available
    if _graphiti_core_available is None:
        try:
            from graphiti_core import Graphiti
            from graphiti_core.nodes import EpisodeType
            _graphiti_core_available = True
            # Apply FalkorDB workaround for single group_id search bug
            # (upstream PR #1170 pending on getzep/graphiti)
            from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
            apply_falkordb_workaround()
        except ImportError:
            _graphiti_core_available = False
            logger.warning("graphiti-core not installed. Install with: pip install graphiti-core")
    return _graphiti_core_available


def normalize_project_id(name: str) -> str:
    """Normalize project ID to valid format.

    Rules:
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove non-alphanumeric characters (except hyphens)
    - Truncate to max 50 characters
    - Handle empty strings (return empty string)

    Args:
        name: The name to normalize

    Returns:
        Normalized project ID string
    """
    if not name or not name.strip():
        return ""

    # Convert to lowercase
    result = name.lower()

    # Replace spaces and underscores with hyphens
    result = result.replace(" ", "-").replace("_", "-")

    # Remove non-alphanumeric characters (except hyphens)
    result = re.sub(r'[^a-z0-9-]', '', result)

    # Collapse multiple consecutive hyphens
    result = re.sub(r'-+', '-', result)

    # Remove leading/trailing hyphens
    result = result.strip('-')

    # Truncate to max 50 characters
    return result[:50]


@dataclass(frozen=True)
class GraphitiConfig:
    """Configuration for Graphiti connection via graphiti-core.

    This is a frozen (immutable) dataclass to ensure configuration
    cannot be modified after creation.

    Attributes:
        enabled: Whether Graphiti integration is enabled
        neo4j_uri: Neo4j Bolt URI (e.g., 'bolt://localhost:7687')
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        timeout: Connection timeout in seconds
        project_id: Project ID for namespace prefixing (optional)
        host: Deprecated - use neo4j_uri instead (kept for backwards compatibility)
        port: Deprecated - use neo4j_uri instead (kept for backwards compatibility)

    Raises:
        ValueError: If timeout is not positive
        ValueError: If project_id is invalid (>50 chars or invalid characters)

    Example:
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://graphiti.example.com:7687",
            neo4j_user="neo4j",
            neo4j_password="password123",
            timeout=60.0,
            project_id="my-project"
        )
    """
    enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    timeout: float = 30.0
    project_id: Optional[str] = None  # Project ID for namespace prefixing
    # Deprecated fields for backwards compatibility
    host: str = "localhost"
    port: int = 8000

    def __post_init__(self):
        """Validate and normalize configuration values."""
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")

        # Validate and normalize project_id if provided
        if self.project_id is not None:
            # First check for invalid characters that should be rejected (not normalized)
            invalid_chars = set('@#$%^&*()+=[]{}|\\;:\'",.<>?/~`')
            found_invalid = [c for c in self.project_id if c in invalid_chars]
            if found_invalid:
                raise ValueError(f"project_id contains invalid characters: {found_invalid}")

            # Check length before normalization
            if len(self.project_id) > 50:
                raise ValueError(f"project_id must be <= 50 characters, got {len(self.project_id)}")

            # Normalize valid project_id (frozen dataclass requires object.__setattr__)
            normalized = normalize_project_id(self.project_id)
            # Empty string after normalization means it was all invalid characters
            if normalized == "":
                object.__setattr__(self, 'project_id', None)
            else:
                object.__setattr__(self, 'project_id', normalized)


class GraphitiClient:
    """Wrapper around graphiti-core library with graceful degradation.

    All methods are designed to fail gracefully - returning empty results
    or None instead of raising exceptions. This ensures the application
    continues to function even when Neo4j is unavailable.

    Attributes:
        config: GraphitiConfig instance
        enabled: True only if config enabled AND successfully connected
        project_id: Optional project ID for namespace prefixing

    Example:
        client = GraphitiClient()
        await client.initialize()

        if client.enabled:
            results = await client.search("query", ["group1"])

        await client.close()
    """

    # Project-level groups that require project_id prefixing
    PROJECT_GROUP_NAMES = [
        "project_overview",
        "project_architecture",
        "feature_specs",
        "project_decisions",
        "project_constraints",
        "domain_knowledge",
        "bdd_scenarios",  # Added by FEAT-SC-001 for /impact-analysis deep mode
    ]

    def __init__(self, config: Optional[GraphitiConfig] = None, auto_detect_project: bool = True):
        """Initialize GraphitiClient.

        Args:
            config: GraphitiConfig instance. Uses defaults if None.
            auto_detect_project: If True and project_id not set, auto-detect from cwd.
                                Defaults to True to enable automatic project detection.
        """
        self.config = config or GraphitiConfig()
        self._graphiti = None  # Will hold the Graphiti instance
        self._connected = False
        self._auto_detect_project = auto_detect_project

        # Determine project_id: explicit > auto-detect
        if self.config.project_id is not None:
            self._project_id = self.config.project_id
        elif auto_detect_project:
            self._project_id = normalize_project_id(get_current_project_name())
            logger.warning(
                f"No explicit project_id in config, auto-detected '{self._project_id}' from cwd. "
                "Set project_id in .guardkit/graphiti.yaml for consistent behavior."
            )
        else:
            self._project_id = None

    @property
    def project_id(self) -> Optional[str]:
        """Get the project ID for namespace prefixing.

        Returns:
            Project ID string or None for system/global scope.
        """
        return self.get_project_id()

    @project_id.setter
    def project_id(self, value: Optional[str]) -> None:
        """Set the project ID for namespace prefixing.

        Args:
            value: Project ID string or None for system/global scope.
        """
        self._project_id = value

    def get_project_id(self, auto_detect: Optional[bool] = None) -> Optional[str]:
        """Get the project ID for namespace prefixing.

        Args:
            auto_detect: If True, auto-detect from cwd when project_id is None.
                        If False, return None when project_id is not set.
                        If None (default), uses the auto_detect_project setting from __init__.

        Returns:
            Project ID string or None for system/global scope.
        """
        # If explicit project_id is set, always return it
        if self.config.project_id is not None:
            return self.config.project_id

        # Determine whether to auto-detect
        should_auto_detect = auto_detect if auto_detect is not None else self._auto_detect_project

        if should_auto_detect:
            return normalize_project_id(get_current_project_name())
        else:
            return None

    def is_project_group(self, group_name: str) -> bool:
        """Check if group name is a project-level group (needs prefixing).

        Args:
            group_name: The group name to check

        Returns:
            True if it's a project group, False if system group

        Raises:
            ValueError: If group_name is empty
        """
        if not group_name:
            raise ValueError("group name cannot be empty")

        # System groups: in SYSTEM_GROUP_IDS or starts with guardkit_
        if group_name in self.SYSTEM_GROUP_IDS:
            return False
        if group_name.startswith("guardkit_"):
            return False

        # Known project groups
        if group_name in self.PROJECT_GROUP_NAMES:
            return True

        # Unknown groups default to project scope for safety
        return True

    def _is_already_prefixed(self, group_id: str) -> bool:
        """Check if group_id already has a project prefix.

        Args:
            group_id: The group ID to check

        Returns:
            True if already prefixed (contains __), False otherwise
        """
        return "__" in group_id

    def get_group_id(self, group_name: str, scope: Optional[str] = None) -> str:
        """Get correctly prefixed group ID.

        Args:
            group_name: Base group name
            scope: "project" or "system". Defaults to auto-detection.

        Returns:
            Prefixed group ID for project scope, unprefixed for system scope.

        Raises:
            ValueError: If scope is invalid, project_id required but not set,
                       or project_id is empty.
        """
        # Validate scope
        if scope is not None and scope not in ("project", "system"):
            raise ValueError("scope must be 'project' or 'system'")

        # Auto-detect scope if not specified
        if scope is None:
            scope = "project" if self.is_project_group(group_name) else "system"

        # System scope: return unprefixed
        if scope == "system":
            return group_name

        # Project scope: requires project_id
        if self._project_id is None:
            raise ValueError("project_id must be set for project scope")
        if self._project_id == "":
            raise ValueError("project_id cannot be empty for project scope")

        return f"{self._project_id}__{group_name}"

    def _apply_group_prefix(self, group_id: str, scope: Optional[str] = None) -> str:
        """Apply prefix to a group_id if needed.

        Args:
            group_id: The group ID to potentially prefix
            scope: "project", "system", or None for auto-detection

        Returns:
            Prefixed or unprefixed group_id
        """
        # Already prefixed - don't double-prefix
        if self._is_already_prefixed(group_id):
            return group_id

        # Explicit scope overrides auto-detection
        if scope == "system":
            return group_id
        if scope == "project":
            if self._project_id is None:
                raise ValueError("project_id must be set for project scope")
            if self._project_id == "":
                raise ValueError("project_id cannot be empty for project scope")
            return f"{self._project_id}__{group_id}"

        # Auto-detect based on group name
        if self.is_project_group(group_id):
            if self._project_id is None:
                raise ValueError("project_id must be set for project scope")
            if self._project_id == "":
                raise ValueError("project_id cannot be empty for project scope")
            return f"{self._project_id}__{group_id}"

        return group_id

    @property
    def enabled(self) -> bool:
        """Returns True only if config enabled AND connected.

        This property provides a safe way to check if the client
        is ready to use before making API calls.

        Returns:
            True if both enabled in config and successfully connected
        """
        return self.config.enabled and self._connected

    async def _check_connection(self) -> bool:
        """Check if connection to Neo4j can be established.

        Attempts to connect using the graphiti-core library.

        Returns:
            True if connection successful, False otherwise
        """
        if not _check_graphiti_core():
            logger.debug("graphiti-core not available")
            return False

        try:
            from graphiti_core import Graphiti

            # Create a test connection
            test_graphiti = Graphiti(
                self.config.neo4j_uri,
                self.config.neo4j_user,
                self.config.neo4j_password,
            )
            # Don't build indices here - just test connection
            # The driver will validate the connection on first query
            await test_graphiti.close()
            return True
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False

    async def _check_health(self) -> bool:
        """Check Neo4j/Graphiti health.

        Returns:
            True if the system is healthy and responding, False otherwise
        """
        if not self.config.enabled:
            return False

        if not self._connected or not self._graphiti:
            return False

        try:
            # Try a simple search to verify the system is working
            # This validates both Neo4j connection and Graphiti indices
            await self._graphiti.search("health_check_test", num_results=1)
            return True
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def initialize(self) -> bool:
        """Initialize connection to Neo4j via graphiti-core.

        Performs initialization checks:
        1. Checks if config is enabled
        2. Checks for OPENAI_API_KEY environment variable
        3. Checks if graphiti-core is available
        4. Attempts to establish connection and build indices

        Returns:
            True if initialization successful, False otherwise.
            Returns False and logs warning if:
            - Config disabled
            - OPENAI_API_KEY not set
            - graphiti-core not installed
            - Connection fails
            - Timeout occurs
        """
        # Check if disabled in config
        if not self.config.enabled:
            logger.warning("Graphiti disabled in configuration")
            self._connected = False
            return False

        # Check for OPENAI_API_KEY
        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set, Graphiti requires OpenAI for embeddings")
            self._connected = False
            return False

        # Check if graphiti-core is available
        if not _check_graphiti_core():
            logger.warning("graphiti-core not installed")
            self._connected = False
            return False

        # Try to establish connection
        try:
            from graphiti_core import Graphiti

            self._graphiti = Graphiti(
                self.config.neo4j_uri,
                self.config.neo4j_user,
                self.config.neo4j_password,
            )

            # Build indices and constraints (safe to call multiple times)
            await self._graphiti.build_indices_and_constraints()

            self._connected = True
            logger.info(f"Connected to Neo4j via graphiti-core at {self.config.neo4j_uri}")
            return True

        except TimeoutError as e:
            logger.warning(f"Graphiti connection timeout: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.warning(f"Graphiti initialization error: {e}")
            self._connected = False
            return False

    async def health_check(self) -> bool:
        """Check if Graphiti/Neo4j is healthy.

        Returns:
            True if the system is healthy and responding,
            False if disabled, not connected, or unhealthy.
        """
        if not self.config.enabled:
            return False

        try:
            return await self._check_health()
        except Exception as e:
            logger.warning(f"Graphiti health check failed: {e}")
            return False

    async def _execute_search(
        self,
        query: str,
        group_ids: Optional[List[str]] = None,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Execute the actual search against Graphiti/Neo4j.

        This is the internal method that performs the search.
        It can be mocked in tests.

        Args:
            query: Search query string
            group_ids: List of group IDs to search in
            num_results: Maximum number of results to return

        Returns:
            List of search results as dictionaries
        """
        if not self._graphiti:
            logger.warning("Graphiti not initialized, search unavailable")
            return []

        try:
            # Use graphiti-core search
            results = await self._graphiti.search(
                query,
                group_ids=group_ids,
                num_results=num_results
            )

            # Convert Edge objects to dictionaries
            return [
                {
                    "uuid": edge.uuid,
                    "fact": edge.fact,
                    "name": getattr(edge, 'name', edge.fact[:50] if edge.fact else 'unknown'),
                    "created_at": str(edge.created_at) if hasattr(edge, 'created_at') else None,
                    "valid_at": str(edge.valid_at) if hasattr(edge, 'valid_at') else None,
                    "score": getattr(edge, 'score', 0.0),
                }
                for edge in results
            ]

        except Exception as e:
            logger.warning(f"Search request failed: {e}")
            return []

    async def search(
        self,
        query: str,
        group_ids: Optional[List[str]] = None,
        num_results: int = 10,
        scope: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search Graphiti with graceful degradation.

        Searches the knowledge graph for relevant information.
        Returns empty list on any error to ensure graceful degradation.

        Args:
            query: Search query string
            group_ids: Optional list of group IDs to search in.
                       If None, searches all groups.
            num_results: Maximum number of results (default: 10)
            scope: Optional scope override ("project" or "system").
                   If None, auto-detects based on group names.

        Returns:
            List of search results as dictionaries.
            Empty list if:
            - Client not enabled
            - Search fails
            - Connection error

        Example:
            results = await client.search(
                query="authentication patterns",
                group_ids=["architecture_decisions"],
                num_results=5
            )
        """
        if not self.config.enabled:
            return []

        try:
            # Apply prefixing to group_ids if provided
            prefixed_group_ids = None
            if group_ids is not None:
                prefixed_group_ids = [
                    self._apply_group_prefix(gid, scope) for gid in group_ids
                ]

            return await self._execute_search(
                query=query,
                group_ids=prefixed_group_ids,
                num_results=num_results
            )
        except Exception as e:
            logger.warning(f"Graphiti search failed: {e}")
            return []

    async def _create_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str
    ) -> Optional[str]:
        """Create an episode in Graphiti using graphiti-core.

        This is the internal method that creates the episode.
        It can be mocked in tests.

        Args:
            name: Episode name/title
            episode_body: Episode content
            group_id: Group ID for organization

        Returns:
            Episode UUID if successful, None otherwise
        """
        if not self._graphiti:
            logger.warning("Graphiti not initialized, episode creation unavailable")
            return None

        try:
            from graphiti_core.nodes import EpisodeType

            # Add episode using graphiti-core
            result = await self._graphiti.add_episode(
                name=name,
                episode_body=episode_body,
                source=EpisodeType.text,
                source_description=f"GuardKit knowledge seeding: {name}",
                reference_time=datetime.now(timezone.utc),
                group_id=group_id
            )

            # Return the episode UUID
            if result and hasattr(result, 'episode') and result.episode:
                return result.episode.uuid
            return None

        except Exception as e:
            logger.warning(f"Episode creation request failed: {e}")
            return None

    def _inject_metadata(self, content: str, metadata: "EpisodeMetadata") -> str:
        """Inject metadata block into episode content.

        Args:
            content: Original episode content
            metadata: EpisodeMetadata to inject

        Returns:
            Content with metadata block appended
        """
        metadata_json = json.dumps(metadata.to_dict(), indent=2)
        metadata_block = f"\n\n---\n_metadata:\n```json\n{metadata_json}\n```"
        return content + metadata_block

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        scope: Optional[str] = None,
        metadata: Optional["EpisodeMetadata"] = None,
        source: str = "user_added",
        entity_type: str = "generic",
    ) -> Optional[str]:
        """Add episode with graceful degradation.

        Creates a new episode (knowledge entry) in Graphiti.
        Returns None on any error to ensure graceful degradation.

        Args:
            name: Episode name/title
            episode_body: Episode content (can be empty)
            group_id: Group ID for organization
            scope: Optional scope override ("project" or "system").
                   If None, auto-detects based on group name.
            metadata: Optional EpisodeMetadata to inject. If None, auto-generates.
            source: Source of the episode (default: "user_added").
            entity_type: Type of entity (default: "generic").

        Returns:
            Episode UUID if successful, None if:
            - Client not enabled
            - Creation fails
            - Connection error

        Example:
            episode_id = await client.add_episode(
                name="OAuth2 Implementation Decision",
                episode_body="Decided to use OAuth2 with PKCE flow...",
                group_id="architecture_decisions"
            )
        """
        if not self.config.enabled:
            return None

        # Import EpisodeMetadata here to avoid circular imports
        from guardkit.integrations.graphiti.metadata import EpisodeMetadata

        # Auto-generate metadata if not provided
        if metadata is None:
            metadata = EpisodeMetadata.create_now(
                source=source,
                entity_type=entity_type,
                project_id=self.project_id
            )

        # Inject metadata into episode_body
        episode_body_with_metadata = self._inject_metadata(episode_body, metadata)

        # Apply prefixing to group_id (may raise ValueError if project_id not set)
        prefixed_group_id = self._apply_group_prefix(group_id, scope)

        try:
            return await self._create_episode(
                name=name,
                episode_body=episode_body_with_metadata,
                group_id=prefixed_group_id
            )
        except Exception as e:
            logger.warning(f"Graphiti add_episode failed: {e}")
            return None

    async def upsert_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str,
        entity_id: str,
        source: str = "user_added",
        entity_type: str = "generic",
        scope: Optional[str] = None,
        source_hash: Optional[str] = None,
    ) -> Optional["UpsertResult"]:
        """Create or update an episode.

        Upsert logic:
        1. Check if episode with entity_id exists
        2. If not exists: create new episode
        3. If exists with same content (source_hash match): skip
        4. If exists with different content: create new episode, preserving created_at

        Args:
            name: Episode name/title
            episode_body: Episode content
            group_id: Group for the episode
            entity_id: Stable identifier for upsert
            source: Source type (default: "user_added")
            entity_type: Entity type (default: "generic")
            scope: Optional scope override ("project" or "system")
            source_hash: Optional pre-computed source hash. If None, computed from episode_body.

        Returns:
            UpsertResult with action (created/updated/skipped) and episode info.
            Returns None if client is disabled or not initialized.
        """
        # Import here to avoid circular imports
        import hashlib
        from guardkit.integrations.graphiti.metadata import EpisodeMetadata
        from guardkit.integrations.graphiti.upsert_result import UpsertResult

        # Graceful degradation: return None if disabled
        if not self.config.enabled:
            return None

        # Graceful degradation: return None if not initialized
        if not self._graphiti:
            logger.warning("Graphiti not initialized, upsert_episode unavailable")
            return None

        try:
            # Generate source_hash from content if not provided
            if source_hash is None:
                source_hash = hashlib.sha256(episode_body.encode()).hexdigest()

            # Check if episode exists
            exists_result = await self.episode_exists(
                entity_id=entity_id,
                group_id=group_id,
                source_hash=source_hash
            )

            if exists_result.exists:
                if exists_result.exact_match:
                    # Content unchanged, skip update
                    return UpsertResult.skipped(
                        episode=exists_result.episode,
                        uuid=exists_result.uuid
                    )

                # Episode exists but content changed - update
                # Preserve original created_at from existing episode
                original_created_at = None
                if exists_result.episode and exists_result.episode.get("metadata"):
                    original_created_at = exists_result.episode["metadata"].get("created_at")

                # Create metadata with preserved created_at and new updated_at
                metadata = EpisodeMetadata.create_now(
                    source=source,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    source_hash=source_hash,
                    project_id=self.project_id,
                )

                # Override created_at if we have original
                if original_created_at:
                    object.__setattr__(metadata, "created_at", original_created_at)

                # Set updated_at to now
                now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                metadata.updated_at = now

                # Create new episode (invalidate + create strategy)
                new_uuid = await self.add_episode(
                    name=name,
                    episode_body=episode_body,
                    group_id=group_id,
                    scope=scope,
                    metadata=metadata,
                    source=source,
                    entity_type=entity_type,
                )

                if new_uuid:
                    return UpsertResult.updated(
                        episode={
                            "uuid": new_uuid,
                            "content": episode_body,
                            "metadata": metadata.to_dict(),
                        },
                        uuid=new_uuid,
                        previous_uuid=exists_result.uuid,
                    )
                return None

            else:
                # Episode doesn't exist - create new
                metadata = EpisodeMetadata.create_now(
                    source=source,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    source_hash=source_hash,
                    project_id=self.project_id,
                )

                new_uuid = await self.add_episode(
                    name=name,
                    episode_body=episode_body,
                    group_id=group_id,
                    scope=scope,
                    metadata=metadata,
                    source=source,
                    entity_type=entity_type,
                )

                if new_uuid:
                    return UpsertResult.created(
                        episode={
                            "uuid": new_uuid,
                            "content": episode_body,
                            "metadata": metadata.to_dict(),
                        },
                        uuid=new_uuid,
                    )
                return None

        except Exception as e:
            logger.warning(f"Graphiti upsert_episode failed: {e}")
            return None

    # =========================================================================
    # EPISODE EXISTS METHOD
    # =========================================================================

    def _parse_episode_metadata(self, fact: str) -> Optional[Dict[str, Any]]:
        """Parse metadata from episode fact/body.

        Episodes may contain JSON metadata at the start of the body,
        separated from content by double newline.

        Args:
            fact: The episode fact/body content.

        Returns:
            Parsed metadata dict or None if no valid JSON metadata found.
        """
        import json

        if not fact:
            return None

        # Try to parse JSON from the beginning of the fact
        try:
            # Check if fact starts with '{'
            stripped = fact.strip()
            if not stripped.startswith('{'):
                return None

            # Find the end of JSON - either at newline separator or end
            # Try to find double newline separator
            separator_idx = stripped.find('\n\n')
            if separator_idx > 0:
                json_str = stripped[:separator_idx]
            else:
                # Try to parse entire string as JSON
                json_str = stripped

            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return None

    async def episode_exists(
        self,
        entity_id: str,
        group_id: str,
        source_hash: Optional[str] = None
    ) -> "ExistsResult":
        """Check if episode exists in Graphiti.

        Searches for an episode with matching entity_id in the metadata.
        If source_hash is provided, also checks for exact content match.

        Args:
            entity_id: Stable identifier for the episode.
            group_id: Group to search in (will be prefixed if project group).
            source_hash: Optional content hash for exact match verification.

        Returns:
            ExistsResult with exists flag and episode info if found.
            Returns ExistsResult.not_found() on any error (graceful degradation).

        Example:
            result = await client.episode_exists(
                entity_id="project-overview-001",
                group_id="project_overview",
                source_hash="abc123..."
            )
            if result.exists:
                if result.exact_match:
                    print("Episode exists with same content")
                else:
                    print("Episode exists but content changed")
        """
        # Import here to avoid circular imports
        from guardkit.integrations.graphiti.exists_result import ExistsResult

        # Graceful degradation: return not found if disabled
        if not self.config.enabled:
            return ExistsResult.not_found()

        # Graceful degradation: return not found if not initialized
        if not self._graphiti:
            logger.warning("Graphiti not initialized, episode_exists unavailable")
            return ExistsResult.not_found()

        try:
            # Apply prefixing to group_id
            prefixed_group_id = self._apply_group_prefix(group_id)

            # Search for episodes in the group
            # We search with a broad query and filter results by entity_id
            results = await self._graphiti.search(
                f"entity_id {entity_id}",
                group_ids=[prefixed_group_id],
                num_results=50  # Get enough results to find matches
            )

            if not results:
                return ExistsResult.not_found()

            # Variables to track best match
            exact_match_episode = None
            entity_match_episode = None

            # Iterate through results to find matching entity_id
            for edge in results:
                # Get the fact/body content
                fact = getattr(edge, 'fact', None)
                if not fact:
                    continue

                # Parse metadata from the fact
                metadata = self._parse_episode_metadata(fact)
                if not metadata:
                    continue

                # Check if entity_id matches
                episode_entity_id = metadata.get('entity_id')
                if episode_entity_id != entity_id:
                    continue

                # Found matching entity_id
                episode_data = {
                    "uuid": getattr(edge, 'uuid', None),
                    "fact": fact,
                    "name": getattr(edge, 'name', None),
                    "created_at": str(getattr(edge, 'created_at', None)) if hasattr(edge, 'created_at') else None,
                    "valid_at": str(getattr(edge, 'valid_at', None)) if hasattr(edge, 'valid_at') else None,
                    "metadata": metadata,
                }

                # If source_hash provided, check for exact match
                if source_hash:
                    episode_hash = metadata.get('source_hash')
                    if episode_hash == source_hash:
                        # Found exact match - return immediately
                        return ExistsResult.found(
                            episode=episode_data,
                            exact_match=True,
                            uuid=episode_data["uuid"]
                        )

                # Track this as a potential match
                if entity_match_episode is None:
                    entity_match_episode = episode_data

            # Return best match found
            if entity_match_episode:
                return ExistsResult.found(
                    episode=entity_match_episode,
                    exact_match=False,  # No exact hash match found
                    uuid=entity_match_episode["uuid"]
                )

            return ExistsResult.not_found()

        except Exception as e:
            logger.warning(f"Graphiti episode_exists failed: {e}")
            return ExistsResult.not_found()

    # =========================================================================
    # CLEAR METHODS
    # =========================================================================

    # System group IDs that are cleared with --system-only
    SYSTEM_GROUP_IDS = [
        "guardkit_templates",
        "guardkit_patterns",
        "guardkit_workflows",
        "product_knowledge",
        "command_workflows",
        "quality_gate_phases",
        "technology_stack",
        "feature_build_architecture",
        "architecture_decisions",
        "failure_patterns",
        "component_status",
        "integration_points",
        "templates",
        "agents",
        "patterns",
        "rules",
        "failed_approaches",
        "quality_gate_configs",
        "role_constraints",
        "implementation_modes",
    ]

    async def _list_groups(self) -> List[str]:
        """List all group IDs in the knowledge graph.

        Returns:
            List of group IDs, empty list on error.
        """
        if not self._graphiti or not self._connected:
            return []

        try:
            # Query Neo4j for distinct group IDs
            driver = getattr(self._graphiti, 'driver', None)
            if not driver:
                return []

            async with driver.session() as session:
                result = await session.run(
                    "MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id"
                )
                records = await result.data()
                return [r["group_id"] for r in records if r.get("group_id")]
        except Exception as e:
            logger.warning(f"Failed to list groups: {e}")
            return []

    async def _clear_group(self, group_id: str) -> int:
        """Clear all episodes in a specific group.

        Args:
            group_id: The group ID to clear.

        Returns:
            Number of episodes deleted, 0 on error.
        """
        if not self._graphiti or not self._connected:
            return 0

        try:
            driver = getattr(self._graphiti, 'driver', None)
            if not driver:
                return 0

            async with driver.session() as session:
                # Delete episodes and their relationships in the group
                result = await session.run(
                    """
                    MATCH (e:Episode {group_id: $group_id})
                    WITH e, count(e) as cnt
                    DETACH DELETE e
                    RETURN cnt as count
                    """,
                    group_id=group_id
                )
                record = await result.single()
                return record["count"] if record else 0
        except Exception as e:
            logger.warning(f"Failed to clear group {group_id}: {e}")
            return 0

    async def clear_all(self) -> Dict[str, Any]:
        """Clear all knowledge (system + project groups).

        Returns:
            Dict with clearing results:
            - system_groups_cleared: int
            - project_groups_cleared: int
            - total_episodes_deleted: int
        """
        if not self.config.enabled:
            return {
                "system_groups_cleared": 0,
                "project_groups_cleared": 0,
                "total_episodes_deleted": 0,
            }

        if not self._graphiti or not self._connected:
            return {
                "system_groups_cleared": 0,
                "project_groups_cleared": 0,
                "total_episodes_deleted": 0,
            }

        try:
            all_groups = await self._list_groups()
            system_cleared = 0
            project_cleared = 0
            total_deleted = 0

            for group_id in all_groups:
                deleted = await self._clear_group(group_id)
                total_deleted += deleted

                if group_id in self.SYSTEM_GROUP_IDS or not "__" in group_id:
                    system_cleared += 1
                else:
                    project_cleared += 1

            return {
                "system_groups_cleared": system_cleared,
                "project_groups_cleared": project_cleared,
                "total_episodes_deleted": total_deleted,
            }
        except Exception as e:
            logger.warning(f"Failed to clear all: {e}")
            return {
                "system_groups_cleared": 0,
                "project_groups_cleared": 0,
                "total_episodes_deleted": 0,
                "error": str(e),
            }

    async def clear_system_groups(self) -> Dict[str, Any]:
        """Clear only system-level knowledge groups.

        System groups include templates, patterns, workflows, etc.
        Does NOT clear project-specific knowledge.

        Returns:
            Dict with clearing results:
            - groups_cleared: List[str]
            - episodes_deleted: int
        """
        if not self.config.enabled:
            return {"groups_cleared": [], "episodes_deleted": 0}

        if not self._graphiti or not self._connected:
            return {"groups_cleared": [], "episodes_deleted": 0}

        try:
            all_groups = await self._list_groups()
            cleared = []
            total_deleted = 0

            for group_id in all_groups:
                # Only clear system groups (no __ pattern)
                if group_id in self.SYSTEM_GROUP_IDS or (
                    not "__" in group_id and group_id.startswith("guardkit")
                ):
                    deleted = await self._clear_group(group_id)
                    total_deleted += deleted
                    cleared.append(group_id)

            return {
                "groups_cleared": cleared,
                "episodes_deleted": total_deleted,
            }
        except Exception as e:
            logger.warning(f"Failed to clear system groups: {e}")
            return {"groups_cleared": [], "episodes_deleted": 0, "error": str(e)}

    async def clear_project_groups(
        self, project_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clear only project-level knowledge groups.

        Project groups follow the pattern: {project}__group_name

        Args:
            project_name: Project name to clear. If None, auto-detects from cwd.

        Returns:
            Dict with clearing results:
            - project: str
            - groups_cleared: List[str]
            - episodes_deleted: int
        """
        if not self.config.enabled:
            return {"project": project_name or "", "groups_cleared": [], "episodes_deleted": 0}

        if not self._graphiti or not self._connected:
            return {"project": project_name or "", "groups_cleared": [], "episodes_deleted": 0}

        try:
            # Auto-detect project name if not provided
            if not project_name:
                project_name = get_current_project_name()

            all_groups = await self._list_groups()
            cleared = []
            total_deleted = 0
            prefix = f"{project_name}__"

            for group_id in all_groups:
                # Only clear groups matching this project's prefix
                if group_id.startswith(prefix):
                    deleted = await self._clear_group(group_id)
                    total_deleted += deleted
                    cleared.append(group_id)

            return {
                "project": project_name,
                "groups_cleared": cleared,
                "episodes_deleted": total_deleted,
            }
        except Exception as e:
            logger.warning(f"Failed to clear project groups: {e}")
            return {
                "project": project_name or "",
                "groups_cleared": [],
                "episodes_deleted": 0,
                "error": str(e),
            }

    async def get_clear_preview(
        self,
        system_only: bool = False,
        project_only: bool = False,
        project_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a preview of what would be deleted.

        Args:
            system_only: Only preview system groups.
            project_only: Only preview project groups.
            project_name: Project name for project_only. Auto-detects if None.

        Returns:
            Dict with preview:
            - system_groups: List[str]
            - project_groups: List[str]
            - total_groups: int
            - estimated_episodes: int
        """
        if not self.config.enabled:
            return {
                "system_groups": [],
                "project_groups": [],
                "total_groups": 0,
                "estimated_episodes": 0,
            }

        if not self._graphiti or not self._connected:
            return {
                "system_groups": [],
                "project_groups": [],
                "total_groups": 0,
                "estimated_episodes": 0,
            }

        try:
            all_groups = await self._list_groups()
            system_groups = []
            project_groups = []

            # Auto-detect project name for project_only
            if project_only and not project_name:
                project_name = get_current_project_name()

            for group_id in all_groups:
                is_system = group_id in self.SYSTEM_GROUP_IDS or (
                    not "__" in group_id and group_id.startswith("guardkit")
                )
                is_project = "__" in group_id

                if system_only and is_system:
                    system_groups.append(group_id)
                elif project_only and is_project:
                    if not project_name or group_id.startswith(f"{project_name}__"):
                        project_groups.append(group_id)
                elif not system_only and not project_only:
                    if is_system:
                        system_groups.append(group_id)
                    elif is_project:
                        project_groups.append(group_id)

            # Estimate episode count
            estimated = 0
            try:
                driver = getattr(self._graphiti, 'driver', None)
                if driver:
                    async with driver.session() as session:
                        target_groups = system_groups + project_groups
                        if target_groups:
                            result = await session.run(
                                """
                                MATCH (e:Episode)
                                WHERE e.group_id IN $groups
                                RETURN count(e) as count
                                """,
                                groups=target_groups
                            )
                            record = await result.single()
                            estimated = record["count"] if record else 0
            except Exception:
                pass  # Estimation is best-effort

            return {
                "system_groups": system_groups,
                "project_groups": project_groups,
                "total_groups": len(system_groups) + len(project_groups),
                "estimated_episodes": estimated,
            }
        except Exception as e:
            logger.warning(f"Failed to get clear preview: {e}")
            return {
                "system_groups": [],
                "project_groups": [],
                "total_groups": 0,
                "estimated_episodes": 0,
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the Graphiti connection and clean up resources.

        Safe to call even if not connected or already closed.
        """
        if self._graphiti:
            try:
                await self._graphiti.close()
            except Exception as e:
                logger.debug(f"Error closing Graphiti connection: {e}")
            finally:
                self._graphiti = None
                self._connected = False


def _suppress_httpx_cleanup_errors(loop: "asyncio.AbstractEventLoop") -> None:
    """Install a custom exception handler that suppresses httpx cleanup errors.

    When ``asyncio.run()`` creates a temporary event loop for Graphiti client
    initialization, httpx ``AsyncClient`` objects may schedule background
    ``aclose()`` tasks.  After ``asyncio.run()`` completes the loop is closed,
    so those pending tasks raise ``RuntimeError('Event loop is closed')``.

    These errors are harmless — the OS will reclaim the underlying sockets when
    the thread exits — but they produce noisy ``ERROR:asyncio:Task exception was
    never retrieved`` log lines.

    This handler silences only those specific errors while letting everything
    else propagate normally.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        The event loop to install the handler on.
    """
    original_handler = loop.get_exception_handler()

    def _handler(
        _loop: "asyncio.AbstractEventLoop", context: dict
    ) -> None:
        exception = context.get("exception")
        if (
            isinstance(exception, RuntimeError)
            and str(exception) == "Event loop is closed"
        ):
            # Harmless httpx cleanup error — suppress silently
            return
        # Delegate everything else to the original handler (or default)
        if original_handler is not None:
            original_handler(_loop, context)
        else:
            _loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


class GraphitiClientFactory:
    """Thread-safe factory for creating per-thread GraphitiClient instances.

    Stores shared configuration (frozen dataclass, thread-safe) and manages
    thread-local client storage. Each client gets its own Neo4j driver and
    OpenAI embedder, bound to the event loop of the calling thread.

    This solves BUG-1 from TASK-REV-2AA0: the shared singleton's Neo4j driver
    was bound to one event loop, causing cross-loop errors when worker threads
    in FeatureOrchestrator created their own event loops.

    Attributes:
        config: Frozen GraphitiConfig instance (shared across threads)
    """

    def __init__(self, config: GraphitiConfig):
        self._config = config
        self._thread_local = threading.local()

    @property
    def config(self) -> GraphitiConfig:
        """Get the shared configuration."""
        return self._config

    def create_client(self) -> GraphitiClient:
        """Create a new uninitialized GraphitiClient.

        The caller is responsible for calling ``await client.initialize()``
        in the appropriate async context.

        Returns:
            A new GraphitiClient instance, not yet connected.
        """
        return GraphitiClient(self._config)

    async def create_and_init_client(self) -> Optional[GraphitiClient]:
        """Create and initialize a new GraphitiClient.

        Must be called from an async context. The client's Neo4j driver
        and OpenAI embedder will be bound to the current thread's event loop.

        Returns:
            Initialized GraphitiClient, or None if initialization fails.
        """
        client = self.create_client()
        success = await client.initialize()
        return client if success else None

    def get_thread_client(self) -> Optional[GraphitiClient]:
        """Get or lazily create a client for the current thread.

        Uses threading.local() for automatic per-thread storage.
        On first access in a thread, creates a new client and attempts
        initialization (mirrors _try_lazy_init behavior for async context
        detection).

        Returns:
            GraphitiClient for the current thread, or None if config is
            disabled or initialization fails.
        """
        client = getattr(self._thread_local, 'client', None)
        if client is not None:
            return client

        init_attempted = getattr(self._thread_local, 'init_attempted', False)
        if init_attempted:
            return None

        self._thread_local.init_attempted = True

        if not self._config.enabled:
            logger.info("Graphiti disabled in configuration, thread client not created")
            return None

        client = self.create_client()

        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            logger.info(
                "Graphiti factory: async loop running in thread, created client "
                "but deferred connection"
            )
            self._thread_local.client = client
            return client
        else:
            coro = client.initialize()
            try:
                loop = asyncio.new_event_loop()
                _suppress_httpx_cleanup_errors(loop)
                try:
                    success = loop.run_until_complete(coro)
                finally:
                    loop.close()
                if success:
                    self._thread_local.client = client
                    logger.info("Graphiti factory: thread client initialized successfully")
                    return client
                else:
                    logger.info("Graphiti factory: thread client init failed")
                    return None
            except Exception as e:
                coro.close()  # Suppress RuntimeWarning by explicitly closing
                logger.info(f"Graphiti factory: thread client init error: {e}")
                return None

    def set_thread_client(self, client: Optional[GraphitiClient]) -> None:
        """Explicitly set the client for the current thread.

        Useful for testing or when a caller has already initialized
        a client in the correct async context.

        Args:
            client: GraphitiClient to store, or None to clear.
        """
        self._thread_local.client = client
        self._thread_local.init_attempted = True


def get_current_project_name() -> str:
    """Get the current project name from the working directory.

    Returns:
        Project name derived from the current working directory.
    """
    from pathlib import Path
    return Path.cwd().name


# Module-level factory (replaces singleton)
_factory: Optional[GraphitiClientFactory] = None
_factory_init_attempted: bool = False


async def init_graphiti(config: Optional[GraphitiConfig] = None) -> bool:
    """Initialize the global Graphiti client factory.

    Creates a GraphitiClientFactory and initializes a client for the
    current thread. Safe to call multiple times - will create a new
    factory each time.

    Args:
        config: GraphitiConfig instance. Uses defaults if None.

    Returns:
        True if initialization successful, False otherwise.

    Example:
        config = GraphitiConfig(enabled=True)
        success = await init_graphiti(config)
        if success:
            client = get_graphiti()
    """
    global _factory, _factory_init_attempted
    _factory_init_attempted = True

    if config is None:
        config = GraphitiConfig()

    _factory = GraphitiClientFactory(config)

    client = await _factory.create_and_init_client()
    if client is not None:
        _factory.set_thread_client(client)
        return True
    else:
        _factory = None
        return False


def _try_lazy_init() -> Optional[GraphitiClient]:
    """Attempt lazy initialization of Graphiti factory from config.

    Creates a GraphitiClientFactory from load_graphiti_config() and
    returns a thread-local client. Only attempts once per process
    to avoid repeated connection failures.

    Returns:
        GraphitiClient for the current thread if successful, None otherwise.
    """
    global _factory, _factory_init_attempted

    _factory_init_attempted = True

    try:
        from guardkit.knowledge.config import load_graphiti_config
        settings = load_graphiti_config()

        if not settings.enabled:
            logger.info("Graphiti disabled in configuration, lazy-init skipped")
            return None

        config = GraphitiConfig(
            enabled=settings.enabled,
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
            timeout=settings.timeout,
            project_id=settings.project_id,
        )

        _factory = GraphitiClientFactory(config)
        return _factory.get_thread_client()

    except ImportError as e:
        logger.info(f"Graphiti lazy-init skipped: {e}")
        return None
    except Exception as e:
        logger.info(f"Graphiti lazy-init failed: {e}")
        return None


def get_graphiti() -> Optional[GraphitiClient]:
    """Get a Graphiti client for the current thread, with lazy initialization.

    Backward-compatible API. Now returns a thread-local client instead
    of a shared singleton. Each thread gets its own GraphitiClient with
    its own Neo4j driver bound to that thread's event loop.

    Returns:
        GraphitiClient instance or None if not available.

    Example:
        client = get_graphiti()
        if client and client.enabled:
            results = await client.search("query")
    """
    global _factory, _factory_init_attempted

    if _factory is not None:
        return _factory.get_thread_client()

    # Only attempt lazy-init once per process
    if not _factory_init_attempted:
        return _try_lazy_init()

    return None


def get_factory() -> Optional[GraphitiClientFactory]:
    """Get the global GraphitiClientFactory.

    Returns the factory if initialized, or None. Does NOT trigger
    lazy initialization — use get_graphiti() for that.

    Returns:
        GraphitiClientFactory instance or None.
    """
    return _factory
