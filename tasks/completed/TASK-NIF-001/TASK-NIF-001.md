---
id: TASK-NIF-001
title: Quote unquoted glob patterns in template rule files
status: completed
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
completed: 2026-04-03T00:00:00Z
priority: high
tags: [yaml, templates, rules, glob-patterns, bug-fix]
parent_review: TASK-REV-A8C2
feature_id: FEAT-NIF
implementation_mode: direct
wave: 1
complexity: 1
---

# Task: Quote unquoted glob patterns in template rule files

## Description

Eight rule files across 4 templates have unquoted glob patterns in their YAML frontmatter `paths:` field. The `*` character is a YAML alias indicator, causing `yaml.safe_load()` to fail with "while scanning an alias" errors during `guardkit init` system knowledge seeding.

## Affected Files

1. `installer/core/templates/python-library/.claude/rules/code-style.md`
   - Change: `paths: **/*.py` -> `paths: "**/*.py"`

2. `installer/core/templates/python-library/.claude/rules/testing.md`
   - Change: `paths: **/*.test.*, **/tests/**, **/*_test.*, **/test_*.*,  **/conftest.py` -> `paths: "**/*.test.*, **/tests/**, **/*_test.*, **/test_*.*, **/conftest.py"`

3. `installer/core/templates/langchain-deepagents/.claude/rules/code-style.md`
   - Change: `paths: **/*.py, **/*.pyx` -> `paths: "**/*.py, **/*.pyx"`

4. `installer/core/templates/langchain-deepagents/.claude/rules/testing.md`
   - Change: `paths: **/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*` -> `paths: "**/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*"`

5. `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/code-style.md`
   - Change: `paths: **/*.py, **/*.pyx` -> `paths: "**/*.py, **/*.pyx"`

6. `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/testing.md`
   - Change: `paths: **/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*` -> `paths: "**/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*"`

7. `installer/core/templates/nats-asyncio-service/.claude/rules/code-style.md`
   - Change: `paths: **/*.py, **/*.pyx` -> `paths: "**/*.py, **/*.pyx"`

8. `installer/core/templates/nats-asyncio-service/.claude/rules/testing.md`
   - Change: `paths: **/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*` -> `paths: "**/*.test.*, **/tests/**, **/*_test.*, **/*Test.*, **/*Spec.*"`

Also fix the double-space in python-library testing.md (`**/test_*.*,  **/conftest.py`).

## Acceptance Criteria

- [x] All 8 rule files have quoted glob patterns in `paths:` frontmatter
- [x] `yaml.safe_load()` succeeds on all affected files' frontmatter
- [x] Claude Code still loads rules correctly (quoted paths are valid)

## Notes

Correctly quoted examples already exist in other templates (fastapi-python, default, react-typescript). This is just bringing the 4 affected templates into consistency.
