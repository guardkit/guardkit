"""
Shared helpers for seeding modules.

Provides the _add_episodes helper and SEEDING_VERSION constant used by
all seed_*.py modules. Extracted to avoid circular imports between
seeding.py (orchestrator) and individual seed modules.
"""

import json
import logging

logger = logging.getLogger(__name__)

# Version for tracking seeding updates
SEEDING_VERSION = "1.2.0"


async def _add_episodes(
    client,
    episodes: list,
    group_id: str,
    category_name: str,
    entity_type: str = "generic"
) -> tuple[int, int]:
    """Add multiple episodes to Graphiti with error handling.

    Metadata injection is handled by GraphitiClient.add_episode() via
    the source and entity_type parameters.

    Args:
        client: GraphitiClient instance
        episodes: List of (name, body_dict) tuples
        group_id: Group ID for all episodes
        category_name: Human-readable category name for logging
        entity_type: Type of entity (e.g., "rule", "pattern", "agent")

    Returns:
        Tuple of (created_count, skipped_count).
    """
    if not client.enabled:
        logger.debug(f"Skipping {category_name} seeding - client disabled")
        return (0, 0)

    created = 0
    skipped = 0
    for name, body in episodes:
        try:
            result = await client.add_episode(
                name=name,
                episode_body=json.dumps(body),
                group_id=group_id,
                source="guardkit_seeding",
                entity_type=entity_type
            )
            if result is not None:
                created += 1
            else:
                skipped += 1
        except Exception as e:
            logger.warning(f"Failed to seed episode {name}: {e}")
            skipped += 1
    return (created, skipped)
