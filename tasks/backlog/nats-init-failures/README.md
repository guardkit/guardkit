# Feature: Fix nats-core init failures

## Problem Statement

Running `guardkit init python-library` on the nats-core project produced two categories of failure:
1. LLM connection errors during system knowledge seeding (config mismatch)
2. YAML frontmatter parsing errors on rule files with unquoted glob patterns

## Solution Approach

- Fix unquoted glob patterns in 8 rule files across 4 templates (source fix)
- Add LLM health check to `guardkit init` for faster failure detection
- Add glob pattern validation to `/template-validate` to prevent regression

## Parent Review

TASK-REV-A8C2 — [Review Report](../../../.claude/reviews/TASK-REV-A8C2-review-report.md)

## Subtasks

| Task | Title | Wave | Mode | Priority |
|------|-------|------|------|----------|
| TASK-NIF-001 | Quote unquoted glob patterns in template rule files | 1 | direct | high |
| TASK-NIF-002 | Add LLM health check to guardkit init | 2 | task-work | medium |
| TASK-NIF-003 | Add glob pattern validation to template-validate | 2 | task-work | medium |

## Execution Strategy

**Wave 1** (immediate, 15 min): TASK-NIF-001 — simple find-and-fix across 8 files
**Wave 2** (backlog, parallel): TASK-NIF-002 + TASK-NIF-003 — independent improvements

## Manual Step (outside repo)

Update nats-core's `.guardkit/graphiti.yaml` LLM endpoint from GB10 to MacBook:
```yaml
# Change from:
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic

# Change to:
llm_provider: ollama
llm_base_url: http://richards-macbook-pro.tailebf801.ts.net:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M
```
