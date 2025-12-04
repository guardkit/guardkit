---
id: TASK-FW-002
title: Auto-detect feature slug from review task title
status: backlog
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T11:00:00Z
priority: high
tags: [feature-workflow, auto-detection]
complexity: 3
implementation_mode: direct
parallel_group: 1
conductor_workspace: feature-workflow-1
parent_review: TASK-REV-FW01
---

# Auto-detect Feature Slug from Review Task Title

## Description

Implement logic to automatically extract a feature slug from the review task title for use in subfolder naming.

## Acceptance Criteria

- [ ] Extract feature name from review task title
- [ ] Remove common prefixes: "Plan:", "Review:", "Investigate:", "Analyze:"
- [ ] Convert to URL/folder-safe slug (lowercase, hyphens)
- [ ] Handle edge cases (empty, very long, special characters)
- [ ] Return sensible defaults if extraction fails

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
