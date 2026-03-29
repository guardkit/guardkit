# Completion Report: TASK-TI-023

## Summary

Documented the `ainvoke()` message contract and retry pattern across the langchain-deepagents template to prevent the dual system message crash discovered in TASK-REV-R2A1.

## Changes Made

| File | Change |
|------|--------|
| `lib/factory_guards.py` | Added `ainvoke()` message contract block to module docstring (lines 8-14) |
| `templates/other/scaffold/orchestrator_pattern.py.template` | Added retry pattern code example in `on_rejection()` docstring |
| `templates/other/other/AGENTS.md.template` | Added Framework Contract section with ainvoke() rules |

## Acceptance Criteria

- [x] `ainvoke()` contract documented in factory_guards.py
- [x] Retry pattern documented in orchestrator_pattern.py.template
- [x] AGENTS.md.template includes framework contract note
- [x] Warning references TASK-REV-R2A1 for traceability (7 references across 4 files)

## Quality Gates

- Compilation: PASSED (both .py files parse)
- Tests: 59/59 PASSED
- Complexity: 2/10 (micro-task)
- Duration: ~2 minutes

## Traceability

- Parent review: TASK-REV-32D2
- Root cause: TASK-REV-R2A1
- Feature: FEAT-TI (Template Improvements)
