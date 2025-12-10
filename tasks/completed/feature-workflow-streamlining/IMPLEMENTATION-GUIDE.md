# Feature Workflow Streamlining Implementation Guide

## Overview

This guide details the execution strategy for all 9 tasks (FW-001 through FW-009), including which implementation method to use and how to parallelize work using Conductor workspaces.

## Implementation Method Legend

| Method | Description | When to Use |
|--------|-------------|-------------|
| `/task-work` | Full GuardKit workflow with quality gates | Complex code changes requiring tests, review |
| `Direct` | Direct Claude Code implementation | Scripts, simple changes, documentation |

## Conductor Parallel Execution

Conductor.build enables parallel development via git worktrees. Tasks marked **PARALLEL** can run simultaneously in separate workspaces.

### Workspace Strategy

```
Main Repo (guardkit)
├── Worktree A: Wave 1 (FW-001, FW-002, FW-007)
├── Worktree B: Wave 2a (FW-003, FW-004)
├── Worktree C: Wave 2b (FW-005, FW-006)
└── Main: Wave 3-4 (FW-008, FW-009 - sequential)
```

---

## Wave 1: Quick Wins & Utilities (PARALLEL)

**Duration**: 1.5 days
**Workspaces**: 3 (can run in parallel!)

### TASK-FW-001: Create /feature-plan Command
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** |

**Why Direct**: Simple markdown command file creation, no code logic.

**Execution**:
```bash
# Direct Claude Code implementation
# Create installer/core/commands/feature-plan.md
```

**This is the QUICK WIN** - gives single-command UX immediately!

---

### TASK-FW-002: Auto-detect Feature Slug
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** |

**Why Direct**: Simple utility function, straightforward regex logic.

**Execution**:
```bash
# Direct Claude Code implementation
# Add to installer/core/lib/feature_utils.py
```

---

### TASK-FW-007: Create README.md Generator
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** |

**Why Direct**: Template-based generation, straightforward string formatting.

**Execution**:
```bash
# Direct Claude Code implementation
# Create installer/core/lib/readme_generator.py
```

**CHECKPOINT 1**: After Wave 1, verify:
```bash
# Test /feature-plan command exists
ls installer/core/commands/feature-plan.md

# Test slug extraction
python3 -c "from installer.core.lib.feature_utils import extract_feature_slug; print(extract_feature_slug('Plan: dark mode'))"
# Expected: dark-mode
```

---

## Wave 2: Detection & Generation (PARALLEL)

**Duration**: 4.5 days
**Workspaces**: 2 (can run in parallel!)

### Wave 2a: Subtask Detection (Workspace B)

### TASK-FW-003: Auto-detect Subtasks from Recommendations
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | **YES** - with FW-004 |

**Why /task-work**: Markdown parsing has edge cases, needs tests.

**Execution**:
```bash
/task-work TASK-FW-003
```

---

### TASK-FW-004: Implementation Mode Auto-Tagging
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | **YES** - with FW-003 |

**Why /task-work**: Complexity analysis logic needs testing.

**Execution**:
```bash
/task-work TASK-FW-004
```

---

### Wave 2b: Parallel Detection & Guide (Workspace C)

### TASK-FW-005: Parallel Group Detection
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 6/10 |
| **Effort** | 1.5 days |
| **Parallel** | **YES** - with FW-006 |

**Why /task-work**: Graph algorithm, most complex task in feature.

**Execution**:
```bash
/task-work TASK-FW-005
```

---

### TASK-FW-006: Create IMPLEMENTATION-GUIDE.md Generator
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | **YES** - with FW-005 |

**Why /task-work**: Template generation needs testing with various inputs.

**Execution**:
```bash
/task-work TASK-FW-006
```

**CHECKPOINT 2**: After Wave 2, verify all components work independently:
```bash
# Test subtask extraction
python3 -c "from installer.core.lib.review_parser import extract_subtasks_from_review; ..."

# Test mode assignment
python3 -c "from installer.core.lib.complexity_analyzer import assign_implementation_mode; ..."

# Test parallel detection
python3 -c "from installer.core.lib.parallel_analyzer import detect_parallel_groups; ..."

# Test guide generation
python3 -c "from installer.core.lib.guide_generator import generate_implementation_guide; ..."
```

---

## Wave 3: Orchestration (SEQUENTIAL)

**Duration**: 1 day
**Workspaces**: 1 (main repo)

### TASK-FW-008: Update /task-review [I]mplement Flow
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | No - depends on all Wave 2 |

**Why /task-work**: Integration task, orchestrates all components.

**Execution**:
```bash
/task-work TASK-FW-008
```

**CHECKPOINT 3**: Test full [I]mplement flow:
```bash
# Create test review task
/task-create "Plan: test feature" task_type:review

# Run review (mock recommendations)
/task-review TASK-XXX --mode=decision

# Choose [I]mplement
# Verify: subfolder created, all files generated
ls tasks/backlog/test-feature/
# Expected: README.md, IMPLEMENTATION-GUIDE.md, TASK-TF-001-*.md, ...
```

---

## Wave 4: Documentation (SEQUENTIAL)

**Duration**: 0.5 days
**Workspaces**: 1 (main repo)

### TASK-FW-009: Update Documentation
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - must be last |

**Why Direct**: Documentation updates, no code logic.

**Execution**:
```bash
# Direct Claude Code implementation
# Update CLAUDE.md, task-review.md, feature-plan.md
```

**FINAL CHECKPOINT**: Verify complete workflow:
```bash
# Test full /feature-plan flow
/feature-plan "implement dark mode"

# Verify output
ls tasks/backlog/dark-mode/
# Expected: README.md, IMPLEMENTATION-GUIDE.md, TASK-DM-*.md files

# Verify documentation
grep "feature-plan" CLAUDE.md
# Expected: Command documented
```

---

## Summary: Task Matrix

| Task | Method | Complexity | Effort | Can Parallel |
|------|--------|------------|--------|--------------|
| FW-001 | Direct | 3 | 0.5d | **YES** (Wave 1) |
| FW-002 | Direct | 3 | 0.5d | **YES** (Wave 1) |
| FW-003 | /task-work | 5 | 1d | **YES** (Wave 2a) |
| FW-004 | /task-work | 5 | 1d | **YES** (Wave 2a) |
| FW-005 | /task-work | 6 | 1.5d | **YES** (Wave 2b) |
| FW-006 | /task-work | 5 | 1d | **YES** (Wave 2b) |
| FW-007 | Direct | 3 | 0.5d | **YES** (Wave 1) |
| FW-008 | /task-work | 5 | 1d | No (Wave 3) |
| FW-009 | Direct | 3 | 0.5d | No (Wave 4) |

## Method Breakdown

| Method | Task Count | Total Effort |
|--------|------------|--------------|
| `/task-work` | 5 tasks | 5.5 days |
| `Direct` Claude Code | 4 tasks | 2 days |

## Parallel Execution Savings

**Sequential Duration**: 7.5 days
**With Conductor Parallel** (Waves 1 + 2): **~5 days**

**Savings**: ~2.5 days (33% faster)

---

## Recommended Execution Order

```
Day 1:     Wave 1 (parallel): FW-001, FW-002, FW-007
           CHECKPOINT 1
Days 2-3:  Wave 2a (parallel): FW-003, FW-004
           Wave 2b (parallel): FW-005, FW-006
           CHECKPOINT 2
Day 4:     Wave 3: FW-008 (orchestration)
           CHECKPOINT 3
Day 5:     Wave 4: FW-009 (documentation)
           FINAL CHECKPOINT
```

## Quick Start

**For immediate single-command UX**, start with FW-001 alone:
```bash
# Day 1, Morning
# Just create the /feature-plan command file
# This gives single-command UX immediately!

# Then continue with remaining tasks for full auto-detection
```

---

## Final Deliverables

1. `/feature-plan` command (single-command UX)
2. Enhanced `/task-review` [I]mplement option
3. Auto-detection pipeline (slug, subtasks, modes, waves)
4. IMPLEMENTATION-GUIDE.md generator
5. README.md generator
6. Updated documentation
