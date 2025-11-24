---
id: TASK-FIX-D4E5
title: Fix agent-enhance checkpoint-resume infinite loop
status: backlog
created: 2025-11-24T12:15:00Z
updated: 2025-11-24T12:15:00Z
priority: critical
tags: [bugfix, agent-enhancement, checkpoint-resume]
complexity: 3
related_tasks: [TASK-FIX-A7D3]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-FIX-D4E5: Fix agent-enhance checkpoint-resume infinite loop

## Executive Summary

The `/agent-enhance` command enters an infinite loop due to missing checkpoint-resume pattern implementation. The command repeatedly writes `.agent-request.json` and exits with code 42, but never checks for or loads the response file on subsequent invocations. This is a **pre-existing architectural bug** exposed (not caused) by TASK-FIX-A7D3.

## Context

### Related Work
- **TASK-FIX-A7D3**: Fixed Python scoping issue with `import json` in enhancer.py
- **Root Cause**: Pre-existing bug in agent-enhance command (existed before A7D3)
- **Exposed By**: TASK-FIX-A7D3 fix allowed code to run further, exposing checkpoint-resume bug

### Current Behavior (Broken)

```bash
# User runs command
/agent-enhance maui-mydrive/xunit-nsubstitute-async-testing-specialist --hybrid

# Orchestrator behavior:
1. Creates AgentBridgeInvoker
2. Calls invoker.invoke() immediately (no response check)
3. Writes .agent-request.json
4. Exits with code 42
5. Claude Code generates .agent-response.json

# User re-runs command (or automated retry)
/agent-enhance maui-mydrive/xunit-nsubstitute-async-testing-specialist --hybrid

# Orchestrator behavior (BROKEN):
1. Creates NEW AgentBridgeInvoker
2. Calls invoker.invoke() immediately (STILL no response check!)
3. OVERWRITES .agent-request.json
4. Exits with code 42 (again)
5. INFINITE LOOP CONTINUES
```

### Expected Behavior (Fixed)

```bash
# First invocation
1. Check for .agent-response.json → NOT FOUND
2. Call invoker.invoke()
3. Write .agent-request.json, exit 42

# Second invocation (should resume)
1. Check for .agent-response.json → FOUND
2. Call invoker.load_response() to cache it
3. Call invoker.invoke() (returns cached response immediately)
4. Parse response, continue with enhancement
5. Exit 0 (success)
```

## Root Cause Analysis

### Evidence: Pre-Existing Bug

**Git History Confirms** bug existed BEFORE TASK-FIX-A7D3:

```bash
$ git show 9aa3a3b^:installer/global/lib/agent_enhancement/enhancer.py | grep -A 5 "invoker.invoke"
result_text = invoker.invoke(  # ❌ Same bug existed before
    agent_name="agent-content-enhancer",
    prompt=prompt
)
```

**Commit Timeline**:
- Commit 9aa3a3b (TASK-FIX-A7D3): Fixed import json scoping
- Commit 9aa3a3b^ (before A7D3): Already had checkpoint-resume bug

### Missing Pattern Implementation

**Current Code** (`enhancer.py`, lines 256-271):
```python
try:
    import json  # Local import required - ensures scope covers all exception handlers (line 341)
    # Use AgentBridgeInvoker for Claude Code integration (same pattern as template-create)
    import importlib
    _agent_bridge_module = importlib.import_module('installer.global.lib.agent_bridge.invoker')
    AgentBridgeInvoker = _agent_bridge_module.AgentBridgeInvoker

    invoker = AgentBridgeInvoker(
        phase=8,  # Phase 8: Agent Enhancement
        phase_name="agent_enhancement"
    )

    result_text = invoker.invoke(  # ❌ MISSING RESPONSE CHECK
        agent_name="agent-content-enhancer",
        prompt=prompt
    )
```

**Working Reference** (`template_create_orchestrator.py`, line 1770):
```python
# Load agent response if available
try:
    response = self.agent_invoker.load_response()
    print(f"  ✓ Agent response loaded successfully")
except FileNotFoundError:
    print(f"  ⚠️  No agent response found")
    # Falls back to alternative approach
```

### What's Missing

1. **No response check**: Doesn't call `invoker.has_response()` before invoking
2. **No load logic**: Never calls `invoker.load_response()` to cache response
3. **No conditional invocation**: Always calls `invoke()` regardless of cached state

## Problem Statement

**The `/agent-enhance` command was never fully integrated with the checkpoint-resume pattern.**

The command uses `AgentBridgeInvoker` but lacks the required checkpoint-resume logic:
- Missing `has_response()` check
- Missing `load_response()` call
- Always invokes fresh, never resumes

## Recommended Fix: Option B (Automatic Resume Detection)

### Why Option B?

**Simplest fix with minimal scope**:
- ✅ No command-line changes needed
- ✅ Transparent to user (no `--resume` flag required)
- ✅ Single file modification (enhancer.py only)
- ✅ Matches user request: "scope should be kept as small as possible"

**Alternative Options Rejected**:
- ❌ Option A (Add `--resume` flag): Requires changes to command entry point + enhancer
- ❌ Option C (Direct Task API): Major refactoring, removes checkpoint capability

### Implementation Scope

**CRITICAL: Scope Constraints**

This fix MUST:
- ✅ Modify ONLY `enhancer.py` (single file)
- ✅ Change ONLY `_ai_enhancement()` method (single function)
- ✅ Add ONLY response check logic (5-10 lines)
- ✅ Preserve ALL existing functionality
- ❌ NOT modify command entry point (`agent-enhance.py`)
- ❌ NOT add new CLI flags or parameters
- ❌ NOT change invoker interface (`agent_bridge/invoker.py`)
- ❌ NOT modify any other files

**Justification**: Minimizes regression risk by limiting blast radius to single function in single file.

## Exact Changes Required

### Change 1: Add response check after invoker creation

**Location**: `installer/global/lib/agent_enhancement/enhancer.py`, lines 263-271

**Current Code** (lines 263-271):
```python
        invoker = AgentBridgeInvoker(
            phase=8,  # Phase 8: Agent Enhancement
            phase_name="agent_enhancement"
        )

        result_text = invoker.invoke(
            agent_name="agent-content-enhancer",
            prompt=prompt
        )
```

**Replace With**:
```python
        invoker = AgentBridgeInvoker(
            phase=8,  # Phase 8: Agent Enhancement
            phase_name="agent_enhancement"
        )

        # Check for existing response from previous invocation (checkpoint-resume pattern)
        if invoker.has_response():
            # Response file exists - load cached response
            result_text = invoker.load_response()
            if self.verbose:
                logger.info("  ✓ Loaded agent response from checkpoint")
        else:
            # No response yet - invoke agent (will exit with code 42)
            result_text = invoker.invoke(
                agent_name="agent-content-enhancer",
                prompt=prompt
            )
```

**Lines Changed**: 271 → 280 (9 lines added)

### Expected Diff

```diff
--- a/installer/global/lib/agent_enhancement/enhancer.py
+++ b/installer/global/lib/agent_enhancement/enhancer.py
@@ -268,9 +268,17 @@ class SingleAgentEnhancer:
             phase_name="agent_enhancement"
         )

-        result_text = invoker.invoke(
-            agent_name="agent-content-enhancer",
-            prompt=prompt
-        )
+        # Check for existing response from previous invocation (checkpoint-resume pattern)
+        if invoker.has_response():
+            # Response file exists - load cached response
+            result_text = invoker.load_response()
+            if self.verbose:
+                logger.info("  ✓ Loaded agent response from checkpoint")
+        else:
+            # No response yet - invoke agent (will exit with code 42)
+            result_text = invoker.invoke(
+                agent_name="agent-content-enhancer",
+                prompt=prompt
+            )

         duration = time.time() - start_time
```

## How the Fix Works

### Before Fix (Broken)

```
Invocation 1:
  invoker = AgentBridgeInvoker(...)
  result_text = invoker.invoke(...)  # ❌ Always invokes
  → Writes .agent-request.json, exits 42

Invocation 2:
  invoker = AgentBridgeInvoker(...)  # New instance
  result_text = invoker.invoke(...)  # ❌ Invokes again!
  → Overwrites .agent-request.json, exits 42
  → INFINITE LOOP
```

### After Fix (Working)

```
Invocation 1:
  invoker = AgentBridgeInvoker(...)
  if invoker.has_response():  # ✅ Checks first
      # False - no response yet
  else:
      result_text = invoker.invoke(...)  # ✅ Invokes
  → Writes .agent-request.json, exits 42

Invocation 2:
  invoker = AgentBridgeInvoker(...)
  if invoker.has_response():  # ✅ Checks first
      # True - response exists!
      result_text = invoker.load_response()  # ✅ Loads cached
  else:
      # Skipped
  → Continues with enhancement, exits 0
  → SUCCESS
```

### Key Mechanism

The fix leverages `AgentBridgeInvoker`'s built-in checkpoint-resume capability:

1. **`has_response()`**: Checks if `.agent-response.json` exists
2. **`load_response()`**: Reads response file, caches in `_cached_response`
3. **`invoke()`**: Returns `_cached_response` if not None, else requests agent

By calling `load_response()` before `invoke()`, we ensure `_cached_response` is populated, and `invoke()` returns immediately without writing a new request.

## Acceptance Criteria

### Functional Requirements

1. ✅ **First invocation writes request and exits 42**
   - Creates `.agent-request.json`
   - Exits with code 42 (NEED_AGENT)
   - No response file created by orchestrator

2. ✅ **Second invocation loads response and continues**
   - Detects `.agent-response.json` exists
   - Loads response using `load_response()`
   - Continues enhancement process
   - Exits with code 0 (success)

3. ✅ **Verbose logging shows checkpoint behavior**
   - When response loaded: Logs "✓ Loaded agent response from checkpoint"
   - User can verify checkpoint-resume is working

4. ✅ **No infinite loop**
   - Command completes successfully after 2 invocations
   - No repeated `.agent-request.json` overwrites

5. ✅ **Preserves all existing functionality**
   - AI enhancement strategy works
   - Static enhancement strategy works
   - Hybrid strategy works
   - Retry logic works
   - Error handling works

### Non-Functional Requirements

6. ✅ **Minimal scope (single file, single function)**
   - Only `enhancer.py` modified
   - Only `_ai_enhancement()` method changed
   - No other files touched

7. ✅ **No breaking changes**
   - Command signature unchanged
   - No new CLI flags required
   - Backward compatible with existing usage

8. ✅ **Clear code documentation**
   - Comment explains checkpoint-resume pattern
   - Future maintainers understand WHY check is needed

## Test Cases

### Test Case 1: First Invocation Creates Request

```bash
# Preconditions
rm -f .agent-request.json .agent-response.json

# Execute
/agent-enhance template/agent --hybrid

# Expected Results
✅ Exit code: 42 (NEED_AGENT)
✅ .agent-request.json created
✅ .agent-response.json NOT created by orchestrator
```

### Test Case 2: Second Invocation Loads Response

```bash
# Preconditions
# - .agent-request.json exists (from Test Case 1)
# - .agent-response.json created (by Claude Code or manual)

# Execute
/agent-enhance template/agent --hybrid --verbose

# Expected Results
✅ Exit code: 0 (success)
✅ Log message: "✓ Loaded agent response from checkpoint"
✅ Enhancement applied to agent file
✅ No new .agent-request.json written
```

### Test Case 3: Corrupted Response Falls Back to Re-Invoke

```bash
# Preconditions
echo "INVALID JSON" > .agent-response.json

# Execute
/agent-enhance template/agent --hybrid

# Expected Results
✅ load_response() raises exception
✅ Falls back to invoke() (writes new request)
✅ Exit code: 42 (NEED_AGENT)
✅ User can fix response and retry
```

### Test Case 4: Verbose Mode Shows Checkpoint Behavior

```bash
# Execute with verbose flag
/agent-enhance template/agent --hybrid --verbose

# Expected Output (second invocation)
AI Enhancement Started:
  Agent: xunit-nsubstitute-async-testing-specialist
  Templates: 8
  Prompt size: 1995 chars
  ✓ Loaded agent response from checkpoint  # ← NEW
AI Response Received:
  Duration: 0.02s
  Response size: 13485 chars
```

## Verification Steps

### 1. Verify Syntax and Imports

```bash
# Check Python syntax
python3.14 -m py_compile installer/global/lib/agent_enhancement/enhancer.py
echo "✅ Syntax check passed"

# Verify no import errors
python3.14 -c "from installer.global.lib.agent_enhancement.enhancer import SingleAgentEnhancer"
echo "✅ Import successful"
```

### 2. Clear Previous State

```bash
# Remove old request/response files
rm -f .agent-request.json .agent-response.json
echo "✅ State cleared"
```

### 3. Run First Invocation

```bash
# Should create request and exit 42
/agent-enhance maui-mydrive/xunit-nsubstitute-async-testing-specialist --hybrid

# Expected: Exit code 42
echo "Exit code: $?"  # Should be 42

# Verify request file created
ls -la .agent-request.json  # Should exist
```

### 4. Simulate Agent Response

```bash
# Create mock response (or let Claude Code generate real one)
cat > .agent-response.json << 'EOF'
{
  "request_id": "test-checkpoint-resume",
  "status": "success",
  "response": "{\"sections\": [\"boundaries\"], \"boundaries\": \"## Boundaries\\n\\n### ALWAYS\\n- ✅ Test rule\\n\\n### NEVER\\n- ❌ Test prohibition\\n\\n### ASK\\n- ⚠️ Test escalation\"}",
  "duration_seconds": 1.0
}
EOF

echo "✅ Mock response created"
```

### 5. Run Second Invocation (Should Resume)

```bash
# Should load response and complete
/agent-enhance maui-mydrive/xunit-nsubstitute-async-testing-specialist --hybrid --verbose

# Expected: Exit code 0
echo "Exit code: $?"  # Should be 0

# Verify log message
# Should see: "✓ Loaded agent response from checkpoint"
```

### 6. Verify No Infinite Loop

```bash
# Run command twice with proper response file
/agent-enhance template/agent --hybrid  # First: exit 42
# [Response file created by Claude Code]
/agent-enhance template/agent --hybrid  # Second: exit 0 (SUCCESS)

# Third invocation should also succeed (idempotent)
/agent-enhance template/agent --hybrid  # Third: exit 0 (SUCCESS)

echo "✅ No infinite loop - command completes successfully"
```

## Rollback Plan

### If Fix Fails

1. **Revert commit**:
   ```bash
   git revert HEAD
   ```

2. **Restore original enhancer.py**:
   ```bash
   git checkout HEAD^ -- installer/global/lib/agent_enhancement/enhancer.py
   ```

3. **Clear cache**:
   ```bash
   find installer/global/lib/agent_enhancement -name "*.pyc" -delete
   find installer/global/lib/agent_enhancement -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
   ```

4. **Workaround for users**:
   ```bash
   # Use static strategy (bypasses AI invocation)
   /agent-enhance template/agent --static
   ```

### Rollback Assessment for TASK-FIX-A7D3

**DO NOT ROLLBACK TASK-FIX-A7D3** because:
- ✅ A7D3 fixed a real Python scoping issue with `import json`
- ✅ This checkpoint-resume bug was pre-existing (evidence in git history)
- ✅ Rolling back A7D3 would mask the real problem without fixing it
- ✅ A7D3 import fix is correct and necessary for line 341 exception handler

## Prevention Strategy

### Code Review Checklist

When reviewing checkpoint-resume patterns, verify:

- [ ] `has_response()` checked before `invoke()`
- [ ] `load_response()` called if response exists
- [ ] Conditional invocation based on cached state
- [ ] Verbose logging for debugging
- [ ] Error handling for corrupted responses
- [ ] Clear comments explaining checkpoint behavior

### Integration Test

Add test to prevent regression:

```python
def test_agent_enhance_checkpoint_resume():
    """Test that agent-enhance properly resumes after checkpoint."""
    # First invocation
    result = subprocess.run(
        ["python3.14", "agent-enhance.py", "template/agent", "--hybrid"],
        capture_output=True,
        cwd="installer/global/commands"
    )
    assert result.returncode == 42  # NEED_AGENT
    assert Path(".agent-request.json").exists()

    # Simulate agent response
    response = {
        "request_id": "test",
        "status": "success",
        "response": '{"sections": ["boundaries"], "boundaries": "..."}',
        "duration_seconds": 1.0
    }
    Path(".agent-response.json").write_text(json.dumps(response))

    # Second invocation (should resume and complete)
    result = subprocess.run(
        ["python3.14", "agent-enhance.py", "template/agent", "--hybrid", "--verbose"],
        capture_output=True,
        cwd="installer/global/commands"
    )
    assert result.returncode == 0  # Success
    assert "✓ Loaded agent response from checkpoint" in result.stdout.decode()
    assert not Path(".agent-request.json").exists()  # Cleaned up

    # Third invocation (idempotent - should also succeed)
    result = subprocess.run(
        ["python3.14", "agent-enhance.py", "template/agent", "--hybrid"],
        capture_output=True,
        cwd="installer/global/commands"
    )
    assert result.returncode == 0  # Success
```

### Documentation Update

Add checkpoint-resume pattern to developer documentation:

```markdown
## Agent Bridge Invoker Pattern

When using `AgentBridgeInvoker` for checkpoint-resume:

1. **Always check for response first**:
   ```python
   if invoker.has_response():
       result = invoker.load_response()
   else:
       result = invoker.invoke(...)
   ```

2. **Why**: `invoke()` returns cached response if `load_response()` was called
3. **Prevents**: Infinite checkpoint loops (exit 42 repeats)
4. **Reference**: `template_create_orchestrator.py` line 1770
```

## Related Issues

### GitHub Issues to Close

- [ ] #XXX: `/agent-enhance` enters infinite loop with exit code 42
- [ ] #YYY: Agent enhancement checkpoint-resume not working

### Follow-Up Tasks

- [ ] Add integration test for checkpoint-resume (see Prevention Strategy)
- [ ] Update developer documentation with checkpoint-resume pattern
- [ ] Review other commands using AgentBridgeInvoker for similar issues
- [ ] Consider adding `--no-checkpoint` flag for debugging (future enhancement)

## Success Metrics

### Immediate Success (Day 1)

- ✅ `/agent-enhance` completes successfully after 2 invocations
- ✅ No infinite loop reports from users
- ✅ User can enhance 8+ agents in maui-mydrive template
- ✅ All tests pass (existing + new integration test)

### Long-Term Success (Week 1)

- ✅ Zero regression reports
- ✅ Checkpoint-resume pattern documented
- ✅ Other commands reviewed for similar issues
- ✅ Integration test prevents future regressions

## Stakeholders

- **Primary**: User (blocked by infinite loop)
- **Secondary**: Taskwright maintainers (pattern consistency)
- **Tertiary**: Future template creators (reliable agent enhancement)

## Timeline Estimate

- **Analysis**: 30 minutes (completed via debugging-specialist)
- **Implementation**: 5 minutes (9 lines of code)
- **Testing**: 15 minutes (manual verification + integration test)
- **Documentation**: 10 minutes (inline comments + dev docs)
- **Total**: ~60 minutes

**Complexity**: 3/10 (Simple - conditional logic addition, no architecture changes)

## Implementation Notes

### Key Insight

The `AgentBridgeInvoker` already supports checkpoint-resume via:
- `has_response()` method
- `load_response()` method
- `_cached_response` instance variable

The fix simply adds the missing check before invocation. The invoker does the heavy lifting.

### Why This Wasn't Caught Earlier

1. **Partial implementation**: AgentBridgeInvoker was added but integration was incomplete
2. **Worked by accident**: May have failed earlier due to other bugs (like TASK-FIX-A7D3 import issue)
3. **No integration tests**: Checkpoint-resume cycle was never tested end-to-end
4. **Reference implementation not followed**: `template-create` has correct pattern, but not copied to `agent-enhance`

### Lessons Learned

- Always follow established patterns (template-create reference)
- Add integration tests for multi-step workflows
- Document non-obvious patterns (checkpoint-resume)
- Test full workflow, not just individual functions

---

## Next Steps

When ready to implement:

```bash
# 1. Work on this task
/task-work TASK-FIX-D4E5

# 2. Verify fix with test cases
[See Verification Steps section]

# 3. Complete task
/task-complete TASK-FIX-D4E5
```

**CRITICAL**: After fixing this task, TASK-FIX-A7D3 should remain in place. Both fixes are necessary:
- **TASK-FIX-A7D3**: Fixed import scoping (line 341 exception handler)
- **TASK-FIX-D4E5**: Fixes checkpoint-resume (infinite loop)
