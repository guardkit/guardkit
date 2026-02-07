---
id: TASK-CR-009
title: Trim autobuild.md, task-workflow.md, testing.md, python-library.md, hash-based-ids.md
status: completed
created: 2026-02-05 14:00:00+00:00
updated: 2026-02-06T12:00:00Z
completed: 2026-02-06T12:00:00Z
priority: low
tags:
- context-optimization
- token-reduction
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 3
complexity: 4
task_type: refactor
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CR01
  base_branch: main
  started_at: '2026-02-05T17:34:41.563621'
  last_updated: '2026-02-05T17:47:01.250130'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-02-05T17:34:41.563621'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-05T17:44:55.074917'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Trim Remaining Path-Gated Files

## Description

Compress verbose content in 5 path-gated files to reduce their token footprint when loaded. No Graphiti dependency - just editorial compression.

## Acceptance Criteria

- [x] autobuild.md: Compress Pre-Loop Configuration to table, migrate SDK Timeout detail, workflow examples, agent reports, troubleshooting. Remove Integration section (duplicate). Target: 1,556 -> 720 tokens
- [x] task-workflow.md: Migrate Provenance Fields detail + Provenance Chain Example. Compress Feature Folder Structure and Intensity Levels to table references. Target: 1,224 -> 700 tokens
- [x] testing.md: Migrate standard pytest knowledge (Mock Patterns, Performance Tests, Assertion Patterns). Target: 844 -> 520 tokens
- [x] python-library.md: Migrate Thread-Safe Caching and Logging Setup (standard patterns). Target: 860 -> 620 tokens
- [x] hash-based-ids.md: Migrate PM Tool Integration and FAQ. Remove For Developers links. Target: 344 -> 180 tokens
- [x] No workflow regressions

## Implementation Notes

These are all path-gated files, so savings are conditional on the file being loaded. Combined estimated savings: ~2,088 tokens across 5 files.

For migrated content: move to relevant docs/ files or seed into Graphiti if appropriate. Most of this is editorial compression (remove verbose examples, compress to tables).

## Completion Summary

All 5 files trimmed via editorial compression:

| File | Before (lines) | After (lines) | Key Removals |
|------|----------------|---------------|--------------|
| autobuild.md | 390 | 181 | Pre-Loop verbosity, SDK detail, workflow examples, troubleshooting, Integration section |
| task-workflow.md | 307 | 150 | Provenance Chain Example, Feature README Format, Intensity usage examples |
| testing.md | 212 | 149 | Mock Patterns, Performance Tests, Assertion Patterns |
| python-library.md | 216 | 164 | Thread-Safe Caching, Logging Setup |
| hash-based-ids.md | 87 | 51 | PM Tool Integration detail, For Developers links, FAQ |

Tests: 4265 passed, 0 regressions (112 pre-existing failures unrelated to docs).
