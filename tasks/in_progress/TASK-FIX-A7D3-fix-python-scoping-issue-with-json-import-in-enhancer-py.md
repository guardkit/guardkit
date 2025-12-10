---
id: TASK-FIX-A7D3
title: Fix Python scoping issue with json import in enhancer.py
status: backlog
created: 2025-11-24T10:52:00Z
updated: 2025-11-24T10:52:00Z
priority: critical
tags: [bugfix, python-scoping, linter-regression, enhancer]
complexity: 3
estimated_effort: 1-2 hours
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix Python scoping issue with json import in enhancer.py

## Problem Summary

**Bug**: `UnboundLocalError: cannot access local variable 'json' where it is not associated with a value`
**Location**: `installer/core/lib/agent_enhancement/enhancer.py`, line 341
**Impact**: Agent enhancement fails when AI returns invalid JSON, preventing boundaries workaround
**Severity**: CRITICAL - Blocks `/agent-enhance` command execution

## Root Cause Analysis

### Python Scoping Issue

Python's function-level scoping rules cause `json` to be treated as a LOCAL variable for the ENTIRE `_ai_enhancement()` function when `import json` appears anywhere inside the function (line 291), even though it's also imported at module level (line 12).

**The Problem**:
1. Line 12: `import json` (module-level, global scope)
2. Line 291: `import json  # noqa: F811` (inside nested try block at lines 292-301)
3. Line 341: `except json.JSONDecodeError` (OUTSIDE the nested try block)

When Python sees line 291, it marks `json` as LOCAL for the entire function, shadowing the module-level import. Line 341 tries to reference `json.JSONDecodeError` outside the nested try block where the local `json` was defined, causing `UnboundLocalError`.

### Why Linters Keep Removing It

Linters (including Claude Code's autonomous editing) see:
- Module-level `import json` at line 12
- Local `import json` at line 291
- Flag as "redundant import" (F811)
- Remove it despite `# noqa: F811` comment

This creates a **regression cycle**:
1. Fix is committed with `# noqa: F811` comment
2. Linter/Claude Code removes it as "redundant"
3. Bug reappears
4. Cycle repeats

## Proposed Solution (Minimal Change)

**Move the local `import json` from line 291 to line 257** (beginning of outer try block).

### Why This Works

Moving the import ensures `json` is in scope for ALL exception handlers:
- **Before**: LOCAL `json` scope = lines 291-301 (nested try block only)
- **After**: LOCAL `json` scope = lines 257-356 (entire try-except structure)
- Line 341's `except json.JSONDecodeError` will be within scope ✅

## Implementation Details

### Files to Modify

**File**: `installer/core/lib/agent_enhancement/enhancer.py`
**Function**: `_ai_enhancement()` (lines 213-356)

### Exact Changes Required

#### Change 1: Add import after line 256

**Location**: After line 256 (`try:`)

**Add**:
```python
            import json  # Local import for JSON parsing in exception handlers
```

#### Change 2: Remove import from line 291

**Location**: Line 291 (inside nested ValueError handler)

**Remove**:
```python
                    import json  # noqa: F811 - Required here due to Python scoping rules
```

#### Change 3: Update comment at line 290

**Location**: Line 290 (comment above where import was)

**Change from**:
```python
                    # Parse without validation to get partial enhancement
                    import json  # noqa: F811 - Required here due to Python scoping rules
```

**Change to**:
```python
                    # Parse without validation to get partial enhancement (using local json import)
```

### Expected Diff

```diff
--- a/installer/core/lib/agent_enhancement/enhancer.py
+++ b/installer/core/lib/agent_enhancement/enhancer.py
@@ -254,6 +254,7 @@ class SingleAgentEnhancer:
             logger.info(f"  Prompt size: {len(prompt)} chars")

         try:
+            import json  # Local import for JSON parsing in exception handlers
             # Use AgentBridgeInvoker for Claude Code integration
             import importlib
             _agent_bridge_module = importlib.import_module('installer.core.lib.agent_bridge.invoker')
@@ -287,8 +288,7 @@ class SingleAgentEnhancer:
                     logger.warning(f"Parser detected missing boundaries (schema violation): {e}")
                     logger.info("Triggering workaround: will add generic boundaries")

-                    # Parse without validation to get partial enhancement
-                    import json  # noqa: F811 - Required here due to Python scoping rules
+                    # Parse without validation to get partial enhancement (using local json import)
                     try:
                         # Extract JSON from response (reuse parser's extraction logic)
                         json_content = self.parser._extract_json_from_markdown(result_text)
```

### Lines Changed

- **Added**: 1 line (import statement after line 256)
- **Removed**: 1 line (import statement at line 291)
- **Modified**: 1 line (updated comment at line 290)
- **Net Change**: +1 line

## Acceptance Criteria

### AC1: UnboundLocalError Eliminated ✅

- [ ] Run `/agent-enhance` with AI returning invalid JSON
- [ ] Verify line 341's `except json.JSONDecodeError` catches exception
- [ ] Verify NO `UnboundLocalError` occurs

### AC2: All Exception Handlers Work ✅

- [ ] Test ValueError path with missing boundaries (lines 284-319)
- [ ] Test JSONDecodeError path at line 299 (nested handler)
- [ ] Test JSONDecodeError path at line 341 (outer handler)
- [ ] Test TimeoutError path at line 336
- [ ] All handlers execute without `UnboundLocalError`

### AC3: Existing Tests Pass ✅

- [ ] Run full test suite: `pytest tests/agent_enhancement/test_enhancer.py -v`
- [ ] All existing tests pass
- [ ] No new test failures introduced

### AC4: Linter Compliance ✅

- [ ] Run `ruff check installer/core/lib/agent_enhancement/enhancer.py`
- [ ] Run `flake8 installer/core/lib/agent_enhancement/enhancer.py`
- [ ] No F811 warnings (or justified with comment)
- [ ] No other linter errors

### AC5: Code Review Approved ✅

- [ ] Changes reviewed for Python scoping correctness
- [ ] Comment explains why local import is needed
- [ ] Minimal change principle verified
- [ ] No side effects identified

## Test Requirements

### Test Case 1: Normal Flow (No ValueError)

**Purpose**: Verify normal operation unaffected by change

**Setup**: Mock parser to return valid enhancement with boundaries

**Expected**: Enhancement succeeds, no errors

**Command**:
```bash
pytest tests/agent_enhancement/test_enhancer.py::test_ai_enhancement_success -v
```

### Test Case 2: Missing Boundaries (ValueError Path)

**Purpose**: Verify ValueError handler with json.loads() works

**Setup**: Mock parser to raise `ValueError("missing required 'boundaries' field")`

**Expected**:
- ValueError caught
- Generic boundaries added via workaround
- `json.loads()` at lines 296/298 work
- No `UnboundLocalError`

**Command**:
```bash
pytest tests/agent_enhancement/test_enhancer.py::test_ai_enhancement_missing_boundaries -v
```

### Test Case 3: Invalid JSON at Outer Handler (Line 341) 🆕

**Purpose**: Verify the FIX - line 341's exception handler works

**Setup**: Mock AI to return completely invalid JSON (not caught by line 299)

**Expected**:
- Line 341's `except json.JSONDecodeError` catches error
- ValidationError raised with message "Invalid JSON response: ..."
- **BEFORE FIX**: UnboundLocalError at line 341
- **AFTER FIX**: Proper JSONDecodeError handling

**Command**:
```bash
pytest tests/agent_enhancement/test_enhancer.py::test_json_decode_error_outer_handler -v
```

**Test Code to Add**:
```python
def test_json_decode_error_outer_handler(self, mock_agent_bridge):
    """Test that outer JSONDecodeError handler (line 341) works after fix."""
    # Mock AI to return invalid JSON
    mock_agent_bridge.invoke.return_value = AgentResponse(
        status="completed",
        result="{invalid json}"  # Malformed JSON
    )

    enhancer = SingleAgentEnhancer()

    # Should raise ValidationError, NOT UnboundLocalError
    with pytest.raises(ValidationError) as exc_info:
        enhancer._ai_enhancement(agent_metadata, templates, template_dir)

    assert "Invalid JSON response" in str(exc_info.value)
```

### Test Case 4: Nested JSONDecodeError (Line 299)

**Purpose**: Verify nested JSONDecodeError handler still works

**Setup**: Mock parser to raise ValueError, then return invalid JSON in workaround path

**Expected**:
- Line 299's `except json.JSONDecodeError` catches error
- Re-raises original ValueError
- No `UnboundLocalError`

**Command**:
```bash
pytest tests/agent_enhancement/test_enhancer.py::test_json_decode_error_nested_handler -v
```

## Scope Constraints

### IN SCOPE ✅

1. Move `import json` from line 291 to line 257
2. Update comment at line 290
3. Verify all exception handlers work
4. Run existing test suite
5. Add test for outer JSONDecodeError handler (line 341)

### OUT OF SCOPE ❌

1. **DO NOT** remove module-level `import json` at line 12
2. **DO NOT** change exception handling logic
3. **DO NOT** refactor other parts of the function
4. **DO NOT** modify other files
5. **DO NOT** change function signature or return values

## Why Minimal Scope Matters

**Regression Risk**: This bug was introduced by a well-intentioned linter fix. ANY change beyond moving the import risks:
1. Breaking existing functionality
2. Introducing new bugs
3. Affecting other functions that may depend on module-level import
4. Causing test failures

**Principle**: Make the SMALLEST possible change that fixes the bug. Do not "improve" surrounding code.

## Verification Steps

### Step 1: Apply the Fix

```bash
# Edit the file with the 3 changes specified above
# DO NOT make any other changes
```

### Step 2: Clear Python Cache

```bash
find installer/core/lib/agent_enhancement -name "*.pyc" -delete
find installer/core/lib/agent_enhancement -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
```

### Step 3: Run Tests

```bash
# Run full test suite
pytest tests/agent_enhancement/test_enhancer.py -v --cov=installer/core/lib/agent_enhancement/enhancer --cov-report=term

# Run specific test for the fix (after adding test)
pytest tests/agent_enhancement/test_enhancer.py::test_json_decode_error_outer_handler -v
```

### Step 4: Manual Verification

```bash
# Test with actual agent-enhance command
/agent-enhance maui-mydrive/xunit-nsubstitute-async-testing-specialist --hybrid

# Should complete without UnboundLocalError
```

### Step 5: Linter Check

```bash
ruff check installer/core/lib/agent_enhancement/enhancer.py
flake8 installer/core/lib/agent_enhancement/enhancer.py
```

## Rollback Plan

If the fix causes unexpected issues:

### Quick Rollback (Git Revert)

```bash
git revert <commit-hash>
```

### Manual Rollback

1. Remove line 257: `import json  # Local import...`
2. Restore line 291: `import json  # noqa: F811...`
3. Clear Python cache
4. Run tests to verify rollback

## Prevention Strategy

### Preventing Linter Removal

**Add clear explanatory comment**:
```python
import json  # Local import required - ensures scope covers all exception handlers (line 341)
```

This educates future maintainers and may prevent automated removal.

### Code Review Checklist Item

Add to code review checklist:
- [ ] Function-level imports have clear justification
- [ ] Function-level imports don't shadow module imports unnecessarily
- [ ] All usages of function-level imports are within scope

### Test Coverage

Ensure test coverage includes:
- All exception paths in functions with local imports
- Specific tests for scoping-related bugs
- Tests that would have caught this bug

## References

- **Root Cause Analysis**: Full RCA document from debugging-specialist agent
- **Python Scoping Rules**: [PEP 227 - Statically Nested Scopes](https://peps.python.org/pep-0227/)
- **LEGB Rule**: [Python Scope & LEGB Rule](https://realpython.com/python-scope-legb-rule/)
- **UnboundLocalError**: [Python Docs](https://docs.python.org/3/library/exceptions.html#UnboundLocalError)
- **Commit with noqa fix**: 9aa3a3b (repeatedly removed by linters)

## Implementation Notes

### Why Not Remove Module-Level Import?

**Question**: If we have local import, why keep line 12?

**Answer**:
1. Other functions may use `json` (future-proofing)
2. Shows module dependencies at top of file (Python convention)
3. No harm (module-level imports are cached, zero cost)
4. Minimal change principle (don't touch what works)

### Performance Impact

**None**: Python caches imports, so having both module-level and function-level imports has zero performance cost.

### Side Effects

**None identified**:
- Module-level import remains unchanged
- Local import shadows module-level consistently (same behavior, wider scope)
- No impact on other functions
- No impact on exception handling logic

## Success Metrics

- ✅ UnboundLocalError eliminated at line 341
- ✅ All existing tests pass
- ✅ New test for line 341 handler passes
- ✅ Linter compliance achieved
- ✅ No regressions in agent enhancement workflow
- ✅ Fix persists through linter runs (comment prevents removal)

---

## Next Steps

1. **Review this task specification thoroughly**
2. **When ready to implement**: `/task-work TASK-FIX-A7D3`
3. **Do NOT implement manually** - use `/task-work` for quality gates

The `/task-work` command will:
- Execute Phase 2.5 (Architectural Review) to verify the fix approach
- Execute Phase 4.5 (Test Enforcement) to ensure tests pass
- Execute Phase 5 (Code Review) to verify minimal change principle
- Execute Phase 5.5 (Plan Audit) to detect scope creep

**Expected Duration**: 1-2 hours including testing and verification
