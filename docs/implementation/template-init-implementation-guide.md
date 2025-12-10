# Template-Init Feature Porting: Implementation Guide

**Parent Review**: TASK-5E55
**Decision**: Option B - Port Features (Approved)
**Timeline**: 5 weeks, 60 hours
**Status**: Ready for implementation

---

## Quick Start

```bash
# Week 1: Critical Features (14 hours)
/task-work TASK-INIT-001  # Boundary sections (8 hours)
/task-work TASK-INIT-002  # Agent enhancement tasks (6 hours)

# Week 2: Validation Framework (12 hours) - CAN RUN IN PARALLEL
/task-work TASK-INIT-003  # Level 1 validation (4 hours)
/task-work TASK-INIT-004  # Level 2 validation (4 hours)
/task-work TASK-INIT-005  # Level 3 integration (4 hours)

# Week 3: Quality & Distribution (10 hours) - CAN RUN IN PARALLEL
/task-work TASK-INIT-006  # Quality scoring (6 hours)
/task-work TASK-INIT-007  # Two-location output (4 hours)

# Week 4: Discovery & Automation (6 hours) - CAN RUN IN PARALLEL
/task-work TASK-INIT-008  # Discovery metadata (4 hours)
/task-work TASK-INIT-009  # Exit codes (2 hours)

# Week 5: Polish (8 hours)
/task-work TASK-INIT-010  # Documentation (4 hours)
/task-work TASK-INIT-011  # Comprehensive testing (8 hours)
```

---

## Implementation Workflow

### Use /task-work for Implementation Tasks

**ALL IMPLEMENTATION TASKS** use `/task-work` command (TASK-INIT-001 through TASK-INIT-011).

**DO NOT** use `/task-review` - that's for analysis/decision tasks only.

### Standard Mode (Recommended)

```bash
/task-work TASK-INIT-XXX
```

All tasks are straightforward implementations with detailed specifications, so **standard mode** is recommended (not TDD).

### Why Standard Mode?

- Detailed code snippets provided (BEFORE/AFTER with line numbers)
- Clear integration points identified
- MINIMAL SCOPE principle enforced
- Low complexity (2-6 on 10-point scale)
- Unit tests written after implementation

---

## Wave-Based Implementation Strategy

### Wave 1: Week 1 - Critical Features (Sequential)

**Duration**: 14 hours
**Parallelization**: ❌ **MUST BE SEQUENTIAL**

```bash
# Task 1: Boundary sections (PREREQUISITE for Task 2)
/task-work TASK-INIT-001
/task-complete TASK-INIT-001

# Task 2: Agent enhancement tasks (depends on Task 1)
/task-work TASK-INIT-002
/task-complete TASK-INIT-002
```

**Why Sequential?**
- TASK-INIT-002 references boundary sections from TASK-INIT-001
- Agent enhancement tasks need boundary logic in place

**Quality Gate**: Verify both features work together before Week 2

---

### Wave 2: Week 2 - Validation Framework (Parallel)

**Duration**: 12 hours
**Parallelization**: ✅ **ALL 3 TASKS CAN RUN IN PARALLEL**

```bash
# Option A: Sequential (Solo Developer)
/task-work TASK-INIT-003  # Level 1 validation (4 hours)
/task-complete TASK-INIT-003

/task-work TASK-INIT-004  # Level 2 validation (4 hours)
/task-complete TASK-INIT-004

/task-work TASK-INIT-005  # Level 3 integration (4 hours)
/task-complete TASK-INIT-005

# Option B: Parallel (Team of 3 using Conductor)
# See "Conductor Parallel Development" section below
```

**Why Parallel?**
- TASK-INIT-003 (Level 1) is independent
- TASK-INIT-004 (Level 2) uses Level 1 results but doesn't modify Level 1 code
- TASK-INIT-005 (Level 3) only adds compatibility fields

**Quality Gate**: All 3 validation levels work independently and together

---

### Wave 3: Week 3 - Quality & Distribution (Parallel)

**Duration**: 10 hours
**Parallelization**: ✅ **BOTH TASKS CAN RUN IN PARALLEL**

```bash
# Option A: Sequential (Solo Developer)
/task-work TASK-INIT-006  # Quality scoring (6 hours)
/task-complete TASK-INIT-006

/task-work TASK-INIT-007  # Two-location output (4 hours)
/task-complete TASK-INIT-007

# Option B: Parallel (Team of 2 using Conductor)
# Developer 1: TASK-INIT-006
# Developer 2: TASK-INIT-007
```

**Why Parallel?**
- TASK-INIT-006 (quality scoring) adds new QualityScorer class
- TASK-INIT-007 (two-location output) modifies path resolution
- No overlapping code changes

**Quality Gate**: Quality scoring and output locations work together

---

### Wave 4: Week 4 - Discovery & Automation (Parallel)

**Duration**: 6 hours
**Parallelization**: ✅ **BOTH TASKS CAN RUN IN PARALLEL**

```bash
# Option A: Sequential (Solo Developer)
/task-work TASK-INIT-008  # Discovery metadata (4 hours)
/task-complete TASK-INIT-008

/task-work TASK-INIT-009  # Exit codes (2 hours)
/task-complete TASK-INIT-009

# Option B: Parallel (Team of 2 using Conductor)
# Developer 1: TASK-INIT-008 (requires TASK-INIT-001 complete)
# Developer 2: TASK-INIT-009 (requires TASK-INIT-006 complete)
```

**Why Parallel?**
- TASK-INIT-008 (discovery metadata) adds frontmatter generation
- TASK-INIT-009 (exit codes) modifies run() return type
- Different code sections

**Dependencies**:
- TASK-INIT-008 depends on TASK-INIT-001 (boundary sections)
- TASK-INIT-009 depends on TASK-INIT-006 (quality scoring)

**Quality Gate**: Agent discovery works, exit codes reflect quality

---

### Wave 5: Week 5 - Polish (Sequential)

**Duration**: 8 hours
**Parallelization**: ❌ **MUST BE SEQUENTIAL**

```bash
# Task 10: Documentation (requires ALL tasks 1-9 complete)
/task-work TASK-INIT-010
/task-complete TASK-INIT-010

# Task 11: Testing (requires ALL tasks 1-9 complete)
/task-work TASK-INIT-011
/task-complete TASK-INIT-011
```

**Why Sequential?**
- TASK-INIT-010 (documentation) documents all ported features
- TASK-INIT-011 (testing) tests all ported features
- Both require complete implementation

**Quality Gate**: Documentation accurate, all tests pass, coverage ≥80%

---

## Conductor Parallel Development Guide

[Conductor](https://conductor.build) enables parallel development using git worktrees. Each developer works in an isolated worktree while sharing committed progress.

### Setup (One-Time)

```bash
# Ensure GuardKit is installed
./installer/scripts/install.sh

# Verify symlinks are set up
guardkit doctor

# Main repository is your "coordination branch"
cd ~/Projects/appmilla_github/guardkit
git checkout main
```

### Wave 2 Example: 3 Developers in Parallel

**Developer 1: Level 1 Validation**

```bash
# Create worktree for Task 3
cd ~/Projects/appmilla_github/guardkit
conductor create task-init-003 --base=main

# Switch to worktree (Conductor auto-switches)
cd ~/conductor-workspaces/guardkit-task-init-003

# Implement feature
/task-work TASK-INIT-003

# Commit and push
git add .
git commit -m "feat: Add Level 1 automatic validation (TASK-INIT-003)"
git push origin task-init-003

# Complete task
/task-complete TASK-INIT-003

# Merge to main via PR
# Then delete worktree
conductor delete task-init-003
```

**Developer 2: Level 2 Validation** (parallel)

```bash
cd ~/Projects/appmilla_github/guardkit
conductor create task-init-004 --base=main

cd ~/conductor-workspaces/guardkit-task-init-004
/task-work TASK-INIT-004

git add .
git commit -m "feat: Add Level 2 extended validation (TASK-INIT-004)"
git push origin task-init-004

/task-complete TASK-INIT-004

# Merge to main via PR
conductor delete task-init-004
```

**Developer 3: Level 3 Integration** (parallel)

```bash
cd ~/Projects/appmilla_github/guardkit
conductor create task-init-005 --base=main

cd ~/conductor-workspaces/guardkit-task-init-005
/task-work TASK-INIT-005

git add .
git commit -m "feat: Add Level 3 validation compatibility (TASK-INIT-005)"
git push origin task-init-005

/task-complete TASK-INIT-005

# Merge to main via PR
conductor delete task-init-005
```

### Merge Strategy

**Recommended: Pull Requests**

1. Each developer creates PR from their branch
2. Code review happens in parallel
3. Merge PRs sequentially (first approved, first merged)
4. Resolve conflicts if needed (rare due to minimal scope)
5. Next developer rebases on main if needed

**Alternative: Direct Merge**

```bash
# After task complete and tests pass
git checkout main
git pull origin main
git merge task-init-003
git push origin main
```

### Conflict Resolution

**Minimal conflicts expected** due to MINIMAL SCOPE principle:

- TASK-INIT-003: Adds new methods after line 430
- TASK-INIT-004: Adds new methods after line 530
- TASK-INIT-005: Adds new methods after line 680

**If conflicts occur:**

```bash
# In your worktree
git fetch origin main
git rebase origin/main

# Resolve conflicts (likely in run() method integration)
# ... fix conflicts ...

git add .
git rebase --continue
git push --force-with-lease origin your-branch
```

### State Persistence

GuardKit state is **automatically shared** across worktrees via symlinks:

- Task files: `tasks/*` (git-tracked, shared via commits)
- Todo lists: `.claude/state/*` (symlinked to main repo)
- Agent files: `~/.agentecflow/agents/*` (symlinked, global)
- Commands: `~/.agentecflow/commands/*` (symlinked, global)

**No manual state synchronization needed!**

---

## Parallel Execution Opportunities

### Maximum Parallelization

**Week 2**: 3 developers in parallel (TASK-INIT-003, 004, 005)
**Week 3**: 2 developers in parallel (TASK-INIT-006, 007)
**Week 4**: 2 developers in parallel (TASK-INIT-008, 009)

**Ideal Team Size**: 3 developers

**Timeline with Parallelization**:
- Week 1: 14 hours (sequential, 1 developer)
- Week 2: 4 hours (parallel, 3 developers)
- Week 3: 6 hours (parallel, 2 developers)
- Week 4: 4 hours (parallel, 2 developers)
- Week 5: 8 hours (sequential, 1 developer)

**Total Calendar Time**: ~2 weeks (vs 5 weeks solo)

### Solo Developer (Sequential)

Follow standard workflow without Conductor:

```bash
cd ~/Projects/appmilla_github/guardkit

# Week 1
/task-work TASK-INIT-001
/task-complete TASK-INIT-001

/task-work TASK-INIT-002
/task-complete TASK-INIT-002

# Week 2
/task-work TASK-INIT-003
/task-complete TASK-INIT-003
# ... continue sequentially ...
```

**Total Timeline**: 5 weeks (60 hours at 12 hours/week)

---

## Quality Gates

### After Each Wave

**Must Pass Before Moving to Next Wave:**

1. **All tasks in wave completed**: `/task-complete TASK-INIT-XXX`
2. **All tests pass**: `pytest tests/`
3. **No regressions**: Existing Q&A workflow still works
4. **Feature demo**: Verify features work as specified
5. **Decision point**: Continue or pause

### After Wave 1 (Week 1)

```bash
# Verify boundary sections
/template-init
# Check generated agents have ALWAYS/NEVER/ASK sections

# Verify agent enhancement tasks created
ls -la tasks/backlog/TASK-AGENT-*
```

### After Wave 2 (Week 2)

```bash
# Verify Level 1 validation runs automatically
/template-init
# Should see Phase 3.5 validation output

# Verify Level 2 validation with flag
/template-init --validate
# Should generate validation-report.md

# Verify Level 3 compatibility
/template-validate ~/.agentecflow/templates/your-template
# Should work without errors
```

### After Wave 3 (Week 3)

```bash
# Verify quality scoring
/template-init
# Should see quality score (X/10) and grade

# Verify two-location output
/template-init --output-location=repo
ls -la installer/core/templates/
```

### After Wave 4 (Week 4)

```bash
# Verify discovery metadata
cat ~/.agentecflow/templates/your-template/agents/test-agent.md
# Should have frontmatter with stack, phase, capabilities, keywords

# Verify exit codes
/template-init --validate
echo $?  # Should be 0, 1, or 2 based on quality
```

### After Wave 5 (Week 5)

```bash
# Verify documentation
cat installer/core/commands/template-init.md
# Should document all 13 features

# Verify test coverage
pytest tests/test_template_init/test_enhancements.py --cov
# Should show ≥80% coverage
```

---

## Emergency Rollback

If critical issues arise during any wave:

### Option 1: Revert Last Commit

```bash
git revert HEAD
git push origin main
```

### Option 2: Disable Features via Flags

```bash
# In greenfield_qa_session.py
# Add feature flags to temporarily disable problematic features

def __init__(
    self,
    validate: bool = False,
    output_location: str = 'global',
    no_create_agent_tasks: bool = False,
    disable_boundaries: bool = False,  # Emergency flag
    disable_validation: bool = False    # Emergency flag
):
    # ...
```

### Option 3: Fix Forward

Preferred approach: Create hotfix task and use `/task-work` to fix issue.

---

## Dependencies Graph

```
TASK-INIT-001 (Boundary Sections)
    ├─> TASK-INIT-002 (Agent Tasks) [depends on boundaries]
    └─> TASK-INIT-008 (Discovery Metadata) [extends boundaries]

TASK-INIT-003 (Level 1 Validation) [independent]
    └─> TASK-INIT-004 (Level 2 Validation) [uses Level 1 results]
        └─> TASK-INIT-005 (Level 3 Integration) [ensures compatibility]
            └─> TASK-INIT-006 (Quality Scoring) [uses validation components]
                └─> TASK-INIT-009 (Exit Codes) [uses quality scores]

TASK-INIT-007 (Two-Location Output) [independent]

[ALL TASKS 001-009]
    ├─> TASK-INIT-010 (Documentation) [documents all features]
    └─> TASK-INIT-011 (Testing) [tests all features]
```

**Critical Path**: TASK-INIT-001 → 002 → 003 → 004 → 005 → 006 → 009 → 010 → 011

**Parallel Opportunities**:
- Wave 2: Tasks 003, 004, 005 (independent validation levels)
- Wave 3: Tasks 006, 007 (independent features)
- Wave 4: Tasks 008, 009 (after dependencies met)

---

## Success Metrics

### Overall Goals

- [ ] 100% feature parity with /template-create
- [ ] 0 breaking changes to existing Q&A
- [ ] <5% performance impact
- [ ] 90%+ test coverage
- [ ] All 11 tasks completed

### User Impact

- [ ] Generated templates score ≥8/10
- [ ] Boundary sections in all agents
- [ ] Enhancement tasks provide clear guidance
- [ ] Validation catches quality issues
- [ ] Teams can distribute templates easily

---

## Timeline Summary

### Solo Developer (Sequential)

| Week | Tasks | Hours | Cumulative |
|------|-------|-------|------------|
| 1 | TASK-INIT-001, 002 | 14 | 14 |
| 2 | TASK-INIT-003, 004, 005 | 12 | 26 |
| 3 | TASK-INIT-006, 007 | 10 | 36 |
| 4 | TASK-INIT-008, 009 | 6 | 42 |
| 5 | TASK-INIT-010, 011 | 8 | 50 |

**Total**: 5 weeks, 50 hours (TASK-INIT-011 is 8 hours, bringing real total to 58 hours)

### Team of 3 (Parallel)

| Week | Tasks | Hours (per developer) | Wall Time |
|------|-------|----------------------|-----------|
| 1 | 001, 002 (sequential) | 14 | 14 hours |
| 2 | 003, 004, 005 (parallel) | 4 | 4 hours |
| 3 | 006, 007 (2 devs parallel) | 6 | 6 hours |
| 4 | 008, 009 (2 devs parallel) | 4 | 4 hours |
| 5 | 010, 011 (sequential) | 8 | 8 hours |

**Total Calendar Time**: ~2 weeks (36 hours wall time)

---

## References

- **Parent Review**: [TASK-5E55](../../tasks/in_review/TASK-5E55-review-greenfield-initialization-workflow.md)
- **Decision Analysis**: [template-init-vs-template-create-analysis.md](../decisions/template-init-vs-template-create-analysis.md)
- **Master Task Guide**: [template-init-feature-porting-tasks.md](template-init-feature-porting-tasks.md)
- **Task Files**: `tasks/backlog/template-init-porting/TASK-INIT-*.md`
- **Conductor Documentation**: https://conductor.build

---

## Questions?

**Q: Should I use TDD mode for these tasks?**
A: No, standard mode is recommended. Tasks have detailed specifications with BEFORE/AFTER code snippets.

**Q: Can I skip the quality gates?**
A: No, quality gates ensure each wave works before moving forward. Skipping gates risks compounding issues.

**Q: What if I encounter merge conflicts in Conductor?**
A: Unlikely due to MINIMAL SCOPE, but rebase on main and resolve conflicts in run() method integration points.

**Q: Do I need to use Conductor?**
A: No, Conductor is optional. Solo developers can work sequentially in main branch. Conductor is beneficial for teams wanting parallel development.

**Q: Which tasks MUST be sequential?**
A: Week 1 (001→002) and Week 5 (010, 011). All other weeks can be parallelized.

**Q: How do I verify state persistence in Conductor?**
A: Task files are git-tracked, todo lists are symlinked, commands/agents are global. Run `guardkit doctor` to verify symlinks.
