# Agent Response File Path Bug - Fix Summary

## The Bug

Claude Code wrote `.agent-response.json` (relative path) instead of `/absolute/path/.agent-response.json`, causing the orchestrator to never find the response file.

## Root Cause

**Line 1258 of `template-create.md` showed the WRONG pattern**:

```markdown
# CORRECT: Write(.agent-response.json) at the path in response_file_path  ← BUG!
```

Claude Code extracted the pattern `Write(.agent-response.json)` and ignored "at the path in response_file_path" because it was ambiguous English, not code.

## The Fix

Changed line 1258 to show explicit tool invocation syntax:

```markdown
# CORRECT: Write(file_path=response_file_path, content=response_json)
#          where response_file_path is the ABSOLUTE path from the request JSON
# WRONG:   Write(file_path=".agent-response.json", content=response_json)
```

Also added explicit print statements showing the exact syntax:

```python
print(f"  ⚠️  When calling Write, use: Write(file_path='{absolute_response_path}', content=...)")
print(f"  ⚠️  DO NOT use: Write(file_path='.agent-response.json', content=...)")
```

## Why It Works

1. **Unambiguous**: Shows exact tool syntax, not English description
2. **Variable usage clear**: "use variable X as parameter Y"
3. **Contrast**: Shows CORRECT vs WRONG side-by-side
4. **Runtime guidance**: Print statements show exact syntax during execution

## Why Previous Fixes Failed

All 20+ previous attempts added MORE text (comments, prints, variables, validation) but didn't fix the **core example pattern** that Claude Code uses for pattern-matching.

**Lesson**: The example pattern is the single source of truth. Fix it first, not last.

## Testing

Run template creation and verify:

```bash
# Should see ABSOLUTE path in output:
⏺ Write(/Users/.../codebase/.agent-response.json)  ← CORRECT ✓

# NOT relative path:
⏺ Write(.agent-response.json)  ← BUG ✗
```

## Files Changed

- `installer/global/commands/template-create.md` (3 changes):
  - Lines 1258-1261: Fixed example pattern
  - Lines 1356-1357: Added explicit print statements
  - Lines 1394-1399: Clarified Write tool usage

## Documentation

Full root cause analysis: `docs/debugging/AGENT-RESPONSE-FILE-PATH-BUG-RCA.md`
