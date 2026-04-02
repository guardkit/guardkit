---
id: TASK-ROT-004
title: Update init.py help text to include orchestrator template
status: completed
completed: 2026-04-02T00:00:00Z
completed_location: tasks/completed/TASK-ROT-004/
updated: 2026-04-02T00:00:00Z
created: 2026-04-02T00:00:00Z
priority: high
tags: [installer, cli, help-text]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: direct
wave: 3
complexity: 1
depends_on:
  - TASK-ROT-003
---

# Task: Update init.py help text to include orchestrator template

## Description

Update the hardcoded template list in `guardkit/cli/init.py` (line ~1631) to include `langchain-deepagents-orchestrator`.

## Current Text

```
Available templates: default, fastapi-python, react-typescript, nextjs-fullstack, langchain-deepagents, langchain-deepagents-weighted-evaluation.
```

## Updated Text

```
Available templates: default, fastapi-python, react-typescript, nextjs-fullstack, langchain-deepagents, langchain-deepagents-weighted-evaluation, langchain-deepagents-orchestrator.
```

## Acceptance Criteria

- [x] `guardkit init --help` output includes `langchain-deepagents-orchestrator`
- [x] Template list is alphabetically/logically ordered
