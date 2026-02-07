"""
Agents seeding for GuardKit knowledge graph.

Seeds agent metadata for semantic search into Graphiti for context-aware
AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_agents(client) -> None:
    """Seed agent metadata for semantic search.

    Creates 7+ episodes covering available agents.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("agent_fastapi_specialist", {
            "entity_type": "agent",
            "id": "fastapi-specialist",
            "name": "FastAPI Specialist",
            "role": "Implements FastAPI routes, dependencies, and middleware",
            "capabilities": ["API endpoint implementation", "Dependency injection", "Middleware configuration"],
            "technologies": ["FastAPI", "Pydantic", "Starlette"]
        }),
        ("agent_test_orchestrator", {
            "entity_type": "agent",
            "id": "test-orchestrator",
            "name": "Test Orchestrator",
            "role": "Orchestrates test execution and validates coverage",
            "capabilities": ["Test suite execution", "Coverage measurement", "Test fixture management"],
            "technologies": ["pytest", "pytest-asyncio", "pytest-cov"]
        }),
        ("agent_code_reviewer", {
            "entity_type": "agent",
            "id": "code-reviewer",
            "name": "Code Reviewer",
            "role": "Reviews code for quality, SOLID principles, and best practices",
            "capabilities": ["SOLID validation", "DRY analysis", "YAGNI assessment", "Security review"],
            "technologies": []
        }),
        ("agent_architectural_reviewer", {
            "entity_type": "agent",
            "id": "architectural-reviewer",
            "name": "Architectural Reviewer",
            "role": "Reviews implementation plans for architectural soundness",
            "capabilities": ["Architecture pattern validation", "Layer boundary enforcement", "Dependency analysis"],
            "technologies": []
        }),
        ("agent_autobuild_player", {
            "entity_type": "agent",
            "id": "autobuild-player",
            "name": "AutoBuild Player Agent",
            "role": "Implements tasks by delegating to task-work in Player-Coach pattern",
            "capabilities": ["Task-work delegation", "Implementation reporting", "Quality gate monitoring"],
            "critical_note": "Player MUST delegate to /task-work, NOT implement directly"
        }),
        ("agent_autobuild_coach", {
            "entity_type": "agent",
            "id": "autobuild-coach",
            "name": "AutoBuild Coach Agent",
            "role": "Validates Player implementations in Player-Coach pattern",
            "capabilities": ["Implementation validation", "Independent test execution", "Acceptance criteria verification"],
            "critical_note": "Coach has READ-ONLY access, validates but cannot modify"
        }),
        ("agent_pattern_suggester", {
            "entity_type": "agent",
            "id": "pattern-suggester",
            "name": "Pattern Suggester",
            "role": "Suggests applicable design patterns during planning",
            "capabilities": ["Pattern identification", "Template-specific patterns", "Best practice recommendations"],
            "technologies": []
        })
    ]

    await _add_episodes(client, episodes, "agents", "agents", entity_type="agent")
