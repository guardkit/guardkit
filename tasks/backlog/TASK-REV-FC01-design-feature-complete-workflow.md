---
id: TASK-REV-FC01
title: Design feature-complete workflow and merge strategies
status: review_complete
created: 2025-01-24T10:00:00Z
updated: 2025-01-24T12:00:00Z
priority: high
tags: [architecture-review, feature-build, workflow-design, git-integration]
task_type: review
complexity: 7
decision_required: true
review_results:
  mode: decision
  depth: standard
  findings_count: 6
  recommendations_count: 6
  report_path: .claude/reviews/TASK-REV-FC01-review-report.md
  completed_at: 2026-01-24T12:00:00Z
  key_decisions:
    - merge_strategy: "REVISED: Prepare and Hand Off - let user use their preferred tool"
    - pr_workflow: "Deferred to future waves - Wave 1 is tool-agnostic"
    - task_completion: "Parallel with asyncio.gather"
    - worktree_cleanup: "User runs guardkit worktree cleanup after merge"
    - platform_support: "Wave 1 requires no platform CLI integration"
  implementation:
    feature_id: FEAT-FC-001
    tasks_created: 5
    tasks_path: tasks/backlog/feature-complete/
---

# Task: Design feature-complete workflow and merge strategies

## Description

Design the `/feature-complete` command that finalizes features after successful `feature-build` execution. This command is analogous to `/task-complete` but operates at the feature level, handling:

1. **Task Completion Integration**: Running `/task-complete` for each task in the feature (potentially in parallel to minimize user wait time)
2. **Feature Folder Management**: Moving feature folder from `tasks/backlog/{feature-slug}/` to `tasks/completed/{date}/{feature-slug}/`
3. **Feature YAML Archival**: Moving/updating `.guardkit/features/FEAT-XXXX.yaml` to completed state
4. **Git Worktree Merge Strategy**: Platform-agnostic merge workflow supporting:
   - Direct merge (no PR)
   - GitHub Pull Requests
   - Azure DevOps Pull Requests
   - GitLab Merge Requests
   - Bitbucket Pull Requests

## Context

Reference: Successful feature-build run output at `docs/reviews/feature-build/finally_success.md`

Key observations from the successful run:
- Feature: FEAT-A96D with 5 tasks across 3 waves
- Duration: 23m 24s for complete feature
- Worktree preserved at: `.guardkit/worktrees/FEAT-A96D`
- Branch: `autobuild/FEAT-A96D`
- Current "Next Steps" are manual:
  1. Review: `cd .guardkit/worktrees/FEAT-A96D`
  2. Diff: `git diff main`
  3. Merge: `git checkout main && git merge autobuild/FEAT-A96D`
  4. Cleanup: `guardkit worktree cleanup FEAT-A96D`

## Open Questions to Address

### 1. Merge Strategy Selection
How should the command determine which merge strategy to use?
- Auto-detect from `.git/config` remotes?
- User configuration in `.guardkit/config.yaml`?
- Interactive prompt?
- CLI flag?

### 2. PR/MR Creation
If using PR workflow:
- Should the command create the PR automatically?
- What should be the PR title/description template?
- Should it wait for PR approval or just create and return?
- How to handle PR merge policies (squash, rebase, merge commit)?

### 3. Direct Merge Workflow
If NOT using PRs:
- Merge to which branch? (main, develop, etc.)
- Fast-forward only or create merge commit?
- Should it push to remote automatically?

### 4. Task Completion Parallelization
- Run all `/task-complete` calls in parallel?
- What's the failure mode if one task-complete fails?
- Should task completion be a separate phase or integrated?

### 5. Worktree Cleanup
- Automatic cleanup after successful merge/PR creation?
- Keep worktree until PR is merged (for PR workflows)?
- User-controlled cleanup flag?

### 6. Feature State Transitions
```
feature-build SUCCESS → AWAITING_REVIEW
feature-complete START → MERGING
merge SUCCESS → COMPLETED (archived)
```

### 7. Rollback/Recovery
- What if merge fails?
- What if PR creation fails?
- How to resume partial feature-complete?

## Acceptance Criteria

- [ ] Clear decision on merge strategy detection/selection
- [ ] PR workflow design for GitHub, Azure DevOps, GitLab, Bitbucket
- [ ] Direct merge workflow design
- [ ] Task completion parallelization strategy
- [ ] Feature folder/YAML archival specification
- [ ] Worktree cleanup policy
- [ ] Error handling and recovery design
- [ ] Configuration schema for user preferences
- [ ] CLI interface specification for `/feature-complete`

## Review Output Expected

1. **Architecture Decision Record (ADR)** for merge strategy
2. **Command Specification** for `/feature-complete`
3. **Configuration Schema** for `.guardkit/config.yaml` merge settings
4. **State Diagram** for feature completion workflow
5. **Implementation Recommendations** with complexity estimates

## Related Files

- `docs/reviews/feature-build/finally_success.md` - Successful feature-build output
- `installer/core/commands/feature-build.md` - Feature-build command spec
- `installer/core/commands/task-complete.md` - Task-complete command spec
- `src/guardkit/orchestrator/feature_orchestrator.py` - Feature orchestrator
- `src/guardkit/cli/autobuild.py` - AutoBuild CLI

## Notes

The goal is minimal user overhead - the feature-complete command should handle everything automatically based on team configuration, with the merge/PR step being the only potential human intervention point.

Consider that `/task-complete` runs may execute in parallel with other tasks, so the elapsed time overhead should be minimal from the user's perspective.
