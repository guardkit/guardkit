---
id: TASK-SPR-5399
title: Reset circuit breaker between seeding categories
status: completed
task_type: implementation
created: 2026-03-05T12:00:00Z
completed: 2026-03-05T14:00:00Z
priority: high
complexity: 4
parent_review: TASK-REV-F404
feature_id: FEAT-SPR
tags: [graphiti, circuit-breaker, seeding, falkordb]
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-SPR-5399/
---

# Task: Reset circuit breaker between seeding categories

## Problem

The circuit breaker in `GraphitiClient` trips after 3 consecutive `_record_failure()` calls and blocks ALL subsequent `_create_episode()` calls. In the seeding pipeline, this creates a **cascade**: when rules (72 episodes) triggers 3 consecutive 180s timeouts, the circuit breaker trips and silently skips the remaining ~68 rules + all subsequent categories (project_overview, project_architecture).

The 60s half-open auto-reset is insufficient because:
- Categories are processed sequentially and rapidly (circuit-breaker-blocked episodes return instantly)
- The breaker trips within one category but cascades to ALL subsequent categories

### Evidence (from TASK-REV-F404 review)

```
Seeded rules: 1/72 episodes (71 skipped)      <- circuit breaker tripped after 3 timeouts
Seeded project_overview: 0/3 episodes (3 skipped)   <- cascade victim
Seeded project_architecture: 0/3 episodes (3 skipped)  <- cascade victim
```

### Root Cause (validated by sequence diagrams in Appendix C-D of review report)

`client.enabled` does NOT check circuit breaker — only `_check_circuit_breaker()` inside `_create_episode()` does. So `_add_episodes()` enters its loop (because `enabled=True`), iterates all episodes, and each gets individually blocked at `_create_episode()` level.

## Solution

Implemented Approach A: Orchestrator-level reset.

### Changes Made

1. **`guardkit/knowledge/graphiti_client.py`** — Added `reset_circuit_breaker()` method
2. **`guardkit/knowledge/seeding.py`** — Added `client.reset_circuit_breaker()` call before each category
3. **`tests/knowledge/test_graphiti_client.py`** — Added 5 tests in `TestCircuitBreakerReset`
4. **`tests/knowledge/test_seeding.py`** — Added 2 integration tests for cascade prevention

## Acceptance Criteria

- [x] Circuit breaker resets between seeding categories
- [x] Failures in one category do NOT cascade to subsequent categories
- [x] Circuit breaker still protects within a single category (3 consecutive failures)
- [x] Existing tests pass
- [x] New tests cover reset behavior
