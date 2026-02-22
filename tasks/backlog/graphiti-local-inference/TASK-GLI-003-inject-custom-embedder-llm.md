---
id: TASK-GLI-003
title: Update GraphitiClient.initialize() to inject custom embedder/LLM
task_type: implementation
status: backlog
created: 2026-02-22T23:45:00Z
updated: 2026-02-22T23:45:00Z
priority: high
tags: [graphiti, vllm, embeddings, llm-client]
complexity: 5
parent_review: TASK-REV-8B3A
feature_id: FEAT-GLI
wave: 2
implementation_mode: task-work
dependencies: [TASK-GLI-002]
---

# Task: Update GraphitiClient.initialize() to Inject Custom Embedder/LLM

## Description

Modify `GraphitiClient.initialize()` to pass custom `embedder` and `llm_client` instances to the `Graphiti()` constructor when the provider is not "openai". This is the core integration point — after this task, Graphiti seeding will use the local vLLM server.

## Context

- graphiti-core `Graphiti()` accepts optional `embedder: EmbedderClient` and `llm_client: LLMClient` kwargs
- When omitted, defaults to `OpenAIEmbedder()` and `OpenAIClient()` (cloud OpenAI)
- graphiti-core ships:
  - `OpenAIEmbedder(config=OpenAIEmbedderConfig(base_url=..., embedding_model=..., api_key=...))` — works with any OpenAI-compatible endpoint
  - `OpenAIGenericClient(config=LLMConfig(base_url=..., model=..., api_key=...))` — purpose-built for local models
- Current `initialize()` at `graphiti_client.py:495` creates `Graphiti()` without these kwargs

## Acceptance Criteria

- [ ] When `config.llm_provider != "openai"`:
  - Create `OpenAIGenericClient` with `base_url=config.llm_base_url`, `model=config.llm_model`, `api_key="local-key"`
  - Pass as `llm_client` kwarg to `Graphiti()`
- [ ] When `config.embedding_provider != "openai"`:
  - Create `OpenAIEmbedder` with `base_url=config.embedding_base_url`, `embedding_model=config.embedding_model`, `api_key="local-key"`
  - Pass as `embedder` kwarg to `Graphiti()`
- [ ] When provider is "openai", maintain current behavior (no kwargs, Graphiti uses defaults)
- [ ] When local provider, skip `OPENAI_API_KEY` check (line 520) — local inference doesn't need it
  - But still require `OPENAI_API_KEY` if either provider is "openai"
- [ ] Update `GraphitiClientFactory.create_client()` and `create_and_init_client()` to propagate new config
- [ ] Tests: unit tests with mocked Graphiti constructor verifying correct embedder/llm_client injection
- [ ] Tests: verify backward compatibility — existing "openai" config works unchanged

## Implementation Notes

```python
# In initialize(), after the FalkorDB/Neo4j driver creation:

# Build optional embedder
embedder = None
if self.config.embedding_provider != "openai":
    from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
    embedder = OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            base_url=self.config.embedding_base_url,
            embedding_model=self.config.embedding_model,
            api_key="local-key",
        )
    )

# Build optional llm_client
llm_client = None
if self.config.llm_provider != "openai":
    from graphiti_core.llm_client import OpenAIGenericClient, LLMConfig
    llm_client = OpenAIGenericClient(
        config=LLMConfig(
            base_url=self.config.llm_base_url,
            model=self.config.llm_model,
            api_key="local-key",
        )
    )

# Pass to Graphiti constructor
self._graphiti = Graphiti(
    graph_driver=driver,  # or uri/user/password
    embedder=embedder,
    llm_client=llm_client,
)
```

## Key Files

- `guardkit/knowledge/graphiti_client.py` — GraphitiClient.initialize(), GraphitiClientFactory
- `tests/knowledge/test_graphiti_client.py` — existing tests

## Reference

- Parent review: TASK-REV-8B3A
- graphiti-core constructor: `graphiti_core/graphiti.py` lines 132-236
