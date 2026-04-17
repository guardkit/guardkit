---
id: TASK-G7B2-004
title: Roll out Gemini config to GPU-bound repos (agentic-dataset-factory, forge, specialist-agent)
status: backlog
task_type: implementation
created: 2026-04-17T00:00:00Z
updated: 2026-04-17T00:00:00Z
priority: high
tags: [graphiti, gemini, rollout, multi-repo]
parent_review: TASK-REV-C7A3
feature_id: FEAT-G7B2
implementation_mode: direct
wave: 3
complexity: 3
depends_on:
  - TASK-G7B2-003
---

# Task: Roll out Gemini config to GPU-bound repos

## Description

Apply the same `.mcp.json` and `.guardkit/graphiti.yaml` diffs from Wave 1/2 to
the three repos that benefit most from freeing the GB10 GPU. These are the
heaviest concurrent Graphiti users, so getting them off the local LLM unlocks
the fine-tuning and dataset-factory work.

Can run in parallel with TASK-G7B2-005 (no shared files; separate repos).

## Target Repos

| Repo | `.mcp.json` | `.guardkit/graphiti.yaml` | Notes |
|------|-------------|---------------------------|-------|
| `agentic-dataset-factory` | ✅ | ✅ | Biggest GPU beneficiary |
| `forge` | ✅ | ✅ | Software-factory, heavy user |
| `specialist-agent` | ✅ | ✅ | Architecture agent; has extra MCP entry (`architect-agent`) — leave it alone |

## Acceptance Criteria

For each repo:

- [ ] `.mcp.json` env block replaced with the Gemini shape from TASK-G7B2-002
      (preserving each repo's `CONFIG_PATH` if different; otherwise identical)
- [ ] `.guardkit/graphiti.yaml` updated per TASK-G7B2-003 (preserving the
      per-repo `project_id` — do NOT overwrite with `guardkit`)
- [ ] `embedding_dimensions: 1024` present explicitly (add if missing)
- [ ] Per-repo smoke test: launch Claude Code in that repo's working dir,
      verify `mcp__graphiti__search_nodes` works against that repo's own group
      IDs
- [ ] Commit to each repo separately with a clear message referencing
      TASK-REV-C7A3

## Implementation Notes

- **Preserve `project_id` per repo** — it's the FalkorDB namespace key. Copying
  the guardkit yaml wholesale would merge all repos' knowledge into
  `guardkit__*` groups and break isolation. Diff carefully.
- `specialist-agent`'s `.mcp.json` may have an extra `architect-agent` MCP
  server entry. Only touch the `graphiti` entry.
- If any repo fails its smoke test, revert just that repo and flag it — don't
  block the other two.

## Non-goals

- Other repos (covered in TASK-G7B2-005)
- `vllm-profiling` (intentional local LLM)
- Decommissioning GB10's port-8000 vLLM (post-rollout task)
