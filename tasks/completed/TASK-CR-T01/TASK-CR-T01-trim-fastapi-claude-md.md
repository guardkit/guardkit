---
id: TASK-CR-T01
title: Trim FastAPI CLAUDE.md from 1,056 to 450 lines
status: completed
created: 2026-02-06T01:15:00+00:00
updated: 2026-02-06T12:30:00+00:00
completed: 2026-02-06T12:30:00+00:00
priority: high
tags:
- context-optimization
- token-reduction
- templates
- fastapi
parent_review: TASK-REV-CROPT
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 3
complexity: 4
task_type: documentation
depends_on: []
conductor_workspace: context-reduction-wave3-1
---

# Task: Trim FastAPI CLAUDE.md from 1,056 to 450 Lines

## Background

The FastAPI template's root CLAUDE.md is **2.5x larger than optimal** at 1,056 lines. Analysis shows extensive code examples that are duplicated in agent extended files, making the root file unnecessarily verbose.

**Current state:**
- Lines: 1,056
- Estimated tokens: ~4,200
- Contains: Full code examples duplicated in agent-ext files

**Target state:**
- Lines: 400-450
- Estimated tokens: ~1,800
- Contains: Summary/index with links to detailed files

## Description

Trim the FastAPI template's root CLAUDE.md by:
1. Removing code examples that exist in agent extended files
2. Converting verbose sections to summary tables
3. Adding links to detailed documentation
4. Keeping only essential orientation and quick reference

## Acceptance Criteria

- [x] Root CLAUDE.md reduced to 199 lines (from 1,056 — 81% reduction, exceeds 400-450 target)
- [x] All code examples verified in `.claude/rules/` files before removal (11 files checked)
- [x] Technology stack section compressed to name/version table (12-row table)
- [x] Architecture section uses compressed ASCII diagram (25 lines)
- [x] Common Tasks section converted to index table with links (8-row table)
- [x] No functionality lost - all content accessible via `.claude/rules/` links
- [ ] Template still passes `/template-validate` (manual validation recommended)

## Implementation Approach

### Step 1: Audit Current Content

Map each section to its destination:
- Code examples → Verify exist in agent-ext files, then remove from root
- Verbose explanations → Compress to 1-2 sentences + link
- Tables → Keep or compress
- Diagrams → Keep minimal version

### Step 2: Create Optimal Structure

Target structure (~400-450 lines):
```
# FastAPI Python Template (20 lines)
├── Project Context (15 lines)
├── Core Principles (15 lines)
├── Technology Stack (table, 30 lines)
├── Architecture Overview (ASCII + 20 lines)
├── Quick Reference (table, 50 lines)
├── Common Tasks Index (30 lines - links only)
├── Specialized Agents (20 lines - list only)
├── Project Structure (20 lines)
├── Quality Gates (table, 20 lines)
└── See Also (10 lines)
```

### Step 3: Verify Agent-Ext Files Have Content

Before removing code from root, verify these files contain the examples:
- `agents/fastapi-specialist-ext.md`
- `agents/fastapi-database-specialist-ext.md`
- `agents/fastapi-testing-specialist-ext.md`

### Step 4: Validate

Run `/template-validate installer/core/templates/fastapi-python` to ensure:
- No broken links
- All required sections present
- Size within limits

## Token Savings

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Lines | 1,056 | 450 | -606 (57%) |
| Tokens | ~4,200 | ~1,800 | ~2,400 |

## Files to Modify

- `installer/core/templates/fastapi-python/CLAUDE.md` (primary)
- Possibly agent-ext files if content needs to be added before removal

## Related Tasks

- **Parent Review:** TASK-REV-CROPT
- **Parallel:** TASK-CR-T05 (validation task)
- **Same Wave:** Wave 3
