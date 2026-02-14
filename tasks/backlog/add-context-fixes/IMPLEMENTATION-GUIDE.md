# Implementation Guide: add-context Fixes (FEAT-AC01)

## Parent Review

TASK-REV-1294 — [Review report](.claude/reviews/TASK-REV-1294-review-report.md)

## Wave Structure

### Wave 1: Core Fixes (4 tasks, parallel-safe)

All Wave 1 tasks touch different files and can execute in parallel.

| Task | Title | Complexity | Mode | Files |
|------|-------|-----------|------|-------|
| TASK-FIX-AC01 | Enable full_doc fallback parser | 3 | task-work | `full_doc_parser.py`, `registry.py`, `graphiti.py` |
| TASK-FIX-AC02 | Reduce SEMAPHORE_LIMIT + delay | 3 | task-work | `graphiti.py` (CLI options) |
| TASK-FIX-AC03 | Check add_episode return value | 2 | task-work | `graphiti.py` (episode loop) |
| TASK-FIX-AC04 | Suppress index-exists log noise | 1 | direct | `graphiti.py` (logging setup) |

**Note on AC02/AC03/AC04 file overlap**: All three modify `graphiti.py` but in different sections:
- AC02: early setup (SEMAPHORE_LIMIT) + episode loop (delay)
- AC03: episode loop (return value check)
- AC04: early setup (logging)

If running in parallel, merge carefully. Sequential execution within `graphiti.py` changes is safer.

### Wave 2: Hardening + Content (2 tasks)

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-FIX-AC05 | Add ADR Status sections | 1 | direct | None |
| TASK-FIX-AC06 | Retry with backoff | 4 | task-work | TASK-FIX-AC02 |

AC06 depends on AC02 because the retry logic should complement (not replace) the SEMAPHORE_LIMIT reduction.

## Execution Strategy

```
Wave 1 (parallel):
  AC01 ─── full_doc_parser.py, registry.py
  AC02 ┐
  AC03 ├── graphiti.py (different sections, merge on completion)
  AC04 ┘

Wave 2 (parallel):
  AC05 ─── docs/architecture/decisions/*.md
  AC06 ─── graphiti_client.py
```

## Verification

After all tasks complete, re-run the original command and verify:
```bash
guardkit graphiti add-context docs/architecture/
```

Expected:
- 0 "Index already exists" messages
- 0 "No parser found" messages (all 29 files captured)
- 0 "Max pending queries exceeded" errors
- 0 "Missing required section: Status" warnings
- Summary: `Added 29 files, N episodes` (N >= 29, full_doc may chunk large files)
