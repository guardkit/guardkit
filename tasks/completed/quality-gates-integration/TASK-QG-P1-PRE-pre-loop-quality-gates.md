---
id: TASK-QG-P1-PRE
title: "Pre-Loop Quality Gates via task-work Delegation"
status: completed
task_type: implementation
created: 2025-12-29T16:00:00Z
updated: 2025-12-30T10:00:00Z
completed: 2025-12-30T16:45:00Z
priority: high
tags: [quality-gates, autobuild, pre-loop, phase-1, code-reuse]
complexity: 4
estimated_duration: 1-2 days
dependencies: []
epic: quality-gates-integration
phase: 1
parent_review: TASK-REV-B601
architecture_decision: "Option D - task-work delegation (TASK-REV-0414)"
---

# Task: Pre-Loop Quality Gates via task-work Delegation

## Overview

Implement pre-loop quality gates by **delegating to `/task-work --design-only`** instead of reimplementing phases. This achieves 100% code reuse of existing task-work quality gates.

## Architecture Decision

**Option D Selected** (per TASK-REV-0414 review):

The pre-loop phase simply delegates to `/task-work --design-only`, which already implements:
- Phase 1.6: Clarifying Questions
- Phase 2: Implementation Planning
- Phase 2.5A: Pattern Suggestions
- Phase 2.5B: Architectural Review
- Phase 2.7: Complexity Evaluation
- Phase 2.8: Human Checkpoint

**Why This Approach?**
- ✅ 100% code reuse (zero reimplementation)
- ✅ Single source of truth for quality gates
- ✅ Automatic benefit from future task-work improvements
- ✅ Complexity reduced from 7 to 4
- ✅ Duration reduced from 3-5 days to 1-2 days

## Requirements

### Pre-Loop Orchestrator

**Purpose**: Thin orchestrator that delegates to task-work for design phases

**Implementation**:
```python
class PreLoopQualityGates:
    """Execute pre-loop quality gates by delegating to task-work --design-only."""

    def __init__(self, worktree_path: str):
        self.worktree_path = worktree_path

    def execute(self, task_id: str, options: dict) -> dict:
        """
        Run pre-loop quality gates via task-work delegation.

        Delegates to: /task-work TASK-XXX --design-only
        Which executes: Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8

        Returns:
            dict with plan, complexity, max_turns, checkpoint_result
        """
        # Build task-work command with delegation flags
        cmd_args = self._build_task_work_args(task_id, options)

        # Execute task-work --design-only in worktree
        result = self._invoke_task_work(cmd_args)

        # Extract outputs needed for adversarial loop
        return self._extract_pre_loop_results(task_id, result)

    def _build_task_work_args(self, task_id: str, options: dict) -> list:
        """Build task-work command arguments."""
        args = [task_id, "--design-only"]

        # Pass through relevant flags
        if options.get("no_questions"):
            args.append("--no-questions")
        if options.get("with_questions"):
            args.append("--with-questions")
        if answers := options.get("answers"):
            args.extend(["--answers", answers])

        return args

    def _invoke_task_work(self, args: list) -> dict:
        """
        Invoke task-work --design-only.

        This can be done via:
        1. Direct Python import of task-work logic (preferred)
        2. Subprocess call to guardkit CLI
        3. Agent invocation via task-manager
        """
        # Option 1: Direct import (preferred - no subprocess overhead)
        from installer.core.commands.lib.task_work_executor import TaskWorkExecutor

        executor = TaskWorkExecutor(cwd=self.worktree_path)
        return executor.execute_design_phase(args)

    def _extract_pre_loop_results(self, task_id: str, result: dict) -> dict:
        """Extract outputs needed for Player-Coach loop."""
        return {
            "plan": result.get("implementation_plan"),
            "plan_path": result.get("plan_path"),
            "complexity": result.get("complexity", {}).get("score", 5),
            "max_turns": self._determine_max_turns(result),
            "checkpoint_passed": result.get("checkpoint_result") == "approved",
            "architectural_score": result.get("architectural_review", {}).get("score"),
            "clarifications": result.get("clarifications", {})
        }

    def _determine_max_turns(self, result: dict) -> int:
        """Determine max_turns based on complexity from task-work."""
        complexity = result.get("complexity", {}).get("score", 5)

        if complexity <= 3:
            return 3  # Simple: quick iterations
        elif complexity <= 6:
            return 5  # Medium: standard iterations
        else:
            return 7  # Complex: more iterations allowed
```

### Integration with AutoBuild Orchestrator

**File**: `guardkit/orchestrator/autobuild.py` (MODIFY)

```python
from .quality_gates.pre_loop import PreLoopQualityGates

async def autobuild_task(task_id: str, options: dict) -> dict:
    """Enhanced AutoBuild with quality gates via task-work delegation."""

    # PHASE 1: SETUP
    task = load_task(task_id)
    worktree_path = create_worktree(task_id, task.get("autobuild", {}).get("base_branch", "main"))

    # PHASE 2: PRE-LOOP QUALITY GATES
    # Delegates to: /task-work --design-only
    pre_loop = PreLoopQualityGates(worktree_path)
    try:
        pre_loop_results = pre_loop.execute(task_id, options)
    except QualityGateBlocked as e:
        return abort_task(task_id, worktree_path, reason=str(e))

    # Validate checkpoint passed (Phase 2.8)
    if not pre_loop_results.get("checkpoint_passed", True):
        return abort_task(task_id, worktree_path, reason="Human checkpoint rejected")

    # PHASE 3: ADVERSARIAL LOOP
    loop_result = await adversarial_loop(
        task_id=task_id,
        worktree_path=worktree_path,
        plan=pre_loop_results["plan"],  # Pass plan to Player
        max_turns=pre_loop_results["max_turns"],  # Dynamic based on complexity
        options=options
    )

    # PHASE 4: FINALIZE
    return finalize_autobuild(task_id, worktree_path, loop_result)
```

## Implementation Tasks

### 1. Create Pre-Loop Module

**File**: `guardkit/orchestrator/quality_gates/__init__.py`

```python
"""Quality gates for feature-build via task-work delegation."""

from .pre_loop import PreLoopQualityGates

__all__ = ["PreLoopQualityGates"]
```

### 2. Implement Pre-Loop Delegator

**File**: `guardkit/orchestrator/quality_gates/pre_loop.py`

- Implement `PreLoopQualityGates` class (see above)
- Handle task-work invocation (direct import preferred)
- Extract and return results needed for loop

### 3. Create Task-Work Interface

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

```python
"""Interface for invoking task-work from feature-build."""

from pathlib import Path
from typing import Optional

class TaskWorkInterface:
    """
    Interface to invoke task-work phases from feature-build.

    Enables feature-build to reuse task-work quality gates
    without reimplementation.
    """

    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path

    def execute_design_phase(self, task_id: str, options: dict) -> dict:
        """
        Execute task-work --design-only phases.

        Returns dict with:
        - implementation_plan: The generated plan
        - complexity: Complexity evaluation results
        - checkpoint_result: Human checkpoint decision
        - architectural_review: SOLID/DRY/YAGNI scores
        """
        # Import task-work executor
        from installer.core.commands.lib.task_work_executor import TaskWorkExecutor

        executor = TaskWorkExecutor(
            cwd=str(self.worktree_path),
            design_only=True
        )

        return executor.execute(task_id, options)

    def execute_implement_phase(self, task_id: str, options: dict) -> dict:
        """
        Execute task-work --implement-only phases.

        Returns dict with:
        - implementation_result: Success/failure
        - test_results: Test execution results
        - code_review: Code review results
        - plan_audit: Plan audit results
        """
        from installer.core.commands.lib.task_work_executor import TaskWorkExecutor

        executor = TaskWorkExecutor(
            cwd=str(self.worktree_path),
            implement_only=True
        )

        return executor.execute(task_id, options)
```

### 4. Update AutoBuild Orchestrator

**File**: `guardkit/orchestrator/autobuild.py` (MODIFY)

- Import `PreLoopQualityGates`
- Add pre-loop execution before adversarial loop
- Pass plan and max_turns to loop

### 5. Create Unit Tests

**File**: `tests/unit/test_pre_loop_delegation.py`

```python
"""Tests for pre-loop quality gates via task-work delegation."""

import pytest
from unittest.mock import Mock, patch
from guardkit.orchestrator.quality_gates.pre_loop import PreLoopQualityGates


class TestPreLoopQualityGates:
    """Test pre-loop delegation to task-work --design-only."""

    def test_execute_delegates_to_task_work(self):
        """Pre-loop delegates to task-work --design-only."""
        with patch("guardkit.orchestrator.quality_gates.pre_loop.TaskWorkInterface") as mock:
            mock.return_value.execute_design_phase.return_value = {
                "implementation_plan": {"approach": "Test"},
                "complexity": {"score": 5},
                "checkpoint_result": "approved"
            }

            gates = PreLoopQualityGates("/path/to/worktree")
            result = gates.execute("TASK-001", {})

            mock.return_value.execute_design_phase.assert_called_once()
            assert result["plan"]["approach"] == "Test"

    def test_passes_no_questions_flag(self):
        """--no-questions flag passed through to task-work."""
        with patch("guardkit.orchestrator.quality_gates.pre_loop.TaskWorkInterface") as mock:
            mock.return_value.execute_design_phase.return_value = {}

            gates = PreLoopQualityGates("/path/to/worktree")
            gates.execute("TASK-001", {"no_questions": True})

            call_args = mock.return_value.execute_design_phase.call_args
            assert call_args[1].get("no_questions") == True

    def test_determines_max_turns_from_complexity(self):
        """max_turns determined based on complexity score."""
        with patch("guardkit.orchestrator.quality_gates.pre_loop.TaskWorkInterface") as mock:
            # Test simple complexity (1-3)
            mock.return_value.execute_design_phase.return_value = {
                "complexity": {"score": 2}
            }
            gates = PreLoopQualityGates("/path/to/worktree")
            result = gates.execute("TASK-001", {})
            assert result["max_turns"] == 3

            # Test medium complexity (4-6)
            mock.return_value.execute_design_phase.return_value = {
                "complexity": {"score": 5}
            }
            result = gates.execute("TASK-002", {})
            assert result["max_turns"] == 5

            # Test complex (7+)
            mock.return_value.execute_design_phase.return_value = {
                "complexity": {"score": 8}
            }
            result = gates.execute("TASK-003", {})
            assert result["max_turns"] == 7

    def test_checkpoint_rejection_blocks_loop(self):
        """Pre-loop blocks if human checkpoint rejected."""
        with patch("guardkit.orchestrator.quality_gates.pre_loop.TaskWorkInterface") as mock:
            mock.return_value.execute_design_phase.return_value = {
                "checkpoint_result": "rejected"
            }

            gates = PreLoopQualityGates("/path/to/worktree")
            result = gates.execute("TASK-001", {})

            assert result["checkpoint_passed"] == False

    def test_extracts_plan_for_player(self):
        """Pre-loop extracts plan to pass to Player agent."""
        plan = {
            "approach": "Implement feature X",
            "files_to_create": ["src/feature.py"],
            "estimated_loc": 200
        }

        with patch("guardkit.orchestrator.quality_gates.pre_loop.TaskWorkInterface") as mock:
            mock.return_value.execute_design_phase.return_value = {
                "implementation_plan": plan,
                "plan_path": ".claude/task-plans/TASK-001.md"
            }

            gates = PreLoopQualityGates("/path/to/worktree")
            result = gates.execute("TASK-001", {})

            assert result["plan"] == plan
            assert result["plan_path"] == ".claude/task-plans/TASK-001.md"
```

## Acceptance Criteria

- [x] `PreLoopQualityGates` class delegates to task-work --design-only
- [x] All task-work flags passed through (--no-questions, --answers, etc.)
- [x] Plan extracted and available for Player agent
- [x] max_turns determined from complexity score
- [x] Checkpoint rejection blocks adversarial loop
- [x] Integration with autobuild.py complete
- [x] Unit tests pass (51 tests, all passing)
- [x] No reimplementation of task-work phases

## Files to Create

- `guardkit/orchestrator/quality_gates/__init__.py`
- `guardkit/orchestrator/quality_gates/pre_loop.py`
- `guardkit/orchestrator/quality_gates/task_work_interface.py`
- `tests/unit/test_pre_loop_delegation.py`

## Files to Modify

- `guardkit/orchestrator/autobuild.py` (integrate pre-loop gates)

## Testing Strategy

1. **Unit Tests**: Mock task-work interface, verify delegation
2. **Integration Test**: End-to-end pre-loop with real task-work
3. **Edge Cases**:
   - Task-work fails at Phase 2.8 (checkpoint rejection)
   - Low complexity (max_turns=3)
   - High complexity (max_turns=7)
   - Flags passed through correctly

## Dependencies

- Task-work executor module (existing)
- No agent reimplementation required
- No MCP direct integration (task-work handles it)

## Benefits of Delegation Approach

| Aspect | Original (Reimplementation) | New (Delegation) |
|--------|----------------------------|------------------|
| Code to write | ~500 LOC | ~100 LOC |
| Complexity | 7 | 4 |
| Duration | 3-5 days | 1-2 days |
| Code reuse | ~20% | 100% |
| Maintenance | Two implementations | Single source |
| Future improvements | Manual sync | Automatic |

## Notes

- This is Phase 1 of 3 in the quality gates integration epic (reduced from 4)
- Delegation approach approved per TASK-REV-0414 architectural review
- Player receives the implementation plan as its "contract"
- Coach validates against the same plan (consistency guaranteed)
