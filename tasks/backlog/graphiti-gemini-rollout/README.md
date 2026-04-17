# Feature: Graphiti Gemini 2.5 Flash Rollout

- **Feature ID**: FEAT-G7B2
- **Parent Review**: [TASK-REV-C7A3](../../review_complete/TASK-REV-C7A3-graphiti-groq-gpt-oss-rollout.md)
- **Review Report**: [.claude/reviews/TASK-REV-C7A3-review-report.md](../../../.claude/reviews/TASK-REV-C7A3-review-report.md)
- **Research Doc**: [docs/research/graphiti-cloud/graphiti-cloud-llm-config.md](../../../docs/research/graphiti-cloud/graphiti-cloud-llm-config.md)

## Pivot Note (April 2026)

Originally scoped for **Groq + openai/gpt-oss-120b**. Pivoted to **Google
Gemini 2.5 Flash** because Groq's Developer tier closed to new applicants —
Free tier rate limits are too tight for Graphiti's concurrent seeding.
Structural plan unchanged; only the provider/model/env-var specifics differ.
Groq remains a documented fallback when the Developer tier reopens.

## Problem

GB10 runs Qwen2.5-14B (port 8000) for Graphiti entity extraction. This blocks
fine-tuning, model hosting, and dataset-factory GPU work. Graphiti only calls
the LLM during ingestion/seeding — a perfect fit for a cloud API.

## Solution

Move Graphiti's entity-extraction LLM to **Google Gemini 2.5 Flash**. Keep
embeddings local on GB10 (port 8001, nomic-v1.5, 1024-dim).

Why Gemini:

- **Native `GeminiClient` + `GeminiRerankerClient`** in graphiti-core (no OpenAI
  key needed anywhere)
- **Graphiti docs explicitly recommend Gemini** for structured output
- **Generous free tier** — 1000+ req/day on Flash models, no credit card
- **No thinking mode on Flash** — avoids the Qwen3 `<think>` block class of bug
- **Strategic alignment** — Gemini 3.1 Pro already planned for Forge; one provider

## Key Finding From Review (still applies)

The **Graphiti MCP server already has native Gemini support** (alongside groq,
openai, azure_openai, anthropic) in `factories.py`. No upstream PR needed —
config-only on the MCP side. Only GuardKit's Python client (`guardkit.knowledge`)
needs code: three small touches plus one latent-bug fix.

## Subtasks

| Wave | ID | Title | Mode | Depends on |
|------|----|-------|------|------------|
| 1 | TASK-G7B2-001 | Add `gemini` provider + fix embedding_dim bug in Python client | task-work | — |
| 1 | TASK-G7B2-002 | Update guardkit MCP server config (`.mcp.json` + `config-guardkit.yaml`) to Gemini | direct | — |
| 2 | TASK-G7B2-003 | Switch guardkit's `.guardkit/graphiti.yaml` to Gemini + smoke-test | direct | 001, 002 |
| 3 | TASK-G7B2-004 | Roll out to GPU-bound repos (agentic-dataset-factory, forge, specialist-agent) | direct | 003 |
| 3 | TASK-G7B2-005 | Roll out to remaining 7 active repos (+ add missing `embedding_dimensions`) | direct | 003 |
| 4 | TASK-G7B2-006 | Retire graphiti-macbook-offload.md + capture ADR in Graphiti | direct | 004, 005 |

## Execution Strategy

- **Waves 1 and 3** are parallelizable.
- **Wave 2** is the gate — smoke-test must pass before any other repo is touched.
- **Wave 4** runs after all rollout waves complete and soak for a few days.

## Explicit Non-Goals

- Groq (deferred until Developer tier reopens)
- Bedrock / Anthropic / LiteLLM paths
- Cloud reranker for non-Gemini providers
- Decommissioning the GB10 Qwen2.5-14B vLLM on port 8000 — separate follow-up
- `vllm-profiling` (intentionally local), `agentecflow_platform`, `deepagents`
  (independent MCP configs)
- Retired repos (`architect-agent_delete_me`, `deepagents-player-coach-exemplar-original`)

## Secrets

`GOOGLE_API_KEY` is referenced via `"${GOOGLE_API_KEY}"` interpolation in
`.mcp.json`. Export it in your shell before launching Claude Code. Never
commit the raw key.

Get a Google API key at https://aistudio.google.com/apikey (free tier, no
credit card).
