# Completion Report: TASK-GMR-008

## Summary

Wired up the `/task-review` command's `--capture-knowledge` flag and [A]ccept decision checkpoint to write review findings to the Graphiti knowledge graph via MCP.

## Files Modified

| File | Change |
|------|--------|
| `installer/core/commands/task-review.md` | Phase 4.5: Added Graphiti write step after interactive capture session. Phase 5: Added `capture_review_to_graphiti()` function and LLM execution instructions for [A]ccept handler. |
| `guardkit/knowledge/review_knowledge_capture.py` | Added `format_review_for_graphiti()` function that formats review data into two Graphiti episodes (findings → `guardkit__project_decisions`, outcome → `guardkit__task_outcomes`). |
| `tests/test_task_review_knowledge_capture.py` | Added 20 tests for `format_review_for_graphiti()` covering group IDs, content formatting, edge cases (empty findings, string inputs, missing scores, dict recommendations). |

## Architecture

Two write paths, both writing to the same Graphiti groups:

1. **Phase 4.5** (`--capture-knowledge` flag) — Interactive capture session followed by Graphiti write. Captures user-provided insights alongside automated review data.
2. **Phase 5 [A]ccept** — Automatic write on review acceptance. No interactive session needed.

Access method priority: MCP `mcp__graphiti__add_memory` (Tier 0) → CLI `guardkit graphiti add-context` (Tier 1) → Skip with warning (Tier 2).

## Test Results

- Tests: 51 passed, 0 failed
- New tests: 20 (TestFormatReviewForGraphiti class)
- Existing tests: 31 (unchanged, all passing)

## Feature Progress

FEAT-GMR (Graphiti MCP Restoration):
- Wave 3 tasks: TASK-GMR-007 (task-complete write path) + **TASK-GMR-008 (task-review write path) ✅**
