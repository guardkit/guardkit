---
id: TASK-ROT-006
title: Add missing configuration templates (langgraph.json, config YAML, domain)
status: completed
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T12:00:00Z
completed: 2026-04-02T12:00:00Z
priority: medium
tags: [template, configuration, langgraph]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: task-work
wave: 4
complexity: 3
depends_on:
  - TASK-ROT-003
completed_location: tasks/completed/TASK-ROT-006/
---

# Task: Add missing configuration templates

## Description

The orchestrator template is missing three configuration files that the base `langchain-deepagents` template provides. The code templates reference these files at runtime (with fallback defaults), but scaffolding them during `guardkit init` gives users a working starting point.

## Files Added

### 1. `templates/other/other/langgraph.json.template`

LangGraph deployment config mapping graph name `"orchestrator"` to `./src/{{ProjectName}}/agent.py:agent`.

### 2. `templates/other/other/orchestrator-config.yaml.template`

Model selection config with sensible defaults matching `agent.py.template` fallbacks (`_DEFAULT_CONFIG`).

### 3. `templates/other/example-domain/DOMAIN.md.template`

Starter domain file adapted for the orchestrator's two-model architecture (reasoning + implementation).

## Acceptance Criteria

- [x] `langgraph.json.template` exists and references correct agent entrypoint
- [x] `orchestrator-config.yaml.template` has sensible defaults for both models
- [x] `example-domain/DOMAIN.md.template` provides a starter domain file
- [x] All templates use `{{ProjectName}}` placeholder consistently
