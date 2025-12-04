---
id: TASK-PD-015
title: Split react-fastapi-monorepo/agents/*.md
status: backlog
created: 2025-12-03T16:00:00Z
updated: 2025-12-03T16:00:00Z
priority: medium
tags: [progressive-disclosure, phase-4, template-agents, react-fastapi-monorepo]
complexity: 4
blocked_by: [TASK-PD-011]
blocks: [TASK-PD-016]
review_task: TASK-REV-426C
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Split react-fastapi-monorepo/agents/*.md

## Phase

**Phase 4: Built-in Template Agents** (LOW RISK)

## Description

Split the react-fastapi-monorepo template agents using the automated splitter.

## Template Agents

```
installer/global/templates/react-fastapi-monorepo/agents/
└── [agent files]
```

## Execution

```bash
# Dry run first
python3 scripts/split-agent.py --dry-run --template react-fastapi-monorepo

# Execute split
python3 scripts/split-agent.py --template react-fastapi-monorepo

# Validate
python3 scripts/split-agent.py --validate --template react-fastapi-monorepo
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

## Phase 4 Checkpoint

After completing TASK-PD-012 through TASK-PD-015:

```bash
# Validate all template agents
for template in react-typescript fastapi-python nextjs-fullstack react-fastapi-monorepo; do
    echo "=== $template ==="
    python3 scripts/split-agent.py --validate --template $template
done
```

All template agents should show ≥40% reduction before proceeding to Phase 5.
