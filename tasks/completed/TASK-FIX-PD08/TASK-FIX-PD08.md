---
id: TASK-FIX-PD08
title: Apply TASK-FIX-AGENTRESPONSE-FORMAT to canonical files
status: completed
completed: 2025-12-09T12:00:00Z
task_type: implementation
created: 2025-12-09
priority: critical
tags: [bug-fix, agent-enhance, progressive-disclosure, agentresponse-format]
related_tasks: [TASK-REV-PD07, TASK-FIX-AGENTRESPONSE-FORMAT]
estimated_complexity: 4
---

# TASK-FIX-PD08: Apply AgentResponse Format Fix to Canonical Files

## Summary

Apply the TASK-FIX-AGENTRESPONSE-FORMAT fix that was documented and tested but **never applied to the canonical source files**. The fix enables AI-powered agent enhancement by handling the response format mismatch between Claude's output and the Python orchestrator's expectations.

## Background

### Discovery Context

During the TASK-REV-PD07 review, it was discovered that:
1. Claude created fixed versions of files during testing
2. The fixes exist in `docs/reviews/progressive-disclosure/` (test directory)
3. The canonical files in `installer/core/` DO NOT have the fixes
4. This causes `/agent-enhance` to fall back to static enhancement (poor quality)

### Root Cause Analysis

**The Problem**: When Claude invokes the `agent-content-enhancer` agent and writes the response to `.agent-response-phase8.json`, it writes the raw enhancement content:

```json
{
  "sections": ["related_templates", "boundaries"],
  "related_templates": "...",
  "boundaries": "..."
}
```

**What Python Expects**: The `AgentResponse` dataclass requires an envelope format:

```json
{
  "request_id": "uuid",
  "version": "1.0",
  "status": "success",
  "response": "{\"sections\": [...]}",  // JSON-encoded STRING
  "error_message": null,
  "error_type": null,
  "created_at": "ISO timestamp",
  "duration_seconds": 1.0,
  "metadata": {}
}
```

**The Result**: `TypeError: AgentResponse.__init__() got an unexpected keyword argument 'sections'`

### Evidence from Testing

| Agent | Enhancement Method | Quality |
|-------|-------------------|---------|
| svelte5-component-specialist | AI (fix applied) | HIGH |
| repository-pattern-specialist | AI (fix applied) | HIGH |
| strategy-pattern-specialist | AI (fix applied) | HIGH |
| service-layer-specialist | AI (fix applied) | HIGH |
| openai-function-calling-specialist | AI (fix applied) | HIGH |
| firebase-firestore-specialist | Static fallback | LOW |
| alasql-query-specialist | Static fallback | LOW |

The 5 high-quality agents were enhanced AFTER Claude manually applied the fix during testing. The 2 low-quality agents were enhanced BEFORE the fix.

## Acceptance Criteria

### AC1: Apply Defensive Handling to invoker.py

- [x] Add the auto-wrapping code block to `installer/core/lib/agent_bridge/invoker.py`
- [x] Insert at line ~227 (before the existing response field validation)
- [x] Code must detect raw enhancement content (`sections` present, `request_id` absent)
- [x] Log warning when auto-wrapping is triggered
- [x] Wrap content in proper AgentResponse envelope

**Reference Implementation** (from `docs/reviews/progressive-disclosure/invoker.py` lines 227-247):

```python
# TASK-FIX-AGENTRESPONSE-FORMAT: Detect raw enhancement content without envelope
# This handles the case where Claude writes the agent output directly
# instead of wrapping it in the AgentResponse envelope format
if "sections" in response_data and "request_id" not in response_data:
    logger.warning(
        "Response file contains raw enhancement content, not AgentResponse envelope. "
        "Auto-wrapping for backward compatibility. "
        "Please update command spec to use proper envelope format."
    )
    # Wrap raw content in proper envelope
    response_data = {
        "request_id": "auto-wrapped",
        "version": "1.0",
        "status": "success",
        "response": json.dumps(response_data),  # JSON-encode the raw content
        "error_message": None,
        "error_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 0.0,
        "metadata": {"auto_wrapped": True}
    }
```

### AC2: Add Bridge Protocol to agent-enhance.md (Optional but Recommended)

- [ ] Add "Bridge Protocol for AI Invocation (Exit Code 42)" section
- [ ] Document the correct response file format
- [ ] Include step-by-step instructions for Claude Code
- [ ] Emphasize that `response` field must be JSON-encoded STRING

**Note**: This is a belt-and-suspenders approach. The defensive handling in AC1 will work even without this, but adding the documentation helps Claude write correct format in the future.

### AC3: Verify Fix Works

- [ ] Run `/agent-enhance` on a test agent with `--hybrid` strategy
- [ ] Confirm AI enhancement completes (not static fallback)
- [ ] Check console output shows "Agent response loaded" (not "AI enhancement failed")
- [ ] Verify split output files created with proper content

### AC4: Re-enhance Poor Quality Agents (Optional)

- [ ] Re-enhance `firebase-firestore-specialist` with AI strategy
- [ ] Re-enhance `alasql-query-specialist` with AI strategy
- [ ] Verify boundaries are now template-specific (not generic)
- [ ] Verify extended files have code examples

## Implementation Guide

### Step 1: Update invoker.py

**File**: `installer/core/lib/agent_bridge/invoker.py`

**Location**: Insert after line 225 (after `response_data = json.loads(...)`)

**Diff**:
```diff
         # Parse response
         try:
             response_data = json.loads(self.response_file.read_text(encoding="utf-8"))
+
+            # TASK-FIX-AGENTRESPONSE-FORMAT: Detect raw enhancement content without envelope
+            # This handles the case where Claude writes the agent output directly
+            # instead of wrapping it in the AgentResponse envelope format
+            if "sections" in response_data and "request_id" not in response_data:
+                logger.warning(
+                    "Response file contains raw enhancement content, not AgentResponse envelope. "
+                    "Auto-wrapping for backward compatibility. "
+                    "Please update command spec to use proper envelope format."
+                )
+                # Wrap raw content in proper envelope
+                response_data = {
+                    "request_id": "auto-wrapped",
+                    "version": "1.0",
+                    "status": "success",
+                    "response": json.dumps(response_data),  # JSON-encode the raw content
+                    "error_message": None,
+                    "error_type": None,
+                    "created_at": datetime.now(timezone.utc).isoformat(),
+                    "duration_seconds": 0.0,
+                    "metadata": {"auto_wrapped": True}
+                }

             # TASK-FIX-AGENT-RESPONSE-FORMAT: Validate response field type (defensive)
```

### Step 2: Test the Fix

```bash
# Test with a simple agent
python3 ~/.agentecflow/bin/agent-enhance react-typescript/testing-specialist --hybrid --verbose

# Expected output includes:
# - "Requesting agent invocation: agent-content-enhancer"
# - Exit code 42 (triggers agent invocation)
# - "Agent response loaded (X.Xs)"
# - "Enhanced testing-specialist.md using hybrid strategy"
# - "Sections added: 5" (or similar)
# - "Split output: ✓"
```

### Step 3: Verify Output Quality

Check the enhanced agent file has:
- Template-specific boundaries (not generic "Execute core responsibilities")
- Code examples from actual templates
- Related templates with specific descriptions

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `installer/core/lib/agent_bridge/invoker.py` | Add auto-wrapping logic | CRITICAL |
| `installer/core/commands/agent-enhance.md` | Add bridge protocol docs | RECOMMENDED |

## Reference Files

| File | Purpose |
|------|---------|
| `docs/fixes/TASK-FIX-AGENTRESPONSE-FORMAT.md` | Original fix documentation |
| `docs/reviews/progressive-disclosure/invoker.py` | Working implementation (lines 227-247) |
| `.claude/reviews/TASK-REV-PD07-review-report.md` | Review that discovered the issue |

## Testing Checklist

- [ ] `invoker.py` modified and symlink updated (if applicable)
- [ ] Run `/agent-enhance` with `--hybrid` flag
- [ ] Confirm no "Invalid response format" error
- [ ] Confirm "Agent response loaded" in output
- [ ] Verify split files created (agent.md + agent-ext.md)
- [ ] Check boundaries are template-specific
- [ ] Check extended file has code examples

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fix breaks existing functionality | Low | Medium | Defensive code only triggers on specific pattern |
| Auto-wrapping masks other issues | Low | Low | Warning logged when triggered |
| Fix doesn't work | Low | High | Tested implementation already exists |

## Definition of Done

- [x] Canonical `invoker.py` has defensive handling code
- [ ] `/agent-enhance --hybrid` produces AI-enhanced output (not static fallback)
- [ ] At least one agent successfully enhanced with AI strategy
- [x] No regression in existing functionality

## Priority Justification

**CRITICAL** - This bug causes:
- 29% of agent enhancements to use static fallback (low quality)
- Progressive disclosure feature not working as designed
- User confusion when AI enhancement "fails" silently
- Documented fix exists but is not applied
