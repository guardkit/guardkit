---
id: TASK-GDU-004
title: Update mkdocs.yml navigation for Graphiti docs
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T00:30:00Z
completed: 2026-02-02T00:30:00Z
priority: high
tags: [documentation, graphiti, github-pages, mkdocs]
complexity: 2
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 2
implementation_mode: direct
dependencies: [TASK-GDU-001, TASK-GDU-002, TASK-GDU-003]
---

# Task: Update mkdocs.yml Navigation for Graphiti Docs

## Description

Update the `mkdocs.yml` navigation structure to include all Graphiti documentation, including the new guides created in Wave 1 and existing orphaned docs.

## Current State

Current navigation (lines 112-115):
```yaml
- Knowledge Graph:
    - Integration Guide: guides/graphiti-integration-guide.md
    - Setup: setup/graphiti-setup.md
    - Architecture: architecture/graphiti-architecture.md
```

Orphaned docs (exist but not in nav):
- `guides/graphiti-commands.md`
- `guides/graphiti-add-context.md`
- `guides/graphiti-project-namespaces.md`
- `guides/graphiti-parsers.md`
- `guides/graphiti-testing-validation.md`
- `guides/graphiti-context-troubleshooting.md`

## Required Changes

Update `mkdocs.yml` Knowledge Graph section to:

```yaml
- Knowledge Graph:
    - Overview: guides/graphiti-integration-guide.md
    - Setup: setup/graphiti-setup.md
    - Architecture: architecture/graphiti-architecture.md
    - Commands:
        - CLI Reference: guides/graphiti-commands.md
        - Add Context: guides/graphiti-add-context.md
        - Query Commands: guides/graphiti-query-commands.md
    - Features:
        - Interactive Capture: guides/graphiti-knowledge-capture.md
        - Job-Specific Context: guides/graphiti-job-context.md
        - Project Namespaces: guides/graphiti-project-namespaces.md
    - Reference:
        - Parsers: guides/graphiti-parsers.md
        - Turn State Tracking: guides/graphiti-turn-states.md
        - Testing & Validation: guides/graphiti-testing-validation.md
        - Troubleshooting: guides/graphiti-context-troubleshooting.md
```

## Acceptance Criteria

- [x] All existing orphaned docs added to navigation
- [x] New Wave 1 docs (001, 002, 003) added to navigation
- [x] Turn states placeholder added (for TASK-GDU-006)
- [x] Navigation structure is logical and organized
- [x] MkDocs builds successfully (`mkdocs build`)
- [x] All navigation links resolve correctly

## Estimated Effort

30 minutes

## Implementation Notes

Completed 2026-02-02. Changes made:

1. Updated mkdocs.yml Knowledge Graph section with organized 3-level hierarchy:
   - Top level: Overview, Setup, Architecture
   - Commands subsection: CLI Reference, Add Context, Query Commands
   - Features subsection: Interactive Capture, Job-Specific Context, Project Namespaces
   - Reference subsection: Parsers, Turn State Tracking, Relevance Tuning, Testing & Validation, Troubleshooting

2. Created placeholder `docs/guides/graphiti-turn-states.md` for TASK-GDU-006

3. Also added `guides/relevance-tuning-testing.md` to navigation (was orphaned)

MkDocs build succeeds with no navigation-related warnings.
