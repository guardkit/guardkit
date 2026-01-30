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

Singleton Pattern:
    await init_graphiti(config)  # Initialize once
    client = get_graphiti()       # Get instance anywhere
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import logging
import os

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
        except ImportError:
            _graphiti_core_available = False
            logger.warning("graphiti-core not installed. Install with: pip install graphiti-core")
    return _graphiti_core_available


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
        host: Deprecated - use neo4j_uri instead (kept for backwards compatibility)
        port: Deprecated - use neo4j_uri instead (kept for backwards compatibility)

    Raises:
        ValueError: If timeout is not positive

    Example:
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://graphiti.example.com:7687",
            neo4j_user="neo4j",
            neo4j_password="password123",
            timeout=60.0
        )
    """
    enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"
    timeout: float = 30.0
    # Deprecated fields for backwards compatibility
    host: str = "localhost"
    port: int = 8000

    def __post_init__(self):
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")


class GraphitiClient:
    """Wrapper around graphiti-core library with graceful degradation.

    All methods are designed to fail gracefully - returning empty results
    or None instead of raising exceptions. This ensures the application
    continues to function even when Neo4j is unavailable.

    Attributes:
        config: GraphitiConfig instance
        enabled: True only if config enabled AND successfully connected

    Example:
        client = GraphitiClient()
        await client.initialize()

        if client.enabled:
            results = await client.search("query", ["group1"])

        await client.close()
    """

    def __init__(self, config: Optional[GraphitiConfig] = None):
        """Initialize GraphitiClient.

        Args:
            config: GraphitiConfig instance. Uses defaults if None.
        """
        self.config = config or GraphitiConfig()
        self._graphiti = None  # Will hold the Graphiti instance
        self._connected = False

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
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search Graphiti with graceful degradation.

        Searches the knowledge graph for relevant information.
        Returns empty list on any error to ensure graceful degradation.

        Args:
            query: Search query string
            group_ids: Optional list of group IDs to search in.
                       If None, searches all groups.
            num_results: Maximum number of results (default: 10)

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
            return await self._execute_search(
                query=query,
                group_ids=group_ids,
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

    async def add_episode(
        self,
        name: str,
        episode_body: str,
        group_id: str
    ) -> Optional[str]:
        """Add episode with graceful degradation.

        Creates a new episode (knowledge entry) in Graphiti.
        Returns None on any error to ensure graceful degradation.

        Args:
            name: Episode name/title
            episode_body: Episode content (can be empty)
            group_id: Group ID for organization

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

        try:
            return await self._create_episode(
                name=name,
                episode_body=episode_body,
                group_id=group_id
            )
        except Exception as e:
            logger.warning(f"Graphiti add_episode failed: {e}")
            return None

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


def get_current_project_name() -> str:
    """Get the current project name from the working directory.

    Returns:
        Project name derived from the current working directory.
    """
    from pathlib import Path
    return Path.cwd().name


# Module-level singleton
_graphiti: Optional[GraphitiClient] = None


async def init_graphiti(config: Optional[GraphitiConfig] = None) -> bool:
    """Initialize the global Graphiti client.

    Creates and initializes a singleton GraphitiClient instance.
    Safe to call multiple times - will create new instance each time.

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
    global _graphiti
    _graphiti = GraphitiClient(config)
    return await _graphiti.initialize()


def get_graphiti() -> Optional[GraphitiClient]:
    """Get the global Graphiti client.

    Returns the singleton GraphitiClient instance if initialized,
    or None if init_graphiti has not been called.

    Returns:
        GraphitiClient instance or None if not initialized.

    Example:
        client = get_graphiti()
        if client and client.enabled:
            results = await client.search("query")
    """
    return _graphiti
