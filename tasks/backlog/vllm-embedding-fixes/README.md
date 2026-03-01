# FEAT-VEF: vLLM Embedding Infrastructure Fixes

## Problem Statement

The vLLM embedding server cannot coexist with the main LLM server on the Dell Pro Max GB10 due to GPU memory over-allocation, model name mismatches prevent API calls from succeeding, and the graphiti.yaml references an incorrect embedding model name.

## Solution Approach

Three targeted fixes addressing configuration and scripting gaps identified in the TASK-CC3E architectural review (score: 78/100):

1. **Fix vllm-embed.sh** — GPU memory default, served model name alias, pre-flight check
2. **Fix graphiti.yaml** — Correct embedding model name to match vLLM served model
3. **Verify end-to-end** — Manual verification on actual hardware

## Subtask Summary

| Task | Title | Wave | Mode | Complexity | Status |
|------|-------|------|------|------------|--------|
| TASK-VEF-001 | Fix vllm-embed.sh (GPU, model name, pre-flight) | 1 | task-work | 3 | Done |
| TASK-VEF-002 | Fix graphiti.yaml embedding model name | 1 | direct | 1 | Done |
| TASK-VEF-003 | End-to-end verification | 2 | manual | 2 | Done |
| TASK-VEF-004 | Fix served-model-name + bc sanitization | 3 | task-work | 2 | Done |
| TASK-VEF-005 | Re-run complete verification (all 4 steps) | 4 | manual | 2 | Done |

## Execution Strategy

**Wave 1** (parallel): TASK-VEF-001 + TASK-VEF-002 — different files, no conflicts
**Wave 2** (sequential): TASK-VEF-003 — depends on both Wave 1 tasks, requires GB10 hardware
**Wave 3** (sequential): TASK-VEF-004 — fixes found during Wave 2 verification
**Wave 4** (sequential): TASK-VEF-005 — re-verify all steps after Wave 3 fix

## Reviews

- **Initial Review**: TASK-CC3E — `.claude/reviews/TASK-CC3E-review-report.md`
- **Verification Review**: TASK-REV-36CC — `.claude/reviews/TASK-REV-36CC-review-report.md`
