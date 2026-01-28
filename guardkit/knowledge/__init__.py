"""
GuardKit Knowledge Graph Integration Module.

This module provides integration with Graphiti, a temporal knowledge graph
for AI systems. It enables GuardKit to maintain persistent memory of:
- Product knowledge and domain concepts
- Command workflows and patterns
- Architecture decisions and rationale

All components are designed for graceful degradation - the system continues
to function normally when Graphiti is unavailable.

Public API:
    GraphitiConfig: Configuration dataclass for client connection
    GraphitiClient: Main client wrapper with graceful degradation
    GraphitiSettings: Settings loaded from YAML configuration
    init_graphiti: Initialize the global client singleton
    get_graphiti: Get the global client instance
    load_graphiti_config: Load configuration from YAML file
    get_config_path: Get the path to the config file

Example:
    from guardkit.knowledge import (
        GraphitiConfig,
        GraphitiClient,
        init_graphiti,
        get_graphiti,
    )

    # Initialize with default config
    await init_graphiti()

    # Or with custom config
    config = GraphitiConfig(host="graphiti.example.com", port=9000)
    client = GraphitiClient(config)
    await client.initialize()

    if client.enabled:
        results = await client.search("authentication patterns")
"""

from guardkit.knowledge.graphiti_client import (
    GraphitiConfig,
    GraphitiClient,
    init_graphiti,
    get_graphiti,
)

from guardkit.knowledge.config import (
    GraphitiSettings,
    load_graphiti_config,
    get_config_path,
)

__all__ = [
    # Client classes
    "GraphitiConfig",
    "GraphitiClient",
    # Singleton functions
    "init_graphiti",
    "get_graphiti",
    # Configuration
    "GraphitiSettings",
    "load_graphiti_config",
    "get_config_path",
]
