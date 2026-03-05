---
id: TASK-SPR-2cf7
title: Change seed status display to reflect actual outcomes
status: completed
completed: 2026-03-05T14:00:00Z
task_type: implementation
created: 2026-03-05T12:00:00Z
priority: medium
complexity: 3
parent_review: TASK-REV-F404
feature_id: FEAT-SPR
tags: [graphiti, seeding, ux, logging]
wave: 2
implementation_mode: task-work
dependencies: [TASK-SPR-5399]
---

# Task: Change seed status display to reflect actual outcomes

## Problem

The seed completion summary shows a checkmark for ALL categories regardless of actual results. With TASK-FIX-bbbd (episode count logging) now showing the truth in logs, the summary display contradicts the detailed output:

```
# Logs show:
WARNING:  Seeded rules: 1/72 episodes (71 skipped)
WARNING:  Seeded project_overview: 0/3 episodes (3 skipped)

# But summary shows:
  ✓ rules
  ✓ project_overview
```

## Solution

Change the summary display to use differentiated indicators based on actual outcomes:

```
Knowledge categories seeded:
  ✓ product_knowledge (3 episodes)
  ✓ quality_gate_phases (12 episodes)
  ⚠ command_workflows (19/20 episodes, 1 skipped)
  ⚠ templates (5/7 episodes, 2 skipped)
  ✗ rules (1/72 episodes, 71 skipped)
  ✗ project_overview (0/3 episodes, 3 skipped)
```

Indicators:
- `✓` — 100% success (all episodes created or no episodes to create)
- `⚠` — Partial success (some episodes created, some skipped)
- `✗` — Failure (0 episodes created, or >80% skipped)

## Files to Modify

- `guardkit/cli/graphiti.py` — Update the seed summary display logic
- `guardkit/knowledge/seeding.py` — May need to return per-category results to CLI

## Acceptance Criteria

- [x] ✓ shown only for 100% success
- [x] ⚠ shown for partial success (1-99% success)
- [x] ✗ shown for failure (0% success or >80% skip rate)
- [x] Episode counts shown alongside indicators
- [x] Existing tests pass
