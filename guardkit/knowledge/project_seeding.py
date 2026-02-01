"""
Project knowledge seeding module for GuardKit init command.

This module orchestrates seeding of project knowledge into Graphiti during
project initialization. It coordinates:
- Project overview parsing from CLAUDE.md or README.md
- Role constraints seeding
- Quality gate configurations seeding
- Implementation modes seeding

Graceful Degradation:
When Graphiti is unavailable or disabled, all operations return success
without attempting to seed, enabling project initialization to proceed.

Coverage Target: >=85%
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardkit.integrations.graphiti.episodes.implementation_mode import (
    IMPLEMENTATION_MODE_DEFAULTS,
)
from guardkit.integrations.graphiti.parsers.project_doc_parser import ProjectDocParser
from guardkit.knowledge.seed_quality_gate_configs import seed_quality_gate_configs
from guardkit.knowledge.seed_role_constraints import seed_role_constraints

logger = logging.getLogger(__name__)


@dataclass
class SeedComponentResult:
    """Result for a single seeding component."""

    component: str
    success: bool
    message: str = ""
    episodes_created: int = 0


@dataclass
class SeedResult:
    """Result of project knowledge seeding operation."""

    success: bool
    results: List[SeedComponentResult] = field(default_factory=list)
    project_name: str = ""

    # Convenience flags for what was seeded
    project_overview_seeded: bool = False
    role_constraints_seeded: bool = False
    quality_gates_seeded: bool = False
    implementation_modes_seeded: bool = False

    def add_result(self, result: SeedComponentResult) -> None:
        """Add a component result to the results list."""
        self.results.append(result)


async def seed_project_overview(
    project_name: str,
    client: Any,
    project_dir: Optional[Path] = None,
) -> SeedComponentResult:
    """Seed project overview from CLAUDE.md or README.md.

    Parses project documentation files to extract and seed project overview
    information into Graphiti.

    Args:
        project_name: Name of the project.
        client: GraphitiClient instance.
        project_dir: Project directory (defaults to cwd).

    Returns:
        SeedComponentResult indicating success/failure.
    """
    if client is None or not client.enabled:
        return SeedComponentResult(
            component="project_overview",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    project_dir = project_dir or Path.cwd()

    # Try CLAUDE.md first, then README.md
    doc_files = ["CLAUDE.md", "README.md", "claude.md", "readme.md"]
    doc_content = None
    doc_path = None

    for filename in doc_files:
        filepath = project_dir / filename
        if filepath.exists():
            doc_content = filepath.read_text()
            doc_path = str(filepath)
            break

    if not doc_content:
        return SeedComponentResult(
            component="project_overview",
            success=True,  # Not a failure, just no doc to parse
            message="No CLAUDE.md or README.md found",
            episodes_created=0,
        )

    # Parse the document
    parser = ProjectDocParser()

    if not parser.can_parse(doc_content, doc_path):
        return SeedComponentResult(
            component="project_overview",
            success=True,
            message=f"Cannot parse {doc_path}",
            episodes_created=0,
        )

    try:
        parse_result = parser.parse(doc_content, doc_path)

        if not parse_result.success:
            return SeedComponentResult(
                component="project_overview",
                success=True,  # Graceful degradation
                message=f"Parse warnings: {', '.join(parse_result.warnings)}",
                episodes_created=0,
            )

        # Seed each parsed episode
        episodes_created = 0
        for episode_data in parse_result.episodes:
            try:
                episode_body = json.dumps(
                    {
                        "entity_type": episode_data.entity_type,
                        "content": episode_data.content,
                        "metadata": episode_data.metadata,
                        "project_name": project_name,
                    }
                )

                await client.add_episode(
                    name=f"project_{episode_data.metadata.get('section_type', 'unknown')}_{project_name}",
                    episode_body=episode_body,
                    group_id="project_overview",
                )
                episodes_created += 1
            except Exception as e:
                logger.warning(f"Failed to seed episode: {e}")

        return SeedComponentResult(
            component="project_overview",
            success=True,
            message=f"Seeded from {Path(doc_path).name}",
            episodes_created=episodes_created,
        )

    except Exception as e:
        logger.warning(f"Error parsing project documentation: {e}")
        return SeedComponentResult(
            component="project_overview",
            success=True,  # Graceful degradation
            message=f"Parse error: {e}",
            episodes_created=0,
        )


async def seed_implementation_modes_from_defaults(
    project_name: str,
    client: Any,
) -> SeedComponentResult:
    """Seed implementation mode defaults into Graphiti.

    Args:
        project_name: Name of the project.
        client: GraphitiClient instance.

    Returns:
        SeedComponentResult indicating success/failure.
    """
    if client is None or not client.enabled:
        return SeedComponentResult(
            component="implementation_modes",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    episodes_created = 0

    for mode_name, mode_episode in IMPLEMENTATION_MODE_DEFAULTS.items():
        try:
            episode_content = mode_episode.to_episode_content()
            episode_body = json.dumps(
                {
                    "entity_type": mode_episode.entity_type,
                    "mode": mode_episode.mode,
                    "invocation_method": mode_episode.invocation_method,
                    "result_location_pattern": mode_episode.result_location_pattern,
                    "state_recovery_strategy": mode_episode.state_recovery_strategy,
                    "when_to_use": mode_episode.when_to_use,
                    "pitfalls": mode_episode.pitfalls,
                    "content": episode_content,
                }
            )

            await client.add_episode(
                name=f"implementation_mode_{mode_name}",
                episode_body=episode_body,
                group_id="implementation_modes",
                scope="system",  # System-level, not project-specific
            )
            episodes_created += 1
        except Exception as e:
            logger.warning(f"Failed to seed implementation mode {mode_name}: {e}")

    return SeedComponentResult(
        component="implementation_modes",
        success=True,
        message=f"Seeded {episodes_created} modes",
        episodes_created=episodes_created,
    )


async def _seed_role_constraints_wrapper(client: Any) -> SeedComponentResult:
    """Wrapper for seed_role_constraints to return SeedComponentResult.

    Args:
        client: GraphitiClient instance.

    Returns:
        SeedComponentResult indicating success/failure.
    """
    if client is None or not client.enabled:
        return SeedComponentResult(
            component="role_constraints",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    try:
        await seed_role_constraints(client)
        return SeedComponentResult(
            component="role_constraints",
            success=True,
            message="Seeded Player and Coach constraints",
            episodes_created=2,
        )
    except Exception as e:
        logger.warning(f"Failed to seed role constraints: {e}")
        return SeedComponentResult(
            component="role_constraints",
            success=True,  # Graceful degradation
            message=f"Error: {e}",
            episodes_created=0,
        )


async def _seed_quality_gate_configs_wrapper(client: Any) -> SeedComponentResult:
    """Wrapper for seed_quality_gate_configs to return SeedComponentResult.

    Args:
        client: GraphitiClient instance.

    Returns:
        SeedComponentResult indicating success/failure.
    """
    if client is None or not client.enabled:
        return SeedComponentResult(
            component="quality_gate_configs",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    try:
        await seed_quality_gate_configs(client)
        return SeedComponentResult(
            component="quality_gate_configs",
            success=True,
            message="Seeded quality gate configurations",
            episodes_created=6,  # Approximate count from QUALITY_GATE_CONFIGS
        )
    except Exception as e:
        logger.warning(f"Failed to seed quality gate configs: {e}")
        return SeedComponentResult(
            component="quality_gate_configs",
            success=True,  # Graceful degradation
            message=f"Error: {e}",
            episodes_created=0,
        )


async def seed_project_knowledge(
    project_name: str,
    client: Any,
    skip_overview: bool = False,
    project_dir: Optional[Path] = None,
) -> SeedResult:
    """Seed all project knowledge to Graphiti.

    Orchestrates seeding of:
    1. Project overview (from CLAUDE.md or README.md)
    2. Role constraints (Player/Coach defaults)
    3. Quality gate configurations (defaults)
    4. Implementation modes (defaults)

    Graceful Degradation:
    If client is None or disabled, returns success with skip messages.
    Individual component failures don't prevent other components from seeding.

    Args:
        project_name: Name of the project.
        client: GraphitiClient instance (optional, handles None gracefully).
        skip_overview: If True, skip project overview seeding.
        project_dir: Project directory (defaults to cwd).

    Returns:
        SeedResult with success status and per-component results.

    Example:
        from guardkit.knowledge.graphiti_client import GraphitiClient
        from guardkit.knowledge.project_seeding import seed_project_knowledge

        client = GraphitiClient()
        await client.initialize()
        result = await seed_project_knowledge("my-project", client)
        if result.success:
            print(f"Seeded {len(result.results)} components")
    """
    result = SeedResult(success=True, project_name=project_name)

    # 1. Seed project overview from CLAUDE.md or README.md
    if not skip_overview:
        overview_result = await seed_project_overview(
            project_name=project_name,
            client=client,
            project_dir=project_dir,
        )
        result.add_result(overview_result)
        result.project_overview_seeded = overview_result.episodes_created > 0

    # 2. Seed role constraints (system-level defaults)
    constraints_result = await _seed_role_constraints_wrapper(client)
    result.add_result(constraints_result)
    result.role_constraints_seeded = constraints_result.episodes_created > 0

    # 3. Seed quality gate configs (system-level defaults)
    quality_result = await _seed_quality_gate_configs_wrapper(client)
    result.add_result(quality_result)
    result.quality_gates_seeded = quality_result.episodes_created > 0

    # 4. Seed implementation modes (system-level defaults)
    modes_result = await seed_implementation_modes_from_defaults(
        project_name=project_name,
        client=client,
    )
    result.add_result(modes_result)
    result.implementation_modes_seeded = modes_result.episodes_created > 0

    # All components use graceful degradation, so overall success is True
    # unless we want to change this to require at least one success
    result.success = True

    return result
