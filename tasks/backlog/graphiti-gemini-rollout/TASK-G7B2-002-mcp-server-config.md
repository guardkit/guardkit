---
id: TASK-G7B2-002
title: Update guardkit MCP server config to use Gemini (shared config-guardkit.yaml + .mcp.json)
status: backlog
task_type: implementation
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: high
tags: [graphiti, gemini, mcp-server, config]
parent_review: TASK-REV-C7A3
feature_id: FEAT-G7B2
implementation_mode: direct
wave: 1
complexity: 2
---

# Task: Update guardkit MCP server config to use Gemini

## Description

The Graphiti MCP server (at
`/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server`) has
native `GeminiClient` support via its `LLMClientFactory` (alongside groq,
openai, azure_openai, anthropic). Config-only change affecting two files:

1. **`guardkit/.mcp.json`** — swap LLM env vars from vLLM to Gemini
2. **`graphiti/mcp_server/config/config-guardkit.yaml`** — set `llm.provider: gemini`

Can run in parallel with TASK-G7B2-001 (no shared files). The MCP-based query
path (`mcp__graphiti__search_nodes`, etc.) works independently of the Python
client path.

## Acceptance Criteria

- [ ] `.mcp.json` env block updated:
  - Remove `OPENAI_API_KEY`, `LLM_API_URL`, `LLM_MODEL`
  - Add `GOOGLE_API_KEY: "${GOOGLE_API_KEY}"` (env-var reference, NOT raw key)
  - Keep `CONFIG_PATH`, `EMBEDDING_API_URL`, `EMBEDDING_DIM`
- [ ] `config-guardkit.yaml` `llm` block updated:
  - `provider: "gemini"`
  - `model: "gemini-2.5-flash"`
  - `providers.gemini.api_key: ${GOOGLE_API_KEY}`
- [ ] Embedder block unchanged (still points at GB10:8001 for nomic-v1.5)
- [ ] Database / graphiti sections unchanged
- [ ] `GOOGLE_API_KEY` exported in shell before Claude Code restart
- [ ] MCP server starts without errors; logs show Gemini provider initialized

## Implementation Notes

- The shared `config-guardkit.yaml` lives in the external `graphiti` repo, not
  inside `guardkit`. Commit separately there.
- `SEMAPHORE_LIMIT` can stay at default; Gemini's free tier is generous. Tune
  later if 429s appear.
- This task ships **without** end-to-end ingestion smoke test — that's
  TASK-G7B2-003. Just verify MCP server boots cleanly.

## Files to Change

- [.mcp.json](.mcp.json)
- `/Users/richardwoollcott/Projects/appmilla_github/graphiti/mcp_server/config/config-guardkit.yaml`

## Non-goals

- `.guardkit/graphiti.yaml` (separate task — TASK-G7B2-003)
- Any other repo's config (Wave 3)
