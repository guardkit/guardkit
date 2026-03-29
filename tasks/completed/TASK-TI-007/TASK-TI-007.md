---
id: TASK-TI-007
title: Model compatibility matrix documentation
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
completed_location: tasks/completed/TASK-TI-007/
priority: p1
tags: [template, documentation, models, base-template]
complexity: 2
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 2
implementation_mode: direct
depends_on: []
previous_state: in_review
state_transition_reason: "task-complete — all acceptance criteria met"
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-29T00:00:00Z
---

# Task: Model Compatibility Matrix Documentation

## Description

Document known model/parser combinations, quirks, and requirements based on the 11-run history. This prevents the 3 model-specific fixes and saves future developers from repeating the same discovery process.

## What to Build

### 1. Tested Combinations Table

| Model | Parser | Context | Tool Calling | Reasoning | Known Issues |
|-------|--------|---------|-------------|-----------|-------------|
| Qwen2.5-14B | hermes | 32K | Yes (hermes) | No native | Double-serializes tool args |
| Nemotron 3 Nano 4B | qwen3_coder | 16K | Yes | No | Too small for reasoning tasks |
| Qwen3.5-35B-A3B-FP8 | qwen3_coder | 262K | Yes | Native thinking | Best performer |

### 2. vLLM Configuration Side Effects
- `--reasoning-parser qwen3`: Strips `<think>` blocks from `.content`, moves to `reasoning_content`
- LangChain `ChatOpenAI` discards `reasoning_content` (non-standard field)
- Workaround: Remove parser and prompt model to include `<think>` blocks explicitly

### 3. Minimum Requirements for Adversarial Cooperation
- BFCL-V4 score >= 60 (tool calling reliability)
- Context window >= 64K (multi-turn tool-calling conversations)
- JSON output reliability (test with concrete examples before deployment)

### 4. Known Quirks by Model Family
- **Qwen**: Native thinking requires explicit prompting without parser; literal newlines in JSON strings
- **Nemotron**: Small models cannot follow complex format instructions
- **General**: All models benefit from CRITICAL section at prompt end

## Fixes Prevented

TRF-001, TRF-002, TRF-024

## Target Location

`docs/model-compatibility.md` (in the template output)

## Acceptance Criteria

- [x] Tested combinations table with evidence from runs
- [x] vLLM configuration side effects documented
- [x] Minimum requirements specified with benchmark thresholds
- [x] Known quirks per model family
- [x] Inline warnings in relevant code files pointing to this doc

## Effort Estimate

0.5 days

## Completion Summary

### Files Created
- `installer/core/templates/langchain-deepagents/docs/reference/model-compatibility.md`

### Files Modified (inline warnings)
- `installer/core/templates/langchain-deepagents/templates/other/other/agent.py.template`
- `installer/core/templates/langchain-deepagents/templates/other/other/coach-config.yaml.template`
- `installer/core/templates/langchain-deepagents/lib/json_extractor.py`
- `installer/core/templates/langchain-deepagents/lib/factory_guards.py`
