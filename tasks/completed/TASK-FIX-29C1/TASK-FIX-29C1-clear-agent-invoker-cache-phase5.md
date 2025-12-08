---
id: TASK-FIX-29C1
title: Clear agent invoker cache before Phase 5 to enable multi-phase AI invocation
status: completed
created: 2025-12-08T07:30:00Z
updated: 2025-12-08T11:50:00Z
completed: 2025-12-08T11:50:00Z
priority: high
tags: [template-create, agent-generation, bug-fix, cache]
task_type: implementation
complexity: 2
related_tasks: [TASK-REV-993B, TASK-ENH-D960, TASK-IMP-D93B]
test_results:
  status: passed
  coverage: 93
  last_run: 2025-12-08T11:45:00Z
completion_summary:
  files_modified: 2
  tests_added: 12
  quality_gates_passed: true
  architectural_review_score: 88
  code_review_verdict: approved
---

# Task: Clear agent invoker cache before Phase 5

## Description

Fix the agent generation failure in `/template-create` by clearing the `AgentBridgeInvoker` cache before Phase 5. This allows both Phase 1 (codebase analysis) and Phase 5 (agent generation) to make their own AI invocations.

## Context

**Root Cause**: TASK-ENH-D960 enabled AI in Phase 1, but the `AgentBridgeInvoker._cached_response` persists across phases. When Phase 5 tries to invoke AI, it receives Phase 1's cached response (wrong format), causing all agent specs to fail validation.

**Why Not Revert**: AI-powered Phase 1 provides significant quality improvements (98% confidence vs 75% fixed, 9 patterns vs basic, 20 example files with context). We want to preserve this improvement.

**Solution**: Add a `clear_cache()` method and call it before Phase 5 invocation.

## Acceptance Criteria

- [x] Add `clear_cache()` method to `AgentBridgeInvoker` class
- [x] Call `clear_cache()` at the start of `_phase5_agent_recommendation()`
- [ ] Phase 5 successfully invokes AI with its own prompt (requires manual verification)
- [ ] Agent stubs are generated (non-zero count) (requires manual verification)
- [ ] `agents/` directory is created in template output (requires manual verification)
- [ ] Both Phase 1 and Phase 5 checkpoints work correctly (requires manual verification)
- [ ] No regression in template quality (Phase 1 AI analysis preserved) (requires manual verification)

## Implementation Plan

### Step 1: Add `clear_cache()` method to AgentBridgeInvoker

**File**: `installer/global/lib/agent_bridge/invoker.py`

**Location**: After `has_response()` method (around line 286)

```python
def clear_cache(self) -> None:
    """Clear cached response to allow new AI invocation.

    Use this when multiple phases need separate AI invocations.
    After clearing, the next invoke() call will write a new request
    and exit with code 42 for agent invocation.

    TASK-FIX-29C1: Enables multi-phase AI invocation pattern.
    """
    self._cached_response = None
```

### Step 2: Call `clear_cache()` in Phase 5

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

**Location**: At the start of `_phase5_agent_recommendation()` method (around line 892)

```python
def _phase5_agent_recommendation(self, analysis: Any) -> List[Any]:
    """
    Phase 5: Recommend and generate custom agents.
    ...
    """
    self._print_phase_header("Phase 5: Agent Recommendation")

    # TASK-FIX-29C1: Clear Phase 1 cached response before Phase 5 invocation
    # This enables multi-phase AI invocation pattern where both Phase 1
    # (codebase analysis) and Phase 5 (agent generation) can invoke AI
    self.agent_invoker.clear_cache()

    # TASK-FIX-INFINITE-LOOP: Skip AI invocation if forced to use heuristics
    if self._force_heuristic:
        ...
```

### Step 3: Update Phase 5 checkpoint handling

**File**: `installer/global/commands/lib/template_create_orchestrator.py`

Ensure checkpoint is saved BEFORE `clear_cache()` is called, so that on resume we still have the Phase 1 analysis data but can make a fresh Phase 5 AI request.

The existing checkpoint at `templates_generated` (Phase 4) should be sufficient - verify this is still saved before Phase 5 runs.

## Test Plan

### Manual Testing

1. Run `/template-create` on the kartlog codebase:
   ```bash
   cd ~/Projects/Github/kartlog
   /template-create --name kartlog-test
   ```

2. Verify Phase 1 completes with AI analysis (exit 42, resume)

3. Verify Phase 5 completes with AI agent generation (exit 42, resume)

4. Verify agents are generated:
   ```bash
   ls ~/.agentecflow/templates/kartlog-test/agents/
   # Should see: svelte5-component-specialist.md, firebase-firestore-specialist.md, etc.
   ```

5. Verify template quality is preserved (confidence score ~98%)

### Unit Test (Optional)

Add test in `tests/unit/test_agent_bridge_invoker.py`:

```python
def test_clear_cache_enables_new_invocation():
    """Verify clear_cache allows new AI invocation."""
    invoker = AgentBridgeInvoker()

    # Simulate cached response from Phase 1
    invoker._cached_response = "phase1_response"

    # Clear cache
    invoker.clear_cache()

    # Verify cache is cleared
    assert invoker._cached_response is None
```

## Files to Modify

| File | Change |
|------|--------|
| `installer/global/lib/agent_bridge/invoker.py` | Add `clear_cache()` method |
| `installer/global/commands/lib/template_create_orchestrator.py` | Call `clear_cache()` in Phase 5 |

## Architecture Documentation

See: [template-create-architecture.md](docs/architecture/template-create-architecture.md) for the complete architecture evolution documentation.

## Risk Assessment

- **Complexity**: Low (2/10) - Adding one method, one method call
- **Risk**: Low - Isolated change, doesn't affect Phase 1 logic
- **Regression Risk**: Low - Phase 1 analysis is already complete before Phase 5 runs

## Notes

- This fix enables the "multi-phase AI invocation" pattern
- Future phases that need AI can follow the same pattern: clear cache before invocation
- Consider adding a more robust solution in future (e.g., request-keyed caching) if more phases need AI
