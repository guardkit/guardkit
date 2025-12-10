# TASK-FIX-PD05: Fix "When to Use" Guidance Accuracy

## Problem Summary

The `_enhance_agent_info_with_ai` method in `claude_md_generator.py` has a flawed fallback logic that incorrectly categorizes agents. Specifically, the keyword 'view' (from "view Firestore data") causes database agents to be incorrectly categorized as UI agents.

## Solution Provided

A fix script has been created: `apply_fix_pd05.py`

### To Apply the Fix:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
python3 apply_fix_pd05.py
```

This script will:
1. Add the new `_categorize_agent_by_keywords` method with proper keyword prioritization
2. Replace the fallback logic in `_enhance_agent_info_with_ai` with the new categorization approach
3. Remove the problematic 'view' keyword from UI detection

### What Gets Fixed:

**Before:**
```python
elif 'ui' in desc_lower or 'view' in desc_lower:  # BUG: 'view' is too generic
    when_to_use = "Use this agent when creating UI components..."
```

**After:**
```python
# Use proper categorization with database check happening FIRST
category = self._categorize_agent_by_keywords(agent_metadata)
when_to_use = when_to_use_templates.get(category)
```

### Expected Behavior After Fix:

- Firebase Firestore agent: "Use this agent when implementing database operations..." (CORRECT - database)
- React component agent: "Use this agent when creating UI components..." (CORRECT - UI)
- FastAPI endpoint agent: "Use this agent when creating API endpoints..." (CORRECT - API)

## Implementation Details

The new `_categorize_agent_by_keywords` method:
- Uses 6 category levels: database, testing, api, domain, ui, general
- Checks technologies first (most reliable signal)
- Falls back to description keywords with priority ordering
- Database keywords checked BEFORE UI keywords to prevent false matches
- Removed 'view' from UI keywords list

## Verification

After running the fix script, verify with:

```bash
# Check that new method exists
grep -n "_categorize_agent_by_keywords" \
  installer/core/lib/template_generator/claude_md_generator.py

# Verify problematic code removed
grep -n "'view' in desc_lower" \
  installer/core/lib/template_generator/claude_md_generator.py
# Should return: (no results)

# Run tests
pytest tests/unit/test_completeness_validator.py -v
pytest tests/lib/test_claude_md_generator.py -v
```

## Files Modified

- `installer/core/lib/template_generator/claude_md_generator.py`
  - Added: `_categorize_agent_by_keywords` method
  - Modified: Fallback logic in `_enhance_agent_info_with_ai`

## References

This fix addresses the architectural review findings from TASK-REV-TC01, ensuring accurate "When to Use" guidance for all agent types.
