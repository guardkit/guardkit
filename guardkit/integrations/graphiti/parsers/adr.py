"""Parser for Architecture Decision Records (ADR).

This module provides parsing capability for ADR markdown files,
extracting decision information for Graphiti knowledge graph seeding.
"""

import re
from pathlib import Path

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)


class ADRParser(BaseParser):
    """Parser for Architecture Decision Records.

    Detects ADR files by filename (adr-*.md) or by the presence of
    standard ADR sections (Status, Context, Decision).

    Extracts title, status, context, decision, and optionally consequences
    to create episodes for the Graphiti knowledge graph.
    """

    @property
    def parser_type(self) -> str:
        """Return the unique parser type identifier."""
        return "adr"

    @property
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return [".md"]

    def can_parse(self, content: str, file_path: str) -> bool:
        """Check if this is an ADR file.

        Detection criteria:
        1. Filename starts with 'adr-' (case-insensitive), OR
        2. Content contains all three required sections: Status, Context, Decision

        Args:
            content: The file content to check.
            file_path: Path to the file being checked.

        Returns:
            True if this parser can handle the content, False otherwise.
        """
        filename = Path(file_path).name.lower()

        # Check filename pattern
        if filename.startswith("adr-"):
            return True

        # Check for required ADR sections (case-insensitive)
        content_lower = content.lower()
        has_status = "## status" in content_lower
        has_context = "## context" in content_lower
        has_decision = "## decision" in content_lower

        return has_status and has_context and has_decision

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse ADR content and return episodes.

        Extracts title, status, context, decision, and consequences
        sections from the ADR and creates an episode for Graphiti.

        Args:
            content: The file content to parse.
            file_path: Path to the file being parsed (for context).

        Returns:
            ParseResult containing extracted episodes, warnings, and success status.
        """
        warnings: list[str] = []

        # Extract sections
        title = self._extract_title(content)
        status = self._extract_section(content, "Status")
        context = self._extract_section(content, "Context")
        decision = self._extract_section(content, "Decision")
        consequences = self._extract_section(content, "Consequences")

        # Warn if missing required sections (but still attempt to parse)
        if not status:
            warnings.append("Missing required section: Status")
        if not context:
            warnings.append("Missing required section: Context")
        if not decision:
            warnings.append("Missing required section: Decision")

        # Build formatted content for the episode
        content_parts = []
        if title:
            content_parts.append(f"# {title}")
        if status:
            content_parts.append(f"\n## Status\n{status}")
        if context:
            content_parts.append(f"\n## Context\n{context}")
        if decision:
            content_parts.append(f"\n## Decision\n{decision}")
        if consequences:
            content_parts.append(f"\n## Consequences\n{consequences}")

        formatted_content = "\n".join(content_parts)

        # Extract ADR number if present in title
        adr_number = self._extract_adr_number(title) if title else None

        # Build metadata
        metadata: dict[str, str] = {
            "source_path": file_path,
            "status": status.strip() if status else "",
        }
        if adr_number:
            metadata["adr_number"] = adr_number

        # Generate unique entity_id from title
        entity_id = self._generate_entity_id(title) if title else f"adr_{Path(file_path).stem}"

        episode = EpisodeData(
            content=formatted_content,
            group_id="project_decisions",
            entity_type="adr",
            entity_id=entity_id,
            metadata=metadata,
        )

        return ParseResult(
            episodes=[episode],
            warnings=warnings,
            success=True,
        )

    def _extract_title(self, content: str) -> str:
        """Extract the title from H1 heading.

        Args:
            content: The markdown content.

        Returns:
            The title text, or empty string if not found.
        """
        # Match H1 heading (# Title)
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract content from a markdown section.

        Extracts all content between a ## heading and the next ## heading
        or end of file.

        Args:
            content: The markdown content.
            section_name: The section name to extract (e.g., "Status", "Context").

        Returns:
            The section content, or empty string if not found.
        """
        # Pattern to match section heading and capture content until next section or EOF
        # Case-insensitive match on section name
        pattern = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _slugify(self, text: str) -> str:
        """Convert text to a slug suitable for entity IDs.

        Args:
            text: The text to slugify.

        Returns:
            A lowercase, hyphen-separated slug.
        """
        # Remove ADR number prefix if present (e.g., "ADR-001: " or "ADR-001 ")
        text = re.sub(r"^ADR-\d+[:\s]+", "", text, flags=re.IGNORECASE)
        # Convert to lowercase
        text = text.lower()
        # Replace non-alphanumeric characters with hyphens
        text = re.sub(r"[^a-z0-9]+", "-", text)
        # Remove leading/trailing hyphens
        text = text.strip("-")
        return text

    def _generate_entity_id(self, title: str) -> str:
        """Generate a unique entity ID from the title.

        Args:
            title: The ADR title.

        Returns:
            A unique entity ID prefixed with 'adr_'.
        """
        slug = self._slugify(title)
        return f"adr_{slug}" if slug else "adr_unknown"

    def _extract_adr_number(self, title: str) -> str | None:
        """Extract ADR number from title if present.

        Args:
            title: The ADR title (e.g., "ADR-042: Some Decision").

        Returns:
            The ADR number as string (e.g., "042"), or None if not found.
        """
        match = re.search(r"ADR-(\d+)", title, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
