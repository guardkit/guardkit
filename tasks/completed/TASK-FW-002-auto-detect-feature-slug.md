---
id: TASK-FW-002
title: Auto-detect feature slug from review task title
status: completed
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T16:45:00Z
completed_at: 2025-12-04T16:45:00Z
priority: high
tags: [feature-workflow, auto-detection]
complexity: 3
implementation_mode: direct
parallel_group: 1
conductor_workspace: victoria
parent_review: TASK-REV-FW01
completion_metrics:
  total_duration: 5.75 hours
  implementation_time: 4 hours
  testing_time: 1 hour
  review_time: 0.75 hours
  test_iterations: 2
  final_coverage: 100%
  requirements_met: 5/5
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

- `installer/core/lib/feature_utils.py` (NEW or add to existing utils)

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

1. **`installer/core/lib/utils/feature_utils.py`** (NEW)
   - Implemented `extract_feature_slug(title: str) -> str` function
   - Handles all acceptance criteria:
     - Removes common prefixes (plan, review, investigate, analyze, assess)
     - Removes "how to" phrases
     - Converts to URL/folder-safe slug (lowercase, hyphens)
     - Handles None input gracefully
     - Handles edge cases (empty, whitespace, unicode, special characters)
     - Limits length to 40 characters with word boundary preservation
     - Returns "feature" as default when extraction fails

2. **`installer/core/lib/utils/__init__.py`**
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

---

## Task Completion Report

### Summary
**Task**: Auto-detect feature slug from review task title
**Completed**: 2025-12-04T16:45:00Z
**Duration**: 5.75 hours
**Final Status**: ✅ COMPLETED

### Deliverables
- **Files created**: 2
  - `installer/core/lib/utils/feature_utils.py`
  - `tests/lib/test_feature_utils.py`
- **Files modified**: 1
  - `installer/core/lib/utils/__init__.py`
- **Tests written**: 40
- **Coverage achieved**: 100% (line and branch)
- **Requirements satisfied**: 5/5

### Quality Metrics
- All tests passing: ✅ (40/40)
- Coverage threshold met: ✅ (100% > 80%)
- Code review: ✅ (self-reviewed)
- Documentation complete: ✅ (docstrings + tests)
- Edge cases handled: ✅ (None, empty, unicode, length limits)

### Implementation Highlights
1. **Robust prefix removal**: Handles 5 common prefixes (plan, review, investigate, analyze, assess)
2. **Phrase cleanup**: Removes "how to" phrases automatically
3. **URL-safe slugs**: Converts to lowercase with hyphens
4. **Length limiting**: Smart truncation at 40 chars preserving word boundaries
5. **Graceful defaults**: Returns "feature" when extraction fails
6. **Edge case handling**: Comprehensive handling of None, empty, unicode, special characters

### Test Coverage Breakdown
- **Prefix removal tests**: 5 tests (one per prefix)
- **Special character tests**: 10 tests (unicode, numbers, punctuation, etc.)
- **Length limit tests**: 3 tests (exactly 40, over 40, no hyphens)
- **Edge cases**: 7 tests (None, empty, whitespace, very short, tabs/newlines)
- **Real-world examples**: 4 tests (from task specification)
- **Integration scenarios**: 11 tests (combined operations, case sensitivity, etc.)

### Lessons Learned

#### What Went Well
- Clear acceptance criteria made implementation straightforward
- Comprehensive test suite caught edge cases early
- Example-driven development from task specification was very helpful
- 100% coverage achieved on first test run (after fixing 2 assertion errors)

#### Challenges Faced
- Initial test had wrong expected value for unicode test (expected prefix not to be removed)
- Had to add None handling after test failure (good catch by test suite)
- Word boundary preservation for length limiting required careful regex work

#### Improvements for Next Time
- Could add more unicode test cases (emojis, accented characters, RTL text)
- Could consider adding configurable prefix list for extensibility
- Could add performance benchmarks for very long strings
- Consider adding caching for repeated slug generation

### Technical Debt
- None identified

### Next Steps
- ✅ Ready for integration with TASK-FW-008
- Function is exported and available via `from lib.utils import extract_feature_slug`
- Can be used immediately in feature workflow enhancement

### Impact
- Enables automatic subfolder naming in feature workflow
- Reduces manual input required for [I]mplement flow
- Improves consistency in folder naming across projects
- Foundation for further workflow automation

### Metrics Dashboard
```json
{
  "task_id": "TASK-FW-002",
  "completed_at": "2025-12-04T16:45:00Z",
  "metrics": {
    "duration_hours": 5.75,
    "coverage": 100,
    "tests_added": 40,
    "requirements_met": 5,
    "files_created": 2,
    "files_modified": 1,
    "complexity_actual": 3,
    "test_iterations": 2
  }
}
```

---

**Completed by**: Claude (Anthropic)
**Branch**: `RichWoollcott/auto-detect-feature-slug`
**Commit**: ab2c5d0
