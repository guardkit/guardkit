---
id: TASK-PD-012
title: Split react-typescript/agents/*.md (3 files)
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: medium
tags: [progressive-disclosure, phase-4, template-agents, react-typescript]
complexity: 4
blocked_by: [TASK-PD-011]
blocks: [TASK-PD-016]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Split react-typescript/agents/*.md (3 files)

## Phase

**Phase 4: Built-in Template Agents** (LOW RISK)

## Description

Split the react-typescript template agents using the automated splitter.

## Template Agents

```
installer/global/templates/react-typescript/agents/
├── feature-architecture-specialist.md
├── form-validation-specialist.md
└── react-query-specialist.md
```

## Execution

```bash
# Dry run first
python3 scripts/split-agent.py --dry-run --template react-typescript

# Execute split
python3 scripts/split-agent.py --template react-typescript

# Validate
python3 scripts/split-agent.py --validate --template react-typescript
```

## Expected Outcome

| Agent | Original | Core | Extended |
|-------|----------|------|----------|
| react-query-specialist | ~14KB | ~6KB | ~8KB |
| feature-architecture-specialist | ~12KB | ~5KB | ~7KB |
| form-validation-specialist | ~10KB | ~4KB | ~6KB |

## Acceptance Criteria

- [ ] 3 template agents split successfully
- [ ] 6 files exist (3 core + 3 extended)
- [ ] All core files have loading instructions
- [ ] Average reduction ≥40%

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-011 (global agent validation)
