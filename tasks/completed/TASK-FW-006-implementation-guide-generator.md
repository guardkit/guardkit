---
id: TASK-FW-006
title: Create IMPLEMENTATION-GUIDE.md generator
status: completed
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T16:30:00Z
completed_at: 2025-12-04T16:35:00Z
priority: high
tags: [feature-workflow, documentation, generator]
complexity: 5
implementation_mode: task-work
parallel_group: 2
conductor_workspace: feature-workflow-2
parent_review: TASK-REV-FW01
test_coverage: 100%
tests_passing: 42/42
architectural_score: 82/100
code_review_score: 9.2/10
files_created: 2
lines_of_code: 1055
implementation_time: 5.5h
total_duration: 5.5h
---

# Create IMPLEMENTATION-GUIDE.md Generator

## Description

Generate IMPLEMENTATION-GUIDE.md following the established template pattern (see `progressive-disclosure/IMPLEMENTATION-GUIDE.md`).

## Acceptance Criteria

- [ ] Generate guide matching established template format
- [ ] Include method legend (task-work, Direct, Manual)
- [ ] Include wave breakdown with parallel groups
- [ ] Include task matrix with all metadata
- [ ] Include Conductor workspace strategy
- [ ] Include checkpoints between waves
- [ ] Include execution order summary

## Implementation Details

### Template Structure

```markdown
# {Feature Name} Implementation Guide

## Overview

This guide details the execution strategy for all {N} tasks, including which
implementation method to use and how to parallelize work using Conductor workspaces.

## Implementation Method Legend

| Method | Description | When to Use |
|--------|-------------|-------------|
| `/task-work` | Full GuardKit workflow with quality gates | Complex code changes requiring tests, review |
| `Direct` | Direct Claude Code implementation | Scripts, simple changes, documentation |
| `Manual` | Human execution with script | Bulk operations, running scripts |

## Conductor Parallel Execution

Conductor.build enables parallel development via git worktrees. Tasks marked **PARALLEL** can run simultaneously in separate workspaces.

### Workspace Strategy

\`\`\`
Main Repo ({repo-name})
├── Worktree A: Wave 1 ({task-ids})
├── Worktree B: Wave 2 (after Wave 1)
└── ...
\`\`\`

---

## Wave 1: {Wave Title}

**Duration**: {estimate}
**Workspaces**: {count}

### {TASK-ID}: {Title}
| Attribute | Value |
|-----------|-------|
| **Method** | {method} |
| **Complexity** | {score}/10 |
| **Effort** | {days} |
| **Parallel** | {Yes/No} |

**Why {Method}**: {rationale}

**Execution**:
\`\`\`bash
{command}
\`\`\`

---

## Summary: Task Matrix

| Task | Method | Complexity | Effort | Can Parallel |
|------|--------|------------|--------|--------------|
{rows}

## Method Breakdown

| Method | Task Count | Total Effort |
|--------|------------|--------------|
{summary}

## Recommended Execution Order

\`\`\`
{execution_order}
\`\`\`
```

### Generator Function

```python
def generate_implementation_guide(
    feature_name: str,
    subtasks: list[dict],
    output_path: str
) -> str:
    """
    Generate IMPLEMENTATION-GUIDE.md from subtask definitions.

    Args:
        feature_name: Human-readable feature name
        subtasks: List of subtask dicts with all metadata
        output_path: Where to write the guide

    Returns:
        Path to generated file
    """
```

## Files to Create/Modify

- `installer/core/lib/guide_generator.py` (NEW)

## Template Reference

Use `tasks/backlog/progressive-disclosure/IMPLEMENTATION-GUIDE.md` as the template reference.

## Test Cases

1. Generate guide for 5 subtasks with 2 waves
2. Generate guide for 10 subtasks with 4 waves
3. Handle single-task wave (sequential)
4. Handle all-parallel tasks (single wave)

## Dependencies

- TASK-FW-003 (subtask definitions)
- TASK-FW-004 (implementation modes)
- TASK-FW-005 (parallel groups)

## Notes

Can start development in parallel with FW-003/004/005 using mock data.
Final integration happens in FW-008.

## Architectural Review

**Score**: 82/100 (APPROVED WITH RECOMMENDATIONS)
**Date**: 2025-12-04

### Key Recommendations Applied:
1. ✅ Separated content generation from file I/O (SRP)
2. ✅ Extracted method metadata to data structures (OCP)
3. ✅ Added subtask normalization with dataclass (DRY)
4. ✅ Simplified test plan (30 tests instead of 46)
