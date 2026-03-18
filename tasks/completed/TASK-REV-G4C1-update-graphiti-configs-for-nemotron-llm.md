---
id: TASK-REV-G4C1
title: Update Graphiti configs across all repos for Nemotron LLM
status: completed
task_type: review
created: 2026-03-18T09:00:00Z
updated: 2026-03-18T09:35:00Z
priority: high
tags: [graphiti, config, nemotron, vllm, multi-repo]
complexity: 3
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  findings_count: 5
  recommendations_count: 3
  decision: implement-direct
  report_path: .claude/reviews/TASK-REV-G4C1-review-report.md
  completed_at: 2026-03-18T09:30:00Z
---

# Task: Update Graphiti configs across all repos for Nemotron LLM

## Description

Following the vLLM port reallocation (TASK-REV-5B3A), the Graphiti LLM has been switched from Qwen3-Coder-Next (served as `claude-sonnet-4-6` on port 8000) to Nemotron 3 Nano 4B FP8 (served as `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8` on port 8000).

All `.guardkit/graphiti.yaml` configs across appmilla_github repos still reference the old model name, causing 404 errors:

```
The model `claude-sonnet-4-6` does not exist.
```

Evidence: `docs/reviews/additonal-templates/add-context-arch_4.md` — Graphiti fails with 404 when trying to use the old model name against the new Nemotron vLLM instance.

Confirmed working model name from vLLM: `docs/reviews/graphiti-nemotron/models.md` shows the model is serving as `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8`.

## Review Scope

1. **Identify all configs**: Catalogue every `.guardkit/graphiti.yaml` across appmilla_github repos that needs `llm_model` updated
2. **Assess model name approach**: Decide whether to:
   - Update configs to use the actual model name (`nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8`)
   - Or add `--served-model-name` alias to `vllm-graphiti.sh` so existing configs work
3. **Consider `guardkit init --copy-graphiti`**: Check if the init flow needs updating so new projects get the correct model name
4. **Embedding model**: Confirm `nomic-embed-text-v1.5` on port 8001 is unchanged and working
5. **Remediation plan**: Provide the exact config changes needed per repo

## Known Affected Repos

| Repo | Config Path | Current `llm_model` |
|------|-------------|---------------------|
| guardkit | `.guardkit/graphiti.yaml` | `claude-sonnet-4-6` |
| agentic-dataset-factory | `.guardkit/graphiti.yaml` | `claude-sonnet-4-6` |
| deepagents-player-coach-exemplar | `.guardkit/graphiti.yaml` | `claude-sonnet-4-6` |
| deepagents-player-coach-exemplar-original | `.guardkit/graphiti.yaml` | `claude-sonnet-4-6` |
| vllm-profiling | `.guardkit/graphiti.yaml` | `claude-sonnet-4-6` |
| youtube-transcript-mcp | `.guardkit/graphiti.yaml` | `claude-sonnet-4-6` |
| require-kit | `.guardkit/graphiti.yaml` | No LLM config (project_id only) |

## Acceptance Criteria

- [ ] All `.guardkit/graphiti.yaml` files updated with correct `llm_model`
- [ ] Decision documented: actual model name vs served-model-name alias
- [ ] `guardkit init --copy-graphiti` flow verified for new projects
- [ ] Embedding config confirmed unchanged
- [ ] At least one repo verified working with `guardkit graphiti add-context` after update

## Context

- Parent review: TASK-REV-5B3A (wrong project seeded to Graphiti)
- New port allocation: 8000=Graphiti (Nemotron), 8001=Embed (nomic), 8002=AutoBuild (Qwen3-Coder)
- New script: `scripts/vllm-graphiti.sh`
- The 4 remaining agentic-dataset-factory architecture files still need seeding after this config fix

## Implementation Notes

[Space for review findings and recommendations]

## Test Execution Log

[Automatically populated by /task-work]
