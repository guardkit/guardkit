---
id: TASK-REV-CLEANUP
title: "Review: Auto-cleanup of unstaged guardkit artifacts after autobuild feature completion"
status: review_complete
created: 2026-04-12T00:00:00Z
updated: 2026-04-12T08:30:00Z
priority: medium
task_type: review
tags: [autobuild, guardkit, cleanup, workflow, developer-experience]
complexity: 4
test_results:
  status: n/a
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  score: 65
  findings_count: 5
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-CLEANUP-review-report.md
  completed_at: 2026-04-12T08:30:00Z
---

# Review: Auto-cleanup of unstaged guardkit artifacts after autobuild feature completion

## Problem

After merging and cleaning up a feature worktree, several files remain as unstaged or
untracked changes on main. These are orchestration artifacts written to the main tree
during the build, not part of the worktree branch. The `feature-complete` command only
cleans up worktrees — it does not touch main-scoped autobuild artifacts.

### Artifact Categories

1. `.guardkit/features/FEAT-*.yaml` — feature status tracking files updated by orchestrator (currently 27 files)
2. `.guardkit/autobuild/FEAT-*/` — per-feature review summaries and orchestrator artifacts (untracked)
3. `.guardkit/autobuild/TASK-*/` — per-task build logs, progress.log, review summaries (currently 242 dirs, 6.7MB total, untracked)
4. `tasks/backlog/feat-*/TASK-*.md` — task markdown files updated with progress during builds
5. `.guardkit/archive/FEAT-*/` — archives created by feature-complete but never cleaned

> **Note:** `.guardkit/graphiti-query-log.jsonl` is already covered by `.gitignore` (line 83)
> and does not appear as unstaged changes. No action needed for this file.

### Scale and Growth

These artifacts accumulate unboundedly across features. As of 2026-04-12:
- 27 feature YAML files in `.guardkit/features/`
- 242 autobuild directories in `.guardkit/autobuild/`
- 6.7MB total in `.guardkit/autobuild/`

### Manual Worktree Merge Workflow

Currently the end-to-end worktree lifecycle (commit remaining changes, merge to main, delete
worktree branch) is performed manually via Claude Code after autobuild completes. The
`feature-complete` command should own this entire workflow so that a single command takes a
completed feature from worktree to merged-and-cleaned-up, rather than requiring manual
orchestration each time.

## Questions to Answer

- Which of these files should be committed as part of the feature merge (bundled into the merge commit or a follow-up)?
- Which should be auto-cleaned/deleted after merge?
- Should the `feature-complete` skill (Step 5: Archive and Cleanup) be extended to handle this?
- Should `feature-complete` own the full worktree lifecycle (commit → merge → branch delete → artifact cleanup)?
- Are any of these files useful for historical reference vs purely ephemeral?
- What's the right boundary between worktree-scoped artifacts and main-scoped orchestration state?
- Should `.guardkit/autobuild/` be added to `.gitignore` entirely (it's currently tracked in some commits)?

## Scope

Review only — propose a cleanup strategy, don't implement yet.

## Evidence

Observed after FEAT-A337 and FEAT-B1CE autobuild completions on 2026-04-11 and 2026-04-12.
Manual housekeeping commits were created to clear the working tree (e.g. `d8b90828d` "reviews
and cleanup", `181b3bdc2` "chore: cleanup FEAT-GI worktree after merge").

### Current feature-complete Cleanup Gap

The `feature-complete` command (see `installer/core/commands/feature-complete.md`, Step 5)
archives the feature YAML and removes worktrees, but does NOT:
- Delete `.guardkit/autobuild/TASK-*/` directories for merged tasks
- Delete `.guardkit/autobuild/FEAT-*/` directories for the completed feature
- Clean stale feature YAML files for fully-merged features
- Prune `.guardkit/archive/` over time
