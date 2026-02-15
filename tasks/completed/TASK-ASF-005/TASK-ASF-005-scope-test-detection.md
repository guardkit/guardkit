---
id: TASK-ASF-005
title: Scope test detection to task-relevant directories
task_type: bugfix
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 3
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-ASF-003
  - TASK-ASF-004
priority: high
status: completed
completed: 2026-02-15T00:00:00Z
completed_location: tasks/completed/TASK-ASF-005/
tags: [autobuild, stall-fix, R5, phase-3, test-detection]
---

# Task: Scope test detection to task-relevant directories

## Description

The test detection during state recovery runs `pytest --tb=no -q` across the entire worktree (`coach_verification.py:254`), meaning pre-existing test failures mask task-specific test results. In the FEAT-AC1A run, Turn 5's Player created 13 passing tests in `tests/seam/`, but the worktree-wide pytest run reported 0 tests because other tests failed first.

This fix must be in place **before** R4-full (TASK-ASF-006) to prevent the false approval risk identified in the diagnostic diagrams: if synthetic reports gain file-existence promises but test detection is still worktree-wide, scaffolding tasks could be approved via promises while their task-specific tests are actually failing.

## Root Cause Addressed

- **F3**: Test detection runs across entire worktree, not scoped to task (`coach_verification.py:254`)

## Implementation

### Option A: Accept optional test_paths parameter (Recommended)

```python
# coach_verification.py:254 (modified)
def _run_tests(self, test_paths: list[str] | None = None) -> TestResult:
    """Run tests, optionally scoped to specific paths."""
    cmd = ["pytest", "--tb=no", "-q"]
    if test_paths:
        cmd.extend(test_paths)

    result = subprocess.run(
        cmd,
        cwd=self.worktree_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return self._parse_pytest_output(result)
```

### Test path resolution

Test paths should come from the task spec. Options:
1. **Task frontmatter field**: `test_scope: tests/seam/` — explicit, per-task
2. **Convention-based**: Derive from task's target directory (e.g., scaffolding task creating `tests/seam/` → scope to `tests/seam/`)
3. **Hybrid**: Use frontmatter if present, fall back to convention

### Call chain changes

```
state_detection.py:detect_test_results()
  → CoachVerifier._run_tests(test_paths=task.test_scope)  # Pass task context

coach_validator.py:verify_quality_gates()
  → CoachVerifier._run_tests(test_paths=task.test_scope)  # Same scoping for Coach
```

## Files to Modify

1. `guardkit/orchestrator/coach_verification.py` — Add `test_paths` parameter to `_run_tests()` (~line 239)
2. `guardkit/orchestrator/state_detection.py` — Pass task-specific test paths to `detect_test_results()` (~line 320)
3. `guardkit/orchestrator/quality_gates/coach_validator.py` — Pass task-specific test paths through `verify_quality_gates()` (~line 586)
4. `guardkit/orchestrator/autobuild.py` — Extract `test_scope` from task spec, pass to recovery and Coach

## Acceptance Criteria

- [x] `_run_tests()` accepts optional `test_paths` parameter
- [x] When `test_paths` is provided, pytest runs only against specified paths
- [x] When `test_paths` is None, falls back to full-worktree run (backward compatible)
- [x] State recovery (`detect_test_results`) passes task-specific paths when available
- [x] Coach validation (`verify_quality_gates`) reads task-work results (no direct test execution needed)
- [x] Full-worktree run preserved as default for tasks without `test_scope`
- [x] Tests for `_run_tests()` cover both scoped and unscoped execution

## Regression Risk

**Medium** — Changes the `_run_tests()` signature and touches the Coach verification interface. Must ensure:
1. Default behavior (no `test_paths`) remains identical to current behavior
2. Full-worktree tests still run for non-scaffolding tasks that don't specify `test_scope`
3. The `test_paths` parameter propagates correctly through the call chain

## Interaction Notes

- **Must be completed before R4-full (TASK-ASF-006)**: Diagnostic Diagram 5 identified that R4+R5 without ordering could create false approvals. Scoped test detection must be in place before synthetic reports gain promises.
- **Independent of R3 (TASK-ASF-003)**: No interaction — R3 changes feedback text, R5 changes test scope.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 3, Recommendation R5)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 5, R4+R5 interaction)
