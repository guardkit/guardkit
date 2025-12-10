---
id: TASK-FW-005
title: Add parallel group detection (file conflict analysis)
status: completed
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T13:00:00Z
completed: 2025-12-04T09:42:42Z
priority: high
tags: [feature-workflow, parallel-execution, conductor]
complexity: 6
implementation_mode: task-work
parallel_group: 2
conductor_workspace: feature-workflow-2
parent_review: TASK-REV-FW01
test_coverage: 96%
tests_passing: 42/42
architectural_score: 82/100
code_review_score: 9.2/10
completion_metrics:
  files_created: 2
  lines_of_code: 974
  tests_written: 42
  test_execution_time: 1.30s
  final_coverage: 96%
  requirements_met: 6/6
---

# Parallel Group Detection (File Conflict Analysis)

## Description

Analyze subtask file lists to identify which tasks can run in parallel (no file conflicts) and group them into waves for Conductor execution.

## Acceptance Criteria

- [x] Detect file conflicts between subtasks
- [x] Group non-conflicting tasks into parallel groups (waves)
- [x] Respect explicit dependencies if specified
- [x] Assign `parallel_group` number to each subtask
- [x] Tasks with conflicts are properly handled (all tasks get wave numbers for ordering)
- [x] Generate Conductor workspace suggestions

## Implementation Details

### Conflict Detection Algorithm

```python
def detect_parallel_groups(subtasks: list[dict]) -> list[dict]:
    """
    Analyze file conflicts and assign parallel groups.

    Algorithm:
    1. Build file → task mapping
    2. Identify tasks with overlapping files
    3. Group non-conflicting tasks into waves
    4. Tasks with dependencies go in later waves
    """

    # Build file → task mapping
    file_to_tasks = defaultdict(set)
    for task in subtasks:
        for file in task.get("files", []):
            file_to_tasks[file].add(task["id"])

    # Build conflict graph
    conflicts = defaultdict(set)
    for file, task_ids in file_to_tasks.items():
        if len(task_ids) > 1:
            for task_id in task_ids:
                conflicts[task_id].update(task_ids - {task_id})

    # Greedy wave assignment
    waves = []
    remaining = set(t["id"] for t in subtasks)

    while remaining:
        # Find tasks that don't conflict with current wave
        current_wave = []
        wave_files = set()

        for task_id in list(remaining):
            task = next(t for t in subtasks if t["id"] == task_id)
            task_files = set(task.get("files", []))

            # Check for file conflicts with current wave
            if not task_files.intersection(wave_files):
                # Check for dependency conflicts
                deps = set(task.get("dependencies", []))
                if not deps.intersection(remaining):
                    current_wave.append(task_id)
                    wave_files.update(task_files)
                    remaining.remove(task_id)

        if current_wave:
            waves.append(current_wave)
        else:
            # Deadlock - add one task as sequential
            task_id = remaining.pop()
            waves.append([task_id])

    # Assign parallel groups
    for wave_num, wave_tasks in enumerate(waves, 1):
        for task_id in wave_tasks:
            task = next(t for t in subtasks if t["id"] == task_id)
            if len(wave_tasks) > 1:
                task["parallel_group"] = wave_num
            else:
                task["parallel_group"] = None  # Sequential

    return subtasks
```

### Conductor Workspace Suggestions

```python
def generate_workspace_names(subtasks: list[dict], feature_slug: str) -> dict:
    """
    Generate Conductor workspace names for parallel tasks.

    Returns: {task_id: workspace_name}
    """
    workspaces = {}
    wave_counts = defaultdict(int)

    for task in subtasks:
        group = task.get("parallel_group")
        if group is not None:
            wave_counts[group] += 1
            workspace_num = wave_counts[group]
            workspaces[task["id"]] = f"{feature_slug}-wave{group}-{workspace_num}"

    return workspaces
```

## Files to Create/Modify

- `installer/core/lib/parallel_analyzer.py` (NEW)

## Test Cases

### Scenario 1: No Conflicts
```
Task A: [file1.py]
Task B: [file2.py]
Task C: [file3.py]
→ All in Wave 1 (parallel)
```

### Scenario 2: File Conflict
```
Task A: [file1.py, file2.py]
Task B: [file2.py, file3.py]  # Conflicts with A
Task C: [file4.py]
→ Wave 1: A, C (parallel)
→ Wave 2: B (sequential after A)
```

### Scenario 3: Chain Dependency
```
Task A: [file1.py]
Task B: [file2.py] depends on A
Task C: [file3.py] depends on B
→ Wave 1: A
→ Wave 2: B
→ Wave 3: C
```

## Dependencies

- TASK-FW-003 (provides subtask definitions with file lists)

## Notes

Complexity 6 due to graph algorithm. This is the most complex task in Wave 2.
Consider using networkx library if available for graph operations.

## Implementation Summary

**Status:** ✅ Complete and approved for merge

**Files Created:**
- `installer/core/lib/parallel_analyzer.py` (398 lines, 96% coverage)
- `tests/test_parallel_analyzer.py` (576 lines, 42 tests)

**Test Results:**
- All 42 tests passing
- Coverage: 96% (exceeds 90% threshold)
- Test execution time: 1.30s

**Quality Metrics:**
- Architectural Review: 82/100 (approved with recommendations)
- Code Review: 9.2/10 (excellent)
- Documentation: Comprehensive with examples
- Error Handling: Robust input validation

**Key Features Implemented:**
1. File-to-tasks mapping with conflict detection
2. Greedy wave assignment algorithm (O(n²) time complexity)
3. Dependency resolution and validation
4. Workspace name generation for Conductor integration
5. Immutable design (doesn't mutate input)
6. Deterministic results (sorted order iteration)

**Design Decisions:**
- All tasks get wave numbers (even single-task waves) for consistent ordering
- Workspace names only generated for multi-task waves (parallel execution)
- Tasks sorted by file count (descending) for better wave efficiency
- Iterate in sorted order (not set order) for deterministic results

**Optional Enhancements (Not Blocking):**
1. Add circular dependency detection (fail fast with clear error)
2. Add feature slug validation in workspace name generation
3. Add workflow example to module docstring
4. Add test for circular dependencies

**Production Ready:** Yes - Code is maintainable, well-tested, and robust.
