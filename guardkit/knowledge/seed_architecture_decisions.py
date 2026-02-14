"""
Architecture decisions seeding for GuardKit knowledge graph.

Seeds key architecture decisions into Graphiti for context-aware AI assistance.
Delegates to seed_feature_build_adrs for full ADR content including context,
rejected alternatives, and violation symptoms.
"""

import logging

logger = logging.getLogger(__name__)


async def seed_architecture_decisions(client) -> None:
    """Seed key architecture decisions.

    Delegates to seed_feature_build_adrs() which provides full ADR content
    including context, rejected alternatives, and violation symptoms.

    Creates 3 episodes covering critical design decisions:
    - ADR-FB-001: Use SDK query() for task-work invocation
    - ADR-FB-002: In feature mode, paths use FEAT-XXX worktree ID
    - ADR-FB-003: Pre-loop must invoke /task-work --design-only

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    from guardkit.knowledge.seed_feature_build_adrs import seed_feature_build_adrs

    await seed_feature_build_adrs(client)
