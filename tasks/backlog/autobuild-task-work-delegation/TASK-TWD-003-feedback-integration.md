---
id: TASK-TWD-003
title: Implement Coach feedback integration with task-work
status: backlog
task_type: implementation
created: 2025-12-31T14:00:00Z
priority: high
tags: [autobuild, task-work-delegation, feedback, coach-integration]
complexity: 6
parent_feature: autobuild-task-work-delegation
wave: 2
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave2-1
source_review: TASK-REV-RW01
depends_on: [TASK-TWD-001, TASK-TWD-002]
---

# Task: Implement Coach feedback integration with task-work

## Description

When task-work is invoked for Turn 2+, it needs access to the Coach's feedback from the previous turn. This task implements the mechanism to pass Coach feedback to task-work so the Player (via subagents) can address the issues.

## Current Coach Feedback Flow

```
Turn 1:
  Player implements → Coach reviews → Feedback generated
  Feedback stored in: .guardkit/autobuild/{task_id}/coach_turn_1.json

Turn 2:
  Player receives feedback via prompt → Addresses issues
  Current: Feedback embedded in Player prompt
```

## Problem

When delegating to task-work, we can't embed feedback in a prompt. We need a mechanism for task-work to:
1. Know this is a subsequent turn (not fresh implementation)
2. Access the previous Coach feedback
3. Pass feedback context to the implementation subagent

## Proposed Solution

### Option A: Feedback File Convention

Write feedback to a well-known location that task-work can read:

```python
# guardkit/orchestrator/agent_invoker.py

def _write_coach_feedback(self, task_id: str, feedback: dict) -> Path:
    """Write Coach feedback for task-work to read."""
    feedback_path = (
        self.worktree_path
        / ".guardkit"
        / "autobuild"
        / task_id
        / "coach_feedback.json"
    )
    feedback_path.parent.mkdir(parents=True, exist_ok=True)

    with open(feedback_path, "w") as f:
        json.dump({
            "turn": feedback.get("turn", 1),
            "feedback": feedback.get("feedback", ""),
            "must_fix": feedback.get("must_fix", []),
            "should_fix": feedback.get("should_fix", []),
            "validation_results": feedback.get("validation_results", {}),
        }, f, indent=2)

    return feedback_path
```

### Option B: Task Frontmatter Update

Store feedback summary in task frontmatter:

```yaml
# Task frontmatter after Coach review
---
id: TASK-XXX
status: design_approved
autobuild_feedback:
  turn: 1
  must_fix:
    - "Add error handling for network failures"
    - "Missing test for edge case X"
  should_fix:
    - "Consider extracting helper function"
---
```

### Option C: Command-Line Argument (Recommended)

Add a `--feedback-file` argument to task-work:

```bash
guardkit task-work TASK-XXX --implement-only --mode=tdd \
  --feedback-file=.guardkit/autobuild/TASK-XXX/coach_feedback.json
```

Then task-work can load and inject feedback into the subagent prompt.

## Implementation (Option C)

### 1. Update invoke_player to write feedback

```python
# guardkit/orchestrator/agent_invoker.py

async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    feedback: Optional[str] = None,
    mode: str = "tdd",
) -> AgentInvocationResult:
    """Invoke Player via task-work --implement-only."""
    feedback_path = None

    # Write feedback file if this is a subsequent turn
    if feedback and turn > 1:
        feedback_path = self._write_coach_feedback(task_id, feedback)

    result = await self._invoke_task_work_implement(
        task_id=task_id,
        mode=mode,
        feedback_file=feedback_path,
    )

    return AgentInvocationResult(...)
```

### 2. Update _invoke_task_work_implement

```python
async def _invoke_task_work_implement(
    self,
    task_id: str,
    mode: str,
    feedback_file: Optional[Path] = None,
) -> TaskWorkResult:
    """Execute task-work --implement-only in worktree."""
    args = [task_id, "--implement-only", f"--mode={mode}"]

    if feedback_file:
        args.extend(["--feedback-file", str(feedback_file)])

    proc = await asyncio.create_subprocess_exec(
        "guardkit", "task-work", *args,
        cwd=str(self.worktree_path),
        ...
    )
    ...
```

### 3. Update task-work command to accept --feedback-file

```python
# In task-work command handler

@click.option(
    "--feedback-file",
    type=click.Path(exists=True),
    help="Path to Coach feedback JSON for subsequent turns",
)
def task_work(task_id, ..., feedback_file):
    if feedback_file:
        feedback = load_feedback(feedback_file)
        # Inject into subagent prompt
        context["coach_feedback"] = feedback
```

## Coach Feedback Format

```json
{
  "turn": 1,
  "decision": "feedback",
  "feedback_summary": "Implementation needs error handling and additional tests",
  "must_fix": [
    {
      "issue": "No error handling for network failures",
      "location": "src/api/client.py:45",
      "suggestion": "Add try/except with retry logic"
    },
    {
      "issue": "Missing test for empty response",
      "location": "tests/test_client.py",
      "suggestion": "Add test_empty_response() test case"
    }
  ],
  "should_fix": [
    {
      "issue": "Consider extracting HTTP logic to helper",
      "location": "src/api/client.py:30-60",
      "suggestion": "Create _make_request() helper method"
    }
  ],
  "validation_results": {
    "tests_run": true,
    "tests_passed": false,
    "test_failures": ["test_network_error - AssertionError"],
    "code_quality": "Acceptable"
  }
}
```

## Acceptance Criteria

1. Coach feedback is written to a JSON file after each Coach turn
2. task-work accepts `--feedback-file` argument
3. Feedback is injected into the implementation subagent's context
4. Must-fix items are prioritized in the subagent prompt
5. Turn number is tracked for context
6. Works with resume flow (feedback from previous session)

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` - Write feedback, pass to task-work
- `installer/core/commands/task-work.md` - Add --feedback-file option
- Task-work implementation - Accept and use feedback

## Testing

1. Unit test: Feedback file is written correctly
2. Unit test: Feedback is passed to task-work subprocess
3. Unit test: task-work loads feedback file
4. Integration test: Turn 2 addresses Turn 1 feedback issues

## Notes

- Feedback file should be deleted after successful task completion
- Consider feedback history (keep all turns for audit trail)
- Subagent prompt should clearly separate must-fix from should-fix
