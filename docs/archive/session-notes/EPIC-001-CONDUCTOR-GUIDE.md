# EPIC-001: Conductor/Worktree Implementation Guide

## Quick Start

```bash
# From main repo directory
conductor add feature/task-001 --task TASK-001
conductor add feature/task-001b --task TASK-001B
conductor add feature/task-002 --task TASK-002
# etc...

# Work on tasks in parallel
cd ../guardkit-feature-task-001
/task-work TASK-001

cd ../guardkit-feature-task-002
/task-work TASK-002
```

## Overview

EPIC-001 contains 15 tasks organized in 4 waves for parallel development. This guide shows how to use conductor and git worktrees to work on multiple tasks simultaneously.

**Total Effort**: 85 hours (~4-5 weeks solo, ~2-3 weeks with parallelization)

---

## Task Dependency Graph

```
Wave 0 (Foundation - 21h)
├─ TASK-001 (6h) → [Q&A Session - Existing Codebase]
├─ TASK-001B (8h) → [Q&A Session - Greenfield]
├─ TASK-002 (5h) → [AI Analysis] [depends: TASK-001]
└─ TASK-003 (2h) → [Agent Scanner] [independent]

Wave 1 (Template Generation - 26h)
├─ TASK-004A (5h) → [Agent Generator] [depends: TASK-003]
├─ TASK-005 (6h) → [Manifest Generator] [depends: TASK-002]
├─ TASK-006 (4h) → [Settings Generator] [depends: TASK-002]
├─ TASK-007 (5h) → [CLAUDE.md Generator] [depends: TASK-002]
└─ TASK-008 (6h) → [Template Generator] [depends: TASK-002]

Wave 2 (Commands - 10h)
├─ TASK-009 (4h) → [Agent Orchestration] [depends: TASK-004A]
├─ TASK-010 (4h) → [/template-create] [depends: ALL Wave 1]
└─ TASK-011 (2h) → [/template-init] [depends: TASK-010]

Wave 3 (Polish - 28h)
├─ TASK-012 (6h) → [Packaging] [depends: TASK-010, TASK-011]
├─ TASK-013 (10h) → [Integration Tests] [depends: TASK-012]
├─ TASK-014 (6h) → [Documentation] [depends: TASK-013]
└─ TASK-015 (6h) → [Example Templates] [depends: TASK-012]
```

---

## Implementation Waves

### Wave 0: Foundation (Parallel: 3 tasks)

**Can Start Immediately** (no dependencies):

1. **TASK-001** (6h, complexity: 4)
   - Q&A session for existing codebase analysis
   - Worktree: `feature/task-001`
   - Independent: YES

2. **TASK-001B** (8h, complexity: 6)
   - Q&A session for greenfield template creation
   - Worktree: `feature/task-001b`
   - Independent: YES

3. **TASK-003** (2h, complexity: 3)
   - Multi-source agent scanner
   - Worktree: `feature/task-003`
   - Independent: YES

**Sequential After TASK-001**:

4. **TASK-002** (5h, complexity: 4)
   - AI codebase analysis
   - Worktree: `feature/task-002`
   - Depends on: TASK-001
   - Start after: TASK-001 complete

**Wave 0 Timeline**: 8h parallel (longest: TASK-001B) + 5h sequential (TASK-002) = **13h total**

---

### Wave 1: Template Generation (Parallel: 5 tasks)

**Start After**: TASK-002 and TASK-003 complete

All tasks can run in parallel:

5. **TASK-004A** (5h, complexity: 5)
   - AI agent generator
   - Worktree: `feature/task-004a`
   - Depends on: TASK-003

6. **TASK-005** (6h, complexity: 4)
   - Manifest generator
   - Worktree: `feature/task-005`
   - Depends on: TASK-002

7. **TASK-006** (4h, complexity: 3)
   - Settings generator
   - Worktree: `feature/task-006`
   - Depends on: TASK-002

8. **TASK-007** (5h, complexity: 4)
   - CLAUDE.md generator
   - Worktree: `feature/task-007`
   - Depends on: TASK-002

9. **TASK-008** (6h, complexity: 5)
   - Template generator
   - Worktree: `feature/task-008`
   - Depends on: TASK-002

**Wave 1 Timeline**: 6h parallel (longest: TASK-005 or TASK-008) = **6h total**

---

### Wave 2: Commands (Sequential)

**Start After**: All Wave 1 tasks complete

10. **TASK-009** (4h, complexity: 4)
    - Agent orchestration
    - Worktree: `feature/task-009`
    - Depends on: TASK-004A
    - Can overlap slightly with Wave 1

11. **TASK-010** (4h, complexity: 5)
    - /template-create command
    - Worktree: `feature/task-010`
    - Depends on: TASK-001, TASK-002, TASK-005-009
    - **CRITICAL PATH** - orchestrates everything

12. **TASK-011** (2h, complexity: 3)
    - /template-init command
    - Worktree: `feature/task-011`
    - Depends on: TASK-010

**Wave 2 Timeline**: 4h + 4h + 2h = **10h total** (mostly sequential)

---

### Wave 3: Polish (Parallel: 4 tasks)

**Start After**: TASK-010 and TASK-011 complete

13. **TASK-012** (6h, complexity: 4)
    - Packaging and distribution
    - Worktree: `feature/task-012`
    - Depends on: TASK-010, TASK-011

14. **TASK-015** (6h, complexity: 4)
    - Example templates
    - Worktree: `feature/task-015`
    - Depends on: TASK-012
    - Can run parallel with TASK-013

**Sequential After TASK-012**:

15. **TASK-013** (10h, complexity: 6)
    - Integration tests
    - Worktree: `feature/task-013`
    - Depends on: TASK-012

16. **TASK-014** (6h, complexity: 4)
    - Documentation
    - Worktree: `feature/task-014`
    - Depends on: TASK-013

**Wave 3 Timeline**: 6h (TASK-012) + 10h (TASK-013) + 6h (TASK-014) = **22h total** (mostly sequential)
- TASK-015 can overlap with TASK-013 to save ~6h

---

## Optimal Parallel Strategy

### Timeline Summary

| Wave | Sequential | Parallel Optimized | Tasks | Notes |
|------|-----------|-------------------|-------|-------|
| Wave 0 | 21h | 13h | 4 | 3 parallel + 1 sequential |
| Wave 1 | 26h | 6h | 5 | All parallel |
| Wave 2 | 10h | 10h | 3 | Mostly sequential |
| Wave 3 | 28h | 16h | 4 | Some overlap possible |
| **Total** | **85h** | **45h** | **16** | **~50% time savings** |

### Conductor Commands by Wave

**Wave 0 (Start all 3 immediately)**:
```bash
# Create worktrees for independent tasks
conductor add feature/task-001 --task TASK-001    # 6h
conductor add feature/task-001b --task TASK-001B  # 8h
conductor add feature/task-003 --task TASK-003    # 2h

# Work in parallel
cd ../guardkit-feature-task-001 && /task-work TASK-001 &
cd ../guardkit-feature-task-001b && /task-work TASK-001B &
cd ../guardkit-feature-task-003 && /task-work TASK-003 &

# Wait for TASK-001 to complete, then start TASK-002
cd ../guardkit-feature-task-001 && /task-complete TASK-001
conductor add feature/task-002 --task TASK-002    # 5h
cd ../guardkit-feature-task-002 && /task-work TASK-002
```

**Wave 1 (Start after TASK-002 and TASK-003 complete)**:
```bash
# Create all Wave 1 worktrees
conductor add feature/task-004a --task TASK-004A  # 5h
conductor add feature/task-005 --task TASK-005    # 6h
conductor add feature/task-006 --task TASK-006    # 4h
conductor add feature/task-007 --task TASK-007    # 5h
conductor add feature/task-008 --task TASK-008    # 6h

# Work in parallel (all 5 tasks)
cd ../guardkit-feature-task-004a && /task-work TASK-004A &
cd ../guardkit-feature-task-005 && /task-work TASK-005 &
cd ../guardkit-feature-task-006 && /task-work TASK-006 &
cd ../guardkit-feature-task-007 && /task-work TASK-007 &
cd ../guardkit-feature-task-008 && /task-work TASK-008 &
```

**Wave 2 (Sequential)**:
```bash
# TASK-009 (can start slightly earlier if TASK-004A done)
conductor add feature/task-009 --task TASK-009
cd ../guardkit-feature-task-009 && /task-work TASK-009

# TASK-010 (wait for all Wave 1)
conductor add feature/task-010 --task TASK-010
cd ../guardkit-feature-task-010 && /task-work TASK-010

# TASK-011 (wait for TASK-010)
conductor add feature/task-011 --task TASK-011
cd ../guardkit-feature-task-011 && /task-work TASK-011
```

**Wave 3 (Partial parallel)**:
```bash
# TASK-012 first
conductor add feature/task-012 --task TASK-012
cd ../guardkit-feature-task-012 && /task-work TASK-012

# Then TASK-013 and TASK-015 in parallel
conductor add feature/task-013 --task TASK-013
conductor add feature/task-015 --task TASK-015
cd ../guardkit-feature-task-013 && /task-work TASK-013 &
cd ../guardkit-feature-task-015 && /task-work TASK-015 &

# TASK-014 after TASK-013
conductor add feature/task-014 --task TASK-014
cd ../guardkit-feature-task-014 && /task-work TASK-014
```

---

## Critical Path

The critical path (longest sequence) is:

1. TASK-001B (8h) - longest in Wave 0
2. TASK-002 (5h) - depends on TASK-001
3. TASK-008 (6h) - longest in Wave 1, depends on TASK-002
4. TASK-009 (4h) - depends on TASK-004A
5. TASK-010 (4h) - depends on all Wave 1
6. TASK-011 (2h) - depends on TASK-010
7. TASK-012 (6h) - depends on TASK-010, TASK-011
8. TASK-013 (10h) - depends on TASK-012
9. TASK-014 (6h) - depends on TASK-013

**Critical Path Total**: ~51h (can be reduced with aggressive parallelization to ~45h)

---

## State Management

GuardKit uses symlinked state (`.claude/state`) across worktrees, so:

✅ **Works automatically**:
- Task state syncs across all worktrees
- Completing a task in one worktree updates all others
- No manual state management needed

✅ **Best practices**:
- Complete tasks in their respective worktrees
- Check task status before starting dependent tasks
- Use `/task-status` to verify state

---

## Merge Strategy

**Recommended**: Merge in wave order to avoid conflicts

1. Complete all Wave 0 tasks → merge to main
2. Complete all Wave 1 tasks → merge to main
3. Complete all Wave 2 tasks → merge to main
4. Complete all Wave 3 tasks → merge to main

**Alternative**: Merge each task as it completes (more flexible but may have conflicts)

---

## Troubleshooting

### Issue: Dependency not met
```bash
# Check if dependency task is complete
cd /path/to/main/repo
/task-status TASK-XXX

# If blocked, work on independent tasks first
```

### Issue: Merge conflicts
```bash
# Rebase on main before merging
cd worktree-directory
git fetch origin
git rebase origin/main
# Resolve conflicts
git rebase --continue
```

### Issue: State sync issues
```bash
# Verify symlink
ls -la .claude/state
# Should point to main repo's .claude/state

# If broken, recreate
rm -rf .claude/state
ln -s /path/to/main/repo/.claude/state .claude/state
```

---

## Task Files Location

All EPIC-001 task files are in `tasks/backlog/`:

- TASK-001 through TASK-015
- TASK-001B (greenfield variant)
- TASK-004A (agent generator)

Use `/task-status TASK-XXX` to view full task details.

---

## Checklist

**Wave 0**:
- [ ] TASK-001: Q&A Session (Existing Codebase)
- [ ] TASK-001B: Q&A Session (Greenfield)
- [ ] TASK-003: Agent Scanner
- [ ] TASK-002: AI Analysis (after TASK-001)

**Wave 1** (after Wave 0):
- [ ] TASK-004A: Agent Generator
- [ ] TASK-005: Manifest Generator
- [ ] TASK-006: Settings Generator
- [ ] TASK-007: CLAUDE.md Generator
- [ ] TASK-008: Template Generator

**Wave 2** (after Wave 1):
- [ ] TASK-009: Agent Orchestration
- [ ] TASK-010: /template-create Command
- [ ] TASK-011: /template-init Command

**Wave 3** (after Wave 2):
- [ ] TASK-012: Packaging
- [ ] TASK-013: Integration Tests
- [ ] TASK-014: Documentation
- [ ] TASK-015: Example Templates

---

## Success Criteria

- ✅ All 15 tasks complete with passing tests
- ✅ `/template-create` works end-to-end
- ✅ `/template-init` works with generated templates
- ✅ All quality gates pass (80% coverage, 100% tests pass)
- ✅ Documentation complete
- ✅ Example templates available

---

## Ready for v1.0.0

Once EPIC-001 is complete:
1. Update version to 1.0.0 (README.md, package.json)
2. Create git tag: `git tag -a v1.0.0 -m "Release 1.0.0: Template auto-generation"`
3. Push tag: `git push origin main --tags`
4. Blog about it! 🎉

---

**Created**: 2025-11-06
**For**: EPIC-001 implementation with conductor/worktrees
**Time Savings**: ~40h (50%) with optimal parallelization
