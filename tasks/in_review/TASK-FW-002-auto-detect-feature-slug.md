---
id: TASK-FW-002
title: Auto-detect feature slug from review task title
status: in_review
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T16:30:00Z
priority: high
tags: [feature-workflow, auto-detection]
complexity: 3
implementation_mode: direct
parallel_group: 1
conductor_workspace: victoria
parent_review: TASK-REV-FW01
---

# Auto-detect Feature Slug from Review Task Title

## Description

Implement logic to automatically extract a feature slug from the review task title for use in subfolder naming.

## Acceptance Criteria

- [x] Extract feature name from review task title
- [x] Remove common prefixes: "Plan:", "Review:", "Investigate:", "Analyze:"
- [x] Convert to URL/folder-safe slug (lowercase, hyphens)
- [x] Handle edge cases (empty, very long, special characters)
- [x] Return sensible defaults if extraction fails

## Implementation Details

### Slug Generation Logic

```python
def extract_feature_slug(title: str) -> str:
    """
    Extract feature slug from review task title.

    Examples:
        "Plan: implement dark mode" → "dark-mode"
        "Review: user authentication system" → "user-authentication-system"
        "Investigate how to add caching" → "add-caching"
    """
    # Remove common prefixes
    prefixes = ["plan:", "review:", "investigate:", "analyze:", "assess:"]
    lower_title = title.lower()

    for prefix in prefixes:
        if lower_title.startswith(prefix):
            title = title[len(prefix):].strip()
            break

    # Remove "how to" phrases
    title = re.sub(r'\bhow to\b', '', title, flags=re.IGNORECASE)

    # Convert to slug
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
    slug = slug.strip('-')

    # Limit length
    if len(slug) > 40:
        slug = slug[:40].rsplit('-', 1)[0]

    return slug or "feature"
```

### Integration Point

This will be called by the enhanced [I]mplement flow (TASK-FW-008) to determine the subfolder name.

## Files to Create/Modify

- `installer/global/lib/feature_utils.py` (NEW or add to existing utils)

## Test Cases

| Input | Expected Output |
|-------|-----------------|
| "Plan: implement dark mode" | "dark-mode" |
| "Review: user authentication system" | "user-authentication-system" |
| "Investigate how to add caching" | "add-caching" |
| "Plan: Add OAuth 2.0 Support!!!" | "add-oauth-2-0-support" |
| "" | "feature" |
| "Very long title that goes on and on about many things" | "very-long-title-that-goes-on-and-on" |

## Notes

Simple utility function - can be completed in 0.5 days.

## Implementation Summary

### Files Created/Modified

1. **`installer/global/lib/utils/feature_utils.py`** (NEW)
   - Implemented `extract_feature_slug(title: str) -> str` function
   - Handles all acceptance criteria:
     - Removes common prefixes (plan, review, investigate, analyze, assess)
     - Removes "how to" phrases
     - Converts to URL/folder-safe slug (lowercase, hyphens)
     - Handles None input gracefully
     - Handles edge cases (empty, whitespace, unicode, special characters)
     - Limits length to 40 characters with word boundary preservation
     - Returns "feature" as default when extraction fails

2. **`installer/global/lib/utils/__init__.py`**
   - Added export for `extract_feature_slug` function

3. **`tests/lib/test_feature_utils.py`** (NEW)
   - Created comprehensive test suite with 40 test cases
   - 100% code coverage (22 statements, 12 branches)
   - All tests passing

### Test Results

- **Total Tests**: 40
- **Passed**: 40
- **Failed**: 0
- **Coverage**: 100% (line and branch coverage)

### Test Coverage Summary

The test suite covers:
- All 5 prefix removal scenarios (plan, review, investigate, analyze, assess)
- "How to" phrase removal (case insensitive)
- Special character conversion to hyphens
- Length limiting with word boundary preservation
- Empty/whitespace/None input handling
- Unicode character handling
- Real-world examples from task specification
- Edge cases (very short, very long, no hyphens, etc.)

### Integration Point

This function is ready to be called by the enhanced [I]mplement flow (TASK-FW-008) to determine the subfolder name when creating implementation tasks from review tasks.
