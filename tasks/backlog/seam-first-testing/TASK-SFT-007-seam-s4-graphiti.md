---
id: TASK-SFT-007
title: "Seam tests S4 \u2014 Python-to-Graphiti persistence wiring"
task_type: testing
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-SFT-001
priority: medium
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T21:22:24.039313'
  last_updated: '2026-02-15T21:27:37.989222'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-15T21:22:24.039313'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Seam Tests S4: Python → Graphiti Client Persistence

## Objective

Write seam tests verifying that Python code actually calls the Graphiti client for persistence — catching silent errors, false successes, and stubs where `add_episode()` is never called.

## Seam Definition

**Layer A**: Python orchestration (`SystemPlanGraphiti`, `graphiti_client.py`)
**Layer B**: Graphiti client library (`add_episode()`, `search()`, `close()`)

## Acceptance Criteria

- [ ] `tests/seam/test_graphiti_persistence.py` created
- [ ] Test: `SystemPlanGraphiti.upsert_component()` calls `add_episode()` with correct entity body
- [ ] Test: `SystemPlanGraphiti.upsert_system_context()` calls `add_episode()` with system context data
- [ ] Test: `upsert_adr()` produces a valid episode with ADR metadata
- [ ] Test: Search operations return results in expected format
- [ ] Test: Graphiti unavailable → graceful degradation (returns None/empty, no crash)
- [ ] Test: Connection error during `add_episode()` → logged warning, no exception raised to caller
- [ ] Tests use AsyncMock at the `graphiti_core` client level (not mocking GuardKit wrapper functions)
- [ ] All tests pass with `pytest tests/seam/test_graphiti_persistence.py -v`

## Implementation Notes

- The mock boundary is `graphiti_core.Graphiti` — mock this, let `SystemPlanGraphiti` run for real
- Verify `add_episode()` was called with `group_id` containing the project prefix
- Reference `guardkit/knowledge/graphiti_client.py` for client wrapper
- Reference `guardkit/planning/graphiti_arch.py` for `SystemPlanGraphiti`
