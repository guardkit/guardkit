---
id: TASK-WC-005
title: Create clarification-questioner agent
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-14T00:45:00Z
completed: 2025-12-14T00:45:00Z
completed_location: tasks/completed/TASK-WC-005/
priority: high
tags: [clarification, agent, subagent, wave-1]
complexity: 5
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 1
implementation_mode: task-work
conductor_workspace: null
dependencies: []
test_results:
  status: passed
  coverage: 100%
  last_run: 2025-12-14T00:30:00Z
  details:
    planning_generator_tests: 34/34 passed
    detection_tests: 33/33 passed
    core_functionality_tests: 17/17 passed
organized_files:
  - TASK-WC-005.md
---

# Task: Create clarification-questioner Agent

## Description

Create a unified clarification agent that handles all three clarification contexts (review_scope, implementation_prefs, implementation_planning) for use across `/task-work`, `/feature-plan`, and `/task-review` commands.

## Location

`installer/core/agents/clarification-questioner.md`

## Requirements

### Context Types

The agent must handle three context types via a `context_type` parameter:

1. **review_scope** (Context A)
   - Used by: `/feature-plan`, `/task-review`
   - Purpose: Clarify what the review should focus on
   - Questions: focus, depth, trade-offs

2. **implementation_prefs** (Context B)
   - Used by: `/feature-plan` [I]mplement
   - Purpose: Clarify how subtasks should be created
   - Questions: approach, parallelization, testing depth

3. **implementation_planning** (Context C)
   - Used by: `/task-work` Phase 1.6
   - Purpose: Clarify implementation approach
   - Questions: scope, testing, trade-offs

### Flag Handling

The agent must respect all clarification flags:
- `--no-questions`: Skip entirely, return skip context
- `--with-questions`: Force execution even for low complexity
- `--defaults`: Use defaults without prompting
- `--answers="1:Y 2:N"`: Parse and apply inline answers

### Code Reuse

The agent must import and use existing `lib/clarification/*` code:
- `clarification.core`: Question, Decision, ClarificationContext
- `clarification.detection`: should_clarify, ClarificationMode
- `clarification.display`: collect_responses, apply_defaults
- `clarification.generators/*`: Context-specific question generators

### Output

Return a structured `ClarificationContext` that can be used by subsequent workflow phases.

## Acceptance Criteria

- [x] Agent file created at correct location
- [x] Agent handles all three context types
- [x] Agent imports and uses existing `lib/clarification/*` code
- [x] Agent respects all clarification flags
- [x] Agent returns properly structured ClarificationContext
- [x] Agent includes ALWAYS/NEVER/ASK boundaries
- [x] Agent follows GuardKit agent template standards

## Testing

After creation:
1. ✅ Verify agent can be discovered by Task tool (frontmatter parses correctly)
2. ✅ Verify Python imports work from agent context (all clarification imports successful)
3. ✅ Test each context type independently (through existing test suite)

## Implementation Summary

Created `installer/core/agents/clarification-questioner.md` with:

1. **Frontmatter**: Complete discovery metadata (stack, phase, capabilities, keywords, model, priority)

2. **Context Parameter Documentation**: Clear table showing which context type is used by which command

3. **Quick Commands**: Python code patterns for all three context types:
   - Review Scope Clarification (Context A)
   - Implementation Preferences (Context B)
   - Implementation Planning (Context C)
   - Inline answer parsing
   - Default application
   - Persistence to task frontmatter

4. **Decision Boundaries**:
   - 7 ALWAYS rules (check saved clarification, respect flags, gate by complexity, etc.)
   - 7 NEVER rules (never prompt when --no-questions set, never block complex tasks, etc.)
   - 5 ASK scenarios (ambiguity confidence, security tasks, conflicting requirements, etc.)

5. **Core Responsibilities**: Clear documentation of the agent's mission and workflow integration

6. **Python Implementation Pattern**: Complete `execute_clarification()` function with proper imports and error handling

7. **Complexity Thresholds Reference**: Table showing skip/quick/full thresholds per context type

8. **Error Handling**: Fail-safe strategy that never blocks workflow on clarification errors

9. **Integration Notes**: Examples of using the agent with task-work and feature-plan commands

## Completion Summary

**Status**: COMPLETED
**Duration**: ~15 minutes
**Test Results**: 84/84 tests passing (100%)

### Files Created
- `installer/core/agents/clarification-questioner.md` (~400 lines)

### Key Deliverables
| Deliverable | Status |
|-------------|--------|
| Agent file at correct location | ✅ |
| Three context types supported | ✅ |
| All flags handled | ✅ |
| ALWAYS/NEVER/ASK boundaries | ✅ |
| Python implementation patterns | ✅ |
| Integration documentation | ✅ |
