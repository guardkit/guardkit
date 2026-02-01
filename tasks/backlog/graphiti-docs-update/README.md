# Feature: Graphiti Documentation Update

> **Feature ID**: FEAT-GDU
> **Parent Review**: TASK-REV-BBE7
> **Created**: 2026-02-01
> **Status**: In Progress
> **Progress**: 2/8 tasks (25%)

## Problem Statement

Both Graphiti refinement features (FEAT-GR-MVP and FEAT-0F4A) have been fully implemented, but the public GitHub Pages documentation is significantly outdated. Key features like interactive knowledge capture, query commands, and job-specific context retrieval have no public documentation.

Additionally, CLAUDE.md contains ~350 lines of Graphiti documentation which should be refactored to use progressive disclosure (moving detailed content to an ext file).

## Solution Approach

1. Create new public documentation pages for Phase 2 features
2. Update mkdocs.yml navigation to include orphaned docs
3. Update architecture documentation with Phase 2 APIs
4. Refactor CLAUDE.md Graphiti content to use progressive disclosure

## Subtask Summary

| Task ID | Title | Wave | Mode | Status |
|---------|-------|------|------|--------|
| TASK-GDU-001 | Create graphiti-knowledge-capture.md | 1 | direct | ✅ Completed |
| TASK-GDU-002 | Create graphiti-query-commands.md | 1 | direct | ✅ Completed |
| TASK-GDU-003 | Create graphiti-job-context.md | 1 | direct | Pending |
| TASK-GDU-004 | Update mkdocs.yml navigation | 2 | direct | Pending |
| TASK-GDU-005 | Update graphiti-architecture.md | 2 | direct | Pending |
| TASK-GDU-006 | Create graphiti-turn-states.md | 3 | direct | Pending |
| TASK-GDU-007 | Update graphiti-integration-guide.md | 3 | direct | Pending |
| TASK-GDU-008 | Refactor CLAUDE.md Graphiti to progressive disclosure | 3 | task-work | Pending |

## Execution Strategy

### Wave 1: Critical New Docs (Parallel)
- TASK-GDU-001, TASK-GDU-002, TASK-GDU-003
- Can be executed in parallel
- Estimated: 6 hours total

### Wave 2: Navigation & Architecture (Sequential)
- TASK-GDU-004 (navigation update)
- TASK-GDU-005 (architecture update)
- Estimated: 2 hours total

### Wave 3: Additional Docs & Refactoring (Parallel)
- TASK-GDU-006, TASK-GDU-007, TASK-GDU-008
- Can be executed in parallel
- Estimated: 4 hours total

**Total Estimated Effort**: 12 hours

## Success Criteria

- [ ] All Phase 2 features documented publicly
- [ ] mkdocs.yml includes all Graphiti guides
- [ ] Architecture docs include Phase 2 APIs
- [ ] CLAUDE.md Graphiti content uses progressive disclosure (<100 lines in core)
- [ ] GitHub Pages site builds successfully
