# BDD Mode Restoration - Implementation Guide

**Epic**: Restore BDD mode for agentic system development (LangGraph orchestration)
**Total Estimated Effort**: 3-5 hours
**Parallel Waves**: 3 waves for optimal Conductor workspace usage
**Created**: 2025-11-28
**Source Review**: TASK-2E9E architectural review (final revision)

---

## Executive Summary

This guide orchestrates the restoration of BDD mode (`--mode=bdd`) in guardkit for implementing formal agentic orchestration systems (specifically LangGraph). The work is structured into 3 parallel waves using Conductor git worktrees for maximum efficiency.

### What Was Removed

**TASK-037** (November 2, 2025) removed:
- `--mode=bdd` flag from task-work command
- BDD mode documentation from task-work.md
- `.claude/agents/bdd-generator.md` (moved to RequireKit)
- `installer/global/instructions/core/bdd-gherkin.md` (moved to RequireKit)
- All BDD mode examples and references

### What We're Restoring

**In GuardKit**:
- ✅ `--mode=bdd` flag with RequireKit detection
- ✅ Error messages when RequireKit not installed
- ✅ BDD workflow routing logic
- ✅ Documentation for agentic systems use case

**In RequireKit** (separate repo):
- ✅ Update bdd-generator agent with GitHub-inspired format
- ✅ Add frontmatter metadata for agent discovery
- ✅ Update all RequireKit agents to discovery format

### Why We're Restoring It

**Use Case**: Building LangGraph orchestration layer using BDD workflow
- EARS requirements → Gherkin scenarios → Implementation
- State machine behavior specifications
- Checkpoint and routing logic validation
- Dogfooding RequireKit + GuardKit integration

**Reference**: `LangGraph-Native_Orchestration_for_GuardKit_Technical_Architecture.md`

---

## Architecture Approach

### Detection Pattern

```python
# In task-work command
def validate_bdd_mode():
    """Check if BDD mode is available via RequireKit."""
    marker_file = Path.home() / ".agentecflow" / "require-kit.marker"

    if not marker_file.exists():
        print("""
ERROR: BDD mode requires RequireKit installation

Install RequireKit:
  Repository: https://github.com/requirekit/require-kit
  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

Alternative modes:
  /task-work TASK-XXX --mode=tdd      # Test-first development
  /task-work TASK-XXX --mode=standard # Default workflow

BDD mode is designed for:
  • Agentic orchestration systems (LangGraph, state machines)
  • Safety-critical workflows (quality gates, checkpoints)
  • Formal behavior specifications (audit, compliance)

For general features, use standard or TDD modes.
        """)
        sys.exit(1)
```

### Workflow Integration

```markdown
Phase 1: Load Task Context
  ├─ If --mode=bdd: Check supports_bdd()
  ├─ Load bdd_scenarios from frontmatter
  └─ Validate scenarios exist in RequireKit

Phase 2: Implementation Planning
  ├─ Load Gherkin scenarios from RequireKit
  └─ Include in planning context

Phase 3: Implementation
  ├─ Route to RequireKit bdd-generator agent
  ├─ Generate step definitions
  └─ Implement to pass scenarios

Phase 4: Testing
  ├─ Run BDD tests (pytest-bdd, SpecFlow, etc.)
  └─ Validate scenarios pass

Phase 5: Review
  └─ Standard code review
```

---

## Task Breakdown by Wave

### Wave 1: Foundation (Parallel - 3 tasks)

**Can run in parallel using Conductor worktrees**

| Task | Type | Estimated | Worktree | Dependencies |
|------|------|-----------|----------|--------------|
| **TASK-BDD-001** | Investigation | 30 min | `bdd-wave1-investigate` | None |
| **TASK-BDD-002** | Documentation | 45 min | `bdd-wave1-docs` | None |
| **TASK-BDD-006** | RequireKit agents | 1-2 hours | `bdd-wave1-requirekit` | None (different repo) |

**Conductor Setup**:
```bash
# In guardkit repo
conductor create-workspace bdd-wave1-investigate TASK-BDD-001
conductor create-workspace bdd-wave1-docs TASK-BDD-002

# In requirekit repo (separate)
conductor create-workspace bdd-wave1-requirekit TASK-BDD-006
```

### Wave 2: Implementation (Sequential - 2 tasks)

**Must run after Wave 1 completes**

| Task | Type | Estimated | Worktree | Depends On |
|------|------|-----------|----------|------------|
| **TASK-BDD-003** | Implementation | 1-2 hours | `bdd-wave2-flag` | TASK-BDD-001 |
| **TASK-BDD-004** | Implementation | 1-2 hours | `bdd-wave2-workflow` | TASK-BDD-003 |

**Conductor Setup**:
```bash
# After Wave 1 merges
conductor create-workspace bdd-wave2-flag TASK-BDD-003
# Wait for TASK-BDD-003 to merge
conductor create-workspace bdd-wave2-workflow TASK-BDD-004
```

### Wave 3: Integration & Testing (Sequential - 1 task)

**Must run after Wave 2 completes**

| Task | Type | Estimated | Worktree | Depends On |
|------|------|-----------|----------|------------|
| **TASK-BDD-005** | Testing | 30-45 min | `bdd-wave3-testing` | TASK-BDD-002, TASK-BDD-003, TASK-BDD-004, TASK-BDD-006 |

**Conductor Setup**:
```bash
# After all previous tasks merge
conductor create-workspace bdd-wave3-testing TASK-BDD-005
```

---

## Task Implementation Methods

### Use `/task-work` Command For:

**Structured implementation tasks with clear scope**:
- ✅ TASK-BDD-003 (Flag parsing - clear code changes)
- ✅ TASK-BDD-004 (Workflow routing - clear integration points)
- ✅ TASK-BDD-005 (Testing - clear test cases)

**Benefits**:
- Architectural review (Phase 2.5)
- Test enforcement (Phase 4.5)
- Code review (Phase 5)
- Plan audit (Phase 5.5)
- Traceability

### Use Claude Code Directly For:

**Research and discovery tasks**:
- ✅ TASK-BDD-001 (Investigation - exploratory)
- ✅ TASK-BDD-002 (Documentation - writing, not code)
- ✅ TASK-BDD-006 (RequireKit agents - different repo, mass update)

**Benefits**:
- Faster for research/docs
- More flexible for exploration
- Better for mass refactoring (multiple agents)

---

## Detailed Task Descriptions

### TASK-BDD-001: Investigate Task-Work Mode Implementation

**Priority**: High
**Estimated**: 30 minutes
**Type**: Research
**Implementation**: Claude Code (direct)
**Wave**: 1 (parallel)

**Objective**: Understand where and how `--mode=tdd` is currently implemented

**Acceptance Criteria**:
- [ ] Identify where mode flag is parsed (command spec vs Python)
- [ ] Understand TDD mode workflow routing
- [ ] Document integration points for BDD mode
- [ ] Identify agent invocation mechanism
- [ ] Create architecture diagram showing mode flow

**Deliverables**:
- `tasks/backlog/bdd-restoration/TASK-BDD-001-investigation-findings.md`
- Architecture diagram (text or Mermaid)
- Integration points documented

**Research Questions**:
1. Where is `--mode=tdd` parsed? (command spec or Python script?)
2. How does TDD mode route to testing agents?
3. Where is agent invocation handled?
4. What's the state flow through phases for TDD?
5. Where should BDD checks be added?

---

### TASK-BDD-002: Create BDD Workflow Documentation

**Priority**: High
**Estimated**: 45 minutes
**Type**: Documentation
**Implementation**: Claude Code (direct)
**Wave**: 1 (parallel)

**Objective**: Document BDD mode usage for agentic systems

**Acceptance Criteria**:
- [ ] Create `docs/guides/bdd-workflow-for-agentic-systems.md`
- [ ] Include LangGraph case study with examples
- [ ] Document EARS → Gherkin → Implementation flow
- [ ] Add "When to Use BDD" decision guide
- [ ] Include RequireKit installation instructions
- [ ] Update `CLAUDE.md` with BDD section
- [ ] Update `.claude/CLAUDE.md` with BDD workflow

**Content Sections**:
1. **When to Use BDD in GuardKit**
   - Agentic orchestration systems (LangGraph)
   - Safety-critical workflows
   - Formal specifications
   - NOT for general CRUD features

2. **Prerequisites**
   - RequireKit + GuardKit installed
   - Understanding of EARS notation
   - Gherkin scenario basics

3. **LangGraph Case Study**
   ```gherkin
   Feature: Complexity-Based Routing
     Scenario: High complexity triggers mandatory review
       Given a task with complexity score 8
       When the workflow reaches Phase 2.8
       Then the system should invoke FULL_REQUIRED checkpoint
   ```

4. **Complete Workflow**
   - Create epic in RequireKit
   - Formalize EARS requirements
   - Generate BDD scenarios
   - Create task with scenario links
   - `/task-work TASK-XXX --mode=bdd`

5. **Error Handling**
   - What happens without RequireKit
   - What happens without bdd_scenarios
   - Alternative modes

**Reference**: `docs/research/restoring-bdd-feature.md` (sections on documentation)

---

### TASK-BDD-003: Restore --mode=bdd Flag with RequireKit Detection

**Priority**: High
**Estimated**: 1-2 hours
**Type**: Implementation
**Implementation**: `/task-work` (full quality gates)
**Wave**: 2 (depends on TASK-BDD-001)

**Objective**: Add BDD mode flag with marker file detection

**Acceptance Criteria**:
- [ ] Add `--mode=bdd` to valid mode options
- [ ] Implement marker file check (`~/.agentecflow/require-kit.marker`)
- [ ] Display error message if RequireKit not installed
- [ ] Include RequireKit repo link in error message
- [ ] Validate `bdd_scenarios` field in task frontmatter
- [ ] Error if bdd_scenarios missing or empty
- [ ] Update command syntax in task-work.md
- [ ] Add BDD mode section to Development Modes

**Implementation**:

```markdown
# In installer/global/commands/task-work.md

## Command Syntax
```bash
/task-work TASK-XXX [--mode=standard|tdd|bdd] [other-flags...]
```

### Development Modes

#### BDD Mode (Requires RequireKit)
```bash
/task-work TASK-XXX --mode=bdd
```

**Prerequisites**:
- RequireKit installed (checks `~/.agentecflow/require-kit.marker`)
- Task has `bdd_scenarios: [BDD-001, BDD-002]` in frontmatter

**Use for**:
- Agentic orchestration systems (LangGraph, state machines)
- Safety-critical workflows (quality gates, approval logic)
- Formal behavior specifications (compliance, audit)

**Workflow**:
1. Validates RequireKit installation
2. Loads Gherkin scenarios from RequireKit
3. Routes to bdd-generator agent
4. Generates step definitions
5. Implements to pass scenarios
6. Runs BDD tests in Phase 4

**Error Examples**:
```bash
# RequireKit not installed
ERROR: BDD mode requires RequireKit installation
  Repository: https://github.com/requirekit/require-kit
  Installation: cd ~/Projects/require-kit && ./installer/scripts/install.sh

# No scenarios linked
ERROR: BDD mode requires linked Gherkin scenarios
  Add to task frontmatter:
    bdd_scenarios: [BDD-001, BDD-002]
  Or generate scenarios:
    cd ~/Projects/require-kit
    /generate-bdd REQ-XXX
```
```

**Testing**:
- [ ] Test with RequireKit installed → proceeds
- [ ] Test without RequireKit → clear error with instructions
- [ ] Test without bdd_scenarios → clear error with guidance
- [ ] Test with invalid mode → error listing valid modes

**Reference**: `docs/research/restoring-bdd-feature.md` (Phase 2, lines 80-137)

---

### TASK-BDD-004: Implement BDD Workflow Routing Logic

**Priority**: High
**Estimated**: 1-2 hours
**Type**: Implementation
**Implementation**: `/task-work` (full quality gates)
**Wave**: 2 (depends on TASK-BDD-003)

**Objective**: Route BDD mode to RequireKit's bdd-generator agent

**Acceptance Criteria**:
- [ ] In Phase 1: Load bdd_scenarios from task frontmatter
- [ ] In Phase 1: Fetch Gherkin scenarios from RequireKit
- [ ] In Phase 2: Include scenarios in planning context
- [ ] In Phase 3: Route to bdd-generator agent (RequireKit)
- [ ] In Phase 3: Generate step definitions
- [ ] In Phase 3: Implement code to pass scenarios
- [ ] In Phase 4: Run BDD tests (pytest-bdd, SpecFlow, etc.)
- [ ] In Phase 4.5: Fix loop for failing BDD tests
- [ ] In Phase 5: Standard code review

**Integration Points** (from TASK-BDD-001 findings):

```python
# Phase 1: Load Context
if mode == 'bdd':
    # Validate scenarios exist
    scenario_ids = task_frontmatter.get('bdd_scenarios', [])
    if not scenario_ids:
        raise ValidationError("BDD mode requires bdd_scenarios in frontmatter")

    # Load from RequireKit
    scenarios = load_requirekit_scenarios(scenario_ids)
    task_context['gherkin_scenarios'] = scenarios

# Phase 3: Implementation
if mode == 'bdd':
    agent_context = {
        'mode': 'bdd',
        'scenarios': task_context['gherkin_scenarios'],
        'framework': detect_bdd_framework(),  # pytest-bdd, SpecFlow, etc.
    }
    result = invoke_agent('bdd-generator', agent_context)

# Phase 4: Testing
if mode == 'bdd':
    bdd_test_results = run_bdd_tests(stack_config)
    # Standard fix loop applies
```

**BDD Framework Detection**:
- Python → pytest-bdd
- .NET → SpecFlow
- TypeScript/JavaScript → Cucumber.js
- Ruby → Cucumber

**Testing**:
- [ ] Test full BDD workflow with Python project
- [ ] Verify Gherkin scenarios loaded correctly
- [ ] Verify step definitions generated
- [ ] Verify BDD tests execute
- [ ] Test fix loop with failing scenarios

**Reference**: `docs/research/restoring-bdd-feature.md` (Phase 3, lines 138-189)

---

### TASK-BDD-005: Integration Testing & Validation

**Priority**: High
**Estimated**: 30-45 minutes
**Type**: Testing
**Implementation**: `/task-work` (full quality gates)
**Wave**: 3 (depends on all previous tasks)

**Objective**: Comprehensive testing of BDD mode end-to-end

**Acceptance Criteria**:
- [ ] Test BDD workflow with LangGraph example scenario
- [ ] Test with RequireKit installed → full workflow succeeds
- [ ] Test without RequireKit → error message displays
- [ ] Test without bdd_scenarios → error with guidance
- [ ] Test with invalid scenario IDs → error from RequireKit
- [ ] Test BDD test failures → fix loop engages
- [ ] Test max retries exhausted → task blocked
- [ ] Verify documentation accuracy
- [ ] Verify error messages match docs

**Test Scenarios**:

1. **Happy Path** (LangGraph complexity routing):
   ```bash
   # Prerequisites:
   # - RequireKit installed
   # - BDD-ORCH-001 scenario exists in RequireKit
   # - Task has: bdd_scenarios: [BDD-ORCH-001]

   /task-work TASK-LG-001 --mode=bdd

   Expected:
   ✅ Loads Gherkin scenario
   ✅ Routes to bdd-generator
   ✅ Generates step definitions
   ✅ Implements complexity_router()
   ✅ Runs BDD tests
   ✅ All tests pass
   ✅ Task → IN_REVIEW
   ```

2. **RequireKit Not Installed**:
   ```bash
   /task-work TASK-LG-001 --mode=bdd

   Expected:
   ❌ ERROR: BDD mode requires RequireKit installation
   📖 Displays repo link and installation instructions
   📖 Suggests alternative modes
   ```

3. **No Scenarios Linked**:
   ```bash
   # Task missing bdd_scenarios field
   /task-work TASK-LG-001 --mode=bdd

   Expected:
   ❌ ERROR: BDD mode requires linked Gherkin scenarios
   📖 Shows frontmatter example
   📖 Shows /generate-bdd command
   ```

4. **BDD Test Failures**:
   ```bash
   # Scenario: complexity_router returns wrong value
   /task-work TASK-LG-001 --mode=bdd

   Expected:
   ✅ Implementation completes
   ❌ BDD tests fail (AssertionError)
   🔄 Fix loop attempt 1 (re-implement)
   ✅ Tests pass on retry
   ✅ Task → IN_REVIEW
   ```

**Documentation Verification**:
- [ ] Walkthrough docs/guides/bdd-workflow-for-agentic-systems.md
- [ ] Verify all examples work
- [ ] Verify error messages match reality
- [ ] Verify RequireKit link is correct

**Deliverables**:
- Test results document
- Screenshots of error messages
- Validation checklist completed

---

### TASK-BDD-006: Update RequireKit Agents to Discovery Format

**Priority**: High
**Estimated**: 1-2 hours
**Type**: Mass Refactoring
**Implementation**: Claude Code (direct)
**Wave**: 1 (parallel, different repo)

**Objective**: Update all RequireKit agents with GitHub-inspired format and frontmatter metadata

**Scope**: Different repository (`require-kit/`)

**Acceptance Criteria**:
- [ ] Update `bdd-generator` agent to GitHub agent format
- [ ] Add frontmatter metadata for discovery
- [ ] Add ALWAYS/NEVER/ASK boundary sections
- [ ] Update all other RequireKit agents similarly
- [ ] Maintain existing functionality
- [ ] Test agent discovery from GuardKit

**Agent Metadata Schema**:

```yaml
---
name: bdd-generator
description: Converts EARS requirements to Gherkin scenarios
version: 2.0.0
stack: [cross-stack]
phase: implementation
capabilities:
  - ears-to-gherkin
  - scenario-generation
  - given-when-then
  - acceptance-criteria
keywords:
  - bdd
  - gherkin
  - behavior-driven-development
  - ears
  - scenarios
  - feature-files
model: sonnet
author: RequireKit Team
---

# BDD Generator Agent

Converts EARS (Easy Approach to Requirements Syntax) requirements into Gherkin scenarios for Behavior-Driven Development workflows.

## Quick Start

This agent is invoked when:
- Task has `--mode=bdd` flag
- Task frontmatter includes `bdd_scenarios` field
- RequireKit is installed

**Input**: EARS requirement or task description
**Output**: Gherkin feature file with scenarios

## Boundaries

### ALWAYS
- ✅ Convert EARS Event-Driven → Given/When/Then scenarios (precise mapping)
- ✅ Use concrete examples in scenarios (avoid abstract placeholders)
- ✅ Tag scenarios by priority and category (enables selective test runs)
- ✅ Link scenarios to requirement IDs (maintains traceability)
- ✅ Generate scenario outlines for data-driven cases (DRY principle)

### NEVER
- ❌ Never create scenarios without clear acceptance criteria (ambiguity leads to incorrect tests)
- ❌ Never use implementation details in scenarios (breaks abstraction, couples to code)
- ❌ Never generate >20 scenarios per feature (indicates poor feature decomposition)
- ❌ Never skip Background sections when setup is common (violates DRY)
- ❌ Never use database-specific terminology in scenarios (breaks technology independence)

### ASK
- ⚠️ Multiple interpretation paths for requirement: Ask which behavior to prioritize
- ⚠️ Unclear edge case handling: Ask for business rule clarification
- ⚠️ Scenario complexity >7 steps: Ask if feature should be split

## Capabilities

### EARS to Gherkin Transformation

**Event-Driven Requirements**:
```
EARS: WHEN user submits login form, system SHALL authenticate credentials
```
```gherkin
Scenario: User login with valid credentials
  Given a user with email "user@example.com" and password "password123"
  When the user submits the login form
  Then the system should authenticate the credentials
  And the user should be redirected to the dashboard
```

[... rest of agent content ...]
```

**Agents to Update** (in require-kit repo):
1. `bdd-generator.md` (primary)
2. `requirement-formalizer.md`
3. `epic-manager.md`
4. `feature-generator.md`
5. Any other RequireKit-specific agents

**Testing**:
- [ ] GuardKit can discover bdd-generator via metadata
- [ ] Agent invocation works from GuardKit BDD mode
- [ ] Boundary sections validate correctly
- [ ] All existing RequireKit workflows still function

**Reference**:
- GitHub Agent Best Practices Analysis
- agent-content-enhancer.md (boundary section format)
- existing GuardKit agents for format examples

---

## Wave Execution Strategy

### Wave 1: Foundation (Day 1)

**Goal**: Parallel discovery, docs, and RequireKit updates

**Conductor Setup**:
```bash
# GuardKit repo
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave1-investigate TASK-BDD-001
conductor create-workspace bdd-wave1-docs TASK-BDD-002

# RequireKit repo (separate terminal)
cd ~/Projects/require-kit
conductor create-workspace bdd-wave1-requirekit TASK-BDD-006
```

**Execution**:
1. Start all 3 worktrees simultaneously
2. TASK-BDD-001: Investigate (30 min)
3. TASK-BDD-002: Write docs (45 min)
4. TASK-BDD-006: Update agents (1-2 hours)
5. Merge all when complete

**Exit Criteria**:
- Investigation findings documented
- BDD workflow guide complete
- RequireKit agents have discovery metadata

### Wave 2: Implementation (Day 2)

**Goal**: Sequential implementation of flag and workflow

**Conductor Setup**:
```bash
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave2-flag TASK-BDD-003
```

**Execution**:
1. Implement flag with marker detection
2. Test error messages
3. Merge to main
4. Create next workspace:
   ```bash
   conductor create-workspace bdd-wave2-workflow TASK-BDD-004
   ```
5. Implement workflow routing
6. Test with RequireKit
7. Merge to main

**Exit Criteria**:
- `--mode=bdd` flag works
- RequireKit detection functional
- BDD workflow routing complete

### Wave 3: Integration (Day 3)

**Goal**: End-to-end testing and validation

**Conductor Setup**:
```bash
cd ~/Projects/appmilla_github/guardkit
conductor create-workspace bdd-wave3-testing TASK-BDD-005
```

**Execution**:
1. Test all scenarios from acceptance criteria
2. Validate documentation accuracy
3. Test LangGraph workflow (dogfooding)
4. Fix any issues found
5. Merge to main

**Exit Criteria**:
- All test scenarios pass
- Documentation validated
- Ready for LangGraph implementation

---

## Success Metrics

### Functionality
- ✅ `/task-work TASK-XXX --mode=bdd` executes successfully
- ✅ Error message displays if RequireKit not installed
- ✅ Error message displays if scenarios not linked
- ✅ Gherkin scenarios load from RequireKit
- ✅ BDD tests execute in Phase 4
- ✅ Fix loop works for failing BDD tests

### Quality
- ✅ All quality gates enforced (same as standard/TDD)
- ✅ Architectural review scores ≥ 60/100
- ✅ Test pass rate = 100%
- ✅ Code review approved
- ✅ Documentation complete and accurate

### Integration
- ✅ RequireKit agent discovery works
- ✅ GuardKit → RequireKit delegation clean
- ✅ No DIP violations introduced
- ✅ LangGraph workflow executes end-to-end

### Architecture
- ✅ Feature detection pattern maintained
- ✅ Plugin delegation architecture preserved
- ✅ No code duplication (BDD logic in RequireKit only)
- ✅ Clear ownership boundaries

---

## References

### Documentation
- [TASK-2E9E Architectural Review (Final)](./../../../.claude/reviews/TASK-2E9E-architectural-review-FINAL.md)
- [BDD Mode Removal Decision](../../../docs/research/bdd-mode-removal-decision.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md)
- [TASK-037 Removal Task](../../completed/TASK-037/TASK-037-remove-bdd-mode.md)

### Research Documents
- LangGraph-Native_Orchestration_for_GuardKit_Technical_Architecture.md
- GuardKit_LangGraph_Orchestration_Build_Strategy.md

### Code References
- `installer/global/lib/feature_detection.py` (supports_bdd function)
- `installer/global/commands/task-work.md` (command specification)
- `.claude/agents/*.md` (agent format examples)

---

## Contingency Plans

### If RequireKit Changes Location

**Current assumption**: `~/.agentecflow/require-kit.marker`

**If changes**:
- Update marker path in TASK-BDD-003
- Update error messages
- Update documentation

### If Agent Discovery Doesn't Work

**Fallback**: Hardcode bdd-generator path temporarily
- Document as technical debt
- Create follow-up task for proper discovery

### If BDD Framework Detection Fails

**Fallback**: Require explicit `bdd_framework` in task frontmatter
```yaml
bdd_framework: pytest-bdd  # or SpecFlow, Cucumber.js
```

### If Integration Testing Reveals Issues

**Strategy**: Create follow-up fix tasks
- Don't block Wave 3 completion
- Document issues
- Fix in next iteration

---

## Post-Implementation

### Dogfooding with LangGraph

**After all waves complete**:
1. Create LangGraph epic in RequireKit
2. Formalize EARS for Phase 2.8 routing
3. Generate BDD scenarios
4. Create implementation tasks
5. Use `/task-work --mode=bdd`
6. Document lessons learned

### Blog Post Content

**"Building an AI Agent Orchestrator with BDD"**:
- Why agentic systems need formal specs
- EARS → Gherkin → Code traceability
- LangGraph state machine implementation
- Dogfooding GuardKit + RequireKit
- Lessons learned

### Feedback Collection

**Questions to answer**:
- Was BDD mode useful for LangGraph?
- Were error messages clear?
- Did documentation help?
- Any workflow friction points?
- Would recommend for similar projects?

---

**Status**: Ready for implementation
**Next Step**: Create individual task files and begin Wave 1
