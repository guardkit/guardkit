"""
GuardKit init CLI command.

This module provides the `guardkit init` command for initializing GuardKit
in a project directory with optional template and Graphiti seeding.

Usage:
    guardkit init [TEMPLATE] [OPTIONS]

Arguments:
    TEMPLATE    Template to apply (default: 'default')

Options:
    --skip-graphiti    Skip Graphiti project seeding
    --project-name     Override project name (defaults to directory name)
    --interactive      Interactive setup mode for project knowledge

Example:
    guardkit init                          # Initialize with default template
    guardkit init fastapi-python           # Initialize with FastAPI template
    guardkit init --skip-graphiti          # Skip Graphiti seeding
    guardkit init react-typescript -n myapp  # With custom project name
    guardkit init --interactive            # Interactive setup mode

Coverage Target: >=85%
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
from guardkit.knowledge.config import _find_project_root, load_graphiti_config
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig, normalize_project_id
from guardkit.knowledge.project_seeding import estimate_episode_count, seed_project_knowledge

console = Console()
logger = logging.getLogger(__name__)

# Directories that should NOT be copied from templates (code scaffold concerns)
_SKIP_DIRS = {"templates", "config", "docker"}


class _ProgressClient:
    """Wraps a GraphitiClient to display per-episode progress during seeding.

    Intercepts ``add_episode`` calls to print elapsed time and N/M counters
    to the console. All other attribute access delegates to the wrapped client.
    """

    def __init__(self, client, total: int, console_obj):
        self._client = client
        self._total = total
        self._console = console_obj
        self._current = 0

    async def _episode_with_progress(self, method, *args, **kwargs):
        self._current += 1
        self._console.print(
            f"  Seeding episode {self._current}/{self._total}...",
            end="",
        )
        start = time.monotonic()
        try:
            result = await method(*args, **kwargs)
            elapsed = time.monotonic() - start
            self._console.print(f" done ({elapsed:.1f}s)")
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            self._console.print(
                f" [yellow]warning ({elapsed:.1f}s): {e}[/yellow]"
            )
            raise

    async def add_episode(self, *args, **kwargs):
        return await self._episode_with_progress(
            self._client.add_episode, *args, **kwargs
        )

    async def upsert_episode(self, *args, **kwargs):
        return await self._episode_with_progress(
            self._client.upsert_episode, *args, **kwargs
        )

    async def initialize(self):
        return await self._client.initialize()

    async def close(self):
        return await self._client.close()

    @property
    def enabled(self):
        return self._client.enabled

    def __getattr__(self, name):
        return getattr(self._client, name)


def _get_templates_base_dir() -> Path:
    """Return the base directory containing installed templates.

    Uses __file__-relative path to locate installer/core/templates/
    from the guardkit package installation.

    Returns:
        Path to the templates base directory.
    """
    # guardkit/cli/init.py -> guardkit/ -> project root -> installer/core/templates/
    package_root = Path(__file__).resolve().parent.parent.parent
    return package_root / "installer" / "core" / "templates"


def _get_user_templates_dir() -> Path:
    """Return the user-level templates directory (~/.guardkit/templates/).

    Returns:
        Path to the user templates directory.
    """
    return Path.home() / ".guardkit" / "templates"


def _resolve_template_source_dir(template_name: str) -> Optional[Path]:
    """Resolve the source directory for a template.

    Checks installed package templates first, then falls back to
    user-installed templates at ~/.guardkit/templates/.

    Args:
        template_name: Name of the template to resolve.

    Returns:
        Path to the template source directory, or None if not found.
    """
    # Check package-installed templates
    pkg_templates = _get_templates_base_dir()
    pkg_candidate = pkg_templates / template_name
    if pkg_candidate.is_dir():
        return pkg_candidate

    # Fallback: user-installed templates
    user_templates = _get_user_templates_dir()
    user_candidate = user_templates / template_name
    if user_candidate.is_dir():
        return user_candidate

    return None


def _copy_file_if_not_exists(
    src: Path, dest: Path, label: str = ""
) -> bool:
    """Copy a file from src to dest if dest does not already exist.

    Args:
        src: Source file path.
        dest: Destination file path.
        label: Human-readable label for logging.

    Returns:
        True if file was copied, False if skipped (already exists).
    """
    if dest.exists():
        logger.info(f"Skipping {label or dest.name}: already exists at {dest}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    logger.info(f"Copied {label or src.name} → {dest}")
    return True


def _copy_agents(template_dir: Path, target_dir: Path) -> List[str]:
    """Copy agent .md files from template to target .claude/agents/.

    Checks both {template}/agents/ and {template}/.claude/agents/ locations.
    Skips .gitkeep and non-.md files.

    Args:
        template_dir: Template source directory.
        target_dir: Project target directory.

    Returns:
        List of copied agent filenames.
    """
    copied: List[str] = []
    agents_target = target_dir / ".claude" / "agents"

    # Check both possible agent locations
    agent_dirs: List[Path] = []
    dotclaude_agents = template_dir / ".claude" / "agents"
    top_agents = template_dir / "agents"

    if dotclaude_agents.is_dir():
        agent_dirs.append(dotclaude_agents)
    if top_agents.is_dir():
        agent_dirs.append(top_agents)

    for agents_dir in agent_dirs:
        for agent_file in sorted(agents_dir.iterdir()):
            if not agent_file.is_file():
                continue
            if agent_file.suffix != ".md":
                continue
            if agent_file.name.startswith("."):
                continue

            if _copy_file_if_not_exists(
                agent_file,
                agents_target / agent_file.name,
                label=f"agent {agent_file.name}",
            ):
                copied.append(agent_file.name)

    return copied


def _copy_rules(template_dir: Path, target_dir: Path) -> List[str]:
    """Copy rules from template .claude/rules/ preserving directory structure.

    Args:
        template_dir: Template source directory.
        target_dir: Project target directory.

    Returns:
        List of copied rule file relative paths.
    """
    copied: List[str] = []
    rules_src = template_dir / ".claude" / "rules"
    rules_target = target_dir / ".claude" / "rules"

    if not rules_src.is_dir():
        return copied

    for rule_file in sorted(rules_src.rglob("*.md")):
        rel_path = rule_file.relative_to(rules_src)
        dest = rules_target / rel_path

        if _copy_file_if_not_exists(
            rule_file,
            dest,
            label=f"rule {rel_path}",
        ):
            copied.append(str(rel_path))

    return copied


def _copy_claude_md(template_dir: Path, target_dir: Path) -> List[str]:
    """Copy CLAUDE.md files from template to target.

    Handles both root CLAUDE.md and .claude/CLAUDE.md.
    If both exist in the template, both are copied.
    Skips if target already has the file.

    Args:
        template_dir: Template source directory.
        target_dir: Project target directory.

    Returns:
        List of copied CLAUDE.md paths (relative to target).
    """
    copied: List[str] = []

    # Check root CLAUDE.md
    root_src = template_dir / "CLAUDE.md"
    if root_src.is_file():
        if _copy_file_if_not_exists(
            root_src,
            target_dir / "CLAUDE.md",
            label="root CLAUDE.md",
        ):
            copied.append("CLAUDE.md")

    # Check .claude/CLAUDE.md
    dotclaude_src = template_dir / ".claude" / "CLAUDE.md"
    if dotclaude_src.is_file():
        if _copy_file_if_not_exists(
            dotclaude_src,
            target_dir / ".claude" / "CLAUDE.md",
            label=".claude/CLAUDE.md",
        ):
            copied.append(".claude/CLAUDE.md")

    return copied


def _copy_manifest(template_dir: Path, target_dir: Path) -> bool:
    """Copy manifest.json from template to target .claude/manifest.json.

    Args:
        template_dir: Template source directory.
        target_dir: Project target directory.

    Returns:
        True if manifest was copied, False if skipped or not present.
    """
    manifest_src = template_dir / "manifest.json"
    if not manifest_src.is_file():
        logger.info("No manifest.json in template, skipping")
        return False

    return _copy_file_if_not_exists(
        manifest_src,
        target_dir / ".claude" / "manifest.json",
        label="manifest.json",
    )


def write_graphiti_config(project_name: str, target_dir: Path) -> bool:
    """Write project_id to .guardkit/graphiti.yaml configuration file.

    Creates or updates the graphiti.yaml file with the project_id field.
    This ensures explicit project_id is used instead of auto-detection.

    Args:
        project_name: The project name to normalize and write as project_id.
        target_dir: Target directory containing .guardkit folder.

    Returns:
        True if config written successfully, False otherwise.
    """
    try:
        # Import yaml here to handle optional dependency
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, cannot write graphiti.yaml")
            return False

        config_dir = target_dir / ".guardkit"
        config_file = config_dir / "graphiti.yaml"

        # Normalize project_id using the same logic as GraphitiClient
        project_id = normalize_project_id(project_name)

        # Load existing config if present
        config_data = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    existing_data = yaml.safe_load(f)
                    if existing_data and isinstance(existing_data, dict):
                        config_data = existing_data
            except Exception as e:
                logger.debug(f"Could not load existing graphiti.yaml: {e}")

        # Update project_id
        config_data['project_id'] = project_id

        # Write config file
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Written project_id '{project_id}' to {config_file}")
        return True

    except Exception as e:
        logger.warning(f"Failed to write graphiti.yaml: {e}")
        return False


def _find_source_graphiti_config(copy_graphiti: str) -> Optional[Path]:
    """Find the source graphiti.yaml to copy from.

    If an explicit path is given, looks for .guardkit/graphiti.yaml under that path.
    If ``copy_graphiti`` is "auto", uses a two-strategy approach:
      1. Walk up from the parent of cwd to find an ancestor project's config.
      2. Scan sibling directories of cwd for a .guardkit/graphiti.yaml.
    Skips cwd itself to avoid finding the target project's own config.

    Args:
        copy_graphiti: Either "auto" for auto-discovery or an explicit directory path.

    Returns:
        Path to the source graphiti.yaml if found, or None.
    """
    if copy_graphiti == "auto":
        cwd = Path.cwd().resolve()
        parent_dir = cwd.parent

        # Strategy 1: Walk up from the parent of cwd (finds ancestor projects)
        project_root = _find_project_root(parent_dir)
        if project_root is not None:
            candidate = project_root / ".guardkit" / "graphiti.yaml"
            if candidate.is_file():
                return candidate

        # Strategy 2: Scan sibling directories (finds peer projects like guardkit/)
        # Resolve both sides when comparing to handle macOS /var -> /private/var symlinks.
        try:
            for sibling in sorted(parent_dir.iterdir()):
                if not sibling.is_dir() or sibling.resolve() == cwd:
                    continue
                candidate = sibling / ".guardkit" / "graphiti.yaml"
                if candidate.is_file():
                    return candidate
        except PermissionError:
            pass

        return None
    else:
        # Explicit path provided
        source_dir = Path(copy_graphiti).expanduser().resolve()
        candidate = source_dir / ".guardkit" / "graphiti.yaml"
        return candidate if candidate.is_file() else None


def copy_graphiti_config(
    project_name: str,
    target_dir: Path,
    source_config: Path,
) -> bool:
    """Copy a source graphiti.yaml to the target, replacing project_id.

    Loads the full source config, replaces the ``project_id`` field with the
    normalized version of ``project_name``, and writes the result to
    ``target_dir/.guardkit/graphiti.yaml``.

    Args:
        project_name: The new project name; will be normalized to a valid project_id.
        target_dir: Target directory containing .guardkit folder.
        source_config: Path to the source graphiti.yaml to copy from.

    Returns:
        True if config written successfully, False otherwise.
    """
    try:
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, cannot copy graphiti.yaml")
            return False

        # Load source config
        with open(source_config, "r") as f:
            config_data = yaml.safe_load(f)

        if not config_data or not isinstance(config_data, dict):
            logger.warning(f"Source graphiti.yaml is empty or invalid: {source_config}")
            return False

        # Replace project_id with the normalized new project name
        project_id = normalize_project_id(project_name)
        config_data["project_id"] = project_id

        # Write to target
        config_dir = target_dir / ".guardkit"
        config_file = config_dir / "graphiti.yaml"
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Copied graphiti config with project_id '{project_id}' to {config_file}")
        return True

    except Exception as e:
        logger.warning(f"Failed to copy graphiti.yaml: {e}")
        return False


def apply_template(template_name: str, target_dir: Optional[Path] = None) -> bool:
    """Apply a template to the target directory.

    Creates the basic GuardKit directory structure and copies template-specific
    content including agents, rules, CLAUDE.md, and manifest.json.

    Handles structural variations across templates:
    - Agents may be in agents/ or .claude/agents/
    - CLAUDE.md may be at root, .claude/, or both
    - manifest.json may or may not be present
    - Code scaffold directories (templates/, config/, docker/) are NOT copied

    Args:
        template_name: Name of the template to apply.
        target_dir: Target directory (defaults to cwd).

    Returns:
        True if template applied successfully, False otherwise.
    """
    target_dir = target_dir or Path.cwd()

    # Step 1: Create basic GuardKit directory structure (always)
    directories = [
        target_dir / ".claude",
        target_dir / ".claude" / "commands",
        target_dir / ".claude" / "agents",
        target_dir / ".claude" / "task-plans",
        target_dir / "tasks",
        target_dir / "tasks" / "backlog",
        target_dir / "tasks" / "in_progress",
        target_dir / "tasks" / "in_review",
        target_dir / "tasks" / "blocked",
        target_dir / "tasks" / "completed",
        target_dir / ".guardkit",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # Step 2: Resolve template source directory
    template_dir = _resolve_template_source_dir(template_name)

    if template_dir is None:
        logger.warning(
            f"Template '{template_name}' not found in installed or user templates. "
            f"Created basic scaffold only."
        )
        return True

    # Step 3: Copy template content
    agents_copied = _copy_agents(template_dir, target_dir)
    if agents_copied:
        logger.info(f"Copied {len(agents_copied)} agent(s): {', '.join(agents_copied)}")

    rules_copied = _copy_rules(template_dir, target_dir)
    if rules_copied:
        logger.info(f"Copied {len(rules_copied)} rule(s)")

    claude_copied = _copy_claude_md(template_dir, target_dir)
    if claude_copied:
        logger.info(f"Copied CLAUDE.md: {', '.join(claude_copied)}")

    manifest_copied = _copy_manifest(template_dir, target_dir)
    if manifest_copied:
        logger.info("Copied manifest.json")

    logger.info(f"Applied template '{template_name}' to {target_dir}")
    return True


async def interactive_setup(project_name: str) -> ProjectOverviewEpisode:
    """Run interactive setup for project knowledge.

    Prompts the user for project information including purpose, tech stack,
    frameworks, and key goals.

    Args:
        project_name: Name of the project.

    Returns:
        ProjectOverviewEpisode populated with user-provided information.
    """
    default_purpose = "A software project"
    purpose = Prompt.ask(
        "What is the purpose of this project?",
        default=default_purpose
    )
    # Handle empty response (e.g., when mocked in tests)
    if not purpose:
        purpose = default_purpose

    default_language = "python"
    primary_language = Prompt.ask(
        "What is the primary programming language?",
        choices=["python", "typescript", "go", "rust", "java", "other"],
        default=default_language
    )
    # Handle empty response
    if not primary_language:
        primary_language = default_language

    frameworks_input = Prompt.ask(
        "What frameworks are you using? (comma-separated)",
        default=""
    )
    frameworks = [f.strip() for f in frameworks_input.split(",") if f.strip()]

    key_goals = []
    console.print("Enter key goals (empty line to finish):")
    while True:
        goal = Prompt.ask("Goal", default="")
        if not goal:
            break
        key_goals.append(goal)

    return ProjectOverviewEpisode(
        project_name=project_name,
        purpose=purpose,
        primary_language=primary_language,
        frameworks=frameworks,
        key_goals=key_goals,
    )


def generate_claude_md(episode: ProjectOverviewEpisode, target_dir: Path) -> None:
    """Generate CLAUDE.md from ProjectOverviewEpisode.

    Creates a CLAUDE.md file in the target directory with project information
    extracted from the episode.

    Args:
        episode: ProjectOverviewEpisode containing project information.
        target_dir: Directory where CLAUDE.md should be created.
    """
    frameworks_text = ', '.join(episode.frameworks) if episode.frameworks else 'None specified'
    goals_text = '\n'.join(f'- {goal}' for goal in episode.key_goals) if episode.key_goals else 'None specified'

    content = f"""# {episode.project_name}

## Purpose
{episode.purpose}

## Technology Stack
- **Primary Language**: {episode.primary_language}
- **Frameworks**: {frameworks_text}

## Key Goals
{goals_text}
"""
    (target_dir / "CLAUDE.md").write_text(content)


async def _cmd_init(
    template: str,
    skip_graphiti: bool,
    project_name: Optional[str],
    interactive: bool = False,
    copy_graphiti: Optional[str] = None,
    verbose: bool = False,
    no_questions: bool = False,
) -> int:
    """Async implementation of init command.

    Args:
        template: Template name to apply.
        skip_graphiti: If True, skip Graphiti seeding.
        project_name: Override project name.
        interactive: If True, run interactive setup mode.
        copy_graphiti: If set, copy graphiti config from an existing project.
            Use "auto" for auto-discovery or an explicit directory path.
        verbose: If True, show all log output including third-party DEBUG/INFO.
        no_questions: If True, skip the auto-offer prompt and use project_id-only.

    Returns:
        Exit code (0 for success).
    """
    # Suppress noisy third-party loggers (same pattern as graphiti.py:598-599)
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)

    project_dir = Path.cwd()
    project_name = project_name or project_dir.name

    console.print(f"[bold]Initializing GuardKit in {project_dir}[/bold]")
    console.print(f"  Project: {project_name}")
    console.print(f"  Template: {template}")

    # Step 1: Apply template
    console.print("\n[bold]Step 1: Applying template...[/bold]")
    if apply_template(template, project_dir):
        console.print(f"  [green]Applied template: {template}[/green]")
    else:
        console.print(f"  [yellow]Warning: Template '{template}' not found, using defaults[/yellow]")

    # Step 1.1: Write Graphiti config with project_id
    # Track whether we obtained a full config (with connection details).
    # If only project_id was written, seeding would fail with default Neo4j settings.
    graphiti_config_complete = False

    if copy_graphiti is not None:
        # --copy-graphiti flag: try to copy config from existing project
        source_config = _find_source_graphiti_config(copy_graphiti)
        if source_config is not None:
            if copy_graphiti_config(project_name, project_dir, source_config):
                console.print(
                    f"  [green]Copied Graphiti config from {source_config} "
                    f"to .guardkit/graphiti.yaml[/green]"
                )
                graphiti_config_complete = True
            else:
                console.print(
                    f"  [yellow]Warning: Could not copy graphiti.yaml, "
                    f"falling back to project_id only[/yellow]"
                )
                write_graphiti_config(project_name, project_dir)
        else:
            console.print(
                f"  [yellow]Warning: No source graphiti.yaml found "
                f"(--copy-graphiti), falling back to project_id only[/yellow]"
            )
            console.print(
                f"  [dim]Tip: Use --copy-graphiti-from /path/to/project "
                f"to specify the source project explicitly[/dim]"
            )
            write_graphiti_config(project_name, project_dir)
    else:
        # No explicit --copy-graphiti flag: auto-offer if a parent/sibling config exists
        source_config = None if no_questions else _find_source_graphiti_config("auto")
        if source_config is not None:
            console.print(f"\nFound existing graphiti.yaml at {source_config}")
            try:
                should_copy = Confirm.ask(
                    "Copy infrastructure config to this project?", default=True
                )
            except Exception:
                should_copy = True
            if should_copy:
                if copy_graphiti_config(project_name, project_dir, source_config):
                    console.print(
                        f"  [green]Copied Graphiti config from {source_config} "
                        f"to .guardkit/graphiti.yaml[/green]"
                    )
                    graphiti_config_complete = True
                else:
                    console.print(
                        f"  [yellow]Warning: Could not copy graphiti.yaml, "
                        f"falling back to project_id only[/yellow]"
                    )
                    write_graphiti_config(project_name, project_dir)
            else:
                if write_graphiti_config(project_name, project_dir):
                    console.print(f"  [green]Written project_id to .guardkit/graphiti.yaml[/green]")
                else:
                    console.print(f"  [yellow]Warning: Could not write .guardkit/graphiti.yaml[/yellow]")
        elif write_graphiti_config(project_name, project_dir):
            console.print(f"  [green]Written project_id to .guardkit/graphiti.yaml[/green]")
        else:
            console.print(f"  [yellow]Warning: Could not write .guardkit/graphiti.yaml[/yellow]")

    # Step 1.5: Interactive setup (if requested)
    project_overview_episode = None
    if interactive:
        console.print("\n[bold]Interactive Setup[/bold]")
        project_overview_episode = await interactive_setup(project_name)

        # Ask about CLAUDE.md generation
        try:
            should_generate = Confirm.ask("Save this information to CLAUDE.md?", default=True)
            if should_generate:
                generate_claude_md(project_overview_episode, project_dir)
                console.print("  [green]Generated CLAUDE.md[/green]")
        except Exception:
            # In non-interactive contexts (e.g., tests without mock), skip CLAUDE.md prompt
            pass

    # Track whether system seeding ran (for summary)
    system_seeded = False

    # Step 2: Seed Graphiti (if not skipped)
    # Also skip if --copy-graphiti was used but failed — seeding with default
    # Neo4j settings would just produce connection errors for minutes.
    if not skip_graphiti and copy_graphiti is not None and not graphiti_config_complete:
        skip_graphiti = True
        console.print(
            "\n[bold]Step 2: Skipping Graphiti seeding "
            "(no valid config found)[/bold]"
        )
        console.print(
            "  [dim]Run 'guardkit graphiti seed' after configuring "
            ".guardkit/graphiti.yaml[/dim]"
        )
    elif skip_graphiti:
        console.print("\n[bold]Step 2: Skipping Graphiti seeding (--skip-graphiti)[/bold]")
    else:
        console.print("\n[bold]Step 2: Seeding project knowledge to Graphiti...[/bold]")

        # Initialize Graphiti client from .guardkit/graphiti.yaml
        client = None
        try:
            settings = load_graphiti_config()
            config = GraphitiConfig(
                enabled=settings.enabled,
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password,
                timeout=settings.timeout,
                project_id=project_name,
                graph_store=settings.graph_store,
                falkordb_host=settings.falkordb_host,
                falkordb_port=settings.falkordb_port,
                host=settings.host,
                port=settings.port,
                llm_provider=settings.llm_provider,
                llm_base_url=settings.llm_base_url,
                llm_model=settings.llm_model,
                embedding_provider=settings.embedding_provider,
                embedding_base_url=settings.embedding_base_url,
                embedding_model=settings.embedding_model,
            )
            client = GraphitiClient(config)
            initialized = await client.initialize()

            if not initialized or not client.enabled:
                console.print("  [yellow]Warning: Graphiti unavailable, skipping seeding[/yellow]")
            else:
                # Estimate total episodes for progress display
                total_episodes = estimate_episode_count(
                    skip_overview=False,
                    project_dir=project_dir,
                    project_overview_episode=project_overview_episode,
                )

                # Wrap client with progress proxy
                progress_client = _ProgressClient(client, total_episodes, console)

                # Seed project knowledge with progress
                seed_start = time.monotonic()
                result = await seed_project_knowledge(
                    project_name=project_name,
                    client=progress_client,
                    project_dir=project_dir,
                    project_overview_episode=project_overview_episode,
                )
                seed_elapsed = time.monotonic() - seed_start

                if result.success:
                    console.print(
                        f"  [green]Project knowledge seeded successfully"
                        f" ({seed_elapsed:.1f}s total)[/green]"
                    )
                    for component_result in result.results:
                        status = "[green]OK[/green]" if component_result.success else "[yellow]WARN[/yellow]"
                        console.print(f"    {status} {component_result.component}: {component_result.message}")
                    # Step 2.5: Offer system seeding after successful project seeding
                    if client and client.enabled:
                        try:
                            if no_questions:
                                should_seed_system = True
                            else:
                                should_seed_system = Confirm.ask(
                                    "Seed system knowledge now? (recommended for AutoBuild)",
                                    default=True,
                                )
                        except Exception:
                            should_seed_system = True  # Non-interactive fallback

                        if should_seed_system:
                            console.print(
                                "\n[bold]Step 3: Seeding system knowledge...[/bold]"
                            )
                            try:
                                from guardkit.knowledge.system_seeding import (
                                    seed_system_content,
                                )

                                sys_result = await seed_system_content(
                                    client, template_name=template
                                )
                                if sys_result.success:
                                    console.print(
                                        "  [green]System knowledge seeded"
                                        " successfully[/green]"
                                    )
                                    for comp in sys_result.results:
                                        status = (
                                            "[green]OK[/green]"
                                            if comp.success
                                            else "[yellow]WARN[/yellow]"
                                        )
                                        console.print(
                                            f"    {status} {comp.component}:"
                                            f" {comp.message}"
                                        )
                                    system_seeded = True
                                else:
                                    console.print(
                                        "  [yellow]Warning: Some system seeding"
                                        " components failed[/yellow]"
                                    )
                            except Exception as e:
                                console.print(
                                    f"  [yellow]Warning: System seeding"
                                    f" error: {e}[/yellow]"
                                )
                                logger.debug(
                                    f"System seeding error: {e}", exc_info=True
                                )

                else:
                    console.print(
                        f"  [yellow]Warning: Some seeding components failed"
                        f" ({seed_elapsed:.1f}s total)[/yellow]"
                    )

        except Exception as e:
            console.print(f"  [yellow]Warning: Graphiti seeding error: {e}[/yellow]")
            logger.debug(f"Graphiti error: {e}", exc_info=True)
        finally:
            if client:
                try:
                    await client.close()
                except Exception:
                    pass

    # Summary
    console.print("\n[bold green]GuardKit initialized successfully![/bold green]")
    if not skip_graphiti:
        console.print(
            "\n  [green]Seeded:[/green] project knowledge "
            "(project overview from CLAUDE.md/README.md)"
        )
        if system_seeded:
            console.print(
                "  [green]Seeded:[/green] system knowledge "
                "(templates, rules, role constraints, implementation modes)"
            )
        else:
            console.print(
                "  [yellow]Not yet seeded:[/yellow] system knowledge "
                "(templates, rules, role constraints, implementation modes)"
            )
    console.print(f"\nNext steps:")
    if not skip_graphiti and not system_seeded:
        console.print(f"  1. Seed system knowledge: guardkit graphiti seed-system")
        console.print(f"  2. Create a task: /task-create \"Your first task\"")
        console.print(f"  3. Work on it: /task-work TASK-XXX")
        console.print(f"  4. Complete it: /task-complete TASK-XXX")
        console.print(
            "\n  [dim]Tip: For multi-project FalkorDB setups, use --copy-graphiti "
            "to share config across projects.[/dim]"
        )
    else:
        console.print(f"  1. Create a task: /task-create \"Your first task\"")
        console.print(f"  2. Work on it: /task-work TASK-XXX")
        console.print(f"  3. Complete it: /task-complete TASK-XXX")

    return 0


@click.command()
@click.argument("template", default="default")
@click.option(
    "--skip-graphiti",
    is_flag=True,
    help="Skip Graphiti project knowledge seeding",
)
@click.option(
    "--project-name",
    "-n",
    default=None,
    help="Override project name (defaults to directory name)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive setup mode for project knowledge",
)
@click.option(
    "--copy-graphiti",
    is_flag=True,
    default=False,
    help="Auto-discover and copy Graphiti config from a parent directory project. Recommended for multi-project setups sharing a FalkorDB instance to prevent embedding dimension mismatches.",
)
@click.option(
    "--copy-graphiti-from",
    default=None,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Copy Graphiti config from an explicit project path.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all log output including third-party DEBUG/INFO messages.",
)
@click.option(
    "--no-questions",
    is_flag=True,
    default=False,
    help="Skip prompts and use project_id-only graphiti.yaml (backward compatible).",
)
def init(
    template: str,
    skip_graphiti: bool,
    project_name: Optional[str],
    interactive: bool,
    copy_graphiti: bool,
    copy_graphiti_from: Optional[str],
    verbose: bool,
    no_questions: bool,
):
    """Initialize GuardKit in the current directory.

    Applies a template and optionally seeds project knowledge to Graphiti.

    TEMPLATE is the name of the template to apply (default: 'default').
    Available templates: default, fastapi-python, react-typescript, nextjs-fullstack.
    """
    # Merge the two options into a single value for _cmd_init
    copy_graphiti_value: Optional[str] = None
    if copy_graphiti_from:
        copy_graphiti_value = copy_graphiti_from
    elif copy_graphiti:
        copy_graphiti_value = "auto"

    exit_code = asyncio.run(
        _cmd_init(
            template, skip_graphiti, project_name, interactive,
            copy_graphiti_value, verbose, no_questions,
        )
    )
    if exit_code != 0:
        raise SystemExit(exit_code)
