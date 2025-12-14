---
id: TASK-REV-F1BA
title: Claude Code Rules Structure Adoption Impact Review
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
created: 2025-12-11T11:30:00Z
updated: 2025-12-11T12:00:00Z
priority: high
tags: [claude-code, rules-structure, progressive-disclosure, templates, documentation, architecture-review]
complexity: 6
related_tasks:
  - TASK-FIX-SIZE-F8G2
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 12
  recommendations_count: 8
  decision: proceed_with_phases
  report_path: .claude/reviews/TASK-REV-F1BA-review-report.md
  completed_at: 2025-12-11T12:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Claude Code Rules Structure Adoption Impact Review

## Description

Review the impact of adopting Claude Code's new modular `.claude/rules/` structure as described in TASK-FIX-SIZE-F8G2. This architectural review will assess:

1. **Template Refactoring Requirements** - All 5 built-in templates need updating
2. **Documentation Updates** - CLAUDE.md, guides, and workflow docs
3. **Progressive Disclosure Integration** - How rules structure complements existing split
4. **Migration Path** - Backward compatibility and user migration strategy
5. **Implementation Complexity** - Effort estimation and phasing

## Background

Claude Code now supports a 4-tier memory hierarchy with modular rules:

```
.claude/
├── CLAUDE.md           # Core project instructions (~5KB)
└── rules/
    ├── code-style.md   # Code style guidelines
    ├── testing.md      # Testing conventions (conditional: paths: **/*.test.*)
    └── patterns/
        ├── repository.md
        └── viewmodel.md
```

**Benefits:**
- Path-specific rules only load when relevant (reduced context usage)
- Recursive discovery in subdirectories
- Conditional loading with `paths:` frontmatter
- Better organization for large projects

**Reference:** https://code.claude.com/docs/en/memory#determine-memory-type

## Scope

### Areas to Review

**1. Built-in Templates (5 templates)**

| Template | Current Structure | Rules Structure Impact |
|----------|-------------------|----------------------|
| react-typescript | CLAUDE.md + agents/ | rules/react/, rules/testing/ |
| fastapi-python | CLAUDE.md + agents/ | rules/api/, rules/database/ |
| nextjs-fullstack | CLAUDE.md + agents/ | rules/server-components/, rules/actions/ |
| react-fastapi-monorepo | CLAUDE.md + agents/ | rules/frontend/, rules/backend/ |
| default | CLAUDE.md + agents/ | rules/patterns/, rules/code-style/ |

**2. Template Creation (`/template-create`)**

- `installer/core/lib/template_generator/claude_md_generator.py`
- `installer/core/commands/lib/template_create_orchestrator.py`
- Phase 5 CLAUDE.md generation
- New `--use-rules-structure` flag (from TASK-FIX-SIZE-F8G2)

**3. Agent Enhancement (`/agent-enhance`)**

- How agent files map to rules structure
- `rules/agents/` directory pattern
- Path-based conditional loading for specialists

**4. Documentation**

- `CLAUDE.md` (root) - Progressive Disclosure section
- `.claude/CLAUDE.md` - Project Context
- `docs/guides/progressive-disclosure.md`
- `installer/core/commands/template-create.md`
- Template README files (5 templates)

**5. Installation & Initialization**

- `guardkit init` command
- Template installation process
- Upgrade path for existing projects

### Out of Scope

- Implementation (covered by TASK-FIX-SIZE-F8G2 Phase 2)
- Performance benchmarking (future task)
- External tool integrations

## Review Questions

### Architecture

1. Should rules structure be opt-in (`--use-rules-structure`) or default?
2. How do we handle projects with both old (single CLAUDE.md) and new (rules/) structures?
3. What's the recommended rules/ subdirectory organization per stack?
4. How should agent files integrate with rules structure?

### Templates

1. What rules files should each template generate by default?
2. Should we have stack-specific rules/ templates or generate dynamically?
3. How do we maintain consistency across 5 templates?

### Migration

1. What's the migration path for existing GuardKit users?
2. Should `guardkit upgrade` handle rules structure migration?
3. How do we communicate the change to users?

### Documentation

1. Which docs need updates vs rewrites?
2. Should we add a rules structure quick-start guide?
3. How do we version the documentation changes?

## Acceptance Criteria

- [ ] Impact assessment for all 5 built-in templates documented
- [ ] Documentation update requirements catalogued
- [ ] Migration strategy defined (opt-in vs default, upgrade path)
- [ ] Integration points with TASK-FIX-SIZE-F8G2 identified
- [ ] Effort estimation provided (hours/complexity per component)
- [ ] Recommendations prioritized (must-have vs nice-to-have)
- [ ] Backward compatibility strategy defined

## Deliverables

1. **Impact Assessment Report** - Component-by-component analysis
2. **Template Refactoring Plan** - Per-template changes required
3. **Documentation Update Checklist** - Files and sections to update
4. **Migration Strategy** - User communication and upgrade path
5. **Implementation Tasks** - Breakdown of work into tasks

## Implementation Notes

This is a review/analysis task. Use `/task-review` for execution.

**Suggested Review Mode:** `architectural`
**Suggested Depth:** `standard`

```bash
/task-review TASK-REV-F1BA --mode=architectural --depth=standard
```

## Test Execution Log

[Automatically populated by /task-review]
