---
id: TASK-STE-005
title: Enhance fastapi-database-specialist agent
status: deferred
created: 2025-12-13T13:00:00Z
priority: low
tags: [agent-enhance, fastapi, python, database, sqlalchemy, progressive-disclosure, deferred]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: N/A
conductor_workspace: N/A
complexity: 5
depends_on:
  - TASK-STE-001
  - TASK-STE-002
deferred_reason: FastAPI templates are for users creating FastAPI apps, not for GuardKit development. GuardKit is a Python library/CLI tool. See README.md for revised plan.
---

# Task: Enhance fastapi-database-specialist agent

## Description

Apply `/agent-enhance` to the fastapi-database-specialist agent to improve SQLAlchemy 2.0 async patterns and database testing content.

## Target File

`installer/core/templates/fastapi-python/agents/fastapi-database-specialist.md`

## Current State

- Core file: 3.6 KB (smaller than ideal)
- Extended file: 25.4 KB (comprehensive)
- Quality score: 8.5/10
- Good SQLAlchemy async content

## Enhancement Goals

1. **Expand core file** with essential patterns (target 6-8 KB)
2. **Add Alembic migration patterns**
3. **Include connection pooling best practices**
4. **Add async session management patterns**
5. **Strengthen ALWAYS/NEVER/ASK boundaries**

## Commands

```bash
# Dry-run first
/agent-enhance installer/core/templates/fastapi-python/agents/fastapi-database-specialist.md \
  installer/core/templates/fastapi-python --strategy=ai --dry-run

# Review output, then apply if beneficial
/agent-enhance installer/core/templates/fastapi-python/agents/fastapi-database-specialist.md \
  installer/core/templates/fastapi-python --strategy=ai
```

## Acceptance Criteria

- [ ] Core file expanded to 6-8 KB
- [ ] Alembic migration patterns added
- [ ] Connection pooling guidance included
- [ ] Boundaries strengthened
- [ ] Quality score improved to 9/10

## Notes

- Small core file means essential patterns may be missing
- Extended file has good content - ensure core references it properly
- Can run in parallel with TASK-STE-003 and TASK-STE-004
