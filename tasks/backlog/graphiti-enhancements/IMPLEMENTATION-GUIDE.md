# Graphiti Enhancements - Implementation Guide

## Overview

This guide organizes the 7 enhancement tasks into parallel execution waves based on dependencies.

## Wave Structure

```
Wave 1 (Parallel - Foundation): 4 tasks
├── TASK-GE-001: Feature Overview Entity
├── TASK-GE-003: Role Constraint Facts
├── TASK-GE-006: Feature-Build North Star Document (direct)
└── TASK-GE-007: Immediate ADR Seeding

Wave 2 (Parallel - Episodes & Config): 3 tasks
├── TASK-GE-002: Turn State Episodes (depends on GE-001)
├── TASK-GE-004: Failed Approach Episodes
└── TASK-GE-005: Quality Gate Config Facts
```

## Wave 1: Foundation (Start Here)

**Estimated Duration**: 90-120 minutes total (parallel execution)

| Task | Mode | Complexity | Est. Minutes | Conductor Workspace |
|------|------|------------|--------------|---------------------|
| TASK-GE-001 | task-work | 5 | 120 | graphiti-enhancements-wave1-1 |
| TASK-GE-003 | task-work | 4 | 90 | graphiti-enhancements-wave1-2 |
| TASK-GE-006 | direct | 3 | 60 | graphiti-enhancements-wave1-3 |
| TASK-GE-007 | task-work | 4 | 90 | graphiti-enhancements-wave1-4 |

**Wave 1 provides immediate value:**
- North Star document (GE-006) can be used right away
- ADR seeding (GE-007) enables context loading
- Feature Overview and Role Constraints prepare for turn-state capture

### Execution Commands

```bash
# Option 1: Sequential execution
/task-work TASK-GE-001
/task-work TASK-GE-003
# For direct mode task:
# Manually create .claude/rules/feature-build-invariants.md
/task-work TASK-GE-007

# Option 2: Parallel via Conductor (recommended)
conductor workspace create graphiti-enhancements-wave1-1
conductor workspace create graphiti-enhancements-wave1-2
conductor workspace create graphiti-enhancements-wave1-3
conductor workspace create graphiti-enhancements-wave1-4
# Then run tasks in respective workspaces

# Option 3: Feature-build (if configured)
/feature-build FEAT-GE-ENH
```

## Wave 2: Episodes & Configuration

**Estimated Duration**: 120-180 minutes total (parallel execution)
**Dependencies**: Wave 1 must complete first (GE-002 depends on GE-001)

| Task | Mode | Complexity | Est. Minutes | Conductor Workspace |
|------|------|------------|--------------|---------------------|
| TASK-GE-002 | task-work | 6 | 180 | graphiti-enhancements-wave2-1 |
| TASK-GE-004 | task-work | 5 | 120 | graphiti-enhancements-wave2-2 |
| TASK-GE-005 | task-work | 5 | 120 | graphiti-enhancements-wave2-3 |

**Wave 2 adds learning capabilities:**
- Turn State episodes enable cross-turn learning
- Failed Approach episodes prevent repeated mistakes
- Quality Gate configs make thresholds flexible

## Task Details

### TASK-GE-001: Feature Overview Entity
**What it does**: Creates a `FeatureOverviewEntity` dataclass that captures the "big picture" of major features (what it IS, invariants, key decisions).

**Files created**:
- `guardkit/knowledge/entities/feature_overview.py`
- `guardkit/knowledge/seed_feature_overviews.py`

**Integration points**:
- `guardkit/knowledge/context_loader.py` (add overview loading)

### TASK-GE-002: Turn State Episodes
**What it does**: Captures state at the end of each feature-build turn (Player decision, Coach decision, cumulative progress).

**Files created**:
- `guardkit/knowledge/entities/turn_state.py`
- `guardkit/knowledge/turn_state_manager.py`

**Integration points**:
- `guardkit/orchestrator/autobuild.py` (add post-turn capture)
- `guardkit/knowledge/context_loader.py` (add turn continuation)

### TASK-GE-003: Role Constraint Facts
**What it does**: Defines hard constraints for Player and Coach roles (MUST DO, MUST NOT DO).

**Files created**:
- `guardkit/knowledge/facts/role_constraint.py`
- `guardkit/knowledge/seed_role_constraints.py`

**Integration points**:
- `guardkit/knowledge/context_loader.py` (add role loading)

### TASK-GE-004: Failed Approach Episodes
**What it does**: Captures failed approaches with prevention guidance so they don't repeat.

**Files created**:
- `guardkit/knowledge/entities/failed_approach.py`
- `guardkit/knowledge/failed_approach_manager.py`
- `guardkit/knowledge/seed_failed_approaches.py`

**Seeds 5 initial failures from review findings.**

### TASK-GE-005: Quality Gate Config Facts
**What it does**: Makes quality gate thresholds configurable and task-type specific.

**Files created**:
- `guardkit/knowledge/facts/quality_gate_config.py`
- `guardkit/knowledge/seed_quality_gate_configs.py`
- `guardkit/knowledge/quality_gate_queries.py`

**Integration points**:
- `guardkit/orchestrator/coach_validator.py` (use Graphiti thresholds)

### TASK-GE-006: Feature-Build North Star Document
**What it does**: Creates a concise rules document that loads when working on feature-build code.

**Files created**:
- `.claude/rules/feature-build-invariants.md`

**This is a direct mode task (simple documentation).**

### TASK-GE-007: Immediate ADR Seeding
**What it does**: Seeds ADR-FB-001, ADR-FB-002, ADR-FB-003 into Graphiti.

**Files created**:
- `guardkit/knowledge/seed_feature_build_adrs.py`

**Integration points**:
- `guardkit/cli.py` (add seed-adrs command)

## Verification

After Wave 1 completes, verify:
```bash
# Check North Star document exists
cat .claude/rules/feature-build-invariants.md

# Verify ADRs are seeded
guardkit graphiti seed-adrs
guardkit graphiti query "ADR-FB-001"
```

After Wave 2 completes, verify:
```bash
# Run a feature-build and check context includes:
# - Feature overview
# - Role constraints
# - Previous turn state (for Turn > 1)
# - Failed approach warnings
# - Quality gate config for task type
```

## Expected Outcomes

| Metric | Before | After |
|--------|--------|-------|
| Time re-learning architecture | 50-70% | 10-15% |
| Repeated mistakes | ~40% | <10% |
| Time to first success | 10+ turns | 3-5 turns |
| Cross-turn learning | None | Continuous |
