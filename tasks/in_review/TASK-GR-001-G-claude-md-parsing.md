---
complexity: 4
conductor_workspace: gr-mvp-wave7-seeding
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-001-B
- TASK-GR-001-C
feature_id: FEAT-GR-MVP
id: TASK-GR-001-G
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-seeding
- parsing
- mvp-phase-2
task_type: feature
title: Implement CLAUDE.md/README.md parsing
updated: 2026-02-01 00:00:00+00:00
wave: 7
implementation:
  completed_at: 2026-02-01
  mode: tdd
  files_created:
    - guardkit/integrations/graphiti/parsers/project_doc_parser.py
    - tests/integrations/graphiti/parsers/test_project_doc_parser.py
  test_results:
    total: 44
    passed: 44
    failed: 0
    coverage: 100%
  code_review: APPROVED
---

# Task: Implement CLAUDE.md/README.md parsing

## Description

Implement parsing of CLAUDE.md and README.md files to extract project overview and architecture information for seeding into Graphiti.

## Acceptance Criteria

- [x] Parse CLAUDE.md to extract project overview
- [x] Parse README.md as fallback
- [x] Extract: purpose, tech stack, key patterns
- [x] Handle various markdown formats
- [x] Provide helpful errors for unparseable content

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

### Files Created

- `guardkit/integrations/graphiti/parsers/project_doc_parser.py` (282 lines)
- `tests/integrations/graphiti/parsers/test_project_doc_parser.py` (735 lines)

## Test Requirements

- [x] Unit tests with sample CLAUDE.md
- [x] Unit tests with sample README.md
- [x] Test various markdown formats
- [x] Test missing sections handling

## Implementation Summary

**TDD Workflow Completed:**
1. RED: 44 failing tests written covering all acceptance criteria
2. GREEN: Implementation created to pass all tests
3. Tests: 44/44 passed with 100% coverage

**Key Features:**
- Parses YAML frontmatter using python-frontmatter library
- Extracts sections by case-insensitive header matching
- Generates EpisodeData for purpose, tech_stack, and architecture sections
- Handles missing sections with helpful warnings
- Supports both .md and .markdown extensions

## Notes

Uses python-frontmatter library for YAML frontmatter parsing.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
