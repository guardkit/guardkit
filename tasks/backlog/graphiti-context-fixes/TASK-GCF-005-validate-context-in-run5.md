---
id: TASK-GCF-005
title: Validate Graphiti context loading with seeded Run 5
status: backlog
task_type: implementation
priority: medium
tags: [graphiti, validation, vllm, benchmark]
complexity: 3
parent_review: TASK-REV-982B
feature_id: FEAT-GCF
wave: 3
implementation_mode: manual
dependencies: [TASK-GCF-001, TASK-GCF-002, TASK-GCF-003, TASK-GCF-004]
created: 2026-03-08T15:00:00Z
---

# Task: Validate Graphiti context loading with seeded Run 5

## Problem

After fixing all Graphiti root causes (RC1-RC5) and running seeding, we need to validate that context actually loads and impacts AutoBuild performance.

## Steps

1. Run a fresh AutoBuild with all fixes applied:
   ```bash
   guardkit autobuild run --fresh --verbose
   ```

2. Verify in logs:
   - "Player context: N categories, M/5200 tokens" where N > 0
   - Category names listed (e.g., "patterns", "role_constraints")
   - No warning messages from `_query_category()`

3. Compare Run 5 results against Run 4:
   - Total duration
   - Per-task SDK turn counts
   - Context categories loaded per task

## Acceptance Criteria

- [ ] Context categories > 0 for at least 3/10 categories
- [ ] Context tokens > 0 for Player and Coach
- [ ] No silent query failures (verified via new logging from TASK-GCF-002)
- [ ] Performance comparison documented
