---
id: TASK-PD-008
title: Create scripts/split-agent.py (automated splitter)
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: high
tags: [progressive-disclosure, phase-3, automation, script]
complexity: 6
blocked_by: [TASK-PD-007]
blocks: [TASK-PD-009]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create scripts/split-agent.py (automated splitter)

## Phase

**Phase 3: Automated Global Agent Migration**

## Description

Create an automated script to split existing agent files into core and extended files, following the pattern established in TASK-STND-773D for bulk agent processing.

## Script Design

### Usage

```bash
# Split single agent
python3 scripts/split-agent.py --agent installer/global/agents/task-manager.md

# Split all global agents
python3 scripts/split-agent.py --all-global

# Split template agents
python3 scripts/split-agent.py --template react-typescript

# Dry run (preview changes)
python3 scripts/split-agent.py --dry-run --all-global

# Validate existing splits
python3 scripts/split-agent.py --validate --all-global
```

### Core Implementation

```python
#!/usr/bin/env python3
"""
Automated agent file splitter for progressive disclosure.

Pattern: Following TASK-STND-773D automated enhancement approach

Usage:
    python3 scripts/split-agent.py --agent <path>
    python3 scripts/split-agent.py --all-global
    python3 scripts/split-agent.py --template <name>
    python3 scripts/split-agent.py --dry-run --all-global
    python3 scripts/split-agent.py --validate --all-global
"""

import argparse
import re
from pathlib import Path
from typing import Tuple, List, Optional
from dataclasses import dataclass
import yaml


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


class AgentSplitter:
    """Splits agent files into core and extended content."""

    # Section patterns that belong in CORE (always loaded)
    CORE_SECTION_PATTERNS = [
        r'^---[\s\S]+?---',           # Frontmatter
        r'^# .+',                      # Title
        r'^## Quick Start',
        r'^## Boundaries',
        r'^## Capabilities',
        r'^## Phase \d',
        r'^## When to Use',
        r'^## Your (?:Critical )?Mission',
        r'^## Integration',
        r'^## Model',                  # Model configuration
    ]

    # Section patterns that belong in EXTENDED (loaded on-demand)
    EXTENDED_SECTION_PATTERNS = [
        r'^## .*Example',
        r'^## .*Pattern',
        r'^## .*Anti-Pattern',
        r'^## .*Best Practice',
        r'^## .*Troubleshoot',
        r'^## .*Template',
        r'^## .*Technology',
        r'^## .*MCP',
        r'^## .*Detail',
        r'^## .*Reference',
        r'^## .*Implementation Guide',
        r'^## .*Code Sample',
        r'^## .*Workflow Detail',
    ]

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def split_agent(self, agent_path: Path) -> SplitResult:
        """Split agent file into core and extended content.

        Args:
            agent_path: Path to agent markdown file

        Returns:
            SplitResult with split content and metadata
        """
        content = agent_path.read_text(encoding='utf-8')
        original_size = len(content.encode('utf-8'))

        # Parse sections
        sections = self._parse_sections(content)

        # Categorize sections
        core_sections, extended_sections = self._categorize_sections(sections)

        # Build content
        core_content = self._build_core_content(core_sections, agent_path)
        extended_content = self._build_extended_content(extended_sections, agent_path)

        # Calculate metrics
        core_size = len(core_content.encode('utf-8'))
        extended_size = len(extended_content.encode('utf-8'))
        reduction = ((original_size - core_size) / original_size) * 100 if original_size > 0 else 0

        result = SplitResult(
            agent_path=agent_path,
            core_content=core_content,
            extended_content=extended_content,
            core_size=core_size,
            extended_size=extended_size,
            original_size=original_size,
            reduction_percent=reduction,
            sections_moved=[s['heading'] for s in extended_sections]
        )

        if not self.dry_run:
            self._write_files(agent_path, core_content, extended_content)

        return result

    def _parse_sections(self, content: str) -> List[dict]:
        """Parse markdown into sections."""
        sections = []
        current_section = {'heading': '', 'content': '', 'level': 0}

        lines = content.split('\n')
        in_frontmatter = False

        for line in lines:
            # Handle frontmatter
            if line.strip() == '---':
                if not in_frontmatter and not sections:
                    in_frontmatter = True
                    current_section['heading'] = 'frontmatter'
                    current_section['content'] = '---\n'
                    continue
                elif in_frontmatter:
                    current_section['content'] += '---\n'
                    sections.append(current_section)
                    current_section = {'heading': '', 'content': '', 'level': 0}
                    in_frontmatter = False
                    continue

            if in_frontmatter:
                current_section['content'] += line + '\n'
                continue

            # Check for heading
            if line.startswith('# '):
                if current_section['content']:
                    sections.append(current_section)
                current_section = {
                    'heading': line[2:].strip(),
                    'content': line + '\n',
                    'level': 1
                }
            elif line.startswith('## '):
                if current_section['content']:
                    sections.append(current_section)
                current_section = {
                    'heading': line[3:].strip(),
                    'content': line + '\n',
                    'level': 2
                }
            else:
                current_section['content'] += line + '\n'

        if current_section['content']:
            sections.append(current_section)

        return sections

    def _categorize_sections(self, sections: List[dict]) -> Tuple[List[dict], List[dict]]:
        """Categorize sections into core and extended."""
        core = []
        extended = []

        for section in sections:
            if self._is_core_section(section):
                core.append(section)
            else:
                extended.append(section)

        return core, extended

    def _is_core_section(self, section: dict) -> bool:
        """Check if section belongs in core file."""
        heading = section['heading'].lower()

        # Frontmatter always core
        if section['heading'] == 'frontmatter':
            return True

        # Title (level 1) always core
        if section['level'] == 1:
            return True

        # Check against core patterns
        core_keywords = [
            'quick start', 'boundaries', 'capabilities', 'phase',
            'when to use', 'mission', 'integration', 'model',
            'your critical', 'always', 'never', 'ask'
        ]
        if any(kw in heading for kw in core_keywords):
            return True

        # Check against extended patterns
        extended_keywords = [
            'example', 'pattern', 'anti-pattern', 'best practice',
            'troubleshoot', 'template', 'technology', 'mcp',
            'detail', 'reference', 'implementation guide', 'code sample',
            'workflow detail', 'cross-stack', 'edge case'
        ]
        if any(kw in heading for kw in extended_keywords):
            return False

        # Default: keep in core for safety
        return True

    def _build_core_content(self, sections: List[dict], agent_path: Path) -> str:
        """Build core file content with loading instruction."""
        content = ''
        for section in sections:
            content += section['content']

        # Add loading instruction
        ext_filename = f"{agent_path.stem}-ext.md"
        content += self._generate_loading_instruction(ext_filename)

        return content

    def _build_extended_content(self, sections: List[dict], agent_path: Path) -> str:
        """Build extended file content with header."""
        header = f"""# {agent_path.stem} - Extended Reference

**Core file**: `{agent_path.name}`

This file contains detailed examples, patterns, and reference material.
Load this file before detailed implementation work.

---

"""
        content = header
        for section in sections:
            content += section['content']

        return content

    def _generate_loading_instruction(self, ext_filename: str) -> str:
        """Generate loading instruction section."""
        return f'''
---

## Extended Reference

Before generating code or performing detailed implementation, load the extended reference:

```bash
cat agents/{ext_filename}
```

**Extended file contains**:
- Detailed code examples (30+)
- Template best practices
- Anti-patterns to avoid
- Technology-specific guidance
- MCP integration details
- Troubleshooting scenarios
'''

    def _write_files(self, agent_path: Path, core: str, extended: str) -> None:
        """Write split files to disk."""
        # Backup original
        backup_path = agent_path.with_suffix('.md.bak')
        if not backup_path.exists():
            agent_path.rename(backup_path)

        # Write core (overwrites original path)
        agent_path.write_text(core, encoding='utf-8')

        # Write extended
        ext_path = agent_path.with_stem(f"{agent_path.stem}-ext")
        ext_path.write_text(extended, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Split agent files for progressive disclosure')
    parser.add_argument('--agent', type=Path, help='Path to single agent file')
    parser.add_argument('--all-global', action='store_true', help='Split all global agents')
    parser.add_argument('--template', type=str, help='Template name to split agents for')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--validate', action='store_true', help='Validate existing splits')

    args = parser.parse_args()

    splitter = AgentSplitter(dry_run=args.dry_run)

    if args.agent:
        result = splitter.split_agent(args.agent)
        print_result(result, args.dry_run)

    elif args.all_global:
        global_agents_dir = Path('installer/global/agents')
        results = []
        for agent_file in sorted(global_agents_dir.glob('*.md')):
            if agent_file.stem.endswith('-ext'):
                continue
            result = splitter.split_agent(agent_file)
            results.append(result)
            print_result(result, args.dry_run)

        print_summary(results)

    elif args.template:
        template_agents_dir = Path(f'installer/global/templates/{args.template}/agents')
        # Similar to --all-global


def print_result(result: SplitResult, dry_run: bool) -> None:
    """Print split result."""
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}{result.agent_path.name}")
    print(f"  Original: {result.original_size:,} bytes")
    print(f"  Core: {result.core_size:,} bytes")
    print(f"  Extended: {result.extended_size:,} bytes")
    print(f"  Reduction: {result.reduction_percent:.1f}%")
    print(f"  Sections moved: {len(result.sections_moved)}")
    print()


def print_summary(results: List[SplitResult]) -> None:
    """Print summary of all splits."""
    total_original = sum(r.original_size for r in results)
    total_core = sum(r.core_size for r in results)
    avg_reduction = sum(r.reduction_percent for r in results) / len(results)

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Agents processed: {len(results)}")
    print(f"Total original size: {total_original:,} bytes")
    print(f"Total core size: {total_core:,} bytes")
    print(f"Average reduction: {avg_reduction:.1f}%")


if __name__ == '__main__':
    main()
```

## Acceptance Criteria

- [ ] Script handles single agent splitting
- [ ] Script handles all global agents (--all-global)
- [ ] Script handles template agents (--template)
- [ ] Dry run mode works correctly
- [ ] Backup of original files created
- [ ] Loading instruction added to core files
- [ ] Header added to extended files
- [ ] Size metrics calculated and displayed
- [ ] Summary output for batch operations

## Test Strategy

```bash
# Test single agent
python3 scripts/split-agent.py --dry-run --agent installer/global/agents/task-manager.md

# Verify output shows:
# - Original size
# - Projected core size
# - Projected extended size
# - Reduction percentage
# - Sections to be moved

# Test validation
python3 scripts/split-agent.py --validate --agent installer/global/agents/task-manager.md
```

## Files to Create

1. `scripts/split-agent.py` - Main script

## Estimated Effort

**1.5 days**

## Dependencies

- TASK-PD-007 (Phase 2 complete)

## Pattern Reference

This follows the TASK-STND-773D approach where we automated boundary section generation instead of manual conversion.
