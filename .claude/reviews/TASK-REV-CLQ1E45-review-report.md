# Review Report: TASK-REV-CLQ1E45

## Executive Summary

**Status**: Root Cause Identified
**Review Mode**: debugging
**Review Depth**: comprehensive
**Completed**: 2025-12-14

The clarifying questions are not appearing in `/feature-plan` because **the CRITICAL EXECUTION INSTRUCTIONS section in `feature-plan.md` does not include the clarification steps**. Claude follows the explicit execution steps in the CRITICAL section, which jumps directly from task creation to task-review without invoking the clarification-questioner agent.

## Root Cause Analysis

### Primary Root Cause: CRITICAL EXECUTION INSTRUCTIONS Missing Clarification Steps

The `feature-plan.md` file contains two sections:

1. **Workflow Documentation** (lines 403-438, 592-659) - Describes Context A and Context B clarification with Task tool invocations
2. **CRITICAL EXECUTION INSTRUCTIONS** (lines 1040-1096) - The actual steps Claude follows

**The CRITICAL section does NOT mention clarification!**

Current CRITICAL section execution steps:
```markdown
1. ✅ **Parse feature description** from command arguments
2. ✅ **Execute `/task-create`** with task_type:review
3. ✅ **Capture task ID** from output
4. ✅ **Execute `/task-review`** with captured task ID    ← JUMPS DIRECTLY HERE
5. ✅ **Present decision checkpoint**
6. ✅ **Handle user decision**
```

**Missing step after #1:**
```markdown
1.5. ✅ **INVOKE clarification-questioner** with context_type: review_scope
     **WAIT** for agent completion
     **STORE** clarification context for review
```

**Missing step after #6 (before creating structure):**
```markdown
6.5. **IF** [I]mplement chosen AND subtask_count >= 2:
     **INVOKE clarification-questioner** with context_type: implementation_prefs
     **WAIT** for agent completion
     **USE** preferences in structure creation
```

### Secondary Issue: Workflow Documentation vs Execution Instructions Disconnect

The clarification workflow is well-documented in the "Step 2" and "Step 5c" sections (lines 403-438, 592-659), but Claude Code **only follows the CRITICAL EXECUTION INSTRUCTIONS section** at the bottom of the file.

This is a documentation architecture issue - the descriptive steps and the executable instructions are not aligned.

### Evidence from Test (feature-plan-test.md)

Claude's actual execution trace shows:
```
/feature-plan lets build out the application infrastructure
I'll help you plan the application infrastructure for this FastAPI project...
Task:Explore current project state
```

Claude Code:
- Immediately launched an `Explore` Task agent
- Searched for files with `find` and `ls`
- Created a review task directly
- Proceeded to analysis WITHOUT clarification

This shows Claude followed the CRITICAL EXECUTION INSTRUCTIONS section, which doesn't include clarification steps.

### Contributing Factors

| Factor | Impact | Severity |
|--------|--------|----------|
| CRITICAL section missing clarification steps | Clarification never invoked | **Critical** |
| Workflow docs vs execution instructions disconnect | Claude ignores descriptive steps | **Critical** |
| `clarification-questioner` agent exists | Not the issue - agent is installed | OK |
| Python modules installed | Not the issue - subagent pattern used | OK |

## Gap Analysis

### Current State vs Expected State

| Component | Expected | Actual | Gap |
|-----------|----------|--------|-----|
| `clarification-questioner` agent file | Exists | ✅ Present at `~/.agentecflow/agents/` | None |
| Context A in CRITICAL section | Step 1.5 invokes agent | ❌ Not mentioned | **Fix Required** |
| Context B in CRITICAL section | Step 6.5 invokes agent | ❌ Not mentioned | **Fix Required** |
| Example execution trace | Shows clarification | ❌ Omits clarification | **Fix Required** |

### What's Working vs What's Broken

**Working:**
- `clarification-questioner.md` agent is installed (verified in TASK-WC-009)
- Agent frontmatter and capabilities are correct
- Workflow documentation describes clarification correctly
- lib/clarification/ Python modules exist (though not needed for subagent pattern)

**Broken:**
- CRITICAL EXECUTION INSTRUCTIONS section (lines 1040-1096) skips clarification
- Example execution trace (lines 1080-1094) omits clarification
- Claude follows CRITICAL section, not workflow documentation

## Fix Recommendations

### Fix 1: Update CRITICAL EXECUTION INSTRUCTIONS (Primary Fix)

**File**: [installer/core/commands/feature-plan.md:1040-1057](installer/core/commands/feature-plan.md#L1040-L1057)

Replace the current execution steps with:

```markdown
### Execution Steps

1. ✅ **Parse feature description** from command arguments

2. ✅ **Context A: Review Scope Clarification** (IF --no-questions NOT set):
   **INVOKE** Task tool:
   ```
   subagent_type: "clarification-questioner"
   description: "Collect review scope clarifications"
   prompt: "Execute clarification for feature planning.
   CONTEXT TYPE: review_scope
   FEATURE: {feature_description}
   ..."
   ```
   **WAIT** for agent completion
   **STORE** context_a for review

3. ✅ **Execute `/task-create`** with:
   - Title: "Plan: {description}"
   - Flags: `task_type:review priority:high`

4. ✅ **Capture task ID** from output (regex: `TASK-[A-Z0-9-]+`)

5. ✅ **Execute `/task-review`** with captured task ID:
   - Flags: `--mode=decision --depth=standard`
   - Pass context_a to review

6. ✅ **Present decision checkpoint** (inherited from `/task-review`)

7. ✅ **Handle user decision**:
   - [A]ccept: Save review, show reference message
   - [R]evise: Re-run review with additional focus
   - [I]mplement: **→ Go to step 8**
   - [C]ancel: Move to cancelled state

8. ✅ **Context B: Implementation Preferences** (IF [I]mplement AND subtasks >= 2):
   **INVOKE** Task tool:
   ```
   subagent_type: "clarification-questioner"
   description: "Collect implementation preferences"
   prompt: "Execute clarification for implementation.
   CONTEXT TYPE: implementation_prefs
   ..."
   ```
   **WAIT** for agent completion
   **USE** context_b for subtask creation

9. ✅ **Create subfolder + subtasks + guide** using context_b preferences
```

### Fix 2: Update Example Execution Trace

**File**: [installer/core/commands/feature-plan.md:1078-1094](installer/core/commands/feature-plan.md#L1078-L1094)

Update to show clarification:

```markdown
### Example Execution Trace

\`\`\`
User: /feature-plan "implement dark mode"

Claude executes internally:
  1. Parse: feature_description = "implement dark mode"

  2. INVOKE Task(clarification-questioner, context_type=review_scope)
     → User answers: Focus=all, Priority=balanced
     → STORE context_a

  3. /task-create "Plan: implement dark mode" task_type:review priority:high
     → Captures: TASK-REV-A3F2

  4. /task-review TASK-REV-A3F2 --mode=decision --depth=standard
     → Runs analysis (uses context_a), presents options

  5. User chooses: I (Implement)

  6. INVOKE Task(clarification-questioner, context_type=implementation_prefs)
     → User answers: Approach=Option1, Parallel=yes, Testing=standard
     → USE context_b

  7. Creates structure (using context_b):
     - Feature folder
     - Subtasks with Conductor workspace names
     - Implementation guide

  8. Shows completion summary
\`\`\`
```

## Verification Steps

After implementing fixes:

1. **Re-copy feature-plan.md to installed location**:
   ```bash
   cp installer/core/commands/feature-plan.md ~/.agentecflow/commands/
   ```

2. **Test feature-plan with ambiguous input**:
   ```bash
   /feature-plan "lets build out the application infrastructure"
   ```

3. **Expected behavior - Context A questions appear**:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📋 REVIEW SCOPE CLARIFICATION
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Q1. Review Focus
       What aspects should this analysis focus on?

       [A]ll aspects - Comprehensive analysis
       [T]echnical only - Focus on technical feasibility
       ...

   Your choice [A/T/R/P/S]:
   ```

4. **Verify Context B questions at [I]mplement**:
   After answering Context A and choosing [I]mplement at decision checkpoint:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📋 IMPLEMENTATION PREFERENCES
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Q1. Approach Selection
       Which recommended approach should subtasks follow?
       ...
   ```

5. **Verify --no-questions flag works**:
   ```bash
   /feature-plan "add authentication" --no-questions
   # Expected: Skip directly to task creation and review, no questions
   ```

## Implementation Task

Based on this analysis, a single implementation task is needed:

### TASK-WC-014: Fix CRITICAL EXECUTION INSTRUCTIONS in feature-plan.md

**Priority**: Critical
**Complexity**: 3/10
**Effort**: 30 minutes

**What to do**:
1. Update lines 1040-1057 to include clarification steps
2. Add Context A invocation after step 1 (parse description)
3. Add Context B invocation after [I]mplement choice (before structure creation)
4. Update example execution trace (lines 1078-1094) to show clarification

**Why this is the only fix needed**:
- The clarification-questioner agent IS installed (verified)
- The Task tool invocation syntax IS correct in the workflow docs
- The ONLY issue is the CRITICAL section Claude follows doesn't include clarification

**Note**: TASK-WC-007 was marked complete but the fix was incomplete. The workflow documentation was updated but the CRITICAL section was not.

## Appendix: TASK-WC-007 Incomplete Fix Analysis

TASK-WC-007 completion summary states:
> Successfully integrated two clarification touchpoints into feature-plan.md:
> - Context A (review_scope): Added at Step 2, before /task-review execution
> - Context B (implementation_prefs): Added at Step 5c, after [I]mplement choice

**What was done**: Added clarification to workflow documentation (Steps 2 and 5c)

**What was missed**: Did NOT update the CRITICAL EXECUTION INSTRUCTIONS section that Claude actually follows

**Root cause of incomplete fix**: The task description said to add steps to the workflow documentation, but didn't specify that the CRITICAL section also needs updating. The CRITICAL section is the authoritative execution guide that Claude follows.

## Analysis of task-work.md and task-review.md

Per user request, I analyzed whether `task-work.md` and `task-review.md` have the same issue.

### task-work.md - ✅ Correctly Structured

- **3,951 lines** in total
- Phase 1.6 (Clarifying Questions) with `clarification-questioner` invocation is **directly embedded in the phase workflow** (lines 1394-1463)
- The "CRITICAL REMINDER" at line 3932 is about using Task tool, not a separate execution guide
- Claude follows the phase workflow directly, which includes clarification

**No fix needed** - clarification is correctly integrated.

### task-review.md - ✅ Correctly Structured

- **1,449 lines** in total
- Phase 1 (Load Review Context) with `clarification-questioner` invocation is **directly in the phase workflow** (lines 552-588)
- No separate "CRITICAL EXECUTION INSTRUCTIONS" section at the end
- Claude follows the phase workflow directly, which includes clarification

**No fix needed** - clarification is correctly integrated.

### feature-plan.md - ❌ Has Architecture Issue

- **1,096 lines** in source, but only **678 lines** in installed version
- Workflow documentation has clarification (Steps 2 and 5c)
- BUT has a separate "CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE" section (lines 1038-1096)
- The CRITICAL section does NOT include clarification steps
- Claude follows the CRITICAL section, ignoring the workflow documentation

**Issue**: The document has a dual structure that creates ambiguity:
1. Workflow docs describe what "should" happen
2. CRITICAL section describes what Claude "must" do
3. These are not aligned

## Root Cause of Architecture Difference

| Command | Structure | Clarification Location |
|---------|-----------|----------------------|
| `task-work.md` | Single phase workflow | Embedded in Phase 1.6 ✅ |
| `task-review.md` | Single phase workflow | Embedded in Phase 1 ✅ |
| `feature-plan.md` | Dual structure (workflow + CRITICAL) | Only in workflow, missing from CRITICAL ❌ |

The `feature-plan.md` was designed as a "coordination command" that orchestrates other commands. This led to the dual structure where:
- Workflow docs explain the full process
- CRITICAL section gives minimal execution steps

TASK-WC-007 only updated the workflow docs, not the CRITICAL section.

## Implementation Task Created

**TASK-WC-014**: Fix CRITICAL EXECUTION INSTRUCTIONS in feature-plan.md

Location: `tasks/backlog/unified-clarification-subagent/TASK-WC-014-fix-feature-plan-critical-section.md`

**Summary**:
- Update execution steps (add Context A after step 1, Context B after [I]mplement)
- Update example execution trace to show clarification
- Re-copy to installed location after modification

## Decision

**Recommendation**: Implement TASK-WC-014 (documentation fix only).

- `task-work.md` - No changes needed ✅
- `task-review.md` - No changes needed ✅
- `feature-plan.md` - Needs CRITICAL section update via TASK-WC-014

This is the only fix needed. The subagent pattern infrastructure is correctly in place.
