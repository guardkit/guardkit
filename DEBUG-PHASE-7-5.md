# Debug: Why Phase 7.5 Didn't Run

## Evidence from Output

1. **Phase 7 executed**: "✓ 8 agent files written"
2. **Phase 7.5 never appeared**: No "Phase 7.5: Agent Enhancement" message
3. **10 agents exist in final output**: All agents were created
4. **Agents are basic**: Still 36 lines (not enhanced)

## Problem Diagnosis

Phase 7.5 is skipped due to this condition in `_complete_workflow()`:

```python
if self.agents:
    agent_paths = self._phase7_write_agents(self.agents, output_path)
    if not agent_paths:  # ← THIS IS TRUE (Phase 7.5 skipped)
        self.warnings.append("Agent writing failed")
    else:
        # Phase 7.5 - NEVER REACHED
        self._save_checkpoint("agents_written", phase=7)
        enhancement_success = self._phase7_5_enhance_agents(output_path)
```

## Possible Causes

### Theory 1: Empty List Bug (Most Likely)
If `_phase7_write_agents()` returns `[]` instead of a list of paths, the condition `if not agent_paths:` would be TRUE because empty lists are falsy in Python.

**Evidence**: Phase 7 message says "8 agent files written" but 10 agents exist in final output. Something is inconsistent.

### Theory 2: Exception Caught Silently
If an exception occurred in `_phase7_write_agents()`, it might return `None`, causing the same issue.

### Theory 3: Wrong Code Path
The resume might be taking a different code path that doesn't include Phase 7.5.

**Evidence against**: We can see Phase 7 executed, and Phase 7.5 should be in the same code block.

## Recommended Fix

### Option 1: Change Condition Logic (Quick Fix)

**Current code**:
```python
if not agent_paths:
    self.warnings.append("Agent writing failed")
else:
    # Phase 7.5
```

**Fixed code**:
```python
if agent_paths is None:
    self.warnings.append("Agent writing failed")
elif len(agent_paths) > 0:  # Explicitly check for non-empty list
    # Phase 7.5
```

This ensures empty list `[]` doesn't block Phase 7.5.

### Option 2: Fix Return Value (Better Fix)

Ensure `_phase7_write_agents()` never returns `[]` when agents exist:

```python
def _phase7_write_agents(self, agents: List[Any], output_path: Path) -> Optional[List[Path]]:
    if not agents:
        return None  # ← Return None instead of [] for "no agents"
    
    # ... write agents ...
    
    if not agent_paths:
        # Something went wrong - no paths created despite having agents
        return None  # ← Indicate failure
    
    return agent_paths  # ← Non-empty list
```

## Testing Steps

1. **Add debug logging** before Phase 7.5 condition:
   ```python
   print(f"DEBUG: agent_paths = {agent_paths}")
   print(f"DEBUG: type(agent_paths) = {type(agent_paths)}")
   print(f"DEBUG: bool(agent_paths) = {bool(agent_paths)}")
   ```

2. **Run template-create again** and check debug output

3. **Check for warnings** in output (should say "Agent writing failed" if condition was TRUE)

## Next Steps

1. Verify which theory is correct by adding debug logging
2. Apply appropriate fix
3. Test with `/template-create --name test-phase-7-5 --validate`
4. Verify Phase 7.5 appears in output
5. Verify agents are enhanced (150-250 lines)
