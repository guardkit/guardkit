---
id: TASK-LDB-001
title: "Add langchain-deepagents description and Quick Start to init-project.sh"
status: completed
created: 2026-03-16T00:00:00Z
updated: 2026-03-16T00:00:00Z
completed: 2026-03-16T00:00:00Z
priority: medium
complexity: 2
tags: [installer, init-script, langchain-deepagents]
task_type: implementation
parent_review: TASK-REV-38D7
feature_id: FEAT-LDB
wave: 1
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-LDB-001/
---

# Task: Add langchain-deepagents description and Quick Start to init-project.sh

## Description

Update `~/.agentecflow/scripts/init-project.sh` to include a hardcoded description
line and Quick Start section for the `langchain-deepagents` template, matching the
pattern used by existing built-in templates.

## Changes Required

### 1. Template description case statement (~line 153)

Add after the `react-fastapi-monorepo` case:

```bash
langchain-deepagents)
    echo "  * langchain-deepagents - Python Adversarial Cooperation with DeepAgents/LangGraph (10/10)"
    ;;
```

### 2. Quick Start section (~line 610)

Add after the `react-fastapi-monorepo` Quick Start case:

```bash
langchain-deepagents)
    echo -e "${BOLD}Quick Start for LangChain DeepAgents:${NC}"
    echo "  1. cp .env.example .env && edit API keys"
    echo "  2. uv sync"
    echo "  3. Copy a domain from domains/example-domain/"
    echo "  4. uv run pytest tests/"
    echo "  5. Open in LangGraph Studio"
    ;;
```

## Acceptance Criteria

- [x] `guardkit init` shows descriptive line for langchain-deepagents (not generic bullet)
- [x] After init, Quick Start guidance is displayed
- [x] Existing template descriptions unchanged
- [x] Script passes shellcheck (no syntax errors introduced)
