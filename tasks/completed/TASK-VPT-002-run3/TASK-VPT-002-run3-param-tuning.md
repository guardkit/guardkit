---
id: TASK-VPT-002
title: Tune autobuild parameters for vLLM Run 3
status: completed
task_type: implementation
priority: high
tags: [vllm, performance, autobuild, tuning]
complexity: 1
parent_review: TASK-REV-1509
feature_id: FEAT-VR3
wave: 1
implementation_mode: direct
created: 2026-03-07T14:30:00Z
updated: 2026-03-07T15:00:00Z
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-07T15:00:00Z
---

# Task: Tune Autobuild Parameters for vLLM Run 3

## Problem

VPT-001 set `sdk_max_turns=75` and `timeout_multiplier=3.0`. Run 2 showed:
- **33% SDK ceiling hit rate** — FBP-004 (78 turns) and FBP-005 (76 turns) hit the 75-turn ceiling
- **FBP-007 budget exhaustion** — `timeout_multiplier=3.0` reduced `task_timeout` from 9600s to 7200s, insufficient for complex tasks

Qwen3 consumes 2-3x more SDK turns than Claude for equivalent tasks.

## Changes Required

### 1. Increase sdk_max_turns: 75 → 100

Location: The SDK max turns for local backends is set in `guardkit/orchestrator/agent_invoker.py`.

Search for the line that reduces SDK max turns for local backends (currently sets to 75).

### 2. Restore timeout_multiplier: 3.0 → 4.0

Location: The timeout multiplier default for local backends is set in `guardkit/orchestrator/agent_invoker.py` or `guardkit/orchestrator/feature_orchestrator.py`.

Search for the line that sets `timeout_multiplier` default for local backends.

### 3. Keep max_parallel=1

No change needed — already defaults to 1 for local backends per VPT-001.

## Acceptance Criteria

- [x] AC-001: SDK max turns for local backends is 100 (was 75)
- [x] AC-002: Timeout multiplier for local backends is 4.0 (was 3.0)
- [x] AC-003: max_parallel remains 1 for local backends
- [x] AC-004: Anthropic API backend defaults remain unchanged
- [x] AC-005: Log output confirms new values at startup

## References

- Review report: `.claude/reviews/TASK-REV-1509-review-report.md` (Objective 1)
- VPT-001: `tasks/backlog/vllm-perf-tuning/TASK-VPT-001-tune-local-backend-defaults.md`
- Run 2 data: `docs/reviews/vllm-profiling/vllm_run_2.md`
