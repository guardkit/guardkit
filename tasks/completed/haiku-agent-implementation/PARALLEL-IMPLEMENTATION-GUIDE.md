# Parallel Implementation Guide: Agentic Help System

**Created**: 2025-11-25
**Timeline Goal**: 3-4 days before blog post
**Parallelization Tool**: Conductor.build (git worktrees)
**Total Tasks**: 14 (HAI-001 through HAI-014)

---

## Executive Summary

This guide provides a 4-wave implementation strategy optimized for Conductor git worktrees, balancing parallelization, risk mitigation, and state consistency. The strategy completes in **3.5-4.5 days** with **4-6 parallel workspaces** at peak, using a mix of `/task-work` and direct Claude Code implementation.

**Key Decisions**:
- **High-risk tasks** (5): Use `/task-work` with full quality gates
- **Low-risk tasks** (9): Direct Claude Code implementation
- **4 waves**: Foundation → Agents → Discovery → Finalization
- **6 workspaces maximum**: Efficient resource allocation
- **100% state consistency**: Symlink architecture verified

---

## Table of Contents

1. [Task Classification Matrix](#1-task-classification-matrix)
2. [Wave-Based Implementation Plan](#2-wave-based-implementation-plan)
3. [Conductor Workspace Strategy](#3-conductor-workspace-strategy)
4. [Checkpoint Workflow](#4-checkpoint-workflow)
5. [Risk Matrix](#5-risk-matrix)
6. [Timeline Projections](#6-timeline-projections)
7. [Execution Playbook](#7-execution-playbook)

---

## 1. Task Classification Matrix

### Classification Criteria

**Use `/task-work` when**:
- Complex logic requiring architectural review
- Integration with existing code (risk of scope creep)
- Testing validation critical
- State transitions managed by workflow

**Use Direct Claude Code when**:
- Simple file creation (templates/scaffolding)
- Repetitive metadata updates
- Documentation-only changes
- No integration points with existing code

### Task Classification Table

| Task ID | Title | Use /task-work? | Rationale | Workspace | Duration |
|---------|-------|----------------|-----------|-----------|----------|
| **HAI-001** | Design schema | ✅ Yes | Complex logic, needs review | WS-Main | 1.5h |
| **HAI-002** | Python API specialist | ❌ No | New agent file (template) | WS-A | 2h |
| **HAI-003** | React State specialist | ❌ No | New agent file (template) | WS-B | 2h |
| **HAI-004** | .NET Domain specialist | ❌ No | New agent file (template) | WS-C | 2h |
| **HAI-005** | Discovery algorithm | ✅ Yes | Complex matching logic | WS-A | 3h |
| **HAI-006** | Integration w/ task-work | ✅ Yes | Touches existing code | WS-D | 2h |
| **HAI-007** | Documentation | ❌ No | Writing only | WS-A | 1.5h |
| **HAI-008** | E2E testing | ✅ Yes | Validation critical | WS-B | 2h |
| **HAI-009** | Update 12 global agents | ❌ No | Bulk metadata updates | WS-E | 4-6h |
| **HAI-010** | react-typescript agents | ❌ No | Template metadata | WS-B | 1-1.5h |
| **HAI-011** | fastapi-python agents | ❌ No | Template metadata | WS-C | 1-1.5h |
| **HAI-012** | nextjs-fullstack agents | ❌ No | Template metadata | WS-D | 1-1.5h |
| **HAI-013** | react-fastapi-monorepo | ❌ No | Template metadata | WS-E | 1-1.5h |
| **HAI-014** | taskwright-python agents | ❌ No | Template metadata | WS-F | 1-1.5h |

**Summary**:
- `/task-work`: 5 tasks (HAI-001, 005, 006, 008)
- Direct: 10 tasks (HAI-002, 003, 004, 007, 009-014)

---

## 2. Wave-Based Implementation Plan

### Wave 1: Foundation + Agent Creation (Parallel)

**Objective**: Establish schema and create new global agents
**Duration**: 2 hours (parallel)
**Parallelization**: 4 workspaces

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ WS-Main     │ WS-A        │ WS-B        │ WS-C        │
├─────────────┼─────────────┼─────────────┼─────────────┤
│ HAI-001     │ HAI-002     │ HAI-003     │ HAI-004     │
│ Schema      │ Python API  │ React State │ .NET Domain │
│ (1.5h)      │ (2h)        │ (2h)        │ (2h)        │
│ /task-work  │ Direct      │ Direct      │ Direct      │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

**Tasks**:
- **HAI-001** (WS-Main): Design agentic help schema - `/task-work` (complexity ~5/10)
  - Phases: Planning → Architectural Review → Implementation → Testing
  - Output: Schema definitions, validation logic
  - Critical: Must complete before agents reference schema

- **HAI-002** (WS-A): Create Python API specialist agent - Direct
  - Copy template from existing specialist agent
  - Add `agentic_help` metadata to frontmatter
  - Update capabilities, boundaries, examples

- **HAI-003** (WS-B): Create React State specialist agent - Direct
  - Same approach as HAI-002
  - Focus on state management patterns

- **HAI-004** (WS-C): Create .NET Domain specialist agent - Direct
  - Same approach as HAI-002
  - Focus on DDD patterns

**Dependencies**: None (fully parallelizable)

**Checkpoint**: After Wave 1
- Review HAI-001 schema design (5 min)
- Spot-check new agents (10 min)
- **Total checkpoint**: 15 minutes

**Wave 1 Total**: 2 hours work + 15 min checkpoint = **2.25 hours**

---

### Wave 2: Agent Updates (Parallel by Category)

**Objective**: Update existing global agents and template agents
**Duration**: 4-6 hours (parallel)
**Parallelization**: 6 workspaces

```
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ WS-A        │ WS-B        │ WS-C        │ WS-D        │ WS-E        │ WS-F        │
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│             │ HAI-010     │ HAI-011     │ HAI-012     │ HAI-013     │ HAI-014     │
│             │ react-ts    │ fastapi     │ nextjs      │ monorepo    │ taskwright  │
│             │ (1-1.5h)    │ (1-1.5h)    │ (1-1.5h)    │ (1-1.5h)    │ (1-1.5h)    │
│             │ Direct      │ Direct      │ Direct      │ Direct      │ Direct      │
├─────────────┴─────────────┴─────────────┴─────────────┴─────────────┴─────────────┤
│ HAI-009: Update 12 global agents (4-6h, batched across workspaces)                │
│ WS-E: Batch 1 (4 agents: architectural-reviewer, code-reviewer, test-verifier,    │
│       software-architect) - 1.5-2h                                                 │
│ WS-A: Batch 2 (4 agents: task-manager, devops, security, database) - 1.5-2h       │
│ WS-D: Batch 3 (4 agents: remaining global agents) - 1.5-2h                        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

**Tasks**:
- **HAI-009** (WS-A, WS-D, WS-E): Update 12 global agents - Direct (batched)
  - Batch 1 (WS-E): architectural-reviewer, code-reviewer, test-verifier, software-architect
  - Batch 2 (WS-A): task-manager, devops-specialist, security-specialist, database-specialist
  - Batch 3 (WS-D): Remaining 4 global agents
  - Per agent: Add `agentic_help` section with capabilities, use_cases, integration_points
  - Validation script to ensure consistency

- **HAI-010** (WS-B): react-typescript template agents - Direct
  - Update 3 agents in template directory
  - Add `agentic_help` metadata

- **HAI-011** (WS-C): fastapi-python template agents - Direct
  - Same as HAI-010

- **HAI-012** (WS-D): nextjs-fullstack template agents - Direct
  - Same as HAI-010

- **HAI-013** (WS-E): react-fastapi-monorepo template agents - Direct
  - Same as HAI-010

- **HAI-014** (WS-F): taskwright-python template agents - Direct
  - Same as HAI-010

**Dependencies**: HAI-001 complete (schema defined)

**Checkpoint**: After Wave 2
- Validate all metadata consistency (10 min automated)
- Spot-check 3-4 agents (10 min)
- **Total checkpoint**: 20 minutes

**Wave 2 Total**: 6 hours work (parallel) + 20 min checkpoint = **6.3 hours**

---

### Wave 3: Discovery System (Sequential)

**Objective**: Build discovery algorithm and integrate with /task-work
**Duration**: 5 hours (sequential)
**Parallelization**: 1 workspace (sequential dependency)

```
┌─────────────────────────────────────┐
│ WS-A (Sequential)                   │
├─────────────────────────────────────┤
│ HAI-005: Discovery algorithm (3h)   │
│ /task-work (complexity ~7/10)       │
│   ↓                                 │
│ HAI-006: Integration (2h)           │
│ /task-work (complexity ~6/10)       │
└─────────────────────────────────────┘
```

**Tasks**:
- **HAI-005** (WS-A): Create discovery algorithm - `/task-work` (3h)
  - Phases: Planning → Architectural Review → Implementation → Testing → Code Review
  - Complexity: 7/10 (pattern matching, scoring algorithm, edge cases)
  - Review mode: FULL_REQUIRED (manual checkpoint)
  - Output: Matching algorithm, scoring logic, ranking

- **HAI-006** (WS-A): Integrate with /task-work - `/task-work` (2h)
  - Dependency: HAI-005 complete
  - Complexity: 6/10 (integration point, state management)
  - Review mode: QUICK_OPTIONAL (10s timeout)
  - Touches existing orchestrator code (risk of scope creep)
  - Output: Phase 2 integration, agent recommendation logic

**Dependencies**:
- HAI-005 → HAI-006 (sequential)
- HAI-001 complete (schema)
- HAI-002/003/004 complete (agents to discover)

**Checkpoint**: After HAI-005
- Review architectural decisions (Phase 2.8 checkpoint)
- Approve implementation plan
- **Checkpoint**: Built into /task-work Phase 2.8

**Wave 3 Total**: 5 hours + built-in checkpoints = **5 hours**

---

### Wave 4: Finalization (Sequential)

**Objective**: Documentation and E2E testing
**Duration**: 3.5 hours (sequential)
**Parallelization**: 2 workspaces (mostly sequential)

```
┌─────────────────────────────────────┐
│ WS-A (Sequential)                   │
├─────────────────────────────────────┤
│ HAI-007: Documentation (1.5h)       │
│ Direct                              │
│   ↓                                 │
│ HAI-008: E2E testing (2h)           │
│ /task-work (complexity ~5/10)       │
└─────────────────────────────────────┘
```

**Tasks**:
- **HAI-007** (WS-A): Documentation - Direct (1.5h)
  - User guide for agentic help
  - Agent authoring guide (agentic_help section)
  - Examples and best practices

- **HAI-008** (WS-B): E2E testing - `/task-work` (2h)
  - Dependency: All agents complete, discovery integrated
  - Complexity: 5/10 (testing workflow, validation)
  - Review mode: QUICK_OPTIONAL
  - Output: Integration tests, validation suite

**Dependencies**: All previous waves complete

**Checkpoint**: After Wave 4
- Review documentation completeness (10 min)
- Verify E2E tests pass (5 min)
- **Total checkpoint**: 15 minutes

**Wave 4 Total**: 3.5 hours work + 15 min checkpoint = **3.75 hours**

---

## 3. Conductor Workspace Strategy

### Workspace Allocation

**6 Workspaces Total** (reused across waves)

| Workspace | Wave 1 | Wave 2 | Wave 3 | Wave 4 | Total Usage |
|-----------|--------|--------|--------|--------|-------------|
| **WS-Main** | HAI-001 | - | - | - | 1.5h |
| **WS-A** | HAI-002 | HAI-009 (Batch 2) | HAI-005 → HAI-006 | HAI-007 | 11h |
| **WS-B** | HAI-003 | HAI-010 | - | HAI-008 | 5.5h |
| **WS-C** | HAI-004 | HAI-011 | - | - | 3.5h |
| **WS-D** | - | HAI-009 (Batch 3) + HAI-012 | - | - | 3h |
| **WS-E** | - | HAI-009 (Batch 1) + HAI-013 | - | - | 3.5h |
| **WS-F** | - | HAI-014 | - | - | 1.5h |

**Workspace Reuse Strategy**:
- WS-Main: Schema only (1 use)
- WS-A: Heavy reuse (4 tasks across waves)
- WS-B: Moderate reuse (3 tasks)
- WS-C: Light reuse (2 tasks)
- WS-D/E/F: Wave 2 only (parallel agent updates)

### State Persistence Verification

**Symlink Architecture** (already verified compatible):
```
{worktree}/.claude/state → {main-repo}/.claude/state
~/.claude/commands → ~/.agentecflow/commands
~/.claude/agents → ~/.agentecflow/agents
```

**State Consistency Rules**:
1. **Task state files**: Managed by main repo `.claude/state/`
2. **Agent files**: Updated in worktree, symlinked globally
3. **Templates**: Updated in worktree, committed to main
4. **Merge to main**: After each wave checkpoint

**Verification Commands**:
```bash
# Before Wave 1
taskwright doctor  # Verify integration

# During each wave
ls -la .claude/state  # Verify symlink
git status            # Check changes in worktree

# After each wave
git add . && git commit -m "Wave X complete"
conductor merge <workspace>  # Merge to main
```

---

## 4. Checkpoint Workflow

### Checkpoint Types

**Type 1: Built-In /task-work Checkpoints**
- Phase 2.8: Human approval for complex tasks
- Automatic for HAI-001, 005, 006, 008
- Duration: 2-5 minutes per task

**Type 2: Wave Checkpoints**
- After Wave 1, 2, 4
- Manual review of deliverables
- Duration: 15-20 minutes per wave

**Type 3: Integration Checkpoints**
- After HAI-005 (before HAI-006)
- Verify discovery algorithm before integration
- Duration: 5 minutes

### Merge-to-Main Strategy

**Merge Points**:
1. After Wave 1 (2.25h) → Merge all 4 workspaces
2. After Wave 2 (6.3h) → Merge all 6 workspaces
3. After HAI-005 (3h into Wave 3) → Merge WS-A
4. After Wave 3 (5h) → Merge WS-A (HAI-006)
5. After Wave 4 (3.75h) → Merge WS-A, WS-B

**Merge Procedure**:
```bash
# From each workspace
git add .
git commit -m "Wave X: [Task descriptions]"

# From main repo
conductor merge <workspace-name>

# Verify state consistency
taskwright doctor
git log --oneline -5
```

### Review Points

**Wave 1 Review** (15 min):
- [ ] HAI-001: Schema design sensible? (architectural review passed?)
- [ ] HAI-002/003/004: New agents have all metadata sections?
- [ ] All frontmatter valid YAML?

**Wave 2 Review** (20 min):
- [ ] Automated validation: All 15 agents have `agentic_help` section
- [ ] Spot-check 3 agents: Capabilities, use_cases, integration_points present?
- [ ] Template agents consistent with global agents?

**Wave 3 Review** (built into /task-work):
- [ ] HAI-005 Phase 2.8: Approve matching algorithm design
- [ ] HAI-006 auto-approved or quick review (10s timeout)

**Wave 4 Review** (15 min):
- [ ] HAI-007: Documentation covers all new features?
- [ ] HAI-008: E2E tests pass? All agents discoverable?

---

## 5. Risk Matrix

### High-Risk Tasks (Use /task-work)

| Task | Risk Level | Mitigation Strategy | Quality Gates |
|------|-----------|---------------------|---------------|
| **HAI-001** | 🟡 Medium | Architectural review required | Phase 2.5B: ≥60/100, Testing: 100% pass |
| **HAI-005** | 🔴 High | Complex matching logic | Phase 2.8: FULL_REQUIRED, Coverage ≥80% |
| **HAI-006** | 🟡 Medium | Touches existing code | Phase 5.5: Plan audit (scope creep detection) |
| **HAI-008** | 🟡 Medium | Validation critical | Test enforcement loop (Phase 4.5) |

**Risk Factors**:
- **HAI-001**: Incorrect schema breaks all subsequent work
- **HAI-005**: Matching algorithm bugs = poor agent recommendations
- **HAI-006**: Integration bugs break /task-work command
- **HAI-008**: Inadequate testing = bugs in production

**Mitigation Effectiveness**:
- Phase 2.5B (Architectural Review): Catches design issues early
- Phase 4.5 (Test Enforcement): Auto-fixes test failures (3 attempts)
- Phase 5.5 (Plan Audit): Detects scope creep (±20% LOC variance)

---

### Medium-Risk Tasks (Direct with Validation)

| Task | Risk Level | Validation Strategy |
|------|-----------|---------------------|
| **HAI-009** | 🟡 Medium | Automated validation script (check all agents) |
| **HAI-010-014** | 🟢 Low | Template consistency check |

**Validation Script** (for HAI-009):
```python
# validate_agent_metadata.py
def validate_agentic_help_section(agent_path):
    """Validates agent has required agentic_help fields."""
    required_fields = ['capabilities', 'use_cases', 'integration_points']
    # ... validation logic
    return True/False

# Run after HAI-009
agents = glob('installer/global/agents/*.md')
results = [validate_agentic_help_section(a) for a in agents]
assert all(results), "Validation failed"
```

---

### Low-Risk Tasks (Direct Implementation)

| Task | Risk Level | Notes |
|------|-----------|-------|
| **HAI-002/003/004** | 🟢 Low | Template-based, no integration |
| **HAI-007** | 🟢 Low | Documentation only |

---

## 6. Timeline Projections

### Best Case (Full Parallelization)

**Assumption**: All parallel tasks complete simultaneously

```
Day 1:
  Wave 1: 2.25h (parallel 4 workspaces)
  Wave 2: 6.3h (parallel 6 workspaces)
  Total: 8.5h

Day 2:
  Wave 3: 5h (sequential)
  Wave 4: 3.75h (sequential)
  Total: 8.75h

Total: 17.25h → 2.2 days (8h/day)
```

**Risk**: Assumes no blockers, no extended reviews, perfect parallelization

---

### Realistic (With Reviews and Breaks)

**Assumption**: 10% overhead for reviews, context switching

```
Day 1:
  Wave 1: 2.25h × 1.1 = 2.5h
  Break: 0.5h
  Wave 2: 6.3h × 1.1 = 7h
  Total: 10h

Day 2:
  Wave 3: 5h × 1.1 = 5.5h
  Break: 0.5h
  Wave 4: 3.75h × 1.1 = 4h
  Total: 10h

Total: 20h → 2.5 days (8h/day)
```

**Padding**: Add 1 day for blog post writing/editing

**Total Realistic**: **3.5 days**

---

### Conservative (Sequential Fallback)

**Assumption**: Parallelization fails, all tasks sequential

```
Total Sequential Duration:
  HAI-001: 1.5h
  HAI-002/003/004: 6h
  HAI-005: 3h
  HAI-006: 2h
  HAI-007: 1.5h
  HAI-008: 2h
  HAI-009: 6h
  HAI-010-014: 6h
  Checkpoints: 1h

Total: 29h → 3.6 days (8h/day)
```

**Padding**: Add 1 day for issues/blog

**Total Conservative**: **4.5 days**

---

### Recommended Timeline

**Target**: **3.5-4 days** (realistic with buffer)

```
Day 1 (8h):
  - Wave 1: 2.5h
  - Wave 2: 7h (start)

Day 2 (8h):
  - Wave 2: 0h (complete if needed)
  - Wave 3: 5.5h
  - Wave 4: 4h (start)

Day 3 (4h):
  - Wave 4: 0h (complete)
  - Integration testing: 2h
  - Bug fixes: 2h

Day 4 (8h):
  - Blog post writing: 6h
  - Final review: 2h
```

---

## 7. Execution Playbook

### Pre-Execution Checklist

```bash
# 1. Verify Conductor setup
conductor --version

# 2. Verify Taskwright installation
taskwright doctor

# 3. Verify symlinks
ls -la ~/.agentecflow/
ls -la .claude/state

# 4. Create workspaces
conductor create-workspace ws-main
conductor create-workspace ws-a
conductor create-workspace ws-b
conductor create-workspace ws-c
conductor create-workspace ws-d
conductor create-workspace ws-e
conductor create-workspace ws-f

# 5. Verify state persistence
echo "test" > .claude/state/test.txt
conductor switch ws-a
cat .claude/state/test.txt  # Should show "test"
conductor switch main
rm .claude/state/test.txt
```

---

### Wave 1 Execution

**Duration**: 2.25 hours

```bash
# WS-Main: HAI-001 (1.5h, /task-work)
conductor switch main
/task-create "Design agentic help schema" task_type:implementation
/task-work HAI-001
# Review Phase 2.8 checkpoint, approve
/task-complete HAI-001

# WS-A: HAI-002 (2h, Direct)
conductor switch ws-a
# Create Python API specialist agent
# Copy template, add agentic_help metadata
git add . && git commit -m "HAI-002: Python API specialist"

# WS-B: HAI-003 (2h, Direct)
conductor switch ws-b
# Create React State specialist agent
git add . && git commit -m "HAI-003: React State specialist"

# WS-C: HAI-004 (2h, Direct)
conductor switch ws-c
# Create .NET Domain specialist agent
git add . && git commit -m "HAI-004: .NET Domain specialist"

# Checkpoint (15 min)
conductor switch main
# Review schema (HAI-001)
# Spot-check new agents (HAI-002/003/004)

# Merge all workspaces
conductor merge ws-main
conductor merge ws-a
conductor merge ws-b
conductor merge ws-c

# Verify
git log --oneline -4
taskwright doctor
```

---

### Wave 2 Execution

**Duration**: 6.3 hours

```bash
# WS-E: HAI-009 Batch 1 (2h) + HAI-013 (1.5h)
conductor switch ws-e
# Update 4 global agents (batch 1)
# Update react-fastapi-monorepo agents
git add . && git commit -m "HAI-009 (Batch 1) + HAI-013"

# WS-A: HAI-009 Batch 2 (2h)
conductor switch ws-a
# Update 4 global agents (batch 2)
git add . && git commit -m "HAI-009 (Batch 2)"

# WS-D: HAI-009 Batch 3 (2h) + HAI-012 (1.5h)
conductor switch ws-d
# Update 4 global agents (batch 3)
# Update nextjs-fullstack agents
git add . && git commit -m "HAI-009 (Batch 3) + HAI-012"

# WS-B: HAI-010 (1.5h)
conductor switch ws-b
# Update react-typescript agents
git add . && git commit -m "HAI-010"

# WS-C: HAI-011 (1.5h)
conductor switch ws-c
# Update fastapi-python agents
git add . && git commit -m "HAI-011"

# WS-F: HAI-014 (1.5h)
conductor switch ws-f
# Update taskwright-python agents
git add . && git commit -m "HAI-014"

# Checkpoint (20 min)
conductor switch main
# Run validation script
python scripts/validate_agent_metadata.py
# Spot-check 3 agents

# Merge all workspaces
conductor merge ws-a
conductor merge ws-b
conductor merge ws-c
conductor merge ws-d
conductor merge ws-e
conductor merge ws-f

# Verify
git log --oneline -6
```

---

### Wave 3 Execution

**Duration**: 5 hours

```bash
# WS-A: HAI-005 (3h, /task-work)
conductor switch ws-a
/task-create "Create agent discovery algorithm" task_type:implementation
/task-work HAI-005
# Phase 2.8: FULL_REQUIRED checkpoint, review and approve
/task-complete HAI-005

# Checkpoint (built into /task-work)
# Verify discovery algorithm design approved

# Merge WS-A (HAI-005)
conductor switch main
conductor merge ws-a
git log --oneline -1

# WS-A: HAI-006 (2h, /task-work)
conductor switch ws-a
/task-create "Integrate discovery with /task-work" task_type:implementation
/task-work HAI-006
# Phase 2.8: QUICK_OPTIONAL (auto-approve or manual)
/task-complete HAI-006

# Merge WS-A (HAI-006)
conductor switch main
conductor merge ws-a
git log --oneline -1
```

---

### Wave 4 Execution

**Duration**: 3.75 hours

```bash
# WS-A: HAI-007 (1.5h, Direct)
conductor switch ws-a
# Write documentation
git add . && git commit -m "HAI-007: Documentation"

# WS-B: HAI-008 (2h, /task-work)
conductor switch ws-b
/task-create "E2E testing for agentic help" task_type:implementation
/task-work HAI-008
# Phase 2.8: QUICK_OPTIONAL (auto-approve likely)
/task-complete HAI-008

# Checkpoint (15 min)
conductor switch main
# Review documentation completeness
# Verify E2E tests pass

# Merge workspaces
conductor merge ws-a
conductor merge ws-b

# Final verification
git log --oneline -2
taskwright doctor
pytest tests/  # Run all tests
```

---

### Post-Execution Verification

```bash
# 1. All tasks completed
taskwright status | grep HAI

# 2. All agents have agentic_help metadata
python scripts/validate_agent_metadata.py

# 3. E2E tests pass
pytest tests/e2e/test_agentic_help.py -v

# 4. Discovery works
/task-work TEST-001  # Should recommend agents

# 5. Clean up workspaces
conductor delete-workspace ws-a
conductor delete-workspace ws-b
conductor delete-workspace ws-c
conductor delete-workspace ws-d
conductor delete-workspace ws-e
conductor delete-workspace ws-f
conductor delete-workspace ws-main
```

---

## Appendix A: Task Dependency Graph

```
HAI-001 (Schema)
   ├─→ HAI-002 (Python API) ─────┐
   ├─→ HAI-003 (React State) ────┤
   ├─→ HAI-004 (.NET Domain) ────┤
   │                              ↓
   ├─→ HAI-009 (Update 12) ──→ HAI-005 (Discovery) ──→ HAI-006 (Integration)
   │                              ↑                         ↓
   ├─→ HAI-010 (react-ts) ────────┤                         ↓
   ├─→ HAI-011 (fastapi) ─────────┤                         ↓
   ├─→ HAI-012 (nextjs) ──────────┤                         ↓
   ├─→ HAI-013 (monorepo) ────────┤                         ↓
   └─→ HAI-014 (taskwright) ──────┘                         ↓
                                                             ↓
                                   HAI-007 (Docs) ──────────┤
                                                             ↓
                                                          HAI-008 (E2E)
```

**Critical Path**: HAI-001 → HAI-005 → HAI-006 → HAI-008 (8.5h)

---

## Appendix B: Workspace Reuse Details

### WS-A Reuse Pattern (Most Efficient)

```
Wave 1: HAI-002 (2h)
  ↓ merge
Wave 2: HAI-009 Batch 2 (2h)
  ↓ merge
Wave 3: HAI-005 (3h) → HAI-006 (2h)
  ↓ merge (after HAI-005)
  ↓ merge (after HAI-006)
Wave 4: HAI-007 (1.5h)
  ↓ merge

Total: 10.5h across 5 tasks
```

**Efficiency**: Single workspace handles diverse tasks (agent creation, updates, discovery, docs)

---

## Appendix C: Risk Mitigation Summary

| Risk Category | Mitigation | Verification |
|--------------|------------|--------------|
| **Schema errors** | `/task-work` Phase 2.5B architectural review | Review checkpoint |
| **Matching bugs** | `/task-work` Phase 4.5 test enforcement | 100% test pass |
| **Integration bugs** | `/task-work` Phase 5.5 plan audit | Scope creep detection |
| **Metadata inconsistency** | Automated validation script | Post-Wave 2 checkpoint |
| **State conflicts** | Symlink architecture (verified) | `taskwright doctor` |
| **Merge conflicts** | Wave-based merges (not per-task) | Git status checks |

---

## Appendix D: Quick Reference Commands

```bash
# Create workspace
conductor create-workspace <name>

# Switch workspace
conductor switch <name>

# Merge workspace to main
conductor merge <name>

# Delete workspace
conductor delete-workspace <name>

# Verify state
taskwright doctor

# Run validation
python scripts/validate_agent_metadata.py

# Check task status
/task-status HAI-XXX

# Work on task
/task-work HAI-XXX

# Complete task
/task-complete HAI-XXX
```

---

## Summary

This guide provides a complete blueprint for parallel implementation of the agentic help system:

✅ **4 waves**: Foundation → Agents → Discovery → Finalization
✅ **6 workspaces**: Efficient reuse, minimal overhead
✅ **3.5-4 days**: Realistic timeline with buffer
✅ **5 /task-work tasks**: High-risk tasks with quality gates
✅ **10 direct tasks**: Low-risk, efficient implementation
✅ **100% state consistency**: Verified symlink architecture

**Next Steps**:
1. Review this guide (15 min)
2. Run pre-execution checklist (15 min)
3. Execute Wave 1 (2.25h)
4. Blog post writing can start after Wave 3 completion

**Estimated Completion**: Day 3-4 after start, ready for blog post publication.
