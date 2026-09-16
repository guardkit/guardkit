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
import re
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

        # Without a dedicated section the complete task body is the requirement.
        # Task files commonly use domain-specific sections instead of a generic
        # ``## Requirements`` heading, so selecting only the first paragraph can
        # silently reduce the task to its title or preamble.
        body = content.strip()
        return body if body else "No requirements specified"

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

        # Fall back to content parsing. Each top-level list item is one
        # criterion; all following lines belong to it until the next top-level
        # item or peer section. This preserves wrapped prose, nested lists and
        # fenced examples as part of the criterion that they qualify.
        lines = content.split("\n")
        in_criteria = False
        criteria_lines = []
        current_criterion = None
        fence_character = None
        fence_length = 0

        criterion_pattern = re.compile(
            r"^(?:- \[(?: |x|X)\](?: |$)|- |\* )(?P<text>.*)$"
        )
        peer_heading_pattern = re.compile(r"^##(?!#)(?:[ \t]+|$)")
        fence_pattern = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})")

        def finish_criterion() -> None:
            nonlocal current_criterion
            if current_criterion is None:
                return
            while current_criterion and not current_criterion[-1].strip():
                current_criterion.pop()
            criterion = "\n".join(current_criterion)
            if criterion.strip():
                criteria_lines.append(criterion)
            current_criterion = None

        for line in lines:
            if fence_character is not None:
                if in_criteria and current_criterion is not None:
                    current_criterion.append(line)

                closing_fence = re.match(
                    rf"^[ \t]*{re.escape(fence_character)}"
                    rf"{{{fence_length},}}[ \t]*$",
                    line,
                )
                if closing_fence:
                    fence_character = None
                    fence_length = 0
                continue

            opening_fence = fence_pattern.match(line)
            if opening_fence:
                fence = opening_fence.group("fence")
                fence_character = fence[0]
                fence_length = len(fence)
                if in_criteria and current_criterion is not None:
                    current_criterion.append(line)
                continue

            if not in_criteria:
                if line.strip().lower() in [
                    "## acceptance criteria",
                    "## acceptance criterion",
                ]:
                    in_criteria = True
                continue

            if peer_heading_pattern.match(line):
                finish_criterion()
                break

            item = criterion_pattern.match(line)
            if item:
                finish_criterion()
                text = item.group("text")
                if text.strip():
                    current_criterion = [text]
                continue

            if current_criterion is not None:
                current_criterion.append(line)

        finish_criterion()

        return criteria_lines if criteria_lines else ["No acceptance criteria specified"]


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "TaskLoader",
    "TaskNotFoundError",
    "TaskParseError",
]
