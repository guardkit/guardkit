---
id: TASK-REV-9AC5
title: Analyse feature-build command output - SDK timeout and worktree issues
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
created: 2026-01-07T20:30:00Z
updated: 2026-01-08T12:00:00Z
priority: high
tags: [feature-build, autobuild, sdk-timeout, worktree, debugging, phase-4.5, test-enforcement]
complexity: 5
related_features:
  - feature-plan-schema-fix
  - feature-build-cli-native
related_files:
  - docs/reviews/feature-build/feature-build-output.md
review_results:
  mode: architectural
  depth: standard
  score: 62
  findings_count: 5
  recommendations_count: 6
  decision: implement
  report_path: .claude/reviews/TASK-REV-9AC5-review-report.md
  completed_at: 2026-01-08T12:00:00Z
  revisions: 1
  revision_reason: "Added Finding 5 (Phase 4.5 resilience) and R6 after deep dive into test enforcement loop behavior"
  implementation_tasks_created: 2026-01-08T12:15:00Z
  implementation_tasks:
    - TASK-SDK-a7f3  # R1: Add --sdk-timeout CLI flag (CRITICAL)
    - TASK-WKT-b2c4  # R2: Force worktree cleanup (HIGH)
    - TASK-WKT-c5d7  # R3: Branch cleanup fallback (MEDIUM)
    - TASK-STATE-d4e9  # R4: Multi-layered state detection (HIGH, phased)
    - TASK-SDK-e7f2  # R5: Increase default timeout (LOW)
    - TASK-P45-f3a1  # R6: Phase 4.5 resilience (MEDIUM, phased)
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse feature-build command output - SDK timeout and worktree issues

## Context

Following implementation of:
1. **feature-plan-schema-fix** - Fixed YAML schema mismatches between `/feature-plan` and `FeatureLoader`
2. **feature-build-cli-native** - Added native CLI support for `guardkit autobuild feature`

The `/feature-build` command was tested with a 10-task feature (FEAT-119C: Application Infrastructure). Good progress was made, but several issues need to be addressed.

## Observed Issues

### Issue 1: Player Agent SDK Timeout (300s)
**Severity**: HIGH

The Player agent times out at 300 seconds before completing its JSON report file:
```
ERROR: SDK timeout after 300s: Agent invocation exceeded 300s timeout
Player report not found: .../player_turn_1.json
```

**Evidence**:
- Player agent created substantial code (224-line config.py, ~400-line test file)
- Tests ran: 32/40 passing (80%)
- Implementation was largely complete
- JSON report never written before timeout

**Root Cause**:
- Default SDK timeout (300s) is too short for complex tasks
- Task frontmatter `sdk_timeout` configuration not being read by CLI

### Issue 2: Worktree Cleanup on --fresh
**Severity**: MEDIUM

The `--fresh` flag fails to clean up existing worktrees with untracked files:
```
fatal: '.../worktrees/FEAT-119C' contains modified or untracked files, use --force to delete it
```

Then fails to create a new worktree:
```
fatal: a branch named 'autobuild/FEAT-119C' already exists
```

**Root Cause**:
- WorktreeManager doesn't use `--force` flag for cleanup
- Branch cleanup not attempted after worktree cleanup fails

### Issue 3: --resume Not Detecting Previous Work
**Severity**: MEDIUM

When resuming:
- Shows "Completed tasks: 0, Pending tasks: 9"
- But actual work was done (files created, tests passing)
- Restarts from turn 1 instead of recognizing partial completion

**Root Cause**:
- Player report file is required to track completion
- Without report, state tracking is lost
- No fallback detection of "work done but report missing"

### Issue 4: Test Failures (CORS Origins Parsing)
**Severity**: LOW

8/40 tests failing due to Pydantic Settings v2 CORS origins parsing:
```
SettingsError: error parsing value for field "cors_origins" from source "EnvSettingsSource"
```

**Note**: This is an implementation issue in the generated code, not a GuardKit issue.

## What Worked Well

1. **Feature orchestration flow** - Wave-based execution worked correctly
2. **Progress display** - Clear status output with rich formatting
3. **Pre-loop quality gates** - Architecture score (80/100) and complexity (5) extracted
4. **Worktree creation** - Initial setup worked perfectly
5. **Player code generation** - High-quality code produced despite timeout
6. **Error messaging** - Clear guidance on next steps

## Recommendations

### R1: Add --sdk-timeout CLI Flag (HIGH)
```bash
guardkit autobuild feature FEAT-XXX --sdk-timeout 600
```

Also read `autobuild.sdk_timeout` from task/feature frontmatter.

### R2: Force Worktree Cleanup (MEDIUM)
Update `WorktreeManager.remove()` to use `--force` flag when called from `--fresh` mode.

### R3: Add Branch Cleanup (MEDIUM)
When worktree creation fails due to existing branch:
```python
git branch -D autobuild/FEAT-XXX
```

### R4: Partial Work Detection (MEDIUM)
If Player report missing but files were created, detect this and offer:
- "Previous work detected. Create report manually?"
- Or fall back to Coach verification of existing work

### R5: Increase Default Timeout (LOW)
Consider 600s default for feature-level orchestration vs 300s for single tasks.

## Acceptance Criteria

- [ ] Identify root cause of SDK timeout vs task frontmatter sdk_timeout not being read
- [ ] Recommend fix for worktree cleanup with --force
- [ ] Recommend fix for branch cleanup on fresh start
- [ ] Assess partial work detection feasibility
- [ ] Prioritize fixes for next implementation sprint

## Review Mode

**Recommended**: `--mode=architectural --depth=standard`

Focus areas:
1. SDK timeout configuration flow
2. WorktreeManager error handling
3. State tracking in FeatureOrchestrator

## Related

- **Output Log**: [docs/reviews/feature-build/feature-build-output.md](../docs/reviews/feature-build/feature-build-output.md)
- **Schema Fix Feature**: [tasks/backlog/feature-plan-schema-fix/](./feature-plan-schema-fix/)
- **CLI Native Feature**: [tasks/backlog/feature-build-cli-native/](./feature-build-cli-native/)
