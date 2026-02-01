# Implementation Guide: Graphiti Documentation Update

## Execution Strategy

### Wave 1: Critical New Docs (Parallel)

**Can be executed in parallel using Conductor**

| Task | Document | Workspace | Estimate |
|------|----------|-----------|----------|
| TASK-GDU-001 | `guides/graphiti-knowledge-capture.md` | graphiti-docs-wave1-1 | 2h |
| TASK-GDU-002 | `guides/graphiti-query-commands.md` | graphiti-docs-wave1-2 | 2h |
| TASK-GDU-003 | `guides/graphiti-job-context.md` | graphiti-docs-wave1-3 | 2h |

**Source Material**: All content available in CLAUDE.md (lines 794-1139)

**Commands**:
```bash
# Using Conductor for parallel execution
conductor spawn graphiti-docs-wave1-1 "/task-work TASK-GDU-001"
conductor spawn graphiti-docs-wave1-2 "/task-work TASK-GDU-002"
conductor spawn graphiti-docs-wave1-3 "/task-work TASK-GDU-003"
```

---

### Wave 2: Navigation & Architecture (Sequential)

**Dependencies**: Wave 1 must complete first

| Task | Action | Estimate |
|------|--------|----------|
| TASK-GDU-004 | Update mkdocs.yml navigation | 30m |
| TASK-GDU-005 | Update architecture docs | 1.5h |

**Execute sequentially**:
```bash
/task-work TASK-GDU-004  # Quick, do first
/task-work TASK-GDU-005  # More involved
```

---

### Wave 3: Additional Docs & Refactoring (Parallel)

**Can be executed in parallel using Conductor**

| Task | Document/Action | Workspace | Mode | Estimate |
|------|-----------------|-----------|------|----------|
| TASK-GDU-006 | `guides/graphiti-turn-states.md` | graphiti-docs-wave3-1 | direct | 1h |
| TASK-GDU-007 | Update integration guide | graphiti-docs-wave3-2 | direct | 1h |
| TASK-GDU-008 | Refactor CLAUDE.md | graphiti-docs-wave3-3 | task-work | 2h |

**Commands**:
```bash
conductor spawn graphiti-docs-wave3-1 "/task-work TASK-GDU-006"
conductor spawn graphiti-docs-wave3-2 "/task-work TASK-GDU-007"
conductor spawn graphiti-docs-wave3-3 "/task-work TASK-GDU-008"
```

---

## Total Timeline

| Wave | Tasks | Parallel Time | Sequential Time |
|------|-------|---------------|-----------------|
| Wave 1 | 3 | 2h | 6h |
| Wave 2 | 2 | 2h | 2h |
| Wave 3 | 3 | 2h | 4h |
| **Total** | **8** | **6h** | **12h** |

**With Conductor**: ~6 hours
**Sequential**: ~12 hours

---

## Verification Checklist

After all tasks complete:

- [ ] `mkdocs build` succeeds with no warnings
- [ ] All new pages render correctly
- [ ] Navigation structure is correct
- [ ] No broken links
- [ ] CLAUDE.md Graphiti section is <100 lines
- [ ] `.claude/rules/graphiti-knowledge.md` exists with full content
- [ ] GitHub Pages deploys successfully

---

## Rollback Plan

If issues arise:
1. All changes are in separate files (easy to revert)
2. mkdocs.yml can be reverted to previous navigation
3. CLAUDE.md refactoring is the riskiest - validate carefully before committing
