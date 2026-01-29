"""
Feature overview seeding module for GuardKit knowledge graph.

Seeds Graphiti with feature overview entities that capture the "big picture"
of major features. This prevents context loss by ensuring sessions always
know what a feature IS and IS NOT.

Public API:
    seed_feature_overview: Seed a single feature overview
    seed_all_feature_overviews: Seed all predefined feature overviews
    FEATURE_BUILD_OVERVIEW: Predefined feature-build overview entity

Usage:
    from guardkit.knowledge.seed_feature_overviews import (
        seed_all_feature_overviews,
        FEATURE_BUILD_OVERVIEW,
    )

    # Seed all feature overviews
    await seed_all_feature_overviews(graphiti_client)

    # Or seed a specific overview
    from guardkit.knowledge.seed_feature_overviews import seed_feature_overview
    await seed_feature_overview(graphiti_client, FEATURE_BUILD_OVERVIEW)
"""

import json
import logging
from typing import Optional

from guardkit.knowledge.entities.feature_overview import FeatureOverviewEntity

logger = logging.getLogger(__name__)


# =============================================================================
# PREDEFINED FEATURE OVERVIEWS
# =============================================================================

FEATURE_BUILD_OVERVIEW = FeatureOverviewEntity(
    id="feature-build",
    name="feature-build",
    tagline="Autonomous task implementation with Player-Coach validation",

    purpose=(
        "Execute multi-task features autonomously using the Player-Coach "
        "adversarial pattern, preserving worktrees for human review"
    ),

    what_it_is=[
        "An autonomous orchestrator that runs tasks without human guidance",
        "A quality enforcement system using Player-Coach validation",
        "A worktree-based isolation system for parallel development"
    ],

    what_it_is_not=[
        "NOT an assistant that asks for guidance mid-feature",
        "NOT a code reviewer (that's the Coach's job)",
        "NOT a human replacement (prepares work for human approval)",
        "NOT an auto-merger (preserves worktrees for human review)"
    ],

    invariants=[
        "Player implements, Coach validates - NEVER reverse roles",
        "Implementation plans are REQUIRED before Player runs",
        "Quality gates are task-type specific (scaffolding != feature)",
        "State recovery takes precedence over fresh starts",
        "Wave N depends on Wave N-1 completion",
        "Worktrees preserved for human review - NEVER auto-merge"
    ],

    architecture_summary=(
        "Feature-build orchestrates multiple tasks in waves. Each task uses "
        "the Player-Coach pattern: Player implements code, Coach validates "
        "against quality gates. Tasks run in isolated worktrees that are "
        "preserved for human review."
    ),

    key_components=[
        "FeatureOrchestrator - Wave execution",
        "AutoBuildOrchestrator - Player-Coach loop",
        "CoachValidator - Quality gate checks",
        "TaskWorkInterface - Pre-loop design phase"
    ],

    key_decisions=[
        "ADR-FB-001",  # SDK query() not subprocess
        "ADR-FB-002",  # FEAT-XXX paths not TASK-XXX
        "ADR-FB-003"   # Pre-loop must invoke real task-work
    ]
)


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

async def seed_feature_overview(
    client,
    overview: FeatureOverviewEntity
) -> None:
    """Seed a feature overview into Graphiti.

    Args:
        client: GraphitiClient instance (can be None or disabled)
        overview: FeatureOverviewEntity to seed

    Returns:
        None (graceful degradation if client unavailable)
    """
    if client is None:
        logger.debug("Skipping feature overview seeding - client is None")
        return

    if not client.enabled:
        logger.debug("Skipping feature overview seeding - client disabled")
        return

    try:
        episode_name = f"feature_overview_{overview.id}"
        episode_body = json.dumps(overview.to_episode_body())

        await client.add_episode(
            name=episode_name,
            episode_body=episode_body,
            group_id="feature_overviews"
        )

        logger.info(f"Seeded feature overview: {overview.id}")

    except Exception as e:
        logger.warning(f"Failed to seed feature overview {overview.id}: {e}")
        # Graceful degradation - don't crash


async def seed_all_feature_overviews(client) -> None:
    """Seed all predefined feature overviews into Graphiti.

    Args:
        client: GraphitiClient instance (can be None or disabled)

    Returns:
        None (graceful degradation if client unavailable)
    """
    if client is None:
        logger.debug("Skipping all feature overview seeding - client is None")
        return

    if not client.enabled:
        logger.debug("Skipping all feature overview seeding - client disabled")
        return

    # List of all predefined feature overviews
    overviews = [
        FEATURE_BUILD_OVERVIEW,
        # Add more feature overviews here as they are defined
    ]

    logger.info(f"Seeding {len(overviews)} feature overviews...")

    for overview in overviews:
        await seed_feature_overview(client, overview)

    logger.info("Feature overview seeding complete")
