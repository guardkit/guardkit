---
id: TASK-054
title: Implement basic information section for /template-init
status: backlog
created: 2025-11-01T16:20:00Z
priority: medium
complexity: 3
estimated_hours: 3
tags: [template-init, qa-sections]
epic: EPIC-001
feature: template-init
dependencies: [TASK-053]
blocks: [TASK-060]
---

# TASK-054: Implement Basic Information Section

## Objective

Implement Section 1 of Q&A flow (Basic Information):
- Template name question
- Description question
- Version question
- Author question
- Input validation

## Acceptance Criteria

- [ ] Template name question with validation (min 3 chars, hyphen required)
- [ ] Description question with validation (min 10 chars)
- [ ] Version question with default "1.0.0"
- [ ] Author question (optional)
- [ ] Returns basic_info dict
- [ ] Unit tests passing

**Estimated Time**: 3 hours | **Complexity**: 3/10 | **Priority**: MEDIUM
