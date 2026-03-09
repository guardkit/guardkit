---
id: TASK-CRV-537E
title: Add orchestrator-level command execution for runtime criteria
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T12:30:00Z
completed: 2026-03-09T12:30:00Z
previous_state: in_review
state_transition_reason: "Task complete — all acceptance criteria met, 68 tests passing"
completed_location: tasks/completed/TASK-CRV-537E/
priority: high
tags: [autobuild, command-execution, verification, orchestrator]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
---

# Task: Add orchestrator-level command execution for runtime criteria

## Description

Add a verification step in `autobuild.py` that executes `command_execution` acceptance criteria in the worktree BEFORE Coach validation. This directly fixes the FEAT-2AAA class of failures where runtime criteria (`pip install succeeds`, `python -c import runs`) were unverifiable via the synthetic report path.

The orchestrator will:
1. Classify acceptance criteria using the criteria classifier
2. Execute each `command_execution` criterion's extracted command in the worktree
3. Inject successful results into the synthetic report as `requirements_addressed`
4. Pass the enriched report to the Coach for validation

## Acceptance Criteria

- [ ] `command_execution` criteria identified by `classify_acceptance_criteria()` in autobuild turn loop
- [ ] **Worktree path assertion**: Defensive check that `cwd` is under `.guardkit/worktrees/` before any `subprocess.run()` — never execute against the base repo
- [ ] Commands executed via `subprocess.run()` with `shell=True`, `cwd=worktree_path`, `timeout=60`
- [ ] Successful command results injected into `requirements_addressed` of synthetic report
- [ ] Failed command results logged with stdout/stderr for diagnostics
- [ ] Timeout protection (60s per command, 180s total for all criteria)
- [ ] Commands only execute when synthetic report path is active (not when Player returns structured data)
- [ ] Existing autobuild tests continue to pass
- [ ] New test verifying command execution and result injection
- [ ] New test verifying worktree path assertion rejects non-worktree paths

## Implementation Notes

Integration point is `autobuild.py` after `_build_synthetic_report()` and before Coach validation.

```python
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    classify_acceptance_criteria,
    CriterionType,
)

WORKTREE_SENTINEL = ".guardkit/worktrees/"

def _assert_worktree_path(path: Path) -> None:
    """Defensive check: never execute commands outside a worktree."""
    resolved = str(path.resolve())
    if WORKTREE_SENTINEL not in resolved:
        raise RuntimeError(
            f"Refusing to execute commands outside worktree. "
            f"Path '{resolved}' does not contain '{WORKTREE_SENTINEL}'"
        )

# After synthetic report is built, before Coach validation:
_assert_worktree_path(worktree_path)
classification = classify_acceptance_criteria(acceptance_criteria)
for criterion in classification.command_criteria:
    if criterion.extracted_command:
        try:
            proc = subprocess.run(
                criterion.extracted_command,
                shell=True,
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode == 0:
                synthetic_report["requirements_addressed"].append(criterion.text)
                logger.info("Runtime criterion verified: %s", criterion.text[:80])
            else:
                logger.warning(
                    "Runtime criterion failed (exit %d): %s\nstderr: %s",
                    proc.returncode, criterion.text[:80], proc.stderr[:200]
                )
        except subprocess.TimeoutExpired:
            logger.warning("Runtime criterion timed out: %s", criterion.text[:80])
```

## Security Considerations

- **Worktree assertion**: Defensive path check ensures commands never execute against the base repo — `cwd` must contain `.guardkit/worktrees/`
- Commands execute in the worktree (isolated from host)
- 60s timeout per command prevents hanging
- Only `command_execution` classified criteria are executed (not arbitrary text)
- Commands originate from task spec files (authored by the user), not from external input
- Command allowlisting is deferred for initial implementation but should be revisited as the feature matures

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (primary — turn loop)
- `tests/unit/test_autobuild.py` (add command execution test)
