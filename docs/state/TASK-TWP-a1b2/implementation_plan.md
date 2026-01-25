# Implementation Plan: TASK-TWP-a1b2

## Task
Enforce documentation level constraints in agent invocations

## Summary
Add post-invocation validation to ensure agents respect the `max_files` constraint based on `documentation_level`. Currently there is no validation after agent completion.

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/agent_invoker.py` | Add constant, validation method, integrate into invoke flow |
| `tests/unit/test_agent_invoker.py` | Add tests for constraint validation |

## Implementation Phases

### Phase 1: Add Constants
- Add `DOCUMENTATION_LEVEL_MAX_FILES` dictionary mapping level to max files
- minimal: 2, standard: 2, comprehensive: None (unlimited)

### Phase 2: Add Validation Method
- Add `_validate_file_count_constraint()` method
- Takes task_id, documentation_level, files_created
- Returns True if valid, False if violated
- Logs warning on violation

### Phase 3: Integrate Validation
- Call validation after task_work_results are written
- Pass documentation_level through call chain (default: "minimal")

### Phase 4: Add Unit Tests
- Test minimal level allows 2 files
- Test minimal level warns on 3+ files
- Test comprehensive level unlimited

## Estimates
- Duration: ~2 hours
- LOC: ~60 lines (implementation + tests)
- Risk: Low (warning-only, no breaking changes)

## Test Strategy
1. Unit tests for validation method
2. Unit tests for warning logging
3. Verify constant mapping correctness
