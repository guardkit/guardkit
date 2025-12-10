---
id: TASK-FW-008
title: Update /task-review [I]mplement flow (orchestrate all above)
status: completed
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T14:30:00Z
completed: 2025-12-04T14:30:00Z
priority: high
tags: [feature-workflow, orchestration, integration]
complexity: 5
implementation_mode: task-work
parallel_group: null
conductor_workspace: null
parent_review: TASK-REV-FW01
dependencies: [TASK-FW-002, TASK-FW-003, TASK-FW-004, TASK-FW-005, TASK-FW-006, TASK-FW-007]
completed_location: tasks/completed/TASK-FW-008/
organized_files: [
  "TASK-FW-008-orchestrate-implement-flow.md",
  "implementation-summary.md"
]
---

# Update /task-review [I]mplement Flow

## Description

Orchestrate all the auto-detection and generation components into the enhanced [I]mplement option for `/task-review`.

## Acceptance Criteria

- [x] When [I]mplement chosen, execute full auto-detection pipeline
- [x] Display auto-detected values before proceeding
- [x] Create subfolder `tasks/backlog/{feature-slug}/`
- [x] Generate all subtask files with correct metadata
- [x] Generate IMPLEMENTATION-GUIDE.md
- [x] Generate README.md
- [x] Display summary and next steps

## Implementation Details

### Enhanced [I]mplement Flow

```python
async def handle_implement_option(review_task: dict, review_report_path: str):
    """
    Enhanced [I]mplement handler with full auto-detection.
    """

    # Step 1: Auto-detect feature slug
    feature_slug = extract_feature_slug(review_task["title"])

    # Step 2: Auto-detect subtasks from recommendations
    subtasks = extract_subtasks_from_review(review_report_path, feature_slug)

    # Step 3: Assign implementation modes
    for subtask in subtasks:
        subtask["implementation_mode"] = assign_implementation_mode(subtask)

    # Step 4: Detect parallel groups
    subtasks = detect_parallel_groups(subtasks)

    # Step 5: Display auto-detected values
    print(f"""
✅ Auto-detected:
   Feature slug: {feature_slug}
   Subtasks: {len(subtasks)} (from recommendations)
   Parallel groups: {count_waves(subtasks)} waves
    """)

    # Step 6: Create subfolder
    subfolder = f"tasks/backlog/{feature_slug}"
    os.makedirs(subfolder, exist_ok=True)

    # Step 7: Generate subtask files
    for subtask in subtasks:
        generate_subtask_file(subtask, subfolder)

    # Step 8: Generate IMPLEMENTATION-GUIDE.md
    generate_implementation_guide(
        feature_name=extract_feature_name(review_task["title"]),
        subtasks=subtasks,
        output_path=f"{subfolder}/IMPLEMENTATION-GUIDE.md"
    )

    # Step 9: Generate README.md
    generate_feature_readme(
        feature_name=extract_feature_name(review_task["title"]),
        feature_slug=feature_slug,
        review_task_id=review_task["id"],
        review_report_path=review_report_path,
        subtasks=subtasks,
        output_path=f"{subfolder}/README.md"
    )

    # Step 10: Display summary
    print(f"""
Creating {subfolder}/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
{format_subtask_tree(subtasks)}

Next: Review IMPLEMENTATION-GUIDE.md and start with Wave 1
    """)
```

### Integration Points

| Component | From Task | Function |
|-----------|-----------|----------|
| Feature slug | FW-002 | `extract_feature_slug()` |
| Subtask extraction | FW-003 | `extract_subtasks_from_review()` |
| Implementation mode | FW-004 | `assign_implementation_mode()` |
| Parallel groups | FW-005 | `detect_parallel_groups()` |
| Guide generator | FW-006 | `generate_implementation_guide()` |
| README generator | FW-007 | `generate_feature_readme()` |

## Files to Create/Modify

- `installer/core/commands/task-review.md` (MODIFY - add enhanced [I]mplement)
- `installer/core/lib/implement_orchestrator.py` (NEW - orchestration logic)

## Test Scenarios

1. **Happy path**: Review with clear recommendations
2. **No recommendations**: Graceful error message
3. **Single subtask**: Still creates subfolder structure
4. **Many subtasks**: Correctly groups into waves

## Dependencies

All Wave 2 tasks must complete first:
- TASK-FW-002: Feature slug detection
- TASK-FW-003: Subtask extraction
- TASK-FW-004: Implementation mode tagging
- TASK-FW-005: Parallel group detection
- TASK-FW-006: Guide generator
- TASK-FW-007: README generator

## Notes

This is the integration task - depends on all Wave 1 and Wave 2 tasks.
Must be implemented sequentially (Wave 3).
