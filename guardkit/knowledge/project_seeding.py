"""
Project knowledge seeding module for GuardKit init command.

This module orchestrates seeding of project knowledge into Graphiti during
project initialization. It coordinates:
- Project overview parsing from CLAUDE.md or README.md
- Role constraints seeding
- Implementation modes seeding
- Architectural decisions seeding (system-scoped lessons learned)

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

from guardkit.integrations.graphiti.episodes.architectural_decision import (
    ARCHITECTURAL_DECISION_DEFAULTS,
)
from guardkit.integrations.graphiti.episodes.implementation_mode import (
    IMPLEMENTATION_MODE_DEFAULTS,
)
from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
from guardkit.integrations.graphiti.parsers.project_doc_parser import ProjectDocParser
from guardkit.knowledge.episode_splitting import split_episode_content
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
    architectural_decisions_seeded: bool = False

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

        # Seed each parsed episode, splitting large content into chunks
        episodes_created = 0
        for episode_data in parse_result.episodes:
            try:
                section_type = episode_data.metadata.get("section_type", "unknown")
                base_episode_name = f"project_{section_type}_{project_name}"

                # Split large episodes at markdown section boundaries
                chunks = split_episode_content(episode_data.content)

                for chunk in chunks:
                    chunk_metadata = {
                        **episode_data.metadata,
                        "chunk_index": chunk.chunk_index,
                        "total_chunks": chunk.total_chunks,
                    }

                    chunk_name = base_episode_name
                    if chunk.total_chunks > 1:
                        chunk_name = f"{base_episode_name}_chunk{chunk.chunk_index}"

                    chunk_body = json.dumps(
                        {
                            "entity_type": episode_data.entity_type,
                            "content": chunk.content,
                            "metadata": chunk_metadata,
                            "project_name": project_name,
                        }
                    )

                    result = await client.upsert_episode(
                        name=chunk_name,
                        episode_body=chunk_body,
                        group_id="project_overview",
                        entity_id=chunk_name,
                    )
                    if result is not None and getattr(result, "was_skipped", False):
                        logger.info(f"Skipping unchanged episode: {chunk_name}")
                    elif result is not None:
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
            episode_name = f"implementation_mode_{mode_name}"
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

            result = await client.upsert_episode(
                name=episode_name,
                episode_body=episode_body,
                group_id="implementation_modes",
                entity_id=episode_name,
                scope="system",  # System-level, not project-specific
            )
            if result is not None and getattr(result, "was_skipped", False):
                logger.info(f"Skipping unchanged episode: {episode_name}")
            elif result is not None:
                episodes_created += 1
        except Exception as e:
            logger.warning(f"Failed to seed implementation mode {mode_name}: {e}")

    return SeedComponentResult(
        component="implementation_modes",
        success=True,
        message=f"Seeded {episodes_created} modes",
        episodes_created=episodes_created,
    )


async def seed_architectural_decisions(
    client: Any,
) -> SeedComponentResult:
    """Seed system-scoped architectural decisions into Graphiti.

    Seeds lessons learned and architectural decisions that apply across
    all projects, ensuring future sessions don't repeat failed approaches.

    Args:
        client: GraphitiClient instance.

    Returns:
        SeedComponentResult indicating success/failure.
    """
    if client is None or not client.enabled:
        return SeedComponentResult(
            component="architectural_decisions",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    episodes_created = 0

    for decision_key, decision_episode in ARCHITECTURAL_DECISION_DEFAULTS.items():
        try:
            episode_name = f"arch_decision_{decision_key}"
            episode_content = decision_episode.to_episode_content()
            episode_body = json.dumps(
                {
                    "entity_type": decision_episode.entity_type,
                    "title": decision_episode.title,
                    "summary": decision_episode.summary,
                    "implications": decision_episode.implications,
                    "evidence": decision_episode.evidence,
                    "decision_reference": decision_episode.decision_reference,
                    "date": decision_episode.date,
                    "content": episode_content,
                }
            )

            result = await client.upsert_episode(
                name=episode_name,
                episode_body=episode_body,
                group_id="architecture_decisions",
                entity_id=episode_name,
                scope="system",
            )
            if result is not None and getattr(result, "was_skipped", False):
                logger.info(f"Skipping unchanged episode: {episode_name}")
            elif result is not None:
                episodes_created += 1
        except Exception as e:
            logger.warning(
                f"Failed to seed architectural decision {decision_key}: {e}"
            )

    return SeedComponentResult(
        component="architectural_decisions",
        success=True,
        message=f"Seeded {episodes_created} decisions",
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


async def seed_project_overview_from_episode(
    project_name: str,
    client: Any,
    episode: ProjectOverviewEpisode,
) -> SeedComponentResult:
    """Seed project overview from a ProjectOverviewEpisode.

    Seeds the provided ProjectOverviewEpisode directly to Graphiti
    without parsing documentation files.

    Args:
        project_name: Name of the project.
        client: GraphitiClient instance.
        episode: ProjectOverviewEpisode to seed.

    Returns:
        SeedComponentResult indicating success/failure.
    """
    if client is None or not client.enabled:
        return SeedComponentResult(
            component="project_overview",
            success=True,
            message="Skipped (Graphiti unavailable)",
        )

    try:
        episode_name = f"project_overview_{project_name}"
        episode_content = episode.to_episode_content()
        episode_body = json.dumps(
            {
                "entity_type": episode.entity_type,
                "project_name": episode.project_name,
                "purpose": episode.purpose,
                "primary_language": episode.primary_language,
                "frameworks": episode.frameworks,
                "key_goals": episode.key_goals,
                "content": episode_content,
            }
        )

        result = await client.upsert_episode(
            name=episode_name,
            episode_body=episode_body,
            group_id="project_overview",
            entity_id=episode_name,
        )

        if result is not None and getattr(result, "was_skipped", False):
            logger.info(f"Skipping unchanged episode: {episode_name}")
            return SeedComponentResult(
                component="project_overview",
                success=True,
                message="Skipped (unchanged)",
                episodes_created=0,
            )

        return SeedComponentResult(
            component="project_overview",
            success=True,
            message="Seeded from interactive setup",
            episodes_created=1 if result is not None else 0,
        )
    except Exception as e:
        logger.warning(f"Failed to seed project overview episode: {e}")
        return SeedComponentResult(
            component="project_overview",
            success=True,  # Graceful degradation
            message=f"Error: {e}",
            episodes_created=0,
        )


async def seed_project_knowledge(
    project_name: str,
    client: Any,
    skip_overview: bool = False,
    project_dir: Optional[Path] = None,
    project_overview_episode: Optional[ProjectOverviewEpisode] = None,
) -> SeedResult:
    """Seed project-specific knowledge to Graphiti.

    Seeds only project-specific content (project overview). System-scoped
    content (role constraints, implementation modes, architectural decisions,
    template/agent/rule sync) is handled by ``guardkit graphiti seed-system``.

    Graceful Degradation:
    If client is None or disabled, returns success with skip messages.

    Args:
        project_name: Name of the project.
        client: GraphitiClient instance (optional, handles None gracefully).
        skip_overview: If True, skip project overview seeding.
        project_dir: Project directory (defaults to cwd).
        project_overview_episode: Optional ProjectOverviewEpisode from interactive setup.
            If provided, this is used instead of parsing CLAUDE.md/README.md.

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

    # Seed project overview (project-specific content only)
    # System-scoped content (role constraints, implementation modes,
    # architectural decisions) is now handled by `guardkit graphiti seed-system`.
    if not skip_overview:
        if project_overview_episode is not None:
            # Use the provided episode from interactive setup
            overview_result = await seed_project_overview_from_episode(
                project_name=project_name,
                client=client,
                episode=project_overview_episode,
            )
        else:
            # Parse from CLAUDE.md or README.md
            overview_result = await seed_project_overview(
                project_name=project_name,
                client=client,
                project_dir=project_dir,
            )
        result.add_result(overview_result)
        result.project_overview_seeded = overview_result.episodes_created > 0

    result.success = True

    return result


def estimate_episode_count(
    skip_overview: bool = False,
    project_dir: Optional[Path] = None,
    project_overview_episode: Optional[Any] = None,
) -> int:
    """Estimate total episode count for progress display.

    Counts how many ``client.upsert_episode`` calls will be made during
    ``seed_project_knowledge``, allowing callers to show N/M progress.

    Only counts project-specific episodes (project overview). System-scoped
    episodes (role constraints, implementation modes, architectural decisions)
    are handled by ``guardkit graphiti seed-system``.

    Args:
        skip_overview: If True, overview episodes are excluded.
        project_dir: Project directory (defaults to cwd).
        project_overview_episode: If provided, counts as 1 overview episode.

    Returns:
        Estimated total episode count.
    """
    total = 0

    if not skip_overview:
        if project_overview_episode is not None:
            total += 1
        else:
            project_dir = project_dir or Path.cwd()
            doc_files = ["CLAUDE.md", "README.md", "claude.md", "readme.md"]
            for filename in doc_files:
                filepath = project_dir / filename
                if filepath.exists():
                    try:
                        parser = ProjectDocParser()
                        content = filepath.read_text()
                        if parser.can_parse(content, str(filepath)):
                            parse_result = parser.parse(content, str(filepath))
                            if parse_result.success:
                                total += len(parse_result.episodes)
                    except Exception:
                        pass
                    break

    return total
