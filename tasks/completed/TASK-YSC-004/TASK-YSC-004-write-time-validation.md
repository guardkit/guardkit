---
id: TASK-YSC-004
title: Add write-time validation to all feature YAML generation paths
status: completed
created: 2026-02-14T00:00:00Z
updated: 2026-02-15T00:00:00Z
completed: 2026-02-15T00:00:00Z
priority: high
tags: [validation, schema, feature-loader, defense-in-depth]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: task-work
wave: 2
complexity: 4
depends_on:
  - TASK-YSC-002
previous_state: in_review
state_transition_reason: "All quality gates passed - task completed"
completed_location: tasks/completed/TASK-YSC-004/
organized_files:
  - TASK-YSC-004-write-time-validation.md
---

# Task: Add write-time validation to all feature YAML generation paths

## Description

Add a `FeatureLoader.validate_yaml(data: dict) -> List[str]` static method that validates raw YAML data against the Pydantic schema before writing. Call it from all generation paths to catch schema violations before files reach disk.

## Acceptance Criteria

- [x] `FeatureLoader.validate_yaml(data)` method validates raw dict against Pydantic schema
- [x] Returns list of human-readable error strings (empty if valid)
- [x] `generate_feature_yaml.py` calls `validate_yaml()` before `write_yaml()` and exits with error if invalid
- [x] `FeatureLoader.save_feature()` calls `validate_yaml()` before `yaml.dump()`
- [x] Validation errors include field name, expected value, and actual value
- [x] Tests verify that write-time validation catches: invalid status, missing required fields, wrong nesting

## Implementation Notes

- Use Pydantic `model_validate()` in a try/except to convert `ValidationError` to error strings
- The `validate_yaml()` method should be usable standalone (no Feature instance needed)
- Added `--strict` flag to `generate_feature_yaml.py` that makes validation errors fatal (default: warn)

## Files Modified

- `guardkit/orchestrator/feature_loader.py` - Added `validate_yaml()` method, modified `save_feature()` to validate before write
- `installer/core/commands/lib/generate_feature_yaml.py` - Added validation before write_yaml(), added --strict flag
- `tests/unit/test_feature_loader.py` - Added 10 tests for write-time validation

## Completion Summary

- 10/10 new tests passing
- All 6 acceptance criteria met
- 3 files modified
- No regressions introduced
