# Implementation Guide: Provenance-Aware Intensity System

## Overview

This guide outlines the execution strategy for implementing provenance-aware intensity detection in GuardKit's `/task-work` command.

## Prerequisites

Complete TASK-TWP Wave 1 first:
- TASK-TWP-a1b2: Documentation constraints (fixes Phase 2 bloat)
- TASK-TWP-c3d4: Raise micro threshold to ≤3

These provide the foundation for the intensity system.

## Wave Breakdown

### Wave 1: Foundation (Parallel Execution)

Both tasks can be worked on in parallel as they modify different components.

| Task | Focus Area | Files | Conductor Workspace |
|------|------------|-------|---------------------|
| TASK-INT-a1b2 | Frontmatter schema | task-workflow.md, task-create.md | provenance-int-wave1-1 |
| TASK-INT-c3d4 | --intensity flag | task-work.md, CLI parsing | provenance-int-wave1-2 |

**Estimated Time**: 3-4 hours (parallel)
**Expected Outcome**: New frontmatter fields recognized, --intensity flag parsed

### Wave 2: Integration (Parallel Execution)

Depends on Wave 1 completion. Both tasks can run in parallel.

| Task | Focus Area | Files | Conductor Workspace |
|------|------------|-------|---------------------|
| TASK-INT-e5f6 | Auto-detection logic | New intensity.py module | provenance-int-wave2-1 |
| TASK-INT-g7h8 | task-work integration | task-work.md, phase config | provenance-int-wave2-2 |

**Estimated Time**: 3-4 hours (parallel)
**Expected Outcome**: Intensity auto-detected from provenance, phases skip accordingly

### Wave 3: Validation

Depends on Wave 2 completion.

| Task | Focus Area | Files | Conductor Workspace |
|------|------------|-------|---------------------|
| TASK-INT-i9j0 | Integration tests | tests/integration/ | provenance-int-wave3-1 |

**Estimated Time**: 1-2 hours
**Expected Outcome**: Full test coverage for intensity system

## Execution Commands

### Wave 1 (Parallel)

```bash
# Terminal 1
/task-work TASK-INT-a1b2 --micro  # Simple schema change

# Terminal 2
/task-work TASK-INT-c3d4 --micro  # Flag parsing is straightforward
```

Or with Conductor:
```bash
conductor workspace create provenance-int-wave1-1
conductor workspace create provenance-int-wave1-2
```

### Wave 2 (After Wave 1)

```bash
# Terminal 1
/task-work TASK-INT-e5f6  # Core logic, might need standard mode

# Terminal 2
/task-work TASK-INT-g7h8 --micro  # Integration is straightforward with logic in place
```

### Wave 3 (After Wave 2)

```bash
/task-work TASK-INT-i9j0 --micro  # Tests are well-defined
```

## Validation Strategy

### After Wave 1

Verify frontmatter and flag parsing:

```bash
# Create task with provenance
/task-create "Test task" parent_review:TASK-REV-TEST

# Check frontmatter
cat tasks/backlog/TASK-*.md | grep parent_review

# Verify --intensity flag is recognized
/task-work TASK-XXX --intensity=light --help
```

### After Wave 2

Verify auto-detection:

```bash
# Create task from review
/task-review TASK-REV-XXX
# Choose [I]mplement to create subtasks

# Run task-work without flag
/task-work TASK-SUBTASK-XXX
# Expected: "Auto-detected: minimal intensity (parent review: TASK-REV-XXX)"
```

### After Wave 3

Run integration tests:

```bash
pytest tests/integration/test_intensity_system.py -v
```

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Reviewed subtask duration | <15 min | Time /task-work on reviewed subtask |
| Auto-detection accuracy | 100% | Tasks with parent_review → minimal |
| Flag override works | 100% | --intensity=strict forces full ceremony |
| Backwards compatible | 100% | --micro still works as alias |

## Rollback Plan

All changes are additive:
1. New frontmatter fields are optional (backwards compatible)
2. --intensity flag defaults to auto-detection (current behavior preserved)
3. --micro remains as alias for --intensity=minimal

To rollback:
1. Revert task-work.md changes
2. Remove intensity.py module
3. Keep frontmatter fields (harmless)

## Technical Notes

### Provenance Detection

```python
def detect_provenance(task: Task) -> Provenance:
    if task.frontmatter.get("parent_review"):
        return Provenance.FROM_REVIEW
    if task.frontmatter.get("feature_id"):
        return Provenance.FROM_FEATURE_PLAN
    return Provenance.FRESH
```

### Intensity Mapping

```python
INTENSITY_FROM_PROVENANCE = {
    Provenance.FROM_REVIEW: {
        "complexity_le_4": Intensity.MINIMAL,
        "complexity_gt_4": Intensity.LIGHT,
    },
    Provenance.FROM_FEATURE_PLAN: {
        "complexity_le_3": Intensity.MINIMAL,
        "complexity_le_5": Intensity.LIGHT,
        "complexity_gt_5": Intensity.STANDARD,
    },
    Provenance.FRESH: {
        # Complexity-based (current behavior)
    },
}
```

## Dependencies

- No external dependencies
- All changes are to command specs and orchestration logic
- Python changes in guardkit/orchestrator/ (if applicable)

## Related Documentation

- [TASK-REV-FB16 Review Report](/.claude/reviews/TASK-REV-FB16-review-report.md)
- [task-work.md](/installer/core/commands/task-work.md)
- [Micro-Task Mode](/installer/core/commands/task-work.md#micro-task-mode)
