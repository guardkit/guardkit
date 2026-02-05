# Review Report: TASK-REV-AB04

## Executive Summary

The `'AgentInvoker' object has no attribute '_ensure_design_approved_state'` error has a definitive root cause: **commit `b8a827a6` ("add rate limit handling to autobuild, reviews and tasks") introduced a module-level function `detect_rate_limit()` in the middle of the `AgentInvoker` class body, causing 15 methods to become orphaned as nested functions inside `detect_rate_limit` instead of class methods.**

This is a structural indentation bug, not a missing method. The method exists in the source file at line 2817 but Python's parser assigns it (and 14 others) to the wrong scope.

## Review Details

- **Mode**: Architectural Review (root cause analysis)
- **Depth**: Standard
- **Task**: TASK-REV-AB04
- **Related**: TASK-FIX-AB01, TASK-FIX-AB02, TASK-FIX-AB03, TASK-REV-5796

## Findings

### Finding 1: Root Cause - Class Scope Break (CRITICAL)

**File**: `guardkit/orchestrator/agent_invoker.py`
**Commit**: `b8a827a6` ("add rate limit handling to autobuild, reviews and tasks")

**Before commit b8a827a6**:
- `AgentInvoker` class: lines 528-3187
- **40 methods** including `_ensure_design_approved_state`
- All methods properly scoped to the class

**After commit b8a827a6**:
- `AgentInvoker` class: lines 530-2302 (only **25 methods**)
- Module-level `detect_rate_limit()`: lines 2305-3261 (contains **15 orphaned methods**)

**Mechanism**: The `detect_rate_limit()` function was inserted at module level (zero indentation) at line 2305, between the `format_feedback_for_prompt` method (last real class method, ending at line 2302) and `_invoke_task_work_implement` (line 2333). Since `_invoke_task_work_implement` and all subsequent methods are indented at class-method level, Python's parser treats them as nested functions inside `detect_rate_limit()` rather than methods on `AgentInvoker`.

**AST verification**:
```
AgentInvoker class: line 530 to line 2302
  Last method: format_feedback_for_prompt at line 2234-2302

detect_rate_limit function: lines 2305-3261
  Nested: _invoke_task_work_implement (lines 2333-2565)
  Nested: _parse_task_work_output (lines 2567-2608)
  Nested: _parse_task_work_stream (lines 2610-2636)
  Nested: extract_acceptance_criteria (lines 2642-2720)
  Nested: _parse_criteria_from_body (lines 2722-2761)
  Nested: parse_completion_promises (lines 2763-2788)
  Nested: parse_criteria_verifications (lines 2790-2815)
  Nested: _ensure_design_approved_state (lines 2817-2858)    <-- THE ERROR
  Nested: _read_json_artifact (lines 2864-2895)
  Nested: _write_design_results (lines 2897-2947)
  Nested: _read_design_results (lines 2949-2969)
  Nested: _write_task_work_results (lines 2971-3096)
  Nested: _write_failure_results (lines 3098-3169)
  Nested: _generate_summary (lines 3171-3213)
  Nested: _validate_file_count_constraint (lines 3215-3261)
```

**Why it compiles without error**: Python allows nested function definitions inside functions. The `def _invoke_task_work_implement(self, ...)` syntax is valid Python - `self` is just a parameter name, it has no special meaning outside a class context. The file compiles cleanly but the methods are unreachable as class methods.

### Finding 2: Full Impact Assessment

**15 orphaned methods** are inaccessible on the `AgentInvoker` class:

| Method | Called From | Impact |
|--------|------------|--------|
| `_invoke_task_work_implement` | `invoke_player()` (task-work delegation path) | **BLOCKS** all task-work delegation |
| `_ensure_design_approved_state` | `invoke_player()` (task-work delegation path) | **BLOCKS** all task-work delegation |
| `_parse_task_work_output` | `_invoke_task_work_implement` | Task-work results parsing |
| `_parse_task_work_stream` | `_invoke_task_work_implement` | Stream parsing |
| `extract_acceptance_criteria` | Multiple callers | Criteria extraction |
| `_parse_criteria_from_body` | `extract_acceptance_criteria` | Criteria parsing |
| `parse_completion_promises` | Coach validation flow | Promise parsing |
| `parse_criteria_verifications` | Coach validation flow | Verification parsing |
| `_read_json_artifact` | Multiple write methods | JSON artifact reading |
| `_write_design_results` | Design phase | Design results writing |
| `_read_design_results` | Design phase | Design results reading |
| `_write_task_work_results` | Task-work flow | **Results file creation** |
| `_write_failure_results` | Error handling | Failure recording |
| `_generate_summary` | Result formatting | Summary generation |
| `_validate_file_count_constraint` | Validation flow | File count checks |

**Affected code path**: Only the **task-work delegation** path is affected. The direct SDK path (`_invoke_player_direct`) is a separate method that IS on the class (at line 1928), which is why TASK-CR-003 (direct mode) succeeded while TASK-CR-001 and TASK-CR-002 (task-work delegation) failed.

### Finding 3: Cascading task_work_results.json Error (SECONDARY)

The `task_work_results.json not found` warning is a direct consequence of Finding 1. Since `_invoke_task_work_implement` is orphaned:
1. Player invocation fails immediately at `_ensure_design_approved_state`
2. No task-work execution occurs
3. No `task_work_results.json` is written
4. Coach validation reports missing results

This is **not a separate bug** - it's the same root cause cascading.

### Finding 4: Previous Fixes Verified

| Fix | Status | Evidence |
|-----|--------|----------|
| TASK-FIX-AB01 (context param) | **FIXED** | No `TypeError: invoke_player() got unexpected keyword argument 'context'` in logs |
| TASK-FIX-AB02 (git serialization) | **FIXED** | No `index.lock` errors despite 3 parallel tasks |
| TASK-FIX-AB03 (recovery_count rename) | **FIXED** | Working diff present in working copy (`_recovery_count` -> `recovery_count`) |

### Finding 5: Direct SDK Path Confirmed Working

TASK-CR-003 (direct mode, `implementation_mode=direct`) completed successfully:
- Routed to `_invoke_player_direct` (which IS on the class at line 1928)
- Produced `task_work_results.json`
- Coach approved in 1 turn
- This confirms the AutoBuild infrastructure (checkpointing, Coach validation, state recovery) all function correctly

## Recommendations

### Recommendation 1: Move `detect_rate_limit()` Outside the Class Body (FIX)

**Priority**: Critical (blocks all task-work delegation)
**Effort**: Low (< 30 minutes)

The fix is to move the `detect_rate_limit()` function definition **after** the `AgentInvoker` class ends, ensuring the 15 orphaned methods are properly re-scoped to the class.

**Specific fix**:
1. Cut lines 2305-2330 (`detect_rate_limit` function definition, ending at `return False, None`)
2. Paste them **after** the end of `AgentInvoker` class (after line 3261 in current file, which becomes line 2302 + all the re-scoped methods)
3. Verify via AST that `AgentInvoker` now has all 40 methods
4. Run existing tests to confirm no regression

**Alternative**: Make `detect_rate_limit` a static method on the class. However, since it's also used as a standalone utility (no `self` parameter), keeping it module-level is cleaner.

### Recommendation 2: Add AST-Based Class Integrity Test

**Priority**: Medium (prevents recurrence)
**Effort**: Low (< 1 hour)

Add a test that verifies the `AgentInvoker` class has the expected number of methods:

```python
def test_agent_invoker_class_integrity():
    """Ensure all methods are properly scoped to AgentInvoker class."""
    import ast
    from pathlib import Path

    source = Path("guardkit/orchestrator/agent_invoker.py").read_text()
    tree = ast.parse(source)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AgentInvoker":
            methods = [c for c in ast.iter_child_nodes(node)
                      if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef))]
            # Should have ~40 methods, not 25
            assert len(methods) >= 38, (
                f"AgentInvoker has only {len(methods)} methods. "
                f"Expected 38+. Methods may have been orphaned by a scope break."
            )
            # Specific critical methods must be present
            method_names = {m.name for m in methods}
            assert "_ensure_design_approved_state" in method_names
            assert "_invoke_task_work_implement" in method_names
            assert "_write_task_work_results" in method_names
            break
```

### Recommendation 3: Commit TASK-FIX-AB01/AB02/AB03 Working Copy Changes

**Priority**: High
**Effort**: Minimal

The working copy contains uncommitted fixes from TASK-FIX-AB01 (context param), TASK-FIX-AB02 (git serialization), and TASK-FIX-AB03 (recovery_count rename). These should be committed alongside the scope fix.

## Decision Matrix

| Option | Fix Scope | Effort | Risk | Recommendation |
|--------|-----------|--------|------|----------------|
| Move `detect_rate_limit` after class | Surgical | Low | Low | **Recommended** |
| Refactor to static method | Minor refactor | Low | Low | Acceptable alternative |
| Revert commit b8a827a6 | Full revert | Medium | Medium | Not recommended (would lose rate limit handling) |

## Appendix

### How Python Parses the Orphaned Methods

```python
# What the code looks like (simplified):
class AgentInvoker:
    def format_feedback_for_prompt(self, ...):  # Line 2234 - LAST class method
        return "\n".join(lines)                  # Line 2302 - Class ENDS here

                                                  # Line 2304 - blank line
def detect_rate_limit(error_text: str):           # Line 2305 - MODULE-LEVEL function
    # ... rate limit detection logic ...
    return False, None                            # Line 2330

    async def _invoke_task_work_implement(self, ...):  # Line 2333 - NESTED in detect_rate_limit!
        ...

    def _ensure_design_approved_state(self, ...):      # Line 2817 - NESTED in detect_rate_limit!
        ...
```

Python sees the indented methods after `return False, None` as dead code within `detect_rate_limit`. They compile but are never reachable as class methods.

### Verification Commands

```bash
# Confirm the issue
python3 -c "
from guardkit.orchestrator.agent_invoker import AgentInvoker
print(hasattr(AgentInvoker, '_ensure_design_approved_state'))  # False
print(len([m for m in dir(AgentInvoker) if not m.startswith('__')]))  # ~25 instead of ~40
"

# Confirm the fix (after moving detect_rate_limit)
python3 -c "
import ast
with open('guardkit/orchestrator/agent_invoker.py') as f:
    tree = ast.parse(f.read())
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'AgentInvoker':
        methods = [c for c in ast.iter_child_nodes(node)
                  if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef))]
        print(f'AgentInvoker methods: {len(methods)}')  # Should be ~40
"
```
