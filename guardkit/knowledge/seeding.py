"""
System context seeding orchestrator for GuardKit knowledge graph.

Coordinates seeding of all knowledge categories into Graphiti. Individual
category implementations live in dedicated seed_*.py modules.

Usage:
    from guardkit.knowledge.seeding import seed_all_system_context
    from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

    client = GraphitiClient(GraphitiConfig())
    await client.initialize()
    await seed_all_system_context(client)
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from guardkit.knowledge.seed_helpers import SEEDING_VERSION, _add_episodes  # noqa: F401

logger = logging.getLogger(__name__)


def get_state_dir() -> Path:
    """Get the state directory for seeding markers.

    Returns:
        Path to the .guardkit/seeding directory, created if needed.
    """
    # Use project-local .guardkit directory
    state_dir = Path.cwd() / ".guardkit" / "seeding"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def is_seeded() -> bool:
    """Check if system context has been seeded.

    Returns:
        True if seeding marker file exists, False otherwise.
    """
    marker_path = get_state_dir() / ".graphiti_seeded.json"
    return marker_path.exists()


def mark_seeded() -> None:
    """Create marker file indicating seeding is complete."""
    marker_path = get_state_dir() / ".graphiti_seeded.json"
    marker_data = {
        "seeded": True,
        "version": SEEDING_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    marker_path.write_text(json.dumps(marker_data, indent=2))
    logger.info(f"Created seeding marker at {marker_path}")


def clear_seeding_marker() -> None:
    """Remove the seeding marker file.

    Safe to call even if marker doesn't exist.
    """
    marker_path = get_state_dir() / ".graphiti_seeded.json"
    if marker_path.exists():
        marker_path.unlink()
        logger.info(f"Removed seeding marker from {marker_path}")


# Re-exports for backward compatibility and getattr() lookup in orchestrator
from guardkit.knowledge.seed_product_knowledge import seed_product_knowledge  # noqa: E402
from guardkit.knowledge.seed_command_workflows import seed_command_workflows  # noqa: E402
from guardkit.knowledge.seed_quality_gate_phases import seed_quality_gate_phases  # noqa: E402
from guardkit.knowledge.seed_technology_stack import seed_technology_stack  # noqa: E402
from guardkit.knowledge.seed_feature_build_architecture import seed_feature_build_architecture  # noqa: E402
from guardkit.knowledge.seed_architecture_decisions import seed_architecture_decisions  # noqa: E402
from guardkit.knowledge.seed_failure_patterns import seed_failure_patterns  # noqa: E402
from guardkit.knowledge.seed_component_status import seed_component_status  # noqa: E402
from guardkit.knowledge.seed_integration_points import seed_integration_points  # noqa: E402
from guardkit.knowledge.seed_templates import seed_templates  # noqa: E402
from guardkit.knowledge.seed_agents import seed_agents  # noqa: E402
from guardkit.knowledge.seed_patterns import seed_patterns  # noqa: E402
from guardkit.knowledge.seed_rules import seed_rules  # noqa: E402
from guardkit.knowledge.seed_project_overview import seed_project_overview  # noqa: E402
from guardkit.knowledge.seed_project_architecture import seed_project_architecture  # noqa: E402


async def seed_pattern_examples_wrapper(client) -> None:
    """Wrapper for seed_pattern_examples to match orchestrator signature."""
    if not client or not client.enabled:
        return
    from guardkit.knowledge.seed_pattern_examples import seed_pattern_examples
    await seed_pattern_examples(client)


async def seed_failed_approaches_wrapper(client) -> None:
    """Wrapper for seed_failed_approaches to match orchestrator signature."""
    if not client or not client.enabled:
        return
    from guardkit.knowledge.seed_failed_approaches import seed_failed_approaches
    await seed_failed_approaches(client)


async def seed_all_system_context(client, force: bool = False) -> bool:
    """Seed all system context into Graphiti.

    Args:
        client: GraphitiClient instance (required)
        force: If True, re-seed even if already seeded

    Returns:
        True if seeding completed (or skipped because already seeded)
        False if client is disabled or None
    """
    # Handle None client
    if client is None:
        logger.warning("Seeding skipped: client is None")
        return False

    # Handle disabled client
    if not client.enabled:
        logger.warning("Seeding skipped: Graphiti client is disabled")
        return False

    # Check if already seeded
    if is_seeded() and not force:
        logger.info("System context already seeded, skipping (use force=True to re-seed)")
        return True

    logger.info("Seeding GuardKit system context...")

    # Track partial failures but continue
    had_errors = False

    # Get the current module dynamically to support patching in tests
    # sys.modules lookup happens at runtime, allowing unittest.mock.patch to work
    seeding_module = sys.modules[__name__]

    # Seed each category with error handling
    categories = [
        ("product_knowledge", "seed_product_knowledge"),
        ("command_workflows", "seed_command_workflows"),
        ("quality_gate_phases", "seed_quality_gate_phases"),
        ("technology_stack", "seed_technology_stack"),
        ("feature_build_architecture", "seed_feature_build_architecture"),
        ("architecture_decisions", "seed_architecture_decisions"),
        ("failure_patterns", "seed_failure_patterns"),
        ("component_status", "seed_component_status"),
        ("integration_points", "seed_integration_points"),
        ("templates", "seed_templates"),
        ("agents", "seed_agents"),
        ("patterns", "seed_patterns"),
        ("rules", "seed_rules"),
        ("project_overview", "seed_project_overview"),  # TASK-CR-005
        ("project_architecture", "seed_project_architecture"),  # TASK-CR-005
        ("failed_approaches", "seed_failed_approaches_wrapper"),  # TASK-GE-004
        ("pattern_examples", "seed_pattern_examples_wrapper"),  # TASK-CR-006-FIX
    ]

    for name, fn_name in categories:
        try:
            # Dynamic lookup enables unittest.mock.patch to work
            seed_fn = getattr(seeding_module, fn_name)
            await seed_fn(client)
            logger.info(f"  Seeded {name}")
        except Exception as e:
            logger.warning(f"  Failed to seed {name}: {e}")
            had_errors = True

    # Mark as seeded even with partial failures
    try:
        mark_seeded()
    except Exception as e:
        logger.warning(f"Failed to create seeding marker: {e}")
        had_errors = True

    if had_errors:
        logger.warning("System context seeding completed with some errors")
    else:
        logger.info("System context seeding complete")

    return True
