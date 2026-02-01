---
id: TASK-GR3-005
title: Add --context CLI option to feature-plan
status: backlog
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-003
wave: 1
parallel_group: wave1-gr003
implementation_mode: direct
complexity: 2
estimate_hours: 1
dependencies:
  - TASK-GR3-004
---

# Add --context CLI option to feature-plan

## Description

Add explicit `--context` option to `/feature-plan` for specifying context files when auto-detection isn't sufficient.

## Acceptance Criteria

- [ ] `--context path/to/spec.md` seeds specified file
- [ ] Multiple `--context` flags supported
- [ ] Works alongside auto-detection
- [ ] Help text documents usage

## Usage Examples

```bash
# Explicit context file
/feature-plan "implement feature" --context docs/features/FEAT-XXX.md

# Multiple context sources
/feature-plan "implement feature" --context spec.md --context CLAUDE.md
```

**Reference**: See FEAT-GR-003-feature-spec-integration.md usage examples.
