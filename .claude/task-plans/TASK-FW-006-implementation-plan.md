# Implementation Plan: TASK-FW-006 - Implementation Guide Generator

## Overview

Generate IMPLEMENTATION-GUIDE.md files from subtask definitions, following the established template pattern. The guide includes wave breakdowns, parallel execution strategies, method selection rationale, and Conductor workspace recommendations.

## Technical Approach

### 1. Core Function Design

**Module**: `installer/core/lib/guide_generator.py`

**Main Functions**:
```python
def generate_guide_content(
    feature_name: str,
    subtasks: list[dict]
) -> str:
    """Generate IMPLEMENTATION-GUIDE.md content (returns string)."""

def write_guide_to_file(content: str, output_path: str) -> None:
    """Write guide content to file."""
```

**Helper Functions**:
1. `_normalize_subtask(task: dict) -> SubtaskData` - Apply defaults and create dataclass
2. `_format_method(method: str) -> str` - Use METHOD_DISPLAY_NAMES lookup
3. `_generate_default_rationale(method: str) -> str` - Use RATIONALE_TEMPLATES lookup
4. `_group_tasks_by_wave(subtasks: list[SubtaskData]) -> dict[int, list[SubtaskData]]`
5. `_generate_overview(feature_name: str, task_count: int) -> str`
6. `_generate_method_legend() -> str`
7. `_generate_conductor_section(repo_name: str, waves: dict) -> str`
8. `_generate_wave_section(wave_num: int, wave_tasks: list, feature_name: str) -> str`
9. `_generate_task_detail(task: SubtaskData) -> str`
10. `_generate_task_matrix(subtasks: list[SubtaskData]) -> str`
11. `_generate_method_breakdown(subtasks: list[SubtaskData]) -> str`
12. `_generate_execution_order(waves: dict) -> str`

### 2. Data Structure Analysis

**Data Class** (normalized subtask with defaults):
```python
from dataclasses import dataclass, field

@dataclass
class SubtaskData:
    """Normalized subtask with defaults applied."""
    id: str
    title: str
    implementation_method: str = "task-work"
    complexity: int = 5
    estimated_effort_days: float = 1.0
    parallel_group: int = 1
    conductor_workspace: str = ""
    dependencies: list[str] = field(default_factory=list)
    rationale: str = ""
    execution_command: str = ""
```

**Constant Lookups** (OCP compliance):
```python
# Method display names (extensible without code changes)
METHOD_DISPLAY_NAMES = {
    "task-work": "/task-work",
    "direct": "Direct Claude Code",
    "manual": "Manual",
}

# Rationale templates (extensible without code changes)
RATIONALE_TEMPLATES = {
    "task-work": "Full GuardKit workflow with quality gates (architecture review, tests, code review).",
    "direct": "Straightforward changes with clear acceptance criteria and low integration risk.",
    "manual": "Human execution of automated script with review of output.",
}
```

**Input Format** (raw subtask dictionary):
```python
{
    "id": "TASK-FW-003.1",
    "title": "Create Subtask Definition Schema",
    "implementation_method": "task-work",  # Optional (defaults to "task-work")
    "complexity": 5,  # Optional (defaults to 5)
    "estimated_effort_days": 1.5,  # Optional (defaults to 1.0)
    "parallel_group": 1,  # Optional (defaults to 1)
    "conductor_workspace": "feature-workflow-wave1-1",  # Optional
    "dependencies": ["TASK-FW-002"],  # Optional
    "rationale": "Why this method was chosen",  # Optional
    "execution_command": "/task-work TASK-FW-003.1"  # Optional
}
```

**Wave Structure** (derived from parallel_group):
```python
waves = {
    1: [task1, task2, task3],  # Parallel execution
    2: [task4],                # Sequential after wave 1
    3: [task5, task6],         # Parallel after wave 2
}
```

### 3. Template Structure Breakdown

**Section 1: Overview**
- Feature name
- Total task count
- Purpose statement

**Section 2: Implementation Method Legend**
- Static table (same for all guides)
- Methods: /task-work, Direct, Manual

**Section 3: Conductor Parallel Execution**
- Workspace strategy diagram
- Repository name
- Wave-based worktree layout

**Section 4-N: Wave Sections** (one per wave)
- Wave title (e.g., "Wave 1: Foundation & Baseline")
- Duration estimate (sum of task efforts)
- Workspace count
- Task details:
  - Task ID and title
  - Attribute table (Method, Complexity, Effort, Parallel)
  - Rationale for method selection
  - Execution commands
  - Quality gates (if applicable)
- Checkpoint (after significant waves)

**Section N+1: Summary Task Matrix**
- Tabular view of all tasks
- Columns: Task, Method, Complexity, Effort, Can Parallel

**Section N+2: Method Breakdown**
- Count and total effort per method
- Helps understand workload distribution

**Section N+3: Execution Order**
- Day-by-day timeline
- Shows sequential flow and parallel opportunities

### 4. Algorithm Details

**Wave Grouping Logic**:
```python
def _group_tasks_by_wave(subtasks: list[dict]) -> dict[int, list[dict]]:
    """Group tasks by parallel_group number (wave)."""
    waves = defaultdict(list)
    for task in subtasks:
        wave_num = task.get("parallel_group", 1)
        waves[wave_num].append(task)
    return dict(sorted(waves.items()))
```

**Method Capitalization**:
- `/task-work` → Display as `/task-work` (literal command)
- `direct` → Display as `Direct Claude Code`
- `manual` → Display as `Manual` (script execution)

**Parallel Detection**:
```python
def _is_parallel(task: dict, wave_tasks: list) -> str:
    """Determine if task can run in parallel."""
    if len(wave_tasks) > 1:
        return "**YES**"
    return "No"
```

**Duration Estimation**:
```python
def _calculate_wave_duration(wave_tasks: list) -> str:
    """Calculate total duration for wave."""
    total_days = sum(task.get("estimated_effort_days", 0) for task in wave_tasks)
    if total_days < 1:
        return f"{total_days * 8:.1f} hours"
    return f"{total_days:.1f} days"
```

### 5. Edge Cases to Handle

1. **Single Task**: Still generates guide (useful for documentation)
2. **All Sequential**: No parallel groups (wave 1, 2, 3, ...)
3. **All Parallel**: Single wave with all tasks
4. **Mixed Dependencies**: Some tasks parallel, some sequential
5. **Missing Fields**: Graceful defaults for optional fields
6. **Empty Rationale**: Generate generic rationale based on method
7. **No Conductor Workspace**: Task not in multi-task wave

### 6. Template Matching Examples

**Example 1: Sequential Tasks**
```python
subtasks = [
    {"id": "A", "parallel_group": 1, "method": "task-work"},
    {"id": "B", "parallel_group": 2, "method": "direct"},
    {"id": "C", "parallel_group": 3, "method": "manual"},
]
# Output: 3 waves, all sequential
```

**Example 2: Parallel Wave**
```python
subtasks = [
    {"id": "A", "parallel_group": 1, "method": "manual"},
    {"id": "B", "parallel_group": 1, "method": "manual"},
    {"id": "C", "parallel_group": 1, "method": "manual"},
    {"id": "D", "parallel_group": 1, "method": "manual"},
]
# Output: 1 wave with 4 parallel tasks (like PD-012 through PD-015)
```

**Example 3: Mixed Pattern**
```python
subtasks = [
    {"id": "A", "parallel_group": 1, "method": "task-work"},
    {"id": "B", "parallel_group": 2, "method": "direct"},
    {"id": "C", "parallel_group": 2, "method": "direct"},
]
# Output: Wave 1 (sequential), Wave 2 (2 parallel)
```

### 7. Default Values and Fallbacks

**Missing Fields**:
- `implementation_method`: Default to "task-work"
- `complexity`: Default to 5
- `estimated_effort_days`: Default to 1.0
- `parallel_group`: Default to sequential (incrementing wave numbers)
- `rationale`: Generate based on method + complexity
- `execution_command`: Generate based on method + task ID

**Rationale Generation**:
```python
def _generate_default_rationale(method: str, complexity: int) -> str:
    if method == "task-work":
        if complexity >= 7:
            return "High-risk changes requiring architectural review, comprehensive tests, and code review."
        elif complexity >= 5:
            return "Moderate complexity requiring integration testing and quality gates."
        else:
            return "Standard implementation with automated quality validation."
    elif method == "direct":
        return "Straightforward changes with clear acceptance criteria, low integration risk."
    elif method == "manual":
        return "Human execution of automated script, requires review of output."
    return "Standard implementation approach."
```

### 8. Test Coverage Plan

#### Unit Tests (`tests/test_guide_generator.py`)

**Test Classes**:
1. `TestGuideGeneration` (8 tests)
   - Generate guide for 5 tasks, 2 waves
   - Generate guide for 10 tasks, 4 waves
   - Generate guide for single task
   - Generate guide for all sequential tasks
   - Generate guide for all parallel tasks
   - Verify output file created
   - Verify markdown structure valid
   - Verify all sections present

2. `TestWaveGrouping` (5 tests)
   - Group tasks by parallel_group
   - Handle missing parallel_group
   - Sort waves by number
   - Handle empty task list
   - Handle single-task waves

3. `TestMethodFormatting` (4 tests)
   - Format task-work method
   - Format direct method
   - Format manual method
   - Handle invalid method

4. `TestDurationCalculation` (5 tests)
   - Calculate wave duration (hours)
   - Calculate wave duration (days)
   - Calculate wave duration (mixed)
   - Handle missing effort values
   - Handle zero effort

5. `TestParallelDetection` (4 tests)
   - Detect parallel tasks (multiple in wave)
   - Detect sequential tasks (single in wave)
   - Handle dependencies
   - Verify conductor workspace presence

6. `TestRationaleGeneration` (6 tests)
   - Generate rationale for task-work (high complexity)
   - Generate rationale for task-work (medium complexity)
   - Generate rationale for direct method
   - Generate rationale for manual method
   - Use provided rationale if present
   - Handle missing method

7. `TestHelperFunctions` (10 tests)
   - Generate overview section
   - Generate method legend
   - Generate conductor section
   - Generate wave section
   - Generate task detail
   - Generate task matrix
   - Generate method breakdown
   - Generate execution order
   - Handle empty waves
   - Handle missing fields

8. `TestIntegration` (4 tests)
   - End-to-end with progressive-disclosure data
   - Verify checkpoints included
   - Verify workspace layout section
   - Compare output to reference template

**Target Coverage**: ≥90% (comprehensive testing of markdown generation logic)

### 9. Implementation Steps

**Step 1: Core Structure (1.5 hours)**
- Implement `_group_tasks_by_wave()`
- Implement `_format_method()`
- Implement `_calculate_wave_duration()`
- Implement `_is_parallel()`
- Unit tests for core functions

**Step 2: Section Generators (2 hours)**
- Implement `_generate_overview()`
- Implement `_generate_method_legend()`
- Implement `_generate_conductor_section()`
- Implement `_generate_wave_section()`
- Implement `_generate_task_detail()`
- Unit tests for section generators

**Step 3: Summary Generators (1.5 hours)**
- Implement `_generate_task_matrix()`
- Implement `_generate_method_breakdown()`
- Implement `_generate_execution_order()`
- Unit tests for summary generators

**Step 4: Main Function (1 hour)**
- Implement `generate_implementation_guide()`
- Integrate all section generators
- Write to output file
- Integration tests

**Step 5: Edge Cases & Validation (1 hour)**
- Add input validation
- Handle missing fields with defaults
- Implement rationale generation fallback
- Test all edge cases

**Step 6: Documentation (30 min)**
- Add module-level docstrings
- Add function docstrings with examples
- Add inline comments for complex logic

## Estimated LOC
- Implementation: ~400 lines
- Tests: ~500 lines
- Documentation: ~80 lines
**Total: ~980 lines**

## Estimated Duration
**7-8 hours** (matches complexity rating of 5/10)

## Dependencies
- TASK-FW-003: Subtask definition schema (provides input format)
- TASK-FW-004: Implementation mode selection (provides method field)
- TASK-FW-005: Parallel group detection (provides parallel_group field)

## Success Criteria
- [ ] Generate guide matching template format
- [ ] Include all required sections
- [ ] Handle edge cases gracefully
- [ ] Test coverage ≥90%
- [ ] All 46 tests passing
- [ ] Validates against progressive-disclosure reference
- [ ] Clear documentation

## Risk Assessment
- **Low Risk**: Pure markdown generation, no external dependencies
- **Medium Complexity**: Many string formatting operations, multiple sections
- **No Breaking Changes**: New functionality, doesn't modify existing code
