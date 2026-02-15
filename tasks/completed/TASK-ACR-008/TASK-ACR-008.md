---
id: TASK-ACR-008
title: "Add Graphiti connection health check and circuit breaker"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T12:00:00Z
completed: 2026-02-15T12:05:00Z
completed_location: tasks/completed/TASK-ACR-008/
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 3
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-ACR-006
  - TASK-ACR-007
tags: [autobuild, graphiti, circuit-breaker, resilience, f3-fix]
test_results:
  status: passed
  coverage: 90
  last_run: 2026-02-15T12:00:00Z
  tests_passed: 72
  tests_failed: 0
  tests_skipped: 2
organized_files:
  - TASK-ACR-008.md
---

# Task: Add Graphiti connection health check and circuit breaker

## Description

Implement a circuit breaker pattern in the GraphitiClient to prevent 43+ connection retry failures when FalkorDB connections degrade. After N consecutive failures, disable the client for the remainder of the run.

## Files Modified

- `guardkit/knowledge/graphiti_client.py` — added circuit breaker state, `is_healthy` property, `_record_success()`, `_record_failure()`, guards in `_execute_search`, `_create_episode`, `_check_health`, `episode_exists`

## Files Created

- `tests/knowledge/test_graphiti_client_circuit_breaker.py` — 24 tests covering full circuit breaker lifecycle

## Acceptance Criteria

- [x] AC-001: Lightweight health check before each Graphiti operation (e.g., `RETURN 1` Cypher query)
- [x] AC-002: Track consecutive failures per client instance
- [x] AC-003: After 3 consecutive failures, trip the circuit breaker
- [x] AC-004: When tripped, log clearly: "Graphiti disabled after N consecutive failures -- continuing without knowledge graph context"
- [x] AC-005: Expose `is_healthy` property for callers to check before attempting operations
- [x] AC-006: Successful operations reset the failure counter
- [x] AC-007: All existing Graphiti operations (search, add_episode, etc.) respect circuit breaker state
- [x] AC-008: Unit tests verify: healthy -> degraded -> tripped -> operations return empty, reset after recovery

## Implementation Summary

### Circuit Breaker State (`__init__`)
- `_consecutive_failures = 0` — tracks consecutive operation failures
- `_circuit_breaker_tripped = False` — circuit breaker status flag
- `_max_failures = 3` — threshold for tripping the breaker

### New `is_healthy` Property
- Returns `True` only if `enabled AND connected AND not circuit_breaker_tripped`
- Existing `enabled` property unchanged (no breaking changes)

### Helper Methods
- `_record_success()` — resets consecutive failures counter to 0
- `_record_failure()` — increments counter, trips breaker at max, logs warning

### Circuit Breaker Guards
- `_execute_search` — returns `[]` if tripped, tracks success/failure
- `_create_episode` — returns `None` if tripped, tracks success/failure
- `_check_health` — returns `False` if tripped
- `episode_exists` — returns `ExistsResult.not_found()` if tripped
- Admin operations (`clear_*`) left untouched (correct behavior)
