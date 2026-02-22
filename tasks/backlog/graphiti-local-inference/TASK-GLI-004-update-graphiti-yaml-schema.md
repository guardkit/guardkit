---
id: TASK-GLI-004
title: Update .guardkit/graphiti.yaml schema and config loader
task_type: implementation
status: backlog
created: 2026-02-22T23:45:00Z
updated: 2026-02-22T23:45:00Z
priority: medium
tags: [graphiti, config, yaml]
complexity: 2
parent_review: TASK-REV-8B3A
feature_id: FEAT-GLI
wave: 1
implementation_mode: task-work
dependencies: [TASK-GLI-002]
---

# Task: Update .guardkit/graphiti.yaml Schema and Config Loader

## Description

Update the `.guardkit/graphiti.yaml` file with new local inference provider fields and ensure the config loader reads them correctly.

## Context

- `.guardkit/graphiti.yaml` currently has: `enabled`, `graph_store`, `falkordb_host/port`, `timeout`, `embedding_model`, `project_id`, `group_ids`
- Config loader is at `guardkit/knowledge/config.py` — `load_graphiti_config()`
- TASK-GLI-002 adds the new fields to `GraphitiConfig`; this task wires them into the YAML file

## Acceptance Criteria

- [ ] Add new fields to `.guardkit/graphiti.yaml` with comments:
  ```yaml
  # LLM provider for Graphiti entity extraction
  # Options: openai (default), vllm, ollama
  llm_provider: vllm
  llm_base_url: http://promaxgb10-41b1:8000/v1
  llm_model: Qwen/Qwen3-Coder-30B-A3B

  # Embedding provider for Graphiti vector search
  # Options: openai (default), vllm, ollama
  embedding_provider: vllm
  embedding_base_url: http://promaxgb10-41b1:8001/v1
  embedding_model: nomic-ai/nomic-embed-text-v1.5
  ```
- [ ] Update `load_graphiti_config()` to read new fields with defaults
- [ ] Ensure backward compatibility: YAML files without new fields default to "openai"
- [ ] Update `.guardkit/graphiti.yaml` comments to document the new options

## Key Files

- `.guardkit/graphiti.yaml` — config file
- `guardkit/knowledge/config.py` — config loader

## Reference

- Parent review: TASK-REV-8B3A
