---
id: TASK-ASF-002
title: Add pre-flight FalkorDB connectivity check before autobuild
task_type: feature
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: high
status: completed
completed: 2026-02-15T00:00:00Z
tags: [autobuild, stall-fix, R2, phase-1, graphiti]
---

# Task: Add pre-flight FalkorDB connectivity check before autobuild

## Description

Add a pre-flight connectivity check for FalkorDB/Graphiti before autobuild launches. During the FEAT-AC1A run, FalkorDB at `whitestocks:6379` became unreachable mid-run (Turn 4+), adding 5-10 seconds of retry latency per context load without providing value. The Graphiti client degrades gracefully (returns empty context) but the retry cycles waste time.

Additionally, this addresses the newly identified **ghost thread interference** issue (Q8 from diagnostic diagrams): when Feature N fails and its ghost thread keeps running, that thread continues hitting Graphiti, consuming connection pool slots and API credits. A pre-flight check ensures the infrastructure is healthy before committing resources.

## Root Cause Addressed

- **F6**: Graphiti connection loss added latency without value
- **Q8** (new from diagrams): Ghost thread interference across features — ghost threads consume Graphiti connection pool

## Acceptance Criteria

- [x] Pre-flight check runs FalkorDB ping before first wave
- [x] If FalkorDB is unreachable, Graphiti context loading is disabled for the entire run
- [x] Warning logged when FalkorDB connectivity check fails
- [x] Autobuild proceeds without Graphiti (graceful degradation, not a blocker)
- [x] Pre-flight check completes within 5 seconds

## Implementation Summary

### Files Modified

1. **`guardkit/orchestrator/feature_orchestrator.py`**
   - Added `_preflight_check()` method (lines 929-1000)
   - Updated `_wave_phase()` to call preflight before `_pre_init_graphiti()` (line 1054)

2. **`tests/unit/test_feature_orchestrator.py`**
   - Added `TestPreflightCheck` class with 11 test cases

### Design Decisions

- **Synchronous method with async event loop**: `_wave_phase()` is synchronous, so `_preflight_check()` uses `asyncio.new_event_loop()` to run the async health check without nesting `asyncio.run()`.
- **No changes to autobuild.py**: Existing `enable_context` plumbing propagates the disabled flag to child AutoBuildOrchestrator instances via `_execute_task()`.
- **Conservative error handling**: All failure paths (timeout, exception, health check failure) disable Graphiti rather than blocking the build.

### Test Coverage

11 tests covering: context-disabled no-op, null client, disabled client, health success, health failure, timeout, exception, logging (info + warning), call ordering, and context propagation.

## Regression Risk

**Low** — Additive pre-flight check. Disables Graphiti when infrastructure is down (same behavior as existing graceful degradation, but without retry latency).

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 6, Recommendation R2)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 7, Q8)
