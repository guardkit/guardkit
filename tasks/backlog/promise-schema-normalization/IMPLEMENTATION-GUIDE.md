# Implementation Guide: Promise Schema Normalization

## Wave Breakdown

### Wave 1: Defensive Normalization (P0 - Unblocks FEAT-M2P resume)

Execute TASK-PSN-001 and TASK-PSN-002 in parallel.

**TASK-PSN-001** (direct mode, complexity 2):
- File: `guardkit/orchestrator/quality_gates/coach_validator.py` (~line 2273)
- File: `guardkit/orchestrator/schemas.py` (~line 156)
- Change: Add `or p.get("ac_id", "")` fallback in promise map construction
- Change: Add `or data.get("ac_id", "")` fallback in CompletionPromise.from_dict()
- Tests: Add test cases for `ac_id` field in test_schemas.py and test_coach_validator.py

**TASK-PSN-002** (direct mode, complexity 2):
- File: `guardkit/orchestrator/schemas.py` (~line 148)
- File: `guardkit/orchestrator/quality_gates/coach_validator.py` (~line 2284)
- Change: Add STATUS_ALIASES map, normalize before enum construction and comparison
- Tests: Add test cases for "done" status in test_schemas.py and test_coach_validator.py

**After Wave 1**:
```bash
# In specialist-agent repo:
guardkit autobuild feature FEAT-M2P --resume
```

### Wave 2: Root Cause Prevention (P1)

**TASK-PSN-003** (task-work mode, complexity 4):
- File: `guardkit/orchestrator/agent_invoker.py`
- Change: Inject format reminder when SDK turn count >= 80% of max
- Investigation: Determine whether runtime injection is possible or if initial prompt strengthening is needed

## Files Modified

| File | TASK-PSN-001 | TASK-PSN-002 | TASK-PSN-003 |
|------|-------------|-------------|-------------|
| `orchestrator/schemas.py` | field fallbacks | status aliases | - |
| `orchestrator/quality_gates/coach_validator.py` | key fallback | status normalization | - |
| `orchestrator/agent_invoker.py` | - | - | format reinforcement |
| `tests/unit/test_schemas.py` | new tests | new tests | - |
| `tests/unit/test_coach_validator.py` | new tests | new tests | - |

No file conflicts between Wave 1 tasks — safe for parallel execution.
