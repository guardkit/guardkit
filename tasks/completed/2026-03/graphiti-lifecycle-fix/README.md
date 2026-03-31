# FEAT-408A: Graphiti Event Loop Lifecycle Fix

## Source

- Review: `TASK-REV-50E1` — AutoBuild Run 4 Error Analysis (Revised)
- Report: `.claude/reviews/TASK-REV-50E1-review-report.md`
- Run log: `docs/reviews/autobuild-fixes/run_4_success_with_errors.md`

## Problem Statement

AutoBuild Run 4 for FEAT-AC1A completed successfully (11/11 tasks, 43m 35s) but produced ~53 error/warning lines caused by Graphiti/FalkorDB async event loop lifecycle mismanagement. Three distinct issues were identified through deep source code analysis:

1. **Event loop contamination**: `GraphitiClientFactory.get_thread_client()` creates temporary loops for client initialization, leaving FalkorDB driver Locks bound to dead loops
2. **Missing `enable_context` guard**: `_capture_turn_state()` fires Graphiti ops even when context is disabled, producing 11 unnecessary errors per run
3. **Direct mode report gap**: SDK direct mode doesn't produce `player_turn_N.json`, causing false "report not found" errors and wasting turns

## Wave Execution Plan

### Wave 1: Quick Wins (parallel, ~1 hour total)

| Task | Type | Complexity | Mode | Description |
|------|------|------------|------|-------------|
| TASK-GLF-001 | fix | 2 | direct | Add `enable_context` guard to `_capture_turn_state` |
| TASK-GLF-002 | fix | 2 | direct | Add `shutting_down` flag to suppress shutdown errors |

### Wave 2: Core Fixes (parallel, requires Wave 1)

| Task | Type | Complexity | Mode | Description |
|------|------|------------|------|-------------|
| TASK-GLF-003 | refactor | 6 | task-work | Lazy Graphiti client initialization in consumer's loop |
| TASK-GLF-004 | fix | 5 | task-work | Fix direct mode Player report generation |

### Wave 3: Hardening (requires Wave 2)

| Task | Type | Complexity | Mode | Description |
|------|------|------------|------|-------------|
| TASK-GLF-005 | refactor | 4 | task-work | Lightweight health check without full client init |

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Mid-run errors per task | ~3 | 0 |
| Shutdown errors | ~20 | 0 |
| Total error lines | ~53 | 0 |
| Wasted turns (direct mode) | 1 per task | 0 |

## Architecture Impact

- **Modified files**: `graphiti_client.py`, `autobuild.py`, `agent_invoker.py`, `feature_orchestrator.py`
- **No new dependencies**
- **No API changes** — all fixes are internal lifecycle improvements
- **Backward compatible** — existing behavior preserved, errors eliminated
