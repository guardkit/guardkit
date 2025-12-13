---
id: TASK-STE-003
title: Enhance fastapi-specialist agent
status: backlog
created: 2025-12-13T13:00:00Z
priority: high
tags: [agent-enhance, fastapi, python, progressive-disclosure]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 2
conductor_workspace: self-template-wave2-specialist
complexity: 5
depends_on:
  - TASK-STE-001
  - TASK-STE-002
---

# Task: Enhance fastapi-specialist agent

## Description

Apply `/agent-enhance` to the fastapi-specialist agent to improve content quality based on Wave 1 analysis findings.

## Target File

`installer/core/templates/fastapi-python/agents/fastapi-specialist.md`

## Current State

- Core file: 5.8 KB
- Extended file: 14.9 KB
- Quality score: 8.5/10
- Has ALWAYS/NEVER/ASK boundaries
- Has discovery metadata

## Enhancement Goals

1. **Add more code examples** from template source files
2. **Strengthen boundaries** with more specific rules
3. **Add best practices** with rationale
4. **Include anti-patterns** to avoid
5. **Improve discovery metadata** for better agent matching

## Commands

```bash
# Dry-run first
/agent-enhance installer/core/templates/fastapi-python/agents/fastapi-specialist.md \
  installer/core/templates/fastapi-python --strategy=ai --dry-run

# Review output, then apply if beneficial
/agent-enhance installer/core/templates/fastapi-python/agents/fastapi-specialist.md \
  installer/core/templates/fastapi-python --strategy=ai
```

## Acceptance Criteria

- [ ] Dry-run output reviewed
- [ ] Agent enhanced with additional code examples
- [ ] Boundaries strengthened (5-7 ALWAYS, 5-7 NEVER, 3-5 ASK)
- [ ] Best practices section improved
- [ ] Extended file updated if needed
- [ ] Quality score maintained or improved

## Notes

- Use findings from TASK-STE-002 to guide enhancements
- Preserve existing content that is working well
- Can run in parallel with TASK-STE-004 and TASK-STE-005
