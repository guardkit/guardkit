---
id: TASK-REV-CLQ3
title: Review task-work clarification architecture - subagent vs orchestrator
status: completed
task_type: review
review_mode: decision
created: 2025-12-13T21:45:00Z
updated: 2025-12-14T00:00:00Z
completed: 2025-12-14T00:00:00Z
completed_location: tasks/completed/TASK-REV-CLQ3/
priority: high
tags: [clarification, task-work, architecture, decision, subagent, orchestrator]
complexity: 6
decision_required: true
related_tasks:
  - TASK-REV-CLQ2
  - TASK-WC-001
  - TASK-WC-002
  - TASK-WC-003
  - TASK-WC-004
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  recommendation: unified_subagent
  confidence: high
  score: 4.55/5
  revision: 2
  report_path: .claude/reviews/TASK-REV-CLQ3-review-report.md
  completed_at: 2025-12-13T22:45:00Z
  key_findings:
    - "Unified subagent pattern for ALL commands (task-work, feature-plan, task-review)"
    - "Eliminates handoff complexity - agent returns context, Claude continues"
    - "Unified subagent scores 4.55/5 vs orchestrator 2.55/5"
    - "Estimated effort: 6-8 hours total"
    - "Supersedes TASK-WC-001, WC-002, WC-003 (orchestrator approach)"
  implementation_tasks:
    - TASK-WC-005  # Create clarification-questioner agent
    - TASK-WC-006  # Update task-work.md
    - TASK-WC-007  # Update feature-plan.md
    - TASK-WC-008  # Update task-review.md
    - TASK-WC-009  # Update installer
    - TASK-WC-010  # Update guardkit init
    - TASK-WC-011  # Update documentation
    - TASK-WC-012  # Integration smoke tests
---

# Task: Review task-work clarification architecture - subagent vs orchestrator

## Description

Evaluate the best approach to wire up clarifying questions into the `/task-work` command, choosing between:

1. **Orchestrator Pattern**: Python orchestrator invoked at command start (consistent with `/feature-plan` and `/task-review`)
2. **Subagent Pattern**: AI agent invoked via Task tool (consistent with `complexity-evaluator` in `/task-work`)

This review also explores whether clarification should occur earlier in the workflow (e.g., before Phase 2 planning).

## Background

### Current Architecture Discovery (from TASK-REV-CLQ2)

The technical debt review revealed:

1. **Complexity evaluation works** in `/task-work` because it uses a **subagent pattern**:
   - `task-work.md` invokes `Task tool` with `subagent_type: "complexity-evaluator"`
   - The agent spawns, has Python tools, and executes code
   - Returns structured complexity score to the workflow

2. **Clarification doesn't work** in any command because:
   - `/feature-plan` and `/task-review` have Python orchestrators but they're never invoked
   - `/task-work` has no orchestrator AND no subagent for clarification
   - The "Integration Code" in `task-work.md` is just documentation, not executable

3. **Wire-up tasks created** (TASK-WC-001 through TASK-WC-004):
   - These wire up `/feature-plan` and `/task-review` using the **orchestrator pattern**
   - `/task-work` still needs a solution

### The Two Approaches

#### Option A: Orchestrator Pattern (like /feature-plan, /task-review)

**How it works**:
1. Create `task_work_orchestrator.py`
2. Add symlink during installation
3. Update `task-work.md` to invoke: `python3 ~/.agentecflow/bin/task-work-orchestrator`
4. Python handles clarification, then returns control to Claude for remaining phases

**Pros**:
- Consistent with `/feature-plan` and `/task-review` clarification
- Clarification code is centralized in Python
- Easier to test (unit tests for Python code)
- Full control over question flow, timeouts, persistence

**Cons**:
- Inconsistent with rest of `/task-work` phases (which use subagents)
- Requires orchestrator to hand back to Claude for Phases 2-5.5
- Complex handoff between Python orchestrator and Claude workflow
- Different execution model than complexity-evaluator

#### Option B: Subagent Pattern (like complexity-evaluator)

**How it works**:
1. Create `clarification-questioner.md` agent
2. Invoke via Task tool: `subagent_type: "clarification-questioner"`
3. Agent displays questions, collects responses, returns ClarificationContext
4. Claude continues with remaining phases using the context

**Pros**:
- Consistent with `/task-work` architecture (complexity-evaluator, architectural-reviewer, etc.)
- Simpler integration - just add another agent invocation
- No Python orchestrator complexity
- Agent can use Python tools for detection/generation

**Cons**:
- Inconsistent with `/feature-plan` and `/task-review` (which will use orchestrators)
- Less control over interactive terminal flow
- Agent must handle timeout logic and user input
- May be harder to test

### Timing Question

**Current Phase 1.6 location**: After context loading (Phase 1.5), before planning (Phase 2)

**Alternative: Earlier clarification (Phase 0.5 or 1.5)**:

Should clarification happen even earlier? Considerations:
- **Before file discovery**: Ask about scope before analyzing codebase
- **After minimal context**: Ask after reading task file but before full analysis
- **Current position**: Ask after context loading, informed by task complexity

**Impact on complexity gating**:
- If clarification is before complexity calculation, can't gate on complexity
- If after, complexity can inform which questions to ask

## Review Questions

### Primary Decision: Architecture Pattern

1. **Which pattern is more maintainable long-term?**
   - Orchestrator: More Python code, but centralized clarification logic
   - Subagent: More markdown/agent complexity, but consistent with workflow

2. **Which pattern has better UX?**
   - Orchestrator: Full terminal control, better timeout handling
   - Subagent: Must work within Task tool constraints

3. **Which pattern is easier to test?**
   - Orchestrator: Python unit tests
   - Subagent: More integration-test dependent

4. **Consistency considerations**:
   - With other clarification commands (orchestrator)
   - With other `/task-work` phases (subagent)
   - Which consistency is more important?

### Secondary Decision: Timing

1. **Should clarification occur before complexity evaluation?**
   - Pro: User preferences inform complexity assessment
   - Con: Can't gate clarification on complexity

2. **Should clarification occur after complexity evaluation?**
   - Pro: Complexity can determine if clarification is needed
   - Con: May be "too late" - user already committed to approach

3. **Should there be TWO clarification points?**
   - Early: Scope clarification (before complexity)
   - Later: Implementation preferences (after planning, like /feature-plan Context B)

### Evaluation Criteria

Score each option (1-5) on:
- **Consistency**: How well does it fit with existing patterns?
- **Maintainability**: How easy is it to maintain and extend?
- **Testability**: How easy is it to write tests?
- **UX Quality**: How good is the user experience?
- **Implementation Effort**: How much work to implement?

## Evidence Files

1. TASK-REV-CLQ2 review report: `.claude/reviews/TASK-REV-CLQ2-review-report.md`
2. complexity-evaluator agent: `installer/core/agents/complexity-evaluator.md`
3. task-work command: `installer/core/commands/task-work.md`
4. Clarification module: `installer/core/commands/lib/clarification/`
5. Wire-up tasks: `tasks/backlog/wire-up-clarification/`

## Hypotheses

### Hypothesis A: Subagent is Better for task-work

**Rationale**: The `/task-work` command already uses subagents for:
- complexity-evaluator (Phase 2.7)
- architectural-reviewer (Phase 2.5B)
- test-orchestrator (Phase 4)
- code-reviewer (Phase 5)

Adding a `clarification-questioner` subagent maintains consistency within the command, even if it differs from `/feature-plan` and `/task-review`.

### Hypothesis B: Orchestrator is Better for Consistency

**Rationale**: The clarification feature should work identically across all commands. Using orchestrators for `/feature-plan` and `/task-review` but subagents for `/task-work` creates inconsistent behavior and maintenance burden.

### Hypothesis C: Hybrid Approach

**Rationale**: Use the clarification Python module within a subagent. The `clarification-questioner` agent can import and use `lib/clarification/*` code, getting the best of both worlds:
- Consistent with `/task-work` agent architecture
- Reuses existing Python clarification logic
- Tests can cover both agent behavior and Python code

## Acceptance Criteria

- [ ] Clear recommendation on architecture pattern (orchestrator vs subagent)
- [ ] Clear recommendation on timing (when in workflow to ask questions)
- [ ] Pros/cons matrix for both approaches
- [ ] Decision rationale documented
- [ ] Implementation approach outlined for chosen pattern
- [ ] Effort estimate for implementation

## Review Mode

Execute with:
```bash
/task-review TASK-REV-CLQ3 --mode=decision --depth=standard
```

## Implementation Notes

After review completion, choose at decision checkpoint:
- [A]ccept: Accept findings without implementation
- [R]evise: Need deeper analysis
- [I]mplement: Create implementation task(s) based on recommendation
- [C]ancel: Discard review
