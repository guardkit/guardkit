# REVISE: Graphiti ROI — Connect the Wires

**Review**: TASK-REV-GROI
**Decision**: [R]evise
**Rationale**: The review correctly identifies disconnected read paths, but recommends mass deprecation before testing whether connecting those reads delivers value. This revision takes the "connect, measure, then decide" approach.

---

## Problem Statement

The review identified three critical disconnections that make Graphiti appear to deliver zero value when it's actually 80% built with the last 20% (the read wiring) missing:

1. **Coach context assembled but never consumed** — `validate_with_graphiti_thresholds()` builds `arch_context` but `validate()` ignores it
2. **Outcome capture writes every turn but reads are never called** — `find_similar_task_outcomes()` and `load_turn_continuation_context()` exist but aren't wired into the AutoBuild loop
3. **Coach context_prompt retrieved but discarded** — `_invoke_coach_safely` retrieves context via `thread_loader.get_coach_context()` but never passes it to `CoachValidator`

---

## Scope & Constraints

**IN SCOPE**: Wire the 3 disconnected read paths. Add observability to measure impact. Remove confirmed dead code (PATH 10: quality gate config from Graphiti).

**OUT OF SCOPE**: Mass deprecation of seed infrastructure, feature-plan context changes, new Graphiti features.

**Testing**: Each wire-up must have unit tests proving the data flows end-to-end. Integration testing via 3-5 real AutoBuild runs before/after.

---

## Fix 1: Wire Coach Context Into Validation

### The Disconnection

In `guardkit/orchestrator/quality_gates/coach_validator.py`:

```python
# Line ~547-574 in validate_with_graphiti_thresholds():
arch_context = await build_coach_context(...)
# ...
# Note: arch_context is built but not currently used in the validation flow
# It's available for future enhancement of validation prompts or logging
return self.validate(task_id=task_id, turn=turn, task=task, ...)
```

The `validate()` method signature has no `context` parameter. And `_invoke_coach_safely()` in `autobuild.py` calls `validator.validate()` directly, never `validate_with_graphiti_thresholds()`.

Additionally, `_invoke_coach_safely()` retrieves `context_prompt` via `thread_loader.get_coach_context()` but this value is never passed anywhere — it's simply discarded after logging.

### The Fix

**Step 1**: Add `context` parameter to `CoachValidator.validate()`

File: `guardkit/orchestrator/quality_gates/coach_validator.py`

Add an optional `context: Optional[str] = None` parameter to `validate()`. Store it on the result object so it's available for logging and future prompt injection.

```python
def validate(
    self,
    task_id: str,
    turn: int,
    task: Dict[str, Any],
    skip_arch_review: bool = False,
    context: Optional[str] = None,  # NEW: Graphiti context for enhanced validation
) -> CoachValidationResult:
```

Where context is used:
- Include it in the `rationale` field when present (so Coach decisions are traceable to the context that informed them)
- Log it at DEBUG level for observability
- Pass it through to `CoachValidationResult` via a new optional `context_used: Optional[str]` field

This is the minimal wire-up. The context doesn't need to change the approve/feedback decision logic yet — just making it visible and traceable is the first step.

**Step 2**: Pass `context_prompt` from `_invoke_coach_safely()` to `validator.validate()`

File: `guardkit/orchestrator/autobuild.py`

In `_invoke_coach_safely()`, the `context_prompt` variable is already populated by `thread_loader.get_coach_context()`. Currently it's discarded. Change:

```python
# CURRENT (around line where CoachValidator is used):
validation_result = validator.validate(
    task_id=task_id,
    turn=turn,
    task={
        "acceptance_criteria": acceptance_criteria or [],
        "task_type": task_type,
    },
    skip_arch_review=skip_arch_review,
)

# CHANGE TO:
validation_result = validator.validate(
    task_id=task_id,
    turn=turn,
    task={
        "acceptance_criteria": acceptance_criteria or [],
        "task_type": task_type,
    },
    skip_arch_review=skip_arch_review,
    context=context_prompt if context_prompt else None,  # NEW
)
```

**Step 3**: Remove the dead `validate_with_graphiti_thresholds()` method

This async method tried to do what we're now doing properly via the `_invoke_coach_safely` → `validate(context=...)` path. It duplicates logic and its `get_graphiti_thresholds()` query path is confirmed dead (PATH 10). Remove the entire method and the `get_graphiti_thresholds()` static method.

### Tests Required

- `tests/unit/test_coach_validator.py`: Test that `validate(context="some context")` includes context in rationale and result
- `tests/unit/test_coach_validator.py`: Test that `validate(context=None)` works identically to current behavior (backward compat)
- `tests/unit/test_autobuild.py`: Verify `_invoke_coach_safely` passes context_prompt to validator

### Acceptance Criteria

- AC-F1-01: `CoachValidator.validate()` accepts optional `context` parameter
- AC-F1-02: When context is provided, it appears in `CoachValidationResult.rationale` (or new field)
- AC-F1-03: `_invoke_coach_safely` passes the retrieved `context_prompt` to `validator.validate()`
- AC-F1-04: When context retrieval fails/disabled, `validate()` still works (graceful degradation)
- AC-F1-05: `validate_with_graphiti_thresholds()` removed (dead code cleanup)

---

## Fix 2: Wire Outcome Reads Into AutoBuild Context

### The Disconnection

In `guardkit/knowledge/outcome_queries.py`:
- `find_similar_task_outcomes()` — fully implemented, searches `task_outcomes` group
- **Never called from anywhere in the AutoBuild flow**

In `guardkit/knowledge/turn_state_operations.py`:
- `load_turn_continuation_context()` — fully implemented
- **Never called from autobuild.py**

Meanwhile, `_capture_turn_state()` in `autobuild.py` diligently writes 1-5 episodes per run. All writes, no reads.

### The Fix

The cleanest integration point is `AutoBuildContextLoader` which already retrieves context for both Player and Coach. The `JobContextRetriever` already has a `task_outcomes` budget allocation (25%).

**Step 1**: Verify `JobContextRetriever` actually queries `task_outcomes`

File: `guardkit/knowledge/job_context_retriever.py`

Check whether the `similar_outcomes` category in `RetrievedContext` is populated. The budget allocation exists (the review mentions 25%) but we need to confirm the query actually fires. Search for where `find_similar_task_outcomes` or `task_outcomes` group_id is used within `JobContextRetriever.retrieve()`.

If the query IS already wired in `JobContextRetriever` but just returning empty results (because the `task_outcomes` group has no data from prior runs), then this fix becomes: **verify the write path in `_capture_turn_state` uses group_id `task_outcomes`** and **run a test task to confirm round-trip**.

If the query is NOT wired, add it:

```python
# In JobContextRetriever.retrieve(), within the outcomes budget section:
if budget.outcomes_budget > 0:
    outcomes = await find_similar_task_outcomes(
        task_requirements=task["description"],
        limit=3,
    )
    context.similar_outcomes = outcomes
```

**Step 2**: Wire `load_turn_continuation_context()` for turn N > 1

File: `guardkit/knowledge/autobuild_context_loader.py`

In `get_player_context()`, when `turn_number > 1`, call `load_turn_continuation_context()` to give the Player knowledge of what happened in previous turns. This is the cross-turn learning the review says is missing.

```python
# In get_player_context(), after basic context retrieval:
if turn_number > 1:
    try:
        continuation = await load_turn_continuation_context(
            graphiti_client=self.graphiti,
            feature_id=feature_id,
            task_id=task_id,
            current_turn=turn_number,
        )
        if continuation:
            # Append to context under a "Previous Turn Context" section
            context.turn_continuation = continuation
    except Exception as e:
        logger.warning(f"Failed to load turn continuation context: {e}")
```

**Step 3**: Verify `_capture_turn_state` group_id matches `task_outcomes`

File: `guardkit/knowledge/turn_state_operations.py`

Confirm that `capture_turn_state()` writes to the same group_id that `find_similar_task_outcomes()` reads from (`task_outcomes`). If there's a group_id mismatch (e.g., writing to `turn_states` but reading from `task_outcomes`), fix it.

Also check `guardkit/knowledge/entities/turn_state.py` for the `TurnStateEntity` to see what group_id it uses.

### Tests Required

- `tests/unit/test_outcome_queries.py`: Verify `find_similar_task_outcomes` returns results when task_outcomes group has data
- `tests/unit/test_autobuild_context_loader.py`: Verify `get_player_context` calls `load_turn_continuation_context` when turn > 1
- `tests/unit/test_autobuild_context_loader.py`: Verify `get_player_context` skips continuation for turn 1
- `tests/unit/test_turn_state_operations.py`: Verify round-trip: capture → query returns matching data

### Acceptance Criteria

- AC-F2-01: `JobContextRetriever` queries `task_outcomes` group and returns results when data exists
- AC-F2-02: `AutoBuildContextLoader.get_player_context()` calls `load_turn_continuation_context()` for turn > 1
- AC-F2-03: Turn continuation context is included in Player prompt when available
- AC-F2-04: Group IDs are consistent between write (`capture_turn_state`) and read (`find_similar_task_outcomes`) paths
- AC-F2-05: Graceful degradation when no prior outcomes exist (empty results, not errors)

---

## Fix 3: Remove Confirmed Dead Code (PATH 10)

### What to Remove

The review conclusively proved PATH 10 (Quality Gate Config from Graphiti) is dead code:

- `get_graphiti_thresholds()` static method in `coach_validator.py` — queries `quality_gate_configs` group that nobody reads in production
- `validate_with_graphiti_thresholds()` async method in `coach_validator.py` — never called from autobuild.py
- `guardkit/knowledge/quality_gate_queries.py` — provides `get_quality_gate_config()` that is only imported conditionally and never actually used
- `guardkit/knowledge/seed_quality_gate_configs.py` — seeds data nobody reads

### The Fix

**Step 1**: Remove `get_graphiti_thresholds()` and `validate_with_graphiti_thresholds()` from `coach_validator.py`

Also remove the conditional imports at the top:
```python
# REMOVE these blocks:
try:
    from guardkit.knowledge.quality_gate_queries import get_quality_gate_config
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    get_quality_gate_config = None
```

**Step 2**: Delete `guardkit/knowledge/quality_gate_queries.py`

**Step 3**: Remove `quality_gate_configs` from the seeding orchestrator category list

File: `guardkit/knowledge/seeding.py` — remove `quality_gate_configs` from the categories in `seed_all_system_context()`.

**Step 4**: Delete `guardkit/knowledge/seed_quality_gate_configs.py`

### Tests Required

- Verify existing `test_coach_validator.py` tests still pass after removal
- Verify `guardkit graphiti seed` still works without the removed category

### Acceptance Criteria

- AC-F3-01: `quality_gate_queries.py` deleted
- AC-F3-02: `seed_quality_gate_configs.py` deleted
- AC-F3-03: `get_graphiti_thresholds()` and `validate_with_graphiti_thresholds()` removed from `coach_validator.py`
- AC-F3-04: `GRAPHITI_AVAILABLE` import block removed from `coach_validator.py`
- AC-F3-05: All existing coach_validator tests pass unchanged
- AC-F3-06: Seeding orchestrator no longer includes `quality_gate_configs`

---

## Observability: Before/After Measurement

### What to Log

Add structured logging to measure whether the connected reads improve outcomes:

**In `_invoke_coach_safely`** (after Fix 1):
```
[Graphiti] Coach context provided: {len(context_prompt)} chars, {categories_count} categories
```

**In `_capture_turn_state`** (existing, verify logging):
```
[Graphiti] Turn state captured: turn={turn}, decision={decision}, files={files_count}
```

**In `get_player_context`** (after Fix 2):
```
[Graphiti] Turn continuation loaded: {len(continuation)} chars for turn {turn_number}
[Graphiti] Similar outcomes found: {len(outcomes)} matches
```

### Before/After Test Protocol

Run 3-5 identical tasks (same requirements, same acceptance criteria) with:
1. **Before**: Current state (reads disconnected, writes-only)
2. **After**: With Fix 1 + Fix 2 applied

Measure:
- Turns to approval (fewer = better)
- Coach feedback quality (does context reduce false rejections?)
- Cross-turn learning (does turn 2 avoid repeating turn 1 mistakes?)

If there's no measurable improvement after 5 tasks, THEN proceed with the review's Option A deprecation. But not before testing.

---

## Implementation Order

1. **Fix 3** first (dead code removal) — cleanest, no risk, reduces noise
2. **Fix 1** second (Coach context wiring) — straightforward parameter threading
3. **Fix 2** third (outcome reads) — requires verifying group_id consistency
4. **Observability** — add logging alongside each fix
5. **Before/After testing** — run comparison tasks

**Estimated effort**: 1-2 days for all fixes + testing.

---

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Add `context` param to `validate()`, remove dead async methods, remove quality_gate imports |
| `guardkit/orchestrator/autobuild.py` | Pass `context_prompt` to `validator.validate()` |
| `guardkit/knowledge/autobuild_context_loader.py` | Wire `load_turn_continuation_context()` in `get_player_context()` for turn > 1 |
| `guardkit/knowledge/job_context_retriever.py` | Verify/wire `task_outcomes` query in retrieve() |
| `guardkit/knowledge/quality_gate_queries.py` | **DELETE** |
| `guardkit/knowledge/seed_quality_gate_configs.py` | **DELETE** |
| `guardkit/knowledge/seeding.py` | Remove `quality_gate_configs` from category list |
| `tests/unit/test_coach_validator.py` | Add context parameter tests, verify existing tests pass |
| `tests/unit/test_autobuild_context_loader.py` | Add turn continuation tests |

---

## Success Criteria (Overall)

- All 3 disconnected read paths are connected
- Dead code (PATH 10) removed
- All existing tests pass
- New unit tests cover the wire-ups
- Structured logging enables before/after comparison
- Ready for comparative testing (3-5 task runs)
