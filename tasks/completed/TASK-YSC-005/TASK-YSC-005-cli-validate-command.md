---
id: TASK-YSC-005
title: Add guardkit feature validate CLI command
status: completed
created: 2026-02-14T00:00:00Z
updated: 2026-02-15T00:00:00Z
completed: 2026-02-15T16:30:00Z
completed_location: tasks/completed/TASK-YSC-005/
priority: medium
tags: [cli, validation, feature-loader, developer-experience]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: task-work
wave: 3
complexity: 4
depends_on:
  - TASK-YSC-004
previous_state: in_review
state_transition_reason: "All quality gates passed - 16/16 tests passing, implementation complete"
organized_files:
  - TASK-YSC-005-cli-validate-command.md
---

# Task: Add guardkit feature validate CLI command

## Description

Add a `guardkit feature validate FEAT-XXX` CLI command that performs pre-flight validation of a feature YAML file before running `autobuild feature`. This provides a user-facing way to check schema compliance.

## Acceptance Criteria

- [x] `guardkit feature validate FEAT-AC1A` validates the YAML and prints results
- [x] On success: prints "Feature FEAT-AC1A is valid" with green checkmark
- [x] On failure: prints each validation error with file location and expected vs actual values
- [x] Exit code 0 on success, 1 on validation failure
- [x] Validates both schema compliance (Pydantic) and structural integrity (task files exist, orchestration complete)
- [x] `--json` flag outputs results as JSON for CI integration
- [x] Tests verify CLI output for valid and invalid feature files

## Implementation Notes

- Use Click for CLI (consistent with existing `guardkit` commands)
- Reuse `FeatureLoader.validate_yaml()` and `FeatureLoader.validate_feature()`
- Register under the existing `guardkit` CLI group

## Files Modified

- `guardkit/cli/feature.py` - Created: Feature CLI command group with validate subcommand
- `guardkit/cli/main.py` - Modified: Registered feature command group
- `tests/unit/test_feature_cli.py` - Created: 16 tests covering valid, invalid, missing, parse errors, and JSON output

## Completion Summary

- **Tests**: 16/16 passing
- **Coverage**: Feature CLI module fully tested across valid, invalid, missing, parse error, and JSON output scenarios
- **Quality Gates**: All acceptance criteria satisfied
