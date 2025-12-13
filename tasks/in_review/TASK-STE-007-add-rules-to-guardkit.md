---
id: TASK-STE-007
title: Add rules structure to GuardKit .claude/
status: in_review
created: 2025-12-13T13:00:00Z
updated: 2025-12-13T16:00:00Z
priority: high
tags: [rules-structure, guardkit, conditional-loading, python-library]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 2
conductor_workspace: self-template-wave2-guardkit-rules
complexity: 5
depends_on:
  - TASK-STE-001
previous_state: in_progress
state_transition_reason: "All acceptance criteria met - rules structure created"
---

# Task: Add rules structure to GuardKit .claude/

## Description

Create `.claude/rules/` structure in GuardKit repository for conditional loading of **Python library development patterns**. This provides 40-50% context reduction when editing specific file types.

**CRITICAL**: GuardKit is a Python library/CLI tool. Rules should focus on:
- Python library patterns (not API endpoints)
- Pydantic v2 models for data validation
- Dataclasses for internal state
- pytest fixtures with complex mocking
- Module organization for CLI tools
- Type hints with strict mypy

## Target Location

`/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/rules/`

## Rules Structure to Create (REVISED)

```
.claude/rules/
├── python-library.md         # paths: installer/core/lib/**/*.py
├── testing.md                # paths: tests/**/*.py
├── task-workflow.md          # paths: tasks/**/*
├── patterns/
│   ├── template.md           # paths: installer/core/templates/**/*
│   ├── pydantic-models.md    # paths: **/models.py, **/schemas.py
│   └── dataclasses.md        # paths: **/*.py (when using dataclasses)
└── guidance/
    └── agent-development.md  # paths: **/agents/**/*.md
```

## File Contents (REVISED)

### python-library.md
- Python module organization patterns
- Import conventions (relative vs absolute)
- `__all__` exports
- Type hints and mypy compliance
- Docstring conventions (NumPy style)
- Error handling patterns (exceptions, ErrorOr)

### testing.md
- pytest fixture patterns
- Mocking with `unittest.mock`
- `monkeypatch` vs `patch` patterns
- Test file organization
- Coverage requirements (90%+)
- Complex fixture examples from actual tests

### task-workflow.md
- Task state transitions
- Task file format
- Frontmatter requirements
- Review vs implementation workflows

### patterns/pydantic-models.md
- Pydantic v2 BaseModel patterns
- Field validation
- Model serialization
- JSON schema generation

### patterns/dataclasses.md
- `@dataclass` patterns
- `asdict()` usage
- Optional fields with `field(default_factory=...)`
- When to use dataclass vs Pydantic

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

- [x] Rules directory created with 7 files
- [x] Each file has correct `paths:` frontmatter
- [x] Python library patterns extracted from actual GuardKit code
- [x] pytest patterns extracted from actual test files
- [x] Pydantic/dataclass patterns documented
- [x] Rules load correctly when editing relevant files
- [x] Context usage reduced for targeted file editing

## Implementation Summary

Created 7 rule files in `.claude/rules/`:

| File | Lines | Paths |
|------|-------|-------|
| python-library.md | 215 | installer/core/lib/**/*.py |
| testing.md | 211 | tests/**/*.py |
| task-workflow.md | 156 | tasks/**/* |
| patterns/pydantic-models.md | 146 | **/models.py, **/schemas.py |
| patterns/dataclasses.md | 180 | **/*.py |
| patterns/template.md | 159 | installer/core/templates/**/* |
| guidance/agent-development.md | 185 | **/agents/**/*.md |

Patterns extracted from actual GuardKit code:
- `id_generator.py`: Thread-safe caching, compiled regex, NumPy docstrings
- `template_creation/models.py`: Pydantic v2 BaseModel, Field(), nested models
- `agent_enhancement/orchestrator.py`: @dataclass, asdict(), checkpoint-resume
- `tests/unit/test_id_validation.py`: pytest fixtures, monkeypatch, importlib

## Notes

- This is selective rules structure - not full migration
- Root CLAUDE.md remains comprehensive reference
- **Focus on patterns ACTUALLY USED in GuardKit**:
  - `id_generator.py` patterns (SHA-256, threading, caching)
  - `models.py` Pydantic patterns (TemplateManifest, etc.)
  - `orchestrator.py` patterns (checkpoint-resume, state)
  - Test patterns from `test_id_generator.py`
