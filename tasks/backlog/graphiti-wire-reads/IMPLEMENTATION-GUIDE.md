# Implementation Guide: Wire Disconnected Graphiti Reads (FEAT-GWR)

## Execution Strategy

### Wave 1: Dead Code Removal (1 task)

**TASK-GWR-001**: Remove dead quality gate config from Graphiti (PATH 10)

- **Method**: `/task-work TASK-GWR-001`
- **Type**: Pure deletion — no new code
- **Files affected**:
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (remove dead methods + import block)
  - `guardkit/knowledge/quality_gate_queries.py` (delete entire file)
  - `guardkit/knowledge/seed_quality_gate_configs.py` (delete entire file)
  - `guardkit/knowledge/seeding.py` (remove quality_gate_configs entry)
- **Validation**: `pytest tests/unit/test_coach_validator.py -v`
- **Risk**: Low — removing confirmed dead code

### Wave 2: Wire Reads (2 tasks, parallelizable)

These tasks can run in parallel since they touch different files.

**TASK-GWR-002**: Wire coach context into CoachValidator.validate()

- **Method**: `/task-work TASK-GWR-002`
- **Files affected**:
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (add `context` param)
  - `guardkit/orchestrator/autobuild.py` (pass `context_prompt` to `validate()`)
- **Key change**: `_invoke_coach_safely()` already retrieves `context_prompt` at line 2967 — just needs to pass it through at lines 3010-3018
- **Validation**: `pytest tests/unit/test_coach_validator.py -v`

**TASK-GWR-003**: Wire outcome reads and turn continuation into AutoBuild

- **Method**: `/task-work TASK-GWR-003`
- **Files affected**:
  - `guardkit/knowledge/autobuild_context_loader.py` (call `load_turn_continuation_context()` for turn > 1)
- **Key change**: `load_turn_continuation_context()` already exists in `turn_state_operations.py:123` and is fully implemented — just never called
- **Also**: Round-trip verification test for `JobContextRetriever` -> `task_outcomes` path (already wired, needs test)
- **Validation**: `pytest tests/unit/test_autobuild_context_loader.py -v`

## Execution Order

```
Wave 1:  TASK-GWR-001 (dead code removal)
              |
         _____|_____
        |           |
Wave 2: GWR-002   GWR-003   (parallel)
        |           |
        |___________|
              |
        Measurement Phase
```

## Post-Implementation: Measurement Protocol

After all 3 tasks complete:

1. Run 3-5 AutoBuild tasks **with** Graphiti enabled
2. Run same tasks **without** Graphiti (or with reads disabled)
3. Compare:
   - Coach feedback quality (subjective)
   - Turn count to completion
   - Context size and relevance
4. Log analysis: grep for `[Graphiti]` structured log messages
5. Decision: Keep investing, simplify further, or deprecate

## Key Code References

| Component | File | Lines |
|-----------|------|-------|
| Coach context retrieval | `autobuild.py` | 2967 |
| Coach validate() call | `autobuild.py` | 3010-3018 |
| CoachValidator.validate() | `coach_validator.py` | ~200 |
| Dead quality gate methods | `coach_validator.py` | 355, 501 |
| Turn state write | `turn_state_operations.py` | 108-113 |
| Turn state read (unused) | `turn_state_operations.py` | 183-186 |
| Outcome write | `outcome_manager.py` | 156 |
| Outcome read (wired) | `job_context_retriever.py` | 808-814 |
| Seeding categories | `seeding.py` | 150-168 |

## Group ID Reference

| Path | Group ID | Write Location | Read Location |
|------|----------|----------------|---------------|
| Turn states | `"turn_states"` | turn_state_operations.py:111 | turn_state_operations.py:185 |
| Task outcomes | `"task_outcomes"` | outcome_manager.py:156 | job_context_retriever.py:810 |
| Quality gate configs | `"quality_gate_configs"` | seed_quality_gate_configs.py | coach_validator.py (DEAD) |
