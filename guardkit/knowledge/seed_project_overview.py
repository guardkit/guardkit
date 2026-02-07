"""
Project overview seeding for GuardKit knowledge graph.

Seeds project overview knowledge for on-demand retrieval into Graphiti
for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_project_overview(client) -> None:
    """Seed project overview knowledge for on-demand retrieval.

    Creates 3 episodes covering:
    - guardkit_purpose: Project tagline, description, core features
    - guardkit_core_principles: 5 core principles with descriptions
    - guardkit_target_users: Target users, use cases, when to use RequireKit

    Content sourced from root CLAUDE.md (trimmed in TASK-CR-001).

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("guardkit_purpose", {
            "entity_type": "project_overview",
            "name": "GuardKit Purpose and Core Features",
            "tagline": "Lightweight AI-Assisted Development with Quality Gates",
            "description": (
                "GuardKit is a lightweight, pragmatic task workflow system with built-in "
                "quality gates that prevents broken code from reaching production."
            ),
            "core_features": [
                "Quality Gates (Phase 2.5 + 4.5) - Architectural review and test enforcement",
                "Simple Workflow (Create -> Work -> Complete) - 3 commands",
                "AI Collaboration - AI does heavy lifting, humans make decisions",
                "Zero Ceremony - No unnecessary documentation or process"
            ],
            "key_commands": {
                "core": "/task-create, /task-work, /task-complete, /task-status",
                "review": "/task-create task_type:review, /task-review",
                "feature": "/feature-plan, /feature-build, /feature-complete",
                "design_first": "/task-work --design-only, /task-work --implement-only"
            }
        }),
        ("guardkit_core_principles", {
            "entity_type": "project_overview",
            "name": "GuardKit Core Principles",
            "principles": {
                "quality_first": "Never compromise on test coverage or architecture",
                "pragmatic_approach": "Right amount of process for task complexity",
                "ai_human_collaboration": "AI does heavy lifting, humans make decisions",
                "zero_ceremony": "No unnecessary documentation or process",
                "fail_fast": "Block bad code early, don't let it reach production"
            },
            "key_insight": (
                "The value is not in generating code faster, but in preventing "
                "broken code from reaching production"
            )
        }),
        ("guardkit_target_users", {
            "entity_type": "project_overview",
            "name": "GuardKit Target Users and Use Cases",
            "target_users": [
                "Solo developers using AI-assisted development",
                "Small teams needing lightweight quality gates",
                "AI-augmented development workflows"
            ],
            "use_cases": [
                "Task-based development with quality enforcement",
                "Feature planning with automatic subtask generation",
                "Autonomous implementation via AutoBuild Player-Coach pattern",
                "Design-first workflow for complex tasks"
            ],
            "requirekit_integration": (
                "For formal agentic system development (LangGraph, multi-agent coordination), "
                "GuardKit integrates with RequireKit for EARS notation, BDD scenarios, "
                "and requirements traceability."
            )
        })
    ]

    await _add_episodes(client, episodes, "project_overview", "project overview", entity_type="project_overview")
