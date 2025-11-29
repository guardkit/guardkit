# Testing Strategy - Pre-Public Launch

**Created**: 2025-11-29
**Status**: Planning phase
**Target Launch**: Next week
**Critical Context**: Conductor integration working great with task-complete changes

---

## Executive Summary

### Current State Analysis

**Recent Major Changes** (Last 2 weeks):
1. ✅ **BDD Mode Restoration** (5 tasks completed)
   - TASK-BDD-001 to TASK-BDD-005 all merged
   - Integration tests passing
   - Documentation complete

2. ✅ **Template Init & Hash-Based IDs** (completed)
   - Multiple documentation tasks (TASK-DOC-*)
   - GitHub Pages setup
   - Template philosophy updates

3. ✅ **Task Completion Conductor Integration** (working great)
   - State symlinks validated
   - Parallel development working

4. 📋 **Shared Agents Refactoring** (Phase 0 tasks created, not started)
   - 5 Phase 0 tasks ready
   - 33 additional tasks planned
   - 7-11 days estimated duration

### Your Question: Test Now or After Shared Agents?

**Recommendation**: **Test NOW, then implement shared agents**

**Reasoning**:

1. **Risk Mitigation**
   - 3 major feature sets already merged (BDD, template init, hash IDs)
   - Conductor integration changes are critical
   - Better to establish baseline before more changes
   - Shared agents is 7-11 days of work - too long to go untested

2. **Shared Agents is Actually Low Risk**
   - Mostly installation script changes
   - Agent discovery updates (already tested)
   - RequireKit changes isolated to different repo
   - High architectural review score (82/100)

3. **Testing Efficiency**
   - Quick validation now (2-3 hours)
   - Catches regressions from recent merges
   - Establishes baseline for shared agents changes
   - Re-test after shared agents will be faster (delta testing)

4. **Public Launch Confidence**
   - Validate BDD integration actually works end-to-end
   - Validate template init with hash IDs
   - Validate Conductor state management
   - Document any issues found
   - Fix before adding more complexity

---

## Testing Plan - Phase 1 (NOW - Pre-Shared-Agents)

**Duration**: 2-3 hours
**Goal**: Validate recent changes, establish baseline

### Test Categories

#### 1. Critical Path Testing (45 min)

**BDD Mode Integration**:
```bash
# Test 1: BDD mode with RequireKit installed
cd ~/Projects/test-project
/task-create "Test BDD workflow" task_type:implementation
# Add to frontmatter: bdd_scenarios: [BDD-TEST-001]
/task-work TASK-XXX --mode=bdd

Expected:
✅ Loads Gherkin scenarios
✅ Routes to bdd-generator
✅ Completes workflow

# Test 2: BDD mode without RequireKit
cd ~/Projects/test-project-no-requirekit
rm -f ~/.agentecflow/require-kit.marker
/task-work TASK-XXX --mode=bdd

Expected:
❌ Clear error message
📖 Installation instructions
📖 Alternative modes suggested
```

**Template Init with Hash IDs**:
```bash
# Test 3: Template initialization
mkdir -p ~/Projects/test-react-app
cd ~/Projects/test-react-app
git init
taskwright init react-typescript

Expected:
✅ Template files copied
✅ Agents installed
✅ Hash-based ID system ready
✅ /task-create works with hash IDs

# Test 4: Task creation with prefixes
/task-create "Fix bug" prefix:FIX
Expected: TASK-FIX-XXXX format

/task-create "Epic task" prefix:E01
Expected: TASK-E01-XXXX format
```

**Conductor State Management**:
```bash
# Test 5: Parallel task completion
cd ~/Projects/taskwright  # main repo
conductor create-workspace test-parallel-1 TASK-TEST-001
conductor create-workspace test-parallel-2 TASK-TEST-002

# In worktree 1
cd ../test-parallel-1
/task-work TASK-TEST-001
/task-complete TASK-TEST-001

# In worktree 2
cd ../test-parallel-2
/task-work TASK-TEST-002
/task-complete TASK-TEST-002

# Back in main
cd ~/Projects/taskwright
ls tasks/completed/

Expected:
✅ Both tasks in completed/
✅ State synced across worktrees
✅ No file conflicts
✅ Git history clean
```

#### 2. Regression Testing (30 min)

**Agent Discovery**:
```bash
# Test precedence order
cd ~/Projects/test-project
mkdir -p .claude/agents
cat > .claude/agents/test-agent.md << 'EOF'
---
name: test-agent
priority: 10
---
# Local Test Agent
EOF

# Verify local takes precedence
/task-work TASK-XXX  # Should use local agent if applicable
```

**Template Agent Enhancement**:
```bash
# Test Phase 8 task creation
/template-create --name test-template --create-agent-tasks

Expected:
✅ Template created
✅ Agent enhancement tasks created
✅ Tasks have correct metadata
```

**Quality Gates**:
```bash
# Test Phase 2.5 architectural review
/task-work TASK-XXX  # Should trigger review at complexity ≥7

# Test Phase 4.5 test enforcement
# (Create task with failing tests)
/task-work TASK-FAILING

Expected:
❌ Tests fail
🔄 Auto-fix attempts (up to 3)
🚫 Task blocked if all fail
```

#### 3. Integration Testing (45 min)

**BDD + Template Init + Hash IDs**:
```bash
# Complete workflow test
mkdir -p ~/Projects/test-full-stack
cd ~/Projects/test-full-stack
git init

# 1. Initialize with template
taskwright init react-typescript

# 2. Create BDD task with hash ID
/task-create "Implement auth with BDD" prefix:AUTH task_type:implementation
# Add bdd_scenarios: [BDD-AUTH-001]

# 3. Work on task with BDD mode
/task-work TASK-AUTH-XXXX --mode=bdd

# 4. Complete in Conductor worktree
conductor create-workspace auth-impl TASK-AUTH-XXXX
cd ../auth-impl
/task-work TASK-AUTH-XXXX --mode=bdd
/task-complete TASK-AUTH-XXXX

Expected:
✅ Full workflow completes
✅ Hash ID preserved
✅ BDD tests run
✅ State synced
✅ Task in completed/
```

**RequireKit Integration**:
```bash
# Verify RequireKit agents work from TaskWright
cd ~/Projects/test-project
/task-work TASK-XXX --mode=bdd  # Triggers RequireKit bdd-generator

Expected:
✅ Agent discovered in RequireKit
✅ Delegation works
✅ Step definitions generated
```

#### 4. Documentation Validation (30 min)

**Walkthroughs**:
- [ ] Follow BDD workflow guide exactly
- [ ] Follow template init guide exactly
- [ ] Follow hash ID migration guide exactly
- [ ] Verify all examples work
- [ ] Verify all error messages match docs

**Error Message Audit**:
- [ ] BDD mode without RequireKit shows correct error
- [ ] Missing bdd_scenarios shows correct error
- [ ] Invalid task ID format shows correct error
- [ ] All errors include actionable guidance

---

## Testing Plan - Phase 2 (AFTER Shared Agents)

**Duration**: 1-2 hours
**Goal**: Validate shared agents changes, delta from baseline

### Focus Areas

1. **Installation Script Changes**
   - Shared agents download works
   - Checksum validation works
   - Conflict detection works
   - Rollback procedures work

2. **Agent Discovery Updates**
   - Universal agent tier recognized
   - Precedence order: local > user > universal > global > template
   - No regressions in existing discovery

3. **RequireKit Integration**
   - Both repos use shared agents
   - Version pinning works
   - No duplication

### Test Scenarios (from TASK-SHA-002)

1. TaskWright standalone installation
2. RequireKit standalone installation
3. Combined installation (TaskWright first)
4. Combined installation (RequireKit first)
5. Version pinning (different versions)
6. Offline fallback (if implemented)
7. Conflict detection with local agents
8. Rollback to pre-migration state

---

## Risk Assessment

### High Confidence Areas ✅

1. **BDD Mode**
   - Comprehensive tests passed (TASK-BDD-005)
   - Integration validated
   - Documentation complete

2. **Hash-Based IDs**
   - Migration script tested
   - Documentation extensive
   - PM tool integration planned

3. **Conductor Integration**
   - Working great (your words!)
   - State symlinks validated
   - Parallel development proven

### Medium Confidence Areas ⚠️

1. **Template Init**
   - Phase 8 agent tasks created by default (TASK-UX-3A8D)
   - May have edge cases
   - Need walkthrough validation

2. **Agent Discovery**
   - Metadata-based discovery implemented
   - Graceful degradation for missing metadata
   - Need precedence order validation

### Low Confidence Areas ❌

1. **Shared Agents** (not implemented yet)
   - Installation script changes
   - Agent duplication verification needed (TASK-SHA-000)
   - Integration testing required

---

## Recommended Execution Plan

### Option A: Quick Validation (Recommended)

**Timeline**: Today (2-3 hours)

```bash
# 1. Run critical path tests (45 min)
# Focus: BDD, template init, Conductor state

# 2. Run regression tests (30 min)
# Focus: Agent discovery, quality gates

# 3. Quick integration test (45 min)
# Focus: Full workflow end-to-end

# 4. Document findings (30 min)
# Create: BASELINE-TEST-RESULTS.md

# 5. Proceed to shared agents Phase 0
# Start: TASK-SHA-000 (verification)
```

**Benefit**:
- 2-3 hour investment
- Validates recent changes
- Establishes baseline
- Catches any critical issues
- Confident start on shared agents

### Option B: Defer All Testing

**Timeline**: After shared agents complete (7-11 days from now)

```bash
# 1. Complete all 38 shared agents tasks
# 2. Test everything at once (4-6 hours)
# 3. Fix issues found
# 4. Re-test
```

**Risk**:
- 7-11 days of untested changes
- Hard to isolate regressions
- Could find issues requiring rework
- Delays public launch if issues found

### Option C: Comprehensive Testing

**Timeline**: 1-2 days

```bash
# Day 1: Extensive testing
# - All test categories
# - Performance benchmarks
# - Edge case exploration
# - Documentation audit

# Day 2: Issue remediation
# - Fix critical issues
# - Document medium/low issues
# - Re-test fixes
# - Update docs
```

**Benefit**:
- Highest confidence
- Thorough validation
- Production-ready

**Cost**:
- 1-2 days delay
- May be overkill for current state

---

## My Recommendation

### Execute Option A (Quick Validation) TODAY

**Why**:
1. **Shared agents is well-architected** (82/100 review score)
   - Most changes are installation scripts
   - Agent discovery already validated
   - Low regression risk

2. **Recent changes need validation**
   - BDD mode merged but not tested end-to-end in real workflow
   - Template init with default agent tasks needs walkthrough
   - Conductor state management working but not stress-tested

3. **Time-efficient**
   - 2-3 hours investment
   - High value for time spent
   - Establishes baseline for later testing

4. **Confidence builder**
   - Validates what you've built works
   - Documents current state
   - Reduces anxiety about public launch

### Then Execute Shared Agents Phase 0

**After quick validation**:
```bash
# Phase 0: Prerequisites (2 days)
/task-work TASK-SHA-000  # Verify agent duplication (MUST BE FIRST)
/task-work TASK-SHA-001  # Conflict detection
/task-work TASK-SHA-002  # Integration test cases
/task-work TASK-SHA-003  # Rollback procedures
/task-work TASK-SHA-004  # Checksum validation
```

**Benefits**:
- Phase 0 addresses all critical risks
- Creates test plan (TASK-SHA-002)
- Documents rollback (TASK-SHA-003)
- Low regression risk

### Then Test Again After Phase 5

**After shared agents complete**:
- Run integration tests from TASK-SHA-002
- Validate installation scripts
- Test RequireKit integration
- Document delta from baseline

---

## Test Execution Checklist

### Pre-Test Setup

- [ ] Backup current TaskWright state
- [ ] Create test project directory
- [ ] Ensure RequireKit installed
- [ ] Ensure Conductor installed
- [ ] Have test tasks ready

### During Testing

- [ ] Take screenshots of errors
- [ ] Document unexpected behavior
- [ ] Note performance issues
- [ ] Track test execution time
- [ ] Keep notes in BASELINE-TEST-RESULTS.md

### Post-Test

- [ ] Categorize findings (Critical/High/Medium/Low)
- [ ] Create fix tasks for critical issues
- [ ] Document known issues
- [ ] Update documentation if needed
- [ ] Archive test results

---

## Demo & Blog Content Creation

### After Quick Validation

**You can start creating**:
- Demo repository structure
- Blog post outline
- Video script outline
- Example workflows
- Screenshot placeholders

**Wait for shared agents before**:
- Recording final demo video
- Publishing blog post
- Announcing publicly
- Creating "getting started" content

**Why**:
- Shared agents is part of the story
- "Single source of truth for universal agents"
- Shows architectural maturity
- Better user experience

---

## Success Criteria

### Quick Validation (Phase 1)

✅ All critical path tests pass
✅ No regressions in agent discovery
✅ BDD mode works end-to-end
✅ Template init with hash IDs works
✅ Conductor state management validated
✅ Baseline documented

### Shared Agents (Phase 2)

✅ All Phase 0 tasks complete
✅ Integration test plan created
✅ Rollback procedures documented
✅ Conflict detection working
✅ Checksum validation working

### Public Launch Readiness

✅ All tests passing
✅ Demo repository created
✅ Blog post written
✅ Documentation complete
✅ Known issues documented
✅ Support channels ready

---

## Immediate Next Steps

1. **Now** (next 30 min):
   - [ ] Review this testing strategy
   - [ ] Decide: Option A, B, or C
   - [ ] Schedule testing time

2. **Today** (if Option A):
   - [ ] Run critical path tests (45 min)
   - [ ] Run regression tests (30 min)
   - [ ] Run integration test (45 min)
   - [ ] Document baseline (30 min)

3. **Tomorrow**:
   - [ ] Start TASK-SHA-000 (verification)
   - [ ] Continue Phase 0 tasks
   - [ ] Start demo content planning

4. **Next Week**:
   - [ ] Complete shared agents Phase 0-5
   - [ ] Test after Phase 5
   - [ ] Create demo repository
   - [ ] Write blog post
   - [ ] **GO PUBLIC** 🚀

---

## Questions to Answer Before Testing

1. **Do you have time today for 2-3 hours of testing?**
   - If yes: Option A (recommended)
   - If no: When can you allocate time?

2. **What's your risk tolerance?**
   - Low risk tolerance: Option C (comprehensive)
   - Medium risk tolerance: Option A (quick validation)
   - High risk tolerance: Option B (defer testing)

3. **What's your priority?**
   - Speed to public launch: Option A → Shared Agents → Test → Launch
   - Highest confidence: Option C → Shared Agents → Test → Launch
   - Minimal overhead: Option B (risky, not recommended)

4. **What issues would block public launch?**
   - BDD mode doesn't work: CRITICAL
   - Template init broken: CRITICAL
   - Conductor state issues: CRITICAL
   - Documentation errors: HIGH
   - Performance issues: MEDIUM
   - Edge cases: LOW

---

## My Strong Recommendation

**Execute Option A today**. Here's why:

1. **You've built amazing features** - BDD mode, hash IDs, template init
2. **You deserve to validate they work** - Confidence boost before launch
3. **2-3 hours is minimal investment** - High value for time
4. **Shared agents is low risk** - Well-architected, mostly installation scripts
5. **Testing now makes Phase 2 testing faster** - Delta testing vs full testing
6. **You're ready to go public next week** - This validates you're ready

**Let's validate what you've built works, then confidently execute shared agents Phase 0-5, then launch! 🚀**
