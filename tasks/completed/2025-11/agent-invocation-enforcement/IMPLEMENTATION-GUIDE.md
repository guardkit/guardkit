# Agent Invocation Enforcement - Implementation Guide

## Overview

This guide provides a phased implementation strategy for the agent invocation enforcement system, updated based on TASK-REV-9A4E architectural review findings. It includes:
- **Phase 0**: Foundation fixes (agent discovery) - CRITICAL, MUST DO FIRST
- Implementation method recommendations (task-work vs direct Claude Code)
- Parallel execution strategy using Conductor worktrees
- Wave-based deployment approach
- Testing and validation workflow

## CRITICAL UPDATE (2025-11-27)

**TASK-REV-9A4E architectural review identified critical gaps requiring immediate action before enforcement implementation.**

**Key Finding**: Agent discovery does NOT scan `.claude/agents/` directory where template-init copies local agents. This would cause enforcement mechanisms to generate false positives and block valid template workflows.

**Decision**: **PAUSE all enforcement implementation** until Phase 0 foundation fixes complete.

**Review Report**: `.claude/reviews/TASK-REV-9A4E-review-report.md`

---

## Revised Tasks Summary

### Phase 0: Foundation Fixes (CRITICAL - Do First)

| Task | Title | Effort | Priority | Dependencies |
|------|-------|--------|----------|--------------|
| **TASK-ENF-P0-1** | Fix Agent Discovery (scan .claude/agents/) | 2-3h | **CRITICAL** | None |
| **TASK-ENF-P0-2** | Update Agent Discovery Documentation | 1-2h | High | TASK-ENF-P0-1 |
| **TASK-ENF-P0-3** | Update template-init Agent Registration | 1-2h | Medium | TASK-ENF-P0-1 |
| **TASK-ENF-P0-4** | Update agent-enhance Metadata Validation | 2-3h | Medium | TASK-ENF-P0-1 |

**Phase 0 Total**: 6-10 hours (BLOCKING all enforcement tasks)

### Wave 1: Foundation (After Phase 0)

| Task | Title | Effort | Priority | Dependencies |
|------|-------|--------|----------|--------------|
| TASK-ENF2 | Agent Invocation Tracking (+ source paths) | 9-14h | Critical | Phase 0 complete |
| TASK-ENF3 | Prominent Invocation Messages | 2-4h | High | None |
| **TASK-ENF5-v2** | Dynamic Discovery (redesigned) | 2-3h | High | Phase 0 complete |

**Wave 1 Total**: 13-21 hours

### Wave 2: Enforcement Mechanisms (After Wave 1)

| Task | Title | Effort | Priority | Dependencies |
|------|-------|--------|----------|--------------|
| TASK-ENF1 | Pre-Report Validation (+ local agents) | 5-7h | Critical | TASK-ENF2, Phase 0 |
| TASK-ENF4 | Phase Gate Checkpoints (+ local agents) | 7-10h | High | TASK-ENF2, Phase 0 |

**Wave 2 Total**: 12-17 hours

**Revised Total Effort**: 31-48 hours (up from 21-32 hours)

---

## Implementation Method: task-work vs Direct Claude Code

### Use `/task-work` for Implementation Tasks

**Recommendation**: Use `/task-work` for all 5 tasks

**Rationale**:
1. ✅ **Quality Gates**: Phase 4.5 test enforcement ensures 100% test pass rate
2. ✅ **Architectural Review**: Phase 2.5 catches design issues before implementation
3. ✅ **Structured Approach**: Follows planning → implementation → testing → review workflow
4. ✅ **Traceability**: Creates implementation plans, ADRs, and changelogs
5. ✅ **Self-Dogfooding**: These tasks ARE implementing the very protocol enforcement we're testing

**Irony**: We're using `/task-work` to implement enforcement mechanisms that will improve `/task-work` itself. This is the perfect test case!

### Do NOT Use Direct Claude Code

**Why not direct implementation**:
- ❌ No architectural review (could introduce design issues)
- ❌ No test enforcement (might skip tests)
- ❌ No plan validation (scope creep risk)
- ❌ Misses opportunity to dogfood our own system

### Exception: TASK-ENF5 (Agent Table Update)

**This task is documentation-only** - Could be done directly, but still recommend `/task-work` in **micro mode** for consistency:

```bash
/task-work TASK-ENF5 --micro
```

**Micro mode benefits**:
- Simplified workflow (3-5 minutes vs 15+ minutes)
- Still gets linting and quick review
- Maintains traceability

---

## Phase 0: Foundation Fixes (MUST DO FIRST)

### Overview

**CRITICAL**: Phase 0 MUST be completed before any enforcement implementation. Without these fixes, enforcement mechanisms will generate false positives and break template workflows.

**Key Issue**: Agent discovery doesn't scan `.claude/agents/` where template-init copies local agents.

**Impact if skipped**:
- Template agents invisible to discovery
- Enforcement validation blocks valid tasks
- Users experience false-positive errors
- Template workflows broken

---

### Phase 0 Execution Plan

#### Task P0-1: Fix Agent Discovery (CRITICAL)

**Priority**: CRITICAL
**Effort**: 2-3 hours
**Blocks**: ALL enforcement tasks

**Objective**: Add `.claude/agents/` scanning to agent discovery with precedence rules

**Implementation**:
```bash
/task-work TASK-ENF-P0-1
```

**Acceptance Criteria**:
- [ ] Discovery scans `.claude/agents/` as Phase 1 (highest priority)
- [ ] Precedence rules: Local > User > Global > Template
- [ ] Duplicate agents removed (keeping highest priority)
- [ ] Source path logged on agent selection
- [ ] All unit tests pass

**Testing**:
```bash
# Initialize template
taskwright init react-typescript

# Verify agents copied
ls .claude/agents/react-state-specialist.md

# Run task and verify local agent selected
/task-create "Test discovery" stack:react
/task-work TASK-XXX
# Expected log: "Agent selected: react-state-specialist (source: local)"
```

---

#### Task P0-2: Update Agent Discovery Documentation

**Priority**: High
**Effort**: 1-2 hours
**Depends On**: TASK-ENF-P0-1

**Objective**: Document local agent scanning and precedence rules

**Implementation**:
```bash
/task-work TASK-ENF-P0-2
```

**Updates**:
- Add "Agent Sources and Discovery Order" section
- Document precedence: Local > User > Global > Template
- Add discovery flow diagram
- Add troubleshooting guide
- Update pseudo-code examples

---

#### Task P0-3: Update template-init Agent Registration

**Priority**: Medium
**Effort**: 1-2 hours
**Depends On**: TASK-ENF-P0-1

**Objective**: Verify agents discoverable after template initialization

**Implementation**:
```bash
/task-work TASK-ENF-P0-3
```

**Enhancements**:
- Verify agent metadata after copy
- Test discovery after initialization
- Report registered agents to user
- Handle missing metadata gracefully

---

#### Task P0-4: Update agent-enhance Metadata Validation

**Priority**: Medium
**Effort**: 2-3 hours
**Depends On**: TASK-ENF-P0-1

**Objective**: Ensure enhanced agents have discovery metadata

**Implementation**:
```bash
/task-work TASK-ENF-P0-4
```

**Enhancements**:
- Validate discovery metadata (stack, phase, capabilities, keywords)
- Prompt for missing metadata
- Verify discoverability after enhancement
- Update enhancement checklist

---

### Phase 0 Timeline

**Sequential Execution** (Recommended):
1. TASK-ENF-P0-1 (2-3 hours) - CRITICAL, do first
2. TASK-ENF-P0-2 (1-2 hours) - Can start immediately after P0-1
3. TASK-ENF-P0-3 + TASK-ENF-P0-4 (3-5 hours) - Can run in parallel after P0-1

**Total Phase 0 Duration**: 6-10 hours

**Parallel Optimization**:
- P0-1 first (critical path)
- P0-2 + P0-3 + P0-4 in parallel (saves 2-3 hours)
- Total with parallel: 4-7 hours

---

### Phase 0 Validation Checklist

Before proceeding to Wave 1, verify:

- [ ] **Discovery Fix**: `.claude/agents/` scanned with highest priority
- [ ] **Precedence Rules**: Local > User > Global > Template working
- [ ] **Documentation**: agent-discovery-guide.md updated and accurate
- [ ] **Template Init**: Agents verified discoverable after initialization
- [ ] **Agent Enhance**: Discovery metadata validated and added
- [ ] **Integration Test**: Template init → task-work uses local agent
- [ ] **No Regressions**: Existing projects work unchanged

**Test Command**:
```bash
# Full integration test
taskwright init react-typescript
/task-create "Integration test" stack:react
/task-work TASK-INT-001
# Expected: Local react-state-specialist invoked (not global)
```

---

## Wave-Based Implementation Strategy

### Wave 1: Foundation (Parallel Execution Possible)

**Goal**: Build tracking infrastructure and documentation improvements

**Tasks**:
- **TASK-ENF2** (Tracking) - Worktree: `wave-1-tracking`
- **TASK-ENF3** (Messages) - Worktree: `wave-1-messages`
- **TASK-ENF5** (Table Update) - Worktree: `wave-1-table`

**Why parallel**:
- Independent implementations (no code conflicts)
- Different files modified:
  - ENF2: Creates `lib/agent_invocation_tracker.py`
  - ENF3: Modifies `task-work.md` (different sections)
  - ENF5: Modifies `task-work.md` (agent table only)
- Can be tested independently

**Potential Conflict**: ENF3 and ENF5 both modify `task-work.md`
- **Resolution**: ENF5 touches only lines 968-980 (agent table)
- ENF3 touches phase sections (lines 1788+)
- Minimal merge conflict risk (different sections)

**Conductor Setup**:
```bash
# Create 3 parallel worktrees
conductor create wave-1-tracking --task=TASK-ENF2
conductor create wave-1-messages --task=TASK-ENF3
conductor create wave-1-table --task=TASK-ENF5

# Work in parallel across 3 terminals/windows
# Terminal 1:
cd wave-1-tracking
/task-work TASK-ENF2

# Terminal 2:
cd wave-1-messages
/task-work TASK-ENF3

# Terminal 3:
cd wave-1-table
/task-work TASK-ENF5 --micro
```

**Wave 1 Duration**: 8-12 hours (parallel) vs 11-18 hours (sequential)
**Savings**: 3-6 hours with parallel execution

---

### Wave 2: Enforcement Mechanisms (Sequential - Depends on Wave 1)

**Goal**: Implement validation checkpoints using tracking from Wave 1

**Tasks**:
- **TASK-ENF1** (Pre-Report Validation) - Depends on TASK-ENF2
- **TASK-ENF4** (Phase Gate Checkpoints) - Depends on TASK-ENF2

**Why sequential within Wave 2**:
- Both depend on `AgentInvocationTracker` from TASK-ENF2
- Both modify `task-work.md` (enforcement sections)
- High merge conflict risk if done in parallel

**Sequential Order**: TASK-ENF1 → TASK-ENF4
- ENF1 is simpler (single checkpoint before final report)
- ENF4 is more complex (5 phase gates throughout workflow)
- ENF1 completion validates tracker API is stable for ENF4

**Conductor Setup**:
```bash
# After Wave 1 completes and merges to main

# Task 1: Pre-Report Validation
conductor create wave-2-validation --task=TASK-ENF1
cd wave-2-validation
/task-work TASK-ENF1
# Complete, review, merge to main

# Task 2: Phase Gate Checkpoints (after ENF1 merged)
conductor create wave-2-phase-gates --task=TASK-ENF4
cd wave-2-phase-gates
/task-work TASK-ENF4
# Complete, review, merge to main
```

**Wave 2 Duration**: 10-14 hours (sequential only)

---

## Detailed Wave Execution Plan

### Wave 1: Foundation (Parallel)

#### Worktree 1: TASK-ENF2 (Agent Invocation Tracking)

**Branch**: `feature/agent-invocation-tracking`

**Files Modified**:
- `installer/global/commands/lib/agent_invocation_tracker.py` (NEW)
- `installer/global/commands/lib/__init__.py` (add import)
- `installer/global/commands/task-work.md` (add tracker initialization, calls)
- Tests: `tests/test_agent_invocation_tracker.py` (NEW)

**Execution**:
```bash
conductor create wave-1-tracking --task=TASK-ENF2
cd wave-1-tracking
/task-work TASK-ENF2

# When complete:
conductor review wave-1-tracking
conductor merge wave-1-tracking  # Merge to main
```

**Expected Duration**: 8-12 hours

**Acceptance Criteria**:
- [ ] `AgentInvocationTracker` class created
- [ ] Running log displays after each phase
- [ ] Tracker persists across all phases
- [ ] All tests pass

---

#### Worktree 2: TASK-ENF3 (Prominent Invocation Messages)

**Branch**: `feature/prominent-invocation-messages`

**Files Modified**:
- `installer/global/commands/lib/agent_display.py` (NEW)
- `installer/global/commands/task-work.md` (modify Phase 2, 2.5B, 3, 4, 5 sections)
- Tests: `tests/test_agent_display.py` (NEW)

**Execution**:
```bash
conductor create wave-1-messages --task=TASK-ENF3
cd wave-1-messages
/task-work TASK-ENF3

# When complete:
conductor review wave-1-messages
conductor merge wave-1-messages  # Merge to main
```

**Expected Duration**: 2-4 hours

**Acceptance Criteria**:
- [ ] Pre-invocation messages displayed (🤖 INVOKING AGENT)
- [ ] Post-completion messages displayed (✅ AGENT COMPLETED)
- [ ] Model selection transparent (Haiku vs Sonnet)
- [ ] All 5 phases updated

---

#### Worktree 3: TASK-ENF5 (Update Agent Selection Table)

**Branch**: `feature/update-agent-table`

**Files Modified**:
- `installer/global/commands/task-work.md` (modify agent selection table, lines 968-980)
- `installer/global/agents/maui-usecase-specialist.md` (NEW - if decision is to create)

**Execution**:
```bash
conductor create wave-1-table --task=TASK-ENF5
cd wave-1-table
/task-work TASK-ENF5 --micro  # Micro mode (documentation task)

# When complete:
conductor review wave-1-table
conductor merge wave-1-table  # Merge to main
```

**Expected Duration**: 1-2 hours (without creating specialist), 4-5 hours (with)

**Acceptance Criteria**:
- [ ] Agent table references only existing agents
- [ ] Notes column explains agent selection
- [ ] Decision on maui-usecase-specialist documented
- [ ] Fallback behavior clear

---

### Wave 1: Merge Strategy

**After all 3 tasks complete**, merge in this order:

1. **TASK-ENF5** (Agent Table) - Smallest, lowest risk
2. **TASK-ENF2** (Tracking) - Foundation for Wave 2
3. **TASK-ENF3** (Messages) - Cosmetic changes, low risk

**Merge Commands**:
```bash
# Merge ENF5 first (agent table)
git checkout main
git merge feature/update-agent-table
git push

# Merge ENF2 second (tracking)
git checkout main
git merge feature/agent-invocation-tracking
# Resolve any conflicts with ENF5 (unlikely)
git push

# Merge ENF3 third (messages)
git checkout main
git merge feature/prominent-invocation-messages
# Resolve any conflicts with ENF2/ENF5
git push
```

**Conflict Resolution**:
- ENF3 + ENF5 may conflict in `task-work.md` if both modify overlapping sections
- Resolution: Accept both changes (different sections)
- ENF2 + ENF3 may conflict in `task-work.md` phase sections
- Resolution: Integrate tracker calls (ENF2) with display messages (ENF3)

---

### Wave 2: Enforcement Mechanisms (Sequential)

#### Task 1: TASK-ENF1 (Pre-Report Validation)

**Branch**: `feature/pre-report-validation`

**Files Modified**:
- `installer/global/commands/lib/agent_invocation_validator.py` (NEW)
- `installer/global/commands/task-work.md` (add Step 10.5 validation)
- `installer/global/commands/lib/task_state_manager.py` (modify - add BLOCKED state handling)
- Tests: `tests/test_agent_invocation_validator.py` (NEW)

**Dependencies**: TASK-ENF2 (requires `AgentInvocationTracker`)

**Execution**:
```bash
# After Wave 1 fully merged to main
conductor create wave-2-validation --task=TASK-ENF1
cd wave-2-validation
/task-work TASK-ENF1

# When complete:
conductor review wave-2-validation
conductor merge wave-2-validation
```

**Expected Duration**: 4-6 hours

**Acceptance Criteria**:
- [ ] Validation runs before final report
- [ ] Task BLOCKED if agents not invoked
- [ ] Clear error message shows missing phases
- [ ] All tests pass

---

#### Task 2: TASK-ENF4 (Phase Gate Checkpoints)

**Branch**: `feature/phase-gate-checkpoints`

**Files Modified**:
- `installer/global/commands/lib/phase_gate_validator.py` (NEW)
- `installer/global/commands/task-work.md` (add phase gates after each phase)
- Tests: `tests/test_phase_gate_validator.py` (NEW)

**Dependencies**: TASK-ENF2 (requires `AgentInvocationTracker`)

**Execution**:
```bash
# After TASK-ENF1 merged to main
conductor create wave-2-phase-gates --task=TASK-ENF4
cd wave-2-phase-gates
/task-work TASK-ENF4

# When complete:
conductor review wave-2-phase-gates
conductor merge wave-2-phase-gates
```

**Expected Duration**: 6-8 hours

**Acceptance Criteria**:
- [ ] Phase gate after each of 5 phases
- [ ] Task BLOCKED if agent not invoked
- [ ] Cannot proceed to next phase on failure
- [ ] All tests pass

---

## Testing Strategy

### Unit Testing (During Implementation)

Each task includes unit tests executed in Phase 4:

**TASK-ENF2** (Tracking):
```bash
pytest tests/test_agent_invocation_tracker.py -v
```

**TASK-ENF3** (Messages):
```bash
pytest tests/test_agent_display.py -v
```

**TASK-ENF1** (Validation):
```bash
pytest tests/test_agent_invocation_validator.py -v
```

**TASK-ENF4** (Phase Gates):
```bash
pytest tests/test_phase_gate_validator.py -v
```

### Integration Testing (After Each Wave)

**After Wave 1**:
```bash
# Test that tracking works end-to-end
cd /path/to/test/project
taskwright init python
/task-create "Test tracking implementation"
/task-work TASK-XXX

# Expected: Running log displayed after each phase
# Expected: Agent invocations visible
```

**After Wave 2**:
```bash
# Test validation and phase gates
/task-create "Test enforcement implementation"
/task-work TASK-XXX

# Expected: Pre-report validation runs
# Expected: Phase gates validate after each phase
# Expected: Task BLOCKED if protocol violated
```

### Dogfooding Test (MyDrive Scenario)

**Reproduce MyDrive TASK-ROE-007g issue** to verify enforcement prevents it:

```bash
# Simulate Phase 3 direct implementation (bypassing agent)
# Expected after Wave 1: Log shows Phase 3 skipped
# Expected after Wave 2: Phase 3 gate BLOCKS task, prevents Phase 4
```

**Success Criteria**:
- [ ] Wave 1: Tracking log shows Phase 3 skipped (visibility improvement)
- [ ] Wave 2 (ENF4): Phase 3 gate blocks progression (enforcement working)
- [ ] Wave 2 (ENF1): Pre-report validation blocks final report (safety net working)

---

## Rollout Plan

### Stage 1: Wave 1 Deployment (Low Risk)

**Deploy**: TASK-ENF2, TASK-ENF3, TASK-ENF5 (foundation + visibility)

**Risk**: Low - No blocking behavior yet
- Tracking is passive (logs only)
- Messages are cosmetic
- Table update is documentation

**Rollback**: Easy - Revert 3 PRs if issues found

**Validation**:
- [ ] Run existing tasks - no behavior changes
- [ ] Verify tracking log appears
- [ ] Verify messages display correctly

---

### Stage 2: Wave 2 Deployment (Medium Risk)

**Deploy**: TASK-ENF1, TASK-ENF4 (enforcement mechanisms)

**Risk**: Medium - Introduces blocking behavior
- Tasks can now be BLOCKED if protocol violated
- Potential for false positives (incorrect BLOCKED state)

**Gradual Rollout** (Recommended):

**Step 1**: Deploy TASK-ENF1 only (pre-report validation)
- Test on 5-10 tasks
- Monitor for false positives
- If stable after 1 week, proceed to Step 2

**Step 2**: Deploy TASK-ENF4 (phase gates)
- Test on 5-10 tasks
- Monitor for false positives
- Full rollout after 1 week

**Rollback**: Medium difficulty
- Disable validation checkpoints (comment out)
- Revert PRs if major issues

**Validation**:
- [ ] Run 10 test tasks successfully
- [ ] Verify protocol violations are caught
- [ ] Verify no false positives (tasks incorrectly BLOCKED)
- [ ] Monitor for 1 week before full rollout

---

## Parallel Execution with Conductor

### Setup Conductor Worktrees

**Install Conductor** (if not already):
```bash
# See https://conductor.build
```

**Initialize Project**:
```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright
conductor init
```

### Wave 1: Create 3 Parallel Worktrees

```bash
# Terminal 1: Tracking
conductor create wave-1-tracking \
  --branch=feature/agent-invocation-tracking \
  --task=TASK-ENF2

# Terminal 2: Messages
conductor create wave-1-messages \
  --branch=feature/prominent-invocation-messages \
  --task=TASK-ENF3

# Terminal 3: Table Update
conductor create wave-1-table \
  --branch=feature/update-agent-table \
  --task=TASK-ENF5
```

### Work in Parallel

**Terminal 1** (wave-1-tracking):
```bash
cd wave-1-tracking
/task-work TASK-ENF2
# Wait for completion (8-12 hours)
conductor review wave-1-tracking
```

**Terminal 2** (wave-1-messages):
```bash
cd wave-1-messages
/task-work TASK-ENF3
# Wait for completion (2-4 hours)
conductor review wave-1-messages
```

**Terminal 3** (wave-1-table):
```bash
cd wave-1-table
/task-work TASK-ENF5 --micro
# Wait for completion (1-2 hours)
conductor review wave-1-table
```

### Merge Wave 1 Results

```bash
# After all 3 complete and pass review
conductor merge wave-1-table          # Merge first (smallest)
conductor merge wave-1-tracking       # Merge second (foundation)
conductor merge wave-1-messages       # Merge third (cosmetic)

# Cleanup worktrees
conductor cleanup wave-1-table
conductor cleanup wave-1-tracking
conductor cleanup wave-1-messages
```

### Wave 2: Sequential Execution

```bash
# Task 1: Pre-Report Validation
conductor create wave-2-validation \
  --branch=feature/pre-report-validation \
  --task=TASK-ENF1

cd wave-2-validation
/task-work TASK-ENF1
conductor review wave-2-validation
conductor merge wave-2-validation
conductor cleanup wave-2-validation

# Task 2: Phase Gate Checkpoints (after ENF1 merged)
conductor create wave-2-phase-gates \
  --branch=feature/phase-gate-checkpoints \
  --task=TASK-ENF4

cd wave-2-phase-gates
/task-work TASK-ENF4
conductor review wave-2-phase-gates
conductor merge wave-2-phase-gates
conductor cleanup wave-2-phase-gates
```

---

## Expected Timeline

### Parallel Execution (Recommended)

**Wave 1** (Parallel):
- Longest task: TASK-ENF2 (8-12 hours)
- Wave 1 completes in: **12 hours max** (vs 18 hours sequential)
- **Savings: 6 hours**

**Wave 2** (Sequential):
- TASK-ENF1: 4-6 hours
- TASK-ENF4: 6-8 hours
- Wave 2 total: **10-14 hours**

**Total**: 22-26 hours (with parallel) vs 28-32 hours (sequential)
**Overall Savings**: 6-8 hours with Conductor parallel execution

### Sequential Execution (Fallback)

If parallel execution not feasible:

**Week 1**: TASK-ENF2 (8-12 hours)
**Week 1**: TASK-ENF3 (2-4 hours)
**Week 1**: TASK-ENF5 (1-2 hours)
**Week 2**: TASK-ENF1 (4-6 hours)
**Week 2**: TASK-ENF4 (6-8 hours)

**Total**: 21-32 hours over 2 weeks

---

## Success Metrics

### Wave 1 Success

- [ ] Tracking log displays correctly in all test tasks
- [ ] Invocation messages visible and clear
- [ ] Agent table references only existing agents
- [ ] No regressions (existing tasks work unchanged)

### Wave 2 Success

- [ ] Pre-report validation catches protocol violations
- [ ] Phase gates block progression when agents not invoked
- [ ] No false positives (0% incorrectly BLOCKED tasks)
- [ ] MyDrive scenario (TASK-ROE-007g) would be caught by enforcement

### Overall Success

- [ ] 100% of tasks use agents correctly (no direct implementation)
- [ ] 0% false reporting (agents used list matches actual invocations)
- [ ] User confidence: "I can see which agents are being used"
- [ ] Protocol compliance: Violations impossible to miss

---

## Recommendations

### For Maximum Efficiency

1. ✅ **Use Conductor** for Wave 1 parallel execution (saves 6 hours)
2. ✅ **Use `/task-work`** for all 5 tasks (dogfooding + quality gates)
3. ✅ **Deploy in waves** (Wave 1 = foundation, Wave 2 = enforcement)
4. ✅ **Test between waves** (validate Wave 1 before starting Wave 2)
5. ✅ **Gradual Wave 2 rollout** (ENF1 first, monitor, then ENF4)

### For Safety

1. ⚠️ **Monitor after Wave 2** (new blocking behavior)
2. ⚠️ **Have rollback plan** (disable checkpoints if false positives)
3. ⚠️ **Test on non-critical tasks first** (validate enforcement logic)

---

## Quick Start

**To begin Wave 1 immediately**:

```bash
# Setup
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright

# Create 3 parallel worktrees
conductor create wave-1-tracking --task=TASK-ENF2
conductor create wave-1-messages --task=TASK-ENF3
conductor create wave-1-table --task=TASK-ENF5

# Execute in parallel (3 terminals)
# Terminal 1:
cd wave-1-tracking && /task-work TASK-ENF2

# Terminal 2:
cd wave-1-messages && /task-work TASK-ENF3

# Terminal 3:
cd wave-1-table && /task-work TASK-ENF5 --micro
```

---

## Questions?

- **Can we do all 5 in parallel?** No - TASK-ENF1 and TASK-ENF4 depend on TASK-ENF2 (tracking)
- **Can we skip Wave 1?** No - Wave 2 requires tracking from TASK-ENF2
- **Can we do Wave 2 in parallel?** Not recommended - both modify same sections of `task-work.md`
- **Should we use direct Claude Code?** No - use `/task-work` for all tasks (dogfooding + quality gates)
- **What if we don't have Conductor?** Execute sequentially, prioritize TASK-ENF2 → TASK-ENF1 first

---

---

## Revised Implementation Summary (Post TASK-REV-9A4E)

### Critical Changes

1. **Phase 0 Added** (6-10 hours) - CRITICAL foundation fixes
   - Fix agent discovery to scan `.claude/agents/`
   - Implement precedence rules (Local > User > Global > Template)
   - Update documentation and related commands

2. **TASK-ENF5 Redesigned** → **TASK-ENF5-v2**
   - Old approach: Hardcode global agent names in table
   - New approach: Use dynamic discovery, document precedence
   - Effort increased: 1-2h → 2-3h

3. **TASK-ENF1 Enhanced** (4-6h → 5-7h)
   - Add local agent validation support
   - Handle template agent precedence

4. **TASK-ENF2 Enhanced** (8-12h → 9-14h)
   - Add agent source path tracking
   - Log local/user/global source

5. **TASK-ENF4 Enhanced** (6-8h → 7-10h)
   - Add local agent gate validation
   - Precedence-aware checkpoints

### Timeline Comparison

**Original Plan**:
- Total: 21-32 hours
- 2 Waves (Wave 1 parallel, Wave 2 sequential)

**Revised Plan**:
- Total: 31-48 hours (+10-16 hours)
- Phase 0 (4-10 hours) + 2 Waves
- Phase 0 MUST complete before Waves

### Revised Execution Order

```
Phase 0: Foundation Fixes (4-10 hours)
├── TASK-ENF-P0-1 (Fix agent discovery) [CRITICAL]
├── TASK-ENF-P0-2 (Update documentation)
├── TASK-ENF-P0-3 (Update template-init)
└── TASK-ENF-P0-4 (Update agent-enhance)

↓ (Phase 0 validation checkpoint)

Wave 1: Foundation (13-21 hours, parallel possible)
├── TASK-ENF2 (Tracking + source paths)
├── TASK-ENF3 (Invocation messages)
└── TASK-ENF5-v2 (Dynamic discovery)

↓ (Wave 1 merge and validation)

Wave 2: Enforcement (12-17 hours, sequential)
├── TASK-ENF1 (Pre-report validation + local agents)
└── TASK-ENF4 (Phase gates + local agents)

↓ (Wave 2 gradual rollout)

Total: 31-48 hours (with parallelization optimizations)
```

### Key Success Factors

1. **DO NOT skip Phase 0** - Enforcement will break templates without it
2. **Validate Phase 0 thoroughly** - All templates must work before Wave 1
3. **Test local agent precedence** - Critical for template customization
4. **Use parallel execution where possible** - Saves 6-10 hours
5. **Gradual Wave 2 rollout** - Monitor for false positives

### Risk Mitigation

**Risk**: Phase 0 takes longer than estimated
**Mitigation**: P0-1 is critical path (2-3h), others can be delayed if needed

**Risk**: False positives in enforcement (Wave 2)
**Mitigation**: Gradual rollout, easy rollback, extensive testing

**Risk**: Breaking template workflows
**Mitigation**: Phase 0 fixes + validation before Wave 1

---

**Last Updated**: 2025-11-27
**Version**: 2.0 (Post TASK-REV-9A4E)
**Related Reviews**: TASK-8D3F, TASK-REV-9A4E
**Review Report**: .claude/reviews/TASK-REV-9A4E-review-report.md
