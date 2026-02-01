---
id: TASK-GR5-003
title: Implement `list` command
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: direct
complexity: 3
estimate_hours: 1
dependencies:
- TASK-GR5-001
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:23:22.795247'
  last_updated: '2026-02-01T14:26:39.575503'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:23:22.795247'
    player_summary: 'Implemented the `guardkit graphiti list` command following the
      specification from FEAT-GR-005. The command allows users to list knowledge in
      specific categories (features, adrs, patterns, constraints) or all categories
      at once. Implementation includes:


      1. Added `_cmd_list()` async function that handles category-to-group mapping
      and connection management

      2. Added `_list_single_category()` helper function that searches and formats
      results for a single category

      3. Added `list_knowledge()` Click co'
    player_success: true
    coach_success: true
---

# Implement `list` command

## Description

Implement the `guardkit graphiti list` command to list all knowledge in a category.

## Acceptance Criteria

- [ ] `list features` lists all feature specs
- [ ] `list adrs` lists all ADRs
- [ ] `list patterns` lists all patterns
- [ ] `list constraints` lists all constraints
- [ ] `list all` lists all categories
- [ ] Shows count per category

## Usage Examples

```bash
guardkit graphiti list features
guardkit graphiti list all
```

**Reference**: See FEAT-GR-005 list output format.
