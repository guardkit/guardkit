# Turn State Tracking Guide

Track progress across autonomous `/feature-build` turns with persistent state capture for cross-turn learning.

## Overview

In autonomous workflows, Claude executes multiple Player-Coach turns to implement a task. Each turn represents an implementation attempt followed by validation. **The problem**: each turn starts fresh with no memory of previous attempts.

Turn state tracking solves this by capturing what happened at the end of each turn and making it available to subsequent turns:

```
Turn 1: Player implements → Coach rejects (missing validation)
        ↓ [State captured: blockers, feedback, what to try]
Turn 2: Player sees Turn 1 feedback → implements validation → Coach approves
```

**Without turn state tracking**: Turn 2 might repeat Turn 1's mistakes.
**With turn state tracking**: Turn 2 knows exactly what Turn 1 learned.

**Key Benefits:**

| Benefit | Description |
|---------|-------------|
| **Cross-Turn Learning** | Turn N+1 knows what Turn N attempted and learned |
| **Prevents Repeated Mistakes** | Coach feedback from Turn N is emphasized in Turn N+1 |
| **Progress Tracking** | Acceptance criteria status persists across turns |
| **Audit Trail** | Complete history of implementation attempts |
| **Debugging** | Understand why a task took multiple turns |

---

## What Gets Captured

At the end of each `/feature-build` turn, the following is captured:

### Player Actions

- **Player summary**: What was implemented or attempted this turn
- **Player decision**: Final status (`implemented` | `failed` | `blocked`)
- **Files modified**: List of created or changed files
- **Progress summary**: Brief description of progress made

### Coach Feedback

- **Coach decision**: Validation result (`approved` | `feedback` | `rejected`)
- **Coach feedback**: Specific feedback if not approved
- **Acceptance criteria status**: Per-criterion verification status

### Quality Metrics

- **Tests passed/failed**: Test execution results
- **Coverage**: Test coverage percentage
- **Arch score**: Architectural review score (if run)

### Context

- **Turn mode**: How this turn started (fresh, recovering, continuing)
- **Blockers found**: Issues that prevented progress
- **Lessons learned**: What was learned during this turn
- **What to try next**: Suggested focus for the next turn

### Timing

- **Started at**: When the turn began
- **Completed at**: When the turn ended
- **Duration**: Turn duration in seconds

---

## Turn State Schema

The complete turn state entity schema:

### Identity Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Turn identifier: `TURN-{feature_id}-{turn_number}` |
| `feature_id` | string | Feature identifier (e.g., `FEAT-GE`) |
| `task_id` | string | Task identifier (e.g., `TASK-GE-001`) |
| `turn_number` | integer | Turn number (1-indexed) |

### Action Fields

| Field | Type | Description |
|-------|------|-------------|
| `player_summary` | string | What Player implemented/attempted |
| `player_decision` | string | `implemented` \| `failed` \| `blocked` |
| `coach_decision` | string | `approved` \| `feedback` \| `rejected` |
| `coach_feedback` | string? | Specific feedback if not approved |

### Mode Field

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | Turn mode (see [Mode Tracking](#mode-tracking)) |

### Progress Fields

| Field | Type | Description |
|-------|------|-------------|
| `blockers_found` | string[] | List of blockers encountered |
| `progress_summary` | string | Brief description of progress made |
| `files_modified` | string[] | Files created or modified |
| `acceptance_criteria_status` | object | Per-criterion status (see below) |

**Acceptance Criteria Status Format:**
```json
{
  "AC-001: User can log in": "completed",
  "AC-002: Session persists": "in_progress",
  "AC-003: Rate limiting": "not_started"
}
```

Status values: `completed` | `in_progress` | `not_started` | `rejected` | `failed`

### Quality Metrics Fields

| Field | Type | Description |
|-------|------|-------------|
| `tests_passed` | integer? | Number of tests that passed |
| `tests_failed` | integer? | Number of tests that failed |
| `coverage` | float? | Test coverage percentage (0-100) |
| `arch_score` | integer? | Architectural review score (0-100) |

### Timing Fields

| Field | Type | Description |
|-------|------|-------------|
| `started_at` | datetime | When this turn started (ISO 8601) |
| `completed_at` | datetime | When this turn completed (ISO 8601) |
| `duration_seconds` | integer? | Turn duration in seconds |

### Learning Fields

| Field | Type | Description |
|-------|------|-------------|
| `lessons_from_turn` | string[] | Lessons learned during this turn |
| `what_to_try_next` | string? | Suggested focus for the next turn |

---

## Mode Tracking

Each turn starts in one of three modes, indicating how the turn began:

### FRESH_START

First turn of a task, starting from scratch.

```
Turn 1 (mode: FRESH_START)
  → No previous context
  → Begins with initial implementation
```

**When it occurs:**
- First turn of a new task
- After task reset

### CONTINUING_WORK

Normal continuation from previous turn.

```
Turn 2 (mode: CONTINUING_WORK)
  → Has context from Turn 1
  → Addresses Turn 1 feedback
```

**When it occurs:**
- Standard flow after Turn 1 gets feedback/rejection
- Most common mode for turns 2+

### RECOVERING_STATE

Resuming after crash, timeout, or interruption.

```
Turn 3 (mode: RECOVERING_STATE)
  → Previous turn didn't complete properly
  → Attempting to recover and continue
```

**When it occurs:**
- After SDK timeout
- After crash or interruption
- When using `--resume` flag

---

## Querying Turn States

### View All Turns for a Feature

```bash
guardkit graphiti search "turn FEAT-XXX" --group turn_states
```

Example output:
```
Found 3 results for 'turn FEAT-GE':

1. [0.92] turn_state FEAT-GE TASK-GE-001 turn 1: coach_decision=feedback...
2. [0.89] turn_state FEAT-GE TASK-GE-001 turn 2: coach_decision=rejected...
3. [0.87] turn_state FEAT-GE TASK-GE-001 turn 3: coach_decision=approved...
```

### View Turns for a Specific Task

```bash
guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 5
```

### View Recent Turns Across All Tasks

```bash
guardkit graphiti search "turn_state" --group turn_states --limit 10
```

### Filter by Coach Decision

```bash
# View rejected turns (useful for debugging)
guardkit graphiti search "coach_decision rejected" --group turn_states

# View approved turns
guardkit graphiti search "coach_decision approved" --group turn_states
```

### View Turn State Status

```bash
guardkit graphiti status --verbose
```

The `turn_states` group will be listed under "Learning":
```
Learning:
  • task_outcomes: 15
  • failure_patterns: 3
  • successful_fixes: 8
  • turn_states: 12
```

---

## Cross-Turn Learning

The primary purpose of turn state tracking is enabling cross-turn learning. Here's how it works:

### How Turn N+1 Learns from Turn N

When a new turn starts, the system:

1. **Queries previous turns** for this task
2. **Formats context** as actionable information
3. **Emphasizes feedback** if the last turn was rejected
4. **Injects context** into the Player's prompt

### Context Loading

```python
# Automatic context loading at turn start
context = await load_turn_continuation_context(
    graphiti,
    feature_id="FEAT-GE",
    task_id="TASK-GE-001",
    current_turn=2
)
```

### Context Format

The loaded context includes:

```markdown
## Previous Turn Summary (Turn 1)
**What was attempted**: Implemented OAuth2 authentication
**Player decision**: implemented
**Coach decision**: feedback

**Coach feedback**: Add session caching for performance

**Acceptance Criteria Status**:
  ✓ AC-001: User can log in: completed
  ○ AC-002: Session persists: in_progress
  ○ AC-003: Rate limiting: not_started
```

### Emphasized Feedback

If the previous turn was **REJECTED**, the feedback is emphasized:

```markdown
## Previous Turn Summary (Turn 2)
**What was attempted**: Added session caching
**Player decision**: implemented
**Coach decision**: REJECTED

**Coach feedback**: Missing error handling and validation logic

Last Turn Feedback (MUST ADDRESS):
Missing error handling and validation logic. Specifically:
- No validation for session token format
- No handling for Redis connection failures
- No timeout handling for cache operations
```

---

## Example Turn History

Here's a complete example of turn state progression:

### Turn 1 (FRESH_START)

```json
{
  "id": "TURN-FEAT-AUTH-1",
  "feature_id": "FEAT-AUTH",
  "task_id": "TASK-AUTH-001",
  "turn_number": 1,
  "mode": "fresh_start",

  "player_summary": "Implemented JWT-based authentication with login endpoint",
  "player_decision": "implemented",
  "coach_decision": "feedback",
  "coach_feedback": "Missing token refresh mechanism",

  "files_modified": ["src/auth/jwt.py", "src/auth/login.py", "tests/test_auth.py"],
  "tests_passed": 8,
  "tests_failed": 0,
  "coverage": 75.5,

  "acceptance_criteria_status": {
    "AC-001: Login returns JWT": "completed",
    "AC-002: Token refresh works": "not_started",
    "AC-003: Invalid tokens rejected": "completed"
  },

  "lessons_from_turn": ["JWT library handles encoding well"],
  "what_to_try_next": "Implement token refresh endpoint"
}
```

### Turn 2 (CONTINUING_WORK)

```json
{
  "id": "TURN-FEAT-AUTH-2",
  "feature_id": "FEAT-AUTH",
  "task_id": "TASK-AUTH-001",
  "turn_number": 2,
  "mode": "continuing_work",

  "player_summary": "Added token refresh endpoint with sliding window",
  "player_decision": "implemented",
  "coach_decision": "rejected",
  "coach_feedback": "Token refresh endpoint doesn't validate original token expiry",

  "files_modified": ["src/auth/refresh.py", "tests/test_refresh.py"],
  "tests_passed": 10,
  "tests_failed": 2,
  "coverage": 78.2,

  "acceptance_criteria_status": {
    "AC-001: Login returns JWT": "completed",
    "AC-002: Token refresh works": "in_progress",
    "AC-003: Invalid tokens rejected": "completed"
  },

  "blockers_found": ["Unclear requirement on refresh window size"],
  "lessons_from_turn": ["Need to validate original token before refresh"],
  "what_to_try_next": "Add token expiry validation before refresh"
}
```

### Turn 3 (CONTINUING_WORK)

```json
{
  "id": "TURN-FEAT-AUTH-3",
  "feature_id": "FEAT-AUTH",
  "task_id": "TASK-AUTH-001",
  "turn_number": 3,
  "mode": "continuing_work",

  "player_summary": "Fixed token refresh to validate expiry, added edge case tests",
  "player_decision": "implemented",
  "coach_decision": "approved",
  "coach_feedback": null,

  "files_modified": ["src/auth/refresh.py", "tests/test_refresh.py"],
  "tests_passed": 15,
  "tests_failed": 0,
  "coverage": 85.0,

  "acceptance_criteria_status": {
    "AC-001: Login returns JWT": "completed",
    "AC-002: Token refresh works": "completed",
    "AC-003: Invalid tokens rejected": "completed"
  },

  "lessons_from_turn": ["Edge case testing caught the validation bug"],
  "what_to_try_next": null
}
```

---

## Integration with AutoBuild

Turn state tracking is automatically integrated with `/feature-build`:

### Automatic Capture

At the end of each Player-Coach turn, the system automatically:
1. Collects Player report data
2. Collects Coach decision and feedback
3. Creates TurnStateEntity
4. Stores in Graphiti under `turn_states` group

### Automatic Loading

At the start of each turn (after Turn 1), the system:
1. Queries previous turn states
2. Formats as context
3. Injects into Player prompt

### Configuration

Turn state tracking is enabled by default when Graphiti is configured. No additional setup is required.

To verify turn state capture is working:

```bash
# After running a feature-build
guardkit graphiti search "turn TASK-XXX" --group turn_states
```

---

## Debugging with Turn States

Turn states are invaluable for debugging why a task took multiple turns:

### Common Investigation Patterns

**Why did this task take 5 turns?**
```bash
guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 10
# Look for patterns in coach_decision and feedback
```

**What feedback kept getting repeated?**
```bash
guardkit graphiti search "coach_feedback TASK-XXX" --group turn_states
# Check if similar issues recurred
```

**Were there blockers?**
```bash
guardkit graphiti search "blockers TASK-XXX" --group turn_states
# See what blocked progress
```

### Viewing Full Turn Details

For detailed turn inspection, use the search with context:

```bash
guardkit graphiti search "TURN-FEAT-AUTH-2" --group turn_states
```

---

## Best Practices

1. **Review turn history after complex tasks** - Understand what took multiple iterations
   ```bash
   guardkit graphiti search "turn TASK-XXX" --group turn_states
   ```

2. **Check for repeated feedback patterns** - If same feedback appears multiple times, requirements may be unclear

3. **Use turn states for post-mortems** - After difficult tasks, review the turn progression

4. **Monitor turn counts** - Tasks consistently taking 4+ turns may indicate:
   - Requirements too broad
   - Acceptance criteria unclear
   - Task should be split

5. **Verify turn capture is working** - After feature-build, confirm turns were captured:
   ```bash
   guardkit graphiti status --verbose
   ```

---

## Troubleshooting

### No turn states captured

If `guardkit graphiti search "turn TASK-XXX" --group turn_states` returns no results:

1. **Check Graphiti is enabled:**
   ```bash
   guardkit graphiti status
   ```

2. **Verify the task ran via /feature-build:**
   Turn states are only captured during `/feature-build`, not manual `/task-work`.

3. **Check logs for capture errors:**
   ```bash
   grep "turn state" .guardkit/logs/autobuild.log
   ```

### Missing cross-turn context

If Turn N+1 seems to ignore Turn N's feedback:

1. **Verify turn N was captured:**
   ```bash
   guardkit graphiti search "turn TASK-XXX turn N" --group turn_states
   ```

2. **Check context loading:**
   Enable verbose logging to see context injection.

### Stale turn states

If you're seeing turn states from old runs:

- Turn states are not automatically cleaned up
- They provide historical audit trail
- Use specific task IDs in queries to filter

---

## See Also

- [AutoBuild Workflow Guide](autobuild-workflow.md) - Player-Coach workflow details
- [Interactive Knowledge Capture](graphiti-knowledge-capture.md) - Capture project knowledge
- [Job-Specific Context](graphiti-job-context.md) - How context is loaded for tasks
- [Graphiti Commands Guide](graphiti-commands.md) - Complete CLI reference
- [FEAT-GR-005: Knowledge Query Command](../research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md) - Technical specification
