---
id: TASK-REV-B9E1
title: Review system-plan AutoBuild run 2 (post-GTP fixes)
status: review_complete
created: 2026-02-09T17:00:00Z
updated: 2026-02-09T17:00:00Z
priority: high
tags: [review, autobuild, system-plan, graphiti, too-many-open-files, FEAT-6EDD]
task_type: review
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review system-plan AutoBuild Run 2 (Post-GTP Fixes)

## Description

Analyse the second AutoBuild run of FEAT-6EDD (system-plan) captured in `docs/reviews/system_understanding/system_plan_2.md`. This run was executed **after** the Graphiti per-thread migration (FEAT-C90E: TASK-FIX-GTP1 through TASK-DOC-GTP6) which fixed the cross-loop hang from the first run.

### New Failure Mode

The first run (analysed in TASK-REV-2AA0) stalled due to a shared Graphiti singleton causing cross-loop hangs in parallel tasks. That bug has been fixed. This second run shows a **different failure**:

- **SP-003** (Graphiti read-write operations): `Orchestration failed: [Errno 24] Too many open files`
- **SP-005** (Architecture markdown writer): `Orchestration failed: [Errno 24] Too many open files`
- **SP-004** (Adaptive question flow): Completed successfully (1 turn, approved)
- **SP-001, SP-002** (Wave 1): Both completed successfully

The `[Errno 24] Too many open files` error occurred in Wave 2 where SP-003, SP-004, and SP-005 ran in parallel. Two of three parallel tasks hit the file descriptor limit.

### Investigation Areas

1. **Root cause of `[Errno 24]`**: Is this caused by:
   - Per-thread Graphiti clients opening too many Neo4j connections? (Each thread now creates its own client with its own driver)
   - The worktree having too many files open (git operations + SDK + context loading)?
   - A pre-existing system ulimit that's too low for 3 parallel AutoBuild tasks?
   - File descriptor leak in the orchestrator or SDK invocation?

2. **Graphiti per-thread migration validation**: The GTP fixes changed the threading model. Did the fix work correctly?
   - Are there still cross-loop errors?
   - Did the per-thread factory create clients successfully?
   - Is graceful degradation still working?
   - Were there any hangs (the original bug)?

3. **Comparison with first run**:
   - First run: stalled indefinitely (cross-loop hang)
   - Second run: failed fast with `[Errno 24]` (~11 minutes total)
   - Is the `[Errno 24]` a direct consequence of creating more connections (per-thread clients)?
   - Or is it an independent issue that was masked by the hang in the first run?

4. **SP-004 success analysis**: SP-004 completed while SP-003 and SP-005 failed. Why?
   - Did SP-004 not use Graphiti context? (Check if `enable_context` was active)
   - Did SP-004 run first and consume fewer file descriptors?
   - Is the failure timing-dependent (race condition for FDs)?

## Acceptance Criteria

- [ ] Categorise all errors in the output log (Graphiti, file descriptor, SDK, other)
- [ ] Determine root cause of `[Errno 24] Too many open files`
- [ ] Assess whether the per-thread Graphiti migration (GTP fixes) is working correctly
- [ ] Determine if per-thread clients are contributing to FD exhaustion
- [ ] Check for cross-loop errors (should be gone after GTP1)
- [ ] Check for unawaited coroutine warnings (should be gone after GTP3)
- [ ] Verify defensive timeout is in place (GTP4)
- [ ] Compare with first run findings from TASK-REV-2AA0
- [ ] Provide fix recommendations with priority ordering
- [ ] Assess whether the system `ulimit` needs adjusting for parallel AutoBuild

## Key Files to Investigate

### AutoBuild Output
- `docs/reviews/system_understanding/system_plan_2.md` — Second AutoBuild run log (1,322 lines)

### Previous Review
- `.claude/reviews/TASK-REV-2AA0-review-report.md` — First run analysis (cross-loop hang, BUG-1/BUG-2)

### GTP Fix Implementation (FEAT-C90E)
- `guardkit/knowledge/graphiti_client.py` — `GraphitiClientFactory`, per-thread storage
- `guardkit/orchestrator/autobuild.py` — Per-thread loader, capture_turn_state fix, thread cleanup
- `guardkit/orchestrator/feature_orchestrator.py` — Defensive timeout, wave execution
- `guardkit/orchestrator/progress.py` — Timeout status display

### Feature Definition
- `.guardkit/features/FEAT-6EDD.yaml` — Task results showing SP-003/SP-005 failures

### GTP Task Definitions (for reference)
- `tasks/completed/TASK-FIX-GTP1/TASK-FIX-GTP1-client-factory.md`
- `tasks/completed/TASK-FIX-GTP2/TASK-FIX-GTP2-autobuild-migration.md`
- `tasks/backlog/graphiti-per-thread/TASK-FIX-GTP3-fix-capture-turn-state.md`
- `tasks/backlog/graphiti-per-thread/TASK-FIX-GTP4-wave-timeout.md`
- `tasks/completed/TASK-FIX-GTP5/TASK-FIX-GTP5-call-site-migration.md`
- `tasks/completed/TASK-DOC-GTP6/TASK-DOC-GTP6-documentation-update.md`

## Context

- Feature: FEAT-6EDD (Build /system-plan command)
- Previous review: TASK-REV-2AA0 (first run — Graphiti cross-loop hang)
- Fix feature: FEAT-C90E (Graphiti per-thread migration — all 6 tasks completed)
- Run duration: ~11 minutes (12:00:33 → 12:21:25)
- Results: 3 completed (SP-001, SP-002, SP-004), 2 failed (SP-003, SP-005), 3 pending (SP-006-008)

## Implementation Notes

Review completed. Report at: `.claude/reviews/TASK-REV-B9E1-review-report.md`

### Key Findings
1. **Root cause**: macOS `maxfiles` soft limit = 256 FDs, insufficient for 3 parallel AutoBuild tasks
2. **GTP fixes working**: Per-thread Graphiti migration eliminated the cross-loop hang from run 1
3. **Per-thread clients**: Marginal FD impact (+24-48 FDs), not primary cause
4. **No cross-loop hangs**: Only 2 isolated cross-loop errors (vs 159 in run 1), both gracefully degraded
5. **SP-004 succeeded**: Completed before FD exhaustion reached checkpoint code

### Fix Recommendations (with implementation tasks)
- **P0 (Critical)**: Raise FD limit to 4096 via `resource.setrlimit()` → **TASK-FIX-FD01**
- **P1 (High)**: Unify capture_turn_state client storage (BUG-3: dual storage) → **TASK-FIX-FD02**
- **P2 (Medium)**: Pre-initialize Graphiti factory before parallel dispatch (BUG-4: race condition) → **TASK-FIX-FD03**
- **P3 (Low)**: Suppress Neo4j retry storm during FD exhaustion (deferred — P0 mitigates)
- **P4 (Cosmetic)**: Fix unawaited coroutine warning in error path → **TASK-FIX-FD04**

### Implementation Tasks
- `tasks/backlog/parallel-execution-fixes/TASK-FIX-FD01-raise-fd-limit.md` — Raise FD soft limit (complexity: 2)
- `tasks/backlog/parallel-execution-fixes/TASK-FIX-FD02-unify-client-storage.md` — Fix dual client storage (complexity: 4)
- `tasks/backlog/parallel-execution-fixes/TASK-FIX-FD03-preinit-factory.md` — Pre-init factory (complexity: 2)
- `tasks/backlog/parallel-execution-fixes/TASK-FIX-FD04-unawaited-coroutine.md` — Fix coroutine warning (complexity: 2)

All tasks are independent and can be executed in parallel (Wave 1). After all 4 are complete, re-run FEAT-6EDD.

## Test Execution Log

[Automatically populated by /task-review]
