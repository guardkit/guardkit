# Implementation Plan: TASK-FW-005 - Parallel Group Detection

## Overview
Implement file conflict analysis to detect which subtasks can run in parallel and group them into waves for Conductor execution.

## Technical Approach

### 1. Core Algorithm Design
- **Conflict Detection**: Build a file-to-tasks mapping to identify overlapping file usage
- **Graph-Based Grouping**: Use greedy wave assignment to group non-conflicting tasks
- **Dependency Handling**: Respect explicit task dependencies when forming waves
- **Workspace Naming**: Generate Conductor workspace names for parallel execution

### 2. Implementation Structure

#### Module: `installer/global/lib/parallel_analyzer.py`

**Functions to Implement:**
1. `detect_parallel_groups(subtasks: list[dict]) -> list[dict]`
   - Build file → task mapping using defaultdict
   - Create conflict graph for tasks sharing files
   - Use greedy algorithm to assign tasks to waves
   - Handle dependency constraints
   - Assign `parallel_group` numbers (or None for sequential)

2. `generate_workspace_names(subtasks: list[dict], feature_slug: str) -> dict`
   - Generate workspace names in format: `{feature_slug}-wave{N}-{num}`
   - Track wave counts to number workspaces within waves
   - Return mapping of task_id → workspace_name

3. `analyze_file_conflicts(subtasks: list[dict]) -> dict`
   - Helper function to identify which tasks conflict
   - Returns conflict graph: {task_id: set(conflicting_task_ids)}

### 3. Algorithm Details

**Wave Assignment Logic:**
```
Initialize: All tasks unassigned
While unassigned tasks remain:
  1. Create new wave
  2. For each unassigned task:
     - Check if task files conflict with current wave files
     - Check if task dependencies are satisfied
     - If no conflicts and deps satisfied, add to current wave
  3. If wave is empty (deadlock), add one task as sequential
  4. Mark wave tasks as assigned
```

**Dependency Handling:**
- Tasks with dependencies only eligible after dependency waves complete
- Dependencies tracked via `dependencies` field in task metadata
- Circular dependencies detected and flagged as errors

### 4. Data Structures

**Input Format:**
```python
subtasks = [
    {
        "id": "TASK-FW-005.1",
        "files": ["file1.py", "file2.py"],
        "dependencies": []  # Optional
    },
    ...
]
```

**Output Format:**
```python
# Tasks with parallel_group assigned
subtasks = [
    {
        "id": "TASK-FW-005.1",
        "files": ["file1.py", "file2.py"],
        "parallel_group": 1,
        "conductor_workspace": "feature-workflow-wave1-1"
    },
    ...
]
```

### 5. Edge Cases to Handle

1. **No Conflicts**: All tasks in Wave 1
2. **All Conflicts**: Each task in separate wave
3. **Partial Conflicts**: Mixed waves with some parallel, some sequential
4. **Chain Dependencies**: A→B→C results in 3 waves
5. **Diamond Dependencies**: A→B,C→D results in 3 waves
6. **Empty File Lists**: Tasks with no files can run anywhere
7. **Circular Dependencies**: Detect and raise error

### 6. Test Coverage Plan

#### Unit Tests (`tests/test_parallel_analyzer.py`):
- Test conflict detection with various file patterns
- Test wave assignment for each scenario
- Test dependency resolution
- Test workspace name generation
- Test edge cases (empty lists, single task, etc.)

#### Integration Tests:
- Test with real subtask data structures
- Verify output format matches expected schema
- Test error handling for invalid inputs

**Target Coverage:** ≥ 90% (complex algorithm requires thorough testing)

## Implementation Steps

### Step 1: Core Conflict Detection (30 min)
- Implement file-to-tasks mapping
- Build conflict graph
- Unit tests for conflict detection

### Step 2: Wave Assignment Algorithm (45 min)
- Implement greedy wave assignment
- Handle dependency constraints
- Add deadlock detection
- Unit tests for various scenarios

### Step 3: Workspace Naming (15 min)
- Implement workspace name generation
- Test with different feature slugs
- Verify uniqueness

### Step 4: Integration & Polish (30 min)
- Add comprehensive docstrings
- Add input validation
- Add error handling
- Integration tests

### Step 5: Documentation (15 min)
- Add module-level documentation
- Document algorithm complexity
- Add usage examples

## Estimated LOC
- Implementation: ~150 lines
- Tests: ~300 lines
- Documentation: ~50 lines
**Total: ~500 lines**

## Estimated Duration
**2.5 hours** (matches complexity rating of 6/10)

## Dependencies
- Python 3.8+ (for typing support)
- collections.defaultdict (standard library)
- No external dependencies required (networkx optional but not needed)

## Success Criteria
- [ ] All acceptance criteria met
- [ ] Test coverage ≥ 90%
- [ ] All test scenarios pass
- [ ] Code follows Python best practices (PEP 8)
- [ ] Comprehensive documentation
- [ ] No external dependencies added

## Risk Assessment
- **Low Risk**: Algorithm is well-defined with clear test cases
- **Medium Complexity**: Graph operations require careful testing
- **No Breaking Changes**: New functionality, doesn't modify existing code
