---
id: TASK-GK-AC-001
title: AC scanner must not flag bare basenames as missing files
status: backlog
created: 2026-05-07 00:00:00+00:00
updated: 2026-05-07 00:00:00+00:00
priority: high
priority_band: P0
task_type: feature
parent_review: TASK-REV-PEBR-001
parent_review_repo: forge
review_report: ../../../forge/docs/reviews/FEAT-PEBR-failed-run-1-analysis.md
implementation_mode: task-work
wave: 1
complexity: 4
estimated_minutes: 75
dependencies: []
tags:
  - autobuild
  - coach-evaluator
  - plan-audit
  - ac-scanner
  - regression-fix
  - P0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: AC scanner must not flag bare basenames as missing files

## Description

`AgentInvoker._scan_ac_for_missing_paths`
([guardkit/orchestrator/agent_invoker.py:6028-6094](../../../guardkit/orchestrator/agent_invoker.py#L6028-L6094))
extracts file-like tokens from acceptance-criteria text and flags any
that don't exist *verbatim* under the worktree root. When AC text
mentions a file by basename only (e.g. `pipeline_consumer.py`), the
check `(self.worktree_path / "pipeline_consumer.py").exists()` returns
`False` even though the file lives at
`src/forge/adapters/nats/pipeline_consumer.py` and was correctly
modified by the Player.

This is the **primary root cause of the FEAT-PEBR Wave-1
UNRECOVERABLE_STALL** (see review report, AC-1). The verdict
propagates as `plan_audit.violations > 0` → Coach gate fail → Coach
short-circuits → criteria_passed = 0 → stall on turn 3.

The scanner regex set is shared with
`synthetic_report.generate_file_existence_promises` (per the docstring
at lines 6034-6038), so the fix must keep that path unchanged.

## Acceptance Criteria

- [ ] AC-1: A new opt-in parameter (`skip_bare_basenames: bool = False`)
  on the path-extraction helper, OR a glob fallback
  (`worktree.rglob(basename)`) inside `_scan_ac_for_missing_paths`,
  causes bare basenames in AC text to NOT be reported as missing when
  the file exists anywhere under the worktree.
- [ ] AC-2: Reproduce the FEAT-PEBR failure in a unit test:
  given AC text containing `pipeline_consumer.py` (bare basename) and
  a worktree with the file at `src/forge/adapters/nats/pipeline_consumer.py`,
  `_scan_ac_for_missing_paths` returns an empty list. (Today it returns
  `["pipeline_consumer.py"]`.)
- [ ] AC-3: When the AC text contains a fully-qualified path that
  genuinely doesn't exist (e.g. `src/foo/bar/missing.py`), the path is
  STILL reported as missing. (Don't over-correct — real missing files
  must keep firing.)
- [ ] AC-4: The synthetic-report path
  (`synthetic_report.generate_file_existence_promises` and any other
  caller of the shared regex set) is unchanged behaviourally.
  Demonstrate via a test fixture or by passing the new parameter only
  in the audit path.
- [ ] AC-5: A new regression test runs the FEAT-PEBR worktree fixture
  end-to-end through `_compute_plan_audit_verdict` and asserts
  `status == "passed"` (or "skipped") instead of "violation".
- [ ] AC-6: All modified files pass project-configured lint/format
  checks with zero errors.

## Test requirements

- Unit test for the basename-scanner change (AC-1, AC-2, AC-3).
- Unit test for synthetic-report path non-regression (AC-4).
- Integration test using a fixture that mirrors the FEAT-PEBR worktree
  layout (AC-5).
- Existing tests under
  `tests/orchestrator/test_agent_invoker.py` and
  `tests/quality_gates/test_coach_validator.py` must continue to pass.

## Implementation notes

### Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — `_scan_ac_for_missing_paths`
  at lines 6028-6094, and the call site at line 6150.
- `tests/orchestrator/test_agent_invoker.py` — add the three new test
  classes per AC-2/3/4.

### Files to Create

- `tests/fixtures/feat_pebr_worktree/` — minimal worktree fixture
  containing `src/forge/adapters/nats/pipeline_consumer.py` (empty
  file) and a copy of TASK-FRR-PEB-001's task body (for AC-5
  regression test).

### Recommended approach

Option (a) — narrowest change, recommended:

```python
def _scan_ac_for_missing_paths(
    self,
    task_id: str,
    *,
    flag_basenames: bool = False,  # NEW
) -> List[str]:
    ...
    for p in paths:
        if not p.endswith(source_exts):
            continue
        # NEW: skip bare basenames unless caller explicitly opts in.
        if not flag_basenames and "/" not in p:
            continue
        if not (self.worktree_path / p).exists():
            missing.append(p)
    return sorted(set(missing))
```

Then in `_compute_plan_audit_verdict` at line 6150, call with
`flag_basenames=False` (the default). The synthetic-report caller (if
any) keeps the current behaviour by passing `flag_basenames=True` or
relying on its own glob.

Option (b) — glob fallback (keep current signature):

```python
for p in paths:
    if not p.endswith(source_exts):
        continue
    if (self.worktree_path / p).exists():
        continue
    # NEW: for basenames, glob the worktree before declaring missing.
    if "/" not in p:
        if any(self.worktree_path.rglob(p)):
            continue
    missing.append(p)
```

Option (a) is preferred — narrower diff, easier to test, no rglob
walk on every audit. Option (b) is a fallback if the scanner has too
many call sites to change.

## Coach validation commands

```bash
PYTHONPATH=. python -m pytest tests/orchestrator/test_agent_invoker.py -x -v -k scan_ac
PYTHONPATH=. python -m pytest tests/quality_gates/test_coach_validator.py -x -v
ruff check guardkit/orchestrator/agent_invoker.py tests/orchestrator/test_agent_invoker.py
```

## Out of scope

- Fixing `plan_audit.py:_compare_files` (modify-vs-create) — that is
  TASK-GK-PA-001.
- Changing the Coach short-circuit to populate requirements on gate
  fail — that is TASK-GK-CR-001.
- Updating forge task files to add explicit `## Files to Create`
  sections — that is TASK-FRR-PEB-FM-001 in the forge repo.
