# Feature: Graphiti MacBook Offload (FEAT-GMO)

## Problem

The GB10 is a single-GPU system. During 50-60 hour dataset generation runs, the GPU is
fully occupied and cannot co-host the Graphiti LLM (port 8000). This blocks project
initialization, system architecture commands, and AutoBuild context loading.

## Solution

Offload the Graphiti LLM to the MacBook Pro M2 Max over Tailscale, leaving GB10 100%
dedicated to dataset generation. The embedding model (port 8001, ~0.5GB) stays on GB10.

## Approach

Ollama (GGUF backend) with Qwen2.5-14B Q4_K_M — chosen over MLX-based options because
Graphiti's workload (long prompts, short JSON output) is prefill-dominated, where GGUF
outperforms MLX in real-world wall-clock time.

Fallback: llama-server if Ollama's json_schema enforcement is insufficient.

## Parent Review

[TASK-REV-GMAC](.claude/reviews/TASK-REV-GMAC-review-report.md)

## Subtasks

| Task | Title | Wave | Mode | Depends On |
|------|-------|------|------|------------|
| TASK-GMO-001 | Install Ollama + Qwen2.5-14B on MacBook | 1 | direct | — |
| TASK-GMO-002 | Test json_schema enforcement | 1 | direct | GMO-001 |
| TASK-GMO-003 | Update Graphiti config for split endpoints | 2 | task-work | GMO-002 |
| TASK-GMO-004 | End-to-end test with split endpoints | 2 | direct | GMO-003 |
| TASK-GMO-005 | Document setup instructions | 3 | direct | GMO-004 |

## Execution Plan

**Wave 1** (Setup + validation): GMO-001 → GMO-002 (sequential, decision gate at GMO-002)
**Wave 2** (Config + integration): GMO-003 → GMO-004 (sequential)
**Wave 3** (Documentation): GMO-005

Decision gate at GMO-002: If json_schema fails on Ollama, switch to llama-server before proceeding.
