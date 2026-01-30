---
id: TASK-GR-001-G
title: Implement CLAUDE.md/README.md parsing
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: high
tags: [graphiti, project-seeding, parsing, mvp-phase-2]
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 7
conductor_workspace: gr-mvp-wave7-seeding
complexity: 4
depends_on:
  - TASK-GR-001-B
  - TASK-GR-001-C
---

# Task: Implement CLAUDE.md/README.md parsing

## Description

Implement parsing of CLAUDE.md and README.md files to extract project overview and architecture information for seeding into Graphiti.

## Acceptance Criteria

- [ ] Parse CLAUDE.md to extract project overview
- [ ] Parse README.md as fallback
- [ ] Extract: purpose, tech stack, key patterns
- [ ] Handle various markdown formats
- [ ] Provide helpful errors for unparseable content

## Implementation Notes

### Parsing Strategy

```python
class ProjectDocParser:
    """Parse CLAUDE.md and README.md for project info."""

    def parse(self, content: str) -> ParseResult:
        """Parse markdown content for project info."""
        # 1. Look for frontmatter (YAML)
        # 2. Extract sections by headers
        # 3. Identify key information
        pass

    def extract_purpose(self, content: str) -> str:
        """Extract project purpose."""
        # Look for: "## Overview", "## Purpose", "## About"
        pass

    def extract_tech_stack(self, content: str) -> TechStack:
        """Extract technology stack."""
        # Look for: "## Tech Stack", "## Technologies", "## Stack"
        pass

    def extract_patterns(self, content: str) -> List[str]:
        """Extract architecture patterns."""
        # Look for: "## Architecture", "## Patterns", "## Structure"
        pass
```

### Header Patterns to Match

```python
PURPOSE_HEADERS = [
    "overview", "purpose", "about", "description",
    "what is this", "project overview"
]

TECH_HEADERS = [
    "tech stack", "technologies", "stack", "built with",
    "technology stack", "dependencies"
]

ARCH_HEADERS = [
    "architecture", "patterns", "structure", "design",
    "system design", "project structure"
]
```

### Files to Create

- `src/guardkit/integrations/graphiti/parsers/project_doc_parser.py`

## Test Requirements

- [ ] Unit tests with sample CLAUDE.md
- [ ] Unit tests with sample README.md
- [ ] Test various markdown formats
- [ ] Test missing sections handling

## Notes

Uses python-frontmatter library for YAML frontmatter parsing.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
