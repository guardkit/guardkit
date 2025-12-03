# EPIC-001 Parallel Implementation Plan (Conductor Optimized)

**Date**: 2025-11-01
**Epic**: EPIC-001 - Template Creation Automation
**Strategy**: Parallel development using Conductor git worktrees
**Goal**: Reduce timeline from 12 weeks to 5-6 weeks

---

## Executive Summary

By leveraging Conductor's git worktree architecture, we can parallelize independent tasks across multiple worktrees, reducing the implementation timeline by **50-60%** (from 12 weeks to 5-6 weeks).

**Key Metrics:**
- **Total Tasks**: 37
- **Sequential Timeline**: 12 weeks (220 hours @ 20h/week)
- **Parallel Timeline**: 5-6 weeks with 3-4 concurrent worktrees
- **Parallelization Efficiency**: ~58% time reduction

---

## Dependency Graph Analysis

### Wave 0: Foundation (No Dependencies) - 6 Tasks
Can start **immediately in parallel**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 0: Foundation (25 hours total)                          │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-037A  Universal Language Mapping         (3h)    │
│ WT-2: TASK-037   Technology Stack Detection         (6h)    │
│ WT-3: TASK-048B  Local Agent Scanner                (4h)    │
│ WT-4: TASK-048   Subagents.cc Scraper               (6h)    │
│ WT-5: TASK-049   GitHub Agent Parsers               (8h)    │
│ WT-6: TASK-053   Template-init QA Flow              (6h)    │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 6 worktrees
**Duration**: 1.5 weeks (8h max task / 5-6h avg per week = 1.5 weeks)

---

### Wave 1: First Tier (Single Dependency) - 7 Tasks
Start **as soon as Wave 0 completes**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 1: First Tier (33 hours total)                         │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-038A  Generic Structure Analyzer         (6h)    │
│       depends: [TASK-037A] ✓                                 │
│                                                               │
│ WT-2: TASK-038   Architecture Pattern Analyzer      (7h)    │
│       depends: [TASK-037] ✓                                  │
│                                                               │
│ WT-3: TASK-045A  Language Syntax Database           (4h)    │
│       depends: [TASK-037A] ✓                                 │
│                                                               │
│ WT-4: TASK-048C  Configurable Agent Sources         (3h)    │
│       depends: [TASK-048B] ✓                                 │
│                                                               │
│ WT-5: TASK-054   Basic Info Section                 (4h)    │
│       depends: [TASK-053] ✓                                  │
│                                                               │
│ WT-6: TASK-055   Technology Section                 (5h)    │
│       depends: [TASK-053] ✓                                  │
│                                                               │
│ WT-7: TASK-058   Quality Section                    (4h)    │
│       depends: [TASK-053] ✓                                  │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 7 worktrees
**Duration**: 1 week (7h max task)

---

### Wave 2: Second Tier (Multiple Dependencies) - 7 Tasks
Start **when required Wave 1 tasks complete**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 2: Second Tier (42 hours total)                        │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-039A  Generic Text Extraction            (5h)    │
│       depends: [TASK-037A ✓, TASK-038A ✓]                   │
│                                                               │
│ WT-2: TASK-039   Code Pattern Extraction            (8h)    │
│       depends: [TASK-037 ✓, TASK-038 ✓]                     │
│                                                               │
│ WT-3: TASK-040   Naming Convention Inference        (5h)    │
│       depends: [TASK-038 ✓]                                  │
│                                                               │
│ WT-4: TASK-041   Layer Structure Detection          (4h)    │
│       depends: [TASK-038 ✓]                                  │
│                                                               │
│ WT-5: TASK-042   Manifest Generator                 (5h)    │
│       depends: [TASK-037 ✓, TASK-038 ✓]                     │
│                                                               │
│ WT-6: TASK-044   CLAUDE.md Generator                (6h)    │
│       depends: [TASK-037 ✓, TASK-038 ✓]                     │
│                                                               │
│ WT-7: TASK-056   Architecture Section               (5h)    │
│       depends: [TASK-053 ✓, TASK-055 ✓]                     │
│       + TASK-057 Testing Section (4h - can pair)             │
│       depends: [TASK-053 ✓, TASK-055 ✓]                     │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 7 worktrees (WT-7 does 2 tasks)
**Duration**: 1 week (8h max task)

---

### Wave 3: Integration Layer - 4 Tasks
Requires **multiple Wave 2 outputs**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 3: Integration Layer (27 hours total)                  │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-043   Settings Generator                 (4h)    │
│       depends: [TASK-040 ✓, TASK-041 ✓]                     │
│       + TASK-062 Template Versioning (4h - can pair)         │
│       depends: [TASK-042 ✓]                                  │
│                                                               │
│ WT-2: TASK-045   Code Template Generator            (8h)    │
│       depends: [TASK-039 ✓]                                  │
│                                                               │
│ WT-3: TASK-050   Agent Matching Algorithm           (7h)    │
│       depends: [TASK-037 ✓, TASK-038 ✓, TASK-048 ✓,         │
│                 TASK-048B ✓, TASK-048C ✓, TASK-049 ✓]       │
│                                                               │
│ WT-4: TASK-046   Template Validation                (6h)    │
│       depends: [TASK-042 ✓, TASK-043 ✓, TASK-044 ✓,         │
│                 TASK-045 ✓]                                  │
│       NOTE: Must wait for TASK-043, TASK-045 from this wave │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 3-4 worktrees (some sequential within wave)
**Duration**: 1.5 weeks (8h max task + sequencing)

---

### Wave 4: Command Orchestration - 3 Tasks
High-level **orchestration requiring most components**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 4: Command Orchestration (18 hours total)              │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-047   /template-create Orchestrator      (6h)    │
│       depends: [TASK-037 ✓, TASK-038 ✓, TASK-039 ✓,         │
│                 TASK-042 ✓, TASK-043 ✓, TASK-045 ✓,         │
│                 TASK-046 ✓]                                  │
│                                                               │
│ WT-2: TASK-051   Agent Selection UI                 (5h)    │
│       depends: [TASK-050 ✓]                                  │
│                                                               │
│ WT-3: TASK-059   Agent Discovery Integration        (5h)    │
│       depends: [TASK-053 ✓, TASK-050 ✓, TASK-051 ✓]         │
│       + TASK-052 Agent Download Integration (4h - can pair) │
│       depends: [TASK-051 ✓]                                  │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 3 worktrees (WT-3 does 2 tasks sequentially)
**Duration**: 1 week (6h max task)

---

### Wave 5: Template-init Completion - 1 Task
**Massive orchestration task**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 5: Template-init Completion (6 hours total)            │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-060   /template-init Orchestrator        (6h)    │
│       depends: [TASK-042 ✓, TASK-043 ✓, TASK-044 ✓,         │
│                 TASK-045 ✓, TASK-046 ✓, TASK-053 ✓,         │
│                 TASK-054 ✓, TASK-055 ✓, TASK-056 ✓,         │
│                 TASK-057 ✓, TASK-058 ✓, TASK-059 ✓]         │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 1 worktree (integration task)
**Duration**: 0.5 weeks

---

### Wave 6: Distribution & Documentation - 7 Tasks
**Final polish, can parallelize**:

```
┌─────────────────────────────────────────────────────────────┐
│ WAVE 6: Distribution & Documentation (47 hours total)       │
├─────────────────────────────────────────────────────────────┤
│ WT-1: TASK-061   Template Packaging                 (5h)    │
│       depends: [TASK-047 ✓, TASK-060 ✓]                     │
│                                                               │
│ WT-2: TASK-063   Template Update/Merge              (6h)    │
│       depends: [TASK-062 ✓]                                  │
│                                                               │
│ WT-3: TASK-064   Distribution Helpers               (4h)    │
│       depends: [TASK-061 ✓]                                  │
│       NOTE: Sequential with WT-1                             │
│                                                               │
│ WT-4: TASK-065   Integration Tests                  (10h)   │
│       depends: [TASK-047 ✓, TASK-060 ✓]                     │
│                                                               │
│ WT-5: TASK-066   User Documentation                 (8h)    │
│       depends: [TASK-047 ✓, TASK-060 ✓, TASK-065 ✓]         │
│       NOTE: Can start docs while tests run                   │
│                                                               │
│ WT-6: TASK-067   Example Templates                  (10h)   │
│       depends: [TASK-047 ✓]                                  │
└─────────────────────────────────────────────────────────────┘
```

**Parallel Execution**: 4 worktrees (some sequential)
**Duration**: 1.5 weeks (10h max task + sequencing)

---

## Optimal Worktree Allocation Strategy

### Recommended Setup: 4 Concurrent Worktrees

This balances parallelization with coordination overhead.

```bash
# Setup Conductor worktrees for EPIC-001
cd /path/to/guardkit

# Wave 0 (pick 4 most important)
conductor worktree create epic001-wave0-lang-mapping TASK-037A
conductor worktree create epic001-wave0-stack-detect TASK-037
conductor worktree create epic001-wave0-local-agents TASK-048B
conductor worktree create epic001-wave0-ext-agents TASK-048

# After first 4 complete, start next 2
conductor worktree create epic001-wave0-github-agents TASK-049
conductor worktree create epic001-wave0-qa-flow TASK-053
```

### Worktree Naming Convention

```
epic001-wave{N}-{short-descriptor}
```

Examples:
- `epic001-wave0-lang-mapping` → TASK-037A
- `epic001-wave1-structure-analyzer` → TASK-038A
- `epic001-wave2-pattern-extract` → TASK-039

---

## Timeline Comparison

### Sequential Implementation (Original)

```
Week 1-2:  TASK-037A, 037, 038A, 038, 039A, 039
Week 3-4:  TASK-040, 041, 042, 043, 044, 045A, 045
Week 5-6:  TASK-046, 048B, 048C, 048, 049, 050, 051
Week 7-8:  TASK-052, 053, 054, 055, 056, 057, 058
Week 9-10: TASK-059, 060, 061, 062, 063, 064
Week 11-12: TASK-065, 066, 067

Total: 12 weeks (220 hours)
```

### Parallel Implementation (Conductor)

```
Week 1-2:  WAVE 0 (6 tasks in parallel)       ← 25h / 4 = ~1.5 weeks
Week 2-3:  WAVE 1 (7 tasks in parallel)       ← 33h / 4 = ~1 week
Week 3-4:  WAVE 2 (7 tasks in parallel)       ← 42h / 4 = ~1 week
Week 4-5:  WAVE 3 (4 tasks, some sequential)  ← 27h / 3 = ~1.5 weeks
Week 5:    WAVE 4 (3 tasks in parallel)       ← 18h / 3 = ~1 week
Week 5-6:  WAVE 5 (1 task, integration)       ← 6h / 1 = ~0.5 weeks
Week 6-7:  WAVE 6 (4-6 tasks, some sequential) ← 47h / 4 = ~1.5 weeks

Total: 5-6 weeks (220 hours with parallelization)
```

**Time Reduction**: 50-58% (from 12 weeks to 5-6 weeks)

---

## Developer Team Allocation

### Option A: 4 Developers (Optimal)

**Total**: 220 hours / 4 devs = 55 hours per developer
**Timeline**: 5-6 weeks @ 10-12h per week per developer

**Roles:**
- **Dev 1 (Language Expert)**: TASK-037A, 038A, 039A, 045A + supporting tasks
- **Dev 2 (Architecture/Pattern)**: TASK-037, 038, 039, 040, 041
- **Dev 3 (Agent Discovery)**: TASK-048, 048B, 048C, 049, 050, 051
- **Dev 4 (Template-init/UI)**: TASK-053-059, Q&A sections

### Option B: 3 Developers (Budget-Conscious)

**Total**: 220 hours / 3 devs = 73 hours per developer
**Timeline**: 7-8 weeks @ 10h per week per developer

**Roles:**
- **Dev 1**: Pattern Extraction + Language (TASK-037A, 037, 038A, 038, 039A, 039)
- **Dev 2**: Agent Discovery + Matching (TASK-048B, 048C, 048, 049, 050, 051, 052)
- **Dev 3**: Template Generation + Commands (TASK-040-047, 053-060)

### Option C: 2 Developers (Minimal)

**Total**: 220 hours / 2 devs = 110 hours per developer
**Timeline**: 9-10 weeks @ 12h per week per developer

**Roles:**
- **Dev 1**: Backend/Core (TASK-037A-039A, 037-045)
- **Dev 2**: Integration/UI (TASK-046-052, 053-067)

---

## State Synchronization Strategy

### Conductor State Persistence (Already Solved)

From guardkit's Conductor integration:

```bash
# State is automatically synchronized via symlinks
~/.claude/state → {main-repo}/.claude/state

# All worktrees share the same state
worktree-1/.claude/state → main-repo/.claude/state
worktree-2/.claude/state → main-repo/.claude/state
worktree-3/.claude/state → main-repo/.claude/state
```

### Task Completion Protocol

When completing a task in a worktree:

```bash
# 1. Complete implementation
cd epic001-wave0-lang-mapping
# ... implement TASK-037A ...

# 2. Run tests
pytest tests/test_universal_language_mapping.py

# 3. Move task to completed
mv tasks/backlog/TASK-037A-*.md tasks/completed/

# 4. Commit (auto-syncs to main repo)
git add .
git commit -m "feat: Complete TASK-037A - Universal Language Mapping"

# 5. State automatically available to other worktrees via symlink
```

---

## Critical Path Analysis

The **critical path** determines minimum timeline:

```
Critical Path (cannot be parallelized):
TASK-037A (3h)
  → TASK-038A (6h)
    → TASK-039A (5h)
      [Meanwhile: TASK-045A after 037A (4h)]
      [Meanwhile: TASK-037, 038, 039 in parallel]
        → TASK-045 (8h)
          → TASK-046 (6h)
            → TASK-047 (6h)
              → TASK-060 (6h)
                → TASK-061 (5h)
                  → TASK-064 (4h)

Critical Path Total: ~53 hours minimum
With 4 parallel worktrees: 53h + coordination = ~5-6 weeks
```

---

## Risk Mitigation

### Merge Conflict Prevention

1. **File Isolation**: Each task works on different files
2. **Symlinked State**: Conductor's architecture prevents state conflicts
3. **Integration Points**: Use Wave boundaries for integration

### Integration Testing

After each wave:

```bash
# Run full integration test suite
pytest tests/integration/

# Verify all wave N tasks work together
pytest tests/integration/wave_{N}/
```

### Blocked Tasks

If a task is blocked:

```bash
# Switch worktree to alternative task
cd epic001-wave0-lang-mapping

# If TASK-037A is blocked, switch to TASK-048B
git checkout epic001-wave0-local-agents
```

---

## Implementation Phases

### Phase 1: Wave 0 Foundation (Week 1-2)

**Goal**: Complete all foundational tasks with no dependencies

**Worktrees**: 4 concurrent
- WT-1: TASK-037A (3h)
- WT-2: TASK-037 (6h)
- WT-3: TASK-048B (4h)
- WT-4: TASK-048 (6h)

**After first round completes**:
- WT-1: TASK-049 (8h)
- WT-2: TASK-053 (6h)

**Exit Criteria**:
- All 6 foundation tasks complete
- Unit tests passing for each
- Integration tests for cross-task compatibility

### Phase 2: Wave 1 First Tier (Week 2-3)

**Goal**: Build first-tier components using Wave 0 outputs

**Worktrees**: 4 concurrent
- WT-1: TASK-038A (6h)
- WT-2: TASK-038 (7h)
- WT-3: TASK-045A (4h)
- WT-4: TASK-048C (3h)

**After first round**:
- WT-1: TASK-054 (4h)
- WT-2: TASK-055 (5h)
- WT-3: TASK-058 (4h)

**Exit Criteria**:
- All 7 Wave 1 tasks complete
- Architecture/structure analysis working
- Agent source configuration functional

### Phase 3: Wave 2 Second Tier (Week 3-4)

**Goal**: Pattern extraction and template generation components

**Worktrees**: 4 concurrent
- WT-1: TASK-039A (5h)
- WT-2: TASK-039 (8h)
- WT-3: TASK-040 (5h)
- WT-4: TASK-041 (4h)

**After first round**:
- WT-1: TASK-042 (5h)
- WT-2: TASK-044 (6h)
- WT-3: TASK-056 + TASK-057 (9h)

**Exit Criteria**:
- Pattern extraction working for 50+ languages
- Naming conventions inferred correctly
- Manifest/settings generators functional

### Phase 4: Wave 3 Integration (Week 4-5)

**Goal**: Integrate components and prepare for orchestration

**Worktrees**: 3 concurrent
- WT-1: TASK-043 + TASK-062 (8h)
- WT-2: TASK-045 (8h)
- WT-3: TASK-050 (7h)

**After first round**:
- WT-1: TASK-046 (6h)

**Exit Criteria**:
- Template validation working
- Agent matching with bonus scoring
- Settings generator complete

### Phase 5: Wave 4 Orchestration (Week 5)

**Goal**: Command orchestration and UI

**Worktrees**: 3 concurrent
- WT-1: TASK-047 (6h)
- WT-2: TASK-051 (5h)
- WT-3: TASK-059 + TASK-052 (9h)

**Exit Criteria**:
- `/template-create` command working end-to-end
- Agent selection UI with source grouping
- Agent download integration

### Phase 6: Wave 5 Template-init (Week 5-6)

**Goal**: Complete /template-init command

**Worktrees**: 1 (integration)
- WT-1: TASK-060 (6h)

**Exit Criteria**:
- `/template-init` command working end-to-end
- All Q&A sections integrated
- Template generation from answers

### Phase 7: Wave 6 Polish (Week 6-7)

**Goal**: Distribution, testing, documentation

**Worktrees**: 3-4 concurrent
- WT-1: TASK-061 → TASK-064 (9h sequential)
- WT-2: TASK-063 (6h)
- WT-3: TASK-065 (10h)
- WT-4: TASK-067 (10h)

**After tests complete**:
- WT-3: TASK-066 (8h)

**Exit Criteria**:
- All integration tests passing
- Documentation complete
- 3+ example templates created

---

## Success Metrics

### Timeline Goals

- ✅ Complete in **5-6 weeks** (vs. 12 weeks sequential)
- ✅ Achieve **50-58% time reduction**
- ✅ Zero merge conflicts (via file isolation)

### Quality Gates

- ✅ All 37 tasks completed with passing tests
- ✅ Integration tests for both commands passing
- ✅ Example templates generated successfully
- ✅ Documentation complete

### Team Satisfaction

- ✅ Developers work independently (minimal blocking)
- ✅ Clear task boundaries (no stepping on toes)
- ✅ Regular integration points (weekly)

---

## Quick Start Commands

```bash
# 1. Setup Conductor (if not already)
cd /path/to/guardkit

# 2. Create worktrees for Wave 0
conductor worktree create epic001-w0-lang TASK-037A
conductor worktree create epic001-w0-stack TASK-037
conductor worktree create epic001-w0-local TASK-048B
conductor worktree create epic001-w0-ext TASK-048

# 3. Assign to developers
# Dev 1: cd epic001-w0-lang
# Dev 2: cd epic001-w0-stack
# Dev 3: cd epic001-w0-local
# Dev 4: cd epic001-w0-ext

# 4. Start implementation
# (Each developer works in their worktree)

# 5. Monitor progress
conductor status

# 6. When Wave 0 completes, create Wave 1 worktrees
conductor worktree create epic001-w1-struct TASK-038A
# ... etc
```

---

## Conclusion

**Parallelization Strategy**: 6 waves with 3-4 concurrent worktrees
**Timeline Reduction**: From 12 weeks to 5-6 weeks (50-58%)
**Team Size**: 4 developers (optimal) or 3 (budget) or 2 (minimal)
**Risk Level**: Low (file isolation + Conductor state management)

**Recommendation**: Proceed with **4-developer team** for **5-6 week timeline**

---

**Created**: 2025-11-01
**Status**: ✅ **READY FOR PARALLEL EXECUTION**
**Next Step**: Create Wave 0 worktrees and assign to developers
