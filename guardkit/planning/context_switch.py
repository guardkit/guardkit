"""Context switching logic for GuardKit multi-project management.

This module provides functionality for switching between different project
contexts and managing project configuration. It supports:
- Loading and saving project configuration from .guardkit/config.yaml
- Switching active project context
- Finding active tasks in a project
- Querying Graphiti for architecture overview (graceful degradation)

Example Usage:
    from guardkit.planning.context_switch import (
        GuardKitConfig,
        execute_context_switch,
        format_context_switch_display,
    )

    config = GuardKitConfig()
    result = await execute_context_switch(client, "my-project", config)
    print(format_context_switch_display(result, mode="switch"))
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Try to import yaml, gracefully degrade if not available
try:
    import yaml
    _yaml_available = True
except ImportError:
    _yaml_available = False
    logger.warning("PyYAML not installed. Config management will not work.")


class GuardKitConfig:
    """Manages .guardkit/config.yaml for project context.

    Provides methods to load, save, and manage project configuration
    including active project tracking and known projects registry.

    Attributes:
        _path: Path to the config file
        _data: Loaded configuration data

    Example:
        config = GuardKitConfig()
        print(config.active_project)  # Current active project
        config.set_active_project("new-project")  # Switch projects
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize GuardKitConfig.

        Args:
            config_path: Path to config file. Defaults to .guardkit/config.yaml in cwd.
        """
        self._path = config_path or Path(".guardkit/config.yaml")
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load config from YAML file.

        Returns:
            Configuration dict. Returns empty dict if file missing or invalid.
        """
        if not _yaml_available:
            logger.warning("PyYAML not available, returning empty config")
            return {}

        if not self._path.exists():
            logger.debug(f"Config file not found: {self._path}")
            return {}

        try:
            with open(self._path, "r") as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except yaml.YAMLError as e:
            logger.warning(f"Invalid YAML in config file: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
            return {}

    def _save(self) -> None:
        """Write config back to YAML file.

        Creates parent directories if they don't exist.
        """
        if not _yaml_available:
            logger.warning("PyYAML not available, cannot save config")
            return

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                yaml.safe_dump(self._data, f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    @property
    def active_project(self) -> Optional[Dict[str, Any]]:
        """Get current active project.

        Returns:
            Dict with project details (path, last_accessed, etc.) or None if not set.
        """
        active_id = self._data.get("active_project")
        if not active_id:
            return None

        known_projects = self._data.get("known_projects", {})
        project = known_projects.get(active_id)
        if project:
            # Include the ID in the returned dict
            return {"id": active_id, **project}
        return None

    def get_known_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Look up a project by ID.

        Args:
            project_id: The project identifier to look up.

        Returns:
            Dict with project details or None if not found.
        """
        known_projects = self._data.get("known_projects", {})
        project = known_projects.get(project_id)
        if project:
            return {"id": project_id, **project}
        return None

    def set_active_project(self, project_id: str) -> None:
        """Switch active project, update last_accessed timestamp.

        Args:
            project_id: The project ID to switch to.

        Raises:
            ValueError: If project_id is not in known_projects.
        """
        known_projects = self._data.get("known_projects", {})
        if project_id not in known_projects:
            raise ValueError(f"Project '{project_id}' is unknown. Add it to known_projects first.")

        # Update active project
        self._data["active_project"] = project_id

        # Update last_accessed timestamp
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        known_projects[project_id]["last_accessed"] = now
        self._data["known_projects"] = known_projects

        # Persist changes
        self._save()

    def list_known_projects(self) -> List[Dict[str, Any]]:
        """Return all known projects.

        Returns:
            List of project dicts, each containing id and project details.
        """
        known_projects = self._data.get("known_projects", {})
        result = []
        for project_id, project_data in known_projects.items():
            result.append({"id": project_id, **project_data})
        return result


def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Markdown content with optional YAML frontmatter.

    Returns:
        Parsed frontmatter dict, or empty dict if no frontmatter.
    """
    if not _yaml_available:
        return {}

    if not content.startswith("---"):
        return {}

    try:
        # Find the closing ---
        end_marker = content.find("---", 3)
        if end_marker == -1:
            return {}

        frontmatter = content[3:end_marker].strip()
        data = yaml.safe_load(frontmatter)
        return data if data else {}
    except Exception:
        return {}


def _find_active_tasks(project_path: Optional[str]) -> List[Dict[str, Any]]:
    """Find in-progress and pending tasks from task directories.

    Args:
        project_path: Path to the project root directory.

    Returns:
        List of task dicts with id, title, status. Sorted by status
        (in_progress first, then backlog). Empty list if path is None
        or doesn't exist.
    """
    if project_path is None:
        return []

    project = Path(project_path)
    if not project.exists():
        return []

    tasks: List[Dict[str, Any]] = []

    # Check in_progress and backlog directories
    for status, dir_name in [("in_progress", "in_progress"), ("backlog", "backlog")]:
        task_dir = project / "tasks" / dir_name
        if not task_dir.exists():
            continue

        # Find all .md files (including in subdirectories)
        for task_file in task_dir.rglob("*.md"):
            try:
                content = task_file.read_text()
                frontmatter = _parse_frontmatter(content)

                if frontmatter:
                    task = {
                        "id": frontmatter.get("id", task_file.stem),
                        "title": frontmatter.get("title", task_file.stem),
                        "status": frontmatter.get("status", status),
                    }
                    tasks.append(task)
            except Exception as e:
                logger.debug(f"Error reading task file {task_file}: {e}")
                continue

    # Sort: in_progress first, then backlog
    status_order = {"in_progress": 0, "backlog": 1}
    tasks.sort(key=lambda t: status_order.get(t["status"], 2))

    return tasks


async def execute_context_switch(
    client: Optional[Any],  # GraphitiClient or None
    target_project: str,
    config: GuardKitConfig,
) -> Dict[str, Any]:
    """Switch active project context and display orientation.

    Validates the target project exists, updates the config,
    queries Graphiti for architecture overview (if available),
    and finds active tasks.

    Args:
        client: GraphitiClient instance or None (graceful degradation).
        target_project: The project ID to switch to.
        config: GuardKitConfig instance for managing configuration.

    Returns:
        Dict with switch result:
        - status: "success" or "error"
        - message: Human-readable message (for errors)
        - project_id: The target project ID
        - project_path: The project path
        - architecture: Architecture info from Graphiti (empty if unavailable)
        - active_tasks: List of in-progress and backlog tasks
    """
    # Check if project exists
    project = config.get_known_project(target_project)
    if project is None:
        return {
            "status": "error",
            "message": f"Project '{target_project}' not found in known projects.",
            "project_id": target_project,
        }

    # Update config to new active project
    try:
        config.set_active_project(target_project)
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
            "project_id": target_project,
        }

    # Get project path
    project_path = project.get("path")

    # Query Graphiti for architecture overview (graceful degradation)
    architecture = []
    if client is not None and hasattr(client, "enabled") and client.enabled:
        try:
            # Search for architecture info
            results = await client.search(
                query="architecture overview",
                group_ids=["project_architecture"],
                num_results=5,
            )
            architecture = results if results else []
        except Exception as e:
            logger.debug(f"Graphiti search failed: {e}")
            architecture = []

    # Find active tasks
    active_tasks = _find_active_tasks(project_path)

    return {
        "status": "success",
        "project_id": target_project,
        "project_path": project_path,
        "architecture": architecture,
        "active_tasks": active_tasks,
    }


def format_context_switch_display(
    result: Dict[str, Any],
    mode: str = "switch",
) -> str:
    """Format context switch result for display.

    Args:
        result: The result dict from execute_context_switch or project list.
        mode: Display mode - "switch", "list", or "current".

    Returns:
        Formatted string for display.
    """
    lines: List[str] = []

    if mode == "list":
        # List mode: show all known projects
        projects = result.get("projects", [])
        if not projects:
            return "No known projects."

        lines.append("Known Projects:")
        lines.append("-" * 40)
        for proj in projects:
            proj_id = proj.get("id", "unknown")
            path = proj.get("path", "")
            last_accessed = proj.get("last_accessed", "never")
            lines.append(f"  {proj_id}")
            lines.append(f"    Path: {path}")
            lines.append(f"    Last accessed: {last_accessed}")
            lines.append("")

        return "\n".join(lines)

    if mode == "current":
        # Current mode: show active project info
        if result.get("status") == "error":
            return f"Error: {result.get('message', 'Unknown error')}"

        project_id = result.get("project_id", "unknown")
        project_path = result.get("project_path", "")

        lines.append(f"Current Project: {project_id}")
        lines.append(f"Path: {project_path}")

        active_tasks = result.get("active_tasks", [])
        if active_tasks:
            lines.append("")
            lines.append("Active Tasks:")
            for task in active_tasks[:5]:  # Limit to 5
                task_id = task.get("id", "")
                title = task.get("title", "")
                status = task.get("status", "")
                lines.append(f"  [{status}] {task_id}: {title}")

        return "\n".join(lines)

    # Switch mode (default): show orientation after switch
    if result.get("status") == "error":
        return f"Error: {result.get('message', 'Unknown error')}"

    project_id = result.get("project_id", "unknown")
    project_path = result.get("project_path", "")

    lines.append(f"Switched to: {project_id}")
    lines.append(f"Path: {project_path}")

    # Show architecture if available
    architecture = result.get("architecture", [])
    if architecture:
        lines.append("")
        lines.append("Architecture Overview:")
        for item in architecture[:3]:  # Limit to 3
            fact = item.get("fact", "")
            if fact:
                lines.append(f"  • {fact[:100]}...")

    # Show active tasks
    active_tasks = result.get("active_tasks", [])
    if active_tasks:
        lines.append("")
        lines.append("Active Tasks:")
        for task in active_tasks[:5]:  # Limit to 5
            task_id = task.get("id", "")
            title = task.get("title", "")
            status = task.get("status", "")
            lines.append(f"  [{status}] {task_id}: {title}")

    return "\n".join(lines)
