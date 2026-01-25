---
id: TASK-QG-P2-COACH
title: "Lightweight Coach Validator with task-work Delegation"
status: completed
task_type: implementation
created: 2025-12-29T16:00:00Z
updated: 2025-12-30T17:30:00Z
completed: 2025-12-30T17:30:00Z
priority: high
tags: [quality-gates, autobuild, coach, validation, phase-2, code-reuse]
complexity: 5
estimated_duration: 2-3 days
actual_duration: 1 day
dependencies: [TASK-QG-P1-PRE]
epic: quality-gates-integration
phase: 2
parent_review: TASK-REV-B601
architecture_decision: "Option D - task-work delegation (TASK-REV-0414)"
completion_summary: |
  Successfully implemented lightweight CoachValidator with task-work delegation.
  - Created coach_validator.py with CoachValidator class and dataclasses
  - Updated autobuild-coach.md agent definition
  - Integrated CoachValidator into autobuild.py adversarial loop
  - Created 54 comprehensive unit tests (all passing)
  - Updated quality_gates/__init__.py exports
  - 172 total related tests pass
---

# Task: Lightweight Coach Validator with task-work Delegation

## Overview

Implement a lightweight Coach agent that **validates Player's implementation** by checking that task-work quality gates passed, rather than reimplementing the quality gates inside Coach.

## Architecture Decision

**Option D Selected** (per TASK-REV-0414 review):

The Player agent delegates to `/task-work --implement-only`, which already executes:
- Phase 3: Implementation
- Phase 4: Testing
- Phase 4.5: Test Enforcement Loop
- Phase 5: Code Review
- Phase 5.5: Plan Audit

**Coach's New Role**: Independent validator that:
1. Verifies task-work quality gates passed (reads gate outputs)
2. Runs tests independently (trust but verify)
3. Validates requirements satisfaction
4. Makes approve/feedback decision

**What Coach Does NOT Do**:
- ❌ Reimplement Phase 4.5 (Test Enforcement Loop)
- ❌ Reimplement Phase 5 (Code Review)
- ❌ Reimplement architectural scoring
- ❌ Reimplement coverage measurement

**Why This Approach?**
- ✅ Coach stays lightweight and focused
- ✅ No code duplication between Coach and task-work
- ✅ Single source of truth for quality gate logic
- ✅ Complexity reduced from 8 to 5
- ✅ Duration reduced from 5-7 days to 2-3 days

## Requirements

### Coach Validation Workflow

```
Player Turn:
  └── /task-work TASK-XXX --implement-only
      └── Phases 3, 4, 4.5, 5, 5.5 executed
      └── Results saved to .guardkit/autobuild/TASK-XXX/task_work_results.json

Coach Turn:
  └── Read task-work results
  └── Verify quality gates passed
  └── Run independent test verification (trust but verify)
  └── Validate requirements satisfaction
  └── Decision: approve or feedback
```

### Coach Agent Responsibilities

**1. Read Task-Work Quality Gate Results**

```python
def read_quality_gate_results(self, task_id: str, worktree_path: str) -> dict:
    """Read quality gate results from task-work execution."""
    results_path = Path(worktree_path) / ".guardkit" / "autobuild" / task_id / "task_work_results.json"

    if not results_path.exists():
        return {"error": "Task-work results not found"}

    return json.loads(results_path.read_text())
```

**2. Verify Quality Gates Passed**

```python
def verify_quality_gates(self, task_work_results: dict) -> dict:
    """Verify task-work quality gates passed."""
    return {
        "tests_passed": task_work_results.get("test_results", {}).get("all_passed", False),
        "coverage_met": task_work_results.get("coverage", {}).get("threshold_met", False),
        "arch_review_passed": task_work_results.get("code_review", {}).get("score", 0) >= 60,
        "plan_audit_passed": task_work_results.get("plan_audit", {}).get("violations", 0) == 0,
        "all_gates_passed": all([
            task_work_results.get("test_results", {}).get("all_passed", False),
            task_work_results.get("code_review", {}).get("score", 0) >= 60,
        ])
    }
```

**3. Independent Test Verification (Trust But Verify)**

```python
def run_independent_tests(self, worktree_path: str) -> dict:
    """
    Run tests independently to verify Player's report.

    This is a simple verification - we're checking that tests pass,
    not reimplementing the full test enforcement loop.
    """
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=300
    )

    return {
        "tests_passed": result.returncode == 0,
        "test_output_summary": self._summarize_output(result.stdout),
        "independent_verification": True
    }
```

**4. Validate Requirements Satisfaction**

```python
def validate_requirements(self, task: dict, task_work_results: dict) -> dict:
    """Validate all requirements and acceptance criteria are met."""
    acceptance_criteria = task.get("acceptance_criteria", [])
    requirements_met = task_work_results.get("requirements_met", [])

    return {
        "criteria_total": len(acceptance_criteria),
        "criteria_met": len(requirements_met),
        "all_criteria_met": len(requirements_met) >= len(acceptance_criteria),
        "missing": [c for c in acceptance_criteria if c not in requirements_met]
    }
```

### Coach Decision Logic

```python
class CoachValidator:
    """Lightweight Coach that validates task-work results."""

    def validate(self, task_id: str, worktree_path: str, task: dict) -> dict:
        """
        Validate Player's implementation by checking task-work quality gates.

        Returns:
            dict with decision: "approve" or "feedback"
        """
        # 1. Read task-work results
        task_work_results = self.read_quality_gate_results(task_id, worktree_path)

        if "error" in task_work_results:
            return self._feedback("task-work results not found", severity="must_fix")

        # 2. Verify quality gates passed
        gates = self.verify_quality_gates(task_work_results)

        if not gates["all_gates_passed"]:
            return self._feedback_from_gates(gates)

        # 3. Independent test verification (trust but verify)
        test_verification = self.run_independent_tests(worktree_path)

        if not test_verification["tests_passed"]:
            return self._feedback(
                "Independent test verification failed",
                details=test_verification,
                severity="must_fix"
            )

        # 4. Validate requirements
        requirements = self.validate_requirements(task, task_work_results)

        if not requirements["all_criteria_met"]:
            return self._feedback(
                "Not all acceptance criteria met",
                missing=requirements["missing"],
                severity="must_fix"
            )

        # 5. All gates passed, approve
        return {
            "decision": "approve",
            "task_work_results": task_work_results,
            "independent_verification": test_verification,
            "requirements_validation": requirements,
            "rationale": "All quality gates passed. Independent verification confirmed."
        }

    def _feedback(self, message: str, **kwargs) -> dict:
        """Generate feedback decision."""
        return {
            "decision": "feedback",
            "issues": [{
                "description": message,
                **kwargs
            }]
        }

    def _feedback_from_gates(self, gates: dict) -> dict:
        """Generate feedback from failed quality gates."""
        issues = []

        if not gates["tests_passed"]:
            issues.append({
                "severity": "must_fix",
                "category": "test_failure",
                "description": "Tests did not pass during task-work execution"
            })

        if not gates["arch_review_passed"]:
            issues.append({
                "severity": "must_fix",
                "category": "architectural",
                "description": "Architectural review score below 60"
            })

        if not gates["plan_audit_passed"]:
            issues.append({
                "severity": "should_fix",
                "category": "plan_audit",
                "description": "Plan audit detected violations"
            })

        return {
            "decision": "feedback",
            "issues": issues,
            "gates_status": gates
        }
```

### Integration with Adversarial Loop

**File**: `guardkit/orchestrator/autobuild.py` (MODIFY)

```python
async def adversarial_loop(
    task_id: str,
    worktree_path: str,
    plan: dict,
    max_turns: int,
    options: dict
) -> dict:
    """Execute Player-Coach adversarial loop with task-work delegation."""

    task = load_task(task_id)

    for turn in range(1, max_turns + 1):
        # PLAYER TURN: Delegate to task-work --implement-only
        player_result = await invoke_player(
            task_id=task_id,
            turn=turn,
            worktree_path=worktree_path,
            plan=plan,
            options=options
        )

        # Save player results for Coach
        save_turn_results(task_id, turn, "player", player_result)

        # COACH TURN: Lightweight validation
        coach = CoachValidator()
        coach_result = coach.validate(
            task_id=task_id,
            worktree_path=worktree_path,
            task=task
        )

        # Save coach decision
        save_turn_results(task_id, turn, "coach", coach_result)

        if coach_result["decision"] == "approve":
            return {
                "status": "approved",
                "turns": turn,
                "final_coach_result": coach_result
            }

        # Feedback: Continue to next turn with Coach's feedback
        # (Player will address issues in next turn)

    # Max turns reached without approval
    return {
        "status": "max_turns_reached",
        "turns": max_turns,
        "final_coach_result": coach_result
    }


async def invoke_player(
    task_id: str,
    turn: int,
    worktree_path: str,
    plan: dict,
    options: dict
) -> dict:
    """
    Invoke Player agent.

    Player delegates to task-work --implement-only which handles:
    - Phase 3: Implementation
    - Phase 4: Testing
    - Phase 4.5: Test Enforcement Loop
    - Phase 5: Code Review
    - Phase 5.5: Plan Audit
    """
    from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface

    interface = TaskWorkInterface(worktree_path)

    # Add Coach feedback from previous turn if available
    if turn > 1:
        previous_feedback = load_coach_feedback(task_id, turn - 1)
        options["previous_feedback"] = previous_feedback

    return interface.execute_implement_phase(task_id, options)
```

## Implementation Tasks

### 1. Create Coach Validator Module

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`

```python
"""Lightweight Coach validator for autobuild."""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class CoachValidator:
    """
    Lightweight Coach that validates task-work results.

    Does NOT reimplement quality gates - reads task-work outputs
    and performs independent verification.
    """

    def __init__(self, worktree_path: str):
        self.worktree_path = Path(worktree_path)

    def validate(self, task_id: str, task: dict) -> dict:
        """Main validation entry point."""
        # Implementation as shown above
        pass

    def read_quality_gate_results(self, task_id: str) -> dict:
        """Read quality gate results from task-work execution."""
        pass

    def verify_quality_gates(self, task_work_results: dict) -> dict:
        """Verify task-work quality gates passed."""
        pass

    def run_independent_tests(self) -> dict:
        """Run tests independently to verify Player's report."""
        pass

    def validate_requirements(self, task: dict, task_work_results: dict) -> dict:
        """Validate all requirements and acceptance criteria are met."""
        pass
```

### 2. Update Coach Agent Definition

**File**: `.claude/agents/autobuild-coach.md` (MODIFY)

Update to reflect lightweight validation role:

```markdown
# Coach Agent - Lightweight Validator

## Your Mission
Validate that Player's implementation passed all quality gates.

## What You Validate (Read task-work outputs)
- ✅ Tests passed (from Phase 4.5)
- ✅ Coverage met (from Phase 4.5)
- ✅ Architectural review passed (from Phase 5)
- ✅ Plan audit passed (from Phase 5.5)

## What You Verify Independently
- ✅ Run tests yourself (trust but verify)
- ✅ Check requirements satisfaction
- ✅ Validate acceptance criteria

## What You Do NOT Do
- ❌ Reimplement test enforcement loop
- ❌ Reimplement code review
- ❌ Reimplement architectural scoring
- ❌ Reimplement plan auditing

## Decision Flow
1. Read task-work results from .guardkit/autobuild/TASK-XXX/task_work_results.json
2. Check all quality gates passed
3. Run independent test verification
4. Validate requirements met
5. APPROVE if all checks pass, FEEDBACK if any fail
```

### 3. Update Adversarial Loop

**File**: `guardkit/orchestrator/autobuild.py` (MODIFY)

- Update `adversarial_loop()` to use `CoachValidator`
- Update `invoke_player()` to delegate to task-work

### 4. Create Unit Tests

**File**: `tests/unit/test_coach_validator.py`

```python
"""Tests for lightweight Coach validator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


class TestCoachValidator:
    """Test Coach validation of task-work results."""

    def test_validate_approves_when_all_gates_pass(self):
        """Coach approves when all quality gates passed."""
        with patch.object(CoachValidator, "read_quality_gate_results") as mock_read:
            mock_read.return_value = {
                "test_results": {"all_passed": True},
                "coverage": {"threshold_met": True},
                "code_review": {"score": 85},
                "plan_audit": {"violations": 0},
                "requirements_met": ["req1", "req2"]
            }

            with patch.object(CoachValidator, "run_independent_tests") as mock_tests:
                mock_tests.return_value = {"tests_passed": True}

                coach = CoachValidator("/path/to/worktree")
                result = coach.validate("TASK-001", {"acceptance_criteria": ["req1", "req2"]})

                assert result["decision"] == "approve"

    def test_validate_feedback_when_tests_fail(self):
        """Coach provides feedback when tests failed in task-work."""
        with patch.object(CoachValidator, "read_quality_gate_results") as mock_read:
            mock_read.return_value = {
                "test_results": {"all_passed": False},
                "code_review": {"score": 85},
            }

            coach = CoachValidator("/path/to/worktree")
            result = coach.validate("TASK-001", {})

            assert result["decision"] == "feedback"
            assert any(i["category"] == "test_failure" for i in result["issues"])

    def test_validate_feedback_when_arch_score_low(self):
        """Coach provides feedback when architectural score < 60."""
        with patch.object(CoachValidator, "read_quality_gate_results") as mock_read:
            mock_read.return_value = {
                "test_results": {"all_passed": True},
                "code_review": {"score": 55},
            }

            coach = CoachValidator("/path/to/worktree")
            result = coach.validate("TASK-001", {})

            assert result["decision"] == "feedback"
            assert any(i["category"] == "architectural" for i in result["issues"])

    def test_independent_test_verification(self):
        """Coach runs tests independently to verify."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed")

            coach = CoachValidator("/path/to/worktree")
            result = coach.run_independent_tests()

            assert result["tests_passed"] == True
            assert result["independent_verification"] == True

    def test_independent_test_failure_triggers_feedback(self):
        """Coach provides feedback when independent tests fail."""
        with patch.object(CoachValidator, "read_quality_gate_results") as mock_read:
            mock_read.return_value = {
                "test_results": {"all_passed": True},
                "code_review": {"score": 85},
            }

            with patch.object(CoachValidator, "run_independent_tests") as mock_tests:
                mock_tests.return_value = {"tests_passed": False}

                coach = CoachValidator("/path/to/worktree")
                result = coach.validate("TASK-001", {"acceptance_criteria": []})

                assert result["decision"] == "feedback"
                assert "Independent test verification failed" in result["issues"][0]["description"]

    def test_requirements_validation(self):
        """Coach validates all acceptance criteria met."""
        task = {"acceptance_criteria": ["OAuth2 flow", "Token refresh", "HTTPS"]}
        task_work_results = {"requirements_met": ["OAuth2 flow", "Token refresh"]}

        coach = CoachValidator("/path/to/worktree")
        result = coach.validate_requirements(task, task_work_results)

        assert result["all_criteria_met"] == False
        assert "HTTPS" in result["missing"]
```

## Acceptance Criteria

- [x] `CoachValidator` class reads task-work quality gate results
- [x] Coach verifies all gates passed (tests, coverage, arch review, plan audit)
- [x] Coach runs independent test verification
- [x] Coach validates requirements satisfaction
- [x] Coach agent definition updated to reflect lightweight role
- [x] Adversarial loop uses CoachValidator
- [x] Player delegates to task-work --implement-only
- [x] Unit tests pass (54 tests, 100% pass rate)
- [x] No reimplementation of task-work quality gates

## Files to Create

- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `tests/unit/test_coach_validator.py`

## Files to Modify

- `.claude/agents/autobuild-coach.md` (update to lightweight validator role)
- `guardkit/orchestrator/autobuild.py` (update adversarial loop)
- `guardkit/orchestrator/quality_gates/__init__.py` (export CoachValidator)

## Testing Strategy

1. **Unit Tests**: Test CoachValidator methods
2. **Integration Test**: Full adversarial loop with task-work delegation
3. **Edge Cases**:
   - Task-work results not found
   - Quality gates failed
   - Independent test verification fails
   - Missing acceptance criteria

## Benefits of Lightweight Coach Approach

| Aspect | Original (Reimplementation) | New (Validation) |
|--------|----------------------------|------------------|
| Code to write | ~600 LOC | ~150 LOC |
| Complexity | 8 | 5 |
| Duration | 5-7 days | 2-3 days |
| Code reuse | ~10% | 100% |
| Coach focus | Reimplementing gates | Validating gates |
| Maintenance | Two implementations | Single source |

## Notes

- This is Phase 2 of 3 in the quality gates integration epic
- Coach stays lightweight - it validates, not reimplements
- Independent test verification maintains adversarial rigor
- Player handles all quality gate execution via task-work
- Fresh context per turn preserved (Coach reads results, not history)
