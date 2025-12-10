"""
Parallel Group Detection for Task Execution

Analyzes file conflicts between subtasks to determine which tasks can run in parallel
and groups them into waves for Conductor execution.

Algorithm:
    1. Build file-to-tasks mapping to identify overlapping files
    2. Create conflict graph for tasks with file conflicts
    3. Use greedy wave assignment to group non-conflicting tasks
    4. Respect explicit dependencies when forming waves
    5. Assign parallel_group numbers (or None for sequential tasks)

Time Complexity: O(n²) where n is the number of subtasks
Space Complexity: O(n + f) where f is the number of unique files

Example:
    >>> subtasks = [
    ...     {"id": "TASK-A", "files": ["file1.py"]},
    ...     {"id": "TASK-B", "files": ["file2.py"]},
    ...     {"id": "TASK-C", "files": ["file1.py"]},  # Conflicts with TASK-A
    ... ]
    >>> result = detect_parallel_groups(subtasks)
    >>> # Wave 1: TASK-A, TASK-B (parallel)
    >>> # Wave 2: TASK-C (sequential after TASK-A)
"""

from collections import defaultdict
from typing import Dict, List, Set, Optional, Any


def _build_file_to_tasks_mapping(subtasks: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    Build mapping of files to tasks that modify them.

    Args:
        subtasks: List of task dictionaries with 'id' and 'files' fields

    Returns:
        Dictionary mapping file paths to sets of task IDs that touch them

    Example:
        >>> tasks = [
        ...     {"id": "A", "files": ["f1.py", "f2.py"]},
        ...     {"id": "B", "files": ["f2.py", "f3.py"]},
        ... ]
        >>> result = _build_file_to_tasks_mapping(tasks)
        >>> result["f2.py"] == {"A", "B"}
        True
    """
    file_to_tasks: Dict[str, Set[str]] = defaultdict(set)

    for task in subtasks:
        task_id = task["id"]
        files = task.get("files", [])

        # Filter valid file paths
        valid_files = [f for f in files if f and isinstance(f, str)]

        for file_path in valid_files:
            file_to_tasks[file_path].add(task_id)

    return dict(file_to_tasks)


def _build_conflict_graph(file_to_tasks: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """
    Build conflict graph showing which tasks conflict with each other.

    Two tasks conflict if they modify the same file. This creates a graph where
    edges represent conflicts that prevent parallel execution.

    Args:
        file_to_tasks: Mapping of files to tasks that touch them

    Returns:
        Dictionary mapping task IDs to sets of conflicting task IDs

    Example:
        >>> file_map = {"f1.py": {"A", "B"}, "f2.py": {"B", "C"}}
        >>> conflicts = _build_conflict_graph(file_map)
        >>> conflicts["B"] == {"A", "C"}
        True
    """
    conflicts: Dict[str, Set[str]] = defaultdict(set)

    for file_path, task_ids in file_to_tasks.items():
        if len(task_ids) > 1:
            # All tasks touching this file conflict with each other
            for task_id in task_ids:
                # Add all other tasks as conflicts
                conflicts[task_id].update(task_ids - {task_id})

    return dict(conflicts)


def _validate_subtasks(subtasks: List[Dict[str, Any]]) -> None:
    """
    Validate subtasks structure and content.

    Args:
        subtasks: List of task dictionaries to validate

    Raises:
        TypeError: If subtasks is not a list or tasks are malformed
        ValueError: If tasks are missing required fields or have invalid data

    Example:
        >>> _validate_subtasks([{"id": "A", "files": ["f1.py"]}])  # OK
        >>> _validate_subtasks([{"files": ["f1.py"]}])  # Raises ValueError
        Traceback (most recent call last):
            ...
        ValueError: Task missing required 'id' field
    """
    if not isinstance(subtasks, list):
        raise TypeError(f"subtasks must be a list, got {type(subtasks).__name__}")

    for i, task in enumerate(subtasks):
        if not isinstance(task, dict):
            raise TypeError(f"Task at index {i} must be a dict, got {type(task).__name__}")

        if "id" not in task:
            raise ValueError(f"Task at index {i} missing required 'id' field")

        task_id = task["id"]

        # Validate files field if present
        if "files" in task:
            files = task["files"]
            if not isinstance(files, list):
                raise TypeError(f"Task {task_id}: 'files' must be a list, got {type(files).__name__}")

        # Validate dependencies field if present
        if "dependencies" in task:
            deps = task["dependencies"]
            if not isinstance(deps, list):
                raise TypeError(f"Task {task_id}: 'dependencies' must be a list, got {type(deps).__name__}")


def _validate_dependencies(subtasks: List[Dict[str, Any]]) -> None:
    """
    Validate that all task dependencies reference existing tasks.

    Args:
        subtasks: List of task dictionaries with optional 'dependencies' field

    Raises:
        ValueError: If a dependency references a non-existent task

    Example:
        >>> tasks = [
        ...     {"id": "A", "dependencies": ["B"]},
        ...     {"id": "B", "dependencies": []}
        ... ]
        >>> _validate_dependencies(tasks)  # OK
        >>> tasks[0]["dependencies"] = ["C"]
        >>> _validate_dependencies(tasks)  # Raises ValueError
        Traceback (most recent call last):
            ...
        ValueError: Task A: dependency 'C' does not exist
    """
    task_ids = {task["id"] for task in subtasks}

    for task in subtasks:
        deps = task.get("dependencies", [])
        for dep_id in deps:
            if dep_id not in task_ids:
                raise ValueError(f"Task {task['id']}: dependency '{dep_id}' does not exist")


def detect_parallel_groups(subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze file conflicts and assign parallel groups (waves) to subtasks.

    Tasks in the same wave can run in parallel (no file conflicts, dependencies satisfied).
    Tasks assigned to later waves have dependencies or file conflicts with earlier waves.

    Algorithm:
        1. Validate input structure
        2. Sort tasks by file count (descending) for better wave efficiency
        3. Build file-to-tasks mapping and conflict graph
        4. Greedy wave assignment:
           - For each wave, add tasks with no conflicts and satisfied dependencies
           - Continue until all tasks assigned
        5. Assign parallel_group numbers (None for single-task waves)

    Args:
        subtasks: List of task dictionaries. Each task must have:
            - 'id' (str): Unique task identifier
            - 'files' (list[str], optional): Files modified by this task
            - 'dependencies' (list[str], optional): Task IDs that must complete first

    Returns:
        New list of task dictionaries with 'parallel_group' field added.
        Tasks in same group can run in parallel. None means sequential execution.

    Raises:
        TypeError: If input structure is invalid
        ValueError: If tasks reference non-existent dependencies

    Example:
        >>> subtasks = [
        ...     {"id": "A", "files": ["f1.py", "f2.py"]},
        ...     {"id": "B", "files": ["f2.py", "f3.py"]},
        ...     {"id": "C", "files": ["f4.py"]},
        ... ]
        >>> result = detect_parallel_groups(subtasks)
        >>> # Wave 1: A, C (parallel - no conflicts)
        >>> # Wave 2: B (sequential - conflicts with A on f2.py)
        >>> result[0]["parallel_group"]  # A
        1
        >>> result[2]["parallel_group"]  # C
        1
        >>> result[1]["parallel_group"]  # B
        2
    """
    # Validate input
    _validate_subtasks(subtasks)

    # Handle empty list
    if not subtasks:
        return []

    # Validate dependencies reference existing tasks
    _validate_dependencies(subtasks)

    # Clone subtasks to avoid mutation (immutable design)
    result = [task.copy() for task in subtasks]

    # Sort by file count (descending) for better wave efficiency
    # Tasks with more files have more potential conflicts, so assign them first
    result.sort(key=lambda t: len(t.get("files", [])), reverse=True)

    # Build task lookup for O(1) access
    task_by_id = {task["id"]: task for task in result}

    # Build file-to-tasks mapping
    file_to_tasks = _build_file_to_tasks_mapping(result)

    # Build conflict graph
    conflicts = _build_conflict_graph(file_to_tasks)

    # Greedy wave assignment
    waves: List[List[str]] = []
    remaining_set = {task["id"] for task in result}
    assigned_to_previous_waves: Set[str] = set()

    while remaining_set:
        # Create new wave
        current_wave: List[str] = []
        wave_files: Set[str] = set()

        # Iterate in sorted order (not set order) for deterministic results
        for task in result:
            task_id = task["id"]
            if task_id not in remaining_set:
                continue
            task = task_by_id[task_id]
            task_files = set(task.get("files", []))

            # Check for file conflicts with current wave
            has_file_conflict = bool(task_files.intersection(wave_files))

            # Check if dependencies are satisfied
            # All dependencies must be in PREVIOUS waves (not current wave)
            deps = set(task.get("dependencies", []))
            unmet_deps = deps - assigned_to_previous_waves
            has_unmet_dependency = bool(unmet_deps)

            # Add to wave if no conflicts and dependencies satisfied
            if not has_file_conflict and not has_unmet_dependency:
                current_wave.append(task_id)
                wave_files.update(task_files)
                remaining_set.remove(task_id)

        # Handle deadlock: no tasks could be added to current wave
        if not current_wave:
            # This should not happen with valid input (no circular deps)
            # Add one arbitrary task to break deadlock
            task_id = remaining_set.pop()
            current_wave.append(task_id)

        waves.append(current_wave)

        # Mark tasks in current wave as assigned for next iteration
        assigned_to_previous_waves.update(current_wave)

    # Assign parallel_group numbers
    for wave_num, wave_tasks in enumerate(waves, start=1):
        for task_id in wave_tasks:
            task = task_by_id[task_id]
            # Assign wave number to all tasks
            # Multiple tasks in same wave = parallel execution
            # Single task in wave = sequential execution, but still gets wave number for ordering
            task["parallel_group"] = wave_num

    return result


def generate_workspace_names(
    subtasks: List[Dict[str, Any]],
    feature_slug: str
) -> Dict[str, str]:
    """
    Generate Conductor workspace names for parallel tasks.

    Workspace names follow the pattern: {feature_slug}-wave{N}-{num}
    where N is the wave number and num is the task number within that wave.

    Only generates names for waves with multiple tasks (actual parallel execution).
    Single-task waves don't need Conductor workspaces.

    Args:
        subtasks: List of task dictionaries (must have 'id' and 'parallel_group' fields)
        feature_slug: Feature identifier slug (e.g., 'feature-workflow')

    Returns:
        Dictionary mapping task IDs to workspace names. Only includes tasks
        in waves with multiple tasks (parallel execution).

    Example:
        >>> subtasks = [
        ...     {"id": "A", "parallel_group": 1},
        ...     {"id": "B", "parallel_group": 1},
        ...     {"id": "C", "parallel_group": 2},  # Alone in wave 2
        ...     {"id": "D", "parallel_group": 3},
        ...     {"id": "E", "parallel_group": 3},
        ... ]
        >>> names = generate_workspace_names(subtasks, "auth-feature")
        >>> names["A"]
        'auth-feature-wave1-1'
        >>> names["B"]
        'auth-feature-wave1-2'
        >>> "C" in names  # Single-task wave, no workspace
        False
        >>> names["D"]
        'auth-feature-wave3-1'
    """
    # Count tasks per wave
    wave_task_counts: Dict[int, int] = defaultdict(int)
    for task in subtasks:
        group = task.get("parallel_group")
        if group is not None:
            wave_task_counts[group] += 1

    # Generate workspace names only for waves with multiple tasks
    workspaces: Dict[str, str] = {}
    wave_counts: Dict[int, int] = defaultdict(int)

    for task in subtasks:
        task_id = task["id"]
        group = task.get("parallel_group")

        # Only generate workspace names for waves with 2+ tasks
        if group is not None and wave_task_counts[group] > 1:
            wave_counts[group] += 1
            workspace_num = wave_counts[group]
            workspaces[task_id] = f"{feature_slug}-wave{group}-{workspace_num}"

    return workspaces


def analyze_file_conflicts(subtasks: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    Identify which tasks have file conflicts with each other.

    This is a helper function that returns the raw conflict graph without
    performing wave assignment. Useful for debugging and analysis.

    Args:
        subtasks: List of task dictionaries with 'id' and 'files' fields

    Returns:
        Dictionary mapping task IDs to sets of conflicting task IDs.
        Tasks not in the dictionary have no conflicts.

    Example:
        >>> subtasks = [
        ...     {"id": "A", "files": ["f1.py"]},
        ...     {"id": "B", "files": ["f1.py", "f2.py"]},
        ...     {"id": "C", "files": ["f3.py"]},
        ... ]
        >>> conflicts = analyze_file_conflicts(subtasks)
        >>> conflicts["A"] == {"B"}
        True
        >>> conflicts["B"] == {"A"}
        True
        >>> "C" not in conflicts  # No conflicts
        True
    """
    _validate_subtasks(subtasks)

    if not subtasks:
        return {}

    file_to_tasks = _build_file_to_tasks_mapping(subtasks)
    return _build_conflict_graph(file_to_tasks)
