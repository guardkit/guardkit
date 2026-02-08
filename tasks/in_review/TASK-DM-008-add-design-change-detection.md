---
autobuild_state:
  base_branch: main
  current_turn: 2
  last_updated: '2026-02-08T08:22:13.039540'
  max_turns: 15
  started_at: '2026-02-08T08:05:44.437388'
  turns:
  - coach_success: true
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-08T08:05:44.437388'
    turn: 1
  - coach_success: true
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-02-08T08:17:26.870982'
    turn: 2
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
complexity: 5
created: 2026-02-07 10:00:00+00:00
dependencies:
- TASK-DM-003
feature_id: FEAT-D4CE
id: TASK-DM-008
implementation_mode: task-work
parent_review: TASK-REV-D3E0
priority: high
status: in_review
tags:
- design-mode
- change-detection
- cache
- state-management
task_type: feature
test_results:
  coverage: 93%
  last_run: '2026-02-08T11:52:00'
  status: passed
  tests_passed: 47
  tests_total: 47
title: Add design change detection and state-aware handling
updated: 2026-02-07 10:00:00+00:00
wave: 4
---

# Add Design Change Detection and State-Aware Handling

## Description

Implement design change detection using extraction hash comparison. When a design changes while a task is in progress, the system responds based on the task's current state — silent refresh for backlog, pause and notify for in-progress, flag for in-review, new task required for completed.

## Requirements

1. Design change detection mechanism:
   - On each `task-work` invocation, check if `extracted_at` exceeds cache TTL (1 hour)
   - If expired, re-query MCP for the node
   - Hash the new extraction (SHA-256)
   - Compare against stored `extraction_hash`
   - If different → design has changed

2. State-aware handling:

   | Task State | Behaviour |
   |-----------|----------|
   | BACKLOG | Silent cache refresh on next `task-work` |
   | IN_PROGRESS | Pause after current cycle, notify user: "Design has changed since extraction." User decides: continue or restart |
   | IN_REVIEW | Flag in review notes: "Design updated since implementation." Reviewer decides |
   | COMPLETED | New task required (no automatic re-processing) |

3. Implementation in `autobuild.py`:
   - Check design freshness before Phase 0
   - If stale + changed: apply state-aware policy
   - If stale + unchanged: silently update timestamp

4. User notification for IN_PROGRESS tasks:
   ```
   ⚠️  Design Change Detected

   The design at {design_url} has changed since extraction.
   Extracted: {extracted_at}
   Current hash: {new_hash} (was: {old_hash})

   Options:
   [C]ontinue - Keep working with the original design
   [R]estart  - Re-extract design and restart from Phase 0
   ```

5. Cache management:
   - Cache location: `.guardkit/cache/design/{url_hash}/`
   - TTL: 1 hour (configurable)
   - Invalidate on design URL change
   - Clean up expired cache entries

## Acceptance Criteria

- [ ] Extraction hash (SHA-256) computed and stored after each MCP extraction
- [ ] Cache TTL check on each `task-work` invocation
- [ ] BACKLOG tasks: silent cache refresh
- [ ] IN_PROGRESS tasks: pause and notify user with continue/restart options
- [ ] IN_REVIEW tasks: flag design change in review notes
- [ ] COMPLETED tasks: no automatic re-processing
- [ ] Cache invalidated on design URL change
- [ ] Unit tests for each state-aware handling path

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §9 (Caching Strategy) and open questions §3
- No webhook infrastructure needed — hash comparison on `task-work` invocation
- Change detection is lightweight: one MCP call + hash compare
- "Walk before running" — start with notification, automate later