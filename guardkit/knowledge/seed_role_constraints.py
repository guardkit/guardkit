"""
Role constraint seeding for Player-Coach pattern enforcement.

This module seeds role constraints into Graphiti to ensure proper
Player-Coach boundaries are maintained during autonomous builds.
"""

import json
import logging
from typing import Optional

from guardkit.knowledge.facts.role_constraint import (
    PLAYER_CONSTRAINTS,
    COACH_CONSTRAINTS,
)

logger = logging.getLogger(__name__)


async def seed_role_constraints(graphiti) -> None:
    """Seed role constraints into Graphiti.

    Creates episodes for Player and Coach role constraints to enable
    runtime enforcement and context injection.

    Args:
        graphiti: GraphitiClient instance (optional, handles None gracefully)

    Example:
        from guardkit.knowledge import get_graphiti
        from guardkit.knowledge.seed_role_constraints import seed_role_constraints

        client = get_graphiti()
        await seed_role_constraints(client)
    """
    # Handle None client gracefully
    if graphiti is None:
        logger.debug("Graphiti client is None, skipping role constraint seeding")
        return

    # Handle disabled client gracefully
    if not graphiti.enabled:
        logger.debug("Graphiti is disabled, skipping role constraint seeding")
        return

    # Prepare episodes
    episodes = [
        (
            f"role_constraint_player_{PLAYER_CONSTRAINTS.context}",
            PLAYER_CONSTRAINTS.to_episode_body()
        ),
        (
            f"role_constraint_coach_{COACH_CONSTRAINTS.context}",
            COACH_CONSTRAINTS.to_episode_body()
        )
    ]

    # Seed episodes with error handling
    for name, body_dict in episodes:
        try:
            await graphiti.add_episode(
                name=name,
                episode_body=json.dumps(body_dict),
                group_id="role_constraints",
                source="guardkit_seeding",
                entity_type="role_constraint"
            )
            logger.info(f"Seeded role constraint: {name}")
        except Exception as e:
            logger.warning(f"Failed to seed role constraint {name}: {e}")
            # Continue with other episodes
