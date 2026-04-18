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
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from guardkit.integrations.graphiti.episodes.project_overview import ProjectOverviewEpisode
from guardkit.knowledge.config import _find_project_root, load_graphiti_config
from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig, normalize_project_id
from guardkit.knowledge.project_seeding import estimate_episode_count, seed_project_knowledge
from guardkit.templates.resolver import (
    _get_templates_base_dir as _get_templates_base_dir,
    _get_user_templates_dir as _get_user_templates_dir,
    resolve_template_source_dir as resolve_template_source_dir,
)

console = Console()
logger = logging.getLogger(__name__)

# Directories that should NOT be copied from templates (code scaffold concerns)
_SKIP_DIRS = {"templates", "config", "docker"}


async def _check_llm_reachable(config: GraphitiConfig, timeout: float = 5.0) -> bool:
    """Check if the configured LLM endpoint is reachable.

    Sends a lightweight GET request to the LLM's /models endpoint.
    Returns True immediately for OpenAI cloud provider (assumed always available).

    Args:
        config: Graphiti configuration with LLM provider details.
        timeout: Maximum seconds to wait for a response (default 5).

    Returns:
        True if the LLM endpoint responds within the timeout, False otherwise.
    """
    if config.llm_provider not in ("vllm", "ollama"):
        return True

    if not config.llm_base_url:
        return False

    url = f"{config.llm_base_url.rstrip('/')}/models"

    try:
        import httpx
    except ImportError:
        # httpx unavailable — fall back to urllib
        import urllib.request
        import urllib.error

        try:
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except Exception:
            return False

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(url, timeout=timeout)
            return resp.status_code == 200
    except Exception:
        return False


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


# ---------------------------------------------------------------------------
# MCP configuration helpers
# ---------------------------------------------------------------------------

_MCP_SERVER_PATH_CONFIG = Path.home() / ".guardkit" / "mcp-server-path"
_GRAPHITI_MCP_PATH_ENV = "GRAPHITI_MCP_PATH"

# Default entity types for Graphiti MCP server config
_DEFAULT_ENTITY_TYPES = [
    {"name": "Preference", "description": "User preferences, choices, opinions, or selections"},
    {"name": "Requirement", "description": "Specific needs, features, or functionality that must be fulfilled"},
    {"name": "Procedure", "description": "Standard operating procedures and sequential instructions"},
    {"name": "Topic", "description": "Subject of conversation, interest, or knowledge domain"},
    {"name": "Document", "description": "Information content in various forms (books, articles, reports, etc.)"},
]


def _find_uv_command() -> str:
    """Return the absolute path to the uv command, or 'uv' if not found.

    Returns:
        Absolute path string to uv binary, or 'uv' as fallback.
    """
    uv_path = shutil.which("uv")
    return uv_path if uv_path else "uv"


def discover_graphiti_mcp_path(prompt_if_missing: bool = True) -> Optional[Path]:
    """Discover the Graphiti MCP server installation path.

    Discovery order:
    1. GRAPHITI_MCP_PATH environment variable
    2. ~/.guardkit/mcp-server-path config file
    3. Prompt user if prompt_if_missing is True

    If the path is discovered via prompt, stores it to the config file for
    future use.

    Args:
        prompt_if_missing: If True, prompt the user when path not found.

    Returns:
        Path to the Graphiti MCP server directory, or None if not found.
    """
    import os

    # Strategy 1: environment variable
    env_val = os.environ.get(_GRAPHITI_MCP_PATH_ENV)
    if env_val:
        candidate = Path(env_val).expanduser().resolve()
        if candidate.is_dir():
            logger.debug(f"Graphiti MCP path from env: {candidate}")
            return candidate
        logger.warning(f"GRAPHITI_MCP_PATH={env_val} does not exist, ignoring")

    # Strategy 2: config file
    if _MCP_SERVER_PATH_CONFIG.is_file():
        try:
            stored = _MCP_SERVER_PATH_CONFIG.read_text().strip()
            if stored:
                candidate = Path(stored).expanduser().resolve()
                if candidate.is_dir():
                    logger.debug(f"Graphiti MCP path from config: {candidate}")
                    return candidate
                logger.warning(f"Stored MCP path {stored} does not exist, ignoring")
        except Exception as e:
            logger.debug(f"Could not read mcp-server-path config: {e}")

    # Strategy 3: prompt user
    if prompt_if_missing:
        try:
            user_input = Prompt.ask(
                "Enter path to Graphiti MCP server directory",
                default="",
            )
            if user_input:
                candidate = Path(user_input).expanduser().resolve()
                if candidate.is_dir():
                    # Store for future use
                    try:
                        _MCP_SERVER_PATH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
                        _MCP_SERVER_PATH_CONFIG.write_text(str(candidate))
                        logger.info(f"Stored Graphiti MCP path to {_MCP_SERVER_PATH_CONFIG}")
                    except Exception as e:
                        logger.debug(f"Could not store MCP path: {e}")
                    return candidate
                else:
                    console.print(f"  [yellow]Warning: Path does not exist: {candidate}[/yellow]")
        except Exception as e:
            logger.debug(f"Prompt failed: {e}")

    return None


def generate_mcp_server_config(
    project_id: str,
    settings: Any,
) -> Dict[str, Any]:
    """Generate the per-project Graphiti MCP server YAML config as a dict.

    Reads LLM/embedding/database settings from the guardkit graphiti settings
    object and produces a config dict compatible with the Graphiti MCP server.

    Args:
        project_id: Normalized project ID for namespace.
        settings: GraphitiSettings instance loaded from .guardkit/graphiti.yaml.

    Returns:
        Dict representing the MCP server YAML config.
    """
    llm_base_url = getattr(settings, "llm_base_url", None) or "http://localhost:8000/v1"
    llm_model = getattr(settings, "llm_model", None) or "gpt-4o"
    llm_max_tokens = getattr(settings, "llm_max_tokens", None) or 4096
    embedding_base_url = getattr(settings, "embedding_base_url", None) or "http://localhost:8001/v1"
    embedding_model = getattr(settings, "embedding_model", None) or "text-embedding-ada-002"
    embedding_dimensions = getattr(settings, "embedding_dimensions", None) or 1024
    falkordb_host = getattr(settings, "falkordb_host", None) or "localhost"
    falkordb_port = getattr(settings, "falkordb_port", None) or 6379

    return {
        "server": {"transport": "stdio"},
        "llm": {
            "provider": "openai",
            "model": llm_model,
            "max_tokens": llm_max_tokens,
            "providers": {
                "openai": {
                    "api_key": "${OPENAI_API_KEY}",
                    "api_url": f"${{LLM_API_URL:{llm_base_url}}}",
                }
            },
        },
        "embedder": {
            "provider": "openai",
            "model": embedding_model,
            "dimensions": embedding_dimensions,
            "providers": {
                "openai": {
                    "api_key": "${OPENAI_API_KEY}",
                    "api_url": f"${{EMBEDDING_API_URL:{embedding_base_url}}}",
                }
            },
        },
        "database": {
            "provider": "falkordb",
            "providers": {
                "falkordb": {
                    "uri": f"redis://{falkordb_host}:{falkordb_port}",
                    "password": "",
                    "database": "default_db",
                }
            },
        },
        "graphiti": {
            "group_id": project_id,
            "user_id": "user",
            "entity_types": _DEFAULT_ENTITY_TYPES,
        },
    }


def write_mcp_server_config(
    project_id: str,
    mcp_server_path: Path,
    settings: Any,
) -> Optional[Path]:
    """Write the per-project MCP server config YAML to {mcp_server_path}/config/.

    Args:
        project_id: Normalized project ID.
        mcp_server_path: Path to the Graphiti MCP server directory.
        settings: GraphitiSettings instance.

    Returns:
        Path to the written config file, or None on failure.
    """
    try:
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, cannot write MCP server config")
            return None

        config_dir = mcp_server_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / f"config-{project_id}.yaml"

        config_data = generate_mcp_server_config(project_id, settings)

        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        logger.info(f"Written MCP server config to {config_file}")
        return config_file

    except Exception as e:
        logger.warning(f"Failed to write MCP server config: {e}")
        return None


def generate_mcp_json_entry(
    project_id: str,
    mcp_server_path: Path,
    config_path: Path,
    settings: Any,
) -> Dict[str, Any]:
    """Generate the mcpServers entry dict for .mcp.json.

    Args:
        project_id: Normalized project ID (used as server key).
        mcp_server_path: Absolute path to Graphiti MCP server directory.
        config_path: Absolute path to the per-project config YAML.
        settings: GraphitiSettings instance for endpoint env vars.

    Returns:
        Dict with the mcpServers entry for this project.
    """
    uv_cmd = _find_uv_command()
    llm_base_url = getattr(settings, "llm_base_url", None) or "http://localhost:8000/v1"
    embedding_base_url = getattr(settings, "embedding_base_url", None) or "http://localhost:8001/v1"
    embedding_dimensions = getattr(settings, "embedding_dimensions", None) or 1024

    return {
        "type": "stdio",
        "command": uv_cmd,
        "args": [
            "--directory",
            str(mcp_server_path),
            "run",
            "main.py",
            "--transport",
            "stdio",
            "--config",
            str(config_path),
        ],
        "env": {
            "CONFIG_PATH": str(config_path),
            "OPENAI_API_KEY": "not-needed-vllm-local",
            "LLM_API_URL": llm_base_url,
            "EMBEDDING_API_URL": embedding_base_url,
            "EMBEDDING_DIM": str(embedding_dimensions),
        },
    }


def write_mcp_json(
    target_dir: Path,
    mcp_server_path: Path,
    project_id: str,
    settings: Any,
    server_key: str = "graphiti",
) -> bool:
    """Write or merge the Graphiti MCP entry into .mcp.json.

    If .mcp.json already exists, reads it and merges the graphiti entry under
    mcpServers, preserving all other server entries. If it does not exist,
    creates it fresh.

    Args:
        target_dir: Project directory where .mcp.json should be written.
        mcp_server_path: Path to the Graphiti MCP server directory.
        project_id: Normalized project ID.
        settings: GraphitiSettings instance.
        server_key: Key to use in mcpServers (default: "graphiti").

    Returns:
        True if written successfully, False otherwise.
    """
    mcp_json_path = target_dir / ".mcp.json"

    try:
        # Write the per-project server config YAML first
        config_path = write_mcp_server_config(project_id, mcp_server_path, settings)
        if config_path is None:
            logger.warning("Could not write MCP server config, skipping .mcp.json")
            return False

        # Generate the mcpServers entry
        entry = generate_mcp_json_entry(project_id, mcp_server_path, config_path, settings)

        # Load existing .mcp.json or start fresh
        existing: Dict[str, Any] = {}
        if mcp_json_path.is_file():
            try:
                with open(mcp_json_path, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    existing = loaded
            except Exception as e:
                logger.warning(f"Could not parse existing .mcp.json: {e}, overwriting")

        # Merge: add/update mcpServers.graphiti
        if "mcpServers" not in existing or not isinstance(existing["mcpServers"], dict):
            existing["mcpServers"] = {}
        existing["mcpServers"][server_key] = entry

        # Write back
        with open(mcp_json_path, "w") as f:
            json.dump(existing, f, indent=2)
            f.write("\n")

        logger.info(f"Written MCP config to {mcp_json_path}")
        return True

    except Exception as e:
        logger.warning(f"Failed to write .mcp.json: {e}")
        return False


# Template resolution is now provided by guardkit.templates.resolver.
# The wrapper below delegates to the module-level _get_templates_base_dir
# and _get_user_templates_dir names so that existing test mocks which
# patch "guardkit.cli.init._get_templates_base_dir" etc. continue to
# control behaviour.  The canonical, public API lives in
# guardkit.templates.resolver.resolve_template_source_dir.


def _resolve_template_source_dir(template_name: str) -> Optional[Path]:
    """Resolve the source directory for a template.

    Thin wrapper kept for backward compatibility with existing call sites
    and test mocks.  Delegates to :func:`resolve_template_source_dir` in
    ``guardkit.templates.resolver`` via module-level helper imports.

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
    with_mcp: bool = False,
    base_only: bool = False,
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
        with_mcp: If True, generate .mcp.json and per-project MCP server config.
        base_only: If True, install only the base template when extends is used.

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
    if apply_template(template, project_dir, base_only=base_only):
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
                llm_max_tokens=settings.llm_max_tokens,
                embedding_provider=settings.embedding_provider,
                embedding_base_url=settings.embedding_base_url,
                embedding_model=settings.embedding_model,
                embedding_dimensions=getattr(settings, "embedding_dimensions", None),
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
                            # Pre-flight: check LLM reachability before spending
                            # ~32s on retries if the endpoint is down.
                            llm_reachable = await _check_llm_reachable(config)
                            if not llm_reachable:
                                llm_url = config.llm_base_url or "(not configured)"
                                console.print(
                                    f"\n  [yellow]LLM at {llm_url} is unreachable."
                                    " System knowledge seeding requires an LLM.[/yellow]"
                                )
                                try:
                                    if no_questions:
                                        skip_system_seed = True
                                    else:
                                        skip_system_seed = Confirm.ask(
                                            "Skip system seeding?",
                                            default=True,
                                        )
                                except Exception:
                                    skip_system_seed = True

                                if skip_system_seed:
                                    console.print(
                                        "  [dim]Skipping system seeding."
                                        " Run 'guardkit graphiti seed-system'"
                                        " when the LLM is available.[/dim]"
                                    )
                                    should_seed_system = False
                                else:
                                    console.print(
                                        "\n  [red]Cannot proceed without LLM.[/red]"
                                    )
                                    console.print(
                                        "  [dim]Check that the LLM server is running at"
                                        f" {llm_url}\n"
                                        "  and update .guardkit/graphiti.yaml if the"
                                        " URL has changed.[/dim]"
                                    )
                                    return  # Exit init early

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

    # Step 3 (optional): Generate MCP configuration
    mcp_configured = False
    if with_mcp:
        console.print("\n[bold]Step 3: Generating MCP configuration...[/bold]")
        try:
            settings = load_graphiti_config()
            project_id = normalize_project_id(project_name)
            mcp_server_path = discover_graphiti_mcp_path(prompt_if_missing=not no_questions)
            if mcp_server_path is not None:
                if write_mcp_json(project_dir, mcp_server_path, project_id, settings):
                    config_path = mcp_server_path / "config" / f"config-{project_id}.yaml"
                    console.print(f"  [green]Generated .mcp.json with Graphiti MCP config[/green]")
                    console.print(f"  [green]Written MCP server config: {config_path}[/green]")
                    mcp_configured = True
                    # Warn if embedding dimensions may be inconsistent between Python client and MCP
                    explicit_dims = getattr(settings, "embedding_dimensions", None)
                    if explicit_dims is None:
                        model = getattr(settings, "embedding_model", None) or ""
                        from guardkit.knowledge.graphiti_client import KNOWN_EMBEDDING_DIMS
                        known_dim = KNOWN_EMBEDDING_DIMS.get(model)
                        if known_dim is not None and known_dim != 1024:
                            console.print(
                                f"  [yellow]Warning: embedding_dimensions not set in .guardkit/graphiti.yaml.[/yellow]\n"
                                f"  [yellow]MCP server will use 1024 dimensions (default), but model "
                                f"'{model}' default is {known_dim}.[/yellow]\n"
                                f"  [dim]If this FalkorDB was seeded with 1024-dim vectors (Matryoshka), "
                                f"add 'embedding_dimensions: 1024' to .guardkit/graphiti.yaml.[/dim]"
                            )
                else:
                    console.print("  [yellow]Warning: Could not write .mcp.json[/yellow]")
            else:
                console.print(
                    "  [yellow]Warning: Graphiti MCP server path not found.[/yellow]\n"
                    "  [dim]Set GRAPHITI_MCP_PATH env var or re-run with --with-mcp "
                    "after cloning the Graphiti repo.[/dim]"
                )
        except Exception as e:
            console.print(f"  [yellow]Warning: MCP config error: {e}[/yellow]")
            logger.debug(f"MCP config error: {e}", exc_info=True)

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
        console.print(
            "  [dim]Tip: If using a local LLM (~2x slower than GB10 vLLM), use "
            "--timeout to increase per-episode timeout "
            "(e.g., guardkit graphiti seed-system --timeout 300).[/dim]"
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
@click.option(
    "--with-mcp",
    is_flag=True,
    default=False,
    help=(
        "Generate .mcp.json and per-project MCP server config for Claude Code "
        "Graphiti integration. Discovers the Graphiti MCP server path via "
        "GRAPHITI_MCP_PATH env var, ~/.guardkit/mcp-server-path, or user prompt."
    ),
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
    skip_graphiti: bool,
    project_name: Optional[str],
    interactive: bool,
    copy_graphiti: bool,
    copy_graphiti_from: Optional[str],
    verbose: bool,
    no_questions: bool,
    with_mcp: bool,
    base_only: bool,
):
    """Initialize GuardKit in the current directory.

    Applies a template and optionally seeds project knowledge to Graphiti.

    TEMPLATE is the name of the template to apply (default: 'default').
    Available templates: default, fastapi-python, react-typescript, nextjs-fullstack, react-fastapi-monorepo, python-library, nats-asyncio-service, langchain-deepagents, langchain-deepagents-orchestrator, langchain-deepagents-weighted-evaluation, dotnet-railway-fastendpoints.
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
            copy_graphiti_value, verbose, no_questions, with_mcp,
            base_only=base_only,
        )
    )
    if exit_code != 0:
        raise SystemExit(exit_code)
