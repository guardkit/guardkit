---
id: TASK-G7B2-005
title: Roll out Gemini config to remaining active repos + add missing embedding_dimensions
status: backlog
task_type: implementation
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: medium
tags: [graphiti, gemini, rollout, multi-repo, config-tidy]
parent_review: TASK-REV-C7A3
feature_id: FEAT-G7B2
implementation_mode: direct
wave: 3
complexity: 4
depends_on:
  - TASK-G7B2-003
---

# Task: Roll out Gemini config to remaining active repos

## Description

Apply the Gemini config to the remaining 7 active Graphiti-configured repos. Also
fix the pre-existing config drift found in the review: 9 repos are missing an
explicit `embedding_dimensions: 1024` (currently implicit), and
`youtube-transcript-mcp` is missing the field entirely (risk of silent
dimension mismatch if the embedder model ever changes).

Can run in parallel with TASK-G7B2-004.

## Target Repos

| Repo | `.mcp.json` | `.guardkit/graphiti.yaml` | Extra |
|------|-------------|---------------------------|-------|
| `nats-infrastructure` | ✅ | ✅ | Add explicit `embedding_dimensions: 1024` |
| `nats-core` | ✅ | ✅ | Already has explicit `embedding_dimensions: 1024` |
| `lpa-platform` | ✅ | ✅ | Add explicit `embedding_dimensions: 1024` |
| `dotnet-functional-fastendpoints-exemplar` | ✅ | ✅ | Add explicit `embedding_dimensions: 1024` |
| `require-kit` | ❌ | ✅ | yaml only; add explicit `embedding_dimensions: 1024` |
| `deepagents-player-coach-exemplar` | ❌ | ✅ | yaml only; add explicit `embedding_dimensions: 1024` |
| `youtube-transcript-mcp` | ❌ | ✅ | yaml only; **add `embedding_dimensions: 1024` (currently missing entirely)** |

## Acceptance Criteria

For each repo:

- [ ] `.mcp.json` (where present) env block swapped to Gemini (per TASK-G7B2-002)
- [ ] `.guardkit/graphiti.yaml` switched to `llm_provider: gemini`, `llm_model:
      openai/gpt-oss-120b`, `llm_small_model: openai/gpt-oss-20b` (per TASK-G7B2-003)
- [ ] **Explicit `embedding_dimensions: 1024`** present in the yaml (add where
      missing)
- [ ] Per-repo `project_id` preserved (don't overwrite)
- [ ] Per-repo smoke test: `mcp__graphiti__search_nodes` works against that
      repo's group IDs (if MCP is configured for the repo)

## Explicit Skips

Do NOT modify:
- `vllm-profiling` — intentionally uses local GB10 vLLM (profiling target)
- `agentecflow_platform` — independent MCP config (Docker Compose custom
  agents, no Graphiti)
- `deepagents` — independent MCP config (LangChain docs HTTP MCP, no Graphiti)
- `architect-agent_delete_me` — retired
- `deepagents-player-coach-exemplar-original` — retired

## Implementation Notes

- Recommend committing one repo at a time, not a mass commit — easier to
  bisect if one repo breaks after a seed run
- The `embedding_dimensions` cleanup is worth doing in the same commits
  (zero-cost while the yaml is open) but call it out in each commit message
  so it's traceable
- Record any repo that fails its smoke test and revert just that one. Don't
  block the rest.

## Non-goals

- Smoke-testing full end-to-end ingestion in every repo — the guardkit
  smoke-test in TASK-G7B2-003 validates the pipeline; here we just validate
  per-repo config loads cleanly
- Backfilling or re-seeding any repo's existing knowledge graph
