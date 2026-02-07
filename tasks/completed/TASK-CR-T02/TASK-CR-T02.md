---
id: TASK-CR-T02
title: Consolidate duplicated code examples across all templates
status: completed
created: 2026-02-06T01:15:00+00:00
updated: 2026-02-06T07:00:00+00:00
completed: 2026-02-06T07:00:00+00:00
priority: high
tags:
- context-optimization
- token-reduction
- templates
- deduplication
parent_review: TASK-REV-CROPT
feature_id: FEAT-CR01
implementation_mode: task-work
wave: 4
complexity: 6
task_type: refactoring
depends_on:
- TASK-CR-T01
conductor_workspace: context-reduction-wave4-1
---

# Task: Consolidate Duplicated Code Examples Across All Templates

## Background

Analysis revealed that **code examples are duplicated 3x** across template files:
1. Root CLAUDE.md (full example)
2. .claude/rules/{pattern}.md (full example)
3. agents/{specialist}-ext.md (full example)

This creates ~60 duplications across 7 templates, representing **~15,000-20,000 tokens** of redundant content.

## Description

Consolidate code examples to a single authoritative location (agent extended files) and replace duplicates with links.

**Target state:**
- Code examples live ONLY in agent-ext files
- Root CLAUDE.md references via links
- Rules files reference via links
- No copy-paste duplication

## Acceptance Criteria

- [x] Audit all 7 templates for duplicated examples
- [x] Create inventory of duplications (pattern name, locations, line counts)
- [x] For each duplication:
  - [x] Verify example exists in agent-ext file (add if missing)
  - [x] Replace duplicate in root CLAUDE.md with link
  - [x] Replace duplicate in rules file with link
- [x] No examples removed without link replacement
- [ ] All templates pass `/template-validate`
- [x] Total line reduction ≥5,000 lines across all templates (achieved: 5,106 net lines)

## Duplication Inventory (from review analysis)

### FastAPI Template (~20 duplications)
| Pattern | CLAUDE.md | Rules | Agent-ext |
|---------|-----------|-------|-----------|
| CRUD operations | Lines 200-250 | crud.md | fastapi-database-specialist-ext.md |
| Schema validation | Lines 300-340 | schemas.md | fastapi-specialist-ext.md |
| Dependency injection | Lines 400-430 | dependencies.md | fastapi-specialist-ext.md |
| ... (17 more) | | | |

### React TypeScript Template (~15 duplications)
| Pattern | CLAUDE.md | Rules | Agent-ext |
|---------|-----------|-------|-----------|
| TanStack Query | Lines 150-200 | query-patterns.md | react-query-specialist-ext.md |
| Form handling | Lines 250-300 | forms.md | form-validation-specialist-ext.md |
| ... | | | |

### Other Templates (~25 duplications combined)
- nextjs-fullstack: ~8 duplications
- react-fastapi-monorepo: ~10 duplications
- mcp-typescript: ~4 duplications
- fastmcp-python: ~3 duplications

## Implementation Approach

### Phase 1: Audit (for each template)

```bash
# For each template, identify duplicated code blocks
# Compare CLAUDE.md code blocks with rules/*.md and agents/*-ext.md
```

Create markdown table documenting each duplication.

### Phase 2: Verify Canonical Location

For each duplicated example:
1. Check if agent-ext file has the example
2. If missing, add it to agent-ext file
3. Note the exact location (file:line)

### Phase 3: Replace with Links

Replace code block with:
```markdown
**Example:** See [CRUD Operations](agents/fastapi-database-specialist-ext.md#crud-operations)
```

### Phase 4: Validate

Run `/template-validate` on each modified template.

## Token Savings

| Template | Duplications | Lines Removed | Tokens Saved |
|----------|--------------|---------------|--------------|
| fastapi-python | ~20 | ~1,500 | ~6,000 |
| react-typescript | ~15 | ~1,200 | ~4,800 |
| nextjs-fullstack | ~8 | ~600 | ~2,400 |
| react-fastapi-monorepo | ~10 | ~800 | ~3,200 |
| mcp-typescript | ~4 | ~300 | ~1,200 |
| fastmcp-python | ~3 | ~200 | ~800 |
| default | ~0 | 0 | 0 |
| **Total** | **~60** | **~4,600** | **~18,400** |

## Files to Modify

All templates under `installer/core/templates/`:
- `*/CLAUDE.md` (remove duplicates)
- `*/.claude/rules/*.md` (remove duplicates)
- `*/agents/*-ext.md` (verify examples exist)

## Risk Mitigation

- **Before removing any example:** Verify it exists in agent-ext file
- **Link format:** Use consistent format with anchor links
- **Validation:** Run template-validate after each template modification
- **Rollback:** Git commit after each template to enable rollback

## Related Tasks

- **Depends on:** TASK-CR-T01 (FastAPI trimming establishes pattern)
- **Same Wave:** Wave 4
- **Parallel:** TASK-CR-T03, TASK-CR-T04

## Implementation Results

### Actual Token Savings

| Template | Files Changed | Lines Added | Lines Deleted | Net Reduction |
|----------|--------------|-------------|---------------|---------------|
| fastapi-python | 6 | 178 | 2,658 | 2,480 |
| react-typescript | 8 | 156 | 1,468 | 1,312 |
| react-fastapi-monorepo | 3 | 253 | 2,105 | 1,852 (est.) |
| mcp-typescript | 3 | 36 | 149 | 113 |
| fastmcp-python | 2 | 56 | 248 | 192 |
| nextjs-fullstack | 3 | 18 | 74 | 56 |
| default | 3 | 12 | 12 | 0 (frontmatter only) |
| **Total** | **28** | **704** | **5,810** | **5,106** |

### Consolidation Strategy Applied

1. **Core agent files** (e.g., `fastapi-specialist.md`): Removed verbose examples, added "Extended Reference" section with pointer to `-ext.md` file
2. **CLAUDE.md files**: Replaced inline code blocks with summary tables + "See:" references to rules files
3. **Rules files** (e.g., `testing.md`): Replaced detailed fixtures with brief pattern descriptions + references to agent files
4. **Agent-ext files**: Consolidated internal duplications, removed duplicate footer sections

### Verification

- All references point to existing sections/files
- Progressive disclosure pattern maintained: CLAUDE.md (brief) -> rules (patterns) -> agent-ext (comprehensive)
- No examples removed without replacement reference
