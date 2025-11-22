"""
Enhancement Applier

Applies enhancement content to agent files.

TASK-PHASE-8-INCREMENTAL: Shared module for agent enhancement
"""

from pathlib import Path
from typing import Dict, Any
import logging
import difflib

# TASK-FIX-7C3D: Import file I/O utilities
import importlib
_file_io_module = importlib.import_module('installer.global.lib.utils.file_io')
safe_read_file = _file_io_module.safe_read_file
safe_write_file = _file_io_module.safe_write_file

logger = logging.getLogger(__name__)


class EnhancementApplier:
    """Applies enhancement content to agent markdown files."""

    def apply(self, agent_file: Path, enhancement: Dict[str, Any]) -> None:
        """
        Modify agent file in-place with enhancement content.

        Inserts sections (related_templates, examples, best_practices) into
        the agent file while preserving frontmatter and existing content.

        Args:
            agent_file: Path to agent markdown file
            enhancement: Enhancement dict with sections and content

        Raises:
            PermissionError: If file is not writable
            ValueError: If enhancement data is invalid
        """
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")

        if not agent_file.is_file():
            raise ValueError(f"Path is not a file: {agent_file}")

        # Read current content with error handling (TASK-FIX-7C3D)
        success, original_content = safe_read_file(agent_file)
        if not success:
            # original_content contains error message
            raise PermissionError(f"Cannot read agent file: {original_content}")

        # Generate new content with enhancements
        new_content = self._merge_content(original_content, enhancement)

        # Write back to file with error handling (TASK-FIX-7C3D)
        success, error_msg = safe_write_file(agent_file, new_content)
        if not success:
            raise PermissionError(f"Cannot write to agent file: {error_msg}")

    def generate_diff(self, agent_file: Path, enhancement: Dict[str, Any]) -> str:
        """
        Create unified diff showing changes.

        Does NOT modify file.

        Args:
            agent_file: Path to agent markdown file
            enhancement: Enhancement dict with sections and content

        Returns:
            String in unified diff format (like `diff -u`)

        Example Output:
            ```
            --- agent-file.md
            +++ agent-file.md (enhanced)
            @@ -10,3 +10,15 @@
             Existing content...

            +## Related Templates
            +
            +- template1.template
            +- template2.template
            ```
        """
        if not agent_file.exists():
            return f"Error: File not found: {agent_file}"

        try:
            original_content = agent_file.read_text()
        except Exception as e:
            return f"Error reading file: {e}"

        # Generate new content
        new_content = self._merge_content(original_content, enhancement)

        # Generate unified diff
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=str(agent_file),
            tofile=f"{agent_file} (enhanced)",
            lineterm=''
        )

        return ''.join(diff)

    def _merge_content(self, original: str, enhancement: Dict[str, Any]) -> str:
        """
        Merge original content with enhancement sections.

        Strategy:
        1. Preserve frontmatter (YAML between ---...---)
        2. Preserve existing content
        3. Insert boundaries after "Quick Start", before "Capabilities"
        4. Append other sections at the end

        Args:
            original: Original file content
            enhancement: Enhancement dict with sections

        Returns:
            Merged content string
        """
        sections_to_add = enhancement.get("sections", [])

        # Split content into lines
        lines = original.split('\n')

        # Find end of frontmatter (if exists)
        frontmatter_end = 0
        in_frontmatter = False
        frontmatter_count = 0

        for i, line in enumerate(lines):
            if line.strip() == '---':
                frontmatter_count += 1
                if frontmatter_count == 1:
                    in_frontmatter = True
                elif frontmatter_count == 2:
                    in_frontmatter = False
                    frontmatter_end = i + 1
                    break

        # Build new content - preserve all original content
        new_lines = lines.copy()

        # Check if sections already exist (avoid duplicates)
        existing_content = '\n'.join(new_lines)

        # Separate boundaries from other sections for special placement
        boundaries_content = None
        other_sections = []

        for section_name in sections_to_add:
            if section_name == "boundaries":
                boundaries_content = enhancement.get("boundaries", "")
            else:
                other_sections.append(section_name)

        # Handle boundaries special placement (after Quick Start, before Capabilities)
        if boundaries_content and boundaries_content.strip():
            if "## Boundaries" not in existing_content:
                insertion_point = self._find_boundaries_insertion_point(new_lines)
                if insertion_point is not None:
                    # Insert at specific location
                    if new_lines[insertion_point - 1].strip():
                        new_lines.insert(insertion_point, "")
                    new_lines.insert(insertion_point, boundaries_content.strip())
                    new_lines.insert(insertion_point, "")
                else:
                    # Fallback: append at end
                    if new_lines and new_lines[-1].strip():
                        new_lines.append("")
                    new_lines.append(boundaries_content.strip())

        # Update existing_content for duplicate check
        existing_content = '\n'.join(new_lines)

        # Append other enhancement sections at the end
        for section_name in other_sections:
            section_content = enhancement.get(section_name, "")

            if section_content and section_content.strip():
                # Check if this section already exists
                section_header = f"## {section_name.replace('_', ' ').title()}"

                if section_header not in existing_content:
                    # Add blank line before section if content exists
                    if new_lines and new_lines[-1].strip():
                        new_lines.append("")

                    # Add section content
                    new_lines.append(section_content.strip())

        return '\n'.join(new_lines)

    def _find_boundaries_insertion_point(self, lines: list[str]) -> int | None:
        """
        Find the insertion point for boundaries section.

        Looks for "## Capabilities" section and returns index before it.
        If not found, looks for "## Quick Start" and returns index after it.

        Args:
            lines: List of content lines

        Returns:
            Line index for insertion or None if no suitable point found
        """
        # First try: Find "## Capabilities" and insert before it
        for i, line in enumerate(lines):
            if line.strip().startswith("## Capabilities"):
                return i

        # Second try: Find "## Quick Start" and insert after its content
        quick_start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("## Quick Start"):
                quick_start_idx = i
                break

        if quick_start_idx is not None:
            # Find next ## section after Quick Start
            for i in range(quick_start_idx + 1, len(lines)):
                if lines[i].strip().startswith("## "):
                    return i

            # If no next section, append at end
            return len(lines)

        # No suitable insertion point found
        return None

    def remove_sections(
        self,
        agent_file: Path,
        section_names: list[str]
    ) -> None:
        """
        Remove specific sections from agent file (utility method).

        Args:
            agent_file: Path to agent markdown file
            section_names: List of section names to remove (e.g., ["related_templates"])

        Raises:
            PermissionError: If file is not writable
        """
        if not agent_file.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_file}")

        content = agent_file.read_text()
        lines = content.split('\n')
        new_lines = []

        in_section_to_remove = False
        current_section = None

        for line in lines:
            # Check if this is a section header
            if line.startswith('## '):
                section_name = line[3:].strip().lower().replace(' ', '_')

                if section_name in section_names:
                    in_section_to_remove = True
                    current_section = section_name
                    continue
                else:
                    in_section_to_remove = False
                    current_section = None

            # Skip lines in sections to remove
            if not in_section_to_remove:
                new_lines.append(line)

        agent_file.write_text('\n'.join(new_lines))
