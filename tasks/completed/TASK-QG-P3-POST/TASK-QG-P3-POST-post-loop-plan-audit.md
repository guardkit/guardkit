---
id: TASK-QG-P3-POST
title: "Post-Loop Finalization (Minimal - task-work handles Phase 5.5)"
status: completed
task_type: implementation
created: 2025-12-29T16:00:00Z
updated: 2025-12-30T11:15:00Z
completed: 2025-12-30T11:15:00Z
priority: medium
tags: [quality-gates, autobuild, post-loop, finalization, phase-3, code-reuse]
complexity: 2
estimated_duration: 0.5-1 day
actual_duration: 0.5 day
dependencies: [TASK-QG-P1-PRE, TASK-QG-P2-COACH]
epic: quality-gates-integration
phase: 3
parent_review: TASK-REV-B601
architecture_decision: "Option D - task-work delegation (TASK-REV-0414)"
---

# Task: Post-Loop Finalization (Minimal)

## Overview

Implement minimal post-loop finalization. **Phase 5.5 (Plan Audit) is NOT needed** here because it's already executed by task-work during each Player turn.

## Architecture Decision

**Option D Selected** (per TASK-REV-0414 review):

The Player agent delegates to `/task-work --implement-only`, which already executes:
- Phase 3: Implementation
- Phase 4: Testing
- Phase 4.5: Test Enforcement Loop
- Phase 5: Code Review
- **Phase 5.5: Plan Audit** ← Already done!

**What This Means**:
- ❌ We do NOT need to reimplement plan audit
- ❌ We do NOT need `PostLoopQualityGates` class
- ✅ Post-loop is now just finalization (preserve worktree, update status)

**Why This Approach?**
- ✅ Zero code duplication
- ✅ Existing `PlanAuditor` class in task-work handles everything
- ✅ Complexity reduced from 5 to 2
- ✅ Duration reduced from 2-3 days to 0.5-1 day

## What Actually Needs to Happen Post-Loop

After Coach approves (which means task-work quality gates passed + independent verification), we just need:

1. **Preserve Worktree**: Keep for human review (never auto-merge)
2. **Update Task Status**: Mark as ready for human review
3. **Generate Summary**: Show what was accomplished

That's it. No additional quality gates.

## Requirements

### Post-Loop Finalization

```python
def finalize_autobuild(
    task_id: str,
    worktree_path: str,
    loop_result: dict
) -> dict:
    """
    Finalize autobuild after Coach approval.

    This is minimal - task-work already handled all quality gates.
    """
    # 1. Preserve worktree (never auto-delete or auto-merge)
    # Worktree is already created and preserved by design

    # 2. Update task status
    update_task_status(task_id, status="READY_FOR_REVIEW")

    # 3. Generate summary for human
    summary = generate_summary(task_id, worktree_path, loop_result)

    # 4. Save final state
    save_autobuild_state(task_id, {
        "status": "approved",
        "worktree_path": worktree_path,
        "turns_taken": loop_result["turns"],
        "summary": summary
    })

    return {
        "status": "approved",
        "worktree": worktree_path,
        "next_steps": [
            f"Review changes: cd {worktree_path} && git diff main",
            f"Merge if approved: git checkout main && git merge autobuild/{task_id}",
            f"Complete task: /task-complete {task_id}"
        ],
        "summary": summary
    }


def generate_summary(task_id: str, worktree_path: str, loop_result: dict) -> dict:
    """Generate summary of what was accomplished."""
    # Read the final task-work results from Player's last turn
    results_path = Path(worktree_path) / ".guardkit" / "autobuild" / task_id / "task_work_results.json"

    if results_path.exists():
        task_work_results = json.loads(results_path.read_text())
    else:
        task_work_results = {}

    return {
        "turns_taken": loop_result["turns"],
        "files_created": task_work_results.get("files_created", []),
        "files_modified": task_work_results.get("files_modified", []),
        "tests_passed": task_work_results.get("test_results", {}).get("all_passed", False),
        "test_count": task_work_results.get("test_results", {}).get("count", 0),
        "coverage": task_work_results.get("coverage", {}),
        "architectural_score": task_work_results.get("code_review", {}).get("score", 0),
        "plan_audit": task_work_results.get("plan_audit", {})  # Already done by task-work!
    }
```

### Integration with AutoBuild Orchestrator

**File**: `guardkit/orchestrator/autobuild.py` (MODIFY)

```python
async def autobuild_task(task_id: str, options: dict) -> dict:
    """AutoBuild with task-work delegation."""

    # PHASE 1: SETUP
    task = load_task(task_id)
    worktree_path = create_worktree(task_id, task.get("autobuild", {}).get("base_branch", "main"))

    # PHASE 2: PRE-LOOP QUALITY GATES
    pre_loop = PreLoopQualityGates(worktree_path)
    pre_loop_results = pre_loop.execute(task_id, options)

    # PHASE 3: ADVERSARIAL LOOP
    loop_result = await adversarial_loop(
        task_id=task_id,
        worktree_path=worktree_path,
        plan=pre_loop_results["plan"],
        max_turns=pre_loop_results["max_turns"],
        options=options
    )

    # PHASE 4: FINALIZE (minimal - just cleanup and status)
    if loop_result["status"] == "approved":
        return finalize_autobuild(task_id, worktree_path, loop_result)
    else:
        return handle_max_turns_reached(task_id, worktree_path, loop_result)
```

## Implementation Tasks

### 1. Add Finalization Functions

**File**: `guardkit/orchestrator/autobuild.py` (MODIFY)

Add `finalize_autobuild()` and `generate_summary()` functions.

### 2. Remove Redundant Post-Loop Module

If `guardkit/orchestrator/quality_gates/post_loop.py` exists from earlier planning, **delete it** or repurpose as just the finalization helper.

### 3. Create Unit Tests

**File**: `tests/unit/test_autobuild_finalization.py`

```python
"""Tests for autobuild finalization."""

import pytest
from unittest.mock import Mock, patch
from guardkit.orchestrator.autobuild import finalize_autobuild, generate_summary


class TestAutobuildFinalization:
    """Test minimal post-loop finalization."""

    def test_finalize_preserves_worktree(self):
        """Finalization preserves worktree for human review."""
        result = finalize_autobuild("TASK-001", "/path/to/worktree", {"turns": 2, "status": "approved"})

        assert result["worktree"] == "/path/to/worktree"
        assert "Review changes" in result["next_steps"][0]

    def test_finalize_updates_status(self):
        """Finalization updates task status."""
        with patch("guardkit.orchestrator.autobuild.update_task_status") as mock:
            finalize_autobuild("TASK-001", "/path", {"turns": 1, "status": "approved"})
            mock.assert_called_with("TASK-001", status="READY_FOR_REVIEW")

    def test_generate_summary_includes_task_work_results(self):
        """Summary includes results from task-work execution."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value='{"test_results": {"all_passed": true, "count": 10}}'):
                summary = generate_summary("TASK-001", "/path", {"turns": 2})

                assert summary["tests_passed"] == True
                assert summary["test_count"] == 10

    def test_generate_summary_includes_plan_audit(self):
        """Summary includes plan audit from task-work (already done!)."""
        task_work_results = {
            "plan_audit": {
                "file_variance": 0.1,
                "scope_creep_detected": False
            }
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=json.dumps(task_work_results)):
                summary = generate_summary("TASK-001", "/path", {"turns": 2})

                assert "plan_audit" in summary
                assert summary["plan_audit"]["scope_creep_detected"] == False
```

## Acceptance Criteria

- [x] `finalize_autobuild()` function preserves worktree
- [x] Task status updated to READY_FOR_REVIEW (mapped as `in_review`)
- [x] Summary generated from task-work results
- [x] Next steps provided for human review
- [x] No reimplementation of plan audit
- [x] Unit tests pass (16/16 tests passing)
- [x] Integration with autobuild orchestrator complete (exported in `__all__`)

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (add finalization functions)

## Files to Create

- `tests/unit/test_autobuild_finalization.py`

## Files to Delete (if they exist)

- `guardkit/orchestrator/quality_gates/post_loop.py` (redundant - task-work handles Phase 5.5)

## Testing Strategy

1. **Unit Tests**: Test finalization functions
2. **Integration Test**: Full autobuild with finalization
3. **Edge Cases**:
   - Task-work results file missing
   - Max turns reached (not approved)

## Benefits of Minimal Approach

| Aspect | Original (Reimplementation) | New (Minimal) |
|--------|----------------------------|---------------|
| Code to write | ~300 LOC | ~50 LOC |
| Complexity | 5 | 2 |
| Duration | 2-3 days | 0.5-1 day |
| Plan audit | Reimplemented | Reused from task-work |
| Post-loop class | Full PostLoopQualityGates | None needed |

## Why Plan Audit is Already Done

The existing flow:

```
Player Turn:
  └── /task-work --implement-only
      └── Phase 3: Implementation
      └── Phase 4: Testing
      └── Phase 4.5: Test Enforcement
      └── Phase 5: Code Review
      └── Phase 5.5: Plan Audit ← ALREADY DONE HERE!
      └── Results saved to task_work_results.json

Coach Turn:
  └── Read task_work_results.json
  └── Verify plan_audit passed
  └── Approve if all gates passed

Post-Loop:
  └── Just finalize (preserve worktree, update status)
  └── NO additional plan audit needed!
```

## Notes

- This is Phase 3 of 3 in the quality gates integration epic
- Post-loop is now minimal (just finalization)
- Plan audit already runs during each Player turn via task-work
- Coach validates that plan audit passed (reads results)
- No duplication of `PlanAuditor` class
- Human review happens after worktree is preserved
