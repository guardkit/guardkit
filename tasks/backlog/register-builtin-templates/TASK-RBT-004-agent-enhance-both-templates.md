---
id: TASK-RBT-004
title: Run agent-enhance on both templates
status: completed
created: 2026-04-03T22:00:00Z
priority: medium
tags: [template, agents, enhancement]
parent_review: TASK-REV-DF07
feature_id: FEAT-RBT
implementation_mode: direct
wave: 3
complexity: 2
depends_on:
  - TASK-RBT-003
---

# Task: Run agent-enhance on both templates

## Description

Run `/agent-enhance --strategy=hybrid` on all agents in both newly registered templates to ensure they have full template context and meet quality standards.

## Steps

1. For each agent in `installer/core/templates/nats-asyncio-service/agents/`:
   ```bash
   /agent-enhance installer/core/templates/nats-asyncio-service/agents/{agent}.md installer/core/templates/nats-asyncio-service/ --strategy=hybrid
   ```

2. For each agent in `installer/core/templates/python-library/agents/` (after generalization in TASK-RBT-002):
   ```bash
   /agent-enhance installer/core/templates/python-library/agents/{agent}.md installer/core/templates/python-library/ --strategy=hybrid
   ```

## Acceptance Criteria

- [x] All agents in nats-asyncio-service enhanced (7 agents: core + ext files)
- [x] All agents in python-library enhanced (2 agents: core + ext files)
- [x] No agent validation errors (0 errors, all frontmatter parses, discovery metadata present)

## References

- Template specs recommend running agent-enhance after registration
