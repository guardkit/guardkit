---
id: TASK-BOOT-754A
title: Structured diagnostic logging for bootstrap and conditional approval
status: completed
created: 2026-02-18T00:00:00Z
updated: 2026-02-18T12:00:00Z
completed: 2026-02-18T12:00:00Z
completed_location: tasks/completed/TASK-BOOT-754A/
priority: high
tags: [autobuild, environment-bootstrap, diagnostics, logging, coach-validator]
task_type: feature
complexity: 2
parent_review: TASK-REV-C9E5
feature_id: FEAT-BOOT
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Structured diagnostic logging for bootstrap and conditional approval

## Description

Two diagnostic blind spots prevent rapid debugging of bootstrap and conditional approval issues:

1. **Conditional approval**: When it doesn't fire, there's no log showing which of the 5 conditions failed. The propagation gap (F3) was invisible in 859 lines of evidence.
2. **Bootstrap subprocess**: Output is captured (`capture_output=True`) but not logged at appropriate levels. TASK-BOOT-7369's diagnostic logging exists but the Python logger configuration doesn't propagate to subprocess output.

See: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3) — Findings 7 and 8, Recommendation 4 (R4).

## Context

### Conditional approval blind spot

The 5-condition AND at `coach_validator.py:620-626`:
```python
conditional_approval = (
    failure_class == "infrastructure"
    and failure_confidence == "high"
    and bool(requires_infra)
    and not docker_available
    and gates_status.all_gates_passed
)
```

When this evaluates to False, there is no log showing which condition failed. In the FEAT-BA28 evidence, this was the root cause of the stall, but required line-by-line code tracing to identify.

### Bootstrap subprocess blind spot

At `environment_bootstrap.py:621-624`:
```python
proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
```

- On failure: stderr is logged via `logger.warning()` (line 634-639) — visible
- On success: stdout is silently discarded — no visibility
- TASK-BOOT-7369's diagnostic logging uses `logging.getLogger(__name__)` but the subprocess (pip/npm) doesn't read the orchestrator's log level

## Acceptance Criteria

- [ ] Debug log added BEFORE conditional approval evaluation showing all 5 condition values
- [ ] Log format: `conditional_approval check: failure_class={}, confidence={}, requires_infra={}, docker_available={}, all_gates_passed={}`
- [ ] Bootstrap subprocess stderr logged at INFO level on failure (currently WARNING only)
- [ ] Bootstrap subprocess stdout logged at DEBUG level on success (currently discarded)
- [ ] Unit test verifying conditional approval log is emitted with correct values
- [ ] Unit test verifying bootstrap subprocess output is captured in logs

## Implementation Notes

### Conditional approval log (coach_validator.py)

Add immediately before the conditional_approval evaluation:

```python
logger.debug(
    "conditional_approval check: failure_class=%s, confidence=%s, "
    "requires_infra=%s, docker_available=%s, all_gates_passed=%s",
    failure_class,
    failure_confidence,
    requires_infra,
    docker_available,
    gates_status.all_gates_passed,
)
```

### Bootstrap subprocess output (environment_bootstrap.py)

In `_run_install()`, after the subprocess completes:

```python
if proc.returncode == 0:
    logger.info("Install succeeded for %s (%s)", manifest.stack, manifest.path.name)
    if proc.stdout:
        logger.debug("Install stdout:\n%s", proc.stdout)
    return True
else:
    logger.warning(
        "Install failed for %s (%s) with exit code %d:\nstderr: %s\nstdout: %s",
        manifest.stack, manifest.path.name, proc.returncode,
        proc.stderr or "(empty)", proc.stdout or "(empty)",
    )
    return False
```

## Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/quality_gates/coach_validator.py` | Add debug log before conditional approval evaluation (~line 619) |
| `guardkit/orchestrator/environment_bootstrap.py` | Improve subprocess output logging in `_run_install()` |
| `tests/unit/test_coach_validator_logging.py` | NEW: verify conditional approval log emission |
| `tests/unit/test_environment_bootstrap.py` | Add test for subprocess output logging |

## Source Review

- Review report: `.claude/reviews/TASK-REV-C9E5-review-report.md` (Revision 3)
- Evidence: `docs/reviews/autobuild-fixes/db_failed_after_env_changes.md`
