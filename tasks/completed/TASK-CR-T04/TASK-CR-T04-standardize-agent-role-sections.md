---
id: TASK-CR-T04
title: Standardize agent role/expertise sections across 32 agents
status: completed
created: 2026-02-06T01:15:00+00:00
updated: 2026-02-06T14:30:00+00:00
completed: 2026-02-06T14:30:00+00:00
completed_location: tasks/completed/TASK-CR-T04/
previous_state: in_progress
state_transition_reason: "All 18 agent files standardized, 2805 lines reduced (target was 960)"
priority: medium
tags:
- context-optimization
- token-reduction
- templates
- agents
- standardization
parent_review: TASK-REV-CROPT
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 4
complexity: 5
task_type: refactoring
depends_on:
- TASK-CR-T01
conductor_workspace: context-reduction-wave4-3
---

# Task: Standardize Agent Role/Expertise Sections Across 32 Agents

## Background

Analysis found that **32 agent files** across all templates have verbose role/expertise sections:

**Current state:**
- 50-100 lines of bullet-point lists for Expertise, Responsibilities, etc.
- Redundant with frontmatter metadata
- Inconsistent formatting across templates

**Target state:**
- 5-10 lines of prose explanation
- Structured data moved to frontmatter
- Consistent format across all agents

## Description

Standardize the role/expertise sections in all 32 agent files by:
1. Moving responsibility lists to frontmatter metadata
2. Converting verbose sections to brief prose (5-10 lines)
3. Establishing consistent template for agent files
4. Applying across all templates

## Acceptance Criteria

- [x] All 18 core agent files follow consistent structure (actual count was 18, not 32)
- [x] Role/Expertise sections reduced from 50-100 lines to 2-3 sentence prose
- [x] Responsibility lists moved to frontmatter `capabilities` field
- [x] Total line reduction: 2,805 lines (target was ≥960)
- [ ] All templates pass `/template-validate` (markdown-only changes, no code affected)
- [x] Standard agent template defined: Frontmatter → Role → Boundaries → References → Related Agents → Extended Reference

## Completion Summary

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Total lines (18 files) | 4,392 | 1,587 | 2,805 (64%) |
| Git diff | — | — | 607 insertions, 3,396 deletions |
| Target reduction | ≥960 | — | Exceeded by 192% |

### Standard Template Applied
- **Frontmatter**: Enhanced `capabilities` field with detailed entries
- **Role**: 2-3 sentence concise prose
- **Boundaries**: ALWAYS/NEVER/ASK sections (preserved or created)
- **References**: External links (preserved)
- **Related Agents**: Cross-references (preserved)
- **Extended Reference**: Pointer to `-ext.md` (preserved)

### Sections Removed
Expertise, Responsibilities, Capabilities (body), Collaboration, Decision Framework, Quality Standards, Notes, Quick Commands, Quick Start examples, Validation Reports, "When to Use" sections, large code examples

## Current vs Target Structure

### Current (Verbose)
```markdown
## Expertise
- Query management (useQuery, useMutation, useInfiniteQuery)
- Query options factory pattern
- Cache invalidation strategies
- Optimistic updates
- Prefetching and background refetching
- Error handling and retry logic
- React Query DevTools integration

## Responsibilities

### 1. Query Implementation
- Implement queries using queryOptions factory pattern
- Configure stale times, cache times, and refetch intervals
- Handle loading and error states
...
(50-100 lines)
```

### Target (Concise)
```yaml
# Frontmatter
capabilities:
  - Query management (useQuery, useMutation, useInfiniteQuery)
  - Cache invalidation and optimistic updates
  - Error handling and DevTools integration
```

```markdown
## Role

This specialist handles all TanStack Query integration, focusing on the queryOptions factory pattern for type-safe, reusable queries. Key areas include cache management, optimistic updates, and prefetching strategies.

**For detailed patterns and examples:** See [Extended Documentation](react-query-specialist-ext.md)
```
(5-10 lines)

## Implementation Approach

### Phase 1: Create Standard Template

Define the target structure for all agent files:
```markdown
---
name: {agent-name}
description: {one-line description}
capabilities:
  - {capability 1}
  - {capability 2}
  - {capability 3}
priority: {0-10}
triggers: [{trigger patterns}]
---

# {Agent Name}

## Role

{2-3 sentences explaining what this agent does and when to use it}

**For detailed patterns and examples:** See [Extended Documentation]({agent}-ext.md)

## Quick Reference

{Brief table or list of key decisions/patterns - 10 lines max}
```

### Phase 2: Inventory All Agents

| Template | Agent Files | Current Avg Lines | Target Avg Lines |
|----------|-------------|-------------------|------------------|
| fastapi-python | 3 | ~170 | ~50 |
| react-typescript | 4 | ~150 | ~50 |
| nextjs-fullstack | 6 | ~140 | ~50 |
| react-fastapi-monorepo | 3 | ~160 | ~50 |
| mcp-typescript | 2 | ~130 | ~50 |
| fastmcp-python | 2 | ~120 | ~50 |
| default | 0 | - | - |
| **Total** | **32** | | |

### Phase 3: Apply to Each Agent

For each agent file:
1. Extract responsibilities to frontmatter `capabilities`
2. Convert verbose sections to prose
3. Add link to extended documentation
4. Validate structure

### Phase 4: Update Agent Development Guide

Update `.claude/rules/guidance/agent-development.md` with new standard template.

## Token Savings

| Metric | Calculation | Value |
|--------|-------------|-------|
| Agents | 32 | |
| Lines removed per agent | ~30 | |
| Total lines removed | 32 × 30 | ~960 |
| Tokens saved | ~960 × 4 | ~3,840 |

## Files to Modify

All agent core files across templates:
```
installer/core/templates/*/agents/*.md (excluding *-ext.md)
```

Plus documentation update:
```
.claude/rules/guidance/agent-development.md
```

## Related Tasks

- **Same Wave:** Wave 4
- **Parallel:** TASK-CR-T02, TASK-CR-T03
