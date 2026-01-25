# Completion Report: TASK-FIX-C4D8

## Summary

**Task**: Fix Direct Mode SDK max_turns
**Status**: COMPLETED
**Completed**: 2026-01-25T19:45:00Z
**Duration**: ~15 minutes (direct mode fix)

## Changes Made

### Code Changes

1. **guardkit/orchestrator/agent_invoker.py** (lines 1221-1223)
   - Changed `max_turns=self.max_turns_per_agent` to `max_turns=TASK_WORK_SDK_MAX_TURNS`
   - Added explanatory comments referencing TASK-REV-C4D7 and TASK-REV-BB80

2. **tests/unit/test_agent_invoker.py** (lines 11-18, 627-629)
   - Added import for `TASK_WORK_SDK_MAX_TURNS`
   - Updated test assertion to expect `TASK_WORK_SDK_MAX_TURNS` instead of `agent_invoker.max_turns_per_agent`

### Diff

```diff
--- a/guardkit/orchestrator/agent_invoker.py
+++ b/guardkit/orchestrator/agent_invoker.py
@@ -1216,7 +1221,9 @@ class AgentInvoker:
         try:
             options = ClaudeAgentOptions(
                 cwd=str(self.worktree_path),
                 allowed_tools=allowed_tools,
                 permission_mode=permission_mode,
-                max_turns=self.max_turns_per_agent,
+                # TASK-REV-C4D7: Direct mode also needs ~50 internal turns
+                # (same as task-work delegation path fixed in TASK-REV-BB80)
+                max_turns=TASK_WORK_SDK_MAX_TURNS,
                 model=model,
                 setting_sources=["project"],
             )
```

## Quality Gates

| Gate | Status | Notes |
|------|--------|-------|
| Unit Tests | PASSED | 267/267 tests pass |
| Code Review | PASSED | Single-line fix with clear comments |
| Security | N/A | No security implications |
| Coverage | N/A | No new code paths |

## Verification

To verify the fix works:

```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-F392 --max-turns 15
```

Expected behavior:
- All 6 tasks should complete (vs 0 previously)
- Wave 1 parallel tasks should pass
- Duration should be ~30-60 minutes (vs 54 seconds)
- Logs should show `Max turns: 50` for direct mode invocations

## Related Tasks

- **TASK-REV-BB80**: Original SDK max_turns regression fix (task-work delegation path)
- **TASK-REV-C4D7**: Review that identified the direct mode path was not fixed
