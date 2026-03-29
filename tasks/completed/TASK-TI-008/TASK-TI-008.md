---
id: TASK-TI-008
title: Pre-flight validation script (--validate / guardkit validate)
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
previous_state: in_progress
state_transition_reason: "All acceptance criteria met, 59/59 tests passing"
priority: p2
tags: [template, automation, validation, base-template]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 3
implementation_mode: task-work
depends_on: [TASK-TI-004]
test_results:
  status: passed
  total: 59
  passed: 59
  failed: 0
  coverage: null
  last_run: 2026-03-29T00:00:00Z
---

# Task: Pre-Flight Validation Script

## Description

Create an automated pre-flight validation script that runs the first-run success checklist programmatically. Catches the top wiring issues before the first pipeline execution. Becomes a `guardkit validate` command.

## What to Build

### Automated Checks (wiring)
- [x] Player tool inventory matches expected allowlist
- [x] Coach tool list is empty (or evaluator-only)
- [x] Player does NOT have write_output
- [x] Factory uses `create_agent()` for tool-restricted agents
- [x] `max_tokens` explicitly set for all model configs
- [x] Domain config parses without errors
- [x] Metadata field types match validation logic (array vs scalar, range vs enum)
- [x] JSON extraction pipeline order is correct

### Manual Review Prompts (prompts + model config)
- [x] "Does your Player prompt end with a CRITICAL Response Format section?" [Y/n]
- [x] "Does your Coach prompt include explicit accept/reject criteria?" [Y/n]
- [x] "Have you tested your model/parser combination with tool calling?" [Y/n]
- [x] "Is your vLLM reasoning-parser configuration compatible with your extraction?" [Y/n]

### Output
```
$ guardkit validate

Automated Checks:
  [PASS] Player tools: {'rag_retrieval'} (expected: {'rag_retrieval'})
  [PASS] Coach tools: set() (expected: set())
  [PASS] Player does not have write_output
  [PASS] max_tokens set: Player=4096, Coach=2048
  [PASS] Domain config parses: 8 targets, 5 metadata fields
  [FAIL] Metadata field 'turns' uses range notation but validator treats as enum

Manual Review:
  ? Does your Player prompt end with a CRITICAL Response Format section?
  ? Does your Coach prompt include explicit accept/reject criteria?

Result: 1 FAIL, 2 manual checks pending
```

## Target Location

`lib/preflight.py` + CLI entry point (in the template output)

## Acceptance Criteria

- [x] Automated checks for all wiring items
- [x] Manual review prompts for prompt/model items
- [x] Clear PASS/FAIL output with details
- [x] Exit code 1 if any automated check fails
- [x] Can run as `guardkit validate` or `python -m lib.preflight`
- [x] Unit tests for each automated check

## Effort Estimate

1 day

## Implementation Summary

### Files Created
- `installer/core/templates/langchain-deepagents/lib/preflight.py` (370 lines)
- `tests/templates/langchain-deepagents/test_preflight.py` (380 lines)

### Files Modified
- `installer/core/templates/langchain-deepagents/lib/__init__.py` (exports added)

### Key Design Decisions
- AST-based Python analysis (handles both `x = {...}` and `x: set[str] = {...}`)
- Stdlib-only dependencies (ast, json, pathlib, re) - consistent with other lib modules
- YAML parsing with PyYAML fallback to basic parser
- Each check is an independent function returning `CheckResult` (testable in isolation)
