---
id: TASK-FBC-004
title: Improve progress display for feature mode
status: completed
created: 2025-12-31T17:00:00Z
completed: 2025-12-31T23:45:00Z
priority: low
complexity: 3
tags: [cli, autobuild, ux, progress-display]
parent_feature: feature-build-cli-native
source_review: TASK-REV-FB01
implementation_mode: direct
estimated_hours: 2-3
dependencies: [TASK-FBC-001]
implementation_completed: 2025-12-31
completed_location: tasks/completed/feature-build-cli-native/TASK-FBC-004/
code_review_score: 9.5/10
tests_passed: 28/28
---

# Improve Progress Display for Feature Mode

## Description

Enhance the progress display for feature-mode execution to show wave progress, task status, and turn-by-turn updates clearly.

**User Impact**: Better visibility into long-running feature builds.

## Requirements

1. **Wave Progress Header**
   - Show current wave / total waves
   - List tasks in current wave
   - Show parallel execution indicator

2. **Task Status Updates**
   - Real-time status per task
   - Turn counter
   - Coach decision (APPROVED/FEEDBACK)

3. **Summary Display**
   - Wave completion summary
   - Overall feature progress
   - Time elapsed

## Acceptance Criteria

- [x] Wave header shows wave number and tasks
- [x] Task status updates in real-time
- [x] Turn-by-turn progress visible
- [x] Final summary shows all results
- [x] Works in both verbose and normal modes

## Implementation Notes

### Display Format

```
══════════════════════════════════════════════════════════════
FEATURE BUILD: FEAT-XXX
══════════════════════════════════════════════════════════════

Feature: Build Application Infrastructure
Tasks: 12 total across 4 waves
Mode: CLI native

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wave 1/4: Independent Setup
Tasks: [TASK-001, TASK-002, TASK-003, TASK-004]
Parallel: Yes (4 concurrent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK-001: Create pyproject.toml
  Turn 1/5: Player ▶ ... Coach ✓ APPROVED
  Status: COMPLETED (1 turn)

TASK-002: Create requirements/
  Turn 1/5: Player ▶ ... Coach ✓ APPROVED
  Status: COMPLETED (1 turn)

TASK-003: Create .env.example
  Turn 1/5: Player ▶ ... Coach ⚠ FEEDBACK
  Turn 2/5: Player ▶ ... Coach ✓ APPROVED
  Status: COMPLETED (2 turns)

TASK-004: Create src/ structure
  Turn 1/5: Player ▶ ... Coach ✓ APPROVED
  Status: COMPLETED (1 turn)

Wave 1 Complete: 4/4 tasks approved

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wave 2/4: Core Infrastructure
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

══════════════════════════════════════════════════════════════
FEATURE RESULT: SUCCESS
══════════════════════════════════════════════════════════════

Feature: Build Application Infrastructure
Status: COMPLETED
Tasks: 12/12 approved
Total Turns: 15
Duration: 23 minutes

Worktree: .guardkit/worktrees/FEAT-XXX
Branch: autobuild/FEAT-XXX

Next Steps:
  1. Review: cd .guardkit/worktrees/FEAT-XXX && git diff main
  2. Merge: git checkout main && git merge autobuild/FEAT-XXX
  3. Complete: /task-complete FEAT-XXX
```

### Verbose Mode

In `--verbose` mode, show additional details:
- Player implementation summary
- Coach validation details
- Files created/modified per task
- Test output summaries

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `guardkit/cli/display.py` | Create | Progress display utilities |
| `guardkit/orchestrator/feature_orchestrator.py` | Modify | Add display callbacks |

## Testing

```bash
# Normal mode
guardkit autobuild feature FEAT-XXX

# Verbose mode
guardkit autobuild feature FEAT-XXX --verbose

# Verify display is clear and informative
```

## Dependencies

- TASK-FBC-001 (CLI feature command)

## Notes

Good progress display is essential for long-running operations. Users need visibility into what's happening, especially when a feature has many tasks.
