---
id: TASK-G7B2-003
title: Flip guardkit's .guardkit/graphiti.yaml to Gemini + end-to-end smoke test
status: backlog
task_type: implementation
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: high
tags: [graphiti, gemini, config, smoke-test, gating]
parent_review: TASK-REV-C7A3
feature_id: FEAT-G7B2
implementation_mode: direct
wave: 2
complexity: 3
depends_on:
  - TASK-G7B2-001
  - TASK-G7B2-002
---

# Task: Flip guardkit's `.guardkit/graphiti.yaml` to Gemini + smoke test

## Description

With the Python client supporting `gemini` (TASK-G7B2-001) and the MCP server
configured for Gemini (TASK-G7B2-002), switch guardkit's own
`.guardkit/graphiti.yaml` to use Gemini and run the end-to-end smoke tests.
This task is the **gate** for the multi-repo rollout in Wave 3 — if any smoke
test fails, do not proceed.

## Acceptance Criteria

### Config changes

- [ ] `llm_provider: gemini`
- [ ] `llm_model: gemini-2.5-flash`
- [ ] vLLM/Ollama `llm_base_url` lines removed or commented out
- [ ] `embedding_provider: vllm` (unchanged)
- [ ] `embedding_base_url: http://promaxgb10-41b1:8001/v1` (unchanged)
- [ ] `embedding_dimensions: 1024` (explicit — already present)
- [ ] `max_concurrent_episodes: 3` (conservative start; Gemini tolerates more)

### Smoke tests (all must pass)

- [ ] Claude Code restart — MCP server initializes cleanly, no errors in logs
- [ ] `mcp__graphiti__search_nodes` against `guardkit__project_overview` returns
      existing nodes (query path works, no LLM call)
- [ ] `guardkit graphiti seed-system --force` with one small group completes
      successfully and produces new nodes/edges in FalkorDB within normal time
      window — **watch for stalls that could indicate thinking-mode
      contamination on Gemini 2.5** (research doc claims Flash doesn't emit
      think blocks; verify)
- [ ] `mcp__graphiti__add_memory` with a test episode returns success and the
      resulting nodes appear in FalkorDB Browser (`http://whitestocks:3000`)
- [ ] FalkorDB vector-dim sanity check: new embeddings stored at 1024-dim
- [ ] `guardkit graphiti status` reports `llm_provider: gemini` and healthy
      connection

## Implementation Notes

- `GOOGLE_API_KEY` must be exported in the shell before running any CLI
  commands — `guardkit graphiti seed-system` won't find it otherwise
- On 429 rate-limit errors (unlikely on Gemini free tier but possible),
  lower `max_concurrent_episodes` to 1 and re-run
- If an episode takes >60 seconds, suspect thinking-mode contamination. Abort
  the seed, check graphiti-core's GeminiClient for `thinking_config` handling,
  or fall back to `gemini-2.5-flash-lite` (no reasoning mode)
- If smoke-test fails, revert both this task's changes AND TASK-G7B2-002's
  config changes to unblock the existing MCP workflow — do NOT leave the repo
  in a half-flipped state

## Files to Change

- [.guardkit/graphiti.yaml](.guardkit/graphiti.yaml)

## Gate

**This task is blocking for Wave 3 (TASK-G7B2-004, TASK-G7B2-005).** Do not
start Wave 3 until all smoke tests here pass.
