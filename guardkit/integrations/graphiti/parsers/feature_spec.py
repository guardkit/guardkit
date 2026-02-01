"""Parser for feature specification files.

This module provides the FeatureSpecParser class that parses feature
specification markdown files and generates episodes for Graphiti.
"""

import re
from typing import Any

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)


class FeatureSpecParser(BaseParser):
    """Parser for feature specification files.

    Parses feature specification markdown files that define features
    with phases and tasks. Generates episodes for the feature overview
    and individual tasks.

    Example feature spec format:
        ---
        feature_name: Dark Mode Support
        ---

        # Feature Specification: Graphiti Refinement MVP

        > **Status**: Ready

        ## Feature Overview

        Description here...

        ### Phase 1: Foundation (27h)

        | Task | Description | Estimate |
        |------|-------------|----------|
        | PRE-001-A | Add project_id | 2h |
    """

    @property
    def parser_type(self) -> str:
        """Return the unique parser type identifier.

        Returns:
            The string "feature-spec".
        """
        return "feature-spec"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List containing ".md".
        """
        return [".md"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the given content.

        A file can be parsed if:
        - The filename starts with "feature-spec" (case-insensitive)
        - The file has a .md extension

        Args:
            content: The file content to check.
            file_path: Path to the file being checked.

        Returns:
            True if this parser can handle the content, False otherwise.
        """
        # Get the filename from the path
        filename = file_path.split("/")[-1] if "/" in file_path else file_path

        # Check extension
        if not filename.lower().endswith(".md"):
            return False

        # Check if filename starts with "feature-spec" (case-insensitive)
        return filename.lower().startswith("feature-spec")

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse feature spec content and return episodes.

        Args:
            content: The file content to parse.
            file_path: Path to the file being parsed (for context).

        Returns:
            ParseResult containing extracted episodes, warnings, and success status.
        """
        episodes: list[EpisodeData] = []
        warnings: list[str] = []

        # Parse frontmatter
        frontmatter, content_without_frontmatter = self._parse_frontmatter(content)

        # Extract feature name from title
        feature_name = self._extract_title(content_without_frontmatter)

        # If no feature name from title, check frontmatter
        if not feature_name:
            feature_name = frontmatter.get("feature_name", "")

        # If still no feature name, this is not a valid feature spec
        if not feature_name:
            # Check if content has feature spec structure
            if "# Feature Specification:" not in content:
                return ParseResult(
                    episodes=[],
                    warnings=["Content is not a valid feature specification"],
                    success=False,
                )
            warnings.append("Could not extract feature name from content")
            return ParseResult(episodes=[], warnings=warnings, success=False)

        # Create slugified identifiers
        feature_slug = self._slugify(feature_name)
        group_id = feature_slug
        entity_type = "feature-spec"

        # Extract feature overview
        overview = self._extract_overview(content_without_frontmatter)

        if not overview:
            warnings.append("Missing feature overview section")

        # Create overview episode
        overview_content = f"# Feature Specification: {feature_name}\n\n"
        if overview:
            overview_content += f"## Feature Overview\n\n{overview}"
        else:
            # Use whatever content we have
            overview_content += content_without_frontmatter

        # Build metadata
        overview_metadata: dict[str, Any] = {
            "source_path": file_path,
        }

        # Add frontmatter fields to metadata
        if frontmatter.get("feature_name"):
            overview_metadata["feature_name"] = frontmatter["feature_name"]

        overview_episode = EpisodeData(
            content=overview_content,
            group_id=group_id,
            entity_type=entity_type,
            entity_id=f"{feature_slug}-overview",
            metadata=overview_metadata,
        )
        episodes.append(overview_episode)

        # Extract phases and tasks
        phases, phase_warnings = self._extract_phases(content_without_frontmatter)
        warnings.extend(phase_warnings)

        if not phases:
            warnings.append("No phases found in feature spec")

        # Create task episodes
        for phase in phases:
            phase_name = phase.get("name", "Unknown Phase")
            tasks = phase.get("tasks", [])

            for task in tasks:
                task_id = task.get("task_id", "")
                task_desc = task.get("description", "")
                task_estimate = task.get("estimate", "")

                if not task_id or not task_desc:
                    continue

                task_content = (
                    f"Task: {task_id}\n"
                    f"Description: {task_desc}\n"
                    f"Estimate: {task_estimate}\n"
                    f"Phase: {phase_name}"
                )

                task_metadata: dict[str, Any] = {
                    "source_path": file_path,
                    "phase": phase_name,
                    "task_id": task_id,
                    "estimate": task_estimate,
                }

                task_episode = EpisodeData(
                    content=task_content,
                    group_id=group_id,
                    entity_type=entity_type,
                    entity_id=f"{feature_slug}-{self._slugify(task_id)}",
                    metadata=task_metadata,
                )
                episodes.append(task_episode)

        return ParseResult(
            episodes=episodes,
            warnings=warnings,
            success=True,
        )

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-friendly slug.

        Args:
            text: The text to slugify.

        Returns:
            A lowercase, hyphen-separated slug.
        """
        # Convert to lowercase
        slug = text.lower()
        # Replace spaces and underscores with hyphens
        slug = re.sub(r"[\s_]+", "-", slug)
        # Remove any characters that aren't alphanumeric or hyphens
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r"-+", "-", slug)
        # Strip leading/trailing hyphens
        slug = slug.strip("-")
        return slug

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from content.

        Args:
            content: The content potentially containing frontmatter.

        Returns:
            Tuple of (frontmatter dict, content without frontmatter).
        """
        frontmatter: dict[str, Any] = {}

        # Check for YAML frontmatter (starts with ---)
        if not content.strip().startswith("---"):
            return frontmatter, content

        # Find the closing ---
        lines = content.split("\n")
        end_index = -1

        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_index = i
                break

        if end_index == -1:
            return frontmatter, content

        # Parse the frontmatter
        frontmatter_lines = lines[1:end_index]
        for line in frontmatter_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                frontmatter[key] = value

        # Return content without frontmatter
        content_without_frontmatter = "\n".join(lines[end_index + 1 :]).lstrip()
        return frontmatter, content_without_frontmatter

    def _extract_title(self, content: str) -> str:
        """Extract feature name from the title line.

        Looks for "# Feature Specification: {name}" pattern.

        Args:
            content: The content to search.

        Returns:
            The feature name, or empty string if not found.
        """
        # Look for "# Feature Specification: ..." pattern
        match = re.search(r"#\s*Feature\s+Specification:\s*(.+)", content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_overview(self, content: str) -> str:
        """Extract the feature overview section.

        Args:
            content: The content to search.

        Returns:
            The overview text, or empty string if not found.
        """
        # Look for ## Feature Overview section
        match = re.search(
            r"##\s*Feature\s+Overview\s*\n+(.*?)(?=\n##|\n###|\Z)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return ""

    def _extract_phases(
        self, content: str
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Extract phase information with tasks from content.

        Args:
            content: The content to search.

        Returns:
            Tuple of (list of phase dictionaries with name and tasks, list of warnings).
        """
        phases: list[dict[str, Any]] = []
        warnings: list[str] = []

        # Find all phase headers (### Phase N: Name (Xh))
        phase_pattern = r"###\s*(Phase\s+\d+[^(\n]*)\s*\([^)]*\)"
        phase_matches = list(re.finditer(phase_pattern, content, re.IGNORECASE))

        for i, match in enumerate(phase_matches):
            phase_name = match.group(1).strip()
            phase_start = match.end()

            # Find the end of this phase (next phase header or end of content)
            if i + 1 < len(phase_matches):
                phase_end = phase_matches[i + 1].start()
            else:
                phase_end = len(content)

            phase_content = content[phase_start:phase_end]

            # Extract tasks from tables in this phase
            tasks, table_warnings = self._extract_tasks_from_table(
                phase_content, phase_name
            )
            warnings.extend(table_warnings)

            phases.append(
                {
                    "name": phase_name,
                    "tasks": tasks,
                }
            )

        return phases, warnings

    def _extract_tasks_from_table(
        self, content: str, phase_name: str
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Extract tasks from a markdown table.

        Expects tables with Task|Description|Estimate columns.

        Args:
            content: The content containing the table.
            phase_name: The name of the phase (for error reporting).

        Returns:
            Tuple of (list of task dictionaries, list of warnings).
        """
        tasks: list[dict[str, Any]] = []
        warnings: list[str] = []

        # Find the table
        lines = content.split("\n")
        in_table = False
        header_found = False
        header_column_count = 0

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                in_table = False
                header_found = False
                header_column_count = 0
                continue

            # Check if this is a table row
            if line.startswith("|") and line.endswith("|"):
                # Check if it's the separator line
                if re.match(r"\|[-\s|]+\|", line):
                    # Check if separator has expected columns
                    separator_cells = line.split("|")
                    separator_count = len([c for c in separator_cells if c.strip()])
                    if header_column_count > 0 and separator_count != header_column_count:
                        warnings.append(
                            f"Malformed table in {phase_name}: "
                            f"separator has {separator_count} columns but header has {header_column_count}"
                        )
                    header_found = True
                    continue

                # Parse the row
                cells = [cell.strip() for cell in line.split("|")]
                # Remove empty first and last cells from split
                cells = [c for c in cells if c]

                if not header_found:
                    # This is the header row
                    in_table = True
                    header_column_count = len(cells)
                    continue

                if in_table:
                    # Check for column count mismatch
                    if len(cells) != header_column_count and header_column_count > 0:
                        warnings.append(
                            f"Malformed table row in {phase_name}: "
                            f"row has {len(cells)} cells but expected {header_column_count}"
                        )

                    if len(cells) >= 2:
                        # This is a data row
                        task_id = cells[0] if len(cells) > 0 else ""
                        description = cells[1] if len(cells) > 1 else ""
                        estimate = cells[2] if len(cells) > 2 else ""

                        if task_id and description:
                            tasks.append(
                                {
                                    "task_id": task_id,
                                    "description": description,
                                    "estimate": estimate,
                                }
                            )

        return tasks, warnings
