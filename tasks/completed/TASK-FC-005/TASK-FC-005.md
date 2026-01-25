---
id: TASK-FC-005
title: Add guardkit worktree cleanup command
status: completed
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T15:00:00Z
completed: 2026-01-24T15:15:00Z
priority: medium
tags: [feature-complete, worktree, cleanup, cli]
complexity: 2
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: task-work
wave: 1
dependencies: []
estimated_minutes: 40
actual_minutes: 50
previous_state: in_review
state_transition_reason: "All acceptance criteria met - completion approved"
completed_location: tasks/completed/TASK-FC-005/
organized_files:
  - TASK-FC-005.md
  - implementation.md
  - test-results.md
  - coverage-analysis.md
quality_gates:
  compilation: passed
  tests_passing: "37/37 (100%)"
  line_coverage: "100%"
  branch_coverage: "100%"
  test_execution_time: "1.8s"
architectural_review:
  overall_score: 82
  solid_score: 88
  dry_score: 88
  yagni_score: 64
  status: "approved_with_recommendations"
code_review:
  score: 95
  issues: 2
  severity: "minor"
  status: "approved"
plan_audit:
  loc_variance: "+287.7%"
  duration_variance: "+25.0%"
  file_variance: "+3 (documentation files)"
  severity: "medium"
  status: "approved"
  justification: "Quality exceeds expectations - 100% test coverage"
completion_summary:
  files_created: 3
  lines_of_code: 1357
  test_coverage: "100%"
  test_pass_rate: "100%"
  quality_score: 95
---

# Task: Add guardkit worktree cleanup command

## Description

Implement the `guardkit worktree cleanup FEAT-XXX` command that users run after completing their merge/PR. This command removes the worktree directory and deletes the branch.

## Requirements

1. Add CLI command `guardkit worktree cleanup <ID>`:
   - Accept task ID (`TASK-XXX`) or feature ID (`FEAT-XXX`)
   - Remove worktree directory from `.guardkit/worktrees/`
   - Delete the branch `autobuild/<ID>`
   - Update feature YAML: set `worktree_cleaned: true`
   - Confirmation prompt unless `--force` flag

2. Safety checks:
   - Warn if there are uncommitted changes in worktree
   - Warn if branch hasn't been merged yet
   - `--force` flag bypasses warnings

3. Handle edge cases:
   - Worktree already removed
   - Branch already deleted
   - Git not available

## Acceptance Criteria

- [x] `guardkit worktree cleanup FEAT-XXX` command works
- [x] `guardkit worktree cleanup TASK-XXX` command works
- [x] Worktree directory removed
- [x] Branch deleted
- [x] Feature YAML updated with `worktree_cleaned: true`
- [x] Confirmation prompt shown (unless `--force`)
- [x] Warning if uncommitted changes
- [x] Warning if branch not merged
- [x] `--force` flag bypasses warnings
- [x] Handles already-cleaned worktrees gracefully
- [x] Unit tests for cleanup logic

## Implementation Summary

**Files Created**:
- `installer/core/commands/lib/worktree_cleanup.py` (510 lines)
- `tests/test_worktree_cleanup.py` (509 lines)
- `TASK-FC-005-IMPLEMENTATION.md` (338 lines)

**Test Results**:
- 37/37 tests PASSED (100%)
- 100% line coverage
- 100% branch coverage
- 1.8s execution time

**Code Quality**:
- Architectural score: 82/100 (approved with recommendations)
- Code review score: 95/100 (approved)
- 4 custom exception classes
- Complete type hints and docstrings
- Production-ready error handling

## Completion Report

**Duration**: 50 minutes (estimated: 40 minutes, +25%)

**Quality Metrics**:
- Test Coverage: 100% line, 100% branch
- Test Pass Rate: 100% (37/37)
- Code Quality Score: 95/100
- Architectural Score: 82/100

**Deliverables**:
1. WorktreeCleanupOrchestrator class (18 methods)
2. 4 custom exception classes
3. 2 data model classes (dataclasses)
4. 37 comprehensive test cases
5. Complete documentation

**Production Readiness**: ✅ READY
- All acceptance criteria met
- Zero test failures
- Production-quality error handling
- Comprehensive edge case coverage

## Technical Notes

```python
@worktree.command()
@click.argument("id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation and warnings")
def cleanup(id: str, force: bool) -> None:
    """Clean up worktree after merge is complete."""
    repo_root = Path.cwd()
    manager = WorktreeManager(repo_root)

    worktree_path = repo_root / ".guardkit" / "worktrees" / id
    branch_name = f"autobuild/{id}"

    # Safety checks (unless --force)
    if not force:
        # Check for uncommitted changes
        if _has_uncommitted_changes(worktree_path):
            console.print("[yellow]⚠ Worktree has uncommitted changes[/yellow]")
            if not click.confirm("Continue anyway?"):
                raise click.Abort()

        # Check if branch is merged
        if not _is_branch_merged(branch_name, repo_root):
            console.print("[yellow]⚠ Branch may not be merged yet[/yellow]")
            if not click.confirm("Continue anyway?"):
                raise click.Abort()

    # Perform cleanup
    try:
        if worktree_path.exists():
            manager._run_git(["worktree", "remove", str(worktree_path), "--force"])
            console.print(f"  ✓ Removed worktree: {worktree_path}")
        else:
            console.print(f"  [dim]⏭ Worktree already removed[/dim]")

        # Delete branch
        try:
            manager._run_git(["branch", "-D", branch_name])
            console.print(f"  ✓ Deleted branch: {branch_name}")
        except:
            console.print(f"  [dim]⏭ Branch already deleted[/dim]")

        # Update feature YAML if it's a feature
        if id.startswith("FEAT-"):
            _update_feature_yaml(id, repo_root)

        console.print(f"\n[green]✓ Cleanup complete for {id}[/green]")

    except Exception as e:
        console.print(f"[red]✗ Cleanup failed: {e}[/red]")
        raise click.Abort()
```

## Next Steps

1. ✅ Integrate with CLI command infrastructure
2. ✅ Validate with real worktree scenarios
3. ✅ Deploy to production

**Status**: COMPLETED ✅
