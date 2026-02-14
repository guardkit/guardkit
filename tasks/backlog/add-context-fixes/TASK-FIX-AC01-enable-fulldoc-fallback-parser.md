---
id: TASK-FIX-AC01
title: Enable full_doc parser as auto-detection fallback for generic markdown
status: backlog
created: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:00:00Z
priority: high
tags: [fix, graphiti, add-context, parser]
task_type: implementation
parent_review: TASK-REV-1294
feature_id: FEAT-AC01
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Enable full_doc parser as auto-detection fallback for generic markdown

## Description

The `FullDocParser.can_parse()` always returns `False`, making it explicit-only via `--type full_doc`. This causes 69% of files (20/29) to be silently skipped during `add-context` runs. Change it to act as a lowest-priority fallback for `.md` files not matched by any other parser.

## Review Reference

TASK-REV-1294 recommendation R5 (P0). See `.claude/reviews/TASK-REV-1294-review-report.md` AC-003.

## Acceptance Criteria

- [ ] AC-001: `FullDocParser.can_parse()` returns `True` for `.md` files when no other parser matches
- [ ] AC-002: Parser registry tries `full_doc` last (after adr, feature_spec, project_doc, project_overview)
- [ ] AC-003: Existing auto-detection for ADR files still works (ADR parser takes precedence)
- [ ] AC-004: `--type full_doc` explicit usage still works unchanged
- [ ] AC-005: Running `add-context docs/architecture/` now captures all 29 files (9 ADR + 20 full_doc)
- [ ] AC-006: Tests cover fallback behaviour and priority ordering

## Implementation Notes

Key files:
- `guardkit/integrations/graphiti/parsers/full_doc_parser.py` — change `can_parse()` to return `True` for `.md` files
- `guardkit/integrations/graphiti/parsers/registry.py` — ensure registration order gives `full_doc` lowest priority
- `guardkit/cli/graphiti.py` — parser registration order (lines 587-593)

The registry's `_try_all_parsers()` iterates `self._parsers.values()` in insertion order. Ensure `FullDocParser` is registered last.

## Test Execution Log
[Automatically populated by /task-work]
