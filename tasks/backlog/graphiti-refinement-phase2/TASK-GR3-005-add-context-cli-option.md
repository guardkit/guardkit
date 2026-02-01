---
id: TASK-GR3-005
title: Add --context CLI option to feature-plan
status: in_review
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
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T13:22:18.046773'
  last_updated: '2026-02-01T13:26:33.259309'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:22:18.046773'
    player_summary: Added --context CLI option to /feature-plan command. The implementation
      leverages existing context_files parameter in FeaturePlanIntegration.build_enriched_prompt().
      Updated feature-plan.md documentation with new flag, usage examples, and dedicated
      section explaining the --context option. Created comprehensive test suite covering
      all acceptance criteria.
    player_success: true
    coach_success: true
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
