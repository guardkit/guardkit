# FEAT-CR01 Implementation Guide

## Overview

This guide details the execution strategy for the Context Reduction feature after the TASK-REV-CROPT decision to pivot from Graphiti-dependent migration to Graphiti-independent trimming and path-gating.

**Total Tasks:** 12 active (3 cancelled, 1 completed)
**Total Waves:** 5
**Target Savings:** ~13,400 tokens (40% overall)

## Wave Breakdown

### Wave 1: Core CLAUDE.md Trimming + Path-Gating

**Purpose:** Immediate high-value wins with zero Graphiti dependency
**Token Savings:** ~3,400 tokens
**Parallel Execution:** Yes (all 3 tasks independent)

| Task | Type | Conductor Workspace | Notes |
|------|------|---------------------|-------|
| TASK-CR-001 | task-work | context-reduction-wave1-1 | Root CLAUDE.md: 996 → 300 lines |
| TASK-CR-002 | task-work | context-reduction-wave1-2 | .claude/CLAUDE.md: 113 → 30 lines |
| TASK-CR-003 | direct | - | Add `paths:` frontmatter |

**Execution:**
```bash
# Start Wave 1 tasks (can run in parallel with Conductor)
/task-work TASK-CR-001
/task-work TASK-CR-002
# TASK-CR-003: Direct edit to graphiti-knowledge.md frontmatter
```

**Validation:** After Wave 1, verify core workflows still function:
- `/task-create` creates valid task
- Quality gates reference correct thresholds
- Task states documented

---

### Wave 2: Trim Remaining Rules Files

**Purpose:** Trim additional rules files without Graphiti dependency
**Token Savings:** ~2,000 tokens
**Parallel Execution:** Partial (CR-004 depends on CR-003)

| Task | Type | Conductor Workspace | Notes |
|------|------|---------------------|-------|
| TASK-CR-004 | task-work | context-reduction-wave2-1 | Trim graphiti-knowledge.md content |
| TASK-CR-005 | direct | - | Seed project overview (optional) |
| TASK-CR-009 | task-work | context-reduction-wave2-2 | Trim autobuild.md, task-workflow.md, etc. |

**Execution:**
```bash
# After Wave 1 completes
/task-work TASK-CR-004
/task-work TASK-CR-009
# TASK-CR-005: Direct seeding via guardkit graphiti capture
```

**Validation:** After Wave 2, verify:
- Graphiti commands still work
- Path-gated files load correctly when editing relevant files

---

### Wave 3: Template FastAPI + Validation

**Purpose:** Establish template optimization pattern + prevent regressions
**Token Savings:** ~2,400 tokens
**Parallel Execution:** Yes (both tasks independent)

| Task | Type | Conductor Workspace | Notes |
|------|------|---------------------|-------|
| TASK-CR-T01 | task-work | context-reduction-wave3-1 | FastAPI CLAUDE.md: 1,056 → 450 lines |
| TASK-CR-T05 | direct | context-reduction-wave3-2 | Add paths: validation to /template-validate |

**Execution:**
```bash
# Start Wave 3 tasks
/task-work TASK-CR-T01
# TASK-CR-T05: Direct implementation of validation check
```

**Validation:** After Wave 3, verify:
- FastAPI template passes `/template-validate`
- Validation now catches missing `paths:` frontmatter

---

### Wave 4: Template Deduplication

**Purpose:** Consolidate duplicated examples across all 7 templates
**Token Savings:** ~5,600 tokens
**Parallel Execution:** Partial (TASK-CR-T02 should complete first to establish pattern)

| Task | Type | Conductor Workspace | Notes |
|------|------|---------------------|-------|
| TASK-CR-T02 | task-work | context-reduction-wave4-1 | Consolidate duplicated examples |
| TASK-CR-T03 | task-work | context-reduction-wave4-2 | Trim 5 oversized agent-ext files |
| TASK-CR-T04 | task-work | context-reduction-wave4-3 | Standardize 32 agent role sections |

**Execution:**
```bash
# Start TASK-CR-T02 first (establishes consolidation pattern)
/task-work TASK-CR-T02

# After T02 completes, run T03 and T04 in parallel
/task-work TASK-CR-T03
/task-work TASK-CR-T04
```

**Validation:** After Wave 4, verify:
- All 7 templates pass `/template-validate`
- No broken links in templates
- Agent files follow consistent structure

---

### Wave 5: Regression Testing

**Purpose:** Comprehensive verification of all changes
**Token Savings:** 0 (verification only)
**Parallel Execution:** N/A (single task)

| Task | Type | Conductor Workspace | Notes |
|------|------|---------------------|-------|
| TASK-CR-010 | task-work | context-reduction-wave5-1 | Full regression suite |

**Execution:**
```bash
# After all previous waves complete
/task-work TASK-CR-010
```

**Test Suite:**
1. Core commands: /task-create, /task-work, /task-review, /task-complete
2. Feature commands: /feature-plan, /feature-build, /feature-complete
3. Template commands: /template-validate, /template-create (on test codebase)
4. Path-gating: Verify rules load when editing relevant files

---

## Cancelled Tasks

These tasks were cancelled due to Graphiti code retrieval fidelity issues:

| Task | Original Purpose | Cancellation Reason |
|------|-----------------|---------------------|
| TASK-CR-006 | Seed pattern code examples | Graphiti extracts facts, not verbatim code |
| TASK-CR-007 | Trim orchestrators.md | Depended on Graphiti code retrieval |
| TASK-CR-008 | Trim dataclasses/pydantic | Depended on Graphiti code retrieval |

**Pattern files remain as-is:** Already path-gated, contain valuable code examples that Graphiti cannot preserve.

---

## Risk Mitigation

### Risk 1: Breaking Core Workflows
**Mitigation:** Wave 1 focuses on non-critical content removal. Quality gates, task states, and command syntax preserved.

### Risk 2: Template Degradation
**Mitigation:** `/template-validate` run after each modification. TASK-CR-T05 adds validation guard.

### Risk 3: Lost Functionality
**Mitigation:** No code examples removed without verifying they exist in agent-ext files.

### Risk 4: Regression Failures
**Mitigation:** Wave 5 dedicated to comprehensive testing before feature completion.

---

## Progress Tracking

After completing each task, update its status in the task file:
```yaml
status: completed
```

After completing each wave, verify with:
```bash
# Check task statuses
ls tasks/backlog/context-reduction/*.md | xargs grep "status:"
```

---

## Feature Completion

After Wave 5 passes:

1. Update review task TASK-REV-CROPT:
   - Mark acceptance criteria as checked
   - Update status to `completed`

2. Archive completed tasks:
   ```bash
   mv tasks/backlog/context-reduction/TASK-CR-*.md tasks/completed/
   ```

3. Create feature completion summary:
   - Actual token savings measured
   - Any deviations from plan
   - Lessons learned for future features
