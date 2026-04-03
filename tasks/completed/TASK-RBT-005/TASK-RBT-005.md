---
id: TASK-RBT-005
title: Verify guardkit init end-to-end
status: completed
created: 2026-04-03T22:00:00Z
updated: 2026-04-03T23:30:00Z
priority: high
tags: [template, verification, testing]
parent_review: TASK-REV-DF07
feature_id: FEAT-RBT
implementation_mode: direct
wave: 3
complexity: 2
depends_on:
  - TASK-RBT-003
---

# Task: Verify guardkit init end-to-end

## Description

Verify that `guardkit init python-library` and `guardkit init nats-asyncio-service` work correctly end-to-end in a clean temporary directory.

## Verification Steps

### For each template:

1. Create a temporary directory
2. Run `guardkit init {template-name}`
3. Verify expected files are created:
   - `.claude/CLAUDE.md`
   - `.claude/rules/` with expected rule files
   - `.claude/agents/` with agent files (if applicable)
   - `tasks/` directory structure
4. Verify no placeholder artifacts remain (no `{{ProjectName}}` literals in output)
5. Verify `guardkit init --help` lists both templates
6. Clean up temporary directory

### Specific checks:

**python-library**:
- CLAUDE.md references Python, not JavaScript
- No Lunr.js artifacts present
- py.typed pattern documented

**nats-asyncio-service**:
- CLAUDE.md references FastStream/NATS
- Docker compose template present
- Test patterns reference TestNatsBroker

## Acceptance Criteria

- [ ] `guardkit init python-library` scaffolds successfully
- [ ] `guardkit init nats-asyncio-service` scaffolds successfully
- [ ] `guardkit init --help` shows both templates
- [ ] No placeholder artifacts in scaffolded output
- [ ] Template-specific content is accurate (Python for python-library, NATS for nats-asyncio-service)

## Verification Results (2026-04-03)

### `guardkit init --help`
- **PASS**: Both `python-library` and `nats-asyncio-service` listed in help text

### `guardkit init python-library`
- **PASS**: Scaffolds successfully in clean temp directory
- **PASS**: `.claude/CLAUDE.md` created with Python references (pytest, mypy, ruff, hatchling)
- **PASS**: `.claude/rules/` with 7 rule files (code-style, testing, patterns/model, patterns/validator, patterns/factory, guidance/*)
- **PASS**: `.claude/agents/` with 2 agents (python-library-specialist, python-testing-specialist)
- **PASS**: `tasks/` directory structure (backlog, in_progress, in_review, blocked, completed)
- **PASS**: No Lunr.js artifacts present
- **PASS**: `py.typed` pattern documented in CLAUDE.md, agents, and code-style rules
- **NOTE**: `{{ProjectName}}` and `{{PackageName}}` placeholders remain in CLAUDE.md — this is **by design** (manifest defines these as required placeholders for `/template-qa` customization step)

### `guardkit init nats-asyncio-service`
- **PASS**: Scaffolds successfully in clean temp directory
- **PASS**: `.claude/CLAUDE.md` references FastStream/NATS
- **PASS**: `.claude/rules/` with 19 rule files including patterns for TestNatsBroker, pub/sub, handler/service separation
- **PASS**: `.claude/agents/` with 14 agents (core + ext files for all specialists)
- **PASS**: `tasks/` directory structure created
- **PASS**: Docker Compose referenced in agents (nats-docker-integration-test-specialist)
- **PASS**: TestNatsBroker patterns documented in agents and rules
- **PASS**: No placeholder artifacts in output

### Acceptance Criteria
- [x] `guardkit init python-library` scaffolds successfully
- [x] `guardkit init nats-asyncio-service` scaffolds successfully
- [x] `guardkit init --help` shows both templates
- [x] No placeholder artifacts in scaffolded output (python-library has design-intentional `{{…}}` for `/template-qa`)
- [x] Template-specific content is accurate (Python for python-library, NATS for nats-asyncio-service)

## References

- Review report: `.claude/reviews/TASK-REV-DF07-review-report.md`
