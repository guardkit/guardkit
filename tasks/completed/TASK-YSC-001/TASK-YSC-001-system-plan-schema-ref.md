---
id: TASK-YSC-001
title: Add feature YAML schema reference to system-plan command spec
status: completed
created: 2026-02-14T00:00:00Z
updated: 2026-02-15T00:00:00Z
completed: 2026-02-15T00:00:00Z
completed_location: tasks/completed/TASK-YSC-001/
priority: high
tags: [schema, system-plan, documentation, quick-fix]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: direct
wave: 1
complexity: 2
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, documentation verified"
organized_files:
  - TASK-YSC-001-system-plan-schema-ref.md
---

# Task: Add feature YAML schema reference to system-plan command spec

## Description

The `/system-plan` command spec (`.claude/commands/system-plan.md`) contains zero references to the feature YAML schema. When system-plan chains to `/feature-plan` via the `[F]eature-plan` option, there is no mechanism to ensure the generated YAML conforms to `FeatureLoader` expectations.

This is the immediate cause of the FEAT-AC1A bug where `parallel_groups` was generated at the top level instead of nested under `orchestration:`.

## Acceptance Criteria

- [x] `.claude/commands/system-plan.md` includes a "Feature YAML Schema Contract" section with the canonical schema
- [x] The schema section references `guardkit/orchestrator/feature_loader.py` as the authoritative source
- [x] The `[F]eature-plan` chaining section explicitly states that generated YAML must conform to the schema
- [x] Key constraints documented: `orchestration.parallel_groups` nesting, valid `status` values, required `file_path` field

## Implementation Notes

This is a documentation-only change. Add a schema reference section near the review mode `[F]eature-plan` chain point. Use the same schema format as `feature-plan.md` lines 352-502.

## Completion Summary

Added "Feature YAML Schema Contract" section (lines 304-480) to `.claude/commands/system-plan.md` with:
- Complete schema example referencing `guardkit/orchestrator/feature_loader.py`
- Required fields tables (feature-level, task-level, orchestration)
- 4 critical constraints with correct/incorrect YAML examples
- NOTE in `[F]eature-plan` chaining section requiring schema conformance
