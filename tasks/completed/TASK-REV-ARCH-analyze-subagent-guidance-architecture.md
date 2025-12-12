---
id: TASK-REV-ARCH
title: Analyze subagent vs guidance architecture to eliminate duplication
status: completed
task_type: review
created: 2025-12-11T19:00:00Z
updated: 2025-12-11T20:00:00Z
completed: 2025-12-11T20:00:00Z
priority: high
tags: [architecture-review, rules-structure, subagents, progressive-disclosure, maintenance]
complexity: 5
related_to: [TASK-RULES-ENHANCE]
decision_required: true
review_results:
  mode: architectural
  depth: standard
  score: 78
  findings_count: 5
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-ARCH-review-report.md
  implementation_tasks:
    - TASK-GA-001
    - TASK-GA-002
    - TASK-GA-003
    - TASK-GA-004
---

# Task: Analyze Subagent vs Guidance Architecture

## Background

After implementing TASK-RULES-ENHANCE, we now have content duplication between:
- `agents/{name}.md` (subagent definitions - source of truth)
- `.claude/rules/guidance/{name}.md` (path-conditional loading)

This creates maintenance overhead and risk of content divergence if edited independently.

## Constraints (Non-Negotiable)

1. **Subagent definitions MUST be kept** - These are used by GuardKit's Task subagent system for explicit invocation via `/task-work` and `@agent-name`
2. **Subagents use progressive disclosure** - Split into core (`{name}.md`) and extended (`{name}-ext.md`) files

## Current Architecture

```
template/
├── agents/                          # GuardKit subagent system
│   ├── repository-specialist.md     # Core (always loaded by Task tool)
│   └── repository-specialist-ext.md # Extended (loaded on-demand)
└── .claude/
    └── rules/
        └── guidance/
            └── repository-specialist.md  # Claude Code native (path-triggered)
```

## Two Different Mechanisms

| Aspect | agents/ (Subagents) | rules/guidance/ |
|--------|---------------------|-----------------|
| Loading | Explicit (Task tool, @mention) | Automatic (path-based) |
| Scope | Dedicated subprocess | Context injection |
| Control | Active (does work) | Passive (background) |
| System | GuardKit extension | Claude Code native |

## Problem Statement

Currently TASK-RULES-ENHANCE copies full enhanced content to both locations, resulting in:
- **Duplication**: Same content in two places
- **Maintenance risk**: Edits to one may not reflect in other
- **Storage overhead**: ~2x content size

## Options to Evaluate

### Option A: Guidance References Core File Only
```markdown
# .claude/rules/guidance/repository-specialist.md
---
paths: **/Repositories/**, **/Data/**
include: ../../agents/repository-specialist.md
---
```
- **Pros**: Single source of truth, no duplication
- **Cons**: `include:` not a native Claude Code feature (would need preprocessing)

### Option B: Guidance Contains Summary + Reference
```markdown
# .claude/rules/guidance/repository-specialist.md
---
paths: **/Repositories/**, **/Data/**
---

# Repository Specialist (Summary)

## Key Boundaries
### ALWAYS
- ✅ Use IRealmAccessor for all Realm operations
- ✅ Return ErrorOr<T> for all operations

### NEVER  
- ❌ Never instantiate Realm directly

## Full Documentation
For complete guidance including examples and best practices:
`cat agents/repository-specialist.md`
```
- **Pros**: Slim automatic loading, full content available on-demand
- **Cons**: Manual sync of summary content, partial duplication

### Option C: Symlinks (Platform-Dependent)
```bash
ln -s ../../agents/repository-specialist.md \
      .claude/rules/guidance/repository-specialist.md
```
- **Pros**: Zero duplication, always in sync
- **Cons**: Windows compatibility issues, Claude Code may not follow symlinks

### Option D: Only Use rules/guidance/ (Eliminate agents/ for templates)
- Put enhanced content only in `rules/guidance/`
- Task tool loads from `rules/guidance/` instead of `agents/`
- **Pros**: No duplication
- **Cons**: Breaks existing Task tool expectations, changes GuardKit architecture

### Option E: Keep Current Duplication (TASK-RULES-ENHANCE approach)
- Accept duplication as cost of supporting both systems
- Document that `agents/` is source of truth
- **Pros**: Both systems work independently
- **Cons**: Maintenance overhead, divergence risk

### Option F: Guidance Links to Core, Task Tool Uses Core+Ext
```markdown
# .claude/rules/guidance/repository-specialist.md
---
paths: **/Repositories/**, **/Data/**
---

<!-- Auto-generated from agents/repository-specialist.md -->
<!-- DO NOT EDIT - Changes will be overwritten -->
<!-- Source: agents/repository-specialist.md -->

[Content from core file only - boundaries, key rules]
[Excludes: detailed examples, best practices, anti-patterns]
```

Task tool continues to use:
- `agents/repository-specialist.md` (core)
- `agents/repository-specialist-ext.md` (extended, on-demand)

- **Pros**: Guidance gets slim version, subagents get full version, clear source of truth
- **Cons**: Still some duplication (core content), but much less

## Questions to Answer

1. Does Claude Code support `include:` directives in rules files?
2. Does Claude Code follow symlinks in the rules directory?
3. What's the token cost difference between full content vs summary?
4. Is the maintenance risk of duplication acceptable given clear "source of truth" documentation?
5. Should guidance contain different content than subagents (slim vs full)?

## Acceptance Criteria

- [ ] Evaluate each option with pros/cons matrix
- [ ] Test Claude Code behavior with symlinks
- [ ] Test Claude Code behavior with include-style references
- [ ] Measure token impact of each approach
- [ ] Recommend approach that balances: no duplication, both systems work, maintainable
- [ ] If duplication unavoidable, define clear "source of truth" policy

## Recommended Next Steps

After review completion:
1. If Option A/C viable → Implement reference/symlink approach
2. If Option B/F preferred → Implement summary extraction
3. If Option E chosen → Document maintenance policy clearly
