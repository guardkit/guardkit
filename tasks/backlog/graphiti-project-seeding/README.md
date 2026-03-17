# Feature: Graphiti Project-Specific Seeding Improvements

**Parent Review**: TASK-REV-5B3A
**Feature ID**: FEAT-GPS1

## Problem Statement

Running `guardkit graphiti seed` from a project directory seeds GuardKit's own system context rather than the project's architecture artefacts. While this is by-design behaviour, it creates a UX gap:

1. Users expect `seed` to seed their project content
2. The post-seed hint points to `docs/adr/` but `/system-arch` generates ADRs at `docs/architecture/decisions/`
3. `/system-arch` does not offer to seed its output to Graphiti

## Solution Approach

Three targeted improvements:
1. Fix the misleading ADR path hint in the `seed` command output
2. Add auto-seed prompt to `/system-arch` after generating architecture artefacts
3. Document the two-command workflow more prominently

## Subtasks

| ID | Task | Wave | Mode | Priority |
|----|------|------|------|----------|
| TASK-GPS-001 | Fix post-seed ADR path hint | 1 | direct | Low |
| TASK-GPS-002 | Auto-seed prompt after /system-arch | 1 | task-work | Medium |
| TASK-GPS-003 | Seed agentic-dataset-factory artefacts (manual) | 1 | manual | High |
