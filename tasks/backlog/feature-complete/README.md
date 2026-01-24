# Feature: /feature-complete Command (Wave 1)

**Feature ID:** FEAT-FC-001
**Parent Review:** TASK-REV-FC01
**Created:** 2026-01-24

## Overview

Implements the `/feature-complete` command - the feature-level counterpart to `/task-complete`. Wave 1 uses a "Prepare and Hand Off" approach, completing all GuardKit housekeeping and letting users merge/create PRs with their preferred git tool (GitKraken, Fork, Tower, etc.).

## Wave 1 Scope

**What `/feature-complete` does:**
1. Run `/task-complete` for all tasks (parallel)
2. Move feature folder to `tasks/completed/{date}/{slug}/`
3. Update feature YAML status to `awaiting_merge`
4. Display clear instructions for manual merge/PR
5. Provide cleanup command after user confirms merge

**What user does (with their preferred tool):**
- Open GitKraken/Fork/Tower → merge or create PR
- OR use `gh pr create` / `glab mr create` if they prefer CLI
- OR just `git merge` from terminal

## Tasks

| Task ID | Title | Complexity | Mode |
|---------|-------|------------|------|
| TASK-FC-001 | Create feature-complete orchestrator skeleton | 3 | task-work |
| TASK-FC-002 | Implement parallel task completion | 3 | task-work |
| TASK-FC-003 | Implement feature folder archival | 2 | direct |
| TASK-FC-004 | Add merge instruction display | 1 | direct |
| TASK-FC-005 | Add guardkit worktree cleanup command | 2 | task-work |

## Execution Order

All tasks can run in parallel (no dependencies).

## Expected Output

```
══════════════════════════════════════════════════════════════
FEATURE COMPLETE: FEAT-A96D
══════════════════════════════════════════════════════════════

✓ Task Completion
  ✓ TASK-FHA-001: Archived
  ✓ TASK-FHA-002: Archived
  All 5 tasks completed

✓ Feature Archival
  ✓ Moved to: tasks/completed/2026-01-24/fastapi-health/

══════════════════════════════════════════════════════════════
📋 READY FOR MERGE
══════════════════════════════════════════════════════════════

Branch: autobuild/FEAT-A96D → main
Worktree: .guardkit/worktrees/FEAT-A96D

Use your preferred tool to complete the merge:
  • GitKraken/Fork/Tower: Open worktree, create PR or merge
  • CLI: git checkout main && git merge --no-ff autobuild/FEAT-A96D

After merge: guardkit worktree cleanup FEAT-A96D
══════════════════════════════════════════════════════════════
```

## Future Waves (Deferred)

- Wave 2: GitHub `gh` CLI auto-PR (on demand)
- Wave 3: GitLab/Azure CLI integration (on demand)
- Wave 4: Auto-merge after approval (enterprise)

## Related Files

- [Review Report](.claude/reviews/TASK-REV-FC01-review-report.md)
- [feature-build.md](installer/core/commands/feature-build.md)
- [task-complete.md](installer/core/commands/task-complete.md)
- [feature_orchestrator.py](guardkit/orchestrator/feature_orchestrator.py)
