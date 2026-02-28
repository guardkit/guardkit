---
id: TASK-VEF-001
title: Fix vllm-embed.sh GPU memory, model name, and pre-flight check
status: completed
completed: 2026-02-28T12:35:00Z
updated: 2026-02-28T12:35:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria verified, bash syntax validated"
created: 2026-02-28T12:00:00Z
priority: high
tags: [vllm, embedding, gpu, infrastructure]
parent_review: TASK-CC3E
feature_id: FEAT-VEF
implementation_mode: task-work
wave: 1
complexity: 3
completed_location: tasks/completed/TASK-VEF-001/
---

# Task: Fix vllm-embed.sh GPU memory, model name, and pre-flight check

## Description

Apply four fixes to `scripts/vllm-embed.sh` identified in the TASK-CC3E review. All changes are in a single file.

## Parent Review

TASK-CC3E — Diagnose vLLM embedding GPU memory error and fix
Report: `.claude/reviews/TASK-CC3E-review-report.md`

## Changes Applied

### 1. Reduce GPU memory utilization default (CRITICAL)

Changed default from 0.15 to 0.03 on lines 19 and 27.

### 2. Add `--served-model-name` to vllm serve (HIGH)

Added `--served-model-name $(basename "$MODEL")` to EXTRA_ARGS for nomic (line 37) and nemotron (line 42) presets.

### 3. Fix test curl model name (HIGH)

Added comment on line 116 noting both short and full model names work via `--served-model-name`.

### 4. Add pre-flight GPU memory check (LOW)

Added nvidia-smi pre-flight check (lines 79-89) before `docker run`. Gracefully skips when nvidia-smi unavailable.

## Acceptance Criteria

- [x] `VLLM_EMBED_GPU_UTIL` defaults to 0.03
- [x] `--served-model-name` added to nomic and nemotron presets
- [x] Pre-flight GPU memory check warns when insufficient memory
- [x] Script still works when nvidia-smi is not available (pre-flight check skipped gracefully)

## Files Modified

- `scripts/vllm-embed.sh`
