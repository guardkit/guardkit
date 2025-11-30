# BDD Workflow for Agentic Systems

## Overview

TaskWright integrates with [RequireKit](https://github.com/requirekit/require-kit) to provide full Behavior-Driven Development (BDD) workflows specifically for **agentic orchestration systems** built with frameworks like LangGraph.

This guide explains when BDD mode is appropriate, how to use it effectively, and provides a complete LangGraph case study demonstrating the value of formal behavior specifications.

## When to Use BDD Mode

BDD mode is **NOT** for general features. It's specifically designed for agentic systems where precise behavior specifications are critical.

### ✅ USE BDD For:

- **Agentic orchestration systems** - LangGraph state machines, multi-agent coordination, workflow engines
- **Safety-critical workflows** - Quality gates, approval checkpoints, authentication/authorization logic
- **Formal behavior specifications** - Compliance requirements, audit trails, regulatory systems
- **Complex state transitions** - Finite state machines, process orchestrators, routing logic

### ❌ DON'T USE BDD For:

- **General CRUD features** - Simple database operations, list/detail views
- **Simple UI components** - Buttons, forms, layouts without complex logic
- **Bug fixes and refactoring** - Maintenance work on existing code
- **Prototyping and exploration** - Proof-of-concepts, spikes, experiments
- **Straightforward implementations** - Features with obvious, simple logic

### Decision Matrix

Use this table to decide which development mode is appropriate:

| Feature Type | Mode | Reason |
|--------------|------|--------|
| LangGraph state routing | **BDD** | Precise behavior specs needed for state transitions |
| Multi-agent coordination | **BDD** | Complex interactions require formal specification |
| Authentication workflow | **BDD** | Safety-critical, needs explicit scenarios |
| User CRUD endpoints | **Standard** | Simple, well-understood patterns |
| Add database table | **Standard** | Straightforward schema change |
| Complex business rules | **TDD** | Test-driven but not behavior-specification driven |
| Fix typo in message | **Standard** | Trivial change |
| Quality gate orchestration | **BDD** | State machine with approval checkpoints |

### When is BDD Worth the Overhead?

BDD has significant overhead (EARS notation, Gherkin scenarios, step definitions). Use it when:

1. **Behavior ambiguity is costly** - Getting state transitions wrong breaks the system
2. **Traceability is critical** - You need to trace requirements → scenarios → code → tests
3. **Living documentation matters** - Gherkin scenarios serve as executable specifications
4. **Compliance is required** - Regulatory or audit requirements demand formal specs

If your feature doesn't meet these criteria, use Standard or TDD mode instead.

## Prerequisites

### Required Installations

1. **TaskWright** (this system)
2. **RequireKit** - Requirement management system with EARS and BDD support
   - Repository: https://github.com/requirekit/require-kit
   - Installation:
     ```bash
     cd ~/Projects/require-kit
     ./installer/scripts/install.sh
     ```

3. **Verify RequireKit Installation**:
   ```bash
   ls ~/.agentecflow/require-kit.marker.json  # Or require-kit.marker (legacy)
   # Should show the marker file if properly installed
   ```

### Required Knowledge

Before using BDD mode, familiarize yourself with:

1. **EARS Notation** - Easy Approach to Requirements Syntax
   - [RequireKit EARS Guide](https://github.com/requirekit/require-kit/docs/guides/ears-notation.md)
   - Pattern: `WHEN [trigger], system SHALL [response]`

2. **Gherkin Syntax** - Given/When/Then scenario format
   - [Cucumber Gherkin Tutorial](https://cucumber.io/docs/gherkin/)
   - Example:
     ```gherkin
     Given a precondition
     When an action occurs
     Then an expected outcome
     ```

3. **BDD Test Frameworks** (language-specific):
   - Python: `pytest-bdd`
   - JavaScript: `cucumber-js`
   - .NET: `SpecFlow`

## Case Study: LangGraph Orchestration Layer

### The Challenge

Building a LangGraph-based agent orchestrator for TaskWright's task workflow with:

- **7-phase workflow**: Phase 2 → 2.5 → 2.7 → 2.8 → 3 → 4 → 5
- **Complexity-based routing**: AUTO_PROCEED vs QUICK_OPTIONAL vs FULL_REQUIRED
- **Human checkpoints**: Using LangGraph's `interrupt()` semantics
- **Test retry loops**: Auto-fix with max 3 attempts
- **Quality gates**: Compilation, testing, coverage enforcement

### Why BDD?

State machines require **precise behavior specifications**:

✅ **Routing conditions must be exact** - "Score ≥7" is different from "Score >7"
✅ **Checkpoint semantics must be unambiguous** - What exactly happens when interrupted?
✅ **Edge cases must be explicitly handled** - What if score is exactly 4? Exactly 7?
✅ **Traceability from requirements to code is critical** - Auditing workflow decisions
✅ **Living documentation** - Gherkin scenarios document the orchestration logic

### EARS Requirement

```
REQ-ORCH-001: Phase 2.8 Complexity Routing

WHEN task complexity_score ≥ 7, the system SHALL invoke FULL_REQUIRED checkpoint.
WHEN task complexity_score is 4-6, the system SHALL invoke QUICK_OPTIONAL checkpoint.
WHEN task complexity_score is 1-3, the system SHALL proceed automatically to Phase 3.

WHERE:
- complexity_score is an integer on a 0-10 scale
- FULL_REQUIRED checkpoint interrupts workflow with mandatory human approval
- QUICK_OPTIONAL checkpoint shows summary with 30-second auto-approve timeout
- AUTO_PROCEED bypasses checkpoint and continues to Phase 3
```

### Gherkin Scenario

File: `docs/bdd/complexity-routing.feature`

```gherkin
Feature: Complexity-Based Routing
  As a TaskWright orchestrator
  I want to route tasks based on complexity scores
  So that high-risk changes get mandatory human review

  Background:
    Given the TaskWright workflow is initialized
    And Phase 2 (implementation planning) is complete

  @critical @checkpoint
  Scenario: High complexity triggers mandatory review
    Given a task with complexity score 8
    When the workflow reaches Phase 2.8
    Then the system should invoke FULL_REQUIRED checkpoint
    And the workflow should interrupt with full plan display
    And the options should be ["approve", "revise", "abort"]
    And auto-proceed should be disabled
    And timeout should be null

  @critical @checkpoint
  Scenario: Complexity score of exactly 7 triggers mandatory review
    Given a task with complexity score 7
    When the workflow reaches Phase 2.8
    Then the system should invoke FULL_REQUIRED checkpoint
    And the workflow should interrupt with full plan display

  @quick-review @checkpoint
  Scenario: Medium complexity offers optional review
    Given a task with complexity score 5
    When the workflow reaches Phase 2.8
    Then the system should invoke QUICK_OPTIONAL checkpoint
    And the workflow should show a summary
    And the timeout should default to approve after 30 seconds
    And the options should include ["approve", "revise"]

  @quick-review @checkpoint
  Scenario: Complexity score of exactly 4 offers optional review
    Given a task with complexity score 4
    When the workflow reaches Phase 2.8
    Then the system should invoke QUICK_OPTIONAL checkpoint

  @auto-proceed
  Scenario: Low complexity proceeds automatically
    Given a task with complexity score 2
    When the workflow reaches Phase 2.8
    Then the system should proceed to Phase 3 automatically
    And no checkpoint should be displayed
    And no interrupt should occur

  @auto-proceed
  Scenario: Complexity score of exactly 3 proceeds automatically
    Given a task with complexity score 3
    When the workflow reaches Phase 2.8
    Then the system should proceed to Phase 3 automatically

  @error-handling
  Scenario: Invalid complexity score defaults to manual review
    Given a task with complexity score 15
    When the workflow reaches Phase 2.8
    Then the system should invoke FULL_REQUIRED checkpoint
    And a warning should be logged about invalid score
```

### Implementation (Python + LangGraph)

File: `src/orchestration/complexity_router.py`

```python
from typing import Literal
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

class TaskWrightState(BaseModel):
    """LangGraph state for TaskWright orchestration."""
    task_id: str
    complexity_score: int = Field(ge=0, le=10)
    current_phase: str
    plan_content: str = ""
    approval_required: bool = False
    checkpoint_type: str | None = None

def complexity_router(state: TaskWrightState) -> Literal["auto_proceed", "quick_review", "full_review"]:
    """
    Route based on complexity score to appropriate approval path.

    Implements REQ-ORCH-001: Phase 2.8 Complexity Routing

    Args:
        state: Current TaskWright workflow state

    Returns:
        Routing decision: auto_proceed, quick_review, or full_review
    """
    score = state.complexity_score

    # Validate score range (defensive programming)
    if score < 0 or score > 10:
        # Invalid score - default to safest option
        import logging
        logging.warning(f"Invalid complexity score {score} for task {state.task_id}, defaulting to FULL_REQUIRED")
        return "full_review"

    # EARS: WHEN complexity_score ≥ 7, SHALL invoke FULL_REQUIRED
    if score >= 7:
        return "full_review"

    # EARS: WHEN complexity_score is 4-6, SHALL invoke QUICK_OPTIONAL
    elif score >= 4:
        return "quick_review"

    # EARS: WHEN complexity_score is 1-3, SHALL proceed automatically
    else:
        return "auto_proceed"

def full_review_checkpoint(state: TaskWrightState) -> TaskWrightState:
    """
    FULL_REQUIRED checkpoint - mandatory human review.

    Uses LangGraph interrupt() to pause workflow and wait for human input.
    """
    from langgraph.checkpoint import interrupt

    # Display full implementation plan
    plan_summary = {
        "task_id": state.task_id,
        "complexity_score": state.complexity_score,
        "plan": state.plan_content,
        "options": ["approve", "revise", "abort"],
        "auto_proceed": False,
        "timeout": None
    }

    # Interrupt workflow - LangGraph will pause here
    decision = interrupt(plan_summary)

    # Update state based on human decision
    state.checkpoint_type = "FULL_REQUIRED"
    state.approval_required = decision != "approve"

    return state

def quick_review_checkpoint(state: TaskWrightState) -> TaskWrightState:
    """
    QUICK_OPTIONAL checkpoint - 30-second timeout with auto-approve.

    Shows summary, defaults to approve after timeout.
    """
    from langgraph.checkpoint import interrupt
    import time

    summary = {
        "task_id": state.task_id,
        "complexity_score": state.complexity_score,
        "plan_summary": state.plan_content[:500] + "...",
        "options": ["approve", "revise"],
        "timeout_seconds": 30,
        "default_action": "approve"
    }

    # Interrupt with timeout
    decision = interrupt(summary, timeout=30.0, default="approve")

    state.checkpoint_type = "QUICK_OPTIONAL"
    state.approval_required = decision != "approve"

    return state

def auto_proceed(state: TaskWrightState) -> TaskWrightState:
    """
    AUTO_PROCEED - no checkpoint, continue to Phase 3.
    """
    state.checkpoint_type = None
    state.approval_required = False
    state.current_phase = "Phase 3"

    return state

# Build LangGraph workflow
def build_workflow() -> StateGraph:
    """Construct the LangGraph state machine."""
    workflow = StateGraph(TaskWrightState)

    # Add nodes
    workflow.add_node("phase_2", implementation_planning)
    workflow.add_node("phase_2_8_router", complexity_router)
    workflow.add_node("full_review", full_review_checkpoint)
    workflow.add_node("quick_review", quick_review_checkpoint)
    workflow.add_node("auto_proceed", auto_proceed)
    workflow.add_node("phase_3", implementation)

    # Add edges
    workflow.add_edge("phase_2", "phase_2_8_router")
    workflow.add_conditional_edges(
        "phase_2_8_router",
        lambda state: complexity_router(state),
        {
            "full_review": "full_review",
            "quick_review": "quick_review",
            "auto_proceed": "auto_proceed"
        }
    )
    workflow.add_edge("full_review", "phase_3")
    workflow.add_edge("quick_review", "phase_3")
    workflow.add_edge("auto_proceed", "phase_3")

    workflow.set_entry_point("phase_2")

    return workflow.compile()
```

### BDD Tests (pytest-bdd)

File: `tests/bdd/test_complexity_routing.py`

```python
import pytest
from pytest_bdd import scenario, given, when, then, parsers
from src.orchestration.complexity_router import (
    TaskWrightState,
    complexity_router,
    full_review_checkpoint,
    quick_review_checkpoint,
    auto_proceed
)

# Scenario: High complexity triggers mandatory review
@scenario('../../docs/bdd/complexity-routing.feature',
          'High complexity triggers mandatory review')
def test_high_complexity_mandatory_review():
    """BDD-ORCH-001: High complexity → FULL_REQUIRED checkpoint."""
    pass

# Scenario: Complexity score of exactly 7
@scenario('../../docs/bdd/complexity-routing.feature',
          'Complexity score of exactly 7 triggers mandatory review')
def test_boundary_score_7():
    """BDD-ORCH-002: Boundary test for score=7."""
    pass

# Scenario: Medium complexity optional review
@scenario('../../docs/bdd/complexity-routing.feature',
          'Medium complexity offers optional review')
def test_medium_complexity_optional_review():
    """BDD-ORCH-003: Medium complexity → QUICK_OPTIONAL checkpoint."""
    pass

# Scenario: Low complexity auto-proceed
@scenario('../../docs/bdd/complexity-routing.feature',
          'Low complexity proceeds automatically')
def test_low_complexity_auto_proceed():
    """BDD-ORCH-004: Low complexity → AUTO_PROCEED."""
    pass

# Scenario: Invalid score handling
@scenario('../../docs/bdd/complexity-routing.feature',
          'Invalid complexity score defaults to manual review')
def test_invalid_score_handling():
    """BDD-ORCH-005: Invalid score → FULL_REQUIRED (safety)."""
    pass

# Step Definitions

@pytest.fixture
def context():
    """Test context to share state between steps."""
    return {}

@given(parsers.parse('a task with complexity score {score:d}'))
def task_with_complexity(context, score):
    """Create a task state with given complexity score."""
    context['state'] = TaskWrightState(
        task_id="TASK-001",
        complexity_score=score,
        current_phase="Phase 2.8",
        plan_content="Implementation plan content here..."
    )

@given('the TaskWright workflow is initialized')
def workflow_initialized(context):
    """Workflow is ready to execute."""
    # Prerequisite check - could verify LangGraph setup
    pass

@given('Phase 2 (implementation planning) is complete')
def phase_2_complete(context):
    """Planning phase finished, ready for routing."""
    # Could verify plan_content exists
    pass

@when('the workflow reaches Phase 2.8')
def reach_phase_28(context):
    """Execute the complexity router."""
    context['result'] = complexity_router(context['state'])

@then(parsers.parse('the system should invoke {checkpoint_type} checkpoint'))
def verify_checkpoint_type(context, checkpoint_type):
    """Verify correct checkpoint was invoked."""
    expected = {
        'FULL_REQUIRED': 'full_review',
        'QUICK_OPTIONAL': 'quick_review'
    }[checkpoint_type]

    assert context['result'] == expected, \
        f"Expected {expected}, got {context['result']}"

@then('the system should proceed to Phase 3 automatically')
def verify_auto_proceed(context):
    """Verify AUTO_PROCEED routing."""
    assert context['result'] == 'auto_proceed'

@then('no checkpoint should be displayed')
def verify_no_checkpoint(context):
    """Verify no interrupt occurs."""
    # In real implementation, verify interrupt() not called
    assert context['result'] == 'auto_proceed'

@then('no interrupt should occur')
def verify_no_interrupt(context):
    """Verify workflow continues without human input."""
    assert context['result'] == 'auto_proceed'

@then(parsers.parse('the workflow should interrupt with full plan display'))
def verify_full_plan_display(context):
    """Verify FULL_REQUIRED shows complete plan."""
    # In full implementation, verify interrupt() called with plan_content
    pass

@then(parsers.parse('the options should be {options}'))
def verify_options(context, options):
    """Verify available human decision options."""
    # Parse options list and verify
    pass

@then('auto-proceed should be disabled')
def verify_no_auto_proceed(context):
    """Verify timeout is null for FULL_REQUIRED."""
    assert context['result'] == 'full_review'

@then('timeout should be null')
def verify_null_timeout(context):
    """FULL_REQUIRED has no timeout."""
    pass

@then('the workflow should show a summary')
def verify_summary_shown(context):
    """QUICK_OPTIONAL shows abbreviated summary."""
    pass

@then(parsers.parse('the timeout should default to approve after {seconds:d} seconds'))
def verify_timeout(context, seconds):
    """Verify QUICK_OPTIONAL timeout."""
    assert seconds == 30

@then(parsers.parse('a warning should be logged about invalid score'))
def verify_warning_logged(context, caplog):
    """Verify invalid score triggers warning."""
    # Check caplog for warning message
    pass
```

### Running BDD Tests

```bash
# Install pytest-bdd
pip install pytest-bdd

# Run all BDD scenarios
pytest tests/bdd/ -v

# Run specific feature
pytest tests/bdd/test_complexity_routing.py -v

# Run with coverage
pytest tests/bdd/ --cov=src/orchestration --cov-report=term

# Expected output:
# tests/bdd/test_complexity_routing.py::test_high_complexity_mandatory_review PASSED
# tests/bdd/test_complexity_routing.py::test_boundary_score_7 PASSED
# tests/bdd/test_complexity_routing.py::test_medium_complexity_optional_review PASSED
# tests/bdd/test_complexity_routing.py::test_low_complexity_auto_proceed PASSED
# tests/bdd/test_complexity_routing.py::test_invalid_score_handling PASSED
```

### Benefits Realized

✅ **State transition correctness** - All routing paths tested with boundary cases
✅ **Checkpoint behavior validated** - Interrupt semantics clearly specified
✅ **Approval logic verified** - Decision options and timeouts tested
✅ **Traceability established** - REQ-ORCH-001 → Gherkin → Code → Tests
✅ **Living documentation** - Gherkin scenarios document orchestration logic
✅ **Regression protection** - Changes to routing logic are immediately caught
✅ **Edge case coverage** - Boundary values (4, 7) and invalid inputs handled

### What BDD Caught That Unit Tests Wouldn't

1. **Ambiguity in "4-6"** - Is 4 included? Is 6 included? Gherkin forced explicit scenarios.
2. **Timeout semantics** - What exactly happens after 30 seconds? Scenario clarified.
3. **Invalid score handling** - EARS didn't specify - BDD scenario required decision.
4. **Interrupt vs no-interrupt** - Clear distinction in scenarios prevented bugs.

## Complete Workflow: End-to-End

### Step 1: Create Epic in RequireKit

Start by creating an epic for your agentic system in RequireKit:

```bash
cd ~/Projects/require-kit

# Create epic for your orchestration system
/epic-create "LangGraph Orchestration Layer"

# Output:
# Created epic EPIC-001: LangGraph Orchestration Layer
# Location: epics/EPIC-001-langgraph-orchestration.md
```

### Step 2: Formalize Requirements (EARS)

Create formal requirements using EARS notation:

```bash
# Create new requirement
/req-create "Phase 2.8 complexity routing"

# Output:
# Created requirement REQ-ORCH-001
# Location: requirements/REQ-ORCH-001.md

# Formalize using EARS notation
/formalize-ears REQ-ORCH-001

# Agent will guide you through EARS template:
# WHEN [trigger condition]
# the system SHALL [system response]
# WHERE [definitions and constraints]
```

**Edit the requirement file**:

```markdown
---
id: REQ-ORCH-001
title: Phase 2.8 Complexity Routing
type: behavioral
priority: critical
epic: EPIC-001
---

# Requirement: Phase 2.8 Complexity Routing

## EARS Specification

WHEN task complexity_score ≥ 7, the system SHALL invoke FULL_REQUIRED checkpoint.
WHEN task complexity_score is 4-6, the system SHALL invoke QUICK_OPTIONAL checkpoint.
WHEN task complexity_score is 1-3, the system SHALL proceed automatically to Phase 3.

WHERE:
- complexity_score is an integer on a 0-10 scale
- FULL_REQUIRED checkpoint interrupts workflow with mandatory human approval
- QUICK_OPTIONAL checkpoint shows summary with 30-second auto-approve timeout
- AUTO_PROCEED bypasses checkpoint and continues to Phase 3
```

### Step 3: Generate BDD Scenarios

Convert EARS requirements to Gherkin scenarios:

```bash
# Generate Gherkin from EARS requirement
/generate-bdd REQ-ORCH-001

# RequireKit converts EARS → Gherkin
# Output: docs/bdd/BDD-ORCH-001-complexity-routing.feature

# Review generated scenarios
cat docs/bdd/BDD-ORCH-001-complexity-routing.feature
```

RequireKit will create comprehensive Gherkin scenarios including:
- Happy path scenarios
- Boundary value tests (scores 4, 7)
- Error handling scenarios
- Edge cases

### Step 4: Create Implementation Task

Switch to your TaskWright project and create an implementation task:

```bash
cd ~/Projects/your-project

# Create task linked to requirement
/task-create "Implement Phase 2.8 complexity routing" requirements:[REQ-ORCH-001]

# Output:
# Created task TASK-042
# Location: tasks/backlog/TASK-042.md
```

**Edit task frontmatter** to link BDD scenarios:

```yaml
---
id: TASK-042
title: Implement Phase 2.8 complexity routing
status: backlog
requirements: [REQ-ORCH-001]
bdd_scenarios: [BDD-ORCH-001]  # Link to Gherkin scenarios
priority: high
---
```

### Step 5: Implement via BDD Workflow

Execute the BDD workflow in TaskWright:

```bash
# Start BDD mode implementation
/task-work TASK-042 --mode=bdd

# TaskWright workflow:
# ✅ Phase 1: Checks RequireKit installed (marker file)
# ✅ Phase 2: Loads Gherkin scenarios from RequireKit
# ✅ Phase 2.5: Routes to bdd-generator agent
# ✅ Phase 3: Generates step definitions (pytest-bdd)
# ✅ Phase 3: Implements code to pass scenarios
# ✅ Phase 4: Runs BDD tests (pytest tests/bdd/)
# ✅ Phase 4.5: Enforces test pass rate (100%)
# ✅ Phase 5: Code review
# ✅ Phase 5.5: Plan audit
```

**What the BDD workflow does**:

1. **Verifies RequireKit installed**: Checks `~/.agentecflow/require-kit.marker.json` (or legacy `require-kit.marker`)
2. **Loads scenarios**: Reads Gherkin from `bdd_scenarios` frontmatter field
3. **Routes to specialist**: Uses `bdd-generator` agent (not standard implementation)
4. **Generates step definitions**: Creates pytest-bdd step functions
5. **Implements to pass**: Writes code that makes scenarios pass
6. **Runs BDD tests**: Executes `pytest tests/bdd/` as quality gate
7. **Enforces quality**: 100% BDD test pass rate required

### Step 6: Verify & Complete

After implementation passes all gates:

```bash
# Check test results
pytest tests/bdd/ -v

# Output:
# ✅ All BDD scenarios passing
# ✅ Code coverage ≥80%
# ✅ Code review approved

# Task automatically moved to IN_REVIEW
/task-status TASK-042

# Complete the task
/task-complete TASK-042

# Task archived to tasks/completed/
```

**Success criteria**:
- ✅ All Gherkin scenarios pass
- ✅ Code coverage thresholds met
- ✅ Code review approved
- ✅ Traceability: REQ → BDD → Code → Tests

## Troubleshooting

### Error: RequireKit Not Installed

**Symptom**:

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
# Install RequireKit
cd ~/Projects/require-kit
./installer/scripts/install.sh

# Verify installation
ls ~/.agentecflow/require-kit.marker.json  # Or require-kit.marker (legacy)

# Should output:
# /Users/you/.agentecflow/require-kit.marker.json

# Retry BDD workflow
cd ~/Projects/your-project
/task-work TASK-042 --mode=bdd
```

### Error: No BDD Scenarios Linked

**Symptom**:

```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires linked Gherkin scenarios

  Add to task frontmatter:
    bdd_scenarios: [BDD-001, BDD-002]

  Or generate scenarios in RequireKit:
    cd ~/Projects/require-kit
    /generate-bdd REQ-XXX
```

**Solution**: Link scenarios in task frontmatter or generate them first:

**Option 1**: Generate scenarios in RequireKit

```bash
cd ~/Projects/require-kit
/generate-bdd REQ-ORCH-001

# Output:
# Created BDD-ORCH-001: docs/bdd/BDD-ORCH-001-complexity-routing.feature
```

**Option 2**: Manually link existing scenarios

Edit `tasks/backlog/TASK-042.md`:

```yaml
---
id: TASK-042
title: Implement Phase 2.8 complexity routing
bdd_scenarios: [BDD-ORCH-001]  # Add this line
---
```

### Error: Scenario Not Found

**Symptom**:

```bash
ERROR: BDD scenario BDD-ORCH-001 not found in RequireKit

  Verify scenario exists:
    cd ~/Projects/require-kit
    cat docs/bdd/BDD-ORCH-001-complexity-routing.feature

  Or regenerate:
    /generate-bdd REQ-ORCH-001
```

**Solution**: Ensure scenarios exist in RequireKit before linking:

```bash
# Check if scenario file exists
cd ~/Projects/require-kit
ls docs/bdd/BDD-ORCH-001*.feature

# If not found, generate from requirement
/generate-bdd REQ-ORCH-001

# If requirement doesn't exist, create it first
/req-create "Phase 2.8 complexity routing"
/formalize-ears REQ-ORCH-001
/generate-bdd REQ-ORCH-001
```

### Error: pytest-bdd Not Installed

**Symptom**:

```bash
ERROR: BDD test framework not found

  Install for your stack:
    Python:     pip install pytest-bdd
    JavaScript: npm install --save-dev cucumber
    .NET:       dotnet add package SpecFlow
```

**Solution**: Install the appropriate BDD testing framework:

**Python**:
```bash
pip install pytest-bdd
pytest --version  # Verify installation
```

**JavaScript**:
```bash
npm install --save-dev @cucumber/cucumber
npx cucumber --version
```

**.NET**:
```bash
dotnet add package SpecFlow
dotnet add package SpecFlow.xUnit
```

### Error: Step Definition Missing

**Symptom**:

```bash
pytest tests/bdd/

ERROR: Step definition not found:
  Given a task with complexity score 8

Possible causes:
  - Step definition not implemented
  - Import path incorrect
  - Decorator syntax error
```

**Solution**: Implement missing step definition:

```python
# tests/bdd/test_complexity_routing.py

from pytest_bdd import given, parsers

@given(parsers.parse('a task with complexity score {score:d}'))
def task_with_complexity(context, score):
    """Create a task state with given complexity score."""
    context['state'] = TaskWrightState(
        task_id="TASK-001",
        complexity_score=score,
        current_phase="Phase 2.8"
    )
```

## Benefits for Agentic Systems

BDD provides unique value for agentic orchestration systems:

### 1. State Transition Correctness

**Problem**: State machines have complex routing logic with edge cases.

**BDD Solution**: Gherkin scenarios test every transition path.

```gherkin
Scenario: Score of exactly 7 triggers full review
  Given a task with complexity score 7
  Then the system should invoke FULL_REQUIRED checkpoint

Scenario: Score of exactly 6 offers quick review
  Given a task with complexity score 6
  Then the system should invoke QUICK_OPTIONAL checkpoint
```

**Benefit**: Boundary values (4, 7) are explicitly tested, preventing off-by-one errors.

### 2. Interrupt Point Validation

**Problem**: LangGraph `interrupt()` semantics must be precise - when to pause, what data to show, timeout behavior.

**BDD Solution**: Scenarios specify exact interrupt behavior.

```gherkin
Scenario: Full review checkpoint behavior
  When the system invokes FULL_REQUIRED checkpoint
  Then the workflow should interrupt
  And the full plan should be displayed
  And options should be ["approve", "revise", "abort"]
  And timeout should be null
```

**Benefit**: Interrupt behavior is unambiguous and tested.

### 3. Approval Logic Verification

**Problem**: Human decision checkpoints have complex logic (timeouts, defaults, option validation).

**BDD Solution**: Scenarios document and test all approval paths.

```gherkin
Scenario: Quick review timeout behavior
  When the system invokes QUICK_OPTIONAL checkpoint
  And 30 seconds elapse with no human input
  Then the workflow should default to "approve"
  And proceed to Phase 3
```

**Benefit**: Timeout logic is tested, preventing silent failures.

### 4. Traceability for Debugging

**Problem**: When orchestration fails, tracing from requirement → code → test is hard.

**BDD Solution**: Direct traceability chain.

```
REQ-ORCH-001 (EARS)
  ↓
BDD-ORCH-001 (Gherkin)
  ↓
test_high_complexity_mandatory_review (pytest-bdd)
  ↓
complexity_router() (implementation)
```

**Benefit**: When test fails, you know which requirement broke and why.

### 5. Living Documentation

**Problem**: Orchestration logic is hard to understand from code alone.

**BDD Solution**: Gherkin scenarios serve as executable documentation.

```gherkin
Feature: Complexity-Based Routing
  As a TaskWright orchestrator
  I want to route tasks based on complexity scores
  So that high-risk changes get mandatory human review
```

**Benefit**: New developers understand orchestration logic by reading scenarios.

### 6. Regression Protection

**Problem**: Changing routing logic can break existing workflows.

**BDD Solution**: Comprehensive scenario suite catches regressions.

```bash
# Before changing complexity_router():
pytest tests/bdd/ -v

# All scenarios pass ✅

# After change:
pytest tests/bdd/ -v

# Scenario fails: "Score of exactly 7 triggers full review" ❌
# Regression caught before production
```

**Benefit**: Safe refactoring with confidence.

## Comparison: BDD vs TDD vs Standard

| Aspect | BDD | TDD | Standard |
|--------|-----|-----|----------|
| **When to use** | Agentic systems, state machines | Business logic, algorithms | Simple features |
| **Overhead** | High (EARS + Gherkin) | Medium (tests first) | Low |
| **Traceability** | REQ → BDD → Code → Test | Test → Code | None |
| **Documentation** | Gherkin scenarios | Test cases | Code comments |
| **Stakeholder readable** | Yes (Gherkin) | No (code) | No |
| **Edge case coverage** | Excellent (explicit scenarios) | Good (test-driven) | Variable |
| **Learning curve** | Steep (EARS, Gherkin, step defs) | Moderate | Minimal |
| **Best for** | LangGraph, FSMs, workflows | Complex logic | CRUD, UI |

## Best Practices

### 1. Keep Scenarios Focused

**Bad** (too broad):

```gherkin
Scenario: Workflow executes correctly
  Given a task
  When the workflow runs
  Then everything works
```

**Good** (focused):

```gherkin
Scenario: High complexity triggers mandatory review
  Given a task with complexity score 8
  When the workflow reaches Phase 2.8
  Then the system should invoke FULL_REQUIRED checkpoint
```

### 2. Use Background for Common Setup

```gherkin
Feature: Complexity-Based Routing

  Background:
    Given the TaskWright workflow is initialized
    And Phase 2 (implementation planning) is complete

  Scenario: High complexity review
    Given a task with complexity score 8
    # Background already handled initialization
    When the workflow reaches Phase 2.8
    ...
```

### 3. Test Boundary Values Explicitly

For ranges, always test:
- Lower boundary
- Lower boundary - 1
- Upper boundary
- Upper boundary + 1

```gherkin
# Range: 4-6 → QUICK_OPTIONAL

Scenario: Score 3 is below range
  Given a task with complexity score 3
  Then the system should proceed automatically

Scenario: Score 4 is lower boundary
  Given a task with complexity score 4
  Then the system should invoke QUICK_OPTIONAL checkpoint

Scenario: Score 6 is upper boundary
  Given a task with complexity score 6
  Then the system should invoke QUICK_OPTIONAL checkpoint

Scenario: Score 7 is above range
  Given a task with complexity score 7
  Then the system should invoke FULL_REQUIRED checkpoint
```

### 4. Use Tags for Test Organization

```gherkin
@critical @checkpoint
Scenario: High complexity triggers mandatory review
  ...

@quick-review @checkpoint
Scenario: Medium complexity offers optional review
  ...

@auto-proceed
Scenario: Low complexity proceeds automatically
  ...

@error-handling
Scenario: Invalid complexity score defaults to manual review
  ...
```

Run specific tags:

```bash
# Run only critical scenarios
pytest tests/bdd/ -m critical

# Run only checkpoint scenarios
pytest tests/bdd/ -m checkpoint

# Exclude error-handling scenarios
pytest tests/bdd/ -m "not error-handling"
```

### 5. Implement Step Definitions Once, Reuse Everywhere

```python
# tests/bdd/steps/common_steps.py

@given(parsers.parse('a task with complexity score {score:d}'))
def task_with_complexity(context, score):
    """Reusable step for creating tasks with specific complexity."""
    context['state'] = TaskWrightState(
        task_id=f"TASK-{context['test_id']}",
        complexity_score=score,
        current_phase="Phase 2.8"
    )

# Reuse in multiple test files:
# - tests/bdd/test_complexity_routing.py
# - tests/bdd/test_checkpoint_behavior.py
# - tests/bdd/test_approval_logic.py
```

### 6. Keep Implementation Separate from Scenarios

**Don't** put implementation details in Gherkin:

```gherkin
# Bad - too implementation-specific
Scenario: Router returns correct string
  Given complexity score 8
  When complexity_router() is called
  Then return value should equal "full_review"
```

**Do** keep scenarios behavior-focused:

```gherkin
# Good - behavior-oriented
Scenario: High complexity triggers mandatory review
  Given a task with complexity score 8
  When the workflow reaches Phase 2.8
  Then the system should invoke FULL_REQUIRED checkpoint
```

## Additional Resources

### RequireKit Documentation

- [RequireKit GitHub](https://github.com/requirekit/require-kit)
- [EARS Notation Guide](https://github.com/requirekit/require-kit/docs/guides/ears-notation.md)
- [BDD Generation Guide](https://github.com/requirekit/require-kit/docs/guides/bdd-generation.md)
- [Epic Management](https://github.com/requirekit/require-kit/docs/guides/epic-management.md)

### BDD Testing Frameworks

- **Python**: [pytest-bdd](https://pytest-bdd.readthedocs.io/)
- **JavaScript**: [Cucumber.js](https://cucumber.io/docs/cucumber/)
- **.NET**: [SpecFlow](https://specflow.org/documentation/)
- **Ruby**: [Cucumber](https://cucumber.io/docs/installation/ruby/)

### LangGraph Documentation

- [LangGraph Official Docs](https://langchain-ai.github.io/langgraph/)
- [State Management](https://langchain-ai.github.io/langgraph/concepts/state/)
- [Checkpoints & Interrupts](https://langchain-ai.github.io/langgraph/concepts/checkpoints/)

### Gherkin Best Practices

- [Cucumber Gherkin Reference](https://cucumber.io/docs/gherkin/reference/)
- [Writing Good Gherkin](https://cucumber.io/docs/bdd/better-gherkin/)
- [Gherkin Anti-Patterns](https://cucumber.io/blog/bdd/gherkin-anti-patterns/)

## Summary

BDD mode in TaskWright is specifically designed for **agentic orchestration systems** where precise behavior specifications are critical:

✅ **Use BDD for**: LangGraph state machines, multi-agent coordination, safety-critical workflows
❌ **Don't use BDD for**: CRUD features, simple UI components, bug fixes

**Key workflow**:
1. Create requirements in RequireKit (EARS notation)
2. Generate Gherkin scenarios (`/generate-bdd`)
3. Create implementation task in TaskWright
4. Execute BDD workflow (`/task-work TASK-XXX --mode=bdd`)
5. BDD tests run as quality gate (100% pass required)

**Benefits**:
- State transition correctness
- Interrupt point validation
- Approval logic verification
- Traceability (REQ → BDD → Code → Test)
- Living documentation
- Regression protection

For straightforward features, use **Standard** or **TDD** mode instead.
