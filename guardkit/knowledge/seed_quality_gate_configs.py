"""
Quality Gate Configuration seeding for Graphiti knowledge graph.

This module seeds quality gate configurations into Graphiti to enable
task-type and complexity-based threshold queries.
"""

import json
import logging
from typing import Optional

from guardkit.knowledge.facts.quality_gate_config import (
    QUALITY_GATE_CONFIGS,
)

logger = logging.getLogger(__name__)


async def seed_quality_gate_configs(graphiti) -> None:
    """Seed quality gate configurations into Graphiti.

    Creates episodes for all predefined quality gate configurations
    to enable runtime queries based on task type and complexity.

    Args:
        graphiti: GraphitiClient instance (optional, handles None gracefully)

    Example:
        from guardkit.knowledge import get_graphiti
        from guardkit.knowledge.seed_quality_gate_configs import seed_quality_gate_configs

        client = get_graphiti()
        await seed_quality_gate_configs(client)
    """
    # Handle None client gracefully
    if graphiti is None:
        logger.debug("Graphiti client is None, skipping quality gate config seeding")
        return

    # Handle disabled client gracefully
    if not graphiti.enabled:
        logger.debug("Graphiti is disabled, skipping quality gate config seeding")
        return

    # Seed each configuration as an episode
    for config in QUALITY_GATE_CONFIGS:
        try:
            # Convert to episode body and serialize
            body_dict = config.to_episode_body()

            # Convert tuple to list for JSON serialization
            if isinstance(body_dict.get("complexity_range"), tuple):
                body_dict["complexity_range"] = list(body_dict["complexity_range"])

            episode_body = json.dumps(body_dict)

            await graphiti.add_episode(
                name=f"quality_gate_config_{config.id}",
                episode_body=episode_body,
                group_id="quality_gate_configs",
                source="guardkit_seeding",
                entity_type="quality_gate_config"
            )
            logger.info(f"Seeded quality gate config: {config.id}")
        except Exception as e:
            logger.warning(f"Failed to seed quality gate config {config.id}: {e}")
            # Continue with other configs
