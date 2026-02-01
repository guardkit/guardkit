---
id: TASK-FB-004
title: Update /feature-build to Poll Progress File
status: backlog
created: 2025-01-31T16:00:00Z
priority: high
tags: [feature-build, ux, progress, phase-1]
complexity: 5
implementation_mode: task-work
parent_review: TASK-REV-FBA1
feature_id: FEAT-FB-UX
wave: 2
dependencies: [TASK-FB-002, TASK-FB-003]
---

# Task: Update /feature-build to Poll Progress File

## Context

The `/feature-build` slash command currently invokes `guardkit autobuild` via Bash tool and waits for completion with no feedback. With TASK-FB-003's progress file, we can poll for updates and display progress to the user.

**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)

## Requirements

Update `/feature-build` command execution in `feature-build.md` to:

1. Run `guardkit autobuild` with `run_in_background`
2. Poll progress file every 30 seconds
3. Display summarized progress to user
4. Detect completion and show final results

## Acceptance Criteria

- [ ] `/feature-build` runs autobuild in background
- [ ] Progress file polled every 30 seconds
- [ ] User sees: `Wave 1/3, TASK-FB-002 (Turn 2/5, Coach Validation) - 4m 5s elapsed`
- [ ] On completion, final summary displayed
- [ ] On timeout/error, appropriate message shown
- [ ] Documentation updated in `feature-build.md`

## Implementation Notes

The `/feature-build` command spec should instruct Claude to:

```markdown
### CRITICAL EXECUTION INSTRUCTIONS (Updated)

1. **Start build in background**:
   ```bash
   guardkit autobuild task TASK-XXX --progress-file
   ```
   Use Bash tool with `run_in_background: true`

2. **Poll progress file** every 30 seconds:
   ```bash
   cat .guardkit/autobuild/TASK-XXX/progress.json 2>/dev/null || echo "{}"
   ```

3. **Display progress** to user:
   ```
   Building TASK-XXX...
   Wave 1/3, TASK-FB-002 (Turn 2/5, Coach Validation) - 4m 5s elapsed
   ```

4. **Check for completion**:
   - `status: "completed"` → Show final summary
   - `status: "failed"` → Show error details
   - `status: "running"` → Continue polling

5. **Timeout handling**:
   After 30 minutes with no progress update, warn user and offer options.
```

## Example User Experience

```
/feature-build TASK-AUTH-001

Starting autonomous build for TASK-AUTH-001...
Build running in background. Polling for progress...

[1m 30s] Turn 1/5: Player Implementation in progress...
[3m 45s] Turn 1/5: Player completed. Coach validating...
[4m 20s] Turn 1/5: Coach approved!

Build APPROVED after 1 turn.
Worktree: .guardkit/worktrees/TASK-AUTH-001

Next steps:
  1. Review: cd .guardkit/worktrees/TASK-AUTH-001 && git diff main
  2. Merge: /feature-complete TASK-AUTH-001
```

## Files to Modify

- `installer/core/commands/feature-build.md` - Update execution instructions

## Dependencies

- TASK-FB-002 (text output for non-TTY used in progress display)
- TASK-FB-003 (progress file to poll)

## Future: Phase 2 Evolution

In Phase 2, polling is replaced by NATS subscription:

```python
# Phase 2 (future)
async for msg in nats_client.subscribe(f"guardkit.builds.{task_id}.status"):
    display_progress(msg.data)
```

The polling approach is designed to have the same user-facing output format.
