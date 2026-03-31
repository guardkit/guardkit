# Feature: Context Reduction via Path-Gating and Trimming (FEAT-CR01)

## Problem

Static CLAUDE.md, .claude/rules/, and template files load excessive tokens into conversations, contributing to weekly token usage limits.

**Original scope:** ~15,800 tokens always-loaded in core docs
**Expanded scope:** +38,000 lines in template system with duplication

## Solution

**Pivoted approach (per TASK-REV-CROPT):** Graphiti-independent reduction through:
1. Path-gating currently ungated files
2. Trimming verbose documentation
3. Removing duplicates between files
4. Template system optimization (consolidate duplicated examples)

**Out of scope:** Migrating code examples to Graphiti (fidelity insufficient)

**Target:** ~13,400 token reduction (~40% overall)

## Subtasks

### Wave 1: Core CLAUDE.md Trimming + Path-Gating (~3,400 tokens)

| Task ID | Title | Mode | Status |
|---------|-------|------|--------|
| TASK-CR-001 | Trim root CLAUDE.md to lean version | task-work | backlog |
| TASK-CR-002 | Trim .claude/CLAUDE.md remove duplicates | task-work | backlog |
| TASK-CR-003 | Add path gate to graphiti-knowledge.md | direct | backlog |

### Wave 2: Trim Remaining Rules Files (~2,000 tokens)

| Task ID | Title | Mode | Status |
|---------|-------|------|--------|
| TASK-CR-004 | Trim graphiti-knowledge.md content | task-work | backlog |
| TASK-CR-005 | Seed Graphiti project_overview + architecture | direct | backlog |
| TASK-CR-009 | Trim 5 remaining path-gated files | task-work | backlog |

### Wave 3: Template FastAPI + Validation (~2,400 tokens)

| Task ID | Title | Mode | Status |
|---------|-------|------|--------|
| TASK-CR-T01 | Trim FastAPI CLAUDE.md (1,056→450 lines) | task-work | backlog |
| TASK-CR-T05 | Add template validation for paths: frontmatter | direct | backlog |

### Wave 4: Template Deduplication (~5,600 tokens)

| Task ID | Title | Mode | Status |
|---------|-------|------|--------|
| TASK-CR-T02 | Consolidate duplicated examples (all templates) | task-work | backlog |
| TASK-CR-T03 | Trim oversized agent extended files (5 hotspots) | task-work | backlog |
| TASK-CR-T04 | Standardize agent role sections (18 agents) | task-work | **completed** (2,805 lines reduced) |

### Wave 5: Regression Testing

| Task ID | Title | Mode | Status |
|---------|-------|------|--------|
| TASK-CR-010 | Regression test workflows (expanded scope) | task-work | backlog |

### Cancelled Tasks (Graphiti Fidelity Issue)

| Task ID | Title | Reason |
|---------|-------|--------|
| TASK-CR-006 | Seed Graphiti patterns with code examples | Graphiti can't preserve verbatim code |
| TASK-CR-007 | Trim orchestrators.md | Depended on Graphiti code retrieval |
| TASK-CR-008 | Trim dataclasses + pydantic patterns | Depended on Graphiti code retrieval |

### Completed Tasks

| Task ID | Title | Outcome |
|---------|-------|---------|
| TASK-CR-006-FIX | Wire pattern seeding module | Investigation complete - revealed fidelity issue |

### Pre-Implementation Review (Best Practices Compliance)

| Task ID | Title | Mode | Status |
|---------|-------|------|--------|
| TASK-REV-AGMD | Analyze changes against AGENTS.md best practices | task-review | backlog |

**Purpose:** Ensure context reduction doesn't inadvertently remove GitHub AGENTS.md best practices (DO/DON'T sections, code examples, three-tier boundaries).

**Execute before:** Wave 1 implementation

## Parent Reviews

- **TASK-REV-5F19**: Original analysis - [review report](../../../.claude/reviews/TASK-REV-5F19-review-report.md)
- **TASK-REV-CROPT**: Pivot decision - [review report](../../../.claude/reviews/TASK-REV-CROPT-review-report.md)
- **TASK-REV-AGMD**: Best practices compliance - [task file](TASK-REV-AGMD-analyze-against-agentsmd-best-practices.md)

## Key Decisions

1. **Graphiti for semantics, not code:** Graphiti extracts facts, not verbatim content. Pattern files remain static (already path-gated).

2. **Expanded to templates:** Template system analysis added ~8,000 tokens of reduction opportunity through deduplication.

3. **Progressive disclosure works:** 60-70% context reduction already achieved via path-gating. Focus on gaps.

4. **5 waves, not 4:** Expanded scope with template tasks in Waves 3-4, regression testing in Wave 5.

## Token Reduction Summary

| Scope | Before | After | Savings |
|-------|--------|-------|---------|
| Core rules/docs | ~17,314 | ~11,900 | ~5,400 (31%) |
| Template system | ~32,000 | ~24,000 | ~8,000 (25%) |
| **Combined** | ~49,314 | ~35,900 | **~13,400 (27%)** |

**Realistic session impact:** 35-40% reduction (files don't all load simultaneously)

## Execution

```bash
# Pre-Implementation Review (REQUIRED FIRST)
/task-review TASK-REV-AGMD --mode=code-quality --depth=standard

# Wave 1 (parallel) - After review approval
/task-work TASK-CR-001  # or /feature-build
/task-work TASK-CR-002
# TASK-CR-003 is direct edit

# Wave 2 (parallel)
/task-work TASK-CR-004
# TASK-CR-005 is direct edit
/task-work TASK-CR-009

# Wave 3 (parallel)
/task-work TASK-CR-T01
# TASK-CR-T05 is direct edit

# Wave 4 (parallel, but TASK-CR-T02 first recommended)
/task-work TASK-CR-T02  # establishes pattern
/task-work TASK-CR-T03
/task-work TASK-CR-T04

# Wave 5
/task-work TASK-CR-010
```
