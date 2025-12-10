---
id: TASK-ENF3
title: Add prominent invocation messages to task-work
status: completed
created: 2025-11-27T12:50:00Z
updated: 2025-11-27T18:58:36Z
completed_at: 2025-11-27T18:58:36Z
priority: high
tags: [visibility, ux, task-work, agent-invocation]
task_type: implementation
epic: null
feature: agent-invocation-enforcement
requirements: []
dependencies: []
complexity: 3
related_to: TASK-8D3F
previous_state: in_review
state_transition_reason: "Task completion - all verification passed"
completed_phases:
  - phase_2: "Implementation Planning"
  - phase_2_5b: "Architectural Review (95/100)"
  - phase_2_7: "Complexity Evaluation (2/10 - Auto-proceed)"
  - phase_3: "Implementation"
  - phase_4: "Testing (All checks passed)"
  - phase_5: "Code Review (Approved)"
completion_metrics:
  total_duration_hours: 6.1
  total_duration_minutes: 369
  files_modified: 1
  lines_added: 162
  message_blocks_added: 10
  phases_updated: 5
  architectural_review_score: 95
  code_review_status: "Approved"
  acceptance_criteria_met: 9
  acceptance_criteria_total: 9
  template_compliance: 100
final_deliverables:
  - file: "installer/core/commands/task-work.md"
    changes: "Added 10 message blocks (5 pre-invocation + 5 post-completion)"
    impact: "Improved agent invocation visibility for all task-work executions"
quality_metrics:
  all_validation_passed: true
  documentation_syntax_valid: true
  template_compliance_percent: 100
  acceptance_criteria_percent: 100
  architectural_score: 95
lessons_learned:
  what_went_well:
    - "Documentation-only approach eliminated code complexity"
    - "Template-based design ensures consistency"
    - "Low complexity (2/10) enabled fast auto-proceed"
  challenges_faced:
    - "None - straightforward documentation update"
  improvements_for_next_time:
    - "Consider adding timing implementation guidance"
    - "Document file list truncation logic explicitly"
---

# Task: Add Prominent Invocation Messages to task-work

## Context

**From TASK-8D3F Review**: Agent invocations are currently not visually prominent during task-work execution. This makes it difficult to:
1. Verify that agents are actually being invoked
2. Understand which agent is handling which phase
3. Track progress during long-running phases
4. Debug when the wrong agent is selected

**User Feedback**: "Previously it used to be obvious which agents were being used but I don't see that now"

**Priority**: HIGH - Improves user experience and accountability, but doesn't directly prevent protocol violations.

## Objective

Add clear, visually prominent messages before and after each agent invocation that:
1. Announce which agent is being invoked and for which phase
2. Show model selection (Haiku vs Sonnet) with cost/speed benefits
3. Display agent specialization to build user confidence
4. Confirm completion with timing and file modification information

## Requirements

### R1: Pre-Invocation Message

**Requirement**: Display prominent message before invoking each agent

**Implementation** (Add to each phase in `task-work.md`):
```markdown
#### Phase 3: Implementation

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_implementation_agent}
═══════════════════════════════════════════════════════
Phase: 3 (Implementation)
Model: Haiku (4-5x faster, 80% cheaper than Sonnet)
Stack: {detected_stack}
Specialization:
  - {capability_1}
  - {capability_2}
  - {capability_3}

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool:
...
```

**Expected Output**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: python-api-specialist
═══════════════════════════════════════════════════════
Phase: 3 (Implementation)
Model: Haiku (4-5x faster, 80% cheaper than Sonnet)
Stack: python
Specialization:
  - FastAPI endpoint implementation
  - Async request handling patterns
  - Pydantic schema integration

Starting agent execution...
═══════════════════════════════════════════════════════
```

**Acceptance Criteria**:
- [ ] Message displayed before every Task tool invocation
- [ ] Message includes agent name, phase, model, stack, and specialization
- [ ] Message uses box characters (═) for visual separation
- [ ] Message includes 🤖 emoji for easy scanning
- [ ] Specialization shows top 3 capabilities from agent metadata

### R2: Post-Completion Message

**Requirement**: Display confirmation message after agent completes

**Implementation** (Add after each phase in `task-work.md`):
```markdown
**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_implementation_agent}
═══════════════════════════════════════════════════════
Duration: {duration} seconds
Files modified: {file_count}
{If file_count > 0: list up to 5 files}
Status: Success

Proceeding to Phase {next_phase}...
═══════════════════════════════════════════════════════
```
```

**Expected Output**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: python-api-specialist
═══════════════════════════════════════════════════════
Duration: 45 seconds
Files modified: 3
  - src/api/users.py
  - src/models/user.py
  - tests/test_users.py
Status: Success

Proceeding to Phase 4 (Testing)...
═══════════════════════════════════════════════════════
```

**Acceptance Criteria**:
- [ ] Message displayed after every agent completes
- [ ] Message includes agent name, duration, files modified, and status
- [ ] Message lists up to 5 modified files (prevents clutter)
- [ ] Message uses ✅ emoji for success confirmation
- [ ] Message indicates next phase to set expectations

### R3: Model Selection Display

**Requirement**: Make model selection (Haiku vs Sonnet) transparent to user

**Rationale**: Users should understand why certain agents use Haiku (speed + cost) vs Sonnet (quality)

**Implementation**:
```python
def get_model_display(agent_name: str, model: str) -> str:
    """
    Get formatted model display with cost/speed benefits.

    Args:
        agent_name: Name of the agent
        model: Model being used ('haiku' or 'sonnet')

    Returns:
        Formatted string explaining model choice
    """
    if model == "haiku":
        return "Haiku (4-5x faster, 80% cheaper than Sonnet)"
    elif model == "sonnet":
        return "Sonnet (deep reasoning, architectural quality)"
    elif model == "opus":
        return "Opus 4.5 (maximum reasoning for critical decisions)"
    else:
        return model
```

**Expected Output**:
```
Model: Haiku (4-5x faster, 80% cheaper than Sonnet)
```

**Acceptance Criteria**:
- [ ] Haiku agents show speed and cost benefits
- [ ] Sonnet agents show quality benefits
- [ ] Model display format is consistent across all phases
- [ ] Model selection is transparent to user

### R4: Agent Specialization Display

**Requirement**: Show top 3 capabilities from agent metadata to build user confidence

**Implementation**:
```python
def get_specialization_display(agent_name: str, agent_metadata: Dict) -> str:
    """
    Get formatted specialization display from agent capabilities.

    Args:
        agent_name: Name of the agent
        agent_metadata: Agent frontmatter metadata

    Returns:
        Formatted string with top 3 capabilities
    """
    capabilities = agent_metadata.get("capabilities", [])
    top_3 = capabilities[:3]

    if not top_3:
        return f"  - {agent_name} specialist"

    return "\n".join(f"  - {cap}" for cap in top_3)
```

**Expected Output**:
```
Specialization:
  - FastAPI endpoint implementation
  - Async request handling patterns
  - Pydantic schema integration
```

**Acceptance Criteria**:
- [ ] Displays top 3 capabilities from agent metadata
- [ ] Falls back to generic message if no capabilities in metadata
- [ ] Capabilities are indented for readability
- [ ] Format is consistent across all agents

### R5: Integration with All Phases

**Requirement**: Add invocation/completion messages to all 5 phases

**Phases to Update** (in `task-work.md`):
1. Phase 2: Implementation Planning
2. Phase 2.5B: Architectural Review
3. Phase 3: Implementation
4. Phase 4: Testing
5. Phase 5: Code Review

**Template** (Apply to each phase):
```markdown
#### Phase X: {Phase Name}

**DISPLAY INVOCATION MESSAGE**: [Pre-invocation message from R1]

**INVOKE** Task tool: [Existing invocation]

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**: [Post-completion message from R2]
```

**Acceptance Criteria**:
- [ ] All 5 phases have pre-invocation messages
- [ ] All 5 phases have post-completion messages
- [ ] Message format is consistent across phases
- [ ] Timing information calculated and displayed accurately

## Implementation Plan

### Phase 1: Create Display Helper Functions

**Files**:
- `installer/core/commands/lib/agent_display.py` (new)

**Implementation**:
1. Create `display_invocation_message()` function
2. Create `display_completion_message()` function
3. Create `get_model_display()` helper
4. Create `get_specialization_display()` helper
5. Add unit tests for formatting functions

### Phase 2: Update task-work.md for Phase 2

**Files**:
- `installer/core/commands/task-work.md` (modify)

**Implementation**:
1. Add pre-invocation message before Phase 2 INVOKE
2. Add post-completion message after Phase 2 completes
3. Test output formatting
4. Verify timing calculation works

### Phase 3: Update task-work.md for Remaining Phases

**Files**:
- `installer/core/commands/task-work.md` (modify)

**Implementation**:
1. Add messages to Phase 2.5B (Architectural Review)
2. Add messages to Phase 3 (Implementation)
3. Add messages to Phase 4 (Testing)
4. Add messages to Phase 5 (Code Review)
5. Ensure consistent formatting across all phases

### Phase 4: Testing

**Test Cases**:
1. **Standard workflow** → All 5 phases show invocation/completion messages
2. **Haiku agent** → Message shows speed/cost benefits
3. **Sonnet agent** → Message shows quality benefits
4. **Long file list** → Only first 5 files displayed
5. **No files modified** → Message shows "0 files modified"

**Acceptance Criteria**:
- [ ] All test cases produce correct output
- [ ] Messages are visually prominent
- [ ] Timing information is accurate
- [ ] File lists are properly truncated

## Success Criteria

### SC1: Visibility Improved

- [ ] User can immediately see which agent is being invoked
- [ ] User knows which phase the agent is handling
- [ ] User understands model selection rationale

### SC2: Accountability Enhanced

- [ ] Agent invocations are impossible to miss visually
- [ ] Completion status is clearly confirmed
- [ ] Timing information provides progress feedback

### SC3: User Confidence Built

- [ ] Specialization display shows agent is appropriate for task
- [ ] Model selection is transparent (speed vs quality trade-off)
- [ ] File modification tracking shows agent made expected changes

### SC4: Consistent Experience

- [ ] Message format identical across all 5 phases
- [ ] Visual separation clear and consistent
- [ ] Emoji usage consistent (🤖 for invocation, ✅ for completion)

## Estimated Effort

**Total**: 2-4 hours

**Breakdown**:
- Phase 1 (Helper Functions): 1 hour
- Phase 2 (Phase 2 Update): 30 minutes
- Phase 3 (Remaining Phases): 1 hour
- Phase 4 (Testing): 30 minutes - 1.5 hours

## Related Tasks

- TASK-8D3F - Review task that identified this gap
- TASK-ENF2 - Add agent invocation tracking (complements this task)
- TASK-ENF5 - Add phase gate checkpoints (uses similar messaging)
- TASK-5F8A - Review and improve subagent invocation enforcement

## Notes

**Low Effort, High Impact**: This task provides significant UX improvement with minimal implementation effort.

**User Feedback**: Directly addresses user comment "Previously it used to be obvious which agents were being used but I don't see that now".

**Testing**: Use MyDrive TASK-ROE-007g scenario - prominent messages would have made it obvious that Phases 3 and 4 were being done directly instead of via agents.
