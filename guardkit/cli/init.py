"""
GuardKit init CLI command.

This module provides the `guardkit init` command for initializing GuardKit
in a project directory by applying a template.

Knowledge capture is provided by the fleet-memory backend, which is entirely
env-driven (``FLEET_MEMORY_*`` / ``GUARDKIT_MEMORY_BACKEND``) and needs no
init-time configuration. (The former Graphiti seed-on-init / MCP-config /
``graphiti.yaml`` writing was retired in FEAT-MEM-09.)

Usage:
    guardkit init [TEMPLATE] [OPTIONS]

Arguments:
    TEMPLATE    Template to apply (default: 'default')

Options:
    --project-name     Override project name (defaults to directory name)
    --interactive      Interactive setup mode (collects project info -> CLAUDE.md)
    --base-only        Install only the base template when extends is used

Example:
    guardkit init                          # Initialize with default template
    guardkit init fastapi-python           # Initialize with FastAPI template
    guardkit init react-typescript -n myapp  # With custom project name
    guardkit init --interactive            # Interactive setup mode

Coverage Target: >=85%
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from guardkit.templates.conftest_bridge import install_features_conftest_bridge
from guardkit.templates.qa_scaffold import install_qa_scaffold
from guardkit.templates.resolver import (
    _get_templates_base_dir as _get_templates_base_dir,
    resolve_template_source_dir as resolve_template_source_dir,
)

console = Console()
logger = logging.getLogger(__name__)

# Directories that should NOT be copied from templates (code scaffold concerns)
_SKIP_DIRS = {"templates", "config", "docker"}


def _find_uv_command() -> str:
    """Return the absolute path to the uv command, or 'uv' if not found.

    Returns:
        Absolute path string to uv binary, or 'uv' as fallback.
    """
    uv_path = shutil.which("uv")
    return uv_path if uv_path else "uv"


def _resolve_template_source_dir(template_name: str) -> Optional[Path]:
    """Resolve the source directory for a template.

    Thin wrapper kept for backward compatibility with existing call sites
    and test mocks (which patch ``_get_templates_base_dir`` on this module).
    Resolves against the ``installer/core/templates`` payload — packaged under
    the guardkit namespace in a wheel, or the repo checkout for editable
    installs (see :func:`guardkit.templates.resolver._get_installer_core_dir`).

    The former ``~/.guardkit/templates`` user-override fallback was removed in
    DF-011: no installer ever populated it (install.sh writes ``~/.agentecflow``),
    so it only ever resolved to ``None``.

    Args:
        template_name: Name of the template to resolve.

    Returns:
        Path to the template source directory, or None if not found.
    """
    pkg_candidate = _get_templates_base_dir() / template_name
    if pkg_candidate.is_dir():
        return pkg_candidate
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


def _load_manifest(template_dir: Path) -> Optional[Dict[str, Any]]:
    """Load manifest.json from a template directory.

    Args:
        template_dir: Template source directory.

    Returns:
        Parsed manifest dict, or None if not found or invalid.
    """
    manifest_path = template_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load manifest from {manifest_path}: {e}")
        return None


def _resolve_extends_chain(template_name: str) -> List[str]:
    """Resolve the template inheritance chain via the ``extends`` field.

    Walks the ``extends`` field in each template's manifest.json to build an
    ordered list of templates to install.  The returned list is ordered from
    base to extension (install order) so that extension files overlay base
    files.

    Protects against circular references by tracking visited templates.

    Args:
        template_name: Starting (most-derived) template name.

    Returns:
        List of template names from base to extension, e.g.
        ``["langchain-deepagents", "langchain-deepagents-weighted-evaluation"]``.
        If the template has no ``extends`` field, returns ``[template_name]``.
    """
    chain: List[str] = []
    visited: set[str] = set()
    current = template_name

    while current and current not in visited:
        visited.add(current)
        chain.append(current)

        template_dir = _resolve_template_source_dir(current)
        if template_dir is None:
            break

        manifest = _load_manifest(template_dir)
        if manifest is None:
            break

        current = manifest.get("extends")

    # Reverse so base is first, most-derived is last
    chain.reverse()
    return chain


def _count_pattern_layer_files(template_names: List[str]) -> int:
    """Count ``.template`` and ``.j2`` files across the ``templates/`` dirs of
    each resolved template in ``template_names``.

    Deduplicates by resolved source path to avoid double-counting when two
    templates in an extends chain point to the same cached directory.
    Best-effort: any OSError during traversal is logged at debug level and
    that directory is skipped — this never blocks init.
    """
    seen: set[Path] = set()
    count = 0
    for name in template_names:
        tpl_dir = _resolve_template_source_dir(name)
        if tpl_dir is None:
            continue
        patterns_dir = tpl_dir / "templates"
        if not patterns_dir.is_dir():
            continue
        try:
            for suffix in ("*.template", "*.j2"):
                for p in patterns_dir.rglob(suffix):
                    resolved = p.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        count += 1
        except OSError as e:
            logger.debug(
                f"Could not count pattern-layer files in {patterns_dir}: {e}"
            )
    return count


def _merge_manifests(
    base: Dict[str, Any], extension: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge two template manifests with extension values overriding base.

    Scalar values from extension override base.  Dict values are shallow-merged
    (extension keys override base keys).  List values are concatenated with
    deduplication.

    Args:
        base: Base template manifest.
        extension: Extension template manifest.

    Returns:
        Merged manifest dict.
    """
    merged = dict(base)

    for key, ext_val in extension.items():
        base_val = merged.get(key)

        if isinstance(base_val, dict) and isinstance(ext_val, dict):
            # Shallow merge dicts — extension keys override base keys
            merged_dict = dict(base_val)
            merged_dict.update(ext_val)
            merged[key] = merged_dict
        elif isinstance(base_val, list) and isinstance(ext_val, list):
            # Concatenate lists, deduplicate preserving order
            seen: set = set()
            combined: list = []
            for item in base_val + ext_val:
                # For dicts, use json serialization as hashable key
                hash_key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else item
                if hash_key not in seen:
                    seen.add(hash_key)
                    combined.append(item)
            merged[key] = combined
        else:
            # Scalars: extension wins
            merged[key] = ext_val

    return merged


def _apply_single_template(
    template_dir: Path,
    target_dir: Path,
    *,
    overwritable: Optional[set] = None,
) -> Dict[str, List[str]]:
    """Apply files from a single template directory to the target.

    This is the inner copy routine used by ``apply_template`` for each
    template in the inheritance chain.

    Files that already exist at the destination are only overwritten if their
    resolved path is in *overwritable* (i.e. they were created by a previous
    template in the chain).  Pre-existing user files are never clobbered.

    Args:
        template_dir: Template source directory.
        target_dir: Project target directory.
        overwritable: Set of resolved destination paths that may be overwritten
            (populated by previous templates in the chain).

    Returns:
        Dict with keys ``agents``, ``rules``, ``claude_md``, ``manifest``
        listing what was copied.
    """
    if overwritable is None:
        overwritable = set()

    result: Dict[str, List[str]] = {
        "agents": [],
        "rules": [],
        "claude_md": [],
        "manifest": [],
    }

    def _copy(src: Path, dest: Path, label: str = "") -> bool:
        """Copy src to dest, respecting overwritable set."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        resolved = dest.resolve()
        if dest.exists() and resolved not in overwritable:
            logger.info(f"Skipping {label or dest.name}: already exists at {dest}")
            return False
        shutil.copy2(src, dest)
        overwritable.add(resolved)
        return True

    # --- Agents ---
    agents_target = target_dir / ".claude" / "agents"
    for agents_dir in [
        template_dir / ".claude" / "agents",
        template_dir / "agents",
    ]:
        if not agents_dir.is_dir():
            continue
        for agent_file in sorted(agents_dir.iterdir()):
            if not agent_file.is_file() or agent_file.suffix != ".md" or agent_file.name.startswith("."):
                continue
            dest = agents_target / agent_file.name
            if _copy(agent_file, dest, f"agent {agent_file.name}"):
                result["agents"].append(agent_file.name)

    # --- Rules ---
    rules_src = template_dir / ".claude" / "rules"
    rules_target = target_dir / ".claude" / "rules"
    if rules_src.is_dir():
        for rule_file in sorted(rules_src.rglob("*.md")):
            rel_path = rule_file.relative_to(rules_src)
            dest = rules_target / rel_path
            if _copy(rule_file, dest, f"rule {rel_path}"):
                result["rules"].append(str(rel_path))

    # --- CLAUDE.md ---
    for rel in ["CLAUDE.md", ".claude/CLAUDE.md"]:
        src = template_dir / rel
        if src.is_file():
            dest = target_dir / rel
            if _copy(src, dest, rel):
                result["claude_md"].append(rel)

    # --- manifest.json (raw copy; merged manifest written separately) ---
    manifest_src = template_dir / "manifest.json"
    if manifest_src.is_file():
        dest = target_dir / ".claude" / "manifest.json"
        if _copy(manifest_src, dest, "manifest.json"):
            result["manifest"].append("manifest.json")

    return result


def apply_template(
    template_name: str,
    target_dir: Optional[Path] = None,
    *,
    base_only: bool = False,
) -> bool:
    """Apply a template to the target directory, honouring ``extends``.

    Creates the basic GuardKit directory structure and copies template-specific
    content including agents, rules, CLAUDE.md, and manifest.json.

    When a template's manifest.json contains an ``extends`` field, the base
    template is installed first and the extension template is overlaid on top
    so that extension files take precedence.

    Handles structural variations across templates:
    - Agents may be in agents/ or .claude/agents/
    - CLAUDE.md may be at root, .claude/, or both
    - manifest.json may or may not be present
    - Code scaffold directories (templates/, config/, docker/) are NOT copied

    Args:
        template_name: Name of the template to apply.
        target_dir: Target directory (defaults to cwd).
        base_only: If True and the template extends another, install
            only the base template (ignore the extension).

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

    # Step 3: Resolve the extends chain (base → … → extension)
    chain = _resolve_extends_chain(template_name)

    # Validate all templates in the chain are resolvable
    for name in chain:
        if _resolve_template_source_dir(name) is None:
            logger.error(
                f"Base template '{name}' required by extends chain not found. "
                f"Chain: {' → '.join(chain)}"
            )
            return False

    # If --base-only, only install the first template in the chain
    if base_only and len(chain) > 1:
        chain = chain[:1]
        logger.info(f"--base-only: installing base template '{chain[0]}' only")

    # Step 4: Apply each template in chain order (base first, extension last)
    # The overwritable set tracks files created by previous templates in the
    # chain so that extension templates can overlay them.  Pre-existing user
    # files are never clobbered.
    total_agents: List[str] = []
    total_rules: List[str] = []
    total_claude: List[str] = []
    overwritable: set = set()

    for tpl_name in chain:
        tpl_dir = _resolve_template_source_dir(tpl_name)
        if tpl_dir is None:
            continue  # Already validated above

        logger.info(f"Applying template layer: {tpl_name}")
        copied = _apply_single_template(tpl_dir, target_dir, overwritable=overwritable)
        total_agents.extend(copied["agents"])
        total_rules.extend(copied["rules"])
        total_claude.extend(copied["claude_md"])

    # Step 5: Write merged manifest if chain has multiple templates
    if len(chain) > 1:
        manifests = []
        for tpl_name in chain:
            tpl_dir = _resolve_template_source_dir(tpl_name)
            if tpl_dir is not None:
                m = _load_manifest(tpl_dir)
                if m is not None:
                    manifests.append(m)

        if len(manifests) >= 2:
            merged = manifests[0]
            for m in manifests[1:]:
                merged = _merge_manifests(merged, m)

            merged_path = target_dir / ".claude" / "manifest.json"
            merged_path.write_text(json.dumps(merged, indent=2) + "\n")
            logger.info("Wrote merged manifest.json")

    if total_agents:
        # Deduplicate (extension may override base agents with same name)
        unique = list(dict.fromkeys(total_agents))
        logger.info(f"Copied {len(unique)} agent(s): {', '.join(unique)}")

    if total_rules:
        unique = list(dict.fromkeys(total_rules))
        logger.info(f"Copied {len(unique)} rule(s)")

    if total_claude:
        unique = list(dict.fromkeys(total_claude))
        logger.info(f"Copied CLAUDE.md: {', '.join(unique)}")

    if len(chain) > 1:
        logger.info(
            f"Applied template '{template_name}' (extends: {' → '.join(chain)}) "
            f"to {target_dir}"
        )
    else:
        logger.info(f"Applied template '{template_name}' to {target_dir}")

    return True


# ---------------------------------------------------------------------------
# Interactive project setup (optional; renders CLAUDE.md, no knowledge graph)
# ---------------------------------------------------------------------------


@dataclass
class _ProjectInfo:
    """Lightweight project metadata collected during ``--interactive`` init.

    Replaces the retired Graphiti ``ProjectOverviewEpisode`` (FEAT-MEM-09); used
    only to render CLAUDE.md and carries no knowledge-graph coupling.
    """

    project_name: str
    purpose: str
    primary_language: str
    frameworks: List[str]
    key_goals: List[str]


async def interactive_setup(project_name: str) -> _ProjectInfo:
    """Prompt for project purpose, primary language, frameworks, and key goals.

    Args:
        project_name: Name of the project.

    Returns:
        A ``_ProjectInfo`` populated with the user-provided information.
    """
    default_purpose = "A software project"
    purpose = Prompt.ask(
        "What is the purpose of this project?",
        default=default_purpose,
    )
    # Handle empty response (e.g., when mocked in tests)
    if not purpose:
        purpose = default_purpose

    default_language = "python"
    primary_language = Prompt.ask(
        "What is the primary programming language?",
        choices=["python", "typescript", "go", "rust", "java", "other"],
        default=default_language,
    )
    if not primary_language:
        primary_language = default_language

    frameworks_input = Prompt.ask(
        "What frameworks are you using? (comma-separated)",
        default="",
    )
    frameworks = [f.strip() for f in frameworks_input.split(",") if f.strip()]

    key_goals: List[str] = []
    console.print("Enter key goals (empty line to finish):")
    while True:
        goal = Prompt.ask("Goal", default="")
        if not goal:
            break
        key_goals.append(goal)

    return _ProjectInfo(
        project_name=project_name,
        purpose=purpose,
        primary_language=primary_language,
        frameworks=frameworks,
        key_goals=key_goals,
    )


def generate_claude_md(info: _ProjectInfo, target_dir: Path) -> None:
    """Generate CLAUDE.md from collected project information.

    Args:
        info: Project metadata gathered by :func:`interactive_setup`.
        target_dir: Directory where CLAUDE.md should be created.
    """
    frameworks_text = ", ".join(info.frameworks) if info.frameworks else "None specified"
    goals_text = (
        "\n".join(f"- {goal}" for goal in info.key_goals)
        if info.key_goals
        else "None specified"
    )

    content = f"""# {info.project_name}

## Purpose
{info.purpose}

## Technology Stack
- **Primary Language**: {info.primary_language}
- **Frameworks**: {frameworks_text}

## Key Goals
{goals_text}
"""
    (target_dir / "CLAUDE.md").write_text(content)


async def _cmd_init(
    template: str,
    project_name: Optional[str] = None,
    interactive: bool = False,
    verbose: bool = False,
    base_only: bool = False,
) -> int:
    """Async implementation of the init command.

    Applies a template and, optionally, runs interactive project setup. Knowledge
    capture is provided by the fleet-memory backend, which is env-driven
    (``FLEET_MEMORY_*`` / ``GUARDKIT_MEMORY_BACKEND``) and needs no init-time
    configuration.

    Args:
        template: Template name to apply.
        project_name: Override project name (defaults to directory name).
        interactive: If True, run interactive setup and offer to write CLAUDE.md.
        verbose: If True, show all log output including third-party DEBUG/INFO.
        base_only: If True, install only the base template when extends is used.

    Returns:
        Exit code (0 for success).
    """
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    project_dir = Path.cwd()
    project_name = project_name or project_dir.name

    console.print(f"[bold]Initializing GuardKit in {project_dir}[/bold]")
    console.print(f"  Project: {project_name}")
    console.print(f"  Template: {template}")

    # Step 1: Apply template
    console.print("\n[bold]Step 1: Applying template...[/bold]")
    if apply_template(template, project_dir, base_only=base_only):
        console.print(f"  [green]Applied template: {template}[/green]")
    else:
        console.print(
            f"  [yellow]Warning: Template '{template}' not found, using defaults[/yellow]"
        )

    # Step 1.0b: Auto-install the features/conftest.py pytest-bdd bridge when the
    # project already has tagged ``.feature`` files but no bridge
    # (TASK-AB-BDDNEUTRAL01). Guarded + non-raising: a no-op for projects that
    # do not use task-scoped BDD, and never clobbers an existing conftest.
    if install_features_conftest_bridge(project_dir):
        console.print("  [green]Installed features/conftest.py BDD bridge[/green]")

    # Step 1.0c: Scaffold the tier-1 QA format stubs (WS2 B1, 2026-07-07).
    # Per-file skip — never clobbers a repo's existing qa/ instances.
    qa_files = install_qa_scaffold(project_dir)
    if qa_files:
        console.print(
            f"  [green]Scaffolded qa/ format stubs ({len(qa_files)} files — "
            f"see qa/README.md)[/green]"
        )

    # Step 2 (optional): Interactive project setup -> CLAUDE.md
    if interactive:
        console.print("\n[bold]Interactive Setup[/bold]")
        info = await interactive_setup(project_name)
        try:
            should_generate = Confirm.ask(
                "Save this information to CLAUDE.md?", default=True
            )
            if should_generate:
                generate_claude_md(info, project_dir)
                console.print("  [green]Generated CLAUDE.md[/green]")
        except Exception:
            # In non-interactive contexts (e.g., tests without mock), skip prompt.
            pass

    # Summary
    console.print("\n[bold green]GuardKit initialized successfully![/bold green]")
    console.print(
        "\n  [dim]Memory: knowledge capture is env-driven (fleet-memory). Set "
        "FLEET_MEMORY_* / GUARDKIT_MEMORY_BACKEND to enable; no init-time "
        "config is written.[/dim]"
    )

    try:
        pattern_chain = _resolve_extends_chain(template)
        if base_only and len(pattern_chain) > 1:
            pattern_chain = pattern_chain[:1]
        pattern_layer_count = _count_pattern_layer_files(pattern_chain)
    except Exception as e:
        logger.debug(f"Could not compute pattern-layer count: {e}")
        pattern_layer_count = 0

    if pattern_layer_count > 0:
        console.print(
            f"\n  [cyan]Pattern layer:[/cyan] {pattern_layer_count} scaffold "
            "file(s) present in template (not rendered at init time)"
        )
        console.print(
            "    [dim]Tip: these are consumed by AutoBuild / future "
            "`guardkit render`;\n"
            "         see docs/guides/template-two-layer-model.md[/dim]"
        )

    console.print("\nNext steps:")
    console.print('  1. Create a task: /task-create "Your first task"')
    console.print("  2. Work on it: /task-work TASK-XXX")
    console.print("  3. Complete it: /task-complete TASK-XXX")

    return 0


@click.command()
@click.argument("template", default="default")
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
    help="Interactive setup mode (collects project info into CLAUDE.md)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all log output including third-party DEBUG/INFO messages.",
)
@click.option(
    "--base-only",
    is_flag=True,
    default=False,
    help=(
        "When the selected template extends a base template, install only the "
        "base template (ignore extension-specific files)."
    ),
)
def init(
    template: str,
    project_name: Optional[str],
    interactive: bool,
    verbose: bool,
    base_only: bool,
):
    """Initialize GuardKit in the current directory.

    Applies a template. Knowledge capture is provided by the fleet-memory
    backend and is env-driven (``FLEET_MEMORY_*`` / ``GUARDKIT_MEMORY_BACKEND``),
    so no init-time memory configuration is written.

    TEMPLATE is the name of the template to apply (default: 'default').
    Available templates: default, fastapi-python, react-typescript, nextjs-fullstack, react-fastapi-monorepo, python-library, nats-asyncio-service, langchain-deepagents, langchain-deepagents-orchestrator, langchain-deepagents-weighted-evaluation, dotnet-railway-fastendpoints.
    """
    exit_code = asyncio.run(
        _cmd_init(
            template,
            project_name,
            interactive,
            verbose,
            base_only=base_only,
        )
    )
    if exit_code != 0:
        raise SystemExit(exit_code)

