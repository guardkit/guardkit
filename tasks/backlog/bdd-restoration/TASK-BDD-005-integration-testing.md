---
id: TASK-BDD-005
title: Integration testing and validation
status: backlog
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T15:27:39.493246+00:00
priority: high
tags: [bdd-restoration, testing, wave3]
complexity: 3
task_type: testing
estimated_effort: 30-45 minutes
wave: 3
parallel: false
implementation_method: task-work
parent_epic: bdd-restoration
depends_on: [TASK-BDD-002, TASK-BDD-003, TASK-BDD-004, TASK-BDD-006]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Integration testing and validation

## Context

Comprehensive end-to-end testing of BDD mode across all scenarios, including LangGraph complexity routing example.

**Parent Epic**: BDD Mode Restoration
**Wave**: 3 (Integration - after all other tasks complete)
**Implementation**: Use `/task-work` (full quality gates)
**Depends On**: All previous tasks (TASK-BDD-002,003,004,006)

## Description

Validate complete BDD workflow with:
- LangGraph complexity routing scenario
- Error handling scenarios
- Documentation accuracy
- RequireKit integration

This is the final validation before declaring BDD restoration complete.

## Acceptance Criteria

### Test Scenario 1: LangGraph Complexity Routing (Happy Path)

**Setup**:
```bash
# In RequireKit
cd ~/Projects/require-kit
cat > docs/bdd/BDD-ORCH-001.feature << 'GHERKIN'
Feature: Complexity-Based Routing
  Scenario: High complexity triggers mandatory review
    Given a task with complexity score 8
    When the workflow reaches Phase 2.8
    Then the system should invoke FULL_REQUIRED checkpoint
GHERKIN

# Create task
cd ~/Projects/taskwright  # Or test project
/task-create "Implement Phase 2.8 complexity routing"

# Edit task frontmatter:
bdd_scenarios: [BDD-ORCH-001]
```

**Execute**:
```bash
/task-work TASK-LG-001 --mode=bdd
```

**Expected Results**:
- [ ] ✅ Validates RequireKit installed
- [ ] ✅ Loads BDD-ORCH-001.feature
- [ ] ✅ Displays scenario content
- [ ] ✅ Routes to bdd-generator agent
- [ ] ✅ Generates step definitions (pytest-bdd)
- [ ] ✅ Implements `complexity_router()` function
- [ ] ✅ Runs BDD tests
- [ ] ✅ All tests pass
- [ ] ✅ Code review approves
- [ ] ✅ Task → IN_REVIEW

**Validation**:
- [ ] complexity_router() returns correct values
- [ ] Step definitions match scenario
- [ ] Tests are pytest-bdd compatible
- [ ] Code follows quality standards

### Test Scenario 2: RequireKit Not Installed

**Setup**:
```bash
# Temporarily hide marker (don't delete)
mv ~/.agentecflow/require-kit.marker ~/.agentecflow/require-kit.marker.bak
```

**Execute**:
```bash
/task-work TASK-XXX --mode=bdd
```

**Expected Results**:
- [ ] ❌ ERROR: BDD mode requires RequireKit installation
- [ ] 📖 Displays repository link
- [ ] 📖 Shows installation commands
- [ ] 📖 Suggests alternative modes
- [ ] 📖 Explains BDD use case (agentic systems)
- [ ] 🔢 Exit code: 1

**Cleanup**:
```bash
mv ~/.agentecflow/require-kit.marker.bak ~/.agentecflow/require-kit.marker
```

### Test Scenario 3: No BDD Scenarios Linked

**Setup**:
```bash
/task-create "Test no scenarios"
# Don't add bdd_scenarios field
```

**Execute**:
```bash
/task-work TASK-XXX --mode=bdd
```

**Expected Results**:
- [ ] ❌ ERROR: BDD mode requires linked Gherkin scenarios
- [ ] 📖 Shows frontmatter example
- [ ] 📖 Shows /generate-bdd command
- [ ] 📖 Suggests alternative modes
- [ ] 🔢 Exit code: 1

### Test Scenario 4: Scenario Not Found

**Setup**:
```bash
/task-create "Test missing scenario"

# Edit frontmatter:
bdd_scenarios: [BDD-NONEXISTENT]
```

**Execute**:
```bash
/task-work TASK-XXX --mode=bdd
```

**Expected Results**:
- [ ] ❌ ERROR: Scenario BDD-NONEXISTENT not found
- [ ] 📖 Shows expected file path
- [ ] 📖 Suggests /generate-bdd command
- [ ] 🔢 Exit code: 1

### Test Scenario 5: BDD Test Failures (Fix Loop)

**Setup**: Implement scenario with intentional bug

**Execute**:
```bash
/task-work TASK-XXX --mode=bdd
```

**Expected Results**:
- [ ] ✅ Implementation completes
- [ ] ❌ BDD tests fail (AssertionError)
- [ ] 📊 Shows test failure details
- [ ] 🔄 Fix loop attempt 1 initiated
- [ ] ✅ Tests pass on retry
- [ ] ✅ Task → IN_REVIEW

### Test Scenario 6: Max Retries Exhausted

**Setup**: Implement with persistent bug

**Expected Results**:
- [ ] ❌ Tests fail (attempt 1)
- [ ] 🔄 Fix loop attempt 2
- [ ] ❌ Tests fail (attempt 2)
- [ ] 🔄 Fix loop attempt 3
- [ ] ❌ Tests fail (attempt 3)
- [ ] 🚫 Max retries exhausted
- [ ] 📋 Task → BLOCKED

### Test Scenario 7: Documentation Walkthrough

**Execute**: Follow `docs/guides/bdd-workflow-for-agentic-systems.md` step-by-step

**Validate**:
- [ ] All bash commands work
- [ ] RequireKit link is correct
- [ ] Error messages match reality
- [ ] LangGraph example is complete
- [ ] Decision matrix is clear
- [ ] No broken links

### Test Scenario 8: Standard/TDD Modes Unaffected

**Execute**:
```bash
/task-work TASK-XXX --mode=standard
/task-work TASK-YYY --mode=tdd
```

**Expected Results**:
- [ ] ✅ Standard mode works normally
- [ ] ✅ TDD mode works normally
- [ ] ✅ No BDD-related errors
- [ ] ✅ No regression introduced

## Documentation Validation

### Check Error Messages

- [ ] RequireKit not installed → matches docs
- [ ] No scenarios linked → matches docs
- [ ] Scenario not found → matches docs
- [ ] All error messages clear and actionable

### Check CLAUDE.md

- [ ] BDD section exists
- [ ] Agentic systems focus clear
- [ ] RequireKit link correct
- [ ] Workflow example accurate

### Check .claude/CLAUDE.md

- [ ] BDD mode section exists
- [ ] Feature detection example correct
- [ ] Plugin discovery explanation clear

## Success Metrics

### Functionality
- [ ] All 8 test scenarios pass
- [ ] Error messages display correctly
- [ ] Fix loop works for BDD tests
- [ ] Standard/TDD modes unaffected

### Quality
- [ ] BDD tests execute correctly
- [ ] Framework detection works
- [ ] Quality gates enforced
- [ ] Code review passes

### Documentation
- [ ] All error messages match docs
- [ ] Walkthrough guide works
- [ ] Links are valid
- [ ] Examples are accurate

## Deliverables

**File**: `tasks/backlog/bdd-restoration/TASK-BDD-005-test-results.md`

**Content**:
- Test execution log for each scenario
- Screenshots of error messages
- Validation checklist results
- Issues found (if any)
- Recommendations for fixes

## Related Tasks

**Depends On**: All previous tasks (Wave 1 & 2)
**Blocks**: BDD mode release
**Wave**: 3 (final integration testing)

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [BDD Workflow Guide](../../../docs/guides/bdd-workflow-for-agentic-systems.md)
- [CLAUDE.md](../../../CLAUDE.md)
