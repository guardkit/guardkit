---
id: TASK-RBT-003
title: Register both templates as builtins
status: completed
completed: 2026-04-03T23:00:00Z
created: 2026-04-03T22:00:00Z
priority: high
tags: [template, registration, installer, documentation]
parent_review: TASK-REV-DF07
feature_id: FEAT-RBT
implementation_mode: task-work
wave: 2
complexity: 4
depends_on:
  - TASK-RBT-001
  - TASK-RBT-002
---

# Task: Register both templates as builtins

## Description

Copy the fixed python-library and nats-asyncio-service templates from `~/.agentecflow/templates/` to `installer/core/templates/` and update all registration points so they appear as first-class builtin templates.

## Changes Required

### 1. Copy templates

```bash
cp -r ~/.agentecflow/templates/nats-asyncio-service/ installer/core/templates/nats-asyncio-service/
cp -r ~/.agentecflow/templates/python-library/ installer/core/templates/python-library/
```

### 2. Update guardkit/cli/init.py (line 1631)

Add `python-library` and `nats-asyncio-service` to the Available templates help text.

Current:
```
Available templates: default, fastapi-python, react-typescript, nextjs-fullstack, langchain-deepagents, langchain-deepagents-orchestrator, langchain-deepagents-weighted-evaluation.
```

Updated (also adding other missing templates for accuracy):
```
Available templates: default, fastapi-python, react-typescript, nextjs-fullstack, react-fastapi-monorepo, python-library, nats-asyncio-service, langchain-deepagents, langchain-deepagents-orchestrator, langchain-deepagents-weighted-evaluation.
```

### 3. Update root CLAUDE.md (line 223)

Add both templates to the Templates list:
```
Templates: react-typescript | fastapi-python | nextjs-fullstack | react-fastapi-monorepo | python-library | nats-asyncio-service | langchain-deepagents | langchain-deepagents-orchestrator | langchain-deepagents-weighted-evaluation | default
```

### 4. Update installer/scripts/install.sh

Add template descriptions to the help text section for both new templates:
- **python-library**: Standalone pip-installable Python library with hatchling, src layout, pytest, ruff, mypy strict
- **nats-asyncio-service**: NATS event-driven asyncio service with FastStream, TestNatsBroker, pydantic-settings, JetStream

### 5. Verify directory structure

Ensure both template directories match the conventions of existing builtins:
- `manifest.json` present
- `settings.json` present
- `.claude/CLAUDE.md` present
- `.claude/rules/` directory present
- `agents/` directory present (if applicable)

## Acceptance Criteria

- [x] Both templates exist under `installer/core/templates/`
- [x] `guardkit/cli/init.py` help text lists both templates
- [x] Root `CLAUDE.md` template list includes both templates
- [x] `installer/scripts/install.sh` help text includes both templates
- [x] Template directory structure matches existing builtin conventions
- [x] No hardcoded paths from user-local location remain

## References

- Review report: `.claude/reviews/TASK-REV-DF07-review-report.md`
- Reference task: TASK-REV-TI25 (langchain-deepagents-orchestrator registration)
- Existing builtins: `installer/core/templates/`
