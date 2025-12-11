---
id: TASK-CRS-014
title: Rename rules/agents/ to rules/guidance/ (Revised Scope)
status: completed
task_type: review
created: 2025-12-11T14:30:00Z
updated: 2025-12-11T15:30:00Z
priority: medium
tags: [rules-structure, naming, refactor]
complexity: 3
parent_feature: claude-rules-structure
wave: 3
implementation_mode: task-review
conductor_workspace: claude-rules-wave3-4
estimated_hours: 2-3
review_results:
  mode: architectural
  depth: standard
  score: 90
  findings_count: 2
  recommendations_count: 8
  decision: implement
  report_path: .claude/reviews/TASK-CRS-014-review-report.md
  completed_at: 2025-12-11T15:30:00Z
---

# Task: Rename rules/agents/ to rules/guidance/ (Revised Scope)

## Original Scope (Superseded)

The original task assumed `/agent-enhance` needed modification for rules structure support.

## Revised Scope (After Review)

**Key Finding**: The `/agent-enhance` command does NOT need changes. However, a naming confusion was identified:

- `agents/` directory = Full specialist definitions (for Task tool, /agent-enhance)
- `.claude/rules/agents/` directory = Path-based contextual guidance (static)

**Decision**: Rename `.claude/rules/agents/` to `.claude/rules/guidance/` across all components.

## Review Summary

The architectural review (see `.claude/reviews/TASK-CRS-014-review-report.md`) determined:

1. **No changes needed to /agent-enhance** - It operates on `agents/` directory only
2. **Naming confusion exists** - Using "agents" for two different concepts
3. **Solution**: Rename `rules/agents/` → `rules/guidance/`

## Subtasks Created

| ID | Title | Priority | Est. Hours |
|----|-------|----------|------------|
| CRS-014.1 | Update RulesStructureGenerator to output `rules/guidance/` | High | 0.5 |
| CRS-014.2 | Rename react-typescript `rules/agents/` → `guidance/` | High | 0.25 |
| CRS-014.3 | Rename nextjs-fullstack `rules/agents/` → `guidance/` | High | 0.25 |
| CRS-014.4 | Rename fastapi-python `rules/agents/` → `guidance/` | High | 0.25 |
| CRS-014.5 | Rename react-fastapi-monorepo `rules/agents/` → `guidance/` | High | 0.25 |
| CRS-014.7 | Update tests for `rules/guidance/` naming | High | 0.5 |
| CRS-014.8 | Update documentation for `rules/guidance/` naming | Medium | 0.5 |

**Total: ~2.5 hours**

**Note**: CRS-014.6 (default template) was removed - that template doesn't have a `rules/agents/` directory.

## Execution Order

1. **CRS-014.1** (RulesStructureGenerator) - Must be first
2. **CRS-014.2-6** (Template renames) - Can be parallel
3. **CRS-014.7** (Tests) - After CRS-014.1
4. **CRS-014.8** (Documentation) - Can be last

## Key Distinction to Document

```
agents/                    → Full specialist definitions (invokable via Task tool)
.claude/rules/guidance/    → Path-based contextual guidance (static, auto-loaded)
```

## Acceptance Criteria

- [x] Review completed
- [x] Subtasks created
- [x] CRS-014.1: RulesStructureGenerator updated
- [x] CRS-014.2-5: All 4 templates renamed (default doesn't need renaming)
- [x] CRS-014.7: Tests updated
- [x] CRS-014.8: Documentation updated

## Notes

- Original assumption (agent-enhance changes) was incorrect
- Conductor worktrees for CRS-006, CRS-009, CRS-010 may need renaming before merge
- If those tasks are still in worktrees, do rename there to avoid double work
