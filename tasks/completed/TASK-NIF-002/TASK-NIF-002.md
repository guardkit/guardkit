---
id: TASK-NIF-002
title: Add LLM health check to guardkit init before seeding
status: completed
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
completed: 2026-04-03T00:00:00Z
completed_location: tasks/completed/TASK-NIF-002/
priority: medium
tags: [init, graphiti, llm, health-check, ux]
parent_review: TASK-REV-A8C2
feature_id: FEAT-NIF
implementation_mode: task-work
wave: 2
complexity: 4
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
organized_files:
  - TASK-NIF-002.md
---

# Task: Add LLM health check to guardkit init before seeding

## Description

When `guardkit init` copies a `graphiti.yaml` and proceeds to system knowledge seeding (Step 3), it currently takes ~32 seconds to exhaust all retries before the circuit breaker trips on an unreachable LLM. Add a pre-flight health check that validates LLM reachability before attempting seeding.

## Acceptance Criteria

- [x] Before Step 3, send a lightweight request to the configured `llm_base_url` (e.g., GET /v1/models)
- [x] If unreachable within 5s, display clear error: "LLM at {url} is unreachable. System knowledge seeding requires an LLM. Skip seeding? [y/n]"
- [x] If user chooses to skip, continue init without Step 3 (project knowledge still seeded)
- [x] If user chooses not to skip, exit with instructions to fix the config
- [x] Health check adds <2s to the happy path

## Implementation Notes

- The health check should use the same `llm_base_url` from the resolved `graphiti.yaml`
- A simple HTTP GET to `/v1/models` endpoint is sufficient — all OpenAI-compatible APIs support this
- This is the same endpoint that vLLM, Ollama, and OpenAI serve
- Consider reusing the existing `httpx` client if available, or use `urllib.request` for zero deps

## Implementation Summary

### Files Changed
- `guardkit/cli/init.py` — Added `_check_llm_reachable()` async function and integrated pre-flight check before Step 3

### Files Created
- `tests/cli/test_init_llm_health.py` — 13 tests covering all branches

### Test Results
- 13/13 new tests passing
- 102/102 existing init tests passing (no regressions)
