# Feature: Init Graphiti Polish

**Feature ID**: FEAT-IGP
**Parent Review**: TASK-REV-A73F
**Created**: 2026-03-15

## Problem Statement

The `guardkit init` → Graphiti migration is functionally correct (score: 82/100), but has a UX gap: users must remember to run `guardkit graphiti seed-system` as a separate step after init. This leaves new projects in a degraded state for AutoBuild until system seeding completes.

## Solution Approach

Three small improvements to close the gap:

1. **Auto-offer system seeding** inline after project seeding (closes the primary UX gap)
2. **Document the two-phase architecture** so users understand the design
3. **Encourage `--copy-graphiti`** for multi-project FalkorDB setups (prevents config gaps)

## Subtasks

| ID | Title | Mode | Complexity | Priority |
|----|-------|------|------------|----------|
| TASK-IGP-001 | Auto-offer system seeding after init | task-work | 3 | Medium |
| TASK-IGP-002 | Document two-phase seeding architecture | direct | 2 | Low |
| TASK-IGP-003 | Encourage --copy-graphiti for multi-project | direct | 1 | Low |

## Execution Strategy

All 3 tasks are independent and can run in parallel (Wave 1). TASK-IGP-002 should check if TASK-IGP-001 has landed to adjust messaging accordingly, but this is a soft dependency.

## Review Traceability

This feature was created from the [I]mplement decision on TASK-REV-A73F (Review init Graphiti migration integrity). See the full review report at `.claude/reviews/TASK-REV-A73F-review-report.md`.
