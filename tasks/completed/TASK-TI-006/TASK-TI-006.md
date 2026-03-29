---
id: TASK-TI-006
title: Observability logging scaffold
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
priority: p1
tags: [template, observability, logging, base-template]
complexity: 3
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 2
implementation_mode: direct
depends_on: []
previous_state: in_progress
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-TI-006/
test_results:
  status: passed
  total: 40
  passed: 40
  failed: 0
  coverage: null
  last_run: 2026-03-29T00:00:00Z
---

# Task: Observability Logging Scaffold

## Description

Create a standard logging module for the `langchain-deepagents` base template that ensures token usage, pipeline stage timing, and error context are logged from the start — preventing the 4 observability gaps that required reactive fixes.

## What to Build

### 1. Token usage logger
- Log `response.usage` after every LLM API call: prompt_tokens, completion_tokens, total_tokens
- Cumulative totals per target and pipeline-wide summary
- Alert if context utilisation exceeds configurable threshold (default 80%)

### 2. Pipeline stage logger
- Log content length at each stage: raw response -> normalized -> extracted -> validated -> written
- Enables detection of truncation, data loss, or unexpected expansion

### 3. Error context logger
- On extraction/validation failure: log first 200 chars + last 200 chars + total length
- Structured format for easy grep/analysis

### 4. Stage timing
- Wall-clock time per pipeline stage
- Cumulative per target and pipeline summary

## Fixes Prevented

TRF-010, TRF-017, TRF-018, TRF-023

## Target Location

`lib/observability.py` (in the template output)

## Acceptance Criteria

- [x] Token usage logged per API call with cumulative totals
- [x] Content length logged at each pipeline stage
- [x] Error context includes head + tail + length
- [x] Stage timing with summaries
- [x] Uses Python `logging` module (not print statements)
- [x] Configurable log level and format

## Implementation Summary

### Files Created
- `installer/core/templates/langchain-deepagents/lib/observability.py` — 280 lines
- `tests/templates/langchain-deepagents/test_observability.py` — 40 tests

### Files Modified
- `installer/core/templates/langchain-deepagents/lib/__init__.py` — added observability exports

### Components
- **TokenTracker**: Per-call + cumulative token logging with configurable context utilisation alerts
- **PipelineStageLogger**: Content length tracking at each pipeline stage (raw→normalized→extracted→validated→written)
- **log_error_context()**: Head/tail snippet logging (200 chars each) + total length on failure
- **StageTimer**: Context-manager-based wall-clock timing with per-target and pipeline summaries
- **configure_logging()**: Convenience setup for the `deepagents.observability` logger

## Effort Estimate

0.5 days
