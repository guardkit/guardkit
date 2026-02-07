"""
Templates seeding for GuardKit knowledge graph.

Seeds template metadata for semantic search into Graphiti for context-aware
AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_templates(client) -> None:
    """Seed template metadata for semantic search.

    Creates 4+ episodes covering available templates.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("template_fastapi_python", {
            "entity_type": "template",
            "id": "fastapi-python",
            "name": "Python FastAPI Backend",
            "description": "Production-ready FastAPI template based on best practices from 12k+ star repository.",
            "language": "Python",
            "frameworks": ["FastAPI", "SQLAlchemy", "Pydantic", "pytest"],
            "patterns": ["Dependency Injection", "Repository Pattern", "CRUD Base Classes"],
            "complexity": 7,
            "production_ready": True
        }),
        ("template_react_typescript", {
            "entity_type": "template",
            "id": "react-typescript",
            "name": "React TypeScript Frontend",
            "description": "Modern React frontend with TypeScript, hooks, and comprehensive testing.",
            "language": "TypeScript",
            "frameworks": ["React", "TypeScript", "MSW", "Vitest"],
            "patterns": ["Component Composition", "Custom Hooks", "API Layer Abstraction"],
            "complexity": 6,
            "production_ready": True
        }),
        ("template_nextjs_fullstack", {
            "entity_type": "template",
            "id": "nextjs-fullstack",
            "name": "Next.js Fullstack",
            "description": "Full-stack Next.js application with App Router, Server Actions, and Prisma ORM.",
            "language": "TypeScript",
            "frameworks": ["Next.js", "Prisma", "Playwright"],
            "patterns": ["Server Components", "Server Actions", "App Router"],
            "complexity": 8,
            "production_ready": True
        }),
        ("template_default", {
            "entity_type": "template",
            "id": "default",
            "name": "Language-Agnostic Default",
            "description": "Minimal template for any language/framework combination.",
            "language": "Any",
            "frameworks": [],
            "patterns": ["SOLID", "DRY", "YAGNI"],
            "complexity": 3,
            "production_ready": True
        })
    ]

    await _add_episodes(client, episodes, "templates", "templates", entity_type="template")
