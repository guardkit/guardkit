# Feature: Native CLI Feature-Build Command

## Problem Statement

When users run `/feature-build FEAT-XXX`, they see fallback messages like:

```
CLI_NOT_AVAILABLE
Mode: Task tool fallback (CLI not available)
```

This "fallback" messaging **dents user confidence** even though the Task tool fallback works excellently (85/100 architecture score, 12/12 tasks validated in testing).

## Solution

Implement native CLI support for feature-mode orchestration so users see:

```
guardkit autobuild feature FEAT-XXX
Mode: CLI native
```

No fallback messages, no "CLI not available" warnings.

## Subtasks

| Task ID | Title | Priority | Effort | Mode |
|---------|-------|----------|--------|------|
| TASK-FBC-001 | Add `guardkit autobuild feature` CLI command | HIGH | 8-12h | task-work |
| TASK-FBC-002 | Add resume support for feature orchestration | MEDIUM | 4-6h | task-work |
| TASK-FBC-003 | Enhance Player agent test execution | LOW | 1-2h | direct |
| TASK-FBC-004 | Improve progress display for feature mode | LOW | 2-3h | direct |

## Implementation Waves

### Wave 1: Core CLI (TASK-FBC-001)
- Add `feature` subcommand to `guardkit autobuild`
- Load feature YAML and parse waves
- Execute Player-Coach loop per task
- Shared worktree per feature

### Wave 2: Reliability (TASK-FBC-002)
- State persistence in feature YAML
- `--resume` flag implementation
- Interrupted task recovery

### Wave 3: Polish (TASK-FBC-003, TASK-FBC-004)
- Player test execution before reporting
- Wave progress display
- Turn-by-turn status updates

## Success Criteria

1. No "CLI not available" messages when CLI is installed
2. `guardkit autobuild feature FEAT-XXX` works end-to-end
3. Resume from interruption works
4. Progress display shows wave/task status

## Related

- Review: TASK-REV-FB01 (source of recommendations)
- Report: `.claude/reviews/TASK-REV-FB01-cli-fallback-review-report.md`
