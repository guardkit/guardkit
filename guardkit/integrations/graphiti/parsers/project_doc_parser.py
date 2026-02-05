"""Parser for CLAUDE.md and README.md project documentation files.

This parser extracts key information from project documentation including:
- Project overview/purpose
- Technology stack
- Architecture patterns

It creates episodes for each major section found in the document.
"""

import re
from pathlib import Path
from typing import Any

import frontmatter

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)

# Header patterns for different sections
PURPOSE_HEADERS = [
    "overview",
    "purpose",
    "about",
    "description",
    "what is this",
    "project overview",
]

TECH_HEADERS = [
    "tech stack",
    "technologies",
    "stack",
    "built with",
    "technology stack",
    "dependencies",
]

ARCH_HEADERS = [
    "architecture",
    "patterns",
    "structure",
    "design",
    "system design",
    "project structure",
]


class ProjectDocParser(BaseParser):
    """Parser for CLAUDE.md and README.md files.

    Extracts project overview, technology stack, and architecture
    patterns from project documentation files.

    Only parses CLAUDE.md and README.md files (case-insensitive).
    Supports both .md and .markdown extensions.
    """

    @property
    def parser_type(self) -> str:
        """Return the unique parser type identifier.

        Returns:
            "project_doc"
        """
        return "project_doc"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            [".md", ".markdown"]
        """
        return [".md", ".markdown"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the given content.

        Only handles CLAUDE.md and README.md files (case-insensitive).

        Args:
            content: The file content to check.
            file_path: Path to the file being checked.

        Returns:
            True if file is CLAUDE.md or README.md, False otherwise.
        """
        # Extract filename from path
        path_obj = Path(file_path)
        filename = path_obj.name.lower()
        extension = path_obj.suffix.lower()

        # Check if extension is supported
        if extension not in [".md", ".markdown"]:
            return False

        # Check if filename (without extension) matches
        name_without_ext = filename.replace(extension, "")
        return name_without_ext in ["claude", "readme"]

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse content and return episodes.

        Extracts project documentation sections and creates episodes
        for each major section found.

        Args:
            content: The file content to parse.
            file_path: Path to the file being parsed (for context).

        Returns:
            ParseResult containing extracted episodes, warnings, and success status.
        """
        episodes: list[EpisodeData] = []
        warnings: list[str] = []

        # Handle empty content
        if not content or not content.strip():
            warnings.append("Empty content provided")
            return ParseResult(episodes=[], warnings=warnings, success=False)

        # Parse YAML frontmatter if present
        try:
            post = frontmatter.loads(content)
            markdown_content = post.content
            fm_metadata = post.metadata if post.metadata else {}
        except Exception as e:
            warnings.append(f"Error parsing YAML frontmatter: {e}")
            markdown_content = content
            fm_metadata = {}

        # Extract sections
        sections = self._extract_sections(markdown_content)

        # Find purpose section
        purpose_content = self._find_section_by_headers(sections, PURPOSE_HEADERS)
        if purpose_content:
            episodes.append(
                self._create_episode(
                    content=purpose_content,
                    section_type="purpose",
                    file_path=file_path,
                    frontmatter=fm_metadata,
                )
            )
        else:
            warnings.append("No purpose/overview section found in document")

        # Find tech stack section
        tech_content = self._find_section_by_headers(sections, TECH_HEADERS)
        if tech_content:
            episodes.append(
                self._create_episode(
                    content=tech_content,
                    section_type="tech_stack",
                    file_path=file_path,
                    frontmatter=fm_metadata,
                )
            )
        else:
            warnings.append("No tech stack section found in document")

        # Find architecture section
        arch_content = self._find_section_by_headers(sections, ARCH_HEADERS)
        if arch_content:
            episodes.append(
                self._create_episode(
                    content=arch_content,
                    section_type="architecture",
                    file_path=file_path,
                    frontmatter=fm_metadata,
                )
            )
        else:
            warnings.append("No architecture/patterns section found in document")

        # Success is true if we could parse the content (even if sections are missing)
        # Only fail for truly invalid content (empty, parsing errors)
        success = True

        return ParseResult(episodes=episodes, warnings=warnings, success=success)

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Extract markdown sections by headers.

        Args:
            content: Markdown content to parse.

        Returns:
            Dictionary mapping header text (lowercase) to section content.
        """
        sections: dict[str, str] = {}

        # Split by headers (## or #)
        # Pattern matches lines starting with # or ##
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        # Find all headers and their positions
        matches = list(header_pattern.finditer(content))

        if not matches:
            return sections

        # Extract content between headers
        for i, match in enumerate(matches):
            header_text = match.group(2).strip().lower()
            start_pos = match.end()

            # Find next header or end of content
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)

            section_content = content[start_pos:end_pos].strip()
            sections[header_text] = section_content

        return sections

    def _find_section_by_headers(
        self, sections: dict[str, str], header_patterns: list[str]
    ) -> str | None:
        """Find section content matching any of the header patterns.

        Args:
            sections: Dictionary of section headers to content.
            header_patterns: List of header patterns to match (case-insensitive).

        Returns:
            Section content if found, None otherwise.
        """
        # Try each header pattern
        for pattern in header_patterns:
            pattern_lower = pattern.lower()

            # Check for exact match first
            if pattern_lower in sections:
                return sections[pattern_lower]

            # Check for partial match (header contains pattern)
            for header, content in sections.items():
                if pattern_lower in header:
                    return content

        return None

    def _create_episode(
        self,
        content: str,
        section_type: str,
        file_path: str,
        frontmatter: dict[str, Any] | None,
    ) -> EpisodeData:
        """Create an EpisodeData instance for a section.

        Args:
            content: The section content.
            section_type: Type of section (purpose, tech_stack, architecture).
            file_path: Path to the source file.
            frontmatter: YAML frontmatter metadata (None if no frontmatter).

        Returns:
            EpisodeData instance.
        """
        metadata: dict[str, Any] = {"section_type": section_type}

        # Include frontmatter if present and not empty
        if frontmatter is not None and frontmatter:
            metadata["frontmatter"] = frontmatter

        return EpisodeData(
            content=content,
            group_id=f"project_{section_type}",
            entity_type="project_doc",
            entity_id=file_path,
            metadata=metadata,
        )
