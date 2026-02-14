---
id: TASK-YSC-005
title: Add guardkit feature validate CLI command
status: backlog
created: 2026-02-14T00:00:00Z
priority: medium
tags: [cli, validation, feature-loader, developer-experience]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: task-work
wave: 3
complexity: 4
depends_on:
  - TASK-YSC-004
---

# Task: Add guardkit feature validate CLI command

## Description

Add a `guardkit feature validate FEAT-XXX` CLI command that performs pre-flight validation of a feature YAML file before running `autobuild feature`. This provides a user-facing way to check schema compliance.

## Acceptance Criteria

- [ ] `guardkit feature validate FEAT-AC1A` validates the YAML and prints results
- [ ] On success: prints "Feature FEAT-AC1A is valid" with green checkmark
- [ ] On failure: prints each validation error with file location and expected vs actual values
- [ ] Exit code 0 on success, 1 on validation failure
- [ ] Validates both schema compliance (Pydantic) and structural integrity (task files exist, orchestration complete)
- [ ] `--json` flag outputs results as JSON for CI integration
- [ ] Tests verify CLI output for valid and invalid feature files

## Implementation Notes

- Use Click for CLI (consistent with existing `guardkit` commands)
- Reuse `FeatureLoader.validate_yaml()` and `FeatureLoader.validate_feature()`
- Register under the existing `guardkit` CLI group

## Files to Modify

- `guardkit/cli/feature.py` (or create if needed) - CLI command
- `guardkit/cli/main.py` - Register command group
- `tests/unit/test_feature_cli.py` - CLI tests
