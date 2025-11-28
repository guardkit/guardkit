---
id: TASK-BDD-002
title: Create BDD workflow documentation for agentic systems
status: backlog
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T15:27:39.493246+00:00
priority: high
tags: [bdd-restoration, documentation, wave1]
complexity: 2
task_type: documentation
estimated_effort: 45 minutes
wave: 1
parallel: true
implementation_method: claude-code-direct
parent_epic: bdd-restoration
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Create BDD workflow documentation for agentic systems

## Context

BDD mode is being restored specifically for implementing formal agentic orchestration systems (LangGraph). We need comprehensive documentation explaining when and how to use BDD mode.

**Parent Epic**: BDD Mode Restoration
**Wave**: 1 (Foundation - runs in parallel with TASK-BDD-001 and TASK-BDD-006)
**Implementation**: Use Claude Code directly (documentation task)

## Description

Create user-facing documentation that:
1. Explains when to use BDD mode (agentic systems, NOT general features)
2. Provides step-by-step workflow guidance
3. Includes LangGraph case study with real examples
4. Documents error scenarios and troubleshooting
5. Links to RequireKit installation

This is the primary user guide for BDD mode - it must be comprehensive and beginner-friendly.

## Acceptance Criteria

### Primary Deliverable

**File**: `docs/guides/bdd-workflow-for-agentic-systems.md`

**Required Sections**:

#### 1. When to Use BDD in TaskWright

**Content**:
- Clear decision criteria: agentic systems, safety-critical, formal specs
- Explicit anti-patterns: NOT for CRUD, UI components, bug fixes
- Comparison table: BDD vs TDD vs Standard modes

**Example**:
```markdown
## When to Use BDD Mode

### ✅ USE BDD For:
- **Agentic orchestration systems** - LangGraph state machines, multi-agent coordination
- **Safety-critical workflows** - Quality gates, approval checkpoints, auth/security
- **Formal behavior specifications** - Compliance, audit trails, regulatory requirements
- **Complex state transitions** - FSMs, workflow engines, process orchestrators

### ❌ DON'T USE BDD For:
- General CRUD features
- Simple UI components
- Bug fixes and refactoring
- Prototyping and exploration
- Straightforward implementations

### Decision Matrix
| Feature Type | Mode | Reason |
|--------------|------|--------|
| LangGraph state routing | BDD | Precise behavior specs needed |
| Add user table | Standard | Simple CRUD |
| Authentication logic | BDD | Safety-critical |
| Fix typo in message | Standard | Trivial change |
```

#### 2. Prerequisites

**Content**:
- RequireKit + TaskWright installation
- EARS notation understanding (link to RequireKit docs)
- Gherkin basics (link to tutorial)
- When formal requirements are worth the overhead

#### 3. LangGraph Case Study

**Content**: Complete example from your research docs

```markdown
## Case Study: LangGraph Orchestration Layer

### The Challenge
Building a LangGraph-based agent orchestrator for TaskWright with:
- 7-phase workflow (Phase 2 → 2.5B → 2.7 → 2.8 → 3 → 4 → 5)
- Complexity-based routing (AUTO_PROCEED vs QUICK_OPTIONAL vs FULL_REQUIRED)
- Human checkpoints with interrupt() semantics
- Test retry loops with max attempts

### Why BDD?
State machines require **precise behavior specifications**:
- Routing conditions must be exact
- Checkpoint semantics must be unambiguous
- Edge cases must be explicitly handled
- Traceability from requirements to code is critical

### EARS Requirement

```
REQ-ORCH-001: Phase 2.8 Complexity Routing

WHEN task complexity_score ≥ 7, the system SHALL invoke FULL_REQUIRED checkpoint.
WHEN task complexity_score is 4-6, the system SHALL invoke QUICK_OPTIONAL checkpoint.
WHEN task complexity_score is 1-3, the system SHALL proceed automatically.
```

### Gherkin Scenario

```gherkin
Feature: Complexity-Based Routing
  As a TaskWright orchestrator
  I want to route tasks based on complexity scores
  So that high-risk changes get mandatory human review

  @critical @checkpoint
  Scenario: High complexity triggers mandatory review
    Given a task with complexity score 8
    When the workflow reaches Phase 2.8
    Then the system should invoke FULL_REQUIRED checkpoint
    And the workflow should interrupt with full plan display
    And the options should be ["approve", "revise", "abort"]
    And auto-proceed should be disabled

  @quick-review @checkpoint
  Scenario: Medium complexity offers optional review
    Given a task with complexity score 5
    When the workflow reaches Phase 2.8
    Then the system should invoke QUICK_OPTIONAL checkpoint
    And the workflow should show a summary
    And the timeout should default to approve after 30 seconds

  @auto-proceed
  Scenario: Low complexity proceeds automatically
    Given a task with complexity score 2
    When the workflow reaches Phase 2.8
    Then the system should proceed to Phase 3 automatically
    And no checkpoint should be displayed
```

### Implementation (Python + LangGraph)

```python
def complexity_router(state: TaskWrightState) -> Literal["auto_proceed", "quick_review", "full_review"]:
    """Route based on complexity score to appropriate approval path."""
    score = state["complexity_score"]

    if score >= 7:
        return "full_review"
    elif score >= 4:
        return "quick_review"
    else:
        return "auto_proceed"
```

### BDD Tests (pytest-bdd)

```python
@scenario('complexity_routing.feature', 'High complexity triggers mandatory review')
def test_high_complexity_mandatory_review():
    pass

@given('a task with complexity score 8')
def task_high_complexity(context):
    context.state = TaskWrightState(complexity_score=8)

@when('the workflow reaches Phase 2.8')
def reach_phase_28(context):
    context.result = complexity_router(context.state)

@then('the system should invoke FULL_REQUIRED checkpoint')
def verify_full_required(context):
    assert context.result == "full_review"
```

### Benefits Realized
- ✅ State transition correctness (all routes tested)
- ✅ Checkpoint behavior validated (interrupt semantics clear)
- ✅ Approval logic verified (decision routing correct)
- ✅ Traceability (REQ → Gherkin → Code → Test)
```

#### 4. Complete Workflow

**Content**: Step-by-step guide from epic creation to implementation

```markdown
## BDD Workflow: End-to-End

### Step 1: Create Epic in RequireKit

```bash
cd ~/Projects/require-kit
/epic-create "LangGraph Orchestration Layer"
```

### Step 2: Formalize Requirements (EARS)

```bash
/req-create "Phase 2.8 complexity routing"
/formalize-ears REQ-ORCH-001

# Edit requirement using EARS notation:
# WHEN [trigger], system SHALL [response]
```

### Step 3: Generate BDD Scenarios

```bash
/generate-bdd REQ-ORCH-001

# RequireKit converts EARS → Gherkin
# Output: docs/bdd/complexity-routing.feature
```

### Step 4: Create Implementation Task

```bash
cd ~/Projects/your-project
/task-create "Implement Phase 2.8 complexity routing" requirements:[REQ-ORCH-001]

# Add to task frontmatter:
bdd_scenarios: [BDD-ORCH-001]
```

### Step 5: Implement via BDD Workflow

```bash
/task-work TASK-042 --mode=bdd

# TaskWright workflow:
# ✅ Checks RequireKit installed
# ✅ Loads Gherkin scenarios
# ✅ Routes to bdd-generator
# ✅ Generates step definitions
# ✅ Implements to pass scenarios
# ✅ Runs BDD tests
# ✅ Quality gates enforced
```

### Step 6: Verify & Complete

```bash
# All BDD tests should pass
# Code review approved
# Task moved to IN_REVIEW

/task-complete TASK-042
```
```

#### 5. Error Scenarios

**Content**: What happens when things go wrong

```markdown
## Troubleshooting

### Error: RequireKit Not Installed

```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires RequireKit installation

  Repository: https://github.com/requirekit/require-kit
  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Alternative modes:
    /task-work TASK-042 --mode=tdd      # Test-first development
    /task-work TASK-042 --mode=standard # Default workflow
```

**Solution**: Install RequireKit and verify marker file exists:
```bash
ls ~/.agentecflow/require-kit.marker
```

### Error: No BDD Scenarios Linked

```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires linked Gherkin scenarios

  Add to task frontmatter:
    bdd_scenarios: [BDD-001, BDD-002]

  Or generate scenarios in RequireKit:
    cd ~/Projects/require-kit
    /generate-bdd REQ-XXX
```

**Solution**: Link scenarios in task frontmatter or generate them first

### Error: Scenario Not Found

```bash
ERROR: BDD scenario BDD-ORCH-001 not found in RequireKit

  Verify scenario exists:
    cd ~/Projects/require-kit
    cat docs/bdd/BDD-ORCH-001.feature

  Or regenerate:
    /generate-bdd REQ-ORCH-001
```

**Solution**: Ensure scenarios exist in RequireKit before linking
```

#### 6. Benefits for Agentic Systems

**Content**:
- State transition correctness
- Interrupt point validation
- Approval logic verification
- Traceability for debugging
- Living documentation
- Regression protection

### Secondary Deliverables

#### Update CLAUDE.md

**Location**: `CLAUDE.md` (around line 300)

**Add Section**:
```markdown
## BDD Workflow (Agentic Systems)

For formal agentic orchestration systems, TaskWright integrates with RequireKit for BDD workflow:

**Use for**:
- LangGraph state machines
- Multi-agent coordination
- Safety-critical workflows
- Formal behavior specifications

**Prerequisites**: RequireKit + TaskWright installed

**Workflow**:
```bash
# In RequireKit: Create requirements
/req-create "System behavior"
/formalize-ears REQ-001
/generate-bdd REQ-001

# In TaskWright: Implement from scenarios
/task-create "Implement behavior" requirements:[REQ-001]
/task-work TASK-042 --mode=bdd
```

**What happens**:
1. Checks RequireKit installed (marker file)
2. Loads Gherkin scenarios from task frontmatter
3. Routes to bdd-generator agent
4. Generates step definitions
5. Implements to pass scenarios
6. Runs BDD tests as quality gate

**See**: [BDD Workflow Guide](docs/guides/bdd-workflow-for-agentic-systems.md)
```

#### Update .claude/CLAUDE.md

**Location**: `.claude/CLAUDE.md` (around line 500)

**Add to Development Best Practices**:
```markdown
**BDD Mode** (Agentic Systems):
- Requires RequireKit installation
- Delegates to bdd-generator agent
- EARS → Gherkin → Implementation workflow
- Full requirements traceability

**When to use**:
```python
# Example: LangGraph state routing
if building_state_machine or safety_critical or formal_spec_needed:
    use_bdd_mode = True
else:
    use_standard_or_tdd = True
```

**Plugin Discovery**:
```python
from lib.feature_detection import supports_bdd

if supports_bdd():  # Checks ~/.agentecflow/require-kit.marker
    # RequireKit available, BDD mode enabled
    execute_bdd_workflow()
else:
    # RequireKit not installed
    show_installation_guidance()
```
```

## Success Criteria

- [ ] `docs/guides/bdd-workflow-for-agentic-systems.md` created
- [ ] All 6 required sections complete
- [ ] LangGraph case study included with code examples
- [ ] Error scenarios documented with solutions
- [ ] `CLAUDE.md` updated with BDD section
- [ ] `.claude/CLAUDE.md` updated with discovery example
- [ ] All links work (no 404s)
- [ ] Code examples are syntactically correct
- [ ] Walkthrough matches actual implementation

## Testing Checklist

- [ ] Read through docs/guides/bdd-workflow-for-agentic-systems.md
- [ ] Verify LangGraph example is complete
- [ ] Check all bash commands for accuracy
- [ ] Verify RequireKit repo link is correct
- [ ] Ensure decision matrix is clear
- [ ] Validate error messages match reality (after TASK-BDD-003)

## Related Tasks

**Depends On**: None (Wave 1 parallel starter)
**Blocks**: TASK-BDD-005 (testing validates documentation accuracy)
**Parallel With**: TASK-BDD-001 (investigation), TASK-BDD-006 (RequireKit)

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md) (sections 5.1-5.3)
- [LangGraph Architecture](../../../docs/research/LangGraph-Native_Orchestration_for_TaskWright_Technical_Architecture.md)
- [Build Strategy](../../../docs/research/TaskWright_LangGraph_Orchestration_Build_Strategy.md)

## Notes

- Focus on agentic systems use case (NOT general BDD)
- Make LangGraph example as complete as possible
- Include actual code that will be implemented
- Error messages will be validated in TASK-BDD-005
- This is user-facing - prioritize clarity over completeness
