---
id: TASK-STE-006
title: Add rules structure to fastapi-python template
status: backlog
created: 2025-12-13T13:00:00Z
priority: high
tags: [rules-structure, fastapi, python, conditional-loading]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 3
conductor_workspace: self-template-wave3-fastapi-rules
complexity: 5
depends_on:
  - TASK-STE-003
  - TASK-STE-004
  - TASK-STE-005
---

# Task: Add rules structure to fastapi-python template

## Description

Create `.claude/rules/` structure within the fastapi-python template for conditional loading of Python-specific patterns.

## Target Location

`installer/core/templates/fastapi-python/.claude/rules/`

## Rules Structure to Create

```
installer/core/templates/fastapi-python/.claude/rules/
├── python-style.md          # paths: **/*.py
├── testing.md               # paths: tests/**/*.py, **/test_*.py
├── database.md              # paths: **/models/*.py, **/crud/*.py
└── guidance/
    └── fastapi-patterns.md  # paths: src/**/*.py
```

## File Contents

### python-style.md
- Python naming conventions
- Import organization (ruff/isort)
- Type hints guidance
- Async/await patterns

### testing.md
- pytest best practices
- Fixture patterns
- Async test requirements
- Coverage thresholds

### database.md
- SQLAlchemy 2.0 patterns
- Async session management
- Migration guidance
- Connection pooling

### guidance/fastapi-patterns.md
- Router organization
- Dependency injection
- Pydantic v2 usage
- Error handling

## Acceptance Criteria

- [ ] Rules directory created with 4 files
- [ ] Each file has correct `paths:` frontmatter
- [ ] Content extracted from existing CLAUDE.md and agents
- [ ] Rules load correctly when editing relevant files
- [ ] No duplication with existing agent content

## Notes

- Rules should complement, not duplicate, agent content
- Test that rules load conditionally based on file paths
- Can run in parallel with TASK-STE-007
