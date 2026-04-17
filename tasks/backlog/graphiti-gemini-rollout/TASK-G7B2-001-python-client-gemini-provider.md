---
id: TASK-G7B2-001
title: Add gemini provider support to guardkit Python Graphiti client + fix embedding_dim passthrough
status: backlog
task_type: implementation
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: high
tags: [graphiti, gemini, python-client, bug-fix]
parent_review: TASK-REV-C7A3
feature_id: FEAT-G7B2
implementation_mode: task-work
wave: 1
complexity: 4
---

# Task: Add `gemini` provider support + fix embedding_dim passthrough

## Description

The GuardKit Python Graphiti client (`guardkit.knowledge`) currently hardcodes
valid providers to `("openai", "vllm", "ollama")` in two places and rejects
`llm_provider: gemini` at config-validation time. Add a `gemini` branch that
instantiates `graphiti_core.llm_client.gemini_client.GeminiClient` via the
installed graphiti-core 0.26.3 (which already ships Gemini support).

In the same PR, fix a **latent bug**: `_build_embedder()` never passes
`embedding_dimensions` through to `OpenAIEmbedderConfig(embedding_dim=...)`,
and the settings → GraphitiConfig bridge in `_do_init_thread_client` also
drops the field. Works today by accident (nomic-v1.5 returns 1024-dim
natively) but silently breaks any future embedding-model change.

## Acceptance Criteria

- [ ] `valid_providers` in [guardkit/knowledge/config.py](guardkit/knowledge/config.py) ~line 186 extended to
      include `"gemini"`
- [ ] `VALID_PROVIDERS` in [guardkit/knowledge/graphiti_client.py](guardkit/knowledge/graphiti_client.py) line 108
      extended to include `"gemini"`
- [ ] `_build_llm_client()` returns a `GeminiClient` when
      `llm_provider == "gemini"`, reading `GOOGLE_API_KEY` from env
- [ ] `_build_embedder()` passes `embedding_dim=self.config.embedding_dimensions`
      to `OpenAIEmbedderConfig` when set
- [ ] The `settings → GraphitiConfig` bridge in `_do_init_thread_client`
      propagates `embedding_dimensions=settings.embedding_dimensions`
- [ ] `pyproject.toml`: new optional group `gemini = ["graphiti-core[google-genai]"]`,
      included in the `all` extra
- [ ] Unit tests added under `tests/knowledge/`:
  - Config parsing accepts `llm_provider: gemini` without raising
  - `GraphitiConfig(llm_provider="gemini")` validates
  - `_build_llm_client()` returns a `GeminiClient` instance for gemini provider
  - `_build_embedder()` passes `embedding_dim=1024` through when set
- [ ] Existing tests still pass (no regression on vllm/ollama/openai paths)

## Implementation Notes

- Import `GeminiClient` lazily inside the branch — environments without the
  `[google-genai]` extra installed shouldn't fail at module-load time
- `GOOGLE_API_KEY` must be read from env at client-construction time, not at
  config-load time — yaml must never contain the key
- The `LLMConfig` used by `GeminiClient` is
  `graphiti_core.llm_client.config.LLMConfig` (distinct from GuardKit's own
  config dataclass)
- Gemini's `model` defaults to `gemini-2.5-flash` if `llm_model` is None in
  config — pick a reasonable default so operators don't need to duplicate it
  everywhere

## Files to Change

- [guardkit/knowledge/config.py](guardkit/knowledge/config.py) — `valid_providers`
- [guardkit/knowledge/graphiti_client.py](guardkit/knowledge/graphiti_client.py) — `VALID_PROVIDERS`, `_build_llm_client()`, `_build_embedder()`, `_do_init_thread_client`
- [pyproject.toml](pyproject.toml) — new `gemini` extra, update `all`
- `tests/knowledge/test_config.py` — provider tests
- `tests/knowledge/test_graphiti_client_embedder_injection.py` or new file — embedder dim + gemini LLM build tests

## Non-goals

- No `GRAPHITI_LLM_PROVIDER` env-var toggle (yaml field is enough)
- No cloud reranker wiring (defer; GeminiRerankerClient exists but isn't needed
  until we observe a need)
- Do **not** touch MCP server config (TASK-G7B2-002)
