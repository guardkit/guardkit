---
id: TASK-FIX-cc7e
title: Increase project_purpose timeout from 300s to 600s
status: completed
created: 2026-03-06T12:00:00Z
updated: 2026-03-06T12:15:00Z
completed: 2026-03-06T12:20:00Z
priority: high
task_type: implementation
complexity: 2
parent_review: TASK-REV-8A31
feature_id: FEAT-GIP
tags: [graphiti, init, timeout, performance]
wave: 1
implementation_mode: task-work
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
completed_location: tasks/completed/2026-03/TASK-FIX-cc7e/
---

# Task: Increase project_purpose timeout from 300s to 600s

## Problem

Episode 1 (project_purpose) has timed out at 300s in every init run since init_8 — except init_12 where it barely completed at 254.4s (85% of the limit). A single slow vLLM inference cycle would push it back over 300s.

### Evidence

| Run | Episode 1 Time | Status |
|-----|---------------|--------|
| init_8 | 300s+ | Timeout |
| init_10 | 300s+ | Timeout |
| init_11 R1 | 300.5s | Timeout |
| init_11 R2 | 300.5s | Timeout |
| init_12 | 254.4s | Success (45s margin) |

## Solution

Increase the project_purpose episode timeout from 300s to 600s in `graphiti_client.py`. This is the pragmatic fix — the episode processes the full CLAUDE.md which will only grow over time.

## Scope

- Change the timeout constant for project_purpose episodes from 300s to 600s
- Verify no other episodes use the 300s tier that should also be updated
- Update any documentation that references the 300s limit

## Acceptance Criteria

- [x] project_purpose timeout increased to 600s
- [x] Other episode timeout tiers reviewed (no cascading changes needed unless discovered)
- [x] Tests pass

## Implementation Notes

### Changes Made

1. **`guardkit/knowledge/graphiti_client.py:974`** — Changed `episode_timeout = 300.0` to `episode_timeout = 600.0` for `project_overview` group_id
2. **`tests/knowledge/test_graphiti_client.py:752-758`** — Updated test assertion from `300.0` to `600.0`

### Other Timeout Tiers Reviewed

| Group ID | Timeout | Status |
|----------|---------|--------|
| project_overview | 600s (was 300s) | **Updated** |
| rules* | 180s | No change needed |
| role_constraints | 150s | No change needed |
| agents | 150s | No change needed |
| templates | 180s | No change needed |
| default | 120s | No change needed |

No other timeout tiers are at risk of hitting their ceiling based on the review evidence.
