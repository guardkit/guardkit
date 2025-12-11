---
id: TASK-CRS-010
title: Refactor default Template to Rules Structure
status: backlog
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
priority: low
tags: [template-refactor, default, rules-structure]
complexity: 2
parent_feature: claude-rules-structure
wave: 4
implementation_mode: direct
conductor_workspace: claude-rules-wave4-5
estimated_hours: 1-2
dependencies:
  - TASK-CRS-002
  - TASK-CRS-003
---

# Task: Refactor default Template to Rules Structure

## Description

Refactor the `default` template (currently 7.0KB) to use the modular `.claude/rules/` structure. This is the simplest template and lowest priority.

## Current Structure

```
installer/core/templates/default/
├── CLAUDE.md                    (7.0 KB)
├── agents/                      (empty)
└── templates/                   (empty)
```

## Target Structure

```
installer/core/templates/default/
├── .claude/
│   ├── CLAUDE.md                     (~4KB core)
│   └── rules/
│       ├── code-style.md             # (no paths - always load)
│       ├── workflow.md               # (no paths - always load)
│       └── quality-gates.md          # (no paths - always load)
├── agents/
└── templates/
```

## Content Breakdown

### Core CLAUDE.md (~4KB)

The default template is already small, so minimal changes needed:
- Keep all core sections
- Move workflow details to rules/workflow.md
- Move quality gates to rules/quality-gates.md

### rules/code-style.md

```markdown
# Code Style Guidelines

## Language-Agnostic Conventions

These guidelines apply regardless of programming language.

### Naming
- Use descriptive, meaningful names
- Avoid abbreviations unless widely understood
- Be consistent within the project

### File Organization
- Group related files together
- Use clear directory structure
- Keep files focused on single responsibility

### Comments
- Comment why, not what
- Keep comments up to date
- Use doc comments for public APIs
```

### rules/workflow.md

```markdown
# GuardKit Workflow

## Phase Execution

```
Phase 2: Implementation Planning
Phase 2.5: Architectural Review
Phase 2.7: Complexity Evaluation
Phase 2.8: Human Checkpoint (if needed)
Phase 3: Implementation
Phase 4: Testing
Phase 4.5: Test Enforcement
Phase 5: Code Review
Phase 5.5: Plan Audit
```

## Quality Gates

| Gate | Threshold |
|------|-----------|
| Compilation | 100% |
| Tests Pass | 100% |
| Coverage | ≥80% |
| Architecture | ≥60/100 |
```

### rules/quality-gates.md

```markdown
# Quality Standards

## Code Quality
- Test coverage recommended but not enforced (language-dependent)
- Quality gates active for all phases
- Test execution verified in Phase 4

## Documentation
- ADRs for architectural decisions
- Task tracking in markdown
- Implementation plans in `.claude/task-plans/`

## Testing Philosophy
"Implementation and testing are inseparable"
```

## Acceptance Criteria

- [ ] Core CLAUDE.md ~4KB
- [ ] Rules files created (no paths filtering)
- [ ] Workflow documentation split out
- [ ] Quality gates documented
- [ ] Template still works with `guardkit init`

## Notes

- This is Wave 4 (lowest priority)
- Direct implementation (simple refactoring)
- Parallel with other template tasks
- Smallest template, minimal changes needed
