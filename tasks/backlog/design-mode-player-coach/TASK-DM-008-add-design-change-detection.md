---
id: TASK-DM-008
title: Add design change detection and state-aware handling
status: blocked
created: 2026-02-07 10:00:00+00:00
updated: 2026-02-07 10:00:00+00:00
priority: high
task_type: feature
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 4
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-DM-003
tags:
- design-mode
- change-detection
- cache
- state-management
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 2
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
  base_branch: main
  started_at: '2026-02-08T08:05:44.437388'
  last_updated: '2026-02-08T08:22:13.039540'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-08T08:05:44.437388'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-08T08:17:26.870982'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
