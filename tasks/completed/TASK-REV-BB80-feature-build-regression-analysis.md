---
id: TASK-REV-BB80
title: "Review: Feature-Build Regression - Player Not Implementing"
status: completed
created: 2026-01-25T12:00:00Z
updated: 2026-01-25T16:00:00Z
priority: high
task_type: review
review_mode: architectural
review_depth: standard
tags: [feature-build, regression, player-coach, context-pollution, autobuild]
complexity: 7
review_results:
  score: 85
  findings_count: 6
  recommendations_count: 1
  decision: implement
  report_path: .claude/reviews/TASK-REV-BB80-review-report.md
  completed_at: 2026-01-25T16:00:00Z
fix_applied:
  commit_pending: true
  files_changed:
    - guardkit/orchestrator/agent_invoker.py
    - tests/unit/test_agent_invoker.py
  root_cause: "Commit 14327137 changed max_turns from 50 to self.max_turns_per_agent (5)"
  fix: "Added TASK_WORK_SDK_MAX_TURNS=50 constant, used in _invoke_task_work_implement"
---

# Task: Review Feature-Build Regression - Player Not Implementing

## Overview

A serious regression has been observed in the `/feature-build` command where the Player agent fails to implement anything across multiple turns, despite the task-work command reporting success. This regression affects a previously working workflow (FastAPI app structure creation).

## Evidence Files

- **Working Example**: `/docs/reviews/feature-build/finally_success.md`
  - Feature: FEAT-A96D (5 tasks, 3 waves)
  - Result: All 5 tasks completed successfully in 1 turn each
  - Duration: 23m 24s total
  - Files created: Each task created expected files

- **Regression Case**: `/docs/reviews/feature-build/serious_regression.md`
  - Feature: FEAT-FHE (2 tasks, 2 waves)
  - Result: TASK-FHE-001 succeeded (Wave 1), TASK-FHE-002 failed after 10 turns
  - Duration: 20m 46s (with 1 SDK timeout at turn 4)
  - **Critical Issue**: "0 files created, 0 modified, 0 tests (failing)" reported for ALL turns

## Key Observations

### 1. Player Implementation Failure Pattern
Every turn for TASK-FHE-002 shows identical output:
```
✓ 0 files created, 0 modified, 0 tests (failing)
```

The Player reports "success" but creates no files. This suggests the Player is either:
- Not receiving proper context about what to implement
- Misinterpreting the task requirements
- Hitting some guard condition that prevents implementation

### 2. Context Pollution Detection Working
The adversarial cooperation pattern detected context pollution multiple times:
```
WARNING:guardkit.orchestrator.worktree_checkpoints:Context pollution detected: 2 consecutive test failures in turns [1, 2]
WARNING:guardkit.orchestrator.worktree_checkpoints:Context pollution detected: 2 consecutive test failures in turns [2, 3]
... (repeated for all consecutive turn pairs)
```

This is correct behavior - the Coach is detecting that no progress is being made.

### 3. Perspective Reset Triggered But Ineffective
Perspective resets were triggered at turns 3 and 5 (as configured), but they didn't help:
```
INFO:guardkit.orchestrator.autobuild:Perspective reset triggered at turn 3 (scheduled reset)
INFO:guardkit.orchestrator.autobuild:Perspective reset triggered at turn 5 (scheduled reset)
```

The Player still failed to implement anything after the resets.

### 4. SDK Timeout at Turn 4
One turn experienced a 900s timeout:
```
ERROR:guardkit.orchestrator.agent_invoker:[TASK-FHE-002] SDK TIMEOUT: task-work execution exceeded 900s timeout
```

State recovery worked correctly:
```
INFO:guardkit.orchestrator.autobuild:State recovery succeeded via git_only: 4 files, 0 tests (failing)
```

### 5. Task Type Detection Working
Quality gate profiles were correctly applied:
- TASK-FHE-001 (scaffolding): `tests_required=False`
- TASK-FHE-002 (feature): `tests_required=True`

### 6. Differences Between Runs

| Aspect | Success (FEAT-A96D) | Regression (FEAT-FHE) |
|--------|---------------------|----------------------|
| Tasks | 5 | 2 |
| Turns needed | 1 per task | 1 (pass), 10 (fail) |
| Files created | Yes | No (for failed task) |
| Perspective reset | Not needed | Triggered at 3, 5 |
| Context pollution | Not detected | Detected repeatedly |
| SDK timeout | None | 1 (turn 4) |

## Investigation Questions

1. **Why does the Player claim success but create no files?**
   - Is the Player receiving the correct task context?
   - Is the implementation plan stub correct?
   - Are acceptance criteria being parsed correctly?

2. **What changed between the successful and failed runs?**
   - Same codebase version?
   - Different task definitions?
   - Environment differences?

3. **Why don't perspective resets help?**
   - Is the reset actually clearing the problematic context?
   - Is there a persistent issue not related to context?

4. **Is this a regression in GuardKit code or external factors?**
   - Check recent commits
   - Check Claude Agent SDK version
   - Check bundled CLI version

## Acceptance Criteria

- [ ] Root cause identified for Player not creating files
- [ ] Comparison made between working and failing task definitions
- [ ] Relevant code paths analyzed (agent_invoker, autobuild orchestrator)
- [ ] Recommendations provided for fix
- [ ] Determine if context pollution detection needs enhancement

## Review Depth

**Standard** (1-2 hours) - This requires code analysis and comparison between the two runs.

## Files to Review

- `src/guardkit/orchestrator/agent_invoker.py` - Player invocation
- `src/guardkit/orchestrator/autobuild.py` - Main orchestration loop
- `src/guardkit/orchestrator/quality_gates/coach_validator.py` - Coach validation
- `src/guardkit/orchestrator/worktree_checkpoints.py` - Context pollution detection
- Task definitions for both FEAT-A96D and FEAT-FHE (in test repos)

## Notes

The context pollution detection and state recovery mechanisms appear to be working correctly - the issue is that the Player itself isn't implementing anything. This suggests the problem is in:
1. How the task/context is passed to the Player
2. The Player's interpretation of what to do
3. Some gating condition preventing implementation

This is valuable data for the adversarial cooperation pattern - it shows the Coach correctly identifying lack of progress, but the feedback loop isn't resulting in different Player behavior.
