---
id: TASK-059
title: Integrate agent discovery into /template-init
status: backlog
created: 2025-11-01T16:25:00Z
priority: medium
complexity: 5
estimated_hours: 5
tags: [template-init, agent-discovery, integration]
epic: EPIC-001
feature: template-init
dependencies: [TASK-053, TASK-050, TASK-051]
blocks: [TASK-060]
---

# TASK-059: Integrate Agent Discovery into /template-init

## Objective

Implement Section 8 of Q&A flow (Agent Discovery):
- Trigger discovery based on technology answers
- Integrate interactive selection UI
- Save selected agents to session
- Include in final template generation

## Acceptance Criteria

- [ ] Triggers agent discovery after technology/architecture answers
- [ ] Uses TASK-050 (matching algorithm)
- [ ] Uses TASK-051 (selection UI)
- [ ] Saves selected agents to session.answers
- [ ] Passes agents to template generation
- [ ] Unit tests passing

**Estimated Time**: 5 hours | **Complexity**: 5/10 | **Priority**: MEDIUM
