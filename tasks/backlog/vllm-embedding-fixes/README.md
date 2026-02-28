# FEAT-VEF: vLLM Embedding Infrastructure Fixes

## Problem Statement

The vLLM embedding server cannot coexist with the main LLM server on the Dell Pro Max GB10 due to GPU memory over-allocation, model name mismatches prevent API calls from succeeding, and the graphiti.yaml references an incorrect embedding model name.

## Solution Approach

Three targeted fixes addressing configuration and scripting gaps identified in the TASK-CC3E architectural review (score: 78/100):

1. **Fix vllm-embed.sh** — GPU memory default, served model name alias, pre-flight check
2. **Fix graphiti.yaml** — Correct embedding model name to match vLLM served model
3. **Verify end-to-end** — Manual verification on actual hardware

## Subtask Summary

| Task | Title | Wave | Mode | Complexity |
|------|-------|------|------|------------|
| TASK-VEF-001 | Fix vllm-embed.sh (GPU, model name, pre-flight) | 1 | task-work | 3 |
| TASK-VEF-002 | Fix graphiti.yaml embedding model name | 1 | direct | 1 |
| TASK-VEF-003 | End-to-end verification | 2 | manual | 2 |

## Execution Strategy

**Wave 1** (parallel): TASK-VEF-001 + TASK-VEF-002 — different files, no conflicts
**Wave 2** (sequential): TASK-VEF-003 — depends on both Wave 1 tasks, requires GB10 hardware

## Parent Review

- **Review Task**: TASK-CC3E
- **Report**: `.claude/reviews/TASK-CC3E-review-report.md`
