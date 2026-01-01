---
id: TASK-TWD-007
title: Implement Escape Hatch Pattern for blocked task reports
status: backlog
task_type: implementation
created: 2025-12-31T14:30:00Z
priority: high
tags: [autobuild, escape-hatch, debugging, user-experience]
complexity: 3
parent_feature: autobuild-task-work-delegation
wave: 4
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave4-1
source_review: TASK-REV-RW01
---

# Task: Implement Escape Hatch Pattern for blocked task reports

## Description

When AutoBuild approaches the maximum turn limit without successful completion, the Player should generate a structured "blocked task report" that provides actionable debugging information instead of just preserving the worktree with a generic "Human intervention required" message.

This pattern is inspired by the Ralph Wiggum plugin's escape hatch mechanism.

## Current Behavior

When `max_turns` is exceeded:
- Worktree is preserved for inspection
- Generic message: "Human intervention required"
- No structured information about what was tried or what's blocking

## Target Behavior

When `turn >= max_turns - 2`:
- Player generates a structured `blocked_report` section
- Documents blocking issues with specific details
- Lists all attempts made across turns
- Suggests alternative approaches

## Implementation

### 1. Extend Player Report Schema

```python
# guardkit/orchestrator/schemas.py (or wherever report schemas live)

@dataclass
class BlockedReport:
    """Structured report for blocked tasks."""
    blocking_issues: List[BlockingIssue]
    attempts_made: List[AttemptRecord]
    suggested_alternatives: List[str]
    human_action_required: str  # Specific action needed


@dataclass
class BlockingIssue:
    """A specific issue preventing completion."""
    issue: str
    location: Optional[str]  # File/line if applicable
    category: str  # "external_dependency", "test_failure", "architectural", "unclear_requirement"
    details: str


@dataclass
class AttemptRecord:
    """Record of an attempt to resolve an issue."""
    turn: int
    action: str
    result: str
    why_failed: Optional[str]
```

### 2. Update Player Agent Prompt

Add to `.claude/agents/autobuild-player.md`:

```markdown
## Escape Hatch: Blocked Task Reporting

If you reach turn >= (max_turns - 2) and cannot complete the task, you MUST
generate a `blocked_report` section in your JSON report with:

### blocking_issues (REQUIRED)
List each issue preventing completion:
```json
{
  "blocking_issues": [
    {
      "issue": "Cannot mock external payment API",
      "location": "src/payments/stripe_client.py:45",
      "category": "external_dependency",
      "details": "Stripe API requires real credentials for webhook testing"
    }
  ]
}
```

### attempts_made (REQUIRED)
Document what you tried on each turn:
```json
{
  "attempts_made": [
    {"turn": 1, "action": "Used httpretty to mock HTTP calls", "result": "Failed", "why_failed": "Stripe SDK bypasses standard HTTP"},
    {"turn": 2, "action": "Created mock Stripe client class", "result": "Partial", "why_failed": "Webhook signatures cannot be mocked"},
    {"turn": 3, "action": "Attempted VCR-style recording", "result": "Failed", "why_failed": "No real credentials available"}
  ]
}
```

### suggested_alternatives (REQUIRED)
Propose ways to proceed:
```json
{
  "suggested_alternatives": [
    "Use Stripe test mode with real test API keys",
    "Split task: implement without webhooks first",
    "Create integration test that runs against Stripe sandbox"
  ]
}
```

### human_action_required (REQUIRED)
Specify exactly what the human needs to do:
```json
{
  "human_action_required": "Provide Stripe test API keys in .env file, or approve splitting this task into non-webhook and webhook phases"
}
```
```

### 3. Update Orchestrator to Handle Blocked Reports

```python
# guardkit/orchestrator/autobuild.py

def _handle_max_turns_exceeded(self, result: OrchestrationResult) -> None:
    """Handle max turns exceeded with blocked report if available."""
    last_player_report = self._get_last_player_report()

    if blocked_report := last_player_report.get("blocked_report"):
        self._display_blocked_report(blocked_report)
    else:
        # Fallback to generic message
        console.print("[yellow]Max turns exceeded. Human intervention required.[/yellow]")


def _display_blocked_report(self, report: dict) -> None:
    """Display structured blocked task report."""
    console.print(Panel(
        "[bold red]Task Blocked - Structured Report[/bold red]",
        border_style="red"
    ))

    # Blocking Issues
    console.print("\n[bold]Blocking Issues:[/bold]")
    for issue in report.get("blocking_issues", []):
        console.print(f"  • [{issue['category']}] {issue['issue']}")
        if issue.get("location"):
            console.print(f"    Location: {issue['location']}")
        console.print(f"    Details: {issue['details']}")

    # Attempts Made
    console.print("\n[bold]Attempts Made:[/bold]")
    for attempt in report.get("attempts_made", []):
        status = "✓" if attempt["result"] == "Success" else "✗"
        console.print(f"  Turn {attempt['turn']}: {status} {attempt['action']}")
        if attempt.get("why_failed"):
            console.print(f"    → {attempt['why_failed']}")

    # Suggested Alternatives
    console.print("\n[bold]Suggested Alternatives:[/bold]")
    for alt in report.get("suggested_alternatives", []):
        console.print(f"  • {alt}")

    # Human Action Required
    console.print(f"\n[bold yellow]Human Action Required:[/bold yellow]")
    console.print(f"  {report.get('human_action_required', 'Review worktree and determine next steps')}")
```

### 4. Update invoke_player to Pass Turn Context

```python
# guardkit/orchestrator/agent_invoker.py

async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    feedback: Optional[str] = None,
    mode: str = "tdd",
    max_turns: int = 5,  # NEW: Pass max_turns for escape hatch detection
) -> AgentInvocationResult:
    """Invoke Player via task-work --implement-only."""

    # Calculate if approaching max turns
    approaching_limit = turn >= (max_turns - 2)

    # Write context for task-work to read
    self._write_turn_context(task_id, turn, max_turns, approaching_limit)

    # ... rest of implementation
```

## Example Blocked Report Output

```
╭─────────────────────────────────────────────────────────────────╮
│              Task Blocked - Structured Report                    │
╰─────────────────────────────────────────────────────────────────╯

Blocking Issues:
  • [external_dependency] Cannot mock Stripe webhook signatures
    Location: src/payments/webhook_handler.py:78
    Details: Stripe signs webhooks with secret key, cannot mock without real key

  • [test_failure] Integration test requires live API
    Location: tests/integration/test_payments.py:45
    Details: VCR cassettes cannot capture webhook events

Attempts Made:
  Turn 1: ✗ Used httpretty to mock HTTP calls
    → Stripe SDK bypasses standard HTTP library
  Turn 2: ✗ Created mock Stripe client class
    → Webhook signature verification still fails
  Turn 3: ✗ Attempted to disable signature verification
    → Security risk, not acceptable for production code

Suggested Alternatives:
  • Use Stripe test mode with real test API keys (recommended)
  • Split task: implement payment flow without webhooks first
  • Create separate task for webhook testing with sandbox environment

Human Action Required:
  Provide Stripe test API keys in .env.test file, OR approve splitting
  this task into "payment-flow" (completable) and "webhook-handling"
  (requires keys) subtasks.
```

## Acceptance Criteria

1. Player generates `blocked_report` when turn >= max_turns - 2
2. Report includes all four required sections
3. Orchestrator displays formatted blocked report
4. Report is saved to `.guardkit/autobuild/{task_id}/blocked_report.json`
5. Generic fallback still works if Player doesn't generate report
6. Categories are validated against known list

## Files to Modify

- `.claude/agents/autobuild-player.md` - Add escape hatch instructions
- `guardkit/orchestrator/autobuild.py` - Handle and display blocked reports
- `guardkit/orchestrator/agent_invoker.py` - Pass turn/max_turns context
- `guardkit/orchestrator/schemas.py` - Add BlockedReport dataclass (if using)

## Testing

1. Unit test: Blocked report schema validation
2. Unit test: Display formatting
3. Integration test: Player generates report when approaching limit
4. Integration test: Fallback to generic message when no report

## Notes

- Keep blocked report concise - it's for debugging, not documentation
- Categories help humans quickly understand the type of blocker
- The `human_action_required` should be specific and actionable
- Consider adding blocked report to worktree README for easy discovery
