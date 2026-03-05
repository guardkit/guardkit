"""
System content seeding module for GuardKit knowledge graph.

Orchestrates seeding of system-level (non-project-specific) content into
Graphiti. Decoupled from ``guardkit init`` so it can be run independently
via ``guardkit graphiti seed-system``.

Seeding Groups:
- templates: Template manifest metadata
- agents: Agent metadata from .claude/agents/*.md
- rules: Rule previews (500 chars) from .claude/rules/*.md
- role_constraints: Player/Coach constraints
- implementation_modes: Direct/task-work/manual modes

All seeding uses ``upsert_episode`` for idempotency and sequential
execution for reliability.

Coverage Target: >=85%
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

SYSTEM_SEED_MARKER = ".system_seeded.json"
SYSTEM_SEED_VERSION = "1.0.0"


# ============================================================================
# RESULT DATACLASSES
# ============================================================================


@dataclass
class SystemSeedComponentResult:
    """Result for a single system seeding component."""

    component: str
    success: bool
    message: str = ""
    episodes_created: int = 0
    episodes_skipped: int = 0


@dataclass
class SystemSeedResult:
    """Result of system content seeding operation."""

    success: bool
    results: List[SystemSeedComponentResult] = field(default_factory=list)
    template_name: str = ""
    total_episodes: int = 0
    total_skipped: int = 0

    def add_result(self, result: SystemSeedComponentResult) -> None:
        """Add a component result and update totals."""
        self.results.append(result)
        self.total_episodes += result.episodes_created
        self.total_skipped += result.episodes_skipped
        if not result.success:
            self.success = False


# ============================================================================
# SEEDING MARKER
# ============================================================================


def _get_marker_path() -> Path:
    """Get path to the system seed marker file.

    Returns:
        Path to ``.guardkit/seeding/.system_seeded.json``.
    """
    state_dir = Path.cwd() / ".guardkit" / "seeding"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / SYSTEM_SEED_MARKER


def is_system_seeded() -> bool:
    """Check if system content has already been seeded.

    Returns:
        True if marker file exists.
    """
    return _get_marker_path().exists()


def mark_system_seeded(template_name: str, result: SystemSeedResult) -> None:
    """Create marker file indicating system seeding is complete.

    Args:
        template_name: Name of the template that was seeded.
        result: SystemSeedResult with episode counts.
    """
    marker_data = {
        "seeded": True,
        "version": SYSTEM_SEED_VERSION,
        "template": template_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "episodes_created": result.total_episodes,
    }
    _get_marker_path().write_text(json.dumps(marker_data, indent=2))
    logger.info("Created system seed marker")


def clear_system_seed_marker() -> None:
    """Remove the system seed marker file.

    Safe to call even if marker does not exist.
    """
    path = _get_marker_path()
    if path.exists():
        path.unlink()
        logger.info("Removed system seed marker")


# ============================================================================
# TEMPLATE RESOLUTION
# ============================================================================


def resolve_template_path(template_name: Optional[str] = None) -> Optional[Path]:
    """Resolve template source directory for seeding.

    Resolution order:
    1. Explicit ``template_name`` argument.
    2. Auto-detect from ``manifest.json`` in cwd.
    3. Fallback to ``"default"`` template.

    Args:
        template_name: Explicit template name, or None for auto-detect.

    Returns:
        Path to template source directory, or None if not found.
    """
    from guardkit.cli.init import _resolve_template_source_dir

    if template_name:
        return _resolve_template_source_dir(template_name)

    # Try auto-detection from local manifest
    local_manifest = Path.cwd() / "manifest.json"
    if local_manifest.exists():
        try:
            manifest = json.loads(local_manifest.read_text())
            detected_name = manifest.get("name")
            if detected_name:
                resolved = _resolve_template_source_dir(detected_name)
                if resolved:
                    return resolved
        except json.JSONDecodeError:
            logger.debug("manifest.json is not valid JSON, falling back to default")
        except Exception as e:
            logger.debug(f"Failed to read manifest.json: {e}, falling back to default")

    # Fallback to default template
    return _resolve_template_source_dir("default")


# ============================================================================
# ROLE CONSTRAINTS (upsert-based)
# ============================================================================


async def _seed_role_constraints_upsert(client: Any) -> SystemSeedComponentResult:
    """Seed role constraints using ``upsert_episode`` for idempotency.

    The existing ``seed_role_constraints`` function uses ``add_episode``,
    which creates duplicates on re-run. This wrapper uses ``upsert_episode``
    to match the acceptance criteria for seed-system.

    Args:
        client: GraphitiClient instance.

    Returns:
        SystemSeedComponentResult with seeding outcome.
    """
    if client is None or not client.enabled:
        return SystemSeedComponentResult(
            component="role_constraints",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    from guardkit.knowledge.facts.role_constraint import (
        PLAYER_CONSTRAINTS,
        COACH_CONSTRAINTS,
    )

    episodes_created = 0
    episodes_skipped = 0

    constraints = [
        ("player", PLAYER_CONSTRAINTS),
        ("coach", COACH_CONSTRAINTS),
    ]

    for role_name, constraint in constraints:
        try:
            episode_name = f"role_constraint_{role_name}_{constraint.context}"
            episode_body = json.dumps(constraint.to_episode_body())

            result = await client.upsert_episode(
                name=episode_name,
                episode_body=episode_body,
                group_id="role_constraints",
                entity_id=episode_name,
                scope="system",
            )
            if result is not None and getattr(result, "was_skipped", False):
                episodes_skipped += 1
            elif result is not None:
                episodes_created += 1
        except Exception as e:
            logger.warning(f"Failed to seed {role_name} constraints: {e}")

    return SystemSeedComponentResult(
        component="role_constraints",
        success=True,
        message=f"Seeded {episodes_created}, {episodes_skipped} unchanged",
        episodes_created=episodes_created,
        episodes_skipped=episodes_skipped,
    )


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================


async def seed_system_content(
    client: Any,
    template_name: Optional[str] = None,
    force: bool = False,
) -> SystemSeedResult:
    """Seed all system-level content to Graphiti.

    Orchestrates sequential seeding of:
    1. Template manifest + agents + rules (via ``sync_template_to_graphiti``)
    2. Role constraints (Player/Coach defaults, via upsert)
    3. Implementation modes (direct/task-work/manual)

    Args:
        client: GraphitiClient instance.
        template_name: Template to seed. Auto-detected if not provided.
        force: If True, re-seed regardless of existing marker.

    Returns:
        SystemSeedResult with per-component results.
    """
    result = SystemSeedResult(success=True)

    # Check marker unless forcing
    if is_system_seeded() and not force:
        result.results.append(
            SystemSeedComponentResult(
                component="all",
                success=True,
                message="Already seeded (use --force to re-seed)",
            )
        )
        return result

    if client is None or not client.enabled:
        result.success = False
        result.results.append(
            SystemSeedComponentResult(
                component="all",
                success=False,
                message="Graphiti client unavailable or disabled",
            )
        )
        return result

    # Resolve template path
    template_path = resolve_template_path(template_name)
    resolved_name = template_name or "default"

    if template_path:
        resolved_name = template_path.name
    result.template_name = resolved_name

    # 1. Sync template content (manifest + agents + rules) sequentially
    if template_path:
        from guardkit.knowledge.template_sync import sync_template_to_graphiti

        try:
            sync_success = await sync_template_to_graphiti(
                template_path, client=client
            )
            result.add_result(
                SystemSeedComponentResult(
                    component="template_content",
                    success=sync_success,
                    message=(
                        f"Synced template '{resolved_name}'"
                        if sync_success
                        else f"Template sync incomplete for '{resolved_name}'"
                    ),
                    episodes_created=1 if sync_success else 0,
                )
            )
        except Exception as e:
            logger.warning(f"Template sync failed: {e}")
            result.add_result(
                SystemSeedComponentResult(
                    component="template_content",
                    success=False,
                    message=f"Error: {e}",
                )
            )
    else:
        result.add_result(
            SystemSeedComponentResult(
                component="template_content",
                success=True,
                message="Skipped (no template found)",
            )
        )

    # 2. Seed role constraints (using upsert)
    constraints_result = await _seed_role_constraints_upsert(client)
    result.add_result(constraints_result)

    # 3. Seed implementation modes
    from guardkit.knowledge.project_seeding import (
        seed_implementation_modes_from_defaults,
    )

    modes_result = await seed_implementation_modes_from_defaults(
        project_name="system",
        client=client,
    )
    result.add_result(
        SystemSeedComponentResult(
            component="implementation_modes",
            success=modes_result.success,
            message=modes_result.message,
            episodes_created=modes_result.episodes_created,
        )
    )

    # Write marker (caller is responsible for clearing marker before force re-seed)
    try:
        mark_system_seeded(resolved_name, result)
    except Exception as e:
        logger.warning(f"Failed to create system seed marker: {e}")

    return result
