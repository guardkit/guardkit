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
