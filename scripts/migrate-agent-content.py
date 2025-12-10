#!/usr/bin/env python3
"""
Content Migration Script for Progressive Disclosure

Migrates content from core agent files to extended files based on
defined categorization rules to achieve 55%+ token reduction.

Usage:
    python3 scripts/migrate-agent-content.py --agent task-manager [--dry-run]
    python3 scripts/migrate-agent-content.py --all [--dry-run]
    python3 scripts/migrate-agent-content.py --analyze task-manager

Author: GuardKit Team
"""

import argparse
import re
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# Section Categorization Patterns
# =============================================================================

CORE_SECTION_PATTERNS = [
    # Essential metadata and structure
    (r'^## (?:Your )?(?:Core )?Responsibilities', 'responsibilities'),
    (r'^## Overview', 'overview'),
    (r'^## Quick Start', 'quick_start'),
    (r'^## Quick Commands', 'quick_commands'),

    # Boundaries - critical for agent behavior
    (r'^## Boundaries', 'boundaries'),
    (r'^### ALWAYS', 'always'),
    (r'^### NEVER', 'never'),
    (r'^### ASK', 'ask'),

    # Essential reference sections
    (r'^## Capabilities', 'capabilities'),
    (r'^## Phase Integration', 'phase_integration'),
    (r'^## Extended Reference', 'extended_reference'),

    # Safety and navigation
    (r'^## Configuration', 'configuration'),
    (r'^## Security Considerations', 'security'),
    (r'^## See Also', 'see_also'),
    (r'^## References', 'references'),

    # Error handling format
    (r'^## Error Response Template', 'error_template'),
]

EXTENDED_SECTION_PATTERNS = [
    # Detailed content
    (r'^## (?:Additional |Detailed )?Examples?', 'examples'),
    (r'^## Best Practices', 'best_practices'),
    (r'^## Anti-?[Pp]atterns?', 'anti_patterns'),
    (r'^## Template (?:Code )?Examples?', 'template_examples'),

    # Technology-specific
    (r'^## Technology', 'technology'),
    (r'^## Stack-Specific', 'stack_specific'),
    (r'^## Common .* Issues', 'common_issues'),
    (r'^## Related Templates', 'related_templates'),
    (r'^## Cross-Stack', 'cross_stack'),

    # Reference material
    (r'^## Troubleshooting', 'troubleshooting'),
    (r'^## Edge Cases', 'edge_cases'),
    (r'^## Integration (?:Points|Patterns)', 'integration'),
    (r'^## Advanced', 'advanced'),
    (r'^## Reference', 'reference'),

    # Quality and performance
    (r'^## Quality Gates', 'quality_gates'),
    (r'^## Build Gate Criteria', 'build_gates'),
    (r'^## Performance', 'performance'),

    # Historical
    (r'^## History', 'history'),
    (r'^## Changelog', 'changelog'),
    (r'^## Extended Documentation', 'extended_docs'),
]

# Size targets in bytes - Global agents
SIZE_TARGETS = {
    'task-manager': 25000,
    'devops-specialist': 20000,
    'git-workflow-manager': 18000,
    'security-specialist': 18000,
    'database-specialist': 17000,
    'architectural-reviewer': 16000,
    'agent-content-enhancer': 14000,
    'code-reviewer': 12000,
    'debugging-specialist': 12000,
    'test-verifier': 11000,
    'test-orchestrator': 11000,
    'pattern-advisor': 10000,
    'complexity-evaluator': 8000,
    'build-validator': 7000,
}

# Size targets in bytes - Template agents
TEMPLATE_SIZE_TARGETS = {
    # react-typescript
    'feature-architecture-specialist': 12000,
    'form-validation-specialist': 12000,
    'react-query-specialist': 8000,
    'react-state-specialist': 8000,

    # fastapi-python
    'fastapi-specialist': 10000,
    'fastapi-database-specialist': 12000,
    'fastapi-testing-specialist': 10000,

    # nextjs-fullstack
    'nextjs-fullstack-specialist': 12000,
    'nextjs-server-actions-specialist': 12000,
    'nextjs-server-components-specialist': 10000,

    # react-fastapi-monorepo
    'react-fastapi-monorepo-specialist': 12000,
    'docker-orchestration-specialist': 12000,
    'monorepo-type-safety-specialist': 12000,
}

DEFAULT_SIZE_TARGET = 15000


def get_size_target(agent_name: str) -> int:
    """Get size target for agent, checking both global and template targets."""
    if agent_name in SIZE_TARGETS:
        return SIZE_TARGETS[agent_name]
    if agent_name in TEMPLATE_SIZE_TARGETS:
        return TEMPLATE_SIZE_TARGETS[agent_name]
    return DEFAULT_SIZE_TARGET


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Section:
    """Represents a markdown section."""
    heading: str
    level: int
    content: str
    start_line: int
    end_line: int
    category: str = 'unknown'  # 'core', 'extended', 'unknown'
    pattern_match: Optional[str] = None


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    agent_name: str
    original_size: int
    core_size: int
    extended_size: int
    sections_moved: list
    sections_kept: list
    reduction_percent: float
    target_met: bool


# =============================================================================
# Section Parsing
# =============================================================================

def parse_sections(content: str) -> list[Section]:
    """Parse markdown content into sections (H2 only, skip code blocks)."""
    lines = content.split('\n')
    sections = []
    current_section = None
    frontmatter_end = 0
    in_code_block = False

    # Find frontmatter end
    in_frontmatter = False
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if not in_frontmatter:
                in_frontmatter = True
            else:
                frontmatter_end = i + 1
                break

    # Parse sections - only H2 (##) headings, skip inside code blocks
    for i, line in enumerate(lines[frontmatter_end:], start=frontmatter_end):
        # Track code blocks to avoid parsing headers inside them
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Only match H2 headings for section splitting
        heading_match = re.match(r'^(##)\s+(.+)$', line)

        if heading_match:
            # Save previous section
            if current_section:
                current_section.end_line = i - 1
                current_section.content = '\n'.join(
                    lines[current_section.start_line:current_section.end_line + 1]
                )
                sections.append(current_section)

            # Start new section
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            current_section = Section(
                heading=heading,
                level=level,
                content='',
                start_line=i,
                end_line=i,
            )

    # Save last section
    if current_section:
        current_section.end_line = len(lines) - 1
        current_section.content = '\n'.join(
            lines[current_section.start_line:current_section.end_line + 1]
        )
        sections.append(current_section)

    return sections


def categorize_section(section: Section) -> str:
    """Categorize a section as 'core', 'extended', or 'unknown'."""
    heading_line = f"{'#' * section.level} {section.heading}"

    # Check core patterns
    for pattern, name in CORE_SECTION_PATTERNS:
        if re.match(pattern, heading_line, re.IGNORECASE):
            section.category = 'core'
            section.pattern_match = name
            return 'core'

    # Check extended patterns
    for pattern, name in EXTENDED_SECTION_PATTERNS:
        if re.match(pattern, heading_line, re.IGNORECASE):
            section.category = 'extended'
            section.pattern_match = name
            return 'extended'

    # Apply decision matrix for unknown sections
    content_size = len(section.content)
    example_count = section.content.count('```')  # Rough estimate of code blocks

    if example_count >= 10 or content_size > 5000:
        section.category = 'extended'
        section.pattern_match = 'size_heuristic'
        return 'extended'

    # Default: keep small unknown sections in core
    section.category = 'unknown_keep'
    section.pattern_match = 'default_keep'
    return 'unknown'


def categorize_all_sections(sections: list[Section], aggressive: bool = True) -> None:
    """Categorize all H2 sections based on patterns and size heuristics.

    Args:
        sections: List of H2 sections to categorize
        aggressive: If True, use size-based heuristics to move more content
    """
    for section in sections:
        # First, check explicit patterns (highest priority)
        categorize_section(section)

        # If explicitly categorized, keep that
        if section.category in ('core', 'extended'):
            continue

        # Apply size-based heuristics for unknown sections
        content_size = len(section.content)
        code_blocks = section.content.count('```')

        if aggressive:
            # Large sections should move to extended
            if content_size > 4000 or code_blocks >= 6:
                section.category = 'extended'
                section.pattern_match = 'size_heuristic_large'
            else:
                # Keep smaller unknown sections in core
                section.category = 'unknown_keep'
                section.pattern_match = 'size_heuristic_small'
        else:
            # Non-aggressive: keep unknown in core
            section.category = 'unknown_keep'
            section.pattern_match = 'default_keep'


# =============================================================================
# Content Generation
# =============================================================================

def extract_frontmatter(content: str) -> str:
    """Extract frontmatter from content."""
    match = re.match(r'^(---[\s\S]*?---)', content)
    return match.group(1) if match else ''


def generate_core_content(
    content: str,
    sections: list[Section],
    agent_name: str
) -> str:
    """Generate the core file content."""
    frontmatter = extract_frontmatter(content)

    # Collect core sections
    core_parts = [frontmatter]

    for section in sections:
        if section.category in ('core', 'unknown_keep'):
            core_parts.append('')
            core_parts.append(section.content)

    # Add Extended Reference section if not present
    has_extended_ref = any(
        s.pattern_match == 'extended_reference' for s in sections
    )

    if not has_extended_ref:
        extended_ref = f"""
## Extended Reference

For detailed examples, best practices, and troubleshooting:

```bash
cat agents/{agent_name}-ext.md
```

The extended file includes:
- Additional Quick Start examples
- Detailed code examples with explanations
- Best practices with rationale
- Anti-patterns to avoid
- Technology-specific guidance
- Troubleshooting common issues
"""
        core_parts.append(extended_ref)

    return '\n'.join(core_parts).strip() + '\n'


def generate_extended_content(
    sections: list[Section],
    agent_name: str
) -> str:
    """Generate the extended file content."""
    extended_parts = [
        f"# {agent_name} - Extended Reference",
        "",
        f"This file contains detailed documentation for the `{agent_name}` agent.",
        "Load this file when you need comprehensive examples and guidance.",
        "",
        "```bash",
        f"cat agents/{agent_name}-ext.md",
        "```",
        "",
    ]

    for section in sections:
        if section.category == 'extended':
            extended_parts.append('')
            extended_parts.append(section.content)

    return '\n'.join(extended_parts).strip() + '\n'


# =============================================================================
# Migration Operations
# =============================================================================

def analyze_agent(agent_path: Path) -> dict:
    """Analyze an agent file and return migration plan."""
    content = agent_path.read_text()
    sections = parse_sections(content)
    categorize_all_sections(sections)

    agent_name = agent_path.stem
    target_size = get_size_target(agent_name)

    core_sections = [s for s in sections if s.category in ('core', 'unknown_keep')]
    extended_sections = [s for s in sections if s.category == 'extended']

    core_size = sum(len(s.content) for s in core_sections)
    extended_size = sum(len(s.content) for s in extended_sections)

    return {
        'agent_name': agent_name,
        'original_size': len(content),
        'estimated_core_size': core_size,
        'estimated_extended_size': extended_size,
        'target_size': target_size,
        'estimated_reduction': (1 - core_size / len(content)) * 100 if len(content) > 0 else 0,
        'target_met': core_size <= target_size,
        'sections': sections,
        'core_sections': [(s.heading, s.pattern_match) for s in core_sections],
        'extended_sections': [(s.heading, s.pattern_match) for s in extended_sections],
    }


def migrate_agent(
    agent_path: Path,
    dry_run: bool = False,
    verbose: bool = True
) -> MigrationResult:
    """Migrate an agent file to core + extended."""
    content = agent_path.read_text()
    sections = parse_sections(content)
    categorize_all_sections(sections)

    agent_name = agent_path.stem
    agents_dir = agent_path.parent
    ext_path = agents_dir / f"{agent_name}-ext.md"
    backup_path = agents_dir / f"{agent_name}.md.bak"

    target_size = get_size_target(agent_name)

    # Generate new content
    core_content = generate_core_content(content, sections, agent_name)
    extended_content = generate_extended_content(sections, agent_name)

    core_size = len(core_content.encode('utf-8'))
    extended_size = len(extended_content.encode('utf-8'))
    original_size = len(content.encode('utf-8'))

    reduction = (1 - core_size / original_size) * 100 if original_size > 0 else 0

    result = MigrationResult(
        agent_name=agent_name,
        original_size=original_size,
        core_size=core_size,
        extended_size=extended_size,
        sections_moved=[s.heading for s in sections if s.category == 'extended'],
        sections_kept=[s.heading for s in sections if s.category in ('core', 'unknown_keep')],
        reduction_percent=reduction,
        target_met=core_size <= target_size,
    )

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"Agent: {agent_name}")
        print(f"{'=' * 60}")
        print(f"Original size: {original_size:,} bytes ({original_size/1024:.1f}KB)")
        print(f"Core size:     {core_size:,} bytes ({core_size/1024:.1f}KB)")
        print(f"Extended size: {extended_size:,} bytes ({extended_size/1024:.1f}KB)")
        print(f"Target:        {target_size:,} bytes ({target_size/1024:.1f}KB)")
        print(f"Reduction:     {reduction:.1f}%")
        print(f"Target met:    {'Yes' if result.target_met else 'NO - needs adjustment'}")
        print(f"\nSections kept in core ({len(result.sections_kept)}):")
        for s in result.sections_kept[:10]:
            print(f"  - {s}")
        if len(result.sections_kept) > 10:
            print(f"  ... and {len(result.sections_kept) - 10} more")
        print(f"\nSections moved to extended ({len(result.sections_moved)}):")
        for s in result.sections_moved[:10]:
            print(f"  - {s}")
        if len(result.sections_moved) > 10:
            print(f"  ... and {len(result.sections_moved) - 10} more")

    if not dry_run:
        # Create backup
        if verbose:
            print(f"\nCreating backup: {backup_path}")
        shutil.copy2(agent_path, backup_path)

        # Write core file
        if verbose:
            print(f"Writing core: {agent_path}")
        agent_path.write_text(core_content)

        # Write extended file
        if verbose:
            print(f"Writing extended: {ext_path}")
        ext_path.write_text(extended_content)

        if verbose:
            print(f"\nMigration complete!")
    else:
        if verbose:
            print(f"\n[DRY RUN] No files modified")

    return result


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Migrate agent content for progressive disclosure'
    )
    parser.add_argument(
        '--agent',
        help='Agent name to migrate (e.g., task-manager)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Migrate all agents'
    )
    parser.add_argument(
        '--analyze',
        help='Analyze agent without migrating'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--agents-dir',
        default='installer/core/agents',
        help='Path to agents directory'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )

    args = parser.parse_args()
    agents_dir = Path(args.agents_dir)

    if not agents_dir.exists():
        print(f"Error: Agents directory not found: {agents_dir}")
        return 1

    if args.analyze:
        # Analyze mode
        agent_path = agents_dir / f"{args.analyze}.md"
        if not agent_path.exists():
            print(f"Error: Agent not found: {agent_path}")
            return 1

        analysis = analyze_agent(agent_path)
        print(f"\n{'=' * 60}")
        print(f"Analysis: {analysis['agent_name']}")
        print(f"{'=' * 60}")
        print(f"Original size:    {analysis['original_size']:,} bytes")
        print(f"Est. core size:   {analysis['estimated_core_size']:,} bytes")
        print(f"Est. ext size:    {analysis['estimated_extended_size']:,} bytes")
        print(f"Target size:      {analysis['target_size']:,} bytes")
        print(f"Est. reduction:   {analysis['estimated_reduction']:.1f}%")
        print(f"Target met:       {'Yes' if analysis['target_met'] else 'NO'}")

        print(f"\nCore sections ({len(analysis['core_sections'])}):")
        for heading, pattern in analysis['core_sections']:
            print(f"  [{pattern}] {heading}")

        print(f"\nExtended sections ({len(analysis['extended_sections'])}):")
        for heading, pattern in analysis['extended_sections']:
            print(f"  [{pattern}] {heading}")

        return 0

    if args.agent:
        # Single agent migration
        agent_path = agents_dir / f"{args.agent}.md"
        if not agent_path.exists():
            print(f"Error: Agent not found: {agent_path}")
            return 1

        result = migrate_agent(agent_path, dry_run=args.dry_run, verbose=not args.quiet)
        return 0 if result.target_met else 1

    if args.all:
        # Migrate all agents - discover from directory
        results = []

        # Find all core agent files (exclude -ext.md files)
        agent_files = sorted([
            f for f in agents_dir.glob("*.md")
            if not f.stem.endswith('-ext') and not f.stem.endswith('.bak')
        ])

        if not agent_files:
            print(f"No agent files found in: {agents_dir}")
            return 1

        print(f"Found {len(agent_files)} agent(s) in {agents_dir}")

        for agent_path in agent_files:
            result = migrate_agent(
                agent_path,
                dry_run=args.dry_run,
                verbose=not args.quiet
            )
            results.append(result)

        # Summary
        print(f"\n{'=' * 60}")
        print("Migration Summary")
        print(f"{'=' * 60}")

        total_original = sum(r.original_size for r in results)
        total_core = sum(r.core_size for r in results)
        total_extended = sum(r.extended_size for r in results)
        targets_met = sum(1 for r in results if r.target_met)

        print(f"Agents processed: {len(results)}")
        print(f"Targets met:      {targets_met}/{len(results)}")
        print(f"Total original:   {total_original:,} bytes ({total_original/1024:.1f}KB)")
        print(f"Total core:       {total_core:,} bytes ({total_core/1024:.1f}KB)")
        print(f"Total extended:   {total_extended:,} bytes ({total_extended/1024:.1f}KB)")
        print(f"Overall reduction: {(1 - total_core/total_original)*100:.1f}%")

        return 0 if targets_met == len(results) else 1

    parser.print_help()
    return 1


if __name__ == '__main__':
    exit(main())
