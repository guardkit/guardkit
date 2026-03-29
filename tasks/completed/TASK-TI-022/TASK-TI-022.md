---
id: TASK-TI-022
title: Fix agent.py.template — align entrypoint with create_agent factories
status: completed
created: 2026-03-29T23:30:00Z
updated: 2026-03-30T00:05:00Z
completed: 2026-03-30T00:05:00Z
completed_location: tasks/completed/TASK-TI-022/
priority: p0
tags: [template, fix, entrypoint, sdk-alignment]
complexity: 3
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 0
implementation_mode: task-work
depends_on: [TASK-TI-019, TASK-TI-021]
test_results:
  status: passed
  coverage: 100
  last_run: 2026-03-30T00:00:00Z
---

# Task: Fix agent.py.template — Align Entrypoint with create_agent Factories

## Description

The `agent.py.template` entrypoint imports `create_deep_agent` and `FilesystemBackend` for Player creation, and wires them at module level. After TASK-TI-019 and TASK-TI-021 switch the factories to `create_agent()`, the entrypoint must be updated to match.

Additionally, the config should move from `coach-config.yaml` to `agent-config.yaml` with per-role model configuration, matching the proven `agentic-dataset-factory/agent-config.yaml` pattern.

## What to Change

1. **`agent.py.template`**: Update imports and factory calls to match new `player.py.template` and `coach.py.template` signatures
2. **`coach-config.yaml.template`**: Rename to `agent-config.yaml.template` with per-role config:

```yaml
player:
  provider: local
  model: {{DefaultModel}}
  endpoint: {{LocalEndpoint}}
  temperature: 0.6

coach:
  provider: local
  model: {{DefaultModel}}
  endpoint: {{LocalEndpoint}}
  temperature: 0.3

generation:
  max_turns: 3
  llm_retry_attempts: 3
  llm_retry_backoff: 2.0
```

3. **Update `langgraph.json.template`**: Ensure entrypoint reference still works

## Acceptance Criteria

- [x] `agent.py.template` does not import `create_deep_agent`
- [x] Player and Coach created via updated factory functions
- [x] `coach-config.yaml.template` renamed to `agent-config.yaml.template`
- [x] Per-role model configuration supported
- [x] `langgraph.json.template` still works
- [x] Module-level wiring pattern preserved for LangGraph Studio compatibility

## Effort Estimate

1 hour
