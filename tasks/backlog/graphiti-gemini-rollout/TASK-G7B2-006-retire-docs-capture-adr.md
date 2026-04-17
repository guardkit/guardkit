---
id: TASK-G7B2-006
title: Retire graphiti-macbook-offload doc + capture ADR for Gemini decision
status: backlog
task_type: documentation
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: low
tags: [graphiti, groq, docs, adr]
parent_review: TASK-REV-C7A3
feature_id: FEAT-G7B2
implementation_mode: direct
wave: 4
complexity: 2
depends_on:
  - TASK-G7B2-004
  - TASK-G7B2-005
---

# Task: Retire macbook-offload doc + capture ADR

## Description

With Gemini shipping to production, the GB10-vs-MacBook LLM toggle pattern
documented in `docs/reference/graphiti-macbook-offload.md` is superseded.
Either mark the doc as retired or remove it. Also capture the decision as an
ADR in the Graphiti knowledge graph so future sessions (and other projects
sharing the FalkorDB) can find the rationale.

## Acceptance Criteria

- [ ] `docs/reference/graphiti-macbook-offload.md`: either
  - Add a "superseded by Gemini rollout (TASK-REV-C7A3)" banner at the top with
    a link to `docs/research/graphiti-cloud/graphiti-cloud-llm-config.md`, OR
  - Delete if no historical value remains (author's call)
- [ ] `mcp__graphiti__add_memory` ADR captured in `architecture_decisions`
      group:
  - **Name**: `ADR: Graphiti LLM on Gemini (2.5 Flash)`
  - **Content** includes: problem (GPU contention), decision (Gemini +
    `openai/2.5 Flash`), alternatives considered (Groq — deferred due to Developer tier closure,
    Bedrock, Anthropic, stay-local), rationale (native client in graphiti-core
    and MCP server, generous free tier, no thinking mode on Flash, strategic
    alignment with Gemini 3.1 Pro for Forge), rollback path (flip
    `llm_provider: vllm`),
    explicit non-goals (cloud reranker, GB10 decommission this wave)
- [ ] Optional: open a follow-up task "Decommission GB10 Qwen2.5-14B vLLM on
      port 8000" — only open this once Gemini has been live for 7+ days across
      all rolled-out repos with no issues

## Files to Change

- [docs/reference/graphiti-macbook-offload.md](docs/reference/graphiti-macbook-offload.md)

## Non-goals

- Actually stopping the GB10 vLLM on port 8000 — that's a separate follow-up
  task, gated on a soak period
- Updating every references to the old MacBook toggle pattern in other docs
  (do as PRs discover them, not preemptively)
