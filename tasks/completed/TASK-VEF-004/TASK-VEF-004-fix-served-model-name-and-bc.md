---
id: TASK-VEF-004
title: Fix served-model-name and pre-flight bc calculation in vllm-embed.sh
status: completed
created: 2026-02-28T15:00:00Z
updated: 2026-03-01T12:00:00Z
completed: 2026-03-01T12:00:00Z
completed_location: tasks/completed/TASK-VEF-004/
priority: high
tags: [vllm, embedding, fix]
parent_review: TASK-REV-36CC
feature_id: FEAT-VEF
implementation_mode: task-work
wave: 3
complexity: 2
depends_on:
  - TASK-VEF-001
---

# Task: Fix served-model-name and pre-flight bc calculation in vllm-embed.sh

## Description

Two issues identified during TASK-VEF-003 verification (analysed in TASK-REV-36CC):

### Fix 1: Register both short and full model names (HIGH)

The `--served-model-name` flag in vLLM **replaces** the default model name rather than adding an alias. Currently only the short name is registered, causing 404 errors when using the full HuggingFace path.

**File**: `scripts/vllm-embed.sh:37,42`

**Initial proposal** (INCORRECT — duplicate flags only keep last value):
```bash
EXTRA_ARGS="... --served-model-name $(basename "$MODEL") --served-model-name $MODEL"
```

**Actual fix** (space-separated values under single flag):
```bash
EXTRA_ARGS="... --served-model-name $(basename "$MODEL") $MODEL"
```

**Why**: vLLM v0.13.0 treats duplicate `--served-model-name` flags as override (last value wins), not additive. Space-separated values under a single flag correctly register both names: `['nomic-embed-text-v1.5', 'nomic-ai/nomic-embed-text-v1.5']`.

### Fix 2: Handle unified memory in pre-flight GPU check (LOW)

The pre-flight GPU memory check produces `(standard_in) 1: syntax error` on the GB10.

**Root cause**: GB10 unified memory returns `[N/A]` for nvidia-smi memory queries, not a number. The `tr -d ' '` whitespace stripping proposed in the initial review is insufficient — `[N/A]` is not whitespace, it's a fundamentally different value.

**File**: `scripts/vllm-embed.sh:79-94`

**Actual fix**: Added regex check `[[ "$VALUE" =~ ^[0-9]+$ ]]` to validate numeric values before running `bc`, with informational message for unified memory systems:
```bash
if [[ "$FREE_MEM_MIB" =~ ^[0-9]+$ ]] && [[ "$TOTAL_MEM_MIB" =~ ^[0-9]+$ ]]; then
  # ... bc calculation ...
else
  echo "Note: GPU memory query not supported (unified memory). Skipping pre-flight check."
fi
```

## Acceptance Criteria

- [x] `curl /v1/models` returns both short and full model names
- [x] `curl /v1/embeddings` with short name returns 200
- [x] `curl /v1/embeddings` with full name returns 200
- [x] Pre-flight check runs without `(standard_in)` errors
- [x] Pre-flight check shows informational message on unified memory systems

## Evidence

- Initial verification: `docs/reviews/graphiti-local-embedding/verify_1.md`
- Final verification: `docs/reviews/graphiti-local-embedding/verify_2.md`
- Review report: `.claude/reviews/TASK-REV-36CC-review-report.md`
