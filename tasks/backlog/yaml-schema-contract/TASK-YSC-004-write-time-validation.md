---
id: TASK-YSC-004
title: Add write-time validation to all feature YAML generation paths
status: backlog
created: 2026-02-14T00:00:00Z
priority: high
tags: [validation, schema, feature-loader, defense-in-depth]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: task-work
wave: 2
complexity: 4
depends_on:
  - TASK-YSC-002
---

# Task: Add write-time validation to all feature YAML generation paths

## Description

Add a `FeatureLoader.validate_yaml(data: dict) -> List[str]` static method that validates raw YAML data against the Pydantic schema before writing. Call it from all generation paths to catch schema violations before files reach disk.

## Acceptance Criteria

- [ ] `FeatureLoader.validate_yaml(data)` method validates raw dict against Pydantic schema
- [ ] Returns list of human-readable error strings (empty if valid)
- [ ] `generate_feature_yaml.py` calls `validate_yaml()` before `write_yaml()` and exits with error if invalid
- [ ] `FeatureLoader.save_feature()` calls `validate_yaml()` before `yaml.dump()`
- [ ] Validation errors include field name, expected value, and actual value
- [ ] Tests verify that write-time validation catches: invalid status, missing required fields, wrong nesting

## Implementation Notes

- Use Pydantic `model_validate()` in a try/except to convert `ValidationError` to error strings
- The `validate_yaml()` method should be usable standalone (no Feature instance needed)
- Consider adding a `--strict` flag to `generate_feature_yaml.py` that makes validation errors fatal (default: warn)

## Files to Modify

- `guardkit/orchestrator/feature_loader.py` - Add `validate_yaml()` method
- `installer/core/commands/lib/generate_feature_yaml.py` - Call validation before write
- `tests/unit/test_feature_loader.py` - Test write-time validation
