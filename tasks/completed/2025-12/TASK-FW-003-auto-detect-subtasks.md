---
id: TASK-FW-003
title: Auto-detect subtasks from review recommendations
status: completed
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T08:14:34Z
completed_at: 2025-12-04T08:14:34Z
priority: high
tags: [feature-workflow, auto-detection, parsing]
complexity: 5
implementation_mode: task-work
parallel_group: 2
conductor_workspace: feature-workflow-2
parent_review: TASK-REV-FW01
completion_metrics:
  total_duration: 5.5h
  implementation_time: 3h
  testing_time: 2h
  review_time: 0.5h
  test_iterations: 3
  final_coverage: 87
  tests_passed: 28
  tests_total: 28
  files_created: 2
  lines_added: 914
---

# Auto-detect Subtasks from Review Recommendations

## Description

Parse the review report recommendations section to automatically generate subtask definitions.

## Acceptance Criteria

- [x] Parse review report markdown to extract recommendations
- [x] Each actionable recommendation becomes a subtask
- [x] Extract subtask title from recommendation text
- [x] Infer files to modify from recommendation context
- [x] Generate sequential task IDs with feature prefix
- [x] Handle various recommendation formats (numbered, bulleted, etc.)

## Implementation Details

### Parsing Logic

```python
def extract_subtasks_from_review(review_report_path: str, feature_slug: str) -> list[dict]:
    """
    Parse review report and extract subtasks from recommendations.

    Returns list of subtask definitions:
    [
        {
            "id": "TASK-DM-001",
            "title": "Add CSS variables for dark mode",
            "description": "...",
            "files": ["src/styles/variables.css"],
            "complexity": 3,
            "implementation_mode": None,  # Set by FW-004
            "parallel_group": None,  # Set by FW-005
        },
        ...
    ]
    """
```

### Recommendation Section Detection

Look for these section headers:
- `## Recommendations`
- `## Implementation Plan`
- `## Suggested Changes`
- `## Action Items`

### Subtask Extraction Patterns

1. **Numbered list**:
   ```markdown
   1. Add CSS variables for theming
   2. Create theme toggle component
   ```

2. **Bulleted list**:
   ```markdown
   - Add CSS variables for theming
   - Create theme toggle component
   ```

3. **Task table**:
   ```markdown
   | Task | Description |
   |------|-------------|
   | Add CSS variables | ... |
   ```

### File Inference

Look for file mentions in recommendation text:
- Explicit paths: `src/components/Button.tsx`
- Component names: "Update the Button component"
- Directory references: "in the styles folder"

## Files to Create/Modify

- `installer/core/lib/review_parser.py` (NEW)

## Test Cases

1. Parse numbered recommendations list
2. Parse bulleted recommendations list
3. Parse recommendations with file references
4. Handle empty recommendations section
5. Handle malformed markdown

## Dependencies

None - can run in parallel with FW-004, FW-005, FW-006.

## Notes

Complexity 5 due to markdown parsing edge cases.
Recommend using existing markdown parsing library if available.
