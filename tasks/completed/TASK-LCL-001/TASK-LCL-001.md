---
id: TASK-LCL-001
title: Fix broken {{ProjectName}} imports in base coach.py.template and agent.py.template
status: completed
created: 2026-04-18T00:00:00Z
completed: 2026-04-18T00:00:00Z
priority: high
tags: [templates, langchain-deepagents, blocker, rendering-bug]
parent_review: TASK-REV-LES1
feature_id: FEAT-LTL1
implementation_mode: direct
wave: 1
conductor_workspace: langchain-template-lessons-wave1-1
complexity: 1
completed_location: tasks/completed/TASK-LCL-001/
---

# Task: Fix broken `{{ProjectName}}` imports in base coach.py.template and agent.py.template

## Description

Two files in `installer/core/templates/langchain-deepagents/` ship with
`{{ProjectName}}` placeholders in positions where the SDK package name should
appear. After rendering, the imports resolve to project modules that do not
exist, making the template un-runnable.

## Evidence

`installer/core/templates/langchain-deepagents/templates/other/agents/coach.py.template:14-17` —
currently:
```python
from {{ProjectName}}.backends import FilesystemBackend
from {{ProjectName}}.middleware import MemoryMiddleware
from {{ProjectName}}.middleware.patch_tool_calls import PatchToolCallsMiddleware
```

Must become (matching `player.py.template:12-14`):
```python
from deepagents.backends import FilesystemBackend
from deepagents.middleware import MemoryMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
```

`installer/core/templates/langchain-deepagents/templates/other/other/agent.py.template:8` —
currently:
```python
from {{ProjectName}}.chat_models import init_chat_model
```

Must become:
```python
from langchain.chat_models import init_chat_model
```

## Acceptance Criteria

- [ ] `coach.py.template` imports `deepagents.backends`, `deepagents.middleware`, `deepagents.middleware.patch_tool_calls` (matching `player.py.template`).
- [ ] `agent.py.template` imports `langchain.chat_models.init_chat_model`.
- [ ] No other file in the base template still uses `{{ProjectName}}` in place of an SDK package name — grep the entire template tree.
- [ ] After rendering the base template into a scratch project (e.g. `ProjectName=scratch`), `python -c "import scratch.coach; import scratch.agent"` succeeds (paired with TASK-LCL-003 which automates this).

## Files

- `installer/core/templates/langchain-deepagents/templates/other/agents/coach.py.template`
- `installer/core/templates/langchain-deepagents/templates/other/other/agent.py.template`

## Implementation Notes

Pure find-and-replace on 4 lines. Keep `{{ProjectName}}` in place for
**project-local** imports (e.g. `from {{ProjectName}}.player_prompts`) —
those are correct. Only the `deepagents.*` and `langchain.chat_models`
imports are broken.

## Links

- Review: [TASK-REV-LES1 report §BLOCKER-1](../../../.claude/reviews/TASK-REV-LES1-review-report.md)
