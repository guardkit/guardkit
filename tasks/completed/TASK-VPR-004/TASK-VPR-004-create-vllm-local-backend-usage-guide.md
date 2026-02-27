---
id: TASK-VPR-004
title: Create vLLM/local backend usage guide
status: completed
priority: low
complexity: 2
tags: [documentation, vllm, local-llm, gb10, guide]
parent_review: TASK-REV-C960
feature_id: FEAT-VPR
wave: 2
implementation_mode: direct
dependencies: [TASK-VPR-001]
completed: 2026-02-27
---

# Task: Create vLLM/Local Backend Usage Guide

## Description

Create a documentation guide for using GuardKit autobuild with local LLM backends (vLLM, Ollama, etc.), covering when to use local vs API, configuration, and best practices.

## Context

TASK-REV-C960 Recommendation R1: The review established clear guidance on when to use vLLM/GB10 vs Anthropic API. This should be documented for users.

## Acceptance Criteria

- [x] Guide created at `docs/guides/local-backend-autobuild-guide.md`
- [x] Covers: when to use local vs API (decision matrix)
- [x] Covers: vLLM setup (ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY)
- [x] Covers: recommended configuration (--max-turns, timeout_multiplier, --max-parallel)
- [x] Covers: expected performance characteristics (4.3x slowdown, 50% first-pass rate)
- [x] Covers: troubleshooting common issues (GPU contention, turn ceiling, timeout)
- [x] References TASK-REV-C960 review report for data

## Completion Notes

Guide created at `docs/guides/local-backend-autobuild-guide.md` with all sections:
- Decision matrix with clear local vs API criteria
- Full configuration reference (env vars, auto-detection, CLI flags, priority resolution)
- Performance data from TASK-REV-C960 (timing, accuracy, parallelism benchmarks)
- Recommended settings for single task and feature builds
- Troubleshooting for: SDK turn ceiling, GPU contention, timeouts, model alignment, stream errors
- Reference section with source data attribution and key constants
- Cross-references to existing `simple-local-autobuild.md` (setup) and `autobuild-workflow.md` (architecture)
