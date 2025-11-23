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
        3. Insert boundaries after "Quick Start", before next section (targets lines 80-150)
        4. Fallback to line 50-80 if no Quick Start found
        5. Append other sections at the end

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
        Find insertion point for boundaries section.

        Target: After "## Quick Start", before "## Code Examples"/"## Capabilities"
        GitHub recommendation: Lines 80-150 for optimal authority clarity.

        Strategy:
        1. Find "## Quick Start" section
        2. Find next ## section after Quick Start
        3. Insert boundaries before that next section
        4. Fallback: Insert at line 50-80 if no Quick Start found

        Args:
            lines: List of content lines

        Returns:
            Line index for insertion or None if no suitable point found
        """
        # Step 1: Find Quick Start
        quick_start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("## Quick Start"):
                quick_start_idx = i
                break

        if quick_start_idx is None:
            # Fallback: No Quick Start, insert after description
            return self._find_post_description_position(lines)

        # Step 2: Find next ## section after Quick Start
        for i in range(quick_start_idx + 1, len(lines)):
            if lines[i].strip().startswith("## "):
                return i  # Insert before this section

        # Step 3: No next section, insert at reasonable position
        # Target: ~30 lines after Quick Start (hits 80-150 range)
        target_line = quick_start_idx + 30
        return min(target_line, len(lines))

    def _find_post_description_position(self, lines: list[str]) -> int | None:
        """
        Fallback: Find position after description/purpose section.

        Used when "## Quick Start" doesn't exist.
        Targets line 50-80 range by inserting after initial sections
        (Purpose, Technologies, Usage) but before content sections
        (Code Examples, Best Practices, etc.).

        Args:
            lines: List of content lines

        Returns:
            Line index for insertion or None if no structure found
        """
        # Find end of frontmatter
        frontmatter_end = 0
        frontmatter_count = 0

        for i, line in enumerate(lines):
            if line.strip() == '---':
                frontmatter_count += 1
                if frontmatter_count == 2:
                    frontmatter_end = i + 1
                    break

        # Find sections after frontmatter to determine best insertion point
        # We want to insert EARLY, after initial metadata sections but before content
        early_sections = ["Purpose", "Why This Agent Exists", "Technologies", "Usage", "When to Use"]
        content_sections = ["Code Examples", "Examples", "Related Templates", "Best Practices", "Capabilities"]

        sections_found = []
        for i in range(frontmatter_end, min(frontmatter_end + 100, len(lines))):
            if lines[i].strip().startswith("## "):
                section_name = lines[i].strip()[3:].strip()
                sections_found.append((i, section_name))

        # Strategy: Insert before the first "content" section OR after the last "early" section
        last_early_section_idx = None
        first_content_section_idx = None

        for idx, name in sections_found:
            # Check if this is an early section (metadata)
            if any(early in name for early in early_sections):
                last_early_section_idx = idx
            # Check if this is a content section
            elif any(content in name for content in content_sections):
                if first_content_section_idx is None:
                    first_content_section_idx = idx
                break  # Stop at first content section

        # Decision logic:
        # 1. If we found a content section, insert before it
        if first_content_section_idx is not None:
            return first_content_section_idx

        # 2. If we found early sections but no content sections, insert after last early section
        if last_early_section_idx is not None:
            # Find next section after last early section
            for idx, name in sections_found:
                if idx > last_early_section_idx:
                    return idx
            # No section after, insert at reasonable default
            return min(50, len(lines))

        # 3. No recognizable structure, return None (will append at end)
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
