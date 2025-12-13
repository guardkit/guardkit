---
id: TASK-STE-004
title: Enhance fastapi-testing-specialist agent
status: backlog
created: 2025-12-13T13:00:00Z
priority: high
tags: [agent-enhance, fastapi, python, testing, progressive-disclosure]
parent_task: TASK-REV-1DDD
implementation_mode: task-work
wave: 2
conductor_workspace: self-template-wave2-testing
complexity: 5
depends_on:
  - TASK-STE-001
  - TASK-STE-002
---

# Task: Enhance fastapi-testing-specialist agent

## Description

Apply `/agent-enhance` to the fastapi-testing-specialist agent. This agent already has extensive content (17.2 KB) but the extended file is small (2.6 KB) - consider rebalancing.

## Target File

`installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md`

## Current State

- Core file: 17.2 KB (larger than typical)
- Extended file: 2.6 KB (smaller than typical)
- Quality score: 9/10
- Has comprehensive testing patterns

## Enhancement Goals

1. **Rebalance core/extended split** - Move detailed examples to extended
2. **Keep core focused** on essential patterns and boundaries
3. **Add more async testing patterns** to extended
4. **Add pytest-bdd integration examples**
5. **Include common troubleshooting scenarios**

## Commands

```bash
# Dry-run first
/agent-enhance installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md \
  installer/core/templates/fastapi-python --strategy=ai --dry-run

# Review output, then apply if beneficial
/agent-enhance installer/core/templates/fastapi-python/agents/fastapi-testing-specialist.md \
  installer/core/templates/fastapi-python --strategy=ai
```

## Acceptance Criteria

- [ ] Core file reduced to ~8-10 KB (essential content only)
- [ ] Extended file expanded with detailed examples
- [ ] pytest-bdd patterns added
- [ ] Troubleshooting scenarios included
- [ ] Quality score maintained at 9/10

## Notes

- This agent has the best content - focus on organization, not creation
- Progressive disclosure benefits from smaller core file
- Can run in parallel with TASK-STE-003 and TASK-STE-005
