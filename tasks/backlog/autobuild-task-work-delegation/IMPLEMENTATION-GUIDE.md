# Implementation Guide: AutoBuild task-work Delegation

## Wave Breakdown

### Wave 1: Core Delegation (4-5 hours)

These tasks establish the fundamental delegation mechanism.

#### TASK-TWD-001: Modify AgentInvoker.invoke_player()
- **Method**: task-work
- **Parallel**: Yes (with TWD-002)
- **Workspace**: `autobuild-twd-wave1-1`

Replace the current SDK-direct implementation with task-work delegation:

```python
# Current (to be replaced):
await self._invoke_with_role(
    prompt=prompt,
    agent_type="player",
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    ...
)

# New:
result = await self._invoke_task_work_implement(
    task_id=task_id,
    mode=mode,
    feedback=feedback,
)
```

#### TASK-TWD-002: Task State Bridging
- **Method**: task-work
- **Parallel**: Yes (with TWD-001)
- **Workspace**: `autobuild-twd-wave1-2`

Ensure task is in correct state for --implement-only:

```python
# Before player turn: Verify/set design_approved state
# After coach approve: Mark task complete
# Handle state transitions properly
```

---

### Wave 2: Feedback Integration (3-4 hours)

These tasks enable the adversarial loop to work with task-work delegation.

**Dependencies**: Wave 1 must complete first.

#### TASK-TWD-003: Coach Feedback Integration
- **Method**: task-work
- **Parallel**: Yes (with TWD-004)
- **Workspace**: `autobuild-twd-wave2-1`

Write Coach feedback to a location task-work can read:

```python
# Option A: Task frontmatter
# Option B: Separate context file (.claude/task-context/coach_feedback.md)
# Option C: Task state metadata

def _write_coach_feedback(self, task_id: str, feedback: str):
    """Write Coach feedback for next Player turn."""
    feedback_path = self.worktree_path / ".claude" / "task-context" / f"{task_id}_feedback.md"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(feedback)
```

Update task-work Phase 3 to read feedback context.

#### TASK-TWD-004: Development Mode CLI Parameter
- **Method**: task-work
- **Parallel**: Yes (with TWD-003)
- **Workspace**: `autobuild-twd-wave2-2`

Add `--mode` parameter to AutoBuild CLI:

```python
@click.option(
    "--mode",
    type=click.Choice(["standard", "tdd"]),
    default="tdd",
    help="Development mode (default: tdd)",
)
def task(ctx, task_id, mode, ...):
    ...
```

Pass mode through to AgentInvoker.

---

### Wave 3: Testing & Documentation (2-3 hours)

**Dependencies**: Wave 2 must complete first.

#### TASK-TWD-005: Integration Tests
- **Method**: task-work
- **Parallel**: Yes (with TWD-006)
- **Workspace**: `autobuild-twd-wave3-1`

Create tests for:
1. Happy path: task-work delegation executes successfully
2. Feedback loop: Coach feedback passed to next Player turn
3. Max turns: Proper exit when max_turns reached
4. Error handling: task-work failures handled gracefully

#### TASK-TWD-006: Documentation Updates
- **Method**: direct
- **Parallel**: Yes (with TWD-005)
- **Workspace**: `autobuild-twd-wave3-2`

Update:
- CLAUDE.md AutoBuild section
- autobuild-player.md agent definition
- autobuild-coach.md agent definition (if needed)

---

## Execution Strategy

```
Wave 1 (Parallel):
  TWD-001 ─────┬───► Wave 2
  TWD-002 ─────┘

Wave 2 (Parallel, depends on Wave 1):
  TWD-003 ─────┬───► Wave 3
  TWD-004 ─────┘

Wave 3 (Parallel, depends on Wave 2):
  TWD-005 ─────┬───► Done
  TWD-006 ─────┘
```

## Key Files to Modify

| File | Changes |
|------|---------|
| `guardkit/orchestrator/agent_invoker.py` | Replace invoke_player() implementation |
| `guardkit/orchestrator/autobuild.py` | Pass mode parameter, handle state transitions |
| `guardkit/cli/autobuild.py` | Add --mode CLI option |
| `installer/core/commands/task-work.md` | Document feedback context reading (if needed) |
| `CLAUDE.md` | Update AutoBuild documentation |
| `.claude/agents/autobuild-player.md` | Note delegation to task-work |

## Risk Mitigation

1. **Backward Compatibility**: Keep old invoke_player() available behind feature flag initially
2. **State Transitions**: Add comprehensive logging for state changes
3. **Error Recovery**: If task-work fails, fall back to error state (not silent failure)
4. **Testing**: Each wave includes testing before proceeding

## Success Criteria (Core Delegation)

1. AutoBuild tasks use stack-specific subagents (verify via logs)
2. TDD mode enforced (tests written before implementation)
3. Quality gates executed (Phase 4.5, code-reviewer)
4. Coach feedback properly passed to next Player turn
5. All existing AutoBuild tests still pass

---

## Quality Enhancements (Waves 4-5)

These tasks add robustness and debugging improvements to the core delegation.

**Dependencies**: Waves 1-3 must complete first.

---

### Wave 4: Verification & Debugging (2-3 hours)

#### TASK-TWD-007: Escape Hatch Pattern
- **Method**: task-work
- **Parallel**: Yes (with TWD-008)
- **Workspace**: `autobuild-twd-wave4-1`
- **Priority**: HIGH

When approaching max_turns, Player generates structured blocked-task report:

```json
{
  "blocked_report": {
    "blocking_issues": [
      {"issue": "Cannot mock external API", "category": "external_dependency"}
    ],
    "attempts_made": [
      {"turn": 1, "action": "Tried httpretty", "result": "Failed"}
    ],
    "suggested_alternatives": ["Use real test API keys"],
    "human_action_required": "Provide test API keys in .env"
  }
}
```

Benefits:
- Actionable debugging info instead of generic "Human intervention required"
- Tracks what was tried across turns
- Provides clear next steps for human

#### TASK-TWD-008: Honesty Verification
- **Method**: task-work
- **Parallel**: Yes (with TWD-007)
- **Workspace**: `autobuild-twd-wave4-2`
- **Priority**: MEDIUM

Coach cross-references Player claims against reality:

```python
class CoachVerifier:
    def verify_player_report(self, report: dict) -> HonestyVerification:
        # Verify tests_passed claim
        # Verify files exist
        # Verify test count
        return HonestyVerification(
            verified=True/False,
            discrepancies=[...],
            honesty_score=0.0-1.0,
        )
```

Benefits:
- Catches false success claims (hallucination)
- Adds accountability to Player reports
- Prevents premature approval

---

### Wave 5: Completion Rigor (2-3 hours)

**Dependencies**: Wave 4 should complete first (uses honesty verification infrastructure).

#### TASK-TWD-009: Promise-Based Completion
- **Method**: task-work
- **Parallel**: No (depends on TWD-008)
- **Workspace**: `autobuild-twd-wave5-1`
- **Priority**: HIGH

Player maps each acceptance criterion to evidence:

```json
{
  "completion_promise": {
    "statement": "All acceptance criteria verified",
    "criteria": [
      {
        "criterion_id": "AC-001",
        "criterion": "OAuth2 authentication works",
        "status": "verified",
        "evidence": "test_oauth_flow passes"
      }
    ]
  }
}
```

Coach verifies each criterion independently:

```json
{
  "criteria_verification": [
    {
      "criterion_id": "AC-001",
      "coach_verified": true,
      "verification_method": "Ran test, PASSED"
    }
  ]
}
```

Benefits:
- More rigorous than binary approve/feedback
- Explicit mapping of claims to evidence
- Progress tracking per acceptance criterion

---

## Full Execution Strategy

```
Phase 1: Core Delegation
═════════════════════════

Wave 1 (Parallel):
  TWD-001 ─────┬───► Wave 2
  TWD-002 ─────┘

Wave 2 (Parallel, depends on Wave 1):
  TWD-003 ─────┬───► Wave 3
  TWD-004 ─────┘

Wave 3 (Parallel, depends on Wave 2):
  TWD-005 ─────┬───► Core Complete
  TWD-006 ─────┘

Phase 2: Quality Enhancements
═════════════════════════════

Wave 4 (Parallel, depends on Wave 3):
  TWD-007 ─────┬───► Wave 5
  TWD-008 ─────┘

Wave 5 (Sequential, depends on Wave 4):
  TWD-009 ─────────► All Complete
```

## Success Criteria (Quality Enhancements)

1. Player generates blocked_report when approaching max_turns
2. Coach verifies Player claims against actual test results
3. Honesty discrepancies flagged and prevent approval
4. Completion promises map all acceptance criteria
5. Criteria progress tracked and displayed per turn
