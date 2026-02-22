---
id: TASK-FSRF-004
title: "Add scan_codebase result to FeatureSpecResult"
status: completed
task_type: feature
parent_review: TASK-REV-FCA5
feature_id: FEAT-FSRF
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T14:45:00Z
completed: 2026-02-22T14:45:00Z
completed_location: tasks/completed/TASK-FSRF-004/
priority: low
tags: [feature-spec, enhancement, api]
complexity: 2
wave: 2
implementation_mode: task-work
dependencies: [TASK-FSRF-002]
tests_required: true
previous_state: in_review
state_transition_reason: "All quality gates passed, task completed"
organized_files:
  - TASK-FSRF-004.md
---

# Task: Add scan_codebase result to FeatureSpecResult

## Description

In `FeatureSpecCommand.execute()`, the `scan_codebase()` result is discarded (line 443). For programmatic callers, it would be useful to include this in the result.

## Fix

Add optional fields to `FeatureSpecResult`:

```python
@dataclass
class FeatureSpecResult:
    feature_file: Path
    assumptions_file: Path
    summary_file: Path
    scaffolding_files: dict[str, Path] = field(default_factory=dict)
    scenarios_count: int = 0
    assumptions_count: int = 0
    stack: str = "generic"
    modules: list[str] = field(default_factory=list)         # NEW
    existing_features: list[Path] = field(default_factory=list)  # NEW
    patterns: list[str] = field(default_factory=list)         # NEW
```

## Acceptance Criteria

- [x] `FeatureSpecResult` includes `modules`, `existing_features`, `patterns` fields
- [x] `FeatureSpecCommand.execute()` populates these from `scan_codebase()` result
- [x] Tests verify the new fields are populated
- [x] Backwards compatibility maintained (fields default to empty lists)

## Files Changed

- `guardkit/commands/feature_spec.py` - Added 3 fields to dataclass, captured scan_codebase() result
- `tests/unit/commands/test_feature_spec.py` - Added 5 new tests

## Completion Summary

- Tests: 87/87 passing (5 new)
- Intensity: MINIMAL (complexity 2, parent_review)
- Duration: ~3 minutes
