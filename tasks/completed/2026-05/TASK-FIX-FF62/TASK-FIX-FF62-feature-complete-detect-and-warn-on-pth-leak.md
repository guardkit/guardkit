---
id: TASK-FIX-FF62
title: "/feature-complete detect-and-warn on dangling editable .pth references"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T13:30:00Z
completed: 2026-05-06T13:30:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed (18/18 tests, 89% line / 100% branch coverage on new module)"
completed_location: tasks/completed/2026-05/TASK-FIX-FF62/
organized_files:
  - TASK-FIX-FF62-feature-complete-detect-and-warn-on-pth-leak.md
  - implementation-plan.md
priority: medium
task_type: feature
parent_review: TASK-REV-FFC6
feature_id: FEAT-FFC6
implementation_mode: task-work
wave: 2
depends_on: [TASK-FIX-FF61]
complexity: 4
tags: [autobuild, feature-complete, defense-in-depth, pth-scanner, ffc3-bug-4]
related_tasks: [TASK-REV-FFC6, TASK-FIX-FF61]
test_results:
  status: passed
  coverage:
    line: 89
    branch: 100
    target_module: guardkit/worktrees/pth_leak_scanner.py
  tests_added: 18
  tests_passed: 18
  tests_failed: 0
  last_run: 2026-05-06T13:00:00Z
plan_audit:
  status: passed
  severity: medium
  files_planned: 5
  files_actual: 5
  files_variance_pct: 0
  loc_planned: 510
  loc_actual: 940
  loc_variance_pct: 84
  rationale: "LOC variance entirely in hardening tests + module docstring/constants block + defensive try/except wrappers required by AC-002/AC-004 'never abort cleanup' contract. Zero production-surface scope creep, zero new dependencies, same file count."
  decision: approved
---

# Task: `/feature-complete` detect-and-warn on dangling editable .pth references

## Description

Implements **Recommendation R2** (Layer 3 — detect-and-warn at finalization) from [TASK-REV-FFC6 review report](../../../.claude/reviews/TASK-REV-FFC6-review-report.md). This is defense-in-depth on top of TASK-FIX-FF61 (Layer 1).

After TASK-FIX-FF61 lands, new autobuild runs should never write to the parent venv. But this task still has value because:

1. **Pre-existing leaks** — users who hit the FFC3 bug before FF61 lands have already-broken parent venvs. Layer 3 surfaces those at the next `/feature-complete` so the user gets a one-line repair command instead of debugging a `ModuleNotFoundError` cascade.
2. **Future regressions** — if a uv version upgrade or a future code change ever bypasses Layer 1, Layer 3 catches it at the cleanup boundary instead of letting the silent corruption ship.
3. **Per the [absence-of-failure-is-not-success rule](../../../.claude/rules/absence-of-failure-is-not-success.md)**: trusting that Layer 1 silently always works is itself the false-green pattern. An independent verification step at the boundary is the prescribed remediation.

The hook is **read-only and warning-only**. It must never abort cleanup.

## Context

- **Affected file:** [`guardkit/cli/autobuild.py`](../../../guardkit/cli/autobuild.py) (or wherever the `/feature-complete` cleanup flow lives — locate the call site of `WorktreeManager.cleanup` for the feature/task being completed).
- **Helper file (optional):** introduce a small module under `guardkit/orchestrator/` or `guardkit/worktrees/` for the `.pth` scanner. May reuse anything TASK-FIX-FF61 introduces.
- **Depends on:** TASK-FIX-FF61 must merge first. FF61's `_isolated_env` / venv-isolation work establishes the contract that the scanner here verifies.

## Acceptance Criteria

### Implementation

- [ ] **AC-001:** Add a function (suggested: `find_pth_leaks(repo_root: Path, worktree_path: Path) -> List[Tuple[Path, str]]`) that returns `(pth_file, matching_line)` tuples for every editable `.pth` file under known venv roots that contains the worktree path as a substring.
  - Scan roots: `repo_root / ".venv"`, `repo_root / ".guardkit" / "venv"`. (Other roots may be added in future; start with these two.)
  - Glob: `lib/python*/site-packages/_editable_impl_*.pth`.
  - Read-only; never raises (catch `OSError` per file/dir).
  - Symlinks NOT followed (avoid surprise scans of unrelated venvs).
  - Returns `[]` (empty) when no leaks present — including when scan roots don't exist.
- [ ] **AC-002:** Wire the scanner into the `/feature-complete` cleanup flow:
  - Run BEFORE `WorktreeManager.cleanup(worktree)` (so the worktree path is still meaningful at warning-emit time).
  - For every leak found, print a one-line warning + a one-line repair hint:
    ```
    [warning] Editable install in <venv> points into worktree being removed:
      <pth_file>
      Repair: cd <repo_root> && uv pip install -e . --no-deps
    ```
  - Use the project's existing CLI output style (Rich console if used elsewhere; plain stderr otherwise).
  - **NEVER abort cleanup.** Even if 100 leaks are found, the warning is informational; cleanup still runs.
- [ ] **AC-003:** When the scanner finds zero leaks (the expected steady-state after FF61), emit nothing at INFO/WARNING level. (DEBUG log is acceptable for diagnostic traceability.)
- [ ] **AC-004:** When `repo_root` cannot be determined (e.g. the cleanup is invoked from a context where it's unavailable), skip the scan with a DEBUG log; never raise.

### Tests

- [ ] **AC-005:** `test_find_pth_leaks_detects_worktree_reference` — fixture creates a `.venv/lib/pythonX/site-packages/_editable_impl_pkg.pth` containing the worktree path; asserts the scanner returns one tuple matching that file.
- [ ] **AC-006:** `test_find_pth_leaks_returns_empty_when_clean` — fixture creates a `.pth` file pointing at an unrelated path; scanner returns `[]`.
- [ ] **AC-007:** `test_find_pth_leaks_handles_missing_venv_dir` — no `.venv` directory exists; scanner returns `[]`, no exception.
- [ ] **AC-008:** `test_find_pth_leaks_handles_unreadable_pth` — a `.pth` exists but is unreadable (permission error simulated via mock or `chmod 000` on a tmp file); scanner skips it, returns `[]`, no exception.
- [ ] **AC-009:** `test_find_pth_leaks_does_not_follow_symlinks` — `<repo_root>/.venv` is a symlink to an unrelated venv with leaks; scanner does not chase the symlink (returns `[]`).
- [ ] **AC-010:** `test_feature_complete_warns_but_does_not_abort` — integration test: create a fixture worktree + a parent `.venv` with a leaking `.pth`; run `/feature-complete` (or its programmatic entry point); assert (a) warning was emitted, (b) cleanup still ran (worktree directory removed).
- [ ] **AC-011:** `test_feature_complete_silent_when_no_leaks` — same shape, no leaking `.pth`; assert no warning emitted to stderr (DEBUG log allowed).

### Don't-break invariants

- [ ] **AC-012:** `/feature-complete` still works end-to-end on projects with no Python `.venv` at all (e.g. pure Node projects). The scanner returns `[]` early; no warning, no error.
- [ ] **AC-013:** `/feature-complete --force` still aborts on uncommitted changes per existing behaviour; the scanner runs after the merge step but before the cleanup step.
- [ ] **AC-014:** No new dependency added (the scanner uses only `pathlib` and stdlib `os`).

## Files Likely To Change

- `guardkit/cli/autobuild.py` — wire the scanner call into the cleanup flow. Or, depending on layout, the scanner may be invoked from a higher layer (e.g. an orchestrator method) that already has both `repo_root` and `worktree.path` in scope.
- `guardkit/worktrees/pth_leak_scanner.py` (NEW, suggested) — the scanner function. Alternative: bundle into `guardkit/worktrees/manager.py` if it fits naturally.
- `tests/unit/test_pth_leak_scanner.py` (NEW) — AC-005 through AC-009.
- `tests/integration/cli/test_feature_complete_pth_warning.py` (NEW) — AC-010 and AC-011.

## Out Of Scope

- Auto-repairing the leak (Layer 2 — explicitly skipped per review). The scanner warns; it does not run `uv pip install` itself.
- Scanning beyond `<repo_root>/.venv` and `<repo_root>/.guardkit/venv/`. Other venv discovery (Conda, pyenv, asdf, custom paths) is a future extension.
- TypeScript / .NET / Go / Rust / Flutter equivalent scanners — those stacks have no leak vector per [review F8](../../../.claude/reviews/TASK-REV-FFC6-review-report.md).

## Reproduction (manual)

```bash
# Manually corrupt a parent venv (simulating a pre-FFC6 autobuild leak):
cd <parent>
echo "/Users/.../guardkit/worktrees/FEAT-DEMO/src" \
  > .venv/lib/python*/site-packages/_editable_impl_demo.pth

# Run /feature-complete on the worktree:
/feature-complete FEAT-DEMO

# Expected post-fix output (somewhere in the cleanup section):
# [warning] Editable install in /Users/.../parent/.venv points into worktree being removed:
#   /Users/.../parent/.venv/lib/python3.14/site-packages/_editable_impl_demo.pth
#   Repair: cd /Users/.../parent && uv pip install -e . --no-deps

# Cleanup STILL completes; worktree dir gone.
```

## References

- [TASK-REV-FFC6 review report](../../../.claude/reviews/TASK-REV-FFC6-review-report.md) — Sequence Diagram 6 (Layer 3 detect-and-warn flow).
- [.claude/rules/absence-of-failure-is-not-success.md](../../../.claude/rules/absence-of-failure-is-not-success.md) — rationale for not trusting Layer 1's silent success without an independent boundary check.
- [TASK-FIX-FF61](TASK-FIX-FF61-bootstrap-worktree-venv-isolation.md) — must merge first.
