---
id: TASK-GR6-010
title: Add implementation_modes retrieval
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-006
wave: 3
implementation_mode: direct
complexity: 3
estimate_hours: 1
dependencies:
- TASK-GR6-003
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T16:59:40.609360'
  last_updated: '2026-02-01T17:02:33.259494'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T16:59:40.609360'
    player_summary: 'The implementation_modes retrieval was already fully implemented
      in the codebase. The feature includes:


      1. Query logic in build_context() method (lines 380-384) that queries the ''implementation_modes''
      group from Graphiti

      2. Formatting logic in _format_implementation_modes() method (lines 225-243)
      that formats mode, pattern, and description fields

      3. Integration into to_prompt_context() method (lines 110-112) that includes
      implementation modes in the formatted output

      4. Proper error handling thr'
    player_success: true
    coach_success: true
---

# Add implementation_modes retrieval

## Description

Add retrieval and formatting for implementation_modes context, addressing TASK-REV-7549 finding on direct vs task-work confusion.

## Acceptance Criteria

- [ ] Queries `implementation_modes` group
- [ ] Returns direct and task-work mode guidance
- [ ] Formats invocation method, result location, pitfalls
- [ ] Helps prevent "file not found" errors in worktrees

## Technical Details

**Group ID**: `implementation_modes`

**Output Format**:
```
### Implementation Mode
*Use correct mode to avoid file location errors*

**task-work**:
  Invocation: /task-work TASK-XXX
  Results at: .guardkit/worktrees/TASK-XXX/
  Pitfalls:
    ⚠️ Don't expect files in main repo during execution

**direct**:
  Invocation: Inline changes
  Results at: Current working directory
  Pitfalls:
    ⚠️ No isolation from main repo
```

**Reference**: See FEAT-GR-006 implementation_modes formatting.
