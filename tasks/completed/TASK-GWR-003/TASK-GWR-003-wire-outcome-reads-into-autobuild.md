---
id: TASK-GWR-003
title: Wire outcome reads and turn continuation into AutoBuild context
status: completed
completed: 2026-02-15T14:00:00Z
updated: 2026-02-15T14:00:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria verified, tests pass, implementation validated"
completed_location: tasks/completed/TASK-GWR-003/
created: 2026-02-14T10:30:00Z
priority: high
tags: [graphiti, autobuild, cross-turn-learning, outcomes]
parent_review: TASK-REV-GROI
feature_id: FEAT-GWR
implementation_mode: task-work
wave: 2
complexity: 5
task_type: feature
depends_on:
  - TASK-GWR-001
---

# Task: Wire Outcome Reads and Turn Continuation Into AutoBuild Context

## Description

The TASK-REV-GROI review identified that AutoBuild diligently captures turn states (1-5 per run) and task outcomes, but **never reads them back**. Two fully-implemented read functions exist but aren't called:

1. `load_turn_continuation_context()` — reads previous turn state for cross-turn learning
2. `find_similar_task_outcomes()` — searches for similar past outcomes

This task wires the reads so captured data actually informs future turns.

## The Disconnection

### Turn Continuation (cross-turn learning)
- **Write**: `_capture_turn_state()` in `autobuild.py:1516` writes to `"turn_states"` group every turn
- **Read**: `load_turn_continuation_context()` in `turn_state_operations.py:123` reads from `"turn_states"` — NEVER CALLED
- **Missing wire**: `AutoBuildContextLoader.get_player_context()` doesn't call continuation for turn > 1

### Similar Outcomes (cross-task learning)
- **Write**: `capture_task_outcome()` in `outcome_manager.py` writes to `"task_outcomes"` group
- **Read**: `JobContextRetriever` queries `"task_outcomes"` with 25% budget allocation (lines 808-814)
- **Status**: Already wired in `JobContextRetriever` — verify with round-trip test

## Implementation

### Step 1: Verify `JobContextRetriever` queries `task_outcomes` (already wired)

File: `guardkit/knowledge/job_context_retriever.py`

The review confirmed that `JobContextRetriever.retrieve()` already queries the `task_outcomes` group (line 810):
```python
self._query_category(
    query=description,
    group_ids=["task_outcomes"],
    budget_allocation=budget.get_allocation("similar_outcomes"),
    ...
)
```

**Verification needed**: Write a test that:
1. Captures a task outcome via `capture_task_outcome()`
2. Calls `JobContextRetriever.retrieve()` with a matching description
3. Confirms `RetrievedContext.similar_outcomes` contains the captured outcome

If this round-trip works, no code change needed for this sub-path.

### Step 2: Wire `load_turn_continuation_context()` for turn > 1

File: `guardkit/knowledge/autobuild_context_loader.py`

In `get_player_context()`, after the existing `retriever.retrieve()` call (~line 206-210), add turn continuation for turn > 1:

```python
# After existing context retrieval (line 210):
context = await self.retriever.retrieve(
    task=task,
    phase=TaskPhase.IMPLEMENT,
    collect_metrics=self.verbose,
)

# NEW: Load turn continuation context for turn > 1
if turn_number > 1 and self.graphiti is not None:
    try:
        from guardkit.knowledge.turn_state_operations import load_turn_continuation_context
        continuation = await load_turn_continuation_context(
            graphiti_client=self.graphiti,
            feature_id=feature_id,
            task_id=task_id,
            current_turn=turn_number,
        )
        if continuation:
            logger.info(
                "[Graphiti] Turn continuation loaded: %d chars for turn %d",
                len(continuation), turn_number,
            )
            # Append continuation to context prompt
            # The continuation is already formatted markdown from turn_state_operations
    except Exception as e:
        logger.warning(f"Failed to load turn continuation context: {e}")
```

**Integration with AutoBuildContextResult**: The `_build_result()` method formats `RetrievedContext.to_prompt()` into `prompt_text`. Add the continuation text as an additional section appended after the main context.

### Step 3: Add observability logging

In `get_player_context()`:
```
[Graphiti] Turn continuation loaded: {len} chars for turn {N}
[Graphiti] Similar outcomes found: {count} matches
```

In `get_coach_context()`:
```
[Graphiti] Coach context categories: {categories}
```

## Group ID Consistency (Verified)

| Path | Write Group ID | Read Group ID | Status |
|------|---------------|---------------|--------|
| Turn states | `"turn_states"` (turn_state_operations.py:111) | `"turn_states"` (turn_state_operations.py:185) | Consistent |
| Task outcomes | `"task_outcomes"` (outcome_manager.py:156) | `"task_outcomes"` (job_context_retriever.py:810) | Consistent |

## Acceptance Criteria

- [x] AC-F2-01: `AutoBuildContextLoader.get_player_context()` calls `load_turn_continuation_context()` for turn > 1
- [x] AC-F2-02: Turn continuation context is included in the Player prompt text when available
- [x] AC-F2-03: `get_player_context()` for turn 1 does NOT call continuation (no previous turn)
- [x] AC-F2-04: Graceful degradation when no prior turn states exist (None returned, no errors)
- [x] AC-F2-05: Graceful degradation when Graphiti client is None or disabled
- [x] AC-F2-06: `JobContextRetriever` round-trip test: capture outcome → retrieve → found in similar_outcomes
- [x] AC-F2-07: Structured logging for turn continuation and similar outcomes

## Tests Required

- `tests/unit/test_autobuild_context_loader.py`: Test `get_player_context(turn_number=2)` calls `load_turn_continuation_context()`
- `tests/unit/test_autobuild_context_loader.py`: Test `get_player_context(turn_number=1)` does NOT call continuation
- `tests/unit/test_autobuild_context_loader.py`: Test graceful degradation when continuation returns None
- `tests/unit/test_autobuild_context_loader.py`: Test graceful degradation when Graphiti unavailable
- `tests/unit/test_outcome_queries.py` or `tests/unit/test_job_context_retriever.py`: Round-trip test for outcome capture → retrieval

## Implementation Notes

- `load_turn_continuation_context()` returns formatted markdown or None — check `turn_state_operations.py:200+` for format
- The continuation includes: previous turn summary, player/coach decisions, blockers, files modified
- Import `load_turn_continuation_context` lazily inside the method to avoid circular imports
- `AutoBuildContextResult.prompt_text` is the final injection point — append continuation there
