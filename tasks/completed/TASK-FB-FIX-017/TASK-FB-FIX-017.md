---
id: TASK-FB-FIX-017
title: Update CLAUDE.md with pre-loop guidance
status: completed
created: 2026-01-13T15:45:00Z
updated: 2026-01-13T18:35:00Z
completed: 2026-01-13T18:35:00Z
priority: low
tags:
  - feature-build
  - documentation
  - pre-loop
complexity: 2
parent_review: TASK-REV-FB11
implementation_mode: direct
estimated_minutes: 30
actual_minutes: 5
dependencies:
  - TASK-FB-FIX-015
  - TASK-FB-FIX-016
test_results:
  status: passed
  coverage: null
  last_run: 2026-01-13T18:35:00Z
completion_notes: |
  Added Pre-Loop Configuration subsection to CLAUDE.md AutoBuild section.
  Includes default behavior, CLI flags, timeout recommendations table,
  and guidance on when to enable/disable pre-loop.
---

# Update CLAUDE.md with Pre-Loop Guidance

## Description

Add documentation to CLAUDE.md explaining the pre-loop configuration options, default behavior differences between feature-build and task-build, and timeout recommendations for each mode.

## Objectives

- Document default `enable_pre_loop` behavior for feature-build vs task-build
- Add timeout recommendations table
- Explain when to use `--enable-pre-loop` vs `--no-pre-loop`

## Acceptance Criteria

- [x] CLAUDE.md AutoBuild section includes "Pre-Loop Configuration" subsection
- [x] Default behavior documented for feature-build (off) and task-build (on)
- [x] Timeout recommendations table included
- [x] Examples show how to override defaults

## Technical Approach

Add to CLAUDE.md AutoBuild section:

```markdown
### Pre-Loop Configuration

The pre-loop quality gates execute `/task-work --design-only` (Phases 1.6-2.8) before
the Player-Coach loop. This takes 60-90 minutes for comprehensive design.

**Default Behavior**:
- Feature-build (`guardkit autobuild feature`): Pre-loop **disabled** by default
  - Tasks from feature-plan already have detailed specs
  - Use `--enable-pre-loop` to force design phase

- Task-build (`guardkit autobuild task`): Pre-loop **enabled** by default
  - Standalone tasks benefit from design phase
  - Use `--no-pre-loop` to skip for well-defined tasks

**Timeout Recommendations**:
| Mode | Pre-Loop | Recommended Timeout |
|------|----------|---------------------|
| Feature-build | Off (default) | 1800s (30 min) |
| Feature-build | On (--enable-pre-loop) | 7200s (2 hours) |
| Task-build | On (default) | 7200s (2 hours) |
| Task-build | Off (--no-pre-loop) | 1800s (30 min) |
```

## Files to Modify

- `CLAUDE.md` (AutoBuild section)

## Test Requirements

- [x] Documentation renders correctly in markdown preview
- [x] Examples are accurate and match implementation

## Notes

This documentation should be added after TASK-FB-FIX-015 and TASK-FB-FIX-016 are completed to ensure accuracy.
