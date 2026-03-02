---
id: TASK-ABFIX-007
title: Add guardkit feature validate pre-flight CLI command
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 3
implementation_mode: task-work
complexity: 4
dependencies: [TASK-ABFIX-002]
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: backlog
priority: medium
tags: [autobuild, cli, validation, feature-loader]
---

# Task: Add guardkit feature validate pre-flight CLI command

## Description

Add a `guardkit feature validate FEAT-XXX` CLI command that runs `FeatureLoader.validate_feature()` standalone without creating worktrees or starting a build. This enables pre-flight validation after editing feature YAML or task files, catching errors (like intra-wave dependencies or invalid task_type) before committing to a full run.

Also integrate this validation into `/feature-plan` so errors are reported inline after generating the YAML.

## Review Reference

From TASK-REV-A17A Finding 4, Recommendations 4a and 4b:
> 4a: Add `guardkit feature validate FEAT-XXX` CLI command. Runs `FeatureLoader.validate_feature()` standalone without creating worktrees.
> 4b: Run validation in `/feature-plan`. After generating the YAML, call `validate_feature()` and report errors inline.

## Requirements

1. Add `guardkit feature validate FEAT-XXX` CLI command:
   - Loads the feature YAML from `.guardkit/features/FEAT-XXX.yaml`
   - Calls `FeatureLoader.validate_feature()` (which now includes task_type validation from TASK-ABFIX-002)
   - Reports all validation errors with actionable messages
   - Returns exit code 0 on success, 1 on validation failure
2. Integrate validation into `/feature-plan`:
   - After generating the feature YAML, automatically call `validate_feature()`
   - Report any errors inline (intra-wave deps, invalid task_type, missing task files)
3. Add tests for the CLI command (both success and failure cases)

## Files to Modify

- `guardkit/cli/` — add `feature validate` subcommand
- `guardkit/orchestrator/feature_loader.py` — ensure `validate_feature()` is callable standalone
- `installer/core/commands/feature-plan.md` — add validation step
- `tests/` — test CLI command and feature-plan integration

## Acceptance Criteria

- [ ] `guardkit feature validate FEAT-XXX` runs without creating worktrees
- [ ] Reports intra-wave dependency errors
- [ ] Reports invalid task_type errors (requires TASK-ABFIX-002)
- [ ] Returns correct exit codes
- [ ] All existing tests pass
