---
id: TASK-REV-CLQ2
title: Review clarifying questions integration for /feature-plan command
status: review_complete
task_type: review
review_mode: technical-debt
review_depth: standard
created: 2025-12-13T20:30:00Z
updated: 2025-12-13T21:15:00Z
priority: high
tags: [clarification, feature-plan, review, integration]
complexity: 5
decision_required: true
decision: implement
review_results:
  verdict: "dead_code_confirmed"
  dead_code_lines: 8740
  sunk_cost_hours: "40-60"
  completed_tasks: 17
  root_cause: "markdown_python_execution_gap"
  recommendation: "Option A - Wire up Python orchestrators (4-8h)"
  report_path: ".claude/reviews/TASK-REV-CLQ2-review-report.md"
implementation_tasks:
  feature_folder: "tasks/backlog/wire-up-clarification/"
  tasks:
    - TASK-WC-001
    - TASK-WC-002
    - TASK-WC-003
    - TASK-WC-004
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review clarifying questions integration for /feature-plan command

## Description

Review the clarifying questions integration for the `/feature-plan` command to determine:

1. Why clarifying questions were not displayed during a test run of `/feature-plan` with an ambiguous input
2. Whether the implementation from TASK-REV-0614 recommendations was completed correctly
3. If questions are working but correctly gated (skipped because not needed)
4. Whether the markdown-instruction approach can properly invoke Python orchestrators

## Background

### User Test Case

User ran: `/feature-plan lets set up the application infrastructure`

**Expected behavior** (per documentation):
- Context A clarification questions should be asked before review:
  - "What technology stack are you using?"
  - "What type of application?" (web, API, CLI, etc.)
  - "What trade-off priority?" (speed, quality, cost)

**Actual behavior** (observed):
- Task TASK-REV-A4B5 created successfully
- System assumed FastAPI + Python (without asking)
- Proceeded directly to technical analysis with 5 options
- No clarification questions were displayed

### Previous Review

TASK-REV-0614 identified that clarification modules were:
- ✅ Designed and documented
- ✅ Unit tests passing
- ❌ Not integrated into orchestrators

**Recommendations implemented** (per review report):
- REC-001: Integrate clarification into task_review_orchestrator.py
- REC-002: Add explicit feature-plan orchestrator
- REC-003: Update integration tests
- REC-004: Add smoke test

Multiple TASK-CLQ-* tasks were completed implementing these recommendations.

### Key Question

The Python orchestrators (`feature_plan_orchestrator.py` and `task_review_orchestrator.py`) now contain clarification integration code. However:

1. **Is the Python orchestrator being invoked?** The `/feature-plan` command is a markdown-only specification - Claude interprets the markdown rather than calling `python3 feature_plan_orchestrator.py`

2. **Is complexity gating working correctly?** The clarification system uses complexity-based gating:
   - Complexity 1-2: Skip questions (trivial)
   - Complexity 3-4: Quick questions (15s timeout)
   - Complexity 5+: Full questions (blocking)

   The test input was ambiguous ("lets set up the application infrastructure") which should have resulted in medium-high complexity (5+), triggering full clarification.

3. **Did the output indicate clarification was skipped?** If clarification ran but was skipped due to complexity gating or defaults, there should be output like:
   - "Clarification Mode: SKIP"
   - "Using defaults without prompting"

   The test output shows no such messages.

## Evidence Files

1. Test output: `docs/reviews/clarifying-questions/feature-plan-test.md`
2. Previous review: `.claude/reviews/TASK-REV-0614-review-report.md`
3. feature_plan_orchestrator.py: `installer/core/commands/lib/feature_plan_orchestrator.py`
4. task_review_orchestrator.py: `installer/core/commands/lib/task_review_orchestrator.py`
5. Clarification module: `installer/core/commands/lib/clarification/`

## Possible Root Causes

### Hypothesis A: Markdown vs Python Execution Gap

The `/feature-plan` command is defined as a markdown specification (`installer/core/commands/feature-plan.md`). When Claude executes this:

1. Claude reads the markdown file
2. Claude follows the instructions manually (create task, run review, etc.)
3. Claude does NOT call `python3 feature_plan_orchestrator.py`

This means the Python clarification code is never invoked - Claude is manually executing a "soft" version of the workflow based on markdown instructions, not the hardcoded Python orchestrator.

### Hypothesis B: Clarification Module Import Failure

The orchestrators have try/except blocks for clarification imports:
```python
try:
    from clarification import ...
    CLARIFICATION_AVAILABLE = True
except ImportError:
    CLARIFICATION_AVAILABLE = False
```

If the import fails silently, `CLARIFICATION_AVAILABLE` would be False and clarification would be skipped without error messages.

### Hypothesis C: Complexity Gating Too Aggressive

The `should_clarify()` function may be incorrectly calculating complexity for `/feature-plan` inputs, resulting in SKIP mode even for ambiguous descriptions.

### Hypothesis D: Questions Not Needed

The output was high-quality (FastAPI infrastructure with 5 technical options). Perhaps for this type of decision-mode review, the clarification questions wouldn't have changed the outcome significantly.

## Critical Question: Is the Clarification Code Dead Code?

**This is the primary question this review must answer.**

A significant amount of work was invested in the clarifying questions feature:
- Original design and documentation
- TASK-REV-0614 review identifying the integration gap
- Multiple TASK-CLQ-* implementation tasks (CLQ-001 through CLQ-012)
- TASK-CLQ-FIX-001 through TASK-CLQ-FIX-006 fix tasks
- Unit tests, integration tests, smoke tests

**The concern**: If Claude Code executes slash commands by reading markdown files and interpreting instructions (rather than invoking Python orchestrators), then ALL of the clarification Python code may be **dead code that will never execute**.

### What Must Be Determined

1. **Is the Python clarification code ever invoked?**
   - Under what circumstances (if any) does `feature_plan_orchestrator.py` get called?
   - Under what circumstances (if any) does `task_review_orchestrator.py` get called?
   - Or are these files effectively dead code?

2. **How do Claude Code slash commands actually work?**
   - Does Claude read `.md` files as instructions and "role-play" the workflow?
   - Or is there a mechanism to invoke Python scripts from slash commands?
   - What's the execution model for commands in `installer/core/commands/`?

3. **Was all the clarification implementation work wasted?**
   - If Python orchestrators are never called, the answer is YES
   - If there's a way to wire them up, the answer is "not yet, but fixable"
   - Be honest about this assessment

4. **What would it take to make clarification actually work?**
   - If the code is dead, what changes are needed?
   - Is it a simple fix (add Python invocation) or fundamental architecture change?
   - Estimate effort to make clarification functional

### Why This Matters

The purpose of clarifying questions was to **prevent Claude from making assumptions** and implementing the wrong thing. In the test case:

- Input: "lets set up the application infrastructure" (ambiguous)
- Claude assumed: FastAPI + Python stack
- Should have asked: "What technology stack?", "What type of application?"

If clarification never works, Claude will continue making assumptions on ambiguous inputs, leading to:
- Wasted implementation time on wrong approach
- User frustration at having to correct/redo work
- Reduced trust in the GuardKit workflow

## Review Scope

Analyze:
1. **Execution model**: How are slash commands in `installer/core/commands/*.md` actually executed?
2. **Python invocation**: Is there ANY code path that calls the Python orchestrators?
3. **Dead code assessment**: Inventory all clarification-related code and classify as reachable/unreachable
4. **Sunk cost analysis**: Quantify the work invested in clarification feature
5. **Path forward**: What's needed to make clarification functional (if anything)?
6. **Honest assessment**: Was the implementation work wasted? Be direct.

## Acceptance Criteria

- [ ] **Dead code determination**: Clear YES/NO answer on whether clarification Python code is ever executed
- [ ] **Execution model documented**: How slash commands actually work in Claude Code
- [ ] **Inventory of affected code**: List all files/functions that are dead code (if applicable)
- [ ] **Sunk cost quantified**: Estimate of hours/effort invested in clarification feature
- [ ] **Root cause**: Why was dead code written? (miscommunication, incorrect assumptions, etc.)
- [ ] **Path forward recommendation**: One of:
  - A) Delete dead code, update docs to reflect reality
  - B) Wire up Python orchestrators to make code functional (with effort estimate)
  - C) Redesign approach (if fundamental architecture issue)
- [ ] **Honest assessment**: Direct answer to "was the implementation work wasted?"

## Review Mode

Execute with:
```bash
/task-review TASK-REV-CLQ2 --mode=technical-debt --depth=standard
```

## Related Tasks

- TASK-REV-0614: Original clarifying questions regression review
- TASK-CLQ-FIX-001 through TASK-CLQ-FIX-006: Implementation tasks
- TASK-CLQ-008: task-review integration task

## Implementation Notes

After review completion, choose at decision checkpoint:
- [A]ccept: Clarification is working correctly or acceptably
- [R]evise: Need deeper analysis of specific component
- [I]mplement: Create implementation task(s) to fix the gap
- [C]ancel: Discard review
