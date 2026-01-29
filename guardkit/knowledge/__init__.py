"""
GuardKit Knowledge Graph Integration Module.

This module provides integration with Graphiti, a temporal knowledge graph
for AI systems. It enables GuardKit to maintain persistent memory of:
- Product knowledge and domain concepts
- Command workflows and patterns
- Architecture decisions and rationale
- Task outcomes and episodes (TASK-GI-005)
- Feature overviews for context preservation (TASK-GE-001)

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
    load_feature_overview: Load feature overview for context injection (TASK-GE-001)
    format_context_for_injection: Format context for prompt injection
    ContextFormatterConfig: Configuration for context formatting
    ADRStatus: ADR lifecycle status enum (TASK-GI-004)
    ADRTrigger: ADR trigger source enum (TASK-GI-004)
    ADREntity: Architecture Decision Record entity (TASK-GI-004)
    ADRService: Service for ADR CRUD operations (TASK-GI-004)
    DecisionDetector: Detect significant decisions from Q&A (TASK-GI-004)
    OutcomeType: Enum for outcome types (TASK-GI-005)
    TaskOutcome: Dataclass for task outcomes (TASK-GI-005)
    capture_task_outcome: Capture task outcomes (TASK-GI-005)
    find_similar_task_outcomes: Search for similar outcomes (TASK-GI-005)
    FeatureOverviewEntity: Dataclass for feature identity (TASK-GE-001)
    seed_feature_overview: Seed single feature overview (TASK-GE-001)
    seed_all_feature_overviews: Seed all feature overviews (TASK-GE-001)
    FEATURE_BUILD_OVERVIEW: Predefined feature-build overview (TASK-GE-001)

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

    # Episode capture (TASK-GI-005)
    from guardkit.knowledge import (
        OutcomeType,
        TaskOutcome,
        capture_task_outcome,
        find_similar_task_outcomes,
    )

    outcome_id = await capture_task_outcome(
        outcome_type=OutcomeType.TASK_COMPLETED,
        task_id="TASK-1234",
        task_title="Implement OAuth2",
        task_requirements="Add OAuth2 authentication",
        success=True,
        summary="Successfully implemented"
    )
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
    load_feature_overview,
    load_role_context,
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

from guardkit.knowledge.adr import (
    ADRStatus,
    ADRTrigger,
    ADREntity,
)

from guardkit.knowledge.adr_service import (
    ADRService,
    # record_decision is a method on ADRService, not a standalone function
)

from guardkit.knowledge.decision_detector import (
    DecisionDetector,
)

from guardkit.knowledge.entities.outcome import (
    OutcomeType,
    TaskOutcome,
)

from guardkit.knowledge.entities.feature_overview import (
    FeatureOverviewEntity,
)

from guardkit.knowledge.seed_feature_overviews import (
    seed_feature_overview,
    seed_all_feature_overviews,
    FEATURE_BUILD_OVERVIEW,
)

from guardkit.knowledge.seed_role_constraints import (
    seed_role_constraints,
)

from guardkit.knowledge.facts.role_constraint import (
    RoleConstraintFact,
    PLAYER_CONSTRAINTS,
    COACH_CONSTRAINTS,
)

from guardkit.knowledge.outcome_manager import (
    capture_task_outcome,
    OutcomeManager,
)

from guardkit.knowledge.outcome_queries import (
    find_similar_task_outcomes,
    OutcomeQueries,
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
    "load_feature_overview",
    "load_role_context",
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
    # ADR Lifecycle (TASK-GI-004)
    "ADRStatus",
    "ADRTrigger",
    "ADREntity",
    "ADRService",
    "DecisionDetector",
    # Episode capture (TASK-GI-005)
    "OutcomeType",
    "TaskOutcome",
    "capture_task_outcome",
    "find_similar_task_outcomes",
    "OutcomeManager",
    "OutcomeQueries",
    # Feature overview (TASK-GE-001)
    "FeatureOverviewEntity",
    "seed_feature_overview",
    "seed_all_feature_overviews",
    "FEATURE_BUILD_OVERVIEW",
    # Role constraints (TASK-GE-003)
    "RoleConstraintFact",
    "PLAYER_CONSTRAINTS",
    "COACH_CONSTRAINTS",
    "seed_role_constraints",
]
