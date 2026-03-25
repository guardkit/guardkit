---
id: TASK-FIX-SYNTH5
title: Improve synthetic report semantic verification for declarative tasks
status: completed
created: 2026-03-20T23:30:00Z
updated: 2026-03-20T23:30:00Z
completed: 2026-03-20T23:45:00Z
priority: low
tags: [autobuild, synthetic-report, coach, verification, P3]
parent_review: TASK-REV-8BC0
feature_id: FEAT-8BC0
implementation_mode: task-work
wave: 3
complexity: 5
depends_on:
  - TASK-FIX-GEN1
  - TASK-FIX-MODE3
---

# Task: Improve Synthetic Report Semantic Verification

## Description

When direct-mode Player invocations are cancelled and state recovery generates a synthetic report, the Coach uses file-existence verification as a fallback. This cannot verify semantic acceptance criteria like "models match API contract field types exactly" or "Literal constraints applied".

This caused 2 wasted turns in FEAT-5606's TASK-DC-001: Coach rejected turns 1-2 with the same 5 unverifiable criteria, then approved on turn 3 with expanded context.

## Acceptance Criteria

- [x] When synthetic reports are generated, add a lightweight code-reading step that extracts key patterns from changed files (class names, type annotations, constraint decorators, exception classes)
- [x] Extracted patterns are included as evidence in the synthetic report's `completion_promises`
- [x] Coach can use these patterns for text-matching against acceptance criteria
- [x] The code-reading step adds < 5 seconds to synthetic report generation
- [x] Does not require an SDK invocation (pure git diff + AST/regex analysis)

## Key Files

- `guardkit/orchestrator/autobuild.py` (synthetic report generation, ~lines 2754-2884)
- `guardkit/orchestrator/synthetic_report.py`
- `guardkit/orchestrator/quality_gates/coach_validator.py` (synthetic report handling)

## Notes

This is P3 because fixing TASK-FIX-GEN1 (generator lifecycle) and TASK-FIX-MODE3 (default to task-work) will dramatically reduce the frequency of synthetic report generation. This task only matters for the remaining edge cases where synthetic reports are still needed.
