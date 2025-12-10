"""
Agent Markdown Transformers

Applies formatting transformations to improve agent quality metrics.
"""

from typing import Optional
import re
import sys
from pathlib import Path

from .parser import AgentStructure, Section, CodeBlock
from .metrics import QualityMetrics

# TASK-UX-6581: Import shared boundary utilities from agent_enhancement library
# Add agent_enhancement to path for cross-library import
_lib_dir = Path(__file__).resolve().parent.parent
_agent_enhancement_dir = _lib_dir / "agent_enhancement"
if str(_agent_enhancement_dir) not in sys.path:
    sys.path.insert(0, str(_agent_enhancement_dir))

from boundary_utils import (
    find_boundaries_insertion_point,
    validate_boundaries_format,
    generate_generic_boundaries
)


class AgentFormatter:
    """Applies formatting transformations to agent markdown."""

    # TASK-UX-6581: BOUNDARY_TEMPLATE removed - now uses generate_generic_boundaries()
    # from shared boundary_utils library for GitHub-compliant generic boundaries

    QUICK_START_TEMPLATE = """
## Quick Start

### Basic Usage
```bash
[NEEDS_CONTENT: Add command example with flags/options]
```

### Expected Output
```yaml
[NEEDS_CONTENT: Add example output showing validation report]
```
"""

    def format(self, agent: AgentStructure, metrics: QualityMetrics) -> str:
        """
        Apply all formatting rules to improve quality metrics.

        Args:
            agent: Parsed agent structure
            metrics: Current quality metrics

        Returns:
            Formatted markdown content
        """
        lines = agent.raw_content.split('\n')

        # Apply transformations in order
        if metrics.commands_first >= 50 or metrics.commands_first == -1:
            lines = self._add_quick_start(lines, agent)

        if not all(metrics.boundary_sections.values()):
            lines = self._add_boundary_sections(lines, agent, metrics.boundary_sections)

        if metrics.time_to_first_example >= 50 or metrics.time_to_first_example == -1:
            lines = self._move_first_example(lines, agent)

        if metrics.example_density < 40:
            lines = self._add_example_markers(lines, agent, metrics.example_density)

        if metrics.code_to_text_ratio < 1.0:
            lines = self._add_ratio_markers(lines, agent, metrics.code_to_text_ratio)

        return '\n'.join(lines)

    def _add_quick_start(
        self, lines: list[str], agent: AgentStructure
    ) -> list[str]:
        """
        Add Quick Start section with command example.

        Inserts after frontmatter and role description (first paragraph).
        """
        # Find insertion point (after role description)
        insert_line = agent.frontmatter_end_line

        # Skip to end of first paragraph or first section
        in_paragraph = False
        for i in range(agent.frontmatter_end_line, len(lines)):
            line = lines[i].strip()

            if line.startswith('#'):
                # Found first section, insert before it
                insert_line = i
                break

            if line:
                in_paragraph = True
            elif in_paragraph:
                # End of first paragraph
                insert_line = i + 1
                break

        # Insert Quick Start section
        quick_start_lines = self.QUICK_START_TEMPLATE.strip().split('\n')
        lines = lines[:insert_line] + [''] + quick_start_lines + [''] + lines[insert_line:]

        return lines

    def _add_boundary_sections(
        self,
        lines: list[str],
        agent: AgentStructure,
        existing: dict[str, bool],
    ) -> list[str]:
        """
        Add missing ALWAYS/NEVER/ASK boundary sections using shared library.

        TASK-UX-6581: Now generates GitHub-compliant generic boundaries instead of placeholders.

        Uses shared boundary utilities for:
        - Placement: find_boundaries_insertion_point()
        - Content: generate_generic_boundaries()
        - Validation: validate_boundaries_format()

        Inserts after Quick Start section or at optimal location (lines 80-150).
        """
        # Skip if all boundary sections already exist
        if all(existing.values()):
            return lines

        # Step 1: Find insertion point using shared placement logic
        insert_line = find_boundaries_insertion_point(lines)

        if insert_line is None:
            insert_line = len(lines)  # Fallback to end

        # Step 2: Generate generic boundary content using shared generator
        agent_name = agent.frontmatter.get("name", "unknown")
        agent_description = agent.frontmatter.get("description", "")

        boundaries_content = generate_generic_boundaries(agent_name, agent_description)

        # Step 3: Validate generated content using shared validator
        is_valid, issues = validate_boundaries_format(boundaries_content)

        if not is_valid:
            # Fallback to placeholder if generation failed (should never happen)
            boundaries_content = """## Boundaries

### ALWAYS
- ✅ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ✅ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ✅ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ✅ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ✅ [PLACEHOLDER: Generic generation failed - manual intervention required]

### NEVER
- ❌ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ❌ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ❌ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ❌ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ❌ [PLACEHOLDER: Generic generation failed - manual intervention required]

### ASK
- ⚠️ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ⚠️ [PLACEHOLDER: Generic generation failed - manual intervention required]
- ⚠️ [PLACEHOLDER: Generic generation failed - manual intervention required]
"""

        # Step 4: Insert content
        boundary_lines = boundaries_content.strip().split('\n')
        lines = lines[:insert_line] + [''] + boundary_lines + [''] + lines[insert_line:]

        return lines

    def _move_first_example(
        self, lines: list[str], agent: AgentStructure
    ) -> list[str]:
        """
        Move first code example to appear within first 50 lines.

        Leaves a reference comment at the original location.
        """
        if not agent.code_blocks:
            return lines

        # Find first code block
        first_block = min(agent.code_blocks, key=lambda b: b.start_line)

        # Check if it's already in good position
        relative_line = first_block.start_line - agent.frontmatter_end_line
        if relative_line < 50:
            return lines  # Already good

        # Extract code block
        block_lines = lines[first_block.start_line : first_block.end_line + 1]

        # Remove from original location and add comment
        lines = (
            lines[: first_block.start_line]
            + [f'<!-- Example moved to Quick Start section (was line {first_block.start_line}) -->']
            + lines[first_block.end_line + 1 :]
        )

        # Find insertion point (in Quick Start or after role description)
        insert_line = agent.frontmatter_end_line + 10  # Default: early in file

        for i in range(agent.frontmatter_end_line, min(agent.frontmatter_end_line + 50, len(lines))):
            if '## Quick Start' in lines[i]:
                # Insert after "Basic Usage" or before "Expected Output"
                for j in range(i, min(i + 20, len(lines))):
                    if 'Expected Output' in lines[j] or lines[j].startswith('##'):
                        insert_line = j
                        break
                break

        # Insert code block
        lines = lines[:insert_line] + [''] + block_lines + [''] + lines[insert_line:]

        return lines

    def _add_example_markers(
        self, lines: list[str], agent: AgentStructure, current_density: float
    ) -> list[str]:
        """
        Add markers indicating where more examples are needed.
        """
        target_density = 40.0

        # Calculate how many more code lines needed
        total_lines = len([line for line in lines if line.strip()])
        current_code_lines = int(total_lines * current_density / 100)
        needed_code_lines = int(total_lines * target_density / 100) - current_code_lines

        if needed_code_lines <= 0:
            return lines

        # Find good insertion points (after sections with no examples)
        marker = f'[NEEDS_CONTENT: Add ~{needed_code_lines} lines of code examples to reach 40% density (currently {current_density:.1f}%)]'

        # Insert after first major section without examples
        for section in agent.sections:
            # Check if section has code blocks
            has_code = any(
                section.start_line <= block.start_line <= section.end_line
                for block in agent.code_blocks
            )

            if not has_code and section.level == 2:  # Level 2 heading
                # Insert marker at end of section
                lines.insert(section.end_line + 1, '')
                lines.insert(section.end_line + 2, marker)
                lines.insert(section.end_line + 3, '')
                break

        return lines

    def _add_ratio_markers(
        self, lines: list[str], agent: AgentStructure, current_ratio: float
    ) -> list[str]:
        """
        Add markers for improving code-to-text ratio.
        """
        target_ratio = 1.0

        if current_ratio >= target_ratio:
            return lines

        marker = f'[NEEDS_CONTENT: Add code examples - ratio is {current_ratio:.2f}:1, target is ≥1:1]'

        # Find sections with lots of prose but no code
        for section in agent.sections:
            # Count prose lines in section
            section_lines = lines[section.start_line : section.end_line + 1]
            prose_lines = len([line for line in section_lines if line.strip() and not line.strip().startswith('#')])

            # Check for code blocks
            has_code = any(
                section.start_line <= block.start_line <= section.end_line
                for block in agent.code_blocks
            )

            if prose_lines > 10 and not has_code:
                # Insert marker
                lines.insert(section.end_line + 1, '')
                lines.insert(section.end_line + 2, marker)
                lines.insert(section.end_line + 3, '')
                break

        return lines
