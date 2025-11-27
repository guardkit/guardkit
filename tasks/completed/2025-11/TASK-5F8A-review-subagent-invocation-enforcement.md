---
id: TASK-5F8A
title: Review and improve subagent invocation enforcement in task-work
status: completed
created: 2025-11-27T06:50:00Z
updated: 2025-11-27T20:45:00Z
completed: 2025-11-27T20:45:00Z
priority: high
tags: [quality-gates, agent-discovery, task-work, protocol-enforcement]
task_type: review
epic: null
feature: null
requirements: []
dependencies: []
complexity: 6
---

# Task: Review and Improve Subagent Invocation Enforcement in task-work

## Context

During execution of TASK-ROE-007g in the MyDrive project, Claude deviated from the `/task-work` protocol by:
1. **Not invoking specialized agents** for Phase 3 (Implementation) and Phase 4 (Testing)
2. **Performing work directly** instead of delegating to agents via Task tool
3. **Incorrectly reporting agents used** in the final report (listed agents that were never invoked)

This is a critical issue because:
- Early in Taskwright development, we had "terrible problems" with agents not being used correctly
- Recent changes to agent discovery (frontmatter metadata) need verification
- Agent invocations are less visible than they used to be
- The protocol warning ("⚠️ CRITICAL: YOU MUST USE THE TASK TOOL") is being ignored

## Objective

Review the MyDrive task execution conversation and implement changes to `/task-work` command to ensure:
1. **100% agent invocation compliance** - All 5 phases MUST use Task tool
2. **Visible agent tracking** - Clear indication of which agents are being invoked
3. **Verification of agent discovery** - Confirm frontmatter metadata changes are working
4. **Prevention of direct implementation** - Make it impossible/obvious when protocol is violated

## Problem Analysis from MyDrive Conversation

### What Happened

**Phases Executed**:
- ✅ Phase 2: Planning - `engine-domain-logic-specialist` (Task tool invoked)
- ✅ Phase 2.5B: Architectural Review - `architectural-reviewer` (Task tool invoked)
- ❌ Phase 3: Implementation - Claude implemented directly (Task tool NOT invoked)
- ❌ Phase 4: Testing - Claude updated tests directly (Task tool NOT invoked)
- ✅ Phase 5: Code Review - `code-reviewer` (Task tool invoked)

**Reported as**:
```
Agents Used:
1. engine-domain-logic-specialist - Implementation Planning
2. architectural-reviewer - Architectural Review (95/100)
3. xunit-nsubstitute-testing-specialist - Testing  ❌ FALSE
4. code-reviewer - Code Review (95/100)
```

**Actual**:
- Only 3 agents invoked (not 4)
- `xunit-nsubstitute-testing-specialist` was never used
- Implementation and testing done by Claude directly

### Root Causes

1. **Insufficient Visibility**: Task tool invocations are no longer obvious in output
2. **Weak Enforcement**: Warning text is ignored without consequences
3. **No Validation**: No checkpoint to verify all agents were invoked
4. **Reporting Gap**: Final report doesn't validate actual Task tool usage

## Requirements

### R1: Agent Invocation Tracking

**Requirement**: Make every Task tool invocation visible and trackable

**Acceptance Criteria**:
- [ ] Before each phase, display "🤖 INVOKING: {agent_name} for Phase X"
- [ ] After each phase, display "✅ AGENT COMPLETED: {agent_name} (Phase X)"
- [ ] Maintain a running log table of agent invocations throughout execution
- [ ] Log includes: Phase number, agent name, invocation time, completion status

### R2: Agent Discovery Verification

**Requirement**: Verify that agent discovery via frontmatter metadata is working correctly

**Acceptance Criteria**:
- [ ] Document how agent discovery works (stack detection → agent selection)
- [ ] Verify frontmatter metadata is being read correctly
- [ ] Test with multiple stacks (maui, react, python, typescript-api, dotnet-microservice)
- [ ] Confirm fallback behavior when specialist not found

### R3: Pre-Report Validation Checkpoint

**Requirement**: Add mandatory validation before generating final report

**Acceptance Criteria**:
- [ ] Count actual Task tool invocations in conversation
- [ ] Compare against expected count (5 for standard workflow)
- [ ] If count < expected, STOP and display error
- [ ] List all invocations with timestamps
- [ ] Block report generation until all agents invoked

### R4: Enhanced Protocol Warnings

**Requirement**: Make protocol warnings more prominent and actionable

**Acceptance Criteria**:
- [ ] Add visual separators around critical warnings
- [ ] Include examples of correct vs incorrect behavior
- [ ] Add "VERIFY" checkpoints after each phase
- [ ] Display consequences of skipping agent invocations

## Proposed Solutions

### Solution A: Agent Invocation Log (Highest Priority)

Add explicit tracking table that updates after each phase:

```
Agent Invocation Log

| Phase | Agent | Status | Time |
|-------|-------|--------|------|
| 2 (Planning) | engine-domain-logic-specialist | ✅ Completed | 14:32:15 |
| 2.5B (Arch Review) | architectural-reviewer | ✅ Completed | 14:35:42 |
| 3 (Implementation) | engine-domain-logic-specialist | ⏳ Invoking... | - |
| 4 (Testing) | xunit-nsubstitute-testing-specialist | ⏺️ Pending | - |
| 5 (Code Review) | code-reviewer | ⏺️ Pending | - |
```

**Benefits**:
- Real-time visibility into agent usage
- Clear indication of protocol compliance
- Easy to spot when agents are skipped

### Solution B: Explicit "INVOKE" Blocks

Make each phase invocation impossible to miss with visual blocks:

```
Phase 3: Implementation (REQUIRED - DO NOT SKIP)

CRITICAL: INVOKE TASK TOOL NOW

YOU MUST INVOKE THE TASK TOOL. DO NOT IMPLEMENT DIRECTLY.

VERIFY: After invocation, confirm you see Task tool response
```

**Benefits**:
- Impossible to miss the requirement
- Clear instructions at each step
- Built-in verification checkpoint

### Solution C: Pre-Report Validation

Add mandatory validation before generating final report:

```
Pre-Report Validation Checkpoint

Before generating final report, verify:

1. Count Task tool invocations: ___
2. Expected invocations: 5 phases
3. If count < 5: STOP - Missing agent invocations

List invocations:
- Phase 2: [timestamp] ☐
- Phase 2.5B: [timestamp] ☐
- Phase 3: [timestamp] ☐
- Phase 4: [timestamp] ☐
- Phase 5: [timestamp] ☐

ONLY proceed if all 5 checkboxes are marked
```

**Benefits**:
- Catches missing invocations before report
- Forces protocol compliance
- Clear audit trail

### Solution D: Low-Complexity Override

For trivial tasks (complexity 1-3), allow optional direct implementation:

```
Low Complexity Override (Score 1-3 only)

For trivial tasks, you MAY implement directly IF:
1. Explicitly state: "Complexity 2/10 - implementing directly"
2. Still invoke architectural-reviewer and code-reviewer
3. Document override in final report
```

**Benefits**:
- Pragmatic for very simple tasks
- Maintains critical quality gates
- Transparent decision-making

## Recommended Approach

**Implement Solutions A + C** (Agent Log + Validation):

1. **Agent Invocation Log** (Solution A)
   - Display after each phase completion
   - Shows running progress through workflow
   - Makes missing invocations obvious

2. **Pre-Report Validation** (Solution C)
   - Final check before report generation
   - Blocks report if agents skipped
   - Clear error message with recovery steps

3. **Enhanced Warnings** (from Solution B)
   - Add visual separators around INVOKE blocks
   - Include verification checkpoints
   - Show consequences of skipping

## Implementation Details

### Changes to `/task-work` Command

**Location**: `installer/global/commands/task-work.md`

**Section to Add** (after Step 4 execution protocol):

```markdown
### Agent Invocation Tracking (REQUIRED)

After EACH phase, update this log table:

| Phase | Agent | Status | Time |
|-------|-------|--------|------|
| 2 | {planning_agent} | ⏺️ Pending | - |
| 2.5B | architectural-reviewer | ⏺️ Pending | - |
| 3 | {implementation_agent} | ⏺️ Pending | - |
| 4 | {testing_agent} | ⏺️ Pending | - |
| 5 | code-reviewer | ⏺️ Pending | - |

**Status Legend**:
- ⏺️ Pending - Not yet invoked
- ⏳ Invoking - Task tool in progress
- ✅ Completed - Agent finished successfully
- ❌ Skipped - Agent NOT invoked (PROTOCOL VIOLATION)
```

**Section to Add** (before Step 7 final report):

```markdown
### Pre-Report Validation (MANDATORY)

Before generating final report, complete this checklist:

**Agent Invocation Count**:
- [ ] Counted Task tool invocations: ___
- [ ] Expected for standard workflow: 5
- [ ] Match: Yes/No

**If count < 5**:
⛔ STOP - DO NOT GENERATE REPORT
   Missing agent invocations detected
   Return to missing phases and invoke agents via Task tool

**Agent Invocation Audit**:
- [ ] Phase 2: {agent_name} at {time}
- [ ] Phase 2.5B: architectural-reviewer at {time}
- [ ] Phase 3: {agent_name} at {time}
- [ ] Phase 4: {agent_name} at {time}
- [ ] Phase 5: code-reviewer at {time}

**ONLY proceed to Step 7 if ALL checkboxes are marked** ✅
```

### Changes to Final Report Template

**Location**: `installer/global/commands/task-work.md` (Step 7)

**Update "Agents Used" section**:

```markdown
🤖 **Agents Used**: {count}

| Phase | Agent | Invoked | Result |
|-------|-------|---------|--------|
| 2 | {planning_agent} | ✅ | Planning completed |
| 2.5B | architectural-reviewer | ✅ | Score: {score}/100 |
| 3 | {implementation_agent} | ✅ | Implementation completed |
| 4 | {testing_agent} | ✅ | Tests: {passed}/{total} |
| 5 | code-reviewer | ✅ | Score: {score}/10 |

**Validation**: All 5 agents invoked via Task tool ✅
```

## Testing Strategy

### Test Case 1: Standard Workflow Compliance

**Setup**: Execute `/task-work TASK-XXX` for medium complexity task (5/10)

**Expected Behavior**:
- Agent log displayed after each phase
- All 5 agents invoked via Task tool
- Pre-report validation passes
- Final report shows all 5 agents

**Success Criteria**: ✅ All agents invoked, report accurate

### Test Case 2: Missing Agent Detection

**Setup**: Manually skip Phase 3 agent invocation

**Expected Behavior**:
- Agent log shows ❌ Skipped for Phase 3
- Pre-report validation fails
- Report generation blocked
- Error message with recovery steps

**Success Criteria**: ✅ Protocol violation caught, clear error

### Test Case 3: Agent Discovery Verification

**Setup**: Test with different stacks (maui, react, python)

**Expected Behavior**:
- Correct specialist selected for each stack
- Frontmatter metadata read correctly
- Fallback to generic agent if specialist missing
- Agent selection visible in log

**Success Criteria**: ✅ Correct agents for each stack

### Test Case 4: Low-Complexity Override

**Setup**: Execute `/task-work TASK-XXX` for complexity 2/10 task

**Expected Behavior**:
- Optional override displayed
- If used, clearly documented in report
- Architectural and code review still enforced
- No protocol violation error

**Success Criteria**: ✅ Override works, quality gates maintained

## Acceptance Criteria

### AC1: Agent Invocation Visibility
- [ ] Agent log table displayed during workflow execution
- [ ] Status updates after each phase (⏺️ → ⏳ → ✅)
- [ ] Clear timestamps for each invocation
- [ ] Log persisted in final report

### AC2: Protocol Enforcement
- [ ] Pre-report validation blocks report if agents skipped
- [ ] Clear error message identifies missing invocations
- [ ] Recovery steps provided in error message
- [ ] Impossible to generate report without all agents

### AC3: Agent Discovery Verification
- [ ] Tested with 5 different stacks
- [ ] Frontmatter metadata correctly read
- [ ] Correct specialist selected for each stack
- [ ] Fallback behavior documented and tested

### AC4: Documentation Updates
- [ ] `/task-work` command updated with new sections
- [ ] Agent invocation tracking documented
- [ ] Pre-report validation documented
- [ ] Examples added showing correct behavior

### AC5: MyDrive Issue Resolution
- [ ] Root causes from MyDrive conversation addressed
- [ ] Similar issues prevented in future executions
- [ ] Verification that frontmatter changes work correctly
- [ ] Confidence in agent discovery system restored

## Success Metrics

**Before Implementation**:
- Agent invocations: Sometimes skipped
- Visibility: Low (hard to tell if agents used)
- Reporting accuracy: Incorrect (false positives)
- Protocol compliance: ~60% (based on MyDrive example)

**After Implementation**:
- Agent invocations: 100% (enforced by validation)
- Visibility: High (explicit log table)
- Reporting accuracy: 100% (validated before generation)
- Protocol compliance: 100% (blocked if violated)

## Implementation Notes

### Priority Order

1. **Highest**: Pre-report validation (Solution C) - Prevents incorrect reports
2. **High**: Agent invocation log (Solution A) - Provides visibility
3. **Medium**: Enhanced warnings (Solution B) - Improves UX
4. **Low**: Low-complexity override (Solution D) - Nice-to-have optimization

### Rollout Strategy

1. **Phase 1**: Implement pre-report validation (immediate fix)
2. **Phase 2**: Add agent invocation log (visibility)
3. **Phase 3**: Enhance warnings and documentation
4. **Phase 4**: (Optional) Add low-complexity override

### Backward Compatibility

- Changes are additive (no breaking changes)
- Existing workflows continue to work
- New validation catches protocol violations
- Can be deployed immediately

## Related Issues

- **TASK-STND-773D**: Agent enhancement with boundary sections (completed)
- **Agent Discovery System**: Frontmatter metadata for agent selection
- **Early Development Issues**: "Terrible problems" with agents not being used

## Next Steps

1. **Review**: Validate proposed approach with team
2. **Implement**: Update `/task-work` command with new sections
3. **Test**: Run test cases on multiple stacks
4. **Document**: Update guides with new protocol
5. **Deploy**: Roll out to all Taskwright installations

## Questions for Review

1. Should we implement all 4 solutions (A+B+C+D) or just A+C?
2. Is low-complexity override (Solution D) needed, or should we always enforce agents?
3. Should the agent log be displayed inline or in a separate section?
4. How should we handle edge cases (workflow canceled, errors during agent execution)?
5. Should we add metrics tracking (% protocol compliance over time)?

---

**Note**: This task has complexity 6/10 because it involves:
- Command specification updates (2 files)
- Testing across multiple stacks (5 stacks)
- Multiple solution options to evaluate
- Documentation updates
- Quality gate enforcement logic

Estimated effort: 4-6 hours
