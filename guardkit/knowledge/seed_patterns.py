"""
Patterns seeding for GuardKit knowledge graph.

Seeds design pattern knowledge into Graphiti for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_patterns(client) -> None:
    """Seed design pattern knowledge.

    Creates 5+ episodes covering design patterns.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("pattern_dependency_injection", {
            "entity_type": "pattern",
            "id": "dependency_injection",
            "name": "Dependency Injection",
            "category": "structural",
            "description": "Dependencies are provided to a component rather than created by the component itself.",
            "benefits": ["Loose coupling", "Easy testing", "Flexible configuration"],
            "templates_using": ["fastapi-python", "nextjs-fullstack"]
        }),
        ("pattern_repository", {
            "entity_type": "pattern",
            "id": "repository_pattern",
            "name": "Repository Pattern",
            "category": "data_access",
            "description": "Abstracts data access logic into dedicated classes.",
            "benefits": ["Clean separation", "Easy to swap data sources", "Testable"],
            "templates_using": ["fastapi-python"]
        }),
        ("pattern_crud_base", {
            "entity_type": "pattern",
            "id": "crud_base_classes",
            "name": "CRUD Base Classes",
            "category": "data_access",
            "description": "Generic base classes for Create, Read, Update, Delete operations.",
            "benefits": ["DRY", "Consistent API", "Type-safe with generics"],
            "templates_using": ["fastapi-python"]
        }),
        ("pattern_server_components", {
            "entity_type": "pattern",
            "id": "server_components",
            "name": "Server Components",
            "category": "rendering",
            "description": "React components that render on the server.",
            "benefits": ["Reduced client bundle", "Direct database access", "Better SEO"],
            "templates_using": ["nextjs-fullstack"]
        }),
        ("pattern_player_coach", {
            "entity_type": "pattern",
            "id": "player_coach_adversarial",
            "name": "Player-Coach Adversarial Pattern",
            "category": "agent_orchestration",
            "description": "Adversarial cooperation where Player implements and Coach validates.",
            "benefits": ["Quality assurance", "Iterative improvement", "Trust but verify"],
            "templates_using": ["guardkit-default"]
        })
    ]

    await _add_episodes(client, episodes, "patterns", "patterns", entity_type="pattern")
