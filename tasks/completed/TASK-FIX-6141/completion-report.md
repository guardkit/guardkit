# Completion Report: TASK-FIX-6141

## Summary

Fixed `extract_acceptance_criteria()` search path divergence from `_find_task_file()` in `agent_invoker.py`. Replaced 20 lines of custom file search logic with a single delegation call.

## Changes

| File | Change | Lines |
|------|--------|-------|
| `guardkit/orchestrator/agent_invoker.py` | Replaced divergent file search (lines 4108-4129) with `self._find_task_file(task_id)` | -20 / +1 |
| `tests/unit/test_agent_invoker.py` | Added 2 new tests: `design_approved` directory + slug-suffixed filenames | +38 |

## Bugs Fixed

1. **Missing directories**: `extract_acceptance_criteria()` now searches all 6 task directories (`backlog`, `design_approved`, `in_progress`, `in_review`, `completed`, `blocked`) instead of only 3
2. **Wrong filename pattern**: Now uses `rglob(f"{task_id}*.md")` via `_find_task_file()` instead of exact `f"{task_id}.md"` match, correctly finding slug-suffixed filenames

## Test Results

- Total tests in `TestExtractAcceptanceCriteria`: 9/9 passed
- New tests added: 2
  - `test_extract_finds_design_approved_directory`
  - `test_extract_finds_slug_suffixed_filename`
- Regression: None

## Impact

Unblocks TASK-DB-005 (and similar tasks) from scoring 0/6 in vLLM autobuild runs. With this fix, acceptance criteria will be correctly injected into Player prompts regardless of task directory or filename format.
