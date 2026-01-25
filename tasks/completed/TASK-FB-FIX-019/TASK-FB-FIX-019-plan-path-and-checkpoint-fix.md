---
id: TASK-FB-FIX-019
title: Fix plan path extraction and add auto-approve checkpoint for SDK mode
status: completed
created: 2026-01-14T16:00:00Z
updated: 2026-01-14T18:30:00Z
completed: 2026-01-14T18:30:00Z
priority: critical
tags: [feature-build, sdk, regex, checkpoint, autobuild]
parent_task: TASK-REV-FB12
complexity: 5
estimated_effort: 2-3 hours
---

# Task: Fix Plan Path Extraction and Add Auto-Approve Checkpoint for SDK Mode

## Problem Statement

The `/feature-build` command fails with `QualityGateBlocked("Design phase did not return plan path")` due to two issues:

1. **Regex Pattern Mismatch**: The SDK output parser doesn't recognize task-work's actual output format ("Created implementation plan:")
2. **Checkpoint Blocking**: When security keywords are detected, Phase 2.8 forces a human checkpoint that blocks SDK execution

## Root Cause

From TASK-REV-FB12 review analysis:

1. Task-work outputs: `Created implementation plan: .claude/task-plans/TASK-XXX-implementation-plan.md`
2. Parser looks for: `Plan saved to:` or `Implementation plan saved:`
3. No match → plan_path = None → QualityGateBlocked

Additionally, security-related tasks trigger FULL_REQUIRED checkpoint which blocks until human responds - impossible in SDK autonomous mode.

## Acceptance Criteria

- [ ] SDK extracts plan path from "Created implementation plan:" output format
- [ ] New `--auto-approve-checkpoint` flag added to task-work command
- [ ] SDK orchestrator passes `--auto-approve-checkpoint` when invoking task-work
- [ ] Auto-approval is logged with timestamp and task context for audit trail
- [ ] All existing tests pass
- [ ] New tests cover regex pattern and auto-approve scenarios

## Implementation Plan

### Part 1: Add Missing Regex Pattern (Priority 1)

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

Add the pattern to `_parse_sdk_output()`:

```python
plan_path_patterns = [
    r"Plan saved to[:\s]+([^\s\n]+)",
    r"Plan saved[:\s]+to[:\s]+([^\s\n]+)",
    r"Implementation plan saved[:\s]+to[:\s]+([^\s\n]+)",
    r"Implementation plan saved[:\s]+([^\s\n]+)",
    r"Created implementation plan[:\s]+([^\s\n]+)",  # ADD THIS
    r"plan_path[:\s]+[\"']?([^\s\n\"']+)",
    r"(docs/state/[A-Z0-9-]+/implementation_plan\.(?:md|json))",
    r"(\.claude/task-plans/[A-Z0-9-]+-implementation-plan\.(?:md|json))",
]
```

### Part 2: Add --auto-approve-checkpoint Flag (Priority 2)

**File**: `installer/core/commands/task-work.md`

Add to Available Flags section:

```markdown
| `--auto-approve-checkpoint` | Skip Phase 2.8 interactive prompt, auto-approve |
```

Add flag specification:

```markdown
### Flag: --auto-approve-checkpoint

**Purpose**: Automatically approve Phase 2.8 checkpoint without interactive prompt.

**Use cases**:
- SDK/autonomous execution where no human is present
- CI/CD pipelines requiring non-interactive execution
- Batch processing of multiple tasks

**Behavior**:
1. Phase 2.8 checkpoint is displayed (plan summary shown)
2. Instead of waiting for [A]pprove/[M]odify/[C]ancel input
3. Automatically approves with logged audit trail
4. Continues to Phase 3 (or exits with design_approved if --design-only)

**Logging Output**:
```
============================================================
AUTO-APPROVED: --auto-approve-checkpoint flag enabled
   Task: TASK-XXX
   Complexity: 7/10
   Timestamp: 2026-01-14T15:30:00Z
============================================================
```
```

**File**: `installer/core/commands/lib/checkpoint_display.py`

Update `display_phase28_checkpoint()` function:

```python
def display_phase28_checkpoint(
    task_id: str,
    complexity_score: int,
    plan_path: Optional[Path] = None,
    auto_approve: bool = False  # NEW PARAMETER
) -> str:
    """Display Phase 2.8 checkpoint with optional auto-approval."""
    # ... existing display code ...

    if auto_approve:
        from datetime import datetime
        logger.info(f"Auto-approving checkpoint for {task_id}")
        print("\n" + "=" * 60)
        print("AUTO-APPROVED: --auto-approve-checkpoint flag enabled")
        print(f"   Task: {task_id}")
        print(f"   Complexity: {complexity_score}/10")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        print("=" * 60 + "\n")
        return "approved"

    # ... existing interactive prompt code ...
```

### Part 3: SDK Orchestrator Passes Flag (Priority 3)

**File**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

Update prompt building to include auto-approve:

```python
def _build_design_prompt(self, task_id: str, options: Dict[str, Any]) -> str:
    parts = [f"/task-work {task_id} --design-only"]

    # SDK mode: Always auto-approve checkpoints
    parts.append("--auto-approve-checkpoint")

    # Existing flags...
    if options.get("no_questions"):
        parts.append("--no-questions")

    return " ".join(parts)
```

## Testing

### Unit Tests

```python
# tests/unit/test_task_work_interface.py

def test_parse_sdk_output_created_implementation_plan():
    """Test parsing 'Created implementation plan:' format."""
    interface = TaskWorkInterface(worktree_path=Path("/tmp/test"))

    output = """
    Phase 2: Implementation Planning
    Created implementation plan: .claude/task-plans/TASK-WKT-b2c4-implementation-plan.md
    Phase 2.5A: Pattern Suggestions
    """

    result = interface._parse_sdk_output(output)

    assert result["plan_path"] == ".claude/task-plans/TASK-WKT-b2c4-implementation-plan.md"


def test_auto_approve_checkpoint_flag_in_prompt():
    """Test that SDK includes --auto-approve-checkpoint flag."""
    interface = TaskWorkInterface(worktree_path=Path("/tmp/test"))

    prompt = interface._build_design_prompt("TASK-XXX", {})

    assert "--auto-approve-checkpoint" in prompt
    assert "--design-only" in prompt
```

### Integration Tests

```python
# tests/integration/test_checkpoint_auto_approve.py

def test_checkpoint_auto_approve_logs_decision():
    """Test that auto-approve logs audit trail."""
    from installer.core.commands.lib.checkpoint_display import display_phase28_checkpoint
    import io
    import sys

    # Capture stdout
    captured = io.StringIO()
    sys.stdout = captured

    result = display_phase28_checkpoint(
        task_id="TASK-TEST-001",
        complexity_score=7,
        auto_approve=True
    )

    sys.stdout = sys.__stdout__
    output = captured.getvalue()

    assert result == "approved"
    assert "AUTO-APPROVED" in output
    assert "TASK-TEST-001" in output
    assert "7/10" in output
```

## Files to Modify

1. `guardkit/orchestrator/quality_gates/task_work_interface.py`
   - Add regex pattern (Part 1)
   - Add --auto-approve-checkpoint to prompt (Part 3)

2. `installer/core/commands/task-work.md`
   - Add flag documentation (Part 2)

3. `installer/core/commands/lib/checkpoint_display.py`
   - Add auto_approve parameter (Part 2)

4. `tests/unit/test_task_work_interface.py`
   - Add regex pattern test
   - Add prompt flag test

5. `tests/integration/test_checkpoint_auto_approve.py`
   - Add integration test for auto-approve

## Verification

After implementation:

```bash
# Test 1: Regex pattern
/task-work TASK-XXX --design-only
# Should see plan path extracted

# Test 2: Auto-approve flag
/task-work TASK-XXX --design-only --auto-approve-checkpoint
# Should see AUTO-APPROVED log, no interactive prompt

# Test 3: Full feature-build
guardkit autobuild task TASK-XXX --verbose
# Should complete without checkpoint blocking
```

## Notes

- This fix is critical for `/feature-build` to work with security-related tasks
- The auto-approve flag maintains audit trail for compliance
- Human can still use manual `/task-work` without flag for interactive checkpoints
- See `.claude/reviews/TASK-REV-FB12-review-report.md` for full analysis
