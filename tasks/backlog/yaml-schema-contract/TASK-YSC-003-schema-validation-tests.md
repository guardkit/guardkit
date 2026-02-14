---
id: TASK-YSC-003
title: Add schema validation tests for invalid status, extra fields, and round-trip
status: backlog
created: 2026-02-14T00:00:00Z
priority: high
tags: [testing, schema, validation, feature-loader]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: task-work
wave: 2
complexity: 4
depends_on:
  - TASK-YSC-002
---

# Task: Add schema validation tests

## Description

Add missing test cases to `tests/unit/test_feature_loader.py` that verify schema enforcement behavior. These tests should cover the gaps identified in the TASK-REV-YAML review.

## Acceptance Criteria

- [ ] Test: invalid `status` value (e.g., `backlog`) raises `ValidationError` or `FeatureParseError`
- [ ] Test: invalid `implementation_mode` value raises error
- [ ] Test: extra/unknown fields in task data produce a warning (with `extra="warn"`)
- [ ] Test: `parallel_groups` at top level (not under `orchestration:`) fails validation
- [ ] Test: round-trip test - `generate_feature_yaml.py` output loads successfully via `FeatureLoader`
- [ ] Test: `FeatureLoader.save_feature()` output loads back via `FeatureLoader.load_feature()`
- [ ] Test: JSON Schema export via `Feature.model_json_schema()` returns valid schema
- [ ] All new tests pass
- [ ] Coverage for `feature_loader.py` >= 85%

## Implementation Notes

- Use `pytest.raises(FeatureParseError)` or `pytest.raises(ValidationError)` as appropriate
- For the round-trip test with `generate_feature_yaml.py`, import `FeatureFile` and `TaskSpec` from the script
- The warning test may require capturing log output with `caplog` fixture
