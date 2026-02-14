# add-context Fixes (FEAT-AC01)

## Problem

`guardkit graphiti add-context docs/architecture/` exhibited 4 issues:
1. **69% of files skipped** — no auto-detecting parser for generic markdown (20/29 files)
2. **FalkorDB query saturation** — "Max pending queries exceeded" errors during episode ingestion
3. **False-positive success reporting** — `✓` shown for files where episode creation silently failed
4. **Log noise** — ~30 "Index already exists" INFO messages + 8 "Missing Status" warnings

## Solution

6 tasks across 2 waves:

| Wave | Tasks | Focus |
|------|-------|-------|
| 1 | AC01, AC02, AC03, AC04 | Parser fallback, rate limiting, error reporting, log noise |
| 2 | AC05, AC06 | ADR content fix, retry resilience |

## Task Summary

| ID | Title | Priority | Complexity |
|----|-------|----------|-----------|
| TASK-FIX-AC01 | Enable full_doc fallback parser | P0 | 3 |
| TASK-FIX-AC02 | Reduce SEMAPHORE_LIMIT + inter-episode delay | P0 | 3 |
| TASK-FIX-AC03 | Fix false-positive success reporting | P1 | 2 |
| TASK-FIX-AC04 | Suppress index-exists log noise | P1 | 1 |
| TASK-FIX-AC05 | Add ADR Status sections | P2 | 1 |
| TASK-FIX-AC06 | Add retry with exponential backoff | P1 | 4 |

## Review Source

[TASK-REV-1294 Review Report](../../../.claude/reviews/TASK-REV-1294-review-report.md)
