---
id: TASK-FIX-GCI6
title: Clarify library_context spec language in task-create
status: completed
task_type: documentation
created: 2026-02-08T23:00:00Z
updated: 2026-02-09T00:00:00Z
completed: 2026-02-09T00:00:00Z
priority: low
parent_review: TASK-REV-C7EB
tags: [documentation, task-create, context7, spec-clarity]
complexity: 1
wave: 3
dependencies: []
---

# Clarify library_context Spec Language in task-create

## CRITICAL: No Stubs Policy

**All changes written for this task MUST be fully functional.** No placeholder text, no TODO markers, no "see also" references to non-existent sections. The updated spec language must be clear, accurate, and complete.

## Description

The `library_context` field in `installer/core/commands/task-create.md` uses `graphiti-core` as the example library:

```yaml
library_context:
  - name: graphiti-core
    version: ">=0.3"
    focus: "Episode body format, _add_episodes() API"
```

This creates confusion about whether `/task-create` has Graphiti knowledge graph integration. It does not - `library_context` is a **Context7 MCP integration** for fetching any library's API documentation. The `graphiti-core` example is just an example library name.

## Changes Required

1. Replace `graphiti-core` with a more generic example library (e.g., `pydantic`, `fastapi`, or `requests`)
2. Add a clarifying note that `library_context` resolves via Context7 MCP, not Graphiti knowledge graph

## Acceptance Criteria

- [x] Example library in `library_context` field is not `graphiti-core`
- [x] Clarifying note added about Context7 vs Graphiti distinction
- [x] No code changes needed

## Files to Modify

- `installer/core/commands/task-create.md`
- Optionally: `installer/core/commands/task-work.md` (if same example appears)
