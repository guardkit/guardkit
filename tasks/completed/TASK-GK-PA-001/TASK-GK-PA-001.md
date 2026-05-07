---
id: TASK-GK-PA-001
title: Plan-audit must compare files_to_modify against git-modified set
status: completed
created: 2026-05-07 00:00:00+00:00
updated: 2026-05-07 13:00:00+00:00
completed: 2026-05-07T13:00:00Z
previous_state: in_review
state_transition_reason: "Task completed; all 8 ACs satisfied"
completed_location: tasks/completed/TASK-GK-PA-001/
priority: high
priority_band: P1
task_type: refactor
parent_review: TASK-REV-PEBR-001
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md
implementation_mode: task-work
wave: 1
complexity: 5
estimated_minutes: 90
dependencies: []
tags:
  - autobuild
  - plan-audit
  - file-comparison
  - regression-fix
  - P1
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-07T12:30:00Z
  summary: "55+ tests pass (39 plan auditor incl. 7 new + 5 coach validator + 8 integration + 3 new regression). 0 new ruff issues."
---

# Task: Plan-audit must compare files_to_modify against git-modified set

## Description

`PlanAuditor._compare_files`
([guardkit/installer/core/commands/lib/plan_audit.py:420-458](../../../installer/core/commands/lib/plan_audit.py#L420-L458))
only compares `files_to_create` against newly-created files. Files
that the plan declares as "to modify" are not validated at all.
Equally, `_scan_modified_files`
([plan_audit.py:210](../../../installer/core/commands/lib/plan_audit.py#L210))
admits in its docstring: *"Simplified implementation - actual version
would use git diff."*

This bug does not fire on FEAT-PEBR Wave-1 (PlanAuditor short-circuits
to "skipped" before this code runs because the stub plan has no
sections — see TASK-GK-AC-001). However, once the stub-plan path is
patched (whether via TASK-GK-AC-001 or via TASK-FRR-PEB-FM-001 in the
forge repo), the next FRR-PEB task to autobuild will encounter
`files_to_modify` declarations and must have them validated correctly
— otherwise the plan-audit becomes effectively cosmetic on the modify
axis.

## Acceptance Criteria

- [ ] AC-1: `_scan_modified_files` returns the list of files modified
  in the worktree by running `git diff --name-only HEAD` (or
  equivalent) instead of returning an empty/stub list.
- [ ] AC-2: `_compare_files` extends to a second comparison:
  `planned_modify - actual_modify` produces a "missing modification"
  discrepancy (severity `medium` not `high` — the audit signal is
  weaker for modifications than for missing creations).
- [ ] AC-3: `actual_modify - planned_modify` produces an "unplanned
  modification" discrepancy at severity `low` (advisory).
- [ ] AC-4: Tasks with `## Files to Modify` listing
  `src/forge/adapters/nats/pipeline_consumer.py` whose Player
  modifies that file pass the audit (no missing-modify discrepancy).
- [ ] AC-5: Tasks with no `## Files to Modify` section behave as
  before (the `files_to_modify` list defaults to `[]`, no
  discrepancies generated for that axis).
- [ ] AC-6: The deterministic auditor wrapper at
  `guardkit/orchestrator/agent_invoker.py:_compute_plan_audit_verdict`
  surfaces the new modify-axis fields
  (`extra_modifications`, `missing_modifications`) in its returned
  dict so the Coach can quote them in feedback.
- [ ] AC-7: Coach feedback assembly at
  `coach_validator.py:5320-5380` (the `plan_audit` branch in
  `_feedback_from_gates`) extends to mention modify-axis discrepancies
  in the same format as the existing extra_files/missing_files
  preview.
- [ ] AC-8: All modified files pass project-configured lint/format
  checks with zero errors.

## Test requirements

- Unit test: `_scan_modified_files` returns git-detected modified
  files with the worktree fixture used in TASK-GK-AC-001.
- Unit test: `_compare_files` correctly classifies missing-modify vs
  unplanned-modify with severity tiers `medium` / `low`.
- Integration test: a task with `## Files to Modify:
  pipeline_consumer.py` and a Player that modifies that file passes;
  same task with a Player that does NOT modify it produces a
  medium-severity discrepancy and `decision=feedback`.
- Existing plan-audit tests must continue to pass.

## Implementation notes

### Files to Modify

- `guardkit/installer/core/commands/lib/plan_audit.py` — `_scan_modified_files`
  (lines 210+), `_compare_files` (lines 420-458), and the discrepancy
  type definitions if needed
- `guardkit/orchestrator/agent_invoker.py` — `_compute_plan_audit_verdict`
  to surface new fields (around line 6096+)
- `guardkit/orchestrator/quality_gates/coach_validator.py` — feedback
  assembly in `_feedback_from_gates` plan_audit branch (lines
  5320-5380) to mention modify-axis discrepancies
- `tests/installer/test_plan_audit.py` — add the three new test
  classes

### Severity rationale

- Missing creation: `high` (today) — file the plan said would exist
  doesn't. Hard fail.
- Missing modification: `medium` — file the plan said would change
  didn't. Could be legitimate (Player found a better approach) or
  could be a real gap. Worth flagging but not blocking.
- Unplanned modification: `low` — Player touched something the plan
  didn't list. Often legitimate (test files, config tweaks, etc.).
  Advisory only.

### Recommended approach

```python
def _scan_modified_files(self, plan: Dict[str, Any]) -> List[str]:
    """Return git-modified files in the worktree (vs HEAD)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and not self._is_excluded(Path(line))
        ]
    except (subprocess.SubprocessError, OSError):
        return []  # Don't fail audit on git errors
```

`_compare_files` then adds:

```python
planned_modify = set(plan_data.get("files_to_modify", []))
actual_modify = set(actual.get("files_modified", []))

missing_modify = planned_modify - actual_modify
extra_modify = actual_modify - planned_modify

if missing_modify:
    discrepancies.append(Discrepancy(
        category="files_modify",
        severity="medium",  # NOT high — softer signal
        ...
    ))
```

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/installer/test_plan_audit.py -x -v
PYTHONPATH=. python -m pytest tests/quality_gates/test_coach_validator.py -x -v -k plan_audit
ruff check guardkit/installer/core/commands/lib/plan_audit.py guardkit/orchestrator/agent_invoker.py
```

## Out of scope

- The bare-basename scanner fix (TASK-GK-AC-001).
- The Coach gate-fail short-circuit fix (TASK-GK-CR-001).
- Adding `## Files to Modify` sections to forge tasks
  (TASK-FRR-PEB-FM-001).
