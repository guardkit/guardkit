# Feature: Init + Graphiti Resilience (FEAT-IGR)

## Problem

`guardkit init` with Graphiti seeding has several reliability and developer experience issues:

1. **75% of init output is noise** (438 httpx lines, 52 "index already exists" messages)
2. **Episodes silently dropped** on transient FalkorDB errors (no retry)
3. **Step 2.5 template sync always fails** (deferred connection pattern creates uninitialized client)
4. **No progress feedback** during 3-7 minute seeding process

## Solution

7 implementation tasks across 2 waves addressing FalkorDB resilience, log verbosity, template sync, and developer experience.

## Task Summary

| ID | Priority | Title | Status |
|----|----------|-------|--------|
| TASK-IGR-001 | P1 | Suppress noisy loggers | completed |
| TASK-IGR-002 | P1 | Add retry with backoff | backlog |
| TASK-IGR-003 | P1 | Reuse client in template sync | backlog |
| TASK-IGR-004 | P1 | FalkorDB MAX_QUEUED_QUERIES | backlog |
| TASK-IGR-005 | P3 | Episode progress indicator | backlog |
| TASK-IGR-006 | P3 | Unify constants groups | backlog |
| TASK-IGR-007 | P3 | Document group ID scoping | backlog |

## Origin

Created from [TASK-REV-21D3](.claude/reviews/TASK-REV-21D3-review-report.md) review of `guardkit init` output analysis.
