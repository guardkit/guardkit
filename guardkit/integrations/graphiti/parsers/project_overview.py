"""Project overview parser for CLAUDE.md and README.md files.

This parser extracts project information from CLAUDE.md and README.md
files, creating episodes for the project overview and optionally a
separate architecture episode for rich architecture content.
"""

import os
import re
from typing import Any, Optional

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)


class ProjectOverviewParser(BaseParser):
    """Parser for project overview files (CLAUDE.md, README.md).

    This parser extracts structured information from project documentation
    files including:
    - Project purpose/description
    - Technology stack
    - Architecture details

    When architecture content exceeds 500 characters, a separate
    architecture episode is created with group_id 'project_architecture'.
    """

    # Threshold for creating separate architecture episode
    ARCHITECTURE_THRESHOLD = 500

    # Recognized filenames (case-insensitive)
    RECOGNIZED_FILENAMES = {"claude.md", "readme.md"}

    @property
    def parser_type(self) -> str:
        """Return the parser type identifier."""
        return "project_overview"

    @property
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".md"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this parser can handle the given file.

        Returns True only for CLAUDE.md or README.md files (case-insensitive).

        Args:
            content: The file content (not used for this check).
            file_path: Path to the file being checked.

        Returns:
            True if file is CLAUDE.md or README.md, False otherwise.
        """
        if not file_path:
            return False

        # Extract just the filename from the path
        filename = os.path.basename(file_path)
        if not filename:
            return False

        # Check if it's a recognized filename (case-insensitive)
        return filename.lower() in self.RECOGNIZED_FILENAMES

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse project overview file and extract episodes.

        Args:
            content: The file content to parse.
            file_path: Path to the file being parsed.

        Returns:
            ParseResult with episodes, warnings, and success status.
        """
        episodes: list[EpisodeData] = []
        warnings: list[str] = []

        # Handle None content
        if content is None:
            content = ""

        # Handle empty/whitespace content
        if not content or not content.strip():
            warnings.append("Empty content")
            return ParseResult(episodes=episodes, warnings=warnings, success=True)

        # Extract sections
        title = self._extract_title(content)
        purpose = self._extract_purpose(content)
        tech_stack = self._extract_tech_stack(content)
        architecture = self._extract_architecture(content)

        # Determine if document has meaningful structure
        has_sections = bool(re.search(r"^##\s+", content, re.MULTILINE))

        # Generate warnings for missing sections based on document structure
        # If the document has no section headers at all, warn about everything
        # If it has some sections, only warn about what's truly missing
        if has_sections:
            # Document has some structure - only warn about explicitly expected sections
            # Purpose: warn only if there's no content after title before first ##
            if not purpose:
                warnings.append("Missing 'purpose' section")

            # Tech stack: warn only if document seems like it should have tech info
            # but only when architecture is present and short (not rich docs)
            if not tech_stack and architecture and len(architecture) <= self.ARCHITECTURE_THRESHOLD:
                warnings.append("Missing 'tech_stack' section")

            # Architecture: warn if no architecture section found
            if not architecture:
                warnings.append("Missing 'architecture' section")
        else:
            # No section headers - this is just content after title
            # Warn about all missing structured sections
            warnings.append("Missing 'purpose' section")
            warnings.append("Missing 'tech_stack' section")
            warnings.append("Missing 'architecture' section")

        # Extract entity_id from title or use fallback
        entity_id = self._normalize_entity_id(title) if title else self._fallback_entity_id(file_path)

        # Use full content for the episode (not just extracted sections)
        # This preserves all document content including sections like "Core Principles"
        full_content = self._get_content_body(content)

        # Create main project overview episode
        metadata: dict[str, Any] = {
            "file_path": file_path,
            "parser_type": self.parser_type,
            "purpose": purpose or "",
            "tech_stack": tech_stack or "",
            "architecture": architecture or "",
        }

        overview_episode = EpisodeData(
            content=full_content,
            group_id="project_overview",
            entity_type="project",
            entity_id=entity_id,
            metadata=metadata,
        )
        episodes.append(overview_episode)

        # Create separate architecture episode if content is rich (>500 chars)
        if architecture and len(architecture) > self.ARCHITECTURE_THRESHOLD:
            arch_metadata: dict[str, Any] = {
                "file_path": file_path,
                "parser_type": self.parser_type,
                "source_entity_id": entity_id,
            }
            arch_episode = EpisodeData(
                content=architecture,
                group_id="project_architecture",
                entity_type="architecture",
                entity_id=f"{entity_id}-architecture",
                metadata=arch_metadata,
            )
            episodes.append(arch_episode)

        return ParseResult(episodes=episodes, warnings=warnings, success=True)

    def _get_content_body(self, content: str) -> str:
        """Extract the body content (everything after the title).

        Args:
            content: The full markdown content.

        Returns:
            Content body without the title line.
        """
        lines = content.split("\n")
        body_lines = []
        past_title = False

        for line in lines:
            if not past_title:
                if line.startswith("# "):
                    past_title = True
                continue
            body_lines.append(line)

        return "\n".join(body_lines).strip()

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract the title from the first H1 heading.

        Args:
            content: The markdown content.

        Returns:
            The title text or None if not found.
        """
        # Match first H1 heading (# Title)
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_purpose(self, content: str) -> Optional[str]:
        """Extract purpose from the first paragraph after the title.

        The purpose is the content between the title and the first
        section heading (## ...).

        Args:
            content: The markdown content.

        Returns:
            The purpose text or None if not found.
        """
        # Find content between title and first section
        # Remove title line first
        lines = content.split("\n")
        content_after_title = []
        past_title = False

        for line in lines:
            if not past_title:
                if line.startswith("# "):
                    past_title = True
                continue

            # Stop at first section heading
            if line.startswith("## "):
                break

            content_after_title.append(line)

        purpose_text = "\n".join(content_after_title).strip()
        return purpose_text if purpose_text else None

    def _extract_tech_stack(self, content: str) -> Optional[str]:
        """Extract technology stack section.

        Looks for sections named "Tech Stack", "Technology Stack",
        or "Technology".

        Args:
            content: The markdown content.

        Returns:
            The tech stack content or None if not found.
        """
        return self._extract_section(
            content,
            [
                r"##\s+Tech(?:nology)?\s+Stack",
                r"##\s+Technology(?:\s|$)",
            ],
        )

    def _extract_architecture(self, content: str) -> Optional[str]:
        """Extract architecture section.

        Args:
            content: The markdown content.

        Returns:
            The architecture content or None if not found.
        """
        return self._extract_section(
            content,
            [r"##\s+Architecture"],
        )

    def _extract_section(
        self, content: str, header_patterns: list[str]
    ) -> Optional[str]:
        """Extract a section by its header pattern.

        Args:
            content: The markdown content.
            header_patterns: List of regex patterns to match section headers.

        Returns:
            The section content or None if not found.
        """
        for pattern in header_patterns:
            # Find the section header
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                # Find content from header to next section or end
                start_pos = match.end()
                remaining = content[start_pos:]

                # Find next section header (## ...)
                next_section = re.search(r"^##\s+", remaining, re.MULTILINE)
                if next_section:
                    section_content = remaining[: next_section.start()]
                else:
                    section_content = remaining

                section_text = section_content.strip()
                if section_text:
                    return section_text

        return None

    def _normalize_entity_id(self, title: str) -> str:
        """Normalize title to entity_id format.

        Converts title to lowercase, extracts first word/term,
        and replaces spaces with hyphens.

        Args:
            title: The raw title string.

        Returns:
            Normalized entity_id string.
        """
        # Take just the first part before any separator like " - "
        if " - " in title:
            title = title.split(" - ")[0]

        # Convert to lowercase
        entity_id = title.lower()

        # Replace spaces with hyphens
        entity_id = entity_id.replace(" ", "-")

        # Remove any characters that aren't alphanumeric or hyphens
        entity_id = re.sub(r"[^a-z0-9-]", "", entity_id)

        # Remove leading/trailing hyphens and collapse multiple hyphens
        entity_id = re.sub(r"-+", "-", entity_id).strip("-")

        return entity_id

    def _fallback_entity_id(self, file_path: str) -> str:
        """Generate fallback entity_id from filename.

        Args:
            file_path: The file path.

        Returns:
            Entity ID derived from filename.
        """
        filename = os.path.basename(file_path) if file_path else "unknown"
        # Remove extension
        name = os.path.splitext(filename)[0]
        return name.lower()
