"""
Product knowledge seeding for GuardKit knowledge graph.

Seeds core product knowledge about GuardKit - what it is, its value
proposition, and installation methods - into Graphiti for context-aware
AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_product_knowledge(client) -> None:
    """Seed core product knowledge about GuardKit.

    Creates 3 episodes:
    - guardkit_overview: What GuardKit is
    - guardkit_value_proposition: Why it exists
    - guardkit_installation: How to install

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("guardkit_overview", {
            "entity_type": "product",
            "name": "GuardKit",
            "tagline": "Lightweight AI-Assisted Development with Quality Gates",
            "description": (
                "GuardKit is a lightweight, pragmatic task workflow system with built-in "
                "quality gates that prevents broken code from reaching production. It bridges "
                "the gap between AI capabilities and human oversight.\n\n"
                "Core Features:\n"
                "- Quality Gates: Architectural review (Phase 2.5) and test enforcement (Phase 4.5)\n"
                "- Simple Workflow: Create -> Work -> Complete (3 commands)\n"
                "- AI Collaboration: AI handles implementation, humans make decisions\n"
                "- No Ceremony: Minimal process, maximum productivity"
            ),
            "target_users": ["solo developers", "small teams", "AI-augmented development"],
            "competitive_differentiator": "Quality gates that prevent broken code, not just task management"
        }),
        ("guardkit_value_proposition", {
            "entity_type": "value_prop",
            "problem": "AI coding assistants can generate code quickly but often produce broken, untested, or architecturally unsound code",
            "solution": "Quality gates that enforce test coverage and architectural review before code can be marked complete",
            "key_insight": "The value is not in generating code faster, but in preventing broken code from reaching production",
            "workflow": "AI handles implementation grunt work, humans make approval decisions at checkpoints"
        }),
        ("guardkit_installation", {
            "entity_type": "installation",
            "method": "Claude Code installer",
            "command": "/project:add-guardkit or manual installation",
            "creates": [
                ".claude/commands/*.md - Slash commands",
                ".claude/agents/*.md - Subagent definitions",
                ".claude/templates/ - Stack-specific templates",
                "tasks/ - Task directory structure"
            ],
            "note": "GuardKit installs INTO a project, it's not a standalone tool"
        })
    ]

    await _add_episodes(client, episodes, "product_knowledge", "product knowledge", entity_type="product_knowledge")
