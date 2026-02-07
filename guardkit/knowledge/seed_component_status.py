"""
Component status seeding for GuardKit knowledge graph.

Seeds component status tracking into Graphiti for context-aware AI assistance.
"""

import logging

from guardkit.knowledge.seed_helpers import _add_episodes

logger = logging.getLogger(__name__)


async def seed_component_status(client) -> None:
    """Seed component status tracking.

    Creates 2 episodes covering incomplete components.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    episodes = [
        ("component_taskwork_interface", {
            "issue_type": "component_status",
            "component": "TaskWorkInterface",
            "method": "execute_design_phase",
            "status": "stub",
            "notes": "Returns mock data (complexity=5, arch_score=80). Needs SDK query() integration to invoke /task-work --design-only."
        }),
        ("component_agent_invoker_delegation", {
            "issue_type": "component_status",
            "component": "AgentInvoker",
            "method": "_invoke_task_work_implement",
            "status": "incorrect",
            "problem": "Uses subprocess to non-existent CLI command",
            "needs": "SDK query() with slash command in prompt"
        })
    ]

    await _add_episodes(client, episodes, "component_status", "component status", entity_type="component_status")
