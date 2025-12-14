# Decision Review Report: TASK-REV-CLQ3

## Clarification Architecture: Unified Subagent Pattern for All Commands

**Review Mode**: decision
**Review Depth**: standard
**Date**: 2025-12-13
**Reviewer**: Automated Decision Analysis
**Revision**: 2 (Updated based on user feedback)

---

## Executive Summary

**REVISED Recommendation: Unified Subagent Pattern for ALL Commands**

After further analysis prompted by user feedback, the recommendation is expanded: **use the subagent pattern for `/task-work`, `/feature-plan`, AND `/task-review`** - eliminating the orchestrator pattern entirely.

**Key Rationale**:
1. **Eliminates handoff complexity** - Orchestrators must hand back to Claude for remaining workflow; subagents return context naturally
2. **Unified architecture** - One pattern across all commands is easier to maintain
3. **Simpler implementation** - One agent handles all clarification contexts (A, B, C)
4. **Reuses existing code** - Agent imports `lib/clarification/*` via Python tools
5. **No symlinks needed** - Eliminates TASK-WC-003 (installer symlinks)

**Estimated Effort**: 6-8 hours total (vs 12-16 hours for mixed orchestrator/subagent approach)

---

## Revised Analysis: Why Unified Subagent?

### The Handoff Problem with Orchestrators

The original TASK-WC-001 through TASK-WC-003 tasks proposed:
1. `/feature-plan.md` calls `python3 feature-plan-orchestrator`
2. Orchestrator handles clarification
3. Orchestrator must then call `/task-create` and `/task-review`... **OR replicate their logic**

This creates complexity:
```
User → /feature-plan (markdown) → Python orchestrator → ???
                                         ↓
                      Either: Call Claude commands (complex IPC)
                      Or: Replicate command logic in Python (duplication)
```

### How Commands Actually Work Today

| Command | Current Pattern | Uses Subagents? | Python Orchestrator Status |
|---------|----------------|-----------------|---------------------------|
| `/task-work` | Subagent-based | Yes (6+ agents) | None exists |
| `/feature-plan` | Manual coordination | No | Exists but never called |
| `/task-review` | Manual coordination | No | Exists but never called |

**Key Discovery**: `/feature-plan` and `/task-review` are "coordination commands" - they describe a workflow for Claude to follow manually (call `/task-create`, then `/task-review`, etc.). They don't invoke Python directly.

### Unified Subagent Solution

Instead of mixing patterns, use a single `clarification-questioner` agent that:
1. Handles ALL clarification contexts (review_scope, implementation_prefs, implementation_planning)
2. Is invoked at the appropriate point in each command's workflow
3. Returns `ClarificationContext` to Claude for use in subsequent steps

```
/feature-plan.md:
  Step 1: Parse feature description
  Step 2: INVOKE clarification-questioner (Context A: review scope)
  Step 3: Execute /task-create
  Step 4: Execute /task-review (uses Context A)
  Step 5: At [I]mplement: INVOKE clarification-questioner (Context B: impl prefs)
  Step 6: Create feature structure (uses Context B)

/task-review.md:
  Step 1: Load task
  Step 2: INVOKE clarification-questioner (Context A: review scope)
  Step 3: Execute review analysis
  Step 4: Generate report
  Step 5: Decision checkpoint

/task-work.md:
  Phase 1.5: Load context
  Phase 1.6: INVOKE clarification-questioner (Context C: impl planning)
  Phase 2: Implementation planning (uses Context C)
  ...remaining phases...
```

---

## Decision Matrix (Revised)

| Criterion | Weight | Orchestrator Pattern | Unified Subagent |
|-----------|--------|---------------------|------------------|
| **Cross-Command Consistency** | 25% | 2/5 (mixed patterns) | 5/5 (one pattern) |
| **Implementation Effort** | 20% | 2/5 (12-16 hours) | 4/5 (6-8 hours) |
| **Handoff Complexity** | 20% | 2/5 (Python→Claude handoff) | 5/5 (no handoff) |
| **Maintainability** | 15% | 2/5 (two patterns) | 5/5 (one pattern) |
| **Code Reuse** | 10% | 4/5 (direct Python) | 4/5 (via Python tools) |
| **Testability** | 10% | 4/5 (unit tests) | 3/5 (integration tests) |
| **Weighted Total** | 100% | **2.55/5** | **4.55/5** |

**Winner: Unified Subagent Pattern**

---

## Implementation Tasks

### Overview

The unified subagent approach requires these tasks:

| Task ID | Description | Priority | Effort | Wave |
|---------|-------------|----------|--------|------|
| TASK-WC-005 | Create clarification-questioner agent | High | 2-3h | 1 |
| TASK-WC-006 | Update task-work.md with subagent invocation | High | 1-2h | 2 |
| TASK-WC-007 | Update feature-plan.md with subagent invocation | High | 1-2h | 2 |
| TASK-WC-008 | Update task-review.md with subagent invocation | High | 1-2h | 2 |
| TASK-WC-009 | Update installer to copy new agent | Medium | 0.5h | 3 |
| TASK-WC-010 | Update guardkit init to include agent | Medium | 0.5h | 3 |
| TASK-WC-011 | Update CLAUDE.md documentation | Medium | 1h | 3 |
| TASK-WC-012 | Add integration smoke tests | Medium | 1h | 4 |

**Supersedes**: TASK-WC-001, TASK-WC-002, TASK-WC-003 (orchestrator-based approach)
**Retains**: TASK-WC-004 concept (smoke test) → becomes TASK-WC-012

### Task Details

#### TASK-WC-005: Create clarification-questioner Agent

**Description**: Create a unified clarification agent that handles all three contexts.

**Location**: `installer/core/agents/clarification-questioner.md`

**Agent Structure**:
```markdown
---
name: clarification-questioner
description: Unified clarification agent - Collects user preferences before analysis or implementation
tools: Read, Write, Python
model: sonnet
stack: [cross-stack]
phase: orchestration
capabilities:
  - Review scope clarification (Context A)
  - Implementation preferences (Context B)
  - Implementation planning clarification (Context C)
  - Complexity-gated question selection
  - Timeout handling for quick mode
  - Default application
keywords: [clarification, questions, ambiguity, scope, planning, preferences]
priority: high
---

## Context Parameter

The agent accepts a `context_type` parameter:
- `review_scope` (Context A) - For /feature-plan and /task-review
- `implementation_prefs` (Context B) - For /feature-plan [I]mplement
- `implementation_planning` (Context C) - For /task-work Phase 1.6

## Quick Commands

### Execute Clarification
```python
import sys
sys.path.append('~/.agentecflow/lib')

from clarification import should_clarify, ClarificationMode
from clarification.generators import (
    generate_review_questions,      # Context A
    generate_implement_questions,   # Context B
    generate_planning_questions,    # Context C
)
from clarification.display import collect_responses, apply_defaults

# 1. Determine mode based on complexity and flags
mode = should_clarify(task, flags)
if mode == ClarificationMode.SKIP:
    return create_skip_context()

# 2. Generate context-specific questions
if context_type == "review_scope":
    questions = generate_review_questions(task, flags)
elif context_type == "implementation_prefs":
    questions = generate_implement_questions(review_findings)
else:  # implementation_planning
    questions = generate_planning_questions(task, context)

# 3. Collect responses or apply defaults
if mode == ClarificationMode.USE_DEFAULTS or flags.get('defaults'):
    return apply_defaults(questions)
else:
    return collect_responses(questions, mode)
```

## Decision Boundaries

### ALWAYS
- ✅ Check complexity gating before generating questions
- ✅ Respect --no-questions flag (skip entirely)
- ✅ Respect --with-questions flag (force execution)
- ✅ Apply --defaults flag (use defaults without prompting)
- ✅ Parse --answers flag for inline responses
- ✅ Return structured ClarificationContext
- ✅ Persist decisions to appropriate location

### NEVER
- ❌ Block indefinitely (use timeouts for quick mode)
- ❌ Skip when --with-questions flag set
- ❌ Execute when --no-questions flag set
- ❌ Ignore complexity gating rules

### ASK
- ⚠️ Multiple conflicting ambiguities detected
- ⚠️ Context type doesn't match expected workflow
```

**Acceptance Criteria**:
- [ ] Agent handles all three context types
- [ ] Imports and uses existing `lib/clarification/*` code
- [ ] Respects all clarification flags
- [ ] Returns properly structured ClarificationContext
- [ ] Includes ALWAYS/NEVER/ASK boundaries

---

#### TASK-WC-006: Update task-work.md

**Description**: Add Phase 1.6 subagent invocation to task-work command.

**Changes to** `installer/core/commands/task-work.md`:

```markdown
#### Phase 1.6: Clarifying Questions (Complexity-Gated)

**IF** --no-questions flag is set:
  Skip to Phase 2

**ELSE**:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect implementation planning clarifications for TASK-XXX"
prompt: "Execute clarification for TASK-{task_id}.

CONTEXT TYPE: implementation_planning

TASK CONTEXT:
  Title: {task_context.title}
  Description: {task_context.description}
  Complexity: {task_context.complexity}/10
  Acceptance Criteria: {task_context.acceptance_criteria}

FLAGS:
  --no-questions: {flags.no_questions}
  --with-questions: {flags.with_questions}
  --defaults: {flags.defaults}
  --answers: {flags.answers}

Return ClarificationContext with user decisions."
```

**WAIT** for agent completion

**STORE** clarification_context for Phase 2 prompt
```

**Acceptance Criteria**:
- [ ] Phase 1.6 invokes clarification-questioner agent
- [ ] Context type is `implementation_planning`
- [ ] All flags are passed to agent
- [ ] Clarification context stored for Phase 2

---

#### TASK-WC-007: Update feature-plan.md

**Description**: Add subagent invocations for Context A and Context B.

**Changes to** `installer/core/commands/feature-plan.md`:

**Context A (before /task-review)**:
```markdown
### Step 2: Review Scope Clarification

**IF** --no-questions flag is NOT set:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect review scope clarifications"
prompt: "Execute clarification for feature planning.

CONTEXT TYPE: review_scope

FEATURE: {feature_description}
COMPLEXITY: {estimated_complexity}/10

FLAGS: {clarification_flags}

Return ClarificationContext with review preferences."
```

**STORE** context_a for /task-review execution
```

**Context B (after [I]mplement choice)**:
```markdown
### Step 5: Implementation Preferences (if [I]mplement chosen)

**IF** --no-questions flag is NOT set AND subtask_count >= 2:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect implementation preferences"
prompt: "Execute clarification for implementation.

CONTEXT TYPE: implementation_prefs

REVIEW FINDINGS: {review_recommendations}
SUBTASK COUNT: {subtask_count}

FLAGS: {clarification_flags}

Return ClarificationContext with implementation preferences."
```

**USE** context_b for subtask creation
```

**Acceptance Criteria**:
- [ ] Context A invoked before review execution
- [ ] Context B invoked at [I]mplement decision
- [ ] Both contexts use clarification-questioner agent
- [ ] Contexts passed to subsequent workflow steps

---

#### TASK-WC-008: Update task-review.md

**Description**: Add subagent invocation for Context A (review scope).

**Changes to** `installer/core/commands/task-review.md`:

```markdown
### Phase 1: Load Review Context (with Optional Clarification)

**IF** --no-questions flag is NOT set:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect review scope clarifications for TASK-XXX"
prompt: "Execute clarification for task review.

CONTEXT TYPE: review_scope

TASK: {task_id}
TITLE: {task_title}
REVIEW MODE: {review_mode}
COMPLEXITY: {task_complexity}/10

FLAGS: {clarification_flags}

Return ClarificationContext with review preferences."
```

**USE** clarification_context in review analysis
```

**Acceptance Criteria**:
- [ ] Context A invoked at start of review
- [ ] Clarification context used in analysis
- [ ] Respects complexity gating rules

---

#### TASK-WC-009: Update Installer

**Description**: Ensure installer copies clarification-questioner agent.

**Changes to** `installer/scripts/install.sh`:

```bash
# Copy clarification-questioner agent
cp "$GUARDKIT_PATH/installer/core/agents/clarification-questioner.md" \
   "$HOME/.agentecflow/agents/"

echo "✓ Installed clarification-questioner agent"
```

**Acceptance Criteria**:
- [ ] Agent copied during installation
- [ ] Agent available at `~/.agentecflow/agents/clarification-questioner.md`
- [ ] Installation script idempotent

---

#### TASK-WC-010: Update guardkit init

**Description**: Ensure guardkit init includes clarification agent in project setup.

**Changes to** relevant init scripts:

```bash
# During guardkit init, ensure agent is linked/copied to project
# The agent should be available for the Task tool to invoke
```

**Note**: This may be a no-op if agents are loaded from `~/.agentecflow/agents/` globally. Verify and document.

**Acceptance Criteria**:
- [ ] Agent discoverable after guardkit init
- [ ] Works with template initialization
- [ ] Documentation updated if behavior differs per template

---

#### TASK-WC-011: Update Documentation

**Description**: Update CLAUDE.md and related docs to reflect unified subagent pattern.

**Files to Update**:
1. `CLAUDE.md` (root) - Clarifying Questions section
2. `.claude/CLAUDE.md` - Clarifying Questions section
3. `docs/workflows/clarification-workflow.md` (if exists)

**Key Changes**:
- Remove references to Python orchestrators for clarification
- Document unified subagent pattern
- Update command examples
- Explain context types (A, B, C)

**Acceptance Criteria**:
- [ ] CLAUDE.md reflects subagent pattern
- [ ] No references to orchestrator pattern for clarification
- [ ] Context types documented
- [ ] Examples updated

---

#### TASK-WC-012: Add Integration Smoke Tests

**Description**: Create smoke tests verifying clarification works across all commands.

**Test Cases**:
1. `/task-work TASK-XXX` with complexity 5+ → clarification questions appear
2. `/task-work TASK-XXX --no-questions` → clarification skipped
3. `/feature-plan "description"` → Context A questions appear
4. `/feature-plan` [I]mplement → Context B questions appear
5. `/task-review TASK-XXX` → Context A questions appear

**Location**: `tests/integration/clarification/`

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] Tests run in CI
- [ ] Failure modes documented

---

## Execution Strategy

### Wave 1 (No Dependencies)
- TASK-WC-005: Create clarification-questioner agent

### Wave 2 (Depends on Wave 1)
- TASK-WC-006: Update task-work.md
- TASK-WC-007: Update feature-plan.md
- TASK-WC-008: Update task-review.md

### Wave 3 (Depends on Wave 1)
- TASK-WC-009: Update installer
- TASK-WC-010: Update guardkit init
- TASK-WC-011: Update documentation

### Wave 4 (Depends on Waves 2 & 3)
- TASK-WC-012: Integration smoke tests

**Parallel Execution**:
- Wave 2 tasks can run in parallel (3 Conductor workspaces)
- Wave 3 tasks can run in parallel (3 Conductor workspaces)

---

## Superseded Tasks

The following tasks from TASK-REV-CLQ2 are **superseded** by this approach:

| Original Task | Original Purpose | Status |
|---------------|------------------|--------|
| TASK-WC-001 | Update feature-plan.md for orchestrator | **SUPERSEDED** by TASK-WC-007 |
| TASK-WC-002 | Update task-review.md for orchestrator | **SUPERSEDED** by TASK-WC-008 |
| TASK-WC-003 | Add orchestrator symlinks | **DELETED** (not needed) |
| TASK-WC-004 | Smoke test | **RENAMED** to TASK-WC-012 |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Agent Python tool limitations | Medium | Medium | Test thoroughly; fall back to defaults on error |
| Terminal I/O in agent context | Medium | Medium | Use existing complexity-evaluator as reference |
| Context type confusion | Low | Low | Clear documentation and validation |
| Installation path issues | Low | Medium | Test on fresh install |

---

## Effort Summary

| Category | Effort |
|----------|--------|
| Agent creation (TASK-WC-005) | 2-3 hours |
| Command updates (WC-006, 007, 008) | 3-4 hours |
| Infrastructure (WC-009, 010) | 1 hour |
| Documentation (WC-011) | 1 hour |
| Testing (WC-012) | 1 hour |
| **Total** | **6-8 hours** |

---

## Conclusion

The unified subagent pattern provides:
- **Simpler architecture** - One pattern for all commands
- **No handoff complexity** - Agent returns context, Claude continues
- **Lower effort** - 6-8 hours vs 12-16 hours
- **Better maintainability** - Single clarification agent to maintain

The orchestrator pattern is **not recommended** because:
- Creates handoff complexity between Python and Claude
- Requires different patterns for different commands
- Needs symlink management
- More total code to maintain

**Recommended Action**: Create implementation tasks TASK-WC-005 through TASK-WC-012 as specified above.
