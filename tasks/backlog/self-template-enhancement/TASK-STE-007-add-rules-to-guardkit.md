---
id: TASK-STE-007
title: Add rules structure to GuardKit .claude/
status: backlog
created: 2025-12-13T13:00:00Z
priority: medium
tags: [rules-structure, guardkit, conditional-loading]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 3
conductor_workspace: self-template-wave3-guardkit-rules
complexity: 5
depends_on:
  - TASK-STE-001
---

# Task: Add rules structure to GuardKit .claude/

## Description

Create `.claude/rules/` structure in GuardKit repository for conditional loading of development-specific patterns. This provides 40-50% context reduction when editing specific file types.

## Target Location

`/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/rules/`

## Rules Structure to Create

```
.claude/rules/
├── testing.md              # paths: tests/**/*
├── task-workflow.md        # paths: tasks/**/*
├── patterns/
│   └── template.md         # paths: installer/core/templates/**/*
└── guidance/
    └── agent-development.md # paths: **/agents/**/*.md
```

## File Contents

### testing.md
- Test execution patterns
- Quality gate thresholds
- Coverage requirements
- pytest/vitest/dotnet test patterns

### task-workflow.md
- Task state transitions
- Task file format
- Frontmatter requirements
- Review vs implementation workflows

### patterns/template.md
- Template creation guidelines
- Progressive disclosure patterns
- Rules structure requirements
- Agent enhancement workflow

### guidance/agent-development.md
- Agent file format
- ALWAYS/NEVER/ASK boundaries
- Discovery metadata requirements
- Core/extended split guidance

## Acceptance Criteria

- [ ] Rules directory created with 4 files
- [ ] Each file has correct `paths:` frontmatter
- [ ] Content extracted from root CLAUDE.md where appropriate
- [ ] Rules load correctly when editing relevant files
- [ ] Context usage reduced for targeted file editing

## Notes

- This is selective rules structure - not full migration
- Root CLAUDE.md remains comprehensive reference
- Rules provide focused context for specific tasks
- Can run in parallel with TASK-STE-006
