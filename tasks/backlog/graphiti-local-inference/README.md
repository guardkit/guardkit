# Feature: Graphiti Local Inference via vLLM (FEAT-GLI)

## Problem

Graphiti seeding fails for large documents due to OpenAI API rate limiting. A single `add_episode()` call on the feature-spec v2 document (~70KB) triggers ~140 LLM calls + ~215 embedding API calls, overwhelming OpenAI's per-minute rate limits.

## Solution

Deploy local embeddings + LLM inference on the Dell ProMax GB10 via vLLM, fully eliminating OpenAI rate limit dependency. graphiti-core natively supports custom embedder/LLM injection via `base_url` — zero library changes required.

## Architecture

```
MacBook Pro ──Tailscale──> Dell ProMax GB10 (128GB, Blackwell GPU)
     │                        ├── vLLM :8000 (Qwen3-Coder-30B LLM)
     │                        └── vLLM :8001 (nomic-embed-text-v1.5 embeddings)
     │
     └──Tailscale──> Synology NAS (whitestocks)
                        └── FalkorDB :6379 (graph database)
```

## Subtasks

| # | Task ID | Title | Wave | Status |
|---|---------|-------|------|--------|
| 1 | TASK-GLI-001 | GB10 vLLM setup guide (embedding model + optimal config) | 1 | Backlog |
| 2 | TASK-GLI-002 | Extend GraphitiConfig for local inference provider settings | 1 | Backlog |
| 3 | TASK-GLI-003 | Update GraphitiClient.initialize() to inject custom embedder/LLM | 2 | Backlog |
| 4 | TASK-GLI-004 | Update .guardkit/graphiti.yaml schema and config loader | 1 | Backlog |
| 5 | TASK-GLI-005 | Test seeding feature-spec v2 document | 3 | Backlog |

## Execution Strategy

### Wave 1 (Parallel)
- TASK-GLI-001: Setup guide and benchmarks on GB10
- TASK-GLI-002: Extend config dataclass
- TASK-GLI-004: Update YAML schema and loader

### Wave 2
- TASK-GLI-003: Core integration (depends on TASK-GLI-002)

### Wave 3
- TASK-GLI-005: End-to-end test (depends on all Wave 1+2 tasks)

## Parent Review

- [TASK-REV-8B3A Review Report](../../../.claude/reviews/TASK-REV-8B3A-review-report.md)
