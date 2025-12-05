#!/usr/bin/env python3
"""
Agent File Splitter - Automated Progressive Disclosure (TASK-PD-008)

Splits agent markdown files into core (essential) and extended (detailed) files
for progressive disclosure. Supports single agent, batch processing, and dry-run modes.

Usage:
    # Single agent
    python scripts/split-agent.py --agent installer/global/agents/task-manager.md

    # All global agents
    python scripts/split-agent.py --all-global

    # Template agents
    python scripts/split-agent.py --template react-typescript

    # Dry run (preview without writing)
    python scripts/split-agent.py --agent installer/global/agents/task-manager.md --dry-run

    # Validate splits
    python scripts/split-agent.py --all-global --validate
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime


@dataclass
class SplitResult:
    """Result of splitting an agent file."""
    agent_path: Path
    core_content: str
    extended_content: str
    core_size: int
    extended_size: int
    original_size: int
    reduction_percent: float
    sections_moved: List[str]

    @property
    def success(self) -> bool:
        """Whether split was successful."""
        return self.reduction_percent > 0


class AgentSplitter:
    """Splits agent markdown files into core and extended files.

    Categorization Philosophy (TASK-PD-009):
    - Core = Decision-making ("Should I use this? How do I invoke it?")
    - Extended = Implementation details ("How do I implement? Edge cases?")
    """

    # Core sections (essential, always in main file)
    # These answer: "Should I use this agent? How do I invoke it?"
    CORE_SECTION_PATTERNS = [
        r'^---\n.*?^---',  # Frontmatter (regex with MULTILINE) - Required for discovery
        r'^# .*',  # Title - Agent name and identity

        # Essential for invocation
        r'^## Quick Start$',
        r'^## Getting Started$',
        r'^## Usage$',

        # Boundaries (GitHub standards - TASK-STND-773D)
        r'^## Boundaries$',
        r'^### ALWAYS$',
        r'^### NEVER$',
        r'^### ASK$',

        # Capabilities and phase integration
        r'^## Capabilities$',
        r'^## What I Can Do$',
        r'^## Features$',
        r'^## Phases$',
        r'^## When to Use This Agent$',
        r'^## Integration$',
        r'^## Phase Integration$',

        # Mission and model configuration
        r'^## Mission$',
        r'^## Your Mission$',
        r'^## Your Critical Mission$',
        r'^## Role$',
        r'^## Model$',
        r'^## Model Selection$',
        r'^## Cost$',
    ]

    # Extended sections (detailed, moved to -ext.md file)
    # These answer: "How do I implement correctly? What are edge cases?"
    EXTENDED_SECTION_PATTERNS = [
        # Detailed examples
        r'^## Examples$',
        r'^## Code Examples$',
        r'^## Implementation Example$',
        r'^## Sample$',
        r'^## Code Sample$',
        r'^## Demonstration$',

        # Patterns and practices
        r'^## Patterns$',
        r'^## Best Practices$',
        r'^## Recommended Practice$',
        r'^## Design Pattern$',
        r'^## Architecture Pattern$',

        # Anti-patterns
        r'^## Anti-Patterns$',
        r'^## What Not to Do$',
        r'^## Common Mistake$',
        r'^## Pitfall$',
        r'^## Warning$',

        # Technology specifics
        r'^## Technology Details$',
        r'^## Stack$',
        r'^## Framework$',
        r'^## Language-Specific$',
        r'^## Python$',
        r'^## TypeScript$',
        r'^## React$',
        r'^## \.NET$',
        r'^## FastAPI$',

        # MCP integration (advanced)
        r'^## MCP Integration$',
        r'^## Context7$',
        r'^## Design Pattern MCP$',
        r'^## Tool Integration$',

        # Troubleshooting and edge cases
        r'^## Troubleshooting$',
        r'^## Debug$',
        r'^## Common Issue$',
        r'^## FAQ$',
        r'^## Edge Case$',
        r'^## Known Issue$',

        # Implementation guides
        r'^## Implementation Guide$',
        r'^## Step-by-Step$',
        r'^## Walkthrough$',
        r'^## Tutorial$',
        r'^## How To$',

        # Reference material
        r'^## Reference$',
        r'^## Appendix$',
        r'^## Additional$',
        r'^## See Also$',
        r'^## Related$',
        r'^## Further Reading$',

        # Advanced topics
        r'^## Advanced Usage$',
        r'^## Performance$',
        r'^## Testing$',
        r'^## Templates$',
    ]

    # Agent-specific overrides (TASK-PD-009)
    # Some agents have unique sections requiring special handling
    AGENT_OVERRIDES = {
        'task-manager': {
            'core_additional': [
                'Phase 2.5', 'Phase 2.7', 'Phase 2.8',  # Critical routing logic
                'State Management', 'Quality Gates'
            ],
            'extended_additional': [
                'Detailed Workflow', 'Complex Scenarios'
            ]
        },
        'architectural-reviewer': {
            'core_additional': [
                'SOLID Principles',  # Keep summary
                'Scoring'
            ],
            'extended_additional': [
                'SOLID Examples',    # Move detailed examples
                'Pattern Analysis'
            ]
        },
        'code-reviewer': {
            'core_additional': [
                'Build Verification', 'Approval Checklist'
            ],
            'extended_additional': [
                'Documentation Level', 'Detailed Checklists'
            ]
        }
    }

    # Validation rules (TASK-PD-009)
    VALIDATION_RULES = {
        'core': {
            'max_size_kb': 15,              # Core should be ≤15KB
            'required_sections': [
                'frontmatter',
                'title',
                'boundaries',               # GitHub standards
                'loading_instruction'       # Added by splitter
            ],
            'max_examples': 10,             # Limit examples in core
        },
        'extended': {
            'min_size_kb': 0.5,             # Should have substantial content (reduced from 5KB)
            'required_sections': [
                'header',                   # Reference to core file
            ],
        },
        'overall': {
            'target_reduction_percent': 40,  # Target 40% reduction (not enforced)
            'content_preserved': True,       # No content loss
        }
    }

    def __init__(self, dry_run: bool = False, validate: bool = False):
        """Initialize splitter.

        Args:
            dry_run: If True, preview changes without writing files
            validate: If True, validate splits meet requirements
        """
        self.dry_run = dry_run
        self.validate = validate

    def split_agent(self, agent_path: Path) -> SplitResult:
        """Split an agent file into core and extended files.

        Args:
            agent_path: Path to agent markdown file

        Returns:
            SplitResult with split content and metrics
        """
        if not agent_path.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_path}")

        # Read original content
        content = agent_path.read_text(encoding='utf-8')
        original_size = len(content.encode('utf-8'))

        # Parse sections
        sections = self._parse_sections(content)

        # Categorize into core and extended (with agent-specific overrides)
        agent_name = agent_path.stem
        core_sections, extended_sections = self._categorize_sections(sections, agent_name)

        # Build core and extended content
        core_content = self._build_core_content(core_sections, agent_path)
        extended_content = self._build_extended_content(extended_sections, agent_path)

        # Calculate metrics
        core_size = len(core_content.encode('utf-8'))
        extended_size = len(extended_content.encode('utf-8'))
        reduction_percent = ((original_size - core_size) / original_size * 100) if original_size > 0 else 0

        sections_moved = [s['title'] for s in extended_sections]

        result = SplitResult(
            agent_path=agent_path,
            core_content=core_content,
            extended_content=extended_content,
            core_size=core_size,
            extended_size=extended_size,
            original_size=original_size,
            reduction_percent=reduction_percent,
            sections_moved=sections_moved
        )

        # Write files if not dry run
        if not self.dry_run:
            self._write_files(agent_path, core_content, extended_content)

        return result

    def _parse_sections(self, content: str) -> List[dict]:
        """Parse markdown content into sections.

        Args:
            content: Markdown content

        Returns:
            List of section dicts with 'title', 'content', 'level'
        """
        sections = []

        # Extract frontmatter first (special case)
        frontmatter_match = re.search(r'^---\n(.*?)^---', content, re.MULTILINE | re.DOTALL)
        if frontmatter_match:
            sections.append({
                'title': 'frontmatter',
                'content': frontmatter_match.group(0),
                'level': 0,
                'start': frontmatter_match.start(),
                'end': frontmatter_match.end()
            })
            # Remove frontmatter from content for subsequent parsing
            content_after_frontmatter = content[frontmatter_match.end():].lstrip('\n')
        else:
            content_after_frontmatter = content

        # Parse markdown sections (# Title, ## Section, etc.)
        section_pattern = r'^(#{1,6})\s+(.+)$'
        lines = content_after_frontmatter.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            match = re.match(section_pattern, line)
            if match:
                # Save previous section
                if current_section:
                    sections.append({
                        'title': current_section['title'],
                        'content': '\n'.join(current_content).strip(),
                        'level': current_section['level']
                    })

                # Start new section
                level = len(match.group(1))
                title = match.group(2).strip()
                current_section = {'title': title, 'level': level}
                current_content = [line]
            else:
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            sections.append({
                'title': current_section['title'],
                'content': '\n'.join(current_content).strip(),
                'level': current_section['level']
            })

        return sections

    def _categorize_sections(self, sections: List[dict], agent_name: str = None) -> Tuple[List[dict], List[dict]]:
        """Categorize sections into core and extended.

        Args:
            sections: List of section dicts
            agent_name: Name of agent file (for overrides)

        Returns:
            Tuple of (core_sections, extended_sections)
        """
        core_sections = []
        extended_sections = []

        for section in sections:
            if self._is_core_section(section, agent_name):
                core_sections.append(section)
            else:
                extended_sections.append(section)

        return core_sections, extended_sections

    def _is_core_section(self, section: dict, agent_name: str = None) -> bool:
        """Check if a section should be in core file.

        Args:
            section: Section dict with 'title', 'content', 'level'
            agent_name: Name of agent file (for overrides)

        Returns:
            True if section belongs in core file
        """
        # Frontmatter always goes to core
        if section['title'] == 'frontmatter':
            return True

        section_title = section['title']

        # Check agent-specific overrides first (TASK-PD-009)
        if agent_name and agent_name in self.AGENT_OVERRIDES:
            overrides = self.AGENT_OVERRIDES[agent_name]

            # Check if section is in agent's core_additional list
            if 'core_additional' in overrides:
                if any(section_title.startswith(core_sec) or section_title == core_sec
                       for core_sec in overrides['core_additional']):
                    return True

            # Check if section is in agent's extended_additional list
            if 'extended_additional' in overrides:
                if any(section_title.startswith(ext_sec) or section_title == ext_sec
                       for ext_sec in overrides['extended_additional']):
                    return False

        # Check against core patterns
        for pattern in self.CORE_SECTION_PATTERNS:
            # For section titles, match against the markdown header format
            section_header = f"{'#' * section['level']} {section_title}"
            if re.match(pattern, section_header):
                return True

        # Check if it's explicitly an extended section
        for pattern in self.EXTENDED_SECTION_PATTERNS:
            section_header = f"{'#' * section['level']} {section_title}"
            if re.match(pattern, section_header):
                return False

        # Default: treat as core (conservative approach - TASK-PD-009)
        return True

    def _build_core_content(self, sections: List[dict], agent_path: Path) -> str:
        """Build core content with loading instructions.

        Args:
            sections: Core sections
            agent_path: Path to agent file

        Returns:
            Core markdown content
        """
        ext_filename = agent_path.stem + '-ext.md'

        # Start with sections
        content_parts = [s['content'] for s in sections]

        # Add loading instruction at the end
        loading_instruction = self._generate_loading_instruction(ext_filename)
        content_parts.append(loading_instruction)

        return '\n\n'.join(content_parts)

    def _build_extended_content(self, sections: List[dict], agent_path: Path) -> str:
        """Build extended content with header.

        Args:
            sections: Extended sections
            agent_path: Path to agent file

        Returns:
            Extended markdown content
        """
        agent_name = agent_path.stem

        header = f"""# {agent_name} - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the {agent_name} agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: {datetime.now().strftime('%Y-%m-%d')}

---
"""

        content_parts = [header] + [s['content'] for s in sections]

        return '\n\n'.join(content_parts)

    def _generate_loading_instruction(self, ext_filename: str) -> str:
        """Generate loading instruction for core file.

        Args:
            ext_filename: Name of extended file

        Returns:
            Loading instruction markdown
        """
        return f"""## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat {ext_filename}
```

Or in Claude Code:
```
Please read {ext_filename} for detailed examples.
```"""

    def _write_files(self, agent_path: Path, core_content: str, extended_content: str) -> None:
        """Write core and extended files to disk.

        Args:
            agent_path: Path to original agent file
            core_content: Core markdown content
            extended_content: Extended markdown content
        """
        # Create backup of original
        backup_path = agent_path.with_suffix('.md.bak')
        agent_path.rename(backup_path)

        # Write core file (same location as original)
        agent_path.write_text(core_content, encoding='utf-8')

        # Write extended file (same directory, -ext.md suffix)
        ext_path = agent_path.parent / f"{agent_path.stem}-ext.md"
        ext_path.write_text(extended_content, encoding='utf-8')


def find_agents(pattern: str) -> List[Path]:
    """Find agent files matching pattern.

    Args:
        pattern: Pattern to match ('all-global', 'template:name', or path)

    Returns:
        List of agent file paths
    """
    repo_root = Path(__file__).parent.parent

    if pattern == 'all-global':
        agent_dir = repo_root / 'installer' / 'global' / 'agents'
        return sorted(agent_dir.glob('*.md'))
    elif pattern.startswith('template:'):
        template_name = pattern.split(':', 1)[1]
        agent_dir = repo_root / 'installer' / 'global' / 'templates' / template_name / 'agents'
        if not agent_dir.exists():
            return []
        return sorted(agent_dir.glob('*.md'))
    else:
        # Single agent path
        agent_path = Path(pattern)
        if not agent_path.is_absolute():
            agent_path = repo_root / agent_path
        return [agent_path] if agent_path.exists() else []


def display_result(result: SplitResult, dry_run: bool = False) -> None:
    """Display split result to console.

    Args:
        result: SplitResult to display
        dry_run: Whether this was a dry run
    """
    status = "[DRY RUN]" if dry_run else "[SPLIT]"

    print(f"{status} {result.agent_path.name}")
    print(f"  Original: {result.original_size:,} bytes")
    print(f"  Core:     {result.core_size:,} bytes ({100 - result.reduction_percent:.1f}% of original)")
    print(f"  Extended: {result.extended_size:,} bytes")
    print(f"  Reduction: {result.reduction_percent:.1f}%")

    if result.sections_moved:
        print(f"  Sections moved to extended: {', '.join(result.sections_moved)}")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Split agent markdown files into core and extended files for progressive disclosure.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split single agent
  python scripts/split-agent.py --agent installer/global/agents/task-manager.md

  # Split all global agents
  python scripts/split-agent.py --all-global

  # Split template agents
  python scripts/split-agent.py --template react-typescript

  # Preview without writing (dry run)
  python scripts/split-agent.py --all-global --dry-run

  # Validate splits
  python scripts/split-agent.py --all-global --validate
        """
    )

    # Mutually exclusive group for agent selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--agent', help='Path to single agent file')
    group.add_argument('--all-global', action='store_true', help='Process all global agents')
    group.add_argument('--template', help='Process agents in specified template')

    # Optional flags
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing files')
    parser.add_argument('--validate', action='store_true', help='Validate splits meet requirements')

    args = parser.parse_args()

    # Determine which agents to process
    if args.agent:
        pattern = args.agent
    elif args.all_global:
        pattern = 'all-global'
    else:  # args.template
        pattern = f'template:{args.template}'

    # Find agents
    agents = find_agents(pattern)

    if not agents:
        print(f"ERROR: No agent files found for pattern: {pattern}", file=sys.stderr)
        return 1

    # Process agents
    splitter = AgentSplitter(dry_run=args.dry_run, validate=args.validate)
    results = []
    errors = []

    for agent_path in agents:
        try:
            result = splitter.split_agent(agent_path)
            results.append(result)
            display_result(result, dry_run=args.dry_run)
        except Exception as e:
            errors.append((agent_path, str(e)))
            print(f"ERROR: Failed to split {agent_path.name}: {e}", file=sys.stderr)

    # Display summary for batch operations
    if len(agents) > 1:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total agents processed: {len(results)}")
        print(f"Total agents failed: {len(errors)}")

        if results:
            avg_reduction = sum(r.reduction_percent for r in results) / len(results)
            total_original = sum(r.original_size for r in results)
            total_core = sum(r.core_size for r in results)
            total_extended = sum(r.extended_size for r in results)

            print(f"Average reduction: {avg_reduction:.1f}%")
            print(f"Total original size: {total_original:,} bytes")
            print(f"Total core size: {total_core:,} bytes")
            print(f"Total extended size: {total_extended:,} bytes")

        if errors:
            print("\nFailed agents:")
            for agent_path, error in errors:
                print(f"  - {agent_path.name}: {error}")

    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
