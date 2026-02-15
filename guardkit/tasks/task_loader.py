"""
Task file loading and parsing utilities.

This module provides centralized task file loading, implementing the DRY principle
from the architectural review (HIGH PRIORITY recommendation #1).

Example:
    >>> from guardkit.tasks.task_loader import TaskLoader
    >>>
    >>> task_data = TaskLoader.load_task("TASK-AB-001")
    >>> print(task_data["requirements"])
    >>> print(task_data["acceptance_criteria"])
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import frontmatter

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class TaskNotFoundError(FileNotFoundError):
    """Raised when task file cannot be found."""

    pass


class TaskParseError(ValueError):
    """Raised when task file cannot be parsed."""

    pass


# ============================================================================
# TaskLoader
# ============================================================================


class TaskLoader:
    """
    Centralized task file loading and parsing.

    This class implements robust task file discovery and YAML parsing,
    addressing the architectural review recommendation to extract shared
    task loading logic.

    Search Paths
    ------------
    Tasks are searched in this order:
    1. tasks/backlog/
    2. tasks/in_progress/
    3. tasks/design_approved/
    4. tasks/in_review/
    5. tasks/blocked/

    Attributes
    ----------
    SEARCH_PATHS : List[str]
        Task directory search order
    """

    SEARCH_PATHS = ["backlog", "in_progress", "design_approved", "in_review", "blocked"]

    @staticmethod
    def load_task(task_id: str, repo_root: Path = None) -> Dict[str, Any]:
        """
        Load task file from standard locations.

        This method searches for the task file across standard directories
        and parses frontmatter and content.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-AB-001")
        repo_root : Path, optional
            Repository root (defaults to current directory)

        Returns
        -------
        Dict[str, Any]
            Parsed task data with keys:
            - task_id: str
            - requirements: str
            - acceptance_criteria: List[str]
            - frontmatter: dict (raw frontmatter metadata)
            - content: str (markdown content)
            - file_path: Path (path to task file)

        Raises
        ------
        TaskNotFoundError
            If task file cannot be found in any search path
        TaskParseError
            If task file cannot be parsed

        Examples
        --------
        >>> task = TaskLoader.load_task("TASK-AB-001")
        >>> print(task["requirements"])
        'Implement OAuth2 authentication'
        >>> print(task["acceptance_criteria"])
        ['Support authorization code flow', 'Handle token refresh']
        """
        repo_root = repo_root or Path.cwd()
        task_path = TaskLoader._find_task_file(task_id, repo_root)

        if not task_path:
            raise TaskNotFoundError(
                f"Task {task_id} not found.\n\n"
                f"Searched locations (including subdirectories):\n"
                + "\n".join(
                    f"  - {repo_root / 'tasks' / dir_name}/**/"
                    for dir_name in TaskLoader.SEARCH_PATHS
                )
                + "\n\n"
                f"Hints:\n"
                f"  - Check task ID format (e.g., TASK-XXX-001)\n"
                f"  - Verify task file exists with .md extension\n"
                f"  - For feature tasks, check tasks/backlog/<feature-slug>/"
            )

        return TaskLoader._parse_task_file(task_path, task_id)

    @staticmethod
    def _find_task_file(task_id: str, repo_root: Path) -> Path:
        """
        Find task file in search paths using recursive glob.

        Searches for files matching {task_id}*.md pattern, allowing for
        both exact matches (TASK-XXX.md) and extended filenames
        (TASK-XXX-descriptive-name.md) in nested directories.

        Parameters
        ----------
        task_id : str
            Task identifier (e.g., "TASK-AB-001")
        repo_root : Path
            Repository root

        Returns
        -------
        Path
            Path to task file, or None if not found
        """
        for dir_name in TaskLoader.SEARCH_PATHS:
            search_dir = repo_root / "tasks" / dir_name
            if not search_dir.exists():
                continue

            # Use rglob for recursive search with pattern matching
            for task_path in search_dir.rglob(f"{task_id}*.md"):
                logger.debug(f"Found task {task_id} at {task_path}")
                return task_path

        return None

    @staticmethod
    def _parse_task_file(path: Path, task_id: str) -> Dict[str, Any]:
        """
        Parse task markdown file with frontmatter.

        This method implements robust YAML parsing with error handling,
        addressing the architectural review recommendation for task loading.

        Parameters
        ----------
        path : Path
            Path to task file
        task_id : str
            Task identifier

        Returns
        -------
        Dict[str, Any]
            Parsed task data

        Raises
        ------
        TaskParseError
            If file cannot be parsed
        """
        try:
            # Parse frontmatter and content
            with open(path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Extract frontmatter metadata
            metadata = dict(post.metadata)

            # Extract requirements (from frontmatter or content)
            requirements = TaskLoader._extract_requirements(metadata, post.content)

            # Extract acceptance criteria
            acceptance_criteria = TaskLoader._extract_acceptance_criteria(
                metadata, post.content
            )

            return {
                "task_id": task_id,
                "requirements": requirements,
                "acceptance_criteria": acceptance_criteria,
                "frontmatter": metadata,
                "content": post.content,
                "file_path": path,
            }

        except Exception as e:
            logger.error(f"Failed to parse task file {path}: {e}", exc_info=True)
            raise TaskParseError(
                f"Failed to parse task {task_id}:\n"
                f"File: {path}\n"
                f"Error: {str(e)}"
            ) from e

    @staticmethod
    def _extract_requirements(metadata: dict, content: str) -> str:
        """
        Extract requirements from task data.

        Tries frontmatter first, then falls back to content parsing.

        Parameters
        ----------
        metadata : dict
            Frontmatter metadata
        content : str
            Markdown content

        Returns
        -------
        str
            Requirements text
        """
        # Try frontmatter first
        if "requirements" in metadata:
            reqs = metadata["requirements"]
            if isinstance(reqs, str):
                return reqs
            elif isinstance(reqs, list):
                return "\n".join(reqs)

        # Fall back to content parsing
        # Look for "## Requirements" section
        lines = content.split("\n")
        in_requirements = False
        requirements_lines = []

        for line in lines:
            if line.strip().lower() in ["## requirements", "## requirement"]:
                in_requirements = True
                continue
            elif in_requirements:
                if line.startswith("##"):  # Next section
                    break
                if line.strip():  # Non-empty line
                    requirements_lines.append(line.strip())

        if requirements_lines:
            return "\n".join(requirements_lines)

        # Default: Use first paragraph of content
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        return paragraphs[0] if paragraphs else "No requirements specified"

    @staticmethod
    def _extract_acceptance_criteria(metadata: dict, content: str) -> List[str]:
        """
        Extract acceptance criteria from task data.

        Tries frontmatter first, then falls back to content parsing.

        Parameters
        ----------
        metadata : dict
            Frontmatter metadata
        content : str
            Markdown content

        Returns
        -------
        List[str]
            List of acceptance criteria
        """
        # Try frontmatter first
        if "acceptance_criteria" in metadata:
            criteria = metadata["acceptance_criteria"]
            if isinstance(criteria, list):
                return criteria
            elif isinstance(criteria, str):
                return [criteria]

        # Fall back to content parsing
        # Look for "## Acceptance Criteria" section
        lines = content.split("\n")
        in_criteria = False
        criteria_lines = []

        for line in lines:
            if line.strip().lower() in [
                "## acceptance criteria",
                "## acceptance criterion",
            ]:
                in_criteria = True
                continue
            elif in_criteria:
                if line.startswith("##"):  # Next section
                    break
                # Only match TOP-LEVEL list items (no leading whitespace).
                # Indented items (e.g., "  - sub-bullet") are sub-criteria
                # belonging to their parent and should not inflate the count.
                if line.startswith(("- [ ] ", "- [x] ", "- ", "* ")):
                    # Extract text after checkbox/bullet
                    text = line.lstrip("- [x] ").lstrip("- [ ] ").lstrip("- ").lstrip("* ")
                    text = text.strip()
                    if text:
                        criteria_lines.append(text)

        return criteria_lines if criteria_lines else ["No acceptance criteria specified"]


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "TaskLoader",
    "TaskNotFoundError",
    "TaskParseError",
]
