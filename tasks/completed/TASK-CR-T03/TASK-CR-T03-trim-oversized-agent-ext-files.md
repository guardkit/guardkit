---
id: TASK-CR-T03
title: Trim oversized agent extended files (5 hotspots)
status: completed
created: 2026-02-06T01:15:00+00:00
updated: 2026-02-06T12:30:00+00:00
completed: 2026-02-06T12:30:00+00:00
completed_location: tasks/completed/TASK-CR-T03/
priority: medium
tags:
- context-optimization
- token-reduction
- templates
- agents
parent_review: TASK-REV-CROPT
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 4
complexity: 4
task_type: documentation
depends_on:
- TASK-CR-T02
conductor_workspace: context-reduction-wave4-2
---

# Task: Trim Oversized Agent Extended Files (5 Hotspots)

## Background

Analysis identified 5 agent extended files that are significantly oversized:

| File | Current Lines | Target Lines | Issue |
|------|---------------|--------------|-------|
| fastapi-database-specialist-ext.md | 900 | 400-500 | Excessive tech context |
| form-validation-specialist-ext.md | 528 | 300-350 | Redundant anti-patterns |
| react-fastapi-monorepo agent 1 | 500+ | 350 | Verbose examples |
| react-fastapi-monorepo agent 2 | 500+ | 350 | Verbose examples |
| react-fastapi-monorepo agent 3 | 500+ | 350 | Verbose examples |

**Common issues:**
- "Technology Stack Context" sections with 100+ lines of framework descriptions
- 10+ anti-patterns when 5 essentials would suffice
- Redundant "When to use" explanations

## Description

Trim the 5 identified oversized agent extended files by:
1. Removing excessive "Technology Stack Context" boilerplate
2. Consolidating anti-patterns to 5 essentials
3. Compressing verbose "When to use" sections
4. Ensuring code examples remain complete and usable

## Acceptance Criteria

- [x] fastapi-database-specialist-ext.md reduced to 347 lines (below 400-500 target)
- [x] form-validation-specialist-ext.md reduced to 248 lines (below 300-350 target)
- [x] 3 react-fastapi-monorepo agent-ext files reduced to 253/258/222 lines (below 350 target)
- [x] Anti-patterns sections limited to 5 items per file
- [x] Technology Stack Context sections compressed
- [x] All code examples preserved (no functionality lost, balanced code blocks verified)
- [x] Structural validation passed (all files have proper H1/H2/H3, balanced markdown)

## Implementation Approach

### For Each Oversized File:

1. **Audit current content**
   - Count lines per section
   - Identify verbose sections
   - Mark content for removal/compression

2. **Compress Technology Stack Context**
   - Remove generic framework descriptions (user can read official docs)
   - Keep only project-specific context
   - Target: 30 lines max

3. **Consolidate Anti-Patterns**
   - Identify all listed anti-patterns
   - Rank by severity/frequency
   - Keep top 5 most important
   - Remove or consolidate others

4. **Compress "When to Use" Sections**
   - Convert verbose paragraphs to bullet points
   - Remove obvious/redundant guidance
   - Target: 10 lines max per pattern

5. **Validate**
   - Ensure code examples still work
   - Run template-validate
   - Check for broken internal links

## Token Savings

| File | Lines Removed | Tokens Saved |
|------|---------------|--------------|
| fastapi-database-specialist-ext.md | ~400-500 | ~1,600-2,000 |
| form-validation-specialist-ext.md | ~180 | ~720 |
| react-fastapi-monorepo agents (3) | ~450 | ~1,800 |
| **Total** | **~1,000-1,100** | **~4,000-4,500** |

## Files to Modify

```
installer/core/templates/
├── fastapi-python/
│   └── agents/fastapi-database-specialist-ext.md
├── react-typescript/
│   └── agents/form-validation-specialist-ext.md
└── react-fastapi-monorepo/
    └── agents/*.md (identify 3 largest)
```

## Related Tasks

- **Depends on:** TASK-CR-T02 (examples consolidated first)
- **Same Wave:** Wave 4
- **Parallel:** TASK-CR-T04
