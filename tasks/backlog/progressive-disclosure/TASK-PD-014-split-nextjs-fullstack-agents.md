---
id: TASK-PD-014
title: Split nextjs-fullstack/agents/*.md
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: medium
tags: [progressive-disclosure, phase-4, template-agents, nextjs-fullstack]
complexity: 4
blocked_by: [TASK-PD-011]
blocks: [TASK-PD-016]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Split nextjs-fullstack/agents/*.md

## Phase

**Phase 4: Built-in Template Agents** (LOW RISK)

## Description

Split the nextjs-fullstack template agents using the automated splitter.

## Template Agents

```
installer/global/templates/nextjs-fullstack/agents/
└── [agent files]
```

## Execution

```bash
# Dry run first
python3 scripts/split-agent.py --dry-run --template nextjs-fullstack

# Execute split
python3 scripts/split-agent.py --template nextjs-fullstack

# Validate
python3 scripts/split-agent.py --validate --template nextjs-fullstack
```

## Acceptance Criteria

- [ ] All template agents split successfully
- [ ] Core + extended files created for each
- [ ] All core files have loading instructions
- [ ] Average reduction ≥40%

## Estimated Effort

**0.5 days**

## Dependencies

- TASK-PD-011 (global agent validation)
