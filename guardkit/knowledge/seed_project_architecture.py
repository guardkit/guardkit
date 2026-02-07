"""
Project architecture seeding for GuardKit knowledge graph.

Seeds project architecture knowledge for on-demand retrieval into Graphiti
for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_project_architecture(client) -> None:
    """Seed project architecture knowledge for on-demand retrieval.

    Creates 3 episodes covering:
    - guardkit_project_structure: Directory organization and file locations
    - guardkit_conductor_integration: Conductor.build compatibility
    - guardkit_installation_setup: Installation methods and templates

    Content sourced from root CLAUDE.md (trimmed in TASK-CR-001).

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("guardkit_project_structure", {
            "entity_type": "project_architecture",
            "name": "GuardKit Project Structure",
            "directory_layout": {
                ".claude/": "Configuration (agents, commands, task-plans, rules)",
                "tasks/": "Task management (backlog, in_progress, in_review, blocked, completed)",
                "docs/": "Documentation (guides, workflows, state)",
                "guardkit/": "Python package source code",
                "installer/core/": "Global resources (agents, commands, templates)"
            },
            "key_references": {
                "command_specs": "installer/core/commands/*.md",
                "agent_definitions": "installer/core/agents/*.md",
                "workflow_guides": "docs/guides/*.md, docs/workflows/*.md",
                "stack_templates": "installer/core/templates/*/",
                "rules_patterns": ".claude/rules/"
            }
        }),
        ("guardkit_conductor_integration", {
            "entity_type": "project_architecture",
            "name": "Conductor.build Integration",
            "description": (
                "GuardKit is fully compatible with Conductor.build for parallel development. "
                "Hash-based task IDs (TASK-{hash}) prevent duplicates in concurrent workflows."
            ),
            "features": [
                "Zero ID collisions across parallel worktrees",
                "Safe concurrent task creation",
                "PM tool integration (JIRA, Azure DevOps, Linear, GitHub)",
                "Git worktree isolation for autonomous implementation"
            ],
            "task_id_format": {
                "simple": "TASK-{hash} (e.g., TASK-a3f8)",
                "with_prefix": "TASK-{prefix}-{hash} (e.g., TASK-FIX-a3f8)",
                "with_subtask": "TASK-{prefix}-{hash}.{number} (e.g., TASK-E01-b2c4.1)"
            }
        }),
        ("guardkit_installation_setup", {
            "entity_type": "project_architecture",
            "name": "GuardKit Installation and Setup",
            "installation_methods": {
                "basic": "pip install guardkit-py",
                "autobuild": "pip install guardkit-py[autobuild]",
                "development": "pip install guardkit-py[dev]",
                "initialize": "guardkit init [template-name]"
            },
            "available_templates": [
                "react-typescript",
                "fastapi-python",
                "nextjs-fullstack",
                "react-fastapi-monorepo",
                "default"
            ],
            "mcp_integration": {
                "context7": "Library documentation retrieval (optional)",
                "design_patterns": "Pattern recommendations (optional)",
                "note": "All MCPs are optional - falls back gracefully to training data"
            }
        })
    ]

    await _add_episodes(client, episodes, "project_architecture", "project architecture", entity_type="project_architecture")
