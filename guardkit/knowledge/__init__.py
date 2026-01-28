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
    CriticalContext: Dataclass for session context (TASK-GI-003)
    load_critical_context: Load context at session/command start
    format_context_for_injection: Format context for prompt injection
    ContextFormatterConfig: Configuration for context formatting

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

    # Session context loading (TASK-GI-003)
    from guardkit.knowledge import (
        load_critical_context,
        format_context_for_injection,
    )

    context = await load_critical_context(command="feature-build")
    context_text = format_context_for_injection(context)
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

from guardkit.knowledge.context_loader import (
    CriticalContext,
    load_critical_context,
)

from guardkit.knowledge.context_formatter import (
    format_context_for_injection,
    ContextFormatterConfig,
)

from guardkit.knowledge.seeding import (
    # Marker management
    is_seeded,
    mark_seeded,
    clear_seeding_marker,
    get_state_dir,
    # Individual seeding functions
    seed_product_knowledge,
    seed_command_workflows,
    seed_quality_gate_phases,
    seed_technology_stack,
    seed_feature_build_architecture,
    seed_architecture_decisions,
    seed_failure_patterns,
    seed_component_status,
    seed_integration_points,
    seed_templates,
    seed_agents,
    seed_patterns,
    seed_rules,
    # Orchestrator
    seed_all_system_context,
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
    # Context loading (TASK-GI-003)
    "CriticalContext",
    "load_critical_context",
    "format_context_for_injection",
    "ContextFormatterConfig",
    # Seeding - Marker management
    "is_seeded",
    "mark_seeded",
    "clear_seeding_marker",
    "get_state_dir",
    # Seeding - Individual functions
    "seed_product_knowledge",
    "seed_command_workflows",
    "seed_quality_gate_phases",
    "seed_technology_stack",
    "seed_feature_build_architecture",
    "seed_architecture_decisions",
    "seed_failure_patterns",
    "seed_component_status",
    "seed_integration_points",
    "seed_templates",
    "seed_agents",
    "seed_patterns",
    "seed_rules",
    # Seeding - Orchestrator
    "seed_all_system_context",
]
