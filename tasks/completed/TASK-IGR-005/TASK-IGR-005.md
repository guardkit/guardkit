---
id: TASK-IGR-005
title: Add episode progress indicator during seeding
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T12:00:00Z
completed: 2026-03-03T12:30:00Z
priority: medium
complexity: 2
tags: [cli, developer-experience, init, seeding]
parent_review: TASK-REV-21D3
feature_id: FEAT-IGR
wave: 2
implementation_mode: task-work
dependencies: [TASK-IGR-001]
completed_location: tasks/completed/TASK-IGR-005/
---

# Task: Add episode progress indicator during seeding

## Description

Add a progress indicator showing elapsed time and episode count (N/M) during Graphiti seeding in `guardkit init`. Currently, the user sees no feedback between "Step 2: Seeding project knowledge..." and the completion message.

## Context

Seeding takes 3-7 minutes (8 episodes, 21s-79s each with vLLM). Users need visibility into progress. With log noise suppressed (TASK-IGR-001), the only output would be the step header and completion — no intermediate feedback.

## Acceptance Criteria

- [x] Progress shows "Seeding episode N/M..." during seeding
- [x] Elapsed time displayed for each episode
- [x] Failed episodes show warning instead of "done"
- [x] Total seeding time displayed at completion

## Implementation Summary

Used a **proxy pattern** (`_ProgressClient`) that wraps the GraphitiClient and intercepts
`add_episode()` calls to display per-episode progress. Zero changes to internal seeding
functions — the proxy transparently adds progress reporting.

- `_ProgressClient` prints `Seeding episode N/M... done (X.Xs)` per episode
- Failed episodes print `warning (X.Xs): <error>` instead of "done"
- `estimate_episode_count()` pre-counts episodes for N/M display
- Total seeding time shown in completion message

## Files Modified

- `guardkit/cli/init.py` — Added `_ProgressClient`, wrapped seeding client, total time tracking
- `guardkit/knowledge/project_seeding.py` — Added `estimate_episode_count()`

## Files Created

- `tests/cli/test_init_progress.py` — 13 tests (proxy, counting, integration)

## Test Results

- 102/102 tests passed (13 new + 89 existing, zero regressions)
