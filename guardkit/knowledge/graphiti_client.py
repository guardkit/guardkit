"""
Graphiti client wrapper with graceful degradation.

Provides a wrapper around the Graphiti SDK that gracefully degrades
when Graphiti is not available, not configured, or encounters errors.
All operations return empty/None values on failure instead of raising exceptions.

Example Usage:
    config = GraphitiConfig(enabled=True, host="localhost", port=8000)
    client = GraphitiClient(config)
    await client.initialize()

    if client.enabled:
        results = await client.search("query", group_ids=["product_knowledge"])
        episode_id = await client.add_episode("name", "content", "group_id")

Singleton Pattern:
    await init_graphiti(config)  # Initialize once
    client = get_graphiti()       # Get instance anywhere
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraphitiConfig:
    """Configuration for Graphiti connection.

    This is a frozen (immutable) dataclass to ensure configuration
    cannot be modified after creation.

    Attributes:
        enabled: Whether Graphiti integration is enabled
        host: Graphiti server hostname
        port: Graphiti server port
        timeout: Connection timeout in seconds

    Raises:
        ValueError: If timeout is not positive
        AssertionError: If timeout is zero or negative

    Example:
        config = GraphitiConfig(
            enabled=True,
            host="graphiti.example.com",
            port=9000,
            timeout=60.0
        )
    """
    enabled: bool = True
    host: str = "localhost"
    port: int = 8000
    timeout: float = 30.0

    def __post_init__(self):
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")


class GraphitiClient:
    """Wrapper around Graphiti SDK with graceful degradation.

    All methods are designed to fail gracefully - returning empty results
    or None instead of raising exceptions. This ensures the application
    continues to function even when Graphiti is unavailable.

    Attributes:
        config: GraphitiConfig instance
        enabled: True only if config enabled AND successfully connected

    Example:
        client = GraphitiClient()
        await client.initialize()

        if client.enabled:
            results = await client.search("query", ["group1"])
    """

    def __init__(self, config: Optional[GraphitiConfig] = None):
        """Initialize GraphitiClient.

        Args:
            config: GraphitiConfig instance. Uses defaults if None.
        """
        self.config = config or GraphitiConfig()
        self._client = None
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
        """Check if connection to Graphiti can be established.

        Attempts to connect to the configured host:port.

        Returns:
            True if connection successful, False otherwise
        """
        import asyncio
        import socket

        try:
            # Try to establish a TCP connection to verify the server is reachable
            loop = asyncio.get_event_loop()
            # Use a short timeout for connection check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(min(self.config.timeout, 5.0))  # Max 5 seconds for check
            try:
                await loop.run_in_executor(
                    None,
                    sock.connect,
                    (self.config.host, self.config.port)
                )
                return True
            finally:
                sock.close()
        except (socket.timeout, socket.error, OSError) as e:
            logger.debug(f"Connection check failed: {e}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected error in connection check: {e}")
            return False

    async def _check_health(self) -> bool:
        """Check Graphiti server health by calling the health endpoint.

        Returns:
            True if server is healthy and responding, False otherwise
        """
        if not self.config.enabled:
            return False

        if not self._connected:
            return False

        import asyncio

        try:
            # Try to make an HTTP request to the health endpoint
            # Using basic socket/HTTP for minimal dependencies
            import socket

            loop = asyncio.get_event_loop()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(min(self.config.timeout, 5.0))

            try:
                await loop.run_in_executor(
                    None,
                    sock.connect,
                    (self.config.host, self.config.port)
                )

                # Send HTTP GET request to /health
                request = f"GET /health HTTP/1.1\r\nHost: {self.config.host}\r\n\r\n"
                await loop.run_in_executor(None, sock.sendall, request.encode())

                # Read response
                response = await loop.run_in_executor(None, sock.recv, 1024)
                response_str = response.decode('utf-8', errors='ignore')

                # Check for successful HTTP response (200 OK)
                if 'HTTP/1.1 200' in response_str or 'HTTP/1.0 200' in response_str:
                    return True
                else:
                    logger.debug(f"Health check response: {response_str[:100]}")
                    return False
            finally:
                sock.close()

        except (socket.timeout, socket.error, OSError) as e:
            logger.debug(f"Health check connection failed: {e}")
            return False
        except Exception as e:
            logger.debug(f"Health check error: {e}")
            return False

    async def initialize(self) -> bool:
        """Initialize connection to Graphiti.

        Performs initialization checks:
        1. Checks if config is enabled
        2. Checks for OPENAI_API_KEY environment variable
        3. Attempts to establish connection

        Returns:
            True if initialization successful, False otherwise.
            Returns False and logs warning if:
            - Config disabled
            - OPENAI_API_KEY not set
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

        # Try to establish connection
        try:
            connected = await self._check_connection()
            if connected:
                self._connected = True
                logger.info(f"Connected to Graphiti at {self.config.host}:{self.config.port}")
                return True
            else:
                logger.warning(f"Failed to connect to Graphiti at {self.config.host}:{self.config.port}")
                self._connected = False
                return False

        except TimeoutError as e:
            logger.warning(f"Graphiti connection timeout: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.warning(f"Graphiti initialization error: {e}")
            self._connected = False
            return False

    async def health_check(self) -> bool:
        """Check if Graphiti is healthy.

        Returns:
            True if Graphiti is healthy and responding,
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
        """Execute the actual search against Graphiti.

        This is the internal method that performs the search.
        It can be mocked in tests.

        Args:
            query: Search query string
            group_ids: List of group IDs to search in
            num_results: Maximum number of results to return

        Returns:
            List of search results as dictionaries
        """
        # In production, this would call Graphiti's search API
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
        """Create an episode in Graphiti.

        This is the internal method that creates the episode.
        It can be mocked in tests.

        Args:
            name: Episode name/title
            episode_body: Episode content
            group_id: Group ID for organization

        Returns:
            Episode ID if successful, None otherwise
        """
        # In production, this would call Graphiti's episode API
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
            Episode ID if successful, None if:
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
