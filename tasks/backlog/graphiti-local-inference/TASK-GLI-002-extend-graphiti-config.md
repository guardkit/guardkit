---
id: TASK-GLI-002
title: Extend GraphitiConfig for local inference provider settings
task_type: implementation
status: backlog
created: 2026-02-22T23:45:00Z
updated: 2026-02-22T23:45:00Z
priority: high
tags: [graphiti, config, vllm, embeddings]
complexity: 4
parent_review: TASK-REV-8B3A
feature_id: FEAT-GLI
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Extend GraphitiConfig for Local Inference Provider Settings

## Description

Add fields to `GraphitiConfig` (frozen dataclass) and `load_graphiti_config()` to support configurable LLM and embedding providers. When provider is "vllm" or "ollama", the client should use `base_url` to point at the local inference server instead of OpenAI.

## Context

- `GraphitiConfig` is a frozen dataclass at `guardkit/knowledge/graphiti_client.py:98`
- Config is loaded from `.guardkit/graphiti.yaml` by `guardkit/knowledge/config.py`
- graphiti-core accepts `embedder` and `llm_client` kwargs in its `Graphiti()` constructor
- graphiti-core ships `OpenAIGenericClient` (purpose-built for local models) and `OpenAIEmbedder` (accepts `base_url`)

## Acceptance Criteria

- [ ] Add new fields to `GraphitiConfig`:
  - `llm_provider: str = "openai"` — "openai" | "vllm" | "ollama"
  - `llm_base_url: Optional[str] = None` — e.g., "http://promaxgb10-41b1:8000/v1"
  - `llm_model: Optional[str] = None` — e.g., "Qwen/Qwen3-Coder-30B-A3B"
  - `embedding_provider: str = "openai"` — "openai" | "vllm" | "ollama"
  - `embedding_base_url: Optional[str] = None` — e.g., "http://promaxgb10-41b1:8001/v1"
  - `embedding_model: str = "text-embedding-3-small"` — model name (already exists, just ensure it's used)
- [ ] Validate provider values in `__post_init__`
- [ ] Update `load_graphiti_config()` in `config.py` to read new YAML fields
- [ ] Support environment variable overrides: `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_BASE_URL`
- [ ] Backward compatible: existing configs without new fields default to OpenAI
- [ ] Tests: unit tests for new config fields, validation, env var overrides

## Key Files

- `guardkit/knowledge/graphiti_client.py` — GraphitiConfig dataclass
- `guardkit/knowledge/config.py` — load_graphiti_config()
- `.guardkit/graphiti.yaml` — config file
- `tests/knowledge/test_graphiti_client.py` — existing tests

## Reference

- Parent review: TASK-REV-8B3A
