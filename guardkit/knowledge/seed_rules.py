"""
Rules seeding for GuardKit knowledge graph.

Seeds rule metadata for semantic search into Graphiti for context-aware
AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_rules(client) -> None:
    """Seed rule metadata for semantic search.

    Creates 4+ episodes covering code rules.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("rule_fastapi_code_style", {
            "entity_type": "rule",
            "id": "fastapi-python_code-style",
            "name": "Python Code Style",
            "template_id": "fastapi-python",
            "path_patterns": ["**/*.py"],
            "topics": ["naming conventions", "module structure", "class patterns"],
            "key_rules": [
                "Use snake_case for functions and variables",
                "Use PascalCase for classes",
                "Use get_ prefix for dependency functions"
            ]
        }),
        ("rule_fastapi_async", {
            "entity_type": "rule",
            "id": "fastapi-python_async-patterns",
            "name": "Async Patterns",
            "template_id": "fastapi-python",
            "path_patterns": ["**/*.py"],
            "topics": ["async/await", "non-blocking I/O", "database sessions"],
            "key_rules": [
                "Use async def for I/O-bound routes",
                "Never use blocking I/O in async routes",
                "Use asyncio.sleep() not time.sleep() in async context"
            ]
        }),
        ("rule_fastapi_testing", {
            "entity_type": "rule",
            "id": "fastapi-python_testing",
            "name": "Testing Patterns",
            "template_id": "fastapi-python",
            "path_patterns": ["tests/**/*.py", "**/test_*.py"],
            "topics": ["pytest", "async testing", "fixtures"],
            "key_rules": [
                "Use @pytest.mark.asyncio for async tests",
                "Use httpx.AsyncClient for API testing",
                "Clean up test database after each test"
            ],
            "coverage_requirements": {
                "minimum_line": 80,
                "minimum_branch": 75
            }
        }),
        ("rule_react_component_patterns", {
            "entity_type": "rule",
            "id": "react-typescript_components",
            "name": "React Component Patterns",
            "template_id": "react-typescript",
            "path_patterns": ["**/*.tsx", "**/*.jsx"],
            "topics": ["component structure", "hooks", "props typing"],
            "key_rules": [
                "Use function components with hooks",
                "Define prop types with interfaces",
                "Extract custom hooks for reusable logic",
                "Use TypeScript strict mode"
            ]
        })
    ]

    await _add_episodes(client, episodes, "rules", "rules", entity_type="rule")
