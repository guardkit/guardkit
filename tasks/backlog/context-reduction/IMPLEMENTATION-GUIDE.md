# Implementation Guide: Context Reduction via Graphiti Migration

## Overview

Reduce always-loaded static context from ~15,800 tokens to ~8,000 tokens (49% reduction) through editorial trimming, path-gating, and selective Graphiti migration.

## Wave Breakdown

### Wave 1: Quick Wins (No Graphiti Dependency)

**Estimated savings: ~4,400 tokens always-loaded**

Execute in parallel where possible. No external dependencies.

| Task | Title | Mode | Est. Savings |
|------|-------|------|-------------|
| TASK-CR-001 | Trim root CLAUDE.md | task-work | 2,380 tokens |
| TASK-CR-002 | Trim .claude/CLAUDE.md | task-work | 310 tokens |
| TASK-CR-003 | Add path gate to graphiti-knowledge.md | direct | 1,508 tokens (conditional) |
| TASK-CR-004 | Trim graphiti-knowledge.md content | task-work | 1,168 tokens |

**Parallel Groups:**
- TASK-CR-001, TASK-CR-002, TASK-CR-003 can run in parallel (independent files)
- TASK-CR-004 depends on TASK-CR-003 (needs path gate first)

**Conductor Workspaces:**
- `context-reduction-wave1-1` (TASK-CR-001)
- `context-reduction-wave1-2` (TASK-CR-002)
- `context-reduction-wave1-3` (TASK-CR-003 + TASK-CR-004 sequential)

### Wave 2: Seed Graphiti Gaps

**Prerequisite: Wave 1 complete (content identified for migration)**

| Task | Title | Mode | Purpose |
|------|-------|------|---------|
| TASK-CR-005 | Seed project_overview + project_architecture | direct | Enable Wave 3 trimming |
| TASK-CR-006 | Seed pattern code examples | direct | Enable Wave 3 pattern trimming |

**Parallel Groups:**
- TASK-CR-005, TASK-CR-006 can run in parallel (independent Graphiti groups)
- TASK-CR-005 depends on TASK-CR-001 (needs to know what was removed)

**Important**: TASK-CR-006 is a gate for Wave 3 pattern tasks. If code example retrieval fidelity is poor, Wave 3 pattern tasks (CR-007, CR-008) should be cancelled.

### Wave 3: Trim After Verification

**Prerequisite: Wave 2 complete, Graphiti retrieval verified**

| Task | Title | Mode | Est. Savings | Depends On |
|------|-------|------|-------------|------------|
| TASK-CR-007 | Trim orchestrators.md | task-work | 1,220 tokens | CR-006 |
| TASK-CR-008 | Trim dataclasses + pydantic patterns | task-work | 624 tokens | CR-006 |
| TASK-CR-009 | Trim 5 remaining path-gated files | task-work | 2,088 tokens | None |
| TASK-CR-010 | Regression test workflows | task-work | 0 | CR-001, CR-002, CR-004 |

**Parallel Groups:**
- TASK-CR-007, TASK-CR-008 can run in parallel (independent files, same dependency)
- TASK-CR-009 is independent (no Graphiti dependency, just editorial)
- TASK-CR-010 runs last (verification)

**Abort Criteria**: If TASK-CR-006 reveals poor code retrieval fidelity in Graphiti, cancel TASK-CR-007 and TASK-CR-008. The pattern files are already path-gated, so the savings are conditional anyway.

## Risk Mitigation

1. **Wave 1 is risk-free**: Pure editorial work with no Graphiti dependency
2. **Wave 2 is verification**: Seed and test before committing to Wave 3
3. **Wave 3 has abort gates**: Pattern migration can be cancelled if fidelity is poor
4. **Regression testing**: TASK-CR-010 catches any workflow breakage

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Always-loaded tokens | <8,000 | Count tokens in CLAUDE.md files |
| Graphiti retrieval | >0.6 relevance | `guardkit graphiti search` queries |
| Workflow regression | 0 | TASK-CR-010 manual verification |
| Weekly token usage | Meaningful reduction | Monitor over 2 weeks post-implementation |
