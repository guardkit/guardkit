---
id: TASK-YSC-001
title: Add feature YAML schema reference to system-plan command spec
status: backlog
created: 2026-02-14T00:00:00Z
priority: high
tags: [schema, system-plan, documentation, quick-fix]
parent_review: TASK-REV-YAML
feature_id: FEAT-YSC
implementation_mode: direct
wave: 1
complexity: 2
depends_on: []
---

# Task: Add feature YAML schema reference to system-plan command spec

## Description

The `/system-plan` command spec (`.claude/commands/system-plan.md`) contains zero references to the feature YAML schema. When system-plan chains to `/feature-plan` via the `[F]eature-plan` option, there is no mechanism to ensure the generated YAML conforms to `FeatureLoader` expectations.

This is the immediate cause of the FEAT-AC1A bug where `parallel_groups` was generated at the top level instead of nested under `orchestration:`.

## Acceptance Criteria

- [ ] `.claude/commands/system-plan.md` includes a "Feature YAML Schema Contract" section with the canonical schema
- [ ] The schema section references `guardkit/orchestrator/feature_loader.py` as the authoritative source
- [ ] The `[F]eature-plan` chaining section explicitly states that generated YAML must conform to the schema
- [ ] Key constraints documented: `orchestration.parallel_groups` nesting, valid `status` values, required `file_path` field

## Implementation Notes

This is a documentation-only change. Add a schema reference section near the review mode `[F]eature-plan` chain point. Use the same schema format as `feature-plan.md` lines 352-502.
