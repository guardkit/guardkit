# Progressive Disclosure Implementation Guide

## Overview

This guide details the execution strategy for all 25 progressive disclosure tasks (PD-000 through PD-024), including which implementation method to use and how to parallelize work using Conductor workspaces.

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | ✅ Complete | Measurement Framework |
| Phase 1-4 | ✅ Complete | Infrastructure |
| Phase 5 | ✅ Complete | Validation & Documentation |
| **Phase 6** | 🔄 **Next** | **Content Migration** |

## Phase 6 Revisions (TASK-REV-PD6)

The following revisions were applied based on architectural review (TASK-REV-PD6):

| Revision | Task | Description |
|----------|------|-------------|
| Dependency fix | PD-020 | Added TASK-REV-PD6 to blocked_by |
| Rollback strategy | PD-020 | Added backup/restore procedures |
| Section matrix | PD-020 | Decision matrix for ambiguous sections |
| Selection criteria | PD-020 | Quick Start example selection rules |
| Backup mandate | PD-021 | Required backup before migration |
| Backup mandate | PD-022 | Required backup for all 12 agents |
| Scope clarification | README | Template agents deferred to Phase 7 |

**Review Report**: [TASK-REV-PD6-review-report.md](../../../.claude/reviews/TASK-REV-PD6-review-report.md)

## Implementation Method Legend

| Method | Description | When to Use |
|--------|-------------|-------------|
| `/task-work` | Full GuardKit workflow with quality gates | Complex code changes requiring tests, review |
| `Direct` | Direct Claude Code implementation | Scripts, simple changes, documentation |
| `Manual` | Human execution with script | Bulk operations, running scripts |

## Conductor Parallel Execution

Conductor.build enables parallel development via git worktrees. Tasks marked **PARALLEL** can run simultaneously in separate workspaces.

### Workspace Strategy

```
Main Repo (guardkit)
├── Worktree A: Phase 1 foundation (PD-001 → PD-004)
├── Worktree B: Phase 2 generator (after Phase 1)
├── Worktree C: Phase 3 script (after Phase 2)
└── Worktree D: Phase 4 templates (parallelizable after script ready)
```

---

## Wave 1: Foundation & Baseline

**Duration**: 4.5 days
**Workspaces**: 1 (sequential - establishes core infrastructure)

### TASK-PD-000: Measurement Framework
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - must complete first |

**Why Direct**: Simple Python script creation, no integration with existing systems.

**Execution**:
```bash
# In main repo
# Claude Code creates:
# - scripts/measure-token-usage.py
# - measurements/ directory

# Human runs:
python3 scripts/measure-token-usage.py --baseline
```

**Output**: `measurements/baseline.json` captured before any changes.

---

### TASK-PD-001: Refactor applier.py
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 7/10 |
| **Effort** | 2-3 days |
| **Parallel** | No - foundation for all subsequent tasks |

**Why /task-work**: High-risk refactor of core enhancement pipeline. Requires architectural review, unit tests, and code review.

**Execution**:
```bash
/task-work TASK-PD-001
# Phases: 2 → 2.5 → 2.7 → 2.8 (checkpoint) → 3 → 4 → 4.5 → 5 → 5.5
```

**Quality Gates**:
- Architectural review score ≥60
- Unit test coverage ≥80%
- Existing `apply()` behavior unchanged

---

### TASK-PD-002: Loading Instruction Template
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on PD-001 |

**Why Direct**: Simple template function, low risk, integrates with completed PD-001.

**Execution**:
```bash
# Claude Code adds generate_loading_instruction() to applier.py
# Manual verification:
python3 -c "from installer.core.lib.agent_enhancement.applier import generate_loading_instruction; print(generate_loading_instruction('test', 'test-ext.md'))"
```

---

### TASK-PD-003: Update enhancer.py
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | No - depends on PD-002 |

**Why /task-work**: Modifies second core component, needs integration testing.

**Execution**:
```bash
/task-work TASK-PD-003
```

---

### TASK-PD-004: Agent Discovery Exclusion
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on PD-003 |

**Why Direct**: Simple filter addition, low risk, clear acceptance criteria.

**Execution**:
```bash
# Claude Code modifies agent_scanner.py
# Manual verification:
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/core/lib')
from agent_scanner import is_extended_file
print(is_extended_file(Path('test-ext.md')))  # True
print(is_extended_file(Path('test.md')))       # False
"
```

**CHECKPOINT 1**: After PD-004, validate Phase 1:
```bash
# Test split enhancement on single agent
/agent-enhance test-agent.md test-template/
ls -la test-template/agents/  # Should show test-agent.md + test-agent-ext.md
```

---

## Wave 2: CLAUDE.md Generator

**Duration**: 3.5 days
**Workspaces**: 1 (sequential - modifies generator pipeline)

### TASK-PD-005: Refactor claude_md_generator.py
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 6/10 |
| **Effort** | 2 days |
| **Parallel** | No - starts after Phase 1 complete |

**Why /task-work**: Major refactor of large file (1147 lines), introduces new generation methods.

**Execution**:
```bash
/task-work TASK-PD-005
```

---

### TASK-PD-006: Update Template Orchestrator
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | No - depends on PD-005 |

**Why /task-work**: Integration point between generator and file output.

---

### TASK-PD-007: Update TemplateClaude Model
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on PD-006 |

**Why Direct**: Data model update, low risk, straightforward changes.

**CHECKPOINT 2**: After PD-007, validate Phase 2:
```bash
# Test template creation on sample codebase
/template-create --source ~/sample-project --output /tmp/test-template
ls -la /tmp/test-template/CLAUDE.md        # Should be ≤10KB
ls -la /tmp/test-template/docs/patterns/   # Should exist
ls -la /tmp/test-template/docs/reference/  # Should exist
```

---

## Wave 3: Automated Agent Migration

**Duration**: 3.5 days
**Workspaces**: 1 for script, then parallelizable for execution

### TASK-PD-008: Create split-agent.py Script
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 6/10 |
| **Effort** | 1.5 days |
| **Parallel** | No - script required before PD-010 |

**Why Direct**: Standalone script creation, complex but isolated.

**Execution**:
```bash
# Claude Code creates scripts/split-agent.py
# Verify with dry run:
python3 scripts/split-agent.py --dry-run --agent installer/core/agents/task-manager.md
```

---

### TASK-PD-009: Define Content Categorization Rules
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 5/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on PD-008 |

**Why Direct**: Refinement of split rules in script, pattern tuning.

---

### TASK-PD-010: Run Split on 19 Global Agents
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` script execution |
| **Complexity** | 4/10 |
| **Effort** | 1 day |
| **Parallel** | No - bulk operation |

**Why Manual**: Human runs script, reviews output, handles edge cases.

**Execution**:
```bash
# Dry run first
python3 scripts/split-agent.py --dry-run --all-global

# Review output, then execute
python3 scripts/split-agent.py --all-global

# Verify
ls installer/core/agents/*.md | wc -l  # Should be 38 (19 core + 19 ext)
```

---

### TASK-PD-011: Validate All Split Agents
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` validation |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on PD-010 |

**Why Manual**: Human spot-checks, runs validation script.

**Execution**:
```bash
python3 scripts/split-agent.py --validate --all-global

# Spot check random agents
cat installer/core/agents/task-manager.md | head -50
cat installer/core/agents/task-manager-ext.md | head -50
```

**CHECKPOINT 3**: After PD-011, validate Phase 3:
```bash
# Verify discovery excludes ext files
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, 'installer/core/lib')
from agent_scanner import AgentScanner
agents = AgentScanner().scan_agents(Path('installer/core/agents'))
ext_found = [a for a in agents if '-ext' in a.name]
print(f'Core agents: {len(agents)}')
print(f'Ext files in discovery: {len(ext_found)}')  # Should be 0
"
```

---

## Wave 4: Template Agents (PARALLEL)

**Duration**: 2 days
**Workspaces**: 4 (can run in parallel!)

These tasks are **independent** and can run in **4 parallel Conductor workspaces**.

### Workspace Layout for Parallel Execution

```bash
# Create worktrees
git worktree add ../guardkit-pd-react react-typescript-split
git worktree add ../guardkit-pd-fastapi fastapi-split
git worktree add ../guardkit-pd-nextjs nextjs-split
git worktree add ../guardkit-pd-monorepo monorepo-split
```

### TASK-PD-012: Split react-typescript Agents (Workspace A)
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` script execution |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** - independent of PD-013/014/015 |

**Execution**:
```bash
cd ../guardkit-pd-react
python3 scripts/split-agent.py --template react-typescript
```

---

### TASK-PD-013: Split fastapi-python Agents (Workspace B)
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` script execution |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** - independent of PD-012/014/015 |

**Execution**:
```bash
cd ../guardkit-pd-fastapi
python3 scripts/split-agent.py --template fastapi-python
```

---

### TASK-PD-014: Split nextjs-fullstack Agents (Workspace C)
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` script execution |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** - independent of PD-012/013/015 |

**Execution**:
```bash
cd ../guardkit-pd-nextjs
python3 scripts/split-agent.py --template nextjs-fullstack
```

---

### TASK-PD-015: Split react-fastapi-monorepo Agents (Workspace D)
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` script execution |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** - independent of PD-012/013/014 |

**Execution**:
```bash
cd ../guardkit-pd-monorepo
python3 scripts/split-agent.py --template react-fastapi-monorepo
```

### Merge Strategy for Parallel Work

```bash
# After all 4 complete, merge back to main
git checkout main
git merge react-typescript-split
git merge fastapi-split
git merge nextjs-split
git merge monorepo-split

# Clean up worktrees
git worktree remove ../guardkit-pd-react
git worktree remove ../guardkit-pd-fastapi
git worktree remove ../guardkit-pd-nextjs
git worktree remove ../guardkit-pd-monorepo
```

---

## Wave 5: Validation & Documentation

**Duration**: 3 days
**Workspaces**: 2 (PD-016/017 parallel, then sequential)

### TASK-PD-016: Update Template Validation (Workspace A)
| Attribute | Value |
|-----------|-------|
| **Method** | `/task-work` |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | **YES** - with PD-017 |

**Why /task-work**: Adds validation rules, needs tests.

---

### TASK-PD-017: Update CLAUDE.md Documentation (Workspace B)
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | **YES** - with PD-016 |

**Why Direct**: Documentation updates, no code changes.

---

### TASK-PD-018: Update Command Documentation
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on PD-016/017 |

---

### TASK-PD-019: Full Integration Testing
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` with script |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | No - final validation |

**Execution**:
```bash
# Run integration test script
bash scripts/test-progressive-disclosure.sh

# Capture after measurement
python3 scripts/measure-token-usage.py --after

# Generate comparison report
python3 scripts/measure-token-usage.py --compare
```

---

## Wave 6: Content Migration (NEW)

**Duration**: 3-4 days
**Workspaces**: 1-3 (Wave B parallel possible)
**Review Task**: TASK-REV-PD-CONTENT

This wave migrates actual content from core agent files to extended files, achieving the 55% token reduction target.

### TASK-PD-020: Define Content Migration Rules
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - establishes rules for subsequent tasks |

**Why Direct**: Documentation and rule definition, creates migration script.

**Execution**:
```bash
# Claude Code creates:
# - docs/guides/content-migration-rules.md
# - scripts/migrate-agent-content.py (or updates split-agent.py)
```

**Output**: Content categorization rules defining what stays in core vs moves to extended.

---

### TASK-PD-021: Migrate High-Priority Agents
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 5/10 |
| **Effort** | 1 day |
| **Parallel** | No - validates approach before bulk migration |

**Why Direct**: Content reorganization, not code changes.

**Target Agents**:
- task-manager (70.4KB → ≤25KB core)
- devops-specialist (56.1KB → ≤20KB core)

**Execution**:
```bash
# Migrate task-manager
# Move detailed examples, best practices, troubleshooting to ext file
# Keep frontmatter, quick start, boundaries in core

# Validate
wc -c installer/core/agents/task-manager.md  # Should be ≤25KB
```

**CHECKPOINT**: Review migration quality before proceeding to bulk.

---

### TASK-PD-022: Migrate Remaining Agents
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 5/10 |
| **Effort** | 1-1.5 days |
| **Parallel** | **YES** - can split into 3 workspaces (Wave A/B/C) |

**Why Direct**: Bulk content migration following established patterns.

**Target Agents**: 12 remaining global agents

**Parallel Execution Option**:
```bash
# Workspace A: Wave A (large agents 40KB+)
git worktree add ../guardkit-pd-wave-a wave-a

# Workspace B: Wave B (medium agents 25-35KB)
git worktree add ../guardkit-pd-wave-b wave-b

# Workspace C: Wave C (small agents <25KB)
git worktree add ../guardkit-pd-wave-c wave-c
```

---

### TASK-PD-023: Add Loading Instructions
| Attribute | Value |
|-----------|-------|
| **Method** | `Direct` Claude Code |
| **Complexity** | 3/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - depends on content migration |

**Why Direct**: Simple template addition to all core files.

**Execution**:
```bash
# Add "## Extended Reference" section to all 14 core agents
# Include loading instruction: cat agents/{name}-ext.md
```

---

### TASK-PD-024: Final Validation and Metrics
| Attribute | Value |
|-----------|-------|
| **Method** | `Manual` validation |
| **Complexity** | 4/10 |
| **Effort** | 0.5 days |
| **Parallel** | No - final validation |

**Why Manual**: Human runs validation scripts, reviews metrics.

**Execution**:
```bash
# Run integration tests
./scripts/test-progressive-disclosure.sh

# Validate token reduction
python3 -c "
from pathlib import Path
core_total = sum(f.stat().st_size for f in Path('installer/core/agents').glob('*.md') if not f.stem.endswith('-ext'))
print(f'Core total: {core_total/1024:.1f}KB')
print(f'Reduction: {(1 - core_total/520806)*100:.1f}%')  # 520806 = baseline
"

# Should show ≥55% reduction
```

**FINAL CHECKPOINT**: Review and close TASK-REV-PD-CONTENT

---

## Summary: Task Matrix

### Phases 0-5 (Infrastructure) ✅ COMPLETE

| Task | Method | Complexity | Effort | Can Parallel | Status |
|------|--------|------------|--------|--------------|--------|
| PD-000 | Direct | 4 | 0.5d | No | ✅ |
| PD-001 | /task-work | 7 | 2-3d | No | ✅ |
| PD-002 | Direct | 4 | 0.5d | No | ✅ |
| PD-003 | /task-work | 5 | 1d | No | ✅ |
| PD-004 | Direct | 3 | 0.5d | No | ✅ |
| PD-005 | /task-work | 6 | 2d | No | ✅ |
| PD-006 | /task-work | 5 | 1d | No | ✅ |
| PD-007 | Direct | 4 | 0.5d | No | ✅ |
| PD-008 | Direct | 6 | 1.5d | No | ✅ |
| PD-009 | Direct | 5 | 0.5d | No | ✅ |
| PD-010 | Manual | 4 | 1d | No | ✅ |
| PD-011 | Manual | 4 | 0.5d | No | ✅ |
| PD-012 | Manual | 4 | 0.5d | **YES** | ✅ |
| PD-013 | Manual | 4 | 0.5d | **YES** | ✅ |
| PD-014 | Manual | 4 | 0.5d | **YES** | ✅ |
| PD-015 | Manual | 4 | 0.5d | **YES** | ✅ |
| PD-016 | /task-work | 5 | 1d | **YES** | ✅ |
| PD-017 | Direct | 3 | 0.5d | **YES** | ✅ |
| PD-018 | Direct | 3 | 0.5d | No | ✅ |
| PD-019 | Manual | 5 | 1d | No | ✅ |

### Phase 6 (Content Migration) 🔄 IN PROGRESS

| Task | Method | Complexity | Effort | Can Parallel | Status |
|------|--------|------------|--------|--------------|--------|
| **PD-020** | Direct | 4 | 0.5d | No | Backlog |
| **PD-021** | Direct | 5 | 1d | No | Backlog |
| **PD-022** | Direct | 5 | 1-1.5d | **YES** (3 waves) | Backlog |
| **PD-023** | Direct | 3 | 0.5d | No | Backlog |
| **PD-024** | Manual | 4 | 0.5d | No | Backlog |

## Method Breakdown

| Method | Task Count | Total Effort |
|--------|------------|--------------|
| `/task-work` | 5 tasks | 7-8 days |
| `Direct` Claude Code | 14 tasks | 8.5-9 days |
| `Manual` script/validation | 6 tasks | 4 days |

## Parallel Execution Savings

**Infrastructure (Phases 0-5)**: 16.5-18.5 days → **13-15 days** with parallel
**Content Migration (Phase 6)**: 3-4 days → **2-3 days** with parallel (Wave B split)

**Total with Parallel**: ~15-18 days (vs 19.5-22.5 sequential)

---

## Recommended Execution Order

### Phases 0-5 (Infrastructure) ✅ COMPLETE

```
Day 1:     PD-000 (baseline)
Days 2-4:  PD-001 (/task-work - foundation)
Day 5:     PD-002, PD-003
Day 6:     PD-004, CHECKPOINT 1
Days 7-8:  PD-005 (/task-work - generator)
Day 9:     PD-006, PD-007, CHECKPOINT 2
Days 10-11: PD-008, PD-009 (script)
Day 12:    PD-010, PD-011, CHECKPOINT 3
Day 13:    PD-012/013/014/015 (PARALLEL in 4 workspaces)
Day 14:    PD-016/017 (PARALLEL in 2 workspaces)
Day 15:    PD-018, PD-019 (Infrastructure COMPLETE)
```

### Phase 6 (Content Migration) 🔄 NEXT

```
Day 16:    PD-020 (migration rules)
Day 17:    PD-021 (high-priority agents: task-manager, devops-specialist)
           CHECKPOINT: Review migration quality
Days 18-19: PD-022 (remaining 12 agents - can parallelize in 3 workspaces)
Day 20:    PD-023, PD-024 (loading instructions + final validation)
           FINAL CHECKPOINT: Close TASK-REV-PD-CONTENT
```

## Final Deliverables

### Infrastructure (Phases 0-5) ✅
1. `measurements/baseline.json` - Before metrics
2. Agent scanner excludes `-ext.md` files
3. Extended file structure (14 core + 14 extended)
4. Documentation updated
5. Integration tests passing (6/6)

### Content Migration (Phase 6) 🔄
6. All core agents reduced to ≤ target size
7. All extended files contain migrated content
8. Loading instructions in all core files
9. Token reduction ≥55% validated
10. `docs/reports/progressive-disclosure-implementation-report.md` updated
11. Blog content data ready
