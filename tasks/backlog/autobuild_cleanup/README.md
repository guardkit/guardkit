# AutoBuild Artifact Cleanup

## Problem

After merging and cleaning up a feature worktree, autobuild orchestration artifacts remain committed to git on the main branch. The `feature-complete` command only cleans up worktrees but does not remove `.guardkit/autobuild/` artifacts, feature YAML files, or own the full merge lifecycle.

**Current state** (as of 2026-04-12):
- 241 TASK directories in `.guardkit/autobuild/` (6.7MB) — committed to git
- 27 feature YAML files in `.guardkit/features/` — never pruned
- `.guardkit/archive/` — specified in spec but never created
- Manual worktree merge workflow required before `feature-complete`

## Solution

Three-wave implementation to establish proper artifact lifecycle management:

1. **Wave 1**: Gitignore autobuild artifacts + one-time cleanup (immediate, low risk)
2. **Wave 2**: Extend `feature-complete` Step 5 with artifact cleanup + archive (spec change)
3. **Wave 3**: Full worktree lifecycle ownership in `feature-complete` (spec change)

## Subtasks

| ID | Title | Wave | Mode | Depends On |
|----|-------|------|------|------------|
| TASK-AC-001 | Gitignore autobuild artifacts and one-time cleanup | 1 | task-work | — |
| TASK-AC-002 | Extend feature-complete Step 5 with artifact cleanup | 2 | task-work | TASK-AC-001 |
| TASK-AC-003 | Full worktree lifecycle ownership in feature-complete | 3 | task-work | TASK-AC-002 |

## Parent Review

- **Review**: TASK-REV-CLEANUP
- **Report**: [.claude/reviews/TASK-REV-CLEANUP-review-report.md](../../.claude/reviews/TASK-REV-CLEANUP-review-report.md)
- **Score**: 65/100
