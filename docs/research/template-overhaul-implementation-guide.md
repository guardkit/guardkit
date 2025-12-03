# Template Overhaul Implementation Guide

**Created**: 2025-01-08
**Purpose**: Execution plan for template strategy overhaul with parallel development opportunities

---

## Executive Summary

**Total Tasks**: 11 tasks
- **Validation Infrastructure** (TASK-043, 044, 045): 6-9 days (prerequisite)
- **Template Overhaul** (TASK-056 through TASK-063): 28-41 days

**Timeline**:
- **Sequential**: 10-11 weeks total (1-1.5 weeks validation + 8 weeks templates)
- **Parallel (Solo with Conductor)**: 7-8 weeks total (1-1.5 weeks validation + 6 weeks templates)
- **Parallel (Team of 3)**: 5-6 weeks total (1-1.5 weeks validation + 4 weeks templates)

**All tasks use `/task-work`** for quality gates (architectural review, test enforcement, code review).

**Validation-Enhanced Workflow**: All template creation tasks (TASK-057, 058, 059, 062) leverage `/template-create --validate` and `/template-validate` commands to achieve 9+/10 quality scores systematically.

---

## Prerequisite: Validation Infrastructure (1-1.5 weeks)

**CRITICAL**: TASK-043, 044, 045 must be completed BEFORE template creation tasks (TASK-057, 058, 059, 062).

### Validation Tasks (Sequential Execution Required)

| Task | Description | Duration | Command |
|------|-------------|----------|---------|
| **TASK-043** | Extended Validation Flag (`--validate`) | 1 day | `/task-work TASK-043` |
| **TASK-044** | Template Validate Command (16-section audit) | 3-5 days | `/task-work TASK-044` |
| **TASK-045** | AI-Assisted Validation (sections 8,11,12,13) | 2-3 days | `/task-work TASK-045` |

**Why This Order**:
1. TASK-043 adds `--validate` flag to `/template-create` (extended validation with reports)
2. TASK-044 creates `/template-validate` command (comprehensive 16-section audit)
3. TASK-045 adds AI assistance to TASK-044 (speeds up audits from 2-3 hours to 30-60 min)

**Total Validation Infrastructure**: 6-9 days

### Week 0: Validation Infrastructure Setup

```bash
# Execute sequentially
/task-work TASK-043  # 1 day - Extended validation flag
/task-work TASK-044  # 3-5 days - Template validate command
/task-work TASK-045  # 2-3 days - AI-assisted validation
```

**After completion**:
- ✅ `/template-create --validate` available
- ✅ `/template-validate <path> --sections 1-16` available
- ✅ AI assistance in sections 8, 11, 12, 13
- ✅ Ready for template creation with systematic quality validation

---

## Task Dependency Graph

```
                    TASK-043
                (Validation Flag)
                        ↓
                    TASK-044
                (Template Validate)
                        ↓
                    TASK-045
                (AI-Assisted Validation)
                        ↓
                    ─────────
                        ↓
                    TASK-056
                    (Audit)
                        ↓
        ├───────────────┼───────────────┬─────────────┐
        ↓               ↓               ↓             ↓
    TASK-057        TASK-058        TASK-059    (parallel)
    (React)         (FastAPI)       (Next.js)
    Uses:           Uses:           Uses:
    - /template-create --validate
    - /template-validate
        ↓               ↓               ↓
        └────────┬──────┘               │
                 ↓                      │
             TASK-062                   │
            (Monorepo)                  │
            Uses:                       │
            - /template-create --validate
            - /template-validate
                 ↓                      │
                 └──────────┬───────────┘
                            ↓
                        TASK-060
                        (Remove)
                            ↓
                        TASK-061
                    (Docs 3-template)
                            ↓
                        TASK-063
                    (Docs 4-template)
```

**Key Dependencies**:
- **TASK-043, 044, 045** must complete BEFORE template creation (validation infrastructure prerequisite)
- TASK-057, TASK-058, TASK-059 can run **in parallel** (independent, but all require TASK-043/044/045)
- TASK-062 **depends on** TASK-057 + TASK-058 completion
- TASK-060 waits for all template creation complete
- TASK-061 and TASK-063 can run **sequentially** or in parallel with final review

**Validation-Enhanced Workflow** (all template tasks):
1. Clone/create source codebase
2. Execute `/template-create --validate` (uses TASK-043)
3. Execute `/template-validate <path> --sections 1-16` (uses TASK-044, 045)
4. Iterative improvement loop (refine → re-validate)
5. Achieve 9+/10 score before task completion

---

## Use of `/task-work` Command

### All Tasks Use `/task-work`

**Why**: Every task benefits from built-in quality gates:
- ✅ Phase 2.5: Architectural review (SOLID/DRY/YAGNI)
- ✅ Phase 4.5: Test enforcement (auto-fix up to 3 attempts)
- ✅ Phase 5: Code review
- ✅ Phase 5.5: Plan audit (scope creep detection)

### Task-by-Task Execution

| Task | Command | Quality Gates Used | Duration |
|------|---------|-------------------|----------|
| **TASK-056** | `/task-work TASK-056` | Phase 2.5 (audit logic), Phase 4.5 (validation tests) | 3-5 days |
| **TASK-057** | `/task-work TASK-057` | All phases (template creation is complex) | 5-7 days |
| **TASK-058** | `/task-work TASK-058` | All phases (template creation is complex) | 5-7 days |
| **TASK-059** | `/task-work TASK-059` | All phases (most complex, Next.js patterns) | 7-10 days |
| **TASK-062** | `/task-work TASK-062` | All phases (combines 057+058, monorepo complexity) | 3-5 days |
| **TASK-060** | `/task-work TASK-060` | Phase 2.5 (removal logic), Phase 5.5 (completeness) | 2-3 days |
| **TASK-061** | `/task-work TASK-061` | Phase 5.5 (documentation completeness) | 3-4 days |
| **TASK-063** | `/task-work TASK-063` | Phase 5.5 (documentation completeness) | 3-4 days |

**Design-First Option** (for complex tasks):
```bash
# If you want to review plan before implementation
/task-work TASK-059 --design-only
# [Review and approve implementation plan]
/task-work TASK-059 --implement-only
```

---

## Parallel Development Strategies

### Strategy 1: Solo Developer with Conductor (Recommended)

**Timeline**: 7-8 weeks total (vs 10-11 weeks sequential)
- **Week 0**: 1-1.5 weeks (Validation Infrastructure)
- **Weeks 1-6**: 6 weeks (Template Overhaul)

**Approach**: Use Conductor git worktrees to work on independent templates simultaneously.

#### Week 0: Validation Infrastructure (Sequential - Prerequisites)
```bash
# Main repository - MUST complete before template creation
/task-work TASK-043  # 1 day - Extended validation flag
/task-work TASK-044  # 3-5 days - Template validate command
/task-work TASK-045  # 2-3 days - AI-assisted validation

# Result: Validation tooling ready
# - /template-create --validate available
# - /template-validate command available
# - AI assistance ready
```

#### Week 1: Foundation (Sequential)
```bash
# Main repository
/task-work TASK-056  # Audit all existing templates using new validation tools

# Result: Comparative analysis, removal plan
```

#### Week 2-3: Parallel Template Creation (3 Worktrees)
```bash
# Create worktrees for parallel development
conductor worktree create template-react
conductor worktree create template-fastapi
conductor worktree create template-nextjs

# Terminal 1: React template
cd template-react
/task-work TASK-057
# 5-7 days work

# Terminal 2: FastAPI template
cd template-fastapi
/task-work TASK-058
# 5-7 days work

# Terminal 3: Next.js template
cd template-nextjs
/task-work TASK-059
# 7-10 days work (longest)
```

**Key Points**:
- Work on one task at a time, switching contexts
- OR open 3 Claude Code instances (one per worktree)
- Each worktree is isolated (no conflicts)
- All use same shared state (`.claude/state` symlinked)

**Timeline**:
- Days 1-5: Primary focus TASK-057 (complete)
- Days 6-10: Primary focus TASK-058 (complete)
- Days 11-17: Primary focus TASK-059 (complete)
- **Net**: ~17 days for all 3 templates (vs 19-24 days sequential)

#### Week 4: Monorepo (Sequential)
```bash
# After TASK-057 and TASK-058 complete
cd main-repo  # or new worktree
/task-work TASK-062  # Combines 057 + 058

# 3-5 days
```

#### Week 5: Cleanup (Sequential)
```bash
# Merge all worktrees back to main
conductor worktree merge  # For each worktree

# Remove low-quality templates
/task-work TASK-060

# 2-3 days
```

#### Week 6: Documentation (Can parallelize with review)
```bash
# Can split into 2 worktrees if desired
/task-work TASK-061  # Base documentation
/task-work TASK-063  # Monorepo additions

# OR sequential:
/task-work TASK-061 && /task-work TASK-063

# 3-4 days each, or 6-8 days sequential
```

**Total: ~6 weeks** (25% faster than sequential)

---

### Strategy 2: Team of 3 Developers

**Timeline**: 4 weeks

**Approach**: Each developer owns template(s) in parallel worktrees.

#### Week 1: Foundation (Shared)
```bash
# Developer A handles audit
cd main-repo
/task-work TASK-056

# Developers B & C review results
```

#### Week 2-3: Parallel Template Creation
```bash
# Developer A: React template
conductor worktree create template-react
cd template-react
/task-work TASK-057
# ~5-7 days

# Developer B: FastAPI template
conductor worktree create template-fastapi
cd template-fastapi
/task-work TASK-058
# ~5-7 days

# Developer C: Next.js template
conductor worktree create template-nextjs
cd template-nextjs
/task-work TASK-059
# ~7-10 days (longest, but parallel)
```

**Timeline**: All 3 templates done in ~10 days (parallel)

#### Week 3: Monorepo + Cleanup (Parallel)
```bash
# Developer A: Monorepo (after React + FastAPI merged)
cd main-repo
/task-work TASK-062
# 3-5 days

# Developer B: Start documentation
/task-work TASK-061
# 3-4 days

# Developer C: Continue Next.js if not done, then removal
/task-work TASK-060
# 2-3 days
```

#### Week 4: Final Documentation
```bash
# Developer A: Monorepo documentation
/task-work TASK-063
# 3-4 days

# Developer B: Reviews and tests
# Developer C: Integration testing
```

**Total: ~4 weeks** (50% faster than sequential)

---

### Strategy 3: AI Agent Swarm (Experimental)

**Timeline**: 3-4 weeks

**Approach**: Multiple Claude Code instances, each handling one task.

```bash
# Instance 1: Audit
/task-work TASK-056

# After audit, spawn 3 instances in parallel:

# Instance 2: React
conductor worktree create template-react
/task-work TASK-057

# Instance 3: FastAPI
conductor worktree create template-fastapi
/task-work TASK-058

# Instance 4: Next.js
conductor worktree create template-nextjs
/task-work TASK-059

# After 057+058 complete:
# Instance 5: Monorepo
/task-work TASK-062

# Instance 6: Removal
/task-work TASK-060

# Instance 7 & 8: Documentation
/task-work TASK-061
/task-work TASK-063
```

**Total: ~3-4 weeks** (aggressive parallelization)

---

## Detailed Task Execution Plans

### TASK-056: Audit Existing Templates

**Command**:
```bash
/task-work TASK-056
```

**What `/task-work` Does**:
1. **Phase 2**: Plan audit process (for each of 9 templates)
2. **Phase 2.5**: Architectural review of audit logic
3. **Phase 3**: Execute audits (run `/template-validate` on each)
4. **Phase 4**: Test validation (ensure audit reports generated)
5. **Phase 4.5**: Auto-fix any test failures
6. **Phase 5**: Code review audit implementation
7. **Phase 5.5**: Verify all 9 templates audited

**Outputs**:
- `docs/research/template-audit-comparative-analysis.md`
- `docs/research/template-removal-plan.md`
- Individual audit reports for each template

**Duration**: 3-5 days

**Parallel Opportunity**: None (foundation for other tasks)

---

### TASK-057, TASK-058, TASK-059: Create Reference Templates

**Commands** (can run in parallel):
```bash
# Worktree 1
conductor worktree create template-react
cd template-react
/task-work TASK-057

# Worktree 2
conductor worktree create template-fastapi
cd template-fastapi
/task-work TASK-058

# Worktree 3
conductor worktree create template-nextjs
cd template-nextjs
/task-work TASK-059
```

**What `/task-work` Does** (for each):
1. **Phase 2**: Plan template creation (clone source, analyze patterns)
2. **Phase 2.5**: Architectural review (SOLID, patterns, structure)
3. **Phase 3**: Implement template (use `/template-create`, enhancements)
4. **Phase 4**: Testing (template validates at 9+/10)
5. **Phase 4.5**: Auto-fix validation issues (iterative improvement)
6. **Phase 5**: Code review template quality
7. **Phase 5.5**: Verify completeness (manifest, settings, agents, docs)

**Outputs** (per template):
- `installer/global/templates/{template-name}/`
- Validation report scoring 9+/10
- README, CLAUDE.md, manifest.json, settings.json
- AI agents for template

**Duration**:
- TASK-057: 5-7 days
- TASK-058: 5-7 days
- TASK-059: 7-10 days

**Parallel Opportunity**: ✅ **All 3 can run simultaneously** (independent)

**Conductor Setup**:
```bash
# Ensure GuardKit symlinks created
./installer/scripts/install.sh

# Create 3 worktrees
conductor worktree create template-react
conductor worktree create template-fastapi
conductor worktree create template-nextjs

# Verify state sharing
ls -la template-react/.claude/state  # Should be symlink
ls -la template-fastapi/.claude/state  # Should be symlink
ls -la template-nextjs/.claude/state  # Should be symlink
```

**Merge Strategy** (after completion):
```bash
# Merge in order (least dependencies first)
git checkout main
git merge template-react
git merge template-fastapi
git merge template-nextjs

# OR use Conductor
conductor worktree merge  # For each worktree
```

---

### TASK-062: Create Monorepo Template

**Command**:
```bash
# After TASK-057 and TASK-058 merged
/task-work TASK-062
```

**What `/task-work` Does**:
1. **Phase 2**: Plan monorepo structure (combine 057+058, add Turborepo)
2. **Phase 2.5**: Architectural review (monorepo patterns, type safety)
3. **Phase 3**: Implement (combine templates, Docker Compose, type gen)
4. **Phase 4**: Testing (monorepo validates at 9+/10)
5. **Phase 4.5**: Auto-fix issues (Docker, type generation, builds)
6. **Phase 5**: Code review
7. **Phase 5.5**: Verify completeness

**Outputs**:
- `installer/global/templates/react-fastapi-monorepo/`
- Monorepo structure with Turborepo + Docker Compose
- Type generation working
- Validation report 9+/10

**Duration**: 3-5 days

**Parallel Opportunity**: ❌ **Depends on** TASK-057 + TASK-058 completion

**Note**: Can run in parallel with TASK-059 if desired.

---

### TASK-060: Remove Low-Quality Templates

**Command**:
```bash
# After all new templates created
/task-work TASK-060
```

**What `/task-work` Does**:
1. **Phase 2**: Plan removal (which templates, migration paths)
2. **Phase 2.5**: Review removal logic
3. **Phase 3**: Execute removal (archive branch, delete, update scripts)
4. **Phase 4**: Test installation with remaining templates
5. **Phase 4.5**: Fix any broken references
6. **Phase 5**: Code review
7. **Phase 5.5**: Verify all references updated

**Outputs**:
- Archive branch: `archive/templates-pre-v2.0`
- Updated installation script
- Migration guide

**Duration**: 2-3 days

**Parallel Opportunity**: ❌ **Depends on** all template creation complete

---

### TASK-061, TASK-063: Update Documentation

**Commands**:
```bash
# Sequential
/task-work TASK-061  # Base documentation (3 templates)
/task-work TASK-063  # Add 4th template

# OR Parallel (if using worktrees)
conductor worktree create docs-base
cd docs-base
/task-work TASK-061

cd ../main-repo
/task-work TASK-063
# Then merge
```

**What `/task-work` Does**:
1. **Phase 2**: Plan documentation updates (files, sections, messaging)
2. **Phase 2.5**: Review documentation structure
3. **Phase 3**: Update all documentation files
4. **Phase 4**: Test (no broken links, consistent messaging)
5. **Phase 4.5**: Fix broken references
6. **Phase 5**: Review documentation quality
7. **Phase 5.5**: Verify completeness (all files updated)

**Outputs**:
- Updated CLAUDE.md, README.md
- Updated all guides
- Template Philosophy guide
- Migration guide

**Duration**:
- TASK-061: 3-4 days
- TASK-063: 3-4 days

**Parallel Opportunity**: ⚠️ **Can run in parallel** if careful about file conflicts

---

## Conductor Worktree Best Practices

### Setup
```bash
# 1. Install GuardKit (creates symlinks)
./installer/scripts/install.sh

# 2. Verify state symlinks
ls -la .claude/state  # Should be symlinked to main repo

# 3. Create worktree for each parallel task
conductor worktree create <name>
```

### State Sharing
**Automatic via symlinks**:
- Commands: `~/.claude/*` → `~/.agentecflow/*` (global, shared)
- State: `{worktree}/.claude/state` → `{main-repo}/.claude/state` (shared)
- Agents: Global installation, shared across worktrees

**Result**: All worktrees share same commands, agents, state.

### Merge Strategy
```bash
# Option 1: Sequential merges
git checkout main
git merge worktree-1
git merge worktree-2
git merge worktree-3

# Option 2: Conductor merge
conductor worktree merge  # In each worktree

# Option 3: Manual merge with testing
git merge --no-ff worktree-1
# Test
git merge --no-ff worktree-2
# Test
```

### Conflict Resolution
**Minimal conflicts expected because**:
- Each template goes to separate directory
- No shared template files
- State is symlinked (shared automatically)
- Documentation conflicts handled in TASK-061/063

**If conflicts occur**:
```bash
git merge worktree-name
# Resolve conflicts
git mergetool
# Or manual resolution
git add .
git commit
```

---

## Timeline Comparison

### Sequential Execution (8 weeks)
```
Week 1: TASK-056 (Audit)
Week 2: TASK-057 (React)
Week 3: TASK-058 (FastAPI)
Week 4-5: TASK-059 (Next.js)
Week 5: TASK-062 (Monorepo)
Week 6: TASK-060 (Remove)
Week 7: TASK-061 (Docs)
Week 8: TASK-063 (Docs)
```

### Solo with Conductor (6 weeks)
```
Week 1: TASK-056 (Audit)
Week 2-3: TASK-057, 058, 059 (Parallel, context switching)
Week 4: TASK-062 (Monorepo)
Week 5: TASK-060 (Remove)
Week 6: TASK-061, 063 (Docs, sequential or parallel)
```

### Team of 3 (4 weeks)
```
Week 1: TASK-056 (Audit - Dev A)
Week 2-3:
  - TASK-057 (React - Dev A)
  - TASK-058 (FastAPI - Dev B)
  - TASK-059 (Next.js - Dev C)
Week 3-4:
  - TASK-062 (Monorepo - Dev A)
  - TASK-061 (Docs - Dev B)
  - TASK-060 (Remove - Dev C)
Week 4:
  - TASK-063 (Docs - Dev A)
  - Review/Test - Dev B, C
```

### AI Agent Swarm (3-4 weeks)
```
Week 1: TASK-056 (Agent 1)
Week 2-3: TASK-057, 058, 059 (Agents 2, 3, 4 - fully parallel)
Week 3: TASK-062 (Agent 5)
Week 3: TASK-060 (Agent 6)
Week 4: TASK-061, 063 (Agents 7, 8)
```

---

## Quality Gates Summary

All tasks go through same quality gates via `/task-work`:

| Phase | Gate | Purpose |
|-------|------|---------|
| **2.5** | Architectural Review | Ensure SOLID/DRY/YAGNI compliance |
| **4.5** | Test Enforcement | Auto-fix failures (up to 3 attempts) |
| **5** | Code Review | Quality assurance |
| **5.5** | Plan Audit | Prevent scope creep, verify completeness |

**Result**: All templates guaranteed 9+/10 quality through automated gates.

---

## Success Metrics

### Per-Task Metrics
- [ ] All tasks use `/task-work`: 8/8
- [ ] All quality gates passed: 100%
- [ ] All templates score 9+/10: 4/4
- [ ] All documentation updated: 100%

### Overall Metrics
- [ ] Templates reduced: 9 → 4 (56% reduction)
- [ ] Maintenance burden reduced: 56%
- [ ] All templates validated: 9+/10
- [ ] Timeline: ≤6 weeks (solo with Conductor)
- [ ] Zero scope creep (Phase 5.5 gates)

---

## Troubleshooting

### Issue: Conductor Worktree Conflicts
**Solution**: Ensure `.claude/state` symlink exists in each worktree
```bash
ls -la {worktree}/.claude/state
# If not symlink, re-run installer
./installer/scripts/install.sh
```

### Issue: Template Validation Fails
**Solution**: Iterative improvement using `/task-work` Phase 4.5 auto-fix

### Issue: Documentation Conflicts (TASK-061 vs TASK-063)
**Solution**: Run TASK-061 first, then TASK-063 builds on it

---

## Next Steps

1. **Review this guide** and approve parallel strategy
2. **Start TASK-056** (foundation, sequential)
3. **Create Conductor worktrees** for TASK-057, 058, 059
4. **Execute parallel development** (solo or team)
5. **Merge and validate** after each phase
6. **Complete documentation** (TASK-061, 063)

---

**Implementation Guide Status**: Ready for Execution
**Created**: 2025-01-08
**Updated**: 2025-01-08
**Timeline**: 6-8 weeks depending on parallelization strategy
