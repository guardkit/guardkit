---
id: TASK-GPS-001
title: Fix post-seed ADR path hint in graphiti CLI
status: backlog
task_type: implementation
created: 2026-03-17T15:00:00Z
updated: 2026-03-17T15:00:00Z
priority: low
tags: [graphiti, ux, quick-fix]
parent_review: TASK-REV-5B3A
feature_id: FEAT-GPS1
implementation_mode: direct
wave: 1
complexity: 1
---

# Task: Fix post-seed ADR path hint in graphiti CLI

## Description

After `guardkit graphiti seed` completes, it prints:

```
To seed project ADRs:
  guardkit graphiti add-context docs/adr/ --type adr
```

However, `/system-arch` generates ADRs at `docs/architecture/decisions/`, not `docs/adr/`. The hint should either:
- Auto-detect the actual ADR location, or
- Show a more generic hint that covers both common paths

## Acceptance Criteria

- [ ] Post-seed hint no longer hardcodes `docs/adr/`
- [ ] Hint covers common ADR locations (`docs/adr/`, `docs/architecture/decisions/`, `docs/decisions/`)
- [ ] No test regressions

## Implementation Notes

File: `guardkit/cli/graphiti.py` lines 256-257

Option A (simple): Change hint to generic example:
```
To seed project architecture and ADRs:
  guardkit graphiti add-context docs/architecture/ --pattern "**/*.md"
```

Option B (smart): Auto-detect ADR path from filesystem before printing.
