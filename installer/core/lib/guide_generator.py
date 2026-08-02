"""
Implementation Guide Generator

Generates IMPLEMENTATION-GUIDE.md files from subtask definitions, including wave
breakdowns, parallel execution strategies, method selection rationale, and
Conductor workspace recommendations.

Example:
    >>> subtasks = [
    ...     {"id": "TASK-A", "title": "Foundation", "parallel_group": 1},
    ...     {"id": "TASK-B", "title": "Feature", "parallel_group": 2},
    ... ]
    >>> content = generate_guide_content("My Feature", subtasks)
    >>> write_guide_to_file(content, "docs/IMPLEMENTATION-GUIDE.md")
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Method display names (extensible without code changes - OCP)
METHOD_DISPLAY_NAMES = {
    "task-work": "/task-work",
    "direct": "Direct Claude Code",
    "manual": "Manual",
}

# Rationale templates (extensible without code changes - OCP)
RATIONALE_TEMPLATES = {
    "task-work": "Full GuardKit workflow with quality gates (architecture review, tests, code review).",
    "direct": "Straightforward changes with clear acceptance criteria and low integration risk.",
    "manual": "Human execution of automated script with review of output.",
}


# ---------------------------------------------------------------------------
# Effort coercion (leg-invocation stage-2 design §5)
# ---------------------------------------------------------------------------
#
# ``SubtaskData.estimated_effort_days`` is a FLOAT and ``_calculate_wave_duration``
# sums it. The fix-task producer, however, carries effort as a human string
# ("1d", "4h") — implement_orchestrator.py's guide step passes
# ``subtask.get("effort_estimate", "1d")`` straight through — so the sum raised
# ``TypeError: unsupported operand type(s) for +: 'int' and 'str'`` AFTER the
# fix-task files were already on disk. Measured cost: 42/42 legs of the
# 2026-08-02 crossing produced fix tasks but NO guide and NO README.
#
# The cure is an honest coercion at the one seam where a raw dict becomes
# SubtaskData: parse the unit, never guess silently.

#: Working hours in one effort day — the unit "4h" is converted against.
#: Matches ``_calculate_wave_duration``'s own ``total_days * 8`` hours display.
HOURS_PER_EFFORT_DAY = 8.0

#: What an unparseable effort becomes. Same as the dataclass default: the guide
#: is a planning aid, so a bad estimate must degrade to the default estimate
#: with a warning, never take the whole guide down with it.
DEFAULT_EFFORT_DAYS = 1.0

# NO SIGN CLASS, deliberately. ``[+-]?`` accepted "-2d", and a negative effort
# does not fail — it SUBTRACTS from the wave total, so one mistyped row quietly
# shortens the plan instead of being caught. An effort estimate is a duration;
# a signed one is not a smaller estimate, it is an unparseable one, and it takes
# the named default-with-a-warning path like every other thing this regex
# refuses. (The numeric branch of coerce_effort_days applies the same rule.)
_EFFORT_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(d|day|days|h|hr|hrs|hour|hours|w|wk|week|weeks)?\s*$",
    re.IGNORECASE,
)

_EFFORT_UNIT_DAYS = {
    "d": 1.0, "day": 1.0, "days": 1.0,
    "h": 1.0 / HOURS_PER_EFFORT_DAY,
    "hr": 1.0 / HOURS_PER_EFFORT_DAY,
    "hrs": 1.0 / HOURS_PER_EFFORT_DAY,
    "hour": 1.0 / HOURS_PER_EFFORT_DAY,
    "hours": 1.0 / HOURS_PER_EFFORT_DAY,
    "w": 5.0, "wk": 5.0, "week": 5.0, "weeks": 5.0,
}


def coerce_effort_days(raw: Any, *, subtask_id: str = "") -> float:
    """Coerce an effort estimate to days as a float.

    ``1d`` -> 1.0, ``4h`` -> 0.5, ``2.5`` -> 2.5, ``1w`` -> 5.0. A bare number
    is already days. Anything unparseable (including ``None``, and including a
    NEGATIVE value in either form — see :data:`_EFFORT_RE`) becomes
    :data:`DEFAULT_EFFORT_DAYS` and says so in a WARNING — the estimate is
    guessed exactly once, out loud, instead of crashing the guide or silently
    subtracting from the wave total.
    """
    if isinstance(raw, bool):  # bool is an int; an effort of True is nonsense
        pass
    elif isinstance(raw, (int, float)):
        if raw >= 0:
            return float(raw)
    elif isinstance(raw, str):
        match = _EFFORT_RE.match(raw)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or "d").lower()
            return value * _EFFORT_UNIT_DAYS[unit]

    logger.warning(
        "unparseable effort estimate %r%s — using %.1f day(s)",
        raw,
        f" on {subtask_id}" if subtask_id else "",
        DEFAULT_EFFORT_DAYS,
    )
    return DEFAULT_EFFORT_DAYS


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
    dependencies: List[str] = field(default_factory=list)
    rationale: str = ""
    execution_command: str = ""


def _normalize_subtask(task: dict) -> SubtaskData:
    """
    Apply defaults to subtask dictionary and create normalized dataclass.

    Args:
        task: Raw subtask dictionary

    Returns:
        SubtaskData with defaults applied

    Example:
        >>> task = {"id": "TASK-A", "title": "Test"}
        >>> normalized = _normalize_subtask(task)
        >>> normalized.implementation_method
        'task-work'
        >>> normalized.complexity
        5
        >>> _normalize_subtask({"id": "A", "title": "T",
        ...                     "estimated_effort_days": "1d"}).estimated_effort_days
        1.0
    """
    return SubtaskData(
        id=task["id"],
        title=task["title"],
        implementation_method=task.get("implementation_method", "task-work"),
        complexity=task.get("complexity", 5),
        estimated_effort_days=coerce_effort_days(
            task.get("estimated_effort_days", DEFAULT_EFFORT_DAYS),
            subtask_id=str(task.get("id", "")),
        ),
        parallel_group=task.get("parallel_group", 1),
        conductor_workspace=task.get("conductor_workspace", ""),
        dependencies=task.get("dependencies", []),
        rationale=task.get("rationale", ""),
        execution_command=task.get("execution_command", ""),
    )


def _format_method(method: str) -> str:
    """
    Format method name for display.

    Args:
        method: Internal method name (task-work, direct, manual)

    Returns:
        Formatted display name

    Example:
        >>> _format_method("task-work")
        '/task-work'
        >>> _format_method("direct")
        'Direct Claude Code'
    """
    return METHOD_DISPLAY_NAMES.get(method, method)


def _generate_default_rationale(method: str) -> str:
    """
    Generate default rationale for method selection.

    Args:
        method: Implementation method

    Returns:
        Default rationale text

    Example:
        >>> _generate_default_rationale("task-work")
        'Full GuardKit workflow with quality gates...'
    """
    return RATIONALE_TEMPLATES.get(method, "Standard implementation approach.")


def _group_tasks_by_wave(subtasks: List[SubtaskData]) -> Dict[int, List[SubtaskData]]:
    """
    Group tasks by parallel_group number (wave).

    Args:
        subtasks: List of normalized subtasks

    Returns:
        Dictionary mapping wave number to list of tasks in that wave,
        sorted by wave number

    Example:
        >>> tasks = [
        ...     SubtaskData("A", "Task A", parallel_group=1),
        ...     SubtaskData("B", "Task B", parallel_group=2),
        ...     SubtaskData("C", "Task C", parallel_group=1),
        ... ]
        >>> waves = _group_tasks_by_wave(tasks)
        >>> len(waves[1])
        2
        >>> len(waves[2])
        1
    """
    waves: Dict[int, List[SubtaskData]] = defaultdict(list)
    for task in subtasks:
        waves[task.parallel_group].append(task)
    return dict(sorted(waves.items()))


def _calculate_wave_duration(wave_tasks: List[SubtaskData]) -> str:
    """
    Calculate total duration for wave.

    Args:
        wave_tasks: Tasks in the wave

    Returns:
        Formatted duration string (e.g., "2.5 days", "6.0 hours")

    Example:
        >>> tasks = [SubtaskData("A", "A", estimated_effort_days=1.5),
        ...          SubtaskData("B", "B", estimated_effort_days=2.0)]
        >>> _calculate_wave_duration(tasks)
        '3.5 days'
    """
    total_days = sum(task.estimated_effort_days for task in wave_tasks)
    if total_days < 1:
        return f"{total_days * 8:.1f} hours"
    return f"{total_days:.1f} days"


def _is_parallel(wave_tasks: List[SubtaskData]) -> bool:
    """
    Determine if wave contains parallel tasks.

    Args:
        wave_tasks: Tasks in the wave

    Returns:
        True if multiple tasks (parallel execution), False if single task

    Example:
        >>> tasks = [SubtaskData("A", "A"), SubtaskData("B", "B")]
        >>> _is_parallel(tasks)
        True
    """
    return len(wave_tasks) > 1


def _generate_overview(feature_name: str, task_count: int) -> str:
    """
    Generate overview section.

    Args:
        feature_name: Human-readable feature name
        task_count: Total number of tasks

    Returns:
        Markdown overview section

    Example:
        >>> overview = _generate_overview("My Feature", 10)
        >>> "My Feature" in overview
        True
        >>> "10 tasks" in overview
        True
    """
    return f"""# {feature_name} Implementation Guide

## Overview

This guide details the execution strategy for all {task_count} tasks, including which implementation method to use and how to parallelize work using Conductor workspaces.
"""


def _generate_method_legend() -> str:
    """
    Generate implementation method legend (static section).

    Returns:
        Markdown method legend section

    Example:
        >>> legend = _generate_method_legend()
        >>> "/task-work" in legend
        True
        >>> "Direct" in legend
        True
    """
    return """## Implementation Method Legend

| Method | Description | When to Use |
|--------|-------------|-------------|
| `/task-work` | Full GuardKit workflow with quality gates | Complex code changes requiring tests, review |
| `Direct` | Direct Claude Code implementation | Scripts, simple changes, documentation |
| `Manual` | Human execution with script | Bulk operations, running scripts |
"""


def _generate_conductor_section(repo_name: str, waves: Dict[int, List[SubtaskData]]) -> str:
    """
    Generate Conductor parallel execution section.

    Args:
        repo_name: Repository name
        waves: Grouped tasks by wave

    Returns:
        Markdown Conductor section with workspace strategy

    Example:
        >>> waves = {1: [SubtaskData("A", "A")], 2: [SubtaskData("B", "B")]}
        >>> section = _generate_conductor_section("my-repo", waves)
        >>> "Conductor.build" in section
        True
        >>> "my-repo" in section
        True
    """
    # Generate workspace layout
    layout_lines = [f"Main Repo ({repo_name})"]
    for wave_num, wave_tasks in waves.items():
        task_ids = ", ".join([task.id for task in wave_tasks])
        layout_lines.append(f"├── Worktree {wave_num}: Wave {wave_num} ({task_ids})")

    layout = "\n".join(layout_lines)

    return f"""## Conductor Parallel Execution

Conductor.build enables parallel development via git worktrees. Tasks marked **PARALLEL** can run simultaneously in separate workspaces.

### Workspace Strategy

```
{layout}
```
"""


def _generate_task_detail(task: SubtaskData) -> str:
    """
    Generate detailed task section.

    Args:
        task: Normalized subtask data

    Returns:
        Markdown task detail section

    Example:
        >>> task = SubtaskData("TASK-A", "My Task", complexity=7, estimated_effort_days=2.5)
        >>> detail = _generate_task_detail(task)
        >>> "TASK-A" in detail
        True
        >>> "7/10" in detail
        True
    """
    method_display = _format_method(task.implementation_method)
    rationale = task.rationale if task.rationale else _generate_default_rationale(task.implementation_method)
    execution = task.execution_command if task.execution_command else f"{_format_method(task.implementation_method)} {task.id}"

    parallel_text = "**YES**" if task.conductor_workspace else "No"

    return f"""### {task.id}: {task.title}
| Attribute | Value |
|-----------|-------|
| **Method** | {method_display} |
| **Complexity** | {task.complexity}/10 |
| **Effort** | {task.estimated_effort_days:.1f} days |
| **Parallel** | {parallel_text} |

**Why {method_display}**: {rationale}

**Execution**:
```bash
{execution}
```

---
"""


def _generate_wave_section(wave_num: int, wave_tasks: List[SubtaskData], feature_name: str) -> str:
    """
    Generate complete wave section with all tasks.

    Args:
        wave_num: Wave number
        wave_tasks: Tasks in this wave
        feature_name: Feature name for workspace naming

    Returns:
        Markdown wave section

    Example:
        >>> tasks = [SubtaskData("A", "Task A", estimated_effort_days=1.5)]
        >>> section = _generate_wave_section(1, tasks, "feature")
        >>> "Wave 1" in section
        True
        >>> "1.5 days" in section
        True
    """
    duration = _calculate_wave_duration(wave_tasks)
    workspace_count = len(wave_tasks) if _is_parallel(wave_tasks) else 1

    section = f"""## Wave {wave_num}

**Duration**: {duration}
**Workspaces**: {workspace_count}

"""

    # Add task details
    for task in wave_tasks:
        section += _generate_task_detail(task)

    return section


def _generate_task_matrix(subtasks: List[SubtaskData]) -> str:
    """
    Generate summary task matrix.

    Args:
        subtasks: All normalized subtasks

    Returns:
        Markdown task matrix table

    Example:
        >>> tasks = [SubtaskData("A", "Task A", complexity=5, estimated_effort_days=1.0)]
        >>> matrix = _generate_task_matrix(tasks)
        >>> "TASK-A" in matrix
        True
        >>> "5" in matrix
        True
    """
    section = """## Summary: Task Matrix

| Task | Method | Complexity | Effort | Can Parallel |
|------|--------|------------|--------|--------------|
"""

    for task in subtasks:
        method_display = _format_method(task.implementation_method)
        parallel = "**YES**" if task.conductor_workspace else "No"
        section += f"| {task.id} | {method_display} | {task.complexity} | {task.estimated_effort_days:.1f}d | {parallel} |\n"

    return section


def _generate_method_breakdown(subtasks: List[SubtaskData]) -> str:
    """
    Generate method breakdown summary.

    Args:
        subtasks: All normalized subtasks

    Returns:
        Markdown method breakdown table

    Example:
        >>> tasks = [SubtaskData("A", "A", implementation_method="task-work", estimated_effort_days=2.0),
        ...          SubtaskData("B", "B", implementation_method="direct", estimated_effort_days=0.5)]
        >>> breakdown = _generate_method_breakdown(tasks)
        >>> "/task-work" in breakdown
        True
        >>> "2 tasks" in breakdown
        True
    """
    # Group by method
    method_stats: Dict[str, Dict[str, any]] = defaultdict(lambda: {"count": 0, "effort": 0.0})

    for task in subtasks:
        method = task.implementation_method
        method_stats[method]["count"] += 1
        method_stats[method]["effort"] += task.estimated_effort_days

    section = """## Method Breakdown

| Method | Task Count | Total Effort |
|--------|------------|--------------|
"""

    for method, stats in sorted(method_stats.items()):
        method_display = _format_method(method)
        count = stats["count"]
        effort = stats["effort"]
        section += f"| {method_display} | {count} tasks | {effort:.1f} days |\n"

    return section


def _generate_execution_order(waves: Dict[int, List[SubtaskData]]) -> str:
    """
    Generate recommended execution order.

    Args:
        waves: Grouped tasks by wave

    Returns:
        Markdown execution order section

    Example:
        >>> waves = {1: [SubtaskData("A", "A")], 2: [SubtaskData("B", "B")]}
        >>> order = _generate_execution_order(waves)
        >>> "Wave 1" in order
        True
        >>> "TASK-A" in order
        True
    """
    section = """## Recommended Execution Order

```
"""

    for wave_num, wave_tasks in sorted(waves.items()):
        task_ids = ", ".join([task.id for task in wave_tasks])
        parallel_note = " (PARALLEL)" if _is_parallel(wave_tasks) else ""
        section += f"Wave {wave_num}: {task_ids}{parallel_note}\n"

    section += "```\n"
    return section


def generate_guide_content(
    feature_name: str,
    subtasks: List[dict],
    repo_name: str = "your-repo"
) -> str:
    """
    Generate IMPLEMENTATION-GUIDE.md content (returns string).

    Args:
        feature_name: Human-readable feature name
        subtasks: List of subtask dictionaries with metadata
        repo_name: Repository name for workspace strategy

    Returns:
        Complete implementation guide as markdown string

    Example:
        >>> subtasks = [
        ...     {"id": "TASK-A", "title": "Foundation", "parallel_group": 1},
        ...     {"id": "TASK-B", "title": "Feature", "parallel_group": 2},
        ... ]
        >>> content = generate_guide_content("My Feature", subtasks)
        >>> "My Feature" in content
        True
        >>> "TASK-A" in content
        True
    """
    # Normalize all subtasks
    normalized = [_normalize_subtask(task) for task in subtasks]

    # Group by wave
    waves = _group_tasks_by_wave(normalized)

    # Generate sections
    sections = [
        _generate_overview(feature_name, len(normalized)),
        _generate_method_legend(),
        _generate_conductor_section(repo_name, waves),
        "",
        "---",
        "",
    ]

    # Add wave sections
    for wave_num, wave_tasks in waves.items():
        sections.append(_generate_wave_section(wave_num, wave_tasks, feature_name))

    # Add summary sections
    sections.extend([
        _generate_task_matrix(normalized),
        "",
        _generate_method_breakdown(normalized),
        "",
        _generate_execution_order(waves),
    ])

    return "\n".join(sections)


def write_guide_to_file(content: str, output_path: str) -> None:
    """
    Write guide content to file.

    Args:
        content: Generated guide content
        output_path: Path to output file

    Example:
        >>> content = "# Test Guide\\n\\nContent here"
        >>> write_guide_to_file(content, "/tmp/test-guide.md")
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
