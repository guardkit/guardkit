---
id: TASK-FIX-AC05
title: Add missing Status sections to ADR files in docs/architecture/decisions/
status: backlog
created: 2026-02-13T00:00:00Z
updated: 2026-02-13T00:00:00Z
priority: medium
tags: [fix, documentation, adr]
task_type: implementation
parent_review: TASK-REV-1294
feature_id: FEAT-AC01
wave: 2
implementation_mode: direct
complexity: 1
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add missing Status sections to ADR files

## Description

All 8 ADR files in `docs/architecture/decisions/` are missing a `## Status` section, which is part of the standard ADR template (Michael Nygard format). The ADR parser warns about this on every run.

## Review Reference

TASK-REV-1294 recommendation R8a (P2). See `.claude/reviews/TASK-REV-1294-review-report.md` AC-004.

## Acceptance Criteria

- [ ] AC-001: All 8 ADR files in `docs/architecture/decisions/` have a `## Status` section
- [ ] AC-002: Status value is `Accepted` for all existing ADRs
- [ ] AC-003: Status section placed between title and `## Context` (standard position)
- [ ] AC-004: No "Missing required section: Status" warnings on next `add-context` run

## Files to Update

1. `docs/architecture/decisions/ADR-SP-001-falkordb-over-neo4j.md`
2. `docs/architecture/decisions/ADR-SP-002-client-level-metadata-injection.md`
3. `docs/architecture/decisions/ADR-SP-003-adversarial-cooperation.md`
4. `docs/architecture/decisions/ADR-SP-004-progressive-disclosure.md`
5. `docs/architecture/decisions/ADR-SP-005-ai-first-agent-enhancement.md`
6. `docs/architecture/decisions/ADR-SP-006-adaptive-ceremony.md`
7. `docs/architecture/decisions/ADR-SP-007-markdown-authoritative.md`
8. `docs/architecture/decisions/ADR-SP-008-hash-based-task-ids.md`

Add `## Status\n\nAccepted\n` after the H1 title, before `## Context`.

## Test Execution Log
[Automatically populated by /task-work]
